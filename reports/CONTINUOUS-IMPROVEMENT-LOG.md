# Continuous Improvement Log — Consolidated Release

**Release branch:** `release/consolidated-2026-11-08`
**Composition:** the QA deep-dive log and the Sprint 2 log are both preserved below, with their original branch context.
**Merge policy:** no merge into `main`; the release candidate remains subject to human review.

## QA deep-dive branch

**Branch:** `qa/deep-dive-improvements` (base `main` `140aa77491e1b712e38beeb564f9f1482bd6d1e2`)
**Scope:** API edge cases, accessibility, visual integrity, bundle/image performance, query
plans, session/rate-limit edge cases, dead code and documentation.
**Rule:** nothing here is merged to `main`; every change stays on the QA branch for human review.

---

## 2026-11-08T06:55Z — Phase 1: API fuzzing

- **Found:** no automated malformed-input coverage across the core JSON endpoints.
- **Fixed:** added `scripts/qa_api_fuzz.py`, an isolated-server fuzzer covering 44 cases:
  malformed JSON, missing fields, wrong types, empty/max-length strings, negative/zero
  integers, emoji, RTL text, null bytes and long Unicode.
- **Result:** `API_FUZZ_CASES=44 FAILURES=0`; no 500s, no HTML tracebacks.
- **Tests:** the fuzzer itself is the regression harness; report written to
  `artifacts/qa/api-fuzz-*.json`.
- **Commit:** `fa716ae`.

## 2026-11-08T07:05Z — Phase 2: accessibility fixes

- **Found:** (1) sign-in rendered a `<button>` nested inside an `<a>`, (2) the current journey
  step menu button overrode its visible text with an `aria-label`, (3) template-pack cards
  overrode their accessible name, (4) two dashboard actions were below the 24×24 target floor
  because `.template-select-action` forced `height:100%!important`.
- **Fixed:** single anchor-based sign-in control; removed the overriding labels; raised the
  card floor to 320 px, preview to 36 px, auto action height and corrected the mini-title
  contrast blend.
- **Tests:** `e2e/specs/06-a11y.spec.ts` — **20 passed**.
- **Commit:** `fa716ae`.

## 2026-11-08T07:25Z — Phase 2: visual harness / CSP nonce

- **Found:** the visual harness injected an un-nonced `<style>`, which the nonce-based
  `style-src` CSP blocked. It also copied the nonce from `script[nonce]`, but dashboard pages
  have no inline script carrying one. The dashboard shell diff was therefore not a product
  layout bug: it was the injected account/language/appearance controls moving between runs.
- **Fixed:** read the nonce from the navigation response's `Content-Security-Policy` header;
  freeze CSS now applies. Hide the account/language/appearance cluster with layout-stable
  `visibility:hidden` and keep the invitation grid masked.
- **Tests:** `e2e/specs/07-visual.spec.ts` — **11 passed**, then **11 passed** on two
  consecutive verification runs (previously 10/11 with a 3–5% dashboard diff).
- **Commit:** `fa716ae`.

## 2026-11-08T07:40Z — Phase 3: image loading and query plans

- **Found:** account QR image and landing-page crop preview lacked lazy/async hints; the hero
  image had no intrinsic dimensions (CLS risk). Dashboard pagination had no owner/archived
  composite index.
- **Fixed:** QR `loading="lazy" decoding="async"`; hero `width="800" height="600"
  decoding="async" fetchpriority="high"`; crop preview lazy/async. Added
  `idx_invitations_owner_archived_updated` and
  `idx_invitation_collaborators_user_invite`.
- **Verified:** `EXPLAIN QUERY PLAN` uses the new owner index
  (`SEARCH invitations USING INDEX idx_invitations_owner_archived_updated (owner_id=? AND archived=?)`);
  collaborator reads use `idx_invitation_collaborators_user`.
- **Tests:** new `tests/qa_deep_dive_sessions_test.py` covers the session paths; query-plan
  evidence captured in the QA artifacts.
- **Commit:** `fa716ae`.

## 2026-11-08T07:55Z — Phase 3: static cache headers

- **Found:** only `/assets/template-pack/` sent `Cache-Control`; every other public bundle,
  asset, vendor file and core script was served without a cache policy.
- **Fixed:** added `Handler.static_cache_policy()`. Template-pack artwork remains
  `public, max-age=86400`; all other public static files now send
  `public, max-age=3600, must-revalidate`. Both `GET` and `HEAD` use the same policy; API
  responses keep their existing `no-store` behavior.
- **Tests:** new `tests/qa_deep_dive_static_cache_test.py` asserts GET/HEAD headers for root
  bundles, assets, vendor and core files, the template-pack exception and the API boundary.
- **Commit:** `fa716ae`.

## 2026-11-08T08:05Z — Phase 4: session and rate-limit edge cases

- **Found:** no regression coverage proving logout deletes the server-side session row, and
  no rapid-failure test that also confirms the account lockout still engages.
- **Fixed:** added `tests/qa_deep_dive_sessions_test.py`:
  - logout invalidates the session server-side (cookie cleared, session row deleted);
  - idle-expired sessions return the documented `200 {"user": null}` and delete the row;
  - ten rapid invalid logins do not yield a successful session and the lockout counter still
    applies.
- **Policy preserved:** the `/api/auth/me` contract stays `200 {"user": null}` for invalid
  sessions (no breaking API change); the existing 5-failure/15-minute lockout and
  30-logins/600 s/IP limit are unchanged.
- **Tests:** **2 passed**.
- **Commit:** `fa716ae`.

## 2026-11-08T08:20Z — Phase 4: header injection

- **Found:** redirect and download paths already funnel user data through `safe_header_value`
  or `_safe_inline_filename`, with CR/LF stripping at each `send_header` call.
- **Verified:** `tests/security_media_headers_test.py` (quoted filenames, no raw line breaks,
  no duplicate `Content-Disposition`) and `tests/security_reflected_injection_test.py`
  (escaped title/description/slug) both pass.
- **Result:** no code change required; generated-input property tests recorded in
  `docs/FUTURE-IMPROVEMENTS.md` §8.
- **Commit:** `fa716ae`.

## 2026-11-08T08:30Z — Phase 5: static analysis and dead code

- **Found:** `radon` reports **157 functions with complexity > 10** (largest:
  `validate_document` 263, `do_POST` 217, `do_GET` 180, `connect_sqlite` 122).
  `vulture` found unused imports `hash_recovery_code`, `marketplace_summary`, `tool_catalog`,
  `_delivery_available_channels`, `DeliveryChannelError` and the local `TTLibError` import.
- **Fixed:** removed the unused imports. Kept `JITElevationManager` because an existing
  security test monkey-patches `server.JITElevationManager`.
- **Deferred:** decomposing the 12,280-line `server.py` is an architectural rewrite; recorded
  with a phased proposal in `docs/FUTURE-IMPROVEMENTS.md` §1. The two remaining vulture
  findings are protocol-signature parameters (`makefile(buffering, **kw)`), not dead code.
- **Checks:** `npm run lint`, `npm run lint:security`, `compileall` pass.
- **Commit:** `fa716ae`.

## 2026-11-08T08:45Z — Phase 6: documentation

- **Fixed:** README now documents the CSP nonce lifecycle, the authenticated ZAP DAST
  workflow and the QA verification commands. `docs/ARCHITECTURE.md` gains a QA-hardening
  section covering nonce issuance, static cache policy, session lifecycle, indexes and the
  Playwright nonce handoff. Large/risky items moved to
  `docs/FUTURE-IMPROVEMENTS.md`.
- **Tests:** README hash pin in `tests/v27_3_5_release_evidence_test.py` repinned; full
  verification batch run after the documentation edit.
- **Commit:** `fa716ae`.

---

## Verification summary (branch)

| Check | Result |
|---|---|
| `scripts/qa_api_fuzz.py` | 44 cases, 0 failures |
| `e2e/specs/06-a11y.spec.ts` | 20 passed |
| `e2e/specs/07-visual.spec.ts` | 11 passed on update + 2 verifies |
| `tests/qa_deep_dive_sessions_test.py` | 2 passed |
| Lockout / registration / security regression / media headers / reflected injection | 6 passed |
| `tests/qa_deep_dive_static_cache_test.py` | passed |
| `npm run lint`, `npm run lint:security` | pass |
| `python -m compileall` | pass |
| `build.py all --check` | pass |
| `radon` / `vulture` | baseline captured; backlog documented |

**Not verified here / out of scope:** live HSTS and CSP on the deployed origin, live cookie
and CSRF checks (blocked by the deployment finding), full server decomposition, content-hashed
immutable assets, full-page dashboard baseline. See `docs/FUTURE-IMPROVEMENTS.md`.

---

## 2026-11-08T08:30Z — Release-candidate stabilization

- **Found:** the architecture claim that the dashboard owner path used
  `idx_invitations_owner_archived_updated` was not true for the real `list_invitations` SQL. A
  correlated `EXISTS` inside the `OR` forced `SCAN i` at empty and 50k-row scale. The index
  existed, but the query could not use it.
- **Fixed:** replaced the correlated `EXISTS` with the equivalent set-membership
  `i.id IN (SELECT invitation_id FROM invitation_collaborators WHERE user_id=?)`. At 50k rows
  the archived/published filters now report
  `SEARCH i USING INDEX idx_invitations_owner_archived_updated (ANY(owner_id) AND archived=?)`;
  the unfiltered/search paths use a `MULTI-INDEX OR` over `idx_invitations_owner` and the
  collaborator covering index instead of a scan.
- **Tests:** new `tests/qa_deep_dive_query_plan_test.py` builds a 20k-row in-memory schema,
  asserts no full table scan for the scope and unfiltered plans, and asserts the production
  `list_invitations` clause is the set-membership form. **2 passed**.
- **Evidence:** `artifacts/qa-rc/query-plan-scale.json` (50k rows, before/after plans) and
  `artifacts/qa-rc/logs/focused-security.log` (13 passed).
- **Docs:** `docs/ARCHITECTURE.md` §10.4 and `docs/FUTURE-IMPROVEMENTS.md` §3 now describe the
  actual plans and the remaining temporary B-tree/100k-row coverage gap.
- **Commit:** `29f7722`.

## 2026-11-08T09:00Z — Full-suite reconciliation

- **Found:** the first full `pytest tests/` run on the RC tree reported **239 passed, 3 failed**:
  the gallery test still expected the removed overriding `aria-label`, the new fuzzer contained
  Khmer text forbidden outside approved files, and the old pack cache test expected non-pack
  assets to have no `Cache-Control`.
- **Fixed:** the gallery test now asserts the visible name is the accessible name and the
  control is reachable by that name; the fuzzer uses emoji/Arabic/Greek instead of Khmer; the
  pack cache test asserts the documented one-hour policy for stable-name assets. The gallery
  smoke also waits for `domcontentloaded` at the editor URL instead of the long-pending `load`
  event.
- **Tests:** gallery 1 passed; text/cache contracts 2 passed; fuzzer 44 cases / 0 failures;
  final full-suite rerun **242 passed in 1126.27 s (18:46)**.
- **Commit:** `6c47cb9`.

## Sprint 2 branch

**Branch:** `improve/sprint-2-hardening-and-polish` (from `main` `140aa77`)
**Scope:** static-analysis tooling, header-injection properties, test stability,
local/CI gate wiring.
**Rule:** no merge into `main`; every change stays on this branch for review.

> The QA deep-dive log and sprint plan live on `qa/deep-dive-improvements`
> (draft PR #27), which is not merged. This file starts the Sprint 2 log on the
> stable base; it does not claim the QA branch's commits.

---

## 2026-11-08 — Analysis gate

- **Found:** the repository had no runnable static-analysis gate. Its recorded
  baseline was stale at “157 functions above CC 10”; fresh `radon` evidence on
  `main` reports **213**. `vulture` at >=90% confidence reports **11** existing
  findings, so a raw threshold check would be red on day one.
- **Fixed:** pinned `pytest-cov==7.1.0`, `vulture==2.16` and `radon==6.0.1` in
  `requirements-dev.txt`; added `make analyze` and `make coverage`; added
  `tools/analyze.py` with a baseline-diff gate and
  `tools/analysis_baseline.json`.
- **Tests:** `tests/tooling_analysis_test.py` — 5 new tests (new complexity,
  matching baseline, increased complexity, new vulture finding, repository
  baseline); combined with the existing header tests, **7 passed**. A temporary
  new complex function made the gate return non-zero (tool exit 1, `make`
  exit 2); removing it returned `ANALYSIS_OK` (exit 0).
- **Evidence:** `artifacts/sprint2/analyze.log`,
  `artifacts/sprint2/analyze-write.log`, `artifacts/sprint2/tooling-tests.log`.
- **Docs:** `docs/QUALITY-GATES.md` records the 213 / 11 baseline and the
  regeneration rule.

## 2026-11-08 — Header-injection properties

- **Found:** `safe_header_value()` stripped CR and LF but left NUL, so a
  NUL-containing value could reach a `Location` header. Header filenames and
  the media/download paths had existing example tests but no generated input
  coverage.
- **Fixed:** `safe_header_value()` now strips CR, LF and NUL before the
  4,096-byte cap. Added Hypothesis-generated tests for CR, LF, CRLF, NUL,
  quotes, semicolons, backslashes and Unicode line separators across header
  values, `Location`, filenames, download/binary/media responses and cookie
  construction.
- **Tests:** property + media-header + tooling + reflected-injection suites —
  **16 passed**. The red run recorded 3 genuine NUL failures before the fix;
  the fourth red assertion was a test-helper assumption about `attachment;`
  versus `inline;` and was corrected. `make analyze` stays at the 213 / 11
  baseline.
- **Evidence:** `artifacts/sprint2/header-properties-red.log`,
  `artifacts/sprint2/header-task-tests.log`,
  `artifacts/sprint2/analyze-after-header2.log`.
- **Dependency:** `hypothesis==6.170.15` is pinned in `requirements-dev.txt`; a
  fresh install and `pip check` both pass.

## 2026-11-08 — Analysis gate wired into local and CI runners

- **Found:** `make analyze` existed as a manual target, but neither
  `tools/run-gates.py` nor the Tests workflow called it. A new complexity or
  vulture finding could therefore pass both the local matrix and CI.
- **Fixed:** added the `analyze` phase after `bundles`, with a fail-closed
  `ANALYSIS_OK` marker; added `make analyze` to
  `.github/workflows/tests.yml`; documented the wiring in
  `docs/QUALITY-GATES.md` and `tools/README.md`.
- **Tests:** the new wiring test was red first; `tests/tooling_analysis_test.py`
  now **6 passed**; `tests/test_runner_manifest.py` and
  `tests/lhci_invocation_test.py` **4 passed**;
  `.venv/bin/python tools/run-gates.py --phase analyze` printed
  `PASS analyze` / `GATES_PASSED`; `make analyze` printed 213/213 and 11/11 with
  `ANALYSIS_OK`; build, compileall and diff checks pass. The workflow parses
  with system PyYAML 6.0.1 and the repo's `js-yaml`.
- **Evidence:** `artifacts/sprint2/wiring-red.log`,
  `artifacts/sprint2/wiring-pytest.log`,
  `artifacts/sprint2/wiring-run-gates.log`,
  `artifacts/sprint2/wiring-related-tests.log`,
  `artifacts/sprint2/workflow-parse.log`.

## 2026-11-08 — Sprint close

- **Scope:** three bounded tasks; no product/UI change and no new runtime
  dependency.
- **Full suite:** `250 passed in 1120.81s (18:40)`, exit 0, recorded before the
  wiring task (`artifacts/sprint2/pytest-full.log`). The wiring task was checked
  with its targeted and runner tests rather than a second 18-minute suite.
- **Playwright:** `13-security.spec.ts` (chromium) — **8 passed** on a disposable
  4310 origin; the server was stopped and the user's 4175 server (PID 3005) was
  left running.
- **Final gates:** `python3 build.py all --check` → `BUILD_OK`/730 mirror files;
  `npm run lint` and `npm run lint:security` → PASS; `make analyze` → 213/213
  complexity and 11/11 vulture, `ANALYSIS_OK`; `pip check`, `compileall` and
  `git diff --check` → PASS.
- **Report:** `reports/sprint-2-summary.md`. Deferrals and rejected work:
  `docs/FUTURE-IMPROVEMENTS.md`.
- **No merge, no push, no production access.**
