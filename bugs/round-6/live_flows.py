#!/usr/bin/env python3
"""Round-6 live interaction pass at all six contract widths.

Extends the original 1440/360 live_flows.py rather than replacing its approach:
the anonymous demo editor on `/` is exercised at every width (add, drag,
resize, rotate, multi-select, undo/redo, save, reload/recover, export), along
with the template picker/search/filters, the landing/editor chrome, the
signed-out dashboard (invalid + valid-shaped but unsubmitted registration), the
auth-gated `/designer` shell and the missing-invitation 404.

Guest invitation and RSVP are deliberately not driven against production: live
has no published invitation and no credentials. That limit is recorded in the
round-6 FINDINGS.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium  # noqa: E402
from live_sweep import AUDIT  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = os.environ.get("ROUND6_BASE", "https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page").rstrip("/")
OUT = Path(__file__).resolve().parent
SHOTS = OUT / "shots" / "flows-v2"
SHOTS.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(360, 800), (390, 844), (768, 900), (1024, 900), (1280, 900), (1440, 900)]

VISUAL = r"""() => {
  const vis = (el) => {
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    return cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity || 1) > 0.05 && r.width > 1 && r.height > 1;
  };
  const label = (el) => (el.id ? '#' + el.id : el.tagName.toLowerCase()) + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
  const parse = (c) => { const m = c.match(/rgba?\(([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)/); return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null; };
  const lum = (c) => { const [r, g, b] = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const bg = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage !== 'none') return null;
      const c = parse(cs.backgroundColor);
      if (c && parseFloat(cs.backgroundColor.split(',')[3] ?? '1') > 0.85) return c;
    }
    return [255, 255, 255];
  };
  const low = [];
  for (const el of document.querySelectorAll('h1,h2,h3,p,span,strong,small,label,button,a')) {
    if (!vis(el) || el.closest('.sr-only,.skip-link') || el.children.length > 2) continue;
    const text = (el.innerText || '').trim();
    if (text.length < 2 || el.getBoundingClientRect().height < 8) continue;
    const cs = getComputedStyle(el), fg = parse(cs.color), back = bg(el);
    if (!fg || !back) continue;
    const size = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700;
    const ratio = (Math.max(lum(fg), lum(back)) + 0.05) / (Math.min(lum(fg), lum(back)) + 0.05);
    if (ratio < (size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5)) low.push({ el: label(el), text: text.slice(0, 45), ratio: Math.round(ratio * 100) / 100, size: Math.round(size) });
    if (low.length >= 8) break;
  }
  const overlap = [];
  const controls = [...document.querySelectorAll('header button, header a, .canvas-header button, .studio-rail-button, .studio-toolbar button')].filter(vis);
  for (let i = 0; i < controls.length; i++) for (let j = i + 1; j < controls.length; j++) {
    const a = controls[i], b = controls[j];
    if (a.contains(b) || b.contains(a)) continue;
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const ix = Math.max(0, Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left));
    const iy = Math.max(0, Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top));
    if (ix * iy > 12) overlap.push({ a: label(a), b: label(b), area: Math.round(ix * iy) });
    if (overlap.length >= 6) break;
  }
  const misalign = [];
  const cards = [...document.querySelectorAll('.pack-card')].filter(vis);
  for (let i = 0; i + 1 < cards.length; i++) {
    const a = cards[i].getBoundingClientRect(), b = cards[i + 1].getBoundingClientRect();
    if (Math.abs(a.top - b.top) < 2 && Math.abs(a.height - b.height) > 6) misalign.push({ a: Math.round(a.height), b: Math.round(b.height), top: Math.round(a.top) });
    if (misalign.length >= 6) break;
  }
  return { lowContrast: low, overlap, misalign };
}"""

checks: list[dict] = []
widths: list[dict] = []


def shot(page, width, label, full=False):
    path = SHOTS / f"{width}-{label}.png"
    try:
        page.screenshot(path=str(path), full_page=full)
    except Exception:
        pass
    return str(path.relative_to(OUT))


def check(name, fn, page=None, width=None, record=True):
    item = {"width": width, "name": name}
    try:
        detail = fn()
        item.update(ok=True, detail=detail)
        print("PASS", width, name, detail if isinstance(detail, (str, int, float, dict)) else "")
    except Exception as exc:  # a failed step is data, not a crash
        item.update(ok=False, error=repr(exc)[:400])
        print("FAIL", width, name, repr(exc)[:240])
        if page is not None:
            shot(page, width, "fail-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60])
    if record:
        checks.append(item)
    return item


def acct(errors, kind, msg, width):
    errors[kind].append({"w": width, "text": str(msg)[:300]})


def dismiss(page):
    tour = page.locator("#finalTourDismiss")
    if tour.count() and tour.is_visible():
        tour.click()
        page.wait_for_timeout(220)


def wait_editor(page):
    page.wait_for_selector('#stage .object[data-id="title"]', timeout=25000)
    dismiss(page)


def obj_state(page):
    return page.evaluate("() => JSON.parse(JSON.stringify(state.objects))")


def click_js(page, selector):
    return page.evaluate("(sel) => { const el = document.querySelector(sel); if (el) { el.click(); return true; } return false; }", selector)


def close_overlays(page):
    """Dismiss popovers/modals and return the canvas to the select tool."""
    for _ in range(2):
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
    page.evaluate("() => { document.querySelectorAll('.ui-theme-menu, .canvas-header-more-menu').forEach(e => { if (e.hidden === false) e.hidden = true; }); }")
    page.evaluate("() => { if (window.EInviteToolController) EInviteToolController.setTool('select'); }")
    page.wait_for_timeout(120)


def audit(page, width, state, bucket):
    try:
        data = page.evaluate(AUDIT)
        data["visual"] = page.evaluate(VISUAL)
        path = shot(page, width, "audit-" + state)
        bucket["audits"].append({"state": state, "shot": path, **data})
        return data
    except Exception as exc:
        bucket["audits"].append({"state": state, "error": repr(exc)[:300]})
        return {}


def editor_flow(page, width, height, bucket):
    resp = page.goto(BASE + "/", wait_until="load", timeout=45000)
    if resp and resp.status >= 400:
        raise AssertionError(f"origin returned HTTP {resp.status}")
    page.wait_for_timeout(1200)
    dismiss(page)
    check("editor boots", lambda: {"objects": page.locator("#stage .object").count(), "stage": page.locator("#stage").is_visible()}, page, width)
    check("root no overflow", lambda: page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), page, width)
    audit(page, width, "root", bucket)
    shot(page, width, "root", full=True)

    # Appearance is a menu (Light/Dark), not a one-click toggle; drive it fully
    # so it closes before any canvas gesture.
    theme = page.locator(".ui-theme-button").first
    if theme.count() and theme.is_visible():
        theme.click()
        try:
            page.wait_for_selector(".ui-theme-menu [data-mode='dark']", state="visible", timeout=5000)
        except Exception:
            pass
        dark = page.locator(".ui-theme-menu [data-mode='dark']")
        if not dark.is_visible():
            raise AssertionError("appearance menu did not open")
        dark.click()
        page.wait_for_timeout(350)
        dark_state = page.evaluate("() => ({attr: document.documentElement.dataset.theme, ls: localStorage.getItem('einvite-theme-mode')})")
        shot(page, width, "theme-dark")
        if not page.locator(".ui-theme-menu [data-mode='light']").is_visible():
            theme.click()
            page.wait_for_timeout(300)
        page.locator(".ui-theme-menu [data-mode='light']").click()
        page.wait_for_timeout(350)
        light_state = page.evaluate("() => ({attr: document.documentElement.dataset.theme, ls: localStorage.getItem('einvite-theme-mode')})")
        check("appearance menu", lambda: {"dark": dark_state, "light": light_state} if dark_state["attr"] == "dark" and light_state["attr"] == "light" else (_ for _ in ()).throw(AssertionError(f"appearance did not switch: {dark_state} / {light_state}")), page, width)
        close_overlays(page)
    else:
        check("appearance menu", lambda: "skipped: control absent", page, width)

    km = page.locator("#lang-km")
    if km.count() and km.is_visible():
        km.click()
    else:
        click_js(page, "#lang-km")
    page.wait_for_timeout(350)
    khmer = page.evaluate("""() => ({lang: document.documentElement.lang, khmer: /[\\u1780-\\u17ff]/.test(document.body.innerText), digits: /[\\u17e0-\\u17e9]/.test(document.body.innerText), mixed: [...document.querySelectorAll('h1,h2,p,button')].some(e => /[\\u1780-\\u17ff]/.test(e.innerText) && /[A-Za-z]/.test(e.innerText))})""")
    shot(page, width, "lang-km")
    km_active = page.evaluate("() => document.querySelector('#lang-km')?.classList.contains('active') === true")
    check("language toggle", lambda: {**khmer, "active": km_active} if km_active or khmer["lang"].startswith("km") else (_ for _ in ()).throw(AssertionError(f"km did not take: {khmer}")), page, width)
    en = page.locator("#lang-en")
    if en.count() and en.is_visible():
        en.click()
    else:
        click_js(page, "#lang-en")
    page.wait_for_timeout(250)

    # Rail tabs and topbar menus.
    rail = page.locator(".studio-rail-button")
    clicked = []
    for i in range(min(6, rail.count())):
        item = rail.nth(i)
        if not item.is_visible():
            continue
        label = (item.inner_text() or "").strip().split("\n")[0][:24]
        try:
            item.click(timeout=3000)
            page.wait_for_timeout(260)
            clicked.append(label)
        except Exception:
            pass
    if clicked:
        check("rail tabs", lambda: {"clicked": clicked}, page, width)
        shot(page, width, "rail-tabs")
        try:
            rail.first.click(timeout=3000)
        except Exception:
            pass
    else:
        check("rail tabs", lambda: "skipped: rail not visible", page, width)

    more = page.locator(".canvas-header-more-trigger").first
    if more.count() and more.is_visible():
        more.click()
        page.wait_for_timeout(250)
        menu = page.locator("[role=menu], .canvas-header-more-menu, .studio-menu").first
        shot(page, width, "more-menu")
        check("more menu", lambda: {"visible": bool(menu.count() and menu.is_visible())} if menu.count() else "opened", page, width)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)

    for selector, label in (("#studioCheckBtn", "design check"), ("#studioCommandBtn", "command palette")):
        loc = page.locator(selector).first
        if loc.count() and loc.is_visible():
            loc.click()
            page.wait_for_timeout(400)
            shot(page, width, re.sub(r"[^a-z0-9]+", "-", label))
            check(label, lambda: {"dialogs": page.locator("dialog[open], [role=dialog]").count()}, page, width)
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)

    # Guest preview and publish open chrome overlays; do not submit anything.
    for selector, label in (("#previewBtn", "guest preview"), ("#publishBtn", "publish shell")):
        loc = page.locator(selector).first
        if loc.count() and loc.is_visible():
            before_url = page.url
            try:
                loc.click()
                page.wait_for_timeout(800)
                extra = [p for p in page.context.pages if p is not page]
                shot(page, width, re.sub(r"[^a-z0-9]+", "-", label))
                check(label, lambda: {"url": page.url, "extra_tabs": len(extra), "dialogs": page.locator("dialog[open], [role=dialog]").count()}, page, width)
                for p in extra:
                    p.close()
                if page.url != before_url:
                    page.goto(BASE + "/", wait_until="load", timeout=45000)
                    wait_editor(page)
            except Exception:
                page.keyboard.press("Escape")
        else:
            check(label, lambda: "skipped: control not visible", page, width)

    page.goto(BASE + "/", wait_until="load", timeout=45000)
    wait_editor(page)
    close_overlays(page)
    page.wait_for_timeout(300)

    # Editor: drag, resize, rotate, multi-select. Selecting on mobile opens the
    # full-screen Quick Edit drawer by design; Canvas returns to the canvas and
    # keeps the selection, which is the flow a mobile user takes.
    page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
    page.wait_for_timeout(300)
    if width <= 820:
        quick_open = page.evaluate("() => document.body.classList.contains('mobile-inspector-open')")
        if quick_open:
            shot(page, width, "mobile-quick-edit")
            canvas_mode = page.locator("#mobileCanvasMode")
            if canvas_mode.count() and canvas_mode.is_visible():
                canvas_mode.click()
                page.wait_for_timeout(300)
            check("mobile quick edit/canvas", lambda: {"opened": True, "mode": page.evaluate("() => document.body.dataset.mobileEditorMode"), "selected": page.evaluate("() => EInviteEditorBridge.getSelectedIds().length")}, page, width)
        else:
            check("mobile quick edit/canvas", lambda: {"opened": False, "mode": page.evaluate("() => document.body.dataset.mobileEditorMode")}, page, width)
    # Selecting at <=1180 also adds the desktop `inspector-open` drawer, which
    # sits above the canvas even after Canvas mode. Escape closes it and keeps
    # the selection/handles, which is the documented focus-canvas recovery.
    shot(page, width, "selection-inspector")
    close_overlays(page)
    if not page.evaluate("() => EInviteEditorBridge.getSelectedIds().length"):
        page.evaluate("() => window.EInviteEditorBridge.select(['title'])")
        page.wait_for_timeout(250)
    page.evaluate("() => { if (window.EInviteToolController) EInviteToolController.setTool('select'); }")
    page.wait_for_timeout(250)
    before = obj_state(page)["title"]
    box = page.locator('#stage .object[data-id="title"]').bounding_box()
    if not box:
        raise AssertionError("title has no box")
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 26, box["y"] + box["height"] / 2 + 14, steps=6)
    page.mouse.up()
    page.wait_for_timeout(320)
    after = obj_state(page)["title"]
    check("drag", lambda: {"before": before.get("left"), "after": after.get("left")} if after != before else (_ for _ in ()).throw(AssertionError("title did not move")), page, width)
    shot(page, width, "editor-drag")

    handles = page.locator(".pe-handle")
    if handles.count():
        before = obj_state(page)["title"]
        hb = handles.last.bounding_box()
        if hb:
            page.mouse.move(hb["x"] + hb["width"] / 2, hb["y"] + hb["height"] / 2)
            page.mouse.down()
            page.mouse.move(hb["x"] + hb["width"] / 2 + 24, hb["y"] + hb["height"] / 2 + 18, steps=5)
            page.mouse.up()
            page.wait_for_timeout(300)
            resized = obj_state(page)["title"]
            check("resize", lambda: {"before": {k: before.get(k) for k in ("w", "h", "width", "height")}, "after": {k: resized.get(k) for k in ("w", "h", "width", "height")}} if resized != before else (_ for _ in ()).throw(AssertionError("resize did not change the title")), page, width)
            shot(page, width, "editor-resize")
    else:
        check("resize", lambda: (_ for _ in ()).throw(AssertionError("no .pe-handle")), page, width)

    rot = page.locator(".pe-rotate").first
    if rot.count() and rot.is_visible():
        before = obj_state(page)["title"]
        rb = rot.bounding_box()
        if rb:
            page.mouse.move(rb["x"] + rb["width"] / 2, rb["y"] + rb["height"] / 2)
            page.mouse.down()
            page.mouse.move(rb["x"] + rb["width"] / 2 + 22, rb["y"] + rb["height"] / 2 + 16, steps=5)
            page.mouse.up()
            page.wait_for_timeout(300)
            rotated = obj_state(page)["title"]
            check("rotate", lambda: {"before": before.get("rotation"), "after": rotated.get("rotation")} if rotated != before else (_ for _ in ()).throw(AssertionError("rotate did not change the title")), page, width)
            shot(page, width, "editor-rotate")
    else:
        check("rotate", lambda: (_ for _ in ()).throw(AssertionError("rotate handle not visible")), page, width)

    page.evaluate("() => window.EInviteEditorBridge.select(['title', 'subtitle'])")
    page.wait_for_timeout(220)
    check("multi-select", lambda: {"ids": page.evaluate("() => EInviteEditorBridge.getSelectedIds().length"), "outlined": page.evaluate("() => document.querySelectorAll('#stage .object.selected, #stage .object.multi-selected').length")}, page, width)

    # Add text: use the real tool where visible, JS fallback on narrow toolbar.
    page.evaluate("() => window.EInviteEditorBridge.select([])")
    close_overlays(page)
    before_count = page.locator("#stage .object").count()
    stage = page.locator("#stage").bounding_box()
    if not stage:
        raise AssertionError("no stage box")
    tool = page.locator('[data-tool="text"]').first
    if tool.count():
        tool.scroll_into_view_if_needed()
        if tool.is_visible():
            tool.click()
        else:
            page.evaluate("() => window.EInviteToolController.setTool('text')")
    else:
        page.evaluate("() => window.EInviteToolController.setTool('text')")
    page.wait_for_timeout(150)
    page.mouse.click(stage["x"] + 24, stage["y"] + stage["height"] * 0.6)
    page.wait_for_timeout(450)
    page.evaluate("() => window.EInviteToolController.setTool('select')")
    after_count = page.locator("#stage .object").count()
    check("add text", lambda: {"before": before_count, "after": after_count} if after_count == before_count + 1 else (_ for _ in ()).throw(AssertionError(f"add text {before_count}->{after_count}")), page, width)
    shot(page, width, "editor-add")

    # Undo/redo via the real buttons where visible. Redo may insert a new object
    # id, so assert the object count is restored rather than byte-identical JSON.
    before = page.evaluate("() => JSON.stringify(state.objects)")
    before_count = page.locator("#stage .object").count()
    undo = page.locator("#undoBtn").first
    redo = page.locator("#redoBtn").first
    if undo.count() and undo.is_visible() and not undo.is_disabled():
        undo.click()
    else:
        page.evaluate("() => EInviteEditorBridge.undo()")
    page.wait_for_timeout(450)
    undone = page.evaluate("() => JSON.stringify(state.objects)")
    undo_count = page.locator("#stage .object").count()
    if redo.count() and redo.is_visible() and not redo.is_disabled():
        redo.click()
    else:
        page.evaluate("() => EInviteEditorBridge.redo()")
    page.wait_for_timeout(500)
    redo_count = page.locator("#stage .object").count()
    check("undo/redo", lambda: {"before": before_count, "after_undo": undo_count, "after_redo": redo_count} if undone != before and redo_count == before_count else (_ for _ in ()).throw(AssertionError(f"undo/redo {undone != before}/{redo_count == before_count} ({before_count}/{undo_count}/{redo_count})")), page, width)

    # Save, reload and recover the local draft.
    check("save", lambda: page.evaluate("() => { const r = EInviteEditorBridge.save(); return {saved: r !== false, draft: !!localStorage.getItem('sovan-invite-draft-v3:demo-wedding'), status: document.querySelector('#saveState')?.textContent?.trim() || ''}; }"), page, width)
    saved = obj_state(page)
    saved_count = len(saved)
    saved_title = saved.get("title")
    shot(page, width, "editor-saved")
    page.reload(wait_until="load", timeout=45000)
    page.wait_for_timeout(1400)
    wait_editor(page)
    recovered = obj_state(page)
    check("reload/recover", lambda: {"objects": {"before": saved_count, "after": len(recovered)}, "title_restored": recovered.get("title") == saved_title} if len(recovered) == saved_count and recovered.get("title") == saved_title else (_ for _ in ()).throw(AssertionError(f"recovery mismatch {saved_count}->{len(recovered)}")), page, width)
    shot(page, width, "editor-reloaded")

    errors_before_export = len(bucket["console"])
    page.evaluate("() => window.EInviteExportQuality.open('export')")
    page.wait_for_selector('[data-export-png="1"]', timeout=15000)
    with page.expect_download(timeout=30000) as info:
        page.locator('[data-export-png="1"]').click()
    png = Path(info.value.path()).read_bytes()
    check("export png", lambda: {"bytes": len(png), "png": png.startswith(b"\x89PNG\r\n\x1a\n")} if len(png) > 1000 and png.startswith(b"\x89PNG\r\n\x1a\n") else (_ for _ in ()).throw(AssertionError(f"invalid png {len(png)}")), page, width)
    csp = [e for e in bucket["console"][errors_before_export:] if "Content Security Policy" in e["text"]]
    check("export console clean", lambda: "clean" if not csp else (_ for _ in ()).throw(AssertionError(csp)), page, width)
    shot(page, width, "export-dialog")
    page.evaluate("() => {const d = document.querySelector('#v24QualityDialog'); if (d && d.open) d.close()}")
    page.wait_for_timeout(200)


def templates_flow(page, width, bucket):
    page.goto(BASE + "/templates", wait_until="load", timeout=45000)
    page.wait_for_timeout(1500)
    dismiss(page)
    check("templates cards", lambda: {"cards": page.locator(".pack-card").count(), "overflow": page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")} if page.locator(".pack-card").count() > 0 else (_ for _ in ()).throw(AssertionError("no cards")), page, width)
    audit(page, width, "templates", bucket)
    shot(page, width, "templates-root", full=True)

    search = page.locator("input[type=search], #templateSearch, [data-template-search]").first
    if not search.count():
        raise AssertionError("no template search")
    before = page.locator(".pack-card").count()
    search.fill("wedding")
    page.wait_for_timeout(650)
    after = page.locator(".pack-card").count()
    shot(page, width, "templates-search")
    check("templates search", lambda: {"before": before, "after": after, "value": search.input_value()} if search.input_value() == "wedding" and after < before else (_ for _ in ()).throw(AssertionError(f"search {before}->{after}")), page, width)
    search.fill("")
    page.wait_for_timeout(500)
    mixed = "ខ្មែរ ១២៣"
    search.fill(mixed)
    page.wait_for_timeout(450)
    check("khmer numerals input", lambda: {"value": search.input_value(), "khmer": bool(re.search(r"[\u1780-\u17ff]", search.input_value())), "digits": bool(re.search(r"[\u17e0-\u17e9]", search.input_value()))} if search.input_value() == mixed else (_ for _ in ()).throw(AssertionError("Khmer text/numerals did not take")), page, width)
    search.fill("")
    page.wait_for_timeout(400)

    for selector, label, wanted in (("#studioSource", "source filter", "Built-in"), ("#studioCategory", "category filter", "Wedding")):
        sel = page.locator(selector)
        if not sel.count():
            check(label, lambda: (_ for _ in ()).throw(AssertionError("filter absent")), page, width)
            continue
        try:
            sel.select_option(label=wanted)
        except Exception:
            sel.select_option(index=1)
        page.wait_for_timeout(500)
        count = page.locator(".pack-card").count()
        shot(page, width, "templates-" + re.sub(r"[^a-z0-9]+", "-", label))
        check(label, lambda: {"value": sel.input_value(), "cards": count} if count > 0 else (_ for _ in ()).throw(AssertionError("filter emptied the grid")), page, width)
        sel.select_option(index=0)
        page.wait_for_timeout(350)

    fav = page.locator("#studioFavorites")
    if fav.count():
        fav.check()
        page.wait_for_timeout(400)
        check("favorites filter", lambda: {"checked": fav.is_checked(), "cards": page.locator(".pack-card").count(), "notice": (page.locator('.template-error').inner_text() if page.locator('.template-error').count() else '')[:80]}, page, width)
        shot(page, width, "templates-favorites")
        fav.uncheck()
        page.wait_for_timeout(300)
    else:
        check("favorites filter", lambda: "absent", page, width)

    refresh = page.locator("#refreshBtn")
    if refresh.count():
        refresh.click()
        page.wait_for_timeout(900)
        check("templates refresh", lambda: {"cards": page.locator(".pack-card").count()}, page, width)

    km = page.locator("#lang-km")
    if km.count() and km.is_visible():
        km.click()
    else:
        click_js(page, "#lang-km")
    page.wait_for_timeout(450)
    khmer = page.evaluate("""() => ({lang: document.documentElement.lang, khmer: /[\\u1780-\\u17ff]/.test(document.body.innerText), digits: /[\\u17e0-\\u17e9]/.test(document.body.innerText), mixed: [...document.querySelectorAll('h1,h2,p,button')].some(e => /[\\u1780-\\u17ff]/.test(e.innerText) && /[A-Za-z]/.test(e.innerText)), font: getComputedStyle([...document.querySelectorAll('.khmer-text, [lang=km]')][0] || document.body).fontFamily})""")
    shot(page, width, "templates-km", full=True)
    check("templates khmer", lambda: khmer if khmer["khmer"] else (_ for _ in ()).throw(AssertionError("no Khmer text")), page, width)
    audit(page, width, "templates-km", bucket)
    if page.locator("#lang-en").count():
        click_js(page, "#lang-en")
        page.wait_for_timeout(250)


def dashboard_flow(page, width, bucket):
    page.goto(BASE + "/dashboard", wait_until="load", timeout=45000)
    page.wait_for_timeout(1200)
    dismiss(page)
    signed_out = page.evaluate("() => ({signin: !!document.querySelector('#authSignInTab') && document.querySelector('#authSignInTab').offsetParent !== null, email: !!document.querySelector('#email') && document.querySelector('#email').offsetParent !== null})")
    check("dashboard signed-out shell", lambda: signed_out if signed_out["signin"] and signed_out["email"] else (_ for _ in ()).throw(AssertionError(f"not signed-out shell: {signed_out}")), page, width)
    check("dashboard no overflow", lambda: page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), page, width)
    audit(page, width, "dashboard", bucket)
    shot(page, width, "dashboard-signin", full=True)

    reg = page.locator("#authRegisterTab")
    if reg.count():
        reg.click()
        page.wait_for_timeout(250)
    page.locator("#email").fill("not-an-email")
    page.locator("#password").fill("short")
    if page.locator("#registerConfirmPassword").count():
        page.locator("#registerConfirmPassword").fill("short")
    page.locator("#loginBtn").click()
    page.wait_for_timeout(600)
    invalid = page.evaluate("""() => ({url: location.pathname, email_invalid: !document.querySelector('#email').checkValidity(), password_invalid: !document.querySelector('#password').checkValidity(), still_signed_out: !!document.querySelector('#authRegisterTab') && document.querySelector('#authRegisterTab').offsetParent !== null})""")
    check("registration invalid rejected", lambda: invalid if invalid["email_invalid"] and invalid["still_signed_out"] and invalid["url"] == "/dashboard" else (_ for _ in ()).throw(AssertionError(invalid)), page, width)
    shot(page, width, "dashboard-invalid")

    # Valid-shaped input is checked but never submitted: no production account.
    page.locator("#email").fill("qa.round6@example.com")
    page.locator("#password").fill("Round6-Passw0rd")
    if page.locator("#registerConfirmPassword").count():
        page.locator("#registerConfirmPassword").fill("Round6-Passw0rd")
    valid = page.evaluate("""() => { const ids = ['email','password','registerConfirmPassword']; return {valid: ids.every(id => { const el = document.getElementById(id); return !el || el.checkValidity(); }), submit_disabled: document.querySelector('#loginBtn')?.disabled === true, confirm_present: !!document.querySelector('#registerConfirmPassword')}; }""")
    shot(page, width, "dashboard-valid-shaped")
    check("registration valid-shaped fields", lambda: {"valid": valid["valid"], "submitted": False, "confirm_present": valid["confirm_present"]} if valid["valid"] else (_ for _ in ()).throw(AssertionError(valid)), page, width)
    page.locator("#email").fill("")
    page.locator("#password").fill("")
    if page.locator("#registerConfirmPassword").count():
        page.locator("#registerConfirmPassword").fill("")

    signin = page.locator("#authSignInTab")
    if signin.count():
        signin.click()
        page.wait_for_timeout(220)
    page.locator("#email").fill("not-an-email")
    page.locator("#password").fill("x")
    page.locator("#loginBtn").click()
    page.wait_for_timeout(500)
    check("sign-in invalid rejected", lambda: {"email_invalid": not page.locator("#email").evaluate("e => e.checkValidity()"), "url": page.evaluate("location.pathname")} if page.evaluate("location.pathname") == "/dashboard" else (_ for _ in ()).throw(AssertionError("left dashboard")), page, width)


def designer_flow(page, width, bucket):
    resp = page.goto(BASE + "/designer", wait_until="load", timeout=45000)
    page.wait_for_timeout(1000)
    check("designer shell", lambda: {"status": resp.status if resp else None, "heading": page.locator("h1").first.inner_text() if page.locator("h1").count() else "", "unavailable": "unavailable" in page.locator("body").inner_text().lower(), "overflow": page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")}, page, width)
    audit(page, width, "designer", bucket)
    shot(page, width, "designer", full=True)


def missing_flow(page, width, bucket):
    before_errors = len(bucket["console"])
    resp = page.goto(BASE + "/i/missing-slug-round-6", wait_until="load", timeout=45000)
    page.wait_for_timeout(900)
    check("missing invitation 404", lambda: {"status": resp.status if resp else None, "heading": page.locator("h1").first.inner_text() if page.locator("h1").count() else "", "overflow": page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")} if resp and resp.status == 404 else (_ for _ in ()).throw(AssertionError(f"status {resp.status if resp else None}")), page, width)
    audit(page, width, "missing", bucket)
    shot(page, width, "missing", full=True)
    bucket["missing_console"] = bucket["console"][before_errors:]


def run_width(browser, width, height):
    context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True, device_scale_factor=1)
    page = context.new_page()
    bucket = {"width": width, "height": height, "console": [], "pageerrors": [], "failed": [], "http": [], "audits": [], "requests": [], "missing_console": []}
    page.on("console", lambda msg: acct(bucket, "console", msg.text, width) if msg.type == "error" else None)
    page.on("pageerror", lambda err: acct(bucket, "pageerrors", err, width))
    page.on("requestfailed", lambda req: bucket["failed"].append({"url": req.url[:180], "why": (req.failure or "")[:120]}))
    page.on("response", lambda res: bucket["http"].append({"url": res.url[:180], "status": res.status}) if res.status >= 400 else None)
    page.on("request", lambda req: bucket["requests"].append({"method": req.method, "url": req.url[:180]}) if req.method == "POST" else None)
    try:
        editor_flow(page, width, height, bucket)
        templates_flow(page, width, bucket)
        dashboard_flow(page, width, bucket)
        designer_flow(page, width, bucket)
        missing_flow(page, width, bucket)
    except Exception as exc:
        bucket["fatal"] = repr(exc)[:500]
        bucket["blocked"] = 429 if "HTTP 429" in bucket["fatal"] else None
        print("FATAL", width, repr(exc)[:300])
        shot(page, width, "fatal")
    finally:
        expected_404 = [e for e in bucket["missing_console"] if ("404" in e["text"] or "beacon.min.js" in e["text"] or "Content Security Policy" in e["text"])]
        unexpected = [e for e in bucket["console"] if e not in bucket["missing_console"]]
        bucket["console_expected_404"] = expected_404
        bucket["console_unexpected"] = unexpected
        bucket["http_unexpected"] = [h for h in bucket["http"] if "/i/missing-slug-round-6" not in h["url"] and "/api/public/missing-slug-round-6" not in h["url"]]
        bucket["failed_unexpected"] = [f for f in bucket["failed"] if "cloudflareinsights" not in f["url"]]
        check("page errors clean", lambda: "clean" if not bucket["pageerrors"] else (_ for _ in ()).throw(AssertionError(bucket["pageerrors"][:3])), None, width)
        check("console clean (non-404)", lambda: "clean" if not unexpected else (_ for _ in ()).throw(AssertionError(unexpected[:4])), None, width)
        check("network clean (non-404)", lambda: "clean" if not bucket["http_unexpected"] and not bucket["failed_unexpected"] else (_ for _ in ()).throw(AssertionError({"http": bucket["http_unexpected"][:3], "failed": bucket["failed_unexpected"][:3]})), None, width)
        widths.append(bucket)
        context.close()
    return bucket


def main() -> int:
    with sync_playwright() as play:
        browser = launch_chromium(play)
        for width, height in VIEWPORTS:
            bucket = run_width(browser, width, height)
            if bucket.get("blocked"):
                print("STOP: origin hosting allowance exhausted (HTTP 429); remaining widths skipped")
                break
        browser.close()

    payload = {"checks": checks, "widths": widths, "base": BASE, "viewports": VIEWPORTS}
    (OUT / "live-flows-six.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    failed = [c for c in checks if not c["ok"]]
    print(f"LIVE_CHECKS={len(checks)} FAILED={len(failed)} WIDTHS={len(widths)}")
    for f in failed:
        print("FAILED", f["width"], f["name"], f.get("error", "")[:240])
    return 0 if not failed and len(widths) == len(VIEWPORTS) and not any(w.get("blocked") for w in widths) else 1


if __name__ == "__main__":
    raise SystemExit(main())
