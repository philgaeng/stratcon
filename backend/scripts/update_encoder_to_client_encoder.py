#!/usr/bin/env python3
"""
Update user_group from 'encoder' to 'client_encoder' in the users table.

This script updates all users with user_group='encoder' to user_group='client_encoder'
for consistency with the renamed Cognito group.
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

def update_encoder_to_client_encoder():
    """Update all users with user_group='encoder' to 'client_encoder'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, check how many users have 'encoder' as their user_group
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_group = ?", ("encoder",))
        count_row = cursor.fetchone()
        encoder_count = count_row["count"] if count_row else 0
        
        if encoder_count == 0:
            print("✅ No users found with user_group='encoder'. Nothing to update.")
            return
        
        print(f"Found {encoder_count} user(s) with user_group='encoder'")
        print("\nUsers to be updated:")
        cursor.execute("SELECT id, email, first_name, last_name, user_group FROM users WHERE user_group = ?", ("encoder",))
        for row in cursor.fetchall():
            print(f"  - ID {row['id']}: {row['email']} ({row['first_name']} {row['last_name']})")
        
        # Update all users with 'encoder' to 'client_encoder'
        cursor.execute(
            "UPDATE users SET user_group = ? WHERE user_group = ?",
            ("client_encoder", "encoder")
        )
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"\n✅ Successfully updated {updated_count} user(s) from 'encoder' to 'client_encoder'")
        
        # Verify the update
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_group = ?", ("encoder",))
        remaining_row = cursor.fetchone()
        remaining = remaining_row["count"] if remaining_row else 0
        
        if remaining == 0:
            print("✅ Verification: No users remain with user_group='encoder'")
        else:
            print(f"⚠️ Warning: {remaining} user(s) still have user_group='encoder'")
        
        # Show updated users
        cursor.execute("SELECT id, email, first_name, last_name, user_group FROM users WHERE user_group = ?", ("client_encoder",))
        print(f"\nUsers with user_group='client_encoder':")
        for row in cursor.fetchall():
            print(f"  - ID {row['id']}: {row['email']} ({row['first_name']} {row['last_name']})")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating user groups: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Update user_group: 'encoder' → 'client_encoder'")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print()
    
    update_encoder_to_client_encoder()
    
    print("\n" + "=" * 60)
    print("Update complete!")
    print("=" * 60)

