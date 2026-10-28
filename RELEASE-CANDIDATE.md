# RELEASE-CANDIDATE — Phase 8 tree, 2026-10-28

**This is a candidate record, not a release.** No tag, push, merge or PR was made (OD-3: local-only).
`VERSION_HISTORY.md` is owner-held and unchanged; the three entries this tree needs are drafted in
`artifacts/next-work/OWNER-QUEUE.md`.

The previous snapshot (2026-10-21, `pass/2026-10-21-next-work`) was replaced by this record. Its text
remains in git at `f05ee2e` if the older gate numbers are needed.

## 1. Tree state

| Field | Value |
|---|---|
| Branch | `fix/2026-10-22-open-issues` |
| HEAD | `f05ee2e` — no commit has been made since |
| Working tree | 423 changed/untracked entries (282 tracked modifications, 141 untracked) |
| Version | 0.69.0 / 0.70.0 / 0.70.1 **drafted, not applied** (Parts 4, 5 and the Phase 7 close) |
| Distribution | local only; nothing pushed, tagged or published |

Phases 1–7 are closed (`artifacts/ui-audit/fixes/STATE.md`). Phase 8 is closed through LT-8.5: LT-8.1
(quick-start verified on a clean clone), LT-8.2 (docs audited against the code), LT-8.3 (this record),
LT-8.4 (status index rebuilt) and LT-8.5 (final report, `artifacts/next-work/FINAL-REPORT.md`).

## 2. Gate matrix on this tree

Run at the Phase 7 close (`artifacts/next-work/lt-7-close/gates-all.log` →
`artifacts/next-work/gates/20261028-071637/gates.log`, plus `gates-rest-phases.log` for the nine phases
run separately).

| Gate | Signature | Result |
|---|---|---|
| build | `MIRROR_CHECK_PASSED (up_to_date=528)` · `BUILD_OK editor bundles manifests mirror (check)` | PASS |
| bundles | `ROUTE_BUNDLE_CHECK_PASSED` · `BUILD_OK bundles (check)` | PASS |
| smoke | `TOTAL pages=16 consoleErrors=0 non2xx=0` | PASS |
| layout | `UI_LAYOUT_GUARD_PASSED` (1533 checks, 0 failed, incl. `long-task`) | PASS |
| pytest | `1 failed, 200 passed` | **1 red** (below) |
| budgets | `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)` | PASS |
| lhci | `reports=16/16 minA11y=1.00` | PASS |
| csp | `CSP_CHECK_PASSED` (0 violations) | PASS |
| canvas | `CANVAS_MOTION_VERIFY_PASSED` (22 pass / 0 fail / 2 skipped) | PASS |
| important | `total=3809 ≤ pin 3809` | PASS |

**The open red is known and diagnosed.** `lt_2_6` compares an editor screenshot with a PDF raster;
Chromium prints the 420 px `@page` as 315.12 pt (420.16 px), so identical runs read 4.24–4.75 against a
locked 4.5 tolerance. This tree's close run read `pdf_mae 4.6270 > 4.5`. No threshold, fixture or
assertion was touched. Its future is an owner decision (queue row `lt_2_6`). Everything else is green.

**Independent confirmation from a clean clone** (LT-8.1, working tree overlaid on `f05ee2e`):
`collected 201 items` → `1 failed, 200 passed, 2 warnings in 610.19s`, **0 skipped** — the browser
modules ran. The only red was the same `lt_2_6`. Log:
`artifacts/next-work/lt-8-1/make-test-clean-clone.log`.

## 3. Verification recipe

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
python3 build.py all --check                 # BUILD_OK … (check)
.venv/bin/python -m pytest tests/ -q         # 1 known red: lt_2_6
.venv/bin/python tools/run-gates.py --phase all
```

`tools/run-gates.py` prefers `.venv/bin/python` and runs build → bundles → smoke → layout → pytest →
budgets → lhci → csp → canvas → important. Do **not** export `EINVITE_REQUIRE_BROWSER=1` for the pytest
phase: it turns `layers_panel_guard_test`'s tolerated harness skip into a failure.

## 4. Roadmap §8.3 — 1.0.0 criteria

| # | Criterion | Status | What is still needed |
|---|---|---|---|
| 1 | All six roadmap parts complete | **Open** | Part 3 rows 3.7, 3.9, 3.10, 3.11 and Part 6 rows 6.3, 6.4, 6.6 (`docs/ROADMAP-RECONCILIATION-2026-10-24.md`) |
| 2a | Load test run with real numbers | **Not run** | Copy `docs/certification/LOAD-TEST-RESULT-TEMPLATE.md`, run the k6 plan on the reference deployment, record results |
| 2b | DR drill run, signed report in `docs/ops/` | **Not run** | Execute `docs/ops/BACKUP-DR.md` §9, file `docs/ops/drill-reports/<YYYY>-Q<n>.md` from its §9.4 template |
| 2c | Native platform matrix executed | **Pending** | All six N1–N6 rows in `docs/certification/CERTIFICATION.md` §1 are `pending` |
| 2d | Browser matrix executed | **Pending** | All six B1–B6 rows in §2 are `pending` |
| 2e | Pen test commissioned, Critical/High fixed | **Not commissioned** | Copy `docs/certification/PEN-TEST-INTAKE-TEMPLATE.md`, commission an independent firm (ASVS 5.0.0 L2), file the report |
| 3 | `CERTIFICATION.md` signed by maintainer + auditor | **Unsigned** | Every §1–§5 row is `pending`; the signature fields are empty |
| 4 | Tenant isolation suite passes | **Yes** | `tests/security_tenant_isolation_test.py` is green in the suite above |
| 5 | Field encryption live in production | **Not attestable here** | Code, migration and rollback exist (LT-7.2 step 4); “live in production” needs a deployed instance |
| 6 | Analytics has ≥ 30 days of real data | **No** | Needs a production deployment collecting for a month |

Criteria 4 is met; 5 is implemented but cannot be attested from this checkout; 1–3 and 6 are open.

## 5. Known limitations carried into the candidate

- **`lt_2_6`** — the one pytest red, as diagnosed above.
- **Browser coverage** — the suite runs Chromium only; the six-browser matrix is a separate manual
  execution and remains `pending`.
- **Icon set** — no sprite exists (UX-4 was never executed); the shell uses text glyphs. Documented in
  `docs/ARCHITECTURE.md` §7.1 and queued for the owner.
- **Khmer display fonts** — the pack substitutes registered faces for 12 of its 14 requested families;
  D-4 (real display faces) was not executed (`docs/FONT_LICENSES_AND_REGISTRY.md`).
- **Windows/macOS** — the native matrix is unexecuted; the only verified host for this candidate is
  Ubuntu 24.04 / Python 3.12.
- **External evidence** — load test, DR drill and penetration test are templates only; none has been run
  or commissioned.

## 6. Owner decisions before any release

1. **OD-3** — whether to commit/push this tree at all (nothing has been committed since `f05ee2e`).
2. **`VERSION_HISTORY.md`** — apply 0.69.0, 0.70.0 and 0.70.1 from `OWNER-QUEUE.md`, or revise them.
3. **`lt_2_6`** — widen/redesign the metric, or accept a documented red at close.
4. **UX-4 / D-4** — run the icon and font work, or ship without them (the docs record their absence).
5. **External engagements** — commission the load test, the DR drill and the penetration test; none can
   be produced by an agent from this checkout.

Only then does `git tag v1.0.0` become a question, and this file does not propose one.
