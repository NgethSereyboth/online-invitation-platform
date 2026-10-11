#!/usr/bin/env python3
"""font-payload.py — what index.html's faces cost, on disk and over the wire.

Why this exists
---------------
Section 4 of the report quotes a before/after font payload. The first draft took
its "before" number from a Lighthouse `transferSize` sum (which includes ~168
bytes of HTTP overhead per face) and its "after" number from the file sizes on
disk, then divided one by the other. Both numbers were real; the comparison was
not, and it overstated the reduction (37.9% instead of 37.7% on disk).

This tool prints both measures side by side, per face and in total, from sources
that can each be named: the git tree (on-disk bytes) and an lhci `lhr-*.json`
(transferSize). Nothing here needs a server or a browser.

Usage
-----
    python3 tools/font-payload.py                      # working tree, newest lhr
    python3 tools/font-payload.py --at 7b5f912         # on-disk sizes as committed
    python3 tools/font-payload.py --lhr .lighthouseci/lhr-1791708069007.json
    python3 tools/font-payload.py --lhr none           # on-disk only
    python3 tools/font-payload.py --json

Read-only: it reads tracked blobs, files and lhr JSON, and prints.
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parent  # same convention as the other tools/*.py
FONT_DIR = "assets/fonts"
PAGE = "index.html"


def git_tree_sizes(rev: str | None) -> dict[str, int] | None:
    """{filename: bytes} for every .woff2 under assets/fonts, at a revision or on disk."""
    if rev:
        out = subprocess.run(
            ["git", "ls-tree", "-r", "-l", rev, "--", FONT_DIR],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            sys.exit(f"font-payload: git ls-tree {rev} failed: {out.stderr.strip()}")
        sizes = {}
        for line in out.stdout.splitlines():
            meta, _, name = line.partition("\t")
            fields = meta.split()
            if len(fields) < 4 or not name.endswith(".woff2"):
                continue
            sizes[Path(name).name] = int(fields[3])
        return sizes
    d = REPO_ROOT / FONT_DIR
    return {p.name: p.stat().st_size for p in sorted(d.glob("*.woff2"))} if d.exists() else None


def newest_lhr() -> str | None:
    """The most recent lhr for index.html, or None if none is on disk."""
    best = None
    for path in sorted(glob.glob(str(REPO_ROOT / ".lighthouseci" / "lhr-*.json"))):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not str(data.get("requestedUrl", "")).endswith(PAGE):
            continue
        best = path  # sorted() == chronological, so the last match wins
    return best


def lhr_fonts(path: str) -> dict[str, int]:
    """{filename: transferSize} for every Font resource in one lhr."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data["audits"]["network-requests"]["details"]["items"]
    return {
        str(i["url"]).rsplit("/", 1)[-1]: int(i["transferSize"])
        for i in items
        if i.get("resourceType") == "Font"
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Per-face font payload, on disk and over the wire.")
    ap.add_argument("--at", metavar="REV", help="take on-disk sizes from this revision instead of the working tree")
    ap.add_argument("--lhr", metavar="PATH", help="lhr JSON to take transferSize from ('none' for on-disk only)")
    ap.add_argument("--fetched-from", metavar="FILE",
                    help="file listing the face names the page fetches, one per line "
                         "(committed under tools/evidence/ so the block does not depend on "
                         ".lighthouseci/, whose filenames are run timestamps)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    sizes = git_tree_sizes(args.at)
    if not sizes:
        sys.exit(f"font-payload: no .woff2 found under {FONT_DIR}"
                 + (f" at {args.at}" if args.at else ""))

    lhr_path = args.lhr
    if lhr_path is None:
        lhr_path = newest_lhr()
    if lhr_path in ("none", ""):
        lhr_path = None
    transfer = lhr_fonts(lhr_path) if lhr_path else {}

    named = None
    if args.fetched_from:
        src = Path(args.fetched_from)
        if not src.is_absolute():
            src = REPO_ROOT / src
        if not src.is_file():
            sys.exit(f"font-payload: not found: {src}")
        named = [
            line.strip() for line in src.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        missing = [n for n in named if n not in sizes]
        if missing:
            sys.exit("font-payload: fetched list names faces that are not in the tree at "
                     f"{args.at or 'HEAD'}: {', '.join(missing)}")

    # A delta is only meaningful when the on-disk bytes and the transferSize come
    # from the same state of the tree. With --at they cannot: the lhr measured
    # whatever was served when it ran. Printing `-24368` for a base-revision file
    # measured against an after-revision lhr is exactly the mixed-measure error
    # this tool exists to stop, so the column is suppressed and said so.
    deltas_meaningful = not args.at

    if named is not None:
        fetched = sorted(named)
    elif transfer:
        fetched = sorted(transfer)
    else:
        fetched = sorted(sizes)
    rows = []
    for name in sorted(sizes, key=lambda n: (-sizes[n], n)):
        rows.append(
            {
                "face": name,
                "on_disk": sizes[name],
                "transfer": transfer.get(name),
                "delta": (transfer[name] - sizes[name]) if (name in transfer and deltas_meaningful) else None,
                "fetched": name in fetched if (transfer or named) else None,
            }
        )

    all_disk = sum(sizes.values())
    fetch_disk = sum(sizes[n] for n in fetched if n in sizes)
    fetch_transfer = sum(transfer[n] for n in fetched if n in transfer)

    if args.json:
        print(json.dumps(
            {
                "on_disk_from": args.at or "working tree",
                "lhr": lhr_path,
                "deltas_meaningful": deltas_meaningful,
                "rows": rows,
                "total_all_faces_on_disk": all_disk,
                "fetched_faces": len(fetched),
                "fetched_on_disk": fetch_disk,
                "fetched_transfer": fetch_transfer or None,
            },
            indent=2,
        ))
        return 0

    where = f"{FONT_DIR} @ {args.at}" if args.at else f"{FONT_DIR} (working tree)"
    print(f"# {where}")
    if named is not None:
        print(f"# fetched set from {Path(args.fetched_from).name} ({len(named)} faces)")
    if lhr_path:
        print(f"# transferSize from {Path(lhr_path).name}")
    if lhr_path and not deltas_meaningful:
        print(f"# delta suppressed: on-disk sizes are {args.at}'s, the lhr measured the working tree")
    print(f"{'face':36} {'on disk':>9} {'transfer':>9} {'delta':>7}")
    for r in rows:
        mark = "" if r["fetched"] is None else ("  <- fetched by " + PAGE if r["fetched"] else "")
        print(
            f"{r['face']:36} {r['on_disk']:9}"
            f" {r['transfer'] if r['transfer'] is not None else '-':>9}"
            f" {r['delta'] if r['delta'] is not None else '-':>7}{mark}"
        )
    print(f"\n{'all faces on disk':36} {all_disk:9}")
    print(f"{'fetched faces on disk':36} {fetch_disk:9}   ({len(fetched)} faces)")
    if transfer:
        label = "fetched faces transferSize"
        print(f"{label:36} {fetch_transfer:9}   ({Path(lhr_path).name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
