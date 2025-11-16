#!/usr/bin/env python3
"""
Data loading and preparation functions for electricity analysis
"""
import pandas as pd
import numpy as np
import sqlite3
from calendar import monthrange
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from .db_manager import DbQueries
import os

from .config import (
    PHILIPPINES_TZ,
    MAX_MISSING_DAYS_PER_MONTH,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH,
)
from .utils import ReportLogger, raise_with_context


def load_and_prepare_data_legacy(
    path: str,
    cutoff_day: int,
    logger: ReportLogger
) -> Tuple[pd.DataFrame, list, str, str]:
    """
    Load electricity consumption data from CSV and prepare it for analysis.
    
    Args:
        path: Path to CSV file
        cutoff_day: Day of month for billing cutoff
        logger: Logger instance (required)
        
    Returns:
        Tuple of (DataFrame, loads list, client_name, client_detail_name)
    """
    
    try:
        logger.debug(f"Loading data from: {path}")
        logger.debug(f"File exists: {os.path.exists(path)}")
        
        # Read CSV with proper decimal handling for European format
        df = pd.read_csv(
            path,
            delimiter=',',
            decimal=',',
            thousands='.',
            parse_dates=['Date']
        )
        logger.debug(f"CSV read successfully. Shape: {df.shape}")
        
        # Extract client name from path
        path_parts = path.split('/')
        if len(path_parts) >= 2:
            client_name = path_parts[-2]  # Parent directory name
        else:
            client_name = "Unknown Client"
        
        # Extract client detail name from filename
        filename = path_parts[-1]
        if '- Electricity consumption' in filename:
            client_detail_name = filename.split('- Electricity consumption')[0]
        else:
            client_detail_name = filename.replace('.csv', '')
        
        logger.debug(f"Client name: {client_name} - Client detail name: {client_detail_name}")
        
        # Rename Date column to timestamp
        df.rename(columns={'Date': 'timestamp'}, inplace=True)
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        logger.debug(f"Index set successfully. Shape: {df.shape}")
        
        # Select loads from columns
        loads = select_loads(df)
        logger.debug(f"Selected loads: {loads}")
        
        # Filter dataframe to power columns
        power_columns = [generate_power_column_name(load) for load in loads]
        df = df[power_columns]
        logger.debug(f"Filtered dataframe shape: {df.shape}")
        
        # Add time-based features
        df['Date'] = df.index.strftime('%Y-%m-%d')
        df['Month'] = df.index.month
        df['Year'] = df.index.year
        df['Hour'] = df.index.hour
        df['Day'] = df.index.day
        df['DayOfWeek'] = df.index.dayofweek
        
        # Convert cutoff_day to datetime for timezone-aware processing
        cutoff_datetime = create_cutoff_datetime(cutoff_day)
        df = generate_cutoff_month_column(df, cutoff_datetime, logger)
        
        logger.debug(f"✅ Data loaded successfully!")
        logger.debug(f"Dataset shape: {df.shape}")
        logger.debug(f"Date range: {df.index.min()} to {df.index.max()}")
        
        return df, loads, client_name, client_detail_name
        
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        raise

def load_and_prepare_data_for_tenant(
    tenant_ids: List[int],
    cutoff_datetime: Optional[datetime] = None,
    cutoff_day: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    source: str = 'meter_records',
    aggregate_multi_load: bool = True,
    conn: Optional[sqlite3.Connection] = None,
    logger: Optional[ReportLogger] = None,
    ) -> Tuple[pd.DataFrame, list, str, str]:
    """
    Load electricity consumption data from database and prepare it for analysis.
    
    Args:
        tenant_ids: List of tenant IDs to query
        cutoff_datetime: Optional cutoff datetime
        cutoff_day: Optional cutoff day (used if cutoff_datetime not provided)
        start_date: Optional start date filter
        end_date: Optional end date filter
        source: Data source ('meter_records' or other)
        aggregate_multi_load: Whether to aggregate multiple loads
        conn: Optional database connection
        logger: Logger instance (required)
        
    Returns:
        Tuple of (DataFrame, loads list, client_name, client_detail_name)
    """
    if logger is None:
        raise ValueError("logger parameter is required")
    
    try:
        # Load data from database
        df = DbQueries.load_consumption_data_for_tenant(
            tenant_id=tenant_ids,
            start_date=start_date,
            end_date=end_date,
            conn=conn
        )
        
        # Select loads from columns
        loads = select_loads(df)
        logger.debug(f"Selected loads: {loads}")
        
        # Filter dataframe to power columns
        power_columns = [generate_power_column_name(load) for load in loads]
        df = df[power_columns]
        logger.debug(f"Filtered dataframe shape: {df.shape}")
        
        # Add time-based features
        df['Date'] = df.index.strftime('%Y-%m-%d')
        df['Month'] = df.index.month
        df['Year'] = df.index.year
        df['Hour'] = df.index.hour
        df['Day'] = df.index.day
        df['DayOfWeek'] = df.index.dayofweek
        
        if len(tenant_ids) == 1:
            tenant_id = tenant_ids[0]
            df = CutoffManager.generate_cutoff_month_column_for_tenant(df, tenant_id, source=source)
        
        else:
            list_df = []
            for tenant_id in tenant_ids:
                df_tenant = df[df['tenant_id'] == tenant_id]
                df_tenant = CutoffManager.generate_cutoff_month_column_for_tenant(df_tenant, tenant_id, source=source)
                list_df.append(df_tenant)
            df = pd.concat(list_df)

        
        logger.debug(f"✅ Data loaded successfully!")
        logger.debug(f"Dataset shape: {df.shape}")
        logger.debug(f"Date range: {df.index.min()} to {df.index.max()}")
        
        # Return empty strings for client_name and client_detail_name when loading from DB
        # These would need to be determined from the tenant_ids if needed
        return df, loads, "", ""
        
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        raise

def select_loads(df: pd.DataFrame) -> list:
    """Extract load names from DataFrame columns that contain [kW]"""
    loads = [col.replace("[kW]", "").strip() for col in df.columns if '[kW]' in col]
    return loads


def select_loads_by_level(df: pd.DataFrame, df_loads: pd.DataFrame, client: str, level: int) -> pd.DataFrame:
    """Select loads based on client and level (fixed bitwise operator bug)"""
    df_loads = df_loads[(df_loads['Client'] == client) & (df_loads['Level'] <= level)]
    loads = df_loads['Load'].unique()
    loads = [load + ' [kW]' for load in loads]
    columns = [col for col in df.columns if col in loads]
    df = df[columns]
    return df


def generate_cutoff_hourly(date: datetime, cutoff_datetime: datetime) -> datetime:
    """
    Adjust date based on cutoff time (hour/minute/second) before applying day-based logic.
    
    Logic:
    - If cutoff time < 12:00 (e.g., 08:00:00):
      * date_time < cutoff_time → move to previous day
      * date_time >= cutoff_time → stay on current day
      * Hours 00:00 to (cutoff_time-1) of next day → move to current day
    
    - If cutoff time >= 12:00 (e.g., 18:00:00):
      * date_time < cutoff_time → stay on current day
      * date_time >= cutoff_time → move to next day
      * Hours >= cutoff_time of previous day → move to current day
    
    Args:
        date: datetime object (can be naive or timezone-aware)
        cutoff_datetime: datetime object with time and timezone info for cutoff
        
    Returns:
        datetime: Adjusted date based on hourly cutoff logic
    """
    # Convert to Philippines timezone if not already timezone-aware
    if date.tzinfo is None:
        date_ph = PHILIPPINES_TZ.localize(date)
    else:
        date_ph = date.astimezone(PHILIPPINES_TZ)
    
    # Convert cutoff_datetime to Philippines timezone if needed
    if cutoff_datetime.tzinfo is None:
        cutoff_ph = PHILIPPINES_TZ.localize(cutoff_datetime)
    else:
        cutoff_ph = cutoff_datetime.astimezone(PHILIPPINES_TZ)
    
    # Extract time components
    date_time = date_ph.time()
    cutoff_time = cutoff_ph.time()
    
    # Compare times (hours, minutes, seconds, microseconds)
    cutoff_hour = cutoff_ph.hour
    
    # Adjust date based on cutoff time
    if cutoff_hour < 12:
        # Early cutoff (e.g., 08:00:00): early hours go to previous day
        if date_time < cutoff_time:
            # Before cutoff time → move to previous day
            adjusted_date = date_ph - timedelta(days=1)
        else:
            # On or after cutoff time → stay on current day
            adjusted_date = date_ph
    else:
        # Late cutoff (e.g., 18:00:00): late hours go to next day
        if date_time < cutoff_time:
            # Before cutoff time → stay on current day
            adjusted_date = date_ph
        else:
            # On or after cutoff time → move to next day
            adjusted_date = date_ph + timedelta(days=1)
    
    return adjusted_date


def generate_cutoff(date: datetime, cutoff_datetime: datetime) -> str:
    """
    Generate cutoff month for a single date/datetime with corrected logic.
    
    A cutoff month always has 28/30/31 days and spans from cutoff_day to (cutoff_day-1) of next month.
    
    Logic:
    - If cutoff_day is 1-15 (inclusive):
      * Dates from cutoff_day to end of current month → current month cutoff
      * Dates from start of next month to (cutoff_day-1) → current month cutoff
      * Dates from start of current month to (cutoff_day-1) → previous month cutoff
    
    - If cutoff_day is 16-31:
      * Dates from start of current month to (cutoff_day-1) → current month cutoff
      * Dates from cutoff_day to end of current month → next month cutoff
      * Dates from previous month's cutoff_day to end of previous month → current month cutoff
    
    Args:
        date: datetime object (can be naive or timezone-aware)
        cutoff_datetime: datetime object with time and timezone info for cutoff
        
    Returns:
        str: Year-Month string in format "YYYY-MM" representing the cutoff month
    """
    # First apply hourly adjustment
    adjusted_date = generate_cutoff_hourly(date, cutoff_datetime)
    
    # Now extract date components from adjusted date (ignore time for day-based logic)
    date_day = adjusted_date.day
    date_month = adjusted_date.month
    date_year = adjusted_date.year
    
    # Extract cutoff day (use day from cutoff_datetime)
    if cutoff_datetime.tzinfo is None:
        cutoff_ph = PHILIPPINES_TZ.localize(cutoff_datetime)
    else:
        cutoff_ph = cutoff_datetime.astimezone(PHILIPPINES_TZ)
    
    cutoff_day = cutoff_ph.day
    
    # Determine which cutoff month this date belongs to
    # A cutoff month always has 28/30/31 days and spans from cutoff_day to (cutoff_day-1) of next month
    
    if cutoff_day <= 15:
        # Cutoff day is 1-15: cutoff month spans from cutoff_day to (cutoff_day-1) of next month
        # Example: cutoff_day=8 → Sept cutoff month = Sept 8-30 + Oct 1-7
        # - Sept 1-7 → Aug cutoff (before cutoff in Sept)
        # - Sept 8-30 → Sept cutoff (on/after cutoff in Sept)
        # - Oct 1-7 → Sept cutoff (before cutoff in Oct, part of Sept cutoff month)
        
        if date_day >= cutoff_day:
            # Date is on or after cutoff_day in its month → belongs to that month's cutoff
            result_month = date_month
            result_year = date_year
        else:
            # Date is before cutoff_day in its month → belongs to previous month's cutoff
            if date_month == 1:
                result_month = 12
                result_year = date_year - 1
            else:
                result_month = date_month - 1
                result_year = date_year
    
    else:
        # Cutoff day is 16-31: cutoff month spans from start of month to (cutoff_day-1) plus
        # dates from previous month from cutoff_day onwards
        # Example: cutoff_day=25 → Sept cutoff = Sept 1-24 + Aug 25-31
        # - Sept 1-24 → Sept cutoff (before cutoff in Sept)
        # - Sept 25-30 → Oct cutoff (on/after cutoff in Sept)
        # - Aug 25-31 → Sept cutoff (on/after cutoff in Aug, part of Sept cutoff month)
        
        if date_day < cutoff_day:
            # Date is before cutoff_day in current month → belongs to current month cutoff
            result_month = date_month
            result_year = date_year
        else:
            # Date is on or after cutoff_day in current month → belongs to next month cutoff
            if date_month == 12:
                result_month = 1
                result_year = date_year + 1
            else:
                result_month = date_month + 1
                result_year = date_year
        
    return f"{result_year}-{result_month:02d}"


def create_cutoff_datetime(cutoff_day: int, hour: int = 23, minute: int = 59, second: int = 59) -> datetime:
    """
    Create a cutoff datetime from an integer day.
    
    Args:
        cutoff_day: int, day of the month (1-31)
        hour: int, hour for cutoff time (default: 23)
        minute: int, minute for cutoff time (default: 59)
        second: int, second for cutoff time (default: 59)
        
    Returns:
        datetime: datetime object with Philippines timezone
    """
    # Create a datetime for the cutoff day (month/year don't matter for component extraction)
    cutoff_datetime = datetime(2024, 1, cutoff_day, hour, minute, second)
    return PHILIPPINES_TZ.localize(cutoff_datetime)


def generate_cutoff_month_column(
    df: pd.DataFrame,
    cutoff_datetime: datetime,
    logger: ReportLogger
) -> pd.DataFrame:
    """
    Generate month-year labels based on a cutoff datetime for rolling months.
    
    Args:
        df: pandas DataFrame with DatetimeIndex
        cutoff_datetime: datetime object with time and timezone info for cutoff
        logger: Logger instance (required)
        
    Returns:
        pandas.DataFrame: DataFrame with added 'Year-Month-cut-off' column
    """
    
    try:
        # Convert DatetimeIndex to Series to use apply
        cutoff_series = pd.Series(df.index).apply(lambda x: generate_cutoff(x, cutoff_datetime))
        df['Year-Month-cut-off'] = cutoff_series.values
        return df
    except Exception as e:
        logger.error(f"❌ Error generating cutoff month column: {e}")
        raise_with_context("Failed to generate cutoff month column", e)


def init_interval_and_alarm_levels(
    df: pd.DataFrame,
    logger: ReportLogger
) -> Tuple[pd.DataFrame, float, float, float, float]:
    """
    Initialize interval calculations and alarm thresholds.
    
    Args:
        df: DataFrame with time series data
        logger: Logger instance (required)
        
    Returns:
        Tuple of (df, interval_minutes, max_per_hour, max_per_day, max_per_month)
    """
    
    try:
        if "interval_minutes" not in df.columns:
            df['interval_minutes'] = df.index.diff() / np.timedelta64(1, 'm')
        
        interval_minutes = round(df['interval_minutes'].mean(), 0)
        timestamps_per_hour = round(60 / interval_minutes)
        
        df['Nb_of_intervals_between_timestamps'] = df['interval_minutes'] / interval_minutes
        df['Missing_timestamps_after_timestamp'] = df['Nb_of_intervals_between_timestamps'] - 1
        
        max_missing_per_hour = np.ceil(timestamps_per_hour * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR)
        max_missing_per_day = np.ceil(timestamps_per_hour * 24 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY)
        max_missing_per_month = np.ceil(timestamps_per_hour * 24 * 30 * MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH)
        
        logger.debug(f"✅ Interval minutes: {interval_minutes}")
        logger.debug(f"✅ timestamps per hour: {timestamps_per_hour}")
        logger.debug(f"✅ Max missing timestamps per hour: {max_missing_per_hour}")
        logger.debug(f"✅ Max missing timestamps per day: {max_missing_per_day}")
        logger.debug(f"✅ Max missing timestamps per month: {max_missing_per_month}")
        
        return df, interval_minutes, max_missing_per_hour, max_missing_per_day, max_missing_per_month
        
    except Exception as e:
        logger.error(f"❌ Error while initializing interval and alarm levels: {e}")
        raise_with_context("Failed to initialize interval and alarm levels", e)


def select_full_months_by_day(
    year: str,
    month: str,
    missing_days: list,
    warning_only: bool = True,
    logger: ReportLogger
) -> bool:
    """
    Determine if a month should be selected based on missing days.
    
    Args:
        year: Year as string
        month: Month as string
        missing_days: List of missing day numbers
        warning_only: If True, accept with warning; if False, reject
        logger: Logger instance (required)
        
    Returns:
        bool: True if month should be included, False otherwise
    """
    
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
    df: pd.DataFrame,
    warning_only: bool = True,
    logger: Optional[ReportLogger] = None,
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
        logger: Logger instance (required)
        cutoff_datetime: Optional cutoff datetime to calculate cutoff month boundaries
        
    Returns:
        DataFrame with only selected months, or None if no months selected
    """
    if logger is None:
        raise ValueError("logger parameter is required")
    
    try:
        logger.debug(f"🔍 DEBUG select_full_months: Starting with df shape={df.shape}, warning_only={warning_only}")
        logger.debug(f"🔍 DEBUG select_full_months: DataFrame columns: {list(df.columns)}")
        
        # Check if Year-Month-cut-off column exists
        if 'Year-Month-cut-off' not in df.columns:
            logger.error(f"❌ Year-Month-cut-off column not found in DataFrame")
            raise ValueError("Year-Month-cut-off column not found in DataFrame")
        
        # Extract cutoff day if cutoff_datetime provided
        cutoff_day = None
        if cutoff_datetime is not None:
            if cutoff_datetime.tzinfo is None:
                cutoff_ph = PHILIPPINES_TZ.localize(cutoff_datetime)
            else:
                cutoff_ph = cutoff_datetime.astimezone(PHILIPPINES_TZ)
            cutoff_day = cutoff_ph.day
            logger.debug(f"🔍 DEBUG select_full_months: Using cutoff_day={cutoff_day} from cutoff_datetime")
        
        # Get unique month-year tuples
        month_year_tuples_raw = df['Year-Month-cut-off'].unique()
        logger.debug(f"🔍 DEBUG select_full_months: Found unique month-year tuples: {month_year_tuples_raw}")
        
        month_year_tuples = []
        
        for month_year in month_year_tuples_raw:
            logger.debug(f"🔍 DEBUG select_full_months: Processing month_year: {month_year}")
            
            year = month_year.split('-')[0]
            month = month_year.split('-')[1]
            logger.debug(f"🔍 DEBUG select_full_months: Parsed year={year}, month={month}")
            
            df_month = df[df['Year-Month-cut-off'] == month_year].copy()
            logger.debug(f"🔍 DEBUG select_full_months: df_month shape for {month_year}: {df_month.shape}")
            
            if df_month.empty:
                logger.debug(f"🔍 DEBUG select_full_months: REJECTED {month_year} - empty dataframe")
                continue
            
            month_dates = df_month['Date'].unique()
            logger.debug(f"🔍 DEBUG select_full_months: Unique dates in {month_year}: {len(month_dates)} dates")
            logger.debug(f"🔍 DEBUG select_full_months: Date range: {min(month_dates)} to {max(month_dates)}")
            
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
            logger.debug(f"🔍 DEBUG select_full_months: Cutoff month {month_year} - Unique dates present: {unique_dates_count}, expected: ~{expected_days} (cutoff_day={cutoff_day or 'unknown'})")
            
            # For cutoff months, check if we have approximately the right number of days
            # Allow for some missing days (within MAX_MISSING_DAYS_PER_MONTH threshold)
            missing_days_count = max(0, expected_days - unique_dates_count)
            
            logger.debug(f"🔍 DEBUG select_full_months: Missing days count: {missing_days_count} for {month_year}")
            
            # Use a threshold check instead of specific missing days list
            if missing_days_count > MAX_MISSING_DAYS_PER_MONTH:
                logger.debug(f"🔍 DEBUG select_full_months: REJECTED {month_year} - Too many missing days ({missing_days_count} > {MAX_MISSING_DAYS_PER_MONTH})")
                continue
            
            if missing_days_count == 0:
                logger.debug(f"🔍 DEBUG select_full_months: ACCEPTED {month_year} - No missing days")
                month_year_tuples.append((year, month))
            elif warning_only:
                logger.warning(f"⚠️ Warning: {month_year} has {missing_days_count} missing days - computation continues")
                logger.debug(f"🔍 DEBUG select_full_months: ACCEPTED {month_year} with warning")
                month_year_tuples.append((year, month))
            else:
                logger.warning(f"⚠️ Month {month_year} will be removed from the analysis for {missing_days_count} missing days")
                logger.debug(f"🔍 DEBUG select_full_months: REJECTED {month_year}")
        
        logger.debug(f"🔍 DEBUG select_full_months: Final selected months: {month_year_tuples}")
        logger.debug(f"✅ Selected months for computation: {[(int(year), int(month)) for year, month in month_year_tuples]}")
        
        if not month_year_tuples:
            logger.warning(f"⚠️ No months selected for computation!")
            return None
        
        list_df = []
        for year, month in month_year_tuples:
            df_month = df[(df['Year-Month-cut-off'] == f"{year}-{month}")]
            logger.debug(f"🔍 DEBUG select_full_months: Adding df_month for {year}-{month}, shape: {df_month.shape}")
            list_df.append(df_month)
        
        if list_df:
            df_result = pd.concat(list_df)
            df_result.sort_index(inplace=True)
            logger.debug(f"🔍 DEBUG select_full_months: Final result shape: {df_result.shape}")
            return df_result
        else:
            logger.warning(f"⚠️ No dataframes to concatenate!")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error while selecting full months: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise ValueError(f"❌ Error while selecting full months: {e}")


def select_last_month_with_cutoff_day(df: pd.DataFrame) -> pd.DataFrame:
    """Select the last month with the cutoff day"""
    try:
        df = df.copy()
        df['Year-Month-digit'] = df['Year-Month-cut-off'].apply(lambda x: int(x.replace('-', '')))
        last_month = df['Year-Month-digit'].max()
        df = df[df['Year-Month-digit'] == last_month]
        return df
    except Exception as e:
        raise ValueError(f"❌ Error while selecting last month with cutoff day: {e}")


def compute_monthly_date_range(df: pd.DataFrame) -> Tuple[str, str]:
    """
    Compute the date range for the monthly data.
    
    Returns:
        Tuple of (date_range string, last_month string)
    """
    try:
        df_last_month = select_last_month_with_cutoff_day(df)
        last_month = df_last_month['Year-Month-cut-off'].values[0]
        date_range = df_last_month.index.min().strftime('%B %d, %Y') + ' - ' + df_last_month.index.max().strftime('%B %d, %Y')
        return date_range, last_month
    except Exception as e:
        raise ValueError(f"❌ Error while computing monthly date range: {e}")


def get_last_month_data(df: pd.DataFrame) -> pd.DataFrame:
    """Get data for the last month"""
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


# Import helper functions from utils
from .utils import generate_consumption_column_name, generate_power_column_name
