#!/usr/bin/env python3
"""D-12: the admin Users tab must show suspension from /api/admin/users.

The legacy users endpoint is the one this page reads. It already selects and
returns ``suspended``; the row renderer ignored it, so a suspended account was
indistinguishable from an active one. This intercepts the page's API calls and
drives the real renderer, which keeps the check independent of admin seeding.
"""
from __future__ import annotations

import json

import pytest

from browser_runtime import launch_chromium


def _payload(path: str) -> dict:
    if path.endswith("/api/auth/me"):
        return {"user": {"id": "admin-1", "role": "admin"}}
    if path.endswith("/api/admin/overview"):
        return {"users": 2, "invitations": 0}
    if path.endswith("/api/admin/users"):
        return [
            {
                "id": "u-suspended",
                "email": "suspended@example.com",
                "role": "customer",
                "plan": "free",
                "uploadEnabled": False,
                "createdAt": 1793530000000,
                "suspended": True,
                "invitationCount": 0,
                "templateCount": 0,
            },
            {
                "id": "u-active",
                "email": "active@example.com",
                "role": "designer",
                "plan": "creator",
                "uploadEnabled": True,
                "createdAt": 1793530000000,
                "suspended": False,
                "invitationCount": 1,
                "templateCount": 2,
            },
        ]
    if path.endswith("/api/admin/templates") or path.endswith("/api/admin/invitations"):
        return []
    if path.endswith("/api/admin/ai/providers"):
        return {"providers": [], "modelRoles": {}, "modelDirectory": {}}
    return {}


def test_admin_users_row_shows_suspension():
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")

            page = browser.new_page(viewport={"width": 1200, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))

            def fulfill(route):
                path = route.request.url.split("?", 1)[0]
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(_payload(path)),
                )

            page.route("**/api/**", fulfill)
            page.goto(base + "/admin.html", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector('#usersPanel tr[data-user-id="u-suspended"]', timeout=15000)

            suspended = page.locator('#usersPanel tr[data-user-id="u-suspended"]')
            active = page.locator('#usersPanel tr[data-user-id="u-active"]')
            assert suspended.locator(".ei-tag").inner_text() == "Suspended"
            assert "ei-tag-warn" in (suspended.locator(".ei-tag").get_attribute("class") or "")
            assert active.locator(".ei-tag").inner_text() == "Active"
            assert "ei-tag-ok" in (active.locator(".ei-tag").get_attribute("class") or "")
            assert not errors, errors
            browser.close()
