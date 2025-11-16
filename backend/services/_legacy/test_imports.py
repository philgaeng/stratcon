#!/usr/bin/env python3
"""
Simple test to verify imports work from within services directory
"""

import sys
import os

print("🔍 Testing imports from services directory...")
print("=" * 50)

try:
    # Test direct imports (since we're in the services directory)
    from config import DEFAULT_REPORTS_DIR, ReportStyle
    print("✅ Config imports work")
    
    from utils import ReportLogger
    print("✅ Utils imports work")
    
    from data_preparation import DataPreparationOrchestrator
    print("✅ Data preparation orchestrator import works")
    
    from electricity_analysis import ElectricityAnalysisOrchestrator
    print("✅ Electricity analysis orchestrator import works")
    
    from reporting import ReportingOrchestrator
    print("✅ Reporting orchestrator import works")
    
    # Test functionality
    print("\n🔍 Testing basic functionality...")
    logger = ReportLogger()
    logger.info("Test log message")
    print("✅ ReportLogger works")
    
    orchestrator = ReportingOrchestrator(client_id=1, logger=logger)
    print("✅ ReportingOrchestrator instantiation works")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
