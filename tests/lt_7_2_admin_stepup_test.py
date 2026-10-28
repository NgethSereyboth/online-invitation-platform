#!/usr/bin/env python3
"""LT-7.2 — destructive admin routes require a live step-up grant (ROADMAP §4.2, §5.9).

Real-HTTP proof on the full app server:

1. Every destructive admin mutation answers **403 `step_up_required`** without a
   grant — the ten routes LT-7.2 moved onto ``require_admin_with_stepup`` plus the
   invitation-flag route that was already gated (parity check).
2. Read-only admin routes keep working without a grant (the gate is not blanket).
3. A **wrong password** is refused (401) and audited as ``admin.stepup_denied``.
4. The real ``POST /api/admin/step-up`` (password, no MFA on this account in dev)
   returns ``stepUp: true`` with a future ``expiresAt`` and audits
   ``admin.stepup_granted``.
5. Every one of the eleven calls now succeeds with the documented response shape.

No SQL shortcut: this exercises the endpoint's own password path.
"""
from __future__ import annotations

import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))


def _cookie(opener, name):
    for cookie in getattr(opener, "handlers", []):
        jar = getattr(cookie, "cookiejar", None)
        if jar is None:
            continue
        for item in jar:
            if item.name == name:
                return urllib.parse.unquote(item.value)
    return ""


def _do(opener, method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    csrf = _cookie(opener, "einvite_csrf")
    if csrf and method in {"POST", "PUT", "DELETE", "PATCH"}:
        h.setdefault("X-CSRF-Token", csrf)
    request = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read() or b""
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, {"_raw": raw.decode("utf-8", "replace")}
    except urllib.error.HTTPError as error:
        raw = error.read() or b""
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"_raw": raw.decode("utf-8", "replace")}


def _opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _register(base, email, password):
    opener = _opener()
    status, data = _do(opener, "POST", f"{base}/api/auth/register", {"email": email, "password": password})
    assert status in {200, 201}, (status, data)
    return opener


def _login(base, email, password):
    opener = _opener()
    status, data = _do(opener, "POST", f"{base}/api/auth/login", {"email": email, "password": password})
    assert status in {200, 201}, (status, data)
    return opener


_DOCUMENT = {
    "schemaVersion": 13,
    "eventType": "Wedding",
    "fields": {
        "names": "Step Up & Test", "namesKm": "", "date": "2029-12-27", "time": "16:05",
        "venue": "Phnom Penh", "venueKm": "", "message": "Welcome", "messageKm": "",
    },
    "settings": {
        "rsvpEnabled": True, "wishesEnabled": False, "scheduleEnabled": False,
        "venueEnabled": False, "galleryEnabled": False, "countdownEnabled": False,
        "musicEnabled": False, "openingEnabled": True, "contactEnabled": False,
    },
    "languageMode": "en", "dateFormat": "gregorian", "accent": "#9d4555",
    "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
    "sectionOrder": ["rsvp"], "schedule": [], "venues": [], "customBlocks": [],
    "designPages": [], "objects": {}, "slug": "lt-7-2-step-up",
}


def test_destructive_admin_routes_require_step_up():
    pytest.importorskip("urllib.request")
    from v14_test_utils import app_server

    admin_email = "admin@einvite.test"
    victim_email = f"lt72-victim-{int(time.time())}@einvite.test"
    password = "Test1234!Pass"
    extra_env = {
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_ADMIN_EMAIL": admin_email,
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
    }

    with app_server(extra_env=extra_env) as (_process, base, _data):
        _register(base, admin_email, password)
        admin = _login(base, admin_email, password)
        status, me = _do(admin, "GET", f"{base}/api/auth/me")
        assert status == 200 and me["user"]["role"] == "admin", (status, me)

        _register(base, victim_email, password)
        victim = _login(base, victim_email, password)
        status, victim_me = _do(victim, "GET", f"{base}/api/auth/me")
        assert status == 200, (status, victim_me)
        victim_id = victim_me["user"]["id"]

        # Fixtures the last two routes need: one user template and one invitation.
        status, template = _do(admin, "POST", f"{base}/api/templates", {
            "name": f"lt72-{int(time.time())}",
            "category": "Wedding",
            "description": "LT-7.2 step-up fixture",
            "document": _DOCUMENT,
        })
        assert status in {200, 201}, (status, template)
        template_id = template.get("id") or template.get("template", {}).get("id")
        assert template_id, template

        status, invite = _do(victim, "POST", f"{base}/api/invitations", {
            "slug": f"lt-7-2-step-up-{int(time.time())}", "document": _DOCUMENT,
        })
        assert status in {200, 201}, (status, invite)
        invite_id = invite.get("id")
        assert invite_id, invite

        destructive = [
            ("POST", f"/api/admin/users/{victim_id}/suspend", {"reason": "lt-7-2 probe"}),
            ("POST", f"/api/admin/users/{victim_id}/unsuspend", {}),
            ("POST", f"/api/admin/users/{victim_id}/reset-password", {}),
            ("POST", f"/api/admin/users/{victim_id}/force-mfa", {}),
            ("PUT", f"/api/admin/users/{victim_id}/plan", {"plan": "creator"}),
            ("PUT", f"/api/admin/users/{victim_id}/role", {"role": "designer"}),
            ("PUT", f"/api/admin/users/{victim_id}/uploads", {"enabled": False}),
            ("PUT", f"/api/admin/users/{victim_id}/session-policy", {"neverExpires": True}),
            ("PUT", "/api/admin/settings/session-idle-days-nonadmin", {"days": 15}),
            ("PUT", f"/api/admin/templates/{template_id}/visibility", {"visibility": "public"}),
            ("PUT", f"/api/admin/invitations/{invite_id}/published", {"published": True}),
            # Already gated before this item — parity check.
            ("POST", f"/api/admin/invitations/{invite_id}/flag", {"flagged": True}),
        ]

        # 2) A read-only admin route keeps working without a grant.
        status, listing = _do(admin, "GET", f"{base}/api/admin/users-v2?limit=5")
        assert status == 200, (status, listing)

        # 1) Every destructive route is refused, with the machine-readable code.
        gated = 0
        for method, path, body in destructive:
            status, data = _do(admin, method, base + path, body)
            assert status == 403, f"{method} {path} without step-up → {status}: {data}"
            assert data.get("code") == "step_up_required", f"{method} {path} → {data}"
            gated += 1
        print(f"[OK] {gated} destructive admin routes refused with step_up_required", flush=True)

        # 3) A wrong password is refused and audited.
        status, data = _do(admin, "POST", f"{base}/api/admin/step-up", {"password": "not-the-password"})
        assert status == 401, (status, data)

        # 4) The real step-up endpoint issues the grant.
        status, data = _do(admin, "POST", f"{base}/api/admin/step-up", {"password": password})
        assert status == 200 and data.get("stepUp") is True, (status, data)
        assert int(data.get("expiresAt", 0)) > int(time.time() * 1000), data

        # 5) Replay every call: all succeed with their documented shapes.
        expected = [
            ("suspended", True), ("unsuspended", True), ("sent", None), ("forceMfa", True),
            ("updated", True), ("updated", True), ("updated", True), ("updated", True),
            ("value", 15), ("updated", True), ("updated", True), ("ok", None),
        ]
        for (method, path, body), (key, value) in zip(destructive, expected):
            status, data = _do(admin, method, base + path, body)
            assert status == 200, f"{method} {path} with step-up → {status}: {data}"
            if value is not None:
                assert data.get(key) == value, f"{method} {path} → {data} (wanted {key}={value})"
            elif key == "sent":
                assert isinstance(data.get("sent"), bool), data
            elif key == "ok":
                assert data.get("flagged") is True or data.get("ok") is True or "flagged" in data, data
        print("[OK] all 12 destructive admin calls succeed with the grant", flush=True)

        # Audited both ways.
        status, events = _do(admin, "GET", f"{base}/api/admin/audit-events?limit=200&action=admin.stepup_granted")
        assert status == 200, (status, events)
        rows = events.get("items") or events.get("events") or []
        assert rows, events
        status, denied = _do(admin, "GET", f"{base}/api/admin/audit-events?limit=200&action=admin.stepup_denied")
        assert status == 200, (status, denied)
        denied_rows = denied.get("items") or denied.get("events") or []
        assert denied_rows, denied
        print("[OK] audit rows admin.stepup_granted + admin.stepup_denied present", flush=True)

    print("LT_7_2_ADMIN_STEPUP_PASSED", flush=True)
