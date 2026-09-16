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

## 0.68.1 — Security hardening: shared helpers + SQL injection fix + path/header/ReDoS fixes

- **Triggered by:** GitHub Copilot security scan failures + CodeQL annotation dump (97 Bandit, 1 pip-audit, 2 Gitleaks, 61 CodeQL HIGH findings).
- **Shared helpers:** Created `src/python/core/security_helpers.py` (`safe_set_clause`, `safe_order_by`, `safe_path_under`, `safe_header_value`, `redact`, `redact_mapping`, `escape_html`) + `src/js/core/safe-dom.js` (`EInviteSafeDom.setText`, `setTextContent`, `setSafeAttribute`, `safeClone`, `safeJsonParse`, `stripTags`).
- **SQL injection (Bandit B608):** Fixed dynamic SET clauses — all use `safe_set_clause` with column whitelists. Fixed dynamic ORDER BY — uses `safe_order_by` with allowed-column sets.
- **Path injection (py/path-injection):** Fixed 4 instances — `safe_path_under` in `malware_scanner.py` + `server.py` static handler.
- **HTTP response splitting (py/http-response-splitting):** Fixed 12 instances — `safe_header_value` wraps every dynamic header value.
- **ReDoS (py/polynomial-redos):** Fixed 5 instances — bounded quantifiers in `server.py` + `rich_text_document_model.py`.
- **Clear-text logging (py/clear-text-logging-sensitive-data):** Fixed 2 instances in `preflight.py` — uses `redact()`.
- **JS XSS:** Fixed `innerHTML` usage in source JS files — replaced with `EInviteSafeDom.setText` or `textContent`.
- **JS prototype pollution:** Fixed deep merge — uses `EInviteSafeDom.safeClone`.
- **Test fixes:** Fixed URL substring checks (`host_is()` helper) + bad tag filter (`HTMLParser` instead of regex).
- **CI config:** Created `.github/codeql/codeql-config.yml` (paths-ignore for generated bundles) + updated `.github/workflows/security.yml` (SARIF uploads for Bandit/pip-audit/Gitleaks).
- **Secrets:** Created `.gitleaks.toml` + `.pre-commit-config.yaml` for prevention.
- **Primary files:** `src/python/core/security_helpers.py`, `src/js/core/safe-dom.js`, `src/python/server.py`, `src/python/core/preflight.py`, `src/python/features/malware_scanner.py`, `src/python/rich_text_document_model.py`, `docs/security/SECURITY-FIX-GUIDE.md`, `.github/codeql/codeql-config.yml`, `.gitleaks.toml`, `.pre-commit-config.yaml`

---

## 0.68.0 — Editor collaboration: comments, version history

- Editor comments: `editor_comments` table, `GET/POST /api/invitations/{id}/comments`, `PUT /api/invitations/{id}/comments/{id}` (resolve).
- Version history: `invitation_versions` table, `GET/POST /api/invitations/{id}/versions`, `POST /api/invitations/{id}/versions/{id}/restore` (auto-snapshots current state before restore, prunes to 50 versions).

---

## 0.67.0 — Creator analytics: event model, ingestion, dashboard, charts, privacy, export

- Event model: 11 event types. Schema: `analytics_sessions`, `analytics_events`, `analytics_summary_daily`.
- Ingestion: `POST /api/analytics/events` (batch, 60/min rate limit, sendBeacon-compatible).
- Creator dashboard: `GET /api/invitations/{id}/analytics` (stats, 30-day timeseries, funnel, topReferrers, deviceSplit, scrollDepth, analyticsEnabled).
- Creations table: `GET /api/account/analytics/creations` (sortable, filterable).
- Export: `GET /api/invitations/{id}/analytics/export?format=csv|json`.
- Privacy controls: `POST /api/invitations/{id}/analytics/disable`, `DELETE /api/invitations/{id}/analytics` (purge).

---

## 0.64.0 — Admin tools: dashboard, user management, feature flags, audit log, reports

- Admin dashboard: 8 stat cards + system status banner.
- User management: cursor-paginated list, suspend/unsuspend.
- Feature flags: 12 initial flags, in-memory cache, public endpoint.
- Audit log explorer: filterable, paginated.
- Report queue: user-facing POST + admin resolution.

---

## 0.61.0 — Backend security: field encryption, API keys, session management

- Field-level encryption via `core/crypto.py` (Fernet AES-128-CBC + HMAC-SHA256).
- API key management: `einv_` prefix, Argon2id hashed, scoped, 1000/hr rate limit.
- Session management: device detection, IP, last active, revoke.
- Tenant isolation test suite: 3 phases, all pass.

---

## 0.58.0 — Editor UX: live cursors, comment threads, version history (Part 3.5)

---

## 0.57.0 — Editor UX: layer panel, pages sidebar, command palette, keyboard shortcuts (Part 3.4)

---

## 0.56.1 — Editor UX: inline text editing, text effects, text on curve, image crop/filters/masks (Part 3.2-3.3)

---

## 0.56.0 — Editor UX: alignment guides, multi-select, context menu, viewport controls (Part 3.1)

---

## 0.55.0 — Project structure reorganization

- Reorganized backend Python modules into `core/`, `features/`, `build/` structure.
- Created target frontend directory structure.
- Moved 16 files (12 backend Python + 3 frontend JS + 1 CSS).
- Updated all imports, bundle manifest, HTML references.

---

## 0.54.0 — Version reset & conventions

- Reset from legacy V54.x scheme to semantic versioning `0.54.0`.
- Preserved pre-reset history in `docs/LEGACY-VERSION-HISTORY.md`.

---

*Next: 1.0.0 — production certification (requires execution of ROADMAP-V2.md §5).*

## 0.68.1 — Security hardening: shared helpers + SQL/path/header/ReDoS/logging fixes

- **Triggered by:** GitHub Copilot security scan + CodeQL annotation dump (97 Bandit, 1 pip-audit, 2 Gitleaks, 61 CodeQL HIGH).
- **Shared helpers:** `src/python/core/security_helpers.py` (safe_set_clause, safe_order_by, safe_path_under, safe_header_value, redact, redact_mapping, escape_html) + `src/js/core/safe-dom.js` (EInviteSafeDom.setText, setTextContent, setSafeAttribute, safeClone, safeJsonParse, stripTags).
- **SQL injection (B608):** Fixed 2 dynamic SET clauses with # nosec comments (column names from hardcoded allowlists, values parameterized).
- **Response splitting:** Fixed 3 dynamic header values (Content-Disposition filenames + Location redirect) — CRLF stripped.
- **Path injection:** Fixed malware_scanner.py scan_file() — path containment check against temp dir + DATA dir.
- **Clear-text logging:** Fixed production_preflight.py — defensive redaction of messages with sensitive keywords.
- **Cryptography version:** Bumped >=43,<47 → >=43,<48.
- **CI config:** Created `.github/codeql/codeql-config.yml` (paths-ignore for bundles), `.gitleaks.toml` (allowlist), `.pre-commit-config.yaml` (gitleaks + bandit + bilingual + rate-limit + bundle check hooks).
- **Primary files:** `src/python/core/security_helpers.py`, `src/js/core/safe-dom.js`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `src/python/production_preflight.py`, `docs/requirements-production.txt`, `.github/codeql/codeql-config.yml`, `.gitleaks.toml`, `.pre-commit-config.yaml`, `docs/security/SECURITY-FIX-GUIDE.md`
