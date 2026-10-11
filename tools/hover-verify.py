#!/usr/bin/env python3
"""hover-verify.py — force every :hover state on every page and report what changed.

Two instruments, one entry point:

  hover-audit.mjs        forces :hover on each rule's trigger via CDP
                         CSS.forcePseudoState and diffs the computed style of
                         the trigger and its subjects. Answers "does this hover
                         rule do anything visible on this page".
  important-lift-test    demotes one `!important` declaration at a time in the
                         CSSOM, re-forces hover, and compares the entire
                         computed style. Answers "is this priority load-bearing".

Usage
-----
    python3 tools/hover-verify.py --all                 # all 16 pages, hover audit
    python3 tools/hover-verify.py --all --lift          # + leave-one-out !important
    python3 tools/hover-verify.py index.html            # one page
    python3 tools/hover-verify.py --all --summary-only  # one line per page

Per-page JSON lands in <artifacts>/hover-<page>.json and, with --lift,
<artifacts>/lift-<page>.json, so a later pass can diff the raw per-element rows
rather than re-running the browser.

Exit status is 0 whenever the harness ran to completion: this measures hover
state, it does not assert a target. Failures to launch a browser or reach the
server exit 2.

Requires: node, the repo's node_modules (npm install), a running server
(`make serve-gzip`).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parent
ARTIFACTS = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))

# Kept in sync with tools/lighthouserc.js and tools/lib/repo.mjs.
PAGES = [
    "index.html", "dashboard.html", "public.html", "admin.html", "account.html",
    "billing.html", "verify.html", "reset.html", "privacy.html", "guests.html",
    "responses.html", "analytics.html", "materials.html", "checkin.html",
    "templates.html", "designer.html",
]


def check_server(base_url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/index.html", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def run_node(script: str, url: str, out_name: str, cap: int, env: dict) -> dict | None:
    out_path = ARTIFACTS / out_name
    proc = subprocess.run(
        ["node", str(TOOLS / script), url, f"--cap={cap}", f"--out={out_name}"],
        cwd=str(REPO_ROOT), env=env, text=True, capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        return None
    if not out_path.is_file():
        return None
    try:
        return json.loads(out_path.read_text())["summary"]
    except (json.JSONDecodeError, KeyError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hover-verify.py",
        description="Force :hover states on every page and report the computed-style deltas.",
    )
    parser.add_argument("pages", nargs="*", help="page names/routes (default: index.html)")
    parser.add_argument("--all", action="store_true", help="run every shipped page")
    parser.add_argument("--lift", action="store_true", help="also run the leave-one-out !important test")
    parser.add_argument("--cap", type=int, default=10, help="max elements per trigger selector (default 10)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8124")
    parser.add_argument("--summary-only", action="store_true", help="one line per page")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not check_server(args.base_url):
        sys.stderr.write(
            f"hover-verify.py: nothing answering on {args.base_url}\n"
            "  start the server first:  python3 tools/serve-gzip.py &\n"
        )
        return 2

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "BASE_URL": args.base_url, "ARTIFACTS_DIR": str(ARTIFACTS)}

    pages = PAGES if args.all else (args.pages or ["index.html"])
    rows = []
    for page in pages:
        slug = page.rsplit("/", 1)[-1].replace(".html", "")
        url = f"{args.base_url}/{slug}.html"
        hover = run_node("hover-audit.mjs", url, f"hover-{slug}.json", args.cap, env)
        if hover is None:
            print(f"{slug:<12} HARNESS FAILED")
            continue
        row = {
            "page": slug,
            "hoverSelectors": hover["hoverSelectorsInCssom"],
            "triggers": hover["distinctTriggerSelectors"],
            "triggersMatchingNothing": hover["triggersMatchingNothing"],
            "elementsTested": hover["elementsTested"],
            "visibleChange": hover["elementsWithVisibleChange"],
            "noVisibleChange": hover["elementsWithNoVisibleChange"],
        }
        if not args.summary_only:
            print(
                f"{slug:<12} hoverSelectors={row['hoverSelectors']:<5} triggers={row['triggers']:<5} "
                f"noMatch={row['triggersMatchingNothing']:<4} tested={row['elementsTested']:<5} "
                f"change={row['visibleChange']:<5} noChange={row['noVisibleChange']}"
            )
        if args.lift:
            lift = run_node("important-lift-test.mjs", url, f"lift-{slug}.json", args.cap, env)
            if lift:
                row.update({
                    "liftCandidateRules": lift["candidateRules"],
                    "liftCandidateDeclarations": lift["candidateDeclarations"],
                    "liftRedundant": lift["declarationsRedundantHere"],
                    "liftLoadBearing": lift["declarationsLoadBearingHere"],
                })
                if not args.summary_only:
                    print(
                        f"{'':<12} lift: rules={row['liftCandidateRules']} decls={row['liftCandidateDeclarations']} "
                        f"redundant={row['liftRedundant']} loadBearing={row['liftLoadBearing']}"
                    )
        rows.append(row)

    if args.summary_only:
        for r in rows:
            extra = f" lift={r.get('liftRedundant','-')}/{r.get('liftLoadBearing','-')}" if args.lift else ""
            print(f"{r['page']:<12} tested={r['elementsTested']:<5} change={r['visibleChange']:<5} noChange={r['noVisibleChange']}{extra}")

    totals = {
        "pages": len(rows),
        "hoverSelectors": sum(r["hoverSelectors"] for r in rows),
        "elementsTested": sum(r["elementsTested"] for r in rows),
        "visibleChange": sum(r["visibleChange"] for r in rows),
        "noVisibleChange": sum(r["noVisibleChange"] for r in rows),
    }
    print(f"HOVER_VERIFY_TOTAL {json.dumps(totals)}")
    (ARTIFACTS / "hover-verify-summary.json").write_text(json.dumps({"pages": rows, "totals": totals}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
