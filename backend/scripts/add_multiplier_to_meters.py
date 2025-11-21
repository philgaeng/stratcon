#!/usr/bin/env python3
"""
Add multiplier column to meters table.
- Default value: 1
- Set 80 for meter IDs: 51, 52
- Set 120 for meter ID: 61
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.data.db_manager.db_schema import get_db_connection


def add_multiplier_column():
    """Add multiplier column to meters table and update specific meters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(meters)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'multiplier' in columns:
            print("⚠️  Column 'multiplier' already exists in meters table")
        else:
            # Add multiplier column with default value 1
            print("📝 Adding 'multiplier' column to meters table...")
            cursor.execute("""
                ALTER TABLE meters 
                ADD COLUMN multiplier REAL DEFAULT 1
            """)
            print("   ✅ Column added successfully")
        
        # Update specific meter IDs
        updates = [
            (80, 51),
            (80, 52),
            (120, 61),
        ]
        
        print("\n📝 Updating specific meter multipliers...")
        for multiplier, meter_id in updates:
            cursor.execute("""
                UPDATE meters 
                SET multiplier = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (multiplier, meter_id))
            
            # Verify update
            cursor.execute("SELECT id, meter_ref, multiplier FROM meters WHERE id = ?", (meter_id,))
            row = cursor.fetchone()
            if row:
                print(f"   ✅ Meter ID {meter_id} ({row['meter_ref']}): multiplier = {row['multiplier']}")
            else:
                print(f"   ⚠️  Meter ID {meter_id} not found")
        
        conn.commit()
        
        # Show summary
        print("\n📊 Summary:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_meters,
                COUNT(CASE WHEN multiplier = 1 THEN 1 END) as default_multiplier,
                COUNT(CASE WHEN multiplier != 1 THEN 1 END) as custom_multiplier
            FROM meters
        """)
        summary = cursor.fetchone()
        print(f"   Total meters: {summary['total_meters']}")
        print(f"   With default multiplier (1): {summary['default_multiplier']}")
        print(f"   With custom multiplier: {summary['custom_multiplier']}")
        
        # Show meters with custom multipliers
        cursor.execute("""
            SELECT id, meter_ref, multiplier 
            FROM meters 
            WHERE multiplier != 1
            ORDER BY id
        """)
        custom_meters = cursor.fetchall()
        if custom_meters:
            print("\n🔢 Meters with custom multipliers:")
            for meter in custom_meters:
                print(f"   ID {meter['id']}: {meter['meter_ref']} = {meter['multiplier']}")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    add_multiplier_column()

