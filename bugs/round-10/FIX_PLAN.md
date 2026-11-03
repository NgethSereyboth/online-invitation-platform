# Round 10 — fix plan

## BUG-R10-1 — `/templates` layout shift (P1)

**Cause.** `src/js/templates.js` starts `load()` during parsing, and the pack gallery
(`src/js/template-pack-gallery.js`) is injected as a `<script>` and only mounts after
DOMContentLoaded. Its `mount()` inserts an empty `<section>` before `#studioGrid`, then
the catalog fetch replaces it with 36 cards. Nothing reserves that space before first
paint, so the studio grid's visible state (loading/sign-in/empty) is painted at y≈442 and
then pushed to y≈3500 — a 3,000px move, CLS 0.825 at 1440px.

**Fix (root cause — reserve the space before paint).**

1. `src/html/templates.html`: ship the gallery section in the initial markup — heading,
   status line, 36 skeleton cards and the empty-state node — immediately before
   `#studioGrid`, plus a static stylesheet link and a static gallery script tag carrying
   `data-pack-gallery-module` (so `templates.js`'s loader does not inject a duplicate).
2. `src/js/template-pack-gallery.js`: `mount()` adopts the existing static section
   instead of blindly returning when it is present; after a successful render (or a
   failed catalog fetch) it clears `aria-busy` and removes the skeletons.
3. `src/css/template-pack-gallery.css`: style the skeleton cards with the same thumbnail
   aspect ratio and tokens as real cards.

The skeleton preserves the gallery's final geometry through the catalog fetch, so the
studio grid below is off-screen from the first paint and no visible element moves.

**Files.** `src/html/templates.html`, `src/js/template-pack-gallery.js`,
`src/css/template-pack-gallery.css`.

**Verify.** `python3 build.py all`, restart `einvite-app`, re-run `cls_probe.py`
(expect < 0.1 at both widths), then re-run the full six-width sweep.
