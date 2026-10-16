# Design-space preview — Canva-style editor rebuild (review guide, 2026-10-16)

Standalone visual rebuild of the **editor page** (`src/html/index.html`) in the Canva design-space
layout: top bar → tool rail + panel → centred artboard → contextual inspector. **Design layer only —
no editor logic.** It is built standalone, ahead of any `src/` change, so the direction can be
approved before integration work starts.

**Status:** awaiting review. No application file was touched by this pass — the preview lives in
`artifacts/` (gitignored), and this guide is the part that travels with the repo.

## 1. Where it is and how to open it

| File | What it is |
| --- | --- |
| `artifacts/design-space-preview/design-space.html` | the whole page (~47 KB) |
| `artifacts/design-space-preview/design-space.css` | all styling (~38 KB); `:root` mirrors `src/css/tokens.css` 1:1, `@font-face` points at the real `assets/fonts/*.woff2` |
| `artifacts/design-space-preview/README.md` | short open/integration notes |

`artifacts/` is gitignored (`.gitignore:41`), so the page does not ship with the repo. Double-click
`design-space.html` (fonts resolve via `../../assets/fonts/`), or serve it:

```powershell
python -m http.server 4186 --directory F:\Project\eInvite\online-invitation-platform
# http://127.0.0.1:4186/artifacts/design-space-preview/design-space.html
```

## 2. What's in it

- **Top bar** — the real set from `index.html`: collapse «, brand, "Untitled design" ✎, •••,
  EN | ខ្មែរ, Saved locally ●, Local mode, Undo / Redo, Guest preview, Publish snapshot (primary),
  AI, ⌘K
- **Tool rail** — 7 tools, one scrollable panel each: Content, Templates, Elements, Text, Materials,
  Pages, Music
- **Canvas** — 390 × 844 artboard, safe-area guides, selection overlay, floating object card
  **below** the selection (Canva behaviour), device pills (Mobile / Tablet / Desktop), zoom with
  Fit / Hand / Rulers
- **Inspector** — Design / Content / Animate, carrying the real option sets (font families incl.
  Khmer Sans, alignment, animation list, layers)
- **Responsive** — 1440 / 1024 / ≤900 (desktop hint) / ≤760

## 3. Why this should be less buggy than the current editor

All switching is **CSS-only**: hidden radios/checkboxes (`ds-tool-*`, `ds-insp-*`, `ds-collapse`,
`ds-lang-km`) plus `:has()`. Tool panels, inspector tabs, panel collapse and the EN | KM toggle have
no JS state to desync, the page renders identically from `file://` and over HTTP, and the control
inputs stay real form controls (focus rings, keyboard) rather than scripted divs.

## 4. Fidelity rules honoured

- **Colour:** tokens only (`--brand #8b465b`, `--brand-soft #f5e8ed`, …) — no literals
- **Type:** the real EInvite faces; Inter is declared locally because the standalone has no
  page-level Inter `@font-face`
- **Strings:** real labels from `index.html` and `docs/i18n/TRANSLATIONS.csv`; labels without a
  translation keep the EN-fallback inside the KM span — **no invented Khmer**
- **CSS:** no `!important`; `:has()` is sanctioned by `docs/certification/BROWSER-MATRIX.md`

## 5. Evidence (headless)

Playwright Chromium `149.0.7827.55`, 2026-10-16, opened from `file://`:

- fonts: 6 of 11 declared families load on first paint (the unused EInvite variants stay
  unloaded); **zero console errors**
- scripted: tool radio `ds-tool-templates` switches the panel; `ds-lang-km` flips every bilingual
  span; inspector tabs and the collapse checkbox likewise
- pixel-diff of the artboard across interaction states = 0.000 (no flicker); this run's full-page
  1440 × 900 render vs the earlier verified capture: **identical (diff bbox = none)**
- screenshots reviewed at 1440 × 900, 1024 × 768 and 390 × 844

## 6. Intentionally out of scope

- Editor behaviour (selection, publishing, uploads, undo history) — visual layer only
- Artboard copy ("Dara & Sokha · Saturday · 14 March 2026 · …") is placeholder
- Light theme only — dark mode arrives via tokens at integration time

## 7. Integration plan (only after approval)

1. Move the layout rules into `src/css/pages/editor.css` (+ route sources); delete the mirrored
   `:root` / `@font-face` blocks and reuse `tokens.css` + `typography-fonts.css`
2. The editor JS binds to the current IDs (`#names`, `#stage`, `#properties` …) → selector-mapping
   pass; the `:has()` switching keeps the same inputs or gets a tiny delegation shim
3. `python3 build.py bundles` then `python3 build.py bundles --check` → must print
   `ROUTE_BUNDLE_CHECK_PASSED`

## 8. Questions for review

1. Default open tool — Content (current mock) or Templates?
2. Rail + panel width 240 px — keep, or narrower?
3. Floating card below the selection — keep (Canva), or above?
4. Anything missing from the top bar / rail / inspector before this replaces the current editor?
