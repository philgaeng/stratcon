# Electricity Analysis Refactoring Summary

## Overview

The `electricity_analysis.py` module has been refactored from a single `ComputeEnergy` class into two separate classes with distinct responsibilities:

1. **`ComputeEnergy`** - Handles energy calculations and data processing
2. **`GenerateReport`** - Handles report generation and data preparation

## Class Structure

### ComputeEnergy Class

**Purpose**: Energy calculations and data processing

**Key Methods**:

- `generate_cut_off(date, cutoff_day)` - Generate cutoff month for a date
- `generate_cut_off_month_column(df, cutoff_day)` - Add cutoff month column to DataFrame
- `select_full_months_by_day(year, month, missing_days, warning_only)` - Validate month completeness
- `select_full_months(df, warning_only)` - Select complete months from data
- `compute_energy(df)` - Calculate energy consumption from power data
- `check_data_completeness(df, strict)` - Validate data quality
- `init_interval_and_alarm_levels(df)` - Set up time interval calculations
- `generate_summary_energy(data, cutoff_day)` - Generate energy summaries
- `draw_energy_kWh_per_month(month_data)` - Create monthly energy charts
- `draw_energy_kWh_per_day(day_data)` - Create daily energy charts
- `generate_report(...)` - Generate HTML reports
- `generate_onepager_report(df, loads_data_path)` - Generate one-pager reports

### GenerateReport Class

**Purpose**: Report generation and data preparation

**Key Methods**:

- `load_and_prepare_data(path, cutoff_day)` - Load and prepare CSV data
- `select_loads(df)` - Identify power columns from DataFrame
- `generate_single_file_report(data_path, loads_summary_path, cutoff_day, strict)` - Generate report for one file
- `generate_onepager_only(data_path, loads_summary_path, cutoff_day)` - Generate only one-pager
- `generate_reports_for_folder(folder_path, loads_summary_path, strict)` - Generate reports for all files in folder

## Usage Examples

### Single File Report

```python
from electricity_analysis import report_generator

# Generate full report for one file
report_path = report_generator.generate_single_file_report(
    data_path="/path/to/data.csv",
    loads_summary_path=None,
    cutoff_day=7,
    strict=False
)
```

### One-Pager Only

```python
# Generate only the one-pager report (faster)
report_path = report_generator.generate_onepager_only(
    data_path="/path/to/data.csv",
    loads_summary_path=None,
    cutoff_day=7
)
```

### Folder Reports

```python
# Generate reports for all CSV files in a folder
report_paths = report_generator.generate_reports_for_folder(
    folder_path="/path/to/folder",
    loads_summary_path="/path/to/loads_summary.csv",
    strict=False
)
```

### Direct Energy Computation

```python
from electricity_analysis import ea

# Use ComputeEnergy class directly for calculations
cutoff_month = ea.generate_cut_off(datetime(2025, 1, 15), cutoff_day=7)
consumption_col = ea.generate_consumption_column_name("Main Load")
```

## Key Benefits

1. **Separation of Concerns**: Energy computation is separate from report generation
2. **Individual File Processing**: Can generate reports for single files instead of all files
3. **Flexible Report Types**: Choose between full analysis or one-pager only
4. **Reusable Components**: ComputeEnergy class can be used independently
5. **Better Maintainability**: Clearer code organization and responsibilities

## Backward Compatibility

The refactored code maintains backward compatibility by:

- Keeping the same function signatures where possible
- Setting necessary attributes in ComputeEnergy instance from GenerateReport
- Providing both `ea` (ComputeEnergy) and `report_generator` (GenerateReport) instances

## Files Created

- `test_refactored_classes.py` - Test script for the new structure
- `example_usage.py` - Usage examples for the refactored classes
- `REFACTORING_SUMMARY.md` - This documentation

## Migration Guide

### Old Usage (Single Class)

```python
from electricity_analysis import ea

# Old way - process all files
ea.run(path, loads_summary_path, strict=False)
```

### New Usage (Separated Classes)

```python
from electricity_analysis import report_generator

# New way - process individual files
report_path = report_generator.generate_single_file_report(
    data_path=path,
    loads_summary_path=loads_summary_path,
    strict=False
)

# Or process all files in folder
report_paths = report_generator.generate_reports_for_folder(
    folder_path=folder_path,
    loads_summary_path=loads_summary_path,
    strict=False
)
```

## Testing

Run the test script to verify the refactored functionality:

```bash
python test_refactored_classes.py
```

Run the usage examples:

```bash
python example_usage.py
```
