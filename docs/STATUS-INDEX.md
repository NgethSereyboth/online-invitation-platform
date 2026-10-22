# STATUS-INDEX — work orders, ledgers, and audits

Verdicts as of 2026-10-21 (`pass/2026-10-21-next-work` pushed at `6f7de27`; code HEAD
`11e549f`, docs HEAD `8d256e3` plus the harness/docs follow-up that carries this line; legs
`ec0cf91` a11y, `6a30d9e` i18n, `8952381`/`cd56ac0` CI, `837042f`+`15554e3`+`8d256e3` docs,
`ca53dbe` contrast fix, `11e549f` toolbar reachability). One row per document: its standing
today. Keep dated.

**Update 2026-10-22 (FB-12):** an approved continuation work order,
[`FREEBUFF-OPEN-ISSUES-2026-10-21.md`](../FREEBUFF-OPEN-ISSUES-2026-10-21.md), is being
executed on the new local branch `fix/2026-10-22-open-issues` from `6f7de27`. Owner answers
2026-10-22: OD-1/OD-2 approved, OD-3 local-only (no push/PR/merge/tag), OD-4/OD-5 confirmed,
OD-7 Option A, OD-8 deferred; i18n audit-first; v14 non-blocking. FINAL HEAD for that pass:
see `git log fix/2026-10-22-open-issues` (this index is not HEAD-bound going forward).

| Document | Verdict | Date note |
|---|---|---|
| `NEXT-WORK-TASK.md` | **authoritative** — the live work order (phases 0–7); NW-0–NW-5 executed, NW-6.1–6.6 executed same-day (`nw-6-3/FINDING.md`), NW-3.3–3.5 + NW-2 owner-gated. NW-5.2 closed per FB-13 (2026-10-22 closure note inside) | 2026-10-21 |
| `FREEBUFF-OPEN-ISSUES-2026-10-21.md` (repo root) | **active work order, approved 2026-10-22** — the 22-item follow-up (FB-01…FB-22) being executed on `fix/2026-10-22-open-issues`. Owner answers: OD-1/2/7 approved, OD-4/5 confirmed, OD-8 deferred, v14 non-blocking, release local-only | 2026-10-22 |
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
