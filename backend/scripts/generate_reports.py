#!/usr/bin/env python3
"""Generate electricity reports for specific tenants or clients."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Ensure backend package is importable
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.domain.reporting.folder_helpers import list_tenant_folders
from services.domain.reporting import (
    generate_reports_for_tenant,
    generate_reports_for_client,
)

def interactive_run() -> None:
    tenants = list_tenant_folders()
    if not tenants:
        print("❌ No tenant folders found under downloads/" )
        sys.exit(1)

    print("Available floor folders:")
    for folder in tenants:
        print(f"  - {folder.name}")

    choice = input("Enter folder name (e.g., NEO3_0708) or 'all': ").strip()
    if choice.lower() == "all":
        generate_reports_for_client()
    else:
        generate_reports_for_tenant(choice)


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate electricity reports.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tenant", help="Tenant/floor token (e.g., NEO3_0708 or NEO/NEO3_0708)")
    group.add_argument("--client", help="Client token (e.g., NEO) to generate all tenant reports")
    args = parser.parse_args(argv)

    if args.client:
        generate_reports_for_client(args.client)
    elif args.tenant:
        generate_reports_for_tenant(args.tenant)
    else:
        interactive_run()

    print("\n✅ Report generation completed")


if __name__ == "__main__":
    main()


