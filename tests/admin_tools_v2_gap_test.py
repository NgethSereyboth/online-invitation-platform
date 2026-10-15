#!/usr/bin/env python3
"""admin_tools_v2_gap_test.py — regression guard for the Part-5 admin route gap (inventory A2).

History
-------
``tests/admin_tools_test.py`` is the *spec* for the nine Part-5 admin tasks, but it is a
script — its own ``main()`` plus an ``app_server()`` boot — not a pytest module. Measured:

    .venv/bin/python -m pytest tests/admin_tools_test.py --collect-only -q
    no tests collected in 0.35s

So when the ``/api/admin/*-v2`` routes were missing (every caller got 404), the suite
could not report it. This module ran the spec's first call under a strict ``xfail`` to make
the gap *named* in ``pytest -q``. The server routes have since landed
(``docs/reviews/A2-2026-10-13.md`` §4), so the xfail is removed; the test stays as a
fast regression guard asserting the contract the dashboard depends on.

The spec script is imported, never modified: ``main()`` is ``__main__``-guarded, so
importing it has no side effects.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from v14_test_utils import app_server  # type: ignore  # noqa: E402
import admin_tools_test as spec  # type: ignore  # noqa: E402  (the spec script)


def test_admin_metrics_v2_route_exists() -> None:
    """The spec's first assertion: `phase_dashboard_overview` requires this to return 200."""
    extra_env = {
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_ADMIN_EMAIL": "admin@einvite.test",
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
    }
    with app_server(extra_env=extra_env) as (_process, base, _data_dir):
        spec.register(base, "admin@einvite.test")
        opener = spec.login(base, "admin@einvite.test")
        status, _, data = spec._do(opener, "GET", f"{base}/api/admin/metrics-v2")
        assert status == 200, f"GET /api/admin/metrics-v2 returned {status}: {data}"
        cards = data.get("cards") or []
        keys = {c["key"] for c in cards}
        expected = {"users", "invitations", "activeSessions", "storage", "failedLogins",
                    "rateLimitHits", "jobQueueDepth", "dbP95"}
        assert keys == expected, f"missing/extra stat keys: {keys ^ expected}"
