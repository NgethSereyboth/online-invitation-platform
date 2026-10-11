#!/usr/bin/env python3
"""determinism-50x.py — run the 50-capture determinism check for a page.

The measuring instrument is ``tools/capture.mjs`` (node + puppeteer-core): it
loads a page 50 times, each in a fresh page in one browser process, and reports
the distribution of document height, section geometry and rendered text length.
This wrapper is the documented entry point so the check is a single command with
a meaningful exit status, and so CI/a reviewer never has to remember the node
flags.

A run is deterministic when every capture agrees. Two or more distinct states in
50 captures is a race with a reproducible signature — that is exactly how the
public.html content-visibility race was found (5440px vs 4220px, 50/50 each).

Usage
-----
    python3 tools/determinism-50x.py                     # public.html, 50 captures
    python3 tools/determinism-50x.py public.html --n 50
    python3 tools/determinism-50x.py index.html --n 20 --mode fixed --json

Exit status
-----------
0  every capture identical (deterministic)
1  more than one distinct state (nondeterministic)
2  setup or harness failure (no browser, server not answering)

Requires: node, the repo's node_modules (npm install), and a running server —
`make serve-gzip`, or `make reproduce` which starts one itself.
Produces: a distribution on stdout, and <artifacts>/determinism-<page>.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parent


def check_server(base_url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/index.html", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="determinism-50x.py",
        description="Capture a page N times and report whether it is deterministic.",
    )
    parser.add_argument("page", nargs="?", default="public.html",
                        help="page name, route or full URL (default public.html)")
    parser.add_argument("--n", type=int, default=50, help="number of captures (default 50)")
    parser.add_argument("--mode", choices=("wild", "fixed"), default="wild",
                        help="'fixed' freezes transitions/animations before first paint")
    parser.add_argument("--settle", type=int, default=1200, help="ms to wait after load")
    parser.add_argument("--base-url", default="http://127.0.0.1:8124")
    parser.add_argument("--json", action="store_true", help="emit the raw JSON report")
    parser.add_argument("--quiet", action="store_true", help="summary line only")
    parser.add_argument("--out", default=None, help="artifact filename (default determinism-<page>.json)")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not check_server(args.base_url):
        sys.stderr.write(
            f"determinism-50x.py: nothing answering on {args.base_url}\n"
            "  start the server first:  python3 tools/serve-gzip.py &\n"
            "  (or `make serve-gzip`)\n"
        )
        return 2

    page = args.page
    slug = page if "/" not in page else page.rsplit("/", 1)[-1]
    out = args.out or f"determinism-{slug.replace('.html', '')}.json"
    cmd = [
        sys.executable and "node", str(TOOLS / "capture.mjs"), page,
        f"--n={args.n}", f"--mode={args.mode}", f"--settle={args.settle}",
        f"--out={out}",
    ]
    cmd = ["node"] + cmd[1:]
    env_base = {"BASE_URL": args.base_url}
    import os
    env = {**os.environ, **env_base}
    if args.json:
        cmd.append("--json")
    if args.quiet:
        cmd.append("--quiet")

    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        return 2

    # The wrapper's own verdict, from the machine-readable summary the harness
    # writes, so the exit status never depends on parsing human-facing text.
    summary_path = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts")) / out
    if not summary_path.is_file():
        sys.stderr.write(f"determinism-50x.py: harness produced no summary at {summary_path}\n")
        return 2
    data = json.loads(summary_path.read_text())
    summary = data["summary"]
    print(
        f"DETERMINISM {'PASS' if summary['deterministic'] else 'FAIL'}: "
        f"{summary['n']} captures, {summary['distinctStates']} distinct state(s), "
        f"console errors {summary['consoleErrors']}"
    )
    return 0 if summary["deterministic"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
