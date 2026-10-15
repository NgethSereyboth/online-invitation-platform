# Plan 003: Triage the failing non-pytest test scripts and classify every failure

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving on. If anything in "STOP conditions" occurs, stop and report — do not improvise. When done, update the row for plan 003 in `plans/README.md`.
>
> **Drift check (run first)**: `git log --oneline 39c8ef1..HEAD -- tests/ src/python/server.py | head`
> If many commits touched the tests since this plan was written, re-run Step 1 from scratch and use the new list rather than the one below.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (classification and, where the replacement is unambiguous, test-only updates)
- **Depends on**: none. Plan 002 may change one of the failures in this list (`security_tenant_isolation_test.py`); do not re-triage it here.
- **Category**: tests
- **Planned at**: commit `39c8ef1`, 2026-10-14

## Why this matters

Many standalone test scripts under `tests/` are not run by pytest and exit non-zero. A broken signal trains everyone to ignore the suite, which hides real regressions. In a first pass of ~10 scripts, the failures were: `tests/final_features_test.py` imports `validate_document` from `server`, which no longer exists there and then hangs until timeout; `tests/p5_canva_onboarding_test.py` queries a column `canva_connected_at` that the schema does not have; `tests/p2c_features_test.py` and `tests/plugin_sandbox_test.py` get 404s from routes; `tests/production_foundations_test.py` gets 401; several scripts need `playwright`, which is not installed. The goal of this plan is a complete, honest classification, not a pile of quick fixes.

## Current state

- The test runner is `Makefile` line 37 (`test:` target). Read it first and record the exact command it runs; do not assume.
- Leads from an earlier informal pass. **These were NOT re-verified when this plan was written.** Treat them as hypotheses and confirm each one in Step 1; the list is not exhaustive:
  - `tests/final_features_test.py` — `from server import validate_document` path; times out.
  - `tests/p5_canva_onboarding_test.py` — missing column `canva_connected_at`.
  - `tests/p2c_features_test.py` — 404 from a route.
  - `tests/plugin_sandbox_test.py` — 404 from a route.
  - `tests/production_foundations_test.py` — 401.
  - Scripts importing `playwright` — `ModuleNotFoundError`.
- Some scripts may start servers or need free ports. Use `timeout 180` per script so a hang becomes exit `124` instead of blocking.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Discover standalone scripts | `grep -L "pytest" tests/*_test.py` | list of files (not pytest-based) |
| Run one script with bounded time | `timeout 180 python3 tests/<name>.py > /tmp/triage-<name>.log 2>&1; echo $?` | exit code recorded per script |
| Make gate | `make check; echo $?` | `0` |

## Scope

**In scope**:
- Reading any test file and the source it imports, to classify.
- `plans/003-triage-results.md` (create): the classification table.
- Test files under `tests/` ONLY for Class B fixes described in Step 4 (stale import/route/column names where the replacement is unambiguous).

**Out of scope**:
- Any source file under `src/` — this plan never changes product code.
- Installing packages (do not `pip install playwright`). Record the missing module instead.
- `tests/security_tenant_isolation_test.py` (plan 002 owns it).
- Assertions: never remove, weaken, skip, or broaden an assertion. Never add `# noqa`, `xfail`, or `skip` to hide a failure in order to pass the run.

## Steps

### Step 1: Enumerate and run
List the standalone scripts (`grep -L "pytest" tests/*_test.py`) and, for each, run `timeout 180 python3 <file> > /tmp/triage-<name>.log 2>&1; echo "$f $?"`. Record the exit code and the last 5 lines of the log.

**Verify**: a table with one row per script and an exit code. Every row has a value (0, non-zero, or `124` for timeout).

### Step 2: Classify each non-zero result
Assign exactly one class per failing script:

- **A — environment**: a missing module (`ModuleNotFoundError: playwright`), a missing binary, or a missing service. Action: none in code; record the exact missing dependency.
- **B — stale test**: the test imports a symbol that no longer exists, queries a column or route that was renamed or removed, or hardcodes an outdated path. Verify by reading the source: `grep -n "def validate_document" src/python/*.py` etc. Action: Step 4 (only if the replacement is unambiguous).
- **C — suspected regression**: the test's expectation matches documented behavior and the product code does not satisfy it (for example a 401 where the contract says 200, or a missing column that a migration should have added). Action: STOP and report (do not change tests or code).
- **D — hang/timeout**: exit `124`. Classify by reading the first stage it reached; usually A, B or C.

Write `plans/003-triage-results.md` with columns: `script | exit | class | first error line | evidence (file:line)`.

**Verify**: `grep -c "^|" plans/003-triage-results.md` → at least the number of failing scripts plus 2 header lines.

### Step 3: Confirm class C claims
For each class C script, open the cited product code and the test's assertion yourself. Only report class C if the evidence is solid. Put the evidence in the results file.

**Verify**: each class C row in the results file has a `file:line` for both the test assertion and the product code.

### Step 4: Class B fixes (test-only, optional)
For each class B script where the replacement is unambiguous (a single renamed symbol, a single renamed column with a migration showing the new name), update only the stale reference in the test. Do not change the expectations. Re-run that script.

Examples of unambiguous: `from server import validate_document` where `validate_document` now lives in a named module (`grep -rn "def validate_document" src/python`) and has the same signature.
Examples of ambiguous (do NOT fix; report): a 404 where the route might have been removed on purpose; a 401 where the auth model changed.

**Verify**: for each fixed script: `timeout 180 python3 tests/<name>.py; echo $?` → `0`.

### Step 5: Gate
**Verify**: `make check; echo $?` → `0`. `git status --short` → only `plans/003-triage-results.md` and test files you intentionally updated in Step 4.

## Test plan

This plan does not add product tests. Its output is the classification table and any updated stale references. Each Class B change must be verified by re-running its script (Step 4).

## Done criteria

- [ ] Every standalone script in `grep -L "pytest" tests/*_test.py` has an exit code recorded in `plans/003-triage-results.md`
- [ ] Every non-zero script has exactly one class (A/B/C/D) and evidence
- [ ] Every class C script has file:line evidence on both sides
- [ ] Every Class B change was re-run and exits 0, with no assertion removed or weakened (`git diff tests/` shows only import/name changes)
- [ ] `make check; echo $?` → `0`
- [ ] `git status --short` shows only in-scope files
- [ ] `plans/README.md` row for 003 updated

## STOP conditions

- A Class B fix would require changing an assertion's expected value or removing a check. STOP for that script and report.
- A script that was passing before your change now fails. Revert the change for that script and report.
- Triage finds a class C regression in a security or authorization test (for example a 401/403 mismatch, or a route that serves data without a check). STOP and report that item immediately; do not wait for the full run.

## Maintenance notes

- Reviewers: the diff under `tests/` should contain only import, route, or column-name changes; any assertion-value change is a red flag.
- Class A items should be fixed in CI setup (installing `playwright` for the scripts that need it), which is a separate decision for the maintainer.
- The triage table is the input for deciding which failing scripts to delete or convert to pytest. That is a follow-up decision for the maintainer.
