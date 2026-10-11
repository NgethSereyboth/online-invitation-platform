#!/usr/bin/env python3
"""Deprecated repo-root forwarder for the editor bundle generator.

Use ``python3 build.py editor [--check]`` instead. Kept runnable by this
filename because tests, ``src/python/release_check.py`` and CI invoke it.

The real generator lives in ``src/python/build/build_editor_bundle.py``.
"""
import os
import runpy
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_target = os.path.join(_here, "src", "python", "build", "build_editor_bundle.py")
if not os.path.isfile(_target):
    sys.stderr.write("forwarder: missing " + _target + "\n")
    sys.exit(2)
sys.path.insert(0, os.path.join(_here, "src", "python"))
sys.path.insert(0, os.path.join(_here, "src", "python", "build"))
sys.stderr.write(
    "deprecated: build_editor_bundle.py has moved - use 'python3 build.py editor'\n"
)
sys.argv[0] = _target
runpy.run_path(_target, run_name="__main__")
