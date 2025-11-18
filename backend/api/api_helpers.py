#!/usr/bin/env python3
"""Shared helper functions for API routes."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from fastapi import HTTPException, Request, status

from backend.services.core.config import DEFAULT_CLIENT
from backend.services.core.utils import ReportLogger
from backend.services.data.db_manager import DbQueries, MeterLoggingDbQueries, ReportingDbQueries
from backend.services.domain.reporting import generate_report_for_tenant_artifacts
from backend.services.services.email import send_report_email

# Environment variable for auth bypass
AUTH_BYPASS_SCOPE = os.getenv("AUTH_BYPASS_SCOPE", "true").strip().lower() in {"1", "true", "yes"}


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class UserScope:
    """User scope information for reporting API."""
    user_id: Optional[int]
    epc_ids: List[int]
    client_ids: List[int]
    tenant_ids: List[int]


# ============================================================================
# Common Helper Functions
# ============================================================================

def _normalize_ids(value: Optional[Any]) -> List[int]:
    """Normalize various input types to a list of integers."""
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
    """Parse user ID from header or query parameter."""
    if raw_value is None:
        return None
    candidate = raw_value.strip()
    if not candidate:
        return None
    try:
        return int(candidate)
    except ValueError as exc:  # pragma: no cover - input validation
        raise HTTPException(status_code=400, detail=f"Invalid {source}: {raw_value}") from exc


def _normalize_timestamp(value: Optional[object]) -> Optional[str]:
    """Normalize timestamp to ISO format string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    value_str = str(value).strip()
    if not value_str:
        return None
    candidate = value_str.replace(" ", "T")
    candidate = candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
    try:
        return datetime.fromisoformat(candidate).isoformat()
    except ValueError:
        return value_str.replace(" ", "T")


# ============================================================================
# User Scope Helpers (Shared across APIs)
# ============================================================================

def _get_user_scope(request: Request) -> UserScope:
    """Get user scope from request (returns UserScope dataclass).
    
    Standardized user scope function used across all APIs.
    Returns a UserScope dataclass with user_id, epc_ids, client_ids, and tenant_ids.
    """
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


# ============================================================================
# Reporting API Helpers
# ============================================================================

def _resolve_client(client_token: str) -> Dict[str, Any]:
    """Resolve client by ID or name."""
    lookup: Optional[Dict[str, Any]] = None
    if client_token.isdigit():
        lookup = DbQueries.get_client_by_id(int(client_token))
    if lookup is None:
        lookup = DbQueries.get_client_by_name(client_token)
    if lookup is None:
        raise HTTPException(status_code=404, detail=f"Client '{client_token}' not found.")
    return lookup


def _ensure_client_access(scope: UserScope, client_id: int) -> None:
    """Ensure user has access to the requested client."""
    if AUTH_BYPASS_SCOPE:
        return
    if scope.user_id is None:
        return
    if scope.client_ids:
        if client_id not in scope.client_ids:
            raise HTTPException(
                status_code=403,
                detail="Current user does not have access to the requested client.",
            )


def _resolve_tenant_for_client(
    *,
    scope: UserScope,
    client_row: Dict[str, Any],
    tenant_token: str,
) -> Dict[str, Any]:
    """Resolve tenant for a specific client."""
    client_id = client_row["id"]
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
    return tenant_row


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
    load_ids: Optional[List[int]] = None,
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
            load_ids=load_ids,
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


# ============================================================================
# Meter Logging API Helpers
# ============================================================================

def _resolve_meter_pk_or_404(meter_identifier: str) -> int:
    """Resolve meter primary key from identifier or raise 404."""
    try:
        return MeterLoggingDbQueries.get_meter_pk_for_identifier(meter_identifier)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

