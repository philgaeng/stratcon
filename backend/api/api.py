#!/usr/bin/env python3
"""
Application bootstrap that wires reporting and meter logging routers.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend package is importable when run as script
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables from env.local if available
try:  # pragma: no cover - optional convenience
    from load_env import load_env_local

    load_env_local()
except ImportError:
    pass

from .api_reporting import reporting_router
from .api_meter_logging import meter_router
from .api_user_management import user_router
from backend.middleware.auth_middleware import AuthMiddleware

app = FastAPI(
    title="Electricity Report Generation API",
    description="API for generating electricity consumption reports and manual meter logs.",
    version="1.0.0",
)

# Add CORS middleware first (runs last, wraps everything to ensure CORS headers on all responses)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://52.221.59.184",  # AWS server IP
        "http://52.221.59.184:3000",  # If frontend runs on same server
        "http://52.221.59.184:8000",  # Direct API access
        # Add more origins as needed for demo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware (runs before CORS, but CORS wraps it)
app.add_middleware(AuthMiddleware)

app.include_router(reporting_router)
app.include_router(meter_router)
app.include_router(user_router)


@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "message": "Electricity Report Generation API",
        "version": "1.0.0",
        "endpoints": {
            # Reporting API endpoints
            "GET /clients": "List accessible clients for the authenticated user",
            "GET /buildings": "List buildings for a client (user-scoped)",
            "GET /tenants": "List tenants for a client (user-scoped)",
            "POST /reports/tenant": "Generate reports for a specific tenant",
            "POST /reports/client": "Generate reports for all tenants under a client",
            "POST /reports/generate_last_records": "Generate and email the last records CSV for a client",
            "POST /reports/generate_billing_info": "Generate and email the billing info CSV for a client",
            "POST /settings/client": "Update client settings (cutoff day/time)",
            "POST /settings/tenant": "Update tenant settings (cutoff day/time)",
            "GET /settings/client/{client_token}": "Get all settings for a client",
            "GET /settings/cutoff": "Get cutoff datetime settings for a client/tenant/load",
            
            # Meter Logging API endpoints
            "GET /meters/v1/buildings": "Get buildings assigned to a user (requires user_id query param)",
            "GET /meters/v1/buildings/{building_id}/tenants": "Get tenants for a specific building",
            "GET /meters/v1/tenants": "List tenants available for manual meter logging (requires client_id query param)",
            "GET /meters/v1/tenants/{tenant_id}/floors": "Get distinct floors for a tenant",
            "GET /meters/v1/tenants/{tenant_id}/meters": "List meters assigned to a tenant (optional floor filter)",
            "POST /meters/v1/records": "Submit manual meter readings (bulk-friendly)",
            "POST /meters/v1/approvals": "Attach approval (name/signature) to a meter record session",
            "GET /meters/v1/meter-records": "Get meter record history (filter by tenant_id or meter_id)",
            "GET /meters/v1/user-id": "Get user ID from email address",
            "GET /meters/v1/user-info": "Get user information (ID, role, entity_id) from email address",
            "GET /meters/v1/meta": "Get meter logging API metadata (version, server time, etc.)",
            
            # User Management API endpoints
            "GET /settings/users": "List all users (requires SUPER_ADMIN or CLIENT_ADMIN)",
            "GET /settings/users/{user_id}": "Get a specific user by ID (requires SUPER_ADMIN or CLIENT_ADMIN)",
            "POST /settings/users": "Create a new user (requires SUPER_ADMIN or CLIENT_ADMIN)",
            "PUT /settings/users/{user_id}": "Update an existing user (requires SUPER_ADMIN or CLIENT_ADMIN)",
            "DELETE /settings/users/{user_id}": "Delete a user (soft delete, requires SUPER_ADMIN)",
            "GET /settings/users/roles": "Get all available roles and their permissions",
            "GET /settings/users/roles/{role_name}": "Get information about a specific role",
        },
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

