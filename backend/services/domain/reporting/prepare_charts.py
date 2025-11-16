#!/usr/bin/env python3
"""
Helpers to prepare chart HTML snippets for reporting.
"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from backend.services.core.utils import ReportLogger
from backend.services.services.visualization import (
    generate_daily_consumption_chart_html,
    generate_monthly_history_chart_html,
    draw_hourly_consumption_chart_html,
    draw_days_consumption_chart_html,
)


def generate_charts(
    *,
    df_daily: pd.DataFrame,
    df_monthly: pd.DataFrame,
    df_avg_hourly_consumption: pd.DataFrame,
    df_avg_daily_consumption: pd.DataFrame,
    last_month: str,
    logger: Optional[ReportLogger] = None,
) -> Dict[str, str]:
    """
    Generate all chart HTML snippets required for the one-pager report.
    """
    if logger is None:
        logger = ReportLogger()

    # Filter daily data for last month
    last_month_daily_data = pd.DataFrame(
        df_daily[df_daily['Year-Month-cut-off'] == last_month].copy()
    )
    if 'Date' in last_month_daily_data.columns:
        last_month_daily_data['Date'] = pd.to_datetime(last_month_daily_data['Date'])
        last_month_daily_data.sort_values(by='Date', ascending=True, inplace=True)

    chart_daily = generate_daily_consumption_chart_html(last_month_daily_data, logger)
    chart_monthly = generate_monthly_history_chart_html(df_monthly, logger)
    chart_hourly = draw_hourly_consumption_chart_html(df_avg_hourly_consumption, logger)
    chart_days = draw_days_consumption_chart_html(df_avg_daily_consumption, logger)

    return {
        "daily": chart_daily,
        "monthly": chart_monthly,
        "hourly": chart_hourly,
        "days": chart_days,
    }

