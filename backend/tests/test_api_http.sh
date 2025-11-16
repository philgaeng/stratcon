#!/bin/bash
# HTTP API Test Script for Phase 1

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "Testing Phase 1 API Endpoints"
echo "=========================================="

echo ""
echo "1. Testing GET / (Root endpoint)"
echo "--------------------------------"
curl -s "$BASE_URL/" | python3 -m json.tool
echo ""

echo "2. Testing GET /clients"
echo "--------------------------------"
curl -s "$BASE_URL/clients" | python3 -m json.tool
echo ""

echo "3. Testing GET /tenants (default client)"
echo "--------------------------------"
curl -s "$BASE_URL/tenants" | python3 -m json.tool
echo ""

echo "4. Testing GET /tenants?client_token=NEO"
echo "--------------------------------"
curl -s "$BASE_URL/tenants?client_token=NEO" | python3 -m json.tool
echo ""

echo "5. Testing POST /reports/tenant (dry run - without email)"
echo "--------------------------------"
curl -s -X POST "$BASE_URL/reports/tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_token": "NEO3_0708",
    "client_token": "NEO"
  }' | python3 -m json.tool
echo ""

echo "6. Testing POST /reports/tenant with month and cutoff"
echo "--------------------------------"
curl -s -X POST "$BASE_URL/reports/tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_token": "NEO3_0708",
    "client_token": "NEO",
    "month": "2025-01",
    "cutoff_date": "2025-01-15",
    "cutoff_time": "23:59"
  }' | python3 -m json.tool
echo ""

echo "=========================================="
echo "Tests complete!"
echo "=========================================="
echo ""
echo "Note: Report generation runs in background."
echo "Check logs/ directory for report generation progress."

