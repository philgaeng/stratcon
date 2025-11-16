#!/usr/bin/env python3
"""
Computation and analysis functions for electricity data.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.services.core.base import ServiceContext
from backend.services.core.config import (
    CO2_EMISSIONS_PER_KWH,
    DAY_HOURS,
    MAX_CONSECUTIVE_MISSING_TIMESTAMPS,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH,
    NIGHT_HOURS,
    WEEKDAYS,
)
from backend.services.domain.data_preparation.dataframe_preparer import DataFramePreparer
from backend.services.core.utils import ReportLogger, raise_with_context


class Computations(ServiceContext):
    """Core computation helpers reused by reporting."""

    def __init__(
        self,
        *,
        user_id: Optional[int] = None,
        client_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        logger: Optional[ReportLogger] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        super().__init__(
            user_id=user_id,
            client_id=client_id,
            tenant_id=tenant_id,
            logger=logger,
            conn=conn,
        )
        # if self.client_id is None:
        #     raise ValueError("client_id is required to perform electricity computations")


    def compute_energy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute energy consumption from power values for each load in the dataframe.
        """
        try:
            if df.empty:
                return df

            df = df.copy()
            if "timestamp" not in df.columns:
                if df.index.name == "timestamp":
                    df.reset_index(inplace=True)
                else:
                    raise ValueError("Dataframe must contain a 'timestamp' column.")

            if "power_kW" not in df.columns:
                if "load_kW" in df.columns:
                    df["power_kW"] = df["load_kW"]
                elif "meter_kW" in df.columns:
                    df["power_kW"] = df["meter_kW"]
                else:
                    raise ValueError("No power column found (expected 'load_kW' or 'meter_kW').")

            frames: List[pd.DataFrame] = []
            for load_id in df["load_id"].unique():
                df_part = (
                    df.loc[df["load_id"] == load_id]
                    .sort_values(by="timestamp")
                    .copy()
                )
                df_part["interval_dt"] = df_part["timestamp"].diff().dt.total_seconds()
                df_part["interval_dt"] = df_part["interval_dt"].bfill()
                df_part["mean_kW"] = df_part["power_kW"].rolling(window=2).mean().shift(-1)
                df_part["mean_kW"] = df_part["mean_kW"].fillna(df_part["power_kW"])
                df_part["consumption_kWh"] = (df_part["mean_kW"] * df_part["interval_dt"]) / 3600.0
                frames.append(df_part)

            result = pd.concat(frames, ignore_index=True)
            return result.drop(columns=["interval_dt", "mean_kW"])
        except Exception as exc:
            self.logger.error(f"❌ Error while computing energy: {exc}")
            raise ValueError(f"❌ Error while computing energy: {exc}")


    def prepare_aggregated_tables(self,
        df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, 
            pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Prepare aggregated tables for analysis.
        
        Returns:
            Tuple of (df_daily, df_hourly, df_monthly, df_night, df_day, df_weekdays, 
                    df_weekends, df_avg_hourly_consumption, df_avg_daily_consumption)
        """
        try:
            self.logger.debug(f"🔍 DEBUG prepare_aggregated_tables: Starting with df shape={df.shape}")
            self.logger.debug(f"🔍 DEBUG prepare_aggregated_tables: DataFrame columns: {list(df.columns)}")
            
            # Select only date and energy columns (retain tenant context)
            date_columns = ['tenant_id', 'Date', 'Month', 'Year', 'Hour', 'Day', 'DayOfWeek', 'Year-Month-cut-off']
            df_filtered = df[date_columns + ['consumption_kWh']]
            
            # Daily aggregation per tenant
            df_daily = df_filtered.groupby(
                ['tenant_id', 'Year-Month-cut-off', 'Day', 'DayOfWeek', 'Date']
            )['consumption_kWh'].sum().reset_index()
            df_daily['Date'] = pd.to_datetime(df_daily['Date'])
            df_daily.sort_values(by='Date', ascending=True, inplace=True)
            self.logger.debug(f"🔍 DEBUG df_daily: len():: {len(df_daily)} \n {df_daily.head(3)}")
            
            # Hourly aggregation per tenant
            df_hourly = df_filtered.groupby(
                ['tenant_id', 'Year-Month-cut-off', 'Day', 'Hour', 'DayOfWeek', 'Date']
            )['consumption_kWh'].sum().reset_index()
            df_hourly['Date'] = pd.to_datetime(df_hourly['Date'])
            df_hourly.sort_values(by='Date', ascending=True, inplace=True)
            
            # Monthly aggregation per tenant
            df_monthly = df_filtered.groupby(['tenant_id', 'Year-Month-cut-off'])['consumption_kWh'].sum().reset_index()
            self.logger.debug(f"🔍 DEBUG df_monthly: len():: {len(df_monthly)} \n {df_monthly.head(3)}")
            
            self.logger.debug(f"🔍 DEBUG df_daily columns: {list(df_daily.columns)}")
            self.logger.debug(f"🔍 DEBUG df_hourly columns: {list(df_hourly.columns)}")
            self.logger.debug(f"🔍 DEBUG df_monthly columns: {list(df_monthly.columns)}")
            
            # Filter by time periods
            df_night = df_hourly[df_hourly['Hour'].isin(NIGHT_HOURS)]
            df_day = df_hourly[df_hourly['Hour'].isin(DAY_HOURS)]
            df_weekdays = df_daily[df_daily['DayOfWeek'].isin(WEEKDAYS)]
            df_weekends = df_daily[~df_daily['DayOfWeek'].isin(WEEKDAYS)]
            
            # Compute averages
            df_avg_hourly_consumption = self.compute_avg_hourly_consumption(df_hourly, ['consumption_kWh'])
            df_avg_daily_consumption = self.compute_avg_daily_consumption(df_daily, ['consumption_kWh'])
            
            return (df_daily, df_hourly, df_monthly, df_night, df_day, df_weekdays, 
                    df_weekends, df_avg_hourly_consumption, df_avg_daily_consumption)
            
        except Exception as e:
            self.logger.error(f"❌ Error while preparing aggregated tables: {e}")
            raise ValueError(f"❌ Error while preparing aggregated tables: {e}")


    def compute_avg_hourly_consumption(self,
        df_hourly: pd.DataFrame,
        energy_columns: list
    ) -> pd.DataFrame:
        """Compute average hourly consumption for weekdays in last month"""
        try:
            # Segregate by weekdays
            df = df_hourly[df_hourly['DayOfWeek'].isin(WEEKDAYS)]
            # Select only the last month
            df = DataFramePreparer.select_last_month_with_cutoff_day(df)    
            # Compute the average hourly consumption
            df_avg_hourly_consumption = df.groupby(['Hour'])[energy_columns].mean()
            self.logger.debug(f"🔍 DEBUG df_avg_hourly_consumption: len():: {len(df_avg_hourly_consumption)} \n {df_avg_hourly_consumption.head(3)}")
            return df_avg_hourly_consumption
        except Exception as e:
            self.logger.error(f"❌ Error while computing average hourly consumption: {e}")
            raise ValueError(f"❌ Error while computing average hourly consumption: {e}")


    def compute_avg_daily_consumption(self,
        df_daily: pd.DataFrame,
        energy_columns: list
    ) -> pd.DataFrame:
        """Compute average daily consumption for last month"""
        try:
            df = DataFramePreparer.select_last_month_with_cutoff_day(df_daily)
            df_avg_daily_consumption = df.groupby(['DayOfWeek'])[energy_columns].mean()
            # Remap the index to the day of the week when all days are present
            if len(df_avg_daily_consumption.index) == 7:
                df_avg_daily_consumption.index = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
            else:
                df_avg_daily_consumption.index = df_avg_daily_consumption.index.astype(str)
            self.logger.debug(f"🔍 DEBUG df_avg_daily_consumption: len():: {len(df_avg_daily_consumption)} \n {df_avg_daily_consumption.head(3)}")
            return df_avg_daily_consumption
        except Exception as e:
            self.logger.error(f"❌ Error while computing average daily consumption: {e}")
            raise ValueError(f"❌ Error while computing average daily consumption: {e}")


    def compute_energy_per_sqm(self,
        df_monthly: pd.DataFrame,
        tenant_id: int  
    ) -> pd.DataFrame:
        """Compute energy per sqm for each load"""
        try:
            df_result = self.compute_energy_per_sqm_columns(df_monthly, tenant_id)
            df_result = self.compute_percentile_position_for_energy_per_sqm(df_result)
            self.logger.debug(f"🔍 DEBUG df_result: len():: {len(df_result)} \n {df_result.head(3)}")
            return df_result
        except Exception as e:
            self.logger.error(f"❌ Error while computing energy per sqm: {e}")
            raise ValueError(f"❌ Error while computing energy per sqm: {e}")

    def compute_energy_per_sqm_columns(self,
        df_monthly: pd.DataFrame,
        tenant_id: int
    ) -> pd.DataFrame:
        """Compute energy per sqm for each load"""
        try:
            tenant_sqm_data = self.db.get_tenant_sqm_data_for_client(self.client_id, conn=self.conn)
            all_tenant_ids = tenant_sqm_data.keys()

            list_df = []
            for tenant_id in all_tenant_ids:
                df_part = df_monthly
                sqm = tenant_sqm_data.get(tenant_id)
                if df_part.empty or not sqm:
                    continue
                df_part['sqm_area'] = sqm
                df_part['consumption_kWh_per_sqm'] = df_part['consumption_kWh'] / sqm
                list_df.append(df_part)
            if not list_df:
                return pd.DataFrame(columns=df_monthly.columns.tolist() + ['sqm_area', 'consumption_kWh_per_sqm'])

            result_df = pd.concat(list_df)
            self.logger.debug(f'debug df_energy_per_sqm {result_df.head()}')
            return result_df
        except Exception as e:
            self.logger.error(f"❌ Error while computing energy per sqm: {e}")
            raise ValueError(f"❌ Error while computing energy per sqm: {e}")

    def compute_percentile_position_for_energy_per_sqm(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute percentile position for energy per sqm for a specific tenant or load.
        """
        try:
            list_df = []
            for month in df['Year-Month-cut-off'].unique():
                df_month = df[df['Year-Month-cut-off'] == month].sort_values(by='consumption_kWh_per_sqm', ascending=True).reset_index(drop=True)
                df_month['rank'] = df_month.index + 1
                df_month['percentile_position'] = df_month['rank'] / len(df_month) * 100
                list_df.append(df_month)
            if not list_df:
                return pd.DataFrame(columns=df.columns.tolist() + ['rank', 'percentile_position'])

            df_percentile_position = pd.concat(list_df)
            self.logger.debug(f"🔍 DEBUG df_percentile_position: len():: {len(df_percentile_position)} \n {df_percentile_position.head(3)}")
            return df_percentile_position
        except Exception as e:
            self.logger.error(f"❌ Error while computing percentile position for energy per sqm: {e}")
            raise ValueError(f"❌ Error while computing percentile position for energy per sqm: {e}")


    def compute_peak_power_and_always_on_power(
        self,
        df: pd.DataFrame,
        level: str = 'tenant_id'
    ) -> pd.DataFrame:
        """
        Compute peak power and always on power.
        
        Peak power = average of highest 10% of power values
        Always on power = average of lowest 10% of power values
        
        Returns DataFrame with peak and always-on power for each month and load.
        """
        list_df = []
        try:
            if level == 'tenant_id':
                partition_ids = df['tenant_id'].unique()
            elif level == 'load_id':
                partition_ids = df['load_id'].unique()
            else:
                raise ValueError(f"Unsupported level '{level}' for peak power computation")

            for partition_id in partition_ids:
                df_part = df[df[level] == partition_id]
                for month in df_part['Year-Month-cut-off'].unique():
                    df_month = df_part[df_part['Year-Month-cut-off'] == month]
                    df_month = df_month[df_month['power_kW'] > 0].sort_values(by='power_kW', ascending=False).reset_index(drop=True)
                    if df_month.empty:
                        continue
                    slice_size = max(1, int(len(df_month) * 0.1))
                    peak_power = df_month['power_kW'].nlargest(slice_size).mean()
                    always_on_power = df_month['power_kW'].nsmallest(slice_size).mean()
                    result_dict = {
                        level: partition_id,
                        'Year-Month-cut-off': month,
                        'peak power': float(peak_power) if peak_power == peak_power else 0.0,
                        'always on power': float(always_on_power) if always_on_power == always_on_power else 0.0,
                    }
                    list_df.append(result_dict)
            df_power_analysis = pd.DataFrame(list_df)
            return df_power_analysis
        except Exception as e:
            self.logger.error(f"❌ Error while computing peak power and always on power: {e}")
            raise ValueError(f"❌ Error while computing peak power and always on power: {e}")

    def check_data_completeness(self,
        df: pd.DataFrame,
        max_missing_per_hour: float,
        max_missing_per_day: float,
        max_missing_per_month: float,
        strict: bool = False
    ):
        """Check data completeness across different time periods"""
        # Maximum consecutive missing timestamps check
        df['Alarm_consecutive_missing_timestamps'] = df['Missing_timestamps_after_timestamp'] > MAX_CONSECUTIVE_MISSING_TIMESTAMPS
        if len(df[df['Alarm_consecutive_missing_timestamps'] == True]) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(df[df['Alarm_consecutive_missing_timestamps'] == True])} consecutive missing timestamps")
            self.logger.warning(f"   Largest gap: {df['Nb_of_intervals_between_timestamps'].max():.1f} intervals")
            
            if strict:
                self.logger.error(f"⚠️  Warning: Data is not complete to compute energy - consecutive missing timestamps")
                raise ValueError("Data is not complete to compute energy - consecutive missing timestamps")
        
        # Check per hour, day, and month
        self.check_data_completeness_per_hour(df, max_missing_per_hour, strict)
        self.check_data_completeness_per_day(df, max_missing_per_day, strict)
        self.check_data_completeness_per_month(df, max_missing_per_month, strict)


    def check_data_completeness_per_month(
        self,
        df: pd.DataFrame,
        max_missing_per_month: float = MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH,
        strict: bool = False,
    ):
        """Check the data completeness per month"""
        # Group by Year and Month, sum the missing timestamps
        monthly_missing = df.groupby(['Year-Month-cut-off'])['Missing_timestamps_after_timestamp'].sum()
        
        # Check if any month exceeds the threshold
        months_with_too_many_missing = monthly_missing[monthly_missing > max_missing_per_month]
        
        if len(months_with_too_many_missing) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(months_with_too_many_missing)} months with more than {max_missing_per_month} missing timestamps")
            self.logger.warning(f"   Problematic months: {list(months_with_too_many_missing.index)}")
            if strict:
                raise ValueError("Data is not complete to compute energy")
        else:
            self.logger.debug(f"✅ All months are complete: {monthly_missing.index}")


    def check_data_completeness_per_day(
        self,
        df: pd.DataFrame,
        max_missing_per_day: float = MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY,
        strict: bool = False,
    ):
        """Check the data completeness per day"""
        # Group by Year, Month, and Day, sum the missing timestamps
        daily_missing = df.groupby(['Year', 'Month', 'Day'])['Missing_timestamps_after_timestamp'].sum()
        
        # Check if any day exceeds the threshold
        days_with_too_many_missing = daily_missing[daily_missing > max_missing_per_day]
        
        if len(days_with_too_many_missing) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(days_with_too_many_missing)} days with more than {max_missing_per_day} missing timestamps")
            self.logger.warning(f"   Problematic days: {list(days_with_too_many_missing.index)}")
            if strict:
                raise ValueError("Data is not complete to compute energy")
        else:
            self.logger.debug(f"✅ All days are passing the daily threshold: {max_missing_per_day}")


    def check_data_completeness_per_hour(
        self,
        df: pd.DataFrame,
        max_missing_per_hour: float = MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR,
        strict: bool = False,
    ):
        """Check the data completeness per hour"""
        # Group by Year, Month, Day, and Hour, sum the missing timestamps
        hourly_missing = df.groupby(['Year', 'Month', 'Day', 'Hour'])['Missing_timestamps_after_timestamp'].sum()
        
        # Check if any hour exceeds the threshold
        hours_with_too_many_missing = hourly_missing[hourly_missing > max_missing_per_hour  ]
        
        if len(hours_with_too_many_missing) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(hours_with_too_many_missing)} hours with more than {max_missing_per_hour} missing timestamps")
            self.logger.warning(f"   Problematic hours: {list(hours_with_too_many_missing.index)}")
            if strict:
                raise ValueError("Data is not complete to compute energy")
        else:
            self.logger.debug(f"✅ All hours are passing the hourly threshold: {max_missing_per_hour}")


    def analyze_data(self, df: pd.DataFrame):
        """Perform basic data analysis and logging"""
        try:
            self.logger.debug("\n=== DATA ANALYSIS ===")
            self.logger.debug("\nData types:")
            self.logger.debug(str(df.dtypes))
            self.logger.debug("\nMissing values:")
            self.logger.debug(str(df.isnull().sum()))
            self.logger.debug("\nBasic statistics:")
            self.logger.debug(str(df.describe()))
        except Exception as e:
            self.logger.error(f"❌ Error while analyzing data: {e}")
            raise


    def compute_kpis(
        self,
        df_monthly: pd.DataFrame,
        last_month: str,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """
        Compute high-level KPIs for a single tenant.
        """
        if df_monthly.empty:
            return {
                'last_month_energy_consumption': 0.0,
                'average_monthly_consumption_energy': 0.0,
                'last_month_co2_emissions': 0.0,
                'sqm_area': None,
                'consumption_per_sqm_last': None,
                'consumption_per_sqm_yearly': None,
                'percentile_position': None,
            }

        tenant_monthly = df_monthly[df_monthly['tenant_id'] == tenant_id]
        if tenant_monthly.empty:
            raise ValueError(f"No monthly data found for tenant_id={tenant_id}")

        last_month_mask = tenant_monthly['Year-Month-cut-off'] == last_month
        last_month_energy = float(tenant_monthly[last_month_mask]['consumption_kWh'].sum())
        average_monthly_consumption = float(
            tenant_monthly.groupby('Year-Month-cut-off')['consumption_kWh'].sum().mean() or 0.0
        )
        last_month_co2 = last_month_energy * CO2_EMISSIONS_PER_KWH

        sqm_map = self.db.get_tenant_sqm_data_for_client(self.client_id, conn=self.conn)
        tenant_sqm = float(sqm_map.get(tenant_id, 0.0) or 0.0)
        if tenant_sqm > 0:
            energy_per_sqm_last = last_month_energy / tenant_sqm
            energy_per_sqm_yearly = tenant_monthly['consumption_kWh'].sum() / tenant_sqm
        else:
            energy_per_sqm_last = None
            energy_per_sqm_yearly = None
        #TODO: Aggregate the consumption data monthly for all tenants in a specific table for easy retrieval
        # Compute percentile among the provided tenants (if data available)
        # comparison_df = df_monthly[df_monthly['Year-Month-cut-off'] == last_month].copy()
        # comparison_ids = comparison_df['tenant_id'].unique().tolist()
        # comparison_df['sqm'] = comparison_df['tenant_id'].map(sqm_map)
        # comparison_df = comparison_df[comparison_df['sqm'] > 0]
        # comparison_df['per_sqm'] = comparison_df['consumption_kWh'] / comparison_df['sqm']

        percentile_position = .11
        # if not comparison_df.empty and tenant_id in comparison_df['tenant_id'].values:
        #     comparison_df = comparison_df.groupby('tenant_id')['per_sqm'].mean().reset_index()
        #     comparison_df.sort_values('per_sqm', inplace=True)
        #     comparison_df['rank'] = comparison_df['per_sqm'].rank(method='average', pct=True) * 100
        #     percentile_row = comparison_df[comparison_df['tenant_id'] == tenant_id]
        #     if not percentile_row.empty:
        #         percentile_position = float(percentile_row['rank'].iloc[0])

        return {
            'last_month_energy_consumption': last_month_energy,
            'average_monthly_consumption_energy': average_monthly_consumption,
            'last_month_co2_emissions': last_month_co2,
            'sqm_area': tenant_sqm if tenant_sqm > 0 else None,
            'consumption_per_sqm_last': energy_per_sqm_last,
            'consumption_per_sqm_yearly': energy_per_sqm_yearly,
            'percentile_position': percentile_position,
        }
    
    def compute_power_metrics(
        self,
        df_power_analysis: pd.DataFrame,
        last_month: str,
        tenant_id: int,
    ) -> Dict[str, float]:
        """
        Compute power metrics (peak and always-on power) for a single tenant.
        """
        if df_power_analysis.empty:
            return {
                'last_month_peak_power': 0.0,
                'last_month_always_on_power': 0.0,
                'yearly_average_peak_power': 0.0,
                'yearly_average_always_on_power': 0.0,
            }

        subset = df_power_analysis[df_power_analysis['tenant_id'] == tenant_id]
        if subset.empty:
            raise ValueError(f"No power analysis data for tenant_id={tenant_id}")

        peak_col = 'peak power'
        always_col = 'always on power'

        last_month_subset = subset[subset['Year-Month-cut-off'] == last_month]
        last_month_peak = float(last_month_subset[peak_col].mean()) if not last_month_subset.empty else 0.0
        last_month_always = float(last_month_subset[always_col].mean()) if not last_month_subset.empty else 0.0
        yearly_avg_peak = float(subset[peak_col].mean())
        yearly_avg_always = float(subset[always_col].mean())

        return {
            'last_month_peak_power': last_month_peak,
            'last_month_always_on_power': last_month_always,
            'yearly_average_peak_power': yearly_avg_peak,
            'yearly_average_always_on_power': yearly_avg_always,
        }
    
    def compute_time_based_consumption(
        self,
        df_weekdays: pd.DataFrame,
        df_weekends: pd.DataFrame,
        df_day: pd.DataFrame,
        df_night: pd.DataFrame,
        last_month: str,
        tenant_id: int,
    ) -> Dict[str, float]:
        """
        Compute time-based consumption metrics including weekday/weekend and daytime/nighttime.
        """
        def _calc(df: pd.DataFrame) -> pd.DataFrame:
            return df[df['tenant_id'] == tenant_id] if 'tenant_id' in df.columns else df

        weekdays_subset = _calc(df_weekdays)
        weekends_subset = _calc(df_weekends)
        day_subset = _calc(df_day)
        night_subset = _calc(df_night)

        def _last_month_sum(frame: pd.DataFrame) -> float:
            if frame.empty:
                return 0.0
            rows = frame[frame['Year-Month-cut-off'] == last_month]
            return float(rows['consumption_kWh'].sum()) if not rows.empty else 0.0

        def _yearly_average(frame: pd.DataFrame) -> float:
            if frame.empty:
                return 0.0
            grouped = frame.groupby('Year-Month-cut-off')['consumption_kWh'].sum()
            return float(grouped.mean()) if not grouped.empty else 0.0

        return {
            'last_month_weekday_consumption': _last_month_sum(weekdays_subset),
            'yearly_average_weekday_consumption': _yearly_average(weekdays_subset),
            'last_month_weekend_consumption': _last_month_sum(weekends_subset),
            'yearly_average_weekend_consumption': _yearly_average(weekends_subset),
            'last_month_daytime_consumption': _last_month_sum(day_subset),
            'yearly_average_daytime_consumption': _yearly_average(day_subset),
            'last_month_nighttime_consumption': _last_month_sum(night_subset),
            'yearly_average_nighttime_consumption': _yearly_average(night_subset),
        }