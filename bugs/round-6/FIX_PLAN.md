# Round 6 — fix plan

**Local fixes verified; the single redeploy attempt was refused by the daily
allowance.** The 15 failures in the first pass were harness assumptions, not
product defects. The corrected local run is green at all six widths.

| # | Task | Cause | Files | Status |
|---|---|---|---|---|
| 1 | Extend the live harness from 1440/360 to all six widths | Required coverage gap | `bugs/round-6/live_flows.py` | Done |
| 2 | Triage the 15 failures | Drawer opened by selection; exact-JSON redo identity; appearance menu; expected public-API 404 | — | Done — no product defect confirmed |
| 3 | Correct the harness | Close inspector/Quick Edit before gestures; compare restored object count; drive the Light/Dark menu; filter both 404s; scroll the 1024 title into the canvas before gesturing | `live_flows.py` | Done |
| 4 | Re-run all six widths locally | Final source and served bundle | — | **225/225 passed**, 0 failed; console/network clean |
| 5 | Editor CLS | Prewarm selection revealed inspector groups; mobile class and brand markup arrived after first paint | `first-selection-prewarm.js`, `inspector-reorg.js`, `index.html`, `studio-experience.js` | **Fixed** — desktop **0.0698 / 0.0679 / 0.0810**, mobile **0.0973 / 0.0973 / 0.0943**; Pages-group reflow gone |
| 6 | Deploy | Origin still paused from the exhausted daily allowance | — | **Refused once** — request `593d9b20-ecfb-4e0d-9d88-799f4c6099ed`; 10,301/10,000 daily, 21,056/100,000 monthly, reset 2026-11-03T00:00Z; no receipt, no retry |
| 7 | SQLite teardown warning | Platform job threads outlived a test's temporary data directory | `src/python/server.py`, `tests/conftest.py` | **Fixed** — shut down `jobs` on DB-path change and before the autouse data-dir restore; final suite **247 passed / 16 plugin warnings in 1092.83 s**, no SQLite/thread warning |

## After the allowance resets

1. Confirm `/` returns 200 and `sites_inspect` is active.
2. Rebuild `artifacts/sites-public`, deploy, and confirm the served bundle has
   the Canvas/X dismissal and boot-safe selection changes.
3. Run `.venv/bin/python -u bugs/round-6/live_flows.py`; expect zero failed
   checks, six widths, and a fresh `live-flows-six.json`.

## Explicitly not started

- Residual editor CLS **0.3927** (live demo 0.000): recorded, untouched.
- Templates CLS 0.604, guest LCP, 320/375 topbar swipe, artboard fit and bundle
  size remain the previously documented open items.
