#!/usr/bin/env python3
"""Unit tests for the new electricity analysis computations."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.electricity_analysis.computations import Computations
from backend.services.db_manager import DbQueries
from backend.services.utils import ReportLogger


def _build_power_dataframe() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=14, freq="12H")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "load_id": [1] * len(timestamps),
            "tenant_id": [1] * len(timestamps),
            "power_kW": [5.0 + i for i in range(len(timestamps))],
        }
    )


def test_compute_energy_adds_consumption_column():
    computations = Computations(client_id=1, logger=ReportLogger())
    df = _build_power_dataframe()

    result = computations.compute_energy(df)

    assert "consumption_kWh" in result.columns
    assert result["consumption_kWh"].sum() > 0


def test_prepare_aggregated_tables_returns_expected_structures():
    computations = Computations(client_id=1, logger=ReportLogger())
    df = _build_power_dataframe()
    df = computations.compute_energy(df)

    # add derived columns required by aggregation helpers
    df["Date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d")
    df["Month"] = pd.to_datetime(df["timestamp"]).dt.month
    df["Year"] = pd.to_datetime(df["timestamp"]).dt.year
    df["Hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    df["Day"] = pd.to_datetime(df["timestamp"]).dt.day
    df["DayOfWeek"] = pd.to_datetime(df["timestamp"]).dt.dayofweek
    df["Year-Month-cut-off"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m")

    (
        df_daily,
        df_hourly,
        df_monthly,
        df_night,
        df_day,
        df_weekdays,
        df_weekends,
        df_avg_hourly,
        df_avg_daily,
    ) = computations.prepare_aggregated_tables(df)

    assert not df_daily.empty
    assert not df_hourly.empty
    assert not df_monthly.empty
    assert set(df_monthly.columns) >= {"Year-Month-cut-off", "consumption_kWh"}
    assert set(df_avg_hourly.columns) == {"consumption_kWh"}
    assert set(df_avg_daily.columns) == {"consumption_kWh"}


def test_compute_kpis_uses_tenant_sqm(monkeypatch):
    computations = Computations(client_id=1, logger=ReportLogger())
    df_monthly = pd.DataFrame(
        {
            "tenant_id": [1, 1],
            "Year-Month-cut-off": ["2024-01", "2024-02"],
            "consumption_kWh": [300.0, 200.0],
        }
    )

    monkeypatch.setattr(
        DbQueries,
        "get_tenant_sqm_data",
        lambda tenant_ids, conn=None: {1: 100.0},
    )

    kpis = computations.compute_kpis(df_monthly, last_month="2024-02", tenant_id=1)

    assert kpis["last_month_energy_consumption"] == 200.0
    assert kpis["average_monthly_consumption_energy"] == 250.0
    assert kpis["selected_load_energy_per_sqm"] == pytest.approx(2.0)


def test_compute_time_based_consumption(monkeypatch):
    computations = Computations(client_id=1, logger=ReportLogger())
    base = pd.DataFrame(
        {
            "tenant_id": [1, 1, 1],
            "Year-Month-cut-off": ["2024-02", "2024-02", "2024-01"],
            "consumption_kWh": [120.0, 80.0, 200.0],
        }
    )
    results = computations.compute_time_based_consumption(
        df_weekdays=base,
        df_weekends=base,
        df_day=base,
        df_night=base,
        last_month="2024-02",
        tenant_id=1,
    )

    assert results["last_month_weekday_consumption"] == 200.0
    assert results["yearly_average_weekday_consumption"] == pytest.approx(200.0)
