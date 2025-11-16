#!/usr/bin/env python3
"""Core utilities and base classes."""

from backend.services.core.base import ServiceContext
from backend.services.core.config import (
    MAX_MISSING_DAYS_PER_MONTH,
    MAX_CONSECUTIVE_MISSING_TIMESTAMPS,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY,
    MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH,
    WEEKDAYS,
    HOURS,
    NIGHT_HOURS,
    DAY_HOURS,
    CO2_EMISSIONS_PER_KWH,
    PHILIPPINES_TZ,
    DEFAULT_CLIENT,
    DEFAULT_LOGS_DIR,
    DEFAULT_REPORTS_DIR,
    DEFAULT_RESOURCES_DIR,
    SOURCE_TYPES,
    verify_source_type,
    ReportStyle,
    PlotlyStyle,
)
from backend.services.core.utils import (
    ReportLogger,
    raise_with_context,
    generate_power_column_name,
    generate_consumption_column_name,
)

__all__ = [
    # Base classes
    'ServiceContext',
    
    # Logger and utilities
    'ReportLogger',
    'raise_with_context',
    'generate_power_column_name',
    'generate_consumption_column_name',
    
    # Config constants
    'MAX_MISSING_DAYS_PER_MONTH',
    'MAX_CONSECUTIVE_MISSING_TIMESTAMPS',
    'MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR',
    'MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY',
    'MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH',
    'WEEKDAYS',
    'HOURS',
    'NIGHT_HOURS',
    'DAY_HOURS',
    'CO2_EMISSIONS_PER_KWH',
    'PHILIPPINES_TZ',
    'DEFAULT_CLIENT',
    'DEFAULT_LOGS_DIR',
    'DEFAULT_REPORTS_DIR',
    'DEFAULT_RESOURCES_DIR',
    'SOURCE_TYPES',
    'verify_source_type',
    
    # Style classes
    'ReportStyle',
    'PlotlyStyle',
]

