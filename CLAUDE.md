# CLAUDE.md

The agent protocol for this repository is [AGENTS.md](AGENTS.md). Read it before editing anything;
it is the single source of truth and this file only points at it.

Three things worth knowing before the first command:

- **Resume state:** `artifacts/ui-audit/fixes/STATE.md` (ledger, hard rules, next move) and
  `artifacts/next-work/HANDOFF.md` (where the run stands, the last gate lines).
- **The queue is exhausted** (Stages A–F closed 2026-10-29). The closing record is
  `artifacts/next-work/FINAL-REPORT.md`; open work is
  `FREEBUFF-UI-AUDIT-FIX-ORDER-2026-10-29.md` and the owner-held rows in
  `artifacts/next-work/OWNER-QUEUE.md`.
- **Hard rules that never bend:** agents never write Khmer (build samples from code points), never
  change a budget, threshold, frozen canvas or `tools/lighthouserc.js`, never add `!important` or a
  dependency, rebuild from source (`python3 build.py all`), and commit locally only — no push, tag,
  amend or rebase.
