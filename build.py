#!/usr/bin/env python3
"""Single entry point for the E-invitation frontend build.

Every generated artifact in this repository is produced by one of the three
generators under ``src/python/build/``. This module is the one place a human,
a test, or CI should call; the historical repo-root forwarders
(``build_editor_bundle.py``, ``build_route_bundles.py``,
``build_page_manifests.py``) are kept as deprecation shims so existing callers
keep working.

Usage
-----
    python3 build.py editor            # editor-suite.{js,css}
    python3 build.py bundles           # bundle-*.{js,css} for the 16 routes
    python3 build.py manifests         # page-assets.json (server + docs)
    python3 build.py mirror            # src/python/ runtime mirror (sync_frontend_assets.py)
    python3 build.py all               # all four, in dependency order
    python3 build.py all --check       # verify every artifact, write nothing
    python3 build.py bundles --check   # verify one step

Each step prints its own ``*_CHECK_PASSED`` / ``*_BUILT`` marker and exits
non-zero when ``--check`` finds a stale artifact, so the exit status of this
command is the gate.

The ``mirror`` step is why this command is the whole gate. ``src/python/`` is the
HTTP server's ROOT, so the HTML/CSS/JS the server serves is a *mirror* of
``src/html``, ``src/css`` and ``src/js``; keeping it in step used to depend on an
mtime comparison inside ``sync_frontend_assets.py``, which cannot see a content
change that arrives with an equal-or-older timestamp (a ``git checkout``, a
``git mv``, a restored archive) and which reported nothing when it drifted. It now
compares bytes, and ``--check`` prints ``MIRROR_CHECK_PASSED`` or fails.
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "src" / "python" / "build"

# Step name -> generator file under src/python/build/.
STEPS = {
    "editor": "build_editor_bundle.py",
    "bundles": "build_route_bundles.py",
    "manifests": "build_page_manifests.py",
    "mirror": "sync_frontend_assets.py",
}

# Dependency order: the route bundles must exist on disk before the page
# manifest measures their byte sizes, so ``manifests`` runs third; ``mirror``
# goes last so it verifies a fully-generated tree.
ORDER = ("editor", "bundles", "manifests", "mirror")


def run_step(step: str, check: bool) -> int:
    """Run one generator in-process and return its exit status."""
    target = BUILD_DIR / STEPS[step]
    if not target.is_file():
        sys.stderr.write(f"build.py: generator missing: {target}\n")
        return 2
    for extra in (ROOT / "src" / "python", BUILD_DIR):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    saved_argv = sys.argv[:]
    sys.argv = [str(target)] + (["--check"] if check else [])
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    finally:
        sys.argv = saved_argv
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "step",
        choices=sorted(STEPS) + ["all", "check"],
        help="which generator to run ('all' runs every step in order)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the artifacts without writing; non-zero if any is stale",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    steps = ORDER if args.step in ("all", "check") else (args.step,)
    check = args.check or args.step == "check"
    for step in steps:
        code = run_step(step, check)
        if code:
            print(f"BUILD_FAILED {step}", flush=True)
            return code
    print(f"BUILD_OK {' '.join(steps)}{' (check)' if check else ''}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
