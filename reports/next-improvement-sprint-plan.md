# Next Improvement Sprint Plan

**Source:** `docs/FUTURE-IMPROVEMENTS.md` (8 items, QA deep-dive branch)
**Prepared:** 2026-11-08, release-candidate stabilization pass
**Rule:** nothing here is started in the RC pass. The RC branch only fixes a failed verification
finding and records the evidence.

## Classification

| # | Item | Class | Why |
|---:|---|---|---|
| 1 | Decompose `src/python/server.py` (12,280 lines, 157 functions CC > 10) | `ARCHITECTURAL` | Changes import paths, monkey-patch targets and startup order. Human-owned, one seam per PR. |
| 2 | Content-hashed static filenames | `NEEDS_DESIGN` | Requires a build/manifest change, cache-busting review and a migration plan for stable-name fallbacks. |
| 3 | Pagination query coverage | `NEEDS_DESIGN` | The owner/collaborator scope is covered; every status/date/search combination at 100k rows needs a fixture and plan matrix. |
| 4 | Full-page dashboard visual baseline | `NEEDS_DESIGN` | Needs a fixed, isolated seed project so the grid does not grow between runs. |
| 5 | Authenticated DAST against a deployed environment | `NEEDS_DESIGN` | Requires an isolated staging origin, credentials and a post-deploy job; production must never be scanned. |
| 6 | Rate limiting across multiple workers | `ARCHITECTURAL` | No Redis infrastructure in this repository or deployment; needs a deployment contract and disposable-Redis CI. |
| 7 | Test tooling gaps | `SAFE_QUICK_WIN` | Dev-only pins plus a `make analyze` target; no runtime or API change. |
| 8 | Header-injection property tests | `SAFE_QUICK_WIN` | Add Hypothesis to dev requirements and generated CR/LF/NUL/Unicode inputs around existing sanitizers. |

## Top 5 safest high-value tasks for the next autonomous sprint

### 1. Pin the analysis toolchain and add `make analyze` (item 7)

- **Scope:** add exact `pytest-cov`, `vulture` and `radon` pins to `requirements-dev.txt`; add a
  `make analyze` target that runs vulture and radon against `src/python`; document the current
  complexity baseline (157 functions above CC 10).
- **Tests before the task:** a fresh-venv install test (`pip install -r requirements-dev.txt`,
  `pip check`), `pytest --version` including `pytest-timeout`, and a failure test proving
  `make analyze` returns non-zero when a new above-threshold function is introduced.
- **Evidence:** `requirements-dev.txt` diff, clean `pip check`, `make analyze` output, and the
  updated baseline in the docs.

### 2. Add generated header-injection tests (item 8)

- **Scope:** Hypothesis strategies for CR, LF, CRLF, NUL, quotes, semicolons and Unicode line
  separators; drive `safe_header_value`, `_safe_inline_filename`, `Content-Disposition`,
  `Location` and cookie paths.
- **Tests before the task:** property tests asserting no raw line break in any emitted header,
  no duplicate `Content-Disposition`, and unchanged filenames for ordinary input.
- **Evidence:** 100+ generated examples pass, zero production behavior change, and one regression
  test that fails if a raw line break is reintroduced.

### 3. Extend the query-plan matrix to every dashboard filter (item 3)

- **Scope:** reuse the 20k-row fixture from `tests/qa_deep_dive_query_plan_test.py`, add
  `published`, `draft`, `archived`, unfiltered and search combinations, and assert no
  `SCAN i` table scan. Keep the fixture in-memory so the suite stays fast.
- **Tests before the task:** `EXPLAIN QUERY PLAN` assertions for each filter plus a regression
  that the production `list_invitations` clause remains set-membership.
- **Evidence:** the plan matrix in `artifacts/qa-rc/query-plan-scale.json`-style JSON, all cases
  using a named invitation index, and a runtime ceiling for the test.

### 4. Design and prototype content-hashed bundles (item 2, design only)

- **Scope:** produce a design note and a throwaway build prototype that emits
  `bundle-<page>.<hash>.css/js`, rewrites manifests, and keeps stable-name fallbacks. Do not
  merge the prototype.
- **Tests before the task:** manifest rewrite fixtures, a cache-busting check, and a test that
  every HTML reference resolves to an emitted file.
- **Evidence:** design note, prototype output, manifest diff, and a rollback plan. Human review
  decides whether the build change ships.

### 5. Build the isolated full-page dashboard fixture (item 4, harness only)

- **Scope:** a dedicated Playwright project with a fixed seed dataset and cross-suite seeding
  disabled; capture one full-page dashboard image with a deterministic account.
- **Tests before the task:** two consecutive captures produce identical bytes; the seed count is
  fixed; the existing 240 px shell baseline remains unchanged.
- **Evidence:** two identical PNG runs, the fixed seed manifest, and a diff report. Do not replace
  the current shell baseline until the full-page image is stable twice.

## Top 3 human-only tasks

1. **Decompose `src/python/server.py`** — architectural, multi-PR, and it changes monkey-patch
   targets used by security tests. A human must own route parity and startup order.
2. **Multi-worker rate limiting with Redis** — requires infrastructure, a deployment contract,
   startup behavior for missing Redis, and disposable-Redis CI.
3. **Authenticated DAST and live HSTS/CSP** — requires a staging origin, credentials and a
   deployment/operations owner; production must not be the scan target.

## Explicitly not attempted in this pass

- No `server.py` decomposition.
- No Redis work (the live health payload reports `redis: false` and the repository has no Redis
  deployment).
- No change to `GET /api/auth/me` (`200 {"user": null}` stays).
- No new runtime dependency.
- No baseline update: the two visual runs passed against the committed images without
  `--update-snapshots`.
