#!/usr/bin/env python3
"""
Populate database with initial EPC, client, building, tenant, and user data.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.data.db_manager.db_schema import get_db_connection, init_database, create_default_stratcon_epc, populate_entities
import sqlite3


def populate_database():
    """Populate database with initial data."""
    print("🗄️  Initializing database...")
    init_database()
    create_default_stratcon_epc()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ==================== EPCS ====================
        print("\n📦 Creating EPCs...")
        
        # Stratcon EPC (should already exist, but update if needed)
        cursor.execute("SELECT id FROM epcs WHERE name = 'Stratcon'")
        stratcon_epc_row = cursor.fetchone()
        if stratcon_epc_row:
            stratcon_epc_id = stratcon_epc_row['id']
            cursor.execute("""
                UPDATE epcs 
                SET billing_address = '22-4F Madison Galeries, Don Jesus Blvd., Cupang, Muntinlupa City'
                WHERE id = ?
            """, (stratcon_epc_id,))
            print("  ✅ Updated Stratcon EPC")
        else:
            cursor.execute("""
                INSERT INTO epcs (name, billing_address, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
                VALUES ('Stratcon', '22-4F Madison Galeries, Don Jesus Blvd., Cupang, Muntinlupa City', 26, 23, 59, 59)
            """)
            stratcon_epc_id = cursor.lastrowid
            print("  ✅ Created Stratcon EPC")
        
        # Aboitiz Power EPC
        cursor.execute("SELECT id FROM epcs WHERE name = 'Aboitiz Power'")
        aboitiz_row = cursor.fetchone()
        if aboitiz_row:
            aboitiz_epc_id = aboitiz_row['id']
            print("  ✅ Aboitiz Power EPC already exists")
        else:
            cursor.execute("""
                INSERT INTO epcs (name, billing_address, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
                VALUES ('Aboitiz Power', '10F, NAC Tower, 32nd St, Taguig, 1229 Metro Manila', 26, 23, 59, 59)
            """)
            aboitiz_epc_id = cursor.lastrowid
            print("  ✅ Created Aboitiz Power EPC")
        
        # ==================== USERS ====================
        print("\n👤 Creating users...")
        
        users_data = [
            ('colin.steley@stratcon.asia', 'Colin', 'Steley', '+639499958633', None, 'client_admin', 'Stratcon'),
            ('jovs.carcido@stratcon.asia', 'Jovs', 'Carcido', None, None, 'client_admin', 'Stratcon'),
            ('sam.suppiah@stratcon.ph', 'Sam', 'Suppiah', None, None, 'client_admin', 'Stratcon'),
            ('mark.nania@stratcon.ph', 'Mark', 'Nania', None, None, 'client_admin', 'Stratcon'),
            ('philippe@stratcon.ph', 'Philippe', 'Gaeng', '+639175330841', None, 'super_admin', 'Stratcon'),
            ('jherald.casipit@aboitizpower.com', 'Jherald', 'Casipit', None, None, 'client_manager', 'Aboitiz Power'),
            ('antonette.torres@aboitizpower.com', 'Mary Antonette', 'Torres', None, None, 'client_manager', 'Aboitiz Power'),
        ]
        
        user_ids = {}
        for email, first_name, last_name, mobile, landline, user_group, company in users_data:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            existing = cursor.fetchone()
            if existing:
                user_id = existing['id']
                print(f"  ✅ User already exists: {email}")
            else:
                cursor.execute("""
                    INSERT INTO users (email, first_name, last_name, mobile_phone, landline, user_group, company, active, receive_reports_email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)
                """, (email, first_name, last_name, mobile, landline, user_group, company))
                user_id = cursor.lastrowid
                print(f"  ✅ Created user: {email} ({user_group})")
            user_ids[email] = user_id
        
        # ==================== CONTACTS ====================
        print("\n📇 Creating contacts...")
        
        contacts_data = [
            ('Colin', 'Steley', None, '+639499958633', 'colin.steley@stratcon.asia', None, 'colin.steley@stratcon.asia'),
            ('Jovs', 'Carcido', None, None, 'jovs.carcido@stratcon.asia', None, 'jovs.carcido@stratcon.asia'),
            ('Sam', 'Suppiah', None, None, 'sam.suppiah@stratcon.ph', None, 'sam.suppiah@stratcon.ph'),
            ('Mark', 'Nania', None, None, 'mark.nania@stratcon.ph', None, 'mark.nania@stratcon.ph'),
            ('Philippe', 'Gaeng', None, '+639175330841', 'philippe@stratcon.ph', None, 'philippe@stratcon.ph'),
            ('Jherald', 'Casipit', None, None, 'jherald.casipit@aboitizpower.com', None, 'jherald.casipit@aboitizpower.com'),
            ('Mary Antonette', 'Torres', None, None, 'antonette.torres@aboitizpower.com', None, 'antonette.torres@aboitizpower.com'),
            ('Richard', 'De Borja', None, None, 'richard.deborja@neooffice.ph', None, None),  # NEO contact, not a user
        ]
        
        contact_ids = {}
        for first_name, last_name, nick_name, mobile, email, landline, user_email in contacts_data:
            user_id = user_ids.get(user_email) if user_email else None
            
            cursor.execute("SELECT id FROM contacts WHERE email = ?", (email,))
            existing = cursor.fetchone()
            if existing:
                contact_id = existing['id']
                print(f"  ✅ Contact already exists: {email}")
            else:
                cursor.execute("""
                    INSERT INTO contacts (first_name, last_name, nick_name, mobile_phone, email, landline, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (first_name, last_name, nick_name, mobile, email, landline, user_id))
                contact_id = cursor.lastrowid
                print(f"  ✅ Created contact: {email}")
            contact_ids[email] = contact_id
        
        # ==================== EPC CONTACT ASSIGNMENTS ====================
        print("\n🔗 Assigning contacts to EPCs...")
        
        # Stratcon contacts
        stratcon_contacts = [
            ('colin.steley@stratcon.asia', 'General Manager', True, True),
            ('jovs.carcido@stratcon.asia', None, False, True),
            ('sam.suppiah@stratcon.ph', None, False, True),
            ('mark.nania@stratcon.ph', None, False, True),
            ('philippe@stratcon.ph', 'System Administrator', True, True),
        ]
        
        for email, position, main_contact, receive_reports in stratcon_contacts:
            contact_id = contact_ids[email]
            cursor.execute("""
                SELECT id FROM epc_contact_assignments 
                WHERE contact_id = ? AND epc_id = ?
            """, (contact_id, stratcon_epc_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO epc_contact_assignments (contact_id, epc_id, position, main_contact, receive_reports_email)
                    VALUES (?, ?, ?, ?, ?)
                """, (contact_id, stratcon_epc_id, position, main_contact, receive_reports))
                print(f"  ✅ Assigned {email} to Stratcon EPC")
        
        # Aboitiz Power contacts
        aboitiz_contacts = [
            ('jherald.casipit@aboitizpower.com', None, False, True),
            ('antonette.torres@aboitizpower.com', None, False, True),
        ]
        
        for email, position, main_contact, receive_reports in aboitiz_contacts:
            contact_id = contact_ids[email]
            cursor.execute("""
                SELECT id FROM epc_contact_assignments 
                WHERE contact_id = ? AND epc_id = ?
            """, (contact_id, aboitiz_epc_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO epc_contact_assignments (contact_id, epc_id, position, main_contact, receive_reports_email)
                    VALUES (?, ?, ?, ?, ?)
                """, (contact_id, aboitiz_epc_id, position, main_contact, receive_reports))
                print(f"  ✅ Assigned {email} to Aboitiz Power EPC")
        
        # ==================== CLIENTS ====================
        print("\n🏢 Creating clients...")
        
        # NEO client (under Stratcon EPC)
        cursor.execute("SELECT id FROM clients WHERE epc_id = ? AND name = 'NEO'", (stratcon_epc_id,))
        neo_client_row = cursor.fetchone()
        if neo_client_row:
            neo_client_id = neo_client_row['id']
            cursor.execute("""
                UPDATE clients 
                SET billing_address = 'NEO3, 30th St, Taguig, Metro Manila'
                WHERE id = ?
            """, (neo_client_id,))
            print("  ✅ Updated NEO client")
        else:
            cursor.execute("""
                INSERT INTO clients (epc_id, name, billing_address, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
                VALUES (?, 'NEO', 'NEO3, 30th St, Taguig, Metro Manila', 26, 23, 59, 59)
            """, (stratcon_epc_id,))
            neo_client_id = cursor.lastrowid
            print("  ✅ Created NEO client")
        
        # ==================== CLIENT CONTACT ASSIGNMENTS ====================
        print("\n🔗 Assigning contacts to clients...")
        
        # Richard De Borja to NEO
        richard_contact_id = contact_ids['richard.deborja@neooffice.ph']
        cursor.execute("""
            SELECT id FROM client_contact_assignments 
            WHERE contact_id = ? AND client_id = ?
        """, (richard_contact_id, neo_client_id))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO client_contact_assignments (contact_id, client_id, position, main_contact, receive_reports_email)
                VALUES (?, ?, 'Contact Person', 1, 1)
            """, (richard_contact_id, neo_client_id))
            print("  ✅ Assigned Richard De Borja to NEO client")
        
        # ==================== BUILDINGS ====================
        print("\n🏗️  Creating buildings...")
        
        buildings_data = [
            (neo_client_id, 'Neo3', 'NEO3, 30th St, Taguig, Metro Manila'),
            (neo_client_id, 'Neo5', 'Five/NEO, 31st Street, Zamora Circle, Bonifacio Global City, Taguig City, Metro Manila'),
        ]
        
        building_ids = {}
        for client_id, name, address in buildings_data:
            cursor.execute("SELECT id FROM buildings WHERE client_id = ? AND name = ?", (client_id, name))
            existing = cursor.fetchone()
            if existing:
                building_id = existing['id']
                print(f"  ✅ Building already exists: {name}")
            else:
                cursor.execute("""
                    INSERT INTO buildings (client_id, name, address)
                    VALUES (?, ?, ?)
                """, (client_id, name, address))
                building_id = cursor.lastrowid
                print(f"  ✅ Created building: {name}")
            building_ids[name] = building_id
        
        # ==================== TENANTS ====================
        print("\n🏠 Creating tenants...")
        
        # Get tenant folder names from NEO directory
        neo_dir = PROJECT_ROOT / "downloads" / "NEO"
        tenant_folders = sorted([d.name for d in neo_dir.iterdir() if d.is_dir()])
        
        for tenant_folder in tenant_folders:
            # Extract a friendly name from folder name (e.g., NEO3_0708 -> "Floors 07-08")
            if tenant_folder.startswith('NEO3_'):
                floor_nums = tenant_folder.replace('NEO3_', '')
                if len(floor_nums) == 4:  # e.g., "0708"
                    floor_name = f"Floor {floor_nums[:2]}-{floor_nums[2:]}"
                elif len(floor_nums) == 6:  # e.g., "222324"
                    floor_name = f"Floor {floor_nums[:2]}-{floor_nums[2:4]}-{floor_nums[4:]}"
                else:
                    floor_name = f"Tenant {tenant_folder}"
                tenant_name = f"{floor_name} (NEO3)"
            else:
                tenant_name = f"Tenant {tenant_folder}"
            
            cursor.execute("SELECT id FROM tenants WHERE client_id = ? AND name = ?", (neo_client_id, tenant_name))
            existing = cursor.fetchone()
            if existing:
                tenant_id = existing['id']
                print(f"  ✅ Tenant already exists: {tenant_name}")
            else:
                cursor.execute("""
                    INSERT INTO tenants (client_id, name, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)
                    VALUES (?, ?, 26, 23, 59, 59)
                """, (neo_client_id, tenant_name))
                tenant_id = cursor.lastrowid
                print(f"  ✅ Created tenant: {tenant_name}")
        
        # ==================== USER CLIENT ASSIGNMENTS ====================
        print("\n👥 Assigning users to clients...")
        
        # All Stratcon users can access NEO (for now)
        stratcon_user_emails = [
            'colin.steley@stratcon.asia',
            'jovs.carcido@stratcon.asia',
            'sam.suppiah@stratcon.ph',
            'mark.nania@stratcon.ph',
            'philippe@stratcon.ph',
        ]
        
        for email in stratcon_user_emails:
            user_id = user_ids[email]
            cursor.execute("""
                SELECT id FROM user_client_assignments 
                WHERE user_id = ? AND client_id = ?
            """, (user_id, neo_client_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO user_client_assignments (user_id, client_id)
                    VALUES (?, ?)
                """, (user_id, neo_client_id))
                print(f"  ✅ Assigned {email} to NEO client")
        
        conn.commit()
        # ==================== ENTITIES ====================
        print("\n🏷️  Populating entities table...")
        populate_entities()
        
        print("\n✅ Database population complete!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error populating database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    populate_database()
