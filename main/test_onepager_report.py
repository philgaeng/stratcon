#!/usr/bin/env python3
"""
Test script for generating one-pager reports
"""

import sys
import os

# Add the current directory to the path
sys.path.append('.')

# Import the electricity analysis module
from electricity_analysis import ea

def test_onepager_report():
    """Test the one-pager report generation"""
    
    # Paths
    root_path = "/home/philg/projects/stratcon"
    data_path = f"{root_path}/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    loads_summary_path = f"{root_path}/downloads/Neo3/NEO3 - loads_cutoff_dates.csv"
    
    print("🔌 Testing One-Pager Report Generation")
    print("=" * 50)
    
    try:
        # Check if files exist
        if not os.path.exists(data_path):
            print(f"❌ Data file not found: {data_path}")
            return False
            
        if not os.path.exists(loads_summary_path):
            print(f"❌ Loads summary file not found: {loads_summary_path}")
            return False
        
        print(f"✅ Data file found: {data_path}")
        print(f"✅ Loads summary file found: {loads_summary_path}")
        
        # Check file sizes
        data_size = os.path.getsize(data_path)
        loads_size = os.path.getsize(loads_summary_path)
        print(f"📏 Data file size: {data_size:,} bytes")
        print(f"📏 Loads summary size: {loads_size:,} bytes")
        
        # Test data loading step by step
        print("\n🔍 Step-by-step debugging:")
        
        print("Step 1: Loading and preparing data...")
        df = ea.load_and_prepare_data(data_path)
        if df is None:
            print("❌ Failed to load data")
            return False
        print(f"✅ Data loaded successfully. Shape: {df.shape}")
        print(f"📊 Columns: {list(df.columns)}")
        
        print("Step 2: Initializing intervals and alarm levels...")
        df = ea.init_interval_and_alarm_levels(df)
        print(f"✅ Intervals initialized. Shape: {df.shape}")
        
        print("Step 3: Selecting full months...")
        df = ea.select_full_months(df, warning_only=False)
        if df is None:
            print("❌ No complete months found in data")
            return False
        print(f"✅ Full months selected. Shape: {df.shape}")
        
        print("Step 4: Computing energy...")
        df = ea.compute_energy(df)
        print(f"✅ Energy computed. Shape: {df.shape}")
        print(f"📊 Energy columns: {[col for col in df.columns if 'Consumption [kWh]' in col]}")
        
        print("Step 5: Generating one-pager report...")
        report_path = ea.generate_onepager_report(df, loads_summary_path)
        
        if report_path:
            print(f"✅ One-pager report generated successfully!")
            print(f"📄 Report saved to: {report_path}")
            print(f"🌐 Open the file in your browser to view the report")
            return True
        else:
            print("❌ Failed to generate one-pager report")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        print(f"📋 Full traceback:")
        traceback.print_exc()
        return False

def test_full_analysis_with_onepager():
    """Test the full analysis with one-pager report"""
    
    # Paths
    root_path = "/home/philg/projects/stratcon"
    data_path = f"{root_path}/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    loads_summary_path = f"{root_path}/downloads/Neo3/NEO3 - loads_cutoff_dates.csv"
    
    print("\n🔌 Testing Full Analysis with One-Pager Report")
    print("=" * 50)
    
    try:
        # Run full analysis (this will also generate one-pager reports)
        print("🔌 Running full analysis...")
        ea.run(data_path, loads_summary_path, strict=False)
        
        print("✅ Full analysis completed successfully!")
        print("📄 Check the reports directory for generated files")
        return True
        
    except Exception as e:
        print(f"❌ Error during full analysis: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting One-Pager Report Tests")
    print("=" * 60)
    
    # Test 1: One-pager report only
    success1 = test_onepager_report()
    
    # Test 2: Full analysis with one-pager
    success2 = test_full_analysis_with_onepager()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"One-pager only: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Full analysis: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 or success2:
        print("\n🎉 At least one test passed! Check the reports directory for generated files.")
    else:
        print("\n❌ All tests failed. Check the error messages above.")
