"""conftest.py — make `pytest tests/` collectable.

Why this file is needed
-----------------------
`make test` and step 2 of `make reproduce` run `python3 -m pytest tests/`. Before
this file existed that command did not run a single test. pytest's default file
patterns (`test_*.py` and `*_test.py`) collect both real pytest modules and
*runner* scripts, and importing a runner script executes its work — starting the
real server, or calling `argparse.parse_args()` on pytest's own argv. A
`SystemExit` raised during collection aborts the session:

    INTERNALERROR> File ".../tests/final_features_test.py", line 5, in <module>
    INTERNALERROR>     from server import validate_document
    INTERNALERROR> File ".../server.py", line 29, in <module>
    INTERNALERROR>     runpy.run_path(str(_REAL_SERVER), run_name="__main__")
    INTERNALERROR> SystemExit: 2
    no tests ran in 1.64s

So one runner script took the entire suite with it and pytest exited 3 with
"no tests ran". `--continue-on-collection-errors` does not help: this is an
INTERNALERROR, not a collection error.

How the exclusion list was derived — and how it stays honest
------------------------------------------------------------
Not by hand. `tools/tests-import-audit.py` imports every module under tests/ in a
fresh interpreter (exactly what collection does) and reports the ones that do not
survive, with the reason. Run on this tree under the same interpreter pytest uses:

    TESTS_IMPORT_AUDIT {"modules": 250, "importable": 238, "notImportable": 12, ...}

The 12 below are that list verbatim. Two things keep it from rotting:

  * `COLLECT_IGNORE` is checked against the filesystem at the top of this module.
    If a listed file is deleted or renamed, collection fails immediately with the
    stale name instead of silently ignoring the wrong file.
  * A module that *becomes* unimportable but is not listed here will make pytest
    fail loudly with the INTERNALERROR above, which fails step 2 of
    `make reproduce`. The failure mode is a red gate, never a quiet pass.

Each excluded file is still exercised the way the repository is designed to run it:
`python3 tests/<name>.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent

# The backend imports its siblings (core/, security_scanner_v54, ...) directly, and
# contract tests import repo-root launchers, so both roots are on the path exactly
# as tools/tests-import-audit.py sets them for its probe.
for _root in (REPO_ROOT, REPO_ROOT / "src" / "python", TESTS_DIR):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

# Runner scripts and platform-gated modules. Import-time behaviour, measured with
# `python3 tools/tests-import-audit.py` (see artifacts/tests-import-audit.json):
COLLECT_IGNORE = [
    # hangs >8s at import: module body starts the backend
    "final_features_test.py",
    "static_integrity_test.py",
    "v21_0_rich_text_server_test.py",
    # asserts about the served DOM at import time (and prints a banner)
    "_capture_v22_2.py",
    "final_workflow_audit_v7_test.py",
    "v22_zoom_layout_test.py",
    "v23_2_navigation_history_performance_test.py",
    "v52_selected_capabilities_contract_test.py",
    # Windows-only or absolute-path-bound, so they cannot import off the host
    "v0_52_first_time_setup_contract_test.py",
    "v0_52_laptop_host_contract_test.py",
    "v24_canva_experience_contract_test.py",
    # imports a repo-root module that only exists on the caller's sys.path
    "v13_backup_restore_test.py",
]

_missing = [name for name in COLLECT_IGNORE if not (TESTS_DIR / name).is_file()]
if _missing:
    raise RuntimeError(
        "tests/conftest.py: COLLECT_IGNORE lists files that no longer exist: "
        + ", ".join(_missing)
        + " — re-run `python3 tools/tests-import-audit.py` and update the list."
    )

# pytest's documented mechanism for keeping a file out of collection entirely.
collect_ignore = [str(TESTS_DIR / name) for name in COLLECT_IGNORE]
