# Meter Logging API Specification (v0.1)

This document defines the REST endpoints that power the V1 manual meter logging workflow. It aims to satisfy the requirements captured in `website/docs/IMPLEMENTATION_QUESTIONS.md` while keeping the API cohesive with the existing backend.

---

## 1. Scope and Principles

- **Audience:** encoder-facing mobile-web workflow (super_admin has read access).
- **Data sources:** `units`, `unit_meters_history`, `meters`, `meter_records`, `unit_tenants_history`, `tenants`, `users`.
- **Auth:** same session/JWT mechanism as existing API. Encoders must be assigned via `user_client_assignments` (and optionally `user_client_building_assignments` if we implement finer scoping). Super admins bypass tenant filtering.
- **Versioning:** prefixed under `/meters/v1/*` to allow independent evolution.
- **Mobile-first:** minimizes round trips and surfaces everything needed for offline queueing.

---

## 2. Domain Objects

| Object | Source Table(s) | Key Fields |
| ------ | ---------------- | ---------- |
| `TenantSummary` | `tenants`, `unit_tenants_history`, `units` | `tenant_id`, `tenant_name`, `building_id`, `building_name`, `floor` (new column), `active_unit_count` |
| `MeterAssignment` | `unit_meters_history`, `meters`, `unit_loads_history` | `meter_id`, `meter_ref`, `unit_id`, `load_ids[]`, `last_record` |
| `MeterRecord` | `meter_records` | `meter_record_id`, `meter_id`, `timestamp_record`, `meter_kW`, `encoder_user_id`, `approver_name`, `approver_signature_blob (optional)`, `created_at` |
| `BulkSession` (client-side construct) | n/a | `session_id`, array of `MeterRecordInput`, `approver_signature` |

---

## 3. Endpoints

All endpoints live under `/meters/v1`. Unless stated otherwise, responses are JSON and require an authenticated session.

### 3.1 List Tenants for Encoder

```
GET /meters/v1/tenants?client_id={id}&building_id={optional}
```

Returns tenants the encoder can act on. Response includes building metadata and floor to support the “search tenant by building + floor” workflow.

**Response**
```json
{
  "tenants": [
    {
      "tenant_id": 123,
      "tenant_name": "NEO Suites",
      "client_id": 42,
      "building": {
        "id": 7,
        "name": "NEO 3",
        "floor": 18
      },
      "active_units": 3,
      "last_record_at": "2024-10-05T06:30:00Z"
    }
  ]
}
```

Filtering rules:
- Encoders see tenants within their assigned client/building scope.
- Super admins can pass `client_id` or omit for all.

### 3.2 Fetch Meter Assignments for a Tenant

```
GET /meters/v1/tenants/{tenant_id}/meters
```

Returns active meters linked to the tenant’s units. Includes last reading for context.

**Response**
```json
{
  "tenant_id": 123,
  "meters": [
    {
      "meter_id": 555,
      "meter_ref": "MTR-NEO3-1801",
      "unit": {
        "id": 901,
        "unit_number": "1801",
        "floor": 18
      },
      "loads": [321, 322],
      "last_record": {
        "timestamp_record": "2024-10-05T06:30:00Z",
        "meter_kW": 345.7
      }
    }
  ]
}
```

### 3.3 Submit Meter Readings (Bulk-Friendly)

```
POST /meters/v1/records
Content-Type: application/json
```

Accepts one or multiple readings grouped by tenant/session. Designed for online and offline replay (idempotency via client-provided UUID).

**Request**
```json
{
  "tenant_id": 123,
  "session_id": "c05f1f2b-3115-4b4d-b10d-af2f5e5e9aad",
  "records": [
    {
      "client_record_id": "rec-001",
      "meter_id": 555,
      "timestamp_record": "2024-10-06T08:15:00+08:00",
      "meter_kW": 356.2
    }
  ]
}
```

**Response**
```json
{
  "tenant_id": 123,
  "session_id": "c05f1f2b-3115-4b4d-b10d-af2f5e5e9aad",
  "accepted": [
    {
      "client_record_id": "rec-001",
      "meter_record_id": 9012,
      "status": "accepted"
    }
  ],
  "warnings": [
    {
      "client_record_id": "rec-001",
      "type": "decreasing_reading",
      "message": "New reading (356.2) is below previous value (360.0)."
    }
  ]
}
```

Notes:
- Server enforces non-decreasing rule (hard block per requirements).
- For offline mode, timestamps are taken from device payload; server records ingestion time separately.
- If a `client_record_id` reappears, the existing record is returned (idempotent).

### 3.4 Attach Approver Signature (Optional V1 Flow)

```
POST /meters/v1/approvals
```

Stores the approver’s signature metadata for audit. For V1 where approval happens on the encoder’s device, payload is lightweight.

**Request**
```json
{
  "session_id": "c05f1f2b-3115-4b4d-b10d-af2f5e5e9aad",
  "tenant_id": 123,
  "approver": {
    "name": "Juan Dela Cruz",
    "signature_blob": "data:image/png;base64,iVBORw0..."
  }
}
```

Back-end associates the signature with all records posted in the same `session_id` (within a short window).

### 3.5 Retrieve Meter Records (History View)

```
GET /meters/v1/meter-records?meter_id=555&limit=20
GET /meters/v1/meter-records?tenant_id=123&from=2024-09-01&to=2024-10-01
```

Supports charting and quick verification. Encoders see records they created; admins see any.

**Response**
```json
{
  "records": [
    {
      "meter_record_id": 9012,
      "meter_id": 555,
      "tenant_id": 123,
      "timestamp_record": "2024-10-06T08:15:00+08:00",
      "meter_kW": 356.2,
      "encoder_user_id": 77,
      "approver_name": "Juan Dela Cruz",
      "created_at": "2024-10-06T00:15:03Z"
    }
  ]
}
```

### 3.6 Health/Metadata

```
GET /meters/v1/meta
```

Returns enums, validation thresholds (e.g., `max_reading_delta`), and system timestamp for offline sync alignment.

---

## 4. Validation & Business Rules

- **Non-decreasing readings:** reject (HTTP 409) with a descriptive error and include previous reading value.
- **Time bounds:** reject records older than the previous submission by configurable grace period (default 90 days) unless `override=true` and user is super_admin.
- **Session replays:** server stores `session_id` + `client_record_id` to guarantee idempotency for offline resends.
- **Signature capture:** optional in V1; stored alongside meter records, but actual enforcement can be toggled per client.

---

## 5. Error Codes

| HTTP | Code | Description |
| ---- | ---- | ----------- |
| 400 | `invalid_payload` | Missing/invalid fields, malformed timestamps |
| 401 | `unauthorized` | No valid session/token |
| 403 | `forbidden` | Tenant/meter outside encoder scope |
| 404 | `not_found` | Tenant or meter not found/active |
| 409 | `reading_conflict` | Decreasing reading or record already exists |
| 422 | `validation_failed` | Domain rule violation (e.g., record too old) |

---

## 6. Logging & Monitoring

- All write operations log via `ReportLogger` to `db_manager.log` (per project convention).
- Include `session_id` and `client_record_id` in logs to cross-reference encoder issues.
- Emit metrics counters (future work) for success/failure per endpoint.

---

## 7. Open Questions / Future Enhancements

- Approval workflow expansion (separate tenant_approver login/OTP).
- Notifications/WebSockets for real-time dashboards (currently out of scope).
- Soft deletion / correction flow for erroneous readings (post-MVP).
- Offline conflict resolution UI/UX guidelines.

---

**Last updated:** 2025-11-07

