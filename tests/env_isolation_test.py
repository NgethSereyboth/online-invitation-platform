"""Regression guard for the autouse EINVITE_DATA_DIR restore in conftest.

The five in-process suites set a temporary data directory before importing
server.py. They cannot un-import the module, but the variable itself must not
survive the test. This pair relies on pytest's normal definition order: the
second test sees the first test's cleanup, and fails if conftest stops restoring
the variable.
"""
from __future__ import annotations

import os


_LEAK = "/tmp/einvite-env-isolation-leak"


def test_a_sets_a_temporary_data_dir():
    os.environ["EINVITE_DATA_DIR"] = _LEAK
    assert os.environ["EINVITE_DATA_DIR"] == _LEAK


def test_b_previous_test_did_not_leak_its_data_dir():
    assert os.environ.get("EINVITE_DATA_DIR") != _LEAK
