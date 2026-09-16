# Version History

This project uses **semantic versioning**. `0.x` is pre-1.0; `1.0.0` is the first
production-certified release.

> **Legacy history:** the pre-reset version history (V1 → V54.34) is preserved
> in [`docs/LEGACY-VERSION-HISTORY.md`](LEGACY-VERSION-HISTORY.md).

---

## Version numbering scheme

| Bump | When | Example |
|---|---|---|
| **MAJOR** (`0` → `1`) | Only at production certification. Never before. | `0.99.5` → `1.0.0` |
| **MINOR** (`0.54` → `0.55`) | A completed roadmap part. One minor per part. | `0.54.0` → `0.55.0` |
| **PATCH** (`0.54.0` → `0.54.1`) | A completed task within a part. | `0.54.0` → `0.54.1` → `0.54.2` |

---

## 0.68.1 — Security hardening: SQL injection fix + shared helpers + path/header/ReDoS/logging fixes

- **Triggered by:** GitHub Copilot security scan (Bandit B608 HIGH + pip-audit + Gitleaks).
- **SQL injection (B608 HIGH):** Fixed 2 dynamic `SET` clauses in `server.py` (`update_signup_sheet` + `update_poll`) — column names now filtered through hardcoded `frozenset` whitelist via `safe_set_clause()`; values parameter-bound. No `# nosec B608` suppression retained — the fix is real.
- **Shared helpers:** Created `src/python/core/security_helpers.py` (`safe_set_clause`, `safe_order_by`, `safe_path_under`, `safe_header_value`, `redact`, `redact_mapping`, `escape_html`).
- **Path injection:** Fixed `security_scanner_v54.py::scan_file()` — path containment check.
- **Response splitting:** Fixed 3 dynamic header values — CRLF stripped from `Content-Disposition` filenames + `Location` redirect.
- **Clear-text logging:** Fixed `production_preflight.py` — defensive redaction of messages with sensitive keywords.
- **Bandit MEDIUM suppressions:** Added `# nosec B404` (subprocess import, 2 sites), `# nosec B603` (subprocess calls, 4 sites) with reason comments.
- **Primary files:** `src/python/core/security_helpers.py`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `src/python/production_preflight.py`

---

## 0.68.2 — Phase B: consolidate helpers, replace B110 suppressions with logging, fix B404 placement, verify cryptography pin

- **B1 — Consolidated duplicate SQL helper modules:** Deleted `src/python/core/sql_safety.py` (duplicate of `security_helpers.py`). Updated `server.py` import from `core.sql_safety` to `core.security_helpers`. `security_helpers.py` is the single canonical location.
- **B2 — Removed dead import:** `safe_order_by` was imported but never called (no user-supplied `ORDER BY` columns exist). Removed from import line. Only `safe_set_clause` (which IS used at lines 8163 and 8374) is imported.
- **B3 — Replaced 42 `# nosec B110` suppressions with real logging:** Added module-level `_log = logging.getLogger("einvite.server")` with `StreamHandler`. Every `except OSError:pass` and `except Exception:pass` now reads `except <Type> as exc: _log.debug("cleanup failed: %s", exc)`. Zero `# nosec B110` suppressions remain (down from 42).
- **B4 — Corrected B404 suppression:** `# nosec B404` on `server.py` line 5 IS valid (subprocess IS imported there). Added `# nosec B404` to `security_scanner_v54.py:23` (the other `import subprocess` site) with reason comment.
- **B5 — Verified cryptography pin against PyPI:** `pip index versions cryptography` confirms latest is `50.0.1`. `pip-audit --strict` against `cryptography==44.0.1` reports **7 CVEs** (highest fix version: `50.0.0` for PYSEC-2026-3552). Updated pin from `>=44.0.1,<48` to `>=50.0.0,<51`.
- **B6 — Cleaned up duplicate VERSION_HISTORY entry:** Removed the stale second `0.68.1` entry (at line 110 — claimed `>=43,<48` and `# nosec` comments retained). Kept the accurate first entry.
- **Primary files:** `src/python/core/security_helpers.py`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `docs/requirements-production.txt`, `VERSION_HISTORY.md`
