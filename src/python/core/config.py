"""core/config.py — the Config adapter for EINVITE_* settings.

One module answers the question "what is EINVITE_X set to?" for the whole
backend. Two real adapters sit behind the same ``get`` interface:

* the **env adapter** — live ``os.environ``, exactly as ``platform_env``
  behaved in server.py, features, and the maintenance tools;
* the **dict adapter** — in-process overrides installed by tests and
  harnesses (``override``/``clear``), so a test can configure the backend
  without touching process-global environment variables.

Precedence, identical through every path::

    override dict  >  EINVITE_X  >  legacy SOVAN_X  >  default

The legacy ``SOVAN_`` fallback applies inside the override dict too, so a
test may override either spelling and both behave like env did.

Standard library only, like every other module here. Import cost is
negligible; no side effects at import.
"""
from __future__ import annotations

import os
import threading

__all__ = ["get", "legacy_name", "override", "clear", "clear_all", "overrides_snapshot"]

_overrides: dict[str, str] = {}
_lock = threading.Lock()


def legacy_name(name: str) -> str:
    """SOVAN_* spelling for a ``EINVITE_*`` name (byte-preserving passthrough)."""
    return name.replace("EINVITE_", "SOVAN_", 1)


def get(name: str, default=None):
    """Read a setting: overrides first, then env (modern name, then legacy)."""
    with _lock:
        override_map = _overrides
    if name in override_map:
        return override_map[name]
    legacy = legacy_name(name)
    if legacy != name and legacy in override_map:
        return override_map[legacy]
    if os.environ.get(name) is not None:
        return os.environ[name]
    if legacy != name and os.environ.get(legacy) is not None:
        return os.environ[legacy]
    return default


def override(mapping: dict) -> None:
    """Install/extend in-process settings; values are stored as given."""
    with _lock:
        _overrides.update(dict(mapping))


def clear(*names: str) -> None:
    """Remove named settings from the override dict (no-op if absent).

    Exact-name only: clearing ``EINVITE_X`` never erases an independently
    installed ``SOVAN_X`` override, mirroring how env treats the two spellings
    as separate variables.
    """
    with _lock:
        for name in names:
            _overrides.pop(name, None)


def clear_all() -> None:
    """Empty the override dict entirely."""
    with _lock:
        _overrides.clear()


def overrides_snapshot() -> dict[str, str]:
    """View of current overrides (copy; callers cannot mutate internals)."""
    with _lock:
        return dict(_overrides)
