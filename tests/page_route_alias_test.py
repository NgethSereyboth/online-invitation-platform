#!/usr/bin/env python3
"""Regression: extensionless top-level pages resolve to their HTML asset.

The hosted front end accepts pretty URLs such as ``/templates``. The direct
PC server serves the same app, so those URLs must not 404 there either. The
alias list is intentionally closed; this test also confirms the response is
byte-for-byte the canonical page rather than an arbitrary file.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v14_test_utils import app_server  # noqa: E402

PAGES = (
    "account", "admin", "analytics", "billing", "checkin", "dashboard",
    "designer", "guests", "materials", "privacy", "public", "reset",
    "responses", "templates", "verify",
)


def fetch(base: str, path: str) -> bytes:
    with urllib.request.urlopen(base + path, timeout=10) as response:
        assert response.status == 200, (path, response.status)
        assert response.headers.get_content_type() == "text/html", path
        return response.read()


def main() -> int:
    with app_server({"EINVITE_REQUIRE_EMAIL_VERIFICATION": "0"}) as (_process, base, _data):
        for page in PAGES:
            pretty = fetch(base, f"/{page}")
            canonical = fetch(base, f"/{page}.html")
            assert pretty == canonical, f"/{page} did not match /{page}.html"
    print("PAGE_ROUTE_ALIAS_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
