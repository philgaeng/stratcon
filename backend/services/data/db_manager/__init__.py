#!/usr/bin/env python3
"""
Database manager package exports.
"""

from backend.services.data.db_manager.db_schema import (
    get_db_connection,
    init_database,
    create_default_stratcon_epc,
    populate_entities,
    populate_user_entity_ids,
)
from backend.services.data.db_manager.db_queries_reporting import ReportingDbQueries
from backend.services.data.db_manager.db_queries_meter_logging import MeterLoggingDbQueries


class DbQueries(ReportingDbQueries, MeterLoggingDbQueries):
    """Maintains the historic `DbQueries` interface by mixing in specialised helpers."""

    pass

__all__ = [
    'get_db_connection',
    'init_database',
    'create_default_stratcon_epc',
    'populate_entities',
    'populate_user_entity_ids',
    'DbQueries',
    'ReportingDbQueries',
    'MeterLoggingDbQueries',
]
