#!/usr/bin/env python3
"""
Visualization functions for generating charts
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from typing import Optional, Union, List
from .config import PlotlyStyle
from .utils import ReportLogger


def add_yaxis_title_annotation(title: str = "kWh"):
    """Helper function to add y-axis title annotation at the top"""
    return [
        dict(
            text=title,
            x=0,
            y=1.02,
            xref="paper",
            yref="paper",
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            font=dict(size=12)
        )
    ]


def configure_standard_chart_layout(fig, yaxis_title: str = "kWh", height: int = 320, show_legend: bool = False):
    """Helper function to apply standard chart configuration"""
    fig.update_yaxes(tickformat=",.0f")
    fig.update_layout(
        height=height,
        showlegend=show_legend,
        template="plotly_white",
        margin=dict(l=25, r=25, t=30, b=30),
        annotations=add_yaxis_title_annotation(yaxis_title),
        font=dict(size=12),
        title_font=dict(size=16)
    )
    fig.update_xaxes(type='category')
    return fig


def draw_energy_kWh_per_month(
    month_data: pd.DataFrame,
    loads_list: list,
    logger: Optional[ReportLogger] = None
) -> Union[List[go.Figure], go.Figure]:
    """
    Draw bar charts of energy consumption per month.
    
    Args:
        month_data: DataFrame with monthly energy data and 'Year-Month-cut-off' column
        loads_list: List of load names
        logger: Optional logger instance
        
    Returns:
        List of figures (one per load) or single figure for production case
    """
    if logger is None:
        logger = ReportLogger()
    
    try:
        logger.info("\n=== DRAWING ENERGY PER MONTH ===")
        logger.debug(str(month_data))
        
        # Check if we have both consumption and production data
        has_consumption = any("Consumption" in load for load in loads_list)
        has_production = any("Production" in load for load in loads_list)
        
        if has_consumption and has_production:
            return draw_energy_kWh_per_month_production(month_data, logger)
        else:
            # Reset index to make it a regular DataFrame
            month_data_reset = month_data.reset_index()
            logger.debug(f"month_data_reset columns: {month_data_reset.columns}")
            
            # Create a new plot for each load
            columns = []
            for col in month_data.columns:
                for load in loads_list:
                    if load in col:
                        columns.append((load, col))
            
            logger.debug(f"load columns: {columns}")
            figures = []
            
            for load, col in columns:
                # Create individual figure for each load
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=month_data_reset['Year-Month-cut-off'],
                        y=month_data_reset[col],
                        name=load,
                        marker_color=PlotlyStyle.STRATCON_DARK_GREEN,
                        text=[f"{val:,.0f}" for val in month_data_reset[col]],
                        textposition='outside'
                    )
                )
                
                # Apply standard chart configuration
                fig = configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
                
                figures.append(fig)
                logger.debug(f"✅ Energy per month plot generated for {load}")
            
            logger.debug(f"✅ All {len(figures)} energy per month plots generated")
            return figures
            
    except Exception as e:
        logger.error(f"❌ Error while drawing energy per month: {e}")
        raise ValueError(f"❌ Error while drawing energy per month: {e}")


def draw_energy_kWh_per_month_production(
    month_data: pd.DataFrame,
    logger: Optional[ReportLogger] = None
) -> go.Figure:
    """Draw bar charts for production/consumption case"""
    if logger is None:
        logger = ReportLogger()
    
    try:
        logger.info("\n=== DRAWING ENERGY PER MONTH (PRODUCTION) ===")
        logger.debug(str(month_data))
        
        # Reset index
        month_data_reset = month_data.reset_index()
        
        # Create Year-Month column
        month_data_reset['Year-Month'] = (
            month_data_reset['Year'].astype(str) + '-' + 
            month_data_reset['Month'].astype(str).str.zfill(2)
        )
        month_data_reset['Label'] = pd.to_datetime(month_data_reset['Year-Month']).dt.strftime('%b %Y')
        
        # Create two subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Energy Consumption vs Production per Month - kWh',
                'Energy Import vs Export per Month - kWh'
            ),
            vertical_spacing=0.15
        )
        
        # Consumption vs Production
        fig.add_trace(
            go.Bar(
                x=month_data_reset['Label'],
                y=month_data_reset['Energy_consumption_per_interval [kWh]'],
                name='Consumption',
                marker_color=PlotlyStyle.CONSUMPTION_COLOR
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(
                x=month_data_reset['Label'],
                y=month_data_reset['Energy_production_per_interval [kWh]'],
                name='Production',
                marker_color=PlotlyStyle.PRODUCTION_COLOR
            ),
            row=1, col=1
        )
        
        # Import vs Export
        fig.add_trace(
            go.Bar(
                x=month_data_reset['Label'],
                y=-month_data_reset['Energy_import_per_interval [kWh]'],
                name='Import (negative)',
                marker_color=PlotlyStyle.IMPORT_COLOR
            ),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(
                x=month_data_reset['Label'],
                y=month_data_reset['Energy_export_per_interval [kWh]'],
                name='Export',
                marker_color=PlotlyStyle.EXPORT_COLOR
            ),
            row=2, col=1
        )
        
        fig.update_yaxes(tickformat=",.0f")
        fig.update_layout(
            title='Energy Analysis per Month',
            height=800,
            showlegend=True,
            font=PlotlyStyle.update_font,
            title_font=PlotlyStyle.update_title_font
        )
        fig.update_xaxes(type='category')
        
        logger.debug(f"✅ Energy per month plot generated (production)")
        return fig
        
    except Exception as e:
        logger.error(f"❌ Error while drawing energy per month: {e}")
        raise ValueError(f"❌ Error while drawing energy per month: {e}")


def draw_energy_kWh_per_day(
    day_data: pd.DataFrame,
    loads: list,
    logger: Optional[ReportLogger] = None
) -> Union[List[go.Figure], go.Figure]:
    """Draw bar charts of energy consumption per day"""
    if logger is None:
        logger = ReportLogger()
    
    try:
        logger.info("\n=== DRAWING ENERGY PER DAY ===")
        logger.debug(str(day_data))
        
        # Check for production data
        has_consumption = any("Consumption" in load for load in loads)
        has_production = any("Production" in load for load in loads)
        
        if has_consumption and has_production:
            return draw_energy_kWh_per_day_production(day_data, logger)
        else:
            # Reset index
            day_data_reset = day_data.reset_index()
            
            # Create Date column
            day_data_reset['Date'] = (
                day_data_reset['Year'].astype(str) + '-' +
                day_data_reset['Month'].astype(str).str.zfill(2) + '-' +
                day_data_reset['Day'].astype(str).str.zfill(2)
            )
            
            # Find columns for each load
            columns = []
            for col in day_data.columns:
                for load in loads:
                    if load in col:
                        columns.append(col)
            
            figures = []
            for col in columns:
                # Extract load name
                load = col.replace('Energy_consumption_', '').replace('_per_interval [kWh]', '')
                
                # Create figure
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=day_data_reset['Date'],
                        y=day_data_reset[col],
                        name=load,
                        marker_color=PlotlyStyle.CONSUMPTION_COLOR
                    )
                )
                
                fig.update_yaxes(tickformat=",.0f")
                fig.update_layout(
                    height=320,
                    showlegend=True,
                    font=PlotlyStyle.update_font,
                    title_font=PlotlyStyle.update_title_font,
                    margin=dict(l=25, r=25, t=80, b=50),
                    annotations=add_yaxis_title_annotation("kWh")
                )
                fig.update_xaxes(type='category')
                
                figures.append(fig)
                logger.debug(f"✅ Energy per day plot generated for {load}")
            
            logger.debug(f"✅ All {len(figures)} energy per day plots generated")
            return figures
            
    except Exception as e:
        logger.error(f"❌ Error while drawing energy per day: {e}")
        raise ValueError(f"❌ Error while drawing energy per day: {e}")


def draw_energy_kWh_per_day_production(
    day_data: pd.DataFrame,
    logger: Optional[ReportLogger] = None
) -> go.Figure:
    """Draw bar charts for production/consumption per day (placeholder)"""
    if logger is None:
        logger = ReportLogger()
    
    logger.info("\n=== DRAWING ENERGY PER DAY (PRODUCTION) ===")
    logger.debug(str(day_data))
    # TODO: Implement production daily chart
    return None


def generate_daily_consumption_chart_html(
    daily_data: pd.DataFrame,
    logger: Optional[ReportLogger] = None
) -> str:
    """Generate daily consumption chart HTML for the last month"""
    if logger is None:
        logger = ReportLogger()
    
    try:
        if daily_data.empty:
            return "<p>No data available for daily consumption chart.</p>"
        
        daily_consumption = daily_data["consumption_kWh"]
        
        # Format date labels
        if 'Date' in daily_data.columns:
            date_labels = []
            for date_val in daily_data['Date']:
                try:
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime('%a-%m-%d')
                    else:
                        date_obj = pd.to_datetime(date_val)
                        date_str = date_obj.strftime('%a-%m-%d')
                    date_labels.append(date_str)
                except Exception as e:
                    logger.warning(f"Could not format date {date_val}: {e}")
                    date_labels.append(str(date_val))
            
            # Sort by date
            if len(date_labels) > 1:
                temp_df = daily_data.copy()
                temp_df['date_labels'] = date_labels
                temp_df = temp_df.sort_values('Date')
                date_labels = temp_df['date_labels'].tolist()
                daily_consumption = temp_df["consumption_kWh"]
        elif hasattr(daily_consumption.index, 'strftime'):
            date_labels = [date.strftime('%a-%m-%d') for date in daily_consumption.index]
        else:
            date_labels = [f"Day-{i+1:02d}" for i in range(len(daily_consumption))]
            logger.warning("No Date column found, using fallback day labels")
        
        logger.debug(f"Date labels: {date_labels}")
        
        # Create chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=date_labels,
            y=daily_consumption.values,
            name=f'Daily Consumption - kWh',
            marker_color=PlotlyStyle.STRATCON_PRIMARY_GREEN,
            text=[f"{val:,.0f}" for val in daily_consumption.values],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Energy: %{y:,.0f} kWh<extra></extra>'
        ))
        
        fig = configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
        
        fig.update_xaxes(
            tickangle=45,
            type='category',
            tickmode='array',
            tickvals=date_labels,
            ticktext=date_labels
        )
        
        return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        
    except Exception as e:
        logger.error(f"❌ Error generating daily consumption chart: {e}")
        return "<p>Error generating daily consumption chart.</p>"


def generate_monthly_history_chart_html(
    monthly_data: pd.DataFrame,
    logger: Optional[ReportLogger] = None
) -> str:
    """Generate monthly history chart HTML"""
    if logger is None:
        logger = ReportLogger()
    
    try:
        if monthly_data.empty:
            return "<p>No data available for monthly history chart.</p>"
        
        selected_column = "consumption_kWh"
        
        if selected_column not in monthly_data.columns:
            return "<p>Energy consumption data not available for the selected load.</p>"
        
        # Ensure Year-Month-cut-off exists
        if 'Year-Month-cut-off' not in monthly_data.columns:
            if 'Year' in monthly_data.columns and 'Month' in monthly_data.columns:
                monthly_data['Year-Month-cut-off'] = (
                    monthly_data['Year'].astype(str) + '-' +
                    monthly_data['Month'].astype(str).str.zfill(2)
                )
            else:
                monthly_data['Year-Month-cut-off'] = [
                    f"Month-{i+1:02d}" for i in range(len(monthly_data))
                ]
        
        # Use existing function to generate chart
        figures = draw_energy_kWh_per_month(monthly_data, [selected_column], logger)
        
        if figures and len(figures) > 0:
            return pio.to_html(figures[0], full_html=False, include_plotlyjs='cdn')
        else:
            return "<p>Error generating monthly history chart.</p>"
        
    except Exception as e:
        logger.error(f"❌ Error generating monthly history chart: {e}")
        return "<p>Error generating monthly history chart.</p>"


def draw_hourly_consumption_chart_html(
    hourly_data: pd.DataFrame,
    logger: Optional[ReportLogger] = None
) -> str:
    """Generate hourly consumption chart HTML"""
    if logger is None:
        logger = ReportLogger()
    
    try:
        logger.debug(f"🔍 Debug: Hourly data columns: {hourly_data.columns}")
        logger.debug(f"🔍 Debug: Hourly data index: {hourly_data.index}")
        
        if hourly_data.empty:
            return "<p>No data available for hourly consumption chart.</p>"
        
        hourly_values = hourly_data["consumption_kWh"]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=hourly_values.index,
            y=hourly_values.values,
            name=f'Hourly Consumption - kWh',
            marker_color=PlotlyStyle.STRATCON_PRIMARY_GREEN,
        ))
        
        fig = configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
        return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        
    except Exception as e:
        logger.error(f"❌ Error generating hourly consumption chart: {e}")
        return "<p>Error generating hourly consumption chart.</p>"


def draw_days_consumption_chart_html(
    days_data: pd.DataFrame,
    logger: Optional[ReportLogger] = None
) -> str:
    """Generate days of week consumption chart HTML"""
    if logger is None:
        logger = ReportLogger()
    
    try:
        logger.debug(f"🔍 Debug: Days data columns: {days_data.columns}")
        logger.debug(f"🔍 Debug: Days data index: {days_data.index}")
        
        if days_data.empty:
            return "<p>No data available for days consumption chart.</p>"
        
        days_values = days_data["consumption_kWh"]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=days_values.index,
            y=days_values.values,
            name=f'Days Consumption - kWh',
            marker_color=PlotlyStyle.STRATCON_PRIMARY_GREEN,
        ))
        
        fig = configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
        return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        
    except Exception as e:
        logger.error(f"❌ Error generating days consumption chart: {e}")
        return "<p>Error generating days consumption chart.</p>"


