"""LT-2.6 follow-up — an empty photo slot stays editor-only.

The default document stores its hero image as an 800x600 maroon SVG data URI.
That is not a photo, so the editor marks the object and draws the dashed slot +
"Add photo" chip. The stored value is never rewritten: the export DOM snapshot
and the public guest page must contain neither the chip text nor its class.
"""
from __future__ import annotations

import pytest

from browser_runtime import launch_chromium

PLACEHOLDER = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E"
    "%3Crect width='800' height='600' fill='%239d4555'/%3E%3C/svg%3E"
)
SLUG = "lt-2-6-empty-photo"

_CSRF_HEADERS = """() => {
    const match = document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]*)/);
    return match ? {'X-CSRF-Token': decodeURIComponent(match[1])} : {};
}"""


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "Empty photo slot",
            "date": "2029-12-27",
            "time": "16:00",
            "venue": "Phnom Penh",
            "message": "You are invited.",
        },
        "settings": {
            "rsvpEnabled": False,
            "wishesEnabled": False,
            "scheduleEnabled": False,
            "venueEnabled": False,
            "galleryEnabled": False,
            "countdownEnabled": False,
            "musicEnabled": False,
            "openingEnabled": False,
            "contactEnabled": False,
        },
        "languageMode": "en",
        "dateFormat": "gregorian",
        "accent": "#9d4555",
        "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
        "sectionOrder": [],
        "schedule": [],
        "venues": [],
        "customBlocks": [],
        "designPages": [],
        "objects": {
            "title": {
                "id": "title", "type": "text", "left": "8%", "top": "12%", "width": "84%", "height": "110px",
                "html": "Empty photo slot", "fontSize": 52, "color": "#f5d88a", "zIndex": 1,
            },
            "hero": {
                "id": "hero", "type": "image", "left": "12%", "top": "49%", "width": "76%", "height": "250px",
                "src": PLACEHOLDER, "showInHero": True, "zIndex": 3,
            },
        },
        "slug": SLUG,
    }


def test_empty_photo_slot_is_editor_only() -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")

            context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("lt-2-6-empty-photo@example.com")
            page.locator("#password").fill("Strong-lt-2-6-empty-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-2-6-empty-123")
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

            page.goto(base + f"/invitations/{created['id']}/editor", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            page.wait_for_selector('#stage .object.image-object[data-id="hero"]', timeout=20000)
            page.wait_for_timeout(600)

            editor = page.evaluate(
                """() => {
                    const object = document.querySelector('#stage .object.image-object[data-id="hero"]');
                    const slot = object?.querySelector(':scope > .ei-image-placeholder');
                    return {
                        marked: object?.getAttribute('data-image-placeholder'),
                        emptyClass: object?.classList.contains('ei-image-empty'),
                        imgVisibility: object ? getComputedStyle(object.querySelector('img')).visibility : null,
                        src: object?.querySelector('img')?.getAttribute('src'),
                        slots: document.querySelectorAll('#stage .ei-image-placeholder').length,
                        label: slot?.querySelector('.ei-image-placeholder-label')?.textContent,
                        href: slot?.querySelector('use')?.getAttribute('href'),
                    };
                }"""
            )
            assert editor["marked"] == "true" and editor["emptyClass"] is True, editor
            assert editor["imgVisibility"] == "hidden", editor
            assert editor["src"] == PLACEHOLDER, editor
            assert editor["slots"] == 1 and editor["label"] == "Add photo", editor
            assert editor["href"].endswith("#i-image"), editor

            svg = page.evaluate("async () => (await EInviteExportQuality.export.svg()).svg")
            assert "Add photo" not in svg
            assert "ei-image-placeholder" not in svg
            assert 'data-id="hero"' in svg, "the hero object must still be in the export snapshot"

            # Replacing the image clears the editor-only state through the observer.
            page.evaluate(
                """() => {
                    const object = document.querySelector('#stage .object.image-object[data-id="hero"]');
                    object.dataset.assetId = 'lt-2-6-photo';
                    object.querySelector('img').src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lY4fWQAAAABJRU5ErkJggg==';
                }"""
            )
            page.wait_for_function(
                """() => {
                    const object = document.querySelector('#stage .object.image-object[data-id="hero"]');
                    return !object.classList.contains('ei-image-empty')
                        && !object.querySelector('.ei-image-placeholder')
                        && object.getAttribute('data-image-placeholder') === null;
                }""",
                timeout=5000,
            )

            page.goto(base + public_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#publicRoot", timeout=20000)
            public = page.content()
            assert "Add photo" not in public
            assert "ei-image-placeholder" not in public
            assert "ei-image-empty" not in public

            assert not errors, errors
            context.close()
            browser.close()
