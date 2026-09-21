#!/usr/bin/env python3
"""Diagnose test asset references after the structure reorg.

For every test in tests/, find file references and report whether each
resolves from the repo root. Distinguishes:
  OK    - resolves today
  MOVED - exists elsewhere (path fix possible)
  GONE  - not found anywhere (target deleted; test is dead)
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
TESTS = REPO / "tests"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache"}
SUFFIXES = (".js", ".css", ".json", ".html", ".mjs")

index: dict[str, list[Path]] = {}
for p in REPO.rglob("*"):
    if not p.is_file() or p.suffix not in SUFFIXES:
        continue
    if any(part in SKIP_DIRS for part in p.parts):
        continue
    index.setdefault(p.name, []).append(p.relative_to(REPO))

PATTERNS = [
    re.compile(r'ROOT\s*/\s*"([^"]+)"'),
    re.compile(r"ROOT\s*/\s*'([^']+)'"),
    re.compile(r"""readFileSync\(\s*['"]([^'"]+)['"]"""),
    re.compile(r"""['"]([\w./-]+\.(?:js|css|json|html|mjs))['"]"""),
]

def refs_in(text: str) -> set[str]:
    out = set()
    for pat in PATTERNS:
        for m in pat.finditer(text):
            ref = m.group(1)
            if ref.endswith(SUFFIXES) and not ref.startswith(("http", "//", "data:")):
                out.add(ref)
    return out

ok, moved, gone = [], [], []
for test in sorted(TESTS.glob("*.py")):
    text = test.read_text(encoding="utf-8", errors="replace")
    for ref in sorted(refs_in(text)):
        if (REPO / ref).is_file():
            ok.append((test.name, ref))
            continue
        hits = index.get(Path(ref).name, [])
        if hits:
            moved.append((test.name, ref, hits[0]))
        else:
            gone.append((test.name, ref))

print(f"RESOLVES OK : {len(ok)}")
print(f"MOVED       : {len(moved)}")
print(f"GONE        : {len(gone)}\n")

print("=== MOVED (fixable by path rewrite) ===")
for ref, actual in sorted({(r, str(a)) for _, r, a in moved}):
    who = next(t for t, r, _ in moved if r == ref)
    print(f"  {ref}  ->  {actual}    (e.g. {who})")

print("\n=== GONE (not found anywhere) ===")
for ref in sorted({r for _, r in gone}):
    who = next(t for t, r in gone if r == ref)
    print(f"  {ref}    (referenced by {who})")

touched = {t for t, *_ in moved} | {t for t, _ in gone}
print(f"\nDistinct moved assets : {len({r for _, r, _ in moved})}")
print(f"Distinct gone assets  : {len({r for _, r in gone})}")
print(f"Tests with any issue  : {len(touched)}")