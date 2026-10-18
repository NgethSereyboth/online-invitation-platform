"""ui-audit-summary.py — compact cross-page summaries of a ui-audit-capture run.

Companion to tools/ui-audit-digest.py: instead of dumping every finding, this
aggregates heuristics.jsonl into short, deduplicated tables that are safe to
read in a terminal (overflow surfaces, contrast pairs, occlusion pairs,
tiny-text clusters, console/http errors, horizontal-scroll rows).

Usage:
    python3 tools/ui-audit-summary.py --section overflow
    python3 tools/ui-audit-summary.py --section contrast
    python3 tools/ui-audit-summary.py --section occlusion [--page index.html]
    python3 tools/ui-audit-summary.py --section tiny
    python3 tools/ui-audit-summary.py --section errors
    python3 tools/ui-audit-summary.py --section all
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def short_sel(el: str) -> str:
    """Keep only the tail of a descendant selector (most specific 3 parts)."""
    if not el:
        return '?'
    parts = el.split('>')
    return '>'.join(parts[-3:])


def load_rows(cap_dir: Path):
    rows = []
    for line in (cap_dir / 'heuristics.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sec_overflow(rows):
    print('== overflow offenders (elements past the right edge) ==')
    seen = {}
    for r in rows:
        for it in (r.get('h') or {}).get('overflowOffenders') or []:
            key = (r['page'], short_sel(it.get('el', '')))
            d = seen.setdefault(key, {'right': 0, 'docClipped': False, 'vw': set(), 'scrollable': set(), 'text': ''})
            d['right'] = max(d['right'], it.get('right') or 0)
            d['docClipped'] = d['docClipped'] or bool(it.get('docClipped'))
            d['vw'].add(r['vw'])
            d['scrollable'].add(bool(it.get('inScrollable')))
            d['text'] = d['text'] or (it.get('text') or '')[:30]
    for (page, sel), d in sorted(seen.items(), key=lambda kv: -kv[1]['right']):
        print(f"{page:14s} right={d['right']:<5} docClipped={str(d['docClipped']):5s} "
              f"scrollable={sorted(d['scrollable'])} vws={sorted(d['vw'])} {sel} :: {d['text']}")


def sec_hscroll(rows):
    print('== horizontal document scroll ==')
    for r in rows:
        if (r.get('h') or {}).get('horizOverflow'):
            print(f"{r['page']:14s} {r['state']}/{r['theme']}/{r['lang']} {r['vw']}x{r['vh']} "
                  f"scrollW={(r.get('h') or {}).get('docScrollW')}")


def sec_contrast(rows):
    print('== contrast pairs (deduped, worst count first) ==')
    seen = {}
    for r in rows:
        for it in (r.get('h') or {}).get('contrastIssues') or []:
            # Screen-reader-only text is clipped to 1x1 and never painted; skip it.
            if 'sr-only' in (it.get('el') or ''):
                continue
            key = (r['page'], str(it.get('fg')), str(it.get('bg')), str(it.get('need')))
            d = seen.setdefault(key, {'n': 0, 'ratio': 99.0, 'size': it.get('size'), 'el': '', 'text': '', 'caps': Counter()})
            d['n'] += 1
            d['ratio'] = min(d['ratio'], it.get('ratio') or 99.0)
            d['el'] = d['el'] or short_sel(it.get('el', ''))
            d['text'] = d['text'] or (it.get('text') or '')[:32]
            d['caps'][f"{r['state']}/{r['theme']}/{r['lang']}@{r['vw']}"] += 1
    for (page, fg, bg, need), d in sorted(seen.items(), key=lambda kv: -kv[1]['n']):
        caps = ', '.join(c for c, _ in d['caps'].most_common(3))
        print(f"{page:14s} n={d['n']:<3} ratio={d['ratio']:<5} need={need:<4} size={d['size']} "
              f"fg={fg} bg={bg} :: {d['text']} | {d['el']} | {caps}")


def sec_occlusion(rows, page_filter=''):
    print('== occlusion pairs (covered element <- covering element) ==')
    seen = {}
    for r in rows:
        if page_filter and r['page'] != page_filter:
            continue
        for it in (r.get('h') or {}).get('occlusion') or []:
            # .sr-only text is clipped by its 1x1 parent, so "covered by the input"
            # rows for screen-reader labels are not visual defects.
            if 'sr-only' in (it.get('el') or '') or 'sr-only' in (it.get('coveredBy') or ''):
                continue
            key = (r['page'], short_sel(it.get('coveredBy', '')), short_sel(it.get('el', '')))
            d = seen.setdefault(key, {'n': 0, 'text': '', 'caps': Counter()})
            d['n'] += 1
            d['text'] = d['text'] or (it.get('text') or '')[:36]
            d['caps'][f"{r['state']}/{r['theme']}/{r['lang']}@{r['vw']}"] += 1
    for (page, cov, el), d in sorted(seen.items(), key=lambda kv: -kv[1]['n']):
        caps = ', '.join(c for c, _ in d['caps'].most_common(2))
        print(f"{page:14s} n={d['n']:<3} covered='{d['text']}' el={el}")
        print(f"{'':14s}     by {cov} | {caps}")


def sec_tiny(rows):
    print('== tiny text clusters (size < 12px) ==')
    seen = {}
    for r in rows:
        for it in (r.get('h') or {}).get('tinyText') or []:
            m = re.search(r'([a-zA-Z0-9_-]+)$', (it.get('el') or '').split('>')[-1].strip())
            tail = (it.get('el') or '').split('>')[-1].strip()
            key = (r['page'], it.get('size'), tail[:40])
            d = seen.setdefault(key, {'n': 0, 'text': ''})
            d['n'] += 1
            d['text'] = d['text'] or (it.get('text') or '')[:24]
    for (page, size, tail), d in sorted(seen.items(), key=lambda kv: (kv[0][0], -(kv[1]['n']))):
        print(f"{page:14s} {size:<6} n={d['n']:<3} '{d['text']}' <{tail}>")


def sec_errors(rows):
    print('== console / http errors (deduped) ==')
    seen = set()
    for r in rows:
        key = (r['page'], tuple(r.get('consoleErrors') or []), tuple(r.get('httpErrors') or []))
        if key in seen or (not key[1] and not key[2]):
            continue
        seen.add(key)
        print(f"[{r['state']} {r['lang']}/{r['theme']} {r['vw']}] {r['page']}")
        for c in (r.get('consoleErrors') or [])[:4]:
            print(f"    C: {c[:150]}")
        for h in (r.get('httpErrors') or [])[:6]:
            print(f"    H: {h[:150]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(ROOT / 'artifacts' / 'ui-audit' / 'capture'))
    ap.add_argument('--section', default='all',
                    choices=['all', 'overflow', 'hscroll', 'contrast', 'occlusion', 'tiny', 'errors'])
    ap.add_argument('--page', default='')
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:  # noqa: BLE001
        pass
    cap_dir = Path(args.dir)
    if not cap_dir.is_absolute():
        cap_dir = ROOT / cap_dir
    rows = load_rows(cap_dir)
    if args.section in ('all', 'hscroll'):
        sec_hscroll(rows)
    if args.section in ('all', 'overflow'):
        sec_overflow(rows)
    if args.section in ('all', 'contrast'):
        sec_contrast(rows)
    if args.section in ('all', 'occlusion'):
        sec_occlusion(rows, args.page)
    if args.section in ('all', 'tiny'):
        sec_tiny(rows)
    if args.section in ('all', 'errors'):
        sec_errors(rows)


if __name__ == '__main__':
    main()
