"""tests/config_adapter_test.py — the two Config adapters must behave identically.

`core.config` is the single Config interface behind which every EINVITE_*
setting is read. The env adapter (live os.environ, with the legacy SOVAN_
fallback) shipped in four private copies before; the dict adapter lets tests
configure the backend in-process. The contract under test:

    override dict  >  EINVITE_X  >  legacy SOVAN_X  >  default

— identical in both adapters, and `server.platform_env` (the 95-call-site
delegation) must hit the same precedence without changing its signature.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _root in (REPO_ROOT, REPO_ROOT / "src" / "python"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import core.config as config


def _clean_probe_env(monkeypatch, prefix="EINVITE_CONFIG_TEST_"):
    """Remove every env spelling that could interfere with the probes."""
    for var in list(os.environ):
        if var.startswith(prefix) or var.startswith(prefix.replace("EINVITE_", "SOVAN_", 1)):
            monkeypatch.delenv(var, raising=False)


def test_env_adapter_modern_name(monkeypatch):
    _clean_probe_env(monkeypatch)
    monkeypatch.setenv("EINVITE_CONFIG_TEST_PROBE", "from-env")
    assert config.get("EINVITE_CONFIG_TEST_PROBE") == "from-env"


def test_env_adapter_legacy_fallback(monkeypatch):
    _clean_probe_env(monkeypatch)
    monkeypatch.setenv("SOVAN_CONFIG_TEST_PROBE", "from-legacy")
    assert config.get("EINVITE_CONFIG_TEST_PROBE") == "from-legacy"


def test_env_adapter_modern_beats_legacy(monkeypatch):
    _clean_probe_env(monkeypatch)
    monkeypatch.setenv("EINVITE_CONFIG_TEST_PROBE", "modern")
    monkeypatch.setenv("SOVAN_CONFIG_TEST_PROBE", "legacy")
    assert config.get("EINVITE_CONFIG_TEST_PROBE") == "modern"


def test_env_adapter_default_when_unset(monkeypatch):
    _clean_probe_env(monkeypatch)
    assert config.get("EINVITE_CONFIG_TEST_PROBE", None) is None
    assert config.get("EINVITE_CONFIG_TEST_PROBE", "fallback") == "fallback"


def test_dict_adapter_wins_over_env(monkeypatch):
    _clean_probe_env(monkeypatch)
    monkeypatch.setenv("EINVITE_CONFIG_TEST_PROBE", "from-env")
    config.clear_all()
    try:
        config.override({"EINVITE_CONFIG_TEST_PROBE": "from-dict"})
        assert config.get("EINVITE_CONFIG_TEST_PROBE") == "from-dict"
    finally:
        config.clear_all()


def test_dict_adapter_precedence_matches_env_semantics(monkeypatch):
    _clean_probe_env(monkeypatch)
    config.clear_all()
    try:
        config.override({"SOVAN_CONFIG_TEST_PROBE": "legacy-override",
                         "EINVITE_CONFIG_TEST_PROBE": "modern-override"})
        assert config.get("EINVITE_CONFIG_TEST_PROBE") == "modern-override"
        config.clear("EINVITE_CONFIG_TEST_PROBE")
        assert config.get("EINVITE_CONFIG_TEST_PROBE") == "legacy-override"
        config.clear("SOVAN_CONFIG_TEST_PROBE")
        assert config.get("EINVITE_CONFIG_TEST_PROBE", None) is None
    finally:
        config.clear_all()


def test_clear_reverts_to_env(monkeypatch):
    _clean_probe_env(monkeypatch)
    monkeypatch.setenv("EINVITE_CONFIG_TEST_PROBE", "from-env")
    config.clear_all()
    try:
        config.override({"EINVITE_CONFIG_TEST_PROBE": "from-dict"})
        config.clear("EINVITE_CONFIG_TEST_TEST_STALE", "EINVITE_CONFIG_TEST_PROBE")
        assert config.get("EINVITE_CONFIG_TEST_PROBE") == "from-env"
    finally:
        config.clear_all()


def test_legacy_name_is_passthrough_for_other_names():
    assert config.legacy_name("PATH") == "PATH"
    assert config.legacy_name("EINVITE_DATA_DIR") == "SOVAN_DATA_DIR"


def test_server_platform_env_delegates_to_config(monkeypatch):
    _clean_probe_env(monkeypatch)
    config.clear_all()
    try:
        import server  # noqa: PLC0415  (after conftest put src/python on sys.path)
        monkeypatch.setenv("EINVITE_CONFIG_TEST_PROBE", "from-env")
        assert server.platform_env("EINVITE_CONFIG_TEST_PROBE", None) == "from-env"
        config.override({"EINVITE_CONFIG_TEST_PROBE": "from-dict"})
        assert server.platform_env("EINVITE_CONFIG_TEST_PROBE", None) == "from-dict"
    finally:
        config.clear_all()
