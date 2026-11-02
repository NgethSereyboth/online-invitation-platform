# Round 6 — fix plan

**Local fixes verified; redeploy blocked by the daily allowance.** The 15
failures in the first pass were harness assumptions, not product defects. The
corrected local run is green at all six widths.

| # | Task | Cause | Files | Status |
|---|---|---|---|---|
| 1 | Extend the live harness from 1440/360 to all six widths | Required coverage gap | `bugs/round-6/live_flows.py` | Done |
| 2 | Triage the 15 failures | Drawer opened by selection; exact-JSON redo identity; appearance menu; expected public-API 404 | — | Done — no product defect confirmed |
| 3 | Correct the harness | Close inspector/Quick Edit before gestures; compare restored object count; drive the Light/Dark menu; filter both 404s; scroll the 1024 title into the canvas before gesturing | `live_flows.py` | Done |
| 4 | Re-run all six widths locally | Final source and served bundle | — | **225/225 passed**, 0 failed; console/network clean |
| 5 | Editor CLS | Late inspector-group growth and toolbar/Pages geometry | `stabilized.css`, `inspector-reorg.js`, `app.js`, `first-selection-prewarm.js`, `studio-experience.js` | **desktop 0.0962**, mobile **0.0906**; one desktop run 0.1096 (Pages-group reflow) |
| 6 | Deploy | Origin still paused from the exhausted daily allowance | — | **Blocked** — 10,301/10,000; reset 2026-11-03T00:00Z |

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
