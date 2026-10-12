#!/usr/bin/env python3
"""lhci-bucket.py — print the main-thread buckets from a Lighthouse CI run.

Why this exists
---------------
Goal 3 of the previous pass was "reduce Style & Layout on index.html", and the
number that decides it — `styleLayout` inside Lighthouse's
`mainthread-work-breakdown` audit — was read by hand out of the LHR JSON each time.
A number that is extracted by hand is not re-runnable, so it cannot be quoted by a
self-verifying report and cannot be compared across sessions with confidence.

This tool reads the newest (or a named) `.lighthouseci/lhr-*.json` and prints the
same figures the reports quote: the headline metrics, every main-thread bucket with
its share, and the bucket total. It never runs Lighthouse — that is
`npx lhci collect --config=tools/lhci-single.js`, which needs the gzip server — so
the extraction can be re-run at any time against an existing run.

Usage
-----
    python3 tools/lhci-bucket.py                       # newest LHR
    python3 tools/lhci-bucket.py .lighthouseci/lhr-*.json
    python3 tools/lhci-bucket.py --url index.html      # newest LHR for that URL
    python3 tools/lhci-bucket.py --json

Exit status is 3 when no matching LHR exists (nothing to report) and 0 otherwise;
it reports, it does not assert a budget.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LHCI_DIR = Path(os.environ.get("LHCI_DIR", REPO_ROOT / ".lighthouseci"))

# Buckets Lighthouse reports, in the order its own table uses.
BUCKETS = [
    "scriptEvaluation", "scriptParseCompile", "styleLayout", "parseHTML",
    "garbageCollection", "other", "paintCompositeRender",
]
LABELS = {
    "scriptEvaluation": "Script Evaluation", "scriptParseCompile": "Script Parsing & Compilation",
    "styleLayout": "Style & Layout", "parseHTML": "Parse HTML & CSS",
    "garbageCollection": "Garbage Collection", "other": "Other",
    "paintCompositeRender": "Rendering",
}
METRICS = [
    ("first-contentful-paint", "FCP"), ("largest-contentful-paint", "LCP"),
    ("total-blocking-time", "TBT"), ("speed-index", "Speed Index"),
]


def newest_lhr(pattern: str | None, url_filter: str | None) -> Path | None:
    paths = sorted(glob.glob(pattern)) if pattern else sorted(glob.glob(str(LHCI_DIR / "lhr-*.json")))
    if not paths:
        return None
    if url_filter:
        wanted = url_filter.lstrip("/")
        matches = []
        for p in paths:
            try:
                lhr = json.loads(Path(p).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if wanted in str(lhr.get("finalUrl") or lhr.get("finalDisplayedUrl") or ""):
                matches.append(p)
        paths = matches or paths
    return max(paths, key=lambda p: Path(p).stat().st_mtime)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="lhci-bucket.py",
        description="Print the mainthread-work-breakdown buckets from a Lighthouse CI run.",
    )
    ap.add_argument("lhr", nargs="?", default=None, help="an lhr-*.json path (default: newest)")
    ap.add_argument("--url", default=None, help="pick the newest LHR whose finalUrl contains this")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    path = newest_lhr(args.lhr, args.url)
    if path is None:
        sys.stderr.write(
            f"lhci-bucket.py: no Lighthouse report found ({LHCI_DIR}/lhr-*.json).\n"
            "  run one first:  PAGE=index.html npx lhci collect --config=tools/lhci-single.js\n"
        )
        return 3
    lhr = json.loads(Path(path).read_text(encoding="utf-8"))

    breakdown = (lhr.get("audits", {}).get("mainthread-work-breakdown", {}).get("details", {}) or {})
    items = {i.get("group"): i.get("duration", 0) for i in breakdown.get("items", [])}
    total = sum(items.values())

    metrics = {}
    for audit_id, label in METRICS:
        audit = lhr.get("audits", {}).get(audit_id, {})
        metrics[label] = {"display": audit.get("displayValue"), "numeric": audit.get("numericValue")}

    report = {
        "lhr": str(path),
        "url": lhr.get("finalUrl") or lhr.get("finalDisplayedUrl"),
        "fetchTime": lhr.get("fetchTime"),
        "performance": (lhr.get("categories", {}).get("performance", {}) or {}).get("score"),
        "mainThreadMs": total,
        "buckets": {LABELS.get(k, k): round(v, 1) for k, v in sorted(items.items(), key=lambda kv: -kv[1])},
        "metrics": metrics,
    }

    if args.json:
        print(json.dumps(report, indent=1))
        return 0

    print(f"report   : {path}")
    print(f"url      : {report['url']}   fetched {report['fetchTime']}")
    score = report["performance"]
    print(f"performance: {round(score * 100) if isinstance(score, (int, float)) else score}")
    for label, m in metrics.items():
        print(f"  {label:<12} {m['display']}")
    print(f"\nmainthread-work-breakdown  total {total:,.0f} ms")
    for name in BUCKETS:
        if name not in items:
            continue
        share = items[name] / total * 100 if total else 0
        print(f"  {LABELS[name]:<26} {items[name]:>9,.1f} ms   {share:5.1f}%")
    for name, value in sorted(items.items(), key=lambda kv: -kv[1]):
        if name not in BUCKETS:
            print(f"  {LABELS.get(name, name):<26} {value:>9,.1f} ms   {value / total * 100 if total else 0:5.1f}%  (unclassified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
