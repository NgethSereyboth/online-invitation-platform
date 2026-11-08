# QA Release Candidate — 2026-11-08

**Branch:** `qa/deep-dive-improvements`
**Base:** `main` at `140aa77491e1b712e38beeb564f9f1482bd6d1e2`
**Release-candidate code SHA:** `6c47cb9`
**Merge policy:** **blocked until human review passes.** Nothing was merged into `main`.

## Branch relationship

`main` and `origin/main` both pointed at `140aa77` when this pass started. No upstream movement
required a merge, so the QA branch was not rebased and no published commits were rewritten. The
branch is a fast-forward candidate: `main..HEAD` contains only the QA commits below.

| Commit | Purpose |
|---|---|
| `fa716ae` | original QA fixes, regression tests, generated bundles/baselines, documentation |
| `1129bd7` | continuous improvement log |
| `29f7722` | RC remediation: dashboard set-membership scope + query-plan regression test |
| `6c47cb9` | full-suite regressions: fuzzer Khmer text, gallery accessible-name test, cache-policy test |

## Verification table

| # | Check | Command | Result |
|---:|---|---|---|
| 1 | Python compile | `.venv/bin/python -m compileall src/python` | PASS |
| 2 | Build integrity / mirror | `.venv/bin/python build.py all --check` | PASS — `drifted=0`, 730 mirror files up to date |
| 3 | JS lint | `npm run lint` | PASS |
| 4 | JS security lint | `npm run lint:security` | PASS |
| 5 | Full pytest suite | `.venv/bin/python -m pytest tests/ -q` | **242 passed in 1126.27 s (18:46)** |
| 6 | API fuzz | `.venv/bin/python scripts/qa_api_fuzz.py` | **44 cases, 0 failures, no 500s** |
| 7 | Accessibility | Playwright `06-a11y.spec.ts` | **20 passed** |
| 8 | Visual run 1 | Playwright `07-visual.spec.ts` | **11 passed** |
| 9 | Visual run 2 | Playwright `07-visual.spec.ts` | **11 passed** (two consecutive runs, baselines unchanged) |
| 10 | Session/security/cache/release batch | focused pytest (9 files) | **13 passed** |
| 11 | Static cache GET/HEAD | curl against 4310 | PASS — `public, max-age=3600, must-revalidate` for bundles/assets/vendor/core on GET and HEAD; template pack `public, max-age=86400`; API `no-store` |
| 12 | Query plan at 50k rows | `artifacts/qa-rc/query-plan-scale.json` | PASS — no `SCAN i` after the RC rewrite; archived uses the composite index, unfiltered/search use the multi-index OR |
| 13 | Release evidence contract | `tests/v27_3_5_release_evidence_test.py` | **PASS** (in the focused 13) |
| 14 | Whitespace/conflict check | `git diff --check` | PASS |

### Full-suite remediation

The first full run on the RC tree reported **239 passed, 3 failed** and exposed three contract
regressions that the earlier focused batches did not cover:

1. `tests/template_pack_gallery_test.py` still expected the removed `aria-label="Use …"` on
   `.pack-card-open`. The label was removed deliberately so the visible card name is the
   accessible name (WCAG 2.5.3). The test now asserts the label is absent, the visible name is
   present, and the button is reachable by its accessible name.
2. `tests/test_template_pack.py::test_no_khmer_typed_outside_allowed_files` found Khmer text in
   `scripts/qa_api_fuzz.py`. The fuzzer now uses emoji, Arabic and Greek Unicode instead; the
   repository's Khmer-text allowlist is unchanged.
3. `tests/test_template_pack_assets_test.py::test_cache_header_is_scoped_to_the_pack` still
   asserted that non-pack assets had no `Cache-Control`. That predates the QA policy; it now
   asserts the documented one-hour policy for stable-name assets while pack artwork keeps one
   day.

A fourth test-only issue surfaced while re-running the gallery smoke: after the URL had already
changed to the editor, the test waited for the page's `load` event, which long-lived media can
keep pending. It now waits for `domcontentloaded`, which is sufficient for the URL/navigation
contract.

All four checks pass individually after the fix. The final full-suite rerun passed **242/242** in
1126.27 s.

### Focused batch contents

`tests/qa_deep_dive_sessions_test.py`, `tests/qa_deep_dive_static_cache_test.py`,
`tests/qa_deep_dive_query_plan_test.py`, `tests/security_account_lockout_test.py`,
`tests/auth_register_rate_limit_test.py`, `tests/security_regression_test.py`,
`tests/security_reflected_injection_test.py`, `tests/security_media_headers_test.py`,
`tests/v27_3_5_release_evidence_test.py` — **13 passed** in 94.39 s.

## What was fixed in the QA branch

- **API edge cases:** new `scripts/qa_api_fuzz.py`, 44 malformed/type/boundary/Unicode cases;
  zero 500s.
- **Accessibility:** one anchor-based sign-in control instead of a nested button; removed
  `aria-label` overrides that hid visible step/card text; dashboard actions meet the 24 px
  target floor; improved mini-title contrast.
- **Visual stability:** the harness now reads the CSP nonce from the navigation response
  instead of `script[nonce]`, so freeze CSS is applied on dashboard pages. Only the
  independently changing account/language/appearance chrome is hidden; the invitation grid is
  masked. The previous dashboard diff was a harness artifact, not a product layout defect.
- **Images:** QR and crop-preview images lazy/async; hero has intrinsic `800×600` dimensions,
  `decoding="async"` and `fetchpriority="high"`.
- **Caching:** `Handler.static_cache_policy()` applies bounded public caching to stable-name
  assets and keeps API responses `no-store`; GET and HEAD share the policy.
- **Indexes:** `idx_invitations_owner_archived_updated` and
  `idx_invitation_collaborators_user_invite` are created in the SQLite schema.
- **Sessions:** logout deletes the server-side row; idle expiry returns the documented
  `200 {"user": null}` and deletes the row; ten rapid failures stay bounded and hit the lockout.
- **Dead code:** six unused imports removed. `JITElevationManager` is deliberately retained
  because `tests/ai_jit_enforcement_test.py` monkey-patches `server.JITElevationManager`.

## RC remediation: the index claim was not true for the real query

The QA documentation claimed the dashboard owner path used
`idx_invitations_owner_archived_updated`. Fresh `EXPLAIN QUERY PLAN` evidence on the actual
`list_invitations` SQL showed **`SCAN i`** at both empty and 50k-row scale, because the
correlated `EXISTS` inside the `OR` prevented SQLite from taking an index path.

The RC commit replaces it with the equivalent set-membership form:

```sql
(i.owner_id=? OR i.id IN (
    SELECT invitation_id FROM invitation_collaborators WHERE user_id=?
))
```

At 50k rows with the production schema and `ANALYZE`, the plans are now:

| Filter | Before | After |
|---|---|---|
| archived | `SCAN i` + correlated subquery | `SEARCH i USING INDEX idx_invitations_owner_archived_updated (ANY(owner_id) AND archived=?)` |
| published | `SCAN i` + correlated subquery | same composite-index search |
| unfiltered | `SCAN i` | `MULTI-INDEX OR` → `idx_invitations_owner` + collaborator covering index |
| search | `SCAN i` | `MULTI-INDEX OR` → `idx_invitations_owner` + collaborator covering index |

`tests/qa_deep_dive_query_plan_test.py` pins the no-full-table-scan invariant at 20k rows and
asserts that `list_invitations` keeps the set-membership clause. Ordering still needs a temporary
B-tree; covering every filter combination at 100k rows remains in the backlog.

## New tests added

| Test | Covers |
|---|---|
| `scripts/qa_api_fuzz.py` | 44 isolated API edge cases |
| `tests/qa_deep_dive_sessions_test.py` | logout row deletion, idle expiry, rapid failures/lockout |
| `tests/qa_deep_dive_static_cache_test.py` | GET/HEAD cache headers, template-pack exception, API boundary |
| `tests/qa_deep_dive_query_plan_test.py` | dashboard scope plan, index existence, production SQL clause |
| `e2e/specs/07-visual.spec.ts` (modified) | header-nonce handoff and deterministic dashboard shell |

## Visual baseline changes

Two committed baselines changed in `fa716ae`:
`e2e/__screenshots__/07-visual.spec.ts/dashboard-shell.png` and `guest-published.png`.
The RC pass did **not** run `--update-snapshots`; both consecutive verification runs passed
against the committed images (11/11, 23.6 s and 24.1 s).

## Database indexes added

- `idx_invitations_owner_archived_updated(owner_id, archived, updated_at DESC)`
- `idx_invitation_collaborators_user_invite(user_id, invitation_id)`

Both are `CREATE INDEX IF NOT EXISTS` in `src/python/server.py`, so existing databases gain them
on the next schema initialization without a destructive migration.

## Security checks verified

- `/api/auth/me` remains `200 {"user": null}` for invalid/expired sessions; no 401 contract change.
- 5 failures → 15-minute account lockout and 30 logins/600 s/IP remain intact.
- Registration rate limit unchanged.
- Header-injection paths: quoted filenames, no raw line breaks, no duplicate
  `Content-Disposition`.
- Reflected title/description/slug escaping still passes.
- Session logout/idle tests assert server-side deletion, not only cookie clearing.
- No secrets, tokens or live credentials were read or written.

## Deferred work

See `docs/FUTURE-IMPROVEMENTS.md`: server decomposition (12,280 lines; 157 functions CC > 10),
content-hashed immutable assets, full filter-combination query matrix at 100k rows, full-page
dashboard baseline, authenticated DAST on staging, multi-worker Redis rate limiting, dev-tooling
pins, and generated header-injection tests.

## Known limitations

- The live deployment still lacks HSTS and CSP, so live cookie/CSRF checks remain blocked. This is
  a deployment finding, not something the QA branch can fix.
- `pytest-timeout` is pinned in `requirements-dev.txt` but was not installed in the local venv;
  the full suite ran without it. No timeout plugin was silently substituted.
- The first full pytest run on the RC tree exposed three contract regressions; all are fixed in
  `6c47cb9`, and the final full-suite rerun passed **242/242**.
- Dashboard ordering still uses a temporary B-tree; the fix removes the table scan, not the sort.
- The release packet is committed on top of `6c47cb9`; the PR head is the authoritative final SHA.
