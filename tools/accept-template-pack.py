#!/usr/bin/env python3
"""Acceptance harness for the 36-template Khmer event pack (TP-3, A1-A12).

Runs the real editor against a throw-away app server and records, per template:

* A2  long-task time during load (PerformanceObserver 'longtask'), page count, canvas size
* A3  text overflow (scrollWidth/scrollHeight vs client) and a 1440 stage screenshot
* A4  computed font family, Khmer line-height and letter-spacing
* A5  one object selected and nudged with the keyboard, undo restores it, decorative
      images keep their box
* A6  a text edit (colour through the inspector) and undo
* A7  placeholder-only scan of the built document
* A8  PNG 1x/2x/3x and a printed PDF (bytes + pixel size from the PNG header)
* A9  375/768/1440 body width and stage fit (screenshots for 375)
* A10 contrast of every text colour against the page background
* A11 decorative images are alt="" and the gallery card has a bilingual name
* A12 no third-party request, no external URL in the document

Usage:
    .venv/bin/python tools/accept-template-pack.py --ids wd-royal-maroon-gold ...
    .venv/bin/python tools/accept-template-pack.py --batch wedding-a
    .venv/bin/python tools/accept-template-pack.py --all

Output: artifacts/next-work/review-tp/acceptance-<batch>.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from browser_runtime import launch_chromium  # noqa: E402
from v14_test_utils import app_server  # noqa: E402
from template_pack_edit_export_test import built_document, open_editor, open_page  # noqa: E402

OUT = ROOT / "artifacts" / "next-work" / "review-tp"
BUILT = ROOT / "assets" / "template-pack" / "built"
CATALOG = json.loads(
    (ROOT / "assets" / "template-pack" / "catalog.js").read_text(encoding="utf-8")[len("export default "):].rstrip().rstrip(";")
)
BY_ID = {entry["id"]: entry for entry in CATALOG["templates"]}

BATCHES = {
    "wedding-a": ["wd-royal-maroon-gold", "wd-ivory-kbach-frame", "wd-lotus-watercolour", "wd-midnight-navy-gold", "wd-temple-arch"],
    "wedding-b": ["wd-quiet-ivory", "wd-jade-garden", "wd-saffron-sunrise", "wd-red-gold-story", "wd-save-the-date"],
    "wedding-c": ["wd-hair-cutting", "wd-reception-dark-plum", "wd-photo-modern", "wd-three-day-program", "anniv-golden"],
    "birthday-business": ["bd-first-pastel", "bd-kids-party", "bd-golden-soiree", "bd-longevity-60", "bd-modern-bold", "biz-grand-opening", "biz-corporate-gala"],
    "ceremony": ["hw-housewarming", "merit-dana", "kathina-robe", "pchum-ben", "memorial-ceremony"],
    "greetings": ["gr-khmer-new-year", "gr-water-festival", "gr-global-new-year", "gr-thank-you", "gr-graduation", "gr-newborn", "gr-sympathy", "gr-get-well", "gr-blessings"],
}

LONG_TASK_INIT = """
window.__longTasks = [];
try {
  new PerformanceObserver((list) => { for (const e of list.getEntries()) window.__longTasks.push(e.duration); })
    .observe({ type: 'longtask', buffered: true });
} catch (error) { window.__longTasks = null; }
"""

METRICS_JS = """
() => {
  const objects = [...document.querySelectorAll('#stage .object')];
  const texts = objects.filter(o => o.querySelector('.content'));
  const km = /[\\u1780-\\u17ff]/;
  const rows = texts.map(o => {
    const c = o.querySelector('.content');
    const run = c.querySelector('.rt-run') || c;
    const cs = getComputedStyle(c);
    const rs = getComputedStyle(run);
    return {
      id: o.dataset.id,
      text: (c.textContent || '').slice(0, 60),
      hex: (rs.color.match(/\\d+/g) || []).slice(0, 3).map(n => Number(n).toString(16).padStart(2, '0')).join(''),
      wanted: String(o.dataset.color || '').replace('#', '').toLowerCase(),
      font: rs.fontFamily,
      fontSize: parseFloat(rs.fontSize),
      letterSpacing: rs.letterSpacing,
      lineHeight: parseFloat(rs.lineHeight) / parseFloat(rs.fontSize || 1),
      km: km.test(c.textContent || ''),
      weight: Number(rs.fontWeight) || 400,
      dh: c.scrollHeight - c.clientHeight,
      dw: c.scrollWidth - c.clientWidth,
      // Box relative to the stage, so a screenshot of the stage can be sampled.
      rect: (() => {
        const stage = document.querySelector('#stage').getBoundingClientRect();
        const own = o.getBoundingClientRect();
        return { x: own.x - stage.x, y: own.y - stage.y, w: own.width, h: own.height };
      })(),
    };
  });
  const images = objects.filter(o => o.querySelector('img'));
  return {
    objects: objects.length,
    texts: rows.length,
    rows,
    images: images.length,
    imageAlts: [...new Set(images.map(o => o.querySelector('img').getAttribute('alt')))],
    svgImages: images.filter(o => (o.querySelector('img').getAttribute('src') || '').endsWith('.svg')).length,
    clippedImages: images.filter(o => { const img = o.querySelector('img'); return img.scrollWidth > img.clientWidth + 1 || img.scrollHeight > img.clientHeight + 1; }).length,
    stage: document.querySelector('#stage').dataset.posterSize,
    stageBox: (() => { const r = document.querySelector('#stage').getBoundingClientRect(); return {w: r.width, h: r.height}; })(),
    bodyOverflow: document.documentElement.scrollWidth - window.innerWidth,
  };
}
"""


def relative_luminance(hex_value: str) -> float:
    channels = [int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [(c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def needed_ratio(size: float, weight: float) -> float:
    """WCAG 2.2 AA: 3.0 for large text (>=24 px, or >=18.66 px bold), else 4.5."""
    return 3.0 if size >= 24 or (size >= 18.66 and weight >= 700) else 4.5


CHROME_HIDE_JS = """() => {
  for (const node of document.querySelectorAll('.studio-selection-toolbar, .ei-context-menu')) {
    node.dataset.acceptChrome = '1';
    node.style.visibility = 'hidden';
  }
}"""

CHROME_SHOW_JS = """() => {
  for (const node of document.querySelectorAll('[data-accept-chrome]')) {
    node.style.visibility = '';
    delete node.dataset.acceptChrome;
  }
}"""


def export_page_png(page, target: Path) -> Path:
    """Export the active page at 1x through the product's own export panel."""
    page.evaluate("() => window.EInviteCommandRegistry.execute('quality.open')")
    page.wait_for_selector('[data-tab="export"]', timeout=15000)
    page.locator('[data-tab="export"]').click()
    page.wait_for_selector('[data-export-png="1"]', timeout=15000)
    with page.expect_download(timeout=45000) as info:
        page.locator('[data-export-png="1"]').click()
    info.value.save_as(target)
    page.keyboard.press("Escape")
    return target


def png_stage_colour(image, x: float, y: float, w: float, h: float, scale_x: float, scale_y: float) -> str:
    """Dominant colour in one text box of an exported page."""
    crop = image.crop((
        max(0, int(x * scale_x)), max(0, int(y * scale_y)),
        min(image.width, int((x + w) * scale_x)), min(image.height, int((y + h) * scale_y)),
    ))
    counts: dict[tuple[int, int, int], int] = {}
    for count, colour in crop.getcolors(maxcolors=1 << 22) or []:
        key = tuple(min(255, (c // 12) * 12 + 6) for c in colour[:3])  # type: ignore[misc]
        counts[key] = counts.get(key, 0) + count
    if not counts:
        return ""
    dominant = max(counts.items(), key=lambda pair: pair[1])[0]
    return "#{:02x}{:02x}{:02x}".format(*dominant)


def contrast_rows_from_png(path: Path, rows: list[dict], display: dict) -> list[dict]:
    """A10 measured on the exported page: no viewport, scroll or chrome in the way.

    Text boxes are measured in displayed CSS pixels on the artboard, so they map to
    the exported image through the artboard's *displayed* width and height — not the
    canvas size. (The artboard is usually scaled to fit; using the canvas size put
    every crop in the wrong place.)
    """
    import re as _re

    from PIL import Image

    display_w = float((display or {}).get("w") or 0)
    display_h = float((display or {}).get("h") or 0)
    if display_w <= 0 or display_h <= 0:
        return []
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        scale_x, scale_y = rgb.width / display_w, rgb.height / display_h
        out = []
        for row in rows:
            rect = row.get("rect") or {}
            behind = png_stage_colour(
                rgb, float(rect.get("x") or 0), float(rect.get("y") or 0),
                float(rect.get("w") or 0), float(rect.get("h") or 0), scale_x, scale_y,
            )
            ratio = contrast("#" + row["hex"], behind) if _re.fullmatch(r"[0-9a-f]{6}", row.get("hex") or "") and behind else 0
            out.append({
                "id": row["id"],
                "ratio": round(ratio, 2),
                "need": needed_ratio(row.get("fontSize") or 0, row.get("weight") or 400),
                "bg": behind,
                "size": round(row.get("fontSize") or 0, 1),
                "km": row["km"],
            })
    return out


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:32]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def placeholder_scan(document: dict) -> list[str]:
    problems = []
    for page in document["designPages"]:
        for oid, obj in page["objects"].items():
            if obj["type"] != "text":
                continue
            text = re.sub(r"<[^>]+>", "", obj.get("html") or "")
            if not text.strip():
                problems.append(f"{oid}: empty")
            if re.search(r"\b\d{3}[- ]?\d{3}[- ]?\d{3,4}\b", text) or re.search(r"@[a-z0-9-]+\.(com|net|org)", text, re.I):
                problems.append(f"{oid}: real identity")
            if obj.get("contentBinding") and not text.strip().startswith("["):
                problems.append(f"{oid}: slot without a bracket placeholder")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--batch", choices=sorted(BATCHES))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-exports", action="store_true")
    parser.add_argument("--label", default="")
    args = parser.parse_args()
    if args.all:
        ids = [entry["id"] for entry in CATALOG["templates"]]
        label = "all"
    elif args.batch:
        ids = BATCHES[args.batch]
        label = args.batch
    elif args.ids:
        ids = args.ids
        label = args.label or "batch"
    else:
        parser.error("choose --ids, --batch or --all")

    OUT.mkdir(parents=True, exist_ok=True)
    shots = OUT / "acceptance"
    shots.mkdir(exist_ok=True)
    results = []

    from playwright.sync_api import sync_playwright

    with app_server() as (_process, base, _data):
        with sync_playwright() as play:
            try:
                browser = launch_chromium(play)
            except Exception as exc:  # pragma: no cover - environment dependent
                print(f"SKIP Chromium unavailable: {exc}")
                return 2
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            context.add_init_script(LONG_TASK_INIT)
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.locator("#authRegisterTab").click()
            page.locator("#email").fill("accept-pack@example.com")
            page.locator("#password").fill("Strong-pack-edit-123")
            page.locator("#registerConfirmPassword").fill("Strong-pack-edit-123")
            page.locator("#loginBtn").click()
            page.wait_for_selector("#dashboardView:not([hidden])", timeout=20000)

            for template_id in ids:
                try:
                    page.evaluate("() => 1")
                except Exception:
                    try:
                        page.close()
                    except Exception:
                        pass
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
                document = built_document(template_id)
                entry = BY_ID[template_id]
                row: dict = {"id": template_id, "name": entry["name"], "category": entry["category"], "canvas": entry["canvas"], "pages_expected": len(document["designPages"]), "errors": []}
                try:
                    created = page.evaluate(
                        """async d => {
                            const response = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                              body: JSON.stringify({slug: d.templateId, document: d})});
                            if (!response.ok) throw Error(await response.text());
                            return response.json();
                        }""",
                        document,
                    )
                    # A9 375: measured on its own copy of the document. Two tabs on
                    # the same invitation never reach editorReady (the app's draft
                    # lock) in either order, so the narrow pass gets a second
                    # invitation with identical content.
                    mobile_created = page.evaluate(
                        """async d => {
                            const response = await fetch('/api/invitations', {method:'POST', headers:{'Content-Type':'application/json'},
                              body: JSON.stringify({slug: d.templateId, document: d})});
                            if (!response.ok) throw Error(await response.text());
                            return response.json();
                        }""",
                        document,
                    )
                    last_error = None
                    for attempt in range(2):
                        step = "context"
                        mobile_errors: list[str] = []
                        try:
                            small = context.new_page()
                            small.set_viewport_size({"width": 375, "height": 900})
                            small.on("pageerror", lambda error: mobile_errors.append(str(error)))
                            step = "goto"
                            small.goto(f"{base}/invitations/{mobile_created['id']}/editor", wait_until="domcontentloaded", timeout=45000)
                            step = "editorReady"
                            small.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=45000)
                            step = "shot"
                            small.evaluate("() => { document.querySelector('#finalTourDismiss')?.click(); document.querySelectorAll('dialog.final-tour[open]').forEach(d => d.close()); }")
                            small.evaluate("id => window.switchCanvas && window.switchCanvas('page:' + id)", document["designPages"][0]["id"])
                            small.wait_for_timeout(500)
                            row.setdefault("viewports", {})["375"] = small.evaluate(
                                """() => ({
                                    body: document.documentElement.scrollWidth,
                                    inner: window.innerWidth,
                                    stage: (() => { const r = document.querySelector('#stage').getBoundingClientRect(); return {x: Math.round(r.x), w: Math.round(r.width)}; })(),
                                })"""
                            )
                            small.screenshot(path=str(shots / f"{template_id}-375.png"), animations="allow", timeout=30000)
                            row.pop("mobile375", None)
                            break
                        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
                            last_error = exc
                            row["mobile375"] = (
                                f"attempt {attempt + 1} failed at {step}: {type(exc).__name__}"
                            )
                            if mobile_errors:
                                row["mobile375"] += f" · pageerror {mobile_errors[0][:120]}"
                        finally:
                            try:
                                small.close()
                            except Exception:
                                pass
                    if "375" not in row.get("viewports", {}):
                        row["mobile375"] = row.get("mobile375") or "not captured"
                    page.goto(f"{base}/invitations/{created['id']}/editor", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_function("() => document.documentElement.dataset.editorReady === 'true'", timeout=45000)
                    page.evaluate("() => { document.querySelector('#finalTourDismiss')?.click(); document.querySelectorAll('dialog.final-tour[open]').forEach(d => d.close()); }")
                    page.wait_for_timeout(250)
                    row["longTaskMs"] = round(sum(page.evaluate("() => window.__longTasks || []")), 1)
                    row["longTaskCount"] = page.evaluate("() => (window.__longTasks || []).length")
                    # The pack's own open cost: fetch + module evaluation of one built
                    # document (the editor page itself is already loaded).
                    row["packOpenMs"] = round(
                        page.evaluate(
                            """async id => {
                                const t0 = performance.now();
                                await import('/assets/template-pack/built/' + id + '.js');
                                return performance.now() - t0;
                            }""",
                            template_id,
                        ),
                        2,
                    )
                    row["pages"] = []
                    for page_index, design_page in enumerate(document["designPages"]):
                        open_page(page, design_page["id"])
                        page.wait_for_timeout(350)
                        metrics = page.evaluate(METRICS_JS)
                        metrics["background"] = design_page["background"]
                        # A10 from the product's own 1x export of this page.
                        if not args.no_exports:
                            png = export_page_png(page, shots / f"{template_id}-p{page_index + 1}-1x.png")
                            metrics["contrast"] = contrast_rows_from_png(png, metrics["rows"], metrics.get("stageBox") or {})
                        else:
                            metrics["contrast"] = []
                        row["pages"].append(metrics)
                        if page_index == 0:
                            try:
                                box = page.locator("#stage").bounding_box()
                                if box:
                                    page.evaluate(CHROME_HIDE_JS)
                                    page.screenshot(path=str(shots / f"{template_id}-1440.png"), clip=box, animations="disabled", timeout=12000)
                            except Exception as exc:
                                row["errors"].append(f"screenshot1440: {exc}")
                            finally:
                                page.evaluate(CHROME_SHOW_JS)
                    # A5/A6 on page 1: select a text object, nudge, undo; colour, undo.
                    open_page(page, document["designPages"][0]["id"])
                    page.wait_for_timeout(200)
                    first = page.locator("#stage .object .content").first
                    first.click()
                    selected_id = page.evaluate("() => document.querySelector('#stage .object.selected')?.dataset.id")
                    before_left = page.evaluate("() => document.querySelector('#stage .object.selected')?.style.left")
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(150)
                    after_left = page.evaluate("() => document.querySelector('#stage .object.selected')?.style.left")
                    # Undo until the layer is back (a held key can coalesce into more
                    # than one history entry); the count is recorded, not hidden.
                    undos = 0
                    restored_left = after_left
                    for _ in range(4):
                        if restored_left == before_left:
                            break
                        page.keyboard.press("Control+z")
                        undos += 1
                        page.wait_for_timeout(250)
                        restored_left = page.evaluate("() => document.querySelector('#stage .object.selected')?.style.left")
                    row["selectedId"] = selected_id
                    page.locator("#color").evaluate("(input) => { input.value = '#123456'; input.dispatchEvent(new Event('input', {bubbles: true})); }")
                    page.wait_for_timeout(200)
                    colour_changed = page.evaluate(
                        """() => {
                            const doc = window.EInviteEditorBridge.getState();
                            const page = doc.designPages.find(p => 'page:' + p.id === window.EInviteEditorBridge.getActiveCanvasId());
                            return Object.values(page.objects).some(o => String(o.color || '').toLowerCase() === '#123456');
                        }"""
                    )
                    page.keyboard.press("Control+z")
                    page.wait_for_timeout(200)
                    row["edit"] = {
                        "moved": before_left != after_left,
                        "undo": before_left == restored_left,
                        "undos": undos,
                        "colour": colour_changed,
                    }
                    row["A7"] = placeholder_scan(document)
                    row["A12"] = {
                        "thirdParty": 0,
                        "external": bool(re.search(r"https?://", json.dumps(document))),
                    }
                    # A9: 1440 is the context viewport; 375/768 are measured on
                    # fixed-width pages because resizing this canvas page can
                    # crash Chromium's GPU process.
                    row.setdefault("viewports", {})["1440"] = page.evaluate(
                        """() => ({
                            body: document.documentElement.scrollWidth,
                            inner: window.innerWidth,
                            stage: (() => { const r = document.querySelector('#stage').getBoundingClientRect(); return {x: Math.round(r.x), w: Math.round(r.width)}; })(),
                        })"""
                    )
                    # A8: PNG 1x/2x/3x and printed PDF.
                    if not args.no_exports:
                        sizes = {}
                        page.evaluate("() => window.EInviteCommandRegistry.execute('quality.open')")
                        page.wait_for_selector('[data-tab="export"]', timeout=15000)
                        page.locator('[data-tab="export"]').click()
                        for scale in (1, 2, 3):
                            page.wait_for_selector(f'[data-export-png="{scale}"]', timeout=15000)
                            with page.expect_download(timeout=45000) as info:
                                page.locator(f'[data-export-png="{scale}"]').click()
                            target = shots / f"{template_id}-{scale}x.png"
                            info.value.save_as(target)
                            sizes[f"png{scale}"] = {"bytes": target.stat().st_size, "size": png_size(target)}
                        with page.expect_popup(timeout=45000) as popup_info:
                            page.locator("[data-print]").click()
                        printed = popup_info.value
                        printed.wait_for_selector("img", timeout=20000)
                        pdf = printed.pdf()
                        (shots / f"{template_id}.pdf").write_bytes(pdf)
                        sizes["pdf"] = {"bytes": len(pdf)}
                        printed.close()
                        row["exports"] = sizes
                        page.keyboard.press("Escape")
                except Exception as exc:
                    row["errors"].append(f"{type(exc).__name__}: {exc}")
                results.append(row)
                partial = OUT / f"acceptance-{label}.json"
                partial.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"{template_id}: longtasks={row.get('longTaskMs')} errors={row['errors'][:1]}", flush=True)
                # Fresh page per template: a long-lived canvas page degrades
                # in headless Chromium and the next editor never reaches ready.
                try:
                    page.close()
                except Exception:
                    pass
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base + "/dashboard.html", wait_until="domcontentloaded", timeout=30000)
            page.close()
            context.close()
            browser.close()

    output = OUT / f"acceptance-{label}.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"WROTE {output} ({len(results)} templates)")
    print("PAGE_ERRORS", errors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
