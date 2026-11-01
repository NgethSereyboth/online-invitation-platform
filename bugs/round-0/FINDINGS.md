# Round 0 — baseline failures (no sweep yet)

Round 0 exists to close the three editor tests that were still red after the 2026-10-31
Pages-pane change, before round 1 sweeps the product. None of them was a public-page bug:
`lt_2_2`'s public-rendering leg passed at both viewports; each failure was in the editor's
reorganised inspector or its harness.

| ID | Test(s) | Verdict | Severity | Root cause | Fix |
| --- | --- | --- | --- | --- | --- |
| BUG-R0-1 | `lt_4_3_color_picker_test`, `lt_2_2_khmer_format_test` | **Product bug**, plus a stale contract | P1 | `typography-editor.js` installs after `editor/inspector-reorg.js` and rebuilt its shell with `#typographyControls.replaceChildren(...)`. By then the reorg had moved the controls into the visible Text group and hidden the legacy shell, so the rebuild dragged `#color`, `#convertDigits`, the run controls and the rest back into the hidden container. The controls were present but unreachable. | The shell now mounts into the reorg's visible Text group when it exists; the tests open the disclosure that contains the control. |
| BUG-R0-2 | `lt_4_3_color_picker_test`, `lt_2_2_khmer_format_test` | Stale test | P2 | `tests/browser_runtime.py` fell back to a button literally named `Event details`. `studio-experience.js` rebuilds the rail from the old markup and labels the tab `Event`; the stable contract is `data-studio-tab="event"`. | One shared `open_studio_tab()` helper clicks the data attribute (or the drawer opener at narrow widths); `open_event_details()` uses it before waiting for the RSVP/venue fields. |
| BUG-R0-3 | `lt_4_4_run_typography_test` | Stale test | P2 | The test waited for `#typographyControls` to be visible. The 2026-10-30 reorganisation deliberately hides that legacy shell and files the run controls into the Text group's disclosures, so the shell can never be visible again. | `reveal_inspector_control()` opens the real closed `<details>` ancestors; the test then waits for `#v20RunFont`, the control it actually drives. |

## Evidence

- `lt_2_2` failed at `open_event_details(page)` (its public hero, Khmer date, numerals,
  schedule times and both overflow legs had already passed), and the harness call log was
  `waiting for get_by_role("button", name=re.compile(r"^Event details\b"))`.
- A DOM probe of the editor with `title` selected returned
  `selectedNode = {"id":"title","objectType":"text"}` and
  `typography = {"hidden": true, "colorInside": false}`. `#textContent` in the same pane
  stayed visible, proving the selection was live and only the reorganised block was hidden.
- The same probe after a 1.2 s settle saw one visible `#color` (221×34) outside
  `#typographyControls`; the failing locator still resolved a hidden `#color` with the
  markup default `#47252d`. That is the late shell rebuild re-parenting the control.
- The organiser `compactTypography()` explicitly sets `root.hidden = true` after moving
  each `v20-inspector-group` into `details.ix-sub`; `app.js` still owns
  `#typographyControls.hidden` for the no-selection state, so the hidden attribute is
  expected, not a missing-selection bug.
- After the fix the three files report `4 passed in 51.59 s` (both `lt_2_2` parameters and
  the single tests in the other two files).

## Not bugs

- The public invitation page for the `lt_2_2` document renders. Its hero, Gregorian date in
  Khmer digits, schedule times and countdown units all asserted successfully before the
  editor leg.
- `lt_2_2`'s title still renders as one object with `data-object-type="text"`; the
  `textLike` check in `app.js` was not the failure.

Screenshots: none in this round. The failures are editor-visibility contracts diagnosed
from the live DOM; the visual sweep starts at round 1.
