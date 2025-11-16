#!/usr/bin/env python3
"""
DataFrame Preparer - Handles DataFrame transformations and preparations
"""
import pandas as pd
import numpy as np
from calendar import monthrange
from datetime import datetime
from typing import Optional, Tuple
from backend.services.core.config import (
    PHILIPPINES_TZ,
    MAX_MISSING_DAYS_PER_MONTH,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH,
)
from backend.services.core.utils import ReportLogger, raise_with_context


class DataFramePreparer:
    """
    Centralized class for preparing and transforming DataFrames.
    
    This class handles:
    - Adding time-based features
    - Initializing interval calculations
    - Selecting complete months
    - Computing date ranges
    """
    
    def __init__(self, logger: Optional[ReportLogger] = None):
        """Initialize DataFramePreparer with optional logger."""
        self.logger = logger if logger is not None else ReportLogger()
    
    @staticmethod
    def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add time-based features to DataFrame.
        
        Args:
            df: DataFrame with DatetimeIndex
            
        Returns:
            DataFrame with added time features (Date, Month, Year, Hour, Day, DayOfWeek)
        """
        df = df.copy()
        df['Date'] = df.index.strftime('%Y-%m-%d')
        df['Month'] = df.index.month
        df['Year'] = df.index.year
        df['Hour'] = df.index.hour
        df['Day'] = df.index.day
        df['DayOfWeek'] = df.index.dayofweek
        return df
    

    
    def init_interval_and_alarm_levels(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, float, float, float, float]:
        """
        Initialize interval calculations and alarm thresholds.
        
        Args:
            df: DataFrame with time series data
            
        Returns:
            Tuple of (df, interval_minutes, max_per_hour, max_per_day, max_per_month)
        """
        try:
            df = df.copy()
            if "interval_minutes" not in df.columns:
                df['interval_minutes'] = df.index.diff() / np.timedelta64(1, 'm')
            
            interval_minutes = round(df['interval_minutes'].mean(), 0)
            timestamps_per_hour = round(60 / interval_minutes)
            
            df['Nb_of_intervals_between_timestamps'] = df['interval_minutes'] / interval_minutes
            df['Missing_timestamps_after_timestamp'] = df['Nb_of_intervals_between_timestamps'] - 1
            
            max_missing_per_hour = np.ceil(timestamps_per_hour * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR)
            max_missing_per_day = np.ceil(timestamps_per_hour * 24 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY)
            max_missing_per_month = np.ceil(timestamps_per_hour * 24 * 30 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH)
            
            self.logger.debug(f"✅ Interval minutes: {interval_minutes}")
            self.logger.debug(f"✅ timestamps per hour: {timestamps_per_hour}")
            self.logger.debug(f"✅ Max missing timestamps per hour: {max_missing_per_hour}")
            self.logger.debug(f"✅ Max missing timestamps per day: {max_missing_per_day}")
            self.logger.debug(f"✅ Max missing timestamps per month: {max_missing_per_month}")
            
            return df, interval_minutes, max_missing_per_hour, max_missing_per_day, max_missing_per_month
            
        except Exception as e:
            self.logger.error(f"❌ Error while initializing interval and alarm levels: {e}")
            raise_with_context("Failed to initialize interval and alarm levels", e)
    
    @staticmethod
    def select_full_months_by_day(
        year: str,
        month: str,
        missing_days: list,
        warning_only: bool = True,
        logger: Optional[ReportLogger] = None
    ) -> bool:
        """
        Determine if a month should be selected based on missing days.
        
        Args:
            year: Year as string
            month: Month as string
            missing_days: List of missing day numbers
            warning_only: If True, accept with warning; if False, reject
            logger: Optional logger instance
            
        Returns:
            bool: True if month should be included, False otherwise
        """
        if logger is None:
            logger = ReportLogger()
        
        try:
            logger.debug(f"🔍 DEBUG select_full_months_by_day: year={year}, month={month}, missing_days={missing_days}, warning_only={warning_only}")
            logger.debug(f"🔍 DEBUG select_full_months_by_day: MAX_MISSING_DAYS_PER_MONTH={MAX_MISSING_DAYS_PER_MONTH}")
            logger.debug(f"🔍 DEBUG select_full_months_by_day: len(missing_days)={len(missing_days)}")
            
            if len(missing_days) > MAX_MISSING_DAYS_PER_MONTH:
                logger.debug(f"🔍 DEBUG select_full_months_by_day: REJECTED - Too many missing days ({len(missing_days)} > {MAX_MISSING_DAYS_PER_MONTH})")
                return False
            
            if len(missing_days) == 0:
                logger.debug(f"🔍 DEBUG select_full_months_by_day: ACCEPTED - No missing days")
                return True
            
            if warning_only:
                logger.warning(f"⚠️ Warning Missing days {year}-{month}: {missing_days} - computation continues")
                logger.debug(f"🔍 DEBUG select_full_months_by_day: ACCEPTED with warning - warning_only=True")
                return True
            else:
                logger.warning(f"⚠️ Month {year}-{month} will be removed from the analysis for {missing_days} missing days")
                logger.debug(f"🔍 DEBUG select_full_months_by_day: REJECTED - warning_only=False")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error while selecting full months - select_full_months_by_day {year}-{month} {missing_days}: {e}")
            raise ValueError(f"❌ Error while selecting full months - select_full_months_by_day {year}-{month} {missing_days}: {e}")
    
    def select_full_months(
        self,
        df: pd.DataFrame,
        warning_only: bool = True,
        cutoff_datetime: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Select only months that are complete (within threshold of missing days).
        
        For cutoff months, this function understands that a cutoff month spans multiple
        calendar months. For example, with cutoff_day=26, September cutoff month includes:
        - Aug 25-31 (from previous calendar month)
        - Sept 1-24 (from current calendar month)
        Total: 31 days
        
        Args:
            df: DataFrame with 'Year-Month-cut-off' and 'Date' columns
            warning_only: If True, accept months with warnings; if False, reject them
            cutoff_datetime: Optional cutoff datetime to calculate cutoff month boundaries
            
        Returns:
            DataFrame with only selected months, or None if no months selected
        """
        try:
            self.logger.debug(f"🔍 DEBUG select_full_months: Starting with df shape={df.shape}, warning_only={warning_only}")
            self.logger.debug(f"🔍 DEBUG select_full_months: DataFrame columns: {list(df.columns)}")
            
            # Check if Year-Month-cut-off column exists
            if 'Year-Month-cut-off' not in df.columns:
                self.logger.error(f"❌ Year-Month-cut-off column not found in DataFrame")
                raise ValueError("Year-Month-cut-off column not found in DataFrame")

            
            # Get unique month-year tuples
            month_year_tuples_raw = df['Year-Month-cut-off'].unique()
            self.logger.debug(f"🔍 DEBUG select_full_months: Found unique month-year tuples: {month_year_tuples_raw}")
            
            month_year_tuples = []
            
            for month_year in month_year_tuples_raw:
                self.logger.debug(f"🔍 DEBUG select_full_months: Processing month_year: {month_year}")
                
                year = month_year.split('-')[0]
                month = month_year.split('-')[1]
                self.logger.debug(f"🔍 DEBUG select_full_months: Parsed year={year}, month={month}")
                
                df_month = df[df['Year-Month-cut-off'] == month_year].copy()
                self.logger.debug(f"🔍 DEBUG select_full_months: df_month shape for {month_year}: {df_month.shape}")
                
                if df_month.empty:
                    self.logger.debug(f"🔍 DEBUG select_full_months: REJECTED {month_year} - empty dataframe")
                    continue
                
                month_dates = df_month['Date'].unique()
                self.logger.debug(f"🔍 DEBUG select_full_months: Unique dates in {month_year}: {len(month_dates)} dates")
                self.logger.debug(f"🔍 DEBUG select_full_months: Date range: {min(month_dates)} to {max(month_dates)}")
                
                # Calculate expected days for this cutoff month
                # A cutoff month always spans ~28-31 days across multiple calendar months
                # For cutoff_day=26, September cutoff = Aug 25-31 (7 days) + Sept 1-24 (24 days) = 31 days
                # We use the calendar month length as a reasonable approximation
                expected_days = monthrange(int(year), int(month))[1]
                
                # Get actual unique dates present in this cutoff month
                # A cutoff month can span multiple calendar months, so we count all unique dates
                actual_dates = set()
                for date_str in month_dates:
                    if '-' in date_str:
                        # Parse date and add to set (YYYY-MM-DD format)
                        parts = date_str.split('-')
                        if len(parts) >= 3:
                            actual_dates.add((int(parts[0]), int(parts[1]), int(parts[2])))
                
                unique_dates_count = len(actual_dates)
                self.logger.debug(f"🔍 DEBUG select_full_months: Cutoff month {month_year} - Unique dates present: {unique_dates_count}, expected: ~{expected_days}")
                
                # For cutoff months, check if we have approximately the right number of days
                # Allow for some missing days (within MAX_MISSING_DAYS_PER_MONTH threshold)
                missing_days_count = max(0, expected_days - unique_dates_count)
                
                self.logger.debug(f"🔍 DEBUG select_full_months: Missing days count: {missing_days_count} for {month_year}")
                
                # Use a threshold check instead of specific missing days list
                if missing_days_count > MAX_MISSING_DAYS_PER_MONTH:
                    self.logger.debug(f"🔍 DEBUG select_full_months: REJECTED {month_year} - Too many missing days ({missing_days_count} > {MAX_MISSING_DAYS_PER_MONTH})")
                    continue
                
                if missing_days_count == 0:
                    self.logger.debug(f"🔍 DEBUG select_full_months: ACCEPTED {month_year} - No missing days")
                    month_year_tuples.append((year, month))
                elif warning_only:
                    self.logger.warning(f"⚠️ Warning: {month_year} has {missing_days_count} missing days - computation continues")
                    self.logger.debug(f"🔍 DEBUG select_full_months: ACCEPTED {month_year} with warning")
                    month_year_tuples.append((year, month))
                else:
                    self.logger.warning(f"⚠️ Month {month_year} will be removed from the analysis for {missing_days_count} missing days")
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
    
    @staticmethod
    def select_last_month_with_cutoff_day(df: pd.DataFrame) -> pd.DataFrame:
        """
        Select the last month with the cutoff day.
        
        Args:
            df: DataFrame with 'Year-Month-cut-off' column
            
        Returns:
            DataFrame filtered to last cutoff month
        """
        try:
            df = df.copy()
            df['Year-Month-digit'] = df['Year-Month-cut-off'].apply(lambda x: int(x.replace('-', '')))
            last_month = df['Year-Month-digit'].max()
            df = df[df['Year-Month-digit'] == last_month]
            return df
        except Exception as e:
            raise ValueError(f"❌ Error while selecting last month with cutoff day: {e}")
    
    def compute_monthly_date_range(self, df: pd.DataFrame) -> Tuple[str, str]:
        """
        Compute the date range for the monthly data.
        
        Args:
            df: DataFrame with 'Year-Month-cut-off' column
            
        Returns:
            Tuple of (date_range string, last_month string)
        """
        try:
            df_last_month = self.select_last_month_with_cutoff_day(df)
            if df_last_month is None or df_last_month.empty:
                df_last_month = df.copy()
            last_month = df_last_month['Year-Month-cut-off'].values[0]
            date_range = df_last_month.index.min().strftime('%B %d, %Y') + ' - ' + df_last_month.index.max().strftime('%B %d, %Y')
            return date_range, last_month
        except Exception as e:
            self.logger.error(f"❌ Error while computing monthly date range: {e}")
            raise ValueError(f"❌ Error while computing monthly date range: {e}")
    
    @staticmethod
    def get_last_month_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Get data for the last month.
        
        Args:
            df: DataFrame with DatetimeIndex
            
        Returns:
            DataFrame filtered to last calendar month
        """
        try:
            if df.empty:
                return df
            
            # Get the last month from the data
            last_date = df.index.max()
            last_month = last_date.month
            last_year = last_date.year
            
            # Filter data for the last month
            last_month_data = df[(df.index.month == last_month) & (df.index.year == last_year)]
            
            return last_month_data
        except Exception as e:
            return df
