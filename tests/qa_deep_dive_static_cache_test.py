#!/usr/bin/env python3
"""Regression coverage for the public static-asset cache policy.

Browser bundles keep stable filenames across releases, so they are reused for
a bounded hour and revalidated afterwards. Template-pack artwork is
content-addressed per filename and may be cached for a day. API responses must
never inherit either policy.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

from v14_test_utils import app_server

ROOT = Path(__file__).resolve().parents[1]
REVALIDATE = "public, max-age=3600, must-revalidate"


def _request(base: str, path: str, method: str = "GET"):
    request = urllib.request.Request(base + path, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, response.headers.get("Cache-Control")


def test_public_static_cache_policy():
    with app_server({"EINVITE_ALLOW_NO_SCANNER": "1"}) as (_process, base, _data):
        for path in (
            "/bundle-dashboard.css",
            "/assets/icons.svg",
            "/vendor/yjs/y.js",
            "/core/theme.js",
        ):
            status, cache = _request(base, path)
            assert status == 200, path
            assert cache == REVALIDATE, (path, cache)
            status, cache = _request(base, path, "HEAD")
            assert status == 200, path
            assert cache == REVALIDATE, ("HEAD", path, cache)

        pack = next((ROOT / "src/python/assets/template-pack/built").glob("*.js"))
        status, cache = _request(base, f"/assets/template-pack/built/{pack.name}")
        assert status == 200
        assert cache == "public, max-age=86400"

        status, cache = _request(base, "/api/health")
        assert status == 200
        assert cache is None or "no-store" in cache, cache
