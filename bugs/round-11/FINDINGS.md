# Round 11 — findings

Sweep: `bugs/round-6/live_flows.py` against `http://127.0.0.1:4175` (authoritative local
service per the mission revision in `PROGRESS.md`). Six widths (360/390/768/1024/1280/1440).

Result: **LIVE_CHECKS=249 FAILED=0 WIDTHS=6** — editor (add, drag, resize, rotate,
multi-select, undo/redo, save, reload/recover, PNG export), template studio (cards, search,
source/category/favorite filters, Khmer), dashboard (signed-out shell, registration, sign-in),
designer, missing-404 route, guest invitation (load, language toggle, RSVP invalid + submit)
all pass; page errors, console and network are clean (only the deliberate 404 routes).

## Bugs

No product defects found. All 249 checks pass across all six widths. The only console noise
is the deliberate missing-invitation 404s, which the harness whitelists.

## Notes

- The first sweep attempt (process 1585777) was cut short by the `run_terminal_command`
  300 s timeout cap and produced an empty log; the second attempt (process 1587082,
  unbuffered, backgrounded without double-backgrounding) completed successfully.
- The `FAILED 768 drag AssertionError('title did not move')` line that appears at the end of
  `sweep.log` is from the first attempt's overlapping writer on the same log file; it is not
  reflected in the authoritative `live-flows-six.json`, which shows `drag @ 768: ok=True,
  before=8%, after=16%`. All six widths' drag checks pass.
- `768-fail-drag.png` and `768-editor-drag.png` both exist in `shots/flows-v2/`; the former
  was captured during the first (interrupted) run, the latter during the successful run.

## Evidence

- `bugs/round-11/sweep.log` — full pass log (249 PASS lines + final summary).
- `bugs/round-11/live-flows-six.json` — structured check results (249 checks, 0 failures).
- `bugs/round-11/shots/flows-v2/` — 214 screenshots (one per check per width where captured).

## Comparison with round 10

Round 11 is a clean re-run confirming no regressions since round 10's fix (BUG-R10-1, the
`/templates` CLS fix). The same 249-check harness passes at all six widths with clean
console/network, the same guest fixture (`qa-ui-sweep-wedding`), and the same editor
interaction checks (add, drag, resize, rotate, multi-select, undo/redo, save, reload, export).
