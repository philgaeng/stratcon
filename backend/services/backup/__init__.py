#!/usr/bin/env python3
"""
Electricity Analysis Service

A modular service for electricity consumption analysis and report generation.
"""

from .config import *
from .utils import ReportLogger
from .data_preparation import (
    load_and_prepare_data,
    select_loads,
    generate_cutoff_month_column,
    init_interval_and_alarm_levels,
    select_full_months,
    compute_monthly_date_range,
)
from .computations import (
    compute_energy,
    prepare_aggregated_tables,
    compute_peak_power_and_always_on_power,
    compute_energy_per_sqm_values_and_percentile_position,
    check_data_completeness,
)
from .visualization import (
    draw_energy_kWh_per_month,
    draw_energy_kWh_per_day,
    generate_daily_consumption_chart_html,
    generate_monthly_history_chart_html,
    draw_hourly_consumption_chart_html,
    draw_days_consumption_chart_html,
)
from ..reporting import ReportingOrchestrator
from ..reporting.prepare_html import generate_onepager_html
from ..reporting.prepare_charts import generate_charts
from ..reporting import generate_report_for_tenant

__all__ = [
    # Config
    'MAX_MISSING_DAYS_PER_MONTH',
    'MAX_CONSECUTIVE_MISSING_TIMESTAMPS',
    'WEEKDAYS',
    'NIGHT_HOURS',
    'DAY_HOURS',
    'CO2_EMISSIONS_PER_KWH',
    'ReportStyle',
    'PlotlyStyle',
    
    # Utils
    'ReportLogger',
    
    # Data Preparation
    'load_and_prepare_data',
    'select_loads',
    'generate_cutoff_month_column',
    'init_interval_and_alarm_levels',
    'select_full_months',
    'compute_monthly_date_range',
    
    # Computations
    'compute_energy',
    'prepare_aggregated_tables',
    'compute_peak_power_and_always_on_power',
    'compute_energy_per_sqm_values_and_percentile_position',
    'check_data_completeness',
    
    # Visualization
    'draw_energy_kWh_per_month',
    'draw_energy_kWh_per_day',
    'generate_daily_consumption_chart_html',
    'generate_monthly_history_chart_html',
    'draw_hourly_consumption_chart_html',
    'draw_days_consumption_chart_html',
    
    # Reporting
    'ReportingOrchestrator',
    'generate_report_for_tenant',
    'generate_charts',
    'generate_onepager_html',
]
