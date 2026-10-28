#!/usr/bin/env python3
"""lt63-state-probe.py — LT-6.3 interaction-state probe for the `!important` ratchet.

The FB-19 rest-state probe (``tools/fb19-probe-dom.py``) evaluates every candidate
selector against rendered pages at rest. OD-10's continuation requires the
*interaction* states too (hover / focus / drag / JS-added classes), which is this
probe's whole job: it revisits the same seeded matrix and re-evaluates the
candidate selectors **while each interaction state is live**.

  * hover sweep — every visible ``button`` / ``a`` / ``[role="button"]`` /
    ``summary`` handle is hovered; the selectors are evaluated right after each
    hover, while the pointer still rests on the element, so ``:hover`` rules and
    hover-created classes count as live;
  * focus sweep — every visible ``input`` / ``textarea`` / ``select`` /
    ``[contenteditable]`` / ``[tabindex]`` target is focused and evaluated while
    focused;
  * click sweep — visible ``button``\\ s whose label is not destructive are
    clicked (menus, tabs, popovers: the JS-added classes a rest probe cannot see)
    and evaluated after each click; a navigation is rolled back by re-visiting
    the page URL;
  * drag — on editor routes the first canvas object is pointer-dragged and the
    selectors are evaluated while the drag is held and after release.

A selector with any hit during any of these states is live and must be kept.
The output JSON mirrors the FB-19 probe shape (per selector ``liveAny`` +
``hits``) so ``tools/fb19-merge-dead.py`` can merge it unchanged.

Usage::

    python3 tools/lt63-state-probe.py --base http://127.0.0.1:8163 \
        --candidates artifacts/next-work/lt-6-3/pass1/dead-static.json \
        --only-dead artifacts/next-work/lt-6-3/pass1/dom-presence.json \
        --out artifacts/next-work/lt-6-3/pass1/state-presence.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))

from browser_runtime import dismiss_editor_onboarding, launch_chromium, mark_editor_onboarding_seen  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

# Reuse the capture tool's DOCUMENT + seed_account verbatim so the probe sees the
# same page state as the NW-2.2 matrix and the FB-19 probes.
_capture_spec = importlib.util.spec_from_file_location(
    'ui_audit_capture', ROOT / 'tools' / 'ui-audit-capture.py')
capture = importlib.util.module_from_spec(_capture_spec)
sys.modules['ui_audit_capture'] = capture
_capture_spec.loader.exec_module(capture)

PAGES = list(capture.PAGES)
EDITOR_PAGES = {'index.html', 'designer.html'}
PUBLIC_PAGE = capture.PUBLIC_PAGE
EDITOR_ROUTE = '/invitations/{INV}/editor'

# Non-editor pages run one desktop visit each; the editor route runs both the
# desktop and the 375 px visit (its mobile chrome is where #mobileEditorV14Bar
# and the mobile toolbar candidates would appear). Guest combo includes the 375
# public splash because .open-cover is a splash-only surface.
COMBOS = [
    ('user', 'light', 'en', [(1440, 900), (375, 667)]),
    ('guest', 'light', 'en', [(1440, 900), (375, 667)]),
]

PROBE_JS = """(sels) => {
  const res = {};
  for (const sel of sels) {
    let el = sel, n = 0;
    try {
      el = sel.replace(/::(before|after|placeholder|selection|marker|first-line|first-letter)\\b/g, '');
      n = el ? document.querySelectorAll(el).length : 0;
    } catch (e) { n = -1; }
    res[sel] = n;
  }
  return res;
}"""

DESTRUCTIVE = re.compile(
    r'delete|remove|publish|unpublish|sign ?out|log ?out|reset|clear|purge|'
    r'archive|force|revoke|cancel|discard|wipe',
    re.I)

HOVER_CAP = 50
FOCUS_CAP = 40
CLICK_CAP = 18


def visit(page, base, state, page_name, inv_id, slug):
    if page_name == 'editor.html':
        url = base + EDITOR_ROUTE.replace('{INV}', str(inv_id))
    elif page_name == PUBLIC_PAGE:
        url = f'{base}/i/' + slug
    else:
        url = f'{base}/{page_name}'
    try:
        page.goto(url, wait_until='load', timeout=45000)
    except Exception as exc:  # noqa: BLE001
        return url, f'goto: {str(exc)[:140]}'
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:  # noqa: BLE001
        pass
    if state == 'user' and page_name in EDITOR_PAGES:
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
    page.wait_for_timeout(250)
    return url, None


def eval_hits(page, selectors, counts, key, errors):
    try:
        res = page.evaluate(PROBE_JS, selectors)
    except Exception as exc:  # noqa: BLE001
        errors.append(f'{key}: evaluate {str(exc)[:140]}')
        return
    for sel, n in res.items():
        if n == -1:
            errors.append(f'{key}: invalid selector {sel[:80]}')
        elif n > 0:
            counts.setdefault(sel, {}).setdefault(key, min(n, 9999))


def _label(handle):
    try:
        aria = handle.get_attribute('aria-label') or ''
    except Exception:  # noqa: BLE001
        aria = ''
    try:
        text = handle.inner_text() or ''
    except Exception:  # noqa: BLE001
        text = ''
    return (aria + ' ' + text).strip()


def hover_sweep(page, selectors, counts, errors, state_key):
    handles = page.query_selector_all(
        'button:visible, a:visible, [role="button"]:visible, summary:visible')
    for h in handles[:HOVER_CAP]:
        try:
            h.hover(timeout=1500)
        except Exception:  # noqa: BLE001
            continue
        eval_hits(page, selectors, counts, f'{state_key} hover', errors)


def focus_sweep(page, selectors, counts, errors, state_key):
    handles = page.query_selector_all(
        'input:visible, textarea:visible, select:visible, '
        '[contenteditable="true"]:visible, [tabindex]:visible')
    for h in handles[:FOCUS_CAP]:
        try:
            h.focus()
        except Exception:  # noqa: BLE001
            continue
        eval_hits(page, selectors, counts, f'{state_key} focus', errors)


def click_sweep(page, selectors, counts, errors, state_key, visit_url):
    handles = page.query_selector_all('button:visible')
    clicked = 0
    for h in handles:
        if clicked >= CLICK_CAP:
            break
        if DESTRUCTIVE.search(_label(h)):
            continue
        try:
            h.click(timeout=1500)
        except Exception:  # noqa: BLE001
            continue
        clicked += 1
        eval_hits(page, selectors, counts, f'{state_key} click', errors)
        if page.url != visit_url:
            try:
                page.goto(visit_url, wait_until='load', timeout=45000)
                page.wait_for_timeout(400)
            except Exception:  # noqa: BLE001
                return


def drag_sweep(page, selectors, counts, errors, state_key):
    obj = page.query_selector('.object[data-id]')
    if obj is None:
        return
    try:
        box = obj.bounding_box()
        if not box:
            return
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + 40, cy + 24, steps=6)
        eval_hits(page, selectors, counts, f'{state_key} drag', errors)
        page.mouse.up()
        eval_hits(page, selectors, counts, f'{state_key} drag-end', errors)
    except Exception:  # noqa: BLE001
        try:
            page.mouse.up()
        except Exception:  # noqa: BLE001
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8163')
    ap.add_argument('--candidates', required=True)
    ap.add_argument('--only-dead', help='rest-probe JSON; restrict to liveAny=false selectors')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    cand = json.loads(Path(args.candidates).read_text(encoding='utf-8'))
    selectors, seen = [], set()
    for e in cand.get('candidates', []):
        sel = str(e.get('selector', '')).strip()
        if not sel or sel.startswith('@') or sel in seen:
            continue
        if '{' in sel or '}' in sel or ';' in sel:
            continue
        seen.add(sel)
        selectors.append(sel)
    if args.only_dead and Path(args.only_dead).is_file():
        rest = json.loads(Path(args.only_dead).read_text(encoding='utf-8'))
        dead = {r['selector'].strip() for r in rest.get('selectors', []) if not r.get('liveAny')}
        selectors = [s for s in selectors if s in dead]
    print(f'probing {len(selectors)} selectors in interaction states', flush=True)

    out = {'candidates': args.candidates, 'onlyDead': args.only_dead,
           'combos': ['/'.join(c[:3]) for c in COMBOS],
           'selectors': [], 'errors': []}
    counts: dict[str, dict[str, int]] = {}

    with sync_playwright() as pw:
        browser = launch_chromium(pw)
        try:
            for combo in COMBOS:
                state, theme, lang, viewports = combo
                kw = {'color_scheme': theme, 'reduced_motion': 'reduce',
                      'locale': 'km-KH' if lang == 'km' else 'en-US'}
                ctx = browser.new_context(**kw)
                ctx.add_init_script(mark_editor_onboarding_seen())
                page = ctx.new_page()
                scope = f'{state}/{theme}/{lang}'
                page.on('pageerror', lambda e, _s=scope: out['errors'].append(f'{_s}: {str(e)[:120]}'))
                seed = capture.seed_account(page, args.base)
                data = {'invite_id': seed['invite_id'], 'slug': seed['slug']}
                out.setdefault('seeds', []).append(seed)
                print(f"seed[{state}/{theme}/{lang}] slug={seed['slug']} publish={seed['publish_ok']}", flush=True)

                for page_name in PAGES + ['editor.html']:
                    use_viewports = viewports if page_name == 'editor.html' else viewports[:1]
                    for (w, h) in use_viewports:
                        page.set_viewport_size({'width': w, 'height': h})
                        state_key = f'{scope} {page_name}@{w}x{h}'
                        url, err = visit(page, args.base, state, page_name, data['invite_id'], data['slug'])
                        if err:
                            out['errors'].append(f'{state_key}: {err}')
                            continue
                        hover_sweep(page, selectors, counts, out['errors'], state_key)
                        focus_sweep(page, selectors, counts, out['errors'], state_key)
                        click_sweep(page, selectors, counts, out['errors'], state_key, url)
                        drag_sweep(page, selectors, counts, out['errors'], state_key)
                ctx.close()
        finally:
            browser.close()

    for sel in selectors:
        hits = counts.get(sel, {})
        out['selectors'].append({'selector': sel, 'liveAny': bool(hits), 'hits': hits})
    out['summary'] = {'selectors': len(selectors),
                      'live': sum(1 for s in out['selectors'] if s['liveAny']),
                      'dead': sum(1 for s in out['selectors'] if not s['liveAny'])}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(out['summary']), flush=True)


if __name__ == '__main__':
    main()
