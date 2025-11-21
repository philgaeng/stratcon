#!/usr/bin/env python3
"""
Create user: Richard Deborja
- Email: richard.deborja@neooffice.ph
- Company: NEO Office
- Entity ID: 3
- Role: super_admin (via entity_user_assignments)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.data.db_manager.db_schema import get_db_connection

def create_user_richard_deborja():
    """Create user Richard Deborja with entity assignment."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        email = "richard.deborja@neooffice.ph"
        first_name = "Richard"
        last_name = "deborja"
        company = "NEO Office"
        entity_id = 3
        role = "super_admin"
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            user_id = existing_user['id']
            print(f"⚠️  User already exists with ID: {user_id}")
            print(f"   Updating user information...")
            
            # Update user
            cursor.execute("""
                UPDATE users 
                SET first_name = ?, last_name = ?, company = ?, entity_id = ?, user_group = ?
                WHERE id = ?
            """, (first_name, last_name, company, entity_id, role, user_id))
            print(f"   ✅ Updated user {user_id}")
        else:
            # Create new user
            print(f"👤 Creating user: {first_name} {last_name}")
            cursor.execute("""
                INSERT INTO users (
                    email, first_name, last_name, company, 
                    user_group, entity_id, active, receive_reports_email
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email,
                first_name,
                last_name,
                company,
                role,  # user_group
                entity_id,
                1,  # active
                1   # receive_reports_email
            ))
            user_id = cursor.lastrowid
            print(f"   ✅ Created user with ID: {user_id}")
        
        # Check if entity assignment already exists
        cursor.execute("""
            SELECT id FROM entity_user_assignments 
            WHERE user_id = ? AND entity_id = ?
        """, (user_id, entity_id))
        existing_assignment = cursor.fetchone()
        
        if existing_assignment:
            # Update existing assignment
            cursor.execute("""
                UPDATE entity_user_assignments 
                SET role = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND entity_id = ?
            """, (role, user_id, entity_id))
            print(f"   ✅ Updated entity assignment (role: {role})")
        else:
            # Create entity assignment
            cursor.execute("""
                INSERT INTO entity_user_assignments (
                    entity_id, user_id, role
                )
                VALUES (?, ?, ?)
            """, (entity_id, user_id, role))
            print(f"   ✅ Created entity assignment (entity_id: {entity_id}, role: {role})")
        
        conn.commit()
        
        # Verify the user was created correctly
        cursor.execute("""
            SELECT u.id, u.email, u.first_name, u.last_name, u.company, 
                   u.user_group, u.entity_id,
                   eua.role as assignment_role
            FROM users u
            LEFT JOIN entity_user_assignments eua ON u.id = eua.user_id AND eua.entity_id = ?
            WHERE u.id = ?
        """, (entity_id, user_id))
        
        row = cursor.fetchone()
        if row:
            print(f"\n✅ User created successfully!")
            print(f"   ID: {row['id']}")
            print(f"   Email: {row['email']}")
            print(f"   Name: {row['first_name']} {row['last_name']}")
            print(f"   Company: {row['company']}")
            print(f"   User Group: {row['user_group']}")
            print(f"   Entity ID: {row['entity_id']}")
            print(f"   Entity Assignment Role: {row['assignment_role']}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    create_user_richard_deborja()

