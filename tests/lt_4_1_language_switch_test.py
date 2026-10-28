#!/usr/bin/env python3
"""LT-4.1: the visible guest language switch must change the *invitation*, not only the chrome.

The control a guest sees on the public page is the ``.language-switch`` that
``core/i18n.js`` injects into the guest topbar; the static proxy pair and the
renderer's own in-page switch are both ``display:none``. Before this fix the
injected switch ran ``EInviteI18n.set()`` only — it swapped ``<html lang>`` (so
the `.i18n` label spans repainted) but never ran the renderer's
``setLanguage``: the root ``data-language``, the guest-language key, the
option labels rewritten from ``data-en``/``data-km``, the ``guest-language-km``
class and the typography projection all stayed on the old language, so the
visible state could disagree with what the page had rendered.

Drives the real test server (``tests/v14_test_utils.app_server``) with Chromium:
the page is opened at 375, the *visible* switch is clicked (a real click, no
``evaluate`` shortcut), and the renderer's own state must follow in both
directions; ``scrollWidth`` stays inside the viewport in both languages, and a
reload keeps the visible switch truthful.
"""
from __future__ import annotations
import os
from pathlib import Path

import pytest

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-4-1-language"

# Built from code points so the test never writes Khmer literals.
KM_TITLE = "".join(chr(cp) for cp in (0x1780, 0x17A2, 0x17C1, 0x179A))
EN_TITLE = "Language switch test"
GUEST_KEY = f"einvite-guest-language:{SLUG}"


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": EN_TITLE,
            "namesKm": KM_TITLE,
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


# Every authenticated mutation carries the double-submit token the app's own bridge
# sends; without it a session-cookie fetch is rejected with `csrf_required`.
_CSRF_HEADERS = """() => {
    const match = document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]*)/);
    return match ? {'X-CSRF-Token': decodeURIComponent(match[1])} : {};
}"""


def _open_page(page, url: str):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("#shareInvitation", timeout=20000)
    cover = page.locator("#openCover")
    if cover.count():
        cover.click()
        page.wait_for_selector("#openCover", state="hidden", timeout=5000)


def _visible_switch(page):
    """The control a guest can actually see and click."""
    return page.locator("header.guest-topbar .language-switch")


def _renderer_state(page) -> dict:
    return page.evaluate(
        """() => {
            const root = document.querySelector('#publicRoot');
            const option = document.querySelector('select[name="status"] option[data-en]');
            const sw = document.querySelector('header.guest-topbar .language-switch [data-lang="km"]');
            return {
                htmlLang: document.documentElement.lang,
                rootLang: root ? root.dataset.language : null,
                rootKm: !!(root && root.classList.contains('guest-language-km')),
                guestKey: (() => { try { const k = Object.keys(localStorage).find(key => key.startsWith('einvite-guest-language:')); return k ? localStorage.getItem(k) : null; } catch (e) { return null; } })(),
                optionKm: option ? option.textContent === option.dataset.km : null,
                switchKm: sw ? sw.getAttribute('aria-pressed') : null,
            };
        }"""
    )


def test_visible_switch_drives_the_invitation_language():
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

            page = browser.new_page(viewport={"width": 375, "height": 812})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("lt-4-1-language@example.com")
            page.locator("#password").fill("Strong-lt-4-1-pass-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-4-1-pass-123")
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
            public_url = page.evaluate(
                """async ([id, documentModel, token]) => {
                    const response = await fetch('/api/invitations/' + id + '/publish', {
                        method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                        body: JSON.stringify({document: documentModel, expectedRevision: null})
                    });
                    const body = await response.json().catch(() => ({}));
                    if (!response.ok) throw Error(JSON.stringify(body));
                    return body.url;
                }""",
                [created["id"], _document(), page.evaluate(_CSRF_HEADERS)],
            )

            _open_page(page, base + public_url)
            page.evaluate("try{localStorage.removeItem('einvite-guest-language:%s');localStorage.removeItem('einvite-lang')}catch(e){}" % SLUG)
            page.reload(wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#shareInvitation", timeout=20000)
            cover = page.locator("#openCover")
            if cover.count():
                cover.click()
                page.wait_for_selector("#openCover", state="hidden", timeout=5000)

            # --- Premise: the visible control is the i18n-injected switch -------------
            switch = _visible_switch(page)
            assert switch.count() == 1 and switch.is_visible(), "the topbar switch must be the visible one"
            assert page.locator(".guest-topbar__lang").is_hidden()
            assert page.evaluate(
                "() => { const n = document.querySelector('.guest-layout-content .language-switch');"
                " return !n || getComputedStyle(n).display === 'none'; }"
            ), "the renderer's in-page switch must stay hidden"

            before = _renderer_state(page)
            assert before["htmlLang"] == "en" and before["rootLang"] == "en", before
            assert before["optionKm"] is False and before["switchKm"] == "false", before

            # --- Click the visible KM button -------------------------------------------
            switch.locator('[data-lang="km"]').click()
            page.wait_for_function(
                "() => document.documentElement.lang === 'km' "
                "&& document.querySelector('#publicRoot').dataset.language === 'km'",
                timeout=10000,
            )
            page.wait_for_function(
                "() => { const o = document.querySelector('select[name=\"status\"] option[data-en]');"
                " return o && o.textContent === o.dataset.km; }",
                timeout=10000,
            )
            after_km = page.evaluate(
                """() => {
                    const root = document.querySelector('#publicRoot');
                    return {
                        guestKey: (() => { try { const k = Object.keys(localStorage).find(key => key.startsWith('einvite-guest-language:')); return k ? localStorage.getItem(k) : null; } catch (e) { return null; } })(),
                        rootKm: root.classList.contains('guest-language-km'),
                        switchKm: document.querySelector('header.guest-topbar .language-switch [data-lang="km"]').getAttribute('aria-pressed'),
                        switchEn: document.querySelector('header.guest-topbar .language-switch [data-lang="en"]').getAttribute('aria-pressed'),
                    };
                }                """
            )
            assert after_km["guestKey"] == "km", after_km
            assert after_km["rootKm"] is True, after_km
            assert after_km["switchKm"] == "true" and after_km["switchEn"] == "false", after_km
            width = page.evaluate("innerWidth")
            assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
            if capture:
                page.screenshot(path=str(capture / "lt-4-1-375-km.png"), full_page=False)

            # --- The choice survives a reload, and the visible switch stays truthful ---
            page.reload(wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#shareInvitation", timeout=20000)
            cover = page.locator("#openCover")
            if cover.count():
                cover.click()
                page.wait_for_selector("#openCover", state="hidden", timeout=5000)
            reloaded = _renderer_state(page)
            assert reloaded["htmlLang"] == "km" and reloaded["rootLang"] == "km", reloaded
            assert reloaded["optionKm"] is True and reloaded["switchKm"] == "true", reloaded

            # --- Click the visible EN button: everything returns -----------------------
            switch = _visible_switch(page)
            switch.locator('[data-lang="en"]').click()
            page.wait_for_function(
                "() => document.documentElement.lang === 'en' "
                "&& document.querySelector('#publicRoot').dataset.language === 'en'",
                timeout=10000,
            )
            after_en = _renderer_state(page)
            assert after_en["guestKey"] == "en" and after_en["rootKm"] is False, after_en
            assert after_en["optionKm"] is False and after_en["switchKm"] == "false", after_en
            assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
            if capture:
                page.screenshot(path=str(capture / "lt-4-1-375-en.png"), full_page=False)

            # The i18n layer and the renderer agree after both directions.
            assert page.evaluate("localStorage.getItem('einvite-lang')") == "en"

            page.close()
            browser.close()
    assert not errors, errors
