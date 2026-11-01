# Round 2 — live sweep findings

Date: 2026-11-01
Live site: `https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page`
Local backend: `http://127.0.0.1:4175`

Round 2 re-checked BUG-R1-1, BUG-R1-2 and BUG-R1-3 and then ran the full
20-route × 6-viewport live matrix plus the authenticated flow (editor, RSVP,
template picker, export). The round-1 fixes still hold.

| ID | Route | Viewport | Repro | Expected | Actual | Severity |
|---|---|---|---|---|---|---|
| BUG-R2-1 | `/i/<published-slug>` | 390, 768, 1440 | Open a published invitation whose host never enabled or created sign-up sheets, polls or a shared album. | Unconfigured guest features are absent. | Three large `guest-feature` cards are appended unconditionally and show "No sign-up sheets…", "No polls…" and an empty photo album with an upload form, even when the gallery is disabled. | P1 |
| BUG-R2-2 | `/i/<published-slug>` | 390, 1440 | Scroll to the Shared Photo Album card. | "Choose photo" is fully readable; the "Load more" control is hidden while there are no more pages. | The label is clipped to "Choose f…" and overlaps the caption field. `.album .load-more { display:block }` also overrides the `hidden` attribute, so "Load more" is visible with no photos. | P1 |
| BUG-R2-3 | `/i/<published-slug>` | all | Scroll to the end of the invitation. | One platform credit. | "Created with OKID" appears twice: once from the dynamic renderer and once from the static footer in `public.html`. | P2 |

## Re-checked from round 1

| ID | Check | Result |
|---|---|---|
| BUG-R1-1 | Signed-out editor navigation | Pass — lands on `/dashboard?next=…`, no editor leak. |
| BUG-R1-2 | Published vs missing slug status | Pass — live `/i/qa-ui-sweep-wedding` = 200; `/i/missing-slug-round-2` = 404; API equivalents 200/404. |
| BUG-R1-3 | Export and CSP | Pass — downloaded PNG has the PNG signature (39,023 bytes), zero CSP or console errors in the export flow. |

## Observation, not a product defect

- `static.cloudflareinsights.com/beacon.min.js` is injected by the hosting
  proxy and blocked by `script-src 'self'`. The error appears only on the
  deployed origin, is not emitted by this repository, and predates round 2.
  Allowing it would require widening the production CSP to a third-party
  analytics origin; that is an owner/security decision, so it is recorded
  rather than changed here. See `docs/security/CSP-MONITORING.md`.
- The first flow run reported `editor undo/redo` and `editor add text` as
  failures. Both were harness errors: undo compared only `top` after a
  horizontal drag, and the text-tool click landed on the date object. The
  corrected flow compares a full object snapshot and clicks an empty margin.
- A full-page screenshot of `/i/qa-ui-sweep-wedding` showed the three legacy
  design pages as blank 700 px bands. Scrolling each section into view renders
  every text object at opacity 1; the bands were deferred reveal animations,
  not missing content. No renderer change was kept for this.

## Fixes verified

| ID | Commit(s) | Verification |
|---|---|---|
| BUG-R2-1 | `0604f2c` | Flow reports 0 sign-up/poll/album panels and 1 credit; live 390/1440 reports the same, with 0 horizontal overflow. |
| BUG-R2-2 | `ef2f52a`, `33b43eb` | Gallery-enabled fixture: one-column form at 390 and 1440; “Choose photo” fully readable, caption 220/330 px wide, no overlap, Load more `display:none`. |
| BUG-R2-3 | `ef78d67` | Served `public.html` has 0 static `.guest-credit` nodes; live page has exactly 1 dynamic credit. |

Production deploy: `7265e709-7c1a-4af1-9d20-c60d98b092a5`, published
2026-11-01T04:15:09Z. Served `bundle-public.js` =
`c44ae93b1484cba963849970bf85216866145a955bbce403594eb08c858899cc`;
served `bundle-public.css` =
`32c7f20aaa38a5ac860ed7546e448572e44ac80288213eeed84af6534448d87c`.

## Screenshots

- `evidence/r2-before-empty-features-390.png` — empty feature cards, clipped
  album row and duplicate credit before the fixes.
- `evidence/r2-before-empty-features-1440.png` — same defects at desktop width.
- `evidence/r2-fixed-guest-390.png` — local page after the fixes.
- `evidence/r2-album-enabled-390.png` / `-1440.png` — gallery-enabled album
  form after the reflow.
- `evidence/r2-final-live-390.png` / `-1440.png` — deployed page after the
  fixes.
