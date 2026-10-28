# Capability matrix (2026-10-24, LT-3.1; updated 2026-10-27 at the LT-3.10 Phase 3 close)

Scope: what the product can do today, measured against `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` §6
Phase 3-5. Read-only: no product file changed for this item.

- HEAD when written: `18addd7` (Phase 2 close).
- Status words: **exists** = looked at this session (source line, test name, or a one-line live check);
  **partial** = the capability works but a named sub-part is missing or only works in one path;
  **absent** = no implementation found; **unverified** = could not check without a run I did not do.
- Evidence is source:line unless a test is named. Gate numbers are quoted from
  `artifacts/ui-audit/fixes/STATE.md` (Phase 2 close), not re-run for this matrix.
- **Updated 2026-10-27 at the Phase 3 close (LT-3.10).** The pack rows now quote the delivered tree
  (36 templates, 122 ornaments, thumbnails, bilingual names), the guest-page rows quote FB-90, and §6
  carries the Phase-3-close matrix. The 2026-10-24 pass itself stayed read-only.

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
| Bilingual text block | exists | `src/js/rich-text-editing.js` (`runSelection`/`applyRunMark`, `commit` keeps the run range); `src/js/typography-editor.js` (inspector group "Selected text (run)"); `tests/lt_4_4_run_typography_test.py`; `artifacts/next-work/lt-4-4/NOTES.md` | One object holds EN serif 28 px and KM sans 20 px with identical left edges (624.4 / 51.4 / 509.6) and 0 overflow. Per-run font/size authoring ships from the inspector: the range survives the re-render, exactly the selected run moves, and the marks reach the draft, the server document and a **same-profile reload** (FB-96 fixed the boot capture that used to flatten stored runs before the lazy rich-text modules loaded — `artifacts/next-work/lt-4-4/RELOAD-DEFECT.md`) |

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
| Colour picker | exists | `src/js/color-picker-extras.js` (index bundle, after `studio-experience.js`); `tests/lt_4_3_color_picker_test.py` | Native inputs stay the engine; the popover adds 8 persisted recents, an eyedropper where `EyeDropper` exists, and a text-only WCAG contrast verdict with the measured ratio (shapes/borders get no hint on purpose) |
| Autosave + indicator | exists | `src/js/app.js:863-878`; `tests/v0_52_autosave_status_test.py` | 220 ms local write, idle server write, `Saving…`/`Saved` indicator |
| Crash / draft recovery | exists | `src/js/app.js:437-442` | On boot the local draft is read before the initial fallback; server document can supersede it |
| Unsaved-changes guard | exists | `src/js/app.js` `pendingWrite`/`setPendingWrite` + one `beforeunload`; `tests/lt_4_2_unsaved_guard_test.py` | Cancellable `beforeunload` + `data-save-pending` while the 220 ms write is in flight; the native dialog itself is host-dependent (headless Chromium records none), and the local draft is asserted after the write |
| Shortcut cheat-sheet | exists | `src/js/editor-command-system.js:167`; `src/js/command-palette.js:13,49` | `?` opens the shortcut surface; profiles Standard / Canva / Photoshop; custom bindings |
| Comments | exists | `src/js/collaboration-v24.js:31`; server table `invitation_comments` | Page-level review comments, assignments, CSV export; collaboration UI |
| Version history | exists | `src/js/product-operations.js:23`; `src/js/app.js:3383` | Published snapshots, compare, restore as draft; local named checkpoints in `navigation-history.js:67` |

## 3. Templates and assets

| Capability | Status | Evidence | Note |
|---|---|---|---|
| Shipped templates | exists | `docs/templates/CATALOG.md`; `assets/template-pack/built/` (36); `src/js/builtin-templates.js:2-3` (5); `src/js/adaptive-templates.js:25-44` (4 families) | The delivered tree ships the 36-template Khmer events pack (5 categories, 5 canvases) beside the 5 built-ins and 4 adaptive families; the picker lazy-loads the pack (`src/js/template-pack-loader.js`) outside the editor bundle |
| Template thumbnails / tags / bilingual names | exists | `assets/template-pack/thumbs/` (36 webp); `docs/templates/CATALOG.md`; `src/js/template-pack-gallery.js`; `tests/template_pack_loader_test.py` | 36 editor-rendered thumbnails (668 KB, budget 1.5 MB), bilingual names and tags per template, five gallery filters |
| Motif set + licence record | exists | `docs/ASSETS.md`; `template-pack/PROVENANCE.md`; `tests/test_template_pack_assets_test.py` | 27 original procedural SVGs → 122 recoloured served variants, SHA-256 per file, sanitiser-clean, no third-party artwork |
| Image frames | exists | `src/js/ai-editor-action-extension.js:2` | `none` / `white` / `gold` / `dark`, plus `none` / `circle` / `arch` / `rounded` masks |
| Dividers | exists | `docs/ASSETS.md` (`divider-diamond`, `divider-lotus`, `divider-wave` + recoloured variants) | Three divider motifs with served variants, used inside the pack templates |

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
| Telegram / Messenger / WhatsApp share | exists | `src/js/public-share-panel.js:12` | Telegram, WhatsApp and Facebook share URLs plus a `fb-messenger://` share target; on desktop it falls back to copying the public link (item 3, landed `5f78421`) |
| KHQR / bank-QR display-only gift section | exists | `src/js/product-operations.js:19` (owner card + `/assets/raw` upload); `src/js/public-page.js:63` (`giftQrMarkup`); `src/python/server.py:1401` (validation); `tests/lt_3_2_gift_greeting_test.py:135` | Owner toggle + one raster image (PNG/JPEG/WebP/GIF, ≤ 8 MB upload, server-side allowlist), caption ≤ 80 chars, display-only note; no payment control and no account number stored |
| Personalised `?guest=<name>` greeting | exists | `src/js/public-page.js:9` (`sanitizeGreetingName`), `:109` (`data-guest-greeting`); `tests/lt_3_2_gift_greeting_test.py:135` | NFC, control/format/markup characters dropped, whitespace collapsed, ≤ 40 chars, escaped at render; falls back to the RSVP-token name when the query is empty |
| Guest-page language switch | exists | `src/js/public-page.js:75` (renderer `setLanguage`), `:151-186` (proxy delegation, i18n mirror, observer alignment); `tests/lt_4_1_language_switch_test.py` | The visible topbar `.language-switch` (injected by `core/i18n.js`) and the hidden proxy pair both delegate to the renderer's own switch, and the i18n layer is mirrored to the renderer's language — the control, the date/option labels, the per-invitation key and the body all agree. Found `partial` 2026-10-27 (FB-90), fixed the same day (FB-92) |

## 5. Export

| Capability | Status | Evidence | Note |
|---|---|---|---|
| PNG 1x / 2x / 3x | exists | `src/js/export-quality.js:45,53`; `tests/lt_2_6_export_fidelity_test.py` | MAE 0.0 / 1.03 / 0.89 against the editor |
| PDF with embedded fonts | exists | `src/js/export-quality.js:47`; LT-2.6 PDF probe | 1 page, `NotoSansKhmer` embedded, MAE 2.0-3.6 at 96 dpi |
| PDF bleed / crop marks | absent | `src/js/export-quality.js:47` (`@page margin:0`, no bleed box) | Print surface is exact page size; no bleed allowance or marks |

## 6. Quality bars (Phase 3 close, 2026-10-27)

One full matrix on the frozen tree: `artifacts/next-work/gates/20261027-120242/gates.log`,
`GATES_PASSED` (log `artifacts/next-work/fb-91/gates-all.log`).

| Bar | Result | Source |
|---|---|---|
| Build + bundle check | `BUILD_OK editor bundles manifests mirror` / `MIRROR_CHECK_PASSED (after sync)` | same |
| Smoke | `TOTAL pages=16 consoleErrors=0 non2xx=0` | same |
| Layout guard | `UI_LAYOUT_GUARD_PASSED` (0 long-task, 0 nameless-control failures) | same |
| Pytest | **183 passed** in 426.86 s | same |
| Route budgets | `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED` (6 pages within budget) | same |
| LHCI | `LHR reports=16/16 minA11y=1.00`, `Healthcheck passed!` | same |
| CSP | `CSP_CHECK_PASSED`, 0 violations | same |
| Canvas | `CANVAS_MOTION_VERIFY_PASSED` (22 pass / 0 fail / 2 skipped) | same |
| `!important` pin | `total=3816` ≤ pin 3823 | same |
| Editor CLS | median 0.1415 (target ≤ 0.1, accepted miss) | FB-75 |

## 7. What this means for the next items

- **Phase 3 closed 2026-10-27 (LT-3.10).** LT-3.2…LT-3.9 is complete — items (1)(2)(4)(5)(6)(7)
  were already `exists` and are skipped with this table as evidence; (3) Messenger share landed
  2026-10-25 (`5f78421`); (8) the display-only gift QR and the sanitised `?guest=` greeting landed
  2026-10-27 (FB-90, `artifacts/next-work/fb-90/NOTES.md`). The one new `partial` this pass found —
  the guest-page language switch — is the row above and should be its own small item.
- **Phase 4 is scoped to these `absent`/`partial` rows:** bilingual per-run font/size authoring
  (§1). The guest-page language switch found at the close was fixed the same day (FB-92); the
  unsaved-changes guard, the colour-picker extras and per-run authoring closed 2026-10-27
  (`artifacts/next-work/lt-4-2/NOTES.md`, `lt-4-3/NOTES.md`, `lt-4-4/NOTES.md`). Every other editor
  row is `exists` and must not be rebuilt. The one defect found inside LT-4.4 that is *not* an editor
  capability — a same-profile reload flattening the title's runs — was fixed as **FB-96** (the boot
  capture ran before the lazily loaded rich-text modules and dropped the stored model); the trace and
  fix are in `artifacts/next-work/lt-4-4/RELOAD-DEFECT.md`.
- **Phase 4 closed 2026-10-27 (LT-4.close, FB-97):** LT-4.1…LT-4.4 plus FB-96 are done, and one
  full matrix is `GATES_PASSED` — build, bundles, smoke 16/0/0, layout, pytest **187 passed**
  (no red this time), budgets 6/6, LHCI 16/16 `minA11y 1.00`, CSP 0 violations, canvas 22/0/2,
  `!important` 3816 ≤ 3823 — `artifacts/next-work/gates/20261027-162311/gates.log`. The 0.68.7
  `VERSION_HISTORY` entry is drafted in `artifacts/next-work/OWNER-QUEUE.md` (file owner-held, OD-3).
- **Phase 5 is complete via the pack** — its three former gaps are `exists` above; the close-out
  bookkeeping is TP-6.4 in `docs/templates/FINAL-REPORT-2026-10-25.md`.
- **Phase 6 closed 2026-10-27 (LT-6.close, FB-103):** LT-6.1…LT-6.5 are done and one full matrix is
  `GATES_PASSED` — build, bundles, smoke 16/0/0, layout, pytest **189 passed** (no red), budgets 6/6,
  LHCI 16/16 `minA11y 1.00`, CSP 0 violations, canvas 22/0/2, `!important` 3809 ≤ pin 3809 —
  `artifacts/next-work/gates/20261027-211049/gates.log`. **No capability row in §1–§5 changed:** the
  phase is performance, weight and gate durability — LT-6.1 headroom (worst route `index.html` 420 ms
  of the 600 ms ceiling, no split), LT-6.2
  [`docs/perf/BUDGET-STATE-2026-10-24.md`](perf/BUDGET-STATE-2026-10-24.md), LT-6.3 (7 provably-dead
  `!important` tokens removed, pin 3823 → 3809), LT-6.4 (20 MB upload refused with a named limit on all
  three paths; 8.3 MB stored as a 2.18 MB WebP) and LT-6.5 (50 page cycles + a 500-step history inside
  stated CDP heap bounds; the 400-cycle discriminator shows no leak). The 0.68.9 `VERSION_HISTORY` entry
  is drafted in `artifacts/next-work/OWNER-QUEUE.md` (file owner-held, OD-3).
- **Phase 7 started 2026-10-27 (LT-7.1, FB-104, read-only):**
  [`docs/ROADMAP-RECONCILIATION-2026-10-24.md`](ROADMAP-RECONCILIATION-2026-10-24.md) now carries one
  row per acceptance bullet of roadmap Parts 3–6 (37 bullets: **22 `exists` / 10 `partial` / 5
  `absent`**) with `path:line`, test-name or run evidence. It confirms this matrix's editor, guest and
  export rows, and adds the rows this matrix never covered: tenant isolation, sessions, admin tools and
  analytics. Its absent rows are field-level encryption of the listed columns, API keys, secrets
  rotation, automatic version snapshots and the analytics retention scheduler; it also replaces the
  plan's LT-7.2 risk order (tenant isolation, session management and analytics privacy/export already
  exist and pass).
- **Phase 7 closed 2026-10-28 (LT-7.2 FB-105, LT-7.close FB-106):** the eight absent/partial roadmap
  rows are closed — field-level encryption of all six listed columns (with a migration /
  rollback / `--reencrypt` path and a per-data-dir key), step-up on 15 destructive admin routes
  **plus the admin page that can obtain the grant**, scoped API keys with a per-key limit and audit,
  signed webhook delivery with retries, a secrets-rotation doc + script, one
  `analytics_retention_run` log line per prune pass, and the `security_*` collection-order coupling
  fixed at the cause. [`docs/ROADMAP-RECONCILIATION-2026-10-24.md`](ROADMAP-RECONCILIATION-2026-10-24.md)
  now reads **30 `exists` / 6 `partial` / 1 `absent`** (from 22/10/5); Parts 4 and 5 have no open row.
  Gate record, stated plainly: build, bundles, smoke `16/0/0`, layout (1533 checks), budgets 6/6,
  LHCI 16/16 `minA11y 1.00`, CSP 0 violations, canvas 22/0/2 and `!important` 3809 ≤ pin 3809 are
  green; pytest is **200 passed, 1 failed** on the pre-existing `lt_2_6` PDF metric, which reads
  4.24–4.75 against its locked 4.5 tolerance (the test compares an editor screenshot with a PDF
  raster; Chromium prints the 420 px page as 420.16 px). No threshold, fixture or product rendering
  code was changed; the decision is in `artifacts/next-work/OWNER-QUEUE.md`. The three owner-held
  `VERSION_HISTORY.md` entries (0.69.0 Part 4 minor, 0.70.0 Part 5 minor, 0.70.1 Phase 7 patch) are
  drafted there too.

No owner question. No product edit. No FB number consumed (evidence only).
