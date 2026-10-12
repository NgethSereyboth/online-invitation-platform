#!/usr/bin/env python3
"""versioned-rename-surface.py — measure what a rename batch can safely touch.

Why this exists
---------------
The versioned-file cleanup (``admin-page-v13.css`` -> ``admin-page.css``) was done in
batches of ten, chosen by a rule: *versioned files with zero test references*. The
rule matters because a test that pins a name turns a rename into a contract change,
and the batch's verification claim ("the rename changes no shipped byte") only holds
for files whose name is not asserted on.

That rule was applied by hand twice, and hand application is how a pass ends up
renaming a file a hash manifest records. This tool recomputes the surface each time:

  * every versioned CSS/JS file that is not a generated bundle;
  * which of them the live source list (`docs/route-bundle-sources-v15.json`) names,
    i.e. which ones actually ship;
  * which are referenced by `tests/` (the exclude class), and by everything else;
  * for each survivor, whether its name is *shadowed*: a same-basename file exists
    elsewhere (the flat `src/css/x.css` vs `src/css/organized/x.css` ambiguity that
    stopped batch 3 — the generator resolves one of two different files, so renaming
    either can silently change which CSS a route loads).

The output is the batch-N candidate list with the blockers named, so the next batch is
a decision about the list rather than a re-derivation of it.

Usage
-----
    python3 tools/versioned-rename-surface.py
    python3 tools/versioned-rename-surface.py --json

Exit status: 0 (it reports; it does not gate).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSIONED = re.compile(r"-v[0-9][0-9_]*[a-z]*\.(css|js)$")
SOURCE_LIST = REPO_ROOT / "docs" / "route-bundle-sources-v15.json"


def tracked(patterns: list[str]) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", *patterns], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return [p for p in proc.stdout.splitlines() if p.strip()]


def tracked_names() -> list[str]:
    """Every tracked path, once — the corpus a reference search scans.

    `tools/evidence/` is excluded: those files *are* the tool's own output (this
    tool's runs are recorded there, names and all), so counting them would make
    every file it ever reported look like it has a live reference — including in
    the list below the one being printed.
    """
    return [p for p in tracked(["."]) if not p.startswith("tools/evidence/")]


def live_source_names() -> set[str]:
    """File names the route generator reads, from the declared source list."""
    text = SOURCE_LIST.read_text(encoding="utf-8")
    doc = json.loads(text)
    names: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and VERSIONED.search(node):
            names.add(node)

    walk(doc)
    return names


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="versioned-rename-surface.py")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    corpus = tracked_names()
    corpus_text = {p: (REPO_ROOT / p).read_text(encoding="utf-8", errors="replace") for p in corpus if (REPO_ROOT / p).is_file()}

    files = [p for p in corpus if VERSIONED.search(p) and not Path(p).name.startswith("bundle-")]
    live = live_source_names()
    present = {Path(p).name for p in corpus}

    rows = []
    for path in sorted(files):
        name = Path(path).name
        refs_test = [p for p, text in corpus_text.items() if p.startswith("tests/") and name in text]
        refs_other = [p for p, text in corpus_text.items() if not p.startswith("tests/") and p != path and name in text]
        stripped = VERSIONED.sub(lambda m: "m." + m.group(1), name)
        # The rename *target*: same name with the version segment removed.
        target = VERSIONED.sub(lambda m: "." + m.group(1), name)
        # A collision is a tracked file that already holds the target name. The
        # src/python mirror holds the same name as its source by design, so a
        # same-name entry under src/python is not a collision.
        collides = sorted(
            p for p in corpus
            if p != path and Path(p).name == target and not p.startswith("src/python/")
        )
        rows.append({
            "path": path,
            "name": name,
            "target": target,
            "mirror": p if False else sorted(p for p in corpus if p != path and Path(p).name == name),
            "live": name in live,
            "testRefs": refs_test,
            "otherRefs": refs_other,
            "collides": collides,
            "inOrganized": "/organized/" in path,
            "isMirror": path.startswith("src/python/"),
        })

    # A candidate is a *source* file (a src/python entry is a mirror that moves with
    # its source), named by the live source list, that no test pins.
    pool = [r for r in rows if r["live"] and not r["testRefs"] and not r["isMirror"]]
    ready = [r for r in pool if not r["collides"]]
    blocked = [r for r in pool if r["collides"]]

    summary = {
        "versionedFiles": len(rows),
        "liveNamed": sum(1 for r in rows if r["live"]),
        "zeroTestRefs": sum(1 for r in rows if not r["testRefs"]),
        "candidatePool": len(pool),
        "readyToRename": len(ready),
        "blockedByTargetName": len(blocked),
        "inOrganized": sum(1 for r in pool if r["inOrganized"]),
    }

    if args.json:
        print(json.dumps({"summary": summary, "ready": ready, "blocked": blocked}, indent=2))
        return 0

    print("RENAME_SURFACE " + json.dumps(summary))
    print()
    print("--- READY: live-named, no test reference, rename target unclaimed ---")
    for r in ready:
        note = "in src/css/organized/ (resolver falls back, no flat file of this name exists)" if r["inOrganized"] else ""
        refs = [p for p in r["otherRefs"] if "route-bundle-sources" not in p]
        if refs:
            note = (note + "  " if note else "") + f"other reference(s): {', '.join(refs)}"
        print(f"  {r['path']:<48} -> {r['target']:<34} {note}")
    print()
    print("--- BLOCKED: the rename target name is already taken ---")
    for r in blocked:
        print(f"  {r['path']:<48} -> {r['target']:<34} exists at {', '.join(r['collides'])}")
    print()
    print("--- EXCLUDED: referenced by tests/ (a rename would be a contract change) ---")
    for r in sorted((r for r in rows if r["testRefs"] and not r["isMirror"]), key=lambda r: r["path"]):
        print(f"  {r['path']:<48} {len(r['testRefs'])} test reference(s)")
    print()
    print("--- EXCLUDED: not named by the live source list ---")
    orphans = [r for r in rows if not r["live"] and not r["isMirror"]]
    print(f"  {len(orphans)} source file(s); first 10:")
    for r in orphans[:10]:
        print(f"  {r['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
