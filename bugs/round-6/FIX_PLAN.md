# Round 6 — fix plan

**No application fix and no redeploy.** The six-width live pass found no
confirmed product defect; the 15 failed checks are harness assumptions. The
clean rerun is blocked by the site's daily hosting allowance.

| # | Task | Cause | Files | Status |
|---|---|---|---|---|
| 1 | Extend the live harness from 1440/360 to all six widths | Required coverage gap | `bugs/round-6/live_flows.py` | Done — 219 checks, 202 captures |
| 2 | Triage the 15 failures | Drawer opened by selection; exact-JSON redo identity; appearance menu; expected public-API 404 | — | Done — no product defect confirmed |
| 3 | Correct the harness | Close inspector/Quick Edit before gestures; compare restored object count; drive the Light/Dark menu; filter both 404s | `live_flows.py` | Done, not yet run live |
| 4 | Clean six-width rerun | Origin returned HTTP 429 | — | **Blocked** — daily 10,301/10,000; reset 2026-11-03T00:00Z |
| 5 | Deploy | No app source changed | — | Not required |

## After the allowance resets

1. Confirm `/` returns 200 and `sites_inspect` is active.
2. Run `.venv/bin/python -u bugs/round-6/live_flows.py`; expect zero failed
   checks, six widths, and a fresh `live-flows-six.json`.
3. If a failure survives, treat it as a product finding at that width, fix the
   root cause, rebuild/deploy and verify the served hash.

## Explicitly not started

- Residual editor CLS **0.3927** (live demo 0.000): recorded, untouched.
- Templates CLS 0.604, guest LCP, 320/375 topbar swipe, artboard fit and bundle
  size remain the previously documented open items.
