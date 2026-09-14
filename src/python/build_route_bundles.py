#!/usr/bin/env python3
"""Build deterministic V15 page bundles while retaining original source modules.

Repository layout
-----------------
The frontend source files live under ``src/js``, ``src/css`` (+ ``src/css/organized``)
and ``vendor/`` at the repository root, but the HTTP server in ``src/python/server.py``
serves static files from ``src/python/`` (its ``ROOT``). This builder therefore:

* reads source JS/CSS files from the repo layout (``src/js``, ``src/css``,
  ``src/css/organized``, ``vendor/``),
* writes the generated ``bundle-<page>-v15.js``/``.css`` artifacts into BOTH
  ``src/python/`` (so the server can serve them) AND ``src/js``/``src/css``
  (so the generated artifacts in the repo source of truth stay current),
* writes the manifest ``route-bundles-v15.json`` into BOTH ``src/python/``
  (where the server reads it) AND ``docs/`` (repo source of truth).

The build is byte-deterministic: every output is normalised to UTF-8/LF and the
manifest stores sha256 digests of those exact bytes so ``--check`` can verify a
deployment without re-reading the source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

# --- Repo layout -----------------------------------------------------------
# SCRIPT_DIR is the directory this file lives in (src/python/). The HTTP server
# also serves from here, so generated artifacts MUST be written here.
SCRIPT_DIR = Path(__file__).resolve().parent
# REPO_ROOT = /home/z/my-project/einvite-platform (two parents up from src/python/).
REPO_ROOT = SCRIPT_DIR.parent.parent
JS_DIR = REPO_ROOT / "src" / "js"
CSS_DIR = REPO_ROOT / "src" / "css"
CSS_ORG = CSS_DIR / "organized"
VENDOR_DIR = REPO_ROOT / "vendor"
ASSETS_DIR = REPO_ROOT / "assets"
DOCS_DIR = REPO_ROOT / "docs"

# Source manifest (repo source of truth) lives in docs/, NOT src/python/.
SOURCES = DOCS_DIR / "route-bundle-sources-v15.json"
# Output manifest is mirrored to both locations.
MANIFEST_SERVER = SCRIPT_DIR / "route-bundles-v15.json"
MANIFEST_DOCS = DOCS_DIR / "route-bundles-v15.json"


def resolve_js_source(path: str) -> Path:
    """Resolve a JS source path to a concrete file under the repo layout.

    Tries ``src/js/<path>`` first (the common case), then falls back to
    ``<repo_root>/<path>`` so that ``vendor/momentkh.js`` resolves correctly.
    Raises FileNotFoundError if neither location has the file.
    """
    candidate = JS_DIR / path
    if candidate.is_file():
        return candidate
    candidate = REPO_ROOT / path
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Missing route bundle JS source: {path}")


def resolve_css_source(path: str) -> Path:
    """Resolve a CSS source path to a concrete file under the repo layout.

    Tries ``src/css/<path>`` first, then falls back to ``src/css/organized/<path>``.
    Raises FileNotFoundError if neither location has the file.
    """
    candidate = CSS_DIR / path
    if candidate.is_file():
        return candidate
    candidate = CSS_ORG / path
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Missing route bundle CSS source: {path}")


def read_js(path: str) -> str:
    """Read a JS source file's text using the repo-layout resolver."""
    return resolve_js_source(path).read_text(encoding="utf-8")


def read_css(path: str) -> str:
    """Read a CSS source file's text using the repo-layout resolver."""
    return resolve_css_source(path).read_text(encoding="utf-8")


def js_bundle(paths: list[str]) -> str:
    """Concatenate JS sources into a single bundle.

    Each source chunk is prefixed with a ``;`` separator and its trailing
    whitespace stripped — this preserves the original (pre-v54) byte format so
    regenerated bundles stay bit-identical to a clean repo.
    """
    chunks: list[str] = []
    for path in paths:
        chunks.append(f";{read_js(path).rstrip()}")
    return "".join(chunks)


def css_bundle(paths: list[str]) -> str:
    """Concatenate CSS sources into a single bundle.

    Strips block comments (``/* ... */``) from production CSS while preserving
    the legacy ``/* compact authenticated-page zoom support */`` contract
    markers — those are extracted first and re-prepended after stripping so the
    authenticated-page zoom contract survives the minifying transform.
    """
    chunks: list[str] = []
    for path in paths:
        source = read_css(path)
        markers = "".join(
            re.findall(
                r"/\*[^*]*compact authenticated-page zoom support[^*]*\*/",
                source,
                flags=re.I,
            )
        )
        chunks.append(markers + re.sub(r"/\*.*?\*/", "", source, flags=re.S).rstrip())
    return "".join(chunks)


def encoded(text: str) -> bytes:
    """Normalise text to explicit UTF-8/LF bytes; the exact bytes written+hashed."""
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def digest(text: str) -> str:
    """Return the sha256 hex digest of ``encoded(text)``."""
    return hashlib.sha256(encoded(text)).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    """Atomically write normalised UTF-8/LF bytes to ``path`` via a .tmp rename.

    A partial build never leaves a truncated bundle visible to the server.
    """
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encoded(text))
    temporary.replace(path)


def write_both(name: str, content: str, dirs: list[Path]) -> None:
    """Write a generated artifact to every directory in ``dirs``.

    The first directory is treated as the primary (server-served) location and
    is written first; subsequent directories are mirrors (repo source of truth).
    Each copy uses ``atomic_write`` so a crash mid-mirror leaves the primary
    intact and the mirror either fully-written or absent.
    """
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        atomic_write(d / name, content)


def build(write: bool) -> dict:
    """Build the route-bundle manifest (and optionally write artifacts).

    When ``write`` is True, every generated ``bundle-<page>-v15.js``/``.css`` is
    written to BOTH ``src/python/`` (server) and ``src/js``/``src/css`` (repo),
    and the manifest JSON is written to BOTH ``src/python/`` and ``docs/``.
    Returns the manifest dict (always populated, regardless of ``write``).
    """
    spec = json.loads(SOURCES.read_text(encoding="utf-8"))
    result: dict = {"version": 15, "pages": {}}
    for page, entry in sorted(spec["pages"].items()):
        stem = Path(page).stem
        js_name = f"bundle-{stem}-v15.js"
        css_name = f"bundle-{stem}-v15.css"
        js = js_bundle(entry["scripts"])
        css = css_bundle(entry["styles"])
        if write:
            # JS bundles mirror into src/js/ (repo truth); CSS bundles into src/css/.
            write_both(js_name, js, [SCRIPT_DIR, JS_DIR])
            write_both(css_name, css, [SCRIPT_DIR, CSS_DIR])
        result["pages"][page] = {
            "javascript": js_name,
            "stylesheet": css_name,
            "sources": entry,
            "scriptBytes": len(encoded(js)),
            "styleBytes": len(encoded(css)),
            "scriptSha256": digest(js),
            "styleSha256": digest(css),
        }
    if write:
        text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        atomic_write(MANIFEST_SERVER, text)
        atomic_write(MANIFEST_DOCS, text)
    return result


def _manifest_text(result: dict) -> str:
    """Serialise the manifest dict to its canonical JSON form (sorted, LF, +NL)."""
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv=None) -> int:
    """Entry point: ``--check`` verifies artifacts; without it, regenerates them."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Verify generated bundles without writing files")
    args = ap.parse_args(argv)
    expected = build(write=not args.check)
    text = _manifest_text(expected)
    if args.check:
        # Verify BOTH manifest locations exist and match the expected text.
        for manifest_path in (MANIFEST_SERVER, MANIFEST_DOCS):
            if not manifest_path.is_file() or manifest_path.read_text(encoding="utf-8") != text:
                print(f"ROUTE_BUNDLE_MANIFEST_OUT_OF_DATE {manifest_path}")
                return 1
        # Verify every generated bundle file exists in BOTH locations and matches its hash.
        for page, item in expected["pages"].items():
            for key, hash_key in (("javascript", "scriptSha256"), ("stylesheet", "styleSha256")):
                name = item[key]
                mirror_dir = JS_DIR if name.endswith(".js") else CSS_DIR
                for location in (SCRIPT_DIR, mirror_dir):
                    p = location / name
                    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != item[hash_key]:
                        print(f"ROUTE_BUNDLE_OUT_OF_DATE {page} {location/name}")
                        return 1
        print("ROUTE_BUNDLE_CHECK_PASSED")
        return 0
    # Build mode: artifacts already written by build(write=True); emit summary.
    print(f"WROTE {len(expected['pages'])} route bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
