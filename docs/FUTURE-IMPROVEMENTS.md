# Future Improvements — Sprint 2

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
2. Reduce the 213-entry complexity baseline by a bounded, reviewed set.
3. Add the fixed-seed full-page dashboard fixture once the QA harness is merged.
4. Add a staging-only HSTS/CSP assertion to the existing authenticated DAST
   workflow, with an isolated origin and credentials.
