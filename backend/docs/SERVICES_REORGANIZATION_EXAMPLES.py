#!/usr/bin/env python3
"""
Example __init__.py files for the reorganized services structure.

This shows how to maintain backward compatibility while organizing code better.
"""

# ============================================================================
# Example: services/core/__init__.py
# ============================================================================

"""
# services/core/__init__.py

from .base import ServiceContext
from .config import (
    MAX_MISSING_DAYS_PER_MONTH,
    ReportStyle,
    PlotlyStyle,
    PHILIPPINES_TZ,
    DEFAULT_CLIENT,
)
from .utils import ReportLogger, raise_with_context

__all__ = [
    'ServiceContext',
    'ReportLogger',
    'ReportStyle',
    'PlotlyStyle',
    'MAX_MISSING_DAYS_PER_MONTH',
    'PHILIPPINES_TZ',
    'DEFAULT_CLIENT',
    'raise_with_context',
]
"""

# ============================================================================
# Example: services/auth/__init__.py
# ============================================================================

"""
# services/auth/__init__.py

from .permissions import (
    UserRole,
    require_roles,
    require_minimum_role,
    get_user_role_from_request,
    has_role,
    has_minimum_role,
    check_permission,
)

__all__ = [
    'UserRole',
    'require_roles',
    'require_minimum_role',
    'get_user_role_from_request',
    'has_role',
    'has_minimum_role',
    'check_permission',
]
"""

# ============================================================================
# Example: services/settings/__init__.py
# ============================================================================

"""
# services/settings/__init__.py

from .service import SettingsService
from .app_config import AppConfigManager
from .cutoff import CutoffSettingsManager

# For backward compatibility, also export as old names
SettingsManager = AppConfigManager  # Alias for old name

__all__ = [
    'SettingsService',
    'AppConfigManager',
    'SettingsManager',  # Backward compatibility
    'CutoffSettingsManager',
]
"""

# ============================================================================
# Example: services/services/__init__.py
# ============================================================================

"""
# services/services/__init__.py

from .email import send_report_email
from .visualization import generate_charts, generate_onepager_html

__all__ = [
    'send_report_email',
    'generate_charts',
    'generate_onepager_html',
]
"""

# ============================================================================
# Example: Updated services/__init__.py (main package)
# ============================================================================

"""
# services/__init__.py
# Maintains backward compatibility while using new structure

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

# Re-export from new locations for backward compatibility
_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    # Core utilities (old paths still work)
    'ReportLogger': ('backend.services.core', 'ReportLogger'),
    'ReportStyle': ('backend.services.core.config', 'ReportStyle'),
    'PlotlyStyle': ('backend.services.core.config', 'PlotlyStyle'),
    'MAX_MISSING_DAYS_PER_MONTH': ('backend.services.core.config', 'MAX_MISSING_DAYS_PER_MONTH'),
    'ServiceContext': ('backend.services.core.base', 'ServiceContext'),
    
    # Auth (old paths still work)
    'UserRole': ('backend.services.auth', 'UserRole'),
    'require_roles': ('backend.services.auth', 'require_roles'),
    'require_minimum_role': ('backend.services.auth', 'require_minimum_role'),
    
    # Settings (old paths still work)
    'SettingsService': ('backend.services.settings', 'SettingsService'),
    'SettingsManager': ('backend.services.settings', 'SettingsManager'),
    'AppConfigManager': ('backend.services.settings', 'AppConfigManager'),
    
    # Services (old paths still work)
    'send_report_email': ('backend.services.services.email', 'send_report_email'),
    
    # Orchestrators (unchanged)
    'DataPreparationOrchestrator': ('backend.services.domain.data_preparation', 'DataPreparationOrchestrator'),
    'ElectricityAnalysisOrchestrator': ('backend.services.domain.electricity_analysis', 'ElectricityAnalysisOrchestrator'),
    'ReportingOrchestrator': ('backend.services.domain.reporting', 'ReportingOrchestrator'),
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str) -> Any:
    \"\"\"Lazy loading for backward compatibility.\"\"\"
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module 'backend.services' has no attribute '{name}'") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value  # cache for future attribute lookups
    return value
"""

# ============================================================================
# Usage Examples
# ============================================================================

"""
# OLD WAY (still works):
from backend.services.utils import ReportLogger
from backend.services.config import ReportStyle
from backend.services.permissions import UserRole
from backend.services.settings_service import SettingsService

# NEW WAY (preferred):
from backend.services.core import ReportLogger, ReportStyle
from backend.services.auth import UserRole
from backend.services.settings import SettingsService

# OR via main package (backward compatible):
from backend.services import ReportLogger, ReportStyle, UserRole, SettingsService
"""

