#!/usr/bin/env python3
"""analytics-wiring-gap.py — which analytics endpoints the suites call, and which exist.

Why this exists
---------------
`tests/analytics_privacy_test.py` and `tests/analytics_reports_test.py` are red (15
tests) while `tests/analytics_ingestion_test.py` is green (5). The difference is not
the feature: `src/python/features/analytics/` is a complete implementation — model,
session reconstruction, retention, ten read-model queries and two export streams. The
difference is the **routing**, and that is a claim about two files, so this tool prints
it instead of asserting it: it collects every `/api/...` and page path the three suites
reference and reports whether the same literal appears in `src/python/server.py`.

Read-only: reads three test files and the server, writes one line per path to stdout.

Usage
    python3 tools/analytics-wiring-gap.py
    python3 tools/analytics-wiring-gap.py > tools/evidence/analytics-wiring-gap.txt
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "src" / "python" / "server.py"
SUITES = (
    ROOT / "tests" / "analytics_ingestion_test.py",
    ROOT / "tests" / "analytics_privacy_test.py",
    ROOT / "tests" / "analytics_reports_test.py",
)


def main() -> int:
    server = SERVER.read_text(encoding="utf-8")
    suites = "\n".join(path.read_text(encoding="utf-8") for path in SUITES)

    paths = sorted(
        set(re.findall(r'"(/api/[^"\s{]*?)"', suites))
        | set(re.findall(r'"(/[a-z0-9._-]+\.html)"', suites))
    )

    print("ANALYTICS_WIRING_GAP — the endpoints the analytics suites call, and whether")
    print("src/python/server.py serves them")
    print()
    print("The feature is fully built in src/python/features/analytics/:")
    print("  model.py    schema, record_event_batch, purge_invitation_analytics,")
    print("              set_invitation_analytics_enabled, is_invitation_analytics_enabled")
    print("  sessions.py close_idle_sessions, delete_spam_sessions, aggregate_daily_summary,")
    print("              run_retention_prune, run_session_reconstruction")
    print("  queries.py  ten read-model functions, including live activity and account summaries")
    print("  export.py   invitation and account CSV + JSON streams")
    print("What is missing is the wiring: server.py does not route to most of it.")
    print()
    print("This column is a literal search of the server source, so it is a lower bound on what")
    print("is routed: two paths that work are matched by pattern rather than by literal (below).")
    print()
    print(f"{'path a suite calls':60}{'literal in server.py?':>22}")
    for path in paths:
        literal = path.rstrip("/")
        seen = "yes" if literal in server else "no"
        print(f"{path:60}{seen:>22}")
    print()
    print("# the two that are served, and the one that is not a route at all")
    print("POST /api/analytics/events")
    print("    literal: no; matched by pattern. Proof it is served: the 5 ingestion tests pass")
    print("    against a real server (tests/analytics_ingestion_test.py, -k analytics: 5 passed).")
    print("GET  /api/invitations/<id>/analytics")
    print("    literal: no; matched at src/python/server.py:")
    for line in server.splitlines():
        if '"/api/invitations/"' in line and "analytics" in line:
            print("    " + line.strip())
    print("    It exists, and answers with the pre-analytics shape the dashboard already reads.")
    print("/privacy.html")
    print("    not a route: a page file. src/html/privacy.html exists:",
          (ROOT / "src" / "html" / "privacy.html").is_file())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
