# Roadmap reconciliation — Parts 3–6 (LT-7.1, 2026-10-27)

Scope: every acceptance bullet in `docs/ROADMAP-v0.54-to-v1.0.md` **Part 3 (§3.6), Part 4 (§4.8),
Part 5 (§5.10) and Part 6 (§6.11)** — 37 bullets — reconciled against what this tree actually does.

Read-only item: **no product file, test, budget or threshold was changed.** Status words, evidence
rule and the "unverified" rule are copied from `docs/CAPABILITY-MATRIX-2026-10-24.md`:

- **exists** — looked at this session (source line, test name, or a one-line live check).
- **partial** — works, but a named sub-part is missing or only works in one path.
- **absent** — no implementation found.
- **unverified** — could not check without a run I did not do.

Branch `fix/2026-10-22-open-issues`, HEAD `f05ee2e` (366 paths uncommitted on top; OD-3 keeps this
local). Written after `docs/ROADMAP-IMPLEMENTATION-REPORT.md` and `docs/STRUCTURE-MAPPING.md` were
read, as the item requires.

## How each row was checked

1. The four acceptance blocks were read from the roadmap (lines 789, 962, 1196, 1483).
2. Every named test was checked for existence and, where cheap, **run**:
   `pytest tests/security_*_test.py tests/analytics_*_test.py tests/admin_tools_test.py
   tests/admin_tools_v2_gap_test.py -q` → **`1 failed, 46 passed in 182.02s`**
   (`artifacts/next-work/lt-7-1/security-analytics-admin.log`).
3. Every code claim is a `path:line` I read this session; every "no caller" claim is a repo-wide
   grep for the symbol, not an assumption.
4. `scripts/check-bilingual-consistency.py` was run for the bilingual bullet: **exit 0**
   (`OK: bilingual consistency check passed.`).

---

## Part 3 — editor depth (§3.6)

| # | Acceptance bullet | Status | Evidence |
|---|---|---|---|
| 3.1 | A new user can create a multi-page invitation with text, images and a background colour without reading docs | exists | Editor rows `exists` in `docs/CAPABILITY-MATRIX-2026-10-24.md` §2 (pages/thumbnails, text objects, image objects, colour picker, autosave); the real create-dialog → editor → publish path is driven every gate run by `tools/csp-violation-check.py` (`[PASS] create dialog opens`, `invitation created and editor loaded`). "Without reading docs" is a usability claim no test measures — see the caveat below the table |
| 3.2 | Dragging near another element shows guides within 6 px | exists | `src/js/editor-pro.js:138` — `const tolerance=6/zoom` in the world-space snap resolver (`snapCandidates` L128, `resolveSnap` L137); guide checks are part of the frozen canvas gate (`22 pass / 0 fail / 2 skipped`) |
| 3.3 | Double-clicking text opens inline editing with a cursor | exists | `dblclick` handlers in `src/js/app.js`, `src/js/canvas-plus.js`; tests drive it: `tests/v0_52_editor_interaction_refinement_browser_test.py:67`, `tests/template_pack_edit_export_test.py:200,217`, `tests/lt_2_5_khmer_input_test.py:231` |
| 3.4 | Layer panel reorders elements with drag-and-drop | exists | `src/js/professional-layers.js` `handleDragStart` / `handleDragOver` (L48) / `handleDrop`; guarded by `tests/layers_panel_guard_test.py` |
| 3.5 | Ctrl+K opens a searchable command palette | exists | `src/js/editor-command-system.js:90` — command `ui.quickActions`, bindings `Mod+K` and `/`, `run: openUI('commands')`; palette UI/search/conflict handling in `src/js/command-palette.js`; `tests/v23_command_system_browser_test.py` |
| 3.6 | Shift+? shows a keyboard shortcut reference | exists | `src/js/editor-command-system.js:91` — `ui.shortcutSettings` bound to `?` and `Shift+?`; the statusbar also ships a `?` button (same file, `bindButtons`) |
| 3.7 | Live cursors from another browser tab are visible and move smoothly | partial | Implemented: `src/js/collaboration-presence.js` renders a remote-cursor overlay on `#v52RemoteCursors` over a dedicated channel, WebSocket when `window.EINVITE_PRESENCE_WS_ENDPOINT` exists with a poll fallback (L97–100). The server-side presence store is tested (`tests/v15_integration_hardening_test.py:97–115` — endpoint wired, in-process fallback de-duplicates and expires stale rows), but **no test drives two clients' cursors in the DOM** and the WebSocket path is opt-in by env — visibility/smoothness is not proven here |
| 3.8 | Comment threads can be created, replied to and resolved | exists | Routes: `GET/POST /api/invitations/<id>/comments` (`src/python/server.py:4090`, `:4410`), resolve (`:4137`), delete (`:4173`); storage with `parent_id` + `resolved_at` and `resolve_comment` in `src/python/features/editor_comments.py`; thread UI (page summary, open/resolved counts, CSV export) in `src/js/collaboration-v24.js:31`; create/delete exercised by `tests/v24_collaboration_tasks_backend_test.py:35,42`. Reply/resolve are source-verified only |
| 3.9 | Version history shows ≥ 5 snapshots after 30 minutes of editing | absent | Version history = **published** snapshots: `get_versions` reads the `publications` table (`src/python/server.py:8282`), so a snapshot exists only when the owner publishes. `src/python/features/invitation_versions.py` (auto-snapshot + 50-cap + prune) is real but **imported by nothing** (`grep -rn invitation_versions src/python` → only its own file), and editor checkpoints are manual and capped at 12 (`src/js/navigation-history.js:64`). No timer produces 5 snapshots in 30 minutes |
| 3.10 | Every string has an EN+KH variant; the bilingual CI check passes | partial | The check passes — `scripts/check-bilingual-consistency.py` exit 0 (`OK: bilingual consistency check passed.`). "Every string" does not hold: studio-chrome groups ship English-only and are queued in `artifacts/next-work/OWNER-QUEUE.md` (colour-picker labels, run-typography group), and the checker carries `KNOWN_FOREIGN_SCRIPT_DAMAGE` rows awaiting owner Khmer |
| 3.11 | Every new file has a test | partial | Part 5/6 backends have real integration tests (`tests/admin_tools_test.py` covers all nine §5 task groups; `tests/analytics_*_test.py`), but the new **page modules** are exercised only indirectly through routes: `src/js/pages/dashboard/analytics.js` (407 lines) has no DOM test, and `src/js/pages/admin/*.js` have no direct test. The bullet as written is not met |

*Caveat on 3.1:* the flows exist and are gate-driven; discoverability by a first-time user was not
measured and no user test exists. Treat `exists` as "the capability is present and exercised", not
as a usability result.

---

## Part 4 — backend security hardening (§4.8)

| # | Acceptance bullet | Status | Evidence |
|---|---|---|---|
| 4.1 | Field-level encryption live for all listed columns | exists | `src/python/core/crypto.py` provides `encrypt_field` / `decrypt_field` / `hash_for_lookup`, but the only consumer is webhook secrets (`src/python/core/webhooks.py:141`) — the listed columns are plain `TEXT`: `users.email` (`src/python/server.py:1527`), `guests.email` / `guests.phone` (`:1553`). No migration, rollback or tests existed before this pass. **Closed 2026-10-28 (LT-7.2 step 4 + fix-up, FB-105):** `core/crypto.py` (Fernet key resolution, env → data-dir sidecar → ephemeral), `core/db.py` read wrapper + `protect()` write helper, `users.email_hash` with the plaintext fallback, `scripts/migrate_encrypt_sensitive_fields.py` (apply / --rollback / --reencrypt / repo-data-dir guard), and **every listed column is now encrypted on the write path too** (guests via create+edit, `delivery_attempts.recipient` via the deliver route, `audit_events.metadata_json` with the new indexed `admin_only` flag replacing the SQL LIKE, `invitation_edit_history.diff_json` via post-send edit). Proof: `tests/security_field_encryption_test.py` (3 tests — live round trip + restart, per-column write-path ciphertext, migration apply/rollback/re-encrypt) → `3 passed` (`artifacts/next-work/lt-7-2/field-encryption.log`). Docs: `docs/security/FIELD-ENCRYPTION.md` (roadmap §7.1). |
| 4.2 | Admin routes require step-up for destructive operations | exists | `require_admin_with_stepup` (`src/python/server.py:5654`) verifies a live `admin-stepup` token issued after password + TOTP (`:5672`), and is used by 5 destructive routes: invitation flag/unpublish/transfer (`:5797`, `:5808`, `:5819`), bulk actions (super-admin, `:5890`), impersonation (super-admin, `:5914`). Other admin mutations (user role/plan/uploads/session-policy, template visibility, settings) used `_admin_gate` only — role + IP allowlist, no step-up. **Closed 2026-10-28 (LT-7.2 step 3, FB-105):** `require_admin_with_stepup` now gates 15 routes (the original 5 plus user role/plan/uploads/session-policy, reset-password, force-mfa, suspend/unsuspend, settings session-idle-days, template visibility); the admin shell can obtain a grant (`src/js/pages/admin/step-up.js` + the `403 step_up_required` retry hook in `admin.js`). Proof: `tests/lt_7_2_admin_stepup_test.py` (`1 passed` — 12 destructive routes refused then replayed), `tests/lt_7_2_admin_stepup_ui_test.py` (`1 passed` — browser flow). |
| 4.3 | Tenant isolation suite passes and runs in CI | exists | `tests/security_tenant_isolation_test.py` (253 lines) — passed in the subset run. CI runs it: `.github/workflows/tests.yml:80` `pytest tests/ -q`, and the workflow states pytest is never wrapped in `continue-on-error` |
| 4.4 | Users can view and revoke their sessions | exists | Routes `GET /api/account/sessions` (`src/python/server.py:3986`), `DELETE /api/account/sessions/<id>` (`:4166`), `POST /api/account/sessions/revoke-all` (`:4287`); UI lists device, IP, last-active with **Revoke / Sign out here / Sign out every other session** (`src/js/account-security.js:12,16,25`) |
| 4.5 | API keys can be generated, scoped and revoked | exists | No `api_keys` table, route or UI existed (`grep -rn "api_key\|apiKey" src/python/server.py` → only `stripe.api_key` at `:5287`). **Closed 2026-10-28 (LT-7.2 step 5, FB-105):** `api_keys` table + `core/auth.py` `generate/hash/verify_api_key` (`einv_` prefix, 32 random bytes), the central `X-API-Key` auth path with a route allowlist (`invitations:read`, `invitations:write`, `rsvps:read`; everything else `403 api_key_scope_denied`), per-key `rate_limit(1000/h)`, `api.request` audit rows with `auth=api_key`, list/create/revoke routes and the account page card (create → show-once → revoke). Proof: `tests/security_api_keys_test.py` (`1 passed`), `tests/lt_7_2_api_keys_ui_test.py` (`1 passed`), `scripts/check-rate-limit-coverage.py` exit 0. |
| 4.6 | Outbound webhooks are signed | exists | `src/python/core/webhooks.py` implements the scheme (`X-EInvite-Signature: t=<ts>,v1=<hex-hmac>`, L11), `sign_webhook` (L57), `build_headers` (L85), `verify_signature` with timestamp tolerance and `hmac.compare_digest` (L95–126), secrets encrypted via `core.crypto`. **Nothing called it** — `grep -rn "core.webhooks\|sign_webhook(\|build_headers(" src/python` found only the module itself; there was no outbound delivery path and no test. (The Stripe route at `:4240` is *inbound* signing by Stripe, the reverse direction.) **Closed 2026-10-28 (LT-7.2 step 6, FB-105):** the delivery path exists — `webhook_endpoints` store (secret through `protect()`), `GET/POST /api/account/webhooks` + rotate/delete, `dispatch_webhook_event()` emitting `rsvp.created`/`rsvp.updated`, and `core/webhooks.deliver()` with a fresh signature per attempt and bounded retries. Proof: `tests/lt_7_2_webhook_signing_test.py` (`2 passed`); docs `docs/hosted/WEBHOOKS.md`. |
| 4.7 | Secrets rotation is documented and scripted | exists | `docs/ops/` holds `BACKUP-DR.md`, `RESTORE-RUNBOOK.md`, `RPO-RTO-TARGETS.md` — no rotation document; `scripts/` had no rotation script (`ls scripts \| grep -iE "secret\|rotat"` → none); `docs/security/ASVS-L2-GAP-ANALYSIS.md` mentions rotation as a gap, which is not the bullet. **Closed 2026-10-28 (LT-7.2 step 7, FB-105):** `docs/ops/SECRETS-ROTATION.md` + `scripts/rotate-secrets.sh` (timestamped env backup, fingerprints not values, `--dry-run`, `--field-encryption` with the `_PREVIOUS` key window, exit 2 when the active key is not in the env file), and the field key gained a rotation path (previous-key decrypt + `--reencrypt`). Proof: `tests/lt_7_2_secrets_rotation_test.py` (`2 passed`). |
| 4.8 | `pytest tests/security_*` all pass | exists | **`1 failed, 46 passed`** on the bullet's own command. Red: `tests/security_mfa_recovery_test.py::test_mfa_recovery_codes` — `KeyError: 'token'` at `:136` (register response had no dev token). Isolated: the file **passes alone** (`1 passed in 16.42s`) and the full `tests/` suite was green at the Phase 6 close (`189 passed`); it fails deterministically when `tests/security_maintenance_test.py` is collected first (reproduced twice: `1 failed, 17 passed` with the six security files, and `1 failed in 1.63s` with just those two). Consistent with module-state coupling: `server` reads `EINVITE_DEV_AUTH_TOKENS` into a module-level flag at import (`src/python/server.py:251`) while `security_maintenance_test.py:10` imports `server` at module level, i.e. before the recovery test's `setdefault` runs. Test-side defect, not a product regression. **Closed 2026-10-28 (LT-7.2 step 9, FB-105):** the collection-order coupling was fixed at the cause (dev-token flag read at call time, DB path resolved per call, schema-ready flag keyed to the path, service singletons re-ensure schema on path change) and the five test files that keyed on the now-encrypted `users.email` now use `email_hash`. Proof: `pytest tests/security_*_test.py tests/analytics_*_test.py tests/admin_tools*_test.py -q` → `47 passed in 195.21s` (`artifacts/next-work/lt-7-2/test-isolation.log`); the bullet's own `pytest tests/security_*` is green in both file orders. |

---

## Part 5 — admin and super-admin tools (§5.10)

| # | Acceptance bullet | Status | Evidence |
|---|---|---|---|
| 5.1 | Admin dashboard shows live metrics and a system status banner | exists | `GET /api/admin/metrics-v2` (`src/python/server.py:4002`) and `/api/admin/system-status` (`:4003`); computed by `features/admin_metrics.py`; UI `src/js/pages/admin/admin.js`; `tests/admin_tools_test.py` §5.1 |
| 5.2 | Users searched, viewed, suspended, impersonated with full audit | exists | `/api/admin/users-v2` (`:3994`) with query filters; role/plan/uploads/session-policy mutations (`:4121`–`:4125`); suspension via bulk job `admin.bulk_suspend` (`:2980`) and the user routes exercised in `tests/admin_tools_test.py` §5.2; impersonation: `POST /api/admin/impersonate/<id>` + stop, signed hand-back cookie (`:2897`–`:2911`), every action inside a session audited (`:3651`), UI `src/js/pages/admin/impersonate.js` |
| 5.3 | Invitations can be browsed and moderated | exists | `/api/admin/invitations-v2` (`:4004`), unpublish/flag/transfer with step-up (`:5797`–`:5819`); UI `src/js/pages/admin/invitations.js`; `tests/admin_tools_test.py` §5.3 |
| 5.4 | Feature flags toggled without a restart | exists | `features/feature_flags.py` + `GET/PUT /api/admin/feature-flags` (`:3998`), public read `GET /api/feature-flags`; UI `src/js/pages/admin/feature-flags.js`; `tests/admin_tools_test.py` §5.4 |
| 5.5 | Audit log searchable and exportable | exists | `/api/admin/audit-events` (`:4005`) with user/action/target/IP/time filters and `format=csv`; UI `src/js/pages/admin/audit-log.js` (EN+KH labels, load-more, expand); `tests/admin_tools_test.py` §5.5 |
| 5.6 | System health page shows every subsystem with actionable hints | exists | `/api/admin/health-detail` (`:4006`, 60 s cache verified in `tests/admin_tools_test.py` §5.6), `features/admin_metrics.py::get_health_detail_cache`; UI `src/js/pages/admin/system-health.js` |
| 5.7 | Bulk operations run as background jobs with progress | exists | `POST /api/admin/bulk-{email,suspend,export,prune}` + `GET /api/admin/jobs/<id>` (`:4008`, `:2980` ff.); UI `src/js/pages/admin/bulk-operations.js`; `tests/admin_tools_test.py` §5.7 |
| 5.8 | Reports queue exists and is actionable | exists | `POST /api/reports` (5/day rate limit), `GET /api/admin/reports` (`:4007`), resolve; `features/reports.py`; UI `src/js/pages/admin/reports.js`; `tests/admin_tools_test.py` §5.9 |
| 5.9 | Every admin route requires the admin role + step-up for destructive actions | exists | Same evidence as 4.2: 5 destructive routes carry step-up, and all admin routes carry role + IP allowlist through `_admin_gate` (`:5488`), but per-user and settings mutations are role-only. "Every … + step-up" was not met. **Closed 2026-10-28 (LT-7.2 step 3, FB-105):** same evidence as 4.2 — every admin route still carries role + IP allowlist through `_admin_gate`, and the destructive mutations now require a live step-up grant the UI can actually obtain. Proof: `tests/lt_7_2_admin_stepup_test.py`, `tests/lt_7_2_admin_stepup_ui_test.py`. |

---

## Part 6 — creator analytics (§6.11)

| # | Acceptance bullet | Status | Evidence |
|---|---|---|---|
| 6.1 | Every listed event fires on the correct user action | exists | `src/js/public/analytics-collector.js:189–200` declares all 11 events (`invitation.view`, `.view.end`, `.gallery.open`, `.rsvp.open`, `.rsvp.submit`, `.rsvp.abandon`, `.link.click`, `.signup.claim`, `.poll.vote`, `.album.upload`, `.gift.claim`); `tests/analytics_ingestion_test.py` (6 tests: happy path, validation, session upsert/close, rate limit, background reconstruction, declarations) — passed |
| 6.2 | Events are batched and sent via `sendBeacon` on unload | exists | `analytics-collector.js:6,9,29,101,127–160` — max 20 events per batch, `navigator.sendBeacon` on unload, failed batches re-queued. The transport is source-verified; the test suite covers the ingestion endpoint, not the unload timing |
| 6.3 | The creator analytics dashboard renders correctly with real data | partial | `src/js/pages/dashboard/analytics.js` (407 lines, EN+KH label maps, Canvas charts) and the reports API is tested (`tests/analytics_reports_test.py`, 7 tests). **No test drives the dashboard DOM** — no test references `ei-analytics` — so rendering with real data is not proven |
| 6.4 | The creations table is sortable, filterable and exportable | partial | Export is real: buttons + `/api/invitations/<id>/analytics/export?format=csv\|json` (`analytics.js:274–303`, `features/analytics/export.py`). The only table in the page is a **static 2-column** referrer table (`analytics.js:198`) and no sort/filter control exists for the creations list (`grep` for `sort`/`filter`/`search` in the dashboard list modules found none) |
| 6.5 | Charts are built with Canvas 2D, no library | exists | `src/js/components/chart.js:88` `canvas.getContext("2d")`, redraw on `ResizeObserver`; pages render `<canvas data-chart="line\|donut">` (`analytics.js:223,334`); no chart library in `package.json` (`grep -n "chart\|echarts\|d3"` → none) |
| 6.6 | Every label is bilingual EN+KH | partial | `analytics.js` carries two label maps with **41 keys each** (counted), including the privacy strings; the repo-wide checker passes. The gap is shared chrome (English-only studio groups queued in `OWNER-QUEUE.md`) and the checker's known-damage list, so "every label" is not true across the product |
| 6.7 | Analytics can be disabled per invitation | exists | `isAnalyticsEnabled()` gates the collector and auto-start (`analytics-collector.js:204`), the flag is surfaced with EN+KH copy (`analytics.js:15,54,97`), and privacy tests cover the off path (`tests/analytics_privacy_test.py`, 7 tests) |
| 6.8 | Retention cleanup runs daily and is logged | exists | `run_retention_prune` exists and is exported (`features/analytics/sessions.py:227`, `features/analytics/__init__.py:62`) but **has no caller** anywhere in `src/python` — nothing schedules it, so it does not run daily and nothing logs a run. **Closed 2026-10-28 (LT-7.2 step 8, FB-105):** the reconciliation row was imprecise — `run_retention_prune` *is* called (last step of `run_session_reconstruction`, which `analytics_reconstruction_loop` runs every 300 s); what was missing was the run log. The loop now prints one `analytics_retention_run` line per pass with reconstruction counts and prune totals. Proof: `tests/lt_7_2_retention_scheduler_test.py` (`1 passed`). |
| 6.9 | The three analytics test files all pass | exists | `tests/analytics_ingestion_test.py`, `tests/analytics_reports_test.py`, `tests/analytics_privacy_test.py` — all passed in the same run (`46 passed`; the only red was the unrelated MFA test) |

---

## Summary

| Part | exists | partial | absent | total |
|---|---|---|---|---|
| 3 — editor depth | 7 | 3 | 1 | 11 |
| 4 — security | 8 | 0 | 0 | 8 |
| 5 — admin tools | 9 | 0 | 0 | 9 |
| 6 — analytics | 6 | 3 | 0 | 9 |
| **Total** | **30** | **6** | **1** | **37** |

*(Re-counted 2026-10-28 after LT-7.2 closed 4.1, 4.2, 4.5, 4.6, 4.7, 4.8, 5.9 and 6.8 — see
"LT-7.2 closures" below. Rows updated in place above; the original 22/10/5 counts are kept in the
LT-7.1 ledger line of `artifacts/ui-audit/fixes/STATE.md`.)*

## LT-7.2 closures (2026-10-28, FB-105, uncommitted)

Executed in the risk order the earlier "What this means for LT-7.2" section set, plus the item's own
step 9 (test isolation). Each step's full writeup, gates and evidence is in
`artifacts/next-work/lt-7-2/NOTES.md`:

| Plan step | Roadmap row | What closed it | Proof |
|---|---|---|---|
| step 3 | 4.2 / 5.9 | step-up on 15 destructive admin routes + the UI grant/retry path | `lt_7_2_admin_stepup_test.py`, `…_ui_test.py` |
| step 4 (+ fix-up) | 4.1 | encryption code, migration/rollback, and **write-path** encryption for all six listed columns | `security_field_encryption_test.py` (3 tests) |
| step 5 | 4.5 | `api_keys` + scoped `X-API-Key` auth + per-key limit + audit + account card | `security_api_keys_test.py`, `lt_7_2_api_keys_ui_test.py` |
| step 6 | 4.6 | webhook delivery path, retries, rotation, docs | `lt_7_2_webhook_signing_test.py` |
| step 7 | 4.7 | rotation doc + script, previous-key window, `--reencrypt` | `lt_7_2_secrets_rotation_test.py` |
| step 8 | 6.8 | one `analytics_retention_run` log line per prune pass | `lt_7_2_retention_scheduler_test.py` |
| step 9 | 4.8 | collection-order coupling fixed at the cause; `security_*` command green | `artifacts/next-work/lt-7-2/test-isolation.log` |

**Per-Part verdict for LT-7.close:** Part 4 and Part 5 have no `partial`/`absent` row left → **minor**
bump for each; Parts 3 and 6 still carry partial/absent rows (3.7, 3.9, 3.10, 3.11, 6.3, 6.4, 6.6)
→ those Parts stay **patch**. `VERSION_HISTORY.md` is owner-held under OD-3, so the entries are
requested in `artifacts/next-work/OWNER-QUEUE.md` rather than written.

## What this means for LT-7.2

The plan's LT-7.2 risk order was written before this reconciliation and assumed several rows were
missing. The evidence says otherwise for the first three steps — this table **replaces** that list:

1. ~~Tenant isolation suite~~ — **already exists and passes** (`tests/security_tenant_isolation_test.py`,
   CI-covered). No work.
2. ~~Session management UI + routes~~ — **already exists** (`/api/account/sessions*`,
   `src/js/account-security.js`). No work.
3. **Step-up coverage** (4.2 / 5.9, partial): extend `require_admin_with_stepup` to the remaining
   destructive admin mutations (user role/plan/uploads/session-policy, template visibility,
   settings) and test each. The IP-allowlist env already exists and is tested.
4. **Field-level encryption** (4.1, absent): `core/crypto.py` is the building block; needs the
   schema migration, rollback and tests on a temp database — never against `data/`.
5. **API keys** (4.5, absent): table, scoped tokens, per-key rate limit, revoke UI/routes, tests.
6. **Webhook signing wiring** (4.6, partial): `core/webhooks.py` is complete but unused — a delivery
   path, retry/backoff and a signature test are what is missing.
7. **Secrets rotation** (4.7, absent): one doc under `docs/ops/` plus a script, smoke-tested.
8. **Analytics retention scheduler** (6.8, absent): call `run_retention_prune` from the existing
   job loop and log each run.
9. **Test-isolation defect** (4.8): fix the `security_*` collection-order coupling so the bullet's
   own command is green (either import `server` lazily in the maintenance test, or stop caching the
   dev-token flag at import).
10. **Also already satisfied** from the plan's original LT-7.2 list: analytics privacy controls and
    export (disable / re-enable / purge / non-host 403 are tested in `tests/analytics_privacy_test.py`,
    with EN+KH purge strings in `analytics.js:48,65` and CSV/JSON export buttons). No work.
11. Lower-value gaps found but outside the plan's LT-7.2 list — recorded here, not scheduled:
    automatic version snapshots (3.9), two-client cursor proof (3.7), composite sort/filter on the
    creations table (6.4), a dashboard render test for analytics (6.3), and DOM tests for the new
    page modules (3.11).

**No owner question. No product edit. No FB number consumed (read-only).**

## Reproduction

```
.venv/bin/python -m pytest tests/security_*_test.py tests/analytics_*_test.py \
    tests/admin_tools_test.py tests/admin_tools_v2_gap_test.py -q
# -> 1 failed, 46 passed in 182.02s   (artifacts/next-work/lt-7-1/security-analytics-admin.log)

.venv/bin/python -m pytest tests/security_mfa_recovery_test.py -q
# -> 1 passed in 16.42s              (same file alone)

.venv/bin/python -m pytest tests/security_maintenance_test.py tests/security_mfa_recovery_test.py -q
# -> 1 failed in 1.63s               (interference reproduced)

.venv/bin/python scripts/check-bilingual-consistency.py
# -> OK: bilingual consistency check passed.  (exit 0)
```
