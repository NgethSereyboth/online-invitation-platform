#!/usr/bin/env python3
"""Rewrites stale file references left by structural moves.

Reads docs/STRUCTURE-MAPPING.json, builds old->new lookup,
rewrites HTML script/link tags, JSON manifest paths, and Python imports.

Modes:
  (default / --dry-run)  scan only, print diffs/summary, exit 0
  --execute             apply rewrites, print changed files, exit 0

Safety:
- Never writes without --execute.
- Idempotent: second --execute produces zero changes.
- Skips generated artifacts (bundle-*, editor-suite.*) and documentation.
- Reports ambiguous basename collisions rather than guessing.

Run from repository root:
  python scripts/fix_structure_references.py
  python scripts/fix_structure_references.py --execute
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(sys.argv[0]).resolve().parent.parent
MAPPING_PATH = REPO / "docs" / "STRUCTURE-MAPPING.json"

HTML_DIR = REPO / "src" / "html"
MANIFESTS = [
    REPO / "docs" / "route-bundle-sources-v15.json",
    REPO / "docs" / "page-assets-v15.json",
]
PY_ROOTS = [REPO / "tests", REPO / "src" / "python", REPO / "plugins"]

SKIP_DOCS = {
    "docs/STRUCTURE-MAPPING.json",
    "docs/STRUCTURE-MAPPING.md",
    "docs/STRUCTURE-MAPPING.source.md",
    "docs/STRUCTURE-PILOT-AUDIT.md",
    "docs/.structure-migration-state.json",
}
SKIP_SCRIPTS = {"scripts/migrate_structure.py", "scripts/build_structure_mapping.py"}

BUNDLE_PATTERN = re.compile(r"^(bundle-|editor-suite\.)")

# Directory names we never descend into during Python scanning.
EXCLUDED_DIRS = {
    ".venv", ".git", "node_modules", "__pycache__", ".github",
    ".vscode", ".idea", ".m2", ".nuget", ".pytest_cache", "build", "dist",
}


def die(msg):
    print("STOP: " + msg)
    sys.exit(1)


def ensure_utf_stdout():
    """Reconfigure stdout so non-ASCII diffs don't crash on Windows consoles."""
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp1252", "ascii", "mbcs"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass


# ---------- mapping loading ----------

def load_mapping():
    if not MAPPING_PATH.is_file():
        die("missing " + str(MAPPING_PATH))
    data = json.loads(MAPPING_PATH.read_text(encoding="utf-8", errors="replace"))
    rows = data.get("rows", [])
    return rows


def build_indexes(rows):
    by_path = {}
    basename_to_targets = defaultdict(list)
    for r in rows:
        mode = r.get("mode")
        source = r.get("source")
        target = r.get("target")
        generated = r.get("generated")
        if source is None or target is None:
            continue
        if target == source:
            continue
        if generated:
            continue
        if mode not in ("move", "merge", "done"):
            continue
        by_path[source] = target
        basename = Path(source).name
        basename_to_targets[basename].append(source)

    by_basename = {}
    ambiguous = set()
    for basename, sources in basename_to_targets.items():
        targets = {by_path[s] for s in sources if s in by_path}
        if len(targets) == 1:
            by_basename[basename] = targets.pop()
        elif len(targets) > 1:
            ambiguous.add(basename)

    preemptive = []
    for r in rows:
        mode = r.get("mode")
        source = r.get("source")
        if mode not in ("move", "merge", "done"):
            continue
        if source and not (REPO / source).exists():
            preemptive.append(source)

    ambiguous = sorted(ambiguous)
    preemptive = sorted(set(preemptive))
    return by_path, by_basename, ambiguous, preemptive


# ---------- HTML ----------

def rewrite_html(by_basename):
    changed = {}
    for p in sorted(HTML_DIR.glob("*.html")):
        rel = p.relative_to(REPO).as_posix()
        if rel.startswith("bundle-") or BUNDLE_PATTERN.search(p.name):
            continue
        original = p.read_text(encoding="utf-8", errors="replace")
        text = original

        def sub_src(m):
            quote = m.group(1)
            val = m.group(2)
            rest = m.group(3)
            if not val.endswith(".js"):
                return m.group(0)
            basename = Path(val).name
            if basename not in by_basename:
                return m.group(0)
            target = by_basename[basename]
            if target.startswith("src/js/"):
                new_val = target[len("src/js/"):]
            elif target.startswith("src/css/"):
                new_val = target[len("src/css/"):]
            else:
                new_val = target
            return "src=" + quote + new_val + quote + rest

        def sub_href(m):
            quote = m.group(1)
            val = m.group(2)
            rest = m.group(3)
            if val.endswith(".html"):
                return m.group(0)
            if not val.endswith(".css"):
                return m.group(0)
            basename = Path(val).name
            if basename not in by_basename:
                return m.group(0)
            target = by_basename[basename]
            if target.startswith("src/js/"):
                new_val = target[len("src/js/"):]
            elif target.startswith("src/css/"):
                new_val = target[len("src/css/"):]
            else:
                new_val = target
            return "href=" + quote + new_val + quote + rest

        text = re.sub(r'src=(["\'])([^"\']+)\1([\s/>])', sub_src, text)
        text = re.sub(r'href=(["\'])([^"\']+)\1([\s/>])', sub_href, text)
        if text != original:
            changed[rel] = (original, text)
    return changed


# ---------- JSON ----------

def rewrite_json(by_path):
    changed = {}
    for p in MANIFESTS:
        rel = p.relative_to(REPO).as_posix()
        if not p.is_file():
            continue
        original = p.read_text(encoding="utf-8", errors="replace")
        text = original

        def replace_string(m):
            quote = m.group(1)
            val = m.group(2)
            # exact match
            if val in by_path:
                return quote + by_path[val] + quote
            # prefix match: bare path like core/theme.js
            for prefix in ("src/js/", "src/css/"):
                candidate = prefix + val
                if candidate in by_path:
                    return quote + by_path[candidate] + quote
            return m.group(0)

        new_text = re.sub(r'(["\'])([^"\']+?)\1', replace_string, original)
        if new_text != original:
            changed[rel] = (original, new_text)
    return changed


# ---------- Python imports ----------

def compute_py_replacement(target_path):
    stem = Path(target_path).stem
    if target_path.startswith("src/python/core/"):
        return "core." + stem
    elif target_path.startswith("src/python/features/"):
        return "features." + stem
    elif target_path.startswith("src/python/build/"):
        return "build." + stem
    else:
        return stem


def file_can_import_target(rel_path: str, text: str) -> bool:
    """Heuristic: does this file have the target package directory in its import path?

    Files under src/python/ naturally resolve packages such as core, features, build.
    Other files need an explicit sys.path insertion to reach those packages.
    """
    if rel_path.startswith("src/python/"):
        return True
    if "sys.path.insert" in text and ("ROOT" in text or "REPO" in text or "PROJECT_ROOT" in text):
        return True
    return False


def rewrite_python(by_path, by_basename):
    changed = {}
    needs_path = []
    broken = []

    # Build basename -> target mapping for .py files
    py_basename_to_target = {}
    for src, tgt in by_path.items():
        if src.endswith(".py"):
            py_basename_to_target[Path(src).name] = tgt

    import_re = re.compile(r"^(\s*)import\s+([a-zA-Z_][a-zA-Z0-9_]*)")
    from_re = re.compile(r"^(\s*)from\s+([a-zA-Z_][a-zA-Z0-9_*]+)(?:\s+import|$)")

    for root in PY_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            rel = p.relative_to(REPO).as_posix()
            if rel in SKIP_SCRIPTS or rel.startswith("docs/"):
                continue
            # Exclude non-project directories
            parts = Path(rel).parts
            if any(part in EXCLUDED_DIRS or part.startswith(".") for part in parts):
                continue

            original = p.read_text(encoding="utf-8", errors="replace")
            lines = original.splitlines(keepends=True)
            new_lines = []
            changed_file = False
            for line in lines:
                stripped = line.strip()
                new_line = line

                # match import X
                m = import_re.match(stripped)
                if m:
                    indent = m.group(1)
                    token = m.group(2)
                    replacement = _try_replace_token(
                        token, rel, p, py_basename_to_target, needs_path, broken
                    )
                    if replacement != token:
                        new_line = line[:m.start(2)] + replacement + line[m.end(2):]
                        changed_file = True

                if not changed_file:
                    m = from_re.match(stripped)
                    if m:
                        indent = m.group(1)
                        token = m.group(2)
                        if token != "*":
                            replacement = _try_replace_token(
                                token, rel, p, py_basename_to_target, needs_path, broken
                            )
                            if replacement != token:
                                new_line = line[:m.start(2)] + replacement + line[m.end(2):]
                                changed_file = True

                new_lines.append(new_line)

            new_text = "".join(new_lines)
            if new_text != original:
                changed[rel] = (original, new_text)

    return changed, needs_path, broken


def _try_replace_token(token, rel, p, py_basename_to_target, needs_path, broken):
    if "." in token:
        return token
    basename = token + ".py"
    if basename not in py_basename_to_target:
        return token
    target = py_basename_to_target[basename]
    if not (REPO / target).is_file():
        broken.append((rel, token, target))
        return token
    if not file_can_import_target(rel, p.read_text(encoding="utf-8", errors="replace")):
        needs_path.append((rel, token, target))
        return token
    return compute_py_replacement(target)


# ---------- main ----------

def main():
    ensure_utf_stdout()
    parser = argparse.ArgumentParser(description="Fix stale file references after structure moves.")
    parser.add_argument("--dry-run", action="store_true", help="scan only; do not modify files")
    parser.add_argument("--execute", action="store_true", help="apply rewrites")
    args = parser.parse_args()

    if args.dry_run and args.execute:
        die("cannot use --dry-run and --execute together")

    rows = load_mapping()
    by_path, by_basename, ambiguous, preemptive = build_indexes(rows)

    if preemptive:
        print("WARNING: %d mapped source files do not yet exist (pre-emptive references):" % len(preemptive))
        for s in preemptive[:10]:
            print("  " + s)
        if len(preemptive) > 10:
            print("  ... and %d more" % (len(preemptive) - 10))

    html_changes = rewrite_html(by_basename)
    json_changes = rewrite_json(by_path)
    py_changes, needs_path, broken = rewrite_python(by_path, by_basename)

    total_changed = len(html_changes) + len(json_changes) + len(py_changes)
    total_scanned = (
        len(list(HTML_DIR.glob("*.html")))
        + sum(1 for p in MANIFESTS if p.is_file())
        + sum(len(list(r.rglob("*.py"))) for r in PY_ROOTS if r.exists())
    )

    if not args.execute:
        print()
        print("SCANNED: %d files (HTML %d, JSON %d, Python %d)" % (
            total_scanned,
            len(list(HTML_DIR.glob("*.html"))),
            sum(1 for p in MANIFESTS if p.is_file()),
            total_scanned - len(list(HTML_DIR.glob("*.html"))) - sum(1 for p in MANIFESTS if p.is_file()),
        ))
        print("PENDING CHANGES: %d files (%d HTML, %d JSON, %d Python)" % (
            total_changed, len(html_changes), len(json_changes), len(py_changes)))
        print("AMBIGUOUS BASENAMES: %d (%s)" % (len(ambiguous), ", ".join(ambiguous) if ambiguous else "none"))
        print("NEEDS_PATH_SETUP: %d hits" % len(needs_path))
        if needs_path:
            shown = ["%s import %s (target %s)" % (rel, tok, tgt) for rel, tok, tgt in needs_path[:5]]
            print("  examples: " + "; ".join(shown))
        if broken:
            print("BROKEN_REFERENCE: %d hits" % len(broken))
        all_changed = {}
        all_changed.update(html_changes)
        all_changed.update(json_changes)
        all_changed.update(py_changes)
        if all_changed:
            for rel in sorted(all_changed):
                original, new_text = all_changed[rel]
                diff = difflib.unified_diff(
                    original.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=rel, tofile=rel + ".updated",
                )
                sys.stdout.writelines(diff)
                sys.stdout.write("\n")
        print()
        print("DRY RUN: no files were changed.")
        print()
        print("FINAL REPORT:")
        print("- Files scanned: %d" % total_scanned)
        print("- Files with pending changes: %d" % total_changed)
        print("- Ambiguous basenames: %s" % (", ".join(ambiguous) if ambiguous else "none"))
        if needs_path:
            unique_files = sorted({rel for rel, _, _ in needs_path})
            print("- Python imports (tests/): N test files insert repo root into sys.path and import modules now under src/python/features/; reported as NEEDS_PATH_SETUP and left unmodified.")
            print("  Evidence: %s" % "; ".join(unique_files[:3]))
        else:
            print("- Python imports: could be resolved automatically (no NEEDS_PATH_SETUP hits).")
        print("- BROKEN_REFERENCE hits: %d" % len(broken))
        return 0

    # --execute
    all_changed = {}
    all_changed.update(html_changes)
    all_changed.update(json_changes)
    all_changed.update(py_changes)
    for rel, (orig, new_text) in sorted(all_changed.items()):
        p = REPO / rel
        p.write_text(new_text, encoding="utf-8", newline="")

    for rel in sorted(all_changed):
        print("CHANGED: " + rel)

    html_changes2 = rewrite_html(by_basename)
    json_changes2 = rewrite_json(by_path)
    py_changes2, _, _ = rewrite_python(by_path, by_basename)
    second_changed = len(html_changes2) + len(json_changes2) + len(py_changes2)
    if second_changed != 0:
        print("WARNING: second scan after --execute found %d remaining changes (idempotency issue)" % second_changed)
    else:
        print("IDEMPOTENCY OK: second run produced zero changes.")

    print()
    print("FINAL REPORT:")
    for rel in sorted(all_changed):
        print("- Modified: %s" % rel)
    print("- Ambiguous basenames: %s" % (", ".join(ambiguous) if ambiguous else "none"))
    if needs_path:
        unique_files = sorted({rel for rel, _, _ in needs_path})
        print("- Python imports: N test files insert repo root into sys.path and import modules now under src/python/features/; reported as NEEDS_PATH_SETUP and left unmodified (evidence: %s)." % "; ".join(unique_files[:3]))
    else:
        print("- Python imports: could be resolved automatically.")
    print("- Files with changes after --execute: %d" % len(all_changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
