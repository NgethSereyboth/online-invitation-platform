#!/usr/bin/env python3
"""Deprecated repo-root forwarder for the route bundle generator.

Use ``python3 build.py bundles [--check]`` instead. Kept runnable by this
filename because several tests and CI steps invoke it directly.

The real generator lives in ``src/python/build/build_route_bundles.py``.
"""
from __future__ import annotations

import os
import runpy
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TARGET = os.path.join(_HERE, "src", "python", "build", "build_route_bundles.py")
if not os.path.isfile(_TARGET):
    sys.stderr.write("forwarder: missing " + _TARGET + "\n")
    raise SystemExit(2)

for _path in (os.path.join(_HERE, "src", "python"), os.path.dirname(_TARGET)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

sys.stderr.write(
    "deprecated: build_route_bundles.py has moved — use 'python3 build.py bundles'\n"
)
sys.argv[0] = _TARGET
runpy.run_path(_TARGET, run_name="__main__")
