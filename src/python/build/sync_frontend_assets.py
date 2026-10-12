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

Two defects this script used to have, and what replaced them
-----------------------------------------------------------
1. **Staleness was a timestamp comparison** (`dest.st_mtime < src.st_mtime`). A
   `git checkout`, `git mv`, restored archive or any mtime-preserving copy leaves
   a *different* file that is *not older*, so it was never re-copied, and the
   server kept serving the old bytes with nothing reporting it. Staleness is now
   a content comparison (byte equality), so "stale" and "differs" are the same
   question.
2. **Generated artifacts could be overwritten.** `src/css/organized/` still holds
   five stale `bundle-*-v15.css` files (e.g. 71,045 bytes against the generated
   128,721), and because the organised glob is synced *after* the top-level one,
   that glob could claim `src/python/bundle-*.css` and overwrite a generated,
   hash-verified bundle with an old copy. Anything matching `GENERATED` is
   therefore skipped here; those artifacts are written and verified by the three
   generators, not mirrored by this script.

Usage::

    python3 src/python/build/sync_frontend_assets.py        # copy what differs
    python3 src/python/build/sync_frontend_assets.py --check # report drift, exit 1
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path

# --- Repo layout -----------------------------------------------------------
# SCRIPT_DIR is src/python/ (the server ROOT). We copy runtime assets INTO here.
SCRIPT_DIR = Path(__file__).resolve().parent.parent  # src/python/ (server ROOT)
# REPO_ROOT = <repo root> (two parents up from src/python/).
REPO_ROOT = SCRIPT_DIR.parent.parent  # repo root (src/python/ -> src/ -> repo root)
HTML_DIR = REPO_ROOT / "src" / "html"
JS_DIR = REPO_ROOT / "src" / "js"
CSS_DIR = REPO_ROOT / "src" / "css"
CSS_ORG_DIR = CSS_DIR / "organized"
VENDOR_DIR = REPO_ROOT / "vendor"
ASSETS_DIR = REPO_ROOT / "assets"
LICENSES_DIR = REPO_ROOT / "licenses"

# Artifacts the generators write directly into the serve root. They are NOT
# mirror content: build_route_bundles.py / build_editor_bundle.py /
# build_page_manifests.py write them to BOTH src/python/ and the repo source of
# truth, and verify them by sha256 in their own --check. Mirroring them from
# src/css/ or src/css/organized/ can only ever overwrite them.
GENERATED = re.compile(
    r"^(?:bundle-[a-z0-9_-]+-v15\.(?:js|css)|editor-suite\.(?:js|css)|"
    r"route-bundles-v15\.json|page-assets-v15\.json)$"
)

# Each entry: (source_dir, dest_dir, glob_pattern, recursive).
#
# HTML files are flattened (src/html/foo.html -> src/python/foo.html).
# vendor/, assets/, licenses/ are copied recursively preserving subdirectory
# structure (e.g. assets/fonts/*.woff2 -> src/python/assets/fonts/*.woff2).
#
# JS/CSS source files are flattened (src/js/foo.js -> src/python/foo.js) so
# that individually-referenced scripts (the manifest's `earlyScripts` such as
# `core/theme.js` and `backend-mode-v14.js`, plus dynamically-loaded modules
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
    (JS_DIR / "core", SCRIPT_DIR / "core", "*.js", False),
    (CSS_DIR, SCRIPT_DIR, "*.css", False),
    (CSS_ORG_DIR, SCRIPT_DIR, "*.css", False),
]


def _sha256(path: Path) -> str:
    """sha256 of a file's bytes, read in chunks so a large bundle does not load whole."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _needs_copy(src: Path, dest: Path) -> bool:
    """Return True when ``dest`` is missing or its bytes differ from ``src``.

    Content, not mtime: see the module docstring. A size difference short-circuits
    the hash, which keeps the common case cheap without changing the answer.
    """
    if not dest.is_file():
        return True
    if dest.stat().st_size != src.stat().st_size:
        return True
    return _sha256(src) != _sha256(dest)


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
                if GENERATED.match(src.name):
                    continue  # generator-owned; never mirrored
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
        # --check is the mirror gate: it reports every destination whose bytes do
        # not match its source and exits non-zero, so a stale mirror fails the
        # build instead of being served. It mutates nothing.
        drifted: list[str] = []
        total_skipped = 0
        for src_dir, dest_dir, pattern, recursive in SYNC_PLAN:
            drifted_here = 0
            up_to_date = 0
            if src_dir.is_dir():
                for src in src_dir.glob(pattern):
                    if not src.is_file():
                        continue
                    if not recursive and GENERATED.match(src.name):
                        continue
                    rel = src.relative_to(src_dir)
                    dest = dest_dir / rel if recursive else dest_dir / src.name
                    if _needs_copy(src, dest):
                        drifted_here += 1
                        drifted.append(str(dest.relative_to(REPO_ROOT)))
                    else:
                        up_to_date += 1
            total_skipped += up_to_date
            print(f"{src_dir.name}: drifted={drifted_here} up_to_date={up_to_date}")
        if drifted:
            print(f"MIRROR_CHECK_FAILED {len(drifted)} stale destination(s)")
            for path in drifted:
                print(f"  stale  {path}")
            print("MIRROR_CHECK_HINT run: python3 src/python/build/sync_frontend_assets.py")
            return 1
        print(f"MIRROR_CHECK_PASSED (up_to_date={total_skipped})")
        return 0
    summary = sync_all()
    total_copied = 0
    total_skipped = 0
    for name, stats in summary.items():
        print(f"{name}: copied={stats['copied']} skipped={stats['skipped']} -> {stats['dest']}")
        total_copied += stats["copied"]
        total_skipped += stats["skipped"]
    print(f"SYNC_FRONTEND_ASSETS_DONE copied={total_copied} skipped={total_skipped}")
    print("MIRROR_CHECK_PASSED (after sync)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
