#!/usr/bin/env python3
"""Deprecated repo-root forwarder for the page-asset manifest generator.

Use ``python3 build.py manifests [--check]`` instead. This shim is kept
importable and runnable because ``tests/v14_performance_budget_test.py`` does
``import build_page_manifests as manifests`` and calls ``manifests.build()``,
and several tests and CI steps invoke the CLI by this filename.

The real generator lives in ``src/python/build/build_page_manifests.py``.
"""
from __future__ import annotations

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TARGET = os.path.join(_HERE, "src", "python", "build", "build_page_manifests.py")
if not os.path.isfile(_TARGET):
    sys.stderr.write("forwarder: missing " + _TARGET + "\n")
    raise SystemExit(2)

for _path in (os.path.join(_HERE, "src", "python"), os.path.dirname(_TARGET)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

_spec = importlib.util.spec_from_file_location("_einvite_build_page_manifests", _TARGET)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# Re-export the generator's public surface so `import build_page_manifests`
# behaves exactly as it did before the generator moved.
build = _module.build
main = _module.main

if __name__ == "__main__":
    sys.stderr.write(
        "deprecated: build_page_manifests.py has moved — use 'python3 build.py manifests'\n"
    )
    raise SystemExit(_module.main())
