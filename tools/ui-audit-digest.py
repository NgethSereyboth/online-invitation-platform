"""ui-audit-digest.py — compact per-page digest of a ui-audit-capture run.

Reads <capture-dir>/heuristics.jsonl (+ console.jsonl) and prints the concrete
offenders per page and capture: selectors, sample text, sizes, colors. Use it
to turn the raw capture into evidence you can cite in an issue list.

Usage:
    python3 tools/ui-audit-digest.py --dir artifacts/ui-audit/capture > digest.txt
    python3 tools/ui-audit-digest.py --dir artifacts/ui-audit/capture --pages index.html,public.html
    python3 tools/ui-audit-digest.py --dir artifacts/ui-audit/capture --states user --themes light --langs en

Options:
    --dir DIR      capture directory (default artifacts/ui-audit/capture)
    --pages LIST   comma page filter
    --states LIST  state filter (default: all)
    --themes LIST  theme filter (default: all)
    --langs LIST   language filter (default: all)
    --max N        max samples per category per capture (default 4)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CATS = [
    ('overflowOffenders', 'overflow'),
    ('clippedText', 'clipped'),
    ('occlusion', 'occlusion'),
    ('tinyText', 'tiny'),
    ('smallTargets', 'smalltarget'),
    ('contrastIssues', 'contrast'),
    ('namelessInteractive', 'nameless'),
    ('defaultStyledControls', 'defaultstyled'),
    ('offCenter', 'offcenter'),
    ('brokenImages', 'brokenimg'),
]


def fmt_cat(name, items, maxn):
    out = []
    for it in items[:maxn]:
        if name == 'overflowOffenders':
            out.append(f"    right={it.get('right')} w={it.get('w')} scrollable={it.get('inScrollable')} docClipped={it.get('docClipped')} {it.get('el')} :: {it.get('text','')[:40]}")
        elif name == 'clippedText':
            out.append(f"    {it.get('axis')} over={it.get('over')} {it.get('el')} :: {it.get('text','')[:40]}")
        elif name == 'occlusion':
            out.append(f"    {it.get('el')} :: {it.get('text','')[:40]} <- covered by {it.get('coveredBy')}")
        elif name == 'tinyText':
            out.append(f"    {it.get('size')} {it.get('el')} :: {it.get('text','')[:40]}")
        elif name == 'smallTargets':
            out.append(f"    {it.get('w')}x{it.get('h')} {it.get('el')} :: {it.get('text','')[:30]}")
        elif name == 'contrastIssues':
            out.append(f"    {it.get('ratio')}:1 (need {it.get('need')}) fg={it.get('fg')} bg={it.get('bg')} size={it.get('size')} {it.get('el')} :: {it.get('text','')[:40]}")
        elif name == 'namelessInteractive':
            out.append(f"    {it.get('w')}x{it.get('h')} {it.get('el')}")
        elif name == 'defaultStyledControls':
            out.append(f"    ff={it.get('ff')} {it.get('el')}")
        elif name == 'offCenter':
            out.append(f"    left={it.get('left')} right={it.get('right')} gap={it.get('gap')} {it.get('el')}")
        elif name == 'brokenImages':
            out.append(f"    {it.get('el')} src=...{it.get('src','')[-80:]}")
    return out


def main():
    try:
        import sys
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:  # noqa: BLE001 — best effort; older runtimes may not support it
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(ROOT / 'artifacts' / 'ui-audit' / 'capture'))
    ap.add_argument('--pages', default='')
    ap.add_argument('--states', default='')
    ap.add_argument('--themes', default='')
    ap.add_argument('--langs', default='')
    ap.add_argument('--max', type=int, default=4)
    ap.add_argument('--out', default='', help='write digest to this file (UTF-8) instead of stdout')
    args = ap.parse_args()

    cap_dir = Path(args.dir)
    if not cap_dir.is_absolute():
        cap_dir = ROOT / cap_dir
    pages_f = {p.strip() for p in args.pages.split(',') if p.strip()}
    states_f = {s.strip() for s in args.states.split(',') if s.strip()}
    themes_f = {t.strip() for t in args.themes.split(',') if t.strip()}
    langs_f = {l.strip() for l in args.langs.split(',') if l.strip()}

    rows = []
    for line in (cap_dir / 'heuristics.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))

    emit_lines = []
    def emit(text=''):
        emit_lines.append(text)

    by_page = {}
    for r in rows:
        if pages_f and r['page'] not in pages_f:
            continue
        if states_f and r['state'] not in states_f:
            continue
        if themes_f and r['theme'] not in themes_f:
            continue
        if langs_f and r['lang'] not in langs_f:
            continue
        by_page.setdefault(r['page'], []).append(r)

    for page_name in sorted(by_page):
        page_rows = by_page[page_name]
        emit(f"\n{'='*100}\nPAGE {page_name}  ({len(page_rows)} captures)\n{'='*100}")
        for r in page_rows:
            h = r.get('h') or {}
            head = (f"[{r['state']} {r['lang']}/{r['theme']} {r['vw']}x{r['vh']}] "
                    f"final={r.get('finalUrl','?')} bodyTextLen={h.get('bodyTextLen')} "
                    f"theme={h.get('theme')} lang={h.get('lang')} docScrollW={h.get('docScrollW')} "
                    f"h1={h.get('h1Count')} hCounts={h.get('hCounts')}")
            findings = [head]
            if r.get('navError'):
                findings.append(f"  NAVERROR: {r['navError']}")
            if h.get('horizOverflow'):
                findings.append("  HORIZ_SCROLL: document scrolls horizontally")
            for key, label in CATS:
                items = h.get(key) or []
                if items:
                    findings.append(f"  {label}({len(items)}):")
                    findings.extend(fmt_cat(key, items, args.max))
            for key, label in (('inputsWithoutLabel', 'inputsWithoutLabel'), ('imagesMissingAlt', 'img-no-alt'), ('imagesMissingDims', 'img-no-dims')):
                v = h.get(key) or 0
                if v:
                    findings.append(f"  {label}: {v}")
            if h.get('viewportMeta') is not None:
                pass
            fs = h.get('fontSizes') or {}
            if fs:
                findings.append('  fontSizes: ' + ', '.join(f'{k}:{v}' for k, v in list(fs.items())[:10]))
            ce = r.get('consoleErrors') or []
            he = r.get('httpErrors') or []
            if ce:
                findings.append('  console: ' + ' | '.join(x[:120] for x in ce[:5]))
            if he:
                findings.append('  http: ' + ' | '.join(x[:120] for x in he[:5]))
            if len(findings) > 1:
                emit('\n'.join(findings))
    emit('\nDIGEST_DONE')
    text = '\n'.join(emit_lines) + '\n'
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.write_text(text, encoding='utf-8')
        print(f'digest written: {out_path} ({len(emit_lines)} lines)')
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
