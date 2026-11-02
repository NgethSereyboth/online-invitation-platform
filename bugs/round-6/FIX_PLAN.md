# Round 6 — fix plan

The six-width live sweep and the live interaction pass found **no new product
defect**, so this round needs no source change and no redeploy.

| # | Task | Cause | Files | Status |
|---|---|---|---|---|
| 1 | Triage every sweep hit against rounds 2–4 | 108 clipped records are `.skip-link`/`.sr-only`; small targets and right-edge buttons repeat the round-4 triage; 404 console errors are the deliberate missing route | — | Done |
| 2 | Verify live editor/guest depth on the identical bundle | Live has no account and no published invitation; the local bundle’s CSS hash matches live | `bugs/round-4/flow_sweep.py` | Done, 61/61 |
| 3 | Re-check rounds 1–5 | Regression matrix in `FINDINGS.md` | — | Done, no regression |
| 4 | Gates | build, compileall, available JS check, pytest | — | build/compileall pass; suite recorded in `PROGRESS.md` |
| 5 | Deploy | No code changed, so the published build is already the verified build | — | Not required; hash re-confirmed |

## Explicitly not started

- Residual editor CLS **0.3927** (live demo 0.000): recorded and left open.
- Templates CLS 0.604, guest LCP, 320/375 topbar swipe, artboard fit and bundle
  size remain the previously documented open items.
