from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DR = ROOT / "docs" / "ops" / "BACKUP-DR.md"
RPO_RTO = ROOT / "docs" / "ops" / "RPO-RTO-TARGETS.md"


def test_dr_drill_status_is_explicit_and_evidence_backed():
    """A DR drill is complete only with a dated report and measured timings."""
    backup = BACKUP_DR.read_text(encoding="utf-8")
    targets = RPO_RTO.read_text(encoding="utf-8")

    report_dir = ROOT / "docs" / "ops" / "drill-reports"
    reports = list(report_dir.glob("*.md")) if report_dir.exists() else []
    has_measured_report = any(
        re.search(r"(?im)^\s*(?:measured )?R(?:PO|TO)\s*[:=].+", report.read_text(encoding="utf-8"))
        for report in reports
    )
    complete = bool(re.search(r"(?i)(completed|performed).{0,80}restore drill", backup))

    if complete:
        assert reports and has_measured_report, (
            "Do not label the DR drill complete without a report containing measured RPO/RTO"
        )
    else:
        assert "planned" in backup.lower() or "not yet performed" in backup.lower()
        assert "performed end-to-end in staging" in targets
