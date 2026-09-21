#!/usr/bin/env python3
"""Add encoding='utf-8' to bare read_text() calls in test files."""
import re, sys, pathlib

targets = sys.argv[1:] if len(sys.argv) > 1 else ["tests/*.py"]
files = []
for t in targets:
    files.extend(pathlib.Path(".").glob(t))

# Matches .read_text() with no args, or .read_text() at end of a call
pattern = re.compile(r"\.read_text\(\s*\)")
total = 0

for p in files:
    raw = p.read_bytes()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    src = raw.decode("utf-8", errors="replace")
    new, n = pattern.subn(".read_text(encoding='utf-8')", src)
    if n:
        p.write_bytes(new.replace("\r\n", "\n").replace("\n", nl.decode()).encode("utf-8"))
        print(f"{p}: {n} fixed")
        total += n

print(f"\nTotal: {total} fixed across {len(files)} files scanned.")