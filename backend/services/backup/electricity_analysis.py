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
import pytz
from config import ReportStyle, PlotlyStyle




MAX_MISSING_DAYS_PER_MONTH = 5
MAX_CONSECUTIVE_MISSING_TIMESTAMPS = 2
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR = .20
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY = .05
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH = .01

WEEKDAYS = [0, 1, 2, 3, 4]
HOURS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
NIGHT_HOURS = [22, 23, 0, 1, 2, 3,4,5]
DAY_HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17]


CO2_EMISSIONS_PER_KWH = 0.038 # kgCO2e/kWh

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
        self.client_name: Optional[str] = None


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

    def generate_cut_off(self, date, cutoff_datetime):
        """
        Generate cutoff month for a single date/datetime with timezone support.
        
        Args:
            date: datetime object (can be naive or timezone-aware)
            cutoff_datetime: datetime object with time and timezone info for cutoff
        
        Returns:
            str: Year-Month string in format "YYYY-MM"
        """
        # Convert to Philippines timezone if not already timezone-aware
        philippines_tz = pytz.timezone('Asia/Manila')
        
        if date.tzinfo is None:
            # If naive datetime, assume it's already in Philippines timezone
            date_ph = philippines_tz.localize(date)
        else:
            # If timezone-aware, convert to Philippines timezone
            date_ph = date.astimezone(philippines_tz)
        
        # Convert cutoff_datetime to Philippines timezone if needed
        if cutoff_datetime.tzinfo is None:
            cutoff_ph = philippines_tz.localize(cutoff_datetime)
        else:
            cutoff_ph = cutoff_datetime.astimezone(philippines_tz)
        
        # Extract date and time components
        date_day = date_ph.day
        date_month = date_ph.month
        date_year = date_ph.year
        
        cutoff_day = cutoff_ph.day
        cutoff_month = cutoff_ph.month
        cutoff_year = cutoff_ph.year
        
        # Create a comparison datetime for the current month's cutoff
        current_month_cutoff = philippines_tz.localize(
            datetime(date_year, date_month, cutoff_day, 
                    cutoff_ph.hour, cutoff_ph.minute, cutoff_ph.second)
        )
        
        # Compare the input date with the cutoff datetime
        if date_ph < current_month_cutoff:
            # Date is before the cutoff, belongs to previous month
            if date_month == 1:
                result_month = 12
                result_year = date_year - 1
            else:
                result_month = date_month - 1
                result_year = date_year
        else:
            # Date is on or after the cutoff, belongs to current month
            result_month = date_month
            result_year = date_year
            
        return f"{result_year}-{result_month:02d}"
    
    def _create_cutoff_datetime(self, cutoff_day, hour=23, minute=59, second=59):
        """
        Helper method to create a cutoff datetime from an integer day.
        This maintains backward compatibility with the old cutoff_day integer approach.
        
        Args:
            cutoff_day: int, day of the month (1-31)
            hour: int, hour for cutoff time (default: 23)
            minute: int, minute for cutoff time (default: 59) 
            second: int, second for cutoff time (default: 59)
            
        Returns:
            datetime: datetime object with Philippines timezone
        """
        philippines_tz = pytz.timezone('Asia/Manila')
        # Create a datetime for the cutoff day in the current month
        # The actual month/year doesn't matter as we'll use the day and time components
        cutoff_datetime = datetime(2024, 1, cutoff_day, hour, minute, second)
        return philippines_tz.localize(cutoff_datetime)

    def generate_cut_off_month_column(self, df, cutoff_datetime):
        """
        Generate month-year labels based on a cutoff datetime for rolling months.
        
        Args:
            df: pandas DataFrame with DatetimeIndex
            cutoff_datetime: datetime object with time and timezone info for cutoff
            
        Returns:
            pandas.DataFrame: DataFrame with added 'Year-Month-cut-off' column
            
        Example:
            If cutoff_datetime = datetime(2025, 4, 14, 23, 59, 59):
            - April 13, 2025 23:00 -> "2025-03"
            - April 14, 2025 23:58 -> "2025-03" 
            - April 14, 2025 23:59 -> "2025-04"
            - April 15, 2025 00:00 -> "2025-04"
        """
        try:
            # Convert DatetimeIndex to Series to use apply
            cutoff_series = pd.Series(df.index).apply(lambda x: self.generate_cut_off(x, cutoff_datetime))
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

            # Heatmap of consumption by hour and day\
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

            
    def compute_energy(self,df):
        """Compute energy consumption with quality safeguards"""
        try:
            # 1. Compute the mean power consumption per interval defined as the difference between the present row and following row
            for load in self.loads:
                col_mean = f'Mean_{load}_per_interval [kW]'
                col_production = self.generate_power_column_name(load)
                col_consumption = self.generate_consumption_column_name(load)
                df[col_mean] = df[col_production].rolling(window=2).mean().shift(-1)
                df[col_consumption] = df[col_mean] * df['interval_minutes'] / 60
            if 'Production' in self.loads:
                df['Ratio_of_power_generated_by_the_solar_panels'] = df['Energy_production_per_interval [kWh]'] / df['Energy_consumption_per_interval [kWh]']
            return df
        except Exception as e:
            self.logger.error(f"❌ Error while computing energy: {e}")
            raise ValueError(f"❌ Error while computing energy: {e}")


    def prepare_aggregated_tables(self, df, tenant_data):
        """Prepare aggregated tables for analysis"""
        try:
            self.logger.debug(f"🔍 DEBUG prepare_aggregated_tables: Starting with df shape={df.shape}")
            self.logger.debug(f"🔍 DEBUG prepare_aggregated_tables: DataFrame columns: {list(df.columns)}")

            #Select only date and energy columns
            date_columns = ['Date', 'Month', 'Year', 'Hour', 'Day', 'DayOfWeek', 'Year-Month-cut-off']
            energy_columns = [col for col in df.columns if 'Consumption [kWh]' in col]
            df = df[date_columns + energy_columns]


            df_daily = df.groupby(['Year-Month-cut-off','Day','DayOfWeek', 'Date'])[energy_columns].sum().reset_index()
            df_daily['Date'] = pd.to_datetime(df_daily['Date'])
            df_daily.sort_values(by='Date', ascending=True, inplace=True)
            
            df_hourly = df.groupby(['Year-Month-cut-off','Day','Hour','DayOfWeek', 'Date'])[energy_columns].sum().reset_index()
            df_hourly['Date'] = pd.to_datetime(df_hourly['Date'])
            df_hourly.sort_values(by='Date', ascending=True, inplace=True)
            
            df_monthly = df.groupby(['Year-Month-cut-off'])[energy_columns].sum().reset_index()
            
            # Debug: Log the column names to verify they're preserved
            self.logger.debug(f"🔍 DEBUG df_daily columns: {list(df_daily.columns)}")
            self.logger.debug(f"🔍 DEBUG df_hourly columns: {list(df_hourly.columns)}")
            self.logger.debug(f"🔍 DEBUG df_monthly columns: {list(df_monthly.columns)}")

            
            df_night = df_hourly[df_hourly['Hour'].isin(NIGHT_HOURS)]
            print('df_night.head()', df_night.head())
            df_day = df_hourly[df_hourly['Hour'].isin(DAY_HOURS)]
            print('df_day.head()', df_day.head())
            df_weekdays = df_daily[df_daily['DayOfWeek'].isin(WEEKDAYS)]
            print('df_weekdays.head()', df_weekdays.head())
            df_weekends = df_daily[~df_daily['DayOfWeek'].isin(WEEKDAYS)]
            print('df_weekends.head()', df_weekends.head())

            df_avg_hourly_consumption = self.compute_avg_hourly_consumption(df_hourly)
            
            df_avg_daily_consumption = self.compute_avg_daily_consumption(df_daily)
            
            df_monthly = self.compute_energy_per_sqm(df_monthly, tenant_data) #add the energy per sqm column for all the loads
            


            return df_daily, df_hourly, df_monthly, df_night, df_day, df_weekdays, df_weekends, df_avg_hourly_consumption, df_avg_daily_consumption

        except Exception as e:
            self.logger.error(f"❌ Error while preparing aggregated tables: {e}")
            raise ValueError(f"❌ Error while preparing aggregated tables: {e}")


    def select_last_month_with_cutoff_day(self, df):
        """Select the last month with the cutoff day"""
        try:
            df['Year-Month-digit'] = df['Year-Month-cut-off'].apply(lambda x: int(x.replace('-', '')))
            last_month = df['Year-Month-digit'].max()
            df = df[df['Year-Month-digit'] == last_month]
            return df
        except Exception as e:
            self.logger.error(f"❌ Error while selecting last month with cutoff day: {e}")
            raise ValueError(f"❌ Error while selecting last month with cutoff day: {e}")


    def compute_monthly_date_range(self, df):
        """Compute the date range for the monthly data"""
        try:
            df_last_month = self.select_last_month_with_cutoff_day(df)
            last_month = df_last_month['Year-Month-cut-off'].values[0]
            date_range = df_last_month.index.min().strftime('%B %d, %Y') + ' - ' + df_last_month.index.max().strftime('%B %d, %Y')
            return date_range, last_month
        except Exception as e:
            self.logger.error(f"❌ Error while computing monthly date range: {e}")
            raise ValueError(f"❌ Error while computing monthly date range: {e}")


    def compute_avg_hourly_consumption(self, df_hourly):
        """Compute average hourly consumption"""
        try:
            #seggregate by weekdays
            df = df_hourly[df_hourly['DayOfWeek'].isin(WEEKDAYS)]
            #select only the last month
            df = self.select_last_month_with_cutoff_day(df)
            #compute the average hourly consumption
            df_avg_hourly_consumption = df.groupby(['Hour'])[self.energy_columns].mean()
            return df_avg_hourly_consumption

        except Exception as e:
            self.logger.error(f"❌ Error while preparing aggregated tables: {e}")
            raise ValueError(f"❌ Error while preparing aggregated tables: {e}")


    def compute_avg_daily_consumption(self, df_daily):
        """Compute average daily consumption"""
        try:
            
            df = self.select_last_month_with_cutoff_day(df_daily)
            df_avg_daily_consumption = df.groupby(['DayOfWeek'])[self.energy_columns].mean()
            #remap the index to the day of the week
            df_avg_daily_consumption.index = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
            return df_avg_daily_consumption
        except Exception as e:
            self.logger.error(f"❌ Error while computing average daily consumption: {e}")
            raise ValueError(f"❌ Error while computing average daily consumption: {e}")


    def compute_energy_per_sqm(self, df_monthly, tenant_data):
        """Compute energy per sqm"""
        try:
            energy_columns = [col for col in df_monthly.columns if '[kWh]' in col and col.startswith('Consumption') == False]
            sqm_values = {row['load']: row['floor_area'] for _, row in tenant_data.iterrows() if len([i for i in energy_columns if row['load'].replace(' [kW]', '') in i]) > 0 }
            print('debug sqm_values', sqm_values)
            df_energy_per_sqm = df_monthly.copy()
            for column in energy_columns:
                sqm_key = [k for k in sqm_values.keys() if k.replace(' [kW]', '') in column][0] if len([k for k in sqm_values.keys() if k.replace(' [kW]', '') in column]) > 0 else None
                if sqm_key is None:
                    df_energy_per_sqm[column + ' sqm_area'] = None
                    df_energy_per_sqm[column + ' per sqm'] = None
                    continue
                df_energy_per_sqm[column + ' sqm_area'] = sqm_values[sqm_key]
                df_energy_per_sqm[column + ' per sqm'] = df_energy_per_sqm[column] / sqm_values[sqm_key]
            print('debug df_energy_per_sqm', df_energy_per_sqm.head())
            return df_energy_per_sqm
        except Exception as e:
            self.logger.error(f"❌ Error while computing energy per sqm: {e}")
            raise ValueError(f"❌ Error while computing energy per sqm: {e}")


    def generate_summary_energy(self,data, cutoff_day):
        """Generate summary of energy consumption"""
        try:
            self.logger.debug(f"col_energy_consumption: {self.energy_columns}")
    
            # 1. Monthly summary
            month_data = data.groupby(['Year-Month-cut-off'])[self.energy_columns].sum()
            
            # Get the last month data
            cutoff_datetime = self._create_cutoff_datetime(cutoff_day)
            last_month = self.generate_cut_off(data.index.max(), cutoff_datetime) # get the last month based on the cutoff day inside the data
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


    def compute_peak_power_and_always_on_power(self, df):
        """Compute peak power and always on power
        We define the peak power as the average power of the highest 10% of the power values
        We define the always on power as the average power of the lowest 10% of the power values
        We generate a dataframe with the peak power and always on power for each month for each load (power column)
        We return the dataframe
        """
        power_columns = [col for col in df.columns if '[kW]' in col]
        print('compute_peak_power_and_always_on_power : power_columns', power_columns)
        print('df[Year-Month-cut-off].unique()', df['Year-Month-cut-off'].unique())
        list_df =[]
        power_analysis ={}
        try:
            for col in power_columns:
                for month in df['Year-Month-cut-off'].unique():
                    df_month = df[df['Year-Month-cut-off'] == month]
                    month_dic = {}
                    for col in power_columns:
                        power_values = df_month[col].values
                        power_values.sort()
                        # remove 0, negative and nan values
                        power_values = power_values[power_values > 0]
                        power_values = power_values[~np.isnan(power_values)]
                        peak_power = np.mean(power_values[-int(len(power_values) * 0.1):])
                        always_on_power = np.mean(power_values[:int(len(power_values) * 0.1)])
                        month_dic['peak power ' + col] = peak_power
                        month_dic['always on power ' + col] = always_on_power
                    month_dic['Year-Month-cut-off'] = month
                    list_df.append(month_dic)
            df_power_analysis = pd.DataFrame(list_df)
            return df_power_analysis
        except Exception as e:
            self.logger.error(f"❌ Error while computing peak power and always on power: {e}")
            raise ValueError(f"❌ Error while computing peak power and always on power: {e}")


    def compute_energy_per_sqm_values_and_percentile_position(self, df_monthly, last_month, load_energy_col):
        """Compute energy per sqm values and percentile position"""
        selected_load_sqm_area = df_monthly[load_energy_col + ' sqm_area'].iloc[0]
        columns_energy_per_sqm = [col for col in df_monthly.columns if 'per sqm' in col]
        
        # Get the energy per sqm value for the specific load in the last month
        selected_load_energy_per_sqm = df_monthly[df_monthly['Year-Month-cut-off'] == last_month][load_energy_col + ' per sqm'].iloc[0]
        selected_load_yearly_average_energy_per_sqm = df_monthly[load_energy_col + ' per sqm'].mean()
        
        # Get all energy per sqm values for the last month (flatten the 2D array)
        energy_per_sqm_values = df_monthly[df_monthly['Year-Month-cut-off'] == last_month][columns_energy_per_sqm].values.flatten()
        
        # Remove NaN values
        energy_per_sqm_values = energy_per_sqm_values[~np.isnan(energy_per_sqm_values)]

        #remove 0 values
        energy_per_sqm_values = energy_per_sqm_values[energy_per_sqm_values > 0]
        
        # Sort the values in descending order
        energy_per_sqm_values = np.sort(energy_per_sqm_values)[::-1]
        
        # Find the rank of the selected load (0-based index)
        rank = np.where(energy_per_sqm_values == selected_load_energy_per_sqm)[0]
        if len(rank) > 0:
            rank = rank[0]
        else:
            # If exact match not found, find the closest value
            rank = np.argmin(np.abs(energy_per_sqm_values - selected_load_energy_per_sqm))
        
        # Compute the percentile position
        percentile_position = int(rank / len(energy_per_sqm_values) * 100)
        
        return selected_load_sqm_area, selected_load_energy_per_sqm, selected_load_yearly_average_energy_per_sqm, percentile_position

    
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
            if "interval_minutes" not in df.columns:
                df['interval_minutes'] = df.index.diff() / np.timedelta64(1, 'm')
            self.interval_minutes = round(df['interval_minutes'].mean(),0)
            self.timestamps_per_hour = round(60 / self.interval_minutes)
            df['Nb_of_intervals_between_timestamps'] = df['interval_minutes'] / self.interval_minutes
            df['Missing_timestamps_after_timestamp'] = df['Nb_of_intervals_between_timestamps'] - 1
            self.max_missing_timestamps_per_hour = np.ceil(self.timestamps_per_hour * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR)
            self.max_missing_timestamps_per_day = np.ceil(self.timestamps_per_hour * 24 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY)
            self.max_missing_timestamps_per_month = np.ceil(self.timestamps_per_hour * 24 * 30 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH)

            self.logger.debug(f"✅ Interval minutes: {self.interval_minutes}")
            self.logger.debug(f"✅ timestamps per hour: {self.timestamps_per_hour}")
            self.logger.debug(f"✅ Max missing timestamps per hour: {self.max_missing_timestamps_per_hour}")
            self.logger.debug(f"✅ Max missing timestamps per day: {self.max_missing_timestamps_per_day}")
            self.logger.debug(f"✅ Max missing timestamps per month: {self.max_missing_timestamps_per_month}")

            return df
        except Exception as e:
            self.logger.error(f"❌ Error while initializing interval and alarm levels: {e}")
            raise ValueError(f"❌ Error while initializing interval and alarm levels: {e}")
    

    

class DrawCharts:
    """Class responsible for generating graphs"""
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
    
    def add_yaxis_title_annotation(self, title="kWh"):
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
    
    def configure_standard_chart_layout(self, fig, yaxis_title="kWh", height=320, show_legend=False):
        """Helper function to apply standard chart configuration"""
        fig.update_yaxes(tickformat=",.0f")
        fig.update_layout(
            height=height,
            showlegend=show_legend,
            template="plotly_white",
            margin=dict(l=25, r=25, t=30, b=30),
            annotations=self.add_yaxis_title_annotation(yaxis_title),
            font=dict(size=12),
            title_font=dict(size=16)
        )
        fig.update_xaxes(type='category')
        return fig

    def draw_energy_kWh_per_month(self, month_data, loads_list):
        try:
            """Draw bar charts of the energy consumption and import/export per month"""
            self.logger.info("\n=== DRAWING ENERGY PER MONTH ===")
            self.logger.info(month_data)
            
            # Check if we have both consumption and production data
            has_consumption = any("Consumption" in load for load in loads_list)
            has_production = any("Production" in load for load in loads_list)
            
            if has_consumption and has_production:
                fig = self.draw_energy_kWh_per_month_production(month_data)
                return fig
            else:
                # Reset index to make it a regular DataFrame
                month_data_reset = month_data.reset_index()
                self.logger.debug(f"month_data_reset columns: {month_data_reset.columns}")
                
                
                #create a new plot for each load
                columns = []
                for col in month_data.columns:
                    for load in loads_list:
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
                        go.Bar(x=month_data_reset['Year-Month-cut-off'], y=month_data_reset[col],
                            name=load, marker_color=PlotlyStyle.STRATCON_DARK_GREEN,
                            text=[f"{val:,.0f}" for val in month_data_reset[col]],
                            textposition='outside')
                    )
                    
                    # Apply standard chart configuration
                    fig = self.configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
                    
                    # Save individual figure
                    fig.write_html(f"energy_consumption_{load.replace(' ', '_').replace('/', '_')}_per_month.html")
                    # fig.show()  # Commented out to prevent HTML output in terminal
                    
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
        # Check if we have both consumption and production data
        has_consumption = any("Consumption" in load for load in self.loads)
        has_production = any("Production" in load for load in self.loads)
        
        if has_consumption and has_production:
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
                        # title=f'Energy Analysis per Day - {load}',
                        height=320,
                        showlegend=True,
                        font=PlotlyStyle.update_font,
                        title_font=PlotlyStyle.update_title_font,
                        margin=dict(l=25, r=25, t=80, b=50),
                        annotations=[
                            dict(
                                text="kWh",
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
                    )
                    fig.update_xaxes(type='category')
                    
                    # Save individual figure
                    fig.write_html(f"energy_consumption_{load.replace(' ', '_').replace('/', '_')}_per_day.html")
                    # fig.show()  # Commented out to prevent HTML output in terminal
                    
                    figures.append(fig)
                    self.logger.debug(f"✅ Energy per day plot generated for {load}")
                
                self.logger.debug(f"✅ All {len(figures)} energy per day plots generated and shown")
                return figures
            except Exception as e:
                self.logger.error(f"❌ Error while drawing energy per day: {e}")
                raise ValueError(f"❌ Error while drawing energy per day: {e}")

    def draw_energy_kWh_per_month_production(self, month_data):
        try:
            """Draw bar charts of the energy consumption and import/export per month"""
            self.logger.info("\n=== DRAWING ENERGY PER MONTH ===")
            self.logger.info(month_data)
            
            # Check if we have both consumption and production data
            has_consumption = any("Consumption" in load for load in self.loads)
            has_production = any("Production" in load for load in self.loads)
            
            if has_consumption and has_production:
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
                # fig.show()  # Commented out to prevent HTML output in terminal
                self.logger.debug(f"✅ Energy per month plot shown")
                return fig
        except Exception as e:
            self.logger.error(f"❌ Error while drawing energy per month: {e}")
            raise ValueError(f"❌ Error while drawing energy per month: {e}")
        
    def generate_daily_consumption_chart_html(self, daily_data):
        """Generate daily consumption chart for the last month with day of week labels"""
        try:
            if daily_data.empty:
                return "<p>No data available for daily consumption chart.</p>"
            
            # Group by day and sum energy consumption
            daily_consumption = daily_data["consumption_kWh"]
            if 'Date' in daily_data.columns:
                # Handle different date formats in the Date column
                date_labels = []
                for date_val in daily_data['Date']:
                    try:
                        # If it's already a datetime object
                        if hasattr(date_val, 'strftime'):
                            date_str = date_val.strftime('%a-%m-%d')
                        else:
                            # If it's a string, convert to datetime first
                            date_obj = pd.to_datetime(date_val)
                            date_str = date_obj.strftime('%a-%m-%d')
                        date_labels.append(date_str)
                    except Exception as e:
                        # Fallback: use the original value or create a simple label
                        self.logger.warning(f"Could not format date {date_val}: {e}")
                        date_labels.append(str(date_val))
                
                # Ensure the data is sorted by date (should already be sorted, but just in case)
                if len(date_labels) > 1:
                    # Create a temporary dataframe to sort by date
                    temp_df = daily_data.copy()
                    temp_df['date_labels'] = date_labels
                    temp_df = temp_df.sort_values('Date')
                    date_labels = temp_df['date_labels'].tolist()
                    daily_consumption = temp_df["consumption_kWh"]
            elif hasattr(daily_consumption.index, 'strftime'):
                # It's already a datetime index
                date_labels = []
                for date in daily_consumption.index:
                    date_str = date.strftime('%a-%m-%d')
                    date_labels.append(date_str)
            else:
                # Fallback: create simple day labels
                date_labels = [f"Day-{i+1:02d}" for i in range(len(daily_consumption))]
                self.logger.warning("No Date column found, using fallback day labels")
            
            # Debug: Print the raw data
            self.logger.debug(f"Daily consumption index: {daily_consumption.index}")
            self.logger.debug(f"Daily consumption values: {daily_consumption.values}")
            if 'Date' in daily_data.columns:
                self.logger.debug(f"Date column sample: {daily_data['Date'].head().tolist()}")
                self.logger.debug(f"Date column types: {daily_data['Date'].dtype}")
        
            
            # Debug: Print the date labels to verify formatting
            self.logger.debug(f"Date labels: {date_labels}")
            
            # Create the chart
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
            
            # Apply standard chart configuration
            fig = self.configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
            
            # Configure x-axis to use our custom labels
            fig.update_xaxes(
                tickangle=45,
                type='category',  # Ensure it treats x-axis as categories, not dates
                tickmode='array',
                tickvals=date_labels,
                ticktext=date_labels
            )
            
            return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
            
        except Exception as e:
            self.logger.error(f"❌ Error generating daily consumption chart: {e}")
            return "<p>Error generating daily consumption chart.</p>"

    def generate_monthly_history_chart_html(self, monthly_data):
        """Generate monthly history chart using existing draw_energy_kWh_per_month method"""
        try:
            if monthly_data.empty:
                return "<p>No data available for monthly history chart.</p>"
            
           
            
            # Group by year-month and sum energy consumption
            monthly_consumption = monthly_data["consumption_kWh"]
            
            # Create a DataFrame in the format expected by draw_energy_kWh_per_month
            if 'Year-Month-cut-off' not in monthly_data.columns:
                # If we don't have Year-Month-cut-off, try to create it from available columns
                if 'Year' in monthly_data.columns and 'Month' in monthly_data.columns:
                    monthly_data['Year-Month-cut-off'] = monthly_data['Year'].astype(str) + '-' + monthly_data['Month'].astype(str).str.zfill(2)
                else:
                    # If we don't have Year and Month columns, create a simple index-based Year-Month-cut-off
                    monthly_data['Year-Month-cut-off'] = [f"Month-{i+1:02d}" for i in range(len(monthly_data))]
            
            # Use the existing method to generate the chart
            figures = self.draw_energy_kWh_per_month(monthly_data, ["consumption_kWh"])
            
            if figures and len(figures) > 0:
                # Convert the first figure to HTML
                return pio.to_html(figures[0], full_html=False, include_plotlyjs='cdn')
            else:
                return "<p>Error generating monthly history chart.</p>"
            
        except Exception as e:
            self.logger.error(f"❌ Error generating monthly history chart: {e}")
            return "<p>Error generating monthly history chart.</p>"

    def draw_hourly_consumption_chart_html(self, hourly_data):
        """Generate hourly consumption chart"""
        try:
            print(f"🔍 Debug: Hourly data columns: {hourly_data.columns}")
            print(f"🔍 Debug: Hourly data index: {hourly_data.index}")
            if hourly_data.empty:
                return "<p>No data available for hourly consumption chart.</p>"

            hourly_data = hourly_data["consumption_kWh"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=hourly_data.index,
                y=hourly_data.values,
                name=f'Hourly Consumption - kWh',
                marker_color=PlotlyStyle.STRATCON_PRIMARY_GREEN,
            ))
            # Apply standard chart configuration
            fig = self.configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
            return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        except Exception as e:
            self.logger.error(f"❌ Error generating hourly consumption chart: {e}")
            return "<p>Error generating hourly consumption chart.</p>"

    def draw_days_consumption_chart_html(self, days_data):
        """Generate days consumption chart"""
        try:
            print(f"🔍 Debug: Days data columns: {days_data.columns}")
            print(f"🔍 Debug: Days data index: {days_data.index}")
            if days_data.empty:
                return "<p>No data available for days consumption chart.</p>"
            days_data = days_data["consumption_kWh"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=days_data.index,
                y=days_data.values,
                name=f'{selected_column} Days Consumption',
                marker_color=PlotlyStyle.STRATCON_PRIMARY_GREEN,
            ))
            # Apply standard chart configuration
            fig = self.configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
            return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')  
        except Exception as e:
            self.logger.error(f"❌ Error generating days consumption chart: {e}")
            return "<p>Error generating days consumption chart.</p>"
 