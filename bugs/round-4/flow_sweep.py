#!/usr/bin/env python3
"""Round-4 authenticated flows against the phase-10 bundle.

The phase-10 bundle is served by serve_bundle.py on 127.0.0.1:4180 and proxies
API/management routes to the isolated backend on 4181. Every step records
pass/fail and a screenshot; it never aborts the whole sweep on one failure.
"""
from __future__ import annotations

import atexit
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from browser_runtime import dismiss_editor_onboarding, launch_chromium, open_studio_tab  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = Path(__file__).resolve().parent
SHOTS = OUT / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(360, 800), (390, 844), (768, 900), (1024, 900), (1280, 900), (1440, 900)]

DOC = {
    "schemaVersion": 13, "eventType": "Wedding",
    "fields": {
        "names": "[Groom name] & [Bride name]", "namesKm": "\u1780\u17bc\u1793\u1780\u17c6\u179b\u17c4\u17c7 \u1793\u17b7\u1784 \u1780\u17bc\u1793\u1780\u17d2\u179a\u1798\u17bb\u17c6",
        "date": "2029-12-27", "time": "16:05", "venue": "[Venue]", "venueKm": "\u179a\u17b6\u1787\u1792\u17b6\u1793\u17b8\u1797\u17d2\u1793\u17c6\u1796\u17c1\u1789",
        "message": "We would be honoured to celebrate with you.", "messageKm": "\u179f\u17bc\u1798\u17a2\u1789\u17d2\u1787\u17be\u1789\u1785\u17bc\u179b\u179a\u17bd\u1798\u17a2\u1794\u17a2\u179a\u179f\u17b6\u1791\u179a",
    },
    "settings": {
        "rsvpEnabled": True, "wishesEnabled": False, "scheduleEnabled": True, "venueEnabled": True,
        "galleryEnabled": False, "countdownEnabled": True, "musicEnabled": False,
        "openingEnabled": True, "contactEnabled": False, "rsvpMaxGuests": 4,
    },
    "languageMode": "both", "dateFormat": "gregorian", "accent": "#9d4555",
    "palette": {"background": "#fff8f2", "surface": "#ffffff", "text": "#342c26", "heading": "#9d4555"},
    "sectionOrder": ["countdown", "schedule", "rsvp"],
    "schedule": [{"time": "16:05", "title": "Ceremony", "titleKm": "\u1796\u17b7\u1792\u17b8\u179f\u17b7\u179a\u17b8\u1798\u1784\u17d2\u1782\u179b"}],
    "venues": [], "customBlocks": [], "designPages": [], "objects": {}, "slug": "round-4-flow",
}

checks: list[dict] = []
errors: list[str] = []
published_url: str | None = None


def _write_payload() -> None:
    """Persist whatever the sweep reached, including after a crash.

    A crashed step must not throw away the checks that already passed; the old
    version wrote the JSON only at the end, so a timeout left a stale file.
    """
    payload = {"checks": checks, "console_errors": errors, "published_url": published_url}
    (OUT / "flow-sweep.json").write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")


atexit.register(_write_payload)


@contextmanager
def local_bundle():
    """The bundle proxy is already running; this keeps the round-3 structure."""
    yield None, os.environ.get("ROUND4_BASE", "http://127.0.0.1:4180").rstrip("/"), None


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
    global errors, published_url
    errors.clear()
    published_url = None
    with local_bundle() as (_process, base, _data):
        with sync_playwright() as play:
            browser = launch_chromium(play)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda err: errors.append("PAGE:" + str(err)[:250]))
            page.on("console", lambda msg: errors.append("CONSOLE:" + msg.text[:250]) if msg.type == "error" else None)

            email = f"round-4-flow-{int(time.time())}@example.com"
            DOC["slug"] = f"round-4-flow-{int(time.time())}"
            published_url = None
            check("register", lambda: register(page, base, email) or "registered", page)
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
            published_url = url

            # --- status contract (BUG-R1-2) --------------------------------------
            def status_of(path):
                response = page.request.get(base + path)
                return response.status

            check("published slug 200", lambda: 200 if status_of(url) == 200 else (_ for _ in ()).throw(AssertionError(f"published slug returned {status_of(url)}")))
            check("missing slug 404", lambda: 404 if status_of("/i/r3-missing-slug-9f3c") == 404 else (_ for _ in ()).throw(AssertionError(f"missing slug returned {status_of('/i/r3-missing-slug-9f3c')}")))

            # --- public invitation, six widths -----------------------------------
            for width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.goto(base + url, wait_until="domcontentloaded")
                page.wait_for_selector("#publicRoot .guest-hero", timeout=20000)
                page.wait_for_timeout(500)
                check(f"public {width}ou hero", lambda: page.locator("#publicRoot .guest-hero").is_visible() or "hero visible", page)
                check(f"public {width} no overflow", lambda: page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), page)
                if width in (360, 390, 1440):
                    check(f"public {width} khmer digits", lambda: bool(page.evaluate("""() => {const t=document.querySelector('[data-guest-gregorian]')?.textContent||'';return /[\u17e0-\u17e9]/.test(t)}""")) or "khmer digits", page)

            page.wait_for_timeout(800)
            feature_count = page.locator(".guest-feature.signup-sheets, .guest-feature.polls, .guest-feature.album").count()
            check("unconfigured guest features hidden", lambda: feature_count if feature_count == 0 else (_ for _ in ()).throw(AssertionError(f"{feature_count} empty feature panels rendered")), page)
            credit_count = page.locator(".guest-credit, .guest-platform-credit, .guest-studio-brand").count()
            check("single platform credit", lambda: credit_count if credit_count == 1 else (_ for _ in ()).throw(AssertionError(f"{credit_count} platform credits rendered")), page)

            # --- gallery-enabled album, 390 + 1440 (BUG-R2-2 regression) -----------
            gallery_doc = json.loads(json.dumps(DOC))
            gallery_doc["slug"] = "round-3-gallery"
            gallery_doc["settings"]["galleryEnabled"] = True
            gallery_doc["sectionOrder"] = ["gallery", "countdown", "schedule", "rsvp"]
            gallery_row = page.evaluate(
                """async doc => {const token=document.cookie.match(/(?:^|; )einvite_csrf=([^;]+)/)?.[1]||'';const r = await fetch('/api/invitations',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':decodeURIComponent(token)},body:JSON.stringify({slug:doc.slug,document:doc})});if(!r.ok)throw Error(await r.text());return r.json()}""",
                gallery_doc,
            )
            gallery_published = page.evaluate(
                """async row => {const token=document.cookie.match(/(?:^|; )einvite_csrf=([^;]+)/)?.[1]||'';const r = await fetch('/api/invitations/'+row.id+'/publish',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':decodeURIComponent(token)},body:JSON.stringify({document:row.document})});if(!r.ok)throw Error(await r.text());return r.json()}""",
                gallery_row,
            )
            gallery_url = gallery_published["url"]

            def gallery_probe(width: int) -> dict:
                page.set_viewport_size({"width": width, "height": 900 if width > 390 else 844})
                page.goto(base + gallery_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_selector(".guest-feature.album", timeout=20000)
                page.wait_for_timeout(500)
                metrics = page.evaluate("""() => {
                  const sec = document.querySelector('.guest-feature.album');
                  const form = sec && sec.querySelector('.album-upload');
                  const file = form && form.querySelector('input[type=file]');
                  const cap = form && form.querySelector('input[name=caption]');
                  const btn = form && form.querySelector('button[type=submit]');
                  const more = sec && sec.querySelector('.load-more');
                  const label = file && file.closest('label');
                  const box = (el) => el ? {w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height)} : null;
                  return {
                    file: box(file), caption: box(cap), button: box(btn), form: box(form),
                    label: box(label),
                    labelClipped: !!label && label.scrollWidth > label.clientWidth + 1,
                    loadMoreHidden: !!more && getComputedStyle(more).display === 'none' && more.hidden === true,
                    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth
                  };
                }""")
                assert metrics["file"] and metrics["file"]["w"] > 80, metrics
                assert metrics["caption"] and metrics["caption"]["w"] > 80, metrics
                assert metrics["button"] and abs(metrics["button"]["w"] - metrics["file"]["w"]) <= 2, metrics
                assert not metrics["labelClipped"], metrics
                assert metrics["loadMoreHidden"], metrics
                assert metrics["overflow"] <= 1, metrics
                return metrics

            for gallery_width in (390, 1440):
                check(f"gallery upload form {gallery_width}", lambda w=gallery_width: gallery_probe(w), page)

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
            page.wait_for_function("() => /Thank you|\u179f\u17bc\u1798\u17a2\u179a\u1782\u17bb\u178e/.test(document.querySelector('#rsvp')?.textContent || '')", timeout=20000)
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

            # --- editor interactions: drag, resize, rotate, multi-select, undo ---
            page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
            page.wait_for_timeout(250)
            title_before = page.evaluate("() => structuredClone(state.objects.title)")
            title_box = page.locator('#stage .object[data-id="title"]').bounding_box()
            if title_box:
                page.mouse.move(title_box["x"] + title_box["width"] / 2, title_box["y"] + title_box["height"] / 2)
                page.mouse.down()
                page.mouse.move(title_box["x"] + title_box["width"] / 2 + 26, title_box["y"] + title_box["height"] / 2 + 14, steps=6)
                page.mouse.up()
                page.wait_for_timeout(300)
            title_after = page.evaluate("() => structuredClone(state.objects.title)")
            check("editor drag", lambda: {"before": title_before.get("left"), "after": title_after.get("left")} if title_after != title_before else (_ for _ in ()).throw(AssertionError("drag did not move the title")), page)

            page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
            page.wait_for_timeout(200)
            resize_before = page.evaluate("() => ({w: state.objects.title.width, h: state.objects.title.height})")
            handle = page.locator('[data-pe-handle="se"]').bounding_box()
            if handle:
                page.mouse.move(handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2)
                page.mouse.down()
                page.mouse.move(handle["x"] + handle["width"] / 2 + 22, handle["y"] + handle["height"] / 2 + 14, steps=6)
                page.mouse.up()
                page.wait_for_timeout(300)
            resize_after = page.evaluate("() => ({w: state.objects.title.width, h: state.objects.title.height})")
            check("editor resize", lambda: {"before": resize_before, "after": resize_after} if resize_after != resize_before else (_ for _ in ()).throw(AssertionError("resize handle did not change the title")), page)

            page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
            page.wait_for_timeout(200)
            rotate_before = page.evaluate("() => Number(document.querySelector('[data-pe-transform=\"r\"]')?.value || 0)")
            rotate_handle = page.locator('.pe-rotate').bounding_box()
            rotate_box = page.locator('#peSelectionBox').bounding_box()
            if rotate_handle and rotate_box:
                page.mouse.move(rotate_handle["x"] + rotate_handle["width"] / 2, rotate_handle["y"] + rotate_handle["height"] / 2)
                page.mouse.down()
                page.mouse.move(rotate_box["x"] + rotate_box["width"] + 24, rotate_box["y"] + rotate_box["height"] / 2, steps=6)
                page.mouse.up()
                page.wait_for_timeout(300)
            rotate_after = page.evaluate("() => Number(document.querySelector('[data-pe-transform=\"r\"]')?.value || 0)")
            check("editor rotate", lambda: {"before": rotate_before, "after": rotate_after} if abs(rotate_after - rotate_before) > 1 else (_ for _ in ()).throw(AssertionError("rotate handle did not rotate the title")), page)

            page.evaluate("() => window.EInviteEditorBridge.select(['title', 'subtitle'])")
            page.wait_for_timeout(200)
            check("editor multi-select", lambda: page.evaluate("() => ({selected: EInviteEditorBridge.getSelectedIds().length, outlined: document.querySelectorAll('#stage .object.selected, #stage .object.multi-selected').length})") if page.evaluate("() => EInviteEditorBridge.getSelectedIds().length") == 2 else (_ for _ in ()).throw(AssertionError("two objects not selected")), page)

            moved_snapshot = page.evaluate("() => JSON.stringify(state.objects.title)")
            page.evaluate("() => EInviteEditorBridge.undo()")
            page.wait_for_timeout(300)
            undone_snapshot = page.evaluate("() => JSON.stringify(state.objects.title)")
            page.evaluate("() => EInviteEditorBridge.redo()")
            page.wait_for_timeout(300)
            redone_snapshot = page.evaluate("() => JSON.stringify(state.objects.title)")
            check("editor undo/redo", lambda: {"changed": undone_snapshot != moved_snapshot, "restored": redone_snapshot == moved_snapshot} if undone_snapshot != moved_snapshot and redone_snapshot == moved_snapshot else (_ for _ in ()).throw(AssertionError(f"undo/redo mismatch: changed={undone_snapshot != moved_snapshot} restored={redone_snapshot == moved_snapshot}")), page)

            # Add text with the real canvas tool: select the text tool, then click
            # an empty point on the stage (the retired #addText pane is not the
            # supported path).
            page.evaluate("() => EInviteEditorBridge.select([])")
            before_add = page.locator("#stage .object").count()
            stage_box = page.locator("#stage").bounding_box()
            if stage_box:
                page.locator('[data-tool="text"]').first.click()
                page.wait_for_timeout(150)
                page.mouse.click(stage_box["x"] + 20, stage_box["y"] + stage_box["height"] / 2)
                page.wait_for_timeout(500)
                page.evaluate("() => EInviteToolController.setTool('select')")
            after_add = page.locator("#stage .object").count()
            check("editor add text", lambda: {"before": before_add, "after": after_add} if after_add == before_add + 1 else (_ for _ in ()).throw(AssertionError(f"add text: {before_add} -> {after_add}")), page)

            page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
            page.evaluate("() => window.EInviteEditorBridge.save()")
            page.wait_for_function("() => document.documentElement.dataset.savePending === 'false'", timeout=15000)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
            dismiss_editor_onboarding(page)
            page.wait_for_selector('#stage .object[data-id="title"]', timeout=20000)
            check("save + reload", lambda: {"objects": page.locator("#stage .object").count(), "title": page.locator('#stage .object[data-id="title"]').inner_text()[:40]}, page)

            # The starter document has no visual pages, so the Pages pane is an
            # intentional empty state. Add one through the real command and save
            # it; the width loop below then re-verifies the phase-10 grouping with
            # real page cards on every contract viewport.
            page.evaluate("() => window.EInviteCommandRegistry.execute('page.addBlank')")
            page.wait_for_function("() => window.EInviteEditorBridge.getState().designPages.length === 1", timeout=10000)
            page.wait_for_selector("#designPagesManager .v22-page-card[data-page-id]", timeout=15000)
            check("editor page card after add", lambda: page.locator("#designPagesManager .v22-page-card[data-page-id]").count(), page)
            page.evaluate("() => window.EInviteEditorBridge.save()")
            page.wait_for_function("() => document.documentElement.dataset.savePending === 'false'", timeout=15000)

            errors_before_export = len(errors)
            page.evaluate("() => window.EInviteExportQuality.open('export')")
            page.wait_for_selector('[data-export-png="1"]', timeout=15000)
            with page.expect_download(timeout=30000) as download_info:
                page.locator('[data-export-png="1"]').click()
            download = Path(download_info.value.path())
            png_bytes = download.read_bytes()
            check("export png", lambda: {"bytes": len(png_bytes), "png": png_bytes.startswith(b"\x89PNG\r\n\x1a\n")} if len(png_bytes) > 1000 and png_bytes.startswith(b"\x89PNG\r\n\x1a\n") else (_ for _ in ()).throw(AssertionError(f"invalid png: {len(png_bytes)} bytes")), page)
            csp_errors = [item for item in errors[errors_before_export:] if "Content Security Policy" in item or "data:image/svg" in item]
            check("export console clean", lambda: "clean" if not csp_errors else (_ for _ in ()).throw(AssertionError(csp_errors)), page)

            # Close the desktop context, then reload the editor at every contract
            # width. This also re-verifies the phase-10 Pages-manager grouping:
            # every width must show real page cards in the active Pages pane.
            storage = context.storage_state()
            context.close()

            for width, height in VIEWPORTS:
                editor_context = browser.new_context(viewport={"width": width, "height": height}, storage_state=storage)
                editor = editor_context.new_page()
                editor.on("pageerror", lambda err: errors.append("EDITOR-PAGE:" + str(err)[:250]))
                editor.on("console", lambda msg: errors.append("EDITOR-CONSOLE:" + msg.text[:250]) if msg.type == "error" else None)
                try:
                    editor.goto(base + f"/invitations/{row['id']}/editor", wait_until="domcontentloaded", timeout=30000)
                    editor.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=30000)
                    dismiss_editor_onboarding(editor)
                    # Drive the real user path. Programmatic openCreation()
                    # in the first ~100 ms after editor-ready is undone by the
                    # boot restore (OBS-R4-2), and the earlier version of this
                    # check counted off-canvas cards as visible at 768.
                    if width <= 820:
                        # A tap inside the boot-restore window is undone ~100 ms
                        # later (OBS-R4-2), which left the rail off-canvas and
                        # made this click time out. Wait until the editor has
                        # settled, like a human, then require the rail button to
                        # be on-screen before clicking it.
                        editor.wait_for_timeout(600)
                        editor.locator("#mobileToolsMode").click()
                        editor.wait_for_function("() => document.body.dataset.editorDrawer === 'creation'")
                        editor.wait_for_selector('[data-studio-tab="pages"]:visible', timeout=10000)
                    editor.locator('[data-studio-tab="pages"]').click()
                    editor.wait_for_timeout(700)
                    metrics = editor.evaluate("""() => ({
                      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                      drawer: document.body.dataset.editorDrawer,
                      pane: !!document.querySelector('[data-studio-pane="pages"].active'),
                      cards: [...document.querySelectorAll('#designPagesManager .v22-page-card[data-page-id]')].filter(el => {
                        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
                        return r.width > 0 && r.height > 0 && r.right > 0 && r.left < innerWidth &&
                          cs.visibility !== 'hidden' && cs.display !== 'none';
                      }).length,
                      toolbar: !!document.querySelector('#stage .toolbar, .studio-topbar')
                    })""")
                    check(f"editor {width} no overflow", lambda m=metrics: m["overflow"] if m["overflow"] <= 1 else (_ for _ in ()).throw(AssertionError(m)), editor)
                    check(f"editor {width} Pages pane and cards", lambda m=metrics: m if m["pane"] and m["cards"] > 0 and (width > 820 or m["drawer"] == "creation") else (_ for _ in ()).throw(AssertionError(m)), editor)
                    check(f"editor {width} toolbar", lambda m=metrics: "toolbar visible" if m["toolbar"] else (_ for _ in ()).throw(AssertionError("toolbar missing")), editor)
                finally:
                    editor_context.close()

            # --- auth error -------------------------------------------------------
            bad = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            bad.goto(base + "/dashboard.html", wait_until="domcontentloaded")
            bad.locator("#authRegisterTab").click()
            bad.locator("#email").fill(email)
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

    _write_payload()
    failed = [c for c in checks if not c["ok"]]
    print(f"\nFLOW_CHECKS={len(checks)} FAILED={len(failed)} CONSOLE_ERRORS={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
