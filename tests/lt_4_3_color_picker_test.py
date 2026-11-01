#!/usr/bin/env python3
"""LT-4.3: the editor's colour inputs gain recents, an eyedropper and a contrast hint.

The picker itself is the browser's native `<input type="color">`; this item adds a
small popover around it (``src/js/color-picker-extras.js``) instead of a new colour
engine. The test drives the real editor at 1440 and then 375:

- click a text object's colour input in the context toolbar -> the popover opens,
  the native input is still one click away, and the OS dialog is suppressed;
- type a hex value, blur -> the host input, the object's ``data-color`` and the
  local draft all follow (the editor's own handler applied it), and the colour is
  now a recent;
- the contrast hint states a WCAG verdict with the measured ratio, and the ratio
  maths is checked against the known black/white 21:1 pair;
- the eyedropper button appears exactly when ``window.EyeDropper`` exists;
- Escape closes the popover and returns focus to the host input;
- at 375 the popover stays inside the viewport (its CSS is viewport-based, so if no
  colour input is reachable in a drawer at that width the leg opens the popover
  through the module's public API on the object's text colour).

Screenshots are written when ``EINVITE_CAPTURE_DIR`` is set.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from browser_runtime import dismiss_editor_onboarding, launch_chromium, reveal_inspector_control

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-4-3-colour"

_HEX = "#1a6b3f"

_STATE = """() => ({
    popover: !!document.querySelector('.cp-extras'),
    host: document.querySelector('#color')?.value
        || document.querySelector('input[data-ctx="color"]')?.value,
    objectColor: document.querySelector('#stage .object[data-id="title"]')?.dataset.color,
    hint: document.querySelector('.cp-extras [data-cp-contrast]')?.textContent || '',
    hintHidden: document.querySelector('.cp-extras [data-cp-contrast]')?.hidden,
    recents: window.EInviteColorExtras?.recents?.() || [],
    eyedropper: (() => {
        const button = document.querySelector('.cp-extras [data-cp-eyedropper]');
        return button ? { present: !button.hidden, supported: 'EyeDropper' in window } : null;
    })(),
    focused: document.activeElement?.getAttribute('data-cp-value') !== null
        && document.activeElement?.tagName === 'INPUT',
    ratioBW: window.EInviteColorExtras?.contrast?.ratio?.('#000000', '#ffffff') ?? null,
})"""

_CSRF_HEADERS = """() => {
    const match = document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]*)/);
    return match ? {'X-CSRF-Token': decodeURIComponent(match[1])} : {};
}"""


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "Colour picker test",
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


def test_colour_picker_extras():
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

            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("lt-4-3-colour@example.com")
            page.locator("#password").fill("Strong-lt-4-3-pass-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-4-3-pass-123")
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
            # A previous run on this harness profile may have left recents behind.
            page.evaluate("() => localStorage.removeItem('einvite-color-recents-v1')")

            # A real canvas click is what makes the editor show the object inspector;
            # a bridge-only selection leaves #properties hidden.
            page.locator('#stage .object[data-id="title"]').click(position={"x": 8, "y": 8})
            reveal_inspector_control(page, '#color')
            swatch = page.locator('#color')
            swatch.wait_for(state="visible", timeout=15000)
            swatch.click()

            opened = page.wait_for_function(
                "() => !!document.querySelector('.cp-extras input[data-cp-value]')", timeout=5000,
            ) and page.evaluate(_STATE)
            assert opened["popover"] is True, opened
            assert opened["hintHidden"] is False, opened
            assert ":1" in opened["hint"], opened
            assert opened["hint"].startswith(("AA text", "Large text only", "Below AA")), opened
            assert opened["recents"] == [], opened
            assert abs(opened["ratioBW"] - 21.0) < 0.01, opened
            if opened["eyedropper"] and opened["eyedropper"]["supported"]:
                assert opened["eyedropper"]["present"] is True, opened
            else:
                assert opened["eyedropper"]["present"] is False, opened
            if capture:
                page.screenshot(path=str(capture / "lt-4-3-1440-open.png"))

            # A real hex entry, committed with blur (the change event).
            value = page.locator(".cp-extras input[data-cp-value]")
            value.fill(_HEX)
            value.press("Tab")
            page.wait_for_function(
                "(hex) => document.querySelector('#stage .object[data-id=\"title\"]')?.dataset.color === hex",
                arg=_HEX,
                timeout=5000,
            )
            applied = page.evaluate(_STATE)
            assert applied["host"].lower() == _HEX, applied
            assert applied["objectColor"].lower() == _HEX, applied
            assert _HEX in applied["recents"], applied
            assert page.locator(f'.cp-extras .cp-recent[data-color="{_HEX}"]').count() == 1
            # The editor wrote the local draft through its normal save path.
            page.wait_for_function(
                "() => document.documentElement.dataset.savePending === 'false'", timeout=10000,
            )
            stored = page.evaluate(
                """(needle) => Object.entries({...localStorage})
                    .filter(([key]) => key.startsWith('sovan-invite-draft-v3:'))
                    .some(([, value]) => value.includes(needle))""",
                _HEX,
            )
            assert stored, "the picked colour never reached the local draft"

            # Escape closes and hands focus back to the input.
            page.evaluate(
                """() => { window.__lt43Keys = [];
                    window.addEventListener('keydown', (event) =>
                        window.__lt43Keys.push(`${event.key}:${event.target.tagName}:${document.querySelectorAll('.cp-extras').length}`), true); }"""
            )
            page.locator('.cp-extras [data-cp-value]').press("Escape")
            page.wait_for_timeout(250)
            after_escape = page.evaluate(
                """() => ({open: !!document.querySelector('.cp-extras'),
                            active: document.activeElement?.id || document.activeElement?.tagName,
                            keys: window.__lt43Keys, popovers: document.querySelectorAll('.cp-extras').length,
                            modal: [...document.querySelectorAll('dialog[open]')].map(d => d.id || d.className)})"""
            )
            assert after_escape["keys"], f"no keydown reached the page: {after_escape}"
            assert after_escape["open"] is False, after_escape
            assert after_escape["active"] == "color", after_escape

            # --- 375: the popover stays inside the viewport ----------------------------
            page.set_viewport_size({"width": 375, "height": 812})
            page.wait_for_timeout(300)
            visible = page.locator('input[type="color"]:visible')
            if visible.count():
                visible.first.click()
            else:
                page.evaluate("() => window.EInviteColorExtras.open(document.querySelector('#color'))")
            page.wait_for_function("() => !!document.querySelector('.cp-extras')", timeout=5000)
            page.wait_for_timeout(120)
            narrow = page.evaluate(
                """() => {
                    const box = document.querySelector('.cp-extras').getBoundingClientRect();
                    return {left: box.left, right: box.right, top: box.top, bottom: box.bottom,
                            width: innerWidth, height: innerHeight,
                            scrollWidth: document.documentElement.scrollWidth};
                }"""
            )
            assert narrow["left"] >= 0 and narrow["right"] <= narrow["width"], narrow
            assert narrow["top"] >= 0 and narrow["bottom"] <= narrow["height"], narrow
            if capture:
                page.screenshot(path=str(capture / "lt-4-3-375-open.png"))

            browser.close()
    assert not errors, errors
