#!/usr/bin/env python3
"""
Test script for Phase 1 API endpoints.
Tests the new /clients endpoint and updated /reports/tenant endpoint.
"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

def test_list_clients():
    """Test GET /clients endpoint"""
    print("\n" + "="*60)
    print("TEST 1: GET /clients")
    print("="*60)
    
    try:
        from services.reporting.folder_helpers import list_client_folders
        
        clients = list_client_folders()
        print(f"✅ Found {len(clients)} clients:")
        for client in clients:
            print(f"   - {client.name}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_list_tenants():
    """Test GET /tenants endpoint"""
    print("\n" + "="*60)
    print("TEST 2: GET /tenants (for default client)")
    print("="*60)
    
    try:
        from services.reporting.folder_helpers import list_tenant_folders
        from services.config import DEFAULT_CLIENT
        
        tenants = list_tenant_folders(DEFAULT_CLIENT)
        print(f"✅ Found {len(tenants)} tenants for client '{DEFAULT_CLIENT}':")
        for tenant in tenants[:5]:  # Show first 5
            print(f"   - {tenant.name}")
        if len(tenants) > 5:
            print(f"   ... and {len(tenants) - 5} more")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_imports():
    """Test that API module can be imported"""
    print("\n" + "="*60)
    print("TEST 3: API Module Imports")
    print("="*60)
    
    try:
        import api
        print("✅ API module imported successfully")
        print(f"   FastAPI app: {api.app.title}")
        return True
    except Exception as e:
        print(f"❌ Error importing API: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_service_import():
    """Test email service import (with graceful boto3 handling)"""
    print("\n" + "="*60)
    print("TEST 4: Email Service Import")
    print("="*60)
    
    try:
        from services.email_service import send_report_email, BOTO3_AVAILABLE
        print(f"✅ Email service imported successfully")
        print(f"   boto3 available: {BOTO3_AVAILABLE}")
        if not BOTO3_AVAILABLE:
            print("   ⚠️  boto3 not installed - email functionality will not work")
            print("   Install with: pip install boto3")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints_structure():
    """Test that API endpoints are properly defined"""
    print("\n" + "="*60)
    print("TEST 5: API Endpoints Structure")
    print("="*60)
    
    try:
        import api
        
        # Check routes
        routes = [route.path for route in api.app.routes]
        print("✅ Available API routes:")
        for route in sorted(routes):
            print(f"   - {route}")
        
        # Check if new endpoints exist
        expected_routes = ["/", "/clients", "/tenants", "/reports/tenant"]
        missing = [r for r in expected_routes if r not in routes]
        if missing:
            print(f"⚠️  Missing routes: {missing}")
            return False
        else:
            print("✅ All expected routes found")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PHASE 1 API TESTS")
    print("="*60)
    
    tests = [
        ("List Clients", test_list_clients),
        ("List Tenants", test_list_tenants),
        ("API Imports", test_api_imports),
        ("Email Service", test_email_service_import),
        ("API Endpoints", test_api_endpoints_structure),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Phase 1 is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

