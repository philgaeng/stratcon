#!/usr/bin/env python3
"""Generate report for tenant_id = 12"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.services.domain.reporting import generate_report_for_tenant

if __name__ == "__main__":
    try:
        print("Generating report for tenant_id = 12...")
        report_path = generate_report_for_tenant(tenant_id=12)
        print(f"✅ Report generated successfully at: {report_path}")
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

