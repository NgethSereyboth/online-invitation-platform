# Round 10 — findings

Sweep: `bugs/round-6/live_flows.py` against `http://127.0.0.1:4175` (authoritative local
service per the mission revision in `PROGRESS.md`). Six widths (360/390/768/1024/1280/1440).

Result: **LIVE_CHECKS=249 FAILED=0 WIDTHS=6** — editor, template studio, dashboard,
designer, missing/error routes, guest invitation and RSVP all pass; page errors, console
and network are clean (only the deliberate 404 routes).

The harness does not measure layout stability, so a Playwright CLS/LCP probe
(`bugs/round-10/cls_probe.py`) was run on the two routes that still carried an open
performance row in `docs/NEXT-WORK.md` (D-1 templates CLS, D-2 guest LCP).

## Bugs

| ID | Page / route | Viewport | Steps | Expected | Actual | Severity |
| --- | --- | --- | --- | --- | --- | --- |
| BUG-R10-1 | `/templates` | 1440×900, 390×844 | Load `/templates` cold and watch layout | Content below the pack gallery stays put; no large movement | Pack gallery is fetched and inserted above `#studioGrid` after first paint, growing from 126px to 3188px at ~630ms; the studio grid's visible state is pushed from y≈442 to y≈3500. CLS 0.825 (1440) / 0.267 (390) | P1 |

## Evidence

- `cls.json` — baseline CLS/LCP for `/templates` and `/i/qa-ui-sweep-wedding`.
- `cls-trace.json` — frame-by-frame geometry: gallery null → 126px → 3188px; grid top
  442 → 3500. Mutation/geometry changes at t=520/552/628ms.
- `cls-experiment.json` — hiding the transient loading block does not change CLS,
  confirming the mover is the studio grid's rendered state, not the loading text.
- `bugs/round-10/sweep.log` — 249/249 checks.
- `bugs/round-10/shots/` — 213 sweep screenshots.

## Fix verification — BUG-R10-1

- Static gallery shell adopted by `mount()`; skeletons hydrate to real cards.
- CLS after rebuild/restart: **0.0101** (1440×900) and **0.0009** (390×844), down from
  0.825 / 0.267 (`cls-after.json`). LCP 568 ms / 500 ms.
- `/templates` at both widths: 36 real cards, 0 skeletons, count “36 of 36 designs”,
  `aria-busy=false`, Khmer switch keeps 36 cards, console/network clean, no horizontal
  overflow (`verify_templates.py`, screenshots `shots/templates-fixed-*.png`).
- Full six-width sweep after the fix: **249/249 checks, 0 failures** (`sweep-after.log`),
  including all `/templates` search/category/favorite interactions.

## Notes (not bugs)

- Guest LCP: 1004ms desktop, 1328ms mobile — inside the 2.5s "good" threshold, so D-2
  needs no change.
- Guest CLS: 0 / 0.031 — no work needed.
- Templates CLS at 390 (0.267) has the same cause as 1440.
