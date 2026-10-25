#!/usr/bin/env python3
"""LT-3.2: the public share panel exposes Telegram, WhatsApp, Messenger and Facebook,
never leaks the guest token, and stays inside the viewport at 375 and 1440."""
from __future__ import annotations
import os
from pathlib import Path

import pytest

from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-3-2-share"


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "Share panel test",
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


def _open_share(page, base: str, url: str):
    page.goto(base + url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("#shareInvitation", timeout=20000)
    cover = page.locator("#openCover")
    if cover.count():
        cover.click()
        page.wait_for_selector("#openCover", state="hidden", timeout=5000)
    page.locator("#shareInvitation").click()
    page.wait_for_selector("#publicSharePanel", state="visible")


def test_share_panel_targets_and_viewport():
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

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("lt-3-2-share@example.com")
            page.locator("#password").fill("Strong-lt-3-2-share-123")
            page.locator("#registerConfirmPassword").fill("Strong-lt-3-2-share-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            created = page.evaluate(
                """async documentModel => {
                    const response = await fetch('/api/invitations', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({slug: documentModel.slug, document: documentModel})
                    });
                    if (!response.ok) throw Error(await response.text());
                    return response.json();
                }""",
                _document(),
            )
            invitation_id = created["id"]
            published = page.evaluate(                    """async ([id, documentModel]) => {
                        const response = await fetch('/api/invitations/' + id + '/publish', {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({document: documentModel, expectedRevision: null})
                        });
                        const body = await response.json().catch(() => ({}));
                        return {ok: response.ok, status: response.status, body};
                    }""",
                    [invitation_id, _document()],
                )
            assert published["ok"], published
            public_url = published["body"]["url"]

            page.set_viewport_size({"width": 375, "height": 812})
            _open_share(page, base, public_url)

            panel = page.locator("#publicSharePanel")
            assert panel.is_visible()
            assert panel.get_attribute("role") == "dialog"
            assert panel.get_attribute("aria-modal") == "false"
            assert page.locator("#shareInvitation").get_attribute("aria-expanded") == "true"

            hrefs = page.eval_on_selector_all(
                "#publicSharePanel a[href]",
                "nodes => nodes.map(node => node.getAttribute('href'))",
            )
            joined = "\n".join(hrefs or [])
            assert "t.me/share/url" in joined
            assert "wa.me/?text=" in joined
            assert "facebook.com/sharer/sharer.php" in joined
            assert "fb-messenger://share?link=" in joined
            from urllib.parse import unquote

            for href in hrefs or []:
                decoded = unquote(href)
                assert base in decoded, decoded
                assert "g=" not in decoded and "guest=" not in decoded, decoded

            # Messenger is a mobile deep link. On a fine-pointer desktop the panel
            # copies the sanitised public link instead of leaving a dead control.
            before = page.url
            page.locator("#publicSharePanel [data-messenger]").click()
            page.wait_for_timeout(40)
            status = (page.locator("#publicSharePanel [data-share-status]").text_content() or "").strip()
            assert status, "the desktop Messenger fallback must explain what happened"
            assert page.url == before, (before, page.url)

            for action in ("data-copy", "data-message", "data-social", "data-qr"):
                control = page.locator(f"#publicSharePanel [{action}]")
                assert control.count() == 1, action
                assert control.is_visible(), action

            width = page.evaluate("innerWidth")
            doc_width = page.evaluate("document.documentElement.scrollWidth")
            box = panel.bounding_box()
            assert doc_width <= width + 1, (doc_width, width)
            assert box is not None and box["x"] >= 0 and box["x"] + box["width"] <= width + 1, box
            if capture:
                page.screenshot(path=str(capture / "share-panel-375.png"), full_page=False)

            # Same panel in Khmer mode: the new strings must fall back cleanly and
            # the panel must stay inside 375 while the language switch re-renders.
            page.locator("#publicSharePanel [data-close]").click()
            page.evaluate("document.querySelector('[data-guest-lang-proxy=\"km\"]')?.click()")
            page.wait_for_timeout(250)
            assert page.evaluate("document.documentElement.lang") == "km"
            assert page.locator('[data-guest-lang-proxy="km"]').get_attribute("aria-pressed") == "true"
            assert page.locator('[data-guest-lang-proxy="en"]').get_attribute("aria-pressed") == "false"
            page.locator("#shareInvitation").click()
            page.wait_for_selector("#publicSharePanel", state="visible")
            assert page.locator("#publicSharePanel").is_visible()
            assert page.locator("#publicSharePanel [data-messenger]").count() == 1
            km_width = page.evaluate("document.documentElement.scrollWidth")
            assert km_width <= width + 1, (km_width, width)
            if capture:
                page.screenshot(path=str(capture / "share-panel-375-km.png"), full_page=False)

            page.set_viewport_size({"width": 1440, "height": 900})
            page.reload(wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#shareInvitation", timeout=20000)
            cover = page.locator("#openCover")
            if cover.count():
                cover.click()
                page.wait_for_selector("#openCover", state="hidden", timeout=5000)
            page.locator("#shareInvitation").click()
            page.wait_for_selector("#publicSharePanel", state="visible")
            width = page.evaluate("innerWidth")
            doc_width = page.evaluate("document.documentElement.scrollWidth")
            assert doc_width <= width + 1, (doc_width, width)
            if capture:
                page.screenshot(path=str(capture / "share-panel-1440.png"), full_page=False)

            page.close()
            browser.close()
    assert not errors, errors
