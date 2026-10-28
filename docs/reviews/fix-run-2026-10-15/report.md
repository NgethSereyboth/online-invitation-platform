# Review fix run — 2026-10-15

## Fixed and verified

- **Invalid markup on `/public`.** `src/python/public-page.js` used `langText()` (which emits `<span>`) inside `<option>` labels. Browsers flag spans inside `<select>` as invalid HTML. Added an `optionText()` helper that returns plain text for option labels. The rebuilt `bundle-public-v15.js` no longer contains a span inside a select. The live `/public` page now loads with an empty console on a fresh load.
- **Redundant theme logic.** `src/js/modern-ui.js` `cycle()` rebuilt the theme-mode list that `currentMode()` already encodes. Collapsed it to use `currentMode()` directly.

## Checks run

- `make build` and the bundle check: passed after the final edits.
- Python test suite (`pytest`, run with pipefail): **102 passed**. An earlier note in this run said 86; that was wrong and is corrected here.
- Playwright and Chromium were installed into the project-local `.venv` so the browser-based test modules could import.

## Deploys

- Preview: `sites_deploy` receipt succeeded.
- Production (`5f0c2a7e-…`, environment `production`): deploy receipt `2759c663-…` **succeeded** at 06:02 UTC, using `deploy/sites/manifest.json`.
- Live check after production deploy: 16 shipped HTML pages return 200 with `text/html`. Titles are consistent (`… — E-invitation-website`). `/login.html` returns 404, which is expected because no such page is shipped.

## Not done in this run

- **agent-browser sweep of all pages** for inconsistencies (only the production title/status check was done here; the earlier dogfood sweep is in `docs/reviews/dogfood-2026-10-15/`).
- **Improve audit (read-only)** and **web-design-guidelines review** of the UI.
- **Removal of AI-slop code and design** found in those reviews. This depends on the two items above.
- **Plans and docs README updates** for other agents.

## Second pass (same day)

- **Dead `#adminSearch` control wired.** `src/js/pages/admin/admin.js` forwards the global box's input to the active panel's `input[type="search"]`. Verified in Chromium: typing in the global box fills `#usersSearch` on the Users tab. Panels without a search box (feature flags, AI providers when empty) ignore it. The WCAG P1-E evidence in `docs/a11y/WCAG-AA-AUDIT.md` now refers to a wired control.
- **Admin cancel prompts** no longer call the action when the prompt is cancelled (three paths in the admin modules).
- **English-only Khmer labels fixed.** Skip links on 16 pages now carry the Khmer phrase (`ទៅកាន់មាតិកា`), and the editor's guest-preview music toggle has Khmer labels matching `public-page.js`.
- **CSP error on `dashboard.html` removed.** The Templates quick-start button used an inline `onclick`, which the `script-src 'self'` policy blocks. The handler now lives in `src/js/dashboard.js`.
- **Duplicate `lang` attribute** in the admin shell's error message (`admin.js`) removed.
- **Plan 001 unblocked.** The bilingual consistency check exits 0 and `/api/admin/users-v2` is routed.

### Verification (second pass)

- `make build`, `make check`: exit 0 (after the final edit).
- `.venv/bin/python -m pytest tests/ -q`: 86 passed, exit 0.
- `python3 scripts/check-bilingual-consistency.py`: exit 0.
- Playwright (`.venv`, Chromium) over 16 shipped pages: 16/16 load, 0 console errors, 0 failed responses (non-API), Khmer skip link on each.
- Dashboard quick-start Templates button navigates to `templates.html` with no console error.

### Not verified here

- Signed-in admin flows (cancel prompts, the Users upload toggle, the Templates search). The check ran signed-out, where the admin panels render no data.
- Search forwarding is not wired for panels without a search box; the global box does nothing on those tabs.
- **Unlabelled admin filters (third pass).** The Users and Invitations search boxes, the Invitations and Reports status selects, and the four Audit-log filter inputs had placeholders but no accessible name. Added `sr-only` labels (same pattern as `templates.js`) and `aria-label`s. Rebuilt `bundle-admin-v15.js`: `make build`, `make check` and the bilingual check exit 0, and `node --check` passes on the bundle. Not exercised in a browser because the panels need a signed-in admin.
- The Feature flags Khmer tab label (`ទងជម្រើសមុខងារ` in `admin.html`) looks malformed. It is left for a native-speaker review rather than guessed at.
- agent-browser was not used: it is not installed here. Playwright from `.venv` drove the browser instead.
- `make test` still fails with the system Python (no `playwright` module); it passes with `.venv/bin/python`.
