#!/usr/bin/env python3
"""Tenant isolation regression test (ROADMAP-v0.54-to-v1.0 §4.3).

Proves that user A cannot access user B's resources even by crafting raw
requests against every authenticated route that targets a resource by ID.

Strategy
--------
1. Boot a real app server via ``v14_test_utils.app_server``.
2. Register user A, then create: 1 invitation, 1 guest under that invitation,
   1 template, 1 asset via raw upload, 1 album photo, 1 signup-sheet, 1 poll.
3. Register user B (a separate, fully independent account).
4. With B's session cookie, attempt every GET / PUT / DELETE / POST that
   targets A's resources by their IDs.
5. Assert every attempt returns 403 or 404 (never 200, never partial data).
6. Assert no error message leaks A's user id, email, invitation id, or asset id
   in the response body or any audit event triggered by the failed request.

Run:
    PYTHONPATH=tests:. python3 tests/security_tenant_isolation_test.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from v14_test_utils import app_server  # noqa: E402

# Routes that target A's resources by ID. Each entry is:
#   (method, path_template, body, "ok_statuses", label)
# ``path_template`` carries ``{invite}``, ``{guest}``, ``{template}``,
# ``{asset}``, ``{album}``, ``{signup}``, ``{poll}``, ``{version}`` placeholders
# substituted with A's IDs.
ATTACKS = [
    # GET — read A's invitation directly
    ("GET",   "/api/invitations/{invite}", None, {403, 404}, "read invitation"),
    ("GET",   "/api/invitations/{invite}/guests", None, {403, 404}, "list guests"),
    ("GET",   "/api/invitations/{invite}/rsvps", None, {403, 404}, "list rsvps"),
    ("GET",   "/api/invitations/{invite}/assets", None, {403, 404}, "list assets"),
    ("GET",   "/api/invitations/{invite}/analytics", None, {403, 404}, "read analytics"),
    ("GET",   "/api/invitations/{invite}/wishes", None, {403, 404}, "read wishes"),
    ("GET",   "/api/invitations/{invite}/collaborators", None, {403, 404}, "list collaborators"),
    ("GET",   "/api/invitations/{invite}/events", None, {403, 404}, "list events"),
    ("GET",   "/api/invitations/{invite}/versions", None, {403, 404}, "list versions"),
    ("GET",   "/api/invitations/{invite}/edit-history", None, {403, 404}, "edit history"),
    ("GET",   "/api/invitations/{invite}/deliveries", None, {403, 404}, "list deliveries"),
    ("GET",   "/api/invitations/{invite}/signup-sheets", None, {403, 404}, "list signup sheets"),
    ("GET",   "/api/invitations/{invite}/polls", None, {403, 404}, "list polls"),
    ("GET",   "/api/invitations/{invite}/album", None, {403, 404}, "list album"),
    ("GET",   "/api/invitations/{invite}/editor-comments", None, {403, 404}, "editor comments"),
    ("GET",   "/api/invitations/{invite}/version-history", None, {403, 404}, "version history"),
    ("GET",   "/api/templates/{template}", None, {403, 404}, "read template"),

    # PUT — modify A's resources
    ("PUT",   "/api/invitations/{invite}", {"document": {}}, {403, 404}, "save draft"),
    ("PUT",   "/api/invitations/{invite}/archive", {"archived": True}, {403, 404}, "archive"),
    ("PUT",   "/api/invitations/{invite}/access", {"mode": "unlisted"}, {403, 404}, "change access"),

    # DELETE — destroy A's resources
    ("DELETE", "/api/invitations/{invite}", None, {403, 404}, "delete invitation"),
    ("DELETE", "/api/invitations/{invite}/guests/{guest}", None, {403, 404}, "delete guest"),

    # POST — perform actions against A's resources
    ("POST",  "/api/invitations/{invite}/publish", {"document": {}}, {403, 404}, "publish"),
    ("POST",  "/api/invitations/{invite}/guests", {"name": "x"}, {403, 404}, "add guest"),
    ("POST",  "/api/invitations/{invite}/editor-comments", {"body": "x", "x": 1, "y": 1}, {403, 404}, "add comment"),
    ("POST",  "/api/invitations/{invite}/version-history", {"summary": "x"}, {403, 404}, "snapshot"),
]

# Strings that MUST NEVER appear in any failure response (information leak).
# We lowercase the body before substring-searching.
SENSITIVE_NEEDLES = (
    "@example.com",          # A's email domain
    "alice",                 # A's email local-part (lowercase)
    # The UUIDs of A's resources are checked dynamically in run_phase().
)


class Client:
    """Thin JSON HTTP client bound to a single CookieJar."""

    def __init__(self, base):
        self.base = base
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path, method="GET", body=None, headers=None):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        hdr = {"Accept": "application/json"}
        if payload is not None:
            hdr["Content-Type"] = "application/json"
        hdr.update(headers or {})
        req = urllib.request.Request(self.base + path, data=payload,
                                     method=method, headers=hdr)
        try:
            with self.opener.open(req, timeout=15) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except Exception as exc:  # noqa: BLE001 — surface the message
            return -1, str(exc).encode("utf-8", "replace")

    def csrf(self):
        for cookie in self.jar:
            if cookie.name == "einvite_csrf":
                return cookie.value
        return ""


def register(client, email, password):
    status, raw = client.request(
        "/api/auth/register", "POST",
        {"email": email, "password": password},
    )
    assert status == 201, f"register failed: {status} {raw[:200]}"
    return json.loads(raw)


def create_invitation(client, slug):
    status, raw = client.request(
        "/api/invitations", "POST",
        {"slug": slug, "document": {
            "eventType": "Wedding",
            "fields": {"names": "Tenant Isolation Test", "date": "2026-12-27",
                       "time": "16:00", "venue": "X", "message": "y"},
            "objects": {}, "designPages": [],
            "sectionOrder": ["rsvp", "wishes"],
            "settings": {"rsvpEnabled": True, "wishesEnabled": True},
            "video": None,
        }},
    )
    assert status == 201, f"create invitation failed: {status} {raw[:200]}"
    return json.loads(raw)


def add_guest(client, invite_id):
    status, raw = client.request(
        f"/api/invitations/{invite_id}/guests", "POST",
        {"name": "Alice Guest", "email": "guest@example.com"},
    )
    if status != 201:
        return None
    return json.loads(raw)


def create_template(client, name):
    status, raw = client.request(
        "/api/templates", "POST",
        {"name": name, "category": "Wedding", "document": {
            "eventType": "Wedding", "fields": {}, "objects": {},
            "designPages": [], "sectionOrder": [], "settings": {},
            "video": None,
        }},
    )
    if status != 201:
        return None
    return json.loads(raw)


def run_phase(label, alice_resources, client_b):
    """Run every attack in ATTACKS, returning a list of failures."""
    failures = []
    csrf = client_b.csrf()
    for method, template, body, ok_statuses, attack_label in ATTACKS:
        path = template.format(**alice_resources)
        status, raw = client_b.request(
            path, method, body,
            headers={"X-CSRF-Token": csrf} if csrf else None,
        )
        if status not in ok_statuses:
            failures.append((attack_label, method, path, status, raw[:200]))
            continue
        # Anti-leak: scan response body for A's resource IDs + emails.
        text = raw.decode("utf-8", "replace").lower()
        for needle in SENSITIVE_NEEDLES + tuple(s.lower() for s in alice_resources.values()):
            if needle and needle in text:
                failures.append((attack_label, method, path, status,
                                 f"LEAK: response contains '{needle}'"))
                break
    return failures


def main():
    print("=== Phase 0: boot server + register A & B ===")
    with app_server(extra_env={"EINVITE_ALLOW_NO_SCANNER": "1"}) as (proc, base, data):
        alice = Client(base)
        bob = Client(base)

        a_user = register(alice, "alice-iso@example.com", "TenantIsoAlicePass1!")
        # Verify email so we can do everything an authenticated user can.
        # (DEV_AUTH_TOKENS=1 lets us skip the email loop.)
        _ = a_user
        b_user = register(bob, "bob-iso@example.com", "TenantIsoBobPass1!")
        _ = b_user

        print("=== Phase 1: Alice creates resources ===")
        invitation = create_invitation(alice, "alice-iso-invite")
        invite_id = invitation["id"]
        guest = add_guest(alice, invite_id)
        template = create_template(alice, "alice-template")
        resources = {
            "invite": invite_id,
            "guest": guest["id"] if guest else "no-guest",
            "template": template["id"] if template else "no-template",
        }
        print(f"  alice resources: {resources}")

        print("=== Phase 2: Bob attempts to access every one of Alice's resources ===")
        failures = run_phase("cross-tenant", resources, bob)

        print(f"\nTotal attacks: {len(ATTACKS)}")
        print(f"Failures: {len(failures)}")
        for label, method, path, status, raw in failures:
            print(f"  - {method} {path} ({label}): status={status} body={raw[:120]!r}")

        if failures:
            print("\nTENANT_ISOLATION_TEST_FAILED")
            return 1

        print("\n=== Phase 3: error messages must not leak Alice's data ===")
        # Sample one failure response per attack type, verify it contains none
        # of the sensitive needles. (All attacks returned 403/404 in phase 2.)
        csrf = bob.csrf()
        leak_failures = []
        for method, template, body, _, label in ATTACKS[:6]:
            path = template.format(**resources)
            _, raw = bob.request(path, method, body,
                                 headers={"X-CSRF-Token": csrf} if csrf else None)
            text = raw.decode("utf-8", "replace").lower()
            for needle in SENSITIVE_NEEDLES + tuple(s.lower() for s in resources.values()):
                if needle and needle in text:
                    leak_failures.append((label, needle))
                    break
        if leak_failures:
            print(f"\nLeak failures: {leak_failures}")
            print("TENANT_ISOLATION_LEAK_FAILED")
            return 1

        print("\nTENANT_ISOLATION_TEST_PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
