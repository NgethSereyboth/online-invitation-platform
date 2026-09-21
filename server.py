"""Repo-root forwarder for the real backend at ``src/python/server.py``.

The V0.52 reorganization (commit 5ed591e) moved the Python backend into
``src/python/``, but many tests still spawn ``python server.py`` from the
repository root. This shim re-enters the real server in-process via
``runpy.run_path(..., run_name='__main__')`` so no subprocess re-exec happens
(the release gate kills process trees with ``taskkill /T``).
"""
import os
import runpy
import sys
from pathlib import Path

_REAL_SERVER = Path(__file__).resolve().parent / "src" / "python" / "server.py"

if not _REAL_SERVER.is_file():
    sys.stderr.write(f"server.py: real server not found at {_REAL_SERVER}\n")
    sys.exit(1)

# The real server imports sibling modules (core/, security_scanner_v54, ...)
# directly, so make src/python importable before executing it.
_PY_ROOT = str(_REAL_SERVER.parent)
if _PY_ROOT not in sys.path:
    sys.path.insert(0, _PY_ROOT)
os.environ.setdefault("PYTHONPATH", _PY_ROOT)
if _PY_ROOT not in os.environ.get("PYTHONPATH", ""):
    os.environ["PYTHONPATH"] = _PY_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

runpy.run_path(str(_REAL_SERVER), run_name="__main__")
