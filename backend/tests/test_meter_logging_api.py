#!/usr/bin/env python3
"""Integration tests for the meter logging API endpoints."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.api import app  # noqa: E402
from backend.services.db_manager import db_schema  # noqa: E402
from backend.services.db_manager import MeterLoggingDbQueries  # noqa: E402
from backend.services.db_manager.db_schema import init_database  # noqa: E402


def seed_meter_logging_data() -> None:
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO epcs (id, name) VALUES (1, 'Test EPC')")
    cursor.execute("INSERT INTO clients (id, epc_id, name) VALUES (1, 1, 'Test Client')")
    cursor.execute(
        "INSERT INTO buildings (id, client_id, name, address) VALUES (1, 1, 'Test Building', '123 Test St')"
    )
    cursor.execute(
        "INSERT INTO units (id, building_id, unit_number, floor, unit_type, square_meters) "
        "VALUES (1, 1, '18A', 18, 'Office', 120.0)"
    )
    cursor.execute("INSERT INTO tenants (id, client_id, name) VALUES (1, 1, 'Tenant A')")
    cursor.execute("INSERT INTO loads (id, load_name) VALUES (1, 'LOAD-1')")
    cursor.execute("INSERT INTO meters (id, meter_id) VALUES (1, 'MTR-1')")

    cursor.execute(
        "INSERT INTO unit_tenants_history (unit_id, tenant_id, date_start, is_active) "
        "VALUES (1, 1, '2024-01-01', 1)"
    )
    cursor.execute(
        "INSERT INTO unit_meters_history (unit_id, meter_id, date_start, is_active) "
        "VALUES (1, 1, '2024-01-01', 1)"
    )
    cursor.execute(
        "INSERT INTO unit_loads_history (unit_id, load_id, date_start, is_active) "
        "VALUES (1, 1, '2024-01-01', 1)"
    )

    cursor.execute(
        """
        INSERT INTO meter_records (
            meter_id, tenant_id, session_id, client_record_id,
            timestamp_record, meter_kWh
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            "seed-session",
            "seed-record",
            "2024-10-01T00:00:00+00:00",
            100.0,
        ),
    )

    conn.commit()
    conn.close()

    conn_check = db_schema.get_db_connection()
    meter_ids = MeterLoggingDbQueries._get_meter_ids_for_tenant(tenant_id=1, conn=conn_check)
    conn_check.close()
    assert 1 in meter_ids, f"Seed data did not assign meter to tenant; found {meter_ids}"


def fetch_meter_records(meter_id: int) -> List[Tuple[float, str]]:
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT meter_kWh, timestamp_record FROM meter_records WHERE meter_id = ? ORDER BY created_at",
        (meter_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [(row["meter_kWh"], row["timestamp_record"]) for row in rows]


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    test_db_path = tmp_path / "settings.db"
    monkeypatch.setattr(db_schema, "DB_PATH", test_db_path)
    init_database()
    seed_meter_logging_data()
    seeded = MeterLoggingDbQueries.list_tenants_for_client(client_id=1)
    assert seeded, "Seeding failed to create tenant entries"
    with TestClient(app) as client:
        yield client


def test_list_tenants(api_client):
    response = api_client.get("/meters/v1/tenants", params={"client_id": 1})
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["tenants"]) == 1
    tenant = payload["tenants"][0]
    assert tenant["tenant_id"] == 1
    assert tenant["tenant_name"] == "Tenant A"
    assert tenant["building"]["floor"] == 18
    assert tenant["active_units"] == 1
    assert tenant["last_record_at"] == "2024-10-01T00:00:00+00:00"


def test_meter_assignments(api_client):
    response = api_client.get("/meters/v1/tenants/1/meters")
    assert response.status_code == 200

    payload = response.json()
    assert payload["tenant_id"] == 1
    assert len(payload["meters"]) == 1
    meter = payload["meters"][0]
    assert meter["meter_id"] == "MTR-1"
    assert meter["meter_pk"] == 1
    assert meter["unit"]["floor"] == 18
    assert meter["loads"] == [1]
    assert meter["last_record"]["meter_kWh"] == 100.0


def test_submit_meter_records_flow(api_client):
    session_id = "session-123"
    later_time = datetime.now(timezone.utc).isoformat()

    assert 1 in MeterLoggingDbQueries._get_meter_ids_for_tenant(
        tenant_id=1,
        conn=db_schema.get_db_connection(),
    )

    response = api_client.post(
        "/meters/v1/records",
        json={
            "tenant_id": 1,
            "session_id": session_id,
            "records": [
                {
                    "client_record_id": "rec-001",
                    "meter_id": "MTR-1",
                    "timestamp_record": later_time,
                    "meter_kWh": 150.5,
                }
            ],
        },
    )
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["accepted"][0]["status"] == "accepted"
    assert payload["warnings"] == []

    records = fetch_meter_records(1)
    assert len(records) == 2
    assert records[-1][0] == pytest.approx(150.5)

    duplicate = api_client.post(
        "/meters/v1/records",
        json={
            "tenant_id": 1,
            "session_id": session_id,
            "records": [
                {
                    "client_record_id": "rec-001",
                    "meter_id": "MTR-1",
                    "timestamp_record": later_time,
                    "meter_kWh": 150.5,
                }
            ],
        },
    )
    assert duplicate.status_code == 200, duplicate.json()
    dup_payload = duplicate.json()
    assert dup_payload["accepted"][0]["status"] == "duplicate"

    earlier_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    decreasing = api_client.post(
        "/meters/v1/records",
        json={
            "tenant_id": 1,
            "session_id": session_id,
            "records": [
                {
                    "client_record_id": "rec-002",
                    "meter_id": "MTR-1",
                    "timestamp_record": earlier_time,
                    "meter_kWh": 120.0,
                }
            ],
        },
    )
    assert decreasing.status_code == 200, decreasing.json()
    warn_payload = decreasing.json()
    assert warn_payload["accepted"] == []
    assert warn_payload["warnings"][0]["type"] == "decreasing_reading"


def test_attach_approval_and_history(api_client):
    now_iso = datetime.now(timezone.utc).isoformat()

    api_client.post(
        "/meters/v1/records",
        json={
            "tenant_id": 1,
            "session_id": "session-approval",
            "records": [
                {
                    "client_record_id": "rec-approval",
                    "meter_id": "MTR-1",
                    "timestamp_record": now_iso,
                    "meter_kWh": 180.0,
                }
            ],
        },
    )

    approval = api_client.post(
        "/meters/v1/approvals",
        json={
            "tenant_id": 1,
            "session_id": "session-approval",
            "approver": {"name": "Approver One", "signature_blob": "data:image/png;base64,AAA"},
        },
    )
    assert approval.status_code == 200
    assert approval.json() == {"updated": 1}

    history = api_client.get(
        "/meters/v1/meter-records",
        params={"tenant_id": 1, "limit": 5},
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert len(history_payload["records"]) >= 2

    latest = history_payload["records"][0]
    assert latest["approver_name"] == "Approver One"
    assert latest["approver_signature"] == "data:image/png;base64,AAA"
    assert latest["meter_id"] == "MTR-1"
    assert latest["meter_pk"] == 1


def test_meta_endpoint(api_client):
    response = api_client.get("/meters/v1/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v1"
    assert payload["non_decreasing_enforced"] is True
    assert "server_time" in payload

