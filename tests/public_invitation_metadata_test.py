#!/usr/bin/env python3
"""Regression coverage for published-invitation head metadata and robots policy.

The public invitation shell is a link-sharing surface, not a search landing
page. A published slug must therefore render an absolute self-canonical and a
generic social-image description, and must carry ``noindex, nofollow`` in both
the HTML and the HTTP response. Missing slugs keep the older ``noindex``-only
response.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from v14_test_utils import app_server


def _request(base, path, method="GET", body=None, token=None, expected=200):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    assert status == expected, (method, path, status, raw[:500])
    return json.loads(raw or b"{}")


def test_public_invitation_head_and_robots_policy():
    with app_server({
        "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
        "EINVITE_ALLOW_NO_SCANNER": "1",
    }) as (_process, base, _data):
        stamp = time.time_ns()
        registered = _request(
            base,
            "/api/auth/register",
            method="POST",
            body={"email": f"public-meta-{stamp}@example.com", "password": "strong-password-123"},
            expected=201,
        )
        token = registered["token"]
        document = {
            "schemaVersion": 13,
            "eventType": "Wedding",
            "fields": {
                "names": "[Groom name] & [Bride name]",
                "date": "2027-01-03",
                "venue": "Test venue",
            },
            "objects": {},
            "designPages": [],
            "sectionOrder": [],
            "settings": {"rsvpEnabled": False, "wishesEnabled": False},
        }
        invitation = _request(
            base,
            "/api/invitations",
            method="POST",
            body={"slug": "[Groom name]-[Bride name]-meta", "document": document},
            token=token,
            expected=201,
        )
        _request(
            base,
            f"/api/invitations/{invitation['id']}/publish",
            method="POST",
            body={"document": document},
            token=token,
            expected=201,
        )

        path = f"/i/{urllib.parse.quote(invitation['slug'])}"
        with urllib.request.urlopen(base + path, timeout=15) as response:
            assert response.status == 200
            assert response.headers.get("X-Robots-Tag") == "noindex, nofollow", response.headers
            page = response.read().decode("utf-8")

        assert '<meta property="og:image:alt" content="Invitation preview">' in page
        assert '<meta name="twitter:image:alt" content="Invitation preview">' in page
        assert '<meta name="robots" content="noindex, nofollow">' in page
        canonical = f"{base}{path}"
        assert f'<link rel="canonical" href="{canonical}">' in page, canonical
        assert 'og:image:alt' in page and 'twitter:image:alt' in page

        missing = f"/i/missing-invitation-{stamp}"
        try:
            urllib.request.urlopen(base + missing, timeout=15)
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
            assert exc.headers.get("X-Robots-Tag") == "noindex", exc.headers
        else:
            raise AssertionError("a missing invitation must return 404")
