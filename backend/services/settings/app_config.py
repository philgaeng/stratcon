#!/usr/bin/env python3
"""
Settings Manager for reading and writing JSON configuration.

Manages app_settings.json which contains:
- Role definitions and permissions
- Route permissions
- Default settings
- Feature flags

This follows a hybrid approach:
- JSON for static configuration (roles, permissions, defaults)
- Database for runtime data (users, settings, assignments)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class AppConfigManager:
    """Manages JSON-based settings configuration."""
    
    def __init__(self, settings_file: Optional[Path] = None):
        """
        Initialize settings manager.
        
        Args:
            settings_file: Path to settings JSON file. Defaults to backend/config/app_settings.json
        """
        if settings_file is None:
            # Default to backend/config/app_settings.json
            backend_dir = Path(__file__).resolve().parent.parent.parent
            settings_file = backend_dir / "config" / "app_settings.json"
        
        self.settings_file = Path(settings_file)
        self._settings: Optional[Dict[str, Any]] = None
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file."""
        if self._settings is None:
            if not self.settings_file.exists():
                raise FileNotFoundError(
                    f"Settings file not found: {self.settings_file}"
                )
            
            with open(self.settings_file, "r", encoding="utf-8") as f:
                self._settings = json.load(f)
        
        return self._settings
    
    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Save settings to JSON file."""
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        # Invalidate cache
        self._settings = None
    
    def get_roles_config(self) -> Dict[str, Any]:
        """Get roles configuration."""
        settings = self._load_settings()
        return settings.get("roles", {})
    
    def get_role_config(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific role."""
        roles = self.get_roles_config()
        return roles.get(role_name)
    
    def get_route_permissions(self) -> Dict[str, list[str]]:
        """Get route permissions mapping."""
        settings = self._load_settings()
        return settings.get("route_permissions", {})
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings."""
        settings = self._load_settings()
        return settings.get("default_settings", {})
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags."""
        defaults = self.get_default_settings()
        return defaults.get("features", {})
    
    def update_role_permissions(
        self,
        role_name: str,
        permissions: list[str],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Update permissions for a role.
        
        Args:
            role_name: Role identifier (e.g., "client_admin")
            permissions: List of permission strings (e.g., ["clients.view", "users.create"])
            name: Optional display name for the role
            description: Optional description for the role
        """
        settings = self._load_settings()
        roles = settings.get("roles", {})
        
        if role_name not in roles:
            raise ValueError(f"Role '{role_name}' does not exist")
        
        role_config = roles[role_name]
        role_config["permissions"] = permissions
        
        if name is not None:
            role_config["name"] = name
        
        if description is not None:
            role_config["description"] = description
        
        self._save_settings(settings)
    
    def update_route_permission(
        self,
        route: str,
        allowed_roles: list[str],
    ) -> None:
        """
        Update which roles can access a route.
        
        Args:
            route: Route path (e.g., "/clients")
            allowed_roles: List of role identifiers that can access this route
        """
        settings = self._load_settings()
        route_permissions = settings.get("route_permissions", {})
        route_permissions[route] = allowed_roles
        
        self._save_settings(settings)
    
    def update_default_setting(
        self,
        category: str,
        key: str,
        value: Any,
    ) -> None:
        """
        Update a default setting.
        
        Args:
            category: Setting category (e.g., "cutoff", "pagination", "features")
            key: Setting key within the category
            value: New value for the setting
        """
        settings = self._load_settings()
        defaults = settings.get("default_settings", {})
        
        if category not in defaults:
            defaults[category] = {}
        
        defaults[category][key] = value
        
        self._save_settings(settings)
    
    def update_feature_flag(self, feature: str, enabled: bool) -> None:
        """
        Update a feature flag.
        
        Args:
            feature: Feature name (e.g., "meter_logging")
            enabled: Whether the feature is enabled
        """
        self.update_default_setting("features", feature, enabled)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return self._load_settings().copy()
    
    def reload(self) -> None:
        """Reload settings from file (useful if file was modified externally)."""
        self._settings = None
        self._load_settings()

