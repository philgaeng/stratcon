#!/usr/bin/env python3
"""
Test the refactored classes: ComputeEnergy and GenerateReport
"""

import sys
sys.path.append('.')

from electricity_analysis import report_generator, ea
import os

def test_single_file_report():
    """Test generating a report for a single file"""
    print("🔍 Testing Single File Report Generation")
    print("=" * 50)
    
    # Test file path
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    try:
        print("Step 1: Generating single file report...")
        report_path = report_generator.generate_single_file_report(
            data_path=data_path,
            loads_summary_path=None,
            cutoff_day=7,
            strict=False
        )
        
        if report_path:
            print(f"✅ Report generated successfully!")
            print(f"📊 Report path: {report_path}")
        else:
            print("❌ Report generation failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_onepager_only():
    """Test generating only the one-pager report"""
    print("\n🔍 Testing One-Pager Only Report Generation")
    print("=" * 50)
    
    # Test file path
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    try:
        print("Step 1: Generating one-pager only...")
        report_path = report_generator.generate_onepager_only(
            data_path=data_path,
            loads_summary_path=None,
            cutoff_day=7
        )
        
        if report_path:
            print(f"✅ One-pager report generated successfully!")
            print(f"📊 Report path: {report_path}")
        else:
            print("❌ One-pager report generation failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_folder_reports():
    """Test generating reports for all files in a folder"""
    print("\n🔍 Testing Folder Report Generation")
    print("=" * 50)
    
    # Test folder path
    folder_path = "/home/philg/projects/stratcon/downloads/Neo3"
    loads_summary_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - loads_cutoff_dates.csv"
    
    try:
        print("Step 1: Generating reports for all files in folder...")
        report_paths = report_generator.generate_reports_for_folder(
            folder_path=folder_path,
            loads_summary_path=loads_summary_path,
            strict=False
        )
        
        if report_paths:
            print(f"✅ Generated {len(report_paths)} reports successfully!")
            for i, path in enumerate(report_paths, 1):
                print(f"📊 Report {i}: {path}")
        else:
            print("❌ No reports were generated")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_compute_energy_functions():
    """Test the ComputeEnergy class functions directly"""
    print("\n🔍 Testing ComputeEnergy Class Functions")
    print("=" * 50)
    
    try:
        # Test the cutoff generation function
        from datetime import datetime
        test_date = datetime(2025, 1, 15)
        cutoff_result = ea.generate_cut_off(test_date, 7)
        print(f"✅ Cutoff generation test: {test_date} with cutoff_day=7 -> {cutoff_result}")
        
        # Test column name generation
        consumption_col = ea.generate_consumption_column_name("Test Load")
        power_col = ea.generate_power_column_name("Test Load")
        print(f"✅ Column name generation:")
        print(f"   Consumption: {consumption_col}")
        print(f"   Power: {power_col}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def run_all_tests():
    """Run all tests"""
    print("🚀 Running All Tests for Refactored Classes")
    print("=" * 60)
    
    test_compute_energy_functions()
    test_single_file_report()
    test_onepager_only()
    # test_folder_reports()  # Commented out to avoid generating too many reports
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    run_all_tests()
