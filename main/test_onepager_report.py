#!/usr/bin/env python3
"""
Test script for generating one-pager reports
"""

import sys
import os

# Add the current directory to the path
sys.path.append('.')

# Import the electricity analysis module
from electricity_analysis import ComputeEnergy, GenerateReport
import pandas as pd



def test_onepager_with_specific_load(load, warning_only=True):
    """Test the one-pager report with a specific load selection"""
    
    # Paths
    root_path = "/home/philg/projects/stratcon"
    data_path = f"{root_path}/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    loads_summary_path = f"{root_path}/downloads/Neo3/NEO3 - loads_cutoff_dates.csv"
    
    print("\n🔌 Testing One-Pager Report with Specific Load")
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

        
        
        # Initialize the report generator
        report_generator = GenerateReport()
        
        # Generate one-pager report with specific load
        print("🔌 Generating one-pager report with specific load...")
        try:
            values_for_html, df, chart_daily_consumption, chart_monthly_history, chart_hourly_consumption, chart_days_consumption = report_generator.generate_onepager_report_values_and_charts(data_path, loads_summary_path, selected_load = load, warning_only=warning_only)

            report_path = report_generator.generate_onepager_html(values_for_html, chart_daily_consumption, chart_monthly_history, chart_hourly_consumption, chart_days_consumption)
            
            if report_path:
                print("✅ One-pager report with specific load generated successfully!")
                print(f"📄 Report saved to: {report_path}")
                print(f"🌐 Open the file in your browser to view the report")
                return True
            else:
                print("❌ Failed to generate one-pager report with specific load")
                return False
        except Exception as e:
            print(f"❌ Exception during report generation: {e}")
            import traceback
            print(f"📋 Full traceback:")
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Error during specific load test: {e}")
        import traceback
        print(f"📋 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting One-Pager Report Tests")
    print("=" * 60)
    
    # # Test 1: Step-by-step one-pager report generation
    # success1 = test_onepager_report()
    
    # # Test 2: One-pager only (using generate_onepager_only method)
    # success2 = test_onepager_only()
    
    # Test 3: One-pager with specific load selection
    success3 = test_onepager_with_specific_load("MCB 701")

    
    # # Test 4: Full analysis with one-pager
    # success4 = test_full_analysis_with_onepager()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    # print(f"Step-by-step one-pager: {'✅ PASSED' if success1 else '❌ FAILED'}")
    # print(f"One-pager only method: {'✅ PASSED' if success2 else '❌ FAILED'}")
    print(f"One-pager with specific load: {'✅ PASSED' if success3 else '❌ FAILED'}")
    # print(f"Full analysis: {'✅ PASSED' if success4 else '❌ FAILED'}")
    
    # if success1 or success2 or success3 or success4:
    #     print("\n🎉 At least one test passed! Check the reports directory for generated files.")
    # else:
    #     print("\n❌ All tests failed. Check the error messages above.")
