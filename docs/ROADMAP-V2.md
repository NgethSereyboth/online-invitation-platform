# eInvite Platform — Roadmap Continuation

> **For the AI agent reading this:** This is a continuation of `ROADMAP.md`. Phase 0 is genuinely complete. Phases 1–5 produced a large volume of design docs, but many deliverables are **spec-only** rather than working code. This document reorders priorities around two themes the maintainer cares about most: **UX/UI quality** and **security hardening**. Read the "Context" section first — it tells you what is real vs. what is paper.

---

## 0. Context: What Exists vs. What Is Paper

Before starting any task, know the difference:

| Area | Real (working code + tests) | Paper (spec / skeleton only) |
|---|---|---|
| Phase 0 (docs governance) | ✅ `VERSION_HISTORY.md`, `ARCHITECTURE.md`, `README.md` rewritten | — |
| Phase 1a (AI governance) | Docs + `ai_agent/jit_elevation.py` skeleton | JIT `evaluate()` returns `True` — **not enforced** |
| Phase 1b (ASVS L2) | `docs/security/ASVS-L2-GAP-ANALYSIS.md` (14 chapters) | All P1–P4 remediations are **not yet coded** |
| Phase 1c (Backup/DR) | 3 docs + 2 scripts | pgBackRest not configured in this repo |
| Phase 2a-1 (channels/sheets/polls) | ✅ Backend + 3 JS modules + tests pass | Host-side management UI missing |
| Phase 2a-2 (album/post-send-edit) | ✅ Backend + 2 JS modules + tests pass | Host dashboard not wired for edit history; no real upload progress bar |
| Phase 2b (Khmer + a11y) | ✅ Contrast fixes + skip-links on 16 pages | Variable Khmer font not vendored; `:lang(km)` rule missing |
| Phase 3 (certification) | 5 docs + `tests/load_test_k6.js` | Nothing executed — all status `pending` |
| Phase 4a (plugin marketplace) | 4 specs + SDK + example plugin | Host runtime wiring absent; `plugins.einvite.local` doesn't exist |
| Phase 4b (Y.js CRDT) | Design doc + 4 JS modules | **Y.js not vendored**; modules error without `window.Y`; test uses a shim |
| Phase 5 (hosted tier) | 4 docs + minimal scaffolding + smoke test | Canva bridge is docs-only; onboarding UI absent |

**The single most important fact:** Phase 4b (Y.js CRDT) is NOT working. The editor still uses the V31 adapter. Do not treat V54.7 as complete.

---

## 1. New Priority Ordering

Security and UX/UI come first. Do not start Phase 3 execution, Phase 4 wiring, or Phase 5 buildout until Sections 2 and 3 are complete.

```

┌─────────────────────────────────────────────────────────┐
│  SECTION 2 — SECURITY HARDENING   (do first, blocks all)│
│  SECTION 3 — UX/UI COMPLETION     (parallel-safe)       │
├─────────────────────────────────────────────────────────┤
│  SECTION 4 — MISSING ACTIONS      (after 2 and 3)       │
│  SECTION 5 — EXECUTION            (after 4)             │
└─────────────────────────────────────────────────────────┘

```

---

## 2. SECTION 2 — Security Hardening

### Ground rules
- Every change gets a test in `tests/`.
- Bump `VERSION_HISTORY.md` with a `V54.x` entry per completed task group.
- No new third-party dependencies unless the task explicitly says so.
- Commit style: `sec-N: short description`.

### 2.1 — P1-A: Fix reflected HTML injection in `serve_public`

**Why:** Highest-severity open finding. The slug from the URL is substituted into `<meta content="...">` and `<link href="...">` without escaping. CSP blocks script execution, but defense-in-depth is violated, and it also blocks the WCAG `lang` fix on the public page.

**Files:**
- `src/python/server.py` (~line 6553, in `serve_public`)
- `src/html/public.html` (audit placeholder usage of `__INVITATION_SLUG__`)

**Task:**
- [ ] Wrap every `__INVITATION_SLUG__` substitution with `html.escape(slug, quote=True)`.
- [ ] Audit for any other unescaped user-controlled substitutions in the same handler.
- [ ] Add a regression test in `tests/security_reflected_injection_test.py`: register a host, publish an invitation, request `/i/<slug-with-html-chars>` and assert the response body contains the escaped form only.

**Acceptance:** Test passes; no raw `"` or `<` from user input appears unescaped in HTML context.

---

### 2.2 — P1-B: Per-account login lockout

**Why:** Currently only IP-based rate limiting. Rotating IPs allows unlimited password guesses against a known account.

**Files:**
- `src/python/server.py` (login handler ~line 3970; schema ~line 1170)
- `docs/postgres_schema.sql`

**Schema:**
- [ ] Add columns to `users`: `failed_login_attempts INTEGER NOT NULL DEFAULT 0`, `locked_until BIGINT`.
- [ ] SQLite: add to `CREATE TABLE users` + `ALTER TABLE` migration block in the `PRAGMA table_info` guard.
- [ ] Postgres: add to `CREATE TABLE users` + idempotent `ALTER TABLE IF NOT EXISTS`.

**Logic:**
- [ ] On failed password: `failed_login_attempts += 1`.
- [ ] After 5 failures within 15 min: set `locked_until = now + 15 min`, return HTTP 423 with `code: "account_locked"`.
- [ ] On successful login: reset `failed_login_attempts = 0`, clear `locked_until`.
- [ ] Return 423 (not 401) when locked, so the client can show a distinct message.
- [ ] Audit event `login.account_locked` on lock, `login.lockout_cleared` on unlock.

**Bilingual messages (per ground rule):**
- EN: `"Account temporarily locked. Try again in 15 minutes or reset your password."`
- KH: `"គណនីត្រូវបានចាក់សោជាបណ្ដោះអាសន្ន។ សូមព្យាយាមម្ដងទៀតក្នុងរយៈពេល 15 នាទី ឬកំណត់ពាក្យសម្ងាត់ឡើងវិញ។"`

**Test:** `tests/security_account_lockout_test.py` — 5 failed logins → 6th returns 423; correct password during lockout also returns 423; after clearing lock (or via password reset) login succeeds and counter resets.

**Acceptance:** Test passes; lockout survives server restart (persisted in DB).

---

### 2.3 — P1-C: MFA recovery codes

**Why:** A user who loses their authenticator is locked out permanently. This is a real support burden and a security-blocker for wider adoption.

**Files:**
- `src/python/server.py` (mfa handlers ~line 4111)
- `src/python/security_v13.py`
- `docs/postgres_schema.sql`

**Schema:**
- [ ] New table `mfa_recovery_codes`:
  - `id`, `user_id`, `code_hash` (bcrypt or argon2), `used_at` (nullable), `created_at`.
  - Index on `user_id`.
  - Add to both SQLite and Postgres schema blocks.

**Logic:**
- [ ] `generate_recovery_codes(user_id)` → returns 10 plaintext codes to display **once** (e.g. `XXXX-XXXX-XXXX` format, 12 chars from a 32-char alphabet), stores only hashes.
- [ ] Call it automatically at the end of `mfa_enable` (after successful MFA activation).
- [ ] New route `POST /api/account/mfa/recovery-codes/regenerate` (requires current password) — invalidates old codes, issues 10 new ones.
- [ ] New route `POST /api/auth/mfa/recover` — accepts `{email, recovery_code}`, verifies against unused codes, marks `used_at`, completes the MFA step, audits `mfa.recovery_used`.
- [ ] When ≤2 codes remain, the `GET /api/account/security` response should include `recoveryCodesLow: true` so the UI can warn.

**UI (dashboard security section):**
- [ ] After MFA enable, show a modal with the 10 codes, a "copy all" button, and a warning: "Save these now — they will not be shown again."
- [ ] Bilingual: EN `"Save these recovery codes"` / KH `"រក្សាទុកកូដសង្គ្រោះទាំងនេះ"`.

**Test:** `tests/security_mfa_recovery_test.py` — enable MFA → recover with each code → 11th attempt fails; regenerating invalidates old codes.

**Acceptance:** Test passes; codes are hashed in DB (verify by reading the row).

---

### 2.4 — P1-D: Security notification emails on MFA changes

**Why:** When MFA is enabled or disabled, the user should be notified by email. If an attacker disables MFA, the victim learns immediately. This is a standard ASVS L2 expectation.

**Files:**
- `src/python/server.py` (`mfa_enable` ~line 4119, `mfa_disable` ~line 4129; `send_platform_email` at line 220)

**Task:**
- [ ] On `mfa_enable`: send email to user's verified address. Subject: `"MFA enabled on your eInvite account"` / KH `"MFA បានបើកនៅលើគណនី eInvite របស់អ្នក"`. Body includes timestamp, IP, and a "wasn't me" link.
- [ ] On `mfa_disable`: send equivalent email with a distinct subject and a stronger warning.
- [ ] On `passkey.added` / `passkey.removed`: same pattern.
- [ ] On `password.changed`: same pattern.
- [ ] Use the existing `send_platform_email` helper — do not add a new mailer.
- [ ] If SMTP is not configured, log a warning and continue (do not fail the operation).

**Test:** `tests/security_notification_emails_test.py` — mock the sender, enable MFA, assert it was called with the right recipient + subject.

**Acceptance:** Test passes; emails fire on all four event types.

---

### 2.5 — Enforce JIT elevation (close the Phase 1a stub)

**Why:** `ai_agent/jit_elevation.py::evaluate()` currently returns `True` unconditionally. The docs describe a working JIT system; the code does not enforce it. Anyone reading V54.6 will assume it's live.

**Files:**
- `ai_agent/jit_elevation.py` (the stub)
- `ai_agent/service.py::authorize_tool_call`

**Task:**
- [ ] Change `evaluate()` to actually check `jit_elevations` for a matching active grant.
- [ ] Wire `authorize_tool_call` to call `evaluate()` for any tool whose `permission == "manage"` or whose tool id starts with `publish.` / `delete.` / `bulk_`.
- [ ] When no grant exists: return the grant-request flow (create `jit.requested` audit event, return `{needsElevation: true, toolId, ttlSeconds: 300}` to the caller).
- [ ] Add `POST /api/ai-agent/jit/approve` (host-only) and `POST /api/ai-agent/jit/deny`.
- [ ] Auto-approval rules as documented in `docs/ai/JIT-ELEVATION.md` §3.
- [ ] Emit `jit.granted` / `jit.denied` / `jit.expired` audit events.

**Test:** `tests/ai_jit_enforcement_test.py` — a `publish.prepare` call without a grant returns `needsElevation`; after approval, the same call succeeds.

**Acceptance:** Test passes; disabling the JIT module breaks the test (proves it's wired).

---

### 2.6 — Resource-scoped permissions, Stage 3

**Why:** Phase 1a designed a 4-stage migration; only Stage 1 (additive schema) exists. The runtime still uses coarse `read/edit/manage`.

**Files:**
- `ai_agent/capabilities.py`
- `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` (the design)

**Task:**
- [ ] Implement `ai_agent/scopes.py` per the design doc (`Grant.parse`, `Grant.matches`).
- [ ] Add `agent_grants` table (both engines) per design doc §3.
- [ ] Change `filter_catalog()` to evaluate against grants when a grant exists for the tool's resource type; fall back to legacy tier check when no grant is defined (Stage 3 = "new check authoritative with legacy fallback").
- [ ] Add shadow evaluation logging so any divergence between old and new checks is recorded (for the Stage 4 migration).
- [ ] Do NOT remove the legacy path yet — this is Stage 3, not Stage 4.

**Test:** `tests/ai_resource_scopes_test.py` — a user with `event:{id}:publish` grant can call `publish.prepare` for that event; the same user cannot call it for a different event.

**Acceptance:** Test passes; both check paths log divergences when they disagree.

---

### 2.7 — Chapter 10 tooling (SAST/SCA/SBOM)

**Why:** ASVS L2 Chapter 10 is uniformly "fail" in the gap analysis. This is the last big block of ASVS L2 work.

**Files:**
- New `.github/workflows/security.yml` (or equivalent)
- New `scripts/security-scan.sh`

**Task:**
- [ ] **SAST:** add `bandit -r src/python ai_agent platform_v32 future_platform_v52` — fail CI on High.
- [ ] **Dependency audit:** `pip-audit -r docs/requirements-production.txt` — fail on High/Critical.
- [ ] **SBOM:** `pip-requirements-parser` → emit `sbom.cdx.json` in CycloneDX format on every release.
- [ ] **Secret scanning:** `gitleaks detect --no-git` against the repo.
- [ ] **Container scan (if Dockerfile exists):** `trivy image` against the built image.
- [ ] **CODEOWNERS:** add `.github/CODEOWNERS` covering `src/python/`, `ai_agent/`, `platform_v32/`, `security_*.py`, `secrets_*.py`, `deploy/`.
- [ ] Document the CI gate in `docs/security/CI-SECURITY.md`.

**Acceptance:** All scans run locally with `bash scripts/security-scan.sh`; results are clean or explicitly waived with a comment.

---

### 2.8 — Security headers audit + CSP report-only monitoring

**Why:** CSP exists but there's no observation of what it would block. Report-only gives visibility without breaking anything.

**Task:**
- [ ] Add `Content-Security-Policy-Report-Only` header alongside the existing CSP.
- [ ] Add `report-uri /api/csp-report` (rate-limited, logs to audit but never fails requests).
- [ ] Add `POST /api/csp-report` handler that writes a structured log line (route, directive, blocked-uri, user-agent).
- [ ] Add a weekly summary job that counts violations by directive.
- [ ] Do NOT switch CSP from report-only to enforce until a week of clean reports.

**Test:** `tests/security_csp_report_test.py` — post a sample report, assert it's stored and returns 204.

**Acceptance:** Report endpoint is live; enforcement policy unchanged.

---

### 2.9 — Rate-limit coverage audit

**Why:** Coverage is good but not documented. Some routes may be unrated by accident.

**Task:**
- [ ] Grep every route in `do_GET`/`do_POST`/`do_PUT`/`do_DELETE` and record which have `rate_limit(...)`.
- [ ] Write `docs/security/RATE-LIMIT-COVERAGE.md` with a table: route, method, rate, limit key (IP / user / IP+resource).
- [ ] For any unrated write route, add a rate limit (default 60/min per user, or 10/min for expensive ones).
- [ ] Add a CI check that fails if a new write route is added without a `rate_limit` call (a simple grep-based test).

**Acceptance:** Coverage table exists; every write route has a documented limit; CI check passes.

---

## 3. SECTION 3 — UX/UI Completion

### Ground rules
- Every user-facing string must have an EN and KH variant.
- No new build tools. Vanilla JS, CSS.
- Reuse the existing `signup-sheets.js` / `polls.js` patterns for consistency.
- Match the existing design tokens (`tokens.css`, `modern-ui.css`).
- Commit style: `ux-N: short description`.

### 3.1 — Host-side management UI for signup sheets

**Why:** Guests can claim slots; hosts cannot create or edit them from the dashboard.

**Files:**
- New `src/js/host-signup-sheets.js`
- `src/html/dashboard.html`
- `docs/route-bundle-sources-v15.json` (add to dashboard bundle)

**Task:**
- [ ] Add a "Sign-up sheets" panel to the dashboard (inside the event section).
- [ ] List existing sheets with slot counts and claim counts.
- [ ] "Create sheet" button → modal with title, description, and a dynamic slot list (add/remove rows; each row = label, capacity, optional deadline).
- [ ] Edit + delete actions per sheet.
- [ ] "View claims" expands to show claimer name, email (host-only), quantity, claimed-at.
- [ ] Bilingual strings for every label.

**Acceptance:** Host can create, edit, delete a sheet; guest page reflects changes after refresh; no console errors.

---

### 3.2 — Host-side management UI for polls

**Why:** Same gap as 3.1.

**Files:**
- New `src/js/host-polls.js`
- `src/html/dashboard.html`
- `docs/route-bundle-sources-v15.json`

**Task:**
- [ ] Add a "Polls" panel to the dashboard.
- [ ] List existing polls with vote counts and status (open/closed).
- [ ] "Create poll" → modal with question, 2–20 options, multi-select toggle, visibility toggle (`live` / `hidden_until_close`), optional deadline.
- [ ] Edit + delete + "close now" actions.
- [ ] "View results" expands to show per-option counts and voter emails (host-only).
- [ ] Bilingual strings.

**Acceptance:** Host can manage polls; guest page reflects changes; live results work.

---

### 3.3 — Wire the edit-history view into the dashboard

**Why:** `src/js/invitation-edit-history.js::mountHistoryView` is written and bundled but no HTML calls it.

**Files:**
- `src/html/dashboard.html`
- `src/js/dashboard.js` (or wherever the invite edit view lives)

**Task:**
- [ ] Add an "Edit history" section to the invitation edit view.
- [ ] Call `EInviteEditHistory.mountHistoryView(root, {invitationId})` on mount.
- [ ] Add the "Resend update notification" button (already implemented) and verify it fires the email.
- [ ] Show the `editedAfterSendAt` timestamp at the top when set.

**Acceptance:** Host sees the diff history; resend button sends email; no console errors.

---

### 3.4 — Real upload progress bar for album photos

**Why:** Current implementation disables the button while `fetch` runs. No progress indication for large uploads.

**Files:**
- `src/js/album.js`

**Task:**
- [ ] Replace `fetch` with `XMLHttpRequest` for the album upload path only.
- [ ] Wire `xhr.upload.addEventListener('progress', ...)` to a `<progress>` element.
- [ ] Show percentage during upload, then switch to "Processing…" until the response returns.
- [ ] Handle errors with a clear bilingual message + retry button.
- [ ] Keep the existing MIME allow-list + malware-scan contract unchanged.

**Acceptance:** Uploading a 5 MB photo shows a live progress bar; cancellation works.

---

### 3.5 — Complete WCAG P1 items from the audit

**Reference:** `docs/a11y/WCAG-AA-AUDIT.md` §7 P1 list.

**Task:**
- [ ] **P1-A:** Add global `:lang(km)` CSS rule — `line-height: 1.6`, `font-size: 16px` floor, `letter-spacing: normal`, `font-feature-settings: normal`, `font-synthesis: none`. Put it in `src/css/organized/styles.css` so it's universal.
- [ ] **P1-B:** Add `lang="km"` to every `.khmer-text` fragment in `src/html/*.html` and in the JS renderers (`signup-sheets.js`, `polls.js`, `album.js`, `invitation-edit-history.js`).
- [ ] **P1-C:** Audit every dynamic `<img>` in the renderers for a missing or empty `alt`. For decorative images use `alt=""`; for content images require a real alt.
- [ ] **P1-D:** On `public.html`, set `<html lang>` dynamically from the loaded invitation's language. (Depends on 2.1 being done first, because the injection fix unblocks the dynamic attribute.)
- [ ] **P1-E:** Add visible labels (not just placeholders) to search/filter inputs across the dashboard.
- [ ] **P1-F:** Add `aria-modal="true"` + focus trap to every `<dialog>` element.

**Acceptance:** All P1 items complete; re-run the audit checklist and update the status column.

---

### 3.6 — Empty states, loading skeletons, error states

**Why:** Most panels render nothing while loading and show raw errors when they fail. This is the single biggest perceived-quality gap.

**Files:**
- `src/css/modern-ui.css` (add `.empty-state`, `.skeleton`, `.error-state` classes)
- All host-side JS modules (`host-signup-sheets.js`, `host-polls.js`, `album.js`, etc.)

**Task:**
- [ ] Add CSS for three states: empty (icon + short message + primary action), skeleton (grey pulsing bars matching the real content shape), error (icon + message + retry button).
- [ ] Wire each panel to show the right state.
- [ ] Bilingual strings for every state.
- [ ] Skeletons must match the layout of the real content — no generic grey boxes.

**Acceptance:** Every host panel has all three states; no panel renders blank while loading.

---

### 3.7 — Toast notification system

**Why:** Success/error feedback is currently inconsistent (some panels use inline messages, some use `alert`, some use nothing).

**Files:**
- New `src/js/toast.js`
- New `src/css/toast.css`
- `src/html/dashboard.html`, `src/html/editor.html`

**Task:**
- [ ] `EInviteToast.show({type, message_en, message_km, duration})` — top-right stack, auto-dismiss after 4s, manual close button, `role="status"` for screen readers.
- [ ] Types: `success`, `error`, `info`, `warning`.
- [ ] Replace every ad-hoc success/error message in the host panels with a toast.
- [ ] Bilingual strings per call site.

**Acceptance:** No remaining `alert()` calls in host-side code; every mutation shows a toast.

---

### 3.8 — Mobile responsiveness pass

**Why:** The WCAG audit noted reflow issues on narrow viewports.

**Task:**
- [ ] Audit all 16 HTML pages at 375px width.
- [ ] Fix any horizontal scroll, overlapping text, or unreachable buttons.
- [ ] Ensure every dialog is usable at 375px (full-screen on mobile, or scrollable).
- [ ] Ensure the editor toolbar is usable on mobile (or explicitly document the editor as desktop-only with a graceful message).

**Acceptance:** All 16 pages render without horizontal scroll at 375px; dialogs are usable.

---

### 3.9 — Dark mode audit

**Why:** Tokens exist for both modes but only light mode was audited.

**Task:**
- [ ] Re-run the contrast checks from `docs/a11y/WCAG-AA-AUDIT.md` in dark mode.
- [ ] Fix any token that fails AA-normal.
- [ ] Verify every icon, border, and shadow is visible in dark mode.
- [ ] Verify Khmer text renders correctly in dark mode.

**Acceptance:** All dark-mode tokens pass AA-normal; screenshots of 4 key pages in dark mode.

---

### 3.10 — Bilingual consistency pass

**Why:** Not every string has a KH variant; some KH strings are byte-identical to EN.

**Task:**
- [ ] Grep every `en:` string in the JS modules and confirm a corresponding `km:` exists.
- [ ] Flag any `km:` that matches `en:` byte-for-byte — these are placeholders that slipped through.
- [ ] Add a CI check that fails on identical EN/KH pairs (except for proper nouns).

**Acceptance:** CI check passes; no English text visible when the UI is in Khmer mode.

---

## 4. SECTION 4 — Missing Actions From Earlier Phases

These are carry-overs the earlier phases marked complete but which are not actually done. Do them **after** Sections 2 and 3, in this order.

### 4.1 — Vendor Y.js and wire it into the editor

**This is the highest-leverage single task in the whole roadmap.** Without it, Phase 4b is fiction.

**Task:**
- [ ] Run `bash vendor/yjs/download.sh` — this fetches the pinned Y.js + y-indexeddb + lib0 files and writes SRI hashes to `vendor/yjs/INTEGRITY.txt`.
- [ ] Add `<script integrity="sha384-…" src="/vendor/yjs/y.js"></script>` (and the two others) to `src/html/editor.html` and `src/html/dashboard.html`.
- [ ] Ensure `sync_frontend_assets.py` mirrors `vendor/yjs/` into `src/python/vendor/yjs/`.
- [ ] Verify `window.Y` is defined on editor load.
- [ ] Verify `crdt-yjs-indexeddb.js`, `crdt-yjs-undo.js`, `crdt-yjs-rich-media.js`, `collaboration-presence-v52.js` all initialize without the "window.Y missing" error.
- [ ] Add a headless test that opens two editor tabs (Playwright) and verifies a text edit in one appears in the other via Y.js.

**Acceptance:** Two browser tabs converge; offline edit in one merges on reconnect; no console errors.

---

### 4.2 — Flip on the Y.js dual-write and verify V31→V52 migration

**Depends on 4.1.**

**Task:**
- [ ] Set `EINVITE_COLLAB_V52_DUALWRITE=1` in dev.
- [ ] Open an invitation with existing V31 history; verify it seeds a Y.Doc correctly.
- [ ] Make an edit; verify both the V31 row and the V52 row are written.
- [ ] Verify a second client joining sees the V52 state.
- [ ] Document the migration procedure in `docs/collab/CRDT-DESIGN.md` §2.

**Acceptance:** Both paths agree; a client can join from either V31 or V52 history.

---

### 4.3 — Add the Phase 2c guest features

**Roadmap §5 mentioned these but they were deferred.**

- [ ] **Calendar integrations:** `.ics` download + Google Calendar / Apple Calendar links from the event details. Bilingual.
- [ ] **Venue maps:** OpenStreetMap embed on the public invitation page. Respect the existing CSP `frame-src`.
- [ ] **Gift registry:** host-curated list with claim/cancel lifecycle mirroring signup-sheets. Reuse the `signup_claims` pattern.

**Acceptance:** Each has backend + frontend + test.

---

### 4.4 — Plugin sandbox host runtime

**Phase 4a is spec-only. This makes it real.**

**Task:**
- [ ] New `src/js/plugin_sandbox_host.js`: constructs the cross-origin iframe, sets `sandbox="allow-scripts"` + `credentialless`, wires the `MessageChannel` protocol.
- [ ] New `src/python/plugin_marketplace_ca.py`: pinned CA public key, signature verification on install + launch.
- [ ] New marketplace endpoints: `/_marketplace/plugins/submit`, `/_marketplace/crl.json`, `/_marketplace/keys/{author_key_id}`.
- [ ] Add `approved_permissions_json` column to `plugin_installations_v48`.
- [ ] Provision `plugins.einvite.local` in `deploy/Caddyfile` (or document the deploy step).
- [ ] Wire `validate_manifest.py` into the install path.

**Acceptance:** The example plugin installs, runs sandboxed, and can call a whitelisted host method.

---

### 4.5 — Canva bridge (Phase 5.1)

**Design exists; no code.**

**Task:**
- [ ] `POST /api/canva/import` — accepts a Canva design URL or an uploaded PNG/PDF; rehosts through ObjectStorage with malware scan.
- [ ] OAuth2 callback route + `canva_oauth_tokens` table (encrypted at rest).
- [ ] `POST /api/canva/export` — walks the eInvite document, produces a `.canva.json` download.
- [ ] Add the Canva button to the editor import/export menus (Standard+Pro only).
- [ ] Bilingual strings.

**Acceptance:** Import a Canva PNG → appears as a page background; export produces a valid JSON file.

---

### 4.6 — Onboarding flow UI (Phase 5)

**Design exists; no code.**

**Task:**
- [ ] New `src/js/onboarding-flow.js` + `src/js/i18n/onboarding-strings.js` per `docs/hosted/ONBOARDING-FLOW.md`.
- [ ] 6 steps: signup → tier choice → workspace → first invitation → send → custom domain.
- [ ] Every step has a "Skip — I'll do this later" exit.
- [ ] Bilingual EN+KH for every string.
- [ ] Funnel metrics per design doc §3.

**Acceptance:** A new user can complete onboarding in under 5 minutes; every step is skippable.

---

## 5. SECTION 5 — Execution

Only after Sections 2, 3, and 4 are done.

### 5.1 — Run the load test

- [ ] Install k6.
- [ ] Run `tests/load_test_k6.js` against a staging deployment with 100 VUs for 1 minute.
- [ ] Fill in `docs/certification/LOAD-TEST-PLAN.md` §5 with real numbers.
- [ ] Ramp to 1000 VUs if the 100-VU run passes.
- [ ] Mark certification §4 status.

### 5.2 — Run the DR drill

- [ ] Follow `docs/ops/RESTORE-RUNBOOK.md` end-to-end against staging.
- [ ] Fill in `docs/ops/BACKUP-DR.md` §9 drill report.
- [ ] Mark certification §5 status.

### 5.3 — Execute the native platform matrix

- [ ] Follow `docs/certification/NATIVE-PLATFORM-MATRIX.md` on each of the 6 platforms.
- [ ] Record pass/fail per gate.
- [ ] Mark certification §1 status.

### 5.4 — Execute the browser matrix

- [ ] Follow `docs/certification/BROWSER-MATRIX.md` on each of the 6 browsers.
- [ ] Pay particular attention to the Firefox ESR `:has()` fallback.
- [ ] Mark certification §2 status.

### 5.5 — Commission the penetration test

- [ ] Hand `docs/certification/PEN-TEST-SCOPE.md` to an external tester.
- [ ] File the report under `docs/security/pen-test-reports/`.
- [ ] Remediate Critical + High findings.
- [ ] Mark certification §3 status.

### 5.6 — Sign off certification

- [ ] All 5 sections pass.
- [ ] Maintainer signature.
- [ ] External auditor signature.
- [ ] `docs/certification/CERTIFICATION.md` marked complete.

---

## 6. Refined Phase Statuses

Replace the status column in the original roadmap with this:

| Phase | Original status | Actual status | What's left |
|---|---|---|---|
| 0 — Docs governance | Complete | ✅ Complete | — |
| 1a — AI governance | Complete | ⚠️ Docs done, enforcement stub | §2.5, §2.6 |
| 1b — ASVS L2 | Complete | ⚠️ Gap analysis done, no remediations | §2.1–§2.4, §2.7–§2.9 |
| 1c — Backup/DR | Complete | ⚠️ Docs + scripts written, never executed | §5.2 |
| 2a — Guest features | Complete | ⚠️ Backend done, host UI missing | §3.1, §3.2, §4.3 |
| 2b — Khmer + a11y | Complete | ⚠️ Partial — variable font + P1 items missing | §3.5, §3.10 |
| 3 — Certification | Docs complete | ⚠️ Nothing executed | §5.1–§5.6 |
| 4a — Plugin marketplace | Complete | ⚠️ Spec + SDK only, no runtime | §4.4 |
| 4b — Y.js CRDT | Complete | ❌ **Not working — Y.js not vendored** | §4.1, §4.2 |
| 5 — Hosted tier | Complete | ⚠️ Scaffolding only | §4.5, §4.6 |

---

## 7. Definition of Done (unchanged)

A task is done when:
1. The code or document is written.
2. Tests exist and pass.
3. `VERSION_HISTORY.md` is updated.
4. The relevant `docs/` file is updated.
5. No working code was deleted.
6. Bilingual strings are present for all user-facing text.
7. The change is committed with the appropriate prefix (`sec-N`, `ux-N`, `phase-N`).

---

## 8. Suggested Task Order

```

WEEK 1
sec-1: P1-A reflected injection fix                (2.1)
sec-2: P1-B account lockout                        (2.2)
sec-3: P1-C MFA recovery codes                     (2.3)
sec-4: P1-D notification emails                    (2.4)

WEEK 2
sec-5: enforce JIT elevation                       (2.5)
sec-6: resource-scoped permissions stage 3         (2.6)
ux-1:  host signup sheets UI                       (3.1)
ux-2:  host polls UI                               (3.2)

WEEK 3
ux-3:  edit history dashboard wiring               (3.3)
ux-4:  album upload progress bar                   (3.4)
ux-5:  WCAG P1 items                               (3.5)
ux-6:  empty/loading/error states                  (3.6)

WEEK 4
ux-7:  toast system                                (3.7)
ux-8:  mobile responsiveness                       (3.8)
ux-9:  dark mode audit                             (3.9)
ux-10: bilingual consistency                       (3.10)

WEEK 5
sec-7: chapter 10 SAST/SCA/SBOM                    (2.7)
sec-8: CSP report-only + monitoring                (2.8)
sec-9: rate-limit coverage audit                   (2.9)
vendor: Y.js download + wiring                     (4.1)

WEEK 6
phase-4b: Y.js dual-write + migration              (4.2)
phase-2c: calendar + maps + gift registry          (4.3)
phase-4a: plugin sandbox host runtime              (4.4)

WEEK 7
phase-5: Canva bridge                              (4.5)
phase-5: onboarding flow UI                        (4.6)

WEEK 8+
EXECUTION (Section 5)

```

---

*Derived from the worklog assessment dated 2026-09-15. Supersedes Phase 1–5 priorities in the original ROADMAP.md.*
