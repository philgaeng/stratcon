#!/usr/bin/env python3
"""
Update user 6's email to philippe@stratcon.ph

This script updates the email address for user 6 (Philippe Gaeng, super_admin)
from the old email to philippe@stratcon.ph
"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from backend.services.data.db_manager.db_schema import get_db_connection

def update_user6_email():
    """Update user 6's email to philippe@stratcon.ph"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, check if user 6 exists and what their current email is
        cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE id = 6")
        user = cursor.fetchone()
        
        if not user:
            print("❌ User 6 not found in database")
            return
        
        current_email = user['email']
        print(f"📧 Current email for user 6 ({user['first_name']} {user['last_name']}): {current_email}")
        
        # Check if email is already correct
        if current_email == 'philippe@stratcon.ph':
            print("✅ User 6 email is already set to philippe@stratcon.ph")
            return
        
        # Check if philippe@stratcon.ph already exists for another user
        cursor.execute("SELECT id, first_name, last_name FROM users WHERE email = ?", ('philippe@stratcon.ph',))
        existing = cursor.fetchone()
        if existing:
            if existing['id'] == 6:
                print("✅ User 6 email is already set to philippe@stratcon.ph")
                return
            else:
                print(f"⚠️  Warning: philippe@stratcon.ph is already used by user {existing['id']} ({existing['first_name']} {existing['last_name']})")
                response = input("Do you want to continue? This will update user 6's email anyway. (yes/no): ")
                if response.lower() != 'yes':
                    print("❌ Update cancelled")
                    return
        
        # Update user 6's email
        print(f"\n🔄 Updating user 6 email from {current_email} to philippe@stratcon.ph...")
        cursor.execute("""
            UPDATE users
            SET email = 'philippe@stratcon.ph'
            WHERE id = 6
        """)
        
        if cursor.rowcount > 0:
            conn.commit()
            print("✅ Successfully updated user 6 email to philippe@stratcon.ph")
            
            # Verify update
            cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE id = 6")
            updated_user = cursor.fetchone()
            print(f"   Verified: User {updated_user['id']} - {updated_user['email']} ({updated_user['first_name']} {updated_user['last_name']})")
        else:
            print("⚠️  No rows updated")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating user 6 email: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_user6_email()

