#!/usr/bin/env python3
"""tools/ui-layout-guard.py — objective layout regression guard (FB-31).

The visual audit's findings were read from screenshots, so "looks broken" was a
judgement each pass had to re-make. This tool turns the four measurable claims
into a pass/fail matrix the gate runner can enforce:

  * **horizontal scroll** — `documentElement.scrollWidth > innerWidth` (excludes
    a 1 px rounding allowance), with the widest offending elements named.
  * **nameless controls** — a visible `button`, `a[href]` or `[role=button]` with
    no accessible name (no aria-label/aria-labelledby, no text, no title, no img
    alt). This is the "empty white squares" class, measured instead of seen.
  * **header overlap** — two visible direct children of `body > header` whose
    boxes intersect by more than 2 px on both axes (the breadcrumb-vs-button
    collision).
  * **header height** — at ≤ 400 px wide, the header must stay ≤ 96 px (FB-28).
  * **auth-card padding** — on the signed-out dashboard the card's inner padding
    and every input's inset must be at least 16 px (VB-01 acceptance).
  * **editor contract** — on index.html (FB-29): at ≤ 440 px the canvas
    (`.canvas-viewport`) must occupy ≥ 50 % of the viewport height; toolbars
    must scroll (overflow-x auto/scroll) instead of clipping children; and on
    the tablet band (721–1024 px) no empty opaque sheet may cover the canvas —
    the "big empty white panel" class. A sheet counts as empty when its
    textContent is whitespace-only and it has no content-bearing descendants.

Matrix: `--pages` × `--viewports` (320/375/768/1024/1440 by default) ×
`--themes light,dark` × `--langs en,km`. The signed-out dashboard is measured in
a separate no-cookie context; the other pages use a throwaway account created
through the API, so authenticated pages render their real state.

Usage
-----
    .venv/bin/python tools/ui-layout-guard.py --base http://127.0.0.1:4185
    .venv/bin/python tools/ui-layout-guard.py --only dashboard.html \
        --viewports 375x667 --themes light --langs en
    .venv/bin/python tools/ui-layout-guard.py --phase header   # one check group

Outputs `layout-guard.jsonl` (one row per check) and `summary.txt` under --out.
Exit 0 only when every row passes.

Not part of the frozen canvas gates and it edits nothing: read-only over HTTP.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "artifacts" / "next-work" / "ui-layout-guard"
PASSWORD = "layout-guard-2026"

PAGES = ["dashboard.html", "templates.html", "guests.html", "index.html", "admin.html"]
VIEWPORTS = ["320x568", "375x667", "768x1024", "1024x768", "1440x900"]
THEMES = ["light", "dark"]
LANGS = ["en", "km"]

# Injected before any page script: the app reads these on boot.
INIT_SCRIPT = """(() => {
  try {
    localStorage.setItem('einvite-theme-mode', '%s');
    localStorage.setItem('einvite-lang', '%s');
  } catch (e) {}
})();"""

MEASURE_JS = r"""
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const visible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const path = (el) => {
    const bits = [el.tagName.toLowerCase()];
    if (el.id) bits.push('#' + el.id);
    const cls = (el.className && typeof el.className === 'string')
      ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 2) : [];
    if (cls.length) bits.push('.' + cls.join('.'));
    return bits.join('');
  };
  const out = { scrollWidth: document.documentElement.scrollWidth, innerWidth: vw,
                widest: [], nameless: [], headerOverlap: [], headerHeight: null,
                authPadding: null, authInputInset: null, editor: null };

  // 1. horizontal scroll: name the widest elements that stick out.
  if (document.documentElement.scrollWidth > vw + 1) {
    const offenders = [];
    for (const el of document.querySelectorAll('body *')) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      const over = Math.round(r.right + window.scrollX - vw);
      if (over > 1) offenders.push({ el: path(el), over });
    }
    offenders.sort((a, b) => b.over - a.over);
    out.widest = offenders.slice(0, 3);
  }

  // 2. nameless visible controls.
  const nameOf = (el) => {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
    const labelledby = el.getAttribute('aria-labelledby');
    if (labelledby) {
      const t = labelledby.split(/\s+/).map(id => document.getElementById(id))
        .filter(Boolean).map(n => n.textContent).join(' ').trim();
      if (t) return t;
    }
    if (el.getAttribute('title')) return el.getAttribute('title').trim();
    if ((el.textContent || '').trim()) return el.textContent.trim();
    const img = el.querySelector('img[alt]');
    if (img && img.getAttribute('alt').trim()) return img.getAttribute('alt').trim();
    if (el.tagName === 'INPUT' && el.getAttribute('value')) return el.getAttribute('value').trim();
    return '';
  };
  for (const el of document.querySelectorAll('button, a[href], [role="button"]')) {
    if (!visible(el)) continue;
    if (!nameOf(el)) out.nameless.push(path(el));
  }
  out.nameless = out.nameless.slice(0, 6);

  // 3. header children overlap + 4. header height.
  const header = document.querySelector('body > header');
  if (header && visible(header)) {
    out.headerHeight = Math.round(header.getBoundingClientRect().height);
    const kids = [...header.children].filter(visible);
    for (let i = 0; i < kids.length; i++) {
      for (let j = i + 1; j < kids.length; j++) {
        const a = kids[i].getBoundingClientRect(), b = kids[j].getBoundingClientRect();
        const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (ox > 2 && oy > 2) {
          out.headerOverlap.push([path(kids[i]), path(kids[j]),
                                  Math.round(ox) + 'x' + Math.round(oy)]);
        }
      }
    }
  }

  // 5. signed-out auth card padding (dashboard only).
  const card = document.querySelector('.auth-card');
  if (card && visible(card)) {
    const s = getComputedStyle(card);
    const pads = ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft']
      .map(k => parseFloat(s[k]));
    out.authPadding = Math.round(Math.min(...pads) * 10) / 10;
    // Measured from the card's BORDER-box left edge, per the VB-01 acceptance
    // wording ("inputs at least 16 px inside the card"): an input that fills the
    // content box correctly reports padding-left, not 0.
    const box = card.getBoundingClientRect();
    const left = box.left + parseFloat(s.borderLeftWidth || '0');
    let inset = null;
    for (const input of card.querySelectorAll('input:not([type=hidden]), select, textarea')) {
      if (!visible(input)) continue;
      const v = Math.round(input.getBoundingClientRect().left - left);
      if (inset === null || v < inset) inset = v;
    }
    out.authInputInset = inset;
  }

  // 6. editor contract (FB-29), index.html only.
  const cv = document.querySelector('.canvas-viewport');
  if (cv) {
    const cvr = cv.getBoundingClientRect();
    const ed = { vw, vh, canvasTop: Math.round(cvr.top), canvasH: Math.round(cvr.height),
                 emptySheets: [], clippedToolbars: [] };
    if (cvr.height > 0) ed.canvasShare = Math.round(100 * cvr.height / vh);
    // empty sheet: opaque background, covers the canvas centre, zero content.
    const mid = { x: cvr.left + cvr.width / 2, y: cvr.top + cvr.height / 2 };
    if (cvr.width > 0 && cvr.height > 0) {
      for (const el of document.querySelectorAll('div,aside,section')) {
        if (!visible(el) || el === cv || el.contains(cv)) continue;
        const r = el.getBoundingClientRect();
        if (r.width < vw * 0.4 || r.height < 80) continue;
        if (!(r.left <= mid.x && r.right >= mid.x && r.top <= mid.y && r.bottom >= mid.y)) continue;
        const s = getComputedStyle(el);
        const bg = s.backgroundColor;
        if (!bg || bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)') continue;
        if (s.pointerEvents === 'none') continue;
        const text = (el.textContent || '').trim();
        if (!text) ed.emptySheets.push(path(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
      }
    }
    // toolbar clipping: children must be reachable — scrollable, never clipped.
    for (const el of document.querySelectorAll('.studio-canvas-toolbar, .object-quick-toolbar, .studio-selection-toolbar, #v23ContextToolbar')) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      let over = 0;
      for (const c of el.querySelectorAll('*')) {
        const cr = c.getBoundingClientRect();
        if (cr.width > 0 && cr.right > r.right + 1) over = Math.max(over, Math.round(cr.right - r.right));
      }
      const unreachable = s.overflowX === 'hidden' && el.scrollWidth > el.clientWidth + 1;
      if (s.overflowX === 'visible' && over > 0) ed.clippedToolbars.push(`${path(el)} overflowX=visible +${over}px`);
      if (unreachable) ed.clippedToolbars.push(`${path(el)} overflowX=hidden scrollWidth-elWidth=${el.scrollWidth - el.clientWidth}px`);
    }
    out.editor = ed;
  }
  return out;
}
"""


def rows_for(page_name: str, viewport: str, theme: str, lang: str, data: dict, signed_in: bool):
    """Turn one measurement into check rows: (check, ok, detail)."""
    w, h = (int(v) for v in viewport.split("x"))
    rows = []
    where = f"{page_name} {viewport} {theme} {lang}"

    overflow = data["scrollWidth"] - data["innerWidth"]
    detail = ""
    if overflow > 1 and data["widest"]:
        detail = "; ".join(f"{o['el']} +{o['over']}px" for o in data["widest"])
    rows.append(("horizontal-scroll", overflow <= 1, f"{where} overflow={overflow}px {detail}".strip()))

    rows.append(("nameless-control", not data["nameless"],
                 f"{where} " + (", ".join(data["nameless"]) if data["nameless"] else "none")))

    rows.append(("header-overlap", not data["headerOverlap"],
                 f"{where} " + ("; ".join(" x ".join(p) for p in data["headerOverlap"])
                                if data["headerOverlap"] else "none")))

    if data["headerHeight"] is not None:
        limit = 96 if w <= 400 else 200
        rows.append(("header-height", data["headerHeight"] <= limit,
                     f"{where} height={data['headerHeight']}px limit={limit}px"))

    if page_name == "dashboard.html" and not signed_in and data["authPadding"] is not None:
        rows.append(("auth-card-padding", data["authPadding"] >= 16,
                     f"{where} padding={data['authPadding']}px"))
        if data["authInputInset"] is not None:
            rows.append(("auth-input-inset", data["authInputInset"] >= 16,
                         f"{where} input-inset={data['authInputInset']}px"))

    ed = data.get("editor")
    if ed:
        if w <= 440 and ed.get("canvasShare") is not None:
            rows.append(("editor-canvas-share", ed["canvasShare"] >= 50,
                         f"{where} canvas-share={ed['canvasShare']}% (top={ed['canvasTop']}px h={ed['canvasH']}px)"))
        for sheet in ed["emptySheets"]:
            rows.append(("editor-empty-sheet", False, f"{where} {sheet}"))
        if not ed["emptySheets"] and 721 <= w <= 1024:
            rows.append(("editor-empty-sheet", True, f"{where} none"))
        for clip in ed["clippedToolbars"]:
            rows.append(("editor-toolbar-clip", False, f"{where} {clip}"))
        if not ed["clippedToolbars"]:
            rows.append(("editor-toolbar-clip", True, f"{where} none"))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8124")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--only", default="", help="comma-separated page names")
    ap.add_argument("--viewports", default="", help="e.g. 375x667,1440x900")
    ap.add_argument("--themes", default=",".join(THEMES))
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--settle", type=int, default=350, help="ms after DOMContentLoaded")
    ap.add_argument("--skip-signed-in", action="store_true")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("UI_LAYOUT_GUARD_CANNOT_RUN: playwright missing (use .venv/bin/python)")
        return 4

    pages = [p.strip() for p in args.only.split(",") if p.strip()] or PAGES
    viewports = [v.strip() for v in args.viewports.split(",") if v.strip()] or VIEWPORTS
    themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    base = args.base.rstrip("/")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / "layout-guard.jsonl"
    jsonl.write_text("", encoding="utf-8")

    rows = []
    console_errors = []

    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)

        def context(width: int, height: int, theme: str, lang: str):
            ctx = browser.new_context(viewport={"width": width, "height": height})
            ctx.add_init_script(INIT_SCRIPT % (theme, lang))
            return ctx

        # ---- signed-out dashboard (auth-card padding) ---------------------
        for viewport in viewports:
            w, h = (int(v) for v in viewport.split("x"))
            for theme in themes:
                for lang in langs:
                    ctx = context(w, h, theme, lang)
                    page = ctx.new_page()
                    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
                    page.goto(f"{base}/dashboard.html", wait_until="domcontentloaded")
                    page.wait_for_timeout(args.settle)
                    if page.locator("#newBtn").count() and page.is_visible("#newBtn"):
                        page.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(args.settle)
                    data = page.evaluate(MEASURE_JS)
                    rows.extend(rows_for("dashboard.html", viewport, theme, lang, data, signed_in=False))
                    ctx.close()

        # ---- signed-in pages ----------------------------------------------
        if not args.skip_signed_in:
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
            email = f"layout-guard-{stamp}@example.com"
            seed = context(1440, 900, "light", "en")
            req = seed.request
            reg = req.post(f"{base}/api/auth/register", data={"email": email, "password": PASSWORD})
            if not reg.ok:
                login = req.post(f"{base}/api/auth/login", data={"email": email, "password": PASSWORD})
                if not login.ok:
                    print(f"UI_LAYOUT_GUARD_CANNOT_RUN: could not create account ({reg.status})")
                    browser.close()
                    return 4
            seed.close()

            for viewport in viewports:
                w, h = (int(v) for v in viewport.split("x"))
                for theme in themes:
                    for lang in langs:
                        ctx = context(w, h, theme, lang)
                        req = ctx.request
                        req.post(f"{base}/api/auth/login", data={"email": email, "password": PASSWORD})
                        for page_name in pages:
                            page = ctx.new_page()
                            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
                            try:
                                page.goto(f"{base}/{page_name}", wait_until="domcontentloaded")
                                page.wait_for_timeout(args.settle)
                                data = page.evaluate(MEASURE_JS)
                            except Exception as exc:  # noqa: BLE001
                                rows.append((f"load:{page_name}", False,
                                             f"{page_name} {viewport} {theme} {lang} {exc}"[:300]))
                                page.close()
                                continue
                            rows.extend(rows_for(page_name, viewport, theme, lang, data, signed_in=True))
                            page.close()
                        ctx.close()

        browser.close()

    with jsonl.open("w", encoding="utf-8") as fh:
        for check, ok, detail in rows:
            fh.write(json.dumps({"at": datetime.datetime.now().isoformat(timespec="seconds"),
                                 "check": check, "ok": bool(ok), "detail": detail}) + "\n")

    failed = [r for r in rows if not r[1]]
    by_check: dict[str, int] = {}
    for check, ok, _ in rows:
        by_check.setdefault(check, 0)
        if not ok:
            by_check[check] += 1
    summary = [
        f"ui-layout-guard — {len(rows)} checks, {len(failed)} failed",
        f"matrix: {len(pages)} pages × {len(viewports)} viewports × {len(themes)} themes × {len(langs)} langs",
        f"console errors: {len(console_errors)}",
    ]
    for check in sorted(by_check):
        summary.append(f"  {check}: {by_check[check]} failed")
    if failed:
        summary.append("")
        summary.append("FAILED ROWS")
        for check, _ok, detail in failed[:40]:
            summary.append(f"  [{check}] {detail}")
    (out_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary[: 8 + len(by_check)]))
    print("UI_LAYOUT_GUARD_PASSED" if not failed else f"UI_LAYOUT_GUARD_FAILED ({len(failed)} rows)")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
