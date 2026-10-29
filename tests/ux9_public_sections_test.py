"""UX-9 — the public page never loses content to a hidden reveal state, and
never prints a heading for a section that has nothing to show.

Two defects are covered:

1. `.guest .reveal` started at `opacity: 0` and relied on the fadeUp animation to
   become visible. A section animation preset of "None" writes `animation:none`
   inline, which wins over the stylesheet and left the whole section invisible.
   The keyframes supply their own `opacity: 0` frame, so the element no longer
   needs a hidden initial state.
2. The schedule and venue sections rendered their headings whenever the toggle
   was on, even with no rows and no venue, leaving blank heading-only blocks.
"""
from __future__ import annotations

import pytest

from browser_runtime import launch_chromium

IO_STUB = """window.IntersectionObserver = class {
  constructor(callback) { this.callback = callback; }
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
};"""

CSRF_HEADERS = """() => {
    const match = document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]*)/);
    return match ? {'X-CSRF-Token': decodeURIComponent(match[1])} : {};
}"""


def _document(slug: str, *, venue: str, schedule: list[dict], animations: dict | None = None) -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {"names": "Sokha & Dara", "date": "2029-12-27", "time": "16:00", "venue": venue, "message": "You are invited."},
        "settings": {
            "rsvpEnabled": False,
            "wishesEnabled": False,
            "scheduleEnabled": True,
            "venueEnabled": True,
            "galleryEnabled": False,
            "countdownEnabled": False,
            "musicEnabled": False,
            "openingEnabled": False,
            "contactEnabled": False,
            "showMusicControl": False,
        },
        "languageMode": "en",
        "dateFormat": "gregorian",
        "accent": "#9d4555",
        "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
        "sectionOrder": ["schedule", "venue"],
        "schedule": schedule,
        "venues": [],
        "events": [],
        "customBlocks": [],
        "designPages": [],
        "objects": {},
        "sectionAnimations": animations or {"hero": {"preset": "fade-up", "duration": 300}},
        "slug": slug,
    }


def _publish(page, base: str, document: dict) -> str:
    created = page.evaluate(
        """async ([documentModel, token]) => {
            const response = await fetch('/api/invitations', {
                method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                body: JSON.stringify({slug: documentModel.slug, document: documentModel})
            });
            if (!response.ok) throw Error(await response.text());
            return response.json();
        }""",
        [document, page.evaluate(CSRF_HEADERS)],
    )
    published = page.evaluate(
        """async ([id, documentModel, token]) => {
            const response = await fetch('/api/invitations/' + id + '/publish', {
                method: 'POST', headers: {'Content-Type': 'application/json', ...token},
                body: JSON.stringify({document: documentModel})
            });
            const body = await response.json().catch(() => ({}));
            if (!response.ok) throw Error(JSON.stringify(body));
            return body.url;
        }""",
        [created["id"], document, page.evaluate(CSRF_HEADERS)],
    )
    return base + published


def test_public_sections_stay_visible_and_drop_empty_headings() -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api")
    from v14_test_utils import app_server

    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright.sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                pytest.skip(f"Chromium unavailable: {exc}")

            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("ux9-public-sections@example.com")
            page.locator("#password").fill("Strong-ux9-sections-123")
            page.locator("#registerConfirmPassword").fill("Strong-ux9-sections-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            empty_url = _publish(page, base, _document("ux9-empty-sections", venue="", schedule=[]))
            filled_url = _publish(
                page,
                base,
                _document(
                    "ux9-none-animation",
                    venue="Sokha Phnom Penh Hotel",
                    schedule=[{"time": "16:00", "title": "Reception"}],
                    animations={
                        "hero": {"preset": "fade-up", "duration": 300},
                        "schedule": {"preset": "none"},
                        "venue": {"preset": "none"},
                    },
                ),
            )

            def open_public(url: str, reduced: str = "no-preference", stub_observer: bool = False):
                public_context = browser.new_context(
                    viewport={"width": 1440, "height": 1000},
                    reduced_motion=reduced,
                )
                if stub_observer:
                    public_context.add_init_script(IO_STUB)
                public = public_context.new_page()
                public.on("pageerror", lambda error: errors.append(str(error)))
                public.goto(url, wait_until="domcontentloaded", timeout=30000)
                public.wait_for_selector(".guest-hero", timeout=20000)
                public.wait_for_timeout(900)
                return public_context, public

            # 1. Empty schedule and venue: no headings, no heading-only blocks.
            empty_context, empty_page = open_public(empty_url)
            assert empty_page.locator(".schedule-section").count() == 0
            assert empty_page.locator(".venue-section").count() == 0
            assert "Schedule" not in empty_page.locator("#publicRoot h2").all_inner_texts()
            assert "Venue" not in empty_page.locator("#publicRoot h2").all_inner_texts()
            empty_context.close()

            # 2. Animation preset "None": content stays visible, not stranded at opacity 0.
            none_context, none_page = open_public(filled_url)
            measured = none_page.evaluate(
                """() => {
                    const section = selector => {
                        const node = document.querySelector(selector);
                        if (!node) return null;
                        const style = getComputedStyle(node);
                        return {opacity: style.opacity, visibility: style.visibility, animationName: style.animationName,
                                text: (node.textContent || '').replace(/\\s+/g, ' ').trim()};
                    };
                    return {schedule: section('.schedule-section'), venue: section('.venue-section')};
                }"""
            )
            assert measured["schedule"] is not None and measured["venue"] is not None, measured
            for name in ("schedule", "venue"):
                assert measured[name]["opacity"] == "1", measured[name]
                assert measured[name]["visibility"] == "visible", measured[name]
                assert measured[name]["animationName"] == "none", measured[name]
            assert "Reception" in measured["schedule"]["text"], measured["schedule"]
            assert "Sokha Phnom Penh Hotel" in measured["venue"]["text"], measured["venue"]
            none_context.close()

            # 3. Reduced motion with an IntersectionObserver that never fires: still visible
            #    before any scroll, so no section depends on observer callbacks.
            reduced_context, reduced_page = open_public(filled_url, reduced="reduce", stub_observer=True)
            reduced = reduced_page.evaluate(
                """() => [...document.querySelectorAll('.schedule-section, .venue-section')].map(section => {
                    const style = getComputedStyle(section);
                    return {cls: section.className, opacity: style.opacity, visibility: style.visibility,
                            top: Math.round(section.getBoundingClientRect().top)};
                })"""
            )
            assert len(reduced) == 2, reduced
            assert all(item["opacity"] == "1" and item["visibility"] == "visible" for item in reduced), reduced
            assert reduced_page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches") is True
            reduced_context.close()

            assert not errors, errors
            context.close()
            browser.close()
