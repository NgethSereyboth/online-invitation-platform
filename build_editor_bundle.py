#!/usr/bin/env python3
"""Build or verify the deterministic editor enhancement bundle.

Collaboration JavaScript remains a separately loaded runtime because it has its own
network lifecycle. Keeping the network modules out of the JavaScript bundle prevents
duplicate SSE connections and listeners when the editor bundle is regenerated. Its
small style modules remain in the generated CSS bundle so the separately loaded UI
keeps its intended appearance without adding extra stylesheet requests.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JS = [
    "canvas-plus.js",
    "editor-builders.js",
    "editor-pro.js",
    "photo-editor.js",
    "creative-packs.js",
]
CSS = [
    "canvas-plus.css",
    "editor-builders.css",
    "editor-pro.css",
    "photo-editor.css",
    "collaboration.css",
    "creative-packs.css",
    "collaboration-live.css",
]


def bundle_text(files: list[str], comment: str) -> str:
    chunks = [comment]
    for name in files:
        chunks.append(f"\n/* ===== {name} ===== */\n")
        chunks.append((ROOT / name).read_text(encoding="utf-8"))
    return "".join(chunks)


def expected_bundles() -> dict[str, str]:
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
    """Replace generated text atomically so interrupted builds never leave partial bundles."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)

def check() -> bool:
    mismatches: list[str] = []
    for output, expected in expected_bundles().items():
        path = ROOT / output
        actual = path.read_text(encoding="utf-8") if path.exists() else ""
        if actual != expected:
            mismatches.append(output)
    if mismatches:
        print("EDITOR_BUNDLE_OUT_OF_DATE: " + ", ".join(mismatches))
        return False
    print("EDITOR_BUNDLE_CHECK_PASSED")
    return True


def build() -> None:
    for output, content in expected_bundles().items():
        atomic_write(ROOT / output, content)
    print("EDITOR_BUNDLE_BUILT")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify generated bundles without changing files")
    args = parser.parse_args()
    if args.check:
        return 0 if check() else 1
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
