#!/usr/bin/env python3
"""
Debug script for one-pager report generation
"""

from electricity_analysis import ea
import os
import pandas as pd

def debug_onepager():
    print("🔍 Debugging One-Pager Report Generation")
    print("=" * 50)
    
    # Set up paths
    root_path = "/home/philg/projects/stratcon"
    data_path = f"{root_path}/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    loads_summary_path = f"{root_path}/downloads/Neo3/NEO3 - loads_cutoff_dates.csv"
    
    print(f"📁 Data path: {data_path}")
    print(f"📁 Loads summary path: {loads_summary_path}")
    print(f"📁 Data exists: {os.path.exists(data_path)}")
    print(f"📁 Loads summary exists: {os.path.exists(loads_summary_path)}")
    
    if not os.path.exists(data_path):
        print("❌ Data file not found!")
        return
    
    if not os.path.exists(loads_summary_path):
        print("❌ Loads summary file not found!")
        return
    
    try:
        print("\n🔍 Step 1: Loading data...")
        df = ea.load_and_prepare_data(data_path)
        if df is None:
            print("❌ Failed to load data")
            return
        print(f"✅ Data loaded. Shape: {df.shape}")
        print(f"📊 Columns: {list(df.columns)}")
        print(f"📅 Date range: {df.index.min()} to {df.index.max()}")
        
        print("\n🔍 Step 2: Initializing intervals...")
        df = ea.init_interval_and_alarm_levels(df)
        print(f"✅ Intervals initialized. Shape: {df.shape}")
        
        print("\n🔍 Step 3: Selecting full months...")
        df = ea.select_full_months(df, warning_only=False)
        if df is None:
            print("❌ No complete months found")
            return
        print(f"✅ Full months selected. Shape: {df.shape}")
        
        print("\n🔍 Step 4: Computing energy...")
        df = ea.compute_energy(df)
        print(f"✅ Energy computed. Shape: {df.shape}")
        
        # Check what columns we have
        energy_cols = [col for col in df.columns if 'Consumption [kWh]' in col]
        power_cols = [col for col in df.columns if '[kW]' in col]
        print(f"📊 Energy columns: {energy_cols}")
        print(f"📊 Power columns: {power_cols}")
        
        print("\n🔍 Step 5: Generating one-pager report...")
        report_path = ea.generate_onepager_report(df, loads_summary_path)
        
        if report_path:
            print(f"✅ Report generated: {report_path}")
            if os.path.exists(report_path):
                size = os.path.getsize(report_path)
                print(f"📏 File size: {size:,} bytes")
        else:
            print("❌ Report generation failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_onepager()
