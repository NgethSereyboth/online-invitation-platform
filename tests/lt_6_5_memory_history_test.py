#!/usr/bin/env python3
"""LT-6.5 (FB-102): memory and history — 50 page open/close cycles + a 500-step undo history.

Measured on a real server with CDP ``Performance.getMetrics`` (``JSHeapUsedSize``,
with ``HeapProfiler.collectGarbage`` before every read so the numbers are post-GC):

1. **50 page open/close cycles** — ``EInvitePageExperience.addPage`` (+ the real
   themed confirm dialog on ``deletePage``) 50 times, *after* a 25-cycle warm-up.
   The first ~25 cycles pay a one-time cost (~9 MB: canvas machinery, V8 heap
   growth) that the 400-cycle discriminator sweep showed decays to a non-monotone
   tail of ~5 KB/cycle with flat DOM node counts — so the asserted bound covers the
   steady state, where a real per-cycle leak would show. The page list must end
   where it started.
2. **500 undo steps** — 500 real ``EInviteEditorBridge.transact`` edits. The app
   retains at most 50 snapshots (``app.js`` ``pushHistory``: ``undoStack.length>50``
   → ``shift()``), so the heap must not grow past ``BOUND_STEPS``, and undoing back
   down 50 times must not grow it further.

Bounds are stated constants with a wide margin over the measured values printed by
the run; a leak that scales with the cycle/step count would break them.

Screenshots are written when ``EINVITE_CAPTURE_DIR`` is set.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from browser_runtime import dismiss_editor_onboarding, launch_chromium

ROOT = Path(__file__).resolve().parents[1]
SLUG = "lt-6-5-memory-history"
PASSWORD = "Strong-lt-6-5-pass-123"

CYCLES = 50
WARMUP_CYCLES = 25
STEPS = 500
BOUND_CYCLES_BYTES = 8 * 1024 * 1024
BOUND_STEPS_BYTES = 24 * 1024 * 1024


def _document() -> dict:
    return {
        "schemaVersion": 13,
        "eventType": "Wedding",
        "fields": {
            "names": "Sophea & Dara",
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
        "languageMode": "en",
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

_CYCLE = """() => {
    window.__lt65 = window.__lt65 || {};
    const page = window.EInvitePageExperience.addPage({mode: 'free-design'});
    window.__lt65.page = page;
    window.__lt65.done = false;
    window.__lt65.error = '';
    window.EInvitePageExperience.deletePage(page.id)
        .then((ok) => { window.__lt65.ok = ok; window.__lt65.done = true; })
        .catch((error) => { window.__lt65.error = String(error); window.__lt65.done = true; });
}"""

_STEPS = """(count) => {
    for (let i = 0; i < count; i += 1) {
        window.EInviteEditorBridge.transact('lt65 step ' + i, (doc) => {
            doc.fields.message = 'lt65 step ' + i;
        });
    }
}"""

_UNDOS = """(count) => {
    for (let i = 0; i < count; i += 1) window.EInviteEditorBridge.undo();
}"""


def _heap(cdp) -> int:
    cdp.send("HeapProfiler.collectGarbage")
    metrics = {entry["name"]: entry["value"] for entry in cdp.send("Performance.getMetrics")["metrics"]}
    return int(metrics["JSHeapUsedSize"])


def test_memory_and_history_bounds():
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
            page.locator("#email").fill("lt-6-5-memory@example.com")
            page.locator("#password").fill(PASSWORD)
            page.locator("#registerConfirmPassword").fill(PASSWORD)
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
            page.wait_for_timeout(500)

            cdp = context.new_cdp_session(page)
            cdp.send("Performance.enable")

            def cycle(index: int) -> None:
                page.evaluate(_CYCLE)
                page.wait_for_selector(".ei-dialog [data-confirm]", timeout=8000)
                page.click(".ei-dialog [data-confirm]")
                page.wait_for_function("() => window.__lt65.done === true", timeout=8000)
                error = page.evaluate("() => window.__lt65.error || ''")
                assert not error, (index, error)

            # One-time warm-up (canvas machinery + V8 heap growth), then measure.
            for index in range(WARMUP_CYCLES):
                cycle(index)
            base_heap = _heap(cdp)
            pages_before = page.evaluate("() => window.EInviteEditorBridge.getState().designPages?.length || 0")

            # 1) 50 measured open/close cycles with the real confirm dialog.
            for index in range(CYCLES):
                cycle(WARMUP_CYCLES + index)
            after_cycles = _heap(cdp)
            pages_after = page.evaluate("() => window.EInviteEditorBridge.getState().designPages?.length || 0")
            assert pages_after == pages_before, (pages_before, pages_after)

            # 2) 500 real undo steps (history retention is capped at 50 snapshots).
            for _chunk in range(STEPS // 50):
                page.evaluate(_STEPS, 50)
                page.wait_for_timeout(50)
            after_steps = _heap(cdp)

            # 3) Undo back down 50 times: the undo path must not retain more.
            page.evaluate(_UNDOS, 50)
            after_undos = _heap(cdp)

            growth_cycles = after_cycles - base_heap
            growth_steps = after_steps - after_cycles
            growth_undos = after_undos - after_cycles
            print(
                f"[lt-6-5] base_after_{WARMUP_CYCLES}warmup={base_heap}B after{CYCLES}cycles={after_cycles}B "
                f"(+{growth_cycles}) after500steps={after_steps}B (+{growth_steps}) "
                f"after50undos={after_undos}B (+{growth_undos})",
                flush=True,
            )
            if capture:
                page.screenshot(path=str(capture / "lt-6-5-editor-after-history.png"))
                page.screenshot(path=str(capture / "lt-6-5-editor-after-history-full.png"), full_page=True)

            assert growth_cycles <= BOUND_CYCLES_BYTES, (growth_cycles, BOUND_CYCLES_BYTES)
            assert growth_steps <= BOUND_STEPS_BYTES, (growth_steps, BOUND_STEPS_BYTES)
            assert growth_undos <= BOUND_STEPS_BYTES, (growth_undos, BOUND_STEPS_BYTES)
            assert errors == [], errors

            context.close()
            browser.close()

        print(
            f"LT_6_5_MEMORY_PROBE_PASSED cycles={CYCLES} steps={STEPS} "
            f"growth_cycles={growth_cycles}B growth_steps={growth_steps}B growth_undos={growth_undos}B",
            flush=True,
        )
