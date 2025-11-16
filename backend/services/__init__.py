#!/usr/bin/env python3
"""Top-level exports for the `backend.services` package (lazy-loaded)."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple


_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    # Config constants/classes (from core.config)
    'MAX_MISSING_DAYS_PER_MONTH': ('backend.services.core.config', 'MAX_MISSING_DAYS_PER_MONTH'),
    'MAX_CONSECUTIVE_MISSING_TIMESTAMPS': ('backend.services.core.config', 'MAX_CONSECUTIVE_MISSING_TIMESTAMPS'),
    'WEEKDAYS': ('backend.services.core.config', 'WEEKDAYS'),
    'NIGHT_HOURS': ('backend.services.core.config', 'NIGHT_HOURS'),
    'DAY_HOURS': ('backend.services.core.config', 'DAY_HOURS'),
    'CO2_EMISSIONS_PER_KWH': ('backend.services.core.config', 'CO2_EMISSIONS_PER_KWH'),
    'ReportStyle': ('backend.services.core.config', 'ReportStyle'),
    'PlotlyStyle': ('backend.services.core.config', 'PlotlyStyle'),

    # Utils (from core.utils)
    'ReportLogger': ('backend.services.core.utils', 'ReportLogger'),

    # Orchestrators (from domain)
    'DataPreparationOrchestrator': ('backend.services.domain.data_preparation', 'DataPreparationOrchestrator'),
    'ElectricityAnalysisOrchestrator': ('backend.services.domain.electricity_analysis', 'ElectricityAnalysisOrchestrator'),
    'ReportingOrchestrator': ('backend.services.domain.reporting', 'ReportingOrchestrator'),

    # Reporting helpers (from domain.reporting)
    'generate_charts': ('backend.services.domain.reporting.prepare_charts', 'generate_charts'),
    'generate_onepager_html': ('backend.services.domain.reporting.prepare_html', 'generate_onepager_html'),
    'generate_report_for_tenant': ('backend.services.domain.reporting', 'generate_report_for_tenant'),
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module 'backend.services' has no attribute '{name}'") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value  # cache for future attribute lookups
    return value
