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
    python3 tools/hover-verify.py --all --lift --jobs 4 # four pages at once
    python3 tools/hover-verify.py --cross-page          # verdict from artifacts/lift-*.json

Per-page JSON lands in <artifacts>/hover-<page>.json and, with --lift,
<artifacts>/lift-<page>.json, so a later pass can diff the raw per-element rows
rather than re-running the browser.

`--cross-page` is the step that turns those per-page files into a decision. A
`:hover` `!important` declaration is reported `demotable` only when every page
that could measure it measured it inert; pages where no element reaches the rule
are reported as `unmeasured` and are evidence of nothing, so a declaration that is
inert on one page and unmeasured on fifteen is not demotable. The unit is the
DECLARATION, not the longhand: see tools/lib/css-decl.js.

Exit status is 0 whenever the harness ran to completion: this measures hover
state, it does not assert a target. Failures to launch a browser or reach the
server exit 2.

Requires: node, the repo's node_modules (npm install), a running server
(`make serve-gzip`).
"""
from __future__ import annotations

import argparse
import concurrent.futures
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


def cross_page(artifacts: Path, as_json: bool) -> int:
    """Turn the per-page lift files into a demotable / keep verdict, per declaration."""
    files = sorted(artifacts.glob("lift-*.json"))
    if not files:
        sys.stderr.write(f"hover-verify.py --cross-page: no lift-*.json under {artifacts}\n")
        return 2
    rows: dict[tuple[str, str], dict] = {}
    pages_seen = []
    for path in files:
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        page = path.stem[len("lift-"):]
        pages_seen.append(page)
        for bucket, verdict in (("needed", "loadBearing"), ("redundant", "redundant"), ("unmeasured", "unmeasured")):
            for row in payload.get(bucket, []):
                key = (row["selector"], row["declaration"])
                entry = rows.setdefault(key, {
                    "selector": row["selector"], "declaration": row["declaration"],
                    "longhands": row.get("longhands", 1),
                    "loadBearingOn": [], "redundantOn": [], "unmeasuredOn": [], "maxDiffs": 0,
                })
                entry[{"loadBearing": "loadBearingOn", "redundant": "redundantOn", "unmeasured": "unmeasuredOn"}[verdict]].append(page)
                entry["maxDiffs"] = max(entry["maxDiffs"], row.get("diffs", 0))
    for entry in rows.values():
        measured = entry["redundantOn"] + entry["loadBearingOn"]
        entry["measuredOnCount"] = len(measured)
        if entry["loadBearingOn"]:
            entry["verdict"] = "keep"
        elif measured:
            entry["verdict"] = "demotable"
        else:
            # Reachable on no page at all: no evidence either way. Never demotable.
            entry["verdict"] = "unmeasured"
    def bucket(name):
        return sorted((e for e in rows.values() if e["verdict"] == name),
                      key=lambda e: (e["selector"], e["declaration"]))
    demotable, keep, unmeasured = bucket("demotable"), bucket("keep"), bucket("unmeasured")
    summary = {
        "pages": len(pages_seen), "declarations": len(rows),
        "demotable": len(demotable), "keep": len(keep), "noEvidence": len(unmeasured),
    }
    if as_json:
        print(json.dumps({"summary": summary, "demotable": demotable, "keep": keep, "unmeasured": unmeasured}, indent=1))
    else:
        print(f"LIFT_CROSS_PAGE {json.dumps(summary)}")
        print(f"pages: {', '.join(pages_seen)}\n")
        print("--- DEMOTABLE (inert on every page that measured it) ---")
        for e in demotable:
            pages = "+".join(e["redundantOn"])
            un = f"  unmeasured on {len(e['unmeasuredOn'])}" if e["unmeasuredOn"] else ""
            print(f"  {e['declaration']:<22} longhands={e['longhands']:<2} inert on {pages}{un}")
            print(f"      {e['selector']}")
        print("\n--- KEEP (load-bearing on at least one page) ---")
        for e in keep:
            print(f"  {e['declaration']:<22} longhands={e['longhands']:<2} diffs={e['maxDiffs']:<4} on {','.join(e['loadBearingOn'])}")
            print(f"      {e['selector']}")
        print(f"\n--- NO EVIDENCE (reachable on no page: {len(unmeasured)}) ---")
        for e in unmeasured:
            print(f"  {e['declaration']:<22} longhands={e['longhands']:<2}  {e['selector']}")
    return 0


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
    parser.add_argument("--jobs", type=int, default=1, help="pages to run at once (default 1; each spins its own browser)")
    parser.add_argument("--cross-page", action="store_true",
                        help="do not run the browser: read artifacts/lift-*.json and print the demotable verdict")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.cross_page:
        return cross_page(ARTIFACTS, os.environ.get("LIFT_JSON") == "1")

    if not 1 <= args.jobs <= 8:
        sys.stderr.write("hover-verify.py: --jobs must be between 1 and 8\n")
        return 2

    if not check_server(args.base_url):
        sys.stderr.write(
            f"hover-verify.py: nothing answering on {args.base_url}\n"
            "  start the server first:  python3 tools/serve-gzip.py &\n"
        )
        return 2

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "BASE_URL": args.base_url, "ARTIFACTS_DIR": str(ARTIFACTS)}

    pages = PAGES if args.all else (args.pages or ["index.html"])

    def one_page(page: str) -> dict | None:
        slug = page.rsplit("/", 1)[-1].replace(".html", "")
        url = f"{args.base_url}/{slug}.html"
        hover = run_node("hover-audit.mjs", url, f"hover-{slug}.json", args.cap, env)
        if hover is None:
            return None
        row = {
            "page": slug,
            "hoverSelectors": hover["hoverSelectorsInCssom"],
            "triggers": hover["distinctTriggerSelectors"],
            "triggersMatchingNothing": hover["triggersMatchingNothing"],
            "elementsTested": hover["elementsTested"],
            "visibleChange": hover["elementsWithVisibleChange"],
            "noVisibleChange": hover["elementsWithNoVisibleChange"],
        }
        if args.lift:
            lift = run_node("important-lift-test.mjs", url, f"lift-{slug}.json", args.cap, env)
            if lift:
                row.update({
                    "liftCandidateRules": lift["candidateRules"],
                    "liftCandidateDeclarations": lift["candidateDeclarations"],
                    "liftCandidateLonghands": lift["candidateLonghands"],
                    "liftRedundant": lift["declarationsRedundantHere"],
                    "liftLoadBearing": lift["declarationsLoadBearingHere"],
                    "liftUnmeasured": lift["declarationsUnmeasuredHere"],
                    "liftGroupingMismatches": lift["groupingMismatches"],
                    "liftRestoreFailures": lift["restoreFailures"],
                })
        return row

    # Each page is a separate browser process writing its own artifact file, so
    # parallel pages cannot interfere. Results are printed in page order either way.
    if args.jobs > 1 and len(pages) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            produced = list(pool.map(one_page, pages))
    else:
        produced = [one_page(page) for page in pages]

    rows = []
    for page, row in zip(pages, produced):
        slug = page.rsplit("/", 1)[-1].replace(".html", "")
        if row is None:
            print(f"{slug:<12} HARNESS FAILED")
            continue
        if not args.summary_only:
            print(
                f"{slug:<12} hoverSelectors={row['hoverSelectors']:<5} triggers={row['triggers']:<5} "
                f"noMatch={row['triggersMatchingNothing']:<4} tested={row['elementsTested']:<5} "
                f"change={row['visibleChange']:<5} noChange={row['noVisibleChange']}"
            )
            if args.lift and "liftCandidateDeclarations" in row:
                print(
                    f"{'':<12} lift: rules={row['liftCandidateRules']} decls={row['liftCandidateDeclarations']} "
                    f"(longhands={row['liftCandidateLonghands']}) redundant={row['liftRedundant']} "
                    f"loadBearing={row['liftLoadBearing']} unmeasured={row['liftUnmeasured']}"
                )
        rows.append(row)

    if args.summary_only:
        for r in rows:
            extra = ""
            if args.lift and "liftCandidateDeclarations" in r:
                extra = (f" lift={r['liftCandidateDeclarations']}decls/{r['liftCandidateLonghands']}longh"
                         f" inert={r['liftRedundant']} keep={r['liftLoadBearing']} unmeasured={r['liftUnmeasured']}")
            print(f"{r['page']:<12} tested={r['elementsTested']:<5} change={r['visibleChange']:<5} noChange={r['noVisibleChange']}{extra}")

    totals = {
        "pages": len(rows),
        "hoverSelectors": sum(r["hoverSelectors"] for r in rows),
        "elementsTested": sum(r["elementsTested"] for r in rows),
        "visibleChange": sum(r["visibleChange"] for r in rows),
        "noVisibleChange": sum(r["noVisibleChange"] for r in rows),
    }
    lifted = [r for r in rows if "liftCandidateDeclarations" in r]
    if args.lift:
        if len(lifted) != len(rows):
            # A page whose leave-one-out run failed is a hole in the sweep, and it is
            # named rather than quietly summed over.
            missing = [r["page"] for r in rows if "liftCandidateDeclarations" not in r]
            print(f"LIFT_MISSING_PAGES {json.dumps(missing)}")
        totals["liftPages"] = len(lifted)
        totals.update({
            "liftCandidateDeclarations": sum(r["liftCandidateDeclarations"] for r in lifted),
            "liftCandidateLonghands": sum(r["liftCandidateLonghands"] for r in lifted),
            "liftRedundant": sum(r["liftRedundant"] for r in lifted),
            "liftLoadBearing": sum(r["liftLoadBearing"] for r in lifted),
            "liftUnmeasured": sum(r["liftUnmeasured"] for r in lifted),
            "liftGroupingMismatches": sum(r["liftGroupingMismatches"] for r in lifted),
            "liftRestoreFailures": sum(r["liftRestoreFailures"] for r in lifted),
        })
    print(f"HOVER_VERIFY_TOTAL {json.dumps(totals)}")
    (ARTIFACTS / "hover-verify-summary.json").write_text(json.dumps({"pages": rows, "totals": totals}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
