#!/usr/bin/env python3
"""Extract and compile electricity consumption data from CSV files directly to database.

This script replaces the old CSV-based compilation process. It reads compiled CSV files
from backend/data/ (e.g., NEO_NEO3_0708_all_data.csv), transforms them to long format,
and directly inserts the data into the consumptions table.

Usage examples:
    python3 data_extract_and_compile_to_db.py --tenant NEO3_0708
    python3 data_extract_and_compile_to_db.py --client NEO
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple, Iterable, List
from datetime import datetime

import pandas as pd
import sqlite3

# Add backend to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.services.data.db_manager.db_schema import get_db_connection, init_database
from backend.services.settings.legacy import _find_or_create_client, _find_or_create_load

PROJECT_ROOT = BACKEND_DIR.parent
DOWNLOADS_ROOT = PROJECT_ROOT / "downloads"
DB_PATH = BACKEND_DIR / "data" / "settings.db"


def resolve_floor_folder(folder_token: str) -> Path:
    """Resolve the target floor folder inside downloads/."""
    candidate = DOWNLOADS_ROOT / folder_token
    if candidate.is_dir():
        return candidate

    matches: List[Path] = [p for p in DOWNLOADS_ROOT.rglob(folder_token) if p.is_dir()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(
            f"Could not find folder '{folder_token}' inside {DOWNLOADS_ROOT}."
        )
    # Ambiguous
    raise FileNotFoundError(
        f"Multiple folders named '{folder_token}' found. Please provide a more specific path."
    )


def parse_folder_path(folder_path: Path) -> Tuple[str, str, str]:
    """
    Parse client, building, and unit from folder path.
    
    Expected folder structure: downloads/{CLIENT}/{BUILDING}_{UNIT}/
    Example: downloads/NEO/NEO3_0708/ -> ("NEO", "NEO3", "0708")
    
    Returns:
        Tuple of (client_name, building_name, unit_number)
    """
    # Get relative path from DOWNLOADS_ROOT
    relative = folder_path.relative_to(DOWNLOADS_ROOT)
    parts = relative.parts
    
    if len(parts) < 2:
        raise ValueError(f"Cannot parse folder path {folder_path}: expected format downloads/CLIENT/BUILDING_UNIT/")
    
    client_name = parts[0]
    folder_name = parts[1]  # e.g., "NEO3_0708" or "NEO3_222324"
    
    # Split folder name into building and unit
    folder_parts = folder_name.split('_')
    if len(folder_parts) < 2:
        raise ValueError(f"Cannot parse folder name {folder_name}: expected format BUILDING_UNIT")
    
    building_name = folder_parts[0]  # e.g., "NEO3"
    unit_number = "_".join(folder_parts[1:])  # e.g., "0708" or "222324" (handles multi-part units)
    
    return client_name, building_name, unit_number


def standardize_load_name(load_column: str) -> str:
    """
    Standardize load column name.
    
    Example: "MCB 802 [kW]" -> "MCB_802"
    """
    # Remove [kW] suffix
    name = load_column.replace(" [kW]", "").replace("[kW]", "")
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    return name


def read_csv(path: Path) -> pd.DataFrame:
    """Read CSV file with European decimal format."""
    return pd.read_csv(
        path,
        delimiter=',',
        decimal=',',
        thousands='.',
        parse_dates=['Date']
    )


def transform_to_long_format(df: pd.DataFrame, client_name: str, building_name: str) -> pd.DataFrame:
    """
    Transform wide-format DataFrame to long format.
    
    Drops "Consumption [kW]" column and melts load columns.
    Standardizes load names and adds full context.
    
    Returns DataFrame with columns: timestamp, load_name_full, load_name_std, load_kW
    """
    # Drop Consumption [kW] column if it exists
    if "Consumption [kW]" in df.columns:
        df = df.drop(columns=["Consumption [kW]"])
    
    # Identify load columns (those ending with [kW])
    load_columns = [col for col in df.columns if "[kW]" in col]
    
    if not load_columns:
        raise ValueError("No load columns found in CSV file")
    
    # Melt the DataFrame
    df_long = df.melt(
        id_vars=['Date'],
        value_vars=load_columns,
        var_name='load_name_original',
        value_name='load_kW'
    )
    
    # Standardize load names
    df_long['load_name_std'] = df_long['load_name_original'].apply(standardize_load_name)
    
    # Create full load name with client and building context
    df_long['load_name_full'] = f"{client_name}_{building_name}_" + df_long['load_name_std']
    
    # Rename Date to timestamp
    df_long = df_long.rename(columns={'Date': 'timestamp'})
    
    # Convert load_kW to float (handle comma decimals)
    df_long['load_kW'] = df_long['load_kW'].astype(str).str.replace(',', '.').astype(float)
    
    # Sort by timestamp
    df_long = df_long.sort_values(by="timestamp")
    
    return df_long


def find_or_create_building(client_id: int, building_name: str, conn: sqlite3.Connection) -> int:
    """Find or create a building. Returns building ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM buildings WHERE client_id = ? AND name = ?", (client_id, building_name))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    cursor.execute("INSERT INTO buildings (client_id, name) VALUES (?, ?)", (client_id, building_name))
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def find_or_create_unit(building_id: int, unit_number: str, conn: sqlite3.Connection) -> int:
    """Find or create a unit. Returns unit ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM units WHERE building_id = ? AND unit_number = ?", (building_id, unit_number))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    cursor.execute("INSERT INTO units (building_id, unit_number) VALUES (?, ?)", (building_id, unit_number))
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def ensure_load_unit_link(unit_id: int, load_id: int, conn: sqlite3.Connection) -> None:
    """
    Ensure an active link exists in load_unit_history between unit and load.
    
    If no active link exists, creates one with date_start = earliest consumption date or today.
    """
    cursor = conn.cursor()
    
    # Check if active link exists
    cursor.execute("""
        SELECT id FROM load_unit_history
        WHERE unit_id = ? AND load_id = ? AND is_active = 1
    """, (unit_id, load_id))
    
    if cursor.fetchone():
        return  # Active link already exists
    
    # Find earliest consumption date for this load/unit combination
    cursor.execute("""
        SELECT MIN(timestamp) FROM consumptions
        WHERE load_id = ?
    """, (load_id,))
    
    row = cursor.fetchone()
    if row and row[0]:
        date_start = datetime.fromisoformat(row[0]).date().isoformat()
    else:
        date_start = datetime.now().date().isoformat()
    
    # Create new active link
    cursor.execute("""
        INSERT INTO load_unit_history (load_id, unit_id, date_start, is_active)
        VALUES (?, ?, ?, 1)
    """, (load_id, unit_id, date_start))


def is_file_compiled(client_name: str, building_name: str, file_path: Path, conn: sqlite3.Connection) -> bool:
    """Check if a file has already been compiled."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM files_compiled
        WHERE client_name = ? AND building_name = ? AND file_path = ?
    """, (client_name, building_name, str(file_path)))
    return cursor.fetchone() is not None


def record_file_compiled(client_name: str, building_name: str, file_path: Path, conn: sqlite3.Connection) -> None:
    """Record that a file has been compiled."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files_compiled (client_name, building_name, file_path)
        VALUES (?, ?, ?)
    """, (client_name, building_name, str(file_path)))


def compile_floor_to_db(folder_token: str, conn: sqlite3.Connection) -> None:
    """
    Compile data from CSV files in a tenant folder to the database.
    
    Args:
        folder_token: Token like "NEO3_0708" or "NEO/NEO3_0708"
        conn: Database connection
    """
    # Resolve the folder path in downloads/
    folder_path = resolve_floor_folder(folder_token)
    
    # Parse client, building, unit from folder path
    client_name, building_name, unit_number = parse_folder_path(folder_path)
    print(f"\n=== Processing {client_name}/{building_name}_{unit_number} ===")
    print(f"   Folder: {folder_path.relative_to(DOWNLOADS_ROOT)}")
    
    # Find all CSV files in the folder
    csv_files = sorted(folder_path.glob("*.csv"))
    
    if not csv_files:
        print(f"   ⚠️  No CSV files found in {folder_path}")
        return
    
    print(f"   📁 Found {len(csv_files)} CSV file(s)")
    
    # Get or create client, building, unit once for all files
    client_id = _find_or_create_client(client_name, conn=conn)
    building_id = find_or_create_building(client_id, building_name, conn)
    unit_id = find_or_create_unit(building_id, unit_number, conn)
    
    total_insert_count = 0
    
    # Process each CSV file
    for csv_file in csv_files:
        print(f"\n   📄 Processing: {csv_file.name}")
        
        # Check if file already compiled
        if is_file_compiled(client_name, building_name, csv_file, conn):
            print(f"      ⏭️  File already compiled, skipping")
            continue
        
        # Read and transform CSV
        print(f"      📖 Reading CSV...")
        df = read_csv(csv_file)
        print(f"      ✅ Read {len(df)} rows")
        
        print(f"      🔄 Transforming to long format...")
        df_long = transform_to_long_format(df, client_name, building_name)
        print(f"      ✅ Transformed to {len(df_long)} rows")
        
        # Process each unique load
        unique_loads = df_long[['load_name_full', 'load_name_std']].drop_duplicates()
        
        print(f"      🔌 Processing {len(unique_loads)} unique loads...")
        cursor = conn.cursor()
        
        insert_count = 0
        for _, row in unique_loads.iterrows():
            load_name_full = row['load_name_full']
            load_name_std = str(row['load_name_std'])
            
            # Find or create load (use standardized name)
            load_id = _find_or_create_load(load_name_std, conn)
            
            # Ensure load-unit link exists
            ensure_load_unit_link(unit_id, load_id, conn)
            
            # Get data for this load
            load_data = df_long[df_long['load_name_full'] == load_name_full].copy()
            
            # Insert consumptions (with duplicate check)
            for _, cons_row in load_data.iterrows():
                # Convert pandas timestamp to string format for SQLite
                timestamp = cons_row['timestamp']
                if isinstance(timestamp, pd.timestamp):
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(timestamp, datetime):
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp_str = str(timestamp)
                
                # Check if this consumption record already exists
                # (Database also enforces uniqueness via unique index on (timestamp, load_id))
                cursor.execute("""
                    SELECT id FROM consumptions
                    WHERE timestamp = ? AND load_id = ?
                """, (timestamp_str, load_id))
                
                if cursor.fetchone():
                    # Skip duplicate - record already exists
                    continue
                
                # Use INSERT OR IGNORE as safety net in case of race conditions
                # (unique constraint will prevent duplicates at database level)
                try:
                    cursor.execute("""
                        INSERT INTO consumptions (timestamp, load_id, load_name, load_kW)
                        VALUES (?, ?, ?, ?)
                    """, (
                        timestamp_str,
                        load_id,
                        load_name_std,
                        cons_row['load_kW']
                    ))
                except sqlite3.IntegrityError:
                    # Unique constraint violation - skip this record
                    continue
                insert_count += 1
        
        # Record file as compiled
        record_file_compiled(client_name, building_name, csv_file, conn)
        
        # Commit after each file
        conn.commit()
        
        print(f"      ✅ Inserted {insert_count} consumption records")
        print(f"      ✅ File marked as compiled")
        total_insert_count += insert_count
    
    print(f"\n   ✅ Completed {client_name}/{building_name}_{unit_number}: {total_insert_count} total records inserted")


def compile_client_to_db(client_token: str) -> None:
    """
    Compile all tenant folders for a given client.
    
    Looks for tenant folders in downloads/{CLIENT}/ and processes all CSV files in each.
    """
    client_dir = DOWNLOADS_ROOT / client_token
    if not client_dir.is_dir():
        raise FileNotFoundError(f"Client folder '{client_token}' not found under {DOWNLOADS_ROOT}")

    subfolders = sorted([p for p in client_dir.iterdir() if p.is_dir()])
    if not subfolders:
        print(f"❌ No tenant folders found under {client_dir}")
        return

    conn = get_db_connection()
    
    try:
        print(f"\n=== Compiling data for client: {client_token} ===")
        print(f"Found {len(subfolders)} tenant folder(s)")
        
        for folder in subfolders:
            folder_token = f"{client_token}/{folder.name}"
            compile_floor_to_db(folder_token, conn)
        
        print(f"\n✅ Completed compilation for client: {client_token}")
        
    finally:
        conn.close()


def main(argv: Optional[Iterable[str]] = None) -> None:
    """Main entry point."""
    # Initialize database
    init_database()
    
    parser = argparse.ArgumentParser(
        description="Extract and compile electricity consumption data from CSV files to database"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tenant",
        help="Tenant/unit token (e.g., NEO3_0708) or CSV filename (e.g., NEO_NEO3_0708_all_data.csv)"
    )
    group.add_argument(
        "--client",
        help="Client token (e.g., NEO) to compile all files for that client"
    )
    
    args = parser.parse_args(list(argv) if argv else None)
    
    try:
        if args.client:
            compile_client_to_db(args.client)
        else:
            conn = get_db_connection()
            try:
                compile_floor_to_db(args.tenant, conn)
            finally:
                conn.close()
    except Exception as exc:
        print(f"❌ Compilation failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
