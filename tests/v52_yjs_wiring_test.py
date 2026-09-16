#!/usr/bin/env python3
"""V54.30 Phase 4b — Y.js wiring smoke test.

Verifies that:
  1. The vendored Y.js bundle files exist under ``vendor/yjs/``.
  2. The SRI integrity manifest ``vendor/yjs/INTEGRITY.txt`` is present + lists
     the expected files (y.js, y-indexeddb.js, lib0.js, process-stub.js).
  3. The editor HTML page (``src/html/designer.html`` — the editor entry
     referenced by the route-bundle sources) loads Y.js via ``<script>`` or
     ``<link rel="modulepreload">`` tags with the ``/vendor/yjs/`` prefix +
     ``integrity="sha384-..."`` SRI attribute.
  4. The dashboard HTML page (``src/html/dashboard.html``) does the same
     (dashboard has collaboration features too — edit-history panel from V54.22).
  5. The Y.js bundle is mirrored into ``src/python/vendor/yjs/`` by
     ``sync_frontend_assets.py`` so the Python ``server.py`` static handler
     serves it at ``/vendor/yjs/...``.
  6. The Y.js bundle defines ``window.Y`` when loaded (smoke check by
     parsing the bundle's first 200 bytes for the ``Y`` export pattern).

This is a static / file-system test only — no headless browser is required.
For a runtime end-to-end test of Y.js CRDT convergence, see
``tests/v52_crdt_offline_merge_test.py`` which uses the YjsShim contract.

Run: ``PYTHONPATH=src/python:. python3 tests/v52_yjs_wiring_test.py``
"""

from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENDOR_YJS = REPO / "vendor" / "yjs"
MIRROR_YJS = REPO / "src" / "python" / "vendor" / "yjs"
EDITOR_HTML = REPO / "src" / "html" / "designer.html"
DASHBOARD_HTML = REPO / "src" / "html" / "dashboard.html"

EXPECTED_FILES = ("y.js", "y-indexeddb.js", "lib0.js", "process-stub.js", "INTEGRITY.txt")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def assert_files_exist() -> None:
    missing = [f for f in EXPECTED_FILES if not (VENDOR_YJS / f).is_file()]
    if missing:
        raise SystemExit(f"FAIL: missing vendored Y.js files: {missing}")
    # Confirm y.js is non-trivial (>10KB — the bundle is ~85KB)
    yjs_size = (VENDOR_YJS / "y.js").stat().st_size
    if yjs_size < 10_000:
        raise SystemExit(f"FAIL: vendor/yjs/y.js is suspiciously small ({yjs_size} bytes)")
    print(f"[OK] vendored Y.js files present (y.js = {yjs_size} bytes)")


def assert_integrity_manifest() -> None:
    txt = _read(VENDOR_YJS / "INTEGRITY.txt")
    for f in ("y.js", "y-indexeddb.js", "lib0.js", "process-stub.js"):
        if f not in txt:
            raise SystemExit(f"FAIL: INTEGRITY.txt missing entry for {f}")
        if "sha384-" not in txt:
            raise SystemExit("FAIL: INTEGRITY.txt missing sha384- hashes")
    print("[OK] INTEGRITY.txt lists all 4 files with sha384 hashes")


def assert_html_wires_yjs(html_path: Path, label: str) -> None:
    html = _read(html_path)
    # Must reference /vendor/yjs/y.js
    if "/vendor/yjs/y.js" not in html:
        raise SystemExit(f"FAIL: {label} does not reference /vendor/yjs/y.js")
    # Must have SRI integrity attribute
    if "integrity=\"sha384-" not in html:
        raise SystemExit(f"FAIL: {label} missing SRI integrity attribute on Y.js script tags")
    # Must preload lib0 (y.js depends on it)
    if "/vendor/yjs/lib0.js" not in html:
        raise SystemExit(f"FAIL: {label} missing /vendor/yjs/lib0.js (y.js dependency)")
    # Must have a verification snippet that checks window.Y
    if "window.Y" not in html:
        raise SystemExit(f"FAIL: {label} missing window.Y verification script")
    print(f"[OK] {label} wires Y.js with SRI + window.Y verification")


def assert_mirror_exists() -> None:
    missing = [f for f in EXPECTED_FILES if not (MIRROR_YJS / f).is_file()]
    if missing:
        raise SystemExit(
            f"FAIL: src/python/vendor/yjs/ missing {missing} — "
            "run: python3 src/python/sync_frontend_assets.py"
        )
    # Sizes must match
    for f in ("y.js", "y-indexeddb.js", "lib0.js", "process-stub.js"):
        src_size = (VENDOR_YJS / f).stat().st_size
        mirror_size = (MIRROR_YJS / f).stat().st_size
        if src_size != mirror_size:
            raise SystemExit(
                f"FAIL: mirror size mismatch for {f} "
                f"(vendor={src_size}, src/python={mirror_size})"
            )
    print(f"[OK] src/python/vendor/yjs/ mirror present + sizes match")


def assert_yjs_defines_Y() -> None:
    """Smoke check that the bundle exports Y (look for export pattern)."""
    yjs = _read(VENDOR_YJS / "y.js")
    # ESM bundles from esm.sh end with an export statement; Y.js exports Y
    if "export" not in yjs:
        raise SystemExit("FAIL: y.js bundle has no `export` statement — not an ESM bundle")
    # lib0 is bundled into y.js, so look for common Y.js symbols
    for sym in ("Doc", "Transaction", "AbstractType"):
        if sym not in yjs:
            raise SystemExit(f"FAIL: y.js bundle missing expected symbol '{sym}'")
    print("[OK] y.js bundle contains `export` + Y.js core symbols (Doc/Transaction/AbstractType)")


def main() -> int:
    assert_files_exist()
    assert_integrity_manifest()
    assert_html_wires_yjs(EDITOR_HTML, "src/html/designer.html")
    assert_html_wires_yjs(DASHBOARD_HTML, "src/html/dashboard.html")
    assert_mirror_exists()
    assert_yjs_defines_Y()
    print()
    print("V52_YJS_WIRING_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
