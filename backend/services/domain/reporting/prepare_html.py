#!/usr/bin/env python3
"""
Helpers for building HTML output for reporting.
"""

from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Any, Dict, Optional

from backend.services.core.config import (
    ReportStyle,
    PlotlyStyle,
    DEFAULT_RESOURCES_DIR,
)
from backend.services.core.utils import ReportLogger


def generate_html_styles() -> str:
    """Generate shared CSS variables for legacy reports."""
    return f"""
    <link href="https://fonts.googleapis.com/css?family=Montserrat:700,600,400&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Inter:400,600,700&display=swap" rel="stylesheet">
    <style>
    :root {{
    --consumption-color: {ReportStyle.CONSUMPTION_COLOR};
    --production-color: {ReportStyle.PRODUCTION_COLOR};
    --import-color: {ReportStyle.IMPORT_COLOR};
    --export-color: {ReportStyle.EXPORT_COLOR};

    --heading-font: {ReportStyle.HEADING_FONT_FAMILY};
    --body-font: {ReportStyle.BODY_FONT_FAMILY};

    --h1-size: {ReportStyle.H1_FONT_SIZE}px;
    --h2-size: {ReportStyle.H2_FONT_SIZE}px;
    --h3-size: {ReportStyle.H3_FONT_SIZE}px;
    --body-size: {ReportStyle.FONT_SIZE}px;
    }}

    h1, .h1 {{ font-family: var(--heading-font); font-size: var(--h1-size); font-weight: bold; color: #333; }}
    h2, .h2 {{ font-family: var(--heading-font); font-size: var(--h2-size); font-weight: bold; color: #333; }}
    h3, .h3 {{ font-family: var(--body-font); font-size: var(--h3-size); font-weight: bold; color: #333; }}

    body, .body-text {{ font-family: var(--body-font); font-size: var(--body-size); color: #333; }}
    .consumption {{ color: var(--consumption-color); }}
    .production  {{ color: var(--production-color); }}
    .import      {{ color: var(--import-color); }}
    .export      {{ color: var(--export-color); }}
    </style>
    """


def generate_html_separator(level: str) -> str:
    """Generate a separator for the HTML report."""
    return f"""
    <div class="separator {level}">
        <h2>========================================</h2>
        <h2>=========={level.capitalize()}==========</h2>
        <h2>========================================</h2>
    </div>
    """


def get_base64_logo(
    logo_type: str = "white",
    logger: Optional[ReportLogger] = None,
) -> Optional[str]:
    """
    Return a data-URI encoded logo that works in Safari and evergreen browsers.
    """
    if logger is None:
        logger = ReportLogger()

    logo_files = {
        "white": "Stratcon.ph White.png",
        "black": "Stratcon.ph Black.png",
        "full_color": "Stratcon.ph Full Color3.png",
        "brandmark": "Stratcon Brandmark.png",
    }
    logo_filename = logo_files.get(logo_type, logo_files["white"])
    logo_path = os.path.join(DEFAULT_RESOURCES_DIR, logo_filename)

    if not os.path.exists(logo_path):
        logger.warning(f"⚠️ Logo file not found at: {logo_path}")
        return None

    try:
        with open(logo_path, "rb") as handle:
            logo_data = handle.read()
    except Exception as exc:  # pragma: no cover
        logger.error(f"❌ Error reading logo file {logo_path}: {exc}")
        return None

    if not logo_data:
        logger.warning("⚠️ Logo file was empty; skipping logo embedding.")
        return None

    try:
        base64_logo = base64.b64encode(logo_data).decode("ascii")
    except Exception as exc:  # pragma: no cover - extremely unlikely
        logger.error(f"❌ Failed to base64-encode logo data: {exc}")
        return None

    # Safari prefers the short form data URI without charset.
    return f"data:image/png;base64,{base64_logo}"


def build_logo_img(logo_url: str, *, max_font_px: int = 32) -> str:
    """Return an <img> tag for the Stratcon logo constrained to the text size."""
    if not logo_url:
        return ""
    return (
        f'<img src="{logo_url}" alt="Stratcon Logo" '
        f'class="stratcon-logo" style="max-height:{max_font_px}px; width:auto;" />'
    )


def generate_onepager_styles() -> str:
    """Generate the modern CSS styles for the one-pager report."""
    main_title_size = ReportStyle.H1_FONT_SIZE
    subtitle_label_size = ReportStyle.H3_FONT_SIZE
    subtitle_value_size = ReportStyle.H1_FONT_SIZE
    logo_max_height = ReportStyle.H1_FONT_SIZE
    body_font = ReportStyle.BODY_FONT_FAMILY
    header_font = ReportStyle.HEADING_FONT_FAMILY
    return f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: '{body_font}', sans-serif; line-height: 1.6; color: #333;
                background: linear-gradient(135deg, {PlotlyStyle.STRATCON_LIGHT_GREEN} 0%, {PlotlyStyle.STRATCON_PRIMARY_GREEN} 50%, {PlotlyStyle.STRATCON_YELLOW} 100%);
                min-height: 100vh; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white;
                     box-shadow: 0 20px 40px rgba(0,0,0,0.1); min-height: 100vh; }}
        .header {{ background: {PlotlyStyle.STRATCON_DARK_GREEN}; color: white; padding: 2rem;
                   display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; }}
        .logo-section {{ display: flex; align-items: center; gap: 1rem; }}
        .main-title {{ font-size: {main_title_size}px; font-family: '{header_font}', sans-serif; font-weight: 700; margin-bottom: 0.5rem; }}
        .subtitle-label {{ font-size: {subtitle_label_size}px; font-family: '{header_font}', sans-serif; font-weight: 600; margin-right: 0.5rem; }}
        .subtitle-value {{ font-size: {subtitle_value_size}px; font-family: '{header_font}', sans-serif; font-weight: 700; }}
        .stratcon-logo {{ max-height: {logo_max_height}px; width: auto; }}
        .section-title {{ font-size: 1.8rem; font-weight: 600; color: {PlotlyStyle.STRATCON_DARK_GREY};
                         margin-bottom: 1.5rem; border-bottom: 3px solid {PlotlyStyle.STRATCON_PRIMARY_GREEN}; padding-bottom: 0.5rem; }}
        .metrics-section {{ padding: 0.5rem; }}
        .chart-section {{ padding: 0.5rem; }}
        .metric-card {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 4px solid {PlotlyStyle.STRATCON_PRIMARY_GREEN}; }}
        .metric-card-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
        .metric-card-row .metric-card {{ margin: 0; }}
        .metric-value {{ font-size: 2.5rem; font-weight: 700; color: {PlotlyStyle.STRATCON_DARK_GREY}; margin-bottom: 0.25rem; }}
        .chart-container {{ background: white; padding: 1.5rem; border-radius: 8px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .metrics-two-columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem; }}
        .metrics-column {{ display: flex; flex-direction: column; gap: 1rem; }}
        .three-column-layout {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2rem; margin-bottom: 2rem; }}
        .one-thirds-two-thirds-layout {{ display: grid; grid-template-columns: 1fr 2fr; gap: 2rem; margin-bottom: 2rem; }}
        .metrics-three-columns {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2rem; margin-bottom: 2rem; }}
        .footer {{ background: {PlotlyStyle.STRATCON_DARK_GREEN}; color: white; padding: 1.5rem 2rem; text-align: center; }}
    </style>
    """


def _safe_format(value: Any, format_str: str = ".1f", default: str = "N/A") -> str:
    """Safely format a value, handling None and other edge cases."""
    if value is None:
        return default
    try:
        return format(value, format_str)
    except (ValueError, TypeError):
        return default


def generate_onepager_html(
    *,
    tenant_name: str,
    values_for_html: Dict[str, Any],
    charts: Dict[str, str],
    logger: Optional[ReportLogger] = None,
) -> str:
    """
    Build the final HTML string for the one-pager report.
    """
    if logger is None:
        logger = ReportLogger()

    chart_daily = charts.get("daily", "")
    chart_monthly = charts.get("monthly", "")
    chart_hourly = charts.get("hourly", "")
    chart_days = charts.get("days", "")
    chart_pie_energy_per_load = charts.get("pie_energy_per_load", "")

    logo_url = get_base64_logo("white", logger) or ""
    logo_tag = build_logo_img(logo_url)
    
    # Safely format values that might be None
    consumption_per_sqm_last = _safe_format(values_for_html.get('consumption_per_sqm_last'), ".1f", "N/A")
    consumption_per_sqm_yearly = _safe_format(values_for_html.get('consumption_per_sqm_yearly'), ".1f", "N/A")
    percentile_position = _safe_format(values_for_html.get('percentile_position'), ".1f", "N/A")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{tenant_name} - Energy Analysis Report</title>
        {generate_onepager_styles()}
    </head>
    <body>
        <div class="container">
            <header class="header">
                <div class="logo-section">
                    <h1 class="main-title"><span class="subtitle-label">Tenant:</span><span class="subtitle-value"> {tenant_name}</span></h1>
                </div>
                <div class="report-info">
                    <div class="logo-container">
                        {logo_tag}
                    </div>
                    <p class="date-range">Billing Period: {values_for_html['date_range']}</p>
                    <p class="generated-date">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
            </header>

            <section class="metrics-section">
                <h2 class="section-title">Energy Analysis Report</h2>
                <div class="metrics-two-columns">
                    <div class="metrics-column">
                        <div class="metric-card main-metric">
                            <div class="metric-label">Energy Consumption (kWh)</div>
                            <div class="metric-value">{values_for_html['last_month_energy_consumption']:,.0f}</div>
                            <div class="metric-reference">(Yearly average: {values_for_html['average_monthly_consumption_energy']:,.0f} kWh)</div>
                        </div>
                        <div class="metric-card-row">
                            <div class="metric-card">
                                <div class="metric-label">Peak Power (kW)</div>
                                <div class="metric-value">{values_for_html['last_month_peak_power']:.1f}</div>
                                <div class="metric-reference">(Yearly average: {values_for_html['yearly_average_peak_power']:.1f} kW)</div>
                            </div><div class="metric-card">
                                <div class="metric-label">Always On (kW)</div>
                                <div class="metric-value">{values_for_html['last_month_always_on_power']:.1f}</div>
                                <div class="metric-reference">(Yearly average: {values_for_html['yearly_average_always_on_power']:.1f} kW)</div>
                            </div>
                        </div>
                        <div class="metric-card-row">
                            <div class="metric-card">
                                <div class="metric-label">Energy intensity (kWh/m²)</div>
                                <div class="metric-value">{consumption_per_sqm_last}</div>
                                <div class="metric-reference">(Percentile position: {percentile_position}%)</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">CO₂ Emissions (kg)</div>
                                <div class="metric-value">{values_for_html['last_month_co2_emissions']:,.0f}</div>
                            </div>
                        </div>
                    </div>
                    <div class="metrics-column">
                        <h3 class="subsection-title">Energy per Load</h3>
                        <div class="chart-container">{chart_pie_energy_per_load}</div>
                    </div>
                </div>
            </section>

            <section class="chart-section">
                <div class="one-thirds-two-thirds-layout">
                    <div class="column-one-third-1-2">
                        <h3 class="subsection-title">Monthly Consumption Chart</h3>
                        <div class="chart-container">{chart_monthly}</div>
                    </div>
                    <div class="column-two-thirds-1-2">
                        <h3 class="subsection-title">Daily Consumption Chart</h3>
                        <div class="chart-container">{chart_daily}</div>
                    </div>
                </div>
            </section>

            <section class="chart-section">
                <div class="three-column-layout">
                    <div class="column-left">
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">Weekday / Weekend Consumption</div>
                                <div class="metric-value">{values_for_html['last_month_weekday_consumption']:,.0f} / {values_for_html['last_month_weekend_consumption']:,.0f}</div>
                                <div class="metric-reference">(Yearly average: {values_for_html['yearly_average_weekday_consumption']:,.0f} / {values_for_html['yearly_average_weekend_consumption']:,.0f} kWh)</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Daytime / Nighttime Consumption (kWh)</div>
                                <div class="metric-value">{values_for_html['last_month_daytime_consumption']:,.0f} / {values_for_html['last_month_nighttime_consumption']:,.0f}</div>
                                <div class="metric-reference">(Yearly average: {values_for_html['yearly_average_daytime_consumption']:,.0f} / {values_for_html['yearly_average_nighttime_consumption']:,.0f} kWh)</div>
                            </div>
                        </div>
                    </div>
                    <div class="column-center">
                        <h3 class="subsection-title">Days of the Week Analysis</h3>
                        <div class="chart-container">{chart_days}</div>
                    </div>
                    <div class="column-right">
                        <h3 class="subsection-title">Hourly Analysis</h3>
                        <div class="chart-container">{chart_hourly}</div>
                    </div>
                </div>
            </section>

            <footer class="footer">
                <div class="footer-content">
                    <p>This report was generated by Stratcon Energy Analytics Platform</p>
                    <p>For questions or support, contact: support@stratcon.com</p>
                </div>
            </footer>
        </div>
    </body>
    </html>
    """

