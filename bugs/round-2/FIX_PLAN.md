# Round 2 — fix plan

Ordered by severity and dependency. One commit per finding.

1. **BUG-R2-1 — unconfigured guest features**
   - Suspect: `public-page.js` calls `EInviteSignupSheets.enhance`,
     `EInvitePolls.enhance` and `EInviteAlbum.enhance` for every published
     invitation; each module appends its section before knowing whether the
     host has data.
   - Change: remove the section when the API returns an empty collection in
     `signup-sheets.js` and `polls.js`; pass `albumEnabled` from
     `settings.galleryEnabled` and skip the album when disabled.
   - Files: `src/js/public-page.js`, `src/js/signup-sheets.js`,
     `src/js/polls.js`, `src/js/album.js`.

2. **BUG-R2-2 — album upload row**
   - Suspect: `guest-features.css` uses a rigid `1fr 2fr auto` grid and
     `.album .load-more { display:block }` overrides `[hidden]`.
   - Change: allow the columns to shrink (`minmax(0, …)`), add a single-column
     row below 640 px, and add `.album .load-more[hidden]{display:none}`.
   - Files: `src/css/guest-features.css`.

3. **BUG-R2-3 — duplicate credit**
   - Suspect: `public.html` ships a static `.guest-credit` and
     `public-page.js` appends `studioBrandMarkup` inside `#publicRoot`.
   - Change: remove the static duplicate, keep the dynamic branded credit, and
     move it after the asynchronously appended feature sections so it remains
     the final element.
   - Files: `src/html/public.html`, `src/js/public-page.js`.

**Status 2026-11-01: all fixed and deployed.** Commit map: BUG-R2-1
`0604f2c`; BUG-R2-2 `ef2f52a` plus the `33b43eb` reflow after the first
probe collapsed the caption column; BUG-R2-3 `ef78d67`. Production deploy
`7265e709`, published 04:15:09Z. The focused gallery fixture confirms the
album form stacks to one column at 390 and 1440 and keeps the caption visible.

Verification after each fix: focused Playwright probe at 390/1440 plus the
round-2 flow; then rebuild, rerun the live matrix, and redeploy.

Dropped after investigation: the apparent blank design pages on the live QA
invitation are deferred reveal animations. Scrolling each page into view shows
all text at opacity 1, so no renderer change was kept.
