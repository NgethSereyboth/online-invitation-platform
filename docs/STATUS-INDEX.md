# STATUS-INDEX — work orders, ledgers, and audits

**Update 2026-10-25 (LT-1.11, FB-77):** the queue of record is now
[`FREEBUFF-LONG-TERM-PLAN-2026-10-24.md`](../FREEBUFF-LONG-TERM-PLAN-2026-10-24.md) with
[`FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md`](../FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md) as the run
contract. It supersedes the round-5 order/prompt and every earlier queue. Phase 1 is closed at
FB-77: all 17 review shots plus six previews are in `artifacts/next-work/review-lt1/after/` with a
pair table, and the phase-close matrix is `GATES_PASSED` (build, bundles, smoke 16/0/0, layout
1533/0, pytest 157, budgets 6/6, lhci 16/16 a11y 1.00, csp, canvas 22/0/2, important 3816 ≤ 3823) in
`artifacts/next-work/gates/20261025-121010/`. The next item is LT-2.1. Work stays local-only
(OD-3); no push, PR, merge or tag.

Verdicts as of 2026-10-21 (`pass/2026-10-21-next-work` pushed at `6f7de27`; code HEAD
`11e549f`, docs HEAD `8d256e3` plus the harness/docs follow-up that carries this line; legs
`ec0cf91` a11y, `6a30d9e` i18n, `8952381`/`cd56ac0` CI, `837042f`+`15554e3`+`8d256e3` docs,
`ca53dbe` contrast fix, `11e549f` toolbar reachability). One row per document: its standing
today. Keep dated.

**Update 2026-10-23 (FB-33):** the second order,
[`FREEBUFF-REFINEMENT-ORDER-2026-10-22.md`](../FREEBUFF-REFINEMENT-ORDER-2026-10-22.md) (FB-23…FB-34,
untracked owner file), has been executed on the same branch: CSP inline handlers fixed (FB-24),
bilingual scan scripts, FB-26/27 evidence + `core.config` disposition (OD-9 open), Wave 2 visual
fixes FB-28/29/30 committed per bug, `run-gates.py` carries the layout, csp and important
(`!important` ratchet, pin 3823) phases, and the FB-34 fresh-account RILL is green with the
OD-11 RSVP path measured. Ledger truth-up landed in the FB-33 docs commit; owner decisions
OD-10/OD-11/OD-12 are open in `artifacts/next-work/DECISIONS.md`.

**Update 2026-10-22 (FB-12):** an approved continuation work order,
[`FREEBUFF-OPEN-ISSUES-2026-10-21.md`](../FREEBUFF-OPEN-ISSUES-2026-10-21.md), is being
executed on the new local branch `fix/2026-10-22-open-issues` from `6f7de27`. Owner answers
2026-10-22: OD-1/OD-2 approved, OD-3 local-only (no push/PR/merge/tag), OD-4/OD-5 confirmed,
OD-7 Option A, OD-8 deferred; i18n audit-first; v14 non-blocking. FINAL HEAD for that pass:
see `git log fix/2026-10-22-open-issues` (this index is not HEAD-bound going forward).

| Document | Verdict | Date note |
|---|---|---|
| `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` | **authoritative queue** — Phase 1 closed at FB-77; Phase 2 (LT-2.1) is next. Work local-only | 2026-10-25 |
| `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` | **authoritative run contract** — autonomous loop, one item/one commit, no owner questions | 2026-10-24 |
| `NEXT-WORK-TASK.md` | **superseded** — phases 0–7; NW-0–NW-5 executed, NW-6.1–6.6 executed same-day (`nw-6-3/FINDING.md`), NW-3.3–3.5 + NW-2 owner-gated; NW-5.2 closed per FB-13. Kept for history; the long-term plan decides now | 2026-10-21 |
| `FREEBUFF-OPEN-ISSUES-2026-10-21.md` (repo root) | **completed/superseded** — FB-01…FB-22 landed on `fix/2026-10-22-open-issues`; later passes and the long-term plan supersede its queue | 2026-10-22 |
| `FREEBUFF-UI-REFINEMENT-PROMPT.md` | historical — described the closed 2026-10-21 visual pass (`1cd09d2`); do not re-run | historical |
| `FREEBUFF-CONTINUATION-2026-10-21.md` | historical — the continuation brief that produced this pass; superseded by this pass's output | 2026-10-21 |
| `CANVA-UI-TASK.md` | historical — closed at `37bfc8d`, all boxes ticked | 2026-10-15 era |
| `DESIGN-FIX-TASK.md` / `DESIGN-FIX-REPORT.md` | historical — pass closed at `708e675` | earlier |
| `UI-VISUAL-AUDIT-FIX-TASK.md` | historical — superseded by later sweeps; §0/§2 worked-through; its documented heuristic false positives remain the chase-list | earlier |
| `CANVAS-MOTION-FIX-TASK.md` | historical — canvas motion fix closed/accepted `d9818a6` | earlier |
| `CANVA-SMOOTHNESS-BRIEF.md` | **authoritative (frozen)** — read-only contract for canvas gates | frozen |
| `docs/a11y/WCAG-2.2-AA-AUDIT.md` | **authoritative (current)** — delta audit §5 six code asks; all six closed in `ec0cf91`, plus the `ca53dbe` gradient AA close and the `11e549f` toolbar reachability close | 2026-10-21 |
| `docs/a11y/WCAG-AA-AUDIT.md` | historical audit (correct), now carrying a dated 2.5.8 labelling correction | 2026-10-21 |
| `docs/a11y/RESPONSIVE-AUDIT.md` | historical, its 2.5.5-as-AA label rows corrected to 2.5.8 (AA) | 2026-10-21 |
| `docs/reviews/*` status ledgers | historical; `STATE.md` (`artifacts/ui-audit/fixes/`) is the live continuation ledger — note it was **reconstructed** on 2026-10-21 on the Linux box | 2026-10-21 |
| `docs/i18n/TRANSLATIONS.csv` | **authoritative** ledger of translation states; updated 2026-10-21 (286 rows archived `stale-*`, none deleted) | 2026-10-21 |
| `docs/ROADMAP*.md` / `plans/001–003` | historical — completed/blocked; out of continuation scope | earlier |

## Superseded-report banners

The bookkeeping pass of 2026-10-20 already banners the earliest three; as of 2026-10-21 the
remaining historical docs above are listed here rather than individually re-bannered, because
their content is not contradicted — only their currency. If a doc's instructions ever conflict
with `NEXT-WORK-TASK.md`, this index decides: **NEXT-WORK-TASK.md wins**.
