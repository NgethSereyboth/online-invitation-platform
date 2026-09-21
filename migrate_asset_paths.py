#!/usr/bin/env python3
"""Migrate test asset paths after the v54 structure reorg.

Rewrites ROOT-relative asset references in tests/ to current locations.

Ties between multiple copies are broken by PRIORITY, preferring the
canonical source over the src/python/ mirror created by
sync_frontend_assets.py.

Dry-run by default. Pass --apply to write.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
TESTS = REPO / "tests"
SKIP = {".git", "node_modules", "__pycache__", ".pytest_cache"}
EXT = (".js", ".css", ".json", ".html", ".mjs")

# Canonical-first. The src/python/ tree is a build mirror, not the source.
PRIORITY = ["src/js", "src/css", "src/html", "docs", "vendor", "assets", "src/python"]

# Deleted in 5ed591e (v54 refactor); functionality folded into
# editor/editor-core.js. Tests referencing these are stale.
DEAD = {"windows-ui-v16.js", "windows-ui-v16.css",
        "workspace-experience-v24.js", "workspace-experience-v24.css"}

INDEX: dict[str, list[Path]] = {}
for p in REPO.rglob("*"):
    if p.is_file() and p.suffix in EXT:
        if not any(part in SKIP for part in p.parts):
            INDEX.setdefault(p.name, []).append(p.relative_to(REPO))


def _rank(rel: Path) -> int:
    s = rel.as_posix()
    for i, pre in enumerate(PRIORITY):
        if s.startswith(pre + "/"):
            return i
    return len(PRIORITY)


def find(ref: str) -> Path | None:
    """Resolve a reference to a single repo-relative path, or None."""
    name = Path(ref).name
    if name in DEAD:
        return None
    hits = INDEX.get(name, [])
    if not hits:
        return None
    # Exact suffix match wins outright.
    exact = [h for h in hits if h.as_posix().endswith(ref.lstrip("/"))]
    pool = exact or hits
    if len(pool) == 1:
        return pool[0]
    return sorted(pool, key=_rank)[0]      # canonical source wins


def as_py(rel: Path) -> str:
    return "ROOT / " + " / ".join(f'"{p}"' for p in rel.parts)


PAT_A = re.compile(r'ROOT\s*/\s*(?P<q>["\'])(?P<ref>[^"\']+\.(?:js|css|json|html|mjs))(?P=q)')
PAT_B = re.compile(r'(readFileSync\s*\(\s*)(?P<q>["\'])(?P<ref>[^"\']+\.(?:js|css|json|html|mjs))(?P=q)')


def process(path: Path, apply: bool):
    raw = path.read_bytes()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    text = raw.decode("utf-8", errors="replace")
    fixes, dead, unresolved = [], [], []

    def resolve(ref):
        if (REPO / ref.lstrip("/")).is_file() or ref.startswith(("src/", "vendor/", "docs/")):
            return "skip"
        if Path(ref).name in DEAD:
            dead.append(ref)
            return "dead"
        actual = find(ref)
        if actual is None:
            unresolved.append(ref)
            return "skip"
        return actual

    def sub_a(m):
        r = resolve(m.group("ref"))
        if not isinstance(r, Path):
            return m.group(0)
        new = as_py(r)
        fixes.append((m.group(0), new))
        return new

    def sub_b(m):
        r = resolve(m.group("ref"))
        if not isinstance(r, Path):
            return m.group(0)
        new = m.group(1) + m.group("q") + r.as_posix() + m.group("q")
        fixes.append((m.group(0), new))
        return new

    text = PAT_A.sub(sub_a, text)
    text = PAT_B.sub(sub_b, text)

    if apply and fixes:
        text = text.replace("\r\n", "\n").replace("\n", nl.decode())
        path.write_bytes(text.encode("utf-8"))

    return fixes, dead, unresolved


def main():
    apply = "--apply" in sys.argv
    total, n_files = 0, 0
    all_dead, all_unresolved = [], []

    for t in sorted(TESTS.glob("*.py")):
        fixes, dead, unres = process(t, apply)
        if fixes:
            n_files += 1
            total += len(fixes)
            print(f"{'FIXED' if apply else 'WOULD FIX'}  {t.name}  ({len(fixes)})")
        all_dead.extend((t.name, d) for d in dead)
        all_unresolved.extend((t.name, u) for u in unres)

    verb = "Applied" if apply else "Would apply"
    print(f"\n{verb} {total} rewrites across {n_files} test files.")

    if all_dead:
        print(f"\nDEAD REFERENCES ({len({d for _, d in all_dead})} unique) — tests are stale:")
        for name in sorted({d for _, d in all_dead}):
            who = sorted({t for t, d in all_dead if d == name})
            print(f"  {name}\n      used by: {', '.join(who)}")

    if all_unresolved:
        print(f"\nSTILL UNRESOLVED ({len({u for _, u in all_unresolved})}):")
        for u in sorted({u for _, u in all_unresolved}):
            who = sorted({t for t, x in all_unresolved if x == u})
            print(f"  {u}\n      used by: {', '.join(who)}")

    if not apply and total:
        print("\nRun again with --apply to write.")


if __name__ == "__main__":
    main()