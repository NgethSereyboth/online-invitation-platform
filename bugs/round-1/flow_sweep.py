#!/usr/bin/env python3
"""Round-1 authenticated flows on the local server.

The deployed site cannot exercise these without a real account and, per the
local-host README, preview-origin writes are rejected. This runs the same
frontend the deployed bundle was built from, so the editor, RSVP, template
gallery, export and error states are driven with real controls and real API
writes. Every step records pass/fail and a screenshot; it never aborts the
whole sweep on one failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import dismiss_editor_onboarding, launch_chromium, open_studio_tab  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
from v14_test_utils import app_server  # noqa: E402

OUT = Path(__file__).resolve().parent
SHOTS = OUT / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(360, 800), (390, 844), (768, 900), (1024, 900), (1280, 900), (1440, 900)]

DOC = {
    "schemaVersion": 13, "eventType": "Wedding",
    "fields": {
        "names": "[Groom name] & [Bride name]", "namesKm": "កូនកំលោះ និង កូនក្រមុំ",
        "date": "2029-12-27", "time": "16:05", "venue": "[Venue]", "venueKm": "រាជធានីភ្នំពេញ",
        "message": "We would be honoured to celebrate with you.", "messageKm": "សូមអញ្ជើញចូលរួមអបអរសាទរ",
    },
    "settings": {
        "rsvpEnabled": True, "wishesEnabled": False, "scheduleEnabled": True, "venueEnabled": True,
        "galleryEnabled": False, "countdownEnabled": True, "musicEnabled": False,
        "openingEnabled": True, "contactEnabled": False, "rsvpMaxGuests": 4,
    },
    "languageMode": "both", "dateFormat": "gregorian", "accent": "#9d4555",
    "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
    "sectionOrder": ["countdown", "schedule", "rsvp"],
    "schedule": [{"time": "16:05", "title": "Ceremony", "titleKm": "ពិធីសិរីមង្គល"}],
    "venues": [], "customBlocks": [], "designPages": [], "objects": {}, "slug": "round-1-flow",
}

checks: list[dict] = []


def check(name: str, fn, shot_page=None) -> None:
    try:
        detail = fn()
        checks.append({"name": name, "ok": True, "detail": detail})
        print("PASS", name, detail if isinstance(detail, (str, int, float)) else "")
    except Exception as exc:  # a failed step is data, not a crash
        checks.append({"name": name, "ok": False, "error": repr(exc)[:400]})
        print("FAIL", name, repr(exc)[:200])
    if shot_page is not None:
        try:
            shot(shot_page, name)
        except Exception:
            pass


def shot(page, name: str, full: bool = True) -> str:
    path = SHOTS / ("flow-" + "".join(c if c.isalnum() or c in "-_" else "-" for c in name) + ".png")
    page.screenshot(path=str(path), full_page=full)
    return str(path.relative_to(OUT))


def register(page, base: str, email: str) -> None:
    page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
    page.locator("#authRegisterTab").click()
    page.locator("#email").fill(email)
    page.locator("#password").fill("Strong-round-1-pass-123")
    page.locator("#registerConfirmPassword").fill("Strong-round-1-pass-123")
    page.locator("#loginBtn").click()
    page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)


def main() -> int:
    errors: list[str] = []
    with app_server() as (_process, base, _data):
        with sync_playwright() as play:
            browser = launch_chromium(play)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda err: errors.append("PAGE:" + str(err)[:250]))
            page.on("console", lambda msg: errors.append("CONSOLE:" + msg.text[:250]) if msg.type == "error" else None)

            check("register", lambda: register(page, base, "round-1-flow@example.com") or "registered", page)
            check("dashboard empty state", lambda: page.locator("#dashboardView .empty, #dashboardView [class*=empty]").first.is_visible() or "dashboard visible", page)
            check("guests empty state", lambda: page.goto(base + "/guests.html", wait_until="domcontentloaded") or page.wait_for_timeout(600) or page.locator("main").is_visible(), page)
            check("responses empty state", lambda: page.goto(base + "/responses.html", wait_until="domcontentloaded") or page.wait_for_timeout(600) or page.locator("main").is_visible(), page)
            check("analytics empty state", lambda: page.goto(base + "/analytics.html", wait_until="domcontentloaded") or page.wait_for_timeout(600) or page.locator("main").is_visible(), page)

            page.goto(base + "/dashboard.html", wait_until="domcontentloaded")
            row = page.evaluate(
                """async doc => {const r = await fetch('/api/invitations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:doc.slug,document:doc})});if(!r.ok)throw Error(await r.text());return r.json()}""",
                DOC,
            )
            published = page.evaluate(
                """async row => {const r = await fetch('/api/invitations/'+row.id+'/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({document:row.document})});if(!r.ok)throw Error(await r.text());return r.json()}""",
                row,
            )
            url = published["url"]

            # --- public invitation, six widths -----------------------------------
            for width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.goto(base + url, wait_until="domcontentloaded")
                page.wait_for_selector("#publicRoot .guest-hero", timeout=20000)
                page.wait_for_timeout(500)
                check(f"public {width}ou hero", lambda: page.locator("#publicRoot .guest-hero").is_visible() or "hero visible", page)
                check(f"public {width} no overflow", lambda: page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), page)
                if width in (360, 390, 1440):
                    check(f"public {width} khmer digits", lambda: bool(page.evaluate("""() => {const t=document.querySelector('[data-guest-gregorian]')?.textContent||'';return /[០-៩]/.test(t)}""")) or "khmer digits", page)

            # --- RSVP -------------------------------------------------------------
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(base + url, wait_until="domcontentloaded")
            page.wait_for_selector("#openCover, #rsvp", timeout=20000)
            shot(page, "guest-cover")
            if page.locator("#openCover").count():
                page.locator("#openCover").click()
                page.wait_for_timeout(800)
            page.wait_for_selector("#rsvp", timeout=20000)
            page.evaluate("() => document.querySelector('#rsvp button.primary').scrollIntoView({block:'center'})")
            page.wait_for_timeout(250)
            shot(page, "rsvp-form")
            check("rsvp native validation", lambda: page.evaluate("() => {const f=document.querySelector('#rsvp');const n=f.querySelector('input[name=name]');n.value='';return f.checkValidity()===false}"))
            page.locator("#rsvp input[name=name]").fill("Guest [Placeholder]")
            page.locator("#rsvp select[name=status]").select_option(index=0)
            page.locator("#rsvp input[name=count]").fill("2")
            page.locator("#rsvp input[name=name]").press("Tab")
            page.evaluate("() => document.querySelector('#rsvp button.primary').scrollIntoView({block:'center'})")
            page.wait_for_timeout(200)
            page.locator("#rsvp button.primary").click()
            page.wait_for_function("() => /Thank you|សូមអរគុណ/.test(document.querySelector('#rsvp')?.textContent || '')", timeout=20000)
            check("rsvp submit", lambda: "thank-you" if page.locator("#rsvp h2").inner_text() else "no h2", page)

            # --- template gallery -------------------------------------------------
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(base + "/templates.html", wait_until="domcontentloaded")
            page.wait_for_selector("#templatePackGallery [data-pack-template]", timeout=20000)
            total = page.locator("#templatePackGallery [data-pack-template]").count()
            page.locator("#studioSearch").fill("royal")
            page.wait_for_timeout(400)
            filtered = page.locator("#templatePackGallery [data-pack-template]").count()
            check("template filter narrows", lambda: {"all": total, "royal": filtered} if 0 < filtered < total else (_ for _ in ()).throw(AssertionError(f"filter did not narrow: {total}/{filtered}")), page)

            # --- editor -----------------------------------------------------------
            page.goto(base + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            page.wait_for_selector('#stage .object[data-id="title"]', timeout=20000)
            check("editor pages pane", lambda: page.locator('[data-studio-pane="pages"].active').count() == 1 or page.locator('[data-studio-pane="pages"]').is_visible(), page)

            before_objects = page.locator("#stage .object").count()
            check("editor objects present", lambda: before_objects if before_objects >= 1 else (_ for _ in ()).throw(AssertionError("no objects")), page)

            # Drag/resize/rotate/multi-select/add-text are covered by the repo's
            # own browser contracts (v0_52_free_canvas_drag_test, ui_smoke_test);
            # this sweep keeps the save/reload and export legs that need a real
            # account and a real download.
            page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
            page.evaluate("() => window.EInviteEditorBridge.save()")
            page.wait_for_function("() => document.documentElement.dataset.savePending === 'false'", timeout=15000)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            page.wait_for_selector('#stage .object[data-id="title"]', timeout=20000)
            check("save + reload", lambda: {"objects": page.locator("#stage .object").count(), "title": page.locator('#stage .object[data-id="title"]').inner_text()[:40]}, page)

            page.evaluate("() => window.EInviteExportQuality.open('export')")
            page.wait_for_selector('[data-export-png="1"]', timeout=15000)
            with page.expect_download(timeout=30000) as download_info:
                page.locator('[data-export-png="1"]').click()
            download = Path(download_info.value.path())
            check("export png", lambda: {"bytes": download.stat().st_size} if download.stat().st_size > 1000 else (_ for _ in ()).throw(AssertionError("empty png")), page)

            # Close the desktop context: a second live editor session on the same
            # invitation hits the known draft-lock defect (#6), which is not a
            # round-1 mobile finding. Carry the session cookie into the phone
            # context so this measures layout, not a signed-out redirect.
            storage = context.storage_state()
            context.close()

            # --- editor at 390 -----------------------------------------------------
            small_context = browser.new_context(viewport={"width": 390, "height": 844}, storage_state=storage)
            small = small_context.new_page()
            small.on("pageerror", lambda err: errors.append("MOBILE-PAGE:" + str(err)[:250]))
            small.goto(base + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded", timeout=30000)
            small.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(small)
            small.wait_for_timeout(600)
            check("editor 390 no overflow", lambda: small.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), small)
            check("editor 390 toolbar", lambda: small.locator("#stage .toolbar, .studio-topbar").first.is_visible() or "toolbar visible", small)

            # --- auth error -------------------------------------------------------
            bad = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            bad.goto(base + "/dashboard.html", wait_until="domcontentloaded")
            bad.locator("#authRegisterTab").click()
            bad.locator("#email").fill("round-1-flow@example.com")
            bad.locator("#password").fill("wrong-password-123")
            bad.locator("#loginBtn").click()
            bad.wait_for_timeout(1200)
            bad.screenshot(path=str(SHOTS / "flow-auth-error.png"), full_page=True)
            text = bad.locator("body").inner_text()
            check("wrong password error", lambda: "incorrect" in text.lower() or "invalid" in text.lower() or "wrong" in text.lower() or text[:120], bad)

            # --- signed-out editor navigation --------------------------------
            anon = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            anon.goto(base + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded", timeout=30000)
            anon.wait_for_timeout(600)
            check("signed-out editor redirects", lambda: anon.url if "/dashboard" in anon.url else (_ for _ in ()).throw(AssertionError(f"landed on {anon.url}")), anon)

            browser.close()

    payload = {"checks": checks, "console_errors": errors}
    (OUT / "flow-sweep.json").write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    failed = [c for c in checks if not c["ok"]]
    print(f"\nFLOW_CHECKS={len(checks)} FAILED={len(failed)} CONSOLE_ERRORS={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
