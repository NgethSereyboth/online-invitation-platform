#!/usr/bin/env python3
"""bundle-line-map.py — map a line in a generated route bundle back to its source file.

Why this exists
---------------
Every instrument that observes the *running page* reports bundle coordinates:
`tools/forced-layout-attribution.mjs` names the hottest forced-layout site as
`bundle-index.js:11092:22`, and a CDP stack frames a hot selector the same
way. A human cannot edit line 11092 of a 12,000-line concatenation. This tool
replays the generator's own concatenation
(`src/python/build/build_route_bundles.py`: each source is `";" + text.rstrip()`
and the chunks are joined with **no separator at all**) and reports which source
file each bundle line came from.

The bug the first version of this tool had, and the check that now catches it
-----------------------------------------------------------------------------
Joining with no separator means the *last* line of each chunk and the *first*
line of the next chunk share one bundle line. The first version assumed every
chunk started a fresh line, so the mapping drifted one line per chunk — it
reported `11092 -> editor/editor-core.js:1340`, and line 1340 of that file is a
comment while bundle line 11092 is a `return target?.id === …` statement. The
mapping is right by construction now (the bundle line counter only advances
between source lines, never at a chunk boundary), and `--verify` checks the
result rather than trusting it: for every chunk it asserts that the mapped
source line's text actually occurs in the bundle line it was mapped to.

Usage
    python3 tools/bundle-line-map.py index.html 11092 5532 9699
    python3 tools/bundle-line-map.py index.html --verify
    python3 tools/bundle-line-map.py index.html --lines 11092,5532
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS_DIR = ROOT / "src" / "js"
CSS_DIR = ROOT / "src" / "css"
CSS_ORG = CSS_DIR / "organized"
DOCS_DIR = ROOT / "docs"
SOURCES = DOCS_DIR / "route-bundle-sources.json"


def resolve_js(path: str) -> Path:
    for candidate in (JS_DIR / path, ROOT / path):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"missing JS source: {path}")


def resolve_css(path: str) -> Path:
    for candidate in (CSS_DIR / path, CSS_ORG / path):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"missing CSS source: {path}")


def chunks_for(page: str, kind: str) -> list[tuple[str, list[str]]]:
    """[(relative source path, its source lines)] in generator order."""
    spec = json.loads(SOURCES.read_text(encoding="utf-8"))
    resolve = resolve_js if kind == "scripts" else resolve_css
    out = []
    for rel in spec["pages"][page][kind]:
        path = resolve(rel)
        text = path.read_text(encoding="utf-8").rstrip()
        out.append((str(path.relative_to(ROOT)), text.split("\n")))
    return out


def build_map(page: str, kind: str) -> dict[int, list[tuple[str, int]]]:
    """bundle line number -> [(source path, source line)] (one entry per chunk claiming it).

    The bundle line counter advances *between* source lines inside a chunk and
    NOT at a chunk boundary: because the chunks are joined with no separator,
    `…+text.rstrip()` puts the next chunk's first source line on the *same*
    output line as the previous chunk's last source line. Incrementing at the
    boundary is exactly the off-by-one that made the first version of this tool
    point at the wrong file; the boundary line therefore appears twice in the map.
    """
    mapping: dict[int, list[tuple[str, int]]] = {}
    line = 1
    for path, src_lines in chunks_for(page, kind):
        for index in range(1, len(src_lines) + 1):
            mapping.setdefault(line, []).append((path, index))
            if index < len(src_lines):
                line += 1
    return mapping


def exact_bundle_text(page: str, kind: str) -> str:
    return "".join((";" if kind == "scripts" else "") + "\n".join(src) for _, src in chunks_for(page, kind))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", nargs="?", default="index.html")
    ap.add_argument("lines", nargs="*", type=int)
    ap.add_argument("--lines", dest="lines_opt", default=None, help="comma-separated line numbers")
    ap.add_argument("--kind", choices=("scripts", "styles"), default="scripts")
    ap.add_argument("--verify", action="store_true", help="re-derive the bundle, diff against disk, and check every mapping")
    args = ap.parse_args()

    kind = args.kind
    suffix = ".js" if kind == "scripts" else ".css"
    bundle = (JS_DIR if kind == "scripts" else CSS_DIR) / f"bundle-{Path(args.page).stem}{suffix}"

    if args.verify:
        derived = exact_bundle_text(args.page, kind)
        on_disk = bundle.read_text(encoding="utf-8")
        identical = derived == on_disk
        mapping = build_map(args.page, kind)
        bundle_lines = on_disk.split("\n")
        # Cache each source's lines once rather than re-reading per mapping entry.
        source_cache: dict[str, list[str]] = {}
        checked = 0
        bad: list[str] = []
        for line_no, hits in mapping.items():
            if line_no > len(bundle_lines):
                continue
            bundle_line = bundle_lines[line_no - 1]
            # Every (source, src_line) claimed for a bundle line must have its text
            # present in that line. A boundary line genuinely contains two chunks'
            # text, so it has two mappings and both are checked.
            for path, src_line in hits:
                if path not in source_cache:
                    source_cache[path] = (ROOT / path).read_text(encoding="utf-8").rstrip().split("\n")
                src_lines = source_cache[path]
                if src_line - 1 >= len(src_lines):
                    continue
                needle = src_lines[src_line - 1].strip()
                if not needle:
                    continue
                checked += 1
                if needle not in bundle_line:
                    bad.append(f"{path}:{src_line} -> bundle:{line_no}")
        print(
            f"BUNDLE_LINE_MAP_VERIFY page={args.page} kind={kind} bundle_identical={identical} "
            f"mapped_lines={len(mapping)} source_lines_checked={checked} mismatches={len(bad)}"
        )
        for b in bad[:20]:
            print(f"  MISMATCH {b}")
        return 0 if identical and not bad else 1

    wanted = list(args.lines)
    if args.lines_opt:
        wanted += [int(x) for x in args.lines_opt.split(",") if x.strip()]

    mapping = build_map(args.page, kind)
    bundle_lines = bundle.read_text(encoding="utf-8").split("\n")
    print(f"BUNDLE_LINE_MAP page={args.page} kind={kind} bundle={bundle.relative_to(ROOT)} lines={len(bundle_lines)}")
    for n in wanted:
        hits = mapping.get(n)
        if not hits:
            print(f"  {n:>7} -> (out of range)")
            continue
        for path, src_line in hits:
            print(f"  {n:>7} -> {path}:{src_line}")
        if n - 1 < len(bundle_lines):
            print(f"          bundle text: {bundle_lines[n - 1][:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
