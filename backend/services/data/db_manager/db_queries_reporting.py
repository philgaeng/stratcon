#!/usr/bin/env python3
"""Database query helpers used by the reporting application."""

from __future__ import annotations

import pandas as pd
import sqlite3
from collections import defaultdict  # noqa: F401  # Needed when subclasses mix in meter logging queries
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, cast
from backend.services.core.config import PHILIPPINES_TZ, verify_source_type

from backend.services.data.db_manager.db_schema import get_db_connection
from backend.services.core.utils import ReportLogger


class ReportingDbQueries:
    """Static helpers for reporting-related database access."""
    logger = ReportLogger()
    @staticmethod
    def find_load_id_by_name(load_name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        """Find a load identifier by its canonical name (e.g. 'MCB_802')."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM loads WHERE load_name = ?", (load_name,))
            row = cursor.fetchone()
            return row["id"] if row else None
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_all_tenant_ids_for_client(
        client_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[int]:
        """Return all active tenant IDs associated with the given client."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT uth.tenant_id
                FROM unit_tenants_history AS uth
                JOIN units AS u ON uth.unit_id = u.id
                JOIN buildings AS b ON u.building_id = b.id
                WHERE uth.is_active = 1
                  AND b.client_id = ?
                ORDER BY uth.tenant_id
                """,
                (client_id,),
            )
            rows = cursor.fetchall()
            return [row[0] if not isinstance(row, sqlite3.Row) else row["tenant_id"] for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def find_load_ids_by_unit(unit_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]:
        """Find all load IDs associated with a unit via `unit_loads_history`."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT load_id
                FROM unit_loads_history
                WHERE unit_id = ? AND is_active = 1
                """,
                (unit_id,),
            )
            rows = cursor.fetchall()
            return [row["load_id"] for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def find_load_ids_by_building(building_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]:
        """Find all load IDs associated with a building (via units)."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT luh.load_id
                FROM unit_loads_history luh
                JOIN units u ON luh.unit_id = u.id
                WHERE u.building_id = ? AND luh.is_active = 1
                """,
                (building_id,),
            )
            rows = cursor.fetchall()
            return [row["load_id"] for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def find_load_ids_by_client(client_id: int, conn: Optional[sqlite3.Connection] = None) -> List[int]:
        """Find all load IDs associated with a client (via buildings and units)."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT luh.load_id
                FROM unit_loads_history luh
                JOIN units u ON luh.unit_id = u.id
                JOIN buildings b ON u.building_id = b.id
                WHERE b.client_id = ? AND luh.is_active = 1
                """,
                (client_id,),
            )
            rows = cursor.fetchall()
            return [row["load_id"] for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def find_load_ids_by_tenant_floor(
        tenant_id: int,
        floor: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[int]:
        """Find load IDs for a tenant restricted to a specific floor."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT ulh.load_id
                FROM unit_loads_history AS ulh
                JOIN units AS u ON u.id = ulh.unit_id
                JOIN unit_tenants_history AS uth
                    ON uth.unit_id = u.id
                   AND uth.is_active = 1
                WHERE ulh.is_active = 1
                  AND uth.tenant_id = ?
                  AND u.floor = ?
                """,
                (tenant_id, floor),
            )
            rows = cursor.fetchall()
            return [row["load_id"] for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def list_clients(
        client_ids: Optional[Sequence[int]] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, Any]]:
        """Return active clients filtered by optional identifier list."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            params: List[Any] = []
            filtered_ids: Optional[List[int]] = None
            if client_ids is not None:
                filtered_ids = [int(client_id) for client_id in client_ids if client_id is not None]
                if not filtered_ids:
                    return []
            query = """
                SELECT id, name
                FROM clients
                WHERE is_active = 1
            """
            if filtered_ids is not None:
                placeholders = ",".join("?" * len(filtered_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(filtered_ids)
            query += " ORDER BY name COLLATE NOCASE"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [{"id": row["id"], "name": row["name"]} for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_client_by_id(
        client_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return client row (id, name) by identifier."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM clients
                WHERE id = ? AND is_active = 1
                LIMIT 1
                """,
                (client_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {"id": row["id"], "name": row["name"]}
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_client_by_name(
        client_name: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return client row (id, name) by case-insensitive name."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM clients
                WHERE LOWER(name) = LOWER(?) AND is_active = 1
                LIMIT 1
                """,
                (client_name,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {"id": row["id"], "name": row["name"]}
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def list_buildings_for_client(
        client_id: int,
        building_ids: Optional[Sequence[int]] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, Any]]:
        """Return active buildings for the supplied client."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            params: List[Any] = [client_id]
            filtered_ids: Optional[List[int]] = None
            if building_ids is not None:
                filtered_ids = [int(building_id) for building_id in building_ids if building_id is not None]
                if not filtered_ids:
                    return []
            query = """
                SELECT id, name
                FROM buildings
                WHERE client_id = ?
                  AND is_active = 1
            """
            if filtered_ids is not None:
                placeholders = ",".join("?" * len(filtered_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(filtered_ids)
            query += " ORDER BY name COLLATE NOCASE"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [{"id": row["id"], "name": row["name"]} for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def list_tenants_for_client(
        client_id: int,
        tenant_ids: Optional[Sequence[int]] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, Any]]:
        """Return tenants for the supplied client filtered by optional identifiers."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            params: List[Any] = [client_id]
            filtered_ids: Optional[List[int]] = None
            if tenant_ids is not None:
                filtered_ids = [int(tenant_id) for tenant_id in tenant_ids if tenant_id is not None]
                if not filtered_ids:
                    return []
            query = """
                SELECT id, name
                FROM tenants
                WHERE client_id = ?
            """
            if filtered_ids is not None:
                placeholders = ",".join("?" * len(filtered_ids))
                query += f" AND id IN ({placeholders})"
                params.extend(filtered_ids)
            query += " ORDER BY name COLLATE NOCASE"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [{"id": row["id"], "name": row["name"]} for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_tenant_by_id(
        tenant_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return tenant metadata (id, client_id, name) by identifier."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, client_id, name
                FROM tenants
                WHERE id = ?
                LIMIT 1
                """,
                (tenant_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {"id": row["id"], "client_id": row["client_id"], "name": row["name"]}
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_tenant_by_name(
        client_id: int,
        tenant_name: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return tenant metadata by name within a client."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, client_id, name
                FROM tenants
                WHERE client_id = ?
                  AND LOWER(name) = LOWER(?)
                LIMIT 1
                """,
                (client_id, tenant_name),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {"id": row["id"], "client_id": row["client_id"], "name": row["name"]}
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def load_power_data_for_tenant(
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
        load_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Load aggregated consumption or manual meter data for the given tenants."""
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            timestamp_column = "c.timestamp"
            params: List[object] = [tenant_id]
            load_filter = ""
            filtered_loads: Optional[List[int]] = None
            if load_ids:
                filtered_loads = sorted({int(load_id) for load_id in load_ids})
                if not filtered_loads:
                    logger_obj.warning(
                        f"Provided load_ids for tenant_id {tenant_id} are empty after filtering."
                    )
                    empty_df = pd.DataFrame({col: [] for col in ["tenant_id", "load_id", "meter_id", "load_kW"]})
                    empty_df.index = pd.DatetimeIndex([], name="timestamp")
                    return empty_df
                placeholders = ",".join(["?"] * len(filtered_loads))
                load_filter = f" AND ulh.load_id IN ({placeholders})"
                params.extend(filtered_loads)
            query = f"""
                SELECT
                    uth.tenant_id,
                    ulh.load_id,
                    NULL AS meter_id,
                    {timestamp_column} AS timestamp,
                    c.load_kW AS load_kW,
                    c.consumption_kWh AS consumption_kWh
                FROM unit_tenants_history AS uth
                JOIN unit_loads_history AS ulh
                    ON ulh.unit_id = uth.unit_id
                JOIN consumptions AS c
                    ON c.load_id = ulh.load_id
                WHERE uth.is_active = 1
                    AND ulh.is_active = 1
                    AND uth.tenant_id = ?
            """
            query += load_filter

            if start_date:
                query += f" AND {timestamp_column} >= ?"
                params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))

            if end_date:
                query += f" AND {timestamp_column} <= ?"
                params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))

            query += f" ORDER BY {timestamp_column}"

            logger_obj.debug(
                f"Loading power data for tenant_id: {tenant_id} "
                f"between {start_date} and {end_date} "
                + (f"for loads {filtered_loads}" if filtered_loads else "(all loads)")
            )

            df = pd.read_sql_query(query, conn, params=params, parse_dates=["timestamp"])

            if df.empty:
                logger_obj.warning(f"No power data found for tenant_id: {tenant_id}")
                empty_df = pd.DataFrame({col: [] for col in ["tenant_id", "load_id", "meter_id", "load_kW"]})
                empty_df.index = pd.DatetimeIndex([], name="timestamp")
                return empty_df

            df.sort_values("timestamp", inplace=True)
            df.set_index("timestamp", inplace=True)

            logger_obj.debug(f"Loaded {len(df)} rows of power data for tenant_id: {tenant_id}")
            return df
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def load_consumption_data_by_load_name(
        load_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> pd.DataFrame:
        """Convenience helper to fetch consumption data by load name."""
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)
        load_id = ReportingDbQueries.find_load_id_by_name(load_name, conn)
        if load_id is None:
            logger_obj.warning(f"Load '{load_name}' not found in database")
            empty_df = pd.DataFrame({"load_kW": []})
            empty_df.index = pd.DatetimeIndex([], name="timestamp")
            return empty_df

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            params: List[object] = [load_id]
            query = """
                SELECT
                    c.timestamp,
                    c.load_kW
                FROM consumptions AS c
                WHERE c.load_id = ?
            """
            if start_date:
                query += " AND c.timestamp >= ?"
                params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
            if end_date:
                query += " AND c.timestamp <= ?"
                params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))

            query += " ORDER BY c.timestamp"

            df = pd.read_sql_query(query, conn, params=params, parse_dates=["timestamp"])
            if df.empty:
                logger_obj.warning(f"No consumption data found for load '{load_name}'")
                empty_df = pd.DataFrame({"load_kW": []})
                empty_df.index = pd.DatetimeIndex([], name="timestamp")
                return empty_df

            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
            logger_obj.debug(f"Loaded {len(df)} rows for load '{load_name}'")
            return df
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_load_names_for_load_ids(load_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> List[str]:
        """Return load names for the supplied identifiers."""
        if not load_ids:
            return []
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            placeholders = ",".join(["?"] * len(load_ids))
            query = f"""
                SELECT load_name
                FROM loads
                WHERE id IN ({placeholders})
                ORDER BY load_name
            """
            cursor = conn.cursor()
            cursor.execute(query, load_ids)
            rows = cursor.fetchall()
            return [row["load_name"] for row in rows]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_default_values_client_for_client(client_id: int, conn: Optional[sqlite3.Connection] = None) -> pd.DataFrame:
        """Get client-level cutoff defaults."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT c.id, c.cutoff_day, c.cutoff_hour, c.cutoff_minute, c.cutoff_second "
                "FROM clients AS c "
                "WHERE c.id = ?",
                (client_id,),
            )
            rows = cursor.fetchall()
            columns = pd.Index([str(desc[0]) for desc in cursor.description])
            return pd.DataFrame(rows, columns=columns)
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_default_values_building_for_client(
        client_id: int, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[pd.DataFrame]:
        """Get building-level cutoff defaults for a client."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT b.client_id, b.id as building_id, b.cutoff_day, b.cutoff_hour, b.cutoff_minute FROM buildings b WHERE b.client_id = ?",
                    (client_id,),
                )
            except sqlite3.OperationalError:
                empty_columns = pd.Index(["client_id", "building_id", "cutoff_day", "cutoff_hour", "cutoff_minute"])
                return pd.DataFrame(columns=empty_columns)

            rows = cursor.fetchall()
            if not rows:
                return None
            columns = pd.Index([str(desc[0]) for desc in cursor.description])
            return pd.DataFrame(rows, columns=columns)
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_default_values_for_client(client_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
        """Get client-level cutoff defaults."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT cutoff_day, cutoff_hour, cutoff_minute, cutoff_second
                FROM clients
                WHERE id = ? AND is_active = 1
                LIMIT 1
                """,
                (client_id,),
            )
            row = cursor.fetchone()
            return {
                "cutoff_day": row["cutoff_day"],
                "cutoff_hour": row["cutoff_hour"],
                "cutoff_minute": row["cutoff_minute"],
                "cutoff_second": row["cutoff_second"],
            } if row else None
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_default_values_for_building(
        building_id: int, conn: Optional[sqlite3.Connection] = None
    ) -> Optional[dict[str, Any]]:
        """Get building-level cutoff defaults."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT cutoff_day, cutoff_hour, cutoff_minute, cutoff_second
                FROM buildings
                WHERE id = ?
                LIMIT 1
                """,
                (building_id,),
            )
            row = cursor.fetchone()
            return {
                "cutoff_day": row["cutoff_day"],
                "cutoff_hour": row["cutoff_hour"],
                "cutoff_minute": row["cutoff_minute"],
                "cutoff_second": row["cutoff_second"],
            } if row else None
        finally:
            if close_conn:
                conn.close()
            

    @staticmethod
    def get_epc_building_tenant_load_from_epc(
        epc_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> pd.DataFrame:
        """Return mappings of EPC to buildings and loads."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_uth_tenant_active_unit
                ON unit_tenants_history(tenant_id, unit_id)
                WHERE is_active = 1
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_umh_unit_active
                ON unit_meters_history(unit_id, meter_id)
                WHERE is_active = 1
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ulh_unit_active
                ON unit_loads_history(unit_id, load_id)
                WHERE is_active = 1
                """
            )

            query = (
                """
                SELECT
                    c.epc_id,
                    u.building_id,
                    ulh.load_id
                FROM unit_loads_history AS ulh
                JOIN units AS u ON ulh.unit_id = u.id
                JOIN buildings AS b ON u.building_id = b.id
                JOIN clients AS c ON b.client_id = c.id
                WHERE ulh.is_active = 1
                  AND c.epc_id = ?
                GROUP BY c.epc_id, u.building_id, ulh.load_id
                """
            )

            cursor.execute(query, (epc_id,))
            rows = cursor.fetchall()
            return pd.DataFrame(rows)
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_epc_building_tenant_load_from_building(
        building_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> pd.DataFrame:
        """Return mappings of building to loads within its EPC."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_unit_loads_history_active
                ON unit_loads_history(unit_id, load_id)
                WHERE is_active = 1
                """
            )

            query = (
                """
                SELECT
                    c.epc_id,
                    u.building_id,
                    ulh.load_id
                FROM unit_loads_history AS ulh
                JOIN units AS u ON ulh.unit_id = u.id
                JOIN buildings AS b ON u.building_id = b.id
                JOIN clients AS c ON b.client_id = c.id
                WHERE ulh.is_active = 1
                  AND u.building_id = ?
                GROUP BY c.epc_id, u.building_id, ulh.load_id
                """
            )

            cursor.execute(query, (building_id,))
            rows = cursor.fetchall()
            return pd.DataFrame(rows)
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_tenant_sqm_data_for_client(client_id, conn: Optional[sqlite3.Connection] = None) -> Dict[int, float]:
        """Aggregate total square meters per tenant for the supplied IDs."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            if not client_id:
                return {}

            query = f"""
                SELECT 
                    uth.tenant_id,
                    SUM(u.square_meters) AS total_square_meters
                FROM unit_tenants_history AS uth
                JOIN units AS u ON uth.unit_id = u.id
                JOIN buildings AS b ON u.building_id = b.id
                WHERE uth.is_active = 1
                  AND b.client_id = ?
                GROUP BY uth.tenant_id
            """
            cursor = conn.cursor()
            cursor.execute(query, (client_id,))
            rows = cursor.fetchall()
            return {row["tenant_id"]: row["total_square_meters"] for row in rows}
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_tenant_info(tenant_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """Get tenant information for the given tenant ID."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    t.name AS tenant_name,
                    t.billing_address AS tenant_billing_address,
                    c.first_name AS contact_first_name,
                    c.last_name AS contact_last_name,
                    c.email AS contact_email,
                    u.first_name AS user_first_name,
                    u.last_name AS user_last_name,
                    u.email AS user_email
                FROM tenants AS t
                LEFT JOIN entities AS e
                  ON e.entity_type = 'tenant'
                 AND e.entity_ref_id = t.id
                LEFT JOIN entity_user_assignments AS eua
                  ON eua.entity_id = e.id
                 AND (eua.assigned_until IS NULL OR eua.assigned_until > CURRENT_TIMESTAMP)
                LEFT JOIN users AS u
                  ON u.id = eua.user_id
                 AND u.active = 1
                LEFT JOIN contacts AS c
                  ON c.user_id = u.id
                WHERE t.id = ?
                ORDER BY eua.assigned_at DESC
                LIMIT 1
                """,
                (tenant_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "name": None,
                    "billing_address": None,
                    "contact_name": None,
                    "contact_email": None,
                }
            contact_first = row["contact_first_name"] or row["user_first_name"] or ""
            contact_last = row["contact_last_name"] or row["user_last_name"] or ""
            contact_name_parts = [part for part in [contact_first, contact_last] if part]
            contact_name = " ".join(contact_name_parts) if contact_name_parts else None
            contact_email = row["contact_email"] or row["user_email"]
            return {
                "name": row["tenant_name"],
                "billing_address": row["tenant_billing_address"],
                "contact_name": contact_name,
                "contact_email": contact_email,
            }
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_client_id_for_tenant(
        tenant_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[int]:
        """Return the client identifier for a tenant."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT client_id FROM tenants WHERE id = ? LIMIT 1",
                (tenant_id,),
            )
            row = cursor.fetchone()
            return row["client_id"] if row else None
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_info_for_user(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """Return the information for a user."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.epc_id as epc_id, e.client_id as client_id, e.tenant_id as tenant_id
                FROM entity_user_assignments AS eua
                JOIN entities AS e ON e.id = eua.entity_id
                WHERE eua.user_id = ? AND eua.assigned_until IS NULL
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            if len(rows) == 0:
                return {"epc_id": [], "client_id": [], "tenant_id": []}
            list_epc_ids = {
                int(row["epc_id"])
                for row in rows
                if row["epc_id"] is not None
            }
            list_client_ids = {
                int(row["client_id"])
                for row in rows
                if row["client_id"] is not None
            }
            list_tenant_ids = {
                int(row["tenant_id"])
                for row in rows
                if row["tenant_id"] is not None
            }
            return {
                "epc_id": sorted(list_epc_ids),
                "client_id": sorted(list_client_ids),
                "tenant_id": sorted(list_tenant_ids),
            }
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_building_id_for_tenant(
        tenant_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[int]:
        """Return the building identifier for a tenant."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT u.building_id FROM units u JOIN unit_tenants_history uth ON u.id = uth.unit_id WHERE uth.tenant_id = ? AND uth.is_active = 1 LIMIT 1",
                (tenant_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            if isinstance(row, sqlite3.Row):
                return row["building_id"] if "building_id" in row.keys() else row[0]
            return row[0]
        finally:
            if close_conn:
                conn.close()


    @staticmethod
    def get_default_values_for_epc(
        epc_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[dict[str, Any]]:
        """Return the default cutoff values for an EPC."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT cutoff_day, cutoff_hour, cutoff_minute, cutoff_second
                FROM epcs
                WHERE id = ? AND is_active = 1
                LIMIT 1
                """,
                (epc_id,),
            )
            row = cursor.fetchone()
            
            return {
                "cutoff_day": row["cutoff_day"],
                "cutoff_hour": row["cutoff_hour"],
                "cutoff_minute": row["cutoff_minute"],
                "cutoff_second": row["cutoff_second"],
            } if row else None
        finally:
            if close_conn:
                conn.close()


    @staticmethod
    def get_epc_id_for_client(client_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        """Return the EPC identifier for a client."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT c.epc_id FROM clients c WHERE c.id = ? LIMIT 1", (client_id,))
            row = cursor.fetchone()
            return row[0] if row else None if isinstance(row, sqlite3.Row) else None
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_last_n_records_for_client(client_id: int, n: int, conn: Optional[sqlite3.Connection] = None) -> pd.DataFrame:
        """Return the last records for a client."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            list_rn = [str(i) for i in range(1, n+1)]
            list_rn_str = ','.join(list_rn)
            query = """
                WITH ranked_records AS (
                    SELECT 
                        b.name as building_name,
                        t.name as tenant_name,
                        u.id as unit_id,
                        u.unit_number,
                        m.meter_ref,
                        m.description,
                        m.multiplier,
                        mr.timestamp_record,
                        mr.meter_kWh,
                        ROW_NUMBER() OVER (
                            PARTITION BY m.id 
                            ORDER BY mr.timestamp_record DESC
                        ) as rn
                    FROM meter_records mr
                    JOIN meters m ON mr.meter_id = m.id
                    JOIN unit_meters_history umh ON m.id = umh.meter_id AND umh.is_active = 1
                    JOIN units u ON umh.unit_id = u.id
                    JOIN unit_tenants_history uth ON u.id = uth.unit_id AND uth.is_active = 1
                    JOIN tenants t ON uth.tenant_id = t.id
                    JOIN buildings b ON u.building_id = b.id
                    WHERE t.client_id = ?
                )
                SELECT 
                    building_name,
                    tenant_name,
                    unit_id,
                    unit_number,
                    meter_ref,
                    description,
                    timestamp_record,
                    meter_kWh,
                    multiplier
                FROM ranked_records
                WHERE rn in ({list_rn_str})
                ORDER BY building_name ASC, tenant_name ASC, unit_number ASC, timestamp_record DESC
            """.format(list_rn_str=list_rn_str)
            cursor = conn.cursor()
            cursor.execute(query, (client_id,))
            rows = cursor.fetchall()
            return pd.DataFrame(rows)
        finally:
            if close_conn:
                conn.close()


    @staticmethod
    def get_consumptions_for_unit_during_period(unit_id: int, timestamp_start: datetime, timestamp_end: datetime, conn: Optional[sqlite3.Connection] = None) -> pd.DataFrame:
        """Return the consumptions for the given loads during the given period."""
        # Convert unit_id to Python int (in case it's numpy.int64 or other numeric type)
        unit_id = int(unit_id)
        
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            query = """
                SELECT ulh.unit_id, SUM(c.consumption_kWh) as smappy_consumption_kWh, GROUP_CONCAT(DISTINCT l.load_name) as smappy_load_name
                FROM consumptions c
                JOIN unit_loads_history ulh ON c.load_id = ulh.load_id AND ulh.is_active = 1
                JOIN loads l ON c.load_id = l.id
                WHERE ulh.unit_id = ? AND c.timestamp >= ? AND c.timestamp <= ?
                GROUP BY ulh.unit_id
            """
            start = timestamp_start.strftime("%Y-%m-%d %H:%M:%S")
            end = timestamp_end.strftime("%Y-%m-%d %H:%M:%S")
            ReportingDbQueries.logger.debug(f"Executing consumption query for unit_id={unit_id} - start={start} - end={end}")
            cursor.execute(query, (unit_id, start, end))
            rows = cursor.fetchall()
            ReportingDbQueries.logger.debug(f"Query returned {len(rows)} rows")
            return pd.DataFrame(rows, columns=['unit_id', 'smappy_consumption_kWh', 'smappy_load_name']) if rows else pd.DataFrame(columns=['unit_id', 'smappy_consumption_kWh', 'smappy_load_name'])
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_load_info(load_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> pd.DataFrame:
        """Return the load info for the given load ids."""
        close_conn = False
        parameters = ",".join("?" for _ in load_ids)
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT l.id as id, l.load_name, l.description as load_description, u.floor, u.unit_number as unit_number FROM loads l JOIN unit_loads_history ulh ON l.id = ulh.load_id JOIN units u on ulh.unit_id = u.id WHERE ulh.is_active = 1 AND l.id IN ({parameters})", (*load_ids,))
            rows = cursor.fetchall()
            # Explicitly set column names since SQLite may return tuples or dicts
            df = pd.DataFrame(rows, columns=['id', 'load_name', 'load_description', 'floor', 'unit_number'])
            return df
        finally:
            if close_conn:
                conn.close()