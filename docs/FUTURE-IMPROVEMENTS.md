# Future Improvements — Consolidated Release Backlog

**Release branch:** `release/consolidated-2026-11-08`
**Composition:** the QA deep-dive backlog and the Sprint 2 deferred/rejected work are both preserved below.
**Status:** neither source branch is merged into `main`; this is a review candidate.

## QA deep-dive branch

**Origin:** `qa/deep-dive-improvements` (2026-11-08)
**Status:** items below are too large or too risky for the QA branch. They are documented
instead of attempted. None blocks merging the QA branch.

## 1. Decompose `src/python/server.py`

**Problem.** The file is ~12,280 lines and mixes request dispatch, HTML rendering, static
serving, authentication, billing, AI, studio and platform adapters. `radon cc` reports
**157 functions with cyclomatic complexity > 10**. The largest are:

| Complexity | Function | Lines |
|---:|---|---:|
| 263 | `validate_document` | 302 |
| 217 | `do_POST` | 234 |
| 180 | `do_GET` | 186 |
| 122 | `connect_sqlite` | 321 |
| 77 | `do_PUT` | 53 |

**Why not fixed here.** Any extraction changes import paths, monkey-patch targets used by
existing security tests (`server.JITElevationManager`, `server.rate_limit`, and others) and the
startup order. That is an architectural rewrite, not a QA fix.

**Proposed solution.** Extract in dependency order, one seam per PR, with the full test suite
green after each: (1) static/HTML serving, (2) document validation, (3) response helpers and
security headers, (4) auth/session routes, (5) platform/AI adapters. Keep `server.py` as the
composition root and preserve every route and response shape. Add per-module tests before
moving code.

## 2. Content-hashed static filenames

**Problem.** The new policy is `public, max-age=3600, must-revalidate` for stable-name bundles
and assets. That is safe but leaves an hour of avoidable revalidation and a bounded stale
window after a deploy.

**Proposed solution.** Emit `bundle-<page>.<hash>.css/js` (and hashed asset names) from
`build.py`, rewrite the page manifests, and serve them with
`Cache-Control: public, max-age=31536000, immutable`. Keep the current one-hour policy for
anything that cannot be hashed. This needs a build/manifest change and a cache-busting review,
so it belongs in its own workstream.

## 3. Pagination query coverage

**Problem.** The archived/published owner paths now use
`idx_invitations_owner_archived_updated`, and the collaborator `IN` subquery uses
`idx_invitation_collaborators_user_invite`. The unfiltered list uses
`idx_invitations_owner` plus a temporary B-tree for ordering. Search and
status/date filters at larger volumes still need full plan coverage.

**Proposed solution.** Capture `EXPLAIN QUERY PLAN` for every dashboard filter combination
with a seeded 100k-invitation fixture, and add covering indexes only where the plan shows a
scan. `tests/qa_deep_dive_query_plan_test.py` already pins the owner scope at 20k rows; extend
it to every filter combination.

## 4. Full-page dashboard visual baseline

**Problem.** The dashboard grid grows with every seeded run, so only the 240 px shell strip is
captured. Card-level layout regressions are covered by component tests but not by one
full-page image.

**Proposed solution.** Seed a fixed, isolated dataset for a dedicated visual project, disable
cross-suite seeding for that project, and capture the full dashboard with a deterministic
account. Until then, the shell strip plus card component tests are the supported baseline.

## 5. Authenticated DAST against a deployed environment

**Problem.** `.github/workflows/dast-authenticated.yml` runs ZAP against a disposable loopback
fixture. The live deployment still lacks HSTS and a CSP header (observed 2026-11-07), and live
cookie/CSRF checks were therefore out of scope for this branch.

**Proposed solution.** Add a post-deploy DAST job that targets an isolated staging origin with
its own credentials, asserts HSTS/CSP on the first response, and stores the ZAP report as an
artifact. Production must never be the active-scan target.

## 6. Rate limiting across multiple workers

**Problem.** Login lockout and rate limits work in-process when Redis is absent. Multiple
server processes therefore each hold their own counter.

**Proposed solution.** Require `EINVITE_REDIS_URL` in multi-worker deployments (the code
already prefers Redis when configured), add a startup warning when it is absent, and test the
Redis path with a disposable Redis instance in CI.

## 7. Test tooling gaps

**Problem.** `pytest-timeout`, `pytest-cov`, `httpx`, `vulture` and `radon` are not installed by
`requirements-dev.txt`, so timeout enforcement, coverage and static-analysis runs are manual.

**Proposed solution.** Pin `pytest-timeout`, `pytest-cov`, `vulture` and `radon` in
`requirements-dev.txt`, add a `make analyze` target, and record the complexity baseline so new
functions above the threshold fail review.

## 8. Header-injection property tests

**Problem.** `safe_header_value`, `_safe_inline_filename` and the CRLF-stripping call sites are
covered by example-based tests, but not by generated inputs.

**Proposed solution.** Add a Hypothesis-based test that feeds CR/LF, NUL, quote, semicolon and
Unicode line separators through `Location`, `Content-Disposition` and cookie paths, asserting
no header value contains a raw line break and no duplicate header is emitted.

## Sprint 2 branch

**Branch:** `improve/sprint-2-hardening-and-polish`
**Base:** `main` `140aa77`
**Status:** items below were considered for Sprint 2 and deliberately deferred or
rejected. None is required for the completed Sprint 2 tasks.

The fuller QA deep-dive backlog and sprint plan live on the unmerged
`qa/deep-dive-improvements` branch (draft PR #27). They are not duplicated here
until that branch is reviewed and merged.

## Deferred because they depend on the QA branch

- **Dashboard query-plan matrix.** Extending the 20k-row test to every status,
  date and search combination needs the QA branch's set-membership query rewrite
  and `tests/qa_deep_dive_query_plan_test.py`; branching this sprint from `main`
  would duplicate unmerged work.
- **Full-page dashboard visual baseline.** The fixed-seed fixture and Playwright
  nonce handoff are part of PR #27. Rebuilding them here would create two
  competing harnesses.

## Deferred as design or architectural work

- **Content-hashed immutable bundles.** Requires a build/manifest change,
  cache-busting review and a stable-name fallback plan; the sprint plan marked it
  design-only.
- **`server.py` decomposition.** Architectural, changes import paths, startup
  order and monkey-patch targets; explicitly out of scope.
- **Multi-worker Redis rate limiting.** Needs infrastructure and a deployment
  contract; no Redis deployment exists in this repository.
- **Authenticated DAST / live HSTS and CSP.** Needs an isolated staging origin,
  credentials and an operations owner; production must never be the scan target.

## Not reproduced

- **Analytics test order dependence.** `test_phase4_rate_limit` passed alone
  (1/1) and as part of `tests/analytics_ingestion_test.py` (6/6) on this base.
  No change was made; keep watching if the suite order or shared fixture changes.

## Deliberately not duplicated

- **User-visible accessibility fixes.** PR #27 already contains the sign-in,
  accessible-name, target-size and contrast work. Duplicating it on `main`
  would create a conflicting second implementation. Reconcile it after PR #27
  lands.

## Next candidates

1. Reconcile PR #27, then extend the query-plan matrix on top of its rewrite.
2. Reduce the 209-entry complexity baseline by a bounded, reviewed set.
3. Add the fixed-seed full-page dashboard fixture once the QA harness is merged.
4. Add a staging-only HSTS/CSP assertion to the existing authenticated DAST
   workflow, with an isolated origin and credentials.
