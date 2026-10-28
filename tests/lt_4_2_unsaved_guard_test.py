#!/usr/bin/env python3
"""LT-4.2: the editor asks before a close/reload while a draft write is pending.

The editor autosaves, but a scheduled write is not in the local draft for ~220 ms
after an edit. Before this item nothing stopped a reload or tab close inside that
window (``beforeunload`` existed only in unrelated modules), so the edit was lost
silently. ``src/js/app.js`` now mirrors the visible "Saving…" state into a
``pendingWrite`` flag, exposes it as ``documentElement.dataset.savePending`` and
cancels ``beforeunload`` while it is set.

Drives the real test server (``tests/v14_test_utils.app_server``) with Chromium at
1600x1000: the edit is typed into the couple-names field with real key events, the
guard's contract is checked with a dispatched cancelable ``beforeunload`` (the same
event the browser fires), the flag is watched through the save cycle, and the local
draft is inspected to prove the edit really was written. A real
``page.close(run_before_unload=True)`` probe records whether headless Chromium
surfaces the native prompt (host dependent, reported, not asserted).

# ``#saveState`` is deliberately not asserted on: ``studio-experience.js`` rewrites it
into bilingual ``.i18n`` spans, so its ``textContent`` concatenates both languages.
the flag is the contract; the visible label is a rendering detail.
"""
from __future__ import annotations
import os
from pathlib import Path

import pytest

from browser_runtime import dismiss_editor_onboarding, launch_chromium

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-4-2-unsaved"

_EVENT = """() => {
    const event = new Event('beforeunload', {cancelable: true});
    window.dispatchEvent(event);
    return {prevented: event.defaultPrevented, pending: document.documentElement.dataset.savePending,
            state: document.querySelector('#saveState')?.textContent};
}"""


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "Unsaved guard test",
            "namesKm": "",
            "date": "2029-12-27",
            "time": "16:05",
            "venue": "Phnom Penh",
            "venueKm": "",
            "message": "Welcome",
            "messageKm": "",
        },
        "settings": {
            "rsvpEnabled": True,
            "wishesEnabled": False,
            "scheduleEnabled": False,
            "venueEnabled": False,
            "galleryEnabled": False,
            "countdownEnabled": False,
            "musicEnabled": False,
            "openingEnabled": True,
            "contactEnabled": False,
        },
        "languageMode": "both",
        "dateFormat": "gregorian",
        "accent": "#9d4555",
        "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
        "sectionOrder": ["rsvp"],
        "schedule": [],
        "venues": [],
        "customBlocks": [],
        "designPages": [],
        "objects": {},
        "slug": SLUG,
    }


_CSRF_HEADERS = """() => {
    const match = document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]*)/);
    return match ? {'X-CSRF-Token': decodeURIComponent(match[1])} : {};
}"""


def test_editor_guards_a_pending_write():
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    capture = Path(os.environ["EINVITE_CAPTURE_DIR"]) if os.environ.get("EINVITE_CAPTURE_DIR") else None
    if capture:
        capture.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")

            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("lt-4-2-unsaved@example.com")
            page.locator("#password").fill("Strong-lt-4-2-pass-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-4-2-pass-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            created = page.evaluate(
                """async ([documentModel, token]) => {
                    const response = await fetch('/api/invitations', {
                        method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                        body: JSON.stringify({slug: documentModel.slug, document: documentModel})
                    });
                    if (!response.ok) throw Error(await response.text());
                    return response.json();
                }""",
                [_document(), page.evaluate(_CSRF_HEADERS)],
            )

            page.goto(base + f"/invitations/{created['id']}/editor", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)

            # --- Clean state: the guard must stay out of the way -----------------------
            page.wait_for_function(
                "() => document.documentElement.dataset.savePending === 'false'",
                timeout=20000,
            )
            clean = page.evaluate(_EVENT)
            assert clean["prevented"] is False and clean["pending"] == "false", clean

            # --- A real keyboard edit makes the write pending --------------------------
            # The creation panel remembers the last used tab, so open the Event tab the
            # way a person would, then type into the couple-names field: the field commits
            # to the document and schedules the debounced 220 ms write.
            page.locator('[data-studio-tab="event"]').click()
            names = page.locator("#names")
            names.wait_for(state="visible", timeout=15000)
            names.click()
            page.keyboard.press("End")
            before = names.input_value()
            typed = " + guard"
            names.press_sequentially(typed, delay=10)
            assert names.input_value() == before + typed, names.input_value()
            pending_state = None
            for _ in range(60):
                pending_state = page.evaluate(_EVENT)
                if pending_state["pending"] == "true":
                    break
                page.wait_for_timeout(10)
            assert pending_state and pending_state["pending"] == "true", pending_state
            assert pending_state["prevented"] is True, pending_state
            if capture:
                page.screenshot(path=str(capture / "lt-4-2-pending.png"), full_page=False)

            # --- Once saved, the guard releases ---------------------------------------
            page.wait_for_function(
                "() => document.documentElement.dataset.savePending === 'false'",
                timeout=10000,
            )
            settled = page.evaluate(_EVENT)
            assert settled["prevented"] is False and settled["pending"] == "false", settled
            # The edit reached the local draft, so the flag really tracked a write.
            stored = page.evaluate(
                """(needle) => Object.entries({...localStorage})
                    .filter(([key]) => key.startsWith('sovan-invite-draft-v3:'))
                    .some(([, value]) => value.includes(needle))""",
                before + typed,
            )
            assert stored, "the typed edit was not written to the local draft"
            if capture:
                page.screenshot(path=str(capture / "lt-4-2-saved.png"), full_page=False)

            # --- Real close path (host dependent, reported not asserted) --------------
            names.click()
            page.keyboard.press("End")
            names.press_sequentially("!", delay=10)
            pending_again = page.evaluate(_EVENT)
            dialogs: list[str] = []
            page.on("dialog", lambda dialog: (dialogs.append(dialog.type), dialog.dismiss()))
            try:
                page.close(run_before_unload=True)
            except Exception as exc:  # noqa: BLE001 - probe only
                print(f"LT_4_2_CLOSE_PROBE_ERROR {exc}")
            print(f"LT_4_2_PENDING_AGAIN {pending_again['pending']} LT_4_2_DIALOGS {dialogs}")

            browser.close()
    assert not errors, errors
