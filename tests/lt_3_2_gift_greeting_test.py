#!/usr/bin/env python3
"""LT-3.2 item (8): the display-only gift KHQR section and the sanitised ``?guest=`` greeting.

Drives the real test server (``tests/v14_test_utils.app_server``) with Chromium:

  * the owner uploads a real PNG through ``/assets/raw``; the gift block shows that
    uploaded image, and is absent while the owner toggle is off;
  * the block is display-only — no input, button, form, iframe or link inside it;
  * the server rejects a ``giftQrImage`` outside the raster allowlist and a
    non-boolean ``giftQrEnabled``;
  * ``?guest=<name>`` is strictly sanitised (markup, bidi/zero-width characters,
    over-long values) and falls back to "YOU ARE INVITED" when nothing usable is left;
  * the personalised name never reaches the share URLs;
  * the public page stays inside the viewport at 375 EN, 375 KM and 1440.

The QR fixture is a small generated PNG (96x96, QR-like) written by ``khqr_base64``
below — no Pillow and no third-party download.
"""
from __future__ import annotations
import base64
import os
import struct
import zlib
from pathlib import Path

import pytest

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-3-2-gift"


def khqr_base64() -> str:
    """A deterministic QR-like 96x96 PNG, encoded for the in-page upload."""
    width = height = 96

    def png_chunk(kind: bytes, data: bytes) -> bytes:
        body = struct.pack(">I", len(data)) + kind + data
        return body + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            dark = False
            if 6 <= x < 90 and 6 <= y < 90:
                for fx, fy in ((8, 8), (72, 8), (8, 72)):
                    dx, dy = x - fx, y - fy
                    if 0 <= dx < 16 and 0 <= dy < 16:
                        ring = max(abs(dx - 7.5), abs(dy - 7.5))
                        dark = 2.5 <= ring < 4.5 or 6.5 <= ring < 7.5
                        break
                else:
                    dark = hash((x // 2, y // 2)) % 3 == 0
            row += bytes([0, 0, 0] if dark else [255, 255, 255])
        rows.append(bytes(row))
    raw = b"".join(rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )
    return base64.b64encode(png).decode()


def _document(*, gift_enabled: bool, qr_image: str = "") -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "Gift QR test",
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
        "guestExperience": {
            "giftQrEnabled": gift_enabled,
            "giftQrImage": qr_image,
            "giftQrLabel": "Scan to give",
        },
        "languageMode": "both",
        "dateFormat": "gregorian",
        "accent": "#9d4555",
        "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
        "sectionOrder": ["guest-info", "rsvp"],
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


def _greeting(page):
    """The visible hero greeting, e.g. "DEAR Sokha" (EN) or None when absent."""
    node = page.locator("[data-guest-greeting]")
    return node.first.inner_text().strip() if node.count() else None


def test_gift_qr_toggle_and_sanitised_guest_greeting():
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
            page.locator("#email").fill("lt-3-2-gift@example.com")
            page.locator("#password").fill("Strong-lt-3-2-gift-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-3-2-gift-123")
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
                [_document(gift_enabled=False), page.evaluate(_CSRF_HEADERS)],
            )
            invitation_id = created["id"]

            # The owner flow: upload the KHQR image as a real material, then point the
            # document at the returned platform URL (the same path the Ops panel uses).
            uploaded = page.evaluate(
                """async ([id, encoded, token]) => {
                    const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
                    const response = await fetch('/api/invitations/' + id + '/assets/raw', {
                        method: 'POST',
                        headers: {'Content-Type': 'image/png', 'X-File-Name': 'khqr.png', ...token},
                        body: bytes
                    });
                    const body = await response.json().catch(() => ({}));
                    return {ok: response.ok, status: response.status, body};
                }""",
                [invitation_id, khqr_base64(), page.evaluate(_CSRF_HEADERS)],
            )
            assert uploaded["ok"], uploaded
            qr_url = uploaded["body"]["url"]
            assert qr_url.startswith("/uploads/"), qr_url
            qr_file = qr_url.rsplit("/", 1)[-1]

            def publish(document_model):
                result = page.evaluate(
                    """async ([id, documentModel, token]) => {
                        const response = await fetch('/api/invitations/' + id + '/publish', {
                            method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                            body: JSON.stringify({document: documentModel, expectedRevision: null})
                        });
                        const body = await response.json().catch(() => ({}));
                        return {ok: response.ok, status: response.status, body};
                    }""",
                    [invitation_id, document_model, page.evaluate(_CSRF_HEADERS)],
                )
                assert result["ok"], result
                return result["body"]["url"]

            public_url = publish(_document(gift_enabled=False, qr_image=qr_url))

            # --- Toggle off: the uploaded image is in the document but not shown ----
            _open_page(page, base + public_url + "?guest=Sokha%20Dara")
            assert page.locator("[data-gift-qr]").count() == 0
            assert _greeting(page) == "DEAR Sokha Dara"

            # --- ?guest= sanitising -------------------------------------------------
            _open_page(page, base + public_url + "?guest=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E")
            assert _greeting(page) == "DEAR img src=x onerror=alert(1)"
            assert page.evaluate("document.querySelectorAll('img[onerror]').length") == 0

            _open_page(page, base + public_url + "?guest=%E2%80%AEKhmer%E2%80%AC%E2%80%8B%20Name")
            name = _greeting(page)
            assert name == "DEAR Khmer Name", repr(name)

            _open_page(page, base + public_url + "?guest=" + "A" * 80)
            name = _greeting(page)
            assert name is not None and len(name) == len("DEAR ") + 40, name

            _open_page(page, base + public_url + "?guest=%20%20")
            assert _greeting(page) is None
            assert page.locator(".invite-kicker").first.inner_text().strip() == "YOU ARE INVITED"

            # The personalised name must not ride into any share target.
            _open_page(page, base + public_url + "?guest=Sokha")
            page.locator("#shareInvitation").click()
            page.wait_for_selector("#publicSharePanel", state="visible")
            hrefs = page.eval_on_selector_all(
                "#publicSharePanel a[href]", "nodes => nodes.map(n => n.getAttribute('href'))"
            )
            assert hrefs and all("guest=" not in href for href in hrefs), hrefs

            # --- Toggle on: the uploaded image renders, image-only ------------------
            public_url = publish(_document(gift_enabled=True, qr_image=qr_url))
            page.set_viewport_size({"width": 375, "height": 812})
            _open_page(page, base + public_url + "?guest=Sokha")
            block = page.locator('[data-gift-qr="display-only"]')
            assert block.count() == 1
            assert block.locator("h3").inner_text().strip() == "Scan to give"
            image = block.locator("img")
            assert image.count() == 1 and qr_file in image.get_attribute("src")
            assert "Display only" in (block.inner_text() or "")
            controls = page.eval_on_selector(
                '[data-gift-qr="display-only"]',
                "node => node.querySelectorAll('input,button,form,iframe,textarea,select,a[href]').length",
            )
            assert controls == 0, controls
            block.evaluate("node => node.scrollIntoView({block: 'center'})")
            page.wait_for_function(
                "() => {const img=document.querySelector('[data-gift-qr] img');return img && img.naturalWidth>0}",
                timeout=10000,
            )
            width = page.evaluate("innerWidth")
            assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
            if capture:
                page.screenshot(path=str(capture / "gift-375-en.png"), full_page=False)

            # --- 375 KM: the fixed line is the accepted English fallback -------------
            # Drive the renderer's own switch through the (hidden) topbar proxy. The
            # visible i18n switch delegates to the same renderer since LT-4.1 (FB-92) and
            # has its own test: tests/lt_4_1_language_switch_test.py.
            page.evaluate("document.querySelector('[data-guest-lang-proxy=\"km\"]')?.click()")
            page.wait_for_timeout(250)
            assert page.evaluate("document.documentElement.lang") == "km"
            assert page.evaluate("document.querySelector('#publicRoot').dataset.language") == "km"
            assert block.count() == 1 and block.is_visible()
            assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
            block.evaluate("node => node.scrollIntoView({block: 'center'})")
            if capture:
                page.screenshot(path=str(capture / "gift-375-km.png"), full_page=False)

            # --- 1440 (back to EN) --------------------------------------------------
            page.set_viewport_size({"width": 1440, "height": 900})
            page.evaluate(
                "try{localStorage.removeItem('einvite-guest-language:lt-3-2-gift');"
                "localStorage.removeItem('einvite-lang')}catch{}"
            )
            page.reload(wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#shareInvitation", timeout=20000)
            cover = page.locator("#openCover")
            if cover.count():
                cover.click()
                page.wait_for_selector("#openCover", state="hidden", timeout=5000)
            block = page.locator('[data-gift-qr="display-only"]')
            assert block.count() == 1
            assert page.evaluate("document.documentElement.lang") == "en"
            block.evaluate("node => node.scrollIntoView({block: 'center'})")
            wide = page.evaluate("innerWidth")
            assert page.evaluate("document.documentElement.scrollWidth") <= wide + 1
            if capture:
                page.screenshot(path=str(capture / "gift-1440.png"), full_page=False)

            # --- Server rejects images outside the raster allowlist -----------------
            for index, payload in enumerate(
                (
                    {"giftQrEnabled": True, "giftQrImage": "javascript:alert(1)"},
                    {"giftQrEnabled": True, "giftQrImage": "data:image/svg+xml;base64,PHN2Zy8+"},
                    {"giftQrEnabled": "yes", "giftQrImage": qr_url},
                )
            ):
                document_model = _document(gift_enabled=True)
                document_model["guestExperience"] = dict(payload)
                document_model["slug"] = f"{SLUG}-bad-{index}"
                rejected = page.evaluate(
                    """async ([documentModel, token]) => {
                        const response = await fetch('/api/invitations', {
                            method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                            body: JSON.stringify({slug: documentModel.slug, document: documentModel})
                        });
                        return {ok: response.ok, status: response.status};
                    }""",
                    [document_model, page.evaluate(_CSRF_HEADERS)],
                )
                assert rejected["ok"] is False, (index, rejected)
                assert 400 <= rejected["status"] < 500, (index, rejected)

            page.close()
            browser.close()
    assert not errors, errors
