#!/usr/bin/env python3
"""D-3: a second editor tab must autosave after another tab has saved.

The editor intentionally keeps an offline draft in localStorage. A new tab used
to read the cached ``sovan-server-invite:*`` row and skip the server GET, so its
``serverInvite.updatedAt`` was the revision from before the first tab's save.
Its first edit then sent a stale ``expectedRevision`` and the server correctly
answered 409 ``revision_conflict`` — the tab stopped autosaving even though the
first tab had finished.

This drives two real tabs on one invitation. The first tab saves a change, the
second tab saves a different change, and the database must contain both while
the second tab reports no save error.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

from browser_runtime import dismiss_editor_onboarding, launch_chromium


ROOT = Path(__file__).resolve().parents[1]
SLUG = "editor-multi-tab-autosave"


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "[Groom name] & [Bride name]",
            "namesKm": "គូស្នេហ៍",
            "date": "2029-12-27",
            "time": "16:05",
            "venue": "[Venue]",
            "venueKm": "រាជធានីភ្នំពេញ",
            "message": "Welcome",
            "messageKm": "សូមស្វាគមន៍",
        },
        "settings": {
            "rsvpEnabled": True,
            "wishesEnabled": False,
            "scheduleEnabled": True,
            "venueEnabled": True,
            "galleryEnabled": False,
            "countdownEnabled": True,
            "musicEnabled": False,
            "openingEnabled": True,
            "contactEnabled": False,
            "rsvpMaxGuests": 4,
        },
        "languageMode": "both",
        "dateFormat": "gregorian",
        "accent": "#9d4555",
        "palette": {
            "background": "#fff8f2",
            "surface": "#ffffff",
            "text": "#342c26",
            "heading": "#9d4555",
        },
        "sectionOrder": ["countdown", "schedule", "rsvp"],
        "schedule": [],
        "venues": [],
        "customBlocks": [],
        "designPages": [],
        "objects": {},
        "slug": SLUG,
    }


def _read(data: Path, invite_id: str) -> dict:
    with closing(sqlite3.connect(data / "invites.db")) as db:
        row = db.execute(
            "SELECT draft_json,updated_at FROM invitations WHERE id=?", (invite_id,)
        ).fetchone()
    assert row, invite_id
    return {"document": json.loads(row[0]), "updatedAt": int(row[1] or 0)}


def test_second_tab_autosaves_against_the_latest_revision():
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    errors: list[str] = []
    with app_server({"EINVITE_REQUIRE_EMAIL_VERIFICATION": "0"}) as (_process, base, data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")

            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            email = f"multi-tab-{time.time_ns()}@example.com"
            page.locator("#email").fill(email)
            page.locator("#password").fill("Strong-multi-tab-pass-123")
            page.locator("#registerConfirmPassword").fill("Strong-multi-tab-pass-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            created = page.evaluate(
                """async documentModel => {
                    const token = document.cookie.match(/(?:^|; \\s*)einvite_csrf=([^;]*)/)?.[1] || '';
                    const response = await fetch('/api/invitations', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': decodeURIComponent(token)},
                        body: JSON.stringify({slug: documentModel.slug, document: documentModel})
                    });
                    if (!response.ok) throw Error(await response.text());
                    return response.json();
                }""",
                _document(),
            )
            invite_id = created["id"]
            editor_url = base + f"/invitations/{invite_id}/editor"

            first = context.new_page()
            first.on("pageerror", lambda error: errors.append("first:" + str(error)))
            first.goto(editor_url, wait_until="domcontentloaded", timeout=30000)
            dismiss_editor_onboarding(first, timeout=30000)
            stale_cache = first.evaluate(
                "id => localStorage.getItem('sovan-server-invite:' + id)", invite_id
            )
            assert stale_cache, "first tab did not cache its server row"

            # The first tab saves before the second tab boots. The second tab's
            # cached row is still the pre-save one: force that real state before
            # its scripts run. Old code skipped the GET and saved against this
            # stale revision; the refresh must replace it with the server row.
            first.evaluate(
                """() => EInviteEditorBridge.transact('First tab saved', documentState => {
                    documentState.fields.names = 'First tab saved names';
                })"""
            )
            deadline = time.time() + 15
            saved = None
            while time.time() < deadline:
                saved = _read(data, invite_id)
                if saved["document"].get("fields", {}).get("names") == "First tab saved names":
                    break
                time.sleep(0.15)
            assert saved and saved["document"]["fields"]["names"] == "First tab saved names", saved

            second = context.new_page()
            second.on("pageerror", lambda error: errors.append("second:" + str(error)))
            second.add_init_script(
                script="try{localStorage.setItem(%s,%s)}catch{}"
                % (json.dumps(f"sovan-server-invite:{invite_id}"), json.dumps(stale_cache))
            )
            second.goto(editor_url, wait_until="domcontentloaded", timeout=30000)
            dismiss_editor_onboarding(second, timeout=30000)
            assert second.evaluate("() => EInviteEditorBridge.getState().fields.names") == "First tab saved names"

            second.evaluate(
                """() => EInviteEditorBridge.transact('Second tab saved', documentState => {
                    documentState.fields.venue = 'Second tab saved venue';
                })"""
            )
            deadline = time.time() + 15
            latest = None
            while time.time() < deadline:
                latest = _read(data, invite_id)
                if latest["document"].get("fields", {}).get("venue") == "Second tab saved venue":
                    break
                time.sleep(0.15)

            assert latest and latest["document"]["fields"]["venue"] == "Second tab saved venue", latest
            assert latest["document"]["fields"]["names"] == "First tab saved names", latest
            assert second.evaluate("() => document.documentElement.dataset.serverSaveErrorCode || ''") == ""
            assert second.locator("#serverState").inner_text() == "Server connected"
            assert not errors, errors
            browser.close()
