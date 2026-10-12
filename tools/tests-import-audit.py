#!/usr/bin/env python3
"""tests-import-audit.py — which modules under tests/ can pytest actually import?

Why this exists
---------------
`make test` and step 2 of `make reproduce` both run `python3 -m pytest tests/`.
Measured on this tree, that command does not run a single test:

    INTERNALERROR> File ".../tests/final_features_test.py", line 5, in <module>
    INTERNALERROR>     from server import validate_document
    INTERNALERROR> File ".../server.py", line 29, in <module>
    INTERNALERROR>     runpy.run_path(str(_REAL_SERVER), run_name="__main__")
    INTERNALERROR> SystemExit: 2
    no tests ran in 1.64s

`tests/` is not a pytest suite. It is a set of 250 executable scripts: 214 keep an
`if __name__ == "__main__":` guard and are run as `python3 tests/<name>.py`. A
minority are plain pytest modules. pytest's default file pattern (`test_*.py` and
`*_test.py`) collects both kinds, and importing a runner script executes its work —
starting the real server, or calling `argparse.parse_args()` on pytest's own argv.
A `SystemExit` raised during collection aborts the whole session, so one such file
takes the entire run with it, and pytest reports exit status 3 with "no tests ran".

This tool answers the only question that matters for wiring the gate: for each
module, does importing it (which is what collection does) leave the process alive?
A module that cannot be imported is not a test-module-level defect to be papered
over with `--continue-on-collection-errors`; it is a *runner*, and it is run by
`python3 <path>` instead.

Usage
-----
    python3 tools/tests-import-audit.py               # summary + JSON artifact
    python3 tools/tests-import-audit.py --json        # full JSON only
    python3 tools/tests-import-audit.py --timeout 8   # per-module seconds

Writes <artifacts>/tests-import-audit.json. Exit status is 0 whenever the audit
ran, whatever it found: it reports, it does not assert.

Caveat: a module is imported with `run_name` != `__main__`, so a module whose
import starts a server thread or writes files can still be "importable" and still
be unsuitable. Those are reported separately (`importableButSideEffecting`) by
scanning the module source for the calls that do it, and the report treats them as
a known limit of this audit rather than a clean pass.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parent
TESTS = REPO_ROOT / "tests"
ARTIFACTS = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))

# Module-level side effects that must never run during a test collection pass.
SIDE_EFFECT_PATTERNS = [
    (r"runpy\.run_path", "runpy.run_path at import"),
    (r"^\s*args\s*=\s*parser\.parse_args\(\)", "argparse at import"),
    (r"^\s*if not .*\n\s*sys\.exit", "sys.exit at import"),
    (r"^runpy\.", "runpy at import"),
]


def probe(path: Path, timeout: float) -> dict:
    """Import one module in a fresh interpreter and report what happened."""
    name = path.stem
    code = (
        "import importlib.util, sys\n"
        f"sys.path[:0] = [{str(REPO_ROOT)!r}, {str(REPO_ROOT / 'src' / 'python')!r}, {str(TESTS)!r}]\n"
        f"spec = importlib.util.spec_from_file_location({name!r}, {str(path)!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "sys.modules[" + repr(name) + "] = module\n"
        "spec.loader.exec_module(module)\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT), text=True, capture_output=True, timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"module": name, "path": f"tests/{path.name}", "ok": False,
                "reason": "timeout", "detail": f"import did not finish within {timeout}s"}
    if proc.returncode == 0:
        return {"module": name, "path": f"tests/{path.name}", "ok": True, "reason": "", "detail": ""}
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    detail = tail[-1] if tail else ""
    # The first line naming a file inside tests/ is the real origin.
    origin = next((ln.strip() for ln in tail if "tests/" in ln and "line" in ln), "")
    return {
        "module": name, "path": f"tests/{path.name}", "ok": False,
        "reason": f"exit={proc.returncode}", "detail": detail, "origin": origin,
    }


def side_effecting(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for pattern, label in SIDE_EFFECT_PATTERNS:
        if re.search(pattern, text, re.M):
            return label
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="tests-import-audit.py",
        description="Report which modules under tests/ pytest can import.",
    )
    ap.add_argument("--json", action="store_true", help="print the JSON report only")
    ap.add_argument("--timeout", type=float, default=10.0, help="per-module import timeout (s)")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    if not TESTS.is_dir():
        sys.stderr.write(f"tests-import-audit.py: no tests/ directory at {TESTS}\n")
        return 2

    files = sorted(TESTS.glob("*.py"))
    rows = [probe(path, args.timeout) for path in files]
    for row in rows:
        row["sideEffect"] = side_effecting(TESTS / Path(row["path"]).name)

    importable = [r for r in rows if r["ok"]]
    blocked = [r for r in rows if not r["ok"]]
    risky = [r for r in importable if r["sideEffect"]]
    summary = {
        "modules": len(rows),
        "importable": len(importable),
        "notImportable": len(blocked),
        "importableButSideEffecting": len(risky),
        "importableClean": len(importable) - len(risky),
    }
    report = {"summary": summary, "notImportable": blocked, "sideEffecting": risky}
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "tests-import-audit.json").write_text(json.dumps(report, indent=1))

    if args.json:
        print(json.dumps(report, indent=1))
        return 0
    print(f"TESTS_IMPORT_AUDIT {json.dumps(summary)}")
    print("\n--- NOT IMPORTABLE (runner scripts; run as python3 <path>) ---")
    for r in blocked:
        print(f"  {r['path']:<52} {r['reason']:<9} {r['detail'][:80]}")
        if r.get("origin"):
            print(f"      {r['origin'][:110]}")
    print(f"\n--- IMPORTABLE BUT SIDE-EFFECTING ({len(risky)}) ---")
    for r in risky:
        print(f"  {r['path']:<52} {r['sideEffect']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
