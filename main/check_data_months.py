#!/usr/bin/env python3
"""
Check what months are available in the data
"""

import sys
sys.path.append('.')

from electricity_analysis import ea

def check_data_months():
    print("🔍 Checking Data Months")
    print("=" * 30)
    
    # Load data
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - FLOOR PARENT- Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    try:
        df = ea.load_and_prepare_data(data_path)
        
        if df is not None:
            print("✅ Data loaded successfully!")
            print(f"📅 Date range: {df.index.min()} to {df.index.max()}")
            print(f"📊 Shape: {df.shape}")
            
            # Check cutoff months
            cutoff_months = df['Year-Month-cut-off'].unique()
            print(f"📅 Available cutoff months: {sorted(cutoff_months)}")
            
            # Check month distribution
            print(f"\n📊 Month distribution:")
            month_counts = df['Year-Month-cut-off'].value_counts().sort_index()
            for month, count in month_counts.items():
                print(f"  {month}: {count:,} records")
            
            # Check if we have complete months
            print(f"\n🔍 Checking for complete months...")
            for month in cutoff_months:
                month_data = df[df['Year-Month-cut-off'] == month]
                print(f"  {month}: {len(month_data):,} records")
                
        else:
            print("❌ Failed to load data")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data_months()
