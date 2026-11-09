# Sprint 2 Summary — Hardening and Polish

**Branch:** `improve/sprint-2-hardening-and-polish`
**Base:** `main` at `140aa77`
**Commits:** `d639471` (analysis gate), `eed6bb6` (header-injection properties),
`492cd20` (analysis-gate wiring)
**Merge status:** not merged; no push or PR created in this sprint.

## Completed tasks

### 1. Baseline-diff analysis gate — `d639471`

- Pinned `pytest-cov==7.1.0`, `vulture==2.16` and `radon==6.0.1`.
- Added `make analyze` and `make coverage`.
- Added `tools/analyze.py` and `tools/analysis_baseline.json`.
- Corrected the stale complexity claim: the real baseline on `main` is **213**
  functions/methods above CC 10, not 157. The 11 high-confidence vulture findings
  are also recorded.
- The gate fails on new above-threshold functions, increased complexity, or new
  high-confidence vulture findings; resolved findings do not fail it.
- `docs/QUALITY-GATES.md` records the baseline and regeneration rule.

**Evidence:** `tests/tooling_analysis_test.py` 5 passed; a temporary new
complex function made the gate return non-zero (tool exit 1, `make` exit 2);
after removal `make analyze` printed `ANALYSIS_OK`.

### 2. Header-injection properties — `eed6bb6`

- `safe_header_value()` now strips **CR, LF and NUL** before the 4,096-byte cap.
  The NUL gap was a real hardening defect in the `Location` path.
- Added `hypothesis==6.170.15` and generated tests for CR/LF/CRLF/NUL, quotes,
  semicolons, backslashes and Unicode line separators.
- Coverage includes `safe_header_value`, `Location`, `_safe_inline_filename`,
  `send_download`, `send_binary`, `send_media_binary`, session cookies and the
  impersonation cookie.
- Ordinary filenames remain unchanged; hostile filenames remain quoted and
  single-line.

**Evidence:** red run recorded three genuine NUL failures; the fourth red
assertion was a test-helper assumption (`attachment;` vs `inline;`) and was
corrected. Green suite: `header_injection_property_test.py`,
`security_media_headers_test.py`, `tooling_analysis_test.py`,
`security_reflected_injection_test.py` — **16 passed**.

### 3. Analysis gate wired into local and CI runners — `492cd20`

- Closed the integration gap: the gate existed only as `make analyze`, so
  neither the local `run-gates.py` matrix nor CI could catch a new finding.
- Added an `analyze` phase after `bundles` with the fail-closed `ANALYSIS_OK`
  marker, plus a `make analyze` step in the Tests workflow.
- Documented the wiring in `docs/QUALITY-GATES.md` and `tools/README.md`.

**Evidence:** the new wiring test was red first; `tests/tooling_analysis_test.py`
**6 passed**; `tests/test_runner_manifest.py` and
`tests/lhci_invocation_test.py` **4 passed**; `run-gates.py --phase analyze`
printed `PASS analyze` / `GATES_PASSED`; the workflow parsed with both PyYAML
and `js-yaml`.

## Rejected or deferred tasks

| Task | Decision | Why |
|---|---|---|
| Analytics phase-4 order dependence | Rejected | Not reproducible: 1/1 alone, 6/6 in the full analytics file. |
| Dashboard query-plan matrix | Deferred | Depends on unmerged PR #27's query rewrite and test. |
| Full-page dashboard baseline | Deferred | Depends on PR #27's visual harness and fixed seed. |
| Content-hashed bundles | Deferred | Design/prototype work; not a bounded fix. |
| `server.py` decomposition | Rejected | Architectural; explicitly forbidden. |
| Redis multi-worker rate limiting | Deferred | Needs infrastructure and deployment contract. |
| Staging DAST / live HSTS-CSP | Deferred | Needs staging credentials and an operations owner. |
| User-visible accessibility work | Deferred | Already on PR #27; avoid two competing fixes. |

Details: `docs/FUTURE-IMPROVEMENTS.md`.

## Verification evidence

| Check | Result |
|---|---|
| `python3 build.py all --check` | PASS — `BUILD_OK`, 730 mirror files up to date |
| `npm run lint` | PASS |
| `npm run lint:security` | PASS |
| `make analyze` | PASS — 213/213 complexity, 11/11 vulture |
| `make coverage` target | Configured; `pytest-cov` installed and verified by `pip check` |
| `python3 -m compileall -q src/python tests tools` | PASS |
| `pip check` | PASS |
| Focused pytest (property + media + tooling + reflected) | **16 passed** |
| Wiring pytest (`tooling_analysis_test.py`) | **6 passed** |
| Runner/LHCI tests (`test_runner_manifest.py`, `lhci_invocation_test.py`) | **4 passed** |
| `tools/run-gates.py --phase analyze` | PASS — `GATES_PASSED` |
| Tests workflow YAML parse | PASS — PyYAML 6.0.1 and `js-yaml` |
| Analytics ingestion | 6 passed; phase 4 alone 1 passed |
| `git diff --check` | PASS |
| Full pytest suite (before wiring task) | **250 passed in 1120.81s (18:40)**, exit 0 |
| Playwright `13-security.spec.ts` (chromium) | **8 passed** on a disposable 4310 server; server stopped, 4175 untouched |

Artifacts: `artifacts/sprint2/` (gitignored, local to this review machine).

## Remaining risks

- The analysis gate tolerates the existing 213/11 debt; it prevents new debt but
  does not reduce it.
- The NUL change is covered with fake-handler unit tests, not a live browser or
  production origin. No live deployment or HSTS/CSP work was attempted.
- The new Hypothesis test requires `requirements-dev.txt` in CI; it is not a
  runtime dependency.
- The analytics order dependence was not reproduced; the rejection is evidence
  for this base, not a guarantee under every future test order.
- The Playwright security spec passed, but the NUL header behavior is covered
  only by unit/property tests; a browser cannot be made to send NUL header
  values through normal navigation.
- The full suite passed once before the wiring task; the wiring change is
  covered by its targeted and runner tests, not by a second 18-minute run.
- The 18:40 suite runtime is slow; keep an eye on duration if the suite grows
  further.

## Recommended Sprint 3

1. Reconcile and review PR #27, then extend the query-plan matrix on its
   set-membership rewrite.
2. Reduce the 213-entry complexity baseline by a bounded set (for example the
   top 10 functions) and keep `make analyze` green.
3. Add the fixed-seed full-page dashboard fixture after PR #27's harness lands.
4. Add a staging-only HSTS/CSP assertion to the authenticated DAST workflow.
5. Keep the analytics suite in the order-dependence watch list; only reopen if a
   reproducible failing order appears.
