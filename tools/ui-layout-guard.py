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
  * **Khmer face** (LT-1.5) — a fixed set of chrome labels on every route must
    declare the app's `EInvite` Khmer stack, paint with a bundled face (CDP
    `CSS.getPlatformFontsForNode`), and keep line-height ≥ 1.6.
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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "artifacts" / "next-work" / "ui-layout-guard"
DEFAULT_BASELINE = ROOT / "tools" / "ui-layout-guard.console-baseline.json"
PASSWORD = "layout-guard-2026"

# FB-45 (guard v3): checkin + designer joined the matrix — both passed with zero console
# errors before being added (375/1440, light, en), so this is coverage, not a fix.
PAGES = ["dashboard.html", "templates.html", "guests.html", "index.html", "admin.html",
         "checkin.html", "designer.html"]

# FB-45: long-task ceiling, measured before it was set. Worst single task at 1440 on this
# machine: dashboard 137ms, materials 201ms, checkin 146ms, designer 186ms, editor 498ms.
# 600 leaves the editor headroom while still failing on a real main-thread regression.
LONG_TASK_MAX_MS = 600
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

# FB-45: collected from document start so the boot script itself is counted, not just what
# happens after the settle. The selftest fixture ships a deliberate 700ms task to prove the
# check fires.
LONG_TASK_JS = """(() => {
  window.__longTasks = [];
  try {
    new PerformanceObserver(list => {
      for (const e of list.getEntries()) window.__longTasks.push(Math.round(e.duration));
    }).observe({type: 'longtask', buffered: true});
  } catch (e) {}
})();"""

# LT-1.5: a fixed set of chrome labels that exists on every signed-in route.
# Each one must resolve through the app's own --font-khmer/--font-display-km stack
# (declared family starts with "EInvite") AND actually paint with the bundled face;
# a route whose bundle lacks the @font-face declares the family but silently falls
# back to a system Khmer font, which is exactly the V3 defect.
KHMER_FONT_JS = r"""
() => {
  const sel = '.skip-link [lang="km"], .app-brand [lang="km"], .app-crumbs [lang="km"], ' +
              '.app-rail [lang="km"], .app-topbar-right [lang="km"], ' +
              '.language-switch button[lang="km"], .studio-topbar [lang="km"], ' +
              '.guest-topbar [lang="km"]';
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    if (out.length >= 10) break;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim())) continue;
    el.setAttribute('data-guard-font', String(out.length));
    const size = parseFloat(s.fontSize) || 16;
    const lh = s.lineHeight === 'normal' ? null : parseFloat(s.lineHeight);
    out.push({ i: out.length, text: (el.textContent || '').trim().slice(0, 24),
               family: s.fontFamily, weight: s.fontWeight, size,
               ratio: lh ? +(lh / size).toFixed(2) : null });
  }
  return out;
}
"""

MEASURE_JS = r"""
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  // A control can have a visible computed style and a non-zero rect while its
  // ancestor is clipped out of the render tree. The editor keeps the raw
  // section-order textarea inside `.ei-raw-field` (position:absolute; 1x1;
  // overflow:hidden; clip-path:inset(50%)) as a fallback for the visual builder.
  // checkVisibility() does not reject that ancestor, so skip the clipped
  // subtree explicitly rather than reporting its inner textarea as a clipped
  // user-facing field.
  const hiddenByClippedAncestor = (el) => {
    for (let n = el.parentElement; n && n !== document.documentElement; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return true;
      if ((s.overflowX === 'hidden' || s.overflowX === 'clip') &&
          (s.overflowY === 'hidden' || s.overflowY === 'clip') &&
          n.clientWidth <= 1 && n.clientHeight <= 1) return true;
      if (s.clip && s.clip !== 'auto' && s.clip.includes('rect(0')) return true;
      if (s.clipPath && s.clipPath !== 'none' && s.clipPath.includes('inset(50%')) return true;
    }
    return false;
  };
  const visible = (el) => {
    if (hiddenByClippedAncestor(el)) return false;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    // Chromium still reports a non-zero rect for a control inside a closed
    // <details> (or a content-visibility subtree) even though it is not
    // rendered — innerText is empty and checkVisibility() is false. Counting
    // those as visible made the Page group's folded cards read as empty
    // buttons. Ask the engine whether the element is actually rendered.
    if (typeof el.checkVisibility === 'function'
        && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const onScreen = (el) => {
    const r = el.getBoundingClientRect();
    return r.right > 0 && r.left < window.innerWidth && r.bottom > 0 && r.top < window.innerHeight;
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
                authPadding: null, authInputInset: null, editor: null,
                emptyControls: [], clippedFields: [], emptyPills: [],
                longTasks: (window.__longTasks || []).slice() };

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

  // 2b. empty-looking controls (FB-38): a visible bordered button/square that
  // paints nothing — no text, no svg/img/canvas, no background image, no painted
  // child. The old "empty squares" were buttons whose only glyph span was
  // display:none, so innerText is the right emptiness test (it ignores hidden
  // descendants); aria-label does NOT make a control look non-empty.
  const paints = (el) => {
    const s = getComputedStyle(el);
    for (const pseudo of ['::before', '::after']) {
      const ps = getComputedStyle(el, pseudo);
      const c = ps.content;
      if (c && c !== 'none' && c !== 'normal' && c !== '""') return true;
    }
    if (s.backgroundImage && s.backgroundImage !== 'none') return true;
    if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent') return true;
    if (s.boxShadow && s.boxShadow !== 'none') return true;
    return ['Top', 'Right', 'Bottom', 'Left'].some((side) => {
      const w = parseFloat(s['border' + side + 'Width']) || 0;
      const style = s['border' + side + 'Style'];
      return w > 0 && style && style !== 'none';
    });
  };
  const isScroller = (el) => {
    let n = el.parentElement;
    while (n && n !== document.documentElement) {
      const s = getComputedStyle(n);
      if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && n.scrollWidth > n.clientWidth + 1) return true;
      n = n.parentElement;
    }
    return false;
  };
  for (const el of document.querySelectorAll('button, [role="button"], a[href]')) {
    if (!visible(el) || !onScreen(el) || !paints(el)) continue;
    if ((el.innerText || '').trim()) continue;
    if (el.querySelector('svg, img, canvas, use, picture, video')) continue;
    const kidsPaint = [...el.querySelectorAll('*')].some((k) => {
      if (!visible(k)) return false;
      return paints(k) || (k.innerText || '').trim();
    });
    if (!kidsPaint) out.emptyControls.push(path(el));
  }
  out.emptyControls = out.emptyControls.slice(0, 6);

  // 2c. controls clipped by their own box (FB-38): an input/select whose text is
  // cut is fine inside a horizontally scrolling strip (that strip advertises the
  // overflow), but a hard clip is a defect.
  for (const el of document.querySelectorAll('input:not([type=hidden]), select, textarea')) {
    if (!visible(el) || !onScreen(el)) continue;
    if (el.scrollWidth > el.clientWidth + 1 && !isScroller(el)) {
      const label = el.id || el.getAttribute('name') || el.getAttribute('type') || '';
      const host = el.closest('section,form,aside,fieldset');
      const hostPath = host ? ' in ' + path(host) : '';
      out.clippedFields.push(path(el) + (label && !el.id ? '#' + label : '') + hostPath +
                              ' sw=' + el.scrollWidth + ' cw=' + el.clientWidth);
    }
  }
  out.clippedFields = out.clippedFields.slice(0, 6);

  // 2d. unreadable pills (LT-1.4): a badge/pill whose text is painted but cannot be
  // read — white on a white surface (the dashboard's blank "Draft" pill), or text
  // clipped by its own box (the 6px-tall badge). Contrast is composited through
  // alpha surfaces, so color(srgb … / .88) and color-mix() backgrounds work.
  const parseColor = (value) => {
    if (!value) return null;
    let m = value.match(/^rgba?\(([^)]+)\)$/);
    if (m) {
      const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
      if (p.length >= 3) return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
    }
    m = value.match(/^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\)$/);
    if (m) return [255 * Number(m[1]), 255 * Number(m[2]), 255 * Number(m[3]),
                   m[4] == null ? 1 : Number(m[4])];
    if (value === 'transparent') return [0, 0, 0, 0];
    return null;
  };
  const over = (fg, bg) => {
    const a = fg[3] + bg[3] * (1 - fg[3]);
    if (a === 0) return [0, 0, 0, 0];
    const mix = (i) => (fg[i] * fg[3] + bg[i] * bg[3] * (1 - fg[3])) / a;
    return [mix(0), mix(1), mix(2), a];
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const effectiveBg = (el) => {
    const layers = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parseColor(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) layers.push(c);
      if (c && c[3] >= 1) break;
    }
    let bg = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) bg = over(layers[i], bg);
    return bg;
  };
  for (const el of document.querySelectorAll('.app-badge, .invite-status-pill, .fp-project-status, .badge, .pill')) {
    if (!visible(el) || !onScreen(el)) continue;
    if (!(el.innerText || '').trim()) continue;
    const s = getComputedStyle(el);
    const bg = effectiveBg(el);
    const fg = over(parseColor(s.color) || [0, 0, 0, 1], bg);
    const l1 = lum(fg), l2 = lum(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const clipped = el.scrollHeight > el.clientHeight + 2 && s.overflow !== 'visible';
    if (ratio < 1.5 || clipped) {
      out.emptyPills.push(path(el) + ' contrast=' + ratio.toFixed(2) +
        ' box=' + Math.round(el.clientWidth) + 'x' + Math.round(el.clientHeight) +
        ' text=' + Math.round(el.scrollWidth) + 'x' + Math.round(el.scrollHeight) +
        (clipped ? ' clipped' : ''));
    }
  }
  out.emptyPills = out.emptyPills.slice(0, 6);

  // 3. header children overlap + 4. header height.
  const header = document.querySelector('body > header');
  if (header && visible(header)) {
    out.headerHeight = Math.round(header.getBoundingClientRect().height);
    // 3b. UX-1: every visible header control must be reachable. The shell keeps
    // ONE row at the design height on phones and scrolls horizontally (VB-02/FB-28),
    // so "reachable" means inside the header's scrollable content box — not inside
    // the viewport at scrollLeft 0. A bar that clips instead (overflow not
    // auto/scroll) is the defect this cell exists to catch.
    const hs = getComputedStyle(header);
    const hr = header.getBoundingClientRect();
    const scrollable = (hs.overflowX === 'auto' || hs.overflowX === 'scroll') &&
                       header.scrollWidth > header.clientWidth + 1;
    const limit = scrollable ? hr.left + header.scrollWidth : hr.right;
    out.headerScrollable = scrollable;
    out.topbarClipped = [];
    for (const el of header.querySelectorAll('*')) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.right <= limit + 1) continue;
      out.topbarClipped.push(path(el) + ' right=' + Math.round(r.right) +
                             ' limit=' + Math.round(limit));
    }
    out.topbarClipped = out.topbarClipped.slice(0, 6);
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
    // FB-38: artboard visibility at ≤480 — the fitted artboard must sit fully
    // inside the canvas viewport and the floating palette must stay off it.
    const art = document.querySelector('#stage');
    const pal = document.querySelector('nav.ei-tool-rail') || document.querySelector('.ei-tool-rail');
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
    if (art) {
      const ar = art.getBoundingClientRect();
      if (ar.width > 0 && ar.height > 0) {
        ed.artboardInside = ar.left >= cvr.left - 1 && ar.right <= cvr.right + 1 &&
                            ar.top >= cvr.top - 1 && ar.bottom <= cvr.bottom + 1;
        ed.artboard = { x: Math.round(ar.left), y: Math.round(ar.top),
                        w: Math.round(ar.width), h: Math.round(ar.height) };
        if (pal && visible(pal)) {
          const pr = pal.getBoundingClientRect();
          const ox = Math.max(0, Math.min(ar.right, pr.right) - Math.max(ar.left, pr.left));
          const oy = Math.max(0, Math.min(ar.bottom, pr.bottom) - Math.max(ar.top, pr.top));
          ed.paletteOverlapPct = Math.round(1000 * ox * oy / (ar.width * ar.height)) / 10;
        } else {
          ed.paletteOverlapPct = 0;
        }
      }
    }
    out.editor = ed;
  }
  return out;
}
"""


def load_seed(path: str) -> dict:
    """Read the pinned-seed preset (slug/invite_id) the audit tooling reuses."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — the guard still runs without a public page
        return {}


def load_console_patterns(path: str) -> list[str]:
    """Console-baseline patterns: substrings, or `re:<regex>` entries."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — no file means every console error fails
        return []
    patterns = data.get("patterns", data if isinstance(data, list) else [])
    return [p for p in patterns if isinstance(p, str)]


def console_matches(message: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.startswith("re:"):
            try:
                if re.search(pat[3:], message):
                    return True
            except re.error:
                continue
        elif pat in message:
            return True
    return False


def collect_font_rows(ctx, page, where: str) -> list[tuple[str, bool, str]]:
    """LT-1.5: every fixed chrome label must paint with the bundled Khmer face and
    carry the Khmer line box. Returns one `khmer-face` row."""
    try:
        samples = page.evaluate(KHMER_FONT_JS)
    except Exception as exc:  # noqa: BLE001
        return [("khmer-face", False, f"{where} probe failed: {str(exc)[:120]}")]
    if not samples:
        return [("khmer-face", True, f"{where} no fixed-set Khmer label")]
    cdp = ctx.new_cdp_session(page)
    cdp.send("DOM.enable")
    cdp.send("CSS.enable")
    doc = cdp.send("DOM.getDocument", {"depth": 0})
    bad = []
    for s in samples:
        node = cdp.send("DOM.querySelector", {
            "nodeId": doc["root"]["nodeId"],
            "selector": f'[data-guard-font="{s["i"]}"]'})
        used = []
        if node.get("nodeId"):
            try:
                used = cdp.send("CSS.getPlatformFontsForNode",
                                {"nodeId": node["nodeId"]}).get("fonts", [])
            except Exception as exc:  # noqa: BLE001
                used = [{"error": str(exc)[:80]}]
        bundled = [f for f in used if f.get("isCustomFont") and f.get("glyphCount")]
        declared = "EInvite Noto" in (s.get("family") or "")
        used_names = ",".join(str(f.get("postScriptName") or f.get("familyName") or
                                f.get("error") or "?") for f in used) or "none"
        reasons = []
        if not declared:
            reasons.append("declared=" + (s.get("family") or "")[:60])
        if not bundled:
            reasons.append("used=" + used_names)
        if s.get("ratio") is not None and s["ratio"] < 1.55:
            reasons.append(f"line-height={s['ratio']}")
        if reasons:
            bad.append(f"{s.get('text')} [{' '.join(reasons)}]")
    return [("khmer-face", not bad,
             f"{where} " + ("; ".join(bad) if bad else
                            f"{len(samples)} labels bundled, line-height ok"))]


def run_self_test() -> int:
    """FB-38 negative control: a deliberately broken fixture must fail each new
    check and produce the expected signature row. Exit 0 only when all fire."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("UI_LAYOUT_GUARD_CANNOT_RUN: playwright missing (use .venv/bin/python)")
        return 4
    fixture = ROOT / "tools" / "fixtures" / "ui-layout-guard-selftest.html"
    if not fixture.is_file():
        print(f"UI_LAYOUT_GUARD_SELFTEST_MISSING {fixture}")
        return 4
    errors: list[str] = []
    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 375, "height": 667})
        page = ctx.new_page()
        page.add_init_script(LONG_TASK_JS)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(fixture.as_uri(), wait_until="domcontentloaded")
        page.wait_for_timeout(150)
        data = page.evaluate(MEASURE_JS)
        font_rows = collect_font_rows(ctx, page, "selftest.html 375x667 light en")
        ctx.close()
        browser.close()
    rows = rows_for("selftest.html", "375x667", "light", "en", data, signed_in=False)
    rows.extend(font_rows)
    patterns = load_console_patterns(str(DEFAULT_BASELINE))
    console_fails = [m for m in errors if not console_matches(m, patterns)]
    failed_checks = {check for check, ok, _ in rows if not ok}
    expected = {"empty-control", "clipped-field", "empty-pill", "khmer-face",
                "editor-artboard", "long-task", "topbar-cluster-reachable"}
    print("SELFTEST negative control — deliberately broken fixture:")
    for check, ok, detail in rows:
        if not ok and check in expected:
            print(f"  [{check}] {detail}")
    for msg in console_fails:
        print(f"  [console-baseline] selftest.html :: {msg[:160]}")
    missing = expected - failed_checks
    if not console_fails:
        missing.add("console-baseline")
    if missing:
        print("UI_LAYOUT_GUARD_SELFTEST_FAILED missing=" + ",".join(sorted(missing)))
        return 1
    print("UI_LAYOUT_GUARD_SELFTEST_PASSED (empty-control, clipped-field, empty-pill, "
          "khmer-face, editor-artboard, long-task, topbar-cluster-reachable, "
          "console-baseline)")
    return 0


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

    # FB-38: empty-looking controls (bordered box with nothing painted).
    empties = data.get("emptyControls") or []
    if empties:
        for el in empties:
            rows.append(("empty-control", False, f"{where} {el}"))
    else:
        rows.append(("empty-control", True, f"{where} none"))

    # LT-1.4: badges/pills whose own text cannot be read (contrast or clipping).
    pills = data.get("emptyPills") or []
    if pills:
        for el in pills:
            rows.append(("empty-pill", False, f"{where} {el}"))
    else:
        rows.append(("empty-pill", True, f"{where} none"))

    # FB-38: inputs/selects clipped by their own box, outside a scrolling strip.
    clipped = data.get("clippedFields") or []
    if clipped:
        for el in clipped:
            rows.append(("clipped-field", False, f"{where} {el}"))
    else:
        rows.append(("clipped-field", True, f"{where} none"))

    rows.append(("header-overlap", not data["headerOverlap"],
                 f"{where} " + ("; ".join(" x ".join(p) for p in data["headerOverlap"])
                                if data["headerOverlap"] else "none")))

    # UX-1: the bar may scroll horizontally on a phone, but nothing may be clipped
    # by a non-scrollable edge. The editor keeps its own frozen header (canvas gate).
    clipped_top = data.get("topbarClipped")
    if clipped_top is not None and page_name != "index.html":
        rows.append(("topbar-cluster-reachable", not clipped_top,
                     f"{where} scrollable={data.get('headerScrollable')} " +
                     ("; ".join(clipped_top) if clipped_top else "none")))

    # FB-45: main-thread budget — one task over the ceiling is a real regression, not noise.
    tasks = data.get("longTasks") or []
    worst = max(tasks) if tasks else 0
    rows.append(("long-task", worst <= LONG_TASK_MAX_MS,
                 f"{where} max={worst}ms tasks={len(tasks)} ceiling={LONG_TASK_MAX_MS}ms"))

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

        # FB-38: ≤480 the fitted artboard must be fully inside the viewport and
        # the floating palette must not cover more than 10 % of it.
        if w <= 480 and ed.get("artboardInside") is not None:
            art = ed.get("artboard") or {}
            pct = ed.get("paletteOverlapPct")
            ok = bool(ed.get("artboardInside")) and (pct is None or pct <= 10)
            rows.append(("editor-artboard", ok,
                         f"{where} inside={ed.get('artboardInside')} "
                         f"stage={art.get('x')},{art.get('y')} {art.get('w')}x{art.get('h')} "
                         f"palette-overlap={pct}%"))
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
    ap.add_argument("--slug", default="", help="public invitation slug for /i/<slug> (default: seed preset)")
    ap.add_argument("--seed-preset", default=str(ROOT / "artifacts" / "next-work" / "fb-35" / "seed-preset.json"))
    ap.add_argument("--console-baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--self-test", action="store_true", help="run the negative-control fixture for the FB-38 checks")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("UI_LAYOUT_GUARD_CANNOT_RUN: playwright missing (use .venv/bin/python)")
        return 4

    if args.self_test:
        return run_self_test()

    seed = load_seed(args.seed_preset)
    slug = args.slug or seed.get("slug", "")

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
    console_errors: list[tuple[str, str]] = []
    # FB-38: replaced by the account's own invitation once the signed-in seed exists.
    active_invite = {"id": ""}

    def hook(page, label: str):
        def record(m):
            if m.type != "error":
                return
            try:
                url = (m.location or {}).get("url", "")
            except Exception:  # noqa: BLE001
                url = ""
            console_errors.append((label, (url + ' :: ' if url else '') + m.text))
        page.on("console", record)
        page.add_init_script(LONG_TASK_JS)

    def seed_public(base_url: str, browser) -> str:
        """Seed and publish one invitation on the server under test (FB-41).

        The pinned seed preset belongs to the FB-35 data dir; the gate starts a fresh
        server, so its public route answered 404 and the console gate failed on noise.
        Reuse the audit capture's seeder (same DOCUMENT and publish call).
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ui_audit_capture", ROOT / "tools" / "ui-audit-capture.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        try:
            info = mod.seed_account(ctx.new_page(), base_url)
        finally:
            ctx.close()
        print(f"UI_LAYOUT_GUARD_SEED public slug={info['slug']} publish_ok={info['publish_ok']}")
        return info["slug"] if info.get("publish_ok") else ""

    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)

        def context(width: int, height: int, theme: str, lang: str):
            ctx = browser.new_context(viewport={"width": width, "height": height})
            ctx.add_init_script(INIT_SCRIPT % (theme, lang))
            # FB-38: the editor cell runs the seeded invitation with the tour seen so
            # it measures the real fitted canvas, not the first-run overlay.
            ctx.add_init_script("try{localStorage.setItem('einvite-final-tour-seen-v1','1')}catch{}")
            if active_invite["id"]:
                ctx.add_init_script(
                    "try{localStorage.setItem('sovan-active-invite','" + str(active_invite["id"]) +
                    "')}catch{}")
            return ctx

        # ---- signed-out dashboard (auth-card padding) ---------------------
        for viewport in viewports:
            w, h = (int(v) for v in viewport.split("x"))
            for theme in themes:
                for lang in langs:
                    ctx = context(w, h, theme, lang)
                    page = ctx.new_page()
                    hook(page, "dashboard.html")
                    page.goto(f"{base}/dashboard.html", wait_until="domcontentloaded")
                    page.wait_for_timeout(args.settle)
                    if page.locator("#newBtn").count() and page.is_visible("#newBtn"):
                        page.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(args.settle)
                    data = page.evaluate(MEASURE_JS)
                    rows.extend(rows_for("dashboard.html", viewport, theme, lang, data, signed_in=False))
                    ctx.close()

        # ---- public invitation (FB-38): guest page at /i/<slug>, opened state.
        # FB-41: without an explicit --slug, seed our own published invitation on the
        # running server instead of trusting the preset (which belongs to another data dir).
        if slug and not args.slug:
            probe = browser.new_context(viewport={"width": 800, "height": 600})
            try:
                reachable = probe.request.get(f"{base}/api/public/{slug}").ok
            finally:
                probe.close()
            if not reachable:
                slug = seed_public(base, browser)
        if slug:
            for viewport in viewports:
                w, h = (int(v) for v in viewport.split("x"))
                for theme in themes:
                    for lang in langs:
                        ctx = context(w, h, theme, lang)
                        page = ctx.new_page()
                        hook(page, "public.html")
                        try:
                            page.goto(f"{base}/i/{slug}", wait_until="domcontentloaded")
                            page.wait_for_timeout(args.settle)
                            open_btn = page.get_by_role("button", name="Open invitation").first
                            if open_btn.count():
                                try:
                                    open_btn.click(timeout=4000)
                                except Exception:  # noqa: BLE001 — guest page may auto-open
                                    pass
                                page.wait_for_timeout(args.settle)
                            data = page.evaluate(MEASURE_JS)
                        except Exception as exc:  # noqa: BLE001
                            rows.append(("load:public.html", False,
                                         f"public.html {viewport} {theme} {lang} {exc}"[:300]))
                            ctx.close()
                            continue
                        rows.extend(rows_for("public.html", viewport, theme, lang, data, signed_in=False))
                        if lang == "km" and theme == "light" and viewport == "1440x900":
                            rows.extend(collect_font_rows(
                                ctx, page, f"public.html {viewport} {theme} {lang}"))
                        ctx.close()

        # ---- signed-in pages ----------------------------------------------
        if not args.skip_signed_in:
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
            email = f"layout-guard-{stamp}@example.com"
            seed_ctx = context(1440, 900, "light", "en")
            req = seed_ctx.request
            reg = req.post(f"{base}/api/auth/register", data={"email": email, "password": PASSWORD})
            if not reg.ok:
                login = req.post(f"{base}/api/auth/login", data={"email": email, "password": PASSWORD})
                if not login.ok:
                    print(f"UI_LAYOUT_GUARD_CANNOT_RUN: could not create account ({reg.status})")
                    browser.close()
                    return 4
            # FB-38: the fresh account needs its own invitation. Pointing
            # `sovan-active-invite` at the shared seed preset's id made every signed-in
            # page request an invitation this account cannot read (404s in the console)
            # and ran the editor against the offline fallback document.
            created = req.post(f"{base}/api/invitations",
                               data={"title": "Layout guard seed", "eventType": "wedding"})
            if created.ok:
                active_invite["id"] = str((created.json() or {}).get("id") or "")
            else:
                print(f"UI_LAYOUT_GUARD_WARN: seed invitation failed ({created.status})")
            seed_ctx.close()

            for viewport in viewports:
                w, h = (int(v) for v in viewport.split("x"))
                for theme in themes:
                    for lang in langs:
                        ctx = context(w, h, theme, lang)
                        req = ctx.request
                        req.post(f"{base}/api/auth/login", data={"email": email, "password": PASSWORD})
                        for page_name in pages:
                            page = ctx.new_page()
                            hook(page, page_name)
                            try:
                                page.goto(f"{base}/{page_name}", wait_until="domcontentloaded")
                                page.wait_for_timeout(args.settle)
                                if page_name == "index.html":
                                    # Wait for the editor to report ready, then let
                                    # the fit tween and its settle pass finish.
                                    try:
                                        page.wait_for_function(
                                            "() => document.documentElement.dataset.editorReady === 'true'",
                                            timeout=8000)
                                    except Exception:  # noqa: BLE001
                                        pass
                                    page.wait_for_timeout(args.settle + 900)
                                data = page.evaluate(MEASURE_JS)
                            except Exception as exc:  # noqa: BLE001
                                rows.append((f"load:{page_name}", False,
                                             f"{page_name} {viewport} {theme} {lang} {exc}"[:300]))
                                page.close()
                                continue
                            rows.extend(rows_for(page_name, viewport, theme, lang, data, signed_in=True))
                            if lang == "km" and theme == "light" and viewport == "1440x900":
                                rows.extend(collect_font_rows(
                                    ctx, page, f"{page_name} {viewport} {theme} {lang}"))
                            page.close()
                        ctx.close()

        browser.close()

    # FB-38: console baseline — every error must match a committed pattern.
    patterns = load_console_patterns(args.console_baseline)
    unmatched = [(label, msg) for label, msg in console_errors
                 if not console_matches(msg, patterns)]
    if unmatched:
        for label, msg in unmatched[:12]:
            rows.append(("console-baseline", False, f"{label} :: {msg[:180]}"))
    else:
        rows.append(("console-baseline", True,
                     f"{len(console_errors)} console error(s), all baseline-known"))

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
