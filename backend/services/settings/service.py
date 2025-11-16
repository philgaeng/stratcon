#!/usr/bin/env python3
"""
Unified Settings Service.

Provides a clean interface to both:
- Application configuration (JSON): roles, permissions, feature flags
- Business settings (Database): cutoff times for clients/tenants/units

This service uses composition to integrate AppConfigManager and CutoffSettingsManager,
providing a single entry point for all settings operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from backend.services.core.utils import ReportLogger
from backend.services.settings.app_config import AppConfigManager
from backend.services.settings.cutoff import CutoffSettingsManager


class SettingsService:
    """
    Unified settings service that provides access to both application config
    and business domain settings.
    
    Usage:
        service = SettingsService()
        
        # Application config (JSON)
        roles = service.app_config.get_roles_config()
        
        # Business settings (Database)
        cutoff = service.cutoff.get_cutoff_datetime("NEO", "NEO3_0708")
    """
    
    def __init__(
        self,
        config_file: Optional[Path] = None,
        logger: Optional[ReportLogger] = None,
    ):
        """
        Initialize settings service.
        
        Args:
            config_file: Path to app_settings.json (defaults to backend/config/app_settings.json)
            logger: Optional logger instance
        """
        self.logger = logger or ReportLogger()
        
        # Application configuration (JSON)
        self.app_config = AppConfigManager(settings_file=config_file)
        
        # Business domain settings (Database)
        self.cutoff = CutoffSettingsManager(logger=self.logger)
    
    # ============================================================================
    # Application Configuration (JSON) - Delegated to AppConfigManager
    # ============================================================================
    
    def get_roles_config(self) -> Dict[str, Any]:
        """Get all role configurations from JSON."""
        return self.app_config.get_roles_config()
    
    def get_role_config(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific role."""
        return self.app_config.get_role_config(role_name)
    
    def get_route_permissions(self) -> Dict[str, list[str]]:
        """Get route permissions mapping."""
        return self.app_config.get_route_permissions()
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags."""
        return self.app_config.get_feature_flags()
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings."""
        return self.app_config.get_default_settings()
    
    def update_role_permissions(
        self,
        role_name: str,
        permissions: list[str],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Update permissions for a role."""
        self.app_config.update_role_permissions(role_name, permissions, name, description)
    
    def update_route_permission(self, route: str, allowed_roles: list[str]) -> None:
        """Update which roles can access a route."""
        self.app_config.update_route_permission(route, allowed_roles)
    
    def update_feature_flag(self, feature: str, enabled: bool) -> None:
        """Update a feature flag."""
        self.app_config.update_feature_flag(feature, enabled)
    
    # ============================================================================
    # Business Domain Settings (Database) - Cutoff Times
    # ============================================================================
    
    def get_cutoff_datetime(
        self,
        client_token: str,
        tenant_token: Optional[str] = None,
        load_name: Optional[str] = None,
    ) -> Optional[datetime]:
        """
        Get cutoff datetime for a client/tenant/load with fallback hierarchy.
        
        Priority order:
        1. Unit-level cutoff (if unit found and has settings)
        2. Client-level cutoff (if client has settings)
        3. EPC-level cutoff (default for all clients under EPC)
        4. System default (26, 23:59:59) if nothing found
        
        Args:
            client_token: Client identifier (name)
            tenant_token: Optional tenant/unit identifier (name or unit number)
            load_name: Optional load name (e.g., "MCB - 2002 [kW]")
            
        Returns:
            datetime object with timezone, or None if no settings found
        """
        return self.cutoff.get_cutoff_datetime(
            client_token=client_token,
            tenant_token=tenant_token,
            load_name=load_name,
        )
    
    def set_client_cutoff(
        self,
        client_token: str,
        cutoff_day: int,
        cutoff_hour: int = 23,
        cutoff_minute: int = 59,
        cutoff_second: int = 59,
        epc_name: Optional[str] = None,
    ) -> None:
        """
        Set or update client-wide cutoff settings.
        
        Args:
            client_token: Client identifier (name)
            cutoff_day: Cutoff day (1-31)
            cutoff_hour: Cutoff hour (0-23)
            cutoff_minute: Cutoff minute (0-59)
            cutoff_second: Cutoff second (0-59)
            epc_name: Optional EPC name (defaults to 'Stratcon')
        """
        self.cutoff.set_client_cutoff(
            client_token=client_token,
            cutoff_day=cutoff_day,
            cutoff_hour=cutoff_hour,
            cutoff_minute=cutoff_minute,
            cutoff_second=cutoff_second,
            epc_name=epc_name,
        )
    
    def set_tenant_cutoff(
        self,
        client_token: str,
        tenant_token: str,
        cutoff_day: Optional[int] = None,
        cutoff_hour: Optional[int] = None,
        cutoff_minute: Optional[int] = None,
        cutoff_second: Optional[int] = None,
    ) -> None:
        """
        Set or update tenant/unit-specific cutoff settings.
        
        Args:
            client_token: Client identifier (name)
            tenant_token: Tenant/unit identifier (name or unit number)
            cutoff_day: Cutoff day (1-31), optional
            cutoff_hour: Cutoff hour (0-23), optional
            cutoff_minute: Cutoff minute (0-59), optional
            cutoff_second: Cutoff second (0-59), optional
        """
        self.cutoff.set_tenant_cutoff(
            client_token=client_token,
            tenant_token=tenant_token,
            cutoff_day=cutoff_day,
            cutoff_hour=cutoff_hour,
            cutoff_minute=cutoff_minute,
            cutoff_second=cutoff_second,
        )
    
    def get_client_settings(self, client_token: str) -> dict:
        """
        Get all settings for a client including unit overrides.
        
        Args:
            client_token: Client identifier (name)
            
        Returns:
            Dictionary with client settings, EPC settings, and unit settings
        """
        return self.cutoff.get_client_settings(client_token)
    
    # ============================================================================
    # Convenience Methods (Combining both sources)
    # ============================================================================
    
    def get_default_cutoff_settings(self) -> Dict[str, int]:
        """
        Get default cutoff settings from JSON config.
        
        Falls back to hardcoded defaults if not in JSON.
        
        Returns:
            Dictionary with day, hour, minute, second
        """
        defaults = self.get_default_settings()
        cutoff_defaults = defaults.get("cutoff", {})
        
        return {
            "day": cutoff_defaults.get("day", 26),
            "hour": cutoff_defaults.get("hour", 23),
            "minute": cutoff_defaults.get("minute", 59),
            "second": cutoff_defaults.get("second", 59),
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled.
        
        Args:
            feature: Feature name (e.g., "meter_logging")
            
        Returns:
            True if feature is enabled, False otherwise
        """
        flags = self.get_feature_flags()
        return flags.get(feature, False)
    
    def reload_config(self) -> None:
        """Reload application configuration from JSON file."""
        self.app_config.reload()

