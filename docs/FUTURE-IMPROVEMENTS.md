# Future Improvements — QA Deep-Dive Backlog

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
