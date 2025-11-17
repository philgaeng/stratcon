#!/usr/bin/env python3
"""Utility script to rebuild tables using the canonical schema definitions without losing data."""

from __future__ import annotations

import argparse
import re
import sqlite3
from typing import Iterable, Optional

from .db_schema import get_db_connection, init_database


VALID_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_table_name(table_name: str) -> str:
    table_name = table_name.strip()
    if not table_name:
        raise ValueError("table_name must not be empty")
    if not VALID_TABLE_RE.match(table_name):
        raise ValueError(f"Invalid table name '{table_name}'. Letters, numbers, and underscores only.")
    return table_name


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def get_columns(conn: sqlite3.Connection, table_name: str) -> Iterable[str]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def recreate_table(table_name: str, *, force_drop: bool = False) -> None:
    table_name = validate_table_name(table_name)
    temp_table = f"{table_name}__old"

    conn = get_db_connection()

    try:
        if not table_exists(conn, table_name):
            conn.close()
            init_database()
            return

        if force_drop:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            conn.close()
            init_database()
            return

        # Rename existing table to a temporary name so we can recreate and copy data.
        conn.execute(f"ALTER TABLE {table_name} RENAME TO {temp_table}")
        conn.commit()
    finally:
        conn.close()

    # Recreate the canonical schema (including the target table).
    init_database()

    conn = get_db_connection()
    try:
        if not table_exists(conn, table_name):
            raise RuntimeError(f"Failed to recreate table '{table_name}'. Check db_schema definitions.")
        if not table_exists(conn, temp_table):
            # Nothing to migrate (should not happen, but guard anyway).
            return

        old_columns = list(get_columns(conn, temp_table))
        new_columns = list(get_columns(conn, table_name))
        shared_columns = [col for col in old_columns if col in new_columns]

        if shared_columns:
            columns_csv = ", ".join(f'"{col}"' for col in shared_columns)
            conn.execute(
                f"INSERT INTO {table_name} ({columns_csv}) "
                f"SELECT {columns_csv} FROM {temp_table}"
            )
            conn.commit()
        else:
            print(
                f"⚠️ No shared columns between '{temp_table}' and '{table_name}'. "
                "Data was not migrated."
            )

        conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.commit()

    finally:
        conn.close()


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Recreate a table to match the current schema (with best-effort data preservation)."
    )
    parser.add_argument("table", help="Table name to recreate")
    parser.add_argument(
        "--force-drop",
        action="store_true",
        help="Drop the table without attempting to migrate existing data.",
    )
    args = parser.parse_args(argv)

    recreate_table(args.table, force_drop=args.force_drop)
    print(f"✅ Table '{args.table}' recreated successfully.")


if __name__ == "__main__":
    main()

