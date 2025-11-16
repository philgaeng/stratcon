import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.reporting import generate_report_for_tenant
from backend.services.reporting import ReportingOrchestrator
from backend.services.utils import ReportLogger


def test_generate_report_for_tenant_writes_file(monkeypatch, tmp_path):
    html = "<html><body>Report</body></html>"
    fake_bundle = {
        "html": html,
        "analysis": {"label": "Tenant 1"},
        "charts": {},
    }

    fake_orchestrator = MagicMock()
    fake_orchestrator.generate_onepager_report.return_value = fake_bundle

    monkeypatch.setattr(
        "backend.services.reporting.report_generation.ReportingOrchestrator",
        lambda **kwargs: fake_orchestrator,
    )

    output_path = generate_report_for_tenant(
        tenant_id=1,
        client_id=1,
        output_dir=tmp_path,
        logger=ReportLogger(),
    )

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == html
