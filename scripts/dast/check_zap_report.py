#!/usr/bin/env python3
"""Fail the DAST job on High or Critical ZAP alerts and write a summary."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


class ReportError(RuntimeError):
    pass


def alert_risk(alert):
    raw_code = alert.get("riskcode", 0)
    try:
        code = int(raw_code)
    except (TypeError, ValueError):
        code = -1
    # ZAP appends confidence in parentheses, e.g. "Low (High)". Only the
    # text before that parenthesis describes the risk; confidence must not
    # promote a Low/Informational finding to High.
    description = str(alert.get("riskdesc", "")).split("(", 1)[0].strip().lower()
    if code >= 4 or "critical" in description:
        return "Critical", max(code, 4)
    if code >= 3 or "high" in description:
        return "High", max(code, 3)
    if code == 2 or "medium" in description:
        return "Medium", 2
    if code == 1 or "low" in description:
        return "Low", 1
    return "Informational", 0


def collect_alerts(report):
    sites = report.get("site")
    if isinstance(sites, dict):
        sites = [sites]
    if sites is None:
        # Some wrappers emit a root-level alerts array; support it while still
        # requiring a recognizable ZAP document.
        alerts = report.get("alerts")
        if isinstance(alerts, list):
            return alerts
        raise ReportError("ZAP report has no site/alerts data")
    if not isinstance(sites, list) or not sites:
        raise ReportError("ZAP report contains no scanned site")
    alerts = []
    for site in sites:
        site_alerts = site.get("alerts", []) if isinstance(site, dict) else []
        if isinstance(site_alerts, list):
            alerts.extend(site_alerts)
    return alerts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DAST_REPORT_INVALID: {exc}", file=sys.stderr)
        return 1

    try:
        alerts = collect_alerts(report)
    except ReportError as exc:
        print(f"DAST_REPORT_INVALID: {exc}", file=sys.stderr)
        return 1

    counts = Counter()
    findings = []
    for alert in alerts:
        risk, code = alert_risk(alert)
        counts[risk] += 1
        if code >= 3:
            instances = alert.get("instances") or []
            findings.append(
                {
                    "name": alert.get("name") or alert.get("alert"),
                    "risk": risk,
                    "confidence": alert.get("confidence"),
                    "count": len(instances) if isinstance(instances, list) else 1,
                    "urls": [
                        instance.get("uri")
                        for instance in instances
                        if isinstance(instance, dict) and instance.get("uri")
                    ][:20],
                }
            )

    high_critical = counts["High"] + counts["Critical"]
    summary = {
        "totalAlerts": len(alerts),
        "alertsByRisk": dict(counts),
        "highCritical": high_critical,
        "highCriticalFindings": findings,
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"ZAP_REPORT_TOTAL_ALERTS={len(alerts)}")
    print(f"ZAP_REPORT_HIGH_CRITICAL={high_critical}")
    for finding in findings:
        print(f"ZAP_FINDING {finding['risk']}: {finding['name']}")
    if high_critical:
        print("DAST_GATE_FAILED: High or Critical alerts found", file=sys.stderr)
        return 1
    print("DAST_REPORT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
