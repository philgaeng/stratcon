#!/usr/bin/env python3
"""Data management - database queries, schema, data extraction."""

# Re-export from db_manager
from backend.services.data.db_manager import (
    DbQueries,
    MeterLoggingDbQueries,
    ReportingDbQueries,
    get_db_connection,
    init_database,
)

__all__ = [
    'DbQueries',
    'MeterLoggingDbQueries',
    'ReportingDbQueries',
    'get_db_connection',
    'init_database',
]

