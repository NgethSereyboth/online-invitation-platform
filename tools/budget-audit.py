#!/usr/bin/env python3
"""budget-audit.py — list the Lighthouse budgets a page actually carries.

Why this exists
---------------
The report this tool was written for claims that `tools/lighthouserc.js`'s
docstring described removing request-count assertions that the budgets file still
contained. Verifying that claim means reading `docs/perf/lighthouse-budgets.json`
at the revision in question — and the file has since been fixed, so the *current*
file cannot support the *historical* claim. The report's own standard is that the
command printed next to a number can be re-run, so the block quotes this tool with
`--at <rev>` instead of an inline `python3 -c` one-liner that was never printed in
full.

The budgets file is a top-level JSON array of `{path, resourceSizes,
resourceCounts}`. `resourceCounts` are request-count ceilings
(`resourceType == "script"`, budget 3); `resourceSizes` are KiB byte budgets.

Usage
-----
    python3 tools/budget-audit.py                    # working tree
    python3 tools/budget-audit.py --at 7b5f912        # as committed at a revision
    python3 tools/budget-audit.py --file /path/to/budgets.json
    python3 tools/budget-audit.py --at 7b5f912 --json

Read-only: it reads a tracked blob or a file and prints. It never writes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parent  # same convention as the other tools/*.py

DEFAULT_BUDGETS = "docs/perf/lighthouse-budgets.json"


def load(rev: str | None, path: str):
    """Return the parsed budgets list, from a git revision or from disk."""
    if rev:
        blob = subprocess.run(
            ["git", "show", f"{rev}:{path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if blob.returncode != 0:
            sys.exit(f"budget-audit: git show {rev}:{path} failed: {blob.stderr.strip()}")
        return json.loads(blob.stdout)
    full = REPO_ROOT / path
    if not full.exists():
        sys.exit(f"budget-audit: not found: {full}")
    return json.loads(full.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="List Lighthouse request-count and byte budgets per page.")
    ap.add_argument("--at", metavar="REV", help="read the file as committed at this revision")
    ap.add_argument("--file", default=DEFAULT_BUDGETS, help=f"path within the repo (default: {DEFAULT_BUDGETS})")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of the table")
    args = ap.parse_args(argv)

    data = load(args.at, args.file)
    if not isinstance(data, list):
        sys.exit("budget-audit: expected a top-level JSON array of pages")

    rows = []
    for page in data:
        counts = page.get("resourceCounts") or []
        sizes = page.get("resourceSizes") or []
        rows.append(
            {
                "path": page.get("path"),
                "resourceCounts": [(c.get("resourceType"), c.get("budget")) for c in counts],
                "resourceSizes": [(c.get("resourceType"), c.get("budget")) for c in sizes],
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    where = f"{args.file} @ {args.at}" if args.at else args.file
    print(f"# {where}")
    print(f"{'page':22} {'count budgets':>13}  {'byte budgets':>12}   resourceCounts detail")
    for r in rows:
        detail = ", ".join(f"{t} budget {b}" for t, b in r["resourceCounts"]) or "-"
        print(f"{r['path']:22} {len(r['resourceCounts']):>13}  {len(r['resourceSizes']):>12}   {detail}")

    pages_with_counts = sum(1 for r in rows if r["resourceCounts"])
    print(
        f"\npages: {len(rows)}   pages still carrying resourceCounts: {pages_with_counts}   "
        f"total resourceCounts entries: {sum(len(r['resourceCounts']) for r in rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
