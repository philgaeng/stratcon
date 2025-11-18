#!/usr/bin/env python3
"""
Helpers to prepare chart HTML snippets for reporting.
"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from backend.services.core.utils import ReportLogger
from backend.services.domain.utils import normalize_month_year
from backend.services.services.visualization import (
    generate_daily_consumption_chart_html,
    generate_monthly_history_chart_html,
    draw_hourly_consumption_chart_html,
    draw_days_consumption_chart_html,
    draw_pie_chart_energy_per_load_chart_html,
)


def generate_charts(
    *,
    df_daily: pd.DataFrame,
    df_monthly: pd.DataFrame,
    df_avg_hourly_consumption: pd.DataFrame,
    df_avg_daily_consumption: pd.DataFrame,
    last_month: str,
    df_energy_per_load: pd.DataFrame,
    logger: Optional[ReportLogger] = None,
) -> Dict[str, str]:
    """
    Generate all chart HTML snippets required for the one-pager report.
    """
    if logger is None:
        logger = ReportLogger()

    # Filter daily data for last month
    # Normalize last_month format to YYYY-MM (with leading zero for month)
    # This ensures consistency with Year-Month-cut-off column format
    normalized_last_month = normalize_month_year(last_month)
    logger.debug(f"🔍 DEBUG generate_charts: Filtering daily data by last_month={last_month} (normalized={normalized_last_month})")
    logger.debug(f"🔍 DEBUG generate_charts: Available Year-Month-cut-off values in df_daily: {df_daily['Year-Month-cut-off'].unique()}")
    last_month_daily_data = pd.DataFrame(
        df_daily[df_daily['Year-Month-cut-off'] == normalized_last_month].copy()
    )
    if 'Date' in last_month_daily_data.columns:
        last_month_daily_data['Date'] = pd.to_datetime(last_month_daily_data['Date'])
        last_month_daily_data.sort_values(by='Date', ascending=True, inplace=True)

    chart_daily = generate_daily_consumption_chart_html(last_month_daily_data, logger)
    chart_monthly = generate_monthly_history_chart_html(df_monthly, logger)
    chart_hourly = draw_hourly_consumption_chart_html(df_avg_hourly_consumption, logger)
    chart_days = draw_days_consumption_chart_html(df_avg_daily_consumption, logger)
    pie_chart_energy_per_load = draw_pie_chart_energy_per_load_chart_html(df_energy_per_load, logger)

    return {
        "daily": chart_daily,
        "monthly": chart_monthly,
        "hourly": chart_hourly,
        "days": chart_days,
        "pie_energy_per_load": pie_chart_energy_per_load,
    }

