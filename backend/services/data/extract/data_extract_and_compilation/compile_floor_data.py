#!/usr/bin/env python3
"""Compile electricity CSV dumps into consolidated datasets.

Usage examples:

    python3 compile_floor_data.py --tenant NEO3_0708
    python3 compile_floor_data.py --client NEO
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
SERVICES_DIR = SCRIPT_DIR.parent
BACKEND_DIR = SERVICES_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
DOWNLOADS_ROOT = PROJECT_ROOT / "downloads"
OUTPUT_DIR = BACKEND_DIR / "data"


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


def destination_path(floor_folder: Path) -> Path:
    relative = floor_folder.relative_to(DOWNLOADS_ROOT)
    sanitized = "_".join(relative.parts)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"{sanitized}_all_data.csv"


def read_csv(path: Path, expected_columns: Optional[List[str]] = None) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        delimiter=",",
        decimal=",",
        thousands=".",
        parse_dates=["Date"],
    )
    if expected_columns is not None:
        if list(df.columns) != expected_columns:
            raise ValueError(
                f"Schema mismatch in {path.name}. Expected {expected_columns}, got {list(df.columns)}"
            )
    return df


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Date" not in df.columns:
        raise ValueError("CSV file is missing required 'Date' column")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")
    df = df.set_index("Date")
    df = df[~df.index.duplicated(keep="first")]
    return df


def merge_dataframes(base_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    overlap = new_df.index.intersection(base_df.index)
    if not overlap.empty:
        for ts in overlap:
            base_row = base_df.loc[ts]
            new_row = new_df.loc[ts]
            if not base_row.equals(new_row):
                print(
                    f"⚠️  Duplicate timestamp {ts} has differing values; keeping existing destination data."
                )
        new_df = new_df.drop(overlap)

    combined = pd.concat([base_df, new_df])
    combined = combined.sort_index()
    return combined


def compile_floor(folder_token: str) -> Path:
    floor_folder = resolve_floor_folder(folder_token)
    csv_files = sorted(
        [f for f in floor_folder.glob("*.csv")],
        key=lambda p: (p.stat().st_mtime, p.name),
    )

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {floor_folder}")

    dest_path = destination_path(floor_folder)

    base_df: Optional[pd.DataFrame]
    base_columns: List[str]

    if dest_path.exists():
        print(f"📄 Using existing compiled file as baseline: {dest_path.name}")
        dest_df = read_csv(dest_path)
        base_columns = list(dest_df.columns)
        base_df = prepare_dataframe(dest_df)
    else:
        first_csv = csv_files.pop(0)
        base_df_raw = read_csv(first_csv)
        base_columns = list(base_df_raw.columns)
        base_df = prepare_dataframe(base_df_raw)
        print(f"🆕 Starting new compiled file with schema from {first_csv.name}")

    for path in csv_files:
        if path == dest_path:
            continue
        print(f"➡️  Merging {path.name}")
        df = read_csv(path, expected_columns=base_columns)
        df = prepare_dataframe(df)
        base_df = merge_dataframes(base_df, df)

    result = base_df.reset_index()
    result = result[base_columns]
    result.to_csv(dest_path, index=False, date_format="%Y-%m-%d %H:%M:%S", decimal=",")
    print(f"✅ Compiled file written: {dest_path}")
    print(f"   Rows: {len(result)}")
    return dest_path


def compile_client(client_token: str) -> None:
    client_dir = DOWNLOADS_ROOT / client_token
    if not client_dir.is_dir():
        raise FileNotFoundError(f"Client folder '{client_token}' not found under {DOWNLOADS_ROOT}")

    subfolders = sorted([p for p in client_dir.iterdir() if p.is_dir()])
    if not subfolders:
        raise FileNotFoundError(f"No tenant folders found under {client_dir}")

    for folder in subfolders:
        print(f"\n=== Compiling data for {client_token}/{folder.name} ===")
        compile_floor("/".join((client_token, folder.name)))


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compile electricity floor CSV files into consolidated datasets.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tenant", help="Tenant/floor folder token (e.g., NEO3_0708 or NEO/NEO3_0708)")
    group.add_argument("--client", help="Client folder token (e.g., NEO) to compile all subfolders")
    args = parser.parse_args(argv)

    try:
        if args.client:
            compile_client(args.client)
        else:
            compile_floor(args.tenant)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Compilation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()


