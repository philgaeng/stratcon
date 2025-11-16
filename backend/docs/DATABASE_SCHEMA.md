# Database Schema Documentation

## Overview

The Stratcon database uses SQLite to manage Electricity Producing Companies (EPCs), clients (building managers), tenants, buildings, units, loads (digital meters), meters (manual meters), meter_records (manual meter readings), users, and contacts. This document describes the complete schema structure, relationships, and usage patterns.

**Database Location**: `backend/data/settings.db`

## Schema Hierarchy

```
EPCs (Electricity Producing Companies)
  └── Clients (Building Managers)
       └── Buildings
            └── Units
                 ├── Tenants (via unit_tenants_history)
                 ├── Loads (via unit_loads_history) → Consumptions
                 └── Meters (via unit_meters_history) → Meter Records
```

## Tables

### 1. epcs

Electricity Producing Companies (e.g., Aboitiz, Stratcon)

| Column          | Type                 | Description               |
| --------------- | -------------------- | ------------------------- |
| id              | INTEGER PRIMARY KEY  | Unique identifier         |
| name            | TEXT NOT NULL UNIQUE | EPC name                  |
| billing_address | TEXT                 | Billing address           |
| cutoff_day      | INTEGER              | Default cutoff day (1-31) |
| cutoff_hour     | INTEGER DEFAULT 23   | Default cutoff hour       |
| cutoff_minute   | INTEGER DEFAULT 59   | Default cutoff minute     |
| cutoff_second   | INTEGER DEFAULT 59   | Default cutoff second     |
| is_active       | BOOLEAN DEFAULT 1    | Active status             |
| created_at      | TIMESTAMP            | Creation timestamp        |
| updated_at      | TIMESTAMP            | Last update timestamp     |

**Notes**:

- Stratcon is created as an EPC by default
- Cutoff settings cascade down to clients (if not overridden)

### 2. clients

Building Managers (clients of EPCs)

| Column          | Type                | Description                               |
| --------------- | ------------------- | ----------------------------------------- |
| id              | INTEGER PRIMARY KEY | Unique identifier                         |
| epc_id          | INTEGER NOT NULL    | Foreign key to epcs                       |
| name            | TEXT NOT NULL       | Client name (unique per EPC)              |
| billing_address | TEXT                | Billing address                           |
| cutoff_day      | INTEGER             | Cutoff day (overrides EPC default if set) |
| cutoff_hour     | INTEGER DEFAULT 23  | Cutoff hour                               |
| cutoff_minute   | INTEGER DEFAULT 59  | Cutoff minute                             |
| cutoff_second   | INTEGER DEFAULT 59  | Cutoff second                             |
| is_active       | BOOLEAN DEFAULT 1   | Active status                             |
| created_at      | TIMESTAMP           | Creation timestamp                        |
| updated_at      | TIMESTAMP           | Last update timestamp                     |

**Constraints**: `UNIQUE(epc_id, name)` - Client name must be unique within an EPC

### 3. buildings

Buildings managed by clients

| Column        | Type                | Description                            |
| ------------- | ------------------- | -------------------------------------- |
| id            | INTEGER PRIMARY KEY | Unique identifier                      |
| client_id     | INTEGER NOT NULL    | Foreign key to clients                 |
| name          | TEXT NOT NULL       | Building name                          |
| address       | TEXT                | Building address                       |
| cutoff_day    | INTEGER             | Default cutoff day for the building    |
| cutoff_hour   | INTEGER DEFAULT 23  | Default cutoff hour for the building   |
| cutoff_minute | INTEGER DEFAULT 59  | Default cutoff minute for the building |
| cutoff_second | INTEGER DEFAULT 59  | Default cutoff second for the building |
| is_active     | BOOLEAN DEFAULT 1   | Active status                          |
| created_at    | TIMESTAMP           | Creation timestamp                     |
| updated_at    | TIMESTAMP           | Last update timestamp                  |

### 4. units

Units (offices/spaces) within buildings

| Column        | Type                | Description                                 |
| ------------- | ------------------- | ------------------------------------------- |
| id            | INTEGER PRIMARY KEY | Unique identifier                           |
| building_id   | INTEGER NOT NULL    | Foreign key to buildings                    |
| unit_number   | TEXT                | Unit identifier (e.g., "201", "Unit A")     |
| floor         | INTEGER             | Floor number within the building (optional) |
| unit_type     | TEXT                | Type (e.g., "Office", "Retail")             |
| square_meters | REAL                | Floor area in square meters                 |
| created_at    | TIMESTAMP           | Creation timestamp                          |
| updated_at    | TIMESTAMP           | Last update timestamp                       |

### 5. tenants

Tenants (clients of building managers)

| Column        | Type                | Description            |
| ------------- | ------------------- | ---------------------- |
| id            | INTEGER PRIMARY KEY | Unique identifier      |
| client_id     | INTEGER NOT NULL    | Foreign key to clients |
| name          | TEXT NOT NULL       | Tenant name            |
| contact_email | TEXT                | Tenant contact email   |
| contact_name  | TEXT                | Tenant contact person  |
| created_at    | TIMESTAMP           | Creation timestamp     |
| updated_at    | TIMESTAMP           | Last update timestamp  |

### 6. loads

Electrical loads (digital meters/MCBs)

| Column      | Type                 | Description                         |
| ----------- | -------------------- | ----------------------------------- |
| id          | INTEGER PRIMARY KEY  | Unique identifier                   |
| load_name   | TEXT NOT NULL UNIQUE | Load name (e.g., "MCB - 2002 [kW]") |
| description | TEXT                 | Load description                    |
| created_at  | TIMESTAMP            | Creation timestamp                  |
| updated_at  | TIMESTAMP            | Last update timestamp               |

**Notes**:

- Used for digital meters that provide automated readings
- `load_name` must be unique across all digital meters

### 7. meters

Manual meters (non-digital meters that require manual reading)

| Column      | Type                 | Description                       |
| ----------- | -------------------- | --------------------------------- |
| id          | INTEGER PRIMARY KEY  | Unique identifier                 |
| meter_ref   | TEXT NOT NULL UNIQUE | Meter reference number/identifier |
| description | TEXT                 | Meter description                 |
| created_at  | TIMESTAMP            | Creation timestamp                |
| updated_at  | TIMESTAMP            | Last update timestamp             |

**Notes**:

- Used for tracking manual meters (as opposed to digital meters in `loads` table)
- `meter_ref` must be unique across all manual meters
- Manual meters require periodic manual reading and data entry

### 8. unit_tenants_history

History of tenant occupancy in units (tracks when tenants move in/out)

| Column     | Type                | Description                                       |
| ---------- | ------------------- | ------------------------------------------------- |
| id         | INTEGER PRIMARY KEY | Unique identifier                                 |
| unit_id    | INTEGER NOT NULL    | Foreign key to units                              |
| tenant_id  | INTEGER NOT NULL    | Foreign key to tenants                            |
| date_start | DATE NOT NULL       | Start date of occupancy                           |
| date_end   | DATE                | End date (NULL = currently active)                |
| is_active  | BOOLEAN DEFAULT 1   | Active status (automatically updated via trigger) |
| created_at | TIMESTAMP           | Creation timestamp                                |
| updated_at | TIMESTAMP           | Last update timestamp                             |

**Logic**: When `date_end IS NULL`, `is_active = 1` (current tenant)

### 9. unit_loads_history

History of digital load assignments to units (tracks when digital meters are assigned/moved)

| Column     | Type                | Description                                       |
| ---------- | ------------------- | ------------------------------------------------- |
| id         | INTEGER PRIMARY KEY | Unique identifier                                 |
| unit_id    | INTEGER NOT NULL    | Foreign key to units                              |
| load_id    | INTEGER NOT NULL    | Foreign key to loads (digital meters)             |
| date_start | DATE NOT NULL       | Start date of assignment                          |
| date_end   | DATE                | End date (NULL = currently active)                |
| is_active  | BOOLEAN DEFAULT 1   | Active status (automatically updated via trigger) |
| created_at | TIMESTAMP           | Creation timestamp                                |
| updated_at | TIMESTAMP           | Last update timestamp                             |

**Logic**: When `date_end IS NULL`, `is_active = 1` (current assignment)

**Notes**:

- Tracks digital meter (load) assignments to units
- For manual meter assignments, see `unit_meters_history`

### 10. unit_meters_history

History of manual meter assignments to units (tracks when manual meters are assigned/moved)

| Column     | Type                | Description                                       |
| ---------- | ------------------- | ------------------------------------------------- |
| id         | INTEGER PRIMARY KEY | Unique identifier                                 |
| unit_id    | INTEGER NOT NULL    | Foreign key to units                              |
| meter_id   | INTEGER NOT NULL    | Foreign key to meters (manual meters)             |
| date_start | DATE NOT NULL       | Start date of assignment                          |
| date_end   | DATE                | End date (NULL = currently active)                |
| is_active  | BOOLEAN DEFAULT 1   | Active status (automatically updated via trigger) |
| created_at | TIMESTAMP           | Creation timestamp                                |
| updated_at | TIMESTAMP           | Last update timestamp                             |

**Logic**: When `date_end IS NULL`, `is_active = 1` (current assignment)

**Notes**:

- Tracks manual meter assignments to units
- Separated from `unit_loads_history` to maintain clear distinction between digital and manual meters
- A unit can have both digital loads and manual meters assigned simultaneously

### 11. contacts

Generic contacts table (linked to EPCs, clients, or users)

| Column       | Type                | Description                                      |
| ------------ | ------------------- | ------------------------------------------------ |
| id           | INTEGER PRIMARY KEY | Unique identifier                                |
| last_name    | TEXT                | Last name                                        |
| first_name   | TEXT                | First name                                       |
| nick_name    | TEXT                | Nickname                                         |
| mobile_phone | TEXT                | Mobile phone number                              |
| email        | TEXT NOT NULL       | Email address                                    |
| landline     | TEXT                | Landline phone                                   |
| user_id      | INTEGER             | Foreign key to users (if contact is also a user) |
| created_at   | TIMESTAMP           | Creation timestamp                               |
| updated_at   | TIMESTAMP           | Last update timestamp                            |

**Notes**:

- Same person can be contact for multiple entities
- `user_id` links to system user if contact has login access
- Contact info is shared; role-specific fields are in junction tables

### 12. epc_contact_assignments

Junction table linking contacts to EPCs with role-specific information

| Column                | Type                | Description                   |
| --------------------- | ------------------- | ----------------------------- |
| id                    | INTEGER PRIMARY KEY | Unique identifier             |
| contact_id            | INTEGER NOT NULL    | Foreign key to contacts       |
| epc_id                | INTEGER NOT NULL    | Foreign key to epcs           |
| position              | TEXT                | Job position/title            |
| main_contact          | BOOLEAN DEFAULT 0   | Is this the main contact?     |
| receive_reports_email | BOOLEAN DEFAULT 1   | Should receive report emails? |
| created_at            | TIMESTAMP           | Creation timestamp            |
| updated_at            | TIMESTAMP           | Last update timestamp         |

### 13. client_contact_assignments

Junction table linking contacts to clients with role-specific information

| Column                | Type                | Description                   |
| --------------------- | ------------------- | ----------------------------- |
| id                    | INTEGER PRIMARY KEY | Unique identifier             |
| contact_id            | INTEGER NOT NULL    | Foreign key to contacts       |
| client_id             | INTEGER NOT NULL    | Foreign key to clients        |
| position              | TEXT                | Job position/title            |
| main_contact          | BOOLEAN DEFAULT 0   | Is this the main contact?     |
| receive_reports_email | BOOLEAN DEFAULT 1   | Should receive report emails? |
| created_at            | TIMESTAMP           | Creation timestamp            |
| updated_at            | TIMESTAMP           | Last update timestamp         |

### 14. meter_records

Manual meter readings (records of manual meter readings entered by users)

| Column             | Type                | Description                                  |
| ------------------ | ------------------- | -------------------------------------------- |
| id                 | INTEGER PRIMARY KEY | Unique identifier                            |
| meter_id           | INTEGER NOT NULL    | Foreign key to meters (manual meters)        |
| tenant_id          | INTEGER NOT NULL    | Foreign key to tenants                       |
| session_id         | TEXT                | Client-provided bulk session identifier      |
| client_record_id   | TEXT                | Client-generated record identifier           |
| timestamp_record   | TIMESTAMP NOT NULL  | Timestamp when the reading was taken         |
| meter_kW           | REAL NOT NULL       | Power reading in kilowatts                   |
| encoder_user_id    | INTEGER             | Foreign key to users (encoder)               |
| approver_name      | TEXT                | Name captured from tenant approver signature |
| approver_signature | TEXT                | Base64 signature blob (optional)             |
| created_at         | TIMESTAMP           | Creation timestamp                           |

**Notes**:

- Stores manual meter readings entered by encoders
- Supports offline batching via `session_id` + `client_record_id` (idempotent pair)
- `timestamp_record` indicates when the reading was taken (not when it was entered)
- `encoder_user_id` links the record to the user who captured it; approver fields store signature metadata
- Foreign key constraints ensure references to meters, tenants, and users remain valid

### 15. users

System users (can log into the application)

| Column                | Type                 | Description                              |
| --------------------- | -------------------- | ---------------------------------------- |
| id                    | INTEGER PRIMARY KEY  | Unique identifier                        |
| email                 | TEXT NOT NULL UNIQUE | Email (used for login)                   |
| company               | TEXT                 | Company name                             |
| last_name             | TEXT NOT NULL        | Last name                                |
| first_name            | TEXT NOT NULL        | First name                               |
| position              | TEXT                 | Job position                             |
| mobile_phone          | TEXT                 | Mobile phone                             |
| landline              | TEXT                 | Landline phone                           |
| active                | BOOLEAN DEFAULT 1    | Active status                            |
| user_group            | TEXT NOT NULL        | Permission level (see User Groups below) |
| receive_reports_email | BOOLEAN DEFAULT 0    | Should receive report emails?            |
| created_at            | TIMESTAMP            | Creation timestamp                       |
| updated_at            | TIMESTAMP            | Last update timestamp                    |

**User Groups** (permissions):

- `super_admin`: Full system access (modify all settings, create users, see all clients)
- `client_admin`: Manage assigned clients (modify cutoff for assigned clients, create users for assigned clients)
- `client_manager`: View and manage assigned clients (modify cutoff, cannot create users)
- `viewer`: Read-only access to assigned clients
- `tenant_user`: Access to specific tenant(s) only

### 16. user_client_assignments

Junction table assigning users to clients with history

| Column         | Type                | Description                          |
| -------------- | ------------------- | ------------------------------------ |
| id             | INTEGER PRIMARY KEY | Unique identifier                    |
| user_id        | INTEGER NOT NULL    | Foreign key to users                 |
| client_id      | INTEGER NOT NULL    | Foreign key to clients               |
| assigned_at    | TIMESTAMP           | Assignment start date                |
| assigned_until | TIMESTAMP           | Assignment end date (NULL = current) |
| created_at     | TIMESTAMP           | Creation timestamp                   |
| updated_at     | TIMESTAMP           | Last update timestamp                |

**Constraints**: `UNIQUE(user_id, client_id, assigned_at)` - Prevents duplicate assignments

## Relationships Summary

```
EPCs (1) ──< (many) Clients
EPCs (1) ──< (many) epc_contact_assignments ──> (many) Contacts
Clients (1) ──< (many) Buildings
Clients (1) ──< (many) client_contact_assignments ──> (many) Contacts
Clients (1) ──< (many) Tenants
Clients (1) ──< (many) user_client_assignments ──> (many) Users
Buildings (1) ──< (many) Units
Units (many) ──< unit_tenants_history ──> (many) Tenants
Units (many) ──< unit_loads_history ──> (many) Loads ──> (many) Consumptions
Units (many) ──< unit_meters_history ──> (many) Meters ──> (many) Meter Records
Contacts (many) ──> (1) Users (via user_id, nullable)
```

## Schema Maintenance Workflow

- Run `python -m backend.services.db_manager.db_schema` (or call `init_database()`) to create missing tables/indexes on a fresh database.
- For additive changes (for example, adding `units.floor`), prefer the safe rebuild utility:
  - `conda run -n datascience python -m backend.services.db_manager.recreate_table <table_name>`
  - The script renames the existing table, runs the latest schema, migrates shared columns, and drops the temporary copy. Data is preserved when columns match.
  - Use `--force-drop` only when you want to discard existing rows.
- Always back up `backend/data/settings.db` (e.g., `cp ... settings.db.bak`) before running destructive operations or bulk migrations.

## Cutoff Settings Hierarchy

Cutoff settings cascade down with the following priority (most specific wins):

1. **User-provided cutoff** (from frontend) - Highest priority
2. **Unit-level cutoff** (if set in units table)
3. **Client-level cutoff** (if set in clients table)
4. **EPC-level cutoff** (default in epcs table)
5. **System default** (26, 23:59:59) - Lowest priority

**Note**: Tenant-level cutoff fields exist but are not currently used in frontend.

## Email Recipient Logic

When generating reports, emails are sent to:

1. **Client contacts** where `receive_reports_email = true` in `client_contact_assignments`
2. **EPC contacts** where `receive_reports_email = true` in `epc_contact_assignments` (if client doesn't have contacts)
3. **Users** where `receive_reports_email = true` (optional, for system notifications)

## History Tables Logic

Both `unit_tenants_history` and `unit_loads_history` track relationships over time:

- **Current relationship**: `date_end IS NULL` and `is_active = 1`
- **Past relationship**: `date_end IS NOT NULL` and `is_active = 0`
- **Triggers**: Automatically update `is_active` when `date_end` changes

This allows:

- Querying current tenant for a unit
- Querying historical occupancy
- Querying current loads for a unit
- Maintaining audit trail

## Indexes

Performance indexes are created on:

- `contacts(user_id, email)`
- `clients(epc_id)`
- `buildings(client_id)`
- `units(building_id)`
- `tenants(client_id)`
- All junction tables (`contact_id`, `client_id`, `epc_id`, etc.)
- History tables (`unit_id`, `tenant_id`, `load_id`, `meter_id`, `is_active`)
- Data tables (`timestamp`, `timestamp_record`, `meter_id`, `load_id`)

## Initialization

The database is initialized with:

1. **Stratcon EPC** (default EPC for system use)

   - Name: "Stratcon"
   - Cutoff: Day 26, 23:59:59

2. **Default Admin User**
   - Email: admin@stratcon.ph
   - User Group: super_admin
   - Also created as a contact and linked to Stratcon EPC

## Usage Examples

### Get Cutoff Settings for a Load

```python
# Priority: Unit → Client → EPC → Default
# Query unit, then client, then EPC to find cutoff settings
```

### Get Email Recipients for a Client

```sql
-- Get client contacts
SELECT c.email
FROM contacts c
JOIN client_contact_assignments cca ON c.id = cca.contact_id
WHERE cca.client_id = ? AND cca.receive_reports_email = 1

UNION

-- Get EPC contacts if no client contacts
SELECT c.email
FROM contacts c
JOIN epc_contact_assignments eca ON c.id = eca.contact_id
JOIN clients cl ON eca.epc_id = cl.epc_id
WHERE cl.id = ? AND eca.receive_reports_email = 1
```

### Get Current Tenant for a Unit

```sql
SELECT t.*
FROM tenants t
JOIN unit_tenants_history uth ON t.id = uth.tenant_id
WHERE uth.unit_id = ? AND uth.is_active = 1
```

## Migration Notes

When migrating from CSV files:

- Use `backend/scripts/migrate_csv_to_db.py` to import cutoff_day settings
- Map CSV tenant names to database tenant records
- Map CSV load names to database loads records
- Create unit_tenants_history and unit_loads_history records for current assignments

## Future Enhancements

- Add authentication fields to users (if not using Amplify)
- Add tenant-user assignments table (if tenants need direct system access)
- Add audit logging table for tracking changes
- Add settings/preferences tables for UI customization
