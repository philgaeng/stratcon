#!/usr/bin/env python3
"""
Settings service for managing client/tenant/load configuration.
Stores default cutoff times, cutoff days, and other settings in SQLite database.
Uses the comprehensive schema from db_schema.py (EPCs → Clients → Buildings → Units → Loads).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from datetime import datetime
import sqlite3

from backend.services.core.config import PHILIPPINES_TZ, DEFAULT_CLIENT
from backend.services.core.utils import ReportLogger
from backend.services.data.db_manager.db_schema import (
    get_db_connection,
    init_database,
    create_default_stratcon_epc,
)

SERVICES_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SERVICES_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DB_PATH = BACKEND_DIR / "data" / "settings.db"

# Default cutoff time if not specified
DEFAULT_CUTOFF_TIME = "23:59:59"
DEFAULT_CUTOFF_HOUR = 23
DEFAULT_CUTOFF_MINUTE = 59
DEFAULT_CUTOFF_SECOND = 59


def _find_or_create_epc(epc_name: str, conn: sqlite3.Connection) -> int:
    """Find or create an EPC by name. Returns EPC ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM epcs WHERE name = ?", (epc_name,))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Create new EPC with default Stratcon settings
    cursor.execute("""
        INSERT INTO epcs (name, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
        VALUES (?, 26, 23, 59, 59)
    """, (epc_name,))
    return cursor.lastrowid


def _find_or_create_client(client_name: str, epc_id: Optional[int] = None, conn: sqlite3.Connection = None) -> int:
    """Find or create a client by name. Returns client ID."""
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # If epc_id not provided, use Stratcon EPC
        if epc_id is None:
            cursor.execute("SELECT id FROM epcs WHERE name = 'Stratcon'")
            stratcon_row = cursor.fetchone()
            if stratcon_row:
                epc_id = stratcon_row['id']
            else:
                # Create Stratcon EPC if it doesn't exist
                create_default_stratcon_epc()
                cursor.execute("SELECT id FROM epcs WHERE name = 'Stratcon'")
                epc_id = cursor.fetchone()['id']
        
        # Find client
        cursor.execute("SELECT id FROM clients WHERE epc_id = ? AND name = ?", (epc_id, client_name))
        row = cursor.fetchone()
        if row:
            return row['id']
        
        # Create new client
        cursor.execute("""
            INSERT INTO clients (epc_id, name, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
            VALUES (?, ?, 26, 23, 59, 59)
        """, (epc_id, client_name))
        
        if close_conn:
            conn.commit()
        
        return cursor.lastrowid
    finally:
        if close_conn:
            conn.close()


def _find_or_create_load(load_name: str, conn: sqlite3.Connection) -> int:
    """Find or create a load by name. Returns load ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM loads WHERE load_name = ?", (load_name,))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Create new load
    cursor.execute("INSERT INTO loads (load_name) VALUES (?)", (load_name,))
    return cursor.lastrowid


def _find_unit_by_identifier(client_id: int, unit_identifier: str, conn: sqlite3.Connection) -> Optional[int]:
    """
    Find a unit by identifier within a client.
    The unit_identifier could be a tenant name, unit number, or building/unit combination.
    Returns unit ID or None if not found.
    """
    cursor = conn.cursor()
    
    # Strategy 1: Try to find tenant with matching name, then find unit with that tenant
    cursor.execute("""
        SELECT DISTINCT u.id
        FROM units u
        JOIN buildings b ON u.building_id = b.id
        JOIN tenant_unit_history uth ON u.id = uth.unit_id
        JOIN tenants t ON uth.tenant_id = t.id
        WHERE b.client_id = ? AND t.name = ? AND uth.is_active = 1
        LIMIT 1
    """, (client_id, unit_identifier))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Strategy 2: Try to find unit by unit_number
    cursor.execute("""
        SELECT u.id
        FROM units u
        JOIN buildings b ON u.building_id = b.id
        WHERE b.client_id = ? AND u.unit_number = ?
        LIMIT 1
    """, (client_id, unit_identifier))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    return None


def get_cutoff_datetime(
    client_token: str,
    tenant_token: Optional[str] = None,
    load_name: Optional[str] = None,
    logger: Optional[ReportLogger] = None,
) -> Optional[datetime]:
    """
    Get cutoff datetime for a client/tenant/load with fallback hierarchy.
    
    Priority order (new schema):
    1. Unit-level cutoff (if unit found and has settings)
    2. Client-level cutoff (if client has settings)
    3. EPC-level cutoff (default for all clients under EPC)
    4. System default (26, 23:59:59) if nothing found
    
    Args:
        client_token: Client identifier (name)
        tenant_token: Optional tenant/unit identifier (name or unit number)
        load_name: Optional load name (e.g., "MCB - 2002 [kW]")
        logger: Optional logger instance
        
    Returns:
        datetime object with timezone, or None if no settings found
    """
    if logger is None:
        logger = ReportLogger()
    
    # Ensure database is initialized
    init_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cutoff_day = None
    cutoff_hour = DEFAULT_CUTOFF_HOUR
    cutoff_minute = DEFAULT_CUTOFF_MINUTE
    cutoff_second = DEFAULT_CUTOFF_SECOND
    
    try:
        # Get client ID
        client_id = _find_or_create_client(client_token, conn=conn)
        
        # Try to find unit if tenant_token provided
        unit_id = None
        if tenant_token:
            unit_id = _find_unit_by_identifier(client_id, tenant_token, conn)
            if unit_id:
                # Check unit-level cutoff
                cursor.execute("""
                    SELECT cutoff_day, cutoff_hour, cutoff_minute, cutoff_second
                    FROM units
                    WHERE id = ?
                """, (unit_id,))
                row = cursor.fetchone()
                if row and row['cutoff_day'] is not None:
                    cutoff_day = row['cutoff_day']
                    cutoff_hour = row['cutoff_hour'] if row['cutoff_hour'] is not None else DEFAULT_CUTOFF_HOUR
                    cutoff_minute = row['cutoff_minute'] if row['cutoff_minute'] is not None else DEFAULT_CUTOFF_MINUTE
                    cutoff_second = row['cutoff_second'] if row['cutoff_second'] is not None else DEFAULT_CUTOFF_SECOND
                    logger.debug(f"Found unit-level settings for unit_id={unit_id} (client={client_token}, tenant={tenant_token})")
        
        # Try client-level cutoff if unit not found or has no settings
        if cutoff_day is None:
            cursor.execute("""
                SELECT cutoff_day, cutoff_hour, cutoff_minute, cutoff_second
                FROM clients
                WHERE id = ?
            """, (client_id,))
            row = cursor.fetchone()
            if row and row['cutoff_day'] is not None:
                cutoff_day = row['cutoff_day']
                cutoff_hour = row['cutoff_hour'] if row['cutoff_hour'] is not None else DEFAULT_CUTOFF_HOUR
                cutoff_minute = row['cutoff_minute'] if row['cutoff_minute'] is not None else DEFAULT_CUTOFF_MINUTE
                cutoff_second = row['cutoff_second'] if row['cutoff_second'] is not None else DEFAULT_CUTOFF_SECOND
                logger.debug(f"Found client-level settings for {client_token}")
        
        # Try EPC-level cutoff if client has no settings
        if cutoff_day is None:
            cursor.execute("""
                SELECT e.cutoff_day, e.cutoff_hour, e.cutoff_minute, e.cutoff_second
                FROM clients c
                JOIN epcs e ON c.epc_id = e.id
                WHERE c.id = ?
            """, (client_id,))
            row = cursor.fetchone()
            if row and row['cutoff_day'] is not None:
                cutoff_day = row['cutoff_day']
                cutoff_hour = row['cutoff_hour'] if row['cutoff_hour'] is not None else DEFAULT_CUTOFF_HOUR
                cutoff_minute = row['cutoff_minute'] if row['cutoff_minute'] is not None else DEFAULT_CUTOFF_MINUTE
                cutoff_second = row['cutoff_second'] if row['cutoff_second'] is not None else DEFAULT_CUTOFF_SECOND
                logger.debug(f"Found EPC-level settings for {client_token}")
        
        # If still no cutoff_day, return None (will fall back to CSV or default)
        if cutoff_day is None:
            logger.debug(f"No cutoff settings found in database for {client_token}, returning None")
            return None
        
        # Create cutoff datetime from settings
        from backend.services.domain.data_preparation.cutoff_manager import CutoffManager

        cutoff_datetime = CutoffManager.create_cutoff_datetime(cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
        
        logger.debug(f"Created cutoff datetime: {cutoff_datetime} (day={cutoff_day}, time={cutoff_hour:02d}:{cutoff_minute:02d}:{cutoff_second:02d})")
        return cutoff_datetime
        
    finally:
        conn.close()


def set_client_settings(
    client_token: str,
    cutoff_day: int,
    cutoff_hour: int = DEFAULT_CUTOFF_HOUR,
    cutoff_minute: int = DEFAULT_CUTOFF_MINUTE,
    cutoff_second: int = DEFAULT_CUTOFF_SECOND,
    epc_name: Optional[str] = None,
):
    """
    Set or update client-wide default settings.
    
    Args:
        client_token: Client identifier (name)
        cutoff_day: Cutoff day (1-31)
        cutoff_hour: Cutoff hour (0-23)
        cutoff_minute: Cutoff minute (0-59)
        cutoff_second: Cutoff second (0-59)
        epc_name: Optional EPC name (defaults to 'Stratcon')
    """
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get or create EPC
        if epc_name:
            epc_id = _find_or_create_epc(epc_name, conn)
        else:
            cursor.execute("SELECT id FROM epcs WHERE name = 'Stratcon'")
            row = cursor.fetchone()
            if row:
                epc_id = row['id']
            else:
                create_default_stratcon_epc()
                cursor.execute("SELECT id FROM epcs WHERE name = 'Stratcon'")
                epc_id = cursor.fetchone()['id']
        
        # Get or create client
        client_id = _find_or_create_client(client_token, epc_id, conn)
        
        # Update client settings
        cursor.execute("""
            UPDATE clients
            SET cutoff_day = ?, cutoff_hour = ?, cutoff_minute = ?, cutoff_second = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (cutoff_day, cutoff_hour, cutoff_minute, cutoff_second, client_id))
        
        conn.commit()
    finally:
        conn.close()


def set_tenant_settings(
    client_token: str,
    tenant_token: str,
    cutoff_day: Optional[int] = None,
    cutoff_hour: Optional[int] = None,
    cutoff_minute: Optional[int] = None,
    cutoff_second: Optional[int] = None,
):
    """
    Set or update tenant/unit-specific settings.
    
    Note: This function updates unit-level settings. If the unit doesn't exist,
    it will need to be created via the full schema (building/unit/tenant setup).
    
    Args:
        client_token: Client identifier (name)
        tenant_token: Tenant/unit identifier (name or unit number)
        cutoff_day: Cutoff day (1-31), optional
        cutoff_hour: Cutoff hour (0-23), optional
        cutoff_minute: Cutoff minute (0-59), optional
        cutoff_second: Cutoff second (0-59), optional
    """
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get client ID
        client_id = _find_or_create_client(client_token, conn=conn)
        
        # Find unit
        unit_id = _find_unit_by_identifier(client_id, tenant_token, conn)
        
        if unit_id:
            # Update existing unit
            update_fields = []
            update_values = []
            
            if cutoff_day is not None:
                update_fields.append("cutoff_day = ?")
                update_values.append(cutoff_day)
            if cutoff_hour is not None:
                update_fields.append("cutoff_hour = ?")
                update_values.append(cutoff_hour)
            if cutoff_minute is not None:
                update_fields.append("cutoff_minute = ?")
                update_values.append(cutoff_minute)
            if cutoff_second is not None:
                update_fields.append("cutoff_second = ?")
                update_values.append(cutoff_second)
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(unit_id)
                
                cursor.execute(f"""
                    UPDATE units
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, update_values)
                
                conn.commit()
        else:
            # Unit not found - this would require full building/unit setup
            # For now, log a warning
            logger = ReportLogger()
            logger.warning(f"⚠️  Unit not found for client={client_token}, tenant={tenant_token}. Unit must be created via full schema.")
            
    finally:
        conn.close()


def get_all_client_settings(client_token: str) -> dict:
    """
    Get all settings for a client including unit overrides.
    
    Args:
        client_token: Client identifier (name)
        
    Returns:
        Dictionary with client settings and unit settings
    """
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get client ID
        client_id = _find_or_create_client(client_token, conn=conn)
        
        # Get client settings
        cursor.execute("""
            SELECT c.*, e.name as epc_name
            FROM clients c
            JOIN epcs e ON c.epc_id = e.id
            WHERE c.id = ?
        """, (client_id,))
        client_row = cursor.fetchone()
        client_settings = dict(client_row) if client_row else None
        
        # Get unit settings (units with cutoff overrides)
        cursor.execute("""
            SELECT u.id, u.unit_number, u.cutoff_day, u.cutoff_hour, u.cutoff_minute, u.cutoff_second,
                   b.name as building_name
            FROM units u
            JOIN buildings b ON u.building_id = b.id
            WHERE b.client_id = ? AND u.cutoff_day IS NOT NULL
        """, (client_id,))
        unit_rows = cursor.fetchall()
        unit_settings = [dict(row) for row in unit_rows]
        
        # Get EPC settings
        cursor.execute("""
            SELECT e.cutoff_day, e.cutoff_hour, e.cutoff_minute, e.cutoff_second, e.name
            FROM clients c
            JOIN epcs e ON c.epc_id = e.id
            WHERE c.id = ?
        """, (client_id,))
        epc_row = cursor.fetchone()
        epc_settings = dict(epc_row) if epc_row else None
        
        return {
            'client': client_settings,
            'epc': epc_settings,
            'units': unit_settings,
        }
        
    finally:
        conn.close()


__all__ = [
    'init_database',
    'get_cutoff_datetime',
    'set_client_settings',
    'set_tenant_settings',
    'get_all_client_settings',
]
