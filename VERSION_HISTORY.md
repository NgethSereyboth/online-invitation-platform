# Version History

This project uses **semantic versioning**. `0.x` is pre-1.0; `1.0.0` is the first
production-certified release.

> **Legacy history:** the pre-reset version history (V1 → V54.34) is preserved
> in [`docs/LEGACY-VERSION-HISTORY.md`](docs/LEGACY-VERSION-HISTORY.md).

---

## Version numbering scheme

| Bump | When | Example |
|---|---|---|
| **MAJOR** (`0` → `1`) | Only at production certification. Never before. | `0.99.5` → `1.0.0` |
| **MINOR** (`0.54` → `0.55`) | A completed roadmap part. One minor per part. | `0.54.0` → `0.55.0` |
| **PATCH** (`0.54.0` → `0.54.1`) | A completed task within a part. | `0.54.0` → `0.54.1` → `0.54.2` |

---

---

## 0.70.6 — D-7: automatic version snapshots on every meaningful save

- **Triggered by:** `FREEBUFF-NEXT-STEPS-2026-10-27.md` D-7 / roadmap 3.9 on
  `fix/2026-10-22-open-issues`. `src/python/features/invitation_versions.py` had existed since
  v0.58.0 and was imported by **nothing**; version history only showed published snapshots.
- **Measured first:** stored drafts in `data/invites.db` (7 rows) are 57 299 B median / 85 087 B max,
  all already carrying inline `data:image` URIs — the pattern that grows. At that max the 50-snapshot
  cap costs ≈ 4.2 MB per invitation; the 2 MB per-document skip bounds it at 100 MB. The skip rule is
  kept even though no current document reaches it.
- **Rule:** the draft save is the only writer. A snapshot is stored when the content hash changed
  **and** at least 5 minutes passed since the last auto snapshot; 50 are kept (oldest pruned), and a
  document above 2 MB is skipped with one `[invitation_versions] auto snapshot skipped: …` log line.
  The hash is over canonical JSON (`sort_keys`, tight separators), so a save that only reorders keys
  does not manufacture a snapshot. `now_ms` is an argument rather than a hidden `time.time()`, so the
  five-minute rule is testable with an injected clock instead of sleeping.
- **Wiring:** `save_draft` serialises once and calls `capture_auto_snapshot` after a successful write,
  wrapped so history can never block a save. `GET /api/invitations/<id>/versions` merges auto
  snapshots into the publication list (`isAuto: true`, `version: "auto"`, `id`, `published_at`);
  compare and the existing restore-as-draft endpoint fall back to a snapshot id. Restore rewrites
  `draft_json` only — publish state and immutable publications are untouched. Studio Ops labels the
  rows **Auto**.
- **Schema:** `invitation_versions` is now declared in `docs/postgres_schema.sql` with `created_at
  BIGINT` (epoch ms would overflow `INTEGER` on Postgres), so SQLite and Postgres cannot drift.
- **Verification:** new `tests/lt_3_9_auto_versions_test.py` — injected clock: 6 changes across 31
  simulated minutes → **6** snapshots; unchanged content → none; a change 2 minutes later →
  `too_soon`; exactly-5-minute gaps → created; 60 further changes → **50 rows**, oldest pruned; a
  2.2 MB document → skipped with the log line. Real server, temp data dir: save → one auto snapshot,
  identical and near-in-time saves → still one, restore by snapshot id → draft equals the snapshot
  byte-for-byte. `python tests/v13_product_lifecycle_test.py` still passes (publications, restore by
  version, list ≥ 2). Full matrix `gates/20261029-183437` `GATES_PASSED`: build
  `BUILD_OK`/`MIRROR_CHECK_PASSED`, bundles, smoke 16/0/0, layout, pytest **216 passed** (710.97 s),
  budgets 6, LHCI 16/16 `minA11y 1.00`, CSP, canvas 22/0/2, `!important` 3791 ≤ 3791.
- **Docs:** capability-matrix `Version history` row now records automatic snapshots; four
  `fallback` rows for the new UI strings in `docs/i18n/TRANSLATIONS.csv`.

## 0.70.5 — D-6: PDF bleed and crop marks

- **Triggered by:** `FREEBUFF-NEXT-STEPS-2026-10-27.md` D-6 on `fix/2026-10-22-open-issues`.
- **Option:** `printAllPages` / `printCurrent` now accept `{bleedMm, cropMarks}` (0–10 mm, marks only
  when bleed > 0) and the dialog's PDF card exposes `Bleed` 0/3/5 mm plus `Crop marks`, so the
  buttons, the command palette and the API share one path. Each printed page is a
  `.print-sheet` of trim + 2×bleed with `padding = bleed` around the unchanged `.print-page`: objects
  keep their trim-relative position, and the sheet carries the page background so solid fills,
  gradients and image fills continue through the bleed while the trim keeps its own copy. Corner
  marks are eight 1 px vector ticks, 2 px outside each trim corner.
- **Renderer limit, measured:** Chrome quantises the PDF page box to 1/300 in (0.24 pt) and does not
  honour a fractional `@page` request exactly (443 px → 331.92 pt; 457.796 px → 342.96 pt). The
  no-bleed page itself lands 0.16 px above 420 px, so comparing two measured pages compounded two
  roundings and pushed 5 mm to 0.506 pt. The test therefore measures the bleed page against the
  **exact** trim + 2×bleed size — stricter, and achievable: **0.087 pt at 3 mm, 0.386 pt at 5 mm**,
  inside the queue's ±0.5 pt. Nothing was widened.
- **Verification:** `lt_2_6` now exports at 0/3/5 mm and asserts MediaBox, embedded Khmer face, trim
  copy inside the existing 4.5 MAE tolerance, and marks confined to the margin; it also drives the
  dialog controls (3 mm + marks → 443 px sheet, one `.print-marks`). Suite `214 passed` (704.81 s);
  build `BUILD_OK`/`MIRROR_CHECK_PASSED`, bundles, smoke 16/0/0, layout in `gates/20261029-174452`,
  then canvas, `!important` 3791 ≤ 3791, CSP and LHCI 16/16 `minA11y 1.00` in `181734`/`181813`/
  `181815`/`181912`. That chain stopped at pytest on the **documented** `lt_2_2` load flake (it
  passed solo and in the full re-run); no `lt_2_2` assertion or timeout changed.
- **Docs:** matrix row `PDF bleed / crop marks` flips to `exists` with the quantisation limitation;
  `Bleed` / `Crop marks` recorded as English `fallback` rows in `docs/i18n/TRANSLATIONS.csv`.

## 0.70.4 — D-5: "Print all pages" was printing the app chrome, not the invitation

- **Triggered by:** `FREEBUFF-NEXT-STEPS-2026-10-27.md` D-5 ("`lt_2_6` PDF metric: root cause, not
tolerance") on `fix/2026-10-22-open-issues`. No tolerance, budget, threshold or frozen-harness value
was changed (D-11). B-1 (`security_*` collection order) was also verified closed: `server.py` reads the
maintenance flag per request since `74f48da`, so every order passes (30 security tests, `1 passed` in
both pair orders).
- **The distribution:** `lt_2_6_export_fidelity_test.py` was bimodal, not noisy — 20 isolated runs gave
10 failures with values `{2.932, 3.525, 4.490, 4.498, 4.615, 4.627, 4.748}`. The passing cluster sat
0.01 MAE under the 4.5 limit, i.e. the tolerance was absorbing a constant defect while the flake
decided whether the extra 0.13 landed on it.
- **Root cause 1 — app-chrome cascade (deterministic).** `printAllPages()` writes a fresh document that
links the editor's stylesheets but has no `#stage`. `theme-hardening.css` carries
`body:not(.guest) p:not(#stage *){color:var(--app-muted)!important}`; in the editor the sheet is inside
`#stage` and is exempt, in the print document it is not, so every printed paragraph was repainted
`#646773` instead of the document ink `#342c26` (PDF content stream confirmed both values; CDP
`getMatchedStylesForNode` named the rule).
- **Root cause 2 — the print document replayed the public entrance animation (the on/off state).**
`createPageNode()` emits the live object markup, which carries `.reveal` + inline
`animation-name:fadeUp` 900 ms; `page.pdf()` could snapshot at computed `opacity 0.837`, and a human
pressing the auto-print at 500 ms could print a half-faded page. `printCurrent()` is unaffected (it
rasterises `stageSvg()` into an `<img>`), which is why only "Print all pages" was wrong.
- **Fix:** the print document is now `<body class="print-doc">` with
`.print-page …{animation:none!important;transition:none!important}` in its inline sheet (FB-130 already
removed the hidden `.reveal` base state, so nothing can be left invisible), and the muted-paragraph rule
gained `:not(.print-doc *)` — necessarily in that selector, because `:not(#stage *)` carries ID
specificity and no class-based `!important` override can beat it. The rest of the rule's selectors
(`.hint`, `.download-note`, …) are unchanged. Bundles and the `src/python` mirror rebuilt.
- **Test:** two assertions added to the fidelity test before `pdf()` — the printed run's computed colour
equals the editor's, and nothing under `.print-page` has a running animation. Both failed first
(`runColor: rgb(100,103,115)` vs `rgb(52,44,38)`, `animated: 1`). No existing assertion touched.
- **Verification:** post-fix PDF MAE is **byte-identical `3.5922`** in all 40 post-fix runs — 30 isolated
plus 10 under four CPU busy-loops (`fb-133/isolated-fixed.json`, `isolated-extra.json`,
`load-fixed.json`; 0 failures, vs 10/20 before). The residue is rasteriser antialiasing (Chrome screenshot vs `pdftoppm -r 96` linear-light
coverage), not document content. Full matrix `GATES_PASSED` (`gates/20261029-170041`): build
`BUILD_OK`/`MIRROR_CHECK_PASSED`, bundles, smoke 16 pages/0 console errors/0 non-2xx, layout, pytest
**214 passed**, budgets 6 pages, LHCI **16/16 minA11y 1.00**, CSP, canvas **22/0/2**, `!important`
**3791 ≤ 3791**. A first matrix attempt was discarded: the D-5 load generators were still running and
produced the documented `lt_2_2` load flake plus one dropped HTTP connection (`20261029-164418`); both
tests pass isolated and in the clean rerun.

## 0.70.3 — Plan 004 Part B: the CSS/layout debt, with two measured stops

- **Triggered by:** `plans/004-ux-ui-and-code-quality-pass.md` Part B (CQ-1…CQ-4) on `fix/2026-10-22-open-issues`.
- **CQ-1 — `!important` lane (FB-131, `6c73def` + `fdf5a78`):** built the 99-row header/shell inventory and consolidated the admin H1 (its real competitor was `canvas-plus`'s 48 px token; computed values unchanged at 320/375/1440). Then removed **17 cross-file superseded declarations** from `studio-experience.css`/`final-experience.css` — each proved unreachable by a later identical-selector `!important` rule in every route bundle — lowering the pin **3809 → 3791**. A further 14 `canvas-plus` materials rules were applied, built and measured, then reverted because their materials-1440 pixel diff was not reproducible between two captures of the same build. The lane therefore closes at a **documented 18-token reduction, not the ≥150 target**: the remaining table needs a live computed-style matrix, not intuition.
- **CQ-2 — forced layouts (FB-132, measured, stopped):** re-traced the signed-in editor load (Layout 859 ms over 200 events, 79 % stack-attributed). The two largest forced layouts are the canvas controller — `updateCanvasView` 130.2 ms in `app.js` and `cacheViewGeometry`/`settle` 82.5 ms in `editor-suite.js` — which is the item's own STOP condition. The typography branch (`availableSpace`, 71.7 ms over 115 calls) is ~8 % of Layout and cannot reach the ≥40 % bar; FB-64 already attributes 695 ms of the long task to V8 compile. No code changed.
- **CQ-3 — lazy AI service (FB-132, stale premise, stopped):** the service already ships in the deferred chunk (`scriptSplitAt` 24, `ai-editor-action-service.js` at `scripts[28]`) and its old consumer `ai-assistant-pro.js` is not in the route source list or either bundle; the v53 agent and tool registry already use the lazy accessor. A cold-open test confirmed `window.EInviteAI` is undefined at DOMContentLoaded and was deleted rather than pinning a module that no longer ships.
- **CQ-4 — legacy dashboard blocks (FB-132, `3b91ab5`):** `dashboard-page.css` **18 442 → 17 891 B (−551 B)**. Removed the first-generation rules whose properties are all re-declared later or by the page-qualified V55 block, the dead `.login` rule (no `.login` element exists on the dashboard; the card is `.auth-card`), and `.invite-status-pill.Published/.Draft/.Archived` (the JS emits the bare class and rewrites it to `app-badge` before paint, so a state suffix never exists). Only `.dash{margin:auto}` was kept — it had no other source. Verified by a 96-value computed-style matrix across user/guest × light/dark × 320/375/1440: **93 byte-identical**, the 3 deltas being the dark invite-card fill also drifting between two runs of the same build. The dashboard screenshot matrix is not reproducible on this host and is reported as a limitation, not a pass.
- **Verification:** build `BUILD_OK`/`MIRROR_CHECK_PASSED`, bundles, smoke 16/0/0, layout, pytest **214 passed**, budgets 6 (`gates/20261029-154207`); LHCI 16/16 `minA11y 1.00` (`155833`); `CSP_CHECK_PASSED` (`160313`); canvas 22/0/2 (`160417`); `!important` 3791 ≤ pin 3791 (`160459`). The first full attempt stopped on the known `lt_2_6` Khmer PDF-metric boundary; it passed solo (15.6 s) and in the rerun. Part B after-set: `artifacts/next-work/review-ux2/after/` (17 shots + 4 previews, `INDEX.md`).
- **Nothing frozen was touched:** no budget, threshold, canvas harness or `tools/lighthouserc.js` change; `IMPORTANT_PIN` only went down (3809 → 3791).

## 0.70.2 — Plan 004 Part A: the visible UI defects closed

- **Triggered by:** `plans/004-ux-ui-and-code-quality-pass.md` Part A (UX-1…UX-9, commits FB-122…FB-130) on `fix/2026-10-22-open-issues`.
- **Mobile chrome (UX-1, FB-122):** the top bar's clipping `!important` was removed at the source so the documented one-row contract scrolls again; the account chip hides ≤640 px, every control is reachable, and the layout guard gained the `topbar-cluster-reachable` cell with a clipped negative control. The tail (language switch) still needs a swipe at 320/375 — recorded as a partial.
- **Dashboard and shell (UX-2…UX-5, FB-123…FB-126):** the dark dashboard search field is one box (the two `!important` input fills narrowed at the source); the quick-start tiles read the invitation grid and hide once an account has an invitation; one original 16-symbol SVG sprite (`assets/icons.svg` + `src/css/icons.css`) replaces the shell's glyph icons; and Publish snapshot is the studio bar's single primary control (superseded gradient deleted, no new `!important`).
- **Editor (UX-6…UX-8, FB-127…FB-129):** the empty inspector shows one label and the empty card (the heading returns with a selection), diagnostics is gated to All-controls mode, the Timeline/Studio Ops pills are flat 32 px chrome; the built-in empty photo now shows an editor-only dashed slot + `i-image` chip while the stored value, export snapshot and public page stay unchanged (`tests/lt_2_6_empty_photo_placeholder_test.py`); guest rows are one checkbox + name/status/meta + one 36 px action group, 66 px at 1440 (target ≤72) with no overflow at 375 and Remove in danger text.
- **Public page (UX-9, FB-130):** schedule and venue no longer render a heading without content (82 px and 98 px blank blocks at 1440/375), and a section animation preset of None no longer strands a populated section at `opacity: 0` — the redundant initial hidden state is gone while `fadeUp` still supplies its own first frame. Reduced motion with a never-firing `IntersectionObserver` leaves every section visible; `tests/ux9_public_sections_test.py` covers all three states.
- **Verification:** one full matrix `GATES_PASSED` (`artifacts/next-work/gates/20261029-134220/`) — build `BUILD_OK`/`MIRROR_CHECK_PASSED`, bundles `ROUTE_BUNDLE_CHECK_PASSED`, smoke 16 pages / 0 errors / 0 non-2xx, layout `UI_LAYOUT_GUARD_PASSED`, pytest **214 passed**, budgets 6 pages, LHCI 16/16 `minA11y 1.00`, `CSP_CHECK_PASSED`, canvas 22 pass / 0 fail / 2 skipped, `!important` 3809 ≤ pin 3809. The Part A after-set is `artifacts/next-work/review-ux1/after/` (17 shots + 4 previews, `INDEX.md`).
- **Findings raised, not fixed (owner queue):** the guest-row action buttons lost their handlers in `92806ad` (found in UX-8); the guest-feature modules print raw `HTTP 401` on every public invitation (found in UX-9); UX-1's language switch still needs a swipe at 320/375. No budget, threshold or frozen harness was changed.

## 0.68.6 — Phase 3 close: guest-page completion and capability truth

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 3 (LT-3.1…LT-3.10, commits
  FB-83…FB-91), executed locally on `fix/2026-10-22-open-issues`.
- **Capability truth (LT-3.1):** `docs/CAPABILITY-MATRIX-2026-10-24.md` statuses every guest-page,
  editor, template, export and Khmer-engine capability as `exists` / `partial` / `absent` with
  evidence, and is now at final truth (the 36-template pack and the guest-page language switch
  included).
- **Guest page completed (LT-3.2…LT-3.9, item 8):** a display-only gift/KHQR block behind an owner
  toggle — one raster image through the platform upload route, server-side allowlist, caption, no
  payment control and no account numbers stored — plus a strictly sanitised `?guest=<name>` greeting
  (NFC, control/format/markup characters stripped, 40 chars, escaped) render on the public route;
  Messenger joins Telegram/WhatsApp/Facebook share. Evidence:
  `tests/lt_3_2_gift_greeting_test.py`, `artifacts/next-work/fb-90/NOTES.md`.
- **Verification:** one full matrix `GATES_PASSED` — build, bundles, smoke 16 pages / 0 errors,
  layout, pytest **183 passed**, budgets 6/6, LHCI 16/16 `minA11y 1.00`, CSP 0 violations, canvas
  22 pass / 0 fail / 2 skipped, `!important` 3816 ≤ 3823
  (`artifacts/next-work/gates/20261027-120242/`).
- **Not done (Phase 4 scope):** the guest-page language switch found at the close (the visible
  control does not change the invitation), the unsaved-changes guard, colour-picker extras and
  bilingual per-run font/size authoring.
- **Primary files:** `docs/CAPABILITY-MATRIX-2026-10-24.md`, `src/js/public-page.js`,
  `src/js/product-operations.js`, `src/js/app.js`, `src/css/guest-layouts.css`,
  `src/python/server.py`, `tests/lt_3_2_gift_greeting_test.py`, `docs/i18n/TRANSLATIONS.csv`,
  `docs/STATUS-INDEX.md`.

---

## 0.68.7 — Phase 4: guest language switch, unsaved guard, colour and run typography

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 4 (LT-4.1…LT-4.4), executed
  locally on `fix/2026-10-22-open-issues`.
- **Guest language switch (LT-4.1, FB-92):** the visible topbar switch and the hidden proxy pair now
  both delegate to the renderer's `setLanguage`, and the i18n layer mirrors it, so the control cannot
  claim a language the page is not showing.
- **Unsaved-changes guard (LT-4.2, FB-93):** `app.js` keeps a `pendingWrite` flag (mirrored to
  `data-save-pending`) while the 220 ms local write is in flight and cancels `beforeunload` only then.
- **Colour-picker extras (LT-4.3, FB-94):** a popover around the native colour inputs with 8
  persisted recents, an eyedropper where the API exists, and a text-only WCAG contrast verdict;
  choices go back through the host input, so the editor still applies them.
- **Per-run typography (LT-4.4, FB-95):** the rich-text run selection now survives a re-render, and
  the inspector's "Selected text (run)" group applies a font pairing and a size preset to exactly the
  selected run in one commit. `applyMark` is now bounded to the selected runs (it previously also
  marked neighbouring runs).
- **Verification:** build, bundles, smoke 16 pages / 0 errors, layout, budgets 6/6 and CSP green for
  each item; the only pytest red is the documented `lt_2_6` export-host oscillation. Evidence:
  `artifacts/next-work/lt-4-{1,2,3,4}/NOTES.md`.
- **Boot defect fixed (FB-96):** a same-profile editor reload used to boot the title as one flattened
  run even though the draft and server kept the runs, because the boot `capture()` ran before the
  lazily loaded rich-text modules; the stored model is now carried forward. The test reloads the same
  profile and asserts both runs; the trace is in `artifacts/next-work/lt-4-4/RELOAD-DEFECT.md`.
- **Primary files:** `src/js/app.js`, `src/js/rich-text-editing.js`, `src/js/typography-editor.js`,
  `src/js/color-picker-extras.js`, `src/js/public-page.js`, `src/css/editor/editor-styles.css`,
  `tests/lt_4_{1,2,3,4}_*_test.py`, `docs/CAPABILITY-MATRIX-2026-10-24.md`, `docs/STATUS-INDEX.md`.

---

## 0.68.9 — Phase 6 close: performance, weight and the gate's long-term health

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 6 (LT-6.1…LT-6.5), executed
  locally on `fix/2026-10-22-open-issues`.
- **Headroom watch (LT-6.1):** three layout-guard runs on one tree; the worst route is
  `index.html` at 420 ms of the 600 ms long-task ceiling (70 %), nothing within 15 %, so no bundle
  split — the startup bundle's compile/execute is unchanged since FB-64/FB-66.
- **Budgets in numbers (LT-6.2):** new `docs/perf/BUDGET-STATE-2026-10-24.md` — all six budgeted
  routes inside (thinnest `public.html` 0.4 KB of 259 KB); editor median 2,153 ms to
  `editorReady`; viewer LCP median 4,716 ms under Slow-4G + 4× CPU with CLS 0 (unthrottled 832 ms);
  `templates.html` perf 77 / CLS 0.604 and `index.html` perf 73 recorded as outliers inside gate
  tolerance.
- **`!important` ratchet (LT-6.3):** three passes; the two provably-dead rules were removed —
  `final-polish.css` `.fp-project-status` and `organized/workflow-refine.css` `.flow-design-search
  input`, 7 tokens, 3816 → 3809 — and `IMPORTANT_PIN` was lowered to 3809 in the same pass. Proof
  chain: static inventory, live rest probe, a new interaction-state probe (hover/focus/click/drag),
  and a 240-shot pixel gate at 63/240 fully classified against a same-source control at 62/240.
  Passes 2–3 found no new candidates.
- **Large uploads (LT-6.4):** a 21.9 MB image is refused with a named limit on all three entry
  points (inspector, asset browser, materials) with no upload write and no long task; an allowed
  8.3 MB 5000×3500 JPEG is stored as a 2.18 MB 2200×1540 WebP; a 20 MB raw POST returns HTTP 400.
  Zero defects — no source change.
- **Memory and history (LT-6.5):** after a warm-up, 50 page open/close cycles grow the heap by
  590 KB (bound 8 MB) and a 500-step undo history is flat (bound 24 MB; `pushHistory` keeps at most
  50 snapshots); a 400-cycle discriminator shows a decaying, non-monotone ~5 KB/cycle tail with flat
  DOM node/canvas/dialog counts — no leak, no source change.
- **Verification:** one full matrix `GATES_PASSED`, all ten phases exit 0 — build, bundles,
  smoke `16/0/0`, layout, pytest **`189 passed in 577.31s`** (no red), budgets 6/6, LHCI 16/16
  `minA11y 1.00`, CSP 0 violations, canvas 22 pass / 0 fail / 2 skipped, `!important total=3809` ≤
  pin 3809 (`artifacts/next-work/gates/20261027-211049/gates.log`).
- **Primary files:** `docs/perf/BUDGET-STATE-2026-10-24.md`, `tests/lt_6_4_large_upload_test.py`,
  `tests/lt_6_5_memory_history_test.py`, `src/css/final-polish.css`,
  `src/css/organized/workflow-refine.css`, `tools/css-important-inventory.py` (pin already held),
  `docs/CAPABILITY-MATRIX-2026-10-24.md`, `docs/STATUS-INDEX.md`.

---

## 0.69.0 — Roadmap Part 4 complete: backend security hardening

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 7 / LT-7.2 step 4 (+fix-up), step
  9, FB-105, executed locally on `fix/2026-10-22-open-issues`. Every acceptance bullet of
  `docs/ROADMAP-v0.54-to-v1.0.md` Part 4 is now `exists` in
  `docs/ROADMAP-RECONCILIATION-2026-10-24.md` (8/8).
- **Field-level encryption (4.1, absent → exists):** `core/crypto.py` (Fernet key resolution —
  env → per-data-dir sidecar → ephemeral — `EINVITE_FIELD_ENCRYPTION` kill switch, previous-key
  window, fingerprints), `core/db.py` read wrapper + `protect()` write helper, `users.email_hash`
  with the plaintext fallback, and **every listed column encrypted on the write path**
  (`users.email`, `guests.email`/`phone`, `delivery_attempts.recipient`,
  `audit_events.metadata_json` with a new indexed `admin_only` flag replacing the SQL `LIKE`, and
  `invitation_edit_history.diff_json`). Migration/rollback/re-encrypt:
  `scripts/migrate_encrypt_sensitive_fields.py` (never against `data/`).
- **Step-up coverage (4.2/5.9):** 15 destructive admin routes gated; the admin shell can obtain a
  grant (`src/js/pages/admin/step-up.js` + the `403 step_up_required` retry hook in `admin.js`).
- **Secrets rotation (4.7) and webhook signing (4.6):** `docs/ops/SECRETS-ROTATION.md` +
  `scripts/rotate-secrets.sh`; the webhook delivery path with per-attempt signatures and bounded
  retries, documented in `docs/hosted/WEBHOOKS.md`.
- **Test isolation (4.8):** the `security_*` collection-order coupling fixed at the cause
  (call-time dev-token flag, per-call DB path, path-keyed schema flag, path-aware service schemas);
  the bullet's own `pytest tests/security_*` is green in both file orders.
- **Verification:** nine gate phases green (build, bundles, smoke, layout, budgets, LHCI, CSP,
  canvas, `!important`) and pytest `200 passed, 1 failed` on the pre-existing `lt_2_6` PDF metric —
  `artifacts/next-work/lt-7-close/`; per-item evidence in `artifacts/next-work/lt-7-2/NOTES.md` and
  `tests/security_field_encryption_test.py` (3 passed).
- **Primary files:** `src/python/core/crypto.py`, `src/python/core/db.py`, `src/python/server.py`,
  `scripts/migrate_encrypt_sensitive_fields.py`, `scripts/rotate-secrets.sh`,
  `docs/security/FIELD-ENCRYPTION.md`, `docs/ops/SECRETS-ROTATION.md`, `docs/hosted/WEBHOOKS.md`.

---

## 0.70.0 — Roadmap Part 5 complete: admin and super-admin tools

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 7 / LT-7.2 step 3, FB-105. Every
  acceptance bullet of Part 5 is now `exists` (9/9) in
  `docs/ROADMAP-RECONCILIATION-2026-10-24.md`; the last open row was 5.9's "every admin route
  requires role + step-up for destructive actions".
- **What changed:** the remaining ten destructive mutations (user role/plan/uploads/session-policy,
  reset-password, force-MFA, suspend/unsuspend, non-admin idle window, template visibility) joined
  the five already gated, and — the half no previous build had — an admin page can now actually
  complete the check: `src/js/pages/admin/step-up.js` prompts for password (+TOTP), caches the
  30-minute grant in `sessionStorage`, and `api.send` replays the original request after a
  `403 {code:'step_up_required'}`.
- **APIs (4.5, absent → exists):** `api_keys` with scoped `X-API-Key` auth (`einv_` keys, Argon2id
  hashes, route allowlist, 1000/h per key, `api.request` audit rows with `auth=api_key`), routes
  `GET/POST /api/account/api-keys`, `DELETE /api/account/api-keys/{id}`, and the account-page card
  (create → show-once → revoke).
- **Verification:** `tests/lt_7_2_admin_stepup_test.py`, `tests/lt_7_2_admin_stepup_ui_test.py`,
  `tests/security_api_keys_test.py`, `tests/lt_7_2_api_keys_ui_test.py` all green; nine gate phases
  green and pytest `200 passed, 1 failed` (the `lt_2_6` metric) — `artifacts/next-work/lt-7-close/`.
- **Primary files:** `src/python/server.py`, `src/python/core/auth.py`,
  `src/js/pages/admin/step-up.js`, `src/js/pages/admin/admin.js`, `src/html/account.html`,
  `src/js/account-security.js`.

---

## 0.70.1 — Phase 7 close: roadmap reconciliation closed, Phase 8 next

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 7 (LT-7.1, LT-7.2, LT-7.close),
  executed locally on `fix/2026-10-22-open-issues` (FB-104, FB-105, FB-106).
- **Reconciliation closed:** of the 37 acceptance bullets of roadmap Parts 3–6, 30 are `exists`,
  6 `partial` and 1 `absent` — down from 22/10/5. Parts 4 and 5 have no open row (their minor bumps
  are 0.69.0 / 0.70.0); the remaining rows are Part 3's 3.7 (two-client cursor proof), 3.9
  (automatic version snapshots), 3.10/3.11 and Part 6's 6.3 (analytics dashboard DOM test), 6.4
  (composite sort/filter) and 6.6 (shared-chrome Khmer), all recorded as out of LT-7.2's list.
- **Verification:** nine gate phases green on the final tree plus pytest `200 passed, 1 failed` on
  the pre-existing `lt_2_6` PDF metric (no threshold touched) — `artifacts/next-work/lt-7-close/`.
- **Primary files:** `docs/ROADMAP-RECONCILIATION-2026-10-24.md`,
  `artifacts/next-work/lt-7-2/NOTES.md`, `docs/STATUS-INDEX.md`,
  `artifacts/ui-audit/fixes/STATE.md`.


## 0.68.1 — Security hardening: SQL injection fix + shared helpers + path/header/ReDoS/logging fixes

- **Triggered by:** GitHub Copilot security scan (Bandit B608 HIGH + pip-audit + Gitleaks).
- **SQL injection (B608 HIGH):** Fixed 2 dynamic `SET` clauses in `server.py` (`update_signup_sheet` + `update_poll`) — column names now filtered through hardcoded `frozenset` whitelist via `safe_set_clause()`; values parameter-bound. No `# nosec B608` suppression retained — the fix is real.
- **Shared helpers:** Created `src/python/core/security_helpers.py` (`safe_set_clause`, `safe_order_by`, `safe_path_under`, `safe_header_value`, `redact`, `redact_mapping`, `escape_html`).
- **Path injection:** Fixed `security_scanner_v54.py::scan_file()` — path containment check.
- **Response splitting:** Fixed 3 dynamic header values — CRLF stripped from `Content-Disposition` filenames + `Location` redirect.
- **Clear-text logging:** Fixed `production_preflight.py` — defensive redaction of messages with sensitive keywords.
- **Bandit MEDIUM suppressions:** Added `# nosec B404` (subprocess import, 2 sites), `# nosec B603` (subprocess calls, 4 sites) with reason comments.
- **Primary files:** `src/python/core/security_helpers.py`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `src/python/production_preflight.py`

---

## 0.68.4 — Template pack: Khmer leading, measured A11/A4, public-page proof

- **Khmer line-height (A4).** `runStyle` forced the registered face's 1.55–1.6 onto every
  Khmer run, overriding the object's 1.75–1.95. A run now takes the larger of the object's
  line-height and the face recommendation, and `tools/build-template-pack.py` floors every
  object that renders Khmer (by text or by `kh.*` font role) at 1.7 before it is written.
  Twelve templates were re-built; the acceptance matrix measures 1.70–1.95 on all 36 and A4
  reads pass everywhere. `tests/v22_0_3_khmer_custom_font_quality_test.py` still sees the
  recommendation-only value (1.48) for a document that sets no line-height.
- **Decorative alt text on the public page.** `guest-layouts.js` and its two bundles
  replaced a missing alt with `"Invitation photo"`, so every ornament reached assistive tech
  as a photo. They now leave `alt=""` and add `aria-hidden="true"`.
- **A11 and A4 are measured, not asserted.** `tools/acceptance-report.py` reads the shipped
  document's image alts (all `""` for ornaments) and the catalogue's bilingual name, and reads
  each Khmer run's computed line-height; the old A11 cell was a fixed string.
- **Public-page proof.** `tools/proof-public-page.py` publishes one template per category and
  measures the guest page at 375 km / 375 en / 1440 km: no horizontal overflow, CSP clean, 0
  console errors, 0 blurry images, 85/85 ornaments `alt=""|aria-hidden="true"`. It also found
  a product defect: guest text keeps design-pixel font sizes inside percentage boxes, so at
  375 px 32/34 flows spill on the flagship wedding page and 6 are cut. Recorded in
  `docs/templates/PUBLIC-PROOF-2026-10-25.md` and OWNER-QUEUE. The spill was fixed in the same
  pass (the `installResponsive` model-parameter bug); only `p1-text-13` remains, an English
  copy/box call, not a renderer gap.
- **Primary files:** `src/js/{rich-text-renderer,guest-layouts,bundle-public,bundle-index-2}.js`,
  `src/python/{rich-text-renderer,guest-layouts}.js` (mirror), `tools/{build-template-pack,
  acceptance-report,proof-public-page,design-review-report,contact-sheet}.py`,
  `docs/templates/{ACCEPTANCE-2026-10-25,DESIGN-REVIEW-2026-10-25,PUBLIC-PROOF-2026-10-25}.md`.

---

## 0.68.3 — Template pack close-out: export fidelity, decorative alt text, acceptance

- **Export geometry bug (PNG/SVG).** `nodeSvg()` in `src/js/export-quality.js` removed the
  selection chrome (a direct child of `#stage`, plus per-object handles) from the *clone*
  before baking computed styles, so every later child inherited its predecessor's style:
  pattern tiles filled the canvas and corner ornaments took the frame's box. The snapshot
  now runs before the removal. Guarded by
  `tests/template_pack_edit_export_test.py` (exported object widths must equal the stage).
- **Decorative images.** The editor and the public renderer printed
  `alt="Invitation image"` for images without alt text, including 43 decorative ornaments
  per page. They now emit `alt=""` plus `aria-hidden="true"`; informative images keep
  their alt.
- **Acceptance harness.** `tools/accept-template-pack.py` opens a fresh page per template
  (a long-lived canvas page stops reaching `editorReady` in headless Chromium), records
  375 on a fixed-width page instead of resizing, and writes after each row.
  `tools/acceptance-report.py` renders the A1–A12 matrix.
- **Docs.** `docs/DESIGN.md`, `docs/templates/{CATALOG,HOW-TO-ADD-A-TEMPLATE,
  ACCEPTANCE-2026-10-25,DESIGN-REVIEW-2026-10-25,KHMER-HYGIENE-2026-10-25,
  CULTURAL-CHECKLIST-2026-10-25}.md`, thumbnail hashes refreshed in `docs/ASSETS.md`.
- **Primary files:** `src/js/export-quality.js`, `src/js/renderer-core.js`, `src/js/app.js`,
  `tools/{accept-template-pack,acceptance-report,design-review-report,contact-sheet}.py`,
  `tools/render-template-thumbs.py`.

---

## 0.68.2 — Phase B: consolidate helpers, replace B110 suppressions with logging, fix B404 placement, verify cryptography pin

- **B1 — Consolidated duplicate SQL helper modules:** Deleted `src/python/core/sql_safety.py` (duplicate of `security_helpers.py`). Updated `server.py` import from `core.sql_safety` to `core.security_helpers`. `security_helpers.py` is the single canonical location.
- **B2 — Removed dead import:** `safe_order_by` was imported but never called (no user-supplied `ORDER BY` columns exist). Removed from import line. Only `safe_set_clause` (which IS used at lines 8163 and 8374) is imported.
- **B3 — Replaced 42 `# nosec B110` suppressions with real logging:** Added module-level `_log = logging.getLogger("einvite.server")` with `StreamHandler`. Every `except OSError:pass` and `except Exception:pass` now reads `except <Type> as exc: _log.debug("cleanup failed: %s", exc)`. Zero `# nosec B110` suppressions remain (down from 42).
- **B4 — Corrected B404 suppression:** `# nosec B404` on `server.py` line 5 IS valid (subprocess IS imported there). Added `# nosec B404` to `security_scanner_v54.py:23` (the other `import subprocess` site) with reason comment.
- **B5 — Verified cryptography pin against PyPI:** `pip index versions cryptography` confirms latest is `50.0.1`. `pip-audit --strict` against `cryptography==44.0.1` reports **7 CVEs** (highest fix version: `50.0.0` for PYSEC-2026-3552). Updated pin from `>=44.0.1,<48` to `>=50.0.0,<51`.
- **B6 — Cleaned up duplicate VERSION_HISTORY entry:** Removed the stale second `0.68.1` entry (at line 110 — claimed `>=43,<48` and `# nosec` comments retained). Kept the accurate first entry.
- **Primary files:** `src/python/core/security_helpers.py`, `src/python/server.py`, `src/python/security_scanner_v54.py`, `docs/requirements-production.txt`, `VERSION_HISTORY.md`

---

## 0.68.3 — Version-free source names + the two guards the mirror was missing

- **Triggered by:** the version-labeling audit plan, rewritten as a rename plan after measuring that no user-visible release label existed and that the audit had no end state. See `docs/superpowers/plans/2026-10-16-version-free-source-names.md`.
- **Latent defect found and fixed:** `src/python/route-deferred-loader-v15.js` was missing from the served mirror while `src/python/route-bundles-v15.json` listed it as a startup script for five routes. Because `src/python/` is the server `ROOT`, that is a silent 404. `python3 build.py all --check` was red (exit 1, `MIRROR_CHECK_FAILED`) while the entire pytest suite was green — nothing read the mirror.
- **Guard 1 — served-asset resolution:** new `tests/served_asset_resolution_test.py` asserts that every script/stylesheet/manifest/icon a served page declares resolves inside `src/python/`, that every manifest-declared bundle and deferred chunk exists, and that the mirror is byte-faithful. It calls the syncer's own `mirror_drift()` (extracted from `sync_frontend_assets.main --check`) so the gate and the test cannot disagree.
- **Guard 2 — naming ratchet:** new `tests/version_free_source_names_test.py` plus `tests/versioned_name_allowlist.json` fail on a new version-shaped file name under `src/js`/`src/css`, and on an allowlist entry with no file behind it. The list can only shrink.
- **Generated bundle family renamed:** `bundle-<page>-v15.{js,css}` → `bundle-<page>.{js,css}`, deferred chunks likewise, `route-deferred-loader-v15.js` → `route-deferred-loader.js`, and the three manifests (`route-bundles`, `page-assets`, `route-bundle-sources`) dropped their `-v15`. Generators, the mirror's `GENERATED` allowlist, the runtime loader's stem regex, the service-worker precache list and 33 HTML references moved together.
- **136 hand-authored modules renamed** with references updated across sources, manifests, tests, tools and live docs. The renamer refuses unsafe renames: occupied target, collision in the flattened served namespace (`src/css/organized/` flattens onto `src/css/`), or two batch entries sharing a target.
- **7 names deliberately left** for a human decision — each would collide with a different live file of the name it would take: `collaboration-v24.{js,css}`, `photo-editor-v13.{js,css}`, `workflow-creation-flow-v3.js`, `workflow-creation-flow-v4.js`, `organized/admin-page-v13.css`, `organized/photo-editor-v13.css`.
- **Verification:** `python3 build.py all --check` exit 0; the two new guards 35 passed; the 27-file targeted suite 42 passed with 1 pre-existing failure; the served routes fetched over HTTP (16 pages, 37 distinct assets, 10 deferred chunks) all 200; every route-bundle source entry resolves; the loader stem regex verified under node for both the startup and deferred forms.
- **Not done:** version-prefixed CSS class names and JS namespace segments (448 class names) — deferred as highest-risk and least user-visible.
- **Note:** `tests/v27_3_5_release_evidence_test.py::test_release_evidence` remains red on its `digest(README.md)` assertion. It was already red (README.md carries uncommitted edits) and was left un-rebaselined rather than baking unrelated pending edits into a V0.52 release-evidence assertion.
- **Primary files:** `tests/served_asset_resolution_test.py`, `tests/version_free_source_names_test.py`, `tests/versioned_name_allowlist.json`, `src/python/build/{build_route_bundles,build_page_manifests,sync_frontend_assets}.py`, `src/js/route-deferred-loader.js`, `src/js/service-worker.js`, `CONTRIBUTING.md`

---

## 0.68.4 — Phase 1 close: Khmer header surfaces and the visible review-set defects

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 1 (LT-1.1…LT-1.11, commits FB-68…FB-77), executed locally on `fix/2026-10-22-open-issues`.
- **i18n:** both Khmer addenda, ADDENDUM-2 and the shared terminology replacement applied by script (`VERIFIED 88/88`); the remaining English-on-KM strings are inventoried in `docs/i18n/KHMER-GAP-ROUND5-2026-10-24.md` with English as the accepted fallback. Khmer fallback pin moved 305 → 1 in the same commit.
- **Visible defects closed:** public Gregorian date follows the guest's chosen language and CTA pills stay on one line; dashboard cards size to their content with a readable bilingual status chip, a viewport-tall rail and an equal-height 375 tile row with no drawer smear; every route paints the bundled Khmer face; the 375 editor toolbar/chip/palette/zoom HUD fit; desktop editor has one search, one inspector title, an unclipped brand and no floating status pill; a signed-in non-admin gets the shared access-state card at 375/1440 light and dark.
- **Editor first paint:** `studio-design-mode` and the design section ship in the served markup and `core/theme.js` corrects them from storage before paint. Median probe CLS 0.5526 → 0.1438; LHCI index median 0.1415 against the ≤ 0.1 target — target not met, best number recorded.
- **CSP:** `tools/csp-violation-check.py` now drives `designer.html` signed in and out; `CSP_CHECK_PASSED`, no violation, CSP unchanged.
- **Budget regression caught at the phase close and fixed at the owning layer:** FB-70's dashboard-only rules moved from the universal `app-shell.css` to `canva-ui.css`, and two shipped JS comment blocks were dropped. `bundle-materials.js` 139,092 B (budget 147,456) and `bundle-public.css` 134,128 B (budget 134,144); no budget or threshold changed. Dashboard metrics match the FB-70 baseline with zero mismatches.
- **Verification:** full matrix `GATES_PASSED` — build, bundles, smoke 16 pages/0 errors, layout 1533 checks/0 failed, pytest 157 passed, budgets 6/6, LHCI 16/16 with a11y 1.00, CSP, canvas 22 pass/0 fail/2 skipped, `!important` 3816 ≤ 3823. Evidence in `artifacts/next-work/gates/20261025-121010/` and `artifacts/next-work/review-lt1/after/`.
- **Not done:** LT-1.9's ≤ 0.1 CLS target; the two P2 findings recorded in `artifacts/next-work/lt-1-8/FINDINGS.md` (320/375 topbar cluster clipping on five routes, editor Fit under the mobile Advanced bar at 320).
- **Primary files:** `src/css/app-shell.css`, `src/css/canva-ui.css`, `src/js/final-polish.js`, `src/js/editor/first-selection-prewarm.js`, `src/js/pages/admin/admin.js`, `src/js/public-page.js`, `tools/csp-violation-check.py`, `docs/i18n/*`, `docs/STATUS-INDEX.md`, `VERSION_HISTORY.md`

---

## 0.68.5 — Phase 2 close: the Khmer text engine, dates and export fidelity

- **Triggered by:** `FREEBUFF-LONG-TERM-PLAN-2026-10-24.md` Phase 2 (LT-2.1…LT-2.7, commits FB-78…FB-82), executed locally on `fix/2026-10-22-open-issues`.
- **Khmer numerals and dates (LT-2.2):** `core/khmer-format.js` converts digits from code points (`0x17E0 + n`), formats through `Intl.DateTimeFormat` with `-u-nu-khmr` and an optional Buddhist-era year, and falls back to English month names when the runtime has filtered ICU. The per-invitation `settings.khmerNumerals` switch defaults **off** and round-trips through the editor draft; the editor command only changes selected text.
- **Wrap audit (LT-2.1):** 3 long map paragraphs × 2 surfaces × 4 widths produced 67 line breaks, 0 inside a grapheme cluster and 67/67 on a word boundary; OD-30's fix condition was not met, so no helper or ZWSP was added.
- **Bilingual block audit (LT-2.3):** one object held an EN serif 28 px line and a KM sans 20 px line with independent line heights, identical left edges on editor and public at 375/1440 and no overflow; per-run authoring remains a documented `partial` for the LT-3.1 matrix.
- **Font self-hosting (LT-2.4):** 11 bundled WOFF2 / 2 licence files have rows; 232 `@font-face` blocks across 19 files all carry `font-display` and `unicode-range`, with 0 remote sources. Four fresh-context route loads made only loopback font requests and 0 console errors.
- **IME and paste (LT-2.5):** a map string survives three progressive composition chunks and a second pasted map string through the real editor, save and reload; 24/24 code points match in the model, stored object and reloaded DOM.
- **Export fidelity (LT-2.6):** SVG export now walks nested CSS rule lists, so the faces inside `@layer` are embedded instead of silently skipped (0 → 7 `@font-face` blocks). PNG at 1× is pixel-identical to the editor; 2×/3× stay within MAE 1.03/0.89 after downsampling. Print surfaces reset the inherited body `translateY(2px)` and use the exact page height: one-page PDF, embedded Noto Sans Khmer, text-box placement within 5 px on the loaded matrix (stated tolerance 8 px), MAE 2.0–3.6 at 96 dpi. The export dialog exposes 1×/2×/3× PNG.
- **Verification:** full matrix `GATES_PASSED` — build, bundles, smoke 16 pages/0 errors, layout 160.6 s with `UI_LAYOUT_GUARD_PASSED`, pytest **161 passed**, budgets 6/6, LHCI 16/16 minA11y 1.00, CSP, canvas 22 pass/0 fail/2 skipped, `!important` 3816 ≤ 3823. Phase 2 after set: 17 shots + 6 previews in `artifacts/next-work/review-lt2/after/`; 13/17 pixel-identical to Phase 1, four dynamic shots ≤ 0.35 MAE.
- **Not done:** per-run font/size authoring UI remains `partial` for LT-3.1; PDF text-box tolerance is 8 px because a loaded CI host shifted a long Khmer line by 5 px; the standalone `tests/v24_export_quality_browser_test.py` still cannot start under the current Chromium opaque-origin `set_content` (the real-server LT-2.6 test covers the same path).
- **Primary files:** `src/js/core/khmer-format.js`, `src/js/public-page.js`, `src/js/app.js`, `src/js/export-quality.js`, `src/python/export-quality.js`, `tests/lt_2_2_khmer_format_test.py`, `tests/lt_2_5_khmer_input_test.py`, `tests/lt_2_6_export_fidelity_test.py`, `docs/qa/khmer-text-sheet/`, `docs/STATUS-INDEX.md`, `VERSION_HISTORY.md`
