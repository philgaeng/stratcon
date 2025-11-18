import sys
from pathlib import Path

import pandas as pd
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.domain.reporting import ReportingOrchestrator
from backend.services.core.utils import ReportLogger


def _fake_analysis_bundle():
    df_daily = pd.DataFrame({
        'tenant_id': [1],
        'Year-Month-cut-off': ['2024-01'],
        'Day': [1],
        'DayOfWeek': [0],
        'Date': ['2024-01-01'],
        'consumption_kWh': [10.0],
    })
    df_hourly = pd.DataFrame({
        'tenant_id': [1],
        'Year-Month-cut-off': ['2024-01'],
        'Day': [1],
        'Hour': [12],
        'DayOfWeek': [0],
        'Date': ['2024-01-01'],
        'consumption_kWh': [5.0],
    })
    df_monthly = pd.DataFrame({
        'tenant_id': [1],
        'Year-Month-cut-off': ['2024-01'],
        'consumption_kWh': [300.0],
    })
    df_avg_hourly = pd.DataFrame({'consumption_kWh': [5.0]}, index=[12])
    df_avg_daily = pd.DataFrame({'consumption_kWh': [10.0]}, index=['M'])
    df_power = pd.DataFrame({
        'tenant_id': [1],
        'Year-Month-cut-off': ['2024-01'],
        'peak power': [15.0],
        'always on power': [3.0],
    })

    return {
        'df': pd.DataFrame(),
        'tenant_ids': [1],
        'label': 'Tenant 1',
        'df_daily': df_daily,
        'df_hourly': df_hourly,
        'df_monthly': df_monthly,
        'df_night': df_hourly.copy(),
        'df_day': df_hourly.copy(),
        'df_weekdays': df_daily.copy(),
        'df_weekends': df_daily.copy(),
        'df_avg_hourly_consumption': df_avg_hourly,
        'df_avg_daily_consumption': df_avg_daily,
        'df_power_analysis': df_power,
        'date_range': 'January 01, 2024 - January 31, 2024',
        'last_month': '2024-01',
        'kpis': {
            'last_month_energy_consumption': 300.0,
            'average_monthly_consumption_energy': 250.0,
            'last_month_co2_emissions': 300.0 * 0.9,
            'selected_load_sqm_area': 100.0,
            'selected_load_energy_per_sqm': 3.0,
            'selected_load_yearly_average_energy_per_sqm': 2.5,
            'consumption_per_sqm_last': 3.0,
            'consumption_per_sqm_yearly': 2.8,
            'percentile_position': 40.0,
        },
        'power_metrics': {
            'last_month_peak_power': 15.0,
            'last_month_always_on_power': 3.0,
            'yearly_average_peak_power': 12.0,
            'yearly_average_always_on_power': 2.5,
        },
        'time_consumption': {
            'last_month_weekday_consumption': 120.0,
            'yearly_average_weekday_consumption': 100.0,
            'last_month_weekend_consumption': 80.0,
            'yearly_average_weekend_consumption': 70.0,
            'last_month_daytime_consumption': 180.0,
            'yearly_average_daytime_consumption': 160.0,
            'last_month_nighttime_consumption': 60.0,
            'yearly_average_nighttime_consumption': 50.0,
        },
    }


def test_reporting_orchestrator_generate_onepager(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.services.domain.data_preparation.cutoff_manager.CutoffManager.get_cutoff_default_values_for_client",
        lambda self: {},
    )

    logger = ReportLogger()
    orchestrator = ReportingOrchestrator(client_id=1, logger=logger)

    dummy_df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=3, freq='h'),
        'load_id': [1, 1, 1],
        'load_kW': [5.0, 7.0, 6.0],
        'tenant_id': [1, 1, 1],
    }).set_index('timestamp')

    monkeypatch.setattr(
        orchestrator.data_prep,
        "load_and_prepare_data_for_tenant",
        lambda *args, **kwargs: dummy_df,
    )

    analysis_bundle = _fake_analysis_bundle()
    monkeypatch.setattr(
        orchestrator.analysis,
        "computations_for_one_pager",
        lambda *args, **kwargs: analysis_bundle,
    )

    result = orchestrator.generate_onepager_report(tenant_id=1)
    assert "analysis" in result
    assert "charts" in result
    assert "html" in result
    assert "<html" in result["html"]
