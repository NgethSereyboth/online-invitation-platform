# RELEASE-CANDIDATE — session end 2026-10-21

**OD-3 update 2026-10-21 (owner): the push was approved after this snapshot was written.** The
pre-push state below is kept for the record. Do not tag or edit `VERSION_HISTORY.md` without an
explicit owner decision.

## HEAD and commits

- Branch: `pass/2026-10-21-next-work` (cut from `50721ef` per the continuation §7).
- `ec0cf91` — fix(a11y): all six WCAG 2.2 AA code asks (`NW-1.1`–`NW-1.6`).
- `6a30d9e` — feat(i18n): bilingual `<option>` labels (14), CSV reconcile archive, Khmer sweep (NW-4.1–4.4).
- `8952381` — test(ci): portable gate runner + allowlist startup race fix (NW-5).
- `cd56ac0` — test(ci): the allowlist implementation file omitted from `8952381`.
- `837042f` — docs: RELEASE-CANDIDATE reader + STATUS-INDEX.
- `ca53dbe` — fix(a11y): dashboard profile gradient light stop passes AA (white 4.56).
- `11e549f` — fix(a11y): canvas toolbar overflow scroll discoverable from 701px up (NW-6.3).
- `15554e3` — docs: STATUS-INDEX + RELEASE-CANDIDATE refreshed to the code HEAD.
- `8d256e3` — docs: per-commit branch review note for reviewers.
- final commit — test(tools)/docs: the eight verification harnesses this pass used (plus the
  continuation brief) and docs HEAD/count corrections.
- Untracked owner work preserved untouched (78 paths, incl. `.claude/`, `data/`, review PNGs);
  `wip/2026-10-21-backup` branch untouched.

## Gate matrix at this HEAD (exact commands + evidence)

| Gate | Command | Result |
|---|---|---|
| Build | `python3 build.py all --check` → exit 0 (`BUILD_OK… MIRROR_CHECK_PASSED (up_to_date=327)`) | PASS |
| Bundles | `python3 build.py bundles --check` → exit 0 (`ROUTE_BUNDLE_CHECK_PASSED`) | PASS |
| Smoke | `node tools/page-errors.mjs --all` → `TOTAL pages=16 consoleErrors=0 non2xx=0` | PASS |
| LHCI | `npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js` → 16/16 reports, **a11y 1.00**, budgets pass | PASS |
| Bilingual checker | `python3 scripts/check-bilingual-consistency.py` → exit 0 (`OK: … passed.`) | PASS |
| Full pytest (default capture) | `PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/ -q` → **157 passed / 0 failed**, three consecutive runs (4:30 / 4:28 / 4:28) — FB-26 | PASS |
| Canvas acceptance | frozen harness `--phase all` (absolute `--output`) → `pass=22 fail=0 skipped=2`, `CANVAS_MOTION_VERIFY_PASSED` | PASS |
| Canvas perf | env-blocked on this machine (3 launch modes, presentation-quantized timings; `inputToPaintMs` 11.5 under budget) | NOT VERIFIED HERE |
| Canvas visual | frozen baseline absent (`artifacts/canvas-motion/baseline/**` stayed on the Windows box) | NOT RUN |
| Focus-obscured (NW-1.1) | `tools/a11y-focus-obscured.py` → 92 controls, 0 rows, 4 viewports × light/dark | PASS |
| Target size (NW-1.5) | `tools/a11y-target-size.py` → 24×24 desktop hit box, 44×44 mobile, 2 runs | PASS |
| Reorder keyboard (NW-1.2) | `tools/page_reorder_keyboard_check.py` → 8/8 | PASS |
| Option labels (NW-4.1) | `tools/option_labels_i18n_check.py` → 0 failed (2 pages × 6 checks) | PASS |
| Khmer sweep (NW-4.4) | `tools/khmer-visual-sweep.py` → 21 shots, 0 failures | PASS |
| Gate runner (NW-5.3) | `tools/run-gates.py --phase all` → 7/7 phases **PASS**, `GATES_PASSED` (log `artifacts/next-work/gates/20261022-184517/`) — FB-26 | PASS |

The single pytest failure is the documented `v27_3_5` README digest pin — **OD-7**, content-identical
CRLF/LF hash; every other baseline red was fixed (allowlist race ×2) or remains environment-bound.

## Remaining owner decisions

OD-1 (CSS cleanup), OD-2 (dashboard parity), OD-3 (push/release), OD-7 (digest pin),
OD-8 (11 Khmer strings) — evidence and recommendations in
[artifacts/next-work/DECISIONS.md](artifacts/next-work/DECISIONS.md).

## Known limitations

- Canvas perf + visual gates need the Windows box (or the owner copying
  `artifacts/canvas-motion/baseline/` here).
- Files only ever measured against `tools/serve-gzip.py` (no production hosting evidence in
  this pass; `deploy/sites/` is owner work, untouched).
- NW-6.3–6.6 (floating controls, motion audit, contrast sweep, privacy headroom) executed
  same-day (see `artifacts/next-work/nw-6-3/FINDING.md`): one reachability defect fixed in
  `11e549f`, one gradient AA residual fixed in `ca53dbe`; NW-6.6 headroom measured (139 KB
  of 174 KB budget); NW-6.4 reduced-motion contract verified via
  `tests/canvas_motion_contract_test.py` (2/2).
- RILL-WALKTHROUGH end-to-end flow not executed this session (no throwaway account flow run);
  documented as not run, not assumed.

## Push instruction (resolved 2026-10-22)

**OD-3 answered 2026-10-22:** the branch WAS pushed at `6f7de27`; `main` remains
`50721ef`; no tag and no `VERSION_HISTORY.md` edit. **All further work uses local
commits only — no push, no PR, no merge, no tag** until the owner explicitly orders
otherwise. The pre-push snapshot below is preserved for the record. (FB-22)

---

## 2026-10-22 continuation addendum (`fix/2026-10-22-open-issues`, FB-12/22/15)

Follow-up pass over the owner-approved work order
[FREEBUFF-OPEN-ISSUES-2026-10-21.md](FREEBUFF-OPEN-ISSUES-2026-10-21.md).
Scope: local commits only (OD-3). State at the pass end:

| Gate | Command | Result |
|---|---|---|
| Build | `python3 build.py all --check` | PASS (exit 0) |
| Bundles | `python3 build.py bundles --check` | PASS (`ROUTE_BUNDLE_CHECK_PASSED`) |
| v55 route-weight budget (run-gates `budgets` phase, FB-08) | `.venv/bin/python tools/run-gates.py --phase budgets` | PASS — `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)`; the FB-03 admin regression is fixed |
| v14 aspirational budgets | `python tests/v14_performance_budget_test.py` | **KNOWN RED, non-blocking** (owner answer 2026-10-22, OD-6): `AssertionError: ('editor','index.html','styles',2,1)` — aspirational count; see [docs/perf/v14-decision-note.md](docs/perf/v14-decision-note.md) |
| Full pytest (default capture) | `PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/ -q` | **146 passed / 0 failed in 4:03** (first fully green run incl. OD-7 fix FB-04 + FB-05/08 additions). Repeat runs: see FB-15 matrix |
| Security scan | pip-audit `docs/requirements-production.txt` | PASS — clean after the Pillow 13.0.0 bump (FB-01) |
| npm audit | `npm audit` | **0 vulnerabilities** after the @lhci/cli removal (FB-10); 17 → 0 locally. GitHub Dependabot alert closure is deferred to a future push |
| Bilingual checker | `scripts/check-bilingual-consistency.py` | PASS (fallback allowed; FB-14 audit recorded, nothing translated) |
| LHCI clean-checkout autorun | `npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js` | PASS — 16/16 URLs, a11y 1.00, reports under `.lighthouseci/reports` (FB-02) |

The scope of "GATES_PASSED" claims in this document is per-phase (each row names the exact
phase run); no single `--phase all` runner claim is made here.

Owner decisions carried into the ledgers (2026-10-22): OD-1 and OD-2 approved
(implementation deferred to FB-19/FB-20, not in this pass's branch), OD-3 local-only,
OD-4/OD-5 confirmed, OD-7 Option A (implemented, FB-04), OD-8 deferred, i18n audit-first
(FB-14), v14 non-blocking (FB-11).

### FB-15 final matrix (2026-10-22, same branch)

Every row has a fresh run behind it; full commands, exit codes and log paths are in
[artifacts/next-work/fb-15/RESULTS.md](artifacts/next-work/fb-15/RESULTS.md).

- `tools/run-gates.py --phase all` → **all 7 phases green** (build, bundles, smoke
  16/16, pytest 146/0 in 248.44s, budgets, lhci, canvas 22/0/2):
  `artifacts/next-work/gates/20261022-095502/summary.json`.
- Fresh LHCI autorun (`npx --yes @lhci/cli@0.15.1`): 16/16 URLs, **a11y 1.00 on all 16**,
  budget assertions pass (`fb-15/lhci-autorun.log`, `fb-15/lhci-fresh-scores.json`).
  The runner's own lhci phase is assert-only against prior reports — row #8 of the
  RESULTS matrix records that distinction.
- v14 rerun: still the documented known red (exit 1, non-blocking per the owner answer).
- pip-audit: production **clean**; dev/test clean after lifting the test-toolchain Pillow
  pin to `>=13,<14` in `docs/requirements-test.txt` (same 13.x as the installed, fully
  tested environment; pre-fix red log kept in `fb-15/pip-audit-dev.log`).
- npm audit: **0 vulnerabilities**. GitHub Dependabot alert state: not verifiable from
  this machine — recorded as NOT RUN, not claimed.
- `git status` at matrix time: only the 79 owner/work-order/evidence untracked paths;
  no accidental staging; no push/PR/merge/tag performed (OD-3).

Verdict: the release candidate is evidence-complete on this Linux box; the explicit
non-gating remainder is v14 (quarantined), canvas visual/perf (Windows box) and the
GitHub-side alert UI.

## Gate-matrix addendum — 2026-10-22 evening (FB-26)

The rows above were the 2026-10-21 snapshot. Re-run in full at `6fa3f48` after
FB-23/24/25 (`tools/run-gates.py --phase all` → **`GATES_PASSED`**, 7/7). Signature
lines, per phase: `BUILD_OK` + `MIRROR_CHECK_PASSED (after sync)`; `ROUTE_BUNDLE_CHECK_PASSED`;
`TOTAL pages=16 consoleErrors=0 non2xx=0`; `157 passed in 269.44s`; 
`V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)`; `Done running Lighthouse!`
with `reports=16/16 minA11y=1.00`; `pass=22 fail=0 skipped=2` + `CANVAS_MOTION_VERIFY_PASSED`.

**Test-count reconciliation (FB-26):** 146 (FB-15) + 9 (`config_adapter_test.py` from
`829af12`) + 2 (`lhci_invocation_test.py` from FB-23) = **157**. The "162 passed" figure
in `fb-20/RESULTS.md` is not reproducible at any HEAD in this session and is superseded.

**Correction (FB-23):** the earlier "LHCI assert → exit 0" row described a phase that ran a
squatted placeholder package and never started Lighthouse. The LHCI row now names the real
phase and its completion line.
