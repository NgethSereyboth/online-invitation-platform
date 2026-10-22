#!/usr/bin/env python3
"""fb19-pixel-diff.py — FB-19 OD-1 pixel-diff gate between two capture runs.

Compares every PNG in run A with the same relative path in run B (the FB-19
matrix r1 = pre-removal baseline, r2 = post-removal re-capture, both produced
by ``tools/ui-audit-capture.py`` with identical PROFILES).

Rule (OD-1): an unexplained visual diff means STOP. The dead-rule removals are
proven DOM-unmatched, so any render change is a bug. Chromium screenshots are
deterministic for the same build/data (capture determinism hardening), hence
the default tolerance is **zero** bytes — any mismatch enough to fail the gate
requires explicit -r explanation human review.

Report-only artifacts go to artifacts/next-work/fb-19/, never to /tmp.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from PIL import Image, ImageChops

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True, help='run A shots dir (baseline r1)')
    ap.add_argument('--b', required=True, help='run B shots dir (r2)')
    ap.add_argument('--out', default='artifacts/next-work/fb-19/pixel-diff.json')
    ap.add_argument('--tol', type=int, default=0,
                    help='max per-channel delta at any pixel to count as equal (0 = byte-equal)')
    args = ap.parse_args()

    shots = sorted(x for x in Path(args.b).rglob('*.png'))
    a_dir = Path(args.a); b_dir = Path(args.b)
    rows, failed = [], 0
    for bp in shots:
        rel = bp.relative_to(b_dir)
        ap_path = a_dir / rel
        if not ap_path.exists():
            rows.append({'shot': str(rel), 'status': 'missing-in-A'}); failed += 1; continue
        img_b = Image.open(bp).convert('RGB'); img_a = Image.open(ap_path).convert('RGB')
        if img_a.size != img_b.size:
            rows.append({'shot': str(rel), 'status': 'size-diff',
                         'a': list(img_a.size), 'b': list(img_b.size)}); failed += 1; continue
        bbox = ImageChops.difference(img_a, img_b).getbbox()
        if bbox is None:
            rows.append({'shot': str(rel), 'status': 'equal'}); continue
        if args.tol:
            from PIL import ImageChops as C
            ext = C.difference(img_a, img_b).getextrema()  # per-channel extrema
            worst = max(e[1] for e in ext)
            if worst <= args.tol:
                rows.append({'shot': str(rel), 'status': 'equal-within-tol', 'maxDelta': worst}); continue
            rows.append({'shot': str(rel), 'status': 'diff', 'maxDelta': worst, 'bbox': list(bbox)})
        else:
            rows.append({'shot': str(rel), 'status': 'diff', 'bbox': list(bbox)})
        failed += 1

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    data = {'a': args.a, 'b': args.b, 'tol': args.tol, 'compared': len(rows),
            'failed': failed, 'rows': rows, 'verdict': 'PASS' if failed == 0 else 'STOP'}
    out.write_text(json.dumps(data, indent=1), encoding='utf-8')
    diffs = [r for r in rows if r['status'] not in ('equal', 'equal-within-tol')]
    if not diffs:
        print(f"PIXEL_DIFF_GATE {len(rows)}/{len(rows)} shots byte-equal or within tol; verdict=PASS out={out}")
        return 0
    print(f"PIXEL_DIFF_GATE diffs={len(diffs)}/{len(rows)}; verdict=STOP out={out}")
    for r in diffs[:12]:
        print('  ', r)
    return 1

if __name__ == '__main__':
    sys.exit(main())
