#!/usr/bin/env python3
"""
Electricity Consumption Analysis
Gigawatt Power Inc Data Processing
"""

from calendar import month, monthrange
from pickle import TRUE
from statistics import mean
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from contextlib import redirect_stdout
import plotly.io as pio
import warnings
from typing import Optional, Dict, Any
from icecream import ic
warnings.filterwarnings('ignore')
import logging
from datetime import datetime
from pathlib import Path
import uuid
import os
import inspect
from config import ReportStyle, PlotlyStyle
from datetime import datetime




MAX_MISSING_DAYS_PER_MONTH = 5
MAX_CONSECUTIVE_MISSING_TIMESTAMPS = 2
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR = .20
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY = .05
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH = .01

class ReportLogger():
    def __init__(self, logs_dir="../logs"):
        self.session = uuid.uuid4().hex[:8]
        self.logs_dir = os.path.abspath(logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

    def format_message(self, level, msg):
        # You can add timestamp here if you want
        return f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self.session} [{level.upper()}] {msg}\n"

    def log(self, level, msg):
        formatted = self.format_message(level, msg)
        log_path = os.path.join(self.logs_dir, f"{level}.txt")
        with open(log_path, "a") as f:
            f.write(formatted)

    def info(self, msg):
        self.log('info', msg)

    def debug(self, msg):
        self.log('debug', msg)

    def warning(self, msg):
        self.log('warning', msg)

    def error(self, msg):
        self.log('error', msg)

    def get_html(self, levels=('info', 'warning', 'error', 'debug')):
        html = ""
        for level in levels:
            log_path = os.path.join(self.logs_dir, f"{level}.txt")
            with open(log_path, "r") as f:
                #select the lines that contain the session
                lines = [line for line in f.readlines() if self.session in line]
            if lines:
                #remove the session from the message
                lines = [line.replace(f'{self.session} - ', '') for line in lines]
                html += f"<h2>{level.capitalize()}</h2><ul>"
                for msg in lines:
                    html += f"<li>{msg}</li>"
                html += "</ul>"
        return html



class ComputeEnergy:
    """Class responsible for energy calculations and data processing"""
    def __init__(self):
        self.logger = ReportLogger()
        self.last_year = None
        self.last_month = None
        # These will be set by the GenerateReport class when needed
        self.loads = []
        self.energy_columns = []
        self.client_name = None

    def _raise_with_context(self, error_msg, original_error=None):
        """Helper method to raise errors with function context"""
        function_name = inspect.currentframe().f_back.f_code.co_name
        if original_error:
            raise ValueError(f"{function_name}: {error_msg}: {original_error}")
        else:
            raise ValueError(f"{function_name}: {error_msg}")

    def generate_consumption_column_name(self, load):
        return f'{load} - Consumption [kWh]'
    
    def generate_power_column_name(self, load):
        return f'{load} [kW]'

    def generate_cut_off(self, date, cutoff_day):
        """Generate cutoff month for a single date"""
        day = date.day
        year = date.year
        month = date.month
        
        if cutoff_day <= 15:
            if day < cutoff_day:
                if month == 1:
                    result_month = 12
                    result_year = year - 1
                else:
                    result_month = month - 1
                    result_year = year
            else:
                result_month = month
                result_year = year
        else:
            # Determine which month-year this date belongs to
            if day < cutoff_day:
                # Date belongs to the previous month
                result_month = month
                result_year = year
            else:
                if month == 12:
                    result_month = 1
                    result_year = year + 1
                else:
                    result_month = month + 1
                    result_year = year
        return f"{result_year}-{result_month:02d}"
                

    def generate_cut_off_month_column(self, df, cutoff_day):
        """
        Generate month-year labels based on a cutoff day for rolling months.
        
        Args:
            index: pandas DatetimeIndex with timestamps
            cutoff_day: int, the day of the month that marks the cutoff (1-31)
            
        Returns:
            pandas.Series: Series with YYYY-MM labels for each timestamp
            
        Example:
            If cutoff_day = 14:
            - April 13, 2025 -> "2025-03"
            - April 14, 2025 -> "2025-04"
            - January 13, 2025 -> "2024-12"
            - January 14, 2025 -> "2025-01"
        """
        try:
            # Convert DatetimeIndex to Series to use apply
            cutoff_series = pd.Series(df.index).apply(lambda x: self.generate_cut_off(x, cutoff_day))
            df['Year-Month-cut-off'] = cutoff_series.values
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error generating cutoff month column: {e}")
            self._raise_with_context("Failed to generate cutoff month column", e)


    def analyze_data(self,df):
        """Perform basic data analysis"""
        try:
            self.logger.debug("\n=== DATA ANALYSIS ===")
            
            # Check data types and info
            self.logger.debug("\nData types:")
            self.logger.debug(df.dtypes)
            
            self.logger.debug("\nMissing values:")
            self.logger.debug(df.isnull().sum())
            
            self.logger.debug("\nBasic statistics:")
            self.logger.debug(df.describe())

        except Exception as e:
            self.logger.error(f"❌ Error while analyzing data: {e}")
            raise


    def create_visualizations(self,df):
        """Create interactive visualizations with Plotly"""
        try:
            self.logger.info("\n=== CREATING VISUALIZATIONS ===")
            columns = [col for col in df.columns if '[kW]' in col]
            
            # Create interactive plot with Plotly
            fig = make_subplots(
                rows=len(columns), cols=1,
                subplot_titles=columns,
                vertical_spacing=0.1
            )

            for i, column in enumerate(columns):
                fig.add_trace(
                    go.Scatter(x=df.index, y=df[column], 
                            name=column, line=dict(color='red')),
                row=1, col=1
            )

            fig.update_layout(
                title='Electricity Consumption Analysis - June 2025',
                height=800,
                showlegend=True
            )

            # Save the plot
            fig.write_html("electricity_consumption_analysis.html")
            self.logger.debug("✅ Interactive plot saved as 'electricity_consumption_analysis.html'")
            
            # Display the plot in notebook
            fig.show()
            
            return fig
        except Exception as e:
            self.logger.error(f"❌ Error while creating visualizations: {e}")
            raise

    def analyze_patterns(self, df):
        """Analyze consumption patterns"""
        try:
            self.logger.info("\n=== PATTERN ANALYSIS ===")

            # Average consumption by hour
            hourly_avg = df.groupby('Hour')['Consumption [kW]'].mean()
            
            fig_hourly = px.line(x=hourly_avg.index, y=hourly_avg.values,
                                title='Average Consumption by Hour of Day',
                                labels={'x': 'Hour of Day', 'y': 'Average Consumption [kW]'})
            fig_hourly.write_html("hourly_consumption_pattern.html")
            self.logger.debug("✅ Hourly pattern saved as 'hourly_consumption_pattern.html'")
            fig_hourly.show()

            # Heatmap of consumption by hour and day
            pivot_data = df.pivot_table(
                values='Consumption [kW]', 
                index='Hour', 
                columns='Day', 
                aggfunc='mean'
            )

            fig_heatmap = px.imshow(pivot_data,
                                    title='Consumption Heatmap: Hour vs Day',
                                    labels=dict(x="Day of Month", y="Hour of Day", color="Consumption [kW]"),
                                    aspect="auto")
            fig_heatmap.write_html("consumption_heatmap.html")
            self.logger.debug("✅ Heatmap saved as 'consumption_heatmap.html'")
            fig_heatmap.show()
            
            return hourly_avg, pivot_data
        except Exception as e:
            self.logger.error(f"❌ Error while analyzing patterns: {e}")
            raise ValueError(f"❌ Error while analyzing patterns: {e}")

    def generate_summary(self,df):
        """Generate comprehensive summary"""
        try:
            f = io.StringIO()
            with redirect_stdout(f):
                print("\n=== ELECTRICITY CONSUMPTION SUMMARY ===")
                df_last_month = df[(df['Year'] == self.last_year) & (df['Month'] == self.last_month)]
                print(f"Total records: {len(df_last_month)}")
                print(f"Date range: {df_last_month.index.min()} to {df_last_month.index.max()}")
                print(f"Last month: {self.last_month}-{self.last_year}")
                
                for column in self.energy_columns:
                    self.logger.debug(f"generating summary for column: {column}")
                    print(f"\n{column} Statistics: ")
                    print(f"  Total Consumption: {df_last_month[column].sum():.2f} kWh")
                    print(f"  Average Power: {df_last_month[column].mean():.2f} kW")
                    print(f"  Maximum Power: {df_last_month[column].max():.2f} kW")
                    print(f"  Minimum Power: {df_last_month[column].min():.2f} kW")
                    print(f"  Std Dev Power: {df_last_month[column].std():.2f} kW")
                    
                    # # Peak hours analysis
                    peak_hour = df_last_month.groupby('Hour')[self.energy_columns].mean().idxmax()
                    peak_consumption = df_last_month.groupby('Hour')[self.energy_columns].mean().max()
                    print(f"\nPeak Consumption:")
                    print(f"  Peak hour: {peak_hour}:00")
                    print(f"  Peak consumption: {peak_consumption:.2f} kW")
                    self.logger.debug(f"Peak consumption: {peak_consumption:.2f} kW")
                # if 'Production' in self.loads:
                #     print(f"\nPercentage of energy generated by the solar panels:")
                #     print(f"  Ratio of energy generated by the solar panels: {df_last_month['Ratio_of_power_generated_by_the_solar_panels'].mean()*100:.2f}%")
                #     print(f"  Maximum ratio of energy generated by the solar panels: {df_last_month['Ratio_of_power_generated_by_the_solar_panels'].max()*100:.2f}%")
                
                
            generic_summary_html = "<h1>Report Summary</h1><pre>{}</pre>".format(f.getvalue())
            self.logger.debug(f"generic_summary_html generated")
            return generic_summary_html
        except Exception as e:
            self.logger.error(f"❌ Error while generating summary: {e}")
            raise ValueError(f"❌ Error while generating summary: {e}")

    
    def month_range_interval(self,year, month):
                return round(monthrange(year, month)[1] * 24 * 60 /self.interval_minutes * (1 - MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH))

    def select_full_months_by_day(self, year, month, missing_days, warning_only=True) -> bool:
        """Select only months that are full months"""
        try:
            self.logger.debug(f"🔍 DEBUG select_full_months_by_day: year={year}, month={month}, missing_days={missing_days}, warning_only={warning_only}")
            self.logger.debug(f"🔍 DEBUG select_full_months_by_day: MAX_MISSING_DAYS_PER_MONTH={MAX_MISSING_DAYS_PER_MONTH}")
            self.logger.debug(f"🔍 DEBUG select_full_months_by_day: len(missing_days)={len(missing_days)}")
            
            selected_month = []
            warning_months = []
            
            if len(missing_days) > MAX_MISSING_DAYS_PER_MONTH:
                self.logger.debug(f"🔍 DEBUG select_full_months_by_day: REJECTED - Too many missing days ({len(missing_days)} > {MAX_MISSING_DAYS_PER_MONTH})")
                return False
                
            if len(missing_days) == 0:
                self.logger.debug(f"🔍 DEBUG select_full_months_by_day: ACCEPTED - No missing days")
                return True
                
            if warning_only:
                self.logger.warning(f"⚠️ Warning  Missing days {year}-{month}: {missing_days} - computation continues")
                self.logger.debug(f"🔍 DEBUG select_full_months_by_day: ACCEPTED with warning - warning_only=True")
                return True
            else:
                self.logger.warning(f"⚠️ Month {year}-{month} will be removed from the analysis for {missing_days} missing days")
                self.logger.debug(f"🔍 DEBUG select_full_months_by_day: REJECTED - warning_only=False")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error while selecting full months - select_full_months-by_day {year}-{month} {missing_days}: {e}")
            raise ValueError(f"❌ Error while selecting full months - select_full_months-by_day {year}-{month} {missing_days}: {e}")

    
    def select_full_months(self,df, warning_only=True):
        try:
            self.logger.debug(f"🔍 DEBUG select_full_months: Starting with df shape={df.shape}, warning_only={warning_only}")
            self.logger.debug(f"🔍 DEBUG select_full_months: DataFrame columns: {list(df.columns)}")
            
            # Check if Year-Month-cut-off column exists
            if 'Year-Month-cut-off' not in df.columns:
                self.logger.error(f"❌ Year-Month-cut-off column not found in DataFrame")
                raise ValueError("Year-Month-cut-off column not found in DataFrame")
            
            #first we will create the tuples of month and year
            month_year_tuples_raw = df['Year-Month-cut-off'].unique()
            self.logger.debug(f"🔍 DEBUG select_full_months: Found unique month-year tuples: {month_year_tuples_raw}")
            
            month_year_tuples = []
            warning_months_tuples = []
            
            for month_year in month_year_tuples_raw:
                self.logger.debug(f"🔍 DEBUG select_full_months: Processing month_year: {month_year}")
                
                year = month_year.split('-')[0]
                month = month_year.split('-')[1]
                self.logger.debug(f"🔍 DEBUG select_full_months: Parsed year={year}, month={month}")
                
                df_month = df[df['Year-Month-cut-off'] == month_year]
                self.logger.debug(f"🔍 DEBUG select_full_months: df_month shape for {month_year}: {df_month.shape}")
                
                month_dates = df_month['Date'].unique()
                self.logger.debug(f"🔍 DEBUG select_full_months: Unique dates in {month_year}: {len(month_dates)} dates")
                self.logger.debug(f"🔍 DEBUG select_full_months: Date range: {min(month_dates)} to {max(month_dates)}")
                
                # Calculate expected days in month
                expected_days = monthrange(int(year), int(month))[1]
                self.logger.debug(f"🔍 DEBUG select_full_months: Expected days in {year}-{month}: {expected_days}")
                
                # Convert month_dates to day integers for comparison
                month_dates_int = [int(d.split('-')[2]) for d in month_dates if '-' in d]
                missing_days = [i for i in range(1, expected_days + 1) if i not in month_dates_int]
                self.logger.debug(f"🔍 DEBUG select_full_months: Missing days in {month_year}: {missing_days} (count: {len(missing_days)})")
                self.logger.debug(f"🔍 DEBUG select_full_months: Month dates as integers: {sorted(month_dates_int)}")
                
                result = self.select_full_months_by_day(year, month, missing_days, warning_only)
                self.logger.debug(f"🔍 DEBUG select_full_months: select_full_months_by_day result for {month_year}: {result}")
                
                if result == True:
                    month_year_tuples.append((year, month))
                    self.logger.debug(f"🔍 DEBUG select_full_months: ACCEPTED {month_year}")
                else:
                    self.logger.debug(f"🔍 DEBUG select_full_months: REJECTED {month_year}")
                    
            self.logger.debug(f"🔍 DEBUG select_full_months: Final selected months: {month_year_tuples}")
            self.logger.debug(f"✅ Selected months for computation: {[(int(year), int(month)) for year, month in month_year_tuples]}")
            
            if not month_year_tuples:
                self.logger.warning(f"⚠️ No months selected for computation!")
                return None
                
            list_df = []
            for year, month in month_year_tuples:
                df_month = df[(df['Year-Month-cut-off'] == f"{year}-{month}")]
                self.logger.debug(f"🔍 DEBUG select_full_months: Adding df_month for {year}-{month}, shape: {df_month.shape}")
                list_df.append(df_month)
                
            if list_df:
                df_result = pd.concat(list_df)
                df_result.sort_index(inplace=True)
                self.logger.debug(f"🔍 DEBUG select_full_months: Final result shape: {df_result.shape}")
                return df_result
            else:
                self.logger.warning(f"⚠️ No dataframes to concatenate!")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error while selecting full months: {e}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise ValueError(f"❌ Error while selecting full months: {e}")

    def draw_energy_kWh_per_month_production(self, month_data):
        try:
            """Draw bar charts of the energy consumption and import/export per month"""
            self.logger.info("\n=== DRAWING ENERGY PER MONTH ===")
            self.logger.info(month_data)
            
            if "Consumption [kW]" in self.loads and "Production [kW]" in self.loads:
                # Reset index to make it a regular DataFrame
                month_data_reset = month_data.reset_index()
                
                # Create a combined Year-Month column for x-axis
                month_data_reset['Year-Month'] = month_data_reset['Year'].astype(str) + '-' + month_data_reset['Month'].astype(str).str.zfill(2)
                month_data_reset['Label'] = pd.to_datetime(month_data_reset['Year-Month']).dt.strftime('%b %Y')
                
                # Create two subplots: one for consumption/production, one for import/export
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Energy Consumption vs Production per Month - kWh', 'Energy Import vs Export per Month - kWh'),
                    vertical_spacing=0.15
                )
                
                # Consumption vs Production (side by side)
                fig.add_trace(
                    go.Bar(x=month_data_reset['Label'], y=month_data_reset['Energy_consumption_per_interval [kWh]'],
                        name='Consumption', marker_color=PlotlyStyle.CONSUMPTION_COLOR),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Bar(x=month_data_reset['Label'], y=month_data_reset['Energy_production_per_interval [kWh]'],
                        name='Production', marker_color=PlotlyStyle.PRODUCTION_COLOR),
                    row=1, col=1
                )
                
                # Import vs Export (side by side, with import as negative)
                fig.add_trace(
                    go.Bar(x=month_data_reset['Label'], y=-month_data_reset['Energy_import_per_interval [kWh]'],
                        name='Import (negative)', marker_color=PlotlyStyle.IMPORT_COLOR),
                    row=2, col=1
                )
                fig.add_trace(
                    go.Bar(x=month_data_reset['Label'], y=month_data_reset['Energy_export_per_interval [kWh]'],
                        name='Export', marker_color=PlotlyStyle.EXPORT_COLOR),
                    row=2, col=1
                )
                fig.update_yaxes(tickformat=",.0f")
                fig.update_layout(
                    title='Energy Analysis per Month',
                    height=800,
                    showlegend=True,
                )
                fig.update_layout(
                    font=PlotlyStyle.update_font,
                    title_font=PlotlyStyle.update_title_font
                )
                fig.update_xaxes(type='category')
                self.logger.debug(f"✅ Energy per month plot generated")
                fig.show()
                self.logger.debug(f"✅ Energy per month plot shown")
                return fig
        except Exception as e:
            self.logger.error(f"❌ Error while drawing energy per month: {e}")
            raise ValueError(f"❌ Error while drawing energy per month: {e}")

    def draw_energy_kWh_per_month(self, month_data):
        try:
            """Draw bar charts of the energy consumption and import/export per month"""
            self.logger.info("\n=== DRAWING ENERGY PER MONTH ===")
            self.logger.info(month_data)
            
            if "Consumption [kW]" in self.loads and "Production [kW]" in self.loads:
                fig = self.draw_energy_kWh_per_month_production(month_data)
                return fig
            else:
                # Reset index to make it a regular DataFrame
                month_data_reset = month_data.reset_index()
                self.logger.debug(f"month_data_reset columns: {month_data_reset.columns}")
                
                # Create a combined Year-Month column for x-axis
                month_data_reset['Year-Month'] = month_data_reset['Year'].astype(str) + '-' + month_data_reset['Month'].astype(str).str.zfill(2)
                month_data_reset['Label'] = pd.to_datetime(month_data_reset['Year-Month']).dt.strftime('%b %Y')
                
                #create a new plot for each load
                columns = []
                for col in month_data.columns:
                    for load in self.loads:
                        if load in col:
                            columns.append((load, col))
                self.logger.debug(f"load columns: {columns}")
                # Create one figure per load
                figures = []
                
                for i, item in enumerate(columns):
                    load, col = item
                    
                    # Create individual figure for each load
                    fig = go.Figure()
                    fig.add_trace(
                        go.Bar(x=month_data_reset['Label'], y=month_data_reset[col],
                            name=load, marker_color=PlotlyStyle.CONSUMPTION_COLOR)
                    )
                    
                    fig.update_yaxes(tickformat=",.0f")
                    fig.update_layout(
                        title=f'Energy Analysis per Month - {load}',
                        height=400,
                        showlegend=True,
                        font=PlotlyStyle.update_font,
                        title_font=PlotlyStyle.update_title_font
                    )
                    fig.update_xaxes(type='category')
                    
                    # Save individual figure
                    fig.write_html(f"energy_consumption_{load.replace(' ', '_').replace('/', '_')}_per_month.html")
                    fig.show()
                    
                    figures.append(fig)
                    self.logger.debug(f"✅ Energy per month plot generated for {load}")
                
                self.logger.debug(f"✅ All {len(figures)} energy per month plots generated and shown")
                return figures
        except Exception as e:
            self.logger.error(f"❌ Error while drawing energy per month: {e}")
            raise ValueError(f"❌ Error while drawing energy per month: {e}")

    def draw_energy_kWh_per_day_production(self, day_data):
        """Draw bar charts of the energy consumption and import/export per day"""
        self.logger.info("\n=== DRAWING ENERGY PER DAY ===")
        self.logger.info(day_data)
        return None

    def draw_energy_kWh_per_day(self, day_data):
        """Draw bar charts of the energy consumption and import/export per day"""
        self.logger.info("\n=== DRAWING ENERGY PER DAY ===")
        self.logger.info(day_data)
        if "Consumption [kW]" in self.loads and "Production [kW]" in self.loads:
            fig = self.draw_energy_kWh_per_day_production(day_data)
            return fig
        else:
            try:
                # Reset index to make it a regular DataFrame
                day_data_reset = day_data.reset_index()
                
                # Create a combined Year-Month-Day column for x-axis
                day_data_reset['Date'] = day_data_reset['Year'].astype(str) + '-' + day_data_reset['Month'].astype(str).str.zfill(2) + '-' + day_data_reset['Day'].astype(str).str.zfill(2)

                #create a new plot for each load
                columns = []
                for col in day_data.columns:
                    for load in self.loads:
                        if load in col:
                            columns.append(col)
                            
                # Create one figure per load
                figures = []
                
                for col in columns:
                    # Extract load name from column name
                    load = col.replace('Energy_consumption_', '').replace('_per_interval [kWh]', '')
                    
                    # Create individual figure for each load
                    fig = go.Figure()
                    fig.add_trace(
                        go.Bar(x=day_data_reset['Date'], y=day_data_reset[col],
                            name=load, marker_color=PlotlyStyle.CONSUMPTION_COLOR)
                    )
                    
                    fig.update_yaxes(tickformat=",.0f")
                    fig.update_layout(
                        title=f'Energy Analysis per Day - {load}',
                        height=400,
                        showlegend=True,
                        font=PlotlyStyle.update_font,
                        title_font=PlotlyStyle.update_title_font
                    )
                    fig.update_xaxes(type='category')
                    
                    # Save individual figure
                    fig.write_html(f"energy_consumption_{load.replace(' ', '_').replace('/', '_')}_per_day.html")
                    fig.show()
                    
                    figures.append(fig)
                    self.logger.debug(f"✅ Energy per day plot generated for {load}")
                
                self.logger.debug(f"✅ All {len(figures)} energy per day plots generated and shown")
                return figures
            except Exception as e:
                self.logger.error(f"❌ Error while drawing energy per day: {e}")
                raise ValueError(f"❌ Error while drawing energy per day: {e}")
            
    def compute_energy(self,df):
        """Compute energy consumption with quality safeguards"""
        try:
            # 1. Compute the mean power consumption per interval defined as the difference between the present row and following row
            for load in self.loads:
                col_mean = f'Mean_{load}_per_interval [kW]'
                col_production = self.generate_power_column_name(load)
                col_consumption = self.generate_consumption_column_name(load)
                df[col_mean] = df[col_production].rolling(window=2).mean().shift(-1)
                df[col_consumption] = df[col_mean] * df['Interval_minutes'] / 60
            if 'Production' in self.loads:
                df['Ratio_of_power_generated_by_the_solar_panels'] = df['Energy_production_per_interval [kWh]'] / df['Energy_consumption_per_interval [kWh]']
            return df
        except Exception as e:
            self.logger.error(f"❌ Error while computing energy: {e}")
            raise ValueError(f"❌ Error while computing energy: {e}")

    def generate_summary_energy(self,data, cutoff_day):
        """Generate summary of energy consumption"""
        try:
            self.logger.debug(f"col_energy_consumption: {self.energy_columns}")
    
            # 1. Monthly summary
            month_data = data.groupby(['Year-Month-cut-off'])[self.energy_columns].sum()
            
            # Get the last month data
            last_month = self.generate_cut_off(data.index.max(), cutoff_day) # get the last month based on the cutoff day inside the data
            data_last_month = data[data['Year-Month-cut-off'] == last_month]

            fig_energy_monthly = self.draw_energy_kWh_per_month(month_data)
            f = io.StringIO()
            with redirect_stdout(f):
                print("\n=== SUMMARY OF ENERGY CONSUMPTION MONTHLY ===")
                for column_name in  self.energy_columns:
                    summary_energy_monthly = self.generate_summary_energy_per_column(month_data, column_name)
            summary_energy_monthly_html = "<pre>{}</pre>".format(f.getvalue())

            # 2. Daily summary for the last month

            day_data = data_last_month.groupby(['Year','Month','Day'])[self.energy_columns].sum()
            fig_energy_daily = self.draw_energy_kWh_per_day(day_data)
            f = io.StringIO()
            with redirect_stdout(f):
                print("\n=== SUMMARY OF ENERGY CONSUMPTION DAILY ===")
                for column_name in self.energy_columns:
                    summary_energy_daily = self.generate_summary_daily(day_data, column_name)
            summary_energy_daily_html = "<pre>{}</pre>".format(f.getvalue())
            return fig_energy_monthly, fig_energy_daily, summary_energy_monthly_html, summary_energy_daily_html
        except Exception as e:
            self.logger.error(f"❌ Error while generating summary of energy consumption: {e}")
            raise ValueError(f"❌ Error while generating summary of energy consumption: {e}")

    
    def generate_summary_energy_per_column(self,month_data, column_name):
        """Generate summary of energy consumption per column"""
        name = [load for load in self.loads if load in column_name][0]
        print(f"\n-- Comparison of {name} per month --")
        print(f"Total {name} latest month: {month_data.iloc[-1][column_name]:.2f} kWh")
        print(f"Average {name} previous months: {month_data.iloc[:-1][column_name].mean():.2f} kWh") 
        print(f"Max {name} previous months: {month_data.iloc[:-1][column_name].max():.2f} kWh")
        print(f"Min {name} previous months: {month_data.iloc[:-1][column_name].min():.2f} kWh")
        print(f"Delta vs previous month - {name}: {month_data.iloc[-1][column_name] - month_data.iloc[:-1][column_name].mean():.2f} kWh")
    
    def generate_summary_daily(self, day_data, column_name):
        """Generate summary of energy consumption per day"""
        name = [load for load in self.loads if load in column_name][0]
        print(f"\n--- Comparison of {name} per day ---")
        #select data from the last month
        print(f"Average {name} daily consumption: {day_data.iloc[:-1][column_name].mean():.2f} kWh") 
        print(f"Max {name} daily consumption: {day_data.iloc[:-1][column_name].max():.2f} kWh")
        print(f"Min {name} daily consumption: {day_data.iloc[:-1][column_name].min():.2f} kWh")




    def check_data_completeness(self,df, strict=False):
        """Check the data completeness"""
        #Maximum of consecutive missing timestamps check
        df['Alarm_consecutive_missing_timestamps'] = df['Missing_timestamps_after_timestamp'] > MAX_CONSECUTIVE_MISSING_TIMESTAMPS
        if len(df[df['Alarm_consecutive_missing_timestamps'] == True]) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(df[df['Alarm_consecutive_missing_timestamps'] == True])} consecutive missing timestamps")
            self.logger.warning(f"   Largest gap: {df['Nb_of_intervals_between_timestamps'].max():.1f} intervals")
            
            if strict:
                self.logger.error(f"⚠️  Warning: Data is not complete to compute energy - consecutive missing timestamps")
                raise ValueError("Data is not complete to compute energy - consecutive missing timestamps")
        
        #Maximum of missing timestamps per hour check
        self.check_data_completeness_per_hour(df, strict)
        
        #Maximum of missing timestamps per day check
        self.check_data_completeness_per_day(df, strict)

        #Maximum of missing timestamps per month check
        self.check_data_completeness_per_month(df, strict)

    def check_data_completeness_per_month(self, df, strict):
        """Check the data completeness per month"""
        # Group by Year and Month, sum the missing timestamps
        monthly_missing = df.groupby(['Year-Month-cut-off'])['Missing_timestamps_after_timestamp'].sum()
        
        # Check if any month exceeds the threshold
        months_with_too_many_missing = monthly_missing[monthly_missing > self.max_missing_timestamps_per_month]
        
        if len(months_with_too_many_missing) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(months_with_too_many_missing)} months with more than {self.max_missing_timestamps_per_month} missing timestamps")
            self.logger.warning(f"   Problematic months: {list(months_with_too_many_missing.index)}")
            if strict:
                raise ValueError("Data is not complete to compute energy")
        else:
            self.logger.debug(f"✅ All months are complete: {monthly_missing.index}")

    def check_data_completeness_per_day(self, df, strict):
        """Check the data completeness per day"""
        # Group by Year, Month, and Day, sum the missing timestamps
        daily_missing = df.groupby(['Year','Month','Day'])['Missing_timestamps_after_timestamp'].sum()
        
        # Check if any day exceeds the threshold
        days_with_too_many_missing = daily_missing[daily_missing > self.max_missing_timestamps_per_day]
        
        if len(days_with_too_many_missing) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(days_with_too_many_missing)} days with more than {self.max_missing_timestamps_per_day} missing timestamps")
            self.logger.warning(f"   Problematic days: {list(days_with_too_many_missing.index)}")
            if strict:
                raise ValueError("Data is not complete to compute energy")
        else:
            self.logger.debug(f"✅ All days are passing the daily threshold: {self.max_missing_timestamps_per_day}")

    def check_data_completeness_per_hour(self, df, strict):
        """Check the data completeness per hour"""
        # Group by Year, Month, Day, and Hour, sum the missing timestamps
        hourly_missing = df.groupby(['Year','Month','Day','Hour'])['Missing_timestamps_after_timestamp'].sum()
        
        # Check if any hour exceeds the threshold
        hours_with_too_many_missing = hourly_missing[hourly_missing > self.max_missing_timestamps_per_hour]
        
        if len(hours_with_too_many_missing) > 0:
            self.logger.warning(f"⚠️  ALARM: Found {len(hours_with_too_many_missing)} hours with more than {self.max_missing_timestamps_per_hour} missing timestamps")
            self.logger.warning(f"   Problematic hours: {list(hours_with_too_many_missing.index)}")
            if strict:
                raise ValueError("Data is not complete to compute energy")
        else:
            self.logger.debug(f"✅ All hours are passing the hourly threshold: {self.max_missing_timestamps_per_hour}")

    
    def init_interval_and_alarm_levels(self, df):
        """Initialize constants and alarm levels"""
        try:
            if "Interval_minutes" not in df.columns:
                df['Interval_minutes'] = df.index.diff() / np.timedelta64(1, 'm')
            self.interval_minutes = round(df['Interval_minutes'].mean(),0)
            self.timestamps_per_hour = round(60 / self.interval_minutes)
            df['Nb_of_intervals_between_timestamps'] = df['Interval_minutes'] / self.interval_minutes
            df['Missing_timestamps_after_timestamp'] = df['Nb_of_intervals_between_timestamps'] - 1
            self.max_missing_timestamps_per_hour = np.ceil(self.timestamps_per_hour * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR)
            self.max_missing_timestamps_per_day = np.ceil(self.timestamps_per_hour * 24 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY)
            self.max_missing_timestamps_per_month = np.ceil(self.timestamps_per_hour * 24 * 30 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH)

            self.logger.debug(f"✅ Interval minutes: {self.interval_minutes}")
            self.logger.debug(f"✅ Timestamps per hour: {self.timestamps_per_hour}")
            self.logger.debug(f"✅ Max missing timestamps per hour: {self.max_missing_timestamps_per_hour}")
            self.logger.debug(f"✅ Max missing timestamps per day: {self.max_missing_timestamps_per_day}")
            self.logger.debug(f"✅ Max missing timestamps per month: {self.max_missing_timestamps_per_month}")

            return df
        except Exception as e:
            self.logger.error(f"❌ Error while initializing interval and alarm levels: {e}")
            raise ValueError(f"❌ Error while initializing interval and alarm levels: {e}")



    def generate_html_styles(self):
        """Generate HTML styles"""
        try:
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

            /* Headings */
            h1, .h1 {{ font-family: var(--heading-font); font-size: var(--h1-size); font-weight: bold; color: #333; }}
            h2, .h2 {{ font-family: var(--heading-font); font-size: var(--h2-size); font-weight: bold; color: #333; }}
            h3, .h3 {{ font-family: var(--body-font); font-size: var(--h3-size); font-weight: bold; color: #333; }}

            /* Body text */
            body, .body-text {{ font-family: var(--body-font); font-size: var(--body-size); color: #333; }}

            /* Utility color classes */
            .consumption {{ color: var(--consumption-color); }}
            .production  {{ color: var(--production-color); }}
            .import      {{ color: var(--import-color); }}
            .export      {{ color: var(--export-color); }}
            </style>
            """
        except Exception as e:
            self.logger.error(f"❌ Error while generating HTML styles: {e}")
            raise ValueError(f"❌ Error while generating HTML styles: {e}")
    

    def generate_report(self, fig_energy_monthly, fig_energy_daily, summary_energy_monthly_html, summary_energy_daily_html, generic_summary_html):
        """Generate a report from the analysis"""
        # Capture summary output
        try:
            self.logger.debug(f"✅ Generating figures for the report")
            # Get your figures (assume you have fig_month and fig_day)
            if type(fig_energy_monthly) == list and type(fig_energy_daily) == list:
                self.generate_report_large_number_of_loads(fig_energy_monthly, fig_energy_daily, summary_energy_monthly_html, summary_energy_daily_html, generic_summary_html)
            else:
                fig_month_html = pio.to_html(fig_energy_monthly, full_html=False, include_plotlyjs='cdn')
                fig_day_html = pio.to_html(fig_energy_daily, full_html=False, include_plotlyjs=False)
            self.logger.debug(f"✅ Figures generated")
            # Combine into one HTML
            full_html = f"""
            <html>
            {self.generate_html_styles()}
            <head>
                <h1>{self.client_name}</h1>
                <h1>Electricity Analysis Report</h1>
            </head>
            <body>
                {generic_summary_html}
                <h2>Monthly Analysis</h2>
                {fig_month_html}
                {summary_energy_monthly_html}
                <h2>Daily Analysis</h2>
                {fig_day_html}
                {summary_energy_daily_html}
            </body>
            </html>
            """
            self.logger.debug(f"✅ HTML Report generated")
         
            self.write_report(full_html)
        except Exception as e:
            self.logger.error(f"❌ Error while generating HTML Report: {e}")
            raise ValueError(f"❌ Error while generating HTML Report: {e}")
        
    
    def write_report(self, full_html):
        """Write the report to a file"""
        try:
            self.report_name = f"{self.client_name} - {self.last_year}-{self.last_month}"
    
        #write the html report to a file
            self.logger.debug(f"✅ Writing HTML Report to /home/philg/projects/stratcon/reports/{self.report_name}.html")
            with open(f"/home/philg/projects/stratcon/reports/{self.report_name}.html", "w") as f:
                f.write(full_html)
                f.write(self.generate_html_separator("warning"))
                f.write(self.logger.get_html(['warning']))
                f.write(self.generate_html_separator("end of report"))
            self.logger.debug(f"✅ Report written to /home/philg/projects/stratcon/reports/{self.report_name}.html")
        except Exception as e:
            self.logger.error(f"❌ Error while writing HTML Report: {e}")
            raise ValueError(f"❌ Error while writing HTML Report: {e}")

    def generate_report_large_number_of_loads(self, fig_energy_monthly, fig_energy_daily, summary_energy_monthly_html, summary_energy_daily_html, generic_summary_html):
        """Generate a report from the analysis"""
        # Capture summary output
        try:
            self.logger.debug(f"✅ Generating figures for the report")
            # Get your figures (assume you have fig_month and fig_day)
            # Combine into one HTML
            html_report = f"""
            <html>
            {self.generate_html_styles()}
            <head>
                <h1>{self.client_name}</h1>
                <h1>Electricity Analysis Report</h1>
            </head>
            <body>
                {generic_summary_html}
                <h2>Monthly Analysis</h2>
                {summary_energy_monthly_html}
                <h2>Daily Analysis</h2>
                {summary_energy_daily_html}
            </body>
            """
            #prepare the report for each load for the figures
            figures_html = []
            for i, load in enumerate(self.loads):
                fig_energy_monthly_load = fig_energy_monthly[i]
                fig_energy_monthly_load_html = pio.to_html(fig_energy_monthly_load, full_html=False, include_plotlyjs='cdn')
                fig_energy_daily_load = fig_energy_daily[i]
                fig_energy_daily_load_html = pio.to_html(fig_energy_daily_load, full_html=False, include_plotlyjs='cdn')
                fig_html = f"""
                <h2>{load} - Monthly Graphs</h2>
                {fig_energy_monthly_load_html}
                <h2>{load} - Daily Graphs</h2>
                {fig_energy_daily_load_html}
                """
                figures_html.append(fig_html)
            figures_html_report = "\n".join(figures_html)
            figures_html_report = f"""
            <body>
            <h2>Graphs</h2>
            {figures_html_report}
            </body>
            </html>
            """
            html_report += figures_html_report
            self.write_report(html_report)
                


            self.logger.debug(f"✅ HTML Report generated")
        except Exception as e:
            self.logger.error(f"❌ Error while generating HTML Report for large number of loads: {e}")
            raise ValueError(f"❌ Error while generating HTML Report for large number of loads: {e}")


    def generate_html_separator(self, level):
        """Generate a separator for the HTML report"""
        try:
            return f"""
            <div class="separator {level}">
            <h2>========================================</h2>
            <h2>=========={level.capitalize()}==========</h2>
            <h2>========================================</h2>
            </div>
            """
        except Exception as e:
            self.logger.error(f"❌ Error while generating HTML separator: {e}")
            raise ValueError(f"❌ Error while generating HTML separator: {e}")

    def generate_onepager_report(self, df, loads_data_path=None):
        """Generate a professional one-pager report similar to the mockup"""
        try:
            self.logger.info("🔌 Generating One-Pager Report")
            print(f"🔍 Debug: DataFrame shape: {df.shape}")
            print(f"🔍 Debug: DataFrame columns: {list(df.columns)}")
            
            # Load tenant/floor data if provided
            tenant_data = None
            if loads_data_path and os.path.exists(loads_data_path):
                tenant_data = pd.read_csv(loads_data_path)
                self.logger.debug(f"✅ Loaded tenant data from {loads_data_path}")
                print(f"🔍 Debug: Tenant data shape: {tenant_data.shape}")
            else:
                print(f"🔍 Debug: No tenant data path provided or file doesn't exist")
            
            # Calculate key metrics
            energy_columns = [col for col in df.columns if 'Consumption [kWh]' in col]
            power_columns = [col for col in df.columns if '[kW]' in col]
            
            print(f"🔍 Debug: Energy columns found: {energy_columns}")
            print(f"🔍 Debug: Power columns found: {power_columns}")
            
            total_energy = df[energy_columns].sum().sum() if energy_columns else 0
            avg_daily_consumption = df[power_columns].mean().mean() if power_columns else 0
            peak_consumption = df[power_columns].max().max() if power_columns else 0
            
            print(f"🔍 Debug: Total energy: {total_energy}")
            print(f"🔍 Debug: Avg daily consumption: {avg_daily_consumption}")
            print(f"🔍 Debug: Peak consumption: {peak_consumption}")
            
            # Get date range
            date_range = f"{df.index.min().strftime('%B %d, %Y')} - {df.index.max().strftime('%B %d, %Y')}"
            print(f"🔍 Debug: Date range: {date_range}")
            
            # Generate the one-pager HTML
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Adventenergy x NEO x Stratcon - Energy Analysis Report</title>
                {self.generate_onepager_styles()}
            </head>
            <body>
                <div class="container">
                    <!-- Header -->
                    <header class="header">
                        <div class="logo-section">
                            <h1 class="main-title">Adventenergy x NEO x Stratcon</h1>
                            <p class="subtitle">Energy Analysis Report</p>
                        </div>
                        <div class="report-info">
                            <div class="logo-container">
                                <img src="Stratcon.ph White.png" alt="Stratcon Logo" class="stratcon-logo">
                            </div>
                            <p class="date-range">{date_range}</p>
                            <p class="generated-date">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                    </header>

                    <!-- Key Metrics Section -->
                    <section class="metrics-section">
                        <h2 class="section-title">Key Performance Indicators</h2>
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-value">{total_energy:,.0f}</div>
                                <div class="metric-label">Total Energy (kWh)</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">{avg_daily_consumption:.1f}</div>
                                <div class="metric-label">Avg Daily Consumption (kW)</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">{peak_consumption:.1f}</div>
                                <div class="metric-label">Peak Consumption (kW)</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">{len(power_columns)}</div>
                                <div class="metric-label">Total Loads Monitored</div>
                            </div>
                        </div>
                    </section>

                    <!-- Tenant Summary Section -->
                    {self.generate_tenant_summary_section(tenant_data) if tenant_data is not None else ''}

                    <!-- Energy Consumption Chart -->
                    <section class="chart-section">
                        <h2 class="section-title">Energy Consumption Overview</h2>
                        <div class="chart-container">
                            {self.generate_consumption_chart_html(df)}
                        </div>
                    </section>

                    <!-- Footer -->
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
            
            # Write the report
            print("🔍 Debug: About to write report...")
            report_path = self.write_onepager_report(html_content)
            print(f"🔍 Debug: Report written to: {report_path}")
            self.logger.info("✅ One-pager report generated successfully")
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Error generating one-pager report: {e}")
            raise ValueError(f"❌ Error generating one-pager report: {e}")

    def generate_onepager_styles(self):
        """Generate modern CSS styles for the one-pager report"""
        return """
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                min-height: 100vh;
            }
            
            /* Header */
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .main-title {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
            }
            
            .subtitle {
                font-size: 1.2rem;
                opacity: 0.9;
                font-weight: 300;
            }
            
            .report-info {
                text-align: right;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
            }
            
            .logo-container {
                margin-bottom: 1rem;
            }
            
            .stratcon-logo {
                height: 60px;
                width: auto;
                max-width: 200px;
                object-fit: contain;
            }
            
            .date-range {
                font-size: 1.1rem;
                font-weight: 500;
                margin-bottom: 0.5rem;
            }
            
            .generated-date {
                font-size: 0.9rem;
                opacity: 0.8;
            }
            
            /* Sections */
            .metrics-section, .chart-section {
                padding: 2rem;
            }
            
            .section-title {
                font-size: 1.8rem;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 1.5rem;
                border-bottom: 3px solid #3498db;
                padding-bottom: 0.5rem;
            }
            
            /* Metrics Grid */
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            
            .metric-card {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 1.5rem;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-left: 4px solid #3498db;
            }
            
            .metric-value {
                font-size: 2.5rem;
                font-weight: 700;
                color: #2c3e50;
                margin-bottom: 0.5rem;
            }
            
            .metric-label {
                font-size: 0.9rem;
                color: #666;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            /* Tenant Summary */
            .tenant-summary {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 8px;
                margin-bottom: 2rem;
            }
            
            .tenant-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
            }
            
            .tenant-item {
                background: white;
                padding: 1rem;
                border-radius: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .tenant-name {
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 0.25rem;
            }
            
            .tenant-details {
                font-size: 0.85rem;
                color: #666;
            }
            
            /* Chart Container */
            .chart-container {
                background: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            /* Footer */
            .footer {
                background: #2c3e50;
                color: white;
                padding: 1.5rem 2rem;
                text-align: center;
            }
            
            .footer-content p {
                margin-bottom: 0.5rem;
                opacity: 0.9;
            }
            
            /* Responsive */
            @media (max-width: 768px) {
                .header {
                    flex-direction: column;
                    text-align: center;
                }
                
                .report-info {
                    align-items: center;
                    margin-top: 1rem;
                }
                
                .stratcon-logo {
                    height: 50px;
                }
                
                .main-title {
                    font-size: 2rem;
                }
                
                .metrics-grid {
                    grid-template-columns: 1fr;
                }
                
                .container {
                    margin: 0;
                }
            }
        </style>
        """

    def generate_tenant_summary_section(self, tenant_data):
        """Generate tenant summary section HTML"""
        if tenant_data is None:
            return ""
        
        # Group by floor
        floor_summary = tenant_data.groupby('Floor').agg({
            'tenant': 'count',
            'floor_are': 'sum'
        }).reset_index()
        
        tenant_items = []
        for _, row in floor_summary.iterrows():
            tenant_items.append(f"""
                <div class="tenant-item">
                    <div class="tenant-name">{row['Floor']}</div>
                    <div class="tenant-details">
                        {row['tenant']} tenants • {row['floor_are']:,.0f} sq ft
                    </div>
                </div>
            """)
        
        return f"""
        <section class="tenant-summary">
            <h2 class="section-title">Building Overview</h2>
            <div class="tenant-grid">
                {''.join(tenant_items)}
            </div>
        </section>
        """

    def generate_consumption_chart_html(self, df):
        """Generate consumption chart HTML"""
        try:
            print(f"🔍 Debug: Generating chart for DataFrame with shape: {df.shape}")
            # Find power columns in the dataframe
            power_columns = [col for col in df.columns if '[kW]' in col]
            print(f"🔍 Debug: Power columns for chart: {power_columns}")
            
            if not power_columns:
                print("🔍 Debug: No power columns found for chart")
                return "<p>No consumption data available for chart generation.</p>"
            
            # Create a simple consumption chart
            fig = go.Figure()
            
            # Add traces for each power column (limit to first 5 for readability)
            for col in power_columns[:5]:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df[col],
                    mode='lines',
                    name=col.replace(' [kW]', ''),
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title="Energy Consumption Over Time",
                xaxis_title="Date",
                yaxis_title="Power (kW)",
                height=400,
                showlegend=True,
                template="plotly_white"
            )
            
            return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
            
        except Exception as e:
            self.logger.error(f"❌ Error generating consumption chart: {e}")
            return "<p>Error generating consumption chart.</p>"

    def write_onepager_report(self, html_content):
        """Write the one-pager report to a file"""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = "/home/philg/projects/stratcon/reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            # Copy logo file to reports directory if it exists
            logo_source = "/home/philg/projects/stratcon/resources/logos/Stratcon.ph White.png"
            logo_dest = os.path.join(reports_dir, "Stratcon.ph White.png")
            
            if os.path.exists(logo_source):
                import shutil
                shutil.copy2(logo_source, logo_dest)
                self.logger.debug(f"✅ Logo copied to reports directory: {logo_dest}")
            else:
                self.logger.warning(f"⚠️ Logo file not found at: {logo_source}")
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"onepager_report_{timestamp}.html"
            filepath = os.path.join(reports_dir, filename)
            
            # Write the file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            self.logger.info(f"✅ One-pager report written to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"❌ Error writing one-pager report: {e}")
            raise ValueError(f"❌ Error writing one-pager report: {e}")



class GenerateReport:
    """Class responsible for report generation and data preparation"""
    def __init__(self):
        self.logger = ReportLogger()
        self.compute_energy = ComputeEnergy()
        self.client_name = None
        self.client_detail_name = None
        self.loads = []
        self.power_columns = []
        self.energy_columns = []
        self.last_year = None
        self.last_month = None

    def load_and_prepare_data(self, path: str, cutoff_day: int = 7) -> pd.DataFrame:
        """Load electricity consumption data with proper decimal handling"""
        try:
            print(f"🔍 Debug: Loading data from: {path}")
            print(f"🔍 Debug: File exists: {os.path.exists(path)}")
            
            # Read the CSV file with proper decimal handling for European format
            print(f"🔍 Debug: Reading CSV...")
            df = pd.read_csv(path, 
                            delimiter=',', 
                            decimal=',',
                            thousands='.',
                            parse_dates=['Date'])
            print(f"🔍 Debug: CSV read successfully. Shape: {df.shape}")
            
            # Extract client name from path more robustly
            path_parts = path.split('/')
            if len(path_parts) >= 2:
                self.client_name = path_parts[-2]  # Get the parent directory name
            else:
                self.client_name = "Unknown Client"
            
            # Extract client detail name from filename
            filename = path_parts[-1]  # Get the filename
            if '- Electricity consumption' in filename:
                self.client_detail_name = filename.split('- Electricity consumption')[0]
            else:
                self.client_detail_name = filename.replace('.csv', '')
            
            print(f"🔍 Debug: Client name: {self.client_name}")
            print(f"🔍 Debug: Client detail name: {self.client_detail_name}")
            
            self.logger.debug(f"Client name: {self.client_name} - Client detail name: {self.client_detail_name}")
            
            self.logger.debug(f"✅ Data loaded successfully!")
            self.logger.debug(f"Dataset shape: {df.shape}")
            self.logger.debug(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
            
            print(f"🔍 Debug: Renaming Date column to Timestamp...")
            df.rename(columns={'Date': 'Timestamp'}, inplace=True)
            
            print(f"🔍 Debug: Setting Timestamp as index...")
            # Set Date as index for time series analysis FIRST
            df.set_index('Timestamp', inplace=True)
            df.sort_index(inplace=True)
            print(f"🔍 Debug: Index set successfully. Shape: {df.shape}")
            
            #choose the columns to use for the analysis
            print(f"🔍 Debug: Selecting loads from columns: {list(df.columns)}")
            self.loads = self.select_loads(df)
            print(f"🔍 Debug: Selected loads: {self.loads}")
            
            self.power_columns = [self.compute_energy.generate_power_column_name(load) for load in self.loads]
            self.energy_columns = [self.compute_energy.generate_consumption_column_name(load) for load in self.loads]
            print(f"🔍 Debug: Power columns: {self.power_columns}")
            print(f"🔍 Debug: Energy columns: {self.energy_columns}")
            
            # Set attributes in ComputeEnergy instance for compatibility
            self.compute_energy.loads = self.loads
            self.compute_energy.energy_columns = self.energy_columns
            self.compute_energy.client_name = self.client_name

            print(f"🔍 Debug: Filtering dataframe to power columns...")
            df = df[self.power_columns]
            print(f"🔍 Debug: Filtered dataframe shape: {df.shape}")

            # NOW add time-based features using the datetime index
            # Ensure 'Date' column is string in 'YYYY-MM-DD' format
            df['Date'] = df.index.strftime('%Y-%m-%d')
            df['Month'] = df.index.month
            df['Year'] = df.index.year
            df['Hour'] = df.index.hour
            df['Day'] = df.index.day
            df['DayOfWeek'] = df.index.dayofweek
            df = self.compute_energy.generate_cut_off_month_column(df, cutoff_day)

            self.compute_energy.analyze_data(df)
            
            # Set last year and month for report naming
            if not df.empty:
                self.last_year = df.index.max().year
                self.last_month = df.index.max().month
                # Also set in ComputeEnergy instance for compatibility
                self.compute_energy.last_year = self.last_year
                self.compute_energy.last_month = self.last_month
            
            return df
        
        except Exception as e:
            self.logger.error(f"❌ Error loading data: {e}")
            raise  # Re-raise the original exception

    def select_loads(self, df):
        """Choose the columns to use for the analysis"""
        loads = [col.replace("[kW]", "").strip() for col in df.columns if '[kW]' in col]
        return loads

    def select_loads_by_level(self, df, df_loads, client, level):
        """Choose the columns to use for the analysis"""
        df_loads = df_loads[df_loads['Client'] == client & df_loads['Level'] <= level]
        loads = df_loads['Load'].unique()
        loads = loads + [load + ' [kW]' for load in loads]
        columns = [col for col in df.columns if col in loads]
        df = df[columns]
        return df

    def generate_single_file_report(self, data_path, loads_summary_path=None, cutoff_day=7, strict=False):
        """Generate report for a single file"""
        try:
            self.logger.info(f"🔌 Generating report for: {data_path}")
            
            # Load and prepare data
            df = self.load_and_prepare_data(data_path, cutoff_day)
            if df is None:
                self.logger.error("❌ Failed to load data")
                return None
                
            # Initialize intervals and alarm levels
            df = self.compute_energy.init_interval_and_alarm_levels(df)
            
            # Select full months
            df = self.compute_energy.select_full_months(df, strict)
            if df is None:
                self.logger.error("⚠️ No complete months found for analysis")
                return None
            
            # Check data completeness
            self.compute_energy.check_data_completeness(df, strict)
            
            # Compute energy
            df = self.compute_energy.compute_energy(df)
            
            # Generate summaries and visualizations
            fig_energy_monthly, fig_energy_daily, summary_energy_monthly_html, summary_energy_daily_html = self.compute_energy.generate_summary_energy(df, cutoff_day)
            generic_summary_html = self.compute_energy.generate_summary(df)
            
            # Generate reports
            self.compute_energy.generate_report(fig_energy_monthly, fig_energy_daily, summary_energy_monthly_html, summary_energy_daily_html, generic_summary_html)
            
            # Generate one-pager report
            onepager_path = self.compute_energy.generate_onepager_report(df, loads_summary_path)
            
            self.logger.info("✅ Report generation completed successfully")
            return onepager_path
            
        except Exception as e:
            self.logger.error(f"❌ Error generating single file report: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_onepager_only(self, data_path, loads_summary_path=None, cutoff_day=7):
        """Generate only the one-pager report without full analysis"""
        try:
            self.logger.info("🔌 Generating One-Pager Report Only")
            
            # Load and prepare data
            df = self.load_and_prepare_data(data_path, cutoff_day)
            if df is None:
                self.logger.error("❌ Failed to load data")
                return None
                
            df = self.compute_energy.init_interval_and_alarm_levels(df)
            
            # For one-pager, use all available data instead of strict month selection
            print(f"🔍 Debug: Using all available data for one-pager. Shape: {df.shape}")
            
            # Compute energy to get the energy columns
            df = self.compute_energy.compute_energy(df)
            
            # Generate one-pager report
            return self.compute_energy.generate_onepager_report(df, loads_summary_path)
            
        except Exception as e:
            self.logger.error(f"❌ Error generating one-pager report: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_reports_for_folder(self, folder_path, loads_summary_path, strict=False):
        """Generate reports for all CSV files in a folder"""
        try:
            self.logger.info(f"🔌 Generating reports for folder: {folder_path}")
            
            # Find all CSV files in the folder
            csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv') and 'Electricity consumption' in f]
            
            if not csv_files:
                self.logger.warning(f"⚠️ No electricity consumption CSV files found in {folder_path}")
                return []
            
            self.logger.info(f"📊 Found {len(csv_files)} CSV files to process")
            
            report_paths = []
            for csv_file in csv_files:
                file_path = os.path.join(folder_path, csv_file)
                self.logger.info(f"📋 Processing: {csv_file}")
                
                # Generate report for this file
                report_path = self.generate_single_file_report(file_path, loads_summary_path, strict=strict)
                if report_path:
                    report_paths.append(report_path)
                    self.logger.info(f"✅ Report generated: {report_path}")
                else:
                    self.logger.error(f"❌ Failed to generate report for: {csv_file}")
            
            self.logger.info(f"✅ Completed processing {len(report_paths)} files")
            return report_paths
            
        except Exception as e:
            self.logger.error(f"❌ Error generating reports for folder: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []


ea = ComputeEnergy()
report_generator = GenerateReport()
