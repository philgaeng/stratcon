#!/usr/bin/env python3
"""
Update users in the database.

Updates:
- User 6: user_group from 'client_encoder' to 'super_admin', first_name='Philippe', last_name='Gaeng'
- User 9: entity_id from 1 to 3
- Create new user: first_name='Pipo', last_name='Inzaghi', user_group='client_manager', entity_id=3
"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from backend.services.data.db_manager.db_schema import get_db_connection

def update_users():
    """Update users in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update user 6
        print("Updating user 6...")
        cursor.execute("""
            UPDATE users
            SET user_group = 'super_admin',
                first_name = 'Philippe',
                last_name = 'Gaeng'
            WHERE id = 6
        """)
        if cursor.rowcount > 0:
            print(f"  ✅ Updated user 6: user_group='super_admin', first_name='Philippe', last_name='Gaeng'")
        else:
            print("  ⚠️  User 6 not found")
        
        # Update user 9
        print("\nUpdating user 9...")
        cursor.execute("""
            UPDATE users
            SET entity_id = 3
            WHERE id = 9
        """)
        if cursor.rowcount > 0:
            print(f"  ✅ Updated user 9: entity_id=3")
        else:
            print("  ⚠️  User 9 not found")
        
        # Create new user
        print("\nCreating new user...")
        cursor.execute("""
            INSERT INTO users (
                email, first_name, last_name, user_group, entity_id, active
            ) VALUES (
                ?, ?, ?, ?, ?, 1
            )
        """, (
            'pipo.inzaghi@example.com',  # You may want to change this email
            'Pipo',
            'Inzaghi',
            'client_manager',
            3
        ))
        new_user_id = cursor.lastrowid
        print(f"  ✅ Created new user (ID: {new_user_id}): first_name='Pipo', last_name='Inzaghi', user_group='client_manager', entity_id=3")
        
        # Commit changes
        conn.commit()
        print("\n✅ All updates committed successfully!")
        
        # Verify updates
        print("\nVerifying updates...")
        cursor.execute("SELECT id, email, first_name, last_name, user_group, entity_id FROM users WHERE id IN (6, 9, ?)", (new_user_id,))
        rows = cursor.fetchall()
        for row in rows:
            print(f"  User {row['id']}: {row['first_name']} {row['last_name']}, user_group={row['user_group']}, entity_id={row['entity_id']}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_users()

