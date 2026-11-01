# Round 0 — fix plan

Ordered by user impact. All items are complete; the verification column records what was
actually run, not what was intended.

| # | Finding | Change | Files | Verification |
| --- | --- | --- | --- | --- |
| 1 | BUG-R0-1 | When the inspector reorg has already filed the Edit pane, mount the v20 typography shell inside the visible `Text` group instead of the hidden legacy container; drop any superseded `#advancedTextLayout` first so the id stays unique. | `src/js/typography-editor.js` (mirrored by `build.py`) | `lt_4_3`, `lt_2_2` pass; `#color` and `#convertDigits` visible after opening their disclosure |
| 2 | BUG-R0-2 | Replace the hard-coded `Event details` label lookup with `open_studio_tab('event')`, which clicks `[data-studio-tab="event"]` (the stable attribute), opening the tools drawer at narrow widths. Keep the RSVP/venue waits unchanged. | `tests/browser_runtime.py` | `lt_4_3` and `lt_2_2` get past the pane switch |
| 3 | BUG-R0-3 | Add `reveal_inspector_control()`: open the actual closed `<details>` ancestors of a control, then wait for Playwright's visible state. Use it for `#color`, `#convertDigits` and `#v20RunFont`; drop the impossible `#typographyControls` visibility wait. | `tests/browser_runtime.py`, `tests/lt_4_3_color_picker_test.py`, `tests/lt_2_2_khmer_format_test.py`, `tests/lt_4_4_run_typography_test.py` | `lt_4_4` passes |
| 4 | Baseline | Re-run the three files together, then the full suite, the build gates and the repo's lint/type-check equivalent. | — | Recorded in `PROGRESS.md`; see the run log for totals |

## Assertion integrity

No test lost an assertion. `lt_2_2` still checks the Khmer date, the absence of ASCII
digits, the schedule times, the countdown units, both overflow legs and the editor
round-trip. `lt_4_3` still checks the popover, contrast ratio, recents, eyedropper support,
draft persistence, Escape/focus and the 375 px bounds. `lt_4_4` still checks both runs'
marks, the surviving selection, the server document and the same-profile reload.
