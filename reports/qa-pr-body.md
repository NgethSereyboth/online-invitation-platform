## Summary

This is the release-candidate packet for the QA deep-dive on `qa/deep-dive-improvements`. It
hardens malformed-input handling, accessibility, visual determinism, static caching, session
lifecycle and dashboard query planning without changing the public API.

The RC pass also corrected a performance claim that did not survive fresh evidence: the real
dashboard query used by `list_invitations` performed a full scan even after the owner index was
added, because a correlated `EXISTS` inside an `OR` blocked the index path. The query now uses an
equivalent set-membership `IN`, and a regression test pins the no-table-scan plan.

**Merge is blocked until human review passes. This PR is a draft and nothing has been merged
into `main`.**

## Branch and commits

- Base: `main` at `140aa77491e1b712e38beeb564f9f1482bd6d1e2`
- Branch: `qa/deep-dive-improvements`
- Code SHA: `6c47cb9`
- `fa716ae` — QA fixes, regression tests, generated bundles/baselines, documentation
- `1129bd7` — continuous improvement log
- `29f7722` — dashboard set-membership scope + query-plan regression test
- `6c47cb9` — full-suite regressions: fuzzer text, gallery accessible name, cache policy
- Release-packet commit follows on the same branch; see the PR head for the authoritative SHA.

## Risk assessment

**Overall: low-to-moderate, with no API contract change.**

- The dashboard rewrite is semantically equivalent (`IN` over a primary-keyed collaborator table
  instead of a correlated `EXISTS`). It changes planning, not results.
- Session/authentication behavior is unchanged; the `/api/auth/me` contract remains
  `200 {"user": null}` for invalid sessions.
- No runtime dependency, secret, migration or public route was added.
- The largest diff is generated bundles/mirrors, but `build.py all --check` reports
  `drifted=0` and all 730 mirror files up to date.
- The visual harness reads a CSP nonce from the navigation response; this is test-only and does
  not change production CSP issuance.
- Residual risk is concentrated in the large generated diff and the deferred live-deployment
  HSTS/CSP gap. Both need human review.

## Evidence

| Check | Result |
|---|---|
| `python -m compileall src/python` | PASS |
| `python build.py all --check` | PASS — `drifted=0`, 730 mirror files |
| `npm run lint` | PASS |
| `npm run lint:security` | PASS |
| `.venv/bin/python -m pytest tests/ -q` | **242 passed in 1126.27 s (18:46)** |
| `scripts/qa_api_fuzz.py` | **44 cases, 0 failures, no 500s** |
| Playwright a11y (`06-a11y.spec.ts`) | **20 passed** |
| Playwright visual (`07-visual.spec.ts`) run 1 | **11 passed** |
| Playwright visual run 2 | **11 passed** — baselines unchanged |
| Focused session/security/cache/release batch | **13 passed** |
| Static cache GET/HEAD | `public, max-age=3600, must-revalidate`; template pack `max-age=86400`; API `no-store` |
| Query plan at 50k rows | no `SCAN i`; composite index for archived/published, multi-index OR otherwise |
| `git diff --check` | PASS |

Artifacts (ignored, local to the review machine): `artifacts/qa-rc/logs/`,
`artifacts/qa-rc/query-plan-scale.json`, `artifacts/qa/api-fuzz-*.json`.

### Full-suite remediation

The first full run on the RC tree reported **239 passed, 3 failed**. All three were contract
tests that had not been updated with the intentional QA behavior:

1. The gallery test expected the removed `aria-label="Use …"`; it now asserts the visible name
   is the accessible name and the label override is absent.
2. The fuzzer contained Khmer text, which the repository forbids outside approved files; it now
   uses emoji, Arabic and Greek instead.
3. The pack cache test expected non-pack assets to have no `Cache-Control`; it now asserts the
   documented one-hour policy for stable-name assets.

While re-running the gallery smoke, the test was also changed to wait for `domcontentloaded` at
the editor URL instead of the long-lived `load` event. All four checks pass individually. Final full-suite rerun: **242 passed in 1126.27 s**.

## Visual and baseline notes

Two committed baselines changed in `fa716ae`:
`e2e/__screenshots__/07-visual.spec.ts/dashboard-shell.png` and `guest-published.png`. The RC pass
did **not** update snapshots; it ran the visual suite twice against the committed images and both
runs passed (11/11, 23.6 s and 24.1 s). The dashboard baseline deliberately hides the account,
language and appearance controls and masks the invitation grid so seeding volume does not move
the image.

## Security impact

- No weakening of login lockout, registration rate limiting or CSRF checks.
- Logout and idle expiry delete the server-side session row, not only the cookie.
- Header-injection regression tests still pass (quoted filenames, no raw line breaks, no duplicate
  `Content-Disposition`).
- Reflected title/description/slug escaping still passes.
- No secrets or live credentials were read or written. The live deployment's missing HSTS/CSP
  remains a separate deployment blocker, not a code change in this branch.

## Performance impact

- Removes the full scan from the dashboard scope. At 50k rows with the production schema and
  `ANALYZE`:
  - archived: `SEARCH i USING INDEX idx_invitations_owner_archived_updated (ANY(owner_id) AND archived=?)`
  - unfiltered/search: `MULTI-INDEX OR` using `idx_invitations_owner` and
    `idx_invitation_collaborators_user_invite`
- Dashboard ordering still needs a temporary B-tree; covering every filter combination at 100k
  rows remains in `docs/FUTURE-IMPROVEMENTS.md`.
- Public static assets now carry bounded cache headers; hero and QR images use intrinsic
  dimensions and lazy/async hints.

## Accessibility impact

- 20/20 a11y checks pass.
- Sign-in is a single anchor, not a button nested inside a link.
- Visible step/card text is no longer overridden by `aria-label`.
- Dashboard actions meet the 24 px target floor; mini-title contrast improved.

## Human review checklist

- [ ] Confirm the `EXISTS` → `IN` dashboard rewrite is semantically equivalent and acceptable.
- [ ] Review the 20k-row query-plan test and the 50k-row evidence in the release report.
- [ ] Confirm both changed visual baselines are intentional and stable.
- [ ] Confirm no public API, session or auth contract changed.
- [ ] Confirm generated bundles/mirrors match the documented build output.
- [ ] Confirm no secrets, live credentials or production data are present.
- [ ] Accept or defer the remaining backlog in `docs/FUTURE-IMPROVEMENTS.md`.
- [ ] Keep the PR in draft until every item above is resolved.

## Merge blocking

**Do not merge until human review passes.** The live HSTS/CSP finding, the server decomposition
and the multi-worker Redis work are explicitly out of scope and must not be treated as delivered
by this PR.
