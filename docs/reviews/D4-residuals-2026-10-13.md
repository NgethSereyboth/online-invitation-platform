# D4 residuals — detector fixed, candidates re-classified (2026-10-13)

## What was wrong with the instrument

`tools/ui-sweep.mjs --click` decided "dead" by comparing a state fingerprint before and after each
click, then returning the route to where it started. Three things made that comparison lie:

1. **The probe's own dismissal closed the app's default-open disclosures.** A fresh load opens three
   `<details>` (`advancedTextLayout`, two `final-control-group`). The sweep's `DISMISS` closed every
   open `<details>`, so every reset differed from the fresh-load state it was compared against.
2. **Mobile drawers flicker at boot.** `aside#mobileCreationPanel` / `aside#mobileQuickInspector` are
   mounted and opened by the app's own boot logic, so a reset could differ by one of them alone.
3. **Probes read a detached frame.** A click that navigated left the page detached, and the next
   `page.evaluate` threw out of the whole pass (crash at `ui-sweep.mjs` line 440).

## What changed (tools/ui-sweep.mjs only)

- `DISMISS` takes the fresh-load disclosure set and leaves those open; it still closes ones a user opened.
- The reset check ignores the `mobile*` asides. The click fingerprint still records them, so a click
  that opens one is still caught as a state change; only the *reset* check no longer re-verifies them.
- Probe reads go through `safeEval`: on a detached frame the route is reset and the read retried once.
  A control that still cannot be read is recorded as `unmeasured`, never as dead.

## Measurement (index.html @1280, click pass)

| | before fix | after fix |
| --- | --- | --- |
| controls probed | 121 | 121 |
| dead-control candidates | 15 | **8** |
| input-required | 6 | **7** |
| covered (under the onboarding tour) | 4 | 4 |
| skipped (disabled / already-on / select) | 11 | 11 |
| reset reloads | 105 | **5** |
| contaminated (not restored after reset) | 76 | **0** |

Raw: `docs/reviews/sweep-d4-1280/index-dead-controls.json`. Re-derive with
`BASE_URL=http://127.0.0.1:4175 node tools/ui-sweep.mjs --routes=index.html --widths=1280 --click --click-width=1280`.

## Re-classification of the 8 remaining candidates

These are **candidates, not findings**. Each still needs a per-control check (a hit-tested click and a
look at what it targets) before anyone calls it a defect.

| control | page position | note |
| --- | --- | --- |
| `View all` | y 662 | may be a link-style control inside a closed panel |
| `TT` | rail, y 327 | known cosmetic label (listed in D4 row) |
| `≡Layers` / `◐Design` (`studio-inspector-tab`) | top, y 75 | inspector tabs; earlier measured to switch panels, so a no-change here needs checking |
| `#workflowPanelToggle` `‹` | y 424 | a toggle whose `aria-expanded` should change; a real candidate |
| `Automation` / `Templates` | footer, y 877 | footer tools; may open a surface outside the fingerprint |
| `Tools ⌃` (`v54-footer-tools-trigger`) | footer, y 877 | footer tools trigger |

The 7 input-required controls are the workflow-row grips (`⋮⋮`) and the reorder arrows (`↑`/`↓`).
They do nothing until a row is selected or the list has a neighbour, so the classification is
expected. The list-end arrows are the ones that are structurally no-ops at the end of the list.

## Not yet done

- The 16-route click pass has **not** been re-run with the fixed detector. It runs only at the final gate.
- The 8 candidates above are unverified.
