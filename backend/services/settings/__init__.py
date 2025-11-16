#!/usr/bin/env python3
"""Settings management - application config and business domain settings."""

from backend.services.settings.service import SettingsService
from backend.services.settings.app_config import AppConfigManager
from backend.services.settings.cutoff import CutoffSettingsManager

# Backward compatibility aliases
SettingsManager = AppConfigManager  # Old name still works (deprecated)

__all__ = [
    'SettingsService',
    'AppConfigManager',
    'SettingsManager',  # Backward compatibility
    'CutoffSettingsManager',
]

