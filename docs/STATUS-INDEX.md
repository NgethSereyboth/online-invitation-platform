# STATUS-INDEX — work orders, ledgers, and audits

**Update 2026-10-25 (LT-2.7, FB-82):** the queue of record is
[`FREEBUFF-LONG-TERM-PLAN-2026-10-24.md`](../FREEBUFF-LONG-TERM-PLAN-2026-10-24.md) with
[`FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md`](../FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md) as the run
contract. It supersedes the round-5 order/prompt and every earlier queue. **Phase 2 is closed at
FB-82:** Khmer numerals/dates, wrap and bilingual audits, font self-hosting, IME/paste and export
fidelity are done; the 17-shot after set plus six previews is in
`artifacts/next-work/review-lt2/after/` (13/17 pixel-identical to Phase 1), and the phase-close
matrix is `GATES_PASSED` (build, bundles, smoke 16/0/0, layout 1533/0, pytest **161**, budgets 6/6,
lhci 16/16 a11y 1.00, csp, canvas 22/0/2, important 3816 ≤ 3823) in
`artifacts/next-work/gates/20261025-150432/`. **Phase 3 closed 2026-10-27 (LT-3.10, FB-91):**
`docs/CAPABILITY-MATRIX-2026-10-24.md` is at final truth (pack rows and the new guest-language-switch
`partial`), the guest-page gap line LT-3.2…LT-3.9 is complete, and the phase-close matrix is
`GATES_PASSED` (build, bundles, smoke 16/0/0, layout, pytest **183 passed**, budgets 6/6, lhci 16/16
a11y 1.00, csp, canvas 22/0/2, important 3816 ≤ 3823) in
`artifacts/next-work/gates/20261027-120242/` (`artifacts/next-work/fb-91/NOTES.md`). **Phase 4 has
started: LT-4.1 — the visible guest language switch now drives the invitation — landed 2026-10-27
(FB-92, `artifacts/next-work/lt-4-1/NOTES.md`, gate row green except the documented `lt_2_6` host
metric), LT-4.2 — the editor unsaved-changes guard — (FB-93, `artifacts/next-work/lt-4-2/NOTES.md`)
and LT-4.3 — colour-picker extras (recents, eyedropper, contrast hint) — (FB-94,
`artifacts/next-work/lt-4-3/NOTES.md`) all landed 2026-10-27 with the same one documented red.
**LT-4.4 (bilingual per-run authoring) landed 2026-10-27 (FB-95)** — the run range now survives the
re-render, the controls live in the inspector's typography panel, and exactly one run moves; evidence
`artifacts/next-work/lt-4-4/NOTES.md`. It surfaced a separate, pre-existing defect — a same-profile
reload booting the title as one flattened run although the draft and server kept both — which was
then fixed as **FB-96**: the boot `capture()` ran before the lazily loaded rich-text modules, so the
rebuilt title lost its stored model. The test now reloads the same profile, and the guard was proven
both ways (disabled → the one-run failure; restored → green) —
`artifacts/next-work/lt-4-4/RELOAD-DEFECT.md`. **Phase 4 closed 2026-10-27 (LT-4.close, FB-97):** one
full matrix is `GATES_PASSED` — including **`187 passed`** with no red — in
`artifacts/next-work/gates/20261027-162311/gates.log`
(`artifacts/next-work/lt-4-close/NOTES.md`). **Phase 6 is underway:** LT-6.1 — long-task headroom
watch — (FB-98), LT-6.2 — budget state in numbers — (FB-99) and LT-6.3 — the `!important` ratchet
lane, three passes, 7 provably-dead tokens removed and the pin lowered 3823 → **3809** — (FB-100),
LT-6.4 — large-upload handling, a 20 MB probe with **zero defects** — (FB-101) and LT-6.5 — memory
and history, 50 page cycles plus a 500-step undo history inside stated CDP bounds with a 400-cycle
discriminator showing **no leak** — (FB-102) are done. **Phase 6 closed 2026-10-27 (LT-6.close,
FB-103):** one full matrix `GATES_PASSED`, all ten phases exit 0 — including **`189 passed in
577.31s`** with no red — in `artifacts/next-work/gates/20261027-211049/gates.log`
(`artifacts/next-work/lt-6-close/gates-all.log`). **Phase 7 started 2026-10-27 (LT-7.1, FB-104,
read-only):** `docs/ROADMAP-RECONCILIATION-2026-10-24.md` carries one row per acceptance bullet of
roadmap Parts 3–6 — **37 bullets: 22 `exists` / 10 `partial` / 5 `absent`** — and it replaces the plan's
LT-7.2 risk order, because tenant isolation, session management and analytics privacy/export already
exist and pass (`artifacts/next-work/lt-7-1/`). **Phase 7 closed 2026-10-28 (LT-7.2 FB-105 and
LT-7.close FB-106):** the eight absent/partial rows are closed (field-level encryption with
migration/rollback/re-encrypt, step-up on 15 destructive admin routes **plus an admin page that can
obtain the grant**, scoped API keys, signed webhook delivery, a rotation doc + script, the analytics
retention log line and the `security_*` collection-order fix), so the reconciliation now reads **30
`exists` / 6 `partial` / 1 `absent`** and Parts 4–5 have no open row. Gate record, stated plainly:
build, bundles, smoke 16/0/0, layout 1533 checks, budgets 6/6, LHCI 16/16 `minA11y 1.00`, CSP 0
violations, canvas 22/0/2 and `!important` 3809 ≤ pin 3809 are green; pytest is **200 passed, 1
failed** on the pre-existing `lt_2_6` PDF metric, which sits on its 4.5 tolerance
(`artifacts/next-work/lt-7-close/`). Next is **Phase 8, LT-8.1** (README quick-start on a clean
checkout).
**Work stays local-only (OD-3); no push, PR, merge or tag.**

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
| `FREEBUFF-TEMPLATES-WORKORDER-2026-10-25.md` | **completed** — TP-0.1…TP-6.4 ticked; 36-template pack in the working tree, uncommitted (OD-3). Supersedes LT-5.1–LT-5.8, amends the plan only by TP-OD-1…6 | 2026-10-27 |
| `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` | **authoritative queue** — **Phase 3 closed 2026-10-27 (LT-3.10, FB-91)** and **Phase 4 closed 2026-10-27 (LT-4.close, FB-97):** LT-4.1 (visible guest language switch, FB-92), LT-4.2 (unsaved-changes guard, FB-93), LT-4.3 (colour-picker extras, FB-94), LT-4.4 (bilingual per-run authoring, FB-95) and FB-96 (same-profile reload flattening, found inside LT-4.4) done; one full matrix `GATES_PASSED` with **`187 passed`** (`artifacts/next-work/lt-4-close/NOTES.md`). **Phase 6 closed 2026-10-27 (LT-6.close, FB-103):** LT-6.1 (three layout-guard runs, no route near the 600 ms ceiling, FB-98), LT-6.2 (`docs/perf/BUDGET-STATE-2026-10-24.md`, FB-99), LT-6.3 (`!important` ratchet lane: 7 tokens removed, pin 3823 → 3809, FB-100), LT-6.4 (large-upload probe, zero defects, FB-101) and LT-6.5 (heap/history bounds, no leak, FB-102) done; one full matrix `GATES_PASSED` with **`189 passed in 577.31s`** and no red (`artifacts/next-work/lt-6-close/gates-all.log` → `artifacts/next-work/gates/20261027-211049/gates.log`). **Phase 7 started 2026-10-27 (LT-7.1, FB-104):** `docs/ROADMAP-RECONCILIATION-2026-10-24.md` reconciles all 37 acceptance bullets of Parts 3–6 (22 `exists` / 10 `partial` / 5 `absent`) and replaces the LT-7.2 order — tenant isolation, session management and analytics privacy/export already exist and pass; the absent rows are field encryption of the listed columns, API keys, secrets rotation, automatic version snapshots and the analytics retention scheduler; it also isolated a red in the `pytest tests/security_*` bullet (1/47, collection-order coupling). **Phase 7 closed 2026-10-28 (LT-7.2 FB-105, LT-7.close FB-106):** the eight closure items are done and the reconciliation reads **30 exists / 6 partial / 1 absent** (Parts 4–5 complete; minor bumps 0.69.0/0.70.0, patch 0.70.1 drafted in `OWNER-QUEUE.md`). Nine gate phases green; pytest `200 passed, 1 failed` on the pre-existing `lt_2_6` PDF metric at its 4.5 tolerance — no threshold touched (`artifacts/next-work/lt-7-close/`). **Phase 8 closed 2026-10-28 (LT-8.5, FB-111) — the plan is exhausted:** LT-8.1 (FB-107) verified the quick-start, LT-8.2 (FB-108) audited the docs set, LT-8.3 (FB-109) rewrote `RELEASE-CANDIDATE.md` and added the external-evidence templates, LT-8.4 (FB-110) rebuilt this index (table below), LT-8.5 wrote `artifacts/next-work/FINAL-REPORT.md` and rewrote HANDOFF; `CERTIFICATION.md` stays `pending` because no load test, DR drill or pen test has been run. What remains is `artifacts/next-work/OWNER-QUEUE.md`. Work local-only | 2026-10-28 |
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
| `docs/templates/*` (`CATALOG`, `ACCEPTANCE`, `DESIGN-REVIEW`, `PUBLIC-PROOF`, `FONT-GAP`, `KHMER-HYGIENE`, `CULTURAL-CHECKLIST`, `FINAL-REPORT`) | **authoritative (current)** — the pack's catalogue, generated A1–A12 matrix (432/432), design review, public proof, font substitution record, hygiene and cultural audit, close-out report | 2026-10-27 |
| `docs/ROADMAP*.md` / `plans/001–003` | historical — completed/blocked; out of continuation scope | earlier |
| `artifacts/next-work/FINAL-REPORT.md` | **final report** — plan §8: phases and verdicts, the LT-8.5 gate matrix, Khmer files to draft next, `OWNER-QUEUE.md` contents, the final numbers and the final HEAD | 2026-10-28 |
| `FREEBUFF-NEXT-STEPS-2026-10-27.md` (repo root) | **authoritative order** — Stages A–F after the long-term plan: A backup/truth/demo, B cheap security rows, C plan 004, D product-quality gaps, E roadmap security, F Phase 8; §9 is the live checklist. B-1 closed as already fixed in `74f48da`; **D-5 closed 2026-10-29 (0.70.4)** — the `lt_2_6` PDF flake was two product defects in `printAllPages()` (app-chrome muted rule repainted printed text; the print document replayed the 900 ms `fadeUp`), now `body.print-doc` + animation-frozen, PDF MAE byte-identical `3.5922` over 30 runs including 4-way CPU load. Evidence `artifacts/next-work/fb-133` | 2026-10-29 |
| `plans/004-ux-ui-and-code-quality-pass.md` | **closed (both parts)** — Part A UX-1…UX-9 (0.70.2) and Part B CQ-1…CQ-4 (0.70.3). CQ-1 `!important` lane closes at 3809 → 3791 with a documented stop; CQ-2 stopped on its canvas-controller condition (Layout 859 ms, `updateCanvasView` 130 ms); CQ-3 stopped as stale (service already deferred, old consumer not shipped); CQ-4 removed 551 B of superseded `dashboard-page.css` rules. Evidence `artifacts/next-work/fb-131`, `fb-132`; after-set `review-ux2/after` | 2026-10-29 |

## Superseded work orders — every root `FREEBUFF-*.md`

The plan decides; this table says what each root work order used to queue and what replaced it. **No
file was moved or deleted** — the originals stay at the repo root for their FB numbers and evidence, and
the two files marked authoritative below are the only ones to follow.

| Root file | What it queued | Replaced by | Status |
|---|---|---|---|
| `FREEBUFF-PROMPT.md` | Canvas-motion fixes + the 2026-10-21 UI visual audit (Windows paths) | Plan Phases 1 and 6 | historical |
| `FREEBUFF-UI-REFINEMENT-PROMPT.md` | The 2026-10-21 visual-quality/research pass | Plan Phase 1 (closed at `1cd09d2`) | historical |
| `FREEBUFF-CONTINUATION-2026-10-21.md` | Brief that resumed the NW pass | `NEXT-WORK-TASK.md`, then the plan (Phases 0–6) | historical |
| `FREEBUFF-OPEN-ISSUES-2026-10-21.md` | FB-01…FB-22, the original open-issue sweep | Plan Phases 1–2 | completed |
| `FREEBUFF-REFINEMENT-ORDER-2026-10-22.md` | FB-23…FB-34 (round 2 refinement) | Plan Phase 1 | completed |
| `FREEBUFF-REFINEMENT-PROMPT.md` | The prompt for that round-2 order | `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` | historical |
| `FREEBUFF-REFINEMENT-ORDER-2026-10-23.md` | FB-35…FB-41 (round 3) | Plan Phase 1 | completed |
| `FREEBUFF-REFINEMENT-PROMPT-2026-10-23.md` | The prompt for round 3 | `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` | historical |
| `FREEBUFF-REFINEMENT-ORDER-ROUND4-2026-10-23.md` | FB-46…FB-57 (brand, Khmer map, colour work) | Plan Phase 2 | completed |
| `FREEBUFF-REFINEMENT-PROMPT-ROUND4-2026-10-23.md` | The prompt for round 4 | `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` | historical |
| `FREEBUFF-REFINEMENT-ORDER-ROUND5-2026-10-24.md` | FB-66…FB-79 (round 5 backlog) | **Explicitly superseded by the plan** (Phase 1 carries it) | superseded |
| `FREEBUFF-REFINEMENT-PROMPT-ROUND5-2026-10-24.md` | The prompt for round 5 | **`FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md`** (banner in the file) | superseded |
| `FREEBUFF-TEMPLATES-WORKORDER-2026-10-25.md` | TP-0.1…TP-6.4, the 36-template pack | Plan Phase 5 (completed; it also superseded LT-5.1–LT-5.8) | completed |
| `FREEBUFF-TEMPLATES-PROMPT-2026-10-25.md` | The prompt for the template pack | Plan Phase 5 (completed) | historical |
| `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` | Phases 1–8, the current queue | — | **authoritative** |
| `FREEBUFF-LONG-TERM-PROMPT-2026-10-24.md` | The autonomous run contract | — | **authoritative** |
| `FREEBUFF-NEXT-STEPS-2026-10-27.md` | A re-sequenced queue written from documents only (no code read) | Plan (advisory); its Stage F additions were adopted into LT-8.2/LT-8.3 | advisory |
| `FREEBUFF-OWNER-INBOX.md` | Owner-reported issues, one bullet each | — | **live channel** |
| `FREEBUFF-QUESTIONS-2026-10-28.md` | Questions from the document-only reviewer to the agent | — | answered record |
| `NEXT-WORK-TASK.md` | NW-0…NW-6, the Phase 0–6 predecessor | `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` | completed/superseded |

## Superseded-report banners

The bookkeeping pass of 2026-10-20 already banners the earliest three; as of 2026-10-21 the
remaining historical docs above are listed here rather than individually re-bannered, because
their content is not contradicted — only their currency. If a doc's instructions ever conflict
with the queue, this index decides: **`FREEBUFF-NEXT-STEPS-2026-10-27.md` wins on order**, and the
protocol plus per-item rules are **`FREEBUFF-LONG-TERM-PLAN-2026-10-24.md`** (every §6 item is ticked;
it is exhausted, not repealed). `NEXT-WORK-TASK.md` was that authority until 2026-10-24 and is now
itself superseded (see the table above).
