#!/usr/bin/env python3
"""Register the two AI-governance tests in the V0.52 release gate."""
import pathlib, py_compile, re, sys

p = pathlib.Path("src/python/run_review_checks.py")
if not p.is_file():
    sys.exit(f"Not found: {p}  (run from the repo root)")

raw = p.read_text(encoding="utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"      # file is CRLF on Windows
src = raw.replace("\r\n", "\n")

NEW = "'tests/ai_jit_enforcement_test.py','tests/ai_resource_scopes_test.py',"

if "ai_jit_enforcement_test" in src:
    print("Already registered. Nothing to do.")
    raise SystemExit(0)

m = re.search(r"(FAST_CHECKS=\[[\s\S]*?)\n\]", src)
assert m, "FAST_CHECKS closing bracket not found"
src = src[:m.end(1)] + "\n " + NEW + src[m.end(1):]

m = re.search(r"(SERIAL_FAST_CHECKS=\{[\s\S]*?)\n\}", src)
assert m, "SERIAL_FAST_CHECKS closing brace not found"
src = src[:m.end(1)] + "\n " + NEW + src[m.end(1):]

with p.open("w", encoding="utf-8", newline="") as f:
    f.write(src.replace("\n", nl))

py_compile.compile(str(p), doraise=True)

text = p.read_text(encoding="utf-8")
print("Registered in FAST_CHECKS:        ", text.count("ai_jit_enforcement_test") - 1)
print("Registered in SERIAL_FAST_CHECKS: ", text.count("ai_resource_scopes_test") - 1)
print("Compiles:                          OK")
print("\nNow run on an unrestricted machine:")
print("  python src/python/run_review_checks.py --skip-browser")
print("Expect: 'Running 103 V0.52 deterministic checks' with both entries PASS.")