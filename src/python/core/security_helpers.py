"""
Centralized security helpers for the eInvite backend.

Every fix in SECURITY-FIX-GUIDE.md references one of these functions.
Do not duplicate the logic at call sites — import from here.

See: docs/security/SECURITY-FIX-GUIDE.md §4.1
"""
from __future__ import annotations

import hashlib
import html
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

# ---------- SQL safety (Bandit B608) ----------

def safe_set_clause(
    updates: Mapping[str, Any],
    allowed_columns: frozenset[str] | set[str],
) -> tuple[str, list[Any]]:
    """
    Build a ``col1=?, col2=?`` clause from a dict, using ONLY columns
    present in ``allowed_columns``. Values are always returned as a list
    for parameter binding — never interpolated into the SQL string.

    Raises ValueError if ``updates`` is empty or contains only unknown columns.

    Usage::

        clause, params = safe_set_clause(
            {"title": "New", "evil; DROP": "x"},
            ALLOWED_INVITATION_COLUMNS,
        )
        db.execute(
            f"UPDATE invitations SET {clause} WHERE id=?",
            [*params, invitation_id],
        )
    """
    if not updates:
        raise ValueError("no updates supplied")
    filtered = [(k, v) for k, v in updates.items() if k in allowed_columns]
    if not filtered:
        raise ValueError("no valid columns in updates")
    clause = ", ".join(f"{col}=?" for col, _ in filtered)
    params = [v for _, v in filtered]
    return clause, params


def safe_order_by(
    requested: str | None,
    allowed: Iterable[str],
    default: str,
    direction_default: str = "ASC",
) -> str:
    """
    Return a safe ORDER BY fragment. ``requested`` is expected to be
    "column" or "column:desc". Anything not in ``allowed`` falls back to
    ``default``.
    """
    allowed_set = {a.lower() for a in allowed}
    if not requested:
        return f"{default} {direction_default}"
    col, _, direction = requested.partition(":")
    col_l = col.strip().lower()
    if col_l not in allowed_set:
        return f"{default} {direction_default}"
    dir_upper = direction.strip().upper()
    dir_safe = "DESC" if dir_upper == "DESC" else "ASC"
    return f"{col_l} {dir_safe}"


# ---------- Path containment (py/path-injection) ----------

def safe_path_under(base: Path | str, candidate: str) -> Path:
    """
    Resolve ``candidate`` under ``base`` and refuse to return anything that
    escapes ``base``. Raises ValueError on escape.

    Uses Path.resolve + relative_to (Python 3.9+). On Windows, the
    comparison is case-insensitive because NTFS is.
    """
    base_path = Path(base).resolve()
    target = (base_path / candidate).resolve()
    try:
        target.relative_to(base_path)  # raises ValueError if not under base
    except ValueError as exc:
        raise ValueError(f"path escapes base directory: {candidate!r}") from exc
    return target


# ---------- HTTP header safety (py/http-response-splitting) ----------

_HEADER_FORBIDDEN = re.compile(r"[\r\n\x00]")

def safe_header_value(value: Any) -> str:
    """
    Strip CR, LF, and NUL from a value before using it in an HTTP
    response header. Never call this on a header value that must
    contain those characters (there is no such header in this app).
    """
    return _HEADER_FORBIDDEN.sub("", str(value))


# ---------- Logging redaction (py/clear-text-logging-sensitive-data) ----------

_SENSITIVE_KEY = re.compile(
    r"pass(word)?|secret|token|api[_-]?key|authorization|cookie|"
    r"session|private|credential|bearer",
    re.IGNORECASE,
)

def redact(value: Any, *, keep: int = 4) -> str:
    """
    Return a log-safe representation of ``value``. Strings and bytes are
    shown as a fingerprint: a length marker plus a hash prefix. Non-scalars
    are shown as their type.
    """
    if value is None:
        return "None"
    if isinstance(value, (str, bytes, bytearray)):
        raw = value.encode() if isinstance(value, str) else bytes(value)
        digest = hashlib.sha256(raw).hexdigest()[:8]
        return f"<redacted len={len(raw)} sha256={digest}>"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    return f"<{type(value).__name__}>"


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return a copy of ``data`` with values under sensitive-looking keys
    replaced by their redacted form.
    """
    return {
        k: (redact(v) if _SENSITIVE_KEY.search(str(k)) else v)
        for k, v in data.items()
    }


# ---------- HTML escaping (centralize here) ----------

def escape_html(value: Any) -> str:
    """Escape for HTML text or attribute context."""
    return html.escape(str(value), quote=True)
