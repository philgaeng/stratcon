#!/usr/bin/env python3
"""Cutoff manager utilities for reporting pipelines."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Sequence, List, cast, Any

import numpy as np

import pandas as pd
from dateutil.relativedelta import relativedelta

from backend.services.core.config import PHILIPPINES_TZ, verify_source_type
from backend.services.core.utils import ReportLogger
from backend.services.data.db_manager import DbQueries

_DEFAULT_CUTOFF_VALUES: Dict[str, int] = {
    "cutoff_day": 1,
    "cutoff_hour": 0,
    "cutoff_minute": 0,
    "cutoff_second": 0,
}


class CutoffManager:
    """Handles retrieval and application of cutoff settings."""

    def __init__(
        self,
        *,
        logger: Optional[ReportLogger] = None,
        client_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        epc_id: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        self.logger = logger or ReportLogger()
        self.conn = conn
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.epc_id = epc_id
        self._defaults_cache: Optional[Dict[str, Optional[Dict[str, int]]]] = None
        self.building_id = None
        if self.tenant_id is not None:
            try:
                self.building_id = DbQueries.get_building_id_for_tenant(
                    self.tenant_id, conn=self.conn
                )
                self.logger.debug(f"building_id initiated for tenant {self.tenant_id}: {self.building_id}")
            except Exception as exc:  # pragma: no cover - best effort helper
                self.logger.debug(
                    f"Failed to resolve building_id for tenant {self.tenant_id}: {exc}"
                )

        if self.client_id is None and self.tenant_id is not None:
            try:
                self.client_id = DbQueries.get_client_id_for_tenant(
                    self.tenant_id, conn=self.conn
                )
            except Exception as exc:  # pragma: no cover - best effort helper
                self.logger.debug(
                    f"Failed to resolve client_id for tenant {self.tenant_id}: {exc}"
                )

        if self.epc_id is None and self.client_id is not None:
            try:
                self.epc_id = DbQueries.get_epc_id_for_client(
                    self.client_id, conn=self.conn
                )
            except Exception as exc:  # pragma: no cover - best effort helper
                self.logger.debug(
                    f"Failed to resolve epc_id for client {self.client_id}: {exc}"
                )
        self.logger.debug(f"cutoff manager initiated for client {self.client_id}, epc {self.epc_id}, tenant {self.tenant_id}, building {self.building_id}")

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------
    @staticmethod
    def create_cutoff_datetime(
        cutoff_day: int, 
        hour: int = 23, 
        minute: int = 59, 
        second: int = 59,
    ) -> datetime:
        """Return a cutoff datetime localised to the Philippines timezone."""
        base = datetime(2024, 1, cutoff_day, hour, minute, second)
        return PHILIPPINES_TZ.localize(base)

    @staticmethod
    def _as_ph_timezone(value: datetime) -> datetime:
        if value.tzinfo is None:
            return PHILIPPINES_TZ.localize(value)
        return value.astimezone(PHILIPPINES_TZ)

    @staticmethod
    def _normalize_series_to_ph(series: pd.Series) -> pd.Series:
        """Convert a series of timestamps to Philippines timezone."""
        ts_series = pd.Series(pd.to_datetime(series, errors="coerce"), index=series.index)

        if ts_series.empty:
            return ts_series
        if ts_series.dt.tz is None:
            return ts_series.dt.tz_localize(
                PHILIPPINES_TZ, nonexistent="NaT", ambiguous="NaT"
            )
        return ts_series.dt.tz_convert(PHILIPPINES_TZ)

    @staticmethod
    def _normalize_cutoff_points(
        cutoff_points: Sequence[datetime],
    ) -> pd.DatetimeIndex:
        """Convert raw cutoff points to a sorted, timezone-aware index."""
        cutoff_index = pd.to_datetime(list(cutoff_points), errors="coerce")
        cutoff_index = cutoff_index.dropna()
        if cutoff_index.empty:
            return cutoff_index
        if cutoff_index.tz is None:
            cutoff_index = cutoff_index.tz_localize(PHILIPPINES_TZ)
        else:
            cutoff_index = cutoff_index.tz_convert(PHILIPPINES_TZ)
        cutoff_index = cutoff_index.sort_values(ascending=False)
        return pd.DatetimeIndex(cutoff_index.unique())

    def _apply_cutoff_tags(
        self, df: pd.DataFrame, cutoff_points: Sequence[datetime]
    ) -> pd.DataFrame:
        """Assign cutoff month tags using explicit cutoff points."""
        cutoff_index = self._normalize_cutoff_points(cutoff_points)
        if cutoff_index.empty:
            raise ValueError("No cutoff timestamps available.")

        df = df.copy()
        timestamp_series = cast(pd.Series, df["timestamp"])
        normalized_timestamp = self._normalize_series_to_ph(timestamp_series)
        timestamp_idx = cast(int, df.columns.get_loc("timestamp"))
        df = df.drop(columns=["timestamp"])
        df.insert(timestamp_idx, "timestamp", normalized_timestamp)
        result_frames: List[pd.DataFrame] = []
        cutoff_points_i = cutoff_index[:-1]
        cutoff_points_j = cutoff_index[1:]
        for cutoff_point_i, cutoff_point_j in zip(cutoff_points_i, cutoff_points_j):
            mask = (df["timestamp"] <= cutoff_point_i) & (df["timestamp"] > cutoff_point_j)
            part_df = df.loc[mask, :].copy()
            if part_df.empty:
                continue
            try:
                month_cutoff = part_df['timestamp'].dt.month.value_counts().idxmax()
                year_cutoff = part_df['timestamp'].dt.year.value_counts().idxmax()
                month_year_cutoff = f"{year_cutoff}-{month_cutoff}"
                tagged_part_df = part_df.assign(**{"Year-Month-cut-off": month_year_cutoff})
                result_frames.append(tagged_part_df)
            except Exception as tagging_error:  # pragma: no cover - defensive
                self.logger.error(
                    f"❌ Unable to tag cutoff months using meter timestamps for cutoff points "
                    f"{cutoff_point_i} and {cutoff_point_j}: {tagging_error}"
                )
                raise ValueError(
                    "Unable to tag cutoff months using meter timestamps"
                ) from tagging_error
        if not result_frames:
            raise ValueError("Unable to compute cutoff tags with provided timestamps.")
        return pd.concat(result_frames)
        

    # ------------------------------------------------------------------
    # Data fetch helpers
    # ------------------------------------------------------------------
    def get_cutoff_datetime_timestamps_for_tenant_from_meter_records(
        self,
        tenant_id: int,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
        source: str = "meter_records",
    ) -> Dict[int, Dict[str, List]]:
        """Return mapping of meter_id -> {loads, timestamps} for the tenant."""
        if source != "meter_records":
            raise ValueError(
                "get_cutoff_datetime_timestamps_for_tenant_from_meter_records "
                "is only supported for 'meter_records' source."
            )

        mapping: Dict[int, Dict[str, List]] = {}
        loads_by_meter = DbQueries.get_loads_grouped_by_meter_for_tenant(
            tenant_id=tenant_id,
            conn=conn,
            logger=logger or self.logger,
        )
        for meter_id, load_ids in loads_by_meter.items():
            timestamps = DbQueries.get_meter_records_timestamps(
                meter_id=meter_id,
                conn=conn,
                logger=logger or self.logger,
            )
            mapping[meter_id] = {
                "loads": load_ids,
                "timestamps": timestamps,
            }
        return mapping

    def default_cutoff_timestamp_list(
        self,
        cutoff_values: Dict[str, int],
        nb_values: int = 36,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[datetime]:
        """Generate a list of cutoff timestamps going backwards in time."""
        if not cutoff_values:
            return []

        cutoff_day = int(cutoff_values.get("cutoff_day") or 1)
        cutoff_hour = int(cutoff_values.get("cutoff_hour") or 0)
        cutoff_minute = int(cutoff_values.get("cutoff_minute") or 0)
        cutoff_second = int(cutoff_values.get("cutoff_second") or 0)

        reference = pd.Timestamp.now(tz=PHILIPPINES_TZ)
        base_year = year or reference.year
        base_month = month or reference.month

        try:
            current = datetime(
                base_year,
                base_month,
                cutoff_day, 
                cutoff_hour, 
                cutoff_minute, 
                cutoff_second,
            )
        except ValueError:
            # Clamp the day within the target month's bounds.
            reference_month_start = datetime(base_year, base_month, 1)
            last_day = (reference_month_start + relativedelta(day=31)).day
            current = datetime(
                base_year,
                base_month,
                min(cutoff_day, last_day),
                cutoff_hour,
                cutoff_minute,
                cutoff_second,
            )

        timestamps: List[datetime] = []
        localized_current = PHILIPPINES_TZ.localize(current)
        for _ in range(max(nb_values, 1)):
            timestamps.append(localized_current)
            localized_current = localized_current - relativedelta(months=1)
        
        self.logger.debug(f"default cutoff timestamp list: len= {len(timestamps)}, first= {timestamps[:3]}, last= {timestamps[-2]}")
        return sorted(timestamps)

    # ------------------------------------------------------------------
    # Defaults handling
    # ------------------------------------------------------------------


    def get_cutoff_default_values_for_client(
        self, client_id: Optional[int] = None
    ) -> Dict[str, int]:
        defaults = DbQueries.get_default_values_for_client(client_id, conn=self.conn)
        return defaults

    def get_cutoff_default_values_for_building(
        self, building_id: Optional[int] = None
    ) -> Dict[str, int]:
        if building_id is None:
            building_id = self.building_id
        if building_id is None:
            return self.get_cutoff_default_values_for_client()

        defaults = DbQueries.get_default_values_for_building(building_id, conn=self.conn)
        return defaults if defaults else self.get_cutoff_default_values_for_client()

    def get_cutoff_default_value_for_item(
        self,
        *,
        source: str = "building",
        client_id: Optional[int] = None,
        building_id: Optional[int] = None,
    ) -> Dict[str, int]:
        verify_source_type(source)
        if source == "building":
            defaults = DbQueries.get_default_values_for_building(building_id, conn=self.conn)
        if source == "client":
            defaults = DbQueries.get_default_values_for_client(client_id, conn=self.conn)
        if source == "epc":
            defaults = DbQueries.get_default_values_for_epc(self.epc_id, conn=self.conn)
            defaults = defaults if defaults else _DEFAULT_CUTOFF_VALUES
        self.logger.debug(f"cutoff default values extracted for {source} - building_id: {building_id}, client_id: {client_id}, epc_id: {self.epc_id}: {defaults}")
        return defaults

    # ------------------------------------------------------------------
    # DataFrame helpers
    # ------------------------------------------------------------------
    def generate_cutoff_month_column_for_tenant(
        self,
        df: pd.DataFrame,
        tenant_id: int,
        source: str = "meter_records",
    ) -> pd.DataFrame:
        verify_source_type(source)
        if df.empty:
            return df

        try:
            self.logger.debug(f"generating cutoff month column for tenant {tenant_id} from {source}")
            if source == "meter_records":
                mapping = self.get_cutoff_datetime_timestamps_for_tenant_from_meter_records(
                    tenant_id=tenant_id,
                    conn=self.conn,
                    logger=self.logger,
                )
                self.logger.debug(f"mapping found for tenant {tenant_id}: {mapping}")
                if self.valid_mapping(mapping) == False:
                    self.logger.debug(f"invalid mapping found for tenant {tenant_id}, falling back to default cutoff values")
                    return self.generate_cutoff_month_column_for_tenant_from_default_values(df, tenant_id, "building")
                return self.generate_cutoff_month_column_for_tenant_from_meter_records(df, tenant_id, mapping)
        except Exception as e:
            self.logger.error(f"❌ Error generating cutoff month column for tenant {tenant_id}: {e}")
            raise ValueError(f"Error generating cutoff month column for tenant {tenant_id}: {e}") from e

    def valid_mapping(self, mapping: Dict[int, Dict[str, List]]) -> bool:
        timestamps = [timestamp for payload in mapping.values() for timestamp in payload.get("timestamps", [])]
        return len(timestamps) > 0


    def generate_cutoff_month_column_for_tenant_from_meter_records(
        self,
        df: pd.DataFrame,
        mapping: Dict[int, Dict[str, List]],
    ) -> pd.DataFrame:

        result_frames: List[pd.DataFrame] = []
        for payload in mapping.values():
            loads = payload.get("loads", [])
            cutoff_points = payload.get("timestamps", [])
            if not loads or not cutoff_points:
                continue
            part_df = df.loc[df["load_id"].isin(loads), :].copy()
            if part_df.empty:
                continue
            tagged = self._apply_cutoff_tags(part_df, cutoff_points)
            result_frames.append(tagged)

        if result_frames:
            df = pd.concat(result_frames)
            return df
        else:
            raise ValueError("No valid cutoff points found for any loads")

    def generate_cutoff_month_column_for_tenant_from_default_values(
        self,
        df: pd.DataFrame,
        tenant_id: int,
        source: str = "building",
    ) -> pd.DataFrame:
        try:
            self.logger.debug(f"generating cutoff month column for tenant {tenant_id} from {source}")
            cutoff_values = self.get_cutoff_default_value_for_item(
                source=source,
                client_id=self.client_id,
                building_id=self.building_id,
            )
            cutoff_points = self.default_cutoff_timestamp_list(cutoff_values)
            return self._apply_cutoff_tags(df, cutoff_points)
        except Exception as e:
            self.logger.error(f"❌ Error generating cutoff month column for tenant {tenant_id}: {e}")
            raise ValueError(f"Error generating cutoff month column for tenant {tenant_id}: {e}")

    @staticmethod
    def extract_last_month(df: pd.DataFrame) -> str:
        if "Year-Month-cut-off" not in df.columns:
            raise ValueError("Year-Month-cut-off column is required")
        valid = df["Year-Month-cut-off"].dropna()
        if valid.empty:
            raise ValueError("Cannot extract last month from empty cutoff column")
        periods = pd.PeriodIndex(valid.astype(str), freq="M")
        last_period = periods.max()
        return str(last_period)


__all__ = ["CutoffManager"]
