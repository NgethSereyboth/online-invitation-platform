"""ui-audit-capture.py — site-wide screenshot + layout-heuristics capture for the UI audit.

Read-only with respect to app sources: writes only under the chosen --out
directory (default artifacts/ui-audit/capture).

What it does
------------
1. Boots one throwaway account and seeds ONE invitation (published, three
   guests, one RSVP — best effort) so authenticated pages render with data.
2. Loads every shipped page (the 16 routes mirrored from tools/lib/repo.mjs
   PAGES) across viewports / themes / languages / auth states.
3. For each capture writes a viewport screenshot (plus a curated full-page
   screenshot) and runs an in-page heuristics report: horizontal overflow,
   clipped text, occluded text (sampled at top/middle/bottom scroll), low
   contrast, tiny text, small tap targets, nameless interactive elements,
   unlabeled inputs, broken/missing images, off-centre max-width containers,
   fixed/sticky elements, font/colour inventories, heading counts,
   console/HTTP/request errors.

Usage (against the repo's own server wrapper):

    python3 "F:\\Project\\eInvite\\_canva-verify\\run-with-server.py" -- \
        python3 tools/ui-audit-capture.py --out artifacts/ui-audit/capture

Smoke run (one page / one viewport):

    ... -- python3 tools/ui-audit-capture.py --only index.html \
        --states user --themes light --langs en --viewports 1440x900

Outputs under <out>/:
    shots/<state>/<page>/<lang>-<theme>-<WxH>.png        viewport shot
    shots/<state>/<page>/<lang>-<theme>-<WxH>--full.png  full-page shot (curated)
    heuristics.jsonl     one JSON row per capture (the objective findings)
    console.jsonl        one JSON row per capture (console/http/request errors)
    summary.txt, summary.json, README.md
"""
from __future__ import annotations

import argparse
import json
import os
import random
import string
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))

from browser_runtime import dismiss_editor_onboarding, launch_chromium  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

# The 16 shipped routes — mirrors tools/lib/repo.mjs PAGES.
PAGES = [
    'index.html', 'dashboard.html', 'public.html', 'admin.html', 'account.html',
    'billing.html', 'verify.html', 'reset.html', 'privacy.html', 'guests.html',
    'responses.html', 'analytics.html', 'materials.html', 'checkin.html',
    'templates.html', 'designer.html',
]

EDITOR_PAGES = {'index.html', 'designer.html'}
PUBLIC_PAGE = 'public.html'

# Capture profiles per (state, theme, lang). Full-page shots are taken when
# theme == light and vw in {1440, 375, 320}, or vw == 1440 otherwise.
PROFILES = {
    ('user', 'light', 'en'): [(1440, 900), (1024, 768), (768, 1024), (375, 667), (320, 568)],
    ('user', 'dark', 'en'): [(1440, 900), (375, 667)],
    ('user', 'light', 'km'): [(1440, 900)],
    ('guest', 'light', 'en'): [(1440, 900)],
}

FREEZE_CSS = ('*,*::before,*::after{animation:none!important;transition:none!important;'
              'caret-color:transparent!important}')

PASSWORD = 'Ui-audit-password-123!'

DOCUMENT = {
    'eventType': 'Wedding',
    'fields': {
        'names': 'Sokha & Dara',
        'message': 'Together with our families, we invite you to celebrate our wedding.',
        'date': '2026-12-12',
        'venue': 'Sofitel Phnom Penh',
    },
    'objects': {},
    'designPages': [],
    'sectionOrder': ['schedule', 'venue', 'rsvp'],
    'settings': {'rsvpEnabled': True},
}

HEURISTICS_JS = r"""() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const de = document.documentElement, body = document.body;
  const out = {
    url: location.pathname + location.search,
    title: document.title,
    viewport: { w: vw, h: vh },
    theme: de.dataset.theme || de.dataset.themeMode || '',
    lang: de.lang || '',
    docScrollW: de.scrollWidth, docScrollH: de.scrollHeight,
    bodyTextLen: (body.innerText || '').length,
    viewportMeta: (document.querySelector('meta[name=viewport]') || {}).content || '',
    h1Count: document.querySelectorAll('h1').length,
    hCounts: ['h1','h2','h3','h4','h5','h6'].reduce((a,t)=>{a[t]=document.querySelectorAll(t).length;return a;},{}),
    horizOverflow: de.scrollWidth > vw + 1,
    overflowOffenders: [], clippedText: [], occlusion: [],
    tinyText: [], smallTargets: [], contrastIssues: [],
    brokenImages: [], imagesMissingAlt: 0, imagesMissingDims: 0,
    namelessInteractive: [], inputsWithoutLabel: 0, defaultStyledControls: [],
    offCenter: [], fixedEls: [], tabindexPositive: 0, ariaLiveCount: 0,
    fontSizes: {}, fontFamilies: {}, textColors: {}
  };
  const q = (n) => { let s = n.tagName.toLowerCase(); if (n.id) s += '#' + n.id; else if (typeof n.className === 'string' && n.className.trim()) s += '.' + n.className.trim().split(/\s+/).slice(0,2).join('.'); return s; };
  const pathOf = (n) => { const p = []; let d = 0; while (n && n.nodeType === 1 && d < 5) { p.unshift(q(n)); n = n.parentElement; d++; } return p.join('>'); };
  const txt = (n) => (n.innerText || n.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 70);
  const parseColor = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(parseFloat); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const blend = (fg, bg) => ({ r: fg.r*fg.a + bg.r*(1-fg.a), g: fg.g*fg.a + bg.g*(1-fg.a), b: fg.b*fg.a + bg.b*(1-fg.a), a: 1 });
  const lum = (c) => { const f = x => { x /= 255; return x <= 0.03928 ? x/12.92 : Math.pow((x+0.055)/1.055, 2.4); }; return .2126*f(c.r) + .7152*f(c.g) + .0722*f(c.b); };
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1,l2) + .05) / (Math.min(l1,l2) + .05); };
  const effBg = (n) => { const chain = []; let m = n, d = 0;
    while (m && m.nodeType === 1 && d < 24) { const c = parseColor(getComputedStyle(m).backgroundColor); if (c && c.a > 0) { chain.unshift(c); if (c.a >= 0.999) break; } m = m.parentElement; d++; }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    if (!chain.length) { const b = parseColor(getComputedStyle(body).backgroundColor); if (b && b.a > 0) chain.push(b); }
    for (const c of chain) base = blend(c, base);
    return base; };
  const rectOf = (n) => { const r = n.getBoundingClientRect(); return { x: Math.round(r.left), y: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  const occludedBy = (el, r, points) => {
    for (const [fx, fy] of points) {
      const x = r.left + r.width * fx, y = r.top + r.height * fy;
      if (x <= 2 || y <= 2 || x >= vw - 2 || y >= vh - 2) continue;
      const top = document.elementFromPoint(x, y);
      if (top && top !== el && !el.contains(top) && !top.contains(el)) {
        const tcs = getComputedStyle(top);
        if (tcs.display !== 'none' && tcs.visibility !== 'hidden' && parseFloat(tcs.opacity) > 0) return pathOf(top);
      }
    }
    return null;
  };

  const docClipX = ['hidden','clip'].includes(getComputedStyle(de).overflowX) || ['hidden','clip'].includes(getComputedStyle(body).overflowX);
  const all = [...document.querySelectorAll('*')];
  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) continue;

    const ownText = el.children.length === 0 ? txt(el) : '';
    if (ownText) {
      out.fontSizes[cs.fontSize] = (out.fontSizes[cs.fontSize] || 0) + 1;
      const ff = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
      out.fontFamilies[ff] = (out.fontFamilies[ff] || 0) + 1;
      out.textColors[cs.color] = (out.textColors[cs.color] || 0) + 1;
      if (parseFloat(cs.fontSize) < 12) out.tinyText.push({ el: pathOf(el), size: cs.fontSize, text: ownText.slice(0, 40) });
      if (el.scrollWidth > el.clientWidth + 1 && ['hidden','clip'].includes(cs.overflowX)) out.clippedText.push({ el: pathOf(el), axis: 'x', over: el.scrollWidth - el.clientWidth, text: ownText.slice(0, 40) });
      if (el.scrollHeight > el.clientHeight + 1 && ['hidden','clip'].includes(cs.overflowY)) out.clippedText.push({ el: pathOf(el), axis: 'y', over: el.scrollHeight - el.clientHeight, text: ownText.slice(0, 40) });
      const fg = parseColor(cs.color);
      if (fg && fg.a > 0.05) {
        const bg = effBg(el);
        const fgc = fg.a < 1 ? blend(fg, bg) : fg;
        const cr = ratio(fgc, bg);
        const fs = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 600;
        const need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
        if (cr < need - 1e-9) out.contrastIssues.push({ el: pathOf(el), ratio: Math.round(cr * 100) / 100, need, fg: cs.color, bg: 'rgb(' + Math.round(bg.r) + ',' + Math.round(bg.g) + ',' + Math.round(bg.b) + ')', size: cs.fontSize, text: ownText.slice(0, 40) });
      }
      if (r.width > 24 && r.height > 14) {
        const cover = occludedBy(el, r, [[0.5, 0.5], [0.2, 0.5], [0.8, 0.5]]);
        if (cover) out.occlusion.push({ el: pathOf(el), text: ownText.slice(0, 40), coveredBy: cover });
      }
    }

    if (r.right > vw + 1 && r.width <= vw * 4 && el.offsetParent !== null) {
      let inScrollable = false, m = el.parentElement, d = 0;
      while (m && d < 8) { const mcs = getComputedStyle(m); if (['auto','scroll'].includes(mcs.overflowX) && m.getBoundingClientRect().width <= vw + 2) { inScrollable = true; break; } m = m.parentElement; d++; }
      out.overflowOffenders.push({ el: pathOf(el), right: Math.round(r.right), w: Math.round(r.width), inScrollable, docClipped: docClipX, text: txt(el).slice(0, 40) });
    }

    if (el.matches('a,button,input,select,textarea,[role="button"],[onclick]')) {
      const w = Math.round(r.width), h = Math.round(r.height);
      if ((w < 24 || h < 24) && txt(el)) out.smallTargets.push({ el: pathOf(el), w, h, text: txt(el).slice(0, 30) });
      const name = (el.getAttribute('aria-label') || el.getAttribute('title') || txt(el) || '').trim();
      if (!name && el.matches('button,a,[role="button"]')) out.namelessInteractive.push({ el: pathOf(el), w, h });
      if (el.matches('button,input,select,textarea')) {
        const ff = cs.fontFamily.split(',')[0].toLowerCase().trim();
        if (ff.startsWith('times') || ff === 'serif') out.defaultStyledControls.push({ el: pathOf(el), ff: cs.fontFamily.split(',')[0] });
      }
      if (el.matches('input,select,textarea') && el.offsetParent !== null) {
        let hasLabel = !!el.getAttribute('aria-label') || !!el.closest('label');
        if (!hasLabel && el.id) { try { hasLabel = !!document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); } catch (e) { /* ignore */ } }
        if (!hasLabel) out.inputsWithoutLabel++;
      }
    }
    if (cs.position === 'fixed' || cs.position === 'sticky') out.fixedEls.push({ el: pathOf(el), pos: cs.position, rect: rectOf(el) });
    const ti = el.getAttribute('tabindex'); if (ti && parseInt(ti) > 0) out.tabindexPositive++;
    if (el.hasAttribute('aria-live')) out.ariaLiveCount++;
  }

  for (const img of document.querySelectorAll('img')) {
    const r = img.getBoundingClientRect();
    const visible = r.width > 1 && r.height > 1 && getComputedStyle(img).display !== 'none';
    if (!img.complete) continue;
    if (img.naturalWidth === 0 && visible) out.brokenImages.push({ src: (img.currentSrc || img.src || '').slice(-140), el: pathOf(img) });
    if (!img.hasAttribute('alt')) out.imagesMissingAlt++;
    if (!img.hasAttribute('width') || !img.hasAttribute('height')) out.imagesMissingDims++;
  }

  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.marginLeft !== 'auto' || cs.marginRight !== 'auto') continue;
    if (cs.maxWidth === 'none' || !cs.maxWidth.endsWith('px')) continue;
    const mw = parseFloat(cs.maxWidth); if (!(mw > 240)) continue;
    const r = el.getBoundingClientRect();
    if (Math.abs(r.width - mw) > 2) continue;
    const left = r.left, right = vw - r.right;
    if (Math.abs(left - right) > 2) out.offCenter.push({ el: pathOf(el), left: Math.round(left), right: Math.round(right), gap: Math.round(Math.abs(left - right)) });
  }

  const cap = (a, n) => a.slice(0, n);
  out.overflowOffenders = cap(out.overflowOffenders, 15);
  out.clippedText = cap(out.clippedText, 15);
  out.occlusion = cap(out.occlusion, 15);
  out.tinyText = cap(out.tinyText, 15);
  out.smallTargets = cap(out.smallTargets, 15);
  out.contrastIssues = cap(out.contrastIssues, 20);
  out.namelessInteractive = cap(out.namelessInteractive, 10);
  out.defaultStyledControls = cap(out.defaultStyledControls, 10);
  out.offCenter = cap(out.offCenter, 10);
  out.fixedEls = cap(out.fixedEls, 10);
  const top = (o, n) => Object.fromEntries(Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, n));
  out.fontSizes = top(out.fontSizes); out.fontFamilies = top(out.fontFamilies); out.textColors = top(out.textColors);
  return out;
}"""

OCCLUSION_JS = r"""() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const q = (n) => { let s = n.tagName.toLowerCase(); if (n.id) s += '#' + n.id; else if (typeof n.className === 'string' && n.className.trim()) s += '.' + n.className.trim().split(/\s+/).slice(0,2).join('.'); return s; };
  const pathOf = (n) => { const p = []; let d = 0; while (n && n.nodeType === 1 && d < 5) { p.unshift(q(n)); n = n.parentElement; d++; } return p.join('>'); };
  const txt = (n) => (n.innerText || n.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
  const found = [];
  for (const el of document.querySelectorAll('*')) {
    if (el.children.length) continue;
    const t = txt(el); if (!t) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 24 || r.height <= 14) continue;
    for (const [fx, fy] of [[0.5, 0.5], [0.2, 0.5], [0.8, 0.5]]) {
      const x = r.left + r.width * fx, y = r.top + r.height * fy;
      if (x <= 2 || y <= 2 || x >= vw - 2 || y >= vh - 2) continue;
      const top = document.elementFromPoint(x, y);
      if (top && top !== el && !el.contains(top) && !top.contains(el)) {
        const tcs = getComputedStyle(top);
        if (tcs.display !== 'none' && tcs.visibility !== 'hidden' && parseFloat(tcs.opacity) > 0) {
          found.push({ el: pathOf(el), text: t.slice(0, 40), coveredBy: pathOf(top) });
        }
      }
      break;
    }
    if (found.length > 20) break;
  }
  return found.slice(0, 15);
}"""


def seed_account(page, base):
    """Register one throwaway account, seed + publish one invitation, best-effort guests/RSVP."""
    stamp = f'{int(time.time())}-{"".join(random.choices(string.ascii_lowercase, k=4))}'
    email = f'ui-audit-{stamp}@example.com'
    slug = f'ui-audit-{stamp}'
    info = {'email': email, 'slug': slug, 'invite_id': None, 'publish_ok': False,
            'guests_ok': 0, 'rsvp_ok': False, 'notes': []}

    r = page.request.post(base + '/api/auth/register', data={'email': email, 'password': PASSWORD})
    if not r.ok:
        raise RuntimeError(f'register failed: {r.status} {r.text()[:200]}')
    r = page.request.post(base + '/api/invitations', data={'slug': slug, 'document': DOCUMENT})
    if not r.ok:
        raise RuntimeError(f'invitation create failed: {r.status} {r.text()[:200]}')
    invite = r.json()
    info['invite_id'] = invite.get('id')
    if not info['invite_id']:
        raise RuntimeError(f'invitation create returned no id: {invite}')
    invite_id = info['invite_id']

    r = page.request.post(f'{base}/api/invitations/{invite_id}/publish', data={'document': DOCUMENT})
    info['publish_ok'] = r.ok
    if not r.ok:
        info['notes'].append(f'publish {r.status}: {r.text()[:140]}')

    for name in ('Sok Dara', 'Chan Srey', 'Alex Morgan', 'Mealea Rin'):
        r = page.request.post(f'{base}/api/invitations/{invite_id}/guests', data={'name': name})
        if r.ok:
            info['guests_ok'] += 1
    r = page.request.post(f'{base}/api/public/{slug}/rsvps',
                          data={'name': 'Kim Long', 'status': 'Yes, joyfully', 'count': 2})
    info['rsvp_ok'] = r.ok
    if not r.ok:
        info['notes'].append(f'rsvp {r.status}: {r.text()[:140]}')

    return info


def wire_events(page, ev):
    page.on('console', lambda m: ev['console'].append('console: ' + m.text[:200]) if m.type == 'error' else None)
    page.on('pageerror', lambda e: ev['console'].append('pageerror: ' + str(e)[:200]))
    page.on('requestfailed', lambda r: ev['http'].append(f"requestfailed {r.url[:150]} {r.failure or ''}"))
    page.on('response', lambda r: ev['http'].append(f'{r.status} {r.url[:160]}') if r.status >= 400 else None)


def capture_combo(page, ev, base, state, theme, lang, page_name, w, h, slug, out_dir, settle_ms, full):
    ev['console'] = []
    ev['http'] = []
    row = {'state': state, 'theme': theme, 'lang': lang, 'page': page_name,
           'vw': w, 'vh': h, 'navError': None, 'finalUrl': None, 'shot': None, 'full': None}
    url = f'{base}/i/{quote(slug)}' if page_name == PUBLIC_PAGE else f'{base}/{page_name}'
    page.set_viewport_size({'width': w, 'height': h})
    try:
        page.goto(url, wait_until='load', timeout=45000)
    except Exception as exc:  # noqa: BLE001 — record and continue
        row['navError'] = f'goto: {str(exc)[:160]}'
    else:
        try:
            page.wait_for_load_state('networkidle', timeout=12000)
        except Exception:  # noqa: BLE001 — pollers may keep sockets busy; not fatal
            pass
        try:
            page.wait_for_function('document.fonts.status === "loaded"', timeout=8000)
        except Exception:  # noqa: BLE001
            pass

    if state == 'user' and page_name in EDITOR_PAGES and not row['navError']:
        try:
            page.wait_for_function("document.documentElement.dataset.editorReady === 'true'", timeout=20000)
        except Exception:  # noqa: BLE001
            pass
        try:
            dismiss_editor_onboarding(page, timeout=8000)
        except Exception:  # noqa: BLE001
            pass
        try:
            page.evaluate('() => { try { EInviteCanvasViewController.fit(); } catch (e) {} }')
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(400)

    page.wait_for_timeout(settle_ms)
    try:
        page.add_style_tag(content=FREEZE_CSS)
    except Exception:  # noqa: BLE001
        pass
    page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')

    heur = page.evaluate(HEURISTICS_JS)

    # Occlusion rescans at two scrolled positions (sticky headers / sticky rails).
    combined_occ = list(heur.get('occlusion') or [])
    for frac in (0.5, 1.0):
        try:
            page.evaluate('f => { const d = document.documentElement; window.scrollTo(0, Math.max(0, (d.scrollHeight - innerHeight) * f)); }', frac)
            page.wait_for_timeout(150)
            for item in page.evaluate(OCCLUSION_JS):
                key = (item['el'], item['coveredBy'])
                if all((o[0], o[1]) != key for o in combined_occ):
                    combined_occ.append(item)
        except Exception:  # noqa: BLE001
            pass
    heur['occlusion'] = combined_occ[:15]

    page.evaluate('() => window.scrollTo(0, 0)')
    page.wait_for_timeout(120)

    shot_dir = out_dir / 'shots' / state / page_name
    shot_dir.mkdir(parents=True, exist_ok=True)
    name = f'{lang}-{theme}-{w}x{h}'
    shot = shot_dir / f'{name}.png'
    page.screenshot(path=str(shot), full_page=False)
    row['shot'] = str(shot.relative_to(ROOT))
    if full:
        full_shot = shot_dir / f'{name}--full.png'
        page.screenshot(path=str(full_shot), full_page=True)
        row['full'] = str(full_shot.relative_to(ROOT))

    row['finalUrl'] = page.url
    row['h'] = heur
    row['consoleErrors'] = ev['console'][:20]
    row['httpErrors'] = ev['http'][:20]
    return row


def summarize(out_dir, rows):
    by_page = {}
    for r in rows:
        by_page.setdefault(r['page'], []).append(r)

    def score(h):
        if not h:
            return 0
        return (len(h.get('overflowOffenders') or []) + len(h.get('clippedText') or [])
                + len(h.get('occlusion') or []) + len(h.get('tinyText') or [])
                + len(h.get('smallTargets') or []) + len(h.get('contrastIssues') or [])
                + len(h.get('namelessInteractive') or []) + (h.get('inputsWithoutLabel') or 0)
                + len(h.get('brokenImages') or []) + len(h.get('offCenter') or [])
                + len(r.get('consoleErrors') or []) + len(r.get('httpErrors') or []))

    agg = {}
    lines = []
    lines.append('page | combos | navErr | consoleErr | httpErr | overflow(vw320/375) | offCenter | clipped | occl | tiny | tgt<24 | contrast | nameless | noLabel | brokenImg | minTextLen | worstScore')
    for page_name, page_rows in sorted(by_page.items()):
        nav_err = sum(1 for r in page_rows if r['navError'])
        cons = sum(len(r.get('consoleErrors') or []) for r in page_rows)
        http = sum(len(r.get('httpErrors') or []) for r in page_rows)
        small = [r for r in page_rows if r['vw'] <= 375 and r['state'] == 'user' and r['lang'] == 'en']
        overflow = 0
        for r in small:
            if r.get('h') and r['h'].get('horizOverflow'):
                overflow += 1
        def cnt(key):
            return sum(len(r['h'].get(key) or []) for r in page_rows if r.get('h'))
        def cnt_int(key):
            return sum((r['h'].get(key) or 0) for r in page_rows if r.get('h'))
        min_text = min([r['h']['bodyTextLen'] for r in page_rows if r.get('h')] or [0])
        agg[page_name] = {
            'combos': len(page_rows), 'navErrors': nav_err, 'consoleErrors': cons, 'httpErrors': http,
            'overflowAt320_375': overflow, 'offCenter': cnt('offCenter'), 'clipped': cnt('clippedText'),
            'occlusion': cnt('occlusion'), 'tinyText': cnt('tinyText'), 'smallTargets': cnt('smallTargets'),
            'contrast': cnt('contrastIssues'), 'nameless': cnt('namelessInteractive'),
            'inputsWithoutLabel': cnt_int('inputsWithoutLabel'), 'brokenImages': cnt('brokenImages'),
            'minBodyTextLen': min_text, 'worstScore': max(score(r.get('h')) for r in page_rows),
        }
        a = agg[page_name]
        lines.append(f"{page_name} | {a['combos']} | {nav_err} | {cons} | {http} | {overflow} | {a['offCenter']} | "
                     f"{a['clipped']} | {a['occlusion']} | {a['tinyText']} | {a['smallTargets']} | {a['contrast']} | "
                     f"{a['nameless']} | {a['inputsWithoutLabel']} | {a['brokenImages']} | {min_text} | {a['worstScore']}")

    lines.append('')
    lines.append('Per-capture detail (non-zero categories; light/en/user rows first):')
    for r in rows:
        h = r.get('h') or {}
        errs = len(r.get('consoleErrors') or []) + len(r.get('httpErrors') or [])
        cats = []
        for key in ('overflowOffenders', 'clippedText', 'occlusion', 'tinyText', 'smallTargets',
                    'contrastIssues', 'namelessInteractive', 'offCenter', 'brokenImages'):
            n = len(h.get(key) or [])
            if n:
                cats.append(f'{key}={n}')
        nolabel = h.get('inputsWithoutLabel') or 0
        if nolabel:
            cats.append(f'inputsWithoutLabel={nolabel}')
        if h.get('horizOverflow'):
            cats.insert(0, 'HORIZ_SCROLL')
        if errs:
            cats.append(f'errors={errs}')
        if r['navError']:
            cats.insert(0, 'NAV:' + r['navError'][:60])
        if cats:
            lines.append(f"{r['page']} {r['state']} {r['lang']}/{r['theme']} {r['vw']}x{r['vh']}: " + ', '.join(cats))

    (out_dir / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out_dir / 'summary.json').write_text(json.dumps(agg, indent=2), encoding='utf-8')
    return '\n'.join(lines[:18])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', default=os.environ.get('BASE_URL') or 'http://127.0.0.1:8124')
    ap.add_argument('--out', default=str(ROOT / 'artifacts' / 'ui-audit' / 'capture'))
    ap.add_argument('--only', default='', help='comma-separated page names (index or index.html)')
    ap.add_argument('--states', default='user,guest')
    ap.add_argument('--themes', default='light,dark')
    ap.add_argument('--langs', default='en,km')
    ap.add_argument('--viewports', default='', help='override profile, e.g. 1440x900,375x667')
    ap.add_argument('--settle', type=int, default=700)
    ap.add_argument('--no-full', action='store_true')
    args = ap.parse_args()

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    only = {p.strip() if p.strip().endswith('.html') else p.strip() + '.html' for p in args.only.split(',') if p.strip()}
    pages = [p for p in PAGES if (not only or p in only)]
    states = [s for s in args.states.split(',') if s in ('user', 'guest')]
    themes = [t for t in args.themes.split(',') if t in ('light', 'dark')]
    langs = [l for l in args.langs.split(',') if l in ('en', 'km')]
    override = None
    if args.viewports:
        override = []
        for part in args.viewports.split(','):
            w, h = part.lower().split('x')
            override.append((int(w), int(h)))

    heur_path = out_dir / 'heuristics.jsonl'
    cons_path = out_dir / 'console.jsonl'
    rows = []
    seed_info = None

    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            for state in states:
                for theme in themes:
                    for lang in langs:
                        key = (state, theme, lang)
                        if key not in PROFILES and not override:
                            continue
                        viewports = override or PROFILES[key]
                        kw = {'color_scheme': theme, 'reduced_motion': 'reduce',
                              'locale': 'km-KH' if lang == 'km' else 'en-US'}
                        context = browser.new_context(**kw)
                        page = context.new_page()
                        ev = {'console': [], 'http': []}
                        wire_events(page, ev)

                        if state == 'user':
                            if seed_info is None:
                                seed_info = seed_account(page, args.base)
                                print(f"[seed] {json.dumps(seed_info)}", flush=True)
                            else:
                                r = page.request.post(args.base + '/api/auth/login',
                                                      data={'email': seed_info['email'], 'password': PASSWORD})
                                if not r.ok:
                                    print(f"[seed] login failed: {r.status} {r.text()[:120]}", flush=True)
                            init = (f"try{{localStorage.setItem('sovan-active-invite',{json.dumps(str(seed_info['invite_id']))});"
                                    f"localStorage.setItem('einvite-theme-mode','{theme}');"
                                    f"localStorage.setItem('einvite-lang','{lang}');}}catch(e){{}}")
                            page.add_init_script(init)
                        else:
                            init = (f"try{{localStorage.setItem('einvite-theme-mode','{theme}');"
                                    f"localStorage.setItem('einvite-lang','{lang}');}}catch(e){{}}")
                            page.add_init_script(init)

                        # Resolve the public-page slug only AFTER the user state has had a
                        # chance to seed + publish. Fixed 2026-10-18: this used to run
                        # before seed_account(), so the very first combo of every sweep
                        # navigated to /i/no-invite and captured the not-found state.
                        slug = seed_info['slug'] if seed_info else 'no-invite'

                        for page_name in pages:
                            for w, h in viewports:
                                full = (not args.no_full) and ((theme == 'light' and w in (1440, 375, 320)) or w == 1440)
                                try:
                                    row = capture_combo(page, ev, args.base, state, theme, lang,
                                                        page_name, w, h, slug, out_dir, args.settle, full)
                                except Exception as exc:  # noqa: BLE001 — never abort the sweep
                                    row = {'state': state, 'theme': theme, 'lang': lang, 'page': page_name,
                                           'vw': w, 'vh': h, 'navError': f'harness: {str(exc)[:180]}',
                                           'h': None, 'consoleErrors': [], 'httpErrors': []}
                                rows.append(row)
                                with heur_path.open('a', encoding='utf-8') as fh:
                                    fh.write(json.dumps(row, ensure_ascii=False) + '\n')
                                if row.get('consoleErrors') or row.get('httpErrors'):
                                    with cons_path.open('a', encoding='utf-8') as fh:
                                        fh.write(json.dumps({'state': state, 'theme': theme, 'lang': lang,
                                                             'page': page_name, 'vw': w, 'vh': h,
                                                             'console': row.get('consoleErrors'),
                                                             'http': row.get('httpErrors')}, ensure_ascii=False) + '\n')
                                hh = row.get('h') or {}
                                cats = sum(len(hh.get(k) or []) for k in ('overflowOffenders', 'clippedText', 'occlusion', 'tinyText', 'smallTargets', 'contrastIssues'))
                                print(f"[{len(rows)}] {state} {lang}/{theme} {page_name} {w}x{h} "
                                      f"hoverflow={int(bool(hh.get('horizOverflow')))} cats={cats} "
                                      f"errs={len(row.get('consoleErrors') or []) + len(row.get('httpErrors') or [])}"
                                      + (" NAVERR" if row.get('navError') else ''), flush=True)
                        context.close()
        finally:
            browser.close()

    summary_head = summarize(out_dir, rows)
    (out_dir / 'README.md').write_text(
        '# UI audit capture\n\n'
        'Produced by `tools/ui-audit-capture.py`. Re-run with:\n\n'
        '```\npython3 "F:\\Project\\eInvite\\_canva-verify\\run-with-server.py" -- \\\n'
        '    python3 tools/ui-audit-capture.py --out artifacts/ui-audit/capture\n```\n\n'
        'Key files: `heuristics.jsonl` (per-capture findings), `console.jsonl` (errors), '
        '`summary.txt` (compact table), `summary.json` (aggregates), `shots/` (PNGs).\n',
        encoding='utf-8')
    print('UI_AUDIT_CAPTURE_DONE rows=' + str(len(rows)))
    print(summary_head)
    return 0


if __name__ == '__main__':
    sys.exit(main())
