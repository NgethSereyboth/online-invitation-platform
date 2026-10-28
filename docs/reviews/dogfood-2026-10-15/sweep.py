#!/usr/bin/env python3
"""Per-page load sweep: proves each page actually rendered, then records errors.

Run with the dev server on 127.0.0.1:8232 and AGENT_BROWSER_SESSION exported.
Writes docs/reviews/dogfood-2026-10-15/sweep/SUMMARY.txt plus one file per page.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

AB = "./node_modules/.bin/agent-browser"
BASE = "http://127.0.0.1:8232"
PAGES = ["index", "dashboard", "admin", "account", "billing", "verify", "reset", "privacy",
         "guests", "responses", "analytics", "materials", "checkin", "templates", "designer", "public"]
OUT = Path("docs/reviews/dogfood-2026-10-15/sweep")
PROBE = ("JSON.stringify({title: document.title.slice(0,40), "
         "marker: document.body.dataset.page || 'NONE', "
         "nodes: document.querySelectorAll('script,link').length, "
         "text: document.body.innerText.trim().length})")
BAD = re.compile(r" (4\d\d|5\d\d)$")


def ab(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run one agent-browser command in the shared named session."""
    return subprocess.run([AB, *args], input=stdin, capture_output=True, text=True, timeout=120)


def probe() -> dict:
    """Read the page marker/title/nodes, unwrapping the CLI's JSON string encoding."""
    out = ab("eval", "--stdin", stdin=PROBE).stdout.strip()
    value = json.loads(out)
    if isinstance(value, str):
        value = json.loads(value)
    return value


def main() -> int:
    rows = []
    for page in PAGES:
        ab("errors", "--clear")
        ab("console", "--clear")
        ab("open", f"{BASE}/{page}.html")
        ab("wait", "--load", "domcontentloaded")
        time.sleep(2)
        meta = probe()
        errors = [line for line in ab("errors").stdout.splitlines() if line.strip()]
        bad = [line for line in ab("network", "requests").stdout.splitlines()
               if BAD.search(line.strip()) and "favicon" not in line]
        rows.append((page, meta, errors, bad))
        (OUT / f"{page}.txt").write_text(
            f"### {page}.html\n"
            f"marker={meta['marker']} title={meta['title']} script/link nodes={meta['nodes']} "
            f"visible text={meta['text']}\n"
            f"--- page errors ({len(errors)})\n" + "\n".join(errors) + "\n"
            f"--- console (errors/warnings)\n"
            + "\n".join(l for l in ab("console").stdout.splitlines() if re.search(r"error|fail|warn", l, re.I))
            + f"\n--- 4xx/5xx ({len(bad)})\n" + "\n".join(bad) + "\n",
            encoding="utf-8")
        print(f"{page:11} marker={meta['marker']:10} nodes={meta['nodes']:3} text={meta['text']:5} "
              f"errors={len(errors)} bad={len(bad)}")

    loaded = [r for r in rows if r[1]["marker"] not in ("NONE", "none", "", None) and r[1]["text"] > 0]
    total_err = sum(len(r[2]) for r in rows)
    total_bad = sum(len(r[3]) for r in rows)
    print(f"\nloaded pages: {len(loaded)}/{len(rows)} · page errors: {total_err} · 4xx/5xx: {total_bad}")
    (OUT / "SUMMARY.txt").write_text(
        f"pages={len(rows)} loaded={len(loaded)} pageErrors={total_err} badResponses={total_bad}\n"
        + "\n".join(f"{p:11} marker={m['marker']:10} nodes={m['nodes']:3} text={m['text']:5} "
                    f"errors={len(e)} bad={len(b)}" for p, m, e, b in rows) + "\n",
        encoding="utf-8")
    return 0 if len(loaded) == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
