#!/usr/bin/env python3
"""Meter logging API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict

from backend.api.api_helpers import (
    _normalize_ids,
    _normalize_timestamp,
    _parse_user_id,
    _resolve_meter_pk_or_404,
)
from backend.services.data.db_manager import MeterLoggingDbQueries
from backend.services.auth.permissions import require_roles, UserRole


meter_router = APIRouter(prefix="/meters/v1", tags=["Meter Logging"])


class BuildingSummary(BaseModel):
    id: int
    name: str
    floor: Optional[int] = None


class TenantSummary(BaseModel):
    tenant_id: int
    tenant_name: str
    client_id: int
    building: BuildingSummary
    tenant_floors: int
    active_units: int
    last_record_at: Optional[str] = None


class TenantSummaryResponse(BaseModel):
    tenants: list[TenantSummary]


class UnitSummary(BaseModel):
    id: int
    unit_number: Optional[str] = None
    floor: Optional[int] = None


class MeterAssignmentLastRecord(BaseModel):
    timestamp_record: str
    meter_kWh: float


class MeterAssignment(BaseModel):
    meter_id: str
    meter_pk: int
    unit: UnitSummary
    loads: list[int]
    last_record: Optional[MeterAssignmentLastRecord] = None


class MeterAssignmentsResponse(BaseModel):
    tenant_id: int
    meters: list[MeterAssignment]


class MeterRecordInput(BaseModel):
    client_record_id: Optional[str] = None
    meter_id: str
    timestamp_record: datetime
    meter_kWh: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_record_id": "rec-001",
                "meter_id": "MTR-NEO3-1801",
                "timestamp_record": "2024-10-06T08:15:00+08:00",
                "meter_kWh": 356.2,
            }
        }
    )


class MeterRecordBatchRequest(BaseModel):
    tenant_id: int
    session_id: str
    encoder_user_id: Optional[int] = None
    records: list[MeterRecordInput]


class MeterRecordAccepted(BaseModel):
    client_record_id: str
    meter_record_id: Optional[int]
    status: str


class MeterRecordWarning(BaseModel):
    client_record_id: str
    type: str
    message: str


class MeterRecordBatchResponse(BaseModel):
    tenant_id: int
    session_id: str
    accepted: list[MeterRecordAccepted]
    warnings: list[MeterRecordWarning]


class ApprovalInfo(BaseModel):
    name: str
    signature_blob: Optional[str] = None


class ApprovalRequest(BaseModel):
    session_id: str
    tenant_id: int
    approver: ApprovalInfo


class MeterRecordHistoryItem(BaseModel):
    meter_record_id: int
    meter_id: str
    meter_pk: int
    tenant_id: int
    session_id: Optional[str] = None
    client_record_id: Optional[str] = None
    timestamp_record: str
    meter_kWh: float
    encoder_user_id: Optional[int] = None
    approver_name: Optional[str] = None
    approver_signature: Optional[str] = None
    created_at: str


class MeterRecordHistoryResponse(BaseModel):
    records: list[MeterRecordHistoryItem]


class MeterMetaResponse(BaseModel):
    version: str
    server_time: str
    non_decreasing_enforced: bool


class BuildingResponse(BaseModel):
    id: int
    name: str
    client_id: int


class BuildingsResponse(BaseModel):
    buildings: list[BuildingResponse]


class FloorSummary(BaseModel):
    floor: Optional[int]
    unit_count: int
    meter_count: int


class FloorsResponse(BaseModel):
    tenant_id: int
    floors: list[FloorSummary]




@meter_router.get("/buildings", response_model=BuildingsResponse)
# Note: Permission is enforced by AuthMiddleware via ROUTE_PERMISSIONS mapping
# Decorator is optional - only needed if this endpoint needs different permissions
async def list_buildings(
    request: Request,
    user_id: int = Query(..., description="User identifier"),
):
    """Get buildings assigned to the specified user."""
    try:
        # Check if user is super_admin via request state (set by middleware)
        if request and hasattr(request.state, "user_role") and request.state.user_role == UserRole.SUPER_ADMIN:
            buildings = MeterLoggingDbQueries.list_all_buildings()
        else:
            buildings = MeterLoggingDbQueries.list_buildings_for_user(user_id=user_id)
        return BuildingsResponse(
            buildings=[
                BuildingResponse(
                    id=b["id"],
                    name=b["name"],
                    client_id=b["client_id"],
                )
                for b in buildings
            ]
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list buildings: {exc}",
        )


@meter_router.get("/buildings/{building_id}/tenants", response_model=TenantSummaryResponse)
async def list_tenants_for_building(
    building_id: int,
):
    """Get tenants for a specific building."""
    try:
        summaries = MeterLoggingDbQueries.list_tenants_for_building(
            building_id=building_id,
        )
        
        tenants: list[TenantSummary] = []
        for summary in summaries:
            building_data = summary["building"]
            tenants.append(
                TenantSummary(
                    tenant_id=summary["tenant_id"],
                    tenant_name=summary["tenant_name"],
                    client_id=summary["client_id"],
                    building=BuildingSummary(
                        id=building_data["id"],
                        name=building_data["name"]
                    ),
                    tenant_floors=summary["number_of_floors"],
                    active_units=summary["active_units"],
                    last_record_at=_normalize_timestamp(summary.get("last_record_at")),
                )
            )
        return TenantSummaryResponse(tenants=tenants)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {exc}",
        )


@meter_router.get("/tenants/{tenant_id}/floors", response_model=FloorsResponse)
async def get_tenant_floors(tenant_id: int):
    """Get distinct floors for a tenant."""
    try:
        floors = MeterLoggingDbQueries.get_floors_for_tenant(tenant_id)
        return FloorsResponse(
            tenant_id=tenant_id,
            floors=[
                FloorSummary(
                    floor=f["floor"],
                    unit_count=f["unit_count"],
                    meter_count=f["meter_count"],
                )
                for f in floors
            ],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get floors: {exc}",
        )


@meter_router.get("/tenants", response_model=TenantSummaryResponse)
async def list_meter_logging_tenants(
    client_id: int = Query(..., description="Client identifier"),
    building_id: Optional[int] = Query(None, description="Filter by building identifier"),
):
    try:
        summaries = MeterLoggingDbQueries.list_tenants_for_client(
            client_id=client_id,
            building_id=building_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    tenants: list[TenantSummary] = []
    for summary in summaries:
        building_data = summary["building"]
        tenants.append(
            TenantSummary(
                tenant_id=summary["tenant_id"],
                tenant_name=summary["tenant_name"],
                client_id=summary["client_id"],
                building=BuildingSummary(**building_data),
                tenant_floors=summary.get("number_of_floors", 0),
                active_units=summary["active_units"],
                last_record_at=_normalize_timestamp(summary.get("last_record_at")),
            )
        )
    return TenantSummaryResponse(tenants=tenants)


@meter_router.get(
    "/tenants/{tenant_id}/meters",
    response_model=MeterAssignmentsResponse,
)
async def get_tenant_meter_assignments(
    tenant_id: int,
    floor: Optional[int] = Query(None, description="Filter by floor number"),
):
    """Get meter assignments for a tenant, optionally filtered by floor."""
    try:
        assignments = MeterLoggingDbQueries.get_meter_assignments_for_tenant(
            tenant_id=tenant_id,
            floor=floor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get meter assignments: {exc}",
        )

    meters: list[MeterAssignment] = []
    try:
        for assignment in assignments:
            last_record = assignment.get("last_record")
            meters.append(
                MeterAssignment(
                    meter_id=assignment["meter_id"],
                    meter_pk=assignment["meter_pk"],
                    unit=UnitSummary(**assignment["unit"]),
                    loads=assignment["loads"],
                    last_record=(
                        MeterAssignmentLastRecord(
                            timestamp_record=_normalize_timestamp(
                                last_record.get("timestamp_record")
                            ),
                            meter_kWh=float(last_record.get("meter_kWh")),
                        )
                        if last_record
                        else None
                    ),
                )
            )

        return MeterAssignmentsResponse(tenant_id=tenant_id, meters=meters)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process meter assignments: {exc}",
        )


@meter_router.post(
    "/records",
    response_model=MeterRecordBatchResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_meter_records(payload: MeterRecordBatchRequest):
    if not payload.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="records list must not be empty",
        )

    record_payloads: list[Dict[str, object]] = []
    meter_cache: dict[str, int] = {}
    for record in payload.records:
        ts = record.timestamp_record
        if ts.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="timestamp_record must include timezone information",
            )
        if record.meter_kWh < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="meter_kWh must be non-negative",
            )
        meter_identifier = record.meter_id
        if meter_identifier in meter_cache:
            meter_pk = meter_cache[meter_identifier]
        else:
            meter_pk = _resolve_meter_pk_or_404(meter_identifier)
            meter_cache[meter_identifier] = meter_pk
        record_payloads.append(
            {
                "client_record_id": record.client_record_id,
                "meter_id": meter_pk,
                "meter_identifier": meter_identifier,
                "timestamp_record": record.timestamp_record.isoformat(),
                "meter_kWh": record.meter_kWh,
            }
        )

    try:
        accepted, warnings = MeterLoggingDbQueries.insert_meter_records(
            tenant_id=payload.tenant_id,
            session_id=payload.session_id,
            records=record_payloads,
            encoder_user_id=payload.encoder_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return MeterRecordBatchResponse(
        tenant_id=payload.tenant_id,
        session_id=payload.session_id,
        accepted=[MeterRecordAccepted(**item) for item in accepted],
        warnings=[MeterRecordWarning(**item) for item in warnings],
    )


@meter_router.post("/approvals", status_code=status.HTTP_200_OK)
async def attach_meter_approval(request: ApprovalRequest):
    updated = MeterLoggingDbQueries.attach_approval_to_session(
        tenant_id=request.tenant_id,
        session_id=request.session_id,
        approver_name=request.approver.name,
        approver_signature=request.approver.signature_blob,
    )
    if updated == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No meter records found for tenant/session combination",
        )
    return {"updated": updated}


@meter_router.get(
    "/meter-records",
    response_model=MeterRecordHistoryResponse,
)
async def get_meter_records(
    tenant_id: Optional[int] = Query(None),
    meter_id: Optional[str] = Query(None),
    from_timestamp: Optional[str] = Query(None, alias="from"),
    to_timestamp: Optional[str] = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
):
    if tenant_id is None and meter_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id or meter_id must be provided",
        )

    meter_pk: Optional[int] = None
    if meter_id is not None:
        meter_pk = _resolve_meter_pk_or_404(meter_id)

    records = MeterLoggingDbQueries.get_meter_records(
        tenant_id=tenant_id,
        meter_id=meter_pk,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        limit=limit,
    )

    items: list[MeterRecordHistoryItem] = []
    for row in records:
        meter_identifier = row.get("meter_identifier") or str(row["meter_pk"])
        items.append(
            MeterRecordHistoryItem(
                meter_record_id=row["meter_record_id"],
                meter_id=meter_identifier,
                meter_pk=row["meter_pk"],
                tenant_id=row["tenant_id"],
                session_id=row["session_id"],
                client_record_id=row["client_record_id"],
                timestamp_record=_normalize_timestamp(row["timestamp_record"]),
                meter_kWh=float(row["meter_kWh"]),
                encoder_user_id=row["encoder_user_id"],
                approver_name=row["approver_name"],
                approver_signature=row["approver_signature"],
                created_at=_normalize_timestamp(row["created_at"]),
            )
        )

    return MeterRecordHistoryResponse(records=items)


@meter_router.get("/user-id", response_model=dict)
async def get_user_id_by_email(email: str = Query(..., description="User email address")):
    """Get user ID from email address."""
    from backend.services.data.db_manager.db_schema import get_db_connection
    import sqlite3
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ? AND active = 1 LIMIT 1", (email,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' not found",
            )
        return {"user_id": row["id"], "email": email}
    finally:
        conn.close()


@meter_router.get("/user-info", response_model=dict)
async def get_user_info_by_email(email: str = Query(..., description="User email address")):
    """Get user information (ID, role, entity_id) from email address."""
    from backend.services.data.db_manager.db_schema import get_db_connection
    from backend.services.data.db_manager import MeterLoggingDbQueries
    import sqlite3
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_group, entity_id, company FROM users WHERE email = ? AND active = 1 LIMIT 1",
            (email,)
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' not found",
            )
        
        user_id = row["id"]
        user_group_str = row["user_group"]
        
        # Get user role using the query method (in case there's additional logic)
        try:
            user_group_str = MeterLoggingDbQueries.get_user_role_for_user(user_id=user_id, conn=conn)
        except Exception:
            # Fallback to direct DB value if query method fails
            pass
        
        # Convert user_group string to numeric role (hierarchy value)
        from backend.services.auth.permissions import UserRole, ROLE_HIERARCHY
        try:
            user_role_enum = UserRole(user_group_str)
            role_number = ROLE_HIERARCHY.get(user_role_enum, 0)
        except (ValueError, KeyError):
            # If role is not in enum, default to 0
            role_number = 0
        
        return {
            "user_id": user_id,
            "role": role_number,
            "entity_id": row["entity_id"],
            "email": email,
            "company": row["company"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {exc}",
        )
    finally:
        conn.close()


@meter_router.get("/meta", response_model=MeterMetaResponse)
async def get_meter_meta():
    return MeterMetaResponse(
        version="v1",
        server_time=datetime.now(timezone.utc).isoformat(),
        non_decreasing_enforced=True,
    )

