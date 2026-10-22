#!/usr/bin/env python3
"""FB-19 live-DOM probe — does any candidate ``!important`` selector ever match?

Companion to the static scan (``tools/fb19-dead-important.py``): a rule becomes
a candidate when its tokens appear nowhere in the shipped HTML/JS sources; this
probe then confirms against *rendered* pages that nothing matches.

Method (mirrors ``tools/ui-audit-capture.py`` so the probe sees the same page
state the NW-2.2 matrix baselines captured): the capture's own ``seed_account``
(one throwaway account + a published invitation + guests + RSVP) runs inside
each browser context so the session cookie is shared, the shipped 16 routes
plus the dynamic editor route are visited across the matrix's four fully-captured
combos (user/light/en at 1440/1024/768/375/320, user/dark/en, user/light/km,
guest/light/en), and per visit every candidate selector is evaluated with
``document.querySelectorAll`` (pseudo-element suffixes are retried on their
element part; ``-1`` means invalid and is reported, never claimed dead).

Output JSON: per selector ``liveAny`` (matched anywhere) + ``hits`` map. A
``liveAny=False`` selector is live-probe dead.

Usage::

    python3 tools/fb19-probe-dom.py --base http://127.0.0.1:8124 \
        --candidates artifacts/next-work/fb-19/dead-rules-static.json \
        --out artifacts/next-work/fb-19/probe/dom-presence.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))

from browser_runtime import dismiss_editor_onboarding, launch_chromium, mark_editor_onboarding_seen  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

# Reuse the capture tool's DOCUMENT + seed_account verbatim so the probe's page
# state matches the NW-2.2 matrix exactly (same invitation shape, same guests).
_capture_spec = importlib.util.spec_from_file_location(
    'ui_audit_capture', ROOT / 'tools' / 'ui-audit-capture.py')
capture = importlib.util.module_from_spec(_capture_spec)
sys.modules['ui_audit_capture'] = capture
_capture_spec.loader.exec_module(capture)

PAGES = list(capture.PAGES)
EDITOR_PAGES = {'index.html', 'designer.html'}
PUBLIC_PAGE = capture.PUBLIC_PAGE
EDITOR_ROUTE = '/invitations/{INV}/editor'

COMBOS = [
    ('user', 'light', 'en', [(1440, 900), (1024, 768), (768, 1024), (375, 667), (320, 568)]),
    ('user', 'dark', 'en', [(1440, 900), (375, 667)]),
    ('user', 'light', 'km', [(1440, 900)]),
    ('guest', 'light', 'en', [(1440, 900)]),
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


def visit(page, base, state, page_name, inv_id, slug):
    if page_name == 'editor.html':
        url = base + EDITOR_ROUTE.replace('{INV}', str(inv_id))
    elif page_name == PUBLIC_PAGE:
        url = f'{base}/i/'+slug
    else:
        url = f'{base}/{page_name}'
    try:
        page.goto(url, wait_until='load', timeout=45000)
    except Exception as exc:  # noqa: BLE001
        return f'goto: {str(exc)[:140]}'
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
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8124')
    ap.add_argument('--candidates', required=True)
    ap.add_argument('--out', default=str(ROOT / 'artifacts' / 'next-work' / 'fb-19' / 'probe' / 'dom-presence.json'))
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
    print(f'probing {len(selectors)} selectors', flush=True)

    out = {'candidates': args.candidates,
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
                page.on('pageerror', lambda e, _c=f'{state}/{theme}/{lang}':
                        out['errors'].append(f'{_c}: {str(e)[:120]}'))
                seed = capture.seed_account(page, args.base)
                data = {'invite_id': seed['invite_id'], 'slug': seed['slug']}
                out.setdefault('seeds', []).append(seed)
                print(f"seed[{state}/{theme}/{lang}] slug={seed['slug']} publish={seed['publish_ok']}", flush=True)

                for page_name in PAGES + ['editor.html']:
                    for (w, h) in viewports:
                        page.set_viewport_size({'width': w, 'height': h})
                        key = f'{page_name}@{w}x{h}'
                        err = visit(page, args.base, state, page_name, data['invite_id'], data['slug'])
                        if err:
                            out['errors'].append(f'{state}/{theme}/{lang} {key}: {err}')
                            continue
                        try:
                            res = page.evaluate(PROBE_JS, selectors)
                        except Exception as exc:  # noqa: BLE001
                            out['errors'].append(f'{state}/{theme}/{lang} {key}: evaluate {str(exc)[:140]}')
                            continue
                        for sel, n in res.items():
                            if n == -1:
                                out['errors'].append(f'{state}/{theme}/{lang} {key}: invalid selector {sel[:80]}')
                            elif n > 0:
                                counts.setdefault(sel, {}).setdefault(key, min(n, 9999))
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
