#!/usr/bin/env python3
"""Reporting API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from backend.api.api_helpers import (
    AUTH_BYPASS_SCOPE,
    UserScope,
    _ensure_client_access,
    _execute_report_job,
    _get_user_scope,
    _resolve_client,
    _resolve_tenant_for_client,
)
from backend.services.core.config import DEFAULT_CLIENT
from backend.services.core.utils import ReportLogger
from backend.services.data.db_manager import DbQueries
from backend.services.domain.reporting import (
    generate_reports_for_client,
    execute_last_records_job,
    execute_billing_info_job,
    execute_billing_comparison_job,
)
from backend.services.domain.reporting.settings_helpers import (
    get_all_client_settings,
    get_cutoff_datetime,
    set_client_settings,
    set_tenant_settings,
)


reporting_router = APIRouter(tags=["Reporting"])


class TenantReportRequest(BaseModel):
    tenant_token: str
    client_token: Optional[str] = DEFAULT_CLIENT
    loads_summary_path: Optional[str] = None
    month: Optional[str] = None  # Format: YYYY-MM
    cutoff_date: Optional[str] = None  # Format: YYYY-MM-DD
    cutoff_time: Optional[str] = None  # Format: HH:mm
    start_date: Optional[str] = None  # Format: YYYY-MM-DD
    start_time: Optional[str] = None  # Format: HH:mm
    end_date: Optional[str] = None  # Format: YYYY-MM-DD
    end_time: Optional[str] = None  # Format: HH:mm
    user_email: Optional[str] = None  # Email to send report to
    floor: Optional[int] = None
    unit_id: Optional[int] = None
    load_ids: Optional[List[int]] = None


class ClientReportRequest(BaseModel):
    client_token: str = DEFAULT_CLIENT
    loads_summary_path: Optional[str] = None


@reporting_router.get("/clients", response_model=dict)
async def get_clients(request: Request):
    # Check if user is super_admin - if so, return all clients
    from backend.services.auth.permissions import get_user_role_from_request, UserRole
    user_role = get_user_role_from_request(request)
    
    if user_role == UserRole.SUPER_ADMIN:
        # Super admin sees all clients
        client_filter = None
    else:
        # Regular users see only their assigned clients
        scope = _get_user_scope(request)
        client_filter = None if not scope.client_ids else scope.client_ids
    
    try:
        clients = DbQueries.list_clients(client_ids=client_filter)
        return {
            "clients": [client["name"] for client in clients],
            "count": len(clients),
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to list clients: {exc}")


@reporting_router.get("/buildings", response_model=dict)
async def get_buildings(request: Request, client_token: str = DEFAULT_CLIENT):
    scope = _get_user_scope(request)
    client_row = _resolve_client(client_token)
    client_id = client_row["id"]
    _ensure_client_access(scope, client_id)

    building_filter: Optional[List[int]] = None
    if scope.tenant_ids:
        building_ids: set[int] = set()
        for tenant_id in scope.tenant_ids:
            tenant_client = DbQueries.get_client_id_for_tenant(tenant_id)
            if tenant_client != client_id:
                continue
            building_id = DbQueries.get_building_id_for_tenant(tenant_id)
            if building_id is not None:
                building_ids.add(building_id)
        if building_ids:
            building_filter = sorted(building_ids)

    try:
        buildings = DbQueries.list_buildings_for_client(
            client_id=client_id,
            building_ids=building_filter,
        )
        return {
            "client": client_row["name"],
            "buildings": [building["name"] for building in buildings],
            "count": len(buildings),
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to list buildings: {exc}")


@reporting_router.get("/tenants", response_model=dict)
async def get_tenants(request: Request, client_token: str = DEFAULT_CLIENT):
    scope = _get_user_scope(request)
    client_row = _resolve_client(client_token)
    client_id = client_row["id"]
    _ensure_client_access(scope, client_id)

    tenant_filter: Optional[List[int]] = None
    if scope.tenant_ids:
        tenant_filter = [
            tenant_id
            for tenant_id in scope.tenant_ids
            if DbQueries.get_client_id_for_tenant(tenant_id) == client_id
        ]
        if not tenant_filter:
            return {"client": client_row["name"], "tenants": [], "count": 0}

    try:
        tenants = DbQueries.list_tenants_for_client(
            client_id=client_id,
            tenant_ids=tenant_filter,
        )
        return {
            "client": client_row["name"],
            "tenants": [tenant["name"] for tenant in tenants],
            "count": len(tenants),
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to list tenants: {exc}")


@reporting_router.get("/tenant/floors", response_model=dict)
async def get_tenant_floors_for_reports(
    request: Request,
    client_token: str = DEFAULT_CLIENT,
    tenant_token: str = "",
):
    if not tenant_token:
        raise HTTPException(status_code=400, detail="tenant_token is required")

    scope = _get_user_scope(request)
    client_row = _resolve_client(client_token)
    _ensure_client_access(scope, client_row["id"])
    tenant_row = _resolve_tenant_for_client(
        scope=scope,
        client_row=client_row,
        tenant_token=tenant_token,
    )
    tenant_id = tenant_row["id"]
    try:
        floors = DbQueries.get_floors_for_tenant(
            tenant_id,
            tenant_token=tenant_token,
        )
        return {
            "tenant_id": tenant_id,
            "tenant": tenant_row["name"],
            "floors": floors,
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to list floors: {exc}")


@reporting_router.get("/tenant/units", response_model=dict)
async def get_tenant_units_for_reports(
    request: Request,
    client_token: str = DEFAULT_CLIENT,
    tenant_token: str = "",
    floor: Optional[int] = None,
):
    if not tenant_token:
        raise HTTPException(status_code=400, detail="tenant_token is required")

    scope = _get_user_scope(request)
    client_row = _resolve_client(client_token)
    _ensure_client_access(scope, client_row["id"])
    tenant_row = _resolve_tenant_for_client(
        scope=scope,
        client_row=client_row,
        tenant_token=tenant_token,
    )
    tenant_id = tenant_row["id"]

    try:
        units = DbQueries.get_units_for_tenant(
            tenant_id,
            floor=floor,
            tenant_token=tenant_token,
        )
        return {
            "tenant_id": tenant_id,
            "tenant": tenant_row["name"],
            "units": units,
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to list units: {exc}")


@reporting_router.post("/reports/tenant", response_model=dict)
async def generate_tenant_reports(
    request: TenantReportRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
):
    scope = _get_user_scope(fastapi_request)
    client_row = _resolve_client(request.client_token or DEFAULT_CLIENT)
    client_id = client_row["id"]
    _ensure_client_access(scope, client_id)
    logger = ReportLogger()

    tenant_row = _resolve_tenant_for_client(
        scope=scope,
        client_row=client_row,
        tenant_token=request.tenant_token,
    )
    tenant_id = tenant_row["id"]

    try:
        loads_summary_path = (
            Path(request.loads_summary_path) if request.loads_summary_path else None
        )

        from datetime import datetime
        from backend.services.core.config import PHILIPPINES_TZ

        cutoff_datetime = None
        if request.cutoff_date and request.cutoff_time:
            cutoff_datetime_str = f"{request.cutoff_date} {request.cutoff_time}"
            try:
                cutoff_datetime = datetime.strptime(cutoff_datetime_str, "%Y-%m-%d %H:%M")
                cutoff_datetime = PHILIPPINES_TZ.localize(cutoff_datetime)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cutoff_date or cutoff_time format: {exc}",
                ) from exc

        start_datetime = None
        if request.start_date and request.start_time:
            start_datetime_str = f"{request.start_date} {request.start_time}"
            try:
                start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
                start_datetime = PHILIPPINES_TZ.localize(start_datetime)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date or start_time format: {exc}",
                ) from exc

        end_datetime = None
        if request.end_date and request.end_time:
            end_datetime_str = f"{request.end_date} {request.end_time}"
            try:
                end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                end_datetime = PHILIPPINES_TZ.localize(end_datetime)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date or end_time format: {exc}",
                ) from exc

        selected_load_ids: Optional[List[int]] = None
        if request.load_ids:
            selected_load_ids = [
                int(load_id)
                for load_id in request.load_ids
                if load_id is not None
            ]
            if not selected_load_ids:
                raise HTTPException(status_code=400, detail="load_ids cannot be empty")
        elif request.unit_id is not None:
            selected_load_ids = DbQueries.find_load_ids_by_unit(request.unit_id)
            if not selected_load_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"No loads found for unit_id={request.unit_id}",
                )
        elif request.floor is not None:
            selected_load_ids = DbQueries.find_load_ids_by_tenant_floor(
                tenant_id=tenant_id,
                floor=request.floor,
            )
            if not selected_load_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"No loads found for tenant '{tenant_row['name']}' on floor {request.floor}",
                )

        logger.debug(
            f"Queueing tenant report job for client {client_row['name']} ({client_id}), "
            f"tenant {tenant_row['name']} ({tenant_id}), month={request.month or 'all'}, "
            f"user_email={request.user_email or 'none'}, "
            f"floor={request.floor if request.floor is not None else 'all'}, "
            f"unit_id={request.unit_id if request.unit_id is not None else 'all'}"
        )
        background_tasks.add_task(
            _execute_report_job,
            tenant_id=tenant_id,
            client_id=client_id,
            client_name=client_row["name"],
            tenant_name=tenant_row["name"],
            user_email=request.user_email,
            source="meter_records",
            output_dir=None,
            start_date=start_datetime,
            end_date=end_datetime,
            month=request.month,
            cutoff_datetime=cutoff_datetime,
            load_ids=selected_load_ids,
        )

        logger.info(
            f"✅ Tenant report job queued for {tenant_row['name']} ({tenant_id})"
            + (f" with email {request.user_email}" if request.user_email else " without email delivery"),
        )

        return {
            "status": "started",
            "message": f"Report generation started for tenant: {tenant_row['name']}",
            "client": client_row["name"],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to start report generation: {exc}")


@reporting_router.post("/reports/client", response_model=dict)
async def generate_client_reports(
    request: ClientReportRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
):
    scope = _get_user_scope(fastapi_request)
    try:
        loads_summary_path = (
            Path(request.loads_summary_path) if request.loads_summary_path else None
        )

        background_tasks.add_task(
            generate_reports_for_client,
            request.client_token,
            loads_summary_path=loads_summary_path,
        )

        return {
            "status": "started",
            "message": f"Report generation started for client: {request.client_token}",
            "client": request.client_token,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to start report generation: {exc}")




class LastRecordsRequest(BaseModel):
    client_token: str = DEFAULT_CLIENT
    user_email: str  # Email to send report to


class BillingInfoRequest(BaseModel):
    client_token: str = DEFAULT_CLIENT
    user_email: str  # Email to send report to


class BillingComparisonRequest(BaseModel):
    client_token: str = DEFAULT_CLIENT
    user_email: str


@reporting_router.post("/reports/generate_last_records", response_model=dict)
async def generate_last_records(
    request: LastRecordsRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
):
    """Generate and email the last records CSV for a client."""
    scope = _get_user_scope(fastapi_request)
    client_row = _resolve_client(request.client_token or DEFAULT_CLIENT)
    client_id = client_row["id"]
    _ensure_client_access(scope, client_id)
    
    logger = ReportLogger()
    logger.info(
        f"Queueing last records job for client {client_row['name']} ({client_id}), "
        f"email={request.user_email}"
    )
    
    background_tasks.add_task(
        execute_last_records_job,
        client_id=client_id,
        client_name=client_row["name"],
        user_email=request.user_email,
    )
    
    return {
        "status": "started",
        "message": f"Last records generation started for client: {client_row['name']}",
        "client": client_row["name"],
    }


@reporting_router.post("/reports/generate_billing_info", response_model=dict)
async def generate_billing_info(
    request: BillingInfoRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
):
    """Generate and email the billing info CSV for a client."""
    scope = _get_user_scope(fastapi_request)
    client_row = _resolve_client(request.client_token or DEFAULT_CLIENT)
    client_id = client_row["id"]
    _ensure_client_access(scope, client_id)
    
    logger = ReportLogger()
    logger.info(
        f"Queueing billing info job for client {client_row['name']} ({client_id}), "
        f"email={request.user_email}"
    )
    
    background_tasks.add_task(
        execute_billing_info_job,
        client_id=client_id,
        client_name=client_row["name"],
        user_email=request.user_email,
    )
    
    return {
        "status": "started",
        "message": f"Billing info generation started for client: {client_row['name']}",
        "client": client_row["name"],
    }


@reporting_router.get("/debug/auth-scope")
async def debug_auth_scope():
    return {"AUTH_BYPASS_SCOPE": AUTH_BYPASS_SCOPE}


@reporting_router.post("/reports/generate_billing_comparison", response_model=dict)
async def generate_billing_comparison(
    request: BillingComparisonRequest,
    background_tasks: BackgroundTasks,
    fastapi_request: Request,
):
    """Generate and email the billing comparison CSV for a client."""
    # Print to stdout (visible in server terminal) for immediate debugging
    print(f"[DEBUG] generate_billing_comparison called - client_token: {request.client_token}, user_email: {request.user_email}")
    
    logger = ReportLogger()
    logger.info(f"🔔 generate_billing_comparison endpoint called - client_token: {request.client_token}, user_email: {request.user_email}")
    
    try:
        scope = _get_user_scope(fastapi_request)
        logger.debug(f"User scope resolved: {scope}")
        
        client_row = _resolve_client(request.client_token or DEFAULT_CLIENT)
        client_id = client_row["id"]
        logger.debug(f"Client resolved: {client_row['name']} (ID: {client_id})")
        
        _ensure_client_access(scope, client_id)
        logger.debug(f"Client access verified for user scope")

        logger.info(
            f"Queueing billing comparison job for client {client_row['name']} ({client_id}), "
            f"email={request.user_email}"
        )
    except Exception as exc:
        logger.error(f"❌ Error in generate_billing_comparison: {exc}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

    background_tasks.add_task(
        execute_billing_comparison_job,
        client_id=client_id,
        client_name=client_row["name"],
        user_email=request.user_email,
    )

    return {
        "status": "started",
        "message": f"Billing comparison generation started for client: {client_row['name']}",
        "client": client_row["name"],
    }


class ClientSettingsRequest(BaseModel):
    client_token: str
    cutoff_day: int
    cutoff_hour: int = 23
    cutoff_minute: int = 59
    cutoff_second: int = 59


@reporting_router.post("/settings/client")
async def update_client_settings(request: ClientSettingsRequest):
    try:
        set_client_settings(
            client_token=request.client_token,
            cutoff_day=request.cutoff_day,
            cutoff_hour=request.cutoff_hour,
            cutoff_minute=request.cutoff_minute,
            cutoff_second=request.cutoff_second,
        )
        return {"status": "success", "message": f"Settings updated for client: {request.client_token}"}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {exc}")


class TenantSettingsRequest(BaseModel):
    client_token: str
    tenant_token: str
    cutoff_day: Optional[int] = None
    cutoff_hour: Optional[int] = None
    cutoff_minute: Optional[int] = None
    cutoff_second: Optional[int] = None


@reporting_router.post("/settings/tenant")
async def update_tenant_settings(request: TenantSettingsRequest):
    try:
        set_tenant_settings(
            client_token=request.client_token,
            tenant_token=request.tenant_token,
            cutoff_day=request.cutoff_day,
            cutoff_hour=request.cutoff_hour,
            cutoff_minute=request.cutoff_minute,
            cutoff_second=request.cutoff_second,
        )
        return {
            "status": "success",
            "message": f"Settings updated for tenant: {request.client_token}/{request.tenant_token}",
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {exc}")


@reporting_router.get("/settings/client/{client_token}")
async def get_client_settings(client_token: str):
    try:
        return get_all_client_settings(client_token)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {exc}")


@reporting_router.get("/settings/cutoff")
async def get_cutoff_settings(
    client_token: str,
    tenant_token: Optional[str] = None,
    load_name: Optional[str] = None,
):
    try:
        cutoff_dt = get_cutoff_datetime(
            client_token=client_token,
            tenant_token=tenant_token,
            load_name=load_name,
        )

        if cutoff_dt is None:
            return {
                "cutoff_datetime": None,
                "message": "No cutoff settings found, using defaults",
            }

        return {
            "cutoff_day": cutoff_dt.day,
            "cutoff_hour": cutoff_dt.hour,
            "cutoff_minute": cutoff_dt.minute,
            "cutoff_second": cutoff_dt.second,
            "cutoff_time": f"{cutoff_dt.hour:02d}:{cutoff_dt.minute:02d}:{cutoff_dt.second:02d}",
        }
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to get cutoff settings: {exc}")


