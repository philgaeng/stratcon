#!/usr/bin/env python3
"""
Test the cutoff month column fix and select_full_months functions
"""

import sys
sys.path.append('.')

from electricity_analysis import ea
import pandas as pd
import os
from calendar import monthrange
import numpy as np

def test_cutoff_fix():
    print("🔍 Testing Cutoff Month Column Fix")
    print("=" * 40)
    
    # Test file path
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    try:
        print("Step 1: Loading data...")
        df = ea.load_and_prepare_data(data_path)
        
        if df is not None:
            print("✅ Data loaded successfully!")
            print(f"📊 Shape: {df.shape}")
            print(f"📊 Columns: {list(df.columns)}")
            
            # Check if the cutoff column was added
            if 'Year-Month-cut-off' in df.columns:
                print("✅ Cutoff month column added successfully!")
                print(f"📊 Sample cutoff values: {df['Year-Month-cut-off'].head().tolist()}")
                print(f"📊 Unique cutoff values: {df['Year-Month-cut-off'].unique()[:10]}")
            else:
                print("❌ Cutoff month column not found")
                
        else:
            print("❌ Data loading failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_select_full_months_by_day():
    """Test the select_full_months_by_day function with various scenarios"""
    print("\n🔍 Testing select_full_months_by_day Function")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        # (year, month, missing_days, warning_only, expected_result, description)
        (2025, 1, [], True, True, "No missing days - should accept"),
        (2025, 1, [1, 2], True, True, "Few missing days with warning_only=True - should accept with warning"),
        (2025, 1, [1, 2, 3, 4, 5, 6], True, False, "6 missing days (exceeds MAX_MISSING_DAYS_PER_MONTH=5) - should reject"),
        (2025, 1, [1, 2, 3, 4, 5, 6, 7], True, False, "7 missing days (exceeds MAX_MISSING_DAYS_PER_MONTH=5) - should reject"),
        (2025, 1, [1, 2], False, False, "Few missing days with warning_only=False - should reject"),
        (2025, 2, [], False, True, "February with no missing days - should accept"),
    ]
    
    for year, month, missing_days, warning_only, expected, description in test_cases:
        print(f"\n📋 Test: {description}")
        print(f"   Input: year={year}, month={month}, missing_days={missing_days}, warning_only={warning_only}")
        
        try:
            result = ea.select_full_months_by_day(year, month, missing_days, warning_only)
            print(f"   Result: {result}")
            print(f"   Expected: {expected}")
            
            if result == expected:
                print("   ✅ PASS")
            else:
                print("   ❌ FAIL")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_select_full_months():
    """Test the select_full_months function with synthetic data"""
    print("\n🔍 Testing select_full_months Function")
    print("=" * 50)
    
    # Create synthetic test data
    print("📋 Creating synthetic test data...")
    
    # Create a date range for January 2025
    dates_jan = pd.date_range('2025-01-01', '2025-01-31', freq='5min')
    # Create a date range for February 2025 (missing some days)
    dates_feb = pd.date_range('2025-02-01', '2025-02-28', freq='5min')
    # Remove some days from February (simulate missing data)
    # Convert to Series first, then filter by date
    dates_feb_series = pd.Series(dates_feb)
    dates_feb = dates_feb[~dates_feb_series.dt.date.isin([pd.Timestamp('2025-02-15').date(), pd.Timestamp('2025-02-16').date()])]
    
    # Combine dates
    all_dates = list(dates_jan) + list(dates_feb)
    
    # Create DataFrame
    df = pd.DataFrame({
        'Timestamp': all_dates,
        'Load1 [kW]': np.random.randn(len(all_dates)) * 10 + 50,
        'Load2 [kW]': np.random.randn(len(all_dates)) * 5 + 25
    })
    
    # Set timestamp as index
    df.set_index('Timestamp', inplace=True)
    
    # Add required columns
    df['Date'] = df.index.strftime('%Y-%m-%d')
    df['Month'] = df.index.month
    df['Year'] = df.index.year
    df['Hour'] = df.index.hour
    df['Day'] = df.index.day
    df['DayOfWeek'] = df.index.dayofweek
    
    # Add cutoff column (using cutoff_day=7)
    df = ea.generate_cut_off_month_column(df, cutoff_day=7)
    
    print(f"📊 Created test DataFrame with shape: {df.shape}")
    print(f"📊 Date range: {df.index.min()} to {df.index.max()}")
    print(f"📊 Unique cutoff months: {df['Year-Month-cut-off'].unique()}")
    print(f"📊 Unique dates in January: {len(df[df['Year-Month-cut-off'] == '2025-01']['Date'].unique())}")
    print(f"📊 Unique dates in February: {len(df[df['Year-Month-cut-off'] == '2025-02']['Date'].unique())}")
    print(f"📊 Unique dates in December 2024: {len(df[df['Year-Month-cut-off'] == '2024-12']['Date'].unique())}")
    
    # Debug: Show some sample dates and their cutoff assignments
    print(f"📊 Sample date assignments:")
    sample_df = df[['Date', 'Year-Month-cut-off']].drop_duplicates().head(10)
    for _, row in sample_df.iterrows():
        print(f"   {row['Date']} -> {row['Year-Month-cut-off']}")
    
    # Test with warning_only=True
    print("\n📋 Test 1: select_full_months with warning_only=True")
    try:
        result_df = ea.select_full_months(df, warning_only=True)
        if result_df is not None:
            print(f"✅ Result shape: {result_df.shape}")
            print(f"📊 Selected months: {result_df['Year-Month-cut-off'].unique()}")
        else:
            print("❌ Result is None")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with warning_only=False
    print("\n📋 Test 2: select_full_months with warning_only=False")
    try:
        result_df = ea.select_full_months(df, warning_only=False)
        if result_df is not None:
            print(f"✅ Result shape: {result_df.shape}")
            print(f"📊 Selected months: {result_df['Year-Month-cut-off'].unique()}")
        else:
            print("❌ Result is None")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_edge_cases():
    """Test edge cases for the select functions"""
    print("\n🔍 Testing Edge Cases")
    print("=" * 30)
    
    # Test with empty DataFrame
    print("\n📋 Test: Empty DataFrame")
    try:
        empty_df = pd.DataFrame(columns=['Year-Month-cut-off', 'Date'])
        result = ea.select_full_months(empty_df)
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Error with empty DataFrame: {e}")
    
    # Test with DataFrame missing required columns
    print("\n📋 Test: DataFrame missing Year-Month-cut-off column")
    try:
        bad_df = pd.DataFrame({'Date': ['2025-01-01']})
        result = ea.select_full_months(bad_df)
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Expected error with missing column: {e}")

def run_all_tests():
    """Run all tests"""
    print("🚀 Running All Tests for Cutoff and Select Functions")
    print("=" * 60)
    
    test_cutoff_fix()
    test_select_full_months_by_day()
    test_select_full_months()
    test_edge_cases()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    run_all_tests()
