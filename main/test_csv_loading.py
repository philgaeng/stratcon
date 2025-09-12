#!/usr/bin/env python3
"""
Simple test to check CSV loading
"""

import pandas as pd
import os

def test_csv_loading():
    print("🔍 Testing CSV Loading")
    print("=" * 30)
    
    # Test file path
    data_path = "/home/philg/projects/stratcon/downloads/Neo3/NEO3 - 18&19- Electricity consumption - 2025-01-01 - 2025-12-31 - 5 minutes.csv"
    
    print(f"📁 File path: {data_path}")
    print(f"📁 File exists: {os.path.exists(data_path)}")
    
    if not os.path.exists(data_path):
        print("❌ File not found!")
        return
    
    try:
        print("\n🔍 Reading CSV with pandas...")
        df = pd.read_csv(data_path, 
                        delimiter=',', 
                        decimal=',',
                        thousands='.',
                        parse_dates=['Date'])
        
        print(f"✅ CSV loaded successfully!")
        print(f"📊 Shape: {df.shape}")
        print(f"📊 Columns: {list(df.columns)}")
        print(f"📅 Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"📊 First few rows:")
        print(df.head())
        
        # Test path parsing
        print(f"\n🔍 Testing path parsing...")
        path_parts = data_path.split('/')
        client_name = path_parts[-2] if len(path_parts) >= 2 else "Unknown"
        filename = path_parts[-1]
        client_detail_name = filename.split('- Electricity consumption')[0] if '- Electricity consumption' in filename else filename.replace('.csv', '')
        
        print(f"📁 Client name: {client_name}")
        print(f"📁 Client detail name: {client_detail_name}")
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_csv_loading()
