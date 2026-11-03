# Round 9 — six-width sweep with guest/RSVP

- **Date:** 2026-11-03
- **Origin:** `http://127.0.0.1:4175` (`einvite-app`, loopback only)
- **Harness:** `bugs/round-6/live_flows.py` (225-check six-width suite) plus the
  new guest/RSVP flow, run as `ROUND6_OUT=bugs/round-9`
- **Widths:** 360×800, 390×844, 768×900, 1024×900, 1280×900, 1440×900
- **Record:** `bugs/round-9/live-flows-six.json`
- **Screenshots:** `bugs/round-9/shots/flows-v2/` (231 files)

## Result

`LIVE_CHECKS=249 FAILED=0 WIDTHS=6`, exit 0.

| Width | Checks | Failed | Page errors | Console (non-404) | Network (non-404) |
|---|---|---|---|---|---|
| 360 | 42 | 0 | clean | clean | clean |
| 390 | 42 | 0 | clean | clean | clean |
| 768 | 41 | 0 | clean | clean | clean |
| 1024 | 40 | 0 | clean | clean | clean |
| 1280 | 42 | 0 | clean | clean | clean |
| 1440 | 42 | 0 | clean | clean | clean |

The only console/network entries at every width are the deliberate
`/i/missing-slug-round-6` and `/api/public/missing-slug-round-6` 404s from the
missing-invitation check. The guest flow recorded exactly one
`POST /api/public/qa-ui-sweep-wedding/rsvps` per width, answered 200/201.

## Coverage added this round

The published local invitation `qa-ui-sweep-wedding` is now driven at every
width: cover dismissal, title/heading/sections, single platform credit, zero
feature panels, English↔Khmer toggle, an empty-name submit that must stay on the
form, and a valid RSVP that must return 200/201 and render the confirmation in
either language.

## Findings

No product defect was reproduced. Two verification defects were found and fixed:

| ID | Area | Symptom | Cause | Fix | Commit |
|---|---|---|---|---|---|
| BUG-R9-1 | Manual runner | `v17_professional_editor_test.py` failed at 360/390/430 | Still asserted the pre-round-6 Quick-Edit-first mobile model; round 6 made canvas the deliberate default so a selection cannot reopen the drawer | Assert canvas mode + hidden inspector + visible context bar, then open Quick Edit via `#mobileQuickMode` | `7f283d5` |
| BUG-R9-2 | Sweep harness | Guest checks failed at all widths; RSVP intermittently reported failure after a successful POST | Assumed `h1`, `.guest-feature-credit`, and `button[type=submit]`; never dismissed `#openCover`; inferred success from a delay and an English-only string | Shipped selectors, cover click, `POST /rsvps` response assertion, English + Khmer confirmation match | `a5d8cc0` |

Both runners now exit 0: `V18_PROFESSIONAL_EDITOR_TEST_PASSED` and
`V17_PROFESSIONAL_EDITOR_MOBILE_TEST_PASSED`.

## Advisory triage

These audit notes are recorded, not counted as failures:

| Note | Triage |
|---|---|
| Guest contrast (3.83–4.48 at 16 px) on `.invite-kicker`, Khmer heading and countdown `strong` | **Inconclusive.** The probe resolves only `rgb()` backgrounds; the guest page builds surfaces with `color-mix()` and palette gradients, and the known `#lang-km.active` false positive (1.06) appears in the same runs. No illegibility in the captures. |
| Clipped design-page text in 360/390 full-page captures | **Capture artifact.** The page indicator moves 6/9 → 7/9 and the 1440 rest capture is intact; the scroll-linked page transition is stitched mid-slide. Document overflow is 0 and the form geometry checks pass. |
| `.skip-link` / `.sr-only` 1 px rects | Intentional off-screen accessibility text; known since round 6. |
| `#workflowV5Focus` right edge beyond the viewport at 390/768/1024/1280 | Known off-canvas focus proxy; document `scrollWidth` equals `clientWidth`. |
| Header icon hit-area overlaps (21–176 px²) | Icon buttons whose labels are hidden; no visible overlap in the captures. |
| Guest page has no `h1` (hero uses `h2`) | Shipped heading structure, previously accepted. Changing it is a semantic/SEO decision, not a layout defect; left as an advisory. |

## Prior-round regression checks

| ID | Check | Result |
|---|---|---|
| BUG-R1-1 | Signed-out editor redirect | **Pass** — `/invitations/<id>/editor` → 302 `/dashboard.html?next=…`. |
| BUG-R1-2 | Missing vs published slug | **Pass** — missing 404, published 200. |
| BUG-R1-3 | PNG export / CSP | **Pass** — valid PNG at all widths, console clean. |
| BUG-R1-4 | Manual runners | **Pass** — v17 and mobile v17 exit 0. |
| BUG-R2-1/2/3 | Guest features, album reflow, single credit | **Pass** — guest flow: features 0, credits 1, overflow 0. |
| BUG-R4-1/2/3 | Pages grouping, tablet/drawer recovery | **Pass** — editor interactions green at six widths. |
| P1 CLS | Editor first paint | Unchanged this round (no source change); last measured < 0.1. |

## Artifact proof and gates

- Served `bundle-index.js` SHA-256 equals `src/python/bundle-index.js` and
  `src/js/bundle-index.js`: `94570322281650015cd8ea4bc4672fe6649de5f9a08865f8421ea1d31ce2c06a`.
- `python3 build.py all --check` → `BUILD_OK`, `MIRROR_CHECK_PASSED`.
- `python3 -m compileall -q src/python tests tools` → exit 0.
- `node --check` on every `src/js/*.js` → exit 0.
- `git diff --check` → clean.
- v17 desktop and mobile runners → exit 0.

## Deploy status

No product source changed in round 9, so the served build is unchanged and
current. **No push was made and no hosted/Sites deployment was performed.**
Publishing remains owner-held, as recorded in `PROGRESS.md`.
