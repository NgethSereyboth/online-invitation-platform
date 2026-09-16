#!/usr/bin/env python3
"""scripts/audit_file_structure.py — Part 2 Task 2.5.1 (ROADMAP-v0.54-to-v1.0 §2.5.1)

Walks ``src/js/``, ``src/css/``, ``src/python/`` and for each file extracts:
  - path
  - size_bytes
  - lines
  - top_level_symbols (function/class/const/def names)
  - references_count (how many other files in the same tree reference it)

Outputs a CSV to ``docs/STRUCTURE-AUDIT.csv``.

Run: ``python3 scripts/audit_file_structure.py``
"""
from __future__ import annotations
import csv
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "docs" / "STRUCTURE-AUDIT.csv"

# Patterns for top-level declarations
JS_PATTERNS = [
    re.compile(r'^\s*(?:const|let|var)\s+([A-Z_$][A-Za-z0-9_$]*)\s*=', re.MULTILINE),
    re.compile(r'^\s*function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(', re.MULTILINE),
    re.compile(r'^\s*class\s+([A-Za-z_$][A-Za-z0-9_$]*)', re.MULTILINE),
    re.compile(r'^\s*(?:window)\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=', re.MULTILINE),
]
PY_PATTERNS = [
    re.compile(r'^def\s+([a-z_][a-z0-9_]*)\s*\(', re.MULTILINE),
    re.compile(r'^class\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE),
]
CSS_PATTERNS = [
    re.compile(r'^\.([a-z][a-z0-9-]*)', re.MULTILINE),
    re.compile(r'^#([a-z][a-z0-9-]*)', re.MULTILINE),
    re.compile(r'^:root\s*\{([^}]*)\}', re.MULTILINE),  # CSS custom properties
]


def extract_symbols(path: Path) -> list[str]:
    """Extract top-level declarations from a file."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    symbols = []
    suffix = path.suffix.lower()
    if suffix == ".js":
        for pat in JS_PATTERNS:
            symbols.extend(pat.findall(content))
    elif suffix == ".py":
        for pat in PY_PATTERNS:
            symbols.extend(pat.findall(content))
    elif suffix == ".css":
        for pat in CSS_PATTERNS:
            matches = pat.findall(content)
            if isinstance(matches[0], tuple) if matches else False:
                # CSS custom properties group
                for m in matches:
                    if isinstance(m, tuple):
                        symbols.extend(m[0].split("--")[1:2] if "--" in m[0] else [])
            else:
                symbols.extend(matches)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in symbols:
        if s not in seen and len(s) > 1:
            seen.add(s)
            unique.append(s)
    return unique[:30]  # cap at 30 for CSV readability


def count_references(path: Path, all_files: list[Path], tree: str) -> int:
    """Count how many other files reference this file's basename or symbols."""
    name = path.stem  # e.g. "app" from "app.js"
    if name.startswith("bundle-") or name.startswith("editor-suite"):
        return 0  # generated files
    count = 0
    for other in all_files:
        if other == path:
            continue
        if other.suffix not in (".js", ".py", ".html", ".css", ".json"):
            continue
        try:
            content = other.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Check if the basename appears as a reference (script src, import, etc.)
        if f"{path.name}" in content or f"{path.stem}" in content:
            count += 1
    return count


def walk_tree(root: Path, extensions: set[str]) -> list[Path]:
    """Walk a directory tree, returning files matching the extensions."""
    files = []
    if not root.exists():
        return files
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip __pycache__, node_modules, .git
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules", ".git", "data")]
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix.lower() in extensions:
                files.append(p)
    return files


def main() -> int:
    js_files = walk_tree(REPO / "src" / "js", {".js"})
    css_files = walk_tree(REPO / "src" / "css", {".css"})
    py_files = walk_tree(REPO / "src" / "python", {".py"})
    all_files = js_files + css_files + py_files

    rows = []
    for p in all_files:
        try:
            stat = p.stat()
            content_lines = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            stat = type("S", (), {"st_size": 0})()
            content_lines = 0
        symbols = extract_symbols(p)
        tree = "js" if "/src/js/" in str(p) else ("css" if "/src/css/" in str(p) else "python")
        refs = count_references(p, all_files, tree)
        rows.append({
            "path": str(p.relative_to(REPO)),
            "tree": tree,
            "size_bytes": stat.st_size,
            "lines": content_lines,
            "top_level_symbols": "; ".join(symbols[:15]),
            "references_count": refs,
        })

    # Sort: tree, then path
    rows.sort(key=lambda r: (r["tree"], r["path"]))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "tree", "size_bytes", "lines", "top_level_symbols", "references_count"])
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    js_count = sum(1 for r in rows if r["tree"] == "js")
    css_count = sum(1 for r in rows if r["tree"] == "css")
    py_count = sum(1 for r in rows if r["tree"] == "python")
    versioned_js = sum(1 for r in rows if r["tree"] == "js" and re.search(r"-v\d+", r["path"]))
    big_files = sum(1 for r in rows if r["lines"] > 800)

    print(f"STRUCTURE_AUDIT_COMPLETE")
    print(f"  JS files:   {js_count} ({versioned_js} versioned)")
    print(f"  CSS files:  {css_count}")
    print(f"  Python:     {py_count}")
    print(f"  Files >800 lines: {big_files}")
    print(f"  Output: {OUTPUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
