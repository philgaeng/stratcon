#!/usr/bin/env python3
"""
Debug script to understand the timezone cutoff logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))

from datetime import datetime
import pytz
from electricity_analysis import ComputeEnergy

def debug_timezone_logic():
    """Debug the timezone cutoff logic"""
    
    compute_energy = ComputeEnergy()
    philippines_tz = pytz.timezone('Asia/Manila')
    
    # Test the exact case that's failing
    test_date = datetime(2024, 4, 14, 23, 59, 0)  # 2024-04-14 23:59:00
    cutoff_datetime = philippines_tz.localize(datetime(2024, 4, 14, 23, 59, 59))
    
    print(f"Test date: {test_date}")
    print(f"Cutoff datetime: {cutoff_datetime}")
    
    # Convert test_date to Philippines timezone
    if test_date.tzinfo is None:
        test_date_ph = philippines_tz.localize(test_date)
    else:
        test_date_ph = test_date.astimezone(philippines_tz)
    
    print(f"Test date in PH timezone: {test_date_ph}")
    print(f"Cutoff datetime in PH timezone: {cutoff_datetime}")
    
    # Create the comparison datetime
    date_year = test_date_ph.year
    date_month = test_date_ph.month
    cutoff_day = cutoff_datetime.day
    
    current_month_cutoff = philippines_tz.localize(
        datetime(date_year, date_month, cutoff_day, 
                cutoff_datetime.hour, cutoff_datetime.minute, cutoff_datetime.second)
    )
    
    print(f"Current month cutoff: {current_month_cutoff}")
    print(f"Test date < cutoff? {test_date_ph < current_month_cutoff}")
    print(f"Test date == cutoff? {test_date_ph == current_month_cutoff}")
    print(f"Test date > cutoff? {test_date_ph > current_month_cutoff}")
    
    # Test the actual method
    result = compute_energy.generate_cut_off(test_date, cutoff_datetime)
    print(f"Result: {result}")

if __name__ == "__main__":
    debug_timezone_logic()

