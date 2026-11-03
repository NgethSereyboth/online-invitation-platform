# Round 9 — fix plan

- **Date:** 2026-11-03
- **Origin:** `http://127.0.0.1:4175` (`einvite-app`, loopback only)
- **Harness:** `bugs/round-6/live_flows.py`, extended with the guest/RSVP flow
- **Widths:** 360, 390, 768, 1024, 1280, 1440
- **Record:** `bugs/round-9/live-flows-six.json`

## Findings to fix

No product defect was reproduced in round 9. Both findings are defects in the
verification tooling: they made a correct product surface look broken and would
hide a real regression on the next run.

| ID | Kind | Symptom | Cause | File |
|---|---|---|---|---|
| BUG-R9-1 | Runner drift | `v17_professional_editor_test.py` failed at 360/390/430 | The runner still asserted the pre-round-6 model (Quick Edit first). Round 6 commit `0bfbb79` deliberately made canvas the mobile default so a selection cannot reopen the drawer. | `tests/v17_professional_editor_test.py` |
| BUG-R9-2 | Harness assumptions + race | Guest/RSVP checks failed at every width before the fixes | The flow assumed an `h1`, `.guest-feature-credit`, and `button[type=submit]`; it never dismissed `#openCover`; and it inferred RSVP success from a fixed delay and an English-only success string. | `bugs/round-6/live_flows.py` |

## Ordered tasks

1. **BUG-R9-1 — align the v17 mobile runner with the shipped contract.**
   Normalise each width to canvas before selecting, assert canvas mode with the
   inspector closed and the context bar visible, then open Quick Edit through
   `#mobileQuickMode` and keep the existing sheet and 9-handle coverage.
   Verify: `tests/v17_professional_editor_test.py` and
   `tests/v17_professional_editor_mobile_test.py` both exit 0.
2. **BUG-R9-2 — make the guest flow describe the shipped page.**
   Dismiss the cover, wait for `form#rsvp`, use `h2`, count
   `.guest-platform-credit, .guest-studio-brand`, and click
   `form#rsvp button` rather than a typed submit. For the valid submit, wait
   for the actual `POST /rsvps` response, assert 200/201, then match the
   confirmation in English or Khmer, including the Khmer "response updated"
   heading used when a guest edits an existing RSVP.
   Verify: guest flow 12/12 at 1440/390/360, then the full six-width sweep.
3. **Re-run the full sweep** and confirm zero failures with clean
   page/console/network records at every width.
4. **Run the gates:** `build.py all --check`, `compileall`, `node --check`,
   `git diff --check`, and the two v17 runners.
5. **Record the result** in `bugs/round-9/FINDINGS.md` and `PROGRESS.md`.

## Scope guard

No `src/` file is changed in round 9: the product behaviour under test already
matches the specification. Fixing the harness rather than the product is the
root-cause correction here, and it keeps the next sweep honest.
