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
                df[col_consumption] = df[col_mean] * df['Interval_minutes'] / 60
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
    

    def get_last_month_data(self, df, selected_load):
        """Get data for the last month for a specific load"""
        try:
            if df.empty:
                return df
            
            # Get the last month from the data
            last_date = df.index.max()
            last_month = last_date.month
            last_year = last_date.year
            
            # Filter data for the last month
            last_month_data = df[(df.index.month == last_month) & (df.index.year == last_year)]
            
            self.logger.debug(f"✅ Last month data extracted: {last_month_data.shape[0]} records for {last_year}-{last_month:02d}")
            return last_month_data
            
        except Exception as e:
            self.logger.error(f"❌ Error getting last month data: {e}")
            return df

    



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
        
    def generate_daily_consumption_chart_html(self, daily_data, selected_load):
        """Generate daily consumption chart for the last month with day of week labels"""
        try:
            if daily_data.empty:
                return "<p>No data available for daily consumption chart.</p>"
            
            load_energy_col = f"{selected_load} - Consumption [kWh]"
            
            if load_energy_col not in daily_data.columns:
                return "<p>Energy consumption data not available for the selected load.</p>"
            
            # Group by day and sum energy consumption
            daily_consumption = daily_data[load_energy_col]
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
                    daily_consumption = temp_df[load_energy_col]
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
                name=f'{selected_load} Daily Consumption',
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

    def generate_monthly_history_chart_html(self, monthly_data, selected_load):
        """Generate monthly history chart using existing draw_energy_kWh_per_month method"""
        try:
            if monthly_data.empty:
                return "<p>No data available for monthly history chart.</p>"
            
            load_energy_col = f"{selected_load} - Consumption [kWh]"
            
            if load_energy_col not in monthly_data.columns:
                return "<p>Energy consumption data not available for the selected load.</p>"
            
            # Group by year-month and sum energy consumption
            monthly_consumption = monthly_data[load_energy_col]
            
            # Create a DataFrame in the format expected by draw_energy_kWh_per_month
            if 'Year-Month-cut-off' not in monthly_data.columns:
                # If we don't have Year-Month-cut-off, try to create it from available columns
                if 'Year' in monthly_data.columns and 'Month' in monthly_data.columns:
                    monthly_data['Year-Month-cut-off'] = monthly_data['Year'].astype(str) + '-' + monthly_data['Month'].astype(str).str.zfill(2)
                else:
                    # If we don't have Year and Month columns, create a simple index-based Year-Month-cut-off
                    monthly_data['Year-Month-cut-off'] = [f"Month-{i+1:02d}" for i in range(len(monthly_data))]
            
            # Use the existing method to generate the chart
            figures = self.draw_energy_kWh_per_month(monthly_data, [selected_load])
            
            if figures and len(figures) > 0:
                # Convert the first figure to HTML
                return pio.to_html(figures[0], full_html=False, include_plotlyjs='cdn')
            else:
                return "<p>Error generating monthly history chart.</p>"
            
        except Exception as e:
            self.logger.error(f"❌ Error generating monthly history chart: {e}")
            return "<p>Error generating monthly history chart.</p>"

    def draw_hourly_consumption_chart_html(self, hourly_data, selected_load):
        """Generate hourly consumption chart"""
        try:
            print(f"🔍 Debug: Hourly data columns: {hourly_data.columns}")
            print(f"🔍 Debug: Hourly data index: {hourly_data.index}")
            if hourly_data.empty:
                return "<p>No data available for hourly consumption chart.</p>"
            selected_column = [col_name for col_name in hourly_data.columns if selected_load in col_name][0]
            hourly_data = hourly_data[selected_column]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=hourly_data.index,
                y=hourly_data.values,
                name=f'{selected_column} Hourly Consumption',
                marker_color=PlotlyStyle.STRATCON_PRIMARY_GREEN,
            ))
            # Apply standard chart configuration
            fig = self.configure_standard_chart_layout(fig, yaxis_title="kWh", height=320, show_legend=False)
            return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        except Exception as e:
            self.logger.error(f"❌ Error generating hourly consumption chart: {e}")
            return "<p>Error generating hourly consumption chart.</p>"

    def draw_days_consumption_chart_html(self, days_data, selected_load):
        """Generate days consumption chart"""
        try:
            print(f"🔍 Debug: Days data columns: {days_data.columns}")
            print(f"🔍 Debug: Days data index: {days_data.index}")
            if days_data.empty:
                return "<p>No data available for days consumption chart.</p>"
            selected_column = [col_name for col_name in days_data.columns if selected_load in col_name][0]
            days_data = days_data[selected_column]
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
        

class GenerateReport:
    """Class responsible for report generation and data preparation"""
    def __init__(self):
        self.logger = ReportLogger()
        self.compute_energy = ComputeEnergy()
        self.draw_charts = DrawCharts()
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

    def generate_onepager_report_values_and_charts(self, data_path, loads_data_path=None, selected_load=None, warning_only=True):
        """Generate a professional one-pager report for a single load similar to the mockup"""
        
        try:
            self.logger.info("🔌 Generating One-Pager Report Only")

            tenant_data = pd.read_csv(loads_data_path)
            tenant_data = tenant_data[tenant_data['load'].str.startswith('Consumption') == False]
            if tenant_data is None:
                self.logger.error("❌ Failed to load tenant data")
                return None
            if 'load' not in tenant_data.columns:
                self.logger.error("❌ Error: 'load' column not found in tenant data")
                raise ValueError("❌ Error: 'load' column not found in tenant data")
            if selected_load is None:
                self.logger.error("❌ Error: selected_load is None")
                raise ValueError("❌ Error: selected_load is None")
            cutoff_day = tenant_data[tenant_data['load'] == (selected_load + ' [kW]')]['cutoff_day'].values[0]
            if cutoff_day is None:
                self.logger.error("❌ Error: 'cutoff_day' column not found in tenant data")
                raise ValueError("❌ Error: 'cutoff_day' column not found in tenant data")
            
            # Load and prepare data
            df = self.load_and_prepare_data(data_path, cutoff_day)
            if df is None:
                self.logger.error("❌ Failed to load data")
                return None
                
            df = self.compute_energy.init_interval_and_alarm_levels(df)

            
            # Select full months
            df = self.compute_energy.select_full_months(df, warning_only)
            list_months = df['Year-Month-cut-off'].unique()
            print('list_months', list_months)
            if df is None:
                raise ValueError("❌ No complete months found for analysis")

            date_range, last_month = self.compute_energy.compute_monthly_date_range(df)

            print('last_month', last_month)
            print('date_range', date_range)
            
            # For one-pager, use all available data instead of strict month selection
            print(f"🔍 Debug: Using all available data for one-pager. Shape: {df.shape}")
            
            # Compute energy to get the energy columns
            df = self.compute_energy.compute_energy(df)

            # Prepare the aggregated tables for analysis - select only energy columns and prepare df_daily, df_hourly and df_monthly for all loads
            df_daily, df_hourly, df_monthly, df_night, df_day, df_weekdays, df_weekends, df_avg_hourly_consumption, df_avg_daily_consumption = self.compute_energy.prepare_aggregated_tables(df, tenant_data)

            # Compute the peak power and always on power for each load
            df_power_analysis = self.compute_energy.compute_peak_power_and_always_on_power(df)

            
            # Get available loads
            energy_columns = [col for col in df.columns if '[kWh]' in col]
            power_columns = [col for col in df.columns if '[kW]' in col]
            # print(f"🔍 Debug: Power columns: {power_columns}")
            # print(f"🔍 Debug: Energy columns: {energy_columns}")
            
            # print(f"🔍 Debug: Available loads: {energy_columns}")
            
            # Select the load to analyze
            try:
                load_energy_col = [col for col in energy_columns if selected_load in col][0]
                load_power_col = [col for col in power_columns if selected_load in col][0]
                # print(f"🔍 Debug: Selected load for analysis: {selected_load}")
                # print(f"🔍 Debug: Selected load energy column: {load_energy_col}")
            except Exception as e:
                self.logger.error(f"❌ Error while selecting load for analysis: {e}")
                raise ValueError(f"❌ Error while selecting load for analysis: {e}")

            ######## compute the KPIs for the selected load
            last_month_energy_consumption = df_monthly[df_monthly['Year-Month-cut-off'] == last_month][load_energy_col].values[0]
            average_monthly_consumption_energy = df_monthly[load_energy_col].mean()

            last_month_co2_emissions = last_month_energy_consumption * CO2_EMISSIONS_PER_KWH

            selected_load_sqm_area, selected_load_energy_per_sqm, selected_load_yearly_average_energy_per_sqm, percentile_position = self.compute_energy.compute_energy_per_sqm_values_and_percentile_position(df_monthly, last_month, load_energy_col)


            # Get last month peak power with error handling
            last_month_peak_power_data = df_power_analysis[df_power_analysis['Year-Month-cut-off'] == last_month]['peak power ' + load_power_col].values
            last_month_peak_power = last_month_peak_power_data[0] if len(last_month_peak_power_data) > 0 else 0
            
            # Get last month always on power with error handling
            last_month_always_on_power_data = df_power_analysis[df_power_analysis['Year-Month-cut-off'] == last_month]['always on power ' + load_power_col].values
            last_month_always_on_power = last_month_always_on_power_data[0] if len(last_month_always_on_power_data) > 0 else 0

            yearly_average_peak_power = df_power_analysis['peak power ' + load_power_col].mean()
            yearly_average_always_on_power = df_power_analysis['always on power ' + load_power_col].mean()

            last_month_weekday_consumption = df_weekdays[df_weekdays['Year-Month-cut-off'] == last_month][load_energy_col].mean()
            yearly_average_weekday_consumption = df_weekdays[load_energy_col].mean()
            last_month_weekend_consumption = df_weekends[df_weekends['Year-Month-cut-off'] == last_month][load_energy_col].mean()
            yearly_average_weekend_consumption = df_weekends[load_energy_col].mean()

            last_month_daytime_consumption = df_day[df_day['Year-Month-cut-off'] == last_month][load_energy_col].mean()
            yearly_average_daytime_consumption = df_day[load_energy_col].mean()
            last_month_nighttime_consumption = df_night[df_night['Year-Month-cut-off'] == last_month][load_energy_col].mean()
            yearly_average_nighttime_consumption = df_night[load_energy_col].mean()

            
            
            # Get date range
            print(f"🔍 Debug: Date range: {date_range}")

            values_for_html = {
                'selected_load': selected_load,
                'selected_load_sqm_area': selected_load_sqm_area,
                'date_range': date_range,
                'last_month_energy_consumption': last_month_energy_consumption,
                'last_month_co2_emissions': last_month_co2_emissions,
                'selected_load_energy_per_sqm': selected_load_energy_per_sqm,
                'selected_load_yearly_average_energy_per_sqm': selected_load_yearly_average_energy_per_sqm,
                'percentile_position': percentile_position,
                'average_monthly_consumption_energy': average_monthly_consumption_energy,
                'last_month_peak_power': last_month_peak_power,
                'last_month_always_on_power': last_month_always_on_power,
                'yearly_average_peak_power': yearly_average_peak_power,
                'yearly_average_always_on_power': yearly_average_always_on_power,
                'last_month_weekday_consumption': last_month_weekday_consumption,
                'yearly_average_weekday_consumption': yearly_average_weekday_consumption,
                'last_month_weekend_consumption': last_month_weekend_consumption,
                'yearly_average_weekend_consumption': yearly_average_weekend_consumption,
                'last_month_daytime_consumption': last_month_daytime_consumption,
                'yearly_average_daytime_consumption': yearly_average_daytime_consumption,
                'last_month_nighttime_consumption': last_month_nighttime_consumption,
                'yearly_average_nighttime_consumption': yearly_average_nighttime_consumption
            }
            # Filter and sort the daily data for the last month
            last_month_daily_data = df_daily[df_daily['Year-Month-cut-off'] == last_month].copy()
            if 'Date' in last_month_daily_data.columns:
                # Convert Date column to datetime and sort
                last_month_daily_data['Date'] = pd.to_datetime(last_month_daily_data['Date'])
                last_month_daily_data = last_month_daily_data.sort_values('Date')

            
            chart_daily_consumption = self.draw_charts.generate_daily_consumption_chart_html(last_month_daily_data, selected_load)
            chart_monthly_history = self.draw_charts.generate_monthly_history_chart_html(df_monthly, selected_load)
            chart_hourly_consumption = self.draw_charts.draw_hourly_consumption_chart_html(df_avg_hourly_consumption, selected_load)
            chart_days_consumption = self.draw_charts.draw_days_consumption_chart_html(df_avg_daily_consumption, selected_load)
            return values_for_html, df, chart_daily_consumption, chart_monthly_history, chart_hourly_consumption, chart_days_consumption
        except Exception as e:
            self.logger.error(f"❌ Error while generating one-pager report values and charts: {e}")
            raise ValueError(f"❌ Error while generating one-pager report values and charts: {e}")
        

    def generate_onepager_html(self, values_for_html, chart_daily_consumption, chart_monthly_history, chart_hourly_consumption, chart_days_consumption):
        try:
            # Generate the one-pager HTML
            selected_load = values_for_html['selected_load']
            selected_load_sqm_area = values_for_html['selected_load_sqm_area']
            date_range = values_for_html['date_range']
            last_month_energy_consumption = values_for_html['last_month_energy_consumption']
            last_month_co2_emissions = values_for_html['last_month_co2_emissions']
            selected_load_energy_per_sqm = values_for_html['selected_load_energy_per_sqm']
            average_monthly_consumption_energy = values_for_html['average_monthly_consumption_energy']
            last_month_peak_power = values_for_html['last_month_peak_power']
            last_month_always_on_power = values_for_html['last_month_always_on_power']
            yearly_average_peak_power = values_for_html['yearly_average_peak_power']
            yearly_average_always_on_power = values_for_html['yearly_average_always_on_power']
            selected_load_yearly_average_energy_per_sqm = values_for_html['selected_load_yearly_average_energy_per_sqm']
            percentile_position = values_for_html['percentile_position']
            last_month_weekday_consumption = values_for_html['last_month_weekday_consumption']
            yearly_average_weekday_consumption = values_for_html['yearly_average_weekday_consumption']
            last_month_weekend_consumption = values_for_html['last_month_weekend_consumption']
            yearly_average_weekend_consumption = values_for_html['yearly_average_weekend_consumption']
            last_month_daytime_consumption = values_for_html['last_month_daytime_consumption']
            yearly_average_daytime_consumption = values_for_html['yearly_average_daytime_consumption']
            last_month_nighttime_consumption = values_for_html['last_month_nighttime_consumption']
            yearly_average_nighttime_consumption = values_for_html['yearly_average_nighttime_consumption']
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{selected_load} - Energy Analysis Report</title>
                {self.generate_onepager_styles()}
            </head>
            <body>
                <div class="container">
                    <!-- Header -->
                    <header class="header">
                        <div class="logo-section">
                            <h1 class="main-title"><span class="subtitle">Client:</span> {selected_load}</h1>
                        </div>
                        <div class="report-info">
                            <div class="logo-container">
                                <img src="{self.get_base64_logo()}" alt="Stratcon Logo" class="stratcon-logo" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                                <div class="logo-fallback" style="display:none;">
                                    <div style="font-size:24px; font-weight:bold; margin-bottom:5px;">STRATCON</div>
                                    <div style="font-size:12px; opacity:0.8;">Energy Analytics</div>
                                </div>
                            </div>
                            <p class="date-range">Billing Period: {date_range}</p>
                            <p class="generated-date">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                        </div>
                    </header>

                    <!-- Key Metrics Section -->
                    <section class="metrics-section">
                        <h2 class="section-title">Energy Analysis Report</h2>
                        
                        <!-- Three Column Layout -->
                        <div class="metrics-three-columns">
                            <!-- Left Column - Single Cell -->
                            <div class="metrics-column">
                                <div class="metric-card main-metric">
                                    <div class="metric-label">Energy Consumption (kWh)</div>
                                    <div class="metric-value">{last_month_energy_consumption:,.0f}</div>
                                    <div class="metric-reference">(Yearly average: {average_monthly_consumption_energy:,.0f} kWh)</div>
                                </div>
                            </div>
                            
                            <!-- Center Column - Two Cells -->
                            <div class="metrics-column">
                                <div class="metric-card">
                                    <div class="metric-label">Peak Power<sup>(1)</sup> (kW)</div>
                                    <div class="metric-value">{last_month_peak_power:.1f}</div>
                                    <div class="metric-reference">(Yearly average: {yearly_average_peak_power:.1f} kWh)</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-label">Always On Power<sup>(1)</sup> (kW)</div>
                                    <div class="metric-value">{last_month_always_on_power:.1f}</div>
                                    <div class="metric-reference">(Yearly average: {yearly_average_always_on_power:.1f} kW)</div>
                                </div>
                            </div>
                            
                            <!-- Right Column - Two Cells -->
                            <div class="metrics-column">
                                <div class="metrics-grid">
                                    <div class="metric-card">
                                        <div class="metric-label">CO₂ Emissions (kg)</div>
                                        <div class="metric-value">{last_month_co2_emissions:,.0f}</div>
                                        
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-label">Energy intensity per sq.m (kWh/m²)</div>
                                        <div class="metric-value">{selected_load_energy_per_sqm:.1f}</div>
                                        <div class="metric-reference">(Yearly average: {selected_load_yearly_average_energy_per_sqm:.1f} kWh/m²)</div>
                                        <div class="metric-reference">(Percentile position: {percentile_position:.1f}%)</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                    </section>

                    <!-- Consumption Chart (Last Month) - Two Thirds One Third Layout -->
                    <section class="chart-section">
                        <div class="one-thirds-two-thirds-layout">
                             <!-- Left Column: Monthly Consumption Chart -->
                            <div class="column-one-third-1-2">
                                <h3 class="subsection-title">Monthly Consumption Chart</h3>
                                <div class="chart-container">
                                    {chart_monthly_history}
                                </div>
                            </div><!-- Right Column: Daily Consumption Chart -->
                            <div class="column-two-thirds-1-2">
                                <h3 class="subsection-title">Daily Consumption Chart</h3>
                                <div class="chart-container">
                                    {chart_daily_consumption}
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Load Analysis Section - Three Column Layout -->
                    <section class="chart-section">
                        <div class="three-column-layout">
                            <!-- Left Column: Load Analysis -->
                            <div class="column-left">
                                <div class="metrics-grid">
                                    <div class="metric-card">
                                        <div class="metric-label">Weekday / Weekend Consumption</div>
                                        <div class="metric-value">{last_month_weekday_consumption:,.0f} / {last_month_weekend_consumption:,.0f}</div>
                                        <div class="metric-reference">(Yearly average: {yearly_average_weekday_consumption:,.0f} / {yearly_average_weekend_consumption:,.0f} kWh)</div>
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-label">Daytime / Nighttime Consumption<sup>(2)</sup> (kWh)</div>
                                        <div class="metric-value">{last_month_daytime_consumption:,.0f} / {last_month_nighttime_consumption:,.0f}</div>
                                        <div class="metric-reference">(Yearly average: {yearly_average_daytime_consumption:,.0f} / {yearly_average_nighttime_consumption:,.0f} kWh)</div>
                                    </div>
                                </div>
                            </div>
                            <!-- Center Column: Load Analysis -->
                            <div class="column-center">
                                <h3 class="subsection-title">Days of the Week Analysis<sup>(3)</sup></h3>
                                <div class="chart-container">
                                    {chart_days_consumption}
                                </div>
                            </div>
                            
                            <!-- Right Column: Load Analysis -->
                            <div class="column-right">
                                <h3 class="subsection-title">Hourly Analysis<sup>(4)</sup></h3>
                                <div class="chart-container">
                                    {chart_hourly_consumption}
                                </div>
                            </div>
                        </div>
                        <p class="footnote"><sup>(1)</sup> Peak power and always on power are calculated based on the highest and lowest 10% of the power values respectively during the last month.</p>
                        <p class="footnote"><sup>(2)</sup> Daytime and nighttime consumption are calculated based on average hourly consumption between 9am and 6pm, and 10pm and 5am respectively during the last month.</p>
                        <p class="footnote"><sup>(3)</sup> Days of the Week Analysis is based on the average consumption of the load for each day of the week during the last month.</p>
                        <p class="footnote"><sup>(4)</sup> Hourly Analysis is based on the average consumption of the load for each hour of the day during weekdays during the last month.</p>
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
            report_path = self.write_onepager_report(html_content, selected_load)
            print(f"🔍 Debug: Report written to: {report_path}")
            self.logger.info("✅ One-pager report generated successfully")
            return report_path
            
        except Exception as e:
            self.logger.error(f"❌ Error generating one-pager report: {e}")
            raise ValueError(f"❌ Error generating one-pager report: {e}")

    def get_base64_logo(self, logo_type="white"):
        """Get the base64 encoded logo for embedding in HTML (Safari-compatible)
        
        Args:
            logo_type (str): Type of logo to use - "white", "black", "full_color", or "brandmark"
        """
        try:
            logo_files = {
                "white": "Stratcon.ph White.png",
                "black": "Stratcon.ph Black.png", 
                "full_color": "Stratcon.ph Full Color3.png",
                "brandmark": "Stratcon Brandmark.png"
            }
            
            logo_filename = logo_files.get(logo_type, "Stratcon.ph White.png")
            logo_path = f"/home/philg/projects/stratcon/resources/logos/{logo_filename}"
            
            if os.path.exists(logo_path):
                import base64
                with open(logo_path, 'rb') as f:
                    logo_data = f.read()
                    base64_logo = base64.b64encode(logo_data).decode('utf-8')
                    
                    # Safari-compatible data URI with explicit MIME type and charset
                    return f"data:image/png;charset=utf-8;base64,{base64_logo}"
            else:
                self.logger.warning(f"⚠️ Logo file not found at: {logo_path}")
                return None
        except Exception as e:
            self.logger.error(f"❌ Error encoding logo: {e}")
            return None
    
    def get_safari_compatible_logo(self, logo_type="white"):
        """Get Safari-compatible logo using alternative approach"""
        try:
            # For Safari, we'll use a fallback approach
            logo_files = {
                "white": "Stratcon.ph White.png",
                "black": "Stratcon.ph Black.png", 
                "full_color": "Stratcon.ph Full Color3.png",
                "brandmark": "Stratcon Brandmark.png"
            }
            
            logo_filename = logo_files.get(logo_type, "Stratcon.ph White.png")
            logo_path = f"/home/philg/projects/stratcon/resources/logos/{logo_filename}"
            
            if os.path.exists(logo_path):
                import base64
                with open(logo_path, 'rb') as f:
                    logo_data = f.read()
                    
                    # Optimize for Safari: smaller chunks, explicit encoding
                    base64_logo = base64.b64encode(logo_data).decode('ascii')  # Use ASCII instead of UTF-8
                    
                    # Safari prefers shorter data URIs, so we'll use the most compatible format
                    return f"data:image/png;base64,{base64_logo}"
            else:
                self.logger.warning(f"⚠️ Logo file not found at: {logo_path}")
                return None
        except Exception as e:
            self.logger.error(f"❌ Error encoding logo for Safari: {e}")
            return None

    def write_onepager_report(self, html_content, selected_load=None):
        """Write the one-pager report to a file"""
        try:
            # Create reports directory if it doesn't exist
            reports_dir = "/home/philg/projects/stratcon/reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename with load name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if selected_load:
                # Clean the load name for filename
                clean_load_name = selected_load.replace(' ', '_').replace('/', '_').replace('[', '').replace(']', '')
                filename = f"onepager_{clean_load_name}_{timestamp}.html"
            else:
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

    def generate_onepager_styles(self):
        """Generate modern CSS styles for the one-pager report"""
        # Import all color constants
        STRATCON_DARK_GREEN = PlotlyStyle.STRATCON_DARK_GREEN
        STRATCON_MEDIUM_GREEN = PlotlyStyle.STRATCON_MEDIUM_GREEN
        STRATCON_PRIMARY_GREEN = PlotlyStyle.STRATCON_PRIMARY_GREEN
        STRATCON_LIGHT_GREEN = PlotlyStyle.STRATCON_LIGHT_GREEN
        STRATCON_YELLOW = PlotlyStyle.STRATCON_YELLOW
        STRATCON_BLACK = PlotlyStyle.STRATCON_BLACK
        STRATCON_DARK_GREY = PlotlyStyle.STRATCON_DARK_GREY
        STRATCON_MEDIUM_GREY = PlotlyStyle.STRATCON_MEDIUM_GREY
        STRATCON_GREY = PlotlyStyle.STRATCON_GREY
        STRATCON_LIGHT_GREY = PlotlyStyle.STRATCON_LIGHT_GREY
        STRATCON_VERY_LIGHT_GREY = PlotlyStyle.STRATCON_VERY_LIGHT_GREY
        
        return f"""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <script>
        // Safari compatibility script
        document.addEventListener('DOMContentLoaded', function() {{
            const logoImg = document.querySelector('.stratcon-logo');
            const logoFallback = document.querySelector('.logo-fallback');
            
            if (logoImg && logoFallback) {{
                // Check if image loaded successfully
                logoImg.addEventListener('load', function() {{
                    logoFallback.style.display = 'none';
                }});
                
                logoImg.addEventListener('error', function() {{
                    this.style.display = 'none';
                    logoFallback.style.display = 'block';
                }});
                
                // Safari-specific: Check if image is actually displayed
                setTimeout(function() {{
                    if (logoImg.naturalWidth === 0 || logoImg.offsetWidth === 0) {{
                        logoImg.style.display = 'none';
                        logoFallback.style.display = 'block';
                    }}
                }}, 100);
            }}
        }});
        </script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, {STRATCON_LIGHT_GREEN} 0%, {STRATCON_PRIMARY_GREEN} 50%, {STRATCON_YELLOW} 100%);
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                min-height: 100vh;
            }}
            
            /* Header */
            .header {{
                background: {STRATCON_DARK_GREEN};
                color: white;
                padding: 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .main-title {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
            }}
            
            .subtitle {{
                font-size: 1.2rem;
                opacity: 0.9;
                font-weight: 300;
            }}
            
            .report-info {{
                text-align: right;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
            }}
            
            .logo-container {{
                margin-bottom: 1rem;
            }}
            
            .stratcon-logo {{
                height: 60px;
                width: auto;
                max-width: 200px;
                object-fit: contain;
                /* Safari compatibility */
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }}
            
            /* Safari fallback for logo */
            .logo-fallback {{
                display: none;
                color: white;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
            }}
            
            /* Show fallback if image fails to load */
            .logo-container:has(img[src=""]) .logo-fallback,
            .logo-container img:not([src]) + .logo-fallback {{
                display: block;
            }}
            
            .date-range {{
                font-size: 1.1rem;
                font-weight: 500;
                margin-bottom: 0.5rem;
            }}
            
            .generated-date {{
                font-size: 0.9rem;
                opacity: 0.8;
            }}
            
            /* Sections */
            .metrics-section, .chart-section {{
                padding: 2rem;
            }}
            
            .section-title {{
                font-size: 1.8rem;
                font-weight: 600;
                color: {STRATCON_DARK_GREY};
                margin-bottom: 1.5rem;
                border-bottom: 3px solid {STRATCON_PRIMARY_GREEN};
                padding-bottom: 0.5rem;
            }}
            
            .subsection-title {{
                font-size: 1.3rem;
                font-weight: 600;
                color: {STRATCON_DARK_GREEN};
                margin-bottom: 1rem;
                border-bottom: 2px solid {STRATCON_LIGHT_GREEN};
                padding-bottom: 0.3rem;
            }}
            
            .subsection-title sup {{
                font-size: 0.7em;
                color: {STRATCON_MEDIUM_GREY};
                font-weight: 500;
                margin-left: 2px;
            }}
            
            /* Metrics Grid */
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            
            /* Three Column Layout */
            .metrics-three-columns {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }}
            
            /* Two Column Layout */
            .two-column-layout {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }}
            
            /* Two-Thirds One-Third Layout */
            .two-thirds-one-third-layout {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }}
            
            /*  One-Third Two-Thirds Layout */
            .one-thirds-two-thirds-layout {{
                display: grid;
                grid-template-columns: 1fr 2fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }}

            /* Three Column Layout */
            .three-column-layout {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 2rem;
                margin-bottom: 2rem;
            }}
            
            .column-left, .column-right {{
                display: flex;
                flex-direction: column;
            }}
            
            .column-center {{
                display: flex;
                flex-direction: column;
            }}
            
            .column-two-thirds-2-1, .column-one-third-2-1 {{
                display: flex;
                flex-direction: column;
            }}

            .column-one-third-1-2, .column-two-thirds-1-2 {{
                display: flex;
                flex-direction: column;
            }}
            
            .metrics-column {{
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
            }}
            
            .metric-card {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 1.5rem;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-left: 4px solid {STRATCON_PRIMARY_GREEN};
            }}
            
            .metric-card.main-metric {{
                background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%);
                border-left: 4px solid {STRATCON_DARK_GREEN};
                transform: scale(1.05);
            }}
            
            .metric-value {{
                font-size: 2.5rem;
                font-weight: 700;
                color: {STRATCON_DARK_GREY};
                margin-bottom: 0.25rem;
            }}
            
            .metric-reference {{
                font-size: 0.8rem;
                color: {STRATCON_GREY};
                font-weight: 400;
                margin-bottom: 0.5rem;
                font-style: italic;
            }}
            
            .footnote {{
                font-size: 0.8rem;
                color: {STRATCON_GREY};
                font-weight: 400;
            }}
            
            .metric-label {{
                font-size: 0.9rem;
                color: {STRATCON_MEDIUM_GREY};
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .metric-label sup {{
                font-size: 0.6em;
                color: {STRATCON_MEDIUM_GREY};
                font-weight: 400;
                margin-left: 1px;
            }}
            
            /* Tenant Summary */
            .tenant-summary {{
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 8px;
                margin-bottom: 2rem;
            }}
            
            .tenant-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
            }}
            
            .tenant-item {{
                background: white;
                padding: 1rem;
                border-radius: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .tenant-name {{
                font-weight: 600;
                color: {STRATCON_DARK_GREY};
                margin-bottom: 0.25rem;
            }}
            
            .tenant-details {{
                font-size: 0.85rem;
                color: {STRATCON_MEDIUM_GREY};
            }}
            
            /* Chart Container */
            .chart-container {{
                background: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            
            /* Placeholder Chart */
            .placeholder-chart {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border: 2px dashed {STRATCON_VERY_LIGHT_GREY};
                border-radius: 8px;
                padding: 3rem 2rem;
                text-align: center;
                color: {STRATCON_LIGHT_GREY};
                min-height: 300px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}
            
            .placeholder-chart p {{
                margin-bottom: 0.5rem;
                font-size: 1.1rem;
                font-weight: 500;
            }}
            
            .placeholder-note {{
                font-size: 0.9rem;
                font-style: italic;
                opacity: 0.8;
            }}
            
            /* Footer */
            .footer {{
                background: {STRATCON_DARK_GREEN};
                color: white;
                padding: 1.5rem 2rem;
                text-align: center;
            }}
            
            .footer-content p {{
                margin-bottom: 0.5rem;
                opacity: 0.9;
            }}
            
            /* Responsive */
            @media (max-width: 768px) {{
                .header {{
                    flex-direction: column;
                    text-align: center;
                }}
                
                .two-column-layout {{
                    grid-template-columns: 1fr;
                    gap: 1.5rem;
                }}
                
                .two-thirds-one-third-layout {{
                    grid-template-columns: 1fr;
                    gap: 1.5rem;
                }}
                
                .three-column-layout {{
                    grid-template-columns: 1fr;
                    gap: 1.5rem;
                }}
                
                .report-info {{
                    align-items: center;
                    margin-top: 1rem;
                }}
                
                .stratcon-logo {{
                    height: 50px;
                }}
                
                .main-title {{
                    font-size: 2rem;
                }}
                
                .metrics-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .metrics-three-columns {{
                    grid-template-columns: 1fr;
                    gap: 1.5rem;
                }}
                
                .metrics-column {{
                    gap: 1rem;
                }}
                
                .container {{
                    margin: 0;
                }}
            }}
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
