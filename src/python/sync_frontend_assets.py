#!/usr/bin/env python3
"""Sync runtime frontend assets into ``src/python/`` so the HTTP server can serve them.

The server in ``src/python/server.py`` sets ``ROOT = Path(__file__).resolve().parent``
(``src/python/``) and serves static files only from that directory. Source HTML
pages, the ``vendor/`` tree (e.g. ``vendor/momentkh.js``), the ``assets/`` tree
(fonts) and the ``licenses/`` tree (font OFL text) all live at the repo root,
so they must be copied into ``src/python/`` before the server can serve them.

This helper is idempotent: it only copies when the destination is missing or
stale (``dest_mtime < src_mtime``), so re-running it after a build is cheap and
safe. Generated bundle artifacts (``bundle-*-v15.js/.css``, ``editor-suite.*``)
are NOT copied here — they are produced by ``build_route_bundles.py`` and
``build_editor_bundle.py`` directly into ``src/python/``.

Usage::

    python3 src/python/sync_frontend_assets.py        # copy if stale
    python3 src/python/sync_frontend_assets.py --check # report drift without copying
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

# --- Repo layout -----------------------------------------------------------
# SCRIPT_DIR is src/python/ (the server ROOT). We copy runtime assets INTO here.
SCRIPT_DIR = Path(__file__).resolve().parent
# REPO_ROOT = /home/z/my-project/einvite-platform (two parents up from src/python/).
REPO_ROOT = SCRIPT_DIR.parent.parent
HTML_DIR = REPO_ROOT / "src" / "html"
JS_DIR = REPO_ROOT / "src" / "js"
CSS_DIR = REPO_ROOT / "src" / "css"
CSS_ORG_DIR = CSS_DIR / "organized"
VENDOR_DIR = REPO_ROOT / "vendor"
ASSETS_DIR = REPO_ROOT / "assets"
LICENSES_DIR = REPO_ROOT / "licenses"

# Each entry: (source_dir, dest_dir, glob_pattern, recursive).
#
# HTML files are flattened (src/html/foo.html -> src/python/foo.html).
# vendor/, assets/, licenses/ are copied recursively preserving subdirectory
# structure (e.g. assets/fonts/*.woff2 -> src/python/assets/fonts/*.woff2).
#
# JS/CSS source files are flattened (src/js/foo.js -> src/python/foo.js) so
# that individually-referenced scripts (the manifest's `earlyScripts` such as
# `theme-init.js` and `backend-mode-v14.js`, plus dynamically-loaded modules
# like `rich-text-contract.js`, `command-palette-v23.js`, etc.) resolve at the
# server root. The CSS organised subfolder mirrors its files flat too; where a
# name collides between src/css/ and src/css/organized/, the organised copy
# wins (it is the canonical reorganised set) — so organised is synced AFTER
# the top-level css dir.
# The webmanifest is flattened the same way (src/html/manifest.webmanifest ->
# src/python/manifest.webmanifest) so the PWA <link rel="manifest"> resolves.
SYNC_PLAN = [
    (HTML_DIR, SCRIPT_DIR, "*.html", False),
    (HTML_DIR, SCRIPT_DIR, "*.webmanifest", False),
    (VENDOR_DIR, SCRIPT_DIR / "vendor", "**/*", True),
    (ASSETS_DIR, SCRIPT_DIR / "assets", "**/*", True),
    (LICENSES_DIR, SCRIPT_DIR / "licenses", "**/*", True),
    (JS_DIR, SCRIPT_DIR, "*.js", False),
    (CSS_DIR, SCRIPT_DIR, "*.css", False),
    (CSS_ORG_DIR, SCRIPT_DIR, "*.css", False),
]


def _needs_copy(src: Path, dest: Path) -> bool:
    """Return True if ``dest`` is missing or older than ``src`` (so a copy is needed)."""
    if not dest.is_file():
        return True
    return dest.stat().st_mtime < src.stat().st_mtime


def copy_file(src: Path, dest: Path) -> bool:
    """Copy ``src`` to ``dest`` preserving metadata; skip if dest is fresh.

    Returns True if a copy was actually performed, False if it was skipped.
    """
    if not src.is_file():
        return False
    if not _needs_copy(src, dest):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def sync_tree(src_dir: Path, dest_dir: Path, pattern: str, recursive: bool) -> tuple[int, int]:
    """Sync one source tree to its destination, returning (copied, skipped) counts.

    For non-recursive syncs (HTML files), only the top-level files matching
    ``pattern`` are copied. For recursive syncs (vendor/, assets/, licenses/),
    every file under ``src_dir`` is mirrored into ``dest_dir`` preserving the
    relative subdirectory structure. Empty directories are not created — only
    directories that contain at least one copied file are materialised.
    """
    copied = 0
    skipped = 0
    if not src_dir.is_dir():
        return copied, skipped
    if recursive:
        for src in src_dir.glob(pattern):
            if src.is_file():
                rel = src.relative_to(src_dir)
                dest = dest_dir / rel
                if copy_file(src, dest):
                    copied += 1
                else:
                    skipped += 1
    else:
        for src in src_dir.glob(pattern):
            if src.is_file():
                dest = dest_dir / src.name
                if copy_file(src, dest):
                    copied += 1
                else:
                    skipped += 1
    return copied, skipped


def sync_all() -> dict:
    """Run every entry in ``SYNC_PLAN`` and return a per-source summary dict."""
    summary: dict = {}
    for src_dir, dest_dir, pattern, recursive in SYNC_PLAN:
        copied, skipped = sync_tree(src_dir, dest_dir, pattern, recursive)
        summary[src_dir.name] = {"copied": copied, "skipped": skipped, "dest": str(dest_dir)}
    return summary


def main(argv=None) -> int:
    """Entry point: ``--check`` reports drift without copying; otherwise sync."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Report what would be copied without writing")
    args = ap.parse_args(argv)
    if args.check:
        # In --check mode we report per-source drift counts without writing.
        # We use _needs_copy (which only reads stat()) so nothing is mutated.
        report: dict = {}
        for src_dir, dest_dir, pattern, recursive in SYNC_PLAN:
            copied = 0
            skipped = 0
            if src_dir.is_dir():
                for src in src_dir.glob(pattern):
                    if not src.is_file():
                        continue
                    rel = src.relative_to(src_dir)
                    dest = dest_dir / rel if recursive else dest_dir / src.name
                    if _needs_copy(src, dest):
                        copied += 1
                    else:
                        skipped += 1
            report[src_dir.name] = {"would_copy": copied, "up_to_date": skipped}
            print(f"{src_dir.name}: would_copy={copied} up_to_date={skipped}")
        return 0
    summary = sync_all()
    total_copied = 0
    total_skipped = 0
    for name, stats in summary.items():
        print(f"{name}: copied={stats['copied']} skipped={stats['skipped']} -> {stats['dest']}")
        total_copied += stats["copied"]
        total_skipped += stats["skipped"]
    print(f"SYNC_FRONTEND_ASSETS_DONE copied={total_copied} skipped={total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
