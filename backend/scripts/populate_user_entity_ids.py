#!/usr/bin/env python3
"""
Standalone script to populate user entity_id column.
Matches users.company to EPC entity names.
"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.data.db_manager.db_schema import populate_user_entity_ids


if __name__ == "__main__":
    print("👤 Populating user entity_id column...")
    print("=" * 50)
    populate_user_entity_ids()
    print("=" * 50)
    print("✅ User entity_id population complete!")

