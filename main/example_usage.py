#!/usr/bin/env python3
"""
Example usage of the refactored electricity analysis classes
"""

import sys
sys.path.append('.')

from electricity_analysis import report_generator, ea

def example_single_file_report():
    """Example: Generate a report for a single file"""
    print("📋 Example: Single File Report Generation")
    print("-" * 40)
    
    # Path to your data file
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    # Generate full report (includes detailed analysis + one-pager)
    report_path = report_generator.generate_single_file_report(
        data_path=data_path,
        loads_summary_path=None,  # Optional: path to loads summary CSV
        cutoff_day=7,             # Cutoff day for month calculation
        strict=False              # Whether to be strict about data completeness
    )
    
    if report_path:
        print(f"✅ Report generated: {report_path}")
    else:
        print("❌ Report generation failed")

def example_onepager_only():
    """Example: Generate only the one-pager report (faster)"""
    print("\n📋 Example: One-Pager Only Report")
    print("-" * 40)
    
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - 07&08 - Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    # Generate only the one-pager report (faster, less detailed)
    report_path = report_generator.generate_onepager_only(
        data_path=data_path,
        loads_summary_path=None,
        cutoff_day=7
    )
    
    if report_path:
        print(f"✅ One-pager report generated: {report_path}")
    else:
        print("❌ One-pager report generation failed")

def example_folder_reports():
    """Example: Generate reports for all files in a folder"""
    print("\n📋 Example: Folder Report Generation")
    print("-" * 40)
    
    folder_path = "/home/philg/projects/stratcon/downloads/Neo3"
    loads_summary_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - loads_cutoff_dates.csv"
    
    # Generate reports for all CSV files in the folder
    report_paths = report_generator.generate_reports_for_folder(
        folder_path=folder_path,
        loads_summary_path=loads_summary_path,
        strict=False
    )
    
    if report_paths:
        print(f"✅ Generated {len(report_paths)} reports:")
        for i, path in enumerate(report_paths, 1):
            print(f"   {i}. {path}")
    else:
        print("❌ No reports were generated")

def example_direct_energy_computation():
    """Example: Use ComputeEnergy class directly for calculations"""
    print("\n📋 Example: Direct Energy Computation")
    print("-" * 40)
    
    # You can also use the ComputeEnergy class directly for calculations
    from datetime import datetime
    
    # Test cutoff calculation
    test_date = datetime(2025, 1, 15)
    cutoff_month = ea.generate_cut_off(test_date, cutoff_day=7)
    print(f"Cutoff calculation: {test_date} -> {cutoff_month}")
    
    # Test column name generation
    consumption_col = ea.generate_consumption_column_name("Main Load")
    power_col = ea.generate_power_column_name("Main Load")
    print(f"Column names: {consumption_col}, {power_col}")

if __name__ == "__main__":
    print("🚀 Electricity Analysis - Usage Examples")
    print("=" * 50)
    
    # Run examples
    example_single_file_report()
    example_onepager_only()
    # example_folder_reports()  # Uncomment to test folder processing
    example_direct_energy_computation()
    
    print("\n✅ Examples completed!")
    print("\n💡 Key Benefits of the Refactored Structure:")
    print("   • Separate concerns: energy computation vs report generation")
    print("   • Generate reports for individual files or entire folders")
    print("   • Choose between full analysis or one-pager only")
    print("   • Reusable ComputeEnergy class for direct calculations")
