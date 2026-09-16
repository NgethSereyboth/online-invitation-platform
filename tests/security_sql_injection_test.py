#!/usr/bin/env python3
"""Security test for SQL injection fix (SECURITY-FIX-JOB-104649882925 §2.5).

Verifies that safe_set_clause rejects unknown column names and only
allows whitelisted columns through.
"""
import pytest
import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src", "python"))

from core.security_helpers import safe_set_clause, safe_order_by

ALLOWED = frozenset({"title", "url", "price"})


def test_rejects_unknown_column():
    """An attacker-supplied column name must never appear in the SQL clause."""
    clause, params = safe_set_clause(
        {"title": "New", "evil; DROP TABLE users--": "x"},
        ALLOWED,
    )
    assert "evil" not in clause
    assert clause == "title=?"
    assert params == ["New"]


def test_raises_on_empty():
    with pytest.raises(ValueError):
        safe_set_clause({}, ALLOWED)


def test_raises_when_only_unknown():
    with pytest.raises(ValueError):
        safe_set_clause({"evil": "x"}, ALLOWED)


def test_accepts_multiple():
    clause, params = safe_set_clause(
        {"title": "A", "url": "https://x", "price": 5},
        ALLOWED,
    )
    assert "title=?" in clause
    assert "url=?" in clause
    assert "price=?" in clause
    assert len(params) == 3


def test_safe_order_by_rejects_unknown():
    assert safe_order_by("evil; DROP--", ALLOWED, "title") == "title ASC"


def test_safe_order_by_accepts_known():
    assert safe_order_by("title:desc", ALLOWED, "title") == "title DESC"
    assert safe_order_by("url", ALLOWED, "title") == "url ASC"


def test_safe_order_by_defaults():
    assert safe_order_by(None, ALLOWED, "title") == "title ASC"
    assert safe_order_by("", ALLOWED, "title") == "title ASC"


if __name__ == "__main__":
    test_rejects_unknown_column()
    test_raises_on_empty()
    test_raises_when_only_unknown()
    test_accepts_multiple()
    test_safe_order_by_rejects_unknown()
    test_safe_order_by_accepts_known()
    test_safe_order_by_defaults()
    print("SECURITY_SQL_INJECTION_TEST_PASSED")
