#!/usr/bin/env python3
"""Build or verify the deterministic editor enhancement bundle.

Collaboration JavaScript remains a separately loaded runtime because it has its own
network lifecycle. Keeping the network modules out of the JavaScript bundle prevents
duplicate SSE connections and listeners when the editor bundle is regenerated. Its
small style modules remain in the generated CSS bundle so the separately loaded UI
keeps its intended appearance without adding extra stylesheet requests.

Repository layout
-----------------
Source JS lives in ``src/js/<name>`` and source CSS lives in ``src/css/<name>``
(falling back to ``src/css/organized/<name>``). The generated artifacts
``editor-suite.js`` and ``editor-suite.css`` are written to BOTH ``src/python/``
(so the server in ``src/python/server.py`` can serve them — its ``ROOT`` is
``src/python/``) AND ``src/js``/``src/css`` (repo source of truth).
"""
from __future__ import annotations

import argparse
from pathlib import Path

# --- Repo layout -----------------------------------------------------------
# SCRIPT_DIR is src/python/ (where the server serves from). Generated artifacts
# are written here so the server can serve them.
SCRIPT_DIR = Path(__file__).resolve().parent
# REPO_ROOT = /home/z/my-project/einvite-platform
REPO_ROOT = SCRIPT_DIR.parent.parent
JS_DIR = REPO_ROOT / "src" / "js"
CSS_DIR = REPO_ROOT / "src" / "css"
CSS_ORG = CSS_DIR / "organized"

# Source modules that get concatenated into editor-suite.js.
JS = [
    "canvas-plus.js",
    "editor-builders.js",
    "editor-pro.js",
    "photo-editor.js",
    "creative-packs.js",
]
# Source modules that get concatenated into editor-suite.css.
CSS = [
    "canvas-plus.css",
    "editor-builders.css",
    "editor-pro.css",
    "photo-editor.css",
    "collaboration.css",
    "creative-packs.css",
    "collaboration-live.css",
]


def resolve_js(name: str) -> Path:
    """Resolve a JS source module to a concrete file under ``src/js/``.

    Raises FileNotFoundError if the file is missing.
    """
    candidate = JS_DIR / name
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Missing editor bundle JS source: {name}")


def resolve_css(name: str) -> Path:
    """Resolve a CSS source module, trying ``src/css/`` then ``src/css/organized/``.

    Raises FileNotFoundError if neither location has the file.
    """
    candidate = CSS_DIR / name
    if candidate.is_file():
        return candidate
    candidate = CSS_ORG / name
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"Missing editor bundle CSS source: {name}")


def bundle_text(files: list[str], comment: str) -> str:
    """Concatenate source modules into a single bundle string.

    Each module is preceded by a ``/* ===== <name> ===== */`` separator comment
    so the generated bundle stays auditable in a diff.
    """
    chunks: list[str] = [comment]
    for name in files:
        chunks.append(f"\n/* ===== {name} ===== */\n")
        if name.endswith(".js"):
            chunks.append(resolve_js(name).read_text(encoding="utf-8"))
        else:
            chunks.append(resolve_css(name).read_text(encoding="utf-8"))
    return "".join(chunks)


def expected_bundles() -> dict[str, str]:
    """Return the deterministic expected content for both editor-suite bundles."""
    return {
        "editor-suite.js": bundle_text(
            JS,
            "/* Generated editor runtime bundle. Edit source modules, then run build_editor_bundle.py. */\n",
        ),
        "editor-suite.css": bundle_text(
            CSS,
            "/* Generated editor style bundle. Edit source modules, then run build_editor_bundle.py. */\n",
        ),
    }


def atomic_write(path: Path, content: str) -> None:
    """Replace generated text atomically so interrupted builds never leave partial bundles.

    Writes to a sibling ``.tmp`` file then renames over the destination, which is
    atomic on POSIX for same-directory renames.
    """
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_both(name: str, content: str, dirs: list[Path]) -> None:
    """Write a generated artifact to every directory in ``dirs``.

    The first directory is the primary (server-served) location and is written
    first; subsequent directories are mirrors (repo source of truth).
    """
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        atomic_write(d / name, content)


def check() -> bool:
    """Verify the on-disk editor-suite bundles match the freshly-built expected content.

    Returns True if both bundles are present and byte-identical to the expected
    output in BOTH ``src/python/`` and ``src/js``/``src/css``.
    """
    mismatches: list[str] = []
    for output, expected in expected_bundles().items():
        mirror_dir = JS_DIR if output.endswith(".js") else CSS_DIR
        for location in (SCRIPT_DIR, mirror_dir):
            path = location / output
            actual = path.read_text(encoding="utf-8") if path.exists() else ""
            if actual != expected:
                mismatches.append(str(location / output))
    if mismatches:
        print("EDITOR_BUNDLE_OUT_OF_DATE: " + ", ".join(mismatches))
        return False
    print("EDITOR_BUNDLE_CHECK_PASSED")
    return True


def build() -> None:
    """Regenerate editor-suite.js and editor-suite.css in both output locations."""
    for output, content in expected_bundles().items():
        mirror_dir = JS_DIR if output.endswith(".js") else CSS_DIR
        write_both(output, content, [SCRIPT_DIR, mirror_dir])
    print("EDITOR_BUNDLE_BUILT")


def main() -> int:
    """Entry point: ``--check`` verifies; without it, regenerates bundles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify generated bundles without changing files")
    args = parser.parse_args()
    if args.check:
        return 0 if check() else 1
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
