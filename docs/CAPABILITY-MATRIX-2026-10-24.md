# Capability matrix (2026-10-24, LT-3.1, read-only)

Scope: what the product can do today, measured against `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` §6
Phase 3-5. Read-only: no product file changed for this item.

- HEAD when written: `18addd7` (Phase 2 close).
- Status words: **exists** = looked at this session (source line, test name, or a one-line live check);
  **partial** = the capability works but a named sub-part is missing or only works in one path;
  **absent** = no implementation found; **unverified** = could not check without a run I did not do.
- Evidence is source:line unless a test is named. Gate numbers are quoted from
  `artifacts/ui-audit/fixes/STATE.md` (Phase 2 close), not re-run for this matrix.

## 1. Khmer engine

| Capability | Status | Evidence | Note |
|---|---|---|---|
| Font pairing (Khmer + Latin) | exists | `src/js/typography-editor.js`, `src/css/typography-system.css`, `src/css/typography-fonts.css`; FB-71 in STATE | One `:lang(km)` stack backed by bundled Noto Sans/Serif Khmer; 48/48 sampled labels used the bundled face at FB-71 |
| Line-height | exists | `src/css/typography-fonts.css`; FB-71 min 1.6 | Minimum measured line-height 1.6 after FB-71 (was 1.15 on the language switch) |
| Wrapping / line breaking | exists | `tests/lt_2_1` probe; `artifacts/next-work/lt-2-1/wrap-probe.json` | 24 cases, 67 breaks, 0 inside a grapheme cluster, 67/67 on a word boundary; no helper added |
| IME / composition input | exists | `tests/lt_2_5_khmer_input_test.py`; `1 passed in 18.55s` in STATE | 24/24 code points survived three composition chunks, save, and reload |
| Paste | exists | `tests/lt_2_5_khmer_input_test.py` | A second map string pasted byte-for-byte into model, server draft, and reloaded DOM |
| Khmer numerals | exists | `src/core/khmer-format.js`; `tests/lt_2_2_khmer_format_test.py` | `0x17E0 + n`, setting default off, round-trips through the draft |
| Khmer-formatted dates | exists | `src/core/khmer-format.js`; `src/js/public-page.js:17`; LT-1.3 | `km-KH-u-nu-khmer`, optional Buddhist Era, English fallback when ICU is filtered |
| Lunar line | exists | `src/js/public-page.js:8` (`momentkh`), `src/js/app.js:1185` (editor preview) | Owner-entered line; vendor library untouched |
| Bilingual text block | partial | `src/js/typography-editor.js`; LT-2.3 evidence | One object holds EN serif 28 px and KM sans 20 px with identical left edges (624.4 / 51.4 / 509.6) and 0 overflow; per-run font/size authoring for mixed text is not exposed |

## 2. Editor

| Capability | Status | Evidence | Note |
|---|---|---|---|
| Drag | exists | `tests/v0_52_free_canvas_drag_test.py`; `src/js/app.js` pointer path | Gate-backed free canvas drag |
| Resize | exists | `tests/v0_52_resize_handle_ownership_browser_test.cjs`; `src/js/app.js:1173-1175` | `.resize-handle` on text, image, shape; ownership test exists |
| Rotate | exists | `src/js/app.js:1173-1175`, `src/css/organized/professional-editor.css` (`.pe-rotate`); `src/js/canvas-plus.js:187` | Visible rotate handle plus numeric rotation in the transform panel |
| Multi-select | exists | `src/js/app.js:2196` marquee; `tests/v17_professional_editor_test.py:59` (shift toggle, Escape, Ctrl+A) | Marquee adds `.multi-selected`; shift toggles |
| Group / ungroup | exists | `src/js/professional-layers.js:43`; `src/js/editor-command-system.js:167`; `tests/v17_professional_editor_test.py` | Command and layer-panel actions; group ids remapped on paste and duplicate |
| Duplicate | exists | `src/js/app.js:1784` (page), `src/js/editor-command-system.js:167` (selection), `src/js/ai-editor-action-service.js:125` (page clone) | Object and page duplicate |
| Copy / paste | exists | `src/js/app.js:1763-1765`; `tests/v17_layers_clipboard_history_test.py` | Clipboard is browser-local, group ids remapped, paste offsets by 3% |
| Lock / hide | exists | `src/js/app.js:1417`; `src/js/professional-layers.js:33,43`; `src/css` `.object.locked` | Locked objects lost handles; hidden/locked never enter select-all |
| Nudge | exists | `src/js/editor-command-system.js:112`; `src/js/app.js:3441` | Arrow keys 1 px, Shift+Arrow 10 px, repeatable command |
| Undo / redo | exists | `src/js/app.js:413,561-591`; `tests/v17_layers_clipboard_history_test.py` | One gesture costs one history entry; selection restored with the document |
| Guides / snapping / spacing / grid | exists | `src/js/editor-pro.js:127-188`; canvas gate `22 pass / 0 fail / 2 skipped` | World-space snap resolver, user guides, equal-spacing provider, measurement badges, grid toggle |
| Layers panel | exists | `src/js/professional-layers.js`; `tests/layers_panel_guard_test.py` | Reorder, search, type/hidden/locked filters, rename, group, visibility, lock |
| Pages with thumbnails | exists | `src/js/app.js:1740-1760`; `src/js/typography-editor.js:51` | Thumbnail renders page background and objects; drag reorder; duplicate; enable/disable |
| Colour picker | partial | `src/js/editor-pro.js:366`; `src/js/brand-components.js:45` | Native colour inputs and brand palettes work; no recents, no eyedropper, no contrast hint inside the picker |
| Autosave + indicator | exists | `src/js/app.js:863-878`; `tests/v0_52_autosave_status_test.py` | 220 ms local write, idle server write, `Saving…`/`Saved` indicator |
| Crash / draft recovery | exists | `src/js/app.js:437-442` | On boot the local draft is read before the initial fallback; server document can supersede it |
| Unsaved-changes guard | absent | `beforeunload` only in `src/js/crdt-yjs-indexeddb.js:341` and `src/js/dashboard.js:12` | Editor relies on autosave; no confirm dialog before leaving with a pending write |
| Shortcut cheat-sheet | exists | `src/js/editor-command-system.js:167`; `src/js/command-palette.js:13,49` | `?` opens the shortcut surface; profiles Standard / Canva / Photoshop; custom bindings |
| Comments | exists | `src/js/collaboration-v24.js:31`; server table `invitation_comments` | Page-level review comments, assignments, CSV export; collaboration UI |
| Version history | exists | `src/js/product-operations.js:23`; `src/js/app.js:3383` | Published snapshots, compare, restore as draft; local named checkpoints in `navigation-history.js:67` |

## 3. Templates and assets

| Capability | Status | Evidence | Note |
|---|---|---|---|
| Shipped templates | exists | `src/js/builtin-templates.js:2-3` (5), `src/js/adaptive-templates.js:25-44` (4 families) | Built-in: Royal Khmer Gold, Modern Cambodian Luxury, Botanical Blush, Editorial Birthday, Modern Event. Adaptive: Khmer Royal Wedding, Modern Editorial Wedding, Government Delegation Welcome, Conference and Forum |
| Template thumbnails / tags / bilingual names | partial | `src/js/builtin-templates.js:2`; `src/js/adaptive-templates.js:56` | Tags and category exist; adaptive picker shows a page strip, not a rendered thumbnail; names are English-only |
| Motif set + licence record | absent | `docs/ASSETS.md` does not exist; ornaments in templates are text glyphs (`src/js/adaptive-templates.js:28-32`) | No original SVG motif library; no asset licence register |
| Image frames | exists | `src/js/ai-editor-action-extension.js:2` | `none` / `white` / `gold` / `dark`, plus `none` / `circle` / `arch` / `rounded` masks |
| Dividers | absent | only generic shape lines (`src/js/adaptive-templates.js:15`, shape kind `line`) | No named divider asset or divider block |

## 4. Guest page

| Capability | Status | Evidence | Note |
|---|---|---|---|
| Opening scene, skippable, reduced-motion safe | exists | `src/js/opening-scenes.js:7-8` | ESC skips when `skipAllowed !== false`; `prefers-reduced-motion` sets `transition:none` and hides immediately |
| Multi-event schedule | exists | `src/js/public-page.js:59,95` | `events[]` with name, date, time, venue, per-event map URL and add-to-calendar |
| Map link | exists | `src/js/public-page.js:95` (main venue), `:59` (per event) | Only `http(s)` links accepted |
| Dress code | exists | `src/js/public-page.js:60` | Guest-information block, rendered only when the owner filled it |
| Gallery | exists | `src/js/public-page.js:63` | Grid/carousel styles, lazy images, optional gallery password |
| Countdown | exists | `src/js/public-page.js:95`; `startCountdown` `:71` | Honours the per-invitation Khmer numerals setting |
| Contact | exists | `src/js/public-page.js:65` | Phone and Telegram only; toggleable |
| RSVP completeness | exists | `src/js/public-page.js:93,105-106`; `src/python/server.py:8150`; `src/js/responses.js:16` | Required name, status enum, guest-count clamp, required custom fields, select/number validation, hidden honeypot, 12/min/IP rate limit, success and error states, owner CSV |
| Music off by default | exists | `src/js/public-page.js:97`; `src/js/builtin-templates.js:2` (`musicEnabled:false`) | Starts after the cover opens; explicit play/pause; autoplay-policy safe |
| OG / Twitter meta + preview image | exists | `src/html/public.html:8-19`; `src/python/server.py:10664`; `src/js/social-card.js` | Server injects absolute title, description, URL and a generated 1200x630 image path |
| Copy link | exists | `src/js/public-share-panel.js:18` | Copy public link and copy invitation message, with clipboard fallback |
| QR | exists | `src/js/public-share-panel.js:18` (`/qr-card.png`); `src/python/server.py:1028` | Branded QR download; guest personal QR also exists in `src/js/guests.js:57` |
| Telegram / Messenger / WhatsApp share | partial | `src/js/public-share-panel.js:18` | Telegram and WhatsApp share URLs plus Facebook sharer; no Messenger share target |
| KHQR / bank-QR display-only gift section | absent | `src/js/public-page.js:60`; `src/js/product-operations.js:19` | Only outbound gift-registry and payment links; no owner-uploaded QR image, no toggle |
| Personalised `?guest=<name>` greeting | absent | `src/js/public-page.js:74` reads only `?g=` (guest token) | Guest name comes from the server token response (`p.guest.name`), never from a query name; no sanitised query path |

## 5. Export

| Capability | Status | Evidence | Note |
|---|---|---|---|
| PNG 1x / 2x / 3x | exists | `src/js/export-quality.js:45,53`; `tests/lt_2_6_export_fidelity_test.py` | MAE 0.0 / 1.03 / 0.89 against the editor |
| PDF with embedded fonts | exists | `src/js/export-quality.js:47`; LT-2.6 PDF probe | 1 page, `NotoSansKhmer` embedded, MAE 2.0-3.6 at 96 dpi |
| PDF bleed / crop marks | absent | `src/js/export-quality.js:47` (`@page margin:0`, no bleed box) | Print surface is exact page size; no bleed allowance or marks |

## 6. Quality bars (latest numbers, not re-run)

| Bar | Result | Source |
|---|---|---|
| Build + bundle check | pass | `artifacts/next-work/gates/20261025-150432/` |
| Smoke | 16 pass / 0 fail / 0 skip | same |
| Layout guard | 1533 checks, 0 failed | same |
| Pytest | 161 passed | same |
| Route budgets | 6/6 | same |
| LHCI | 16/16, accessibility 1.00 | same |
| CSP | pass, 0 violations | same |
| Canvas | 22 pass / 0 fail / 2 skipped | same |
| `!important` pin | 3816 <= 3823 | same |
| Editor CLS | median 0.1415 (target <= 0.1, accepted miss) | FB-75 |

## 7. What this means for the next items

- **LT-3.2 and later** start from the gaps above, in the plan's binding order. Items (1), (2), (4),
  (5), (6), (7) in the plan's list already meet the bar and are skipped with this table as evidence.
- The remaining Phase 3 work is: Messenger share (item 3, one missing target; Telegram, WhatsApp and
  QR already exist), and the gift section plus personalised greeting (item 8, both absent).
- Phase 4 is scoped to these `absent`/`partial` editor rows: colour-picker extras, unsaved guard, and
  the `partial` bilingual per-run authoring. Everything else in the plan's Phase 4 priority list is
  already `exists` and should not be rebuilt.
- Phase 5 is scoped to: thumbnail/bilingual template names (partial), motif set + licence record
  (absent), dividers (absent), and filling the template count from 9 families to the plan's six
  styles only where a style is genuinely missing.

No owner question. No product edit. No FB number consumed (evidence only).
