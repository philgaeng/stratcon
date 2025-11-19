#!/usr/bin/env python3
"""
Migration script to update user_group from 'encoder' to 'client_encoder'.

This script:
1. Updates the CHECK constraint on the users table to replace 'encoder' with 'client_encoder'
2. Updates all user records with user_group='encoder' to 'client_encoder'

SQLite doesn't support modifying CHECK constraints directly, so we:
- Create a new table with the correct constraint
- Copy data (updating encoder to client_encoder during copy)
- Drop old table
- Rename new table
"""
import sys
from pathlib import Path
import sqlite3
import os

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Use DATABASE_PATH environment variable if set, otherwise use default location
_DEFAULT_DB_PATH = BACKEND_DIR / "data" / "settings.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(_DEFAULT_DB_PATH)))

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_encoder_to_client_encoder():
    """Migrate user_group from 'encoder' to 'client_encoder'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_group = ?", ("encoder",))
        encoder_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_group = ?", ("client_encoder",))
        client_encoder_count = cursor.fetchone()["count"]
        
        print(f"Current state:")
        print(f"  - Users with 'encoder': {encoder_count}")
        print(f"  - Users with 'client_encoder': {client_encoder_count}")
        
        if encoder_count == 0:
            print("\n✅ No users with 'encoder' found. Migration not needed.")
            return
        
        print(f"\n📋 Users to be migrated:")
        cursor.execute("SELECT id, email, first_name, last_name, user_group FROM users WHERE user_group = ?", ("encoder",))
        for row in cursor.fetchall():
            print(f"  - ID {row['id']}: {row['email']} ({row['first_name']} {row['last_name']})")
        
        # Get all columns from users table
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Create new table with updated CHECK constraint
        print("\n🔄 Creating new users table with updated constraint...")
        cursor.execute("""
            CREATE TABLE users_new (
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
                    'client_encoder', 'tenant_approver'
                )),
                receive_reports_email BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE SET NULL
            )
        """)
        
        # Copy data, replacing 'encoder' with 'client_encoder'
        print("📋 Copying data and updating user_group values...")
        column_list = ", ".join(column_names)
        placeholders = ", ".join(["?" for _ in column_names])
        
        # Build SELECT with CASE to replace 'encoder' with 'client_encoder'
        select_cols = []
        for col in column_names:
            if col == "user_group":
                select_cols.append("CASE WHEN user_group = 'encoder' THEN 'client_encoder' ELSE user_group END")
            else:
                select_cols.append(col)
        
        select_query = f"SELECT {', '.join(select_cols)} FROM users"
        insert_query = f"INSERT INTO users_new ({column_list}) {select_query}"
        
        cursor.execute(insert_query)
        copied_count = cursor.rowcount
        
        print(f"✅ Copied {copied_count} user(s) to new table")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) as count FROM users_new WHERE user_group = ?", ("encoder",))
        remaining_encoder = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM users_new WHERE user_group = ?", ("client_encoder",))
        new_client_encoder_count = cursor.fetchone()["count"]
        
        if remaining_encoder > 0:
            print(f"⚠️ Warning: {remaining_encoder} user(s) still have 'encoder' in new table")
        else:
            print(f"✅ Verification: No users with 'encoder' in new table")
            print(f"✅ Users with 'client_encoder': {new_client_encoder_count}")
        
        # Drop old table and rename new table
        print("\n🔄 Replacing old table with new table...")
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # Recreate indexes if they exist
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        
        conn.commit()
        print("✅ Migration complete!")
        
        # Show final state
        print("\n📊 Final state:")
        cursor.execute("SELECT user_group, COUNT(*) as count FROM users GROUP BY user_group ORDER BY user_group")
        for row in cursor.fetchall():
            print(f"  - {row['user_group']}: {row['count']} user(s)")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Update user_group 'encoder' → 'client_encoder'")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print()
    
    migrate_encoder_to_client_encoder()
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)

