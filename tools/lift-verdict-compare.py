#!/usr/bin/env python3
"""lift-verdict-compare.py — compare per-declaration lift verdicts across N runs.

Why this exists
---------------
`tools/hover-verify.py --cross-page` aggregates `lift-<page>.json` files by PAGE
name and answers "is this declaration demotable across the sweep". That is the
right question for the sweep and the wrong one for this pass's first goal, which
was narrower and had to be answered before anything else could be believed:

    does the SAME page, unchanged, give the same verdict twice?

Five runs of the defective probe over one page and one tree disagreed — three
declarations came back `redundant` in one run and `load-bearing` in the next — but
those five artifacts lived in three different directories and were named
`lift-index.json`, `lift-index.run2.json`, ... , so nothing in the harness put them
side by side. `--cross-page` cannot either: it would read `lift-index.json` and
`lift-index.run2.json` as two different pages and report the disagreement as a
cross-page difference rather than as instability of one page.

So this tool takes an explicit list of artifact files and one page's worth of runs,
and prints the verdict of every declaration in each file with a FLIP marker where
they disagree. It is the instrument the three-run stability proof in
`docs/reviews/instrument-repair-report.md` §1 is made of.

Keying: a declaration is keyed by `declaration | selector`, because one rule can
carry two `!important` declarations with different verdicts (that is the whole
reason the probe enumerates at declaration level — see tools/lib/css-decl.js).

Usage
    python3 tools/lift-verdict-compare.py artifacts/lift-index.json artifacts/lift-index.run2.json
    python3 tools/lift-verdict-compare.py --json a.json b.json c.json

Exit status: 0 when every file parsed, 1 when at least one declaration disagreed
across the files (a FLIP), 2 on bad input. An exit of 1 is a finding, not an error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BUCKETS = (("redundant", "R"), ("needed", "L"), ("unmeasured", "U"))


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{path}: {exc}")


def verdicts(payload: dict) -> "dict[tuple[str, str], tuple[str, int]]":
    out: dict[tuple[str, str], tuple[str, int]] = {}
    for bucket, tag in BUCKETS:
        for row in payload.get(bucket) or []:
            key = (row["declaration"], row["selector"])
            out[key] = (tag, int(row.get("diffs") or 0))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="lift-*.json artifacts (one page, N runs, in order)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--max-selector", type=int, default=90, help="truncate the selector column (default 90)")
    args = ap.parse_args()

    if len(args.files) < 2:
        raise SystemExit("lift-verdict-compare.py: give at least two artifact files")

    sets = []
    for spec in args.files:
        path = Path(spec)
        if not path.is_file():
            raise SystemExit(f"{path}: no such artifact")
        payload = load(path)
        sets.append({
            "file": str(path),
            "summary": payload.get("summary") or {},
            "verdicts": verdicts(payload),
        })

    everything = sorted({key for s in sets for key in s["verdicts"]})
    rows = []
    flips = 0
    for key in everything:
        cells = [s["verdicts"].get(key) for s in sets]
        tags = {c[0] for c in cells if c}
        flipped = len(tags) > 1
        if flipped:
            flips += 1
        rows.append({
            "declaration": key[0],
            "selector": key[1],
            "cells": ["?" if c is None else f"{c[0]}{c[1]}" for c in cells],
            "flip": flipped,
        })

    if args.json:
        print(json.dumps({"files": [s["file"] for s in sets], "flips": flips, "rows": rows}, indent=1))
    else:
        print(f"LIFT_VERDICT_COMPARE files={len(sets)} declarations={len(rows)} flips={flips}")
        for s in sets:
            summary = s["summary"]
            print(
                f"  {s['file']:<52} redundant={summary.get('declarationsRedundantHere')}"
                f" loadBearing={summary.get('declarationsLoadBearingHere')}"
                f" unmeasured={summary.get('declarationsUnmeasuredHere')}"
                + (f" settle={json.dumps(summary['settleStats'])}" if summary.get("settleStats") else "")
            )
        print()
        print("R = redundant here (removal changed nothing)   L = load-bearing (removal changed a value)")
        print("U = unmeasured here (no element on the page reaches the rule)   ? = absent from that file")
        print()
        width = max((len(r["declaration"]) for r in rows), default=11)
        for r in rows:
            print(
                f"  {'FLIP' if r['flip'] else '    '}  "
                + "  ".join(f"{c:>4}" for c in r["cells"])
                + "   " + r["declaration"].ljust(width)
                + "  " + r["selector"][: args.max_selector]
            )
    return 1 if flips else 0


if __name__ == "__main__":
    sys.exit(main())
