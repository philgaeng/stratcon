#!/usr/bin/env python3
"""
Database schema definitions and initialization.
"""

import os
import sqlite3
from pathlib import Path

DB_MANAGER_DIR = Path(__file__).resolve().parent
SERVICES_DIR = DB_MANAGER_DIR.parent
BACKEND_DIR = SERVICES_DIR.parent.parent  # Go up two levels: services -> backend

# Use DATABASE_PATH environment variable if set, otherwise use default location
_DEFAULT_DB_PATH = BACKEND_DIR / "data" / "settings.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(_DEFAULT_DB_PATH)))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_has_columns(cursor: sqlite3.Cursor, table_name: str, columns: set[str]) -> bool:
    """
    Return True if the given table contains all requested column names.
    
    Args:
        cursor: Active SQLite cursor.
        table_name: Table to inspect.
        columns: Set of column names that must be present.
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    return columns.issubset(existing_columns)


def init_database() -> None:
    """
    Initialize database tables if they don't exist.
    Uses CREATE TABLE IF NOT EXISTS to avoid errors if tables already exist.
    
    This function creates all tables as defined in DATABASE_SCHEMA.md:
    - Core entities: epcs, clients, buildings, units, tenants, loads
    - People management: users, contacts, contact assignments
    - History tables: unit_tenants_history, unit_loads_history
    - Data tables: consumptions, files_compiled
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ============================================================================
        # Core Entity Tables
        # ============================================================================
        
        # 1. EPCs (Electricity Producing Companies)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS epcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                billing_address TEXT,
                cutoff_day INTEGER,
                cutoff_hour INTEGER DEFAULT 23,
                cutoff_minute INTEGER DEFAULT 59,
                cutoff_second INTEGER DEFAULT 59,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Clients (Building Managers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epc_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                billing_address TEXT,
                cutoff_day INTEGER,
                cutoff_hour INTEGER DEFAULT 23,
                cutoff_minute INTEGER DEFAULT 59,
                cutoff_second INTEGER DEFAULT 59,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (epc_id) REFERENCES epcs(id) ON DELETE CASCADE,
                UNIQUE(epc_id, name)
            )
        """)
        
        # 3. Buildings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buildings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                address TEXT,
                cutoff_day INTEGER,
                cutoff_hour INTEGER DEFAULT 23,
                cutoff_minute INTEGER DEFAULT 59,
                cutoff_second INTEGER DEFAULT 59,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        
        # 4. Units
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                building_id INTEGER NOT NULL,
                unit_number TEXT,
                floor INTEGER,
                unit_type TEXT,
                square_meters REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
            )
        """)
        
        # 5. Tenants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                billing_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        
        # 6. Loads (Digital meters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                load_name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 7. Meters (Manual meters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meter_ref TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ============================================================================
        # People Management Tables
        # ============================================================================
        
        # 8. Users (must be created before contacts since contacts references users)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                company TEXT,
                entity_id INTEGER,
                last_name TEXT NOT NULL,
                first_name TEXT NOT NULL,
                position TEXT,
                mobile_phone TEXT,
                landline TEXT,
                active BOOLEAN DEFAULT 1,
                user_group TEXT NOT NULL CHECK(user_group IN (
                    'super_admin', 'client_admin', 'client_manager', 'viewer', 'tenant_user',
                    'encoder', 'tenant_approver'
                )),
                receive_reports_email BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE SET NULL
            )
        """)
        
        # Add entity_id column if it doesn't exist (for existing databases)
        # Note: SQLite doesn't support adding foreign keys via ALTER TABLE,
        # so we just add the column. The foreign key constraint is only enforced
        # for new tables created with CREATE TABLE.
        if not _table_has_columns(cursor, "users", {"entity_id"}):
            cursor.execute("ALTER TABLE users ADD COLUMN entity_id INTEGER")
        
        # 9. Contacts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_name TEXT,
                first_name TEXT,
                nick_name TEXT,
                mobile_phone TEXT,
                email TEXT NOT NULL,
                landline TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        
        # 10. Client Contact Assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_contact_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                position TEXT,
                main_contact BOOLEAN DEFAULT 0,
                receive_reports_email BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        
        # ============================================================================
        # Entity Assignment Tables
        # ============================================================================
        
        # 11. Entities catalog (generic reference for epcs, clients, tenants, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_ref_id INTEGER NOT NULL,
                epc_id INTEGER,
                client_id INTEGER,
                building_id INTEGER,
                tenant_id INTEGER,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, entity_ref_id),
                FOREIGN KEY (epc_id) REFERENCES epcs(id) ON DELETE CASCADE,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            )
        """)
        
        # 12. Entity → User assignments (many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_user_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(entity_id, user_id, assigned_at)
            )
        """)
        
        # ============================================================================
        # History Tables
        # ============================================================================
        
        # 13. Unit Tenants History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unit_tenants_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id INTEGER NOT NULL,
                tenant_id INTEGER NOT NULL,
                date_start DATE NOT NULL,
                date_end DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            )
        """)
        
        # 13. Unit Loads History (Digital meters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unit_loads_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id INTEGER NOT NULL,
                load_id INTEGER NOT NULL,
                date_start DATE NOT NULL,
                date_end DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
                FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE
            )
        """)
        
        # 14. Unit Meters History (Manual meters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unit_meters_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id INTEGER NOT NULL,
                meter_id INTEGER NOT NULL,
                date_start DATE NOT NULL,
                date_end DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
                FOREIGN KEY (meter_id) REFERENCES meters(id) ON DELETE CASCADE
            )
        """)
        
        # ============================================================================
        # Data Tables
        # ============================================================================
        
        # 15. Consumptions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                load_id INTEGER NOT NULL,
                load_name TEXT NOT NULL,
                load_kW REAL NOT NULL,
                consumption_kWh REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (load_id) REFERENCES loads(id) ON DELETE CASCADE
            )
        """)

        if not _table_has_columns(cursor, "consumptions", {"consumption_kWh"}):
            cursor.execute("ALTER TABLE consumptions ADD COLUMN consumption_kWh REAL")
        
        # 16. Files Compiled
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files_compiled (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                building_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                timestamp_compiled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(client_name, building_name, file_path)
            )
        """)
        
        # 17. Meter Records (Manual meter readings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meter_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meter_id INTEGER NOT NULL,
                timestamp_record TIMESTAMP NOT NULL,
                meter_kWh REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meter_id) REFERENCES meters(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("PRAGMA table_info(meter_records)")
        meter_records_columns = {row[1] for row in cursor.fetchall()}
        if "meter_kWh" not in meter_records_columns:
            if "meter_kW" in meter_records_columns:
                cursor.execute("ALTER TABLE meter_records RENAME COLUMN meter_kW TO meter_kWh")
            else:
                cursor.execute("ALTER TABLE meter_records ADD COLUMN meter_kWh REAL")
        
        # ============================================================================
        # Indexes
        # ============================================================================
        
        # Contacts indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id)")
        
        # Clients indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_epc_id ON clients(epc_id)")
        
        # Buildings indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_buildings_client_id ON buildings(client_id)")
        
        # Units indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_units_building_id ON units(building_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_units_floor ON units(floor)")
        
        # Tenants indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenants_client_id ON tenants(client_id)")
        
        # Junction tables indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_contact_assignments_contact_id ON client_contact_assignments(contact_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_contact_assignments_client_id ON client_contact_assignments(client_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type_ref ON entities(entity_type, entity_ref_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_epc_id ON entities(epc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_client_id ON entities(client_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_building_id ON entities(building_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_tenant_id ON entities(tenant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_user_assignments_entity_id ON entity_user_assignments(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_user_assignments_user_id ON entity_user_assignments(user_id)")
        
        # History tables indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_tenants_history_unit_id ON unit_tenants_history(unit_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_tenants_history_tenant_id ON unit_tenants_history(tenant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_tenants_history_is_active ON unit_tenants_history(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_loads_history_unit_id ON unit_loads_history(unit_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_loads_history_load_id ON unit_loads_history(load_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_loads_history_is_active ON unit_loads_history(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_meters_history_unit_id ON unit_meters_history(unit_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_meters_history_meter_id ON unit_meters_history(meter_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unit_meters_history_is_active ON unit_meters_history(is_active)")
        
        # Consumptions indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumptions_timestamp ON consumptions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumptions_load_id ON consumptions(load_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumptions_load_id_timestamp ON consumptions(load_id, timestamp)")
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_consumptions_unique_timestamp_load_id 
            ON consumptions(timestamp, load_id)
        """)
        
        # Files compiled indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_compiled_client_building ON files_compiled(client_name, building_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_compiled_file_path ON files_compiled(file_path)")
        
        # Meter records indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meter_records_timestamp_record ON meter_records(timestamp_record)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meter_records_meter_id ON meter_records(meter_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meter_records_meter_id_timestamp ON meter_records(meter_id, timestamp_record)")
        
        # ============================================================================
        # Triggers for History Tables
        # ============================================================================
        
        # Trigger to automatically update is_active for unit_tenants_history
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_unit_tenants_history_active
            AFTER UPDATE OF date_end ON unit_tenants_history
            FOR EACH ROW
            BEGIN
                UPDATE unit_tenants_history
                SET is_active = CASE 
                    WHEN date_end IS NULL THEN 1 
                    ELSE 0 
                END
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger to automatically update is_active for unit_loads_history
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_unit_loads_history_active
            AFTER UPDATE OF date_end ON unit_loads_history
            FOR EACH ROW
            BEGIN
                UPDATE unit_loads_history
                SET is_active = CASE 
                    WHEN date_end IS NULL THEN 1 
                    ELSE 0 
                END
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger to automatically update is_active for unit_meters_history
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_unit_meters_history_active
            AFTER UPDATE OF date_end ON unit_meters_history
            FOR EACH ROW
            BEGIN
                UPDATE unit_meters_history
                SET is_active = CASE 
                    WHEN date_end IS NULL THEN 1 
                    ELSE 0 
                END
                WHERE id = NEW.id;
            END
        """)
        
        # ----------------------------------------------------------------------
        # Backfill cutoff columns for legacy databases
        # ----------------------------------------------------------------------
        def ensure_columns(table: str, definitions: dict[str, str]) -> None:
            for column, definition in definitions.items():
                if not _table_has_columns(cursor, table, {column}):
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

        ensure_columns(
            "epcs",
            {
                "cutoff_day": "INTEGER",
                "cutoff_hour": "INTEGER DEFAULT 23",
                "cutoff_minute": "INTEGER DEFAULT 59",
                "cutoff_second": "INTEGER DEFAULT 59",
                "is_active": "BOOLEAN DEFAULT 1",
            },
        )
        ensure_columns(
            "clients",
            {
                "cutoff_day": "INTEGER",
                "cutoff_hour": "INTEGER DEFAULT 23",
                "cutoff_minute": "INTEGER DEFAULT 59",
                "cutoff_second": "INTEGER DEFAULT 59",
                "is_active": "BOOLEAN DEFAULT 1",
            },
        )
        ensure_columns(
            "buildings",
            {
                "cutoff_day": "INTEGER",
                "cutoff_hour": "INTEGER DEFAULT 23",
                "cutoff_minute": "INTEGER DEFAULT 59",
                "cutoff_second": "INTEGER DEFAULT 59",
                "is_active": "BOOLEAN DEFAULT 1",
            },
        )

        # Ensure meter_ref index exists
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_meters_meter_ref ON meters(meter_ref)")

        conn.commit()
        
    finally:
        conn.close()


def create_default_stratcon_epc() -> None:
    """
    Create the default Stratcon EPC if it doesn't exist.
    This is called during database initialization.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM epcs WHERE name = 'Stratcon'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO epcs (name, cutoff_day, cutoff_hour, cutoff_minute)
                VALUES ('Stratcon', 26, 00, 00)
            """)
            conn.commit()
    finally:
        conn.close()


def populate_user_entity_ids() -> None:
    """
    Populate the entity_id column in the users table by matching company names to EPC entities.
    
    Matches users.company to entities.name where entity_type='epc'.
    Uses case-insensitive matching for flexibility.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if entity_id column exists, if not add it
        # Note: SQLite doesn't support adding foreign keys via ALTER TABLE
        if not _table_has_columns(cursor, "users", {"entity_id"}):
            cursor.execute("ALTER TABLE users ADD COLUMN entity_id INTEGER")
            print("  ✅ Added entity_id column to users table")
        
        # Update users with matching EPC entities
        cursor.execute("""
            UPDATE users
            SET entity_id = (
                SELECT e.id
                FROM entities AS e
                WHERE e.entity_type = 'epc'
                  AND LOWER(TRIM(e.name)) = LOWER(TRIM(users.company))
                LIMIT 1
            )
            WHERE company IS NOT NULL
              AND company != ''
              AND entity_id IS NULL
        """)
        updated_count = cursor.rowcount
        
        if updated_count > 0:
            print(f"  ✅ Updated {updated_count} user(s) with entity_id")
        
        # Report summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(entity_id) as users_with_entity_id,
                COUNT(*) - COUNT(entity_id) as users_without_entity_id
            FROM users
            WHERE active = 1
        """)
        stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT u.email, u.company, u.entity_id, e.name as entity_name, e.entity_type
            FROM users AS u
            LEFT JOIN entities AS e ON u.entity_id = e.id
            WHERE u.active = 1
            ORDER BY u.company, u.email
        """)
        user_entities = cursor.fetchall()
        
        conn.commit()
        
        print(f"\n📊 User entity_id summary:")
        print(f"   - Total active users: {stats['total_users']}")
        print(f"   - Users with entity_id: {stats['users_with_entity_id']}")
        print(f"   - Users without entity_id: {stats['users_without_entity_id']}")
        
        if stats['users_without_entity_id'] > 0:
            print(f"\n⚠️  Users without entity_id:")
            for row in user_entities:
                if row['entity_id'] is None:
                    print(f"      - {row['email']} (company: {row['company'] or 'NULL'})")
        
    finally:
        conn.close()


def populate_entities() -> None:
    """
    Populate the entities table with entries for all EPCs, Clients, Buildings, and Tenants.
    
    For each entity type:
    - EPCs: entity_type='epc', entity_ref_id=epc.id, epc_id=epc.id, name=epc.name
    - Clients: entity_type='client', entity_ref_id=client.id, client_id=client.id, 
               epc_id=client.epc_id (from clients table), name=client.name
    - Buildings: entity_type='building', entity_ref_id=building.id, building_id=building.id,
                 client_id=building.client_id, epc_id from clients table (via client_id),
                 name=building.name
    - Tenants: entity_type='tenant', entity_ref_id=tenant.id, tenant_id=tenant.id,
               client_id=tenant.client_id, epc_id from clients table (via client_id),
               name=tenant.name
    
    Uses INSERT OR IGNORE to avoid duplicates (based on UNIQUE(entity_type, entity_ref_id) constraint).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ==================== EPCs ====================
        cursor.execute("""
            INSERT OR IGNORE INTO entities (entity_type, entity_ref_id, epc_id, name)
            SELECT 'epc', id, id, name
            FROM epcs
            WHERE is_active = 1
        """)
        epc_count = cursor.rowcount
        if epc_count > 0:
            print(f"  ✅ Created {epc_count} EPC entity(ies)")
        
        # ==================== Clients ====================
        cursor.execute("""
            INSERT OR IGNORE INTO entities (entity_type, entity_ref_id, epc_id, client_id, name)
            SELECT 'client', id, epc_id, id, name
            FROM clients
            WHERE is_active = 1
        """)
        client_count = cursor.rowcount
        if client_count > 0:
            print(f"  ✅ Created {client_count} client entity(ies)")
        
        # ==================== Buildings ====================
        # For buildings, we need to get epc_id from the clients table
        cursor.execute("""
            INSERT OR IGNORE INTO entities (entity_type, entity_ref_id, epc_id, client_id, building_id, name)
            SELECT 
                'building',
                b.id,
                c.epc_id,
                b.client_id,
                b.id,
                b.name
            FROM buildings AS b
            JOIN clients AS c ON b.client_id = c.id
            WHERE b.is_active = 1
        """)
        building_count = cursor.rowcount
        if building_count > 0:
            print(f"  ✅ Created {building_count} building entity(ies)")
        
        # ==================== Tenants ====================
        # For tenants, we need to get epc_id from the clients table
        cursor.execute("""
            INSERT OR IGNORE INTO entities (entity_type, entity_ref_id, epc_id, client_id, tenant_id, name)
            SELECT 
                'tenant',
                t.id,
                c.epc_id,
                t.client_id,
                t.id,
                t.name
            FROM tenants AS t
            JOIN clients AS c ON t.client_id = c.id
        """)
        tenant_count = cursor.rowcount
        if tenant_count > 0:
            print(f"  ✅ Created {tenant_count} tenant entity(ies)")
        
        conn.commit()
        
        # Report summary
        cursor.execute("SELECT COUNT(*) as count FROM entities WHERE entity_type = 'epc'")
        total_epcs = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM entities WHERE entity_type = 'client'")
        total_clients = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM entities WHERE entity_type = 'building'")
        total_buildings = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM entities WHERE entity_type = 'tenant'")
        total_tenants = cursor.fetchone()['count']
        
        print(f"\n📊 Entities summary:")
        print(f"   - EPCs: {total_epcs}")
        print(f"   - Clients: {total_clients}")
        print(f"   - Buildings: {total_buildings}")
        print(f"   - Tenants: {total_tenants}")
        print(f"   - Total: {total_epcs + total_clients + total_buildings + total_tenants}")
        
    finally:
        conn.close()
