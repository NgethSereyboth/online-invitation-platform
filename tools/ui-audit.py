#!/usr/bin/env python3
"""Reproducible UI audit: screenshots + interactive-surface capture + defect probes.

This is the harness behind ``artifacts/ui-audit-2026-10-29/``. It is deliberately
standalone (Python Playwright only) so the corpus can be rebuilt on any box:

    python3 tools/serve-gzip.py --port 4176 &
    .venv/bin/python tools/ui-audit.py --out artifacts/ui-audit-2026-10-29/pass2 --mode all

Modes
-----
base      every page x every variant: full-page + viewport screenshots + probes
states    the explicit function recipes below (dialogs, panels, tabs, menus)
discover  opens every visible surface trigger found in the DOM, one per reload
focus     keyboard focus walk: is the focused control visible and visibly focused?
all       base + states + discover (+ focus for desktop)

Output
------
    <out>/manifest.json           run metadata, page list, counts, timings
    <out>/findings.json           every finding, grouped, with selectors + rects
    <out>/console.json            console errors and non-2xx / failed requests
    <out>/screens/<variant>/...   page screenshots
    <out>/states/<variant>/...    function screenshots
    <out>/focus.json              focus-walk results

Hard rules inherited from the project ledgers: never writes to ``src/``, never
touches ``artifacts/canvas-motion/``, one browser at a time. Static serving is
enough: the pages render their demo data without the backend, and API 404s are
recorded as expected static-mode noise rather than defects.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        Page,
        TimeoutError as PlaywrightTimeout,
        sync_playwright,
    )
except ImportError:  # pragma: no cover - harness guard
    sys.exit("playwright missing: run through .venv/bin/python (see STATE.md rule 7)")


# --------------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------------- #

PAGES = [
    ("index", "index.html", "Editor / canvas"),
    ("dashboard", "dashboard.html", "My invitations"),
    ("materials", "materials.html", "Materials library"),
    ("templates", "templates.html", "Template studio"),
    ("designer", "designer.html", "Designer workspace"),
    ("guests", "guests.html", "Guest list"),
    ("responses", "responses.html", "Responses"),
    ("checkin", "checkin.html", "Check-in"),
    ("analytics", "analytics.html", "Analytics"),
    ("billing", "billing.html", "Plans / billing"),
    ("account", "account.html", "Account settings"),
    ("admin", "admin.html", "Admin"),
    ("privacy", "privacy.html", "Privacy"),
    ("public", "public.html", "Public invitation"),
    ("reset", "reset.html", "Password reset"),
    ("verify", "verify.html", "Email verification"),
]

# Pages that read the invitation context from ?invitation=<id>.
INVITATION_PAGES = {"index", "guests", "responses", "analytics", "checkin", "materials"}

VARIANTS = [
    {"name": "desktop", "viewport": (1440, 900), "scheme": "light", "lang": "en", "theme": "light"},
    {"name": "mobile", "viewport": (390, 844), "scheme": "light", "lang": "en", "theme": "light", "mobile": True},
    {"name": "km", "viewport": (1440, 900), "scheme": "light", "lang": "km", "theme": "light"},
    {"name": "dark", "viewport": (1440, 900), "scheme": "dark", "lang": "en", "theme": "dark"},
]

# Explicit recipes. A step is ("click", selector) | ("text", text) | ("role", role, name)
# | ("fill", selector, value) | ("press", key) | ("wait", ms) | ("eval", js).
# Keep these to functions a static page can reach: no destructive confirmations.
STATES: dict[str, list[dict[str, Any]]] = {
    "index": [
        {"name": "onboarding-tour", "steps": [], "keep_tour": True},
        {"name": "left-elements", "steps": [("click", "button.studio-rail-button:has-text('Elements')")]},
        {"name": "left-text", "steps": [("click", "button.studio-rail-button:has-text('Text')")]},
        {"name": "left-uploads", "steps": [("click", "button.studio-rail-button:has-text('Uploads')")]},
        {"name": "left-pages", "steps": [("click", "button.studio-rail-button:has-text('Pages')")]},
        {"name": "left-event", "steps": [("click", "button.studio-rail-button:has-text('Event')")]},
        {"name": "left-blocks", "steps": [("click", "button.studio-rail-button:has-text('Blocks')")]},
        {"name": "inspector-layers", "steps": [("click", ".studio-inspector-tab:has-text('Layers')")]},
        {"name": "inspector-sections", "steps": [("click", ".studio-inspector-tab:has-text('Sections')")]},
        {"name": "inspector-design", "steps": [("click", ".studio-inspector-tab:has-text('Design')")]},
        {"name": "inspector-share", "steps": [("click", ".studio-inspector-tab:has-text('Share')")]},
        {"name": "more-editor-actions", "steps": [("click", ".canvas-header-more-trigger")]},

        {"name": "zoom-menu", "steps": [("click", "button.v54-zoom-value")]},
        {"name": "flow-panel", "steps": [("click", "#workflowV6FlowBtn")]},
        {"name": "position-panel", "steps": [("click", "#workflowV6PositionBtn")]},
        {"name": "focus-mode", "steps": [("click", "#workflowV5Focus")]},
        {"name": "creation-panel-toggle", "steps": [("click", "#workflowPanelToggle")]},

        {"name": "command-palette", "steps": [("click", "#studioCommandBtn")]},
        {"name": "ai-panel", "steps": [("click", "#eiAiTopButton")]},
        {"name": "design-check", "steps": [("click", "#studioCheckBtn")]},
        {"name": "guest-preview", "steps": [("click", "#previewBtn")]},
        {"name": "publish", "steps": [("click", "#publishBtn")]},
        {"name": "tools-menu", "steps": [("click", ".v54-footer-tools-trigger")]},
        {"name": "sidebar-collapsed", "steps": [("click", "#v54SidebarCollapse")]},
    ],
    "dashboard": [
        {"name": "create-dialog", "steps": [("click", "#newBtn")]},
        {"name": "template-studio", "steps": [("click", "#studioBtn")]},
        {"name": "search-query", "steps": [("fill", "#dashboardSearch", "royal")]},
        {"name": "search-empty", "steps": [("fill", "#dashboardSearch", "zzzz-no-match")]},
        {"name": "filter-published", "steps": [("role", "button", "Published")]},
        {"name": "filter-archive", "steps": [("role", "button", "Archive")]},
        {"name": "card-menu", "steps": [("click", ".invite-overflow__toggle")]},
        {"name": "profile-menu", "steps": [("click", ".fp-profile-button")]},
        {"name": "card-hover", "steps": [("hover", ".invite-card")]},
        {"name": "rail-collapsed", "steps": [("click", ".app-rail-toggle")]},
    ],
    "materials": [
        {"name": "upload-open", "steps": [("click", ".material-upload-toggle")]},
        {"name": "filter-images", "steps": [("select", "#typeFilter", "Images")]},
        {"name": "sort-largest", "steps": [("select", "#sort", "Largest first")]},
        {"name": "search-empty", "steps": [("fill", "#search", "zzzz-no-match")]},
    ],
    "templates": [
        {"name": "new-poster", "steps": [("click", "#newPosterBtn")]},
        {"name": "category-wedding", "steps": [("click", ".pack-filter:has-text('Wedding')")]},
        {"name": "pack-search", "steps": [("fill", "#packSearch", "gold")]},
        {"name": "card-preview", "steps": [("click", "button:has-text('Preview')")]},
        {"name": "use-card", "steps": [("click", ".pack-card-open")]},
    ],
    "designer": [
        {"name": "new-project", "steps": [("maybe_click", "button:has-text('New project')")]},
    ],
    "guests": [
        {"name": "add-guest", "steps": [("click", "button:has-text('Add guest')")]},
        {"name": "guest-links", "steps": [("click", "#linksBtn")]},
        {"name": "status-attending", "steps": [("select", "#statusFilter", "Attending")]},
        {"name": "search-empty", "steps": [("maybe_fill", "#guestSearch", "zzzz-no-match")]},
    ],
    "responses": [
        {"name": "tab-wishes", "steps": [("click", "button:has-text('Guest wishes')")]},
        {"name": "tab-rsvp", "steps": [("click", "button:has-text('RSVP responses')")]},
    ],
    "checkin": [
        {"name": "scan-qr", "steps": [("click", "#scanQrBtn")]},
        {"name": "search-guest", "steps": [("fill", "#guestSearch", "sof")]},
        {"name": "check-in-first", "steps": [("maybe_click", "button:has-text('Check in')")]},
    ],
    "analytics": [
        {"name": "refresh", "steps": [("click", "#refreshAnalytics")]},
    ],
    "billing": [],
    "account": [
        {"name": "appearance-dark", "steps": [("click", "button:has-text('Dark')")]},
        {"name": "appearance-light", "steps": [("click", "button:has-text('Light')")]},
        {"name": "change-password", "steps": [("click", "button:has-text('Change password')")]},
    ],
    "admin": [
        {"name": "tab-users", "steps": [("maybe_click", "button:has-text('Users')")]},
        {"name": "tab-templates", "steps": [("click", "button:has-text('Templates')")]},
        {"name": "tab-invitations", "steps": [("click", "button:has-text('Invitations')")]},
        {"name": "tab-ai", "steps": [("click", "button:has-text('AI providers')")]},
        {"name": "tab-flags", "steps": [("click", "button:has-text('Feature flags')")]},
        {"name": "tab-system", "steps": [("click", "button:has-text('System')")]},
        {"name": "search-users", "steps": [("fill", "input[placeholder*='email' i], input[placeholder*='Search by' i]", "demo")]},
    ],
    "public": [
        {"name": "open-invitation", "steps": [("maybe_click", "button:has-text('Open Invitation')")]},
        {"name": "rsvp-filled", "steps": [("fill", "input[name=name], input[placeholder*='name' i]", "Audit Guest"), ("maybe_click", "button:has-text('Send RSVP')")]},
        {"name": "calendar-action", "steps": [("maybe_click", "button:has-text('Add event to calendar')")]},
    ],
    "reset": [
        {"name": "invalid-email", "steps": [("fill", "input[type=email], input[name=email]", "not-an-email"), ("maybe_click", "button:has-text('Send reset link')")]},
        {"name": "valid-email", "steps": [("fill", "input[type=email], input[name=email]", "audit@einvite.test"), ("maybe_click", "button:has-text('Send reset link')")]},
    ],
    "verify": [
        {"name": "submit-empty", "steps": [("maybe_click", "button:has-text('Verify'), button:has-text('Confirm'), button.primary")]},
    ],
    "privacy": [],
}


# --------------------------------------------------------------------------- #
# Probe JS (runs in the page; no framework assumptions)
# --------------------------------------------------------------------------- #

PROBE_JS = r"""
() => {
  const SEL = 'a[href],button,input:not([type="hidden"]),select,textarea,summary,[role="button"],[role="link"],[role="tab"],[role="menuitem"],[role="menuitemcheckbox"],[role="menuitemradio"],[role="checkbox"],[role="switch"],[role="radio"],[role="option"],[role="combobox"],[role="slider"],[role="searchbox"],[role="textbox"],[tabindex]:not([tabindex="-1"]),[contenteditable="true"]';
  const findings = [];
  const stats = { elements: 0, interactive: 0, interactiveVisible: 0, interactiveInvisible: 0,
                  smallTargets: 0, controlsWithoutName: 0, textClipped: 0, lowContrast: 0,
                  contrastChecked: 0, images: 0, buttons: 0, links: 0, inputs: 0, dialogs: 0, findings: 0 };
  const meta = { headings: [], h1Count: 0, skippedHeadingLevels: [], landmarks: {}, lang: document.documentElement.lang,
                 title: document.title, duplicateIds: [], horizontalScroll: 0, brokenImages: 0,
                 fixedOverlays: [], canvases: 0, scrollHeight: 0, scrollWidth: 0, viewport: [innerWidth, innerHeight] };
  const seen = new Set();

  const r2 = n => Math.round(n * 10) / 10;
  function rectOf(el) { const r = el.getBoundingClientRect(); return { x: r2(r.x), y: r2(r.y), w: r2(r.width), h: r2(r.height) }; }
  function csOf(el) { return getComputedStyle(el); }
  function pathOf(el) {
    if (!el || el.nodeType !== 1) return '';
    if (el.id && !/^\d/.test(el.id)) return '#' + CSS.escape(el.id);
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && parts.length < 4) {
      let s = n.tagName.toLowerCase();
      if (n.classList && n.classList.length) s += '.' + Array.from(n.classList).slice(0, 2).map(c => CSS.escape(c)).join('.');
      const p = n.parentElement;
      if (p) {
        const sibs = Array.from(p.children).filter(c => c.tagName === n.tagName);
        if (sibs.length > 1) s += ':nth-of-type(' + (sibs.indexOf(n) + 1) + ')';
      }
      parts.unshift(s); n = n.parentElement;
    }
    return parts.join(' > ');
  }
  function nameOf(el) {
    let n = (el.getAttribute('aria-label') || '').trim();
    if (!n && el.getAttribute('aria-labelledby')) {
      n = el.getAttribute('aria-labelledby').split(/\s+/)
        .map(id => { const t = document.getElementById(id); return t ? (t.innerText || t.textContent || '') : ''; })
        .join(' ').trim();
    }
    if (!n && el.labels && el.labels.length) n = Array.from(el.labels).map(l => l.innerText || l.textContent || '').join(' ').trim();
    if (!n && (el.tagName === 'IMG' || el.tagName === 'AREA')) n = (el.getAttribute('alt') || '').trim();
    if (!n) n = (el.innerText || el.textContent || '').trim().slice(0, 140);
    if (!n) n = (el.getAttribute('title') || '').trim();
    if (!n && el.tagName === 'INPUT') n = (el.getAttribute('placeholder') || '').trim();
    return n.replace(/\s+/g, ' ');
  }
  function isDisabled(el) { return !!(el.disabled || el.getAttribute('aria-disabled') === 'true' || el.closest('[aria-disabled="true"]')); }
  function rendered(el) {
    const r = el.getBoundingClientRect();
    const cs = csOf(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    if (r.width < 1 || r.height < 1) return false;
    return true;
  }
  function inViewport(r) { return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth; }
  function fullyInViewport(r) { return r.top >= -0.5 && r.left >= -0.5 && r.bottom <= innerHeight + 0.5 && r.right <= innerWidth + 0.5; }

  function add(el, kind, severity, why, extra) {
    const selector = pathOf(el);
    const key = kind + '|' + selector + '|' + why;
    if (seen.has(key)) return;
    seen.add(key);
    findings.push(Object.assign({
      kind, severity, why, selector,
      tag: el.tagName.toLowerCase(), id: el.id || '',
      cls: (el.className && typeof el.className === 'string') ? el.className.trim().slice(0, 160) : '',
      role: el.getAttribute('role') || '',
      label: nameOf(el).slice(0, 140),
      rect: rectOf(el)
    }, extra || {}));
  }

  function effectiveBg(el) {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = csOf(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;
      const c = cs.backgroundColor;
      const m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
      if (m && (m[4] === undefined || parseFloat(m[4]) > 0.95)) return [+m[1], +m[2], +m[3]];
      n = n.parentElement;
    }
    return [255, 255, 255];
  }
  function lum(c) {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }
  function ratio(a, b) { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); }
  function parseColor(c) {
    const m = String(c).match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    if (!m) return null;
    return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : parseFloat(m[4])];
  }
  function hasDirectText(el) {
    return Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
  }
  function visibleText(el) { return (el.innerText || '').trim().length > 1; }

  const all = Array.from(document.querySelectorAll('*'));
  stats.elements = all.length;
  meta.canvases = document.querySelectorAll('canvas').length;
  meta.scrollHeight = document.documentElement.scrollHeight;
  meta.scrollWidth = document.documentElement.scrollWidth;
  if (document.documentElement.scrollWidth > innerWidth + 1) meta.horizontalScroll = document.documentElement.scrollWidth - innerWidth;

  all.forEach(el => { if (el.tagName === 'IMG') { stats.images++; if (el.complete && el.naturalWidth === 0) meta.brokenImages++; } });
  const ids = {};
  document.querySelectorAll('[id]').forEach(el => { ids[el.id] = (ids[el.id] || 0) + 1; });
  meta.duplicateIds = Object.keys(ids).filter(k => ids[k] > 1).slice(0, 30);

  const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).filter(h => rendered(h) && visibleText(h));
  meta.headings = headings.slice(0, 60).map(h => ({ level: +h.tagName[1], text: (h.innerText || '').trim().slice(0, 100) }));
  meta.h1Count = headings.filter(h => h.tagName === 'H1').length;
  let prev = 0;
  headings.forEach(h => { const lv = +h.tagName[1]; if (prev && lv > prev + 1) meta.skippedHeadingLevels.push(prev + '->' + lv + ' (' + (h.innerText || '').trim().slice(0, 40) + ')'); prev = lv; });
  ['main', 'nav', 'header', 'footer', 'aside'].forEach(k => { meta.landmarks[k] = Array.from(document.querySelectorAll(k)).filter(rendered).length; });

  const interactive = Array.from(document.querySelectorAll(SEL)).filter(el => !el.closest('[inert]'));
  stats.interactive = interactive.length;
  stats.buttons = interactive.filter(e => e.tagName === 'BUTTON' || e.getAttribute('role') === 'button').length;
  stats.links = interactive.filter(e => e.tagName === 'A').length;
  stats.inputs = interactive.filter(e => ['INPUT', 'SELECT', 'TEXTAREA'].includes(e.tagName)).length;
  stats.dialogs = Array.from(document.querySelectorAll('dialog[open],[role="dialog"]')).filter(rendered).length;

  const visible = [];
  interactive.forEach(el => {
    const cs = csOf(el);
    const r = el.getBoundingClientRect();
    const renderedNow = rendered(el);
    if (renderedNow) { stats.interactiveVisible++; visible.push(el); } else { stats.interactiveInvisible++; }

    // 1. clickable but invisible: occupies space yet paints nothing
    const opacityChain = (() => { let n = el, o = 1; while (n && n.nodeType === 1) { o *= parseFloat(csOf(n).opacity || '1'); n = n.parentElement; } return o; })();
    const invisiblePaint = opacityChain < 0.05 || cs.visibility === 'hidden' || cs.clipPath && /inset\(\s*(49|50)%/.test(cs.clipPath) || (cs.transform && /matrix\(0,\s*0,\s*0,\s*0/.test(cs.transform));
    if (invisiblePaint && r.width > 1 && r.height > 1 && cs.pointerEvents !== 'none') {
      add(el, 'clickable-but-invisible', 'high', 'pointer-events on, painted at opacity ' + opacityChain.toFixed(2), { opacity: +opacityChain.toFixed(2) });
    }

    if (!renderedNow) return;
    if (cs.pointerEvents === 'none') return;

    // 2. focused/clickable control clipped by a non-scrollable ancestor
    const offscreenUtility = r.left < -2000 || r.top < -2000 || /skip/i.test(el.className || '');
    if (offscreenUtility) return;
    let n = el.parentElement, clip = null;
    while (n && n !== document.documentElement) {
      const ncs = csOf(n);
      const nr = n.getBoundingClientRect();
      const x = (ncs.overflowX === 'hidden' || ncs.overflowX === 'clip');
      const y = (ncs.overflowY === 'hidden' || ncs.overflowY === 'clip');
      if (x || y) {
        const dx = Math.max(0, nr.left - r.left) + Math.max(0, r.right - nr.right);
        const dy = Math.max(0, nr.top - r.top) + Math.max(0, r.bottom - nr.bottom);
        if ((x && dx > 1) || (y && dy > 1)) {
          clip = { by: pathOf(n), dx: r2(dx), dy: r2(dy), ox: ncs.overflowX, oy: ncs.overflowY,
                   scrollW: n.scrollWidth, clientW: n.clientWidth, scrollH: n.scrollHeight, clientH: n.clientHeight };
          break;
        }
      }
      n = n.parentElement;
    }
    if (clip && clip.dx > 6) {
      const scrollableX = clip.scrollW > clip.clientW + 2 && clip.dx > 0;
      if (!scrollableX) {
        add(el, 'control-clipped-by-ancestor', 'medium', 'clipped horizontally by ' + clip.by + ' (' + clip.ox + ')', clip);
      }
    }

    // 3. interactive outside the document box (not merely below the fold)
    const docW = document.documentElement.scrollWidth, docH = document.documentElement.scrollHeight;
    const outsideDoc = r.right < -1 || r.bottom < -1 || r.left > docW || r.top > docH;
    if (outsideDoc && !offscreenUtility && el.tabIndex >= 0 && !el.closest('[aria-hidden="true"]')) {
      add(el, 'interactive-outside-document', 'medium', 'focusable but its box is outside the document bounds', { tabIndex: el.tabIndex });
    }

    // 4. occlusion: sample five points, majority covered by a different control
    if (r.width > 2 && r.height > 2 && fullyInViewport(r)) {
      const pts = [[0.5, 0.5], [0.2, 0.2], [0.8, 0.2], [0.2, 0.8], [0.8, 0.8]];
      let covered = 0, by = null;
      for (const [px, py] of pts) {
        const hit = document.elementFromPoint(r.left + r.width * px, r.top + r.height * py);
        if (!hit || hit === el || el.contains(hit) || hit.contains(el)) continue;
        const hcs = csOf(hit);
        if (hcs.pointerEvents === 'none' || hcs.visibility === 'hidden') continue;
        covered++; if (!by) by = hit;
      }
      if (covered >= 3) add(el, 'control-occluded', 'high', 'covered at ' + covered + '/5 sample points by ' + pathOf(by), { covered, by: pathOf(by) });
    }

    // 5. target size (WCAG 2.2 AA 24px), inline text links excepted
    const inlineLink = el.tagName === 'A' && cs.display === 'inline';
    if (!inlineLink && !offscreenUtility && (r.width < 24 || r.height < 24) && !isDisabled(el)) {
      stats.smallTargets++;
      add(el, 'tiny-target', 'low', 'target ' + r2(r.width) + 'x' + r2(r.height) + ' < 24px', { w: r2(r.width), h: r2(r.height) });
    }

    // 6. accessible name
    const nm = nameOf(el);
    if (!nm && !['SELECT'].includes(el.tagName)) {
      stats.controlsWithoutName++;
      add(el, 'control-without-name', 'high', 'no accessible name', {});
    }

    // 7. nested interactive
    const nested = Array.from(el.querySelectorAll(SEL)).filter(c => rendered(c) && c.tabIndex >= 0);
    if (nested.length) add(el, 'nested-interactive', 'medium', 'contains ' + nested.length + ' focusable control(s)', { nested: nested.slice(0, 3).map(pathOf) });

    // 8. low contrast for direct text
    if (hasDirectText(el) && !isDisabled(el) && el.getAttribute('aria-hidden') !== 'true') {
      const col = parseColor(cs.color), bg = effectiveBg(el);
      const fs = parseFloat(cs.fontSize || '0'), bold = (parseInt(cs.fontWeight || '400', 10) >= 700);
      if (col && bg && fs > 0) {
        stats.contrastChecked++;
        const cr = ratio([col[0], col[1], col[2]], bg);
        const large = fs >= 24 || (fs >= 18.66 && bold);
        if (cr < (large ? 3 : 4.5)) {
          stats.lowContrast++;
          add(el, 'low-contrast', 'medium', 'ratio ' + cr.toFixed(2) + ':1 (' + Math.round(fs) + 'px)', { ratio: +cr.toFixed(2), color: cs.color, bg: 'rgb(' + bg.join(',') + ')' });
        }
      }
    }

    // 9. text clipped in a non-scrollable box (own text or a clipped child label)
    const labelClipX = el.scrollWidth > el.clientWidth + 2 && (cs.overflowX === 'hidden' || cs.overflowX === 'clip');
    if ((hasDirectText(el) || labelClipX) && visibleText(el)) {
      const clippedX = el.scrollWidth > el.clientWidth + 2 && (cs.overflowX === 'hidden' || cs.overflowX === 'clip');
      const clippedY = el.scrollHeight > el.clientHeight + 2 && (cs.overflowY === 'hidden' || cs.overflowY === 'clip');
      const ellipsis = cs.textOverflow === 'ellipsis';
      const clamp = cs.webkitLineClamp && cs.webkitLineClamp !== 'none';
      if ((clippedX && !ellipsis) || (clippedY && !clamp)) {
        stats.textClipped++;
        add(el, 'text-clipped', 'low', (clippedX ? 'x' : '') + (clippedY ? 'y' : '') + ' clipped, no ellipsis/clamp', { sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight });
      }
    }
  });

  // 9b. the same question rendered twice inside one form (ignore option text)
  document.querySelectorAll('form').forEach(form => {
    const seenLabel = {};
    form.querySelectorAll('label').forEach(l => {
      const clone = l.cloneNode(true);
      clone.querySelectorAll('select,input,textarea,button,option,svg').forEach(n => n.remove());
      const t = (clone.textContent || '').trim().replace(/\s+/g, ' ');
      if (t.length > 2) seenLabel[t] = (seenLabel[t] || 0) + 1;
    });
    Object.keys(seenLabel).forEach(t => {
      if (seenLabel[t] > 1) add(form, 'duplicate-field-label', 'medium', 'label "' + t.slice(0, 70) + '" appears ' + seenLabel[t] + ' times', { count: seenLabel[t] });
    });
  });

  // 9c. option text that concatenates Khmer and Latin without a separator
  document.querySelectorAll('option').forEach(o => {
    const t = (o.textContent || '').trim();
    if (/[\u1780-\u17FF][A-Za-z]|[A-Za-z][\u1780-\u17FF]/.test(t)) {
      add(o, 'mixed-language-option', 'medium', 'English and Khmer run together: "' + t.slice(0, 60) + '"', {});
    }
  });

  // 10. aria-hidden but visible / focusable inside aria-hidden
  let focusableHidden = 0, focusableHiddenExamples = [];
  document.querySelectorAll('[aria-hidden="true"]').forEach(h => {
    const hr = h.getBoundingClientRect();
    const hcs = csOf(h);
    const decorative = h.matches('[role="img"],figure,figcaption') || /thumb|preview|pack-art|cover-art/.test(h.className || '');
    if (rendered(h) && hcs.visibility !== 'hidden' && visibleText(h) && !h.closest('svg') && !decorative) {
      add(h, 'aria-hidden-but-visible', 'low', 'aria-hidden with visible text', {});
    }
    const f = Array.from(h.querySelectorAll(SEL)).filter(c => c.tabIndex >= 0);
    if (f.length) {
      focusableHidden += f.length;
      if (focusableHiddenExamples.length < 5) focusableHiddenExamples.push(f.slice(0, 3).map(pathOf));
    }
  });
  if (focusableHidden) {
    findings.push({
      kind: 'focusable-inside-aria-hidden', severity: 'high', selector: '[aria-hidden="true"]',
      why: focusableHidden + ' focusable control(s) hidden from assistive tech', count: focusableHidden,
      examples: focusableHiddenExamples, tag: '', id: '', cls: '', role: '', label: '', rect: {}
    });
  }

  // 11. pointer cursor with no semantics (aggregate, not one row per element)
  const pointer = all.filter(el => csOf(el).cursor === 'pointer' && !el.matches(SEL) && rendered(el) && visibleText(el));
  if (pointer.length) {
    findings.push({
      kind: 'pointer-cursor-not-semantic', severity: 'low', selector: '(aggregate)',
      why: pointer.length + ' element(s) look clickable but are not keyboard reachable', count: pointer.length,
      examples: pointer.slice(0, 8).map(el => pathOf(el) + ' · ' + (el.innerText || '').trim().slice(0, 40)),
      tag: '', id: '', cls: '', role: '', label: '', rect: {}
    });
  }

  // 12. overlapping visible controls (pairs, non-nested)
  const ov = [];
  const cap = visible.slice(0, 400);
  for (let i = 0; i < cap.length; i++) {
    for (let j = i + 1; j < cap.length; j++) {
      const a = cap[i], b = cap[j];
      if (a.contains(b) || b.contains(a)) continue;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const ox = Math.max(0, Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left));
      const oy = Math.max(0, Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top));
      const area = ox * oy, minA = Math.min(ra.width * ra.height, rb.width * rb.height);
      if (area > 0 && minA > 0 && area / minA > 0.5) {
        ov.push({ a: pathOf(a), b: pathOf(b), overlap: +(area / minA).toFixed(2) });
        if (ov.length >= 8) break;
      }
    }
    if (ov.length >= 8) break;
  }
  ov.forEach(o => findings.push({ kind: 'overlapping-controls', severity: 'low', selector: o.a, why: 'overlaps ' + o.b + ' by ' + Math.round(o.overlap * 100) + '%', tag: '', id: '', cls: '', role: '', label: '', rect: {} }));

  // 13. Khmer line-height contract (>= 1.6)
  Array.from(document.querySelectorAll('[lang="km"],.khmer-text')).filter(rendered).forEach(el => {
    if (!visibleText(el)) return;
    const cs = csOf(el), fs = parseFloat(cs.fontSize || '0');
    if (!fs) return;
    const lh = cs.lineHeight === 'normal' ? fs * 1.2 : parseFloat(cs.lineHeight);
    if (lh / fs < 1.55) add(el, 'khmer-line-height', 'medium', 'line-height ' + (lh / fs).toFixed(2) + ' < 1.6', { ratio: +(lh / fs).toFixed(2) });
  });

  // 14. fixed overlays that may cover content (reported for review, not a defect by itself)
  document.querySelectorAll('body *').forEach(el => {
    const cs = csOf(el);
    if ((cs.position === 'fixed' || cs.position === 'sticky') && rendered(el) && el.offsetParent !== null) {
      const r = el.getBoundingClientRect();
      if (r.width * r.height > innerWidth * innerHeight * 0.02) meta.fixedOverlays.push({ selector: pathOf(el), rect: rectOf(el), position: cs.position });
    }
  });
  meta.fixedOverlays = meta.fixedOverlays.slice(0, 20);

  // surface triggers for the discovery pass
  const triggers = [];
  const tset = new Set();
  document.querySelectorAll('[aria-expanded="false"],[aria-haspopup],[role="tab"][aria-selected="false"],details:not([open])>summary,[data-drawer-toggle],[aria-controls]:not([aria-expanded]),button[aria-label*="more" i],button[aria-label*="option" i],button[aria-label*="action" i],[data-toggle],[data-menu-toggle],.menu-trigger').forEach(el => {
    if (!rendered(el) || el.closest('[aria-hidden="true"]') || el.closest('svg')) return;
    const p = pathOf(el);
    if (tset.has(p)) return; tset.add(p);
    triggers.push({ selector: p, label: nameOf(el).slice(0, 100), tag: el.tagName.toLowerCase(),
                    expanded: el.getAttribute('aria-expanded'), haspopup: el.getAttribute('aria-haspopup') || '' });
  });

  stats.findings = findings.length;
  return { findings, stats, meta, triggers: triggers.slice(0, 60) };
}
"""

FOCUS_JS = r"""
() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const visibleBox = r.width > 1 && r.height > 1 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
  const ring = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth || '0') > 0) ||
               (cs.boxShadow && cs.boxShadow !== 'none') ||
               (cs.textDecorationLine && cs.textDecorationLine !== 'none');
  return {
    tag: el.tagName.toLowerCase(), id: el.id || '',
    cls: (el.className && typeof el.className === 'string') ? el.className.slice(0, 120) : '',
    label: (el.getAttribute('aria-label') || el.innerText || el.value || '').trim().slice(0, 100),
    rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
    visibleBox, ring, outline: cs.outlineStyle + ' ' + cs.outlineWidth, shadow: (cs.boxShadow || '').slice(0, 80)
  };
}
"""


# --------------------------------------------------------------------------- #
# Playwright plumbing
# --------------------------------------------------------------------------- #

@dataclass
class Run:
    out: Path
    base: str
    browser: Browser
    email: str = ""
    password: str = ""
    invitation: str = ""
    storage: dict[str, Any] | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    console: list[dict[str, Any]] = field(default_factory=list)
    states: list[dict[str, Any]] = field(default_factory=list)
    discovery: list[dict[str, Any]] = field(default_factory=list)
    focus: list[dict[str, Any]] = field(default_factory=list)
    started: float = field(default_factory=time.time)


def variant_by_name(name: str) -> dict[str, Any]:
    for v in VARIANTS:
        if v["name"] == name:
            return v
    raise SystemExit(f"unknown variant {name!r}")


def page_path(run: Run, name: str, path: str) -> str:
    if run.invitation and name in INVITATION_PAGES:
        sep = "&" if "?" in path else "?"
        return f"{path}{sep}invitation={run.invitation}"
    return path


def open_page(
    run: Run,
    vendor: dict[str, Any],
    path: str,
    dismiss_onboarding: bool = True,
) -> tuple[BrowserContext, Page, list[dict[str, Any]]]:
    ctx = run.browser.new_context(
        viewport={"width": vendor["viewport"][0], "height": vendor["viewport"][1]},
        color_scheme=vendor["scheme"],
        is_mobile=bool(vendor.get("mobile")),
        has_touch=bool(vendor.get("mobile")),
        device_scale_factor=1,
        reduced_motion="no-preference",
        storage_state=run.storage,
    )
    lang, theme = vendor["lang"], vendor["theme"]
    seed = ""
    if vendor.get("account", True):
        seed = (
            "if(!localStorage.getItem('sovan-account-v1')){"
            "localStorage.setItem('sovan-account-v1',JSON.stringify({id:'audit-user',"
            "email:'audit-admin@einvite.test',role:'admin',plan:'Studio'}));}"
        )
    ctx.add_init_script(
        "try{localStorage.setItem('einvite-lang',%s);"
        "localStorage.setItem('einvite-theme-mode',%s);" % (json.dumps(lang), json.dumps(theme))
        + seed
        + "}catch(e){}"
    )
    page = ctx.new_page()
    page.set_default_timeout(6000)
    events: list[dict[str, Any]] = []
    page.on("console", lambda msg: events.append({"type": "console:" + msg.type, "text": msg.text[:400]}) if msg.type == "error" else None)
    page.on("pageerror", lambda err: events.append({"type": "pageerror", "text": str(err)[:400]}))
    page.on("requestfailed", lambda req: events.append({"type": "requestfailed", "text": req.url[:300], "reason": (req.failure or "")[:120]}))
    page.on("response", lambda res: events.append({"type": "http", "text": res.url[:300], "status": res.status}) if res.status >= 400 else None)
    page.goto(run.base + "/" + path, wait_until="load", timeout=20000)
    try:
        page.wait_for_load_state("networkidle", timeout=6000)
    except PlaywrightTimeout:
        pass
    page.wait_for_timeout(800)
    if dismiss_onboarding:
        for sel in ("#finalTourDismiss", ".final-tour-close"):
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=400):
                    loc.click(timeout=1500)
                    page.wait_for_timeout(400)
                    break
            except Exception:
                pass
    page.evaluate("() => { try { window.scrollTo(0, 0); } catch (e) {} }")
    page.wait_for_timeout(150)
    return ctx, page, events


def shots(page: Page, out_dir: Path, stem: str) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    view = out_dir / f"{stem}--viewport.png"
    full = out_dir / f"{stem}.png"
    page.screenshot(path=str(view), full_page=False, animations="disabled")
    page.screenshot(path=str(full), full_page=True, animations="disabled")
    return {"viewport": str(view), "full": str(full)}


def trim_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = []
    for e in events:
        if e["type"] == "http" and "/api/" in e["text"]:
            e = dict(e); e["expected_static"] = True
        if e["type"] in ("requestfailed",) and "/api/" in e["text"]:
            e = dict(e); e["expected_static"] = True
        keep.append(e)
    return keep[:200]


def probe(page: Page) -> dict[str, Any]:
    return page.evaluate(PROBE_JS)


def run_base(run: Run, pages: list[tuple[str, str, str]], variants: list[dict[str, Any]]) -> None:
    for vendor in variants:
        for name, path, title in pages:
            t0 = time.time()
            ctx = page = None
            try:
                ctx, page, events = open_page(run, vendor, page_path(run, name, path))
                shots_map = shots(page, run.out / "screens" / vendor["name"], name)
                data = probe(page)
                for f in data["findings"]:
                    if f["kind"] != "clickable-but-invisible":
                        continue
                    try:
                        loc = page.locator(f["selector"]).first
                        card = loc.locator("xpath=ancestor-or-self::*[self::article or contains(@class,'card')][1]")
                        card.hover(timeout=1500)
                        page.wait_for_timeout(300)
                        op = loc.evaluate(
                            "el => { let o = 1, n = el; while (n && n.nodeType === 1) { o *= parseFloat(getComputedStyle(n).opacity || '1'); n = n.parentElement; } return o; }"
                        )
                        f["hover_revealed"] = bool(op and op > 0.5)
                        f["severity"] = "low" if op and op > 0.5 else "high"
                        if op and op > 0.5:
                            f["why"] += " — revealed only on hover of " + card.evaluate("el => el.className")
                            if vendor.get("mobile"):
                                f["severity"] = "high"
                                f["why"] += "; touch devices have no hover, so this stays invisible but tappable"
                    except Exception:
                        pass
                data.update({"page": name, "path": path, "title": title, "variant": vendor["name"],
                             "url": run.base + "/" + path, "screenshots": shots_map,
                             "seconds": round(time.time() - t0, 1)})
                run.results.append(data)
                run.console.append({"page": name, "variant": vendor["name"], "events": trim_events(events)})
                print(f"  base {vendor['name']:7s} {name:10s} findings={data['stats']['findings']:3d} {data['seconds']}s")
            except Exception as exc:  # keep going, record the failure
                run.results.append({"page": name, "variant": vendor["name"], "path": path, "error": f"{type(exc).__name__}: {exc}",
                                    "trace": traceback.format_exc()[-1200:]})
                print(f"  base {vendor['name']:7s} {name:10s} ERROR {exc}")
            finally:
                if ctx:
                    ctx.close()


def apply_steps(page: Page, steps: list[tuple]) -> None:
    for step in steps:
        action = step[0]
        if action == "click":
            page.locator(step[1]).first.click(timeout=3500)
        elif action == "text":
            page.get_by_text(step[1], exact=False).first.click(timeout=3500)
        elif action == "role":
            page.get_by_role(step[1], name=step[2]).first.click(timeout=3500)
        elif action == "fill":
            page.locator(step[1]).first.fill(step[2], timeout=3500)
        elif action == "select":
            page.locator(step[1]).first.select_option(label=step[2], timeout=2500)
        elif action == "maybe_click":
            try:
                page.locator(step[1]).first.click(timeout=1200)
            except Exception:
                pass
        elif action == "maybe_fill":
            try:
                page.locator(step[1]).first.fill(step[2], timeout=1200)
            except Exception:
                pass
        elif action == "hover":
            page.locator(step[1]).first.hover(timeout=2500)
        elif action == "press":
            page.keyboard.press(step[1])
        elif action == "wait":
            page.wait_for_timeout(step[1])
        elif action == "eval":
            page.evaluate(step[1])
        else:
            raise ValueError(f"unknown step {action!r}")
        page.wait_for_timeout(350)


def run_states(run: Run, pages: list[tuple[str, str, str]], variants: list[dict[str, Any]]) -> None:
    wanted = {p[0]: p for p in pages}
    for vendor in variants:
        for pname, recipes in STATES.items():
            if pname not in wanted or not recipes:
                continue
            name, path, _title = wanted[pname]
            for recipe in recipes:
                t0 = time.time()
                ctx = page = None
                status, error, after = "ok", None, {}
                try:
                    ctx, page, events = open_page(
                        run, vendor, page_path(run, name, path),
                        dismiss_onboarding=not recipe.get("keep_tour"),
                    )
                    apply_steps(page, recipe["steps"])
                    page.wait_for_timeout(500)
                    after = page.evaluate(
                        "() => ({dialogs: Array.from(document.querySelectorAll('dialog[open],[role=dialog]')).filter(e=>e.getBoundingClientRect().width>1).length,"
                        " expanded: document.querySelectorAll('[aria-expanded=\"true\"]').length,"
                        " bodyClass: document.body.className, active: document.activeElement ? document.activeElement.tagName : '',"
                        " ariaModal: !!document.querySelector('[aria-modal=\"true\"]')})"
                    )
                    shots_map = shots(page, run.out / "states" / vendor["name"], f"{name}--{recipe['name']}")
                    changed = after["dialogs"] > 0 or after["expanded"] > 0 or "open" in (after.get("bodyClass") or "")
                    status = "ok" if changed else "no-change"
                except Exception as exc:
                    status, error = "error", f"{type(exc).__name__}: {exc}"
                    try:
                        shots_dir = run.out / "states" / vendor["name"]
                        shots_dir.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(shots_dir / f"{name}--{recipe['name']}--failed.png"), full_page=False) if page else None
                    except Exception:
                        pass
                run.states.append({"page": name, "variant": vendor["name"], "state": recipe["name"], "status": status,
                                   "error": error, "after": after, "seconds": round(time.time() - t0, 1),
                                   "screenshot": str(run.out / "states" / vendor["name"] / f"{name}--{recipe['name']}.png")})
                json.dump({"states": run.states, "discovery": run.discovery}, open(run.out / "states.json", "w"), indent=1)
                print(f"  state {vendor['name']:7s} {name:10s} {recipe['name']:20s} {status}")
                if ctx:
                    ctx.close()


def run_discover(run: Run, pages: list[tuple[str, str, str]], variants: list[dict[str, Any]], per_page: int) -> None:
    for vendor in variants:
        for name, path, _title in pages:
            ctx = page = None
            try:
                ctx, page, _events = open_page(run, vendor, page_path(run, name, path))
                triggers = probe(page)["triggers"][:per_page]
                print(f"  discover {vendor['name']} {name}: {len(triggers)} triggers")
                for trig in triggers:
                    try:
                        page.goto(run.base + "/" + page_path(run, name, path), wait_until="load", timeout=15000)
                        page.wait_for_timeout(500)
                        page.locator(trig["selector"]).first.click(timeout=2500)
                        page.wait_for_timeout(500)
                        after = page.evaluate(
                            "() => ({dialogs: Array.from(document.querySelectorAll('dialog[open],[role=dialog]')).filter(e=>e.getBoundingClientRect().width>1).length,"
                            " menus: Array.from(document.querySelectorAll('[role=menu],[role=listbox]')).filter(e=>e.getBoundingClientRect().width>1).length,"
                            " expanded: document.querySelectorAll('[aria-expanded=\"true\"]').length,"
                            " active: document.activeElement ? document.activeElement.tagName : ''})"
                        )
                        stem = re.sub(r"[^a-z0-9]+", "-", (trig["label"] or trig["tag"]).lower())[:40].strip("-") or "surface"
                        shots_map = shots(page, run.out / "states" / vendor["name"], f"{name}--surface-{stem}")
                        run.discovery.append({"page": name, "variant": vendor["name"], "trigger": trig,
                                              "status": "ok", "after": after, "screenshot": shots_map["viewport"]})
                        json.dump({"states": run.states, "discovery": run.discovery}, open(run.out / "states.json", "w"), indent=1)
                    except Exception as exc:
                        run.discovery.append({"page": name, "variant": vendor["name"], "trigger": trig,
                                              "status": "error", "error": f"{type(exc).__name__}: {exc}"})
            finally:
                if ctx:
                    ctx.close()


def run_focus(run: Run, pages: list[tuple[str, str, str]], tab_count: int) -> None:
    vendor = variant_by_name("desktop")
    for name, path, _title in pages:
        ctx = page = None
        rows = []
        try:
            ctx, page, _events = open_page(run, vendor, page_path(run, name, path))
            for i in range(tab_count):
                page.keyboard.press("Tab")
                page.wait_for_timeout(45)
                info = page.evaluate(FOCUS_JS)
                if info:
                    info["step"] = i + 1
                    rows.append(info)
            (run.out / "screens" / "focus").mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(run.out / "screens" / "focus" / f"{name}--focus.png"), full_page=False)
            run.focus.append({"page": name, "steps": rows,
                              "no_ring": sum(1 for r in rows if not r["ring"]),
                              "off_screen": sum(1 for r in rows if not r["visibleBox"])})
            print(f"  focus {name:10s} steps={len(rows):2d} no-ring={sum(1 for r in rows if not r['ring'])} off-screen={sum(1 for r in rows if not r['visibleBox'])}")
        finally:
            if ctx:
                ctx.close()


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def write_reports(run: Run) -> None:
    findings: list[dict[str, Any]] = []
    for res in run.results:
        for f in res.get("findings", []):
            row = dict(f)
            row.update({"page": res["page"], "variant": res["variant"], "state": "base",
                        "screenshot": res.get("screenshots", {}).get("full", ""), "url": res.get("url", "")})
            findings.append(row)
    by_kind: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for f in findings:
        by_kind[f["kind"]] = by_kind.get(f["kind"], 0) + 1
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1

    manifest = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base": run.base,
        "python": sys.version.split()[0],
        "pages": [{"name": p[0], "path": p[1], "title": p[2]} for p in PAGES],
        "variants": VARIANTS,
        "counts": {
            "pages": len({r["page"] for r in run.results}),
            "variants": len({r["variant"] for r in run.results}),
            "captures": len(run.results),
            "states": len(run.states),
            "states_ok": sum(1 for s in run.states if s["status"] == "ok"),
            "states_error": sum(1 for s in run.states if s["status"] == "error"),
            "states_no_change": sum(1 for s in run.states if s["status"] == "no-change"),
            "discoveries": len(run.discovery),
            "discoveries_ok": sum(1 for d in run.discovery if d["status"] == "ok"),
            "screenshots": sum(2 for _ in run.results) + len(run.states) + sum(2 for _ in run.discovery if _["status"] == "ok"),
            "findings": len(findings),
            "by_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])),
            "by_severity": by_sev,
        },
        "seconds": round(time.time() - run.started, 1),
    }
    json.dump(manifest, open(run.out / "manifest.json", "w"), indent=1)
    json.dump(findings, open(run.out / "findings.json", "w"), indent=1)
    json.dump(run.console, open(run.out / "console.json", "w"), indent=1)
    json.dump({"states": run.states, "discovery": run.discovery}, open(run.out / "states.json", "w"), indent=1)
    json.dump(run.focus, open(run.out / "focus.json", "w"), indent=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:4177")
    ap.add_argument("--login-email", default="")
    ap.add_argument("--login-password", default="")
    ap.add_argument("--invitation", default="", help="invitation id used for ?invitation= pages")
    ap.add_argument("--out", default="artifacts/ui-audit-2026-10-29/pass2")
    ap.add_argument("--mode", default="all", choices=["base", "states", "discover", "focus", "all"])
    ap.add_argument("--pages", default="", help="comma-separated page names (default: all)")
    ap.add_argument("--variants", default="desktop,mobile,km,dark")
    ap.add_argument("--discover-per-page", type=int, default=10)
    ap.add_argument("--discover-variants", default="desktop,mobile")
    ap.add_argument("--state-variants", default="desktop")
    ap.add_argument("--focus-tabs", type=int, default=24)
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = [n.strip() for n in args.pages.split(",") if n.strip()]
    pages = [p for p in PAGES if not names or p[0] in names]
    variants = [variant_by_name(v.strip()) for v in args.variants.split(",") if v.strip()]
    state_variants = [variant_by_name(v.strip()) for v in args.state_variants.split(",") if v.strip()]
    discover_variants = [variant_by_name(v.strip()) for v in args.discover_variants.split(",") if v.strip()]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed, args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        run = Run(out=out, base=args.base.rstrip("/"), browser=browser,
                  email=args.login_email, password=args.login_password, invitation=args.invitation)
        if args.login_email:
            seed_ctx = browser.new_context()
            resp = seed_ctx.request.post(args.base.rstrip("/") + "/api/auth/login",
                                         data={"email": args.login_email, "password": args.login_password})
            if resp.status >= 400:
                browser.close()
                raise SystemExit(f"login failed: HTTP {resp.status} {resp.text()[:200]}")
            run.storage = seed_ctx.storage_state()
            seed_ctx.close()
            print("logged in once; reusing storage state for every context")
        print(f"audit {args.mode}: {len(pages)} pages x {len(variants)} variants -> {out}")
        try:
            if args.mode in ("base", "all"):
                print("base captures")
                run_base(run, pages, variants)
            if args.mode in ("states", "all"):
                print("function states")
                run_states(run, pages, state_variants)
            if args.mode in ("discover", "all"):
                print("surface discovery")
                run_discover(run, pages, discover_variants, args.discover_per_page)
            if args.mode in ("focus", "all"):
                print("focus walk")
                run_focus(run, pages, args.focus_tabs)
        finally:
            browser.close()
        write_reports(run)

    m = json.load(open(out / "manifest.json"))
    print(json.dumps(m["counts"], indent=1))
    print(f"wrote {out} in {m['seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
