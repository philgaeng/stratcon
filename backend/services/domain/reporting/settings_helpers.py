#!/usr/bin/env python3
"""Re-export settings helpers to keep reporting API imports tidy."""

from __future__ import annotations

from typing import Optional

from backend.services.settings.cutoff import (
    CutoffSettingsManager,
)

# Create a singleton instance for backward compatibility
_cutoff_manager = CutoffSettingsManager()

def get_all_client_settings(client_token: str) -> dict:
    """Get all settings for a client including unit overrides."""
    return _cutoff_manager.get_client_settings(client_token)

def get_cutoff_datetime(
    client_token: str,
    tenant_token: Optional[str] = None,
    load_name: Optional[str] = None,
):
    """Get cutoff datetime for a client/tenant/load with fallback hierarchy."""
    return _cutoff_manager.get_cutoff_datetime(
        client_token=client_token,
        tenant_token=tenant_token,
        load_name=load_name,
    )

def set_client_settings(
    client_token: str,
    cutoff_day: int,
    cutoff_hour: int = 23,
    cutoff_minute: int = 59,
    cutoff_second: int = 59,
    epc_name: Optional[str] = None,
):
    """Set or update client-wide default settings."""
    _cutoff_manager.set_client_cutoff(
        client_token=client_token,
        cutoff_day=cutoff_day,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        cutoff_second=cutoff_second,
        epc_name=epc_name,
    )

def set_tenant_settings(
    client_token: str,
    tenant_token: str,
    cutoff_day: Optional[int] = None,
    cutoff_hour: Optional[int] = None,
    cutoff_minute: Optional[int] = None,
    cutoff_second: Optional[int] = None,
):
    """Set or update tenant/unit-specific settings."""
    _cutoff_manager.set_tenant_cutoff(
        client_token=client_token,
        tenant_token=tenant_token,
        cutoff_day=cutoff_day,
        cutoff_hour=cutoff_hour,
        cutoff_minute=cutoff_minute,
        cutoff_second=cutoff_second,
    )

__all__ = [
    "get_all_client_settings",
    "get_cutoff_datetime",
    "set_client_settings",
    "set_tenant_settings",
]

