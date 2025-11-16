#!/usr/bin/env python3
"""
Migration script to populate settings database from existing CSV files.
Reads cutoff_day from CSV files and migrates to database.
"""

import sys
from pathlib import Path
from typing import Optional

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd
from services.settings.cutoff import CutoffSettingsManager
from services.core.config import DEFAULT_CLIENT
from services.data.db_manager.db_schema import init_database

# Create cutoff manager instance
_cutoff_manager = CutoffSettingsManager()

# Default path for loads summary CSV (if not provided)
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_LOADS_SUMMARY = PROJECT_ROOT / "downloads" / "NEO" / "loads_summary.csv"

# Backward compatibility functions
def set_client_settings(client_token: str, cutoff_day: int, cutoff_hour: int = 23, cutoff_minute: int = 59, cutoff_second: int = 59, epc_name: Optional[str] = None):
    _cutoff_manager.set_client_cutoff(client_token, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second, epc_name)

def set_tenant_settings(client_token: str, tenant_token: str, cutoff_day: Optional[int] = None, cutoff_hour: Optional[int] = None, cutoff_minute: Optional[int] = None, cutoff_second: Optional[int] = None):
    _cutoff_manager.set_tenant_cutoff(client_token, tenant_token, cutoff_day, cutoff_hour, cutoff_minute, cutoff_second)

def migrate_csv_to_db(csv_path: Optional[Path] = None, client_token: str = DEFAULT_CLIENT):
    """
    Migrate cutoff settings from CSV to database.
    
    Args:
        csv_path: Path to CSV file (defaults to DEFAULT_LOADS_SUMMARY)
        client_token: Client identifier
    """
    csv_path = csv_path or DEFAULT_LOADS_SUMMARY
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    print(f"📖 Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Initialize database
    print("🔧 Initializing database...")
    init_database()
    
    # Group by tenant to find most common cutoff_day per tenant
    # (In CSV, cutoff_day is the same for all loads in a tenant)
    if 'tenant' in df.columns and 'cutoff_day' in df.columns:
        tenant_cutoffs = df.groupby('tenant')['cutoff_day'].first()
        
        print(f"📝 Migrating settings for {len(tenant_cutoffs)} tenants...")
        for tenant_token, cutoff_day in tenant_cutoffs.items():
            if pd.notna(cutoff_day):
                set_tenant_settings(
                    client_token=client_token,
                    tenant_token=str(tenant_token),
                    cutoff_day=int(cutoff_day),
                )
                print(f"  ✅ {client_token}/{tenant_token}: cutoff_day={int(cutoff_day)}")
    elif 'cutoff_day' in df.columns:
        # If no tenant column, set all to same cutoff_day (assuming all same client)
        cutoff_day = df['cutoff_day'].iloc[0]
        if pd.notna(cutoff_day):
            set_client_settings(
                client_token=client_token,
                cutoff_day=int(cutoff_day),
            )
            print(f"  ✅ {client_token}: cutoff_day={int(cutoff_day)} (client-wide)")
    
    print("✅ Migration complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate CSV cutoff settings to database")
    parser.add_argument("--csv", type=Path, help="Path to CSV file")
    parser.add_argument("--client", type=str, default=DEFAULT_CLIENT, help="Client token")
    args = parser.parse_args()
    
    migrate_csv_to_db(args.csv, args.client)

