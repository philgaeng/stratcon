#!/usr/bin/env python3
"""Reporting API routes."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from backend.services.domain.reporting import (
    generate_report_for_tenant_artifacts,
    generate_reports_for_client,
    execute_last_records_job,
    execute_billing_info_job,
)
from backend.services.domain.reporting.settings_helpers import (
    get_all_client_settings,
    get_cutoff_datetime,
    set_client_settings,
    set_tenant_settings,
)
from backend.services.core.config import DEFAULT_CLIENT
from backend.services.data.db_manager import DbQueries
from backend.services.services.email import send_report_email
from backend.services.core.utils import ReportLogger


@dataclass
class UserScope:
    user_id: Optional[int]
    epc_ids: List[int]
    client_ids: List[int]
    tenant_ids: List[int]


def _normalize_ids(value: Optional[Any]) -> List[int]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        result: List[int] = []
        for item in value:
            if item is None:
                continue
            try:
                result.append(int(cast(Any, item)))
            except (TypeError, ValueError):
                continue
        return result
    try:
        return [int(cast(Any, value))]
    except (TypeError, ValueError):
        return []


def _parse_user_id(raw_value: Optional[str], *, source: str) -> Optional[int]:
    if raw_value is None:
        return None
    candidate = raw_value.strip()
    if not candidate:
        return None
    try:
        return int(candidate)
    except ValueError as exc:  # pragma: no cover - input validation
        raise HTTPException(status_code=400, detail=f"Invalid {source}: {raw_value}") from exc


def _get_user_scope(request: Request) -> UserScope:
    header_user_id = request.headers.get("x-user-id") or request.headers.get("x-userid")
    user_id = _parse_user_id(header_user_id, source="X-User-Id header")
    if user_id is None:
        query_user_id = request.query_params.get("user_id")
        user_id = _parse_user_id(query_user_id, source="user_id query parameter")

    if user_id is None:
        return UserScope(user_id=None, epc_ids=[], client_ids=[], tenant_ids=[])

    info = DbQueries.get_info_for_user(user_id)
    epc_ids = sorted(set(_normalize_ids(info.get("epc_id"))))
    client_ids = _normalize_ids(info.get("client_id"))
    tenant_ids = sorted(set(_normalize_ids(info.get("tenant_id"))))

    for tenant_id in tenant_ids:
        client_id = DbQueries.get_client_id_for_tenant(tenant_id)
        if client_id is not None:
            client_ids.append(client_id)

    client_ids = sorted({client_id for client_id in client_ids if client_id is not None})

    return UserScope(
        user_id=user_id,
        epc_ids=epc_ids,
        client_ids=client_ids,
        tenant_ids=tenant_ids,
    )


def _resolve_client(client_token: str) -> Dict[str, Any]:
    lookup: Optional[Dict[str, Any]] = None
    if client_token.isdigit():
        lookup = DbQueries.get_client_by_id(int(client_token))
    if lookup is None:
        lookup = DbQueries.get_client_by_name(client_token)
    if lookup is None:
        raise HTTPException(status_code=404, detail=f"Client '{client_token}' not found.")
    return lookup


def _ensure_client_access(scope: UserScope, client_id: int) -> None:
    if scope.user_id is None:
        return
    if not scope.client_ids:
        raise HTTPException(
            status_code=403,
            detail="Current user does not have access to any clients.",
        )
    if client_id not in scope.client_ids:
        raise HTTPException(
            status_code=403,
            detail="Current user does not have access to the requested client.",
        )


def _execute_report_job(
    *,
    tenant_id: int,
    client_id: int,
    client_name: str,
    tenant_name: str,
    user_email: Optional[str],
    source: str,
    output_dir: Optional[Path],
    start_date: Optional[Any],
    end_date: Optional[Any],
    month: Optional[str],
    cutoff_datetime: Optional[Any],
) -> None:
    """Background task that generates a report and emails it if requested."""
    logger = ReportLogger()
    try:
        report_path, metadata, _html = generate_report_for_tenant_artifacts(
            tenant_id=tenant_id,
            client_id=client_id,
            output_dir=output_dir,
            start_date=start_date,
            end_date=end_date,
            source=source,
            logger=logger,
        )
        logger.info(
            f"✅ Report generated for tenant {metadata.get('tenant_name', tenant_name)} ({tenant_id}) at {report_path}"
        )

        if user_email:
            logger.debug(f"sending report email to {user_email} for client {metadata.get('client_name') or client_name} and tenant {metadata.get('tenant_name') or tenant_name} with last month {metadata.get('last_month') or month}")
            success = send_report_email(
                email=user_email,
                client_name=metadata.get("client_name") or client_name,
                tenant_name=metadata.get("tenant_name") or tenant_name,
                last_month=metadata.get("last_month") or month,
                attachments=[report_path],
                logger=logger,
            )
            if success:
                logger.info(f"📬 Email sent to {user_email}")
            else:
                logger.warning(f"⚠️ Failed to send report email to {user_email}")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"❌ Error generating report for tenant {tenant_id}: {exc}")


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


class ClientReportRequest(BaseModel):
    client_token: str = DEFAULT_CLIENT
    loads_summary_path: Optional[str] = None


@reporting_router.get("/clients", response_model=dict)
async def get_clients(request: Request):
    scope = _get_user_scope(request)
    client_filter = None if scope.user_id is None else scope.client_ids
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

    tenant_token = request.tenant_token
    tenant_row: Optional[Dict[str, Any]] = None
    if tenant_token.isdigit():
        tenant_row = DbQueries.get_tenant_by_id(int(tenant_token))
        if tenant_row is None or tenant_row["client_id"] != client_id:
            raise HTTPException(
                status_code=404,
                detail=f"Tenant '{tenant_token}' not found for client '{client_row['name']}'.",
            )
    else:
        tenant_row = DbQueries.get_tenant_by_name(client_id=client_id, tenant_name=tenant_token)
        if tenant_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Tenant '{tenant_token}' not found for client '{client_row['name']}'.",
            )

    tenant_id = tenant_row["id"]
    if scope.tenant_ids and tenant_id not in scope.tenant_ids:
        raise HTTPException(
            status_code=403,
            detail="Current user does not have access to the requested tenant.",
        )

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

        logger.debug(
            f"Queueing tenant report job for client {client_row['name']} ({client_id}), "
            f"tenant {tenant_row['name']} ({tenant_id}), month={request.month or 'all'}, "
            f"user_email={request.user_email or 'none'}"
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
):
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


