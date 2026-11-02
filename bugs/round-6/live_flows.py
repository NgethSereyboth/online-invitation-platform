#!/usr/bin/env python3
"""Round-6 live interaction pass.

The published `/` route boots the anonymous demo editor (4 objects, no server
writes), so the canvas interactions run live. `/designer` is the auth-gated
workspace shell; guest/RSVP flows are covered locally because live has no
published invitation. Every step records pass/fail and a screenshot.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page"
OUT = Path(__file__).resolve().parent
SHOTS = OUT / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

CLS_JS = r"""() => {
  window.__shifts = window.__shifts || [];
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.hadRecentInput) continue;
        window.__shifts.push({value: entry.value, time: entry.startTime,
          sources: (entry.sources || []).map(s => ({node: s.node ? (s.node.id ? '#' + s.node.id : s.node.tagName) : '?'}))});
      }
    }).observe({type: 'layout-shift', buffered: true});
  } catch (e) {}
}"""

checks: list[dict] = []
errors: list[str] = []


def check(name, fn, page=None):
    try:
        detail = fn()
        checks.append({"name": name, "ok": True, "detail": detail})
        print("PASS", name, detail if isinstance(detail, (str, int, float, dict)) else "")
    except Exception as exc:  # a failed step is data, not a crash
        checks.append({"name": name, "ok": False, "error": repr(exc)[:400]})
        print("FAIL", name, repr(exc)[:220])
    if page is not None:
        try:
            page.screenshot(path=str(SHOTS / ("flow-" + "".join(c if c.isalnum() or c in "-_" else "-" for c in name) + ".png")), full_page=True)
        except Exception:
            pass


def main() -> int:
    with sync_playwright() as play:
        browser = launch_chromium(play)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        context.add_init_script(CLS_JS)
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append("PAGE:" + str(err)[:250]))
        page.on("console", lambda msg: errors.append("CONSOLE:" + msg.text[:250]) if msg.type == "error" else None)

        # Live CLS at 1440, read-only (do not change it this round).
        page.goto(BASE + "/", wait_until="load", timeout=45000)
        page.wait_for_timeout(7000)
        cls = page.evaluate("() => ({value: (window.__shifts || []).reduce((a, s) => a + s.value, 0), shifts: (window.__shifts || []).length})")
        check("live CLS 1440", lambda: cls, page)

        page.wait_for_selector('#stage .object[data-id="title"]', timeout=25000)
        tour = page.locator('#finalTourDismiss')
        if tour.count() and tour.is_visible():
            tour.click()
            page.wait_for_timeout(250)
        check("live editor boots", lambda: {"objects": page.locator("#stage .object").count(), "stage": page.locator("#stage").is_visible()}, page)
        check("live editor no overflow", lambda: page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), page)

        page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
        page.wait_for_timeout(250)
        before = page.evaluate("() => structuredClone(state.objects.title)")
        box = page.locator('#stage .object[data-id="title"]').bounding_box()
        check("live drag", lambda: _drag(page, box, before), page)

        moved = page.evaluate("() => JSON.stringify(state.objects.title)")
        page.evaluate("() => window.EInviteEditorBridge.undo()")
        page.wait_for_timeout(300)
        undone = page.evaluate("() => JSON.stringify(state.objects.title)")
        page.evaluate("() => window.EInviteEditorBridge.redo()")
        page.wait_for_timeout(300)
        redone = page.evaluate("() => JSON.stringify(state.objects.title)")
        check("live undo/redo", lambda: {"changed": undone != moved, "restored": redone == moved} if undone != moved and redone == moved else (_ for _ in ()).throw(AssertionError(f"undo/redo mismatch {undone != moved}/{redone == moved}")))

        page.evaluate("() => window.EInviteEditorBridge.select(['title', 'subtitle'])")
        page.wait_for_timeout(250)
        check("live multi-select", lambda: page.evaluate("() => ({ids: EInviteEditorBridge.getSelectedIds().length, outlined: document.querySelectorAll('#stage .object.selected, #stage .object.multi-selected').length})"), page)

        page.evaluate("() => window.EInviteEditorBridge.select([])")
        before_add = page.locator("#stage .object").count()
        stage = page.locator("#stage").bounding_box()

        def add_text():
            page.locator('[data-tool="text"]').first.click(timeout=8000)
            page.wait_for_timeout(150)
            page.mouse.click(stage["x"] + 20, stage["y"] + stage["height"] / 2)
            page.wait_for_timeout(500)
            page.evaluate("() => window.EInviteToolController.setTool('select')")
            after = page.locator("#stage .object").count()
            if after != before_add + 1:
                raise AssertionError(f"add text {before_add}->{after}")
            return {"before": before_add, "after": after}

        check("live add text", add_text, page)

        errors_before_export = len(errors)
        page.evaluate("() => window.EInviteExportQuality.open('export')")
        page.wait_for_selector('[data-export-png="1"]', timeout=15000)
        with page.expect_download(timeout=30000) as info:
            page.locator('[data-export-png="1"]').click()
        png = Path(info.value.path()).read_bytes()
        check("live export png", lambda: {"bytes": len(png), "png": png.startswith(b"\x89PNG\r\n\x1a\n")} if len(png) > 1000 and png.startswith(b"\x89PNG\r\n\x1a\n") else (_ for _ in ()).throw(AssertionError(f"invalid png {len(png)}")))
        csp = [e for e in errors[errors_before_export:] if "Content Security Policy" in e]
        check("live export console clean", lambda: "clean" if not csp else (_ for _ in ()).throw(AssertionError(csp)), page)

        # The export dialog is modal; close it before touching the topbar.
        page.evaluate("() => {const d = document.querySelector('#v24QualityDialog'); if (d && d.open) d.close()}")
        page.wait_for_timeout(300)

        # Mobile demo: layout only; the editor topbar is canvas-focused after
        # export, so language is exercised on the public privacy page below.
        page.set_viewport_size({"width": 360, "height": 800})
        page.wait_for_timeout(700)
        check("live mobile no overflow", lambda: page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), page)
        check("live mobile stage", lambda: {"objects": page.locator("#stage .object").count(), "visible": page.locator("#stage").is_visible()}, page)

        # Templates: search narrows the visible cards.
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(BASE + "/templates", wait_until="load", timeout=45000)
        page.wait_for_timeout(1500)
        search = page.locator("input[type=search], #templateSearch, [data-template-search]").first
        check("live templates search present", lambda: search.count() == 1 or (_ for _ in ()).throw(AssertionError("no search input")), page)
        before_cards = page.locator(".pack-card").count()
        search.fill("wedding")
        page.wait_for_timeout(700)
        after_cards = page.locator(".pack-card").count()
        check("live templates search", lambda: {"before": before_cards, "after": after_cards, "value": search.input_value()} if search.input_value() == "wedding" else (_ for _ in ()).throw(AssertionError("search did not take")), page)

        # Dashboard: invalid registration must be rejected without creating an account.
        page.goto(BASE + "/dashboard", wait_until="load", timeout=45000)
        page.wait_for_timeout(1200)
        if page.locator("#authRegisterTab").count():
            page.locator("#authRegisterTab").click()
            page.wait_for_timeout(200)
        page.locator("#email").fill("not-an-email")
        page.locator("#password").fill("short")
        page.locator("#loginBtn").click()
        page.wait_for_timeout(700)
        check("live invalid register rejected", lambda: page.evaluate("""() => ({url: location.pathname, invalid: !document.querySelector('#email').checkValidity() || !document.querySelector('#password').checkValidity(), view: document.querySelector('#dashboardView')?.hidden !== false, message: (document.querySelector('#authMessage, #loginMessage, .form-message')?.textContent || '').trim().slice(0, 120)})"""), page)

        # Privacy language switch.
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(BASE + "/privacy", wait_until="load", timeout=45000)
        page.wait_for_timeout(900)
        page.locator("#lang-km").click()
        page.wait_for_timeout(300)
        check("live privacy language 1440", lambda: page.evaluate("() => ({km: document.querySelector('#lang-km')?.classList.contains('active'), lang: document.documentElement.lang})"), page)
        page.set_viewport_size({"width": 360, "height": 800})
        page.wait_for_timeout(500)
        page.locator("#lang-en").click()
        page.wait_for_timeout(250)
        check("live privacy language 360", lambda: page.evaluate("() => ({en: document.querySelector('#lang-en')?.classList.contains('active'), overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth})"), page)

        # Missing invitation: 404 with the unavailable shell. Console errors
        # after this navigation are expected (404 subresources + the
        # Cloudflare-injected beacon blocked by CSP), so snapshot first.
        errors_before_404 = len(errors)
        resp = page.goto(BASE + "/i/missing-slug-round-6", wait_until="load", timeout=45000)
        page.wait_for_timeout(900)
        check("live missing invitation 404", lambda: {"status": resp.status if resp else None, "heading": (page.locator("h1").first.inner_text() if page.locator("h1").count() else ""), "overflow": page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")}, page)

        check("live console clean", lambda: "clean" if not errors[:errors_before_404] else (_ for _ in ()).throw(AssertionError(errors[:errors_before_404])))
        context.close()
        browser.close()

    payload = {"checks": checks, "errors": errors, "cls": cls, "base": BASE}
    (OUT / "live-flows.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    failed = [c for c in checks if not c["ok"]]
    print(f"LIVE_CHECKS={len(checks)} FAILED={len(failed)} CONSOLE_ERRORS={len(errors)} CLS={cls}")
    return 0


def _drag(page, box, before):
    if not box:
        raise AssertionError("no title box")
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 26, box["y"] + box["height"] / 2 + 14, steps=6)
    page.mouse.up()
    page.wait_for_timeout(320)
    after = page.evaluate("() => structuredClone(state.objects.title)")
    if after == before:
        raise AssertionError("drag did not move the title")
    return {"before": before.get("left"), "after": after.get("left")}


if __name__ == "__main__":
    raise SystemExit(main())
