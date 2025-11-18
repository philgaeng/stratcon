#!/usr/bin/env python3
"""Database query helpers dedicated to the meter logging / encoding workflows."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple, cast

from backend.services.data.db_manager.db_schema import get_db_connection
from backend.services.core.utils import ReportLogger


def _get_units_table_columns(cursor: sqlite3.Cursor) -> set[str]:
    """
    Return the set of column names available on the `units` table.

    Helpful for installations that added `tenant_id`/`name` columns directly on the table.
    """
    cursor.execute("PRAGMA table_info(units)")
    columns: set[str] = set()
    for row in cursor.fetchall():
        if isinstance(row, sqlite3.Row):
            columns.add(row["name"])
        else:
            columns.add(row[1])
    return columns


class MeterLoggingDbQueries:
    """Static helpers for meter logging related database access."""

    @staticmethod
    def get_user_role_for_user(
        user_id: int,
        conn: Optional[sqlite3.Connection] = None,
    ) -> str:
        """Resolve the user_group for a user (returns user_group value from users table)."""
        if user_id is None:
            raise ValueError("user_id cannot be None")
        
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_group FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"User with id {user_id} not found")
            return row["user_group"]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_meter_pk_for_identifier(
        meter_identifier: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> int:
        """Resolve the internal meter primary key from the client-facing identifier."""
        if not meter_identifier:
            raise ValueError("meter identifier must be provided")

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM meters WHERE meter_id = ? OR meter_ref = ?",
                (meter_identifier, meter_identifier),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Meter '{meter_identifier}' not found")
            return row["id"]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def list_all_buildings(
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Dict[str, object]]:
        """List all buildings."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, client_id FROM buildings WHERE is_active = 1")
            return [{"id": row["id"], "name": row["name"], "client_id": row["client_id"]} for row in cursor.fetchall()]
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def list_tenants_for_building(
        building_id: int,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[Dict[str, object]]:
        """Return tenant summaries for the given building."""
        if building_id is None:
            raise ValueError("building_id cannot be None")
            
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    t.id AS tenant_id,
                    t.name AS tenant_name,
                    b.id AS building_id,
                    b.name AS building_name,
                    b.client_id,
                    COUNT(DISTINCT u.floor) AS number_of_floors,
                    COUNT(DISTINCT u.id) AS active_units,
                    MAX(mr.timestamp_record) AS last_record_at
                FROM unit_tenants_history AS uth
                JOIN tenants AS t ON uth.tenant_id = t.id
                JOIN units AS u ON uth.unit_id = u.id
                JOIN buildings AS b ON u.building_id = b.id
                LEFT JOIN unit_meters_history AS umh ON umh.unit_id = u.id AND umh.is_active = 1
                LEFT JOIN meter_records AS mr ON mr.meter_id = umh.meter_id
                WHERE uth.is_active = 1
                  AND b.id = ?
                GROUP BY t.id, b.id
                ORDER BY b.name, t.name
                """,
                (building_id,),
            )

            rows = cursor.fetchall()
            summaries: List[Dict[str, object]] = []
            for row in rows:
                summaries.append(
                    {
                        "tenant_id": row["tenant_id"],
                        "tenant_name": row["tenant_name"],
                        "client_id": row["client_id"],
                        "building": {
                            "id": row["building_id"],
                            "name": row["building_name"],
                        },
                        "number_of_floors": row["number_of_floors"] or 0,
                        "active_units": row["active_units"] or 0,
                        "last_record_at": row["last_record_at"],
                    }
                )

            logger_obj.debug(
                f"Tenant summary query for building {building_id} "
                f"returned {len(summaries)} rows"
            )
            return summaries
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def _get_meter_ids_for_tenant(
        tenant_id: int,
        conn: sqlite3.Connection,
    ) -> Set[int]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT umh.meter_id
            FROM unit_tenants_history AS uth
            JOIN unit_meters_history AS umh ON umh.unit_id = uth.unit_id
            WHERE uth.tenant_id = ?
              AND uth.is_active = 1
              AND umh.is_active = 1
            """,
            (tenant_id,),
        )
        return {row["meter_id"] for row in cursor.fetchall()}

    @staticmethod
    def _get_latest_records_for_meters(
        meter_ids: Iterable[int],
        conn: sqlite3.Connection,
    ) -> Dict[int, sqlite3.Row]:
        meter_ids = list(set(meter_ids))
        if not meter_ids:
            return {}
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(meter_ids))
        cursor.execute(
            f"""
            SELECT mr.*
            FROM meter_records AS mr
            JOIN (
                SELECT meter_id, MAX(timestamp_record) AS max_ts
                FROM meter_records
                WHERE meter_id IN ({placeholders})
                GROUP BY meter_id
            ) AS latest
            ON latest.meter_id = mr.meter_id
           AND latest.max_ts = mr.timestamp_record
            WHERE mr.meter_id IN ({placeholders})
            ORDER BY mr.meter_id
            """,
            meter_ids + meter_ids,
        )
        rows = cursor.fetchall()
        latest: Dict[int, sqlite3.Row] = {}
        for row in rows:
            # If multiple rows share the same timestamp, keep the one encountered first.
            if row["meter_id"] not in latest:
                latest[row["meter_id"]] = row
        return latest

    @staticmethod
    def list_buildings_for_user(
        user_id: int,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[Dict[str, object]]:
        """
        Return buildings accessible to a user based on their assignments.
        
        Gets buildings from:
        1. Direct building assignments via entity_user_assignments (entity_type='building')
        2. Client assignments via entity_user_assignments (entity_type='client') - all buildings for those clients
        3. EPC assignments via user.entity_id or entity_user_assignments (entity_type='epc') - all buildings for that EPC
        """
        if user_id is None:
            raise ValueError("user_id cannot be None")
            
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            building_ids: Set[int] = set()

            # 1. Get clients from the entity_user_assignments table
            cursor.execute("""
                SELECT e.client_id
                FROM entity_user_assignments AS eua
                JOIN entities AS e ON e.id = eua.entity_id
                WHERE eua.user_id = ?
                  AND eua.assigned_until IS NULL
                  AND e.client_id IS NOT NULL
            """, (user_id,))
            client_id = cursor.fetchone()["client_id"]
            # 2. We generate the list of  building is that are related to this entity_idc
            cursor.execute("""
                SELECT b.id, b.name, b.client_id
                FROM buildings AS b
                WHERE b.client_id = ?
            """, (client_id,))
            building_rows = cursor.fetchall()
            buildings = [{"id": row["id"], "name": row["name"], "client_id": row["client_id"]} for row in building_rows]
            logger_obj.debug(f"Found {len(buildings)} buildings for user {user_id}")
            return buildings
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_floors_for_tenant(
        tenant_id: int,
        tenant_token: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[Dict[str, object]]:
        """Return distinct floors for a tenant with unit and meter counts."""
        if tenant_id is None:
            raise ValueError("tenant_id cannot be None")

        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            units_columns = _get_units_table_columns(cursor)

            if "tenant_id" in units_columns:
                filters: List[str] = []
                params: List[object] = []
                if tenant_id is not None:
                    filters.append("u.tenant_id = ?")
                    params.append(tenant_id)
                if tenant_token:
                    filters.append("LOWER(u.tenant_id) = LOWER(?)")
                    params.append(tenant_token)
                if not filters:
                    raise ValueError("Could not determine tenant filter for floors query.")

                cursor.execute(
                    f"""
                    SELECT
                        u.floor,
                        COUNT(DISTINCT u.id) AS unit_count,
                        COUNT(DISTINCT umh.meter_id) AS meter_count
                    FROM units AS u
                    LEFT JOIN unit_meters_history AS umh
                      ON umh.unit_id = u.id
                     AND umh.is_active = 1
                    WHERE ({' OR '.join(filters)})
                      AND u.floor IS NOT NULL
                    GROUP BY u.floor
                    ORDER BY u.floor
                    """,
                    params,
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        u.floor,
                        COUNT(DISTINCT u.id) AS unit_count,
                        COUNT(DISTINCT umh.meter_id) AS meter_count
                    FROM unit_tenants_history AS uth
                    JOIN units AS u ON u.id = uth.unit_id
                    LEFT JOIN unit_meters_history AS umh
                      ON umh.unit_id = u.id
                     AND umh.is_active = 1
                    WHERE uth.tenant_id = ?
                      AND uth.is_active = 1
                      AND u.floor IS NOT NULL
                    GROUP BY u.floor
                    ORDER BY u.floor
                    """,
                    (tenant_id,),
                )

            rows = cursor.fetchall()
            floors = []
            for row in rows:
                floor_value = row["floor"]
                try:
                    floor_value = int(floor_value) if floor_value is not None else None
                except (TypeError, ValueError):
                    floor_value = None

                floors.append(
                    {
                        "floor": floor_value,
                        "unit_count": row["unit_count"],
                        "meter_count": row["meter_count"],
                    }
                )

            logger_obj.debug(
                f"Found {len(floors)} floors for tenant {tenant_id}"
            )
            return floors
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_units_for_tenant(
        tenant_id: int,
        floor: Optional[int] = None,
        *,
        tenant_token: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[Dict[str, object]]:
        """Return active units for a tenant, optionally filtered by floor."""
        if tenant_id is None:
            raise ValueError("tenant_id cannot be None")

        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            params: List[object] = []
            floor_filter = ""
            if floor is not None:
                floor_filter = "AND u.floor = ?"
                params.append(floor)

            units_columns = _get_units_table_columns(cursor)

            if "tenant_id" in units_columns:
                select_name = "u.name" if "name" in units_columns else "NULL"
                filters: List[str] = []
                tenant_params: List[object] = []
                if tenant_id is not None:
                    filters.append("u.tenant_id = ?")
                    tenant_params.append(tenant_id)
                if tenant_token:
                    filters.append("LOWER(u.tenant_id) = LOWER(?)")
                    tenant_params.append(tenant_token)
                if not filters:
                    raise ValueError("Could not determine tenant filter for units query.")

                cursor.execute(
                    f"""
                    SELECT DISTINCT
                        u.id AS unit_id,
                        u.unit_number,
                        {select_name} AS unit_name,
                        u.floor
                    FROM units AS u
                    WHERE ({' OR '.join(filters)})
                      {floor_filter}
                    ORDER BY
                        CASE WHEN u.unit_number IS NULL THEN 1 ELSE 0 END,
                        u.unit_number COLLATE NOCASE
                    """,
                    [*tenant_params, *params],
                )
            else:
                cursor.execute(
                    f"""
                    SELECT DISTINCT
                        u.id AS unit_id,
                        u.unit_number,
                        NULL AS unit_name,
                        u.floor
                    FROM unit_tenants_history AS uth
                    JOIN units AS u ON u.id = uth.unit_id
                    WHERE uth.tenant_id = ?
                      AND uth.is_active = 1
                      {floor_filter}
                    ORDER BY
                        CASE WHEN u.unit_number IS NULL THEN 1 ELSE 0 END,
                        u.unit_number COLLATE NOCASE
                    """,
                    [tenant_id, *params],
                )

            rows = cursor.fetchall()
            units: List[Dict[str, object]] = []
            for row in rows:
                units.append(
                    {
                        "unit_id": row["unit_id"],
                        "unit_number": row["unit_number"],
                        "name": row["unit_name"],
                        "floor": row["floor"],
                    }
                )
            logger_obj.debug(
                f"Found {len(units)} units for tenant {tenant_id}"
                + (f" on floor {floor}" if floor is not None else "")
            )
            return units
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_meter_assignments_for_tenant(
        tenant_id: int,
        floor: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[Dict[str, object]]:
        """Return meter assignments (meter info, unit info, load ids, last reading), optionally filtered by floor."""
        if tenant_id is None:
            raise ValueError("tenant_id cannot be None")

        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            params: List[object] = [tenant_id]
            floor_filter = ""
            if floor is not None:
                floor_filter = "AND u.floor = ?"
                params.append(floor)

            cursor.execute(
                f"""
                SELECT
                    umh.meter_id AS meter_pk,
                    m.meter_ref AS meter_ref,
                    u.id AS unit_id,
                    u.unit_number,
                    u.floor,
                    ulh.load_id
                FROM unit_tenants_history AS uth
                JOIN unit_meters_history AS umh
                  ON umh.unit_id = uth.unit_id
                 AND umh.is_active = 1
                JOIN meters AS m ON m.id = umh.meter_id
                JOIN units AS u ON u.id = umh.unit_id
                LEFT JOIN unit_loads_history AS ulh
                  ON ulh.unit_id = u.id
                 AND ulh.is_active = 1
                WHERE uth.tenant_id = ?
                  AND uth.is_active = 1
                  {floor_filter}
                ORDER BY u.unit_number, m.meter_ref
                """,
                params,
            )

            meter_rows = cursor.fetchall()
            assignments: Dict[int, Dict[str, object]] = {}
            for row in meter_rows:
                meter_pk = row["meter_pk"]
                if meter_pk not in assignments:
                    assignments[meter_pk] = {
                        "meter_pk": meter_pk,
                        "meter_identifier": row["meter_ref"],
                        "unit": {
                            "id": row["unit_id"],
                            "unit_number": row["unit_number"],
                            "floor": row["floor"],
                        },
                        "loads": set(),
                    }
                if row["load_id"] is not None:
                    assignments[meter_pk]["loads"].add(row["load_id"])

            latest_records = MeterLoggingDbQueries._get_latest_records_for_meters(
                assignments.keys(),
                conn,
            )

            results: List[Dict[str, object]] = []
            for meter_pk, data in assignments.items():
                loads_sorted = sorted(data["loads"])
                record = latest_records.get(meter_pk)
                identifier = data["meter_identifier"] or str(meter_pk)
                results.append(
                    {
                        "meter_pk": meter_pk,
                        "meter_id": identifier,
                        "unit": data["unit"],
                        "loads": loads_sorted,
                        "last_record": (
                            {
                                "timestamp_record": record["timestamp_record"],
                                "meter_kWh": record["meter_kWh"],
                            }
                            if record
                            else None
                        ),
                    }
                )
            logger_obj.debug(
                f"Meter assignments for tenant {tenant_id}: returned {len(results)} meters"
            )
            return results
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_loads_grouped_by_meter_for_tenant(
        tenant_id: int,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> Dict[int, List[int]]:
        """Return mapping of meter_id -> [load_id, ...] for a tenant's active assignments."""
        if tenant_id is None:
            raise ValueError("tenant_id cannot be None")

        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_unit_meters_history_active
                ON unit_meters_history(unit_id, meter_id)
                WHERE is_active = 1
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_unit_loads_history_active
                ON unit_loads_history(unit_id, load_id)
                WHERE is_active = 1
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_unit_tenants_history_active
                ON unit_tenants_history(unit_id, tenant_id)
                WHERE is_active = 1
                """
            )

            cursor.execute(
                """
                SELECT DISTINCT
                    umh.meter_id,
                    ulh.load_id
                FROM unit_meters_history AS umh
                JOIN unit_loads_history AS ulh
                  ON ulh.unit_id = umh.unit_id
                JOIN unit_tenants_history AS uth
                  ON uth.unit_id = umh.unit_id
                WHERE umh.is_active = 1
                  AND ulh.is_active = 1
                  AND uth.is_active = 1
                  AND uth.tenant_id = ?
                """,
                (tenant_id,),
            )

            rows = cursor.fetchall()
            grouped: Dict[int, Set[int]] = defaultdict(set)
            for row in rows:
                grouped[row["meter_id"]].add(row["load_id"])

            result = {meter_id: sorted(load_ids) for meter_id, load_ids in grouped.items()}
            logger_obj.debug(
                f"Loaded meter/load mapping for tenant {tenant_id}: "
                f"{ {mid: len(loads) for mid, loads in result.items()} }"
            )
            return result
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_meter_records_timestamps(
        meter_id: int,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[str]:
        """Load meter records timestamps for a given meter."""
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp_record FROM meter_records WHERE meter_id = ?", (meter_id,))
            rows = cursor.fetchall()
            timestamps = [row["timestamp_record"] for row in rows]
            logger_obj.debug(f"Fetched {len(timestamps)} timestamps for meter {meter_id}")
            return timestamps
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_meters_grouped_by_tenant_and_load(
        tenant_id: int,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> Dict[int, List[int]]:
        """Return mapping of load_id -> [meter_id, ...] for a tenant's active assignments."""
        if tenant_id is None:
            raise ValueError("tenant_id cannot be None")

        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

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
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_unit_meters_history_active
                ON unit_meters_history(unit_id, meter_id)
                WHERE is_active = 1
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_unit_tenants_history_active
                ON unit_tenants_history(unit_id, tenant_id)
                WHERE is_active = 1
                """
            )

            cursor.execute(
                """
                SELECT DISTINCT
                    ulh.load_id,
                    umh.meter_id
                FROM unit_loads_history AS ulh
                JOIN unit_tenants_history AS uth ON ulh.unit_id = uth.unit_id
                JOIN unit_meters_history AS umh ON ulh.unit_id = umh.unit_id
                WHERE ulh.is_active = 1
                  AND uth.is_active = 1
                  AND umh.is_active = 1
                  AND uth.tenant_id = ?
                """,
                (tenant_id,),
            )

            rows = cursor.fetchall()
            grouped: Dict[int, Set[int]] = defaultdict(set)
            for row in rows:
                grouped[row["load_id"]].add(row["meter_id"])

            result = {load_id: sorted(meter_ids) for load_id, meter_ids in grouped.items()}
            logger_obj.debug(
                f"Loaded load/meter mapping for tenant {tenant_id}: "
                f"{ {lid: len(meters) for lid, meters in result.items()} }"
            )
            return result
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def insert_meter_records(
        tenant_id: int,
        session_id: str,
        records: List[Dict[str, object]],
        encoder_user_id: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
        """Insert meter records in bulk while enforcing non-decreasing readings."""
        if not session_id:
            raise ValueError("session_id must be provided")
        if not records:
            return [], []

        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            meter_ids_for_tenant = MeterLoggingDbQueries._get_meter_ids_for_tenant(tenant_id, conn)
            requested_meter_ids = {int(record["meter_id"]) for record in records}
            identifier_map = {
                int(record["meter_id"]): record.get("meter_identifier", str(record["meter_id"]))
                for record in records
            }
            unknown_meters = requested_meter_ids - meter_ids_for_tenant
            if unknown_meters:
                unknown_labels = [
                    identifier_map.get(meter_pk, str(meter_pk)) for meter_pk in sorted(unknown_meters)
                ]
                raise ValueError(
                    f"Meters {unknown_labels} are not assigned to tenant {tenant_id}"
                )

            latest_by_meter = MeterLoggingDbQueries._get_latest_records_for_meters(
                requested_meter_ids,
                conn,
            )

            accepted: List[Dict[str, object]] = []
            warnings: List[Dict[str, object]] = []

            cursor = conn.cursor()
            for record in records:
                meter_id = int(record["meter_id"])
                client_record_id = record.get("client_record_id") or f"{session_id}:{meter_id}:{record.get('timestamp_record')}"
                timestamp_value = record.get("timestamp_record")
                if isinstance(timestamp_value, datetime):
                    if timestamp_value.tzinfo is None:
                        raise ValueError("timestamp_record must include timezone information")
                    timestamp_iso = timestamp_value.isoformat()
                else:
                    timestamp_iso = str(timestamp_value)
                    # Validate format
                    try:
                        datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
                    except ValueError as exc:
                        raise ValueError(f"Invalid ISO timestamp: {timestamp_iso}") from exc

                meter_kwh = float(record["meter_kWh"])
                previous = latest_by_meter.get(meter_id)
                if previous is not None and meter_kwh < float(previous["meter_kWh"]):
                    warnings.append(
                        {
                            "client_record_id": client_record_id,
                            "type": "decreasing_reading",
                            "message": (
                                f"New reading ({meter_kwh}) is below previous value "
                                f"({previous['meter_kWh']}). Record skipped."
                            ),
                        }
                    )
                    continue

                cursor.execute(
                    """
                    INSERT INTO meter_records (
                        meter_id,
                        tenant_id,
                        session_id,
                        client_record_id,
                        timestamp_record,
                        meter_kWh,
                        encoder_user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, client_record_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        meter_id,
                        tenant_id,
                        session_id,
                        client_record_id,
                        timestamp_iso,
                        meter_kwh,
                        encoder_user_id,
                    ),
                )
                inserted_row = cursor.fetchone()

                if inserted_row:
                    meter_record_id = inserted_row["id"]
                    latest_by_meter[meter_id] = {
                        "meter_id": meter_id,
                        "timestamp_record": timestamp_iso,
                        "meter_kWh": meter_kwh,
                    }
                    accepted.append(
                        {
                            "client_record_id": client_record_id,
                            "meter_record_id": meter_record_id,
                            "status": "accepted",
                        }
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, meter_kWh, timestamp_record
                        FROM meter_records
                        WHERE session_id = ? AND client_record_id = ?
                        """,
                        (session_id, client_record_id),
                    )
                    existing = cursor.fetchone()
                    accepted.append(
                        {
                            "client_record_id": client_record_id,
                            "meter_record_id": existing["id"] if existing else None,
                            "status": "duplicate",
                        }
                    )

            conn.commit()
            logger_obj.debug(
                f"Inserted meter records for tenant {tenant_id}, session {session_id}: "
                f"{len([a for a in accepted if a['status'] == 'accepted'])} accepted, "
                f"{len([a for a in accepted if a['status'] == 'duplicate'])} duplicate, "
                f"{len(warnings)} warnings"
            )
            return accepted, warnings
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def attach_approval_to_session(
        tenant_id: int,
        session_id: str,
        approver_name: str,
        approver_signature: Optional[str],
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> int:
        """Attach approval metadata to all meter records in a session."""
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE meter_records
                SET approver_name = ?, approver_signature = ?
                WHERE tenant_id = ? AND session_id = ?
                """,
                (approver_name, approver_signature, tenant_id, session_id),
            )
            conn.commit()
            updated = cursor.rowcount
            logger_obj.debug(
                f"Approval metadata applied to {updated} records for tenant {tenant_id}, session {session_id}"
            )
            return updated
        finally:
            if close_conn:
                conn.close()

    @staticmethod
    def get_meter_records(
        tenant_id: Optional[int] = None,
        meter_id: Optional[int] = None,
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
        limit: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
        logger: Optional[ReportLogger] = None,
    ) -> List[Dict[str, object]]:
        """Retrieve meter records filtered by tenant/meter/time range."""
        if logger is None:
            logger = ReportLogger()
        logger_obj: ReportLogger = cast(ReportLogger, logger)

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor()
            conditions: List[str] = []
            params: List[object] = []

            if tenant_id is not None:
                conditions.append("mr.tenant_id = ?")
                params.append(tenant_id)
            if meter_id is not None:
                conditions.append("mr.meter_id = ?")
                params.append(meter_id)
            if from_timestamp is not None:
                conditions.append("mr.timestamp_record >= ?")
                params.append(from_timestamp)
            if to_timestamp is not None:
                conditions.append("mr.timestamp_record <= ?")
                params.append(to_timestamp)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            limit_clause = ""
            if limit is not None:
                limit_clause = "LIMIT ?"
                params.append(limit)

            cursor.execute(
                f"""
                SELECT
                    mr.id AS meter_record_id,
                    mr.meter_id AS meter_pk,
                    COALESCE(m.meter_id, m.meter_ref) AS meter_identifier,
                    mr.tenant_id,
                    mr.session_id,
                    mr.client_record_id,
                    mr.timestamp_record,
                    mr.meter_kWh,
                    mr.encoder_user_id,
                    mr.approver_name,
                    mr.approver_signature,
                    mr.created_at
                FROM meter_records AS mr
                JOIN meters AS m ON m.id = mr.meter_id
                {where_clause}
                ORDER BY mr.timestamp_record DESC, mr.created_at DESC
                {limit_clause}
                """,
                params,
            )
            rows = cursor.fetchall()
            logger_obj.debug(
                f"Fetched {len(rows)} meter records (tenant={tenant_id}, meter={meter_id})"
            )
            return [dict(row) for row in rows]
        finally:
            if close_conn:
                conn.close()

