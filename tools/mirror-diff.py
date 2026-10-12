#!/usr/bin/env python3
"""mirror-diff.py — verify the served mirror (`src/python/`) by content, not mtime.

The gap this closes
-------------------
`src/python/build/sync_frontend_assets.py` copies the runtime assets the HTTP
server needs into `src/python/` (the server's ROOT): `src/html/*.html` and the
webmanifest flattened to the root, `vendor/`, `assets/`, `licenses/` recursively,
and `src/js` / `src/css` (+ `src/css/organized`) flattened to the root.

Its only staleness test is a timestamp comparison:

    def _needs_copy(src, dest):
        return dest.stat().st_mtime < src.stat().st_mtime

That is wrong in three ways that all fail *silently* — the server keeps serving
the old bytes and nothing reports it:

* **content changed, mtime not newer.** A `git checkout`, a `git mv`, a file
  restored from an archive, or any tool that preserves mtimes leaves a
  *different* file that is *not older*, so it is never re-copied.
* **a source was deleted.** Its mirror stays in `src/python/` forever and is
  served as if it were current.
* **a source was added.** Nothing reports that it never reached the mirror; it
  404s at request time (or, worse, the page links a stale same-name file).

This tool answers the question the timestamp cannot: *do the bytes match?* It
imports `SYNC_PLAN` from the syncer itself (so the two cannot drift apart in the
definition of what is mirrored) and reports three classes:

    drifted      source and mirror both exist, sha256 differs
    unmigrated   source exists, mirror missing
    orphans      mirror file with no source (a deleted or renamed source's copy)

Generated artifacts are exempt, and the exemption is printed rather than hidden:
`bundle-*-v15.{js,css}`, `editor-suite.{js,css}` and the two manifest JSONs are
written *directly* into `src/python/` by the generators, so they are not mirror
content at all. They are listed in `GENERATED` below and counted separately.

Usage
    python3 tools/mirror-diff.py                # report, exit 1 on drift
    python3 tools/mirror-diff.py --json
    python3 tools/mirror-diff.py --list         # print every drifted/orphan path
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYNCER = ROOT / "src" / "python" / "build" / "sync_frontend_assets.py"

# Written straight into src/python/ by build_route_bundles.py /
# build_editor_bundle.py / build_page_manifests.py — not mirror content. They are
# verified by those generators' own `--check`, which hashes them against the
# manifest, so this tool neither compares nor judges them (and it says how many
# it saw, rather than leaving the reader to wonder).
GENERATED = re.compile(
    r"^(?:bundle-[a-z0-9_-]+-v15\.(?:js|css)|editor-suite\.(?:js|css)|"
    r"route-bundles-v15\.json|page-assets-v15\.json)$"
)

# Serve-root files with no source in src/html, src/css or src/js. They are NOT
# stale mirror copies of a moved file — they were authored directly in the serve
# root and are tracked, so a fresh clone has them and nothing is missing. Deleting
# them would drop tracked content that other documents and tests reference
# (`src/python/test-a.html` is named by 15 files outside src/python/), which is a
# worse outcome than naming them here. Each is therefore exempt **by name and with
# a reason**, and the count is still reported separately below.
ORPHAN_EXEMPT = {
    "src/python/dashboard-css-km.html": "hand-authored i18n harness page in the serve root; tracked, no upstream source",
    "src/python/i18n-css-en.html": "hand-authored i18n harness page in the serve root; tracked, no upstream source",
    "src/python/i18n-css-km.html": "hand-authored i18n harness page in the serve root; tracked, no upstream source",
    "src/python/i18n-css-test.html": "hand-authored i18n harness page in the serve root; tracked, no upstream source",
    "src/python/i18n-inject-test.html": "hand-authored i18n harness page in the serve root; tracked, no upstream source",
    "src/python/test-a.html": "hand-authored test page in the serve root; tracked, referenced by 15 files outside src/python/",
    "src/python/test-b.html": "hand-authored test page in the serve root; tracked, no upstream source",
    "src/python/test-c.html": "hand-authored test page in the serve root; tracked, no upstream source",
    "src/python/test-d.html": "hand-authored test page in the serve root; tracked, no upstream source",
    "src/python/test-i18n-beacon.html": "hand-authored test page in the serve root; tracked, no upstream source",
    "src/python/test-i18n-click.html": "hand-authored test page in the serve root; tracked, no upstream source",
    "src/python/workflow-creation-flow-v3.css": "tracked pre-v4 stylesheet kept in the serve root; no upstream source, superseded by workflow-creation-flow-v4.css",
}


def load_syncer():
    """Import the syncer module so SYNC_PLAN has exactly one definition."""
    spec = importlib.util.spec_from_file_location("_sync_frontend_assets", SYNCER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"mirror-diff: cannot import {SYNCER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_gitignored(path: Path) -> bool:
    """True when git ignores this path (so a fresh clone does not contain it)."""
    import subprocess

    proc = subprocess.run(
        ["git", "check-ignore", "--quiet", str(path)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_pairs(syncer) -> tuple[dict[Path, Path], list[Path]]:
    """dest (absolute) -> src (absolute), in SYNC_PLAN order; plus generator-owned files found.

    Later entries overwrite earlier ones for the same destination, which is
    exactly the syncer's own rule ("where a name collides between src/css/ and
    src/css/organized/, the organised copy wins") — and that rule is itself the
    reason generator-owned names are dropped: src/css/organized/ holds five stale
    bundle-*.css files (e.g. 71,045 bytes against the generated 128,721), and
    letting the organised glob claim `src/python/bundle-*.css` means the mirror
    step can overwrite a generated, hash-verified bundle with a stale copy.
    Generator-owned names are therefore excluded from the mirror model entirely.
    """
    pairs: dict[Path, Path] = {}
    generated_seen: list[Path] = []
    seen_dests: set[Path] = set()
    for src_dir, dest_dir, pattern, recursive in syncer.SYNC_PLAN:
        if not src_dir.is_dir():
            continue
        for src in sorted(src_dir.glob(pattern)):
            if not src.is_file():
                continue
            rel = src.relative_to(src_dir)
            dest = dest_dir / rel if recursive else dest_dir / src.name
            if dest in seen_dests and dest not in pairs:
                continue
            seen_dests.add(dest)
            if GENERATED.match(dest.name):
                pairs.pop(dest, None)
                if dest not in generated_seen:
                    generated_seen.append(dest)
                continue
            pairs[dest] = src
    return pairs, generated_seen


def mirrored_destinations(syncer) -> list[Path]:
    """The directories and globs whose contents are mirror content."""
    return [(dest_dir, pattern, recursive) for _src, dest_dir, pattern, recursive in syncer.SYNC_PLAN]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true", help="print every path in every class")
    args = ap.parse_args()

    syncer = load_syncer()
    serve_root = Path(syncer.SCRIPT_DIR)

    pairs, generated_seen = expected_pairs(syncer)

    drifted: list[dict] = []
    unmigrated: list[dict] = []
    for dest, src in sorted(pairs.items()):
        if not dest.is_file():
            unmigrated.append({"source": str(src.relative_to(ROOT)), "dest": str(dest.relative_to(ROOT))})
            continue
        if sha256(dest) != sha256(src):
            drifted.append({"source": str(src.relative_to(ROOT)), "dest": str(dest.relative_to(ROOT))})

    # Orphans: a mirror file inside a mirrored destination that no source maps to.
    # Each mirrored destination is visited once (the CSS_DIR and CSS_ORG_DIR plan
    # entries share a destination root, so a naive walk lists the same orphan
    # twice — which is how the first run reported workflow-creation-flow-v3.css
    # as two files).
    expected_dests = set(pairs.keys())
    orphans: list[dict] = []
    orphans_exempt: list[dict] = []
    generated_present: list[str] = []
    visited_dests: set[Path] = set()
    for dest_dir, pattern, recursive in mirrored_destinations(syncer):
        if not dest_dir.is_dir():
            continue
        for dest in sorted(dest_dir.glob(pattern if recursive else pattern)):
            if not dest.is_file() or dest in visited_dests:
                continue
            visited_dests.add(dest)
            rel = str(dest.relative_to(ROOT))
            if dest in expected_dests:
                continue
            if GENERATED.match(dest.name):
                generated_present.append(rel)
                continue
            reason = ORPHAN_EXEMPT.get(rel)
            if reason is None and is_gitignored(dest):
                reason = "gitignored local scratch: absent from a fresh clone, so nothing is missing there"
            (orphans_exempt if reason else orphans).append({"dest": rel, "reason": reason})

    result = {
        "sources": len(pairs),
        "drifted": len(drifted),
        "unmigrated": len(unmigrated),
        "orphans": len(orphans),
        "orphansExempt": len(orphans_exempt),
        "generatedExempt": len(generated_seen),
        "driftedPaths": drifted,
        "unmigratedPaths": unmigrated,
        "orphanPaths": orphans,
        "orphanExemptPaths": orphans_exempt,
    }

    ok = not (drifted or unmigrated or orphans)
    if args.json:
        print(json.dumps(result, indent=1))
    else:
        print(
            'MIRROR_DIFF {"sources": %d, "drifted": %d, "unmigrated": %d, "orphans": %d, '
            '"orphansExempt": %d, "generatedExempt": %d}'
            % (
                result["sources"],
                result["drifted"],
                result["unmigrated"],
                result["orphans"],
                result["orphansExempt"],
                result["generatedExempt"],
            )
        )
        if args.list:
            for row in drifted:
                print(f"  drifted     {row['source']} -> {row['dest']}")
            for row in unmigrated:
                print(f"  unmigrated  {row['source']} -> {row['dest']} (missing)")
            for row in orphans:
                print(f"  orphan      {row['dest']}")
            for row in orphans_exempt:
                print(f"  exempt      {row['dest']}  — {row['reason']}")
        print(
            f"MIRROR_DIFF_SUMMARY {result['drifted']} drifted, {result['unmigrated']} unmigrated, "
            f"{result['orphans']} orphans ({result['orphansExempt']} named and exempt)"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
