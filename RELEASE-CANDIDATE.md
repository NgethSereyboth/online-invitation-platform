# RELEASE-CANDIDATE — Stage F tree, 2026-10-29

**This is a candidate record, not a release.** No tag, push, merge or PR was made (OD-3: local-only).
`VERSION_HISTORY.md` now carries every entry through **0.70.12** (D-12 superseded the owner-held rule
for that file); nothing is drafted in `OWNER-QUEUE.md` any more.

The previous snapshot (2026-10-28, tree `f05ee2e`) was replaced by this record. Its text remains in git
at `f05ee2e` if the older gate numbers are needed.

## 1. Tree state

| Field | Value |
|---|---|
| Branch | `fix/2026-10-22-open-issues` |
| Gate head | `4880fcb` — the Stage E matrix; **no product code changed after it** |
| Docs head at writing | `2e50379` (architecture, index, this record and the final report are docs-only) |
| Working tree | **clean tracked tree**; the only untracked paths are the two audit harnesses `tools/ui-audit.py` / `tools/ui-audit-report.py` and the git-ignored `FREEBUFF-*.md` owner channel |
| Version | **0.70.12** — 0.68.6 … 0.70.12 all recorded (no tag) |
| Distribution | local only; nothing pushed, tagged or published |

Phases 1–7 and Stages A–E are closed (`artifacts/ui-audit/fixes/STATE.md`). Stage F is closed through
LT-8.5: LT-8.1 (quick-start re-verified on a clean clone of this tree), LT-8.2 (docs refreshed),
LT-8.3 (this record), LT-8.4 (index contradictions resolved) and LT-8.5 (final report,
`artifacts/next-work/FINAL-REPORT.md`).

## 2. Gate matrix on this tree

One `--phase all`, run at the Stage E close on `4880fcb`
(`artifacts/next-work/gates/20261029-203542/gates.log`): `GATES_PASSED`, `stoppedAt: null`, all ten
phases exit 0. Only docs commits followed it (`53453d7`, `ac32a5f`, `e11e5c8`).

| Gate | Signature | Result |
|---|---|---|
| build | `MIRROR_CHECK_PASSED` · `BUILD_OK editor bundles manifests mirror (check)` | PASS |
| bundles | `ROUTE_BUNDLE_CHECK_PASSED` · `BUILD_OK bundles (check)` | PASS |
| smoke | `TOTAL pages=16 consoleErrors=0 non2xx=0` | PASS |
| layout | `UI_LAYOUT_GUARD_PASSED` | PASS |
| pytest | `223 passed, 2 warnings in 726.27s` | PASS |
| budgets | `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)` | PASS |
| lhci | `LHR reports=16/16 minA11y=1.00` | PASS |
| csp | `CSP_CHECK_PASSED` (0 violations) | PASS |
| canvas | `CANVAS_MOTION_VERIFY_PASSED` (22 pass / 0 fail / 2 skipped) | PASS |
| important | `total=3791 ≤ pin 3791` | PASS |

**No open pytest red.** The `lt_2_6` boundary that this record carried on 2026-10-28 was not a
rasteriser flake: D-5 found two product defects in `printAllPages()` — the app's muted-paragraph rule
repainted the print document, and the print page replayed the 900 ms entrance animation — and fixed
both without touching the tolerance. PDF MAE is now byte-identical **3.5922** across 40 post-fix runs.

### 2.1 Independent confirmation from a clean clone (LT-8.1)

A plain `git clone --branch fix/2026-10-22-open-issues` of this tree at **`e11e5c8`**, following only
the README's Development block, on the same Ubuntu 24.04 / Python 3.12 host:

| Step | Command | Time |
|---|---|---|
| 1 | `git clone --branch fix/2026-10-22-open-issues … einvite-clean-8-1` | 55 s |
| 2 | `python3 -m venv .venv` | 4 s |
| 3 | `.venv/bin/pip install -r requirements-dev.txt` | 14 s (warm pip cache) |
| 4 | `.venv/bin/python -m playwright install chromium` | 1 s (browser already cached) |
| 5 | `python3 build.py all --check` → `MIRROR_CHECK_PASSED (up_to_date=530)` · `BUILD_OK … (check)` | 2 s |
| 6 | `make test` → **`223 passed, 2 warnings in 661.90s (0:11:01)`**, 0 failed, 0 skipped | 662.4 s |
| 7 | `PYTHONPATH=src/python:. EINVITE_ALLOW_NO_SCANNER=1 .venv/bin/python src/python/server.py --port 8951` → `/` and `/designer.html` both `200`, Khmer font `shaping=True` | 4 s to first 200 |

The clone's tracked tree stayed clean through the run (`build.py --check` wrote nothing); the only new
files were the git-ignored `.env` the server generates on first run and a `server.pid` the check
itself wrote. **No README or script fix was needed** — every documented step worked as written. Logs:
`/tmp/einvite-clean-8-1/` (`make-test.log`, `build-check.log`, `server.log`).

## 3. Verification recipe

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
python3 build.py all --check                 # BUILD_OK … (check)
.venv/bin/python -m pytest tests/ -q         # 223 passed on this tree
.venv/bin/python tools/run-gates.py --phase all
```

`tools/run-gates.py` prefers `.venv/bin/python` and runs build → bundles → smoke → layout → pytest →
budgets → lhci → csp → canvas → important. Do **not** export `EINVITE_REQUIRE_BROWSER=1` for the pytest
phase: it turns `layers_panel_guard_test`'s tolerated harness skip into a failure.

## 4. Roadmap §8.3 — 1.0.0 criteria

| # | Criterion | Status | What is still needed |
|---|---|---|---|
| 1 | All six roadmap parts complete | **Open** | The reconciliation reads **31 `exists` / 6 `partial` / 0 `absent`**; the six partials are 3.7, 3.10, 3.11 (Part 3) and 6.3, 6.4, 6.6 (Part 6) — backlog or blocked on owner Khmer (`docs/ROADMAP-RECONCILIATION-2026-10-24.md`) |
| 2a | Load test run with real numbers | **Not run** | Copy `docs/certification/LOAD-TEST-RESULT-TEMPLATE.md`, run the k6 plan on the reference deployment, record results |
| 2b | DR drill run, signed report in `docs/ops/` | **Not run** | Execute `docs/ops/BACKUP-DR.md` §9, file `docs/ops/drill-reports/<YYYY>-Q<n>.md` from its §9.4 template |
| 2c | Native platform matrix executed | **Pending** | All six N1–N6 rows in `docs/certification/CERTIFICATION.md` §1 are `pending` |
| 2d | Browser matrix executed | **Pending** | All six B1–B6 rows in §2 are `pending` |
| 2e | Pen test commissioned, Critical/High fixed | **Not commissioned** | Copy `docs/certification/PEN-TEST-INTAKE-TEMPLATE.md`, commission an independent firm (ASVS 5.0.0 L2), file the report |
| 3 | `CERTIFICATION.md` signed by maintainer + auditor | **Unsigned** | Every §1–§5 row is `pending`; the signature fields are empty |
| 4 | Tenant isolation suite passes | **Yes** | `tests/security_tenant_isolation_test.py` is green in the matrix above |
| 5 | Field encryption live in production | **Not attestable here** | Code, migration and rollback exist and ship **on** by default (E-3); “live in production” needs a deployed instance |
| 6 | Analytics has ≥ 30 days of real data | **No** | Needs a production deployment collecting for a month |

Criterion 4 is met; 5 is implemented but cannot be attested from this checkout; 1–3 and 6 are open.

## 5. Known limitations carried into the candidate

- **Canvas visual gate — NOT RUN.** The frozen baseline (`artifacts/canvas-motion/baseline/`) lives on
  the owner's Windows box; the motion gate above is the behavioural one (22/0/2), not pixel comparison.
- **Real-device checklist — SKIP.** `docs/qa/DEVICE-CHECKLIST.md` is ready, but A-4 has no
  phone-reachable host, so its phone-only rows cannot run yet.
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
- **Demo is local only** — `http://127.0.0.1:8941/` at `53453d7`; no phone-reachable host (A-4).
- **Two owner-visible product findings stay open** — public invitations print three `HTTP 401` blocks
  from the guest features (`signup-sheets`, `polls`, `album` fetch host routes anonymously), and the
  guest-row Edit/Link/QR/Check-in/Remove buttons have no handlers. Both are `OWNER-QUEUE.md` rows with
  evidence; neither is a layout or gate failure.

## 6. Owner decisions before any release

1. **OD-3** — whether to push this branch at all; the work is committed locally only.
2. **`lt_2_6`** — closed by fixing the product (D-5); no threshold decision is left.
3. **UX-4 / D-4** — run the icon and font work, or ship without them (the docs record their absence).
4. **A-4** — connect a Python-capable host (Render Blueprint needs your account and a push) so the demo
   and the device checklist can run on a phone.
5. **External engagements** — commission the load test, the DR drill and the penetration test; none can
   be produced by an agent from this checkout.
6. **UI audit fix pass** — `FREEBUFF-UI-AUDIT-FIX-ORDER-2026-10-29.md` is open (the corpus is done, the
   fixes are not started).

Only then does `git tag v1.0.0` become a question, and this file does not propose one.
