# eInvite Platform — Roadmap: v0.54 → v1.0

> **Audience:** the AI agent(s) implementing this roadmap.
> **Mode:** Go through this document top to bottom in one continuous effort. There are no sprints, no weeks, no deadlines. Finish a section, commit, move to the next.
> **Before you start:** read `CONTEXT.md`, `docs/ROADMAP.md`, `docs/ROADMAP-V2.md`, and `/home/z/my-project/worklog.md` for full history. Read the existing `VERSION_HISTORY.md` to understand the last version before you reset it.

---

## 0. How to use this document

This roadmap has six parts, executed **in order**:

1. **Part 1 — Version reset & conventions.** Do this first. It changes how you label everything that follows.
2. **Part 2 — Project structure reorganization.** Do this second. It changes where every file lives; doing it before adding features avoids re-doing the reorganization.
3. **Part 3 — Editor UX/UI upgrade.** The largest part. Makes the editor feel like Canva/Figma.
4. **Part 4 — Backend security hardening.** Ongoing security work.
5. **Part 5 — Admin & Super Admin tools.** The control plane.
6. **Part 6 — Creator analytics & insights.** The feedback loop for hosts.

**Ground rules that apply to every part:**

- Every user-facing string must have both an English (`en`) and a Khmer (`km`) variant. The existing CI check `scripts/check-bilingual-consistency.py` must keep passing.
- No new build tools. Vanilla JS, plain CSS, stdlib Python. No webpack, no Vite, no npm dependencies for frontend code. Vendored libraries only (see `vendor/`).
- Every new backend route must have a `rate_limit(...)` call. The CI check `scripts/check-rate-limit-coverage.py` must keep passing.
- Every new feature gets a test in `tests/` that runs against a real HTTP server via `tests/v14_test_utils.app_server`.
- Bump `VERSION_HISTORY.md` per completed task group. Version scheme is defined in Part 1.
- Commit prefix matches the part: `v0.54`, `structure`, `ux`, `sec`, `admin`, `analytics`. Example: `ux: add alignment guides to editor canvas`.
- Never delete working code without a replacement. Refactor incrementally.
- Log every task in `worklog.md` in the existing format (Task ID / Agent / Task / Work Log / Stage Summary).

---

# PART 1 — Version Reset & Conventions

## 1.1 Why reset to 0.54

The current version history reaches V54.34. This is confusing:
- The project is not 54 major versions old.
- The `.34` micro versions accumulated from rushed additions.
- Two-digit `V54` collides visually with the `V52` Y.js tables and the `V53` AI operator.

Reset to **0.54.0** — read as "the pre-1.0 project at its 54th feature milestone." From here, version 0 progresses to 1.0 as the product stabilizes. `1.0.0` is reserved for the first production-certified release (i.e. when Section 5 execution of `ROADMAP-V2.md` is genuinely complete).

## 1.2 Version numbering scheme

Use **semantic versioning** with a documented meaning:

| Bump | When | Example |
|---|---|---|
| **MAJOR** (`0` → `1`) | Only at production certification. Never before. | `0.99.5` → `1.0.0` |
| **MINOR** (`0.54` → `0.55`) | A completed roadmap part. One minor per part. | `0.54.0` → `0.55.0` |
| **PATCH** (`0.54.0` → `0.54.1`) | A completed task within a part. | `0.54.0` → `0.54.1` → `0.54.2` |

The six parts of this roadmap map to:

| Part | Version range |
|---|---|
| 1 — Version reset | `0.54.0` |
| 2 — Structure reorg | `0.55.0` (patch bumps per module moved) |
| 3 — Editor UX/UI | `0.56.0` … `0.60.0` (patch bumps per feature) |
| 4 — Backend security | `0.61.0` … `0.63.0` |
| 5 — Admin tools | `0.64.0` … `0.66.0` |
| 6 — Creator analytics | `0.67.0` … `0.69.0` |

`1.0.0` is the certification release, after all six parts plus the execution items from `ROADMAP-V2.md` §5.

## 1.3 Branch and commit conventions

- **Branch:** `main` is the trunk. Work on short-lived branches named `v0.54-part2-structure`, `v0.55-part3-editor-ux`, etc. Merge to `main` when a part's tests pass.
- **Commit format:** `<part-slug>: <imperative summary>` on the first line, then a blank line, then a bullet list of what changed and why. Example:

```

ux: add smart alignment guides to canvas

- Implemented AlignmentGuide service in src/js/editor/canvas-guides.js
- Snaps to sibling elements within 6px
- Fires einvite:alignment-snapped event for haptic feedback
- Bilingual labels: "Aligned to center" / "តម្រឹមទៅកណ្តាល"
- Test: tests/editor_alignment_guides_test.py passes

```

## 1.4 VERSION_HISTORY.md rewrite

Rewrite the file from scratch. Structure:

```markdown
# Version History

This project uses semantic versioning. `0.x` is pre-1.0; `1.0.0` is the first
production-certified release.

## 0.69.0 — Creator analytics complete
- <one-line summary>
- Primary files: <paths>

## 0.68.0 — ...
```

Rules:

- Every entry lists **primary file paths** so a reader can find the code.
- Every entry corresponds to a `MINOR` or `PATCH` bump.
- The pre-reset history (V54.x) is preserved in a separate file `docs/LEGACY-VERSION-HISTORY.md`, linked from the top of the new file. Do not delete the old entries — some audit trail references them.

---

# PART 2 — Project Structure Reorganization

## 2.1 Why this matters

The codebase currently has:

- **175 JS files** in `src/js/` — many versioned (`windows-ui-v16.js`, `workspace-experience-v24.js`, `studio-experience-v22.js`, etc.).
- **99 CSS files** split between `src/css/` and `src/css/organized/`.
- **~40 Python modules** in `src/python/` at the top level.
- **~30 docs** now spread across 9 subdirectories of `docs/`.

This makes onboarding hard, makes version bumps confusing, and makes it easy to add a third file that does what two existing ones already do.

**Target:** a small number of well-named folders where a new contributor can guess where a file lives before opening the tree.

## 2.2 Guiding principles

1. **Group by feature, not by version.** A file named `windows-ui-v16.js` should become part of `editor/chrome/` — the version is a footnote, not the filename.
2. **One file per coherent concern.** If `a.js` and `b.js` both define small helpers for the same feature, merge them into one file. Aim for files of 200–800 lines; split if larger.
3. **Flat is bad.** A folder with 175 files is unusable. A folder with 5 subfolders and 10 files each is navigable.
4. **Python mirrors the frontend.** If the frontend has `editor/text/`, the backend that serves it lives in `src/python/routes/editor_text.py` (or similar), not scattered across `server.py`.
5. **Docs live with the code they describe.** Security docs go in `docs/security/`, AI docs in `docs/ai/` — that's already done. Extend the pattern.

## 2.3 Target structure — frontend

```
src/
├── js/
│   ├── core/                       # Framework primitives used everywhere
│   │   ├── events.js               # Custom event bus (einvite:*, dispatch/subscribe)
│   │   ├── state.js                # Application state store with subscribe()
│   │   ├── dom.js                  # DOM helpers (createElement, escapeHtml, qs, qsa)
│   │   ├── http.js                 # fetch wrapper with CSRF, retries, error normalization
│   │   ├── i18n.js                 # Bilingual string resolver (reads documentElement.lang)
│   │   ├── storage.js              # localStorage + IndexedDB wrapper with namespacing
│   │   └── errors.js               # Error boundary + toast integration
│   │
│   ├── editor/                     # The design editor
│   │   ├── canvas/
│   │   │   ├── renderer.js         # Main canvas render loop
│   │   │   ├── guides.js           # Smart alignment guides
│   │   │   ├── selection.js        # Selection model + multi-select
│   │   │   ├── transform.js        # Move/resize/rotate handles
│   │   │   ├── snapping.js         # Grid + element snapping
│   │   │   └── viewport.js         # Zoom, pan, fit-to-screen
│   │   ├── text/
│   │   │   ├── inline-editor.js    # Rich text editing within a text element
│   │   │   ├── typography.js       # Font selection, sizing, line height
│   │   │   ├── effects.js          # Text shadow, outline, gradient fill
│   │   │   └── khmer.js            # Khmer-specific shaping + line-height
│   │   ├── media/
│   │   │   ├── image.js            # Image element (crop, filter, adjust)
│   │   │   ├── crop.js             # Crop tool
│   │   │   ├── filters.js          # Brightness, contrast, saturation, blur
│   │   │   ├── video.js            # Video embed (YouTube, Vimeo, direct)
│   │   │   └── upload.js           # Upload with progress bar
│   │   ├── chrome/                 # The editor shell (toolbar, panels)
│   │   │   ├── toolbar.js          # Top toolbar (undo, redo, zoom, share, export)
│   │   │   ├── sidebar.js          # Left sidebar (elements, uploads, text, pages)
│   │   │   ├── inspector.js        # Right panel (properties of selected element)
│   │   │   ├── pages.js            # Page thumbnail sidebar
│   │   │   ├── layers.js           # Layer panel with drag-reorder
│   │   │   ├── command-palette.js  # Ctrl+K palette
│   │   │   ├── context-menu.js     # Right-click menus
│   │   │   └── shortcuts.js        # Keyboard shortcut registry
│   │   ├── collab/
│   │   │   ├── crdt.js             # Y.js bridge
│   │   │   ├── presence.js         # Live cursors + avatars
│   │   │   ├── undo.js             # Per-user UndoManager
│   │   │   └── comments.js         # Comment threads
│   │   ├── history/
│   │   │   ├── timeline.js         # Version history UI
│   │   │   └── diff.js             # Visual diff between versions
│   │   └── editor.js               # Entry point; wires everything together
│   │
│   ├── pages/                      # Non-editor pages
│   │   ├── public/
│   │   │   ├── invitation.js       # Public invitation page
│   │   │   ├── rsvp.js             # RSVP form + submission
│   │   │   ├── album.js            # Guest photo album
│   │   │   ├── signup-sheets.js    # Guest sign-up sheets
│   │   │   ├── polls.js            # Guest polls
│   │   │   └── gift-registry.js    # Gift registry
│   │   ├── dashboard/
│   │   │   ├── dashboard.js        # Dashboard shell
│   │   │   ├── invitations.js      # Invitation list
│   │   │   ├── host-signup-sheets.js
│   │   │   ├── host-polls.js
│   │   │   ├── host-gift-registry.js
│   │   │   ├── analytics.js        # NEW — creator analytics (Part 6)
│   │   │   └── onboarding.js       # First-run onboarding
│   │   ├── admin/
│   │   │   ├── admin.js            # Admin shell
│   │   │   ├── users.js
│   │   │   ├── system-health.js
│   │   │   ├── audit-log.js
│   │   │   └── feature-flags.js
│   │   ├── auth/
│   │   │   ├── login.js
│   │   │   ├── register.js
│   │   │   ├── mfa.js
│   │   │   └── passkeys.js
│   │   └── checkin/
│   │       └── checkin.js          # QR check-in scanner
│   │
│   ├── components/                 # Reusable UI primitives
│   │   ├── modal.js
│   │   ├── dialog.js
│   │   ├── toast.js
│   │   ├── dropdown.js
│   │   ├── tooltip.js
│   │   ├── tabs.js
│   │   ├── table.js                # Sortable, filterable data table
│   │   ├── chart.js                # Line, bar, donut charts (Canvas 2D)
│   │   ├── date-picker.js
│   │   ├── color-picker.js
│   │   └── file-drop.js
│   │
│   ├── ai/                         # AI agent UI
│   │   ├── agent-panel.js
│   │   ├── tool-call-renderer.js
│   │   └── diff-preview.js
│   │
│   ├── plugins/                    # Plugin runtime (frontend)
│   │   ├── sandbox-host.js
│   │   ├── bridge.js
│   │   └── registry.js
│   │
│   └── vendors/                    # Thin wrappers around vendor/yjs, etc.
│       └── yjs-loader.js
│
├── css/
│   ├── base/                       # Reset, tokens, typography, layout
│   │   ├── reset.css
│   │   ├── tokens.css
│   │   ├── typography.css
│   │   ├── khmer.css               # :lang(km) rules (from WCAG P1-A)
│   │   └── utilities.css           # .sr-only, .hidden, spacing helpers
│   ├── components/                 # One file per component
│   │   ├── button.css
│   │   ├── input.css
│   │   ├── modal.css
│   │   ├── toast.css
│   │   ├── table.css
│   │   ├── chart.css
│   │   └── ...
│   ├── editor/
│   │   ├── canvas.css
│   │   ├── chrome.css
│   │   ├── inspector.css
│   │   └── collab.css
│   ├── pages/
│   │   ├── public.css
│   │   ├── dashboard.css
│   │   ├── admin.css
│   │   └── auth.css
│   └── themes/
│       ├── light.css
│       └── dark.css
│
├── html/                            # Unchanged — 16 pages (rename if you like)
│
└── python/
    ├── core/                        # Framework-level modules
    │   ├── server.py               # HTTP server + request handler (slim)
    │   ├── db.py                   # connect(), migrations runner
    │   ├── auth.py                 # Sessions, passwords, MFA, passkeys
    │   ├── security.py             # CSRF, CSP, rate limit, headers
    │   ├── mail.py                 # SMTP + notification emails
    │   └── storage.py              # ObjectStorage (moved from platform_v32/)
    │
    ├── routes/                      # One file per route group
    │   ├── auth_routes.py
    │   ├── account_routes.py
    │   ├── invitation_routes.py
    │   ├── guest_routes.py         # public RSVP, album, sheets, polls
    │   ├── materials_routes.py
    │   ├── ai_routes.py
    │   ├── collaboration_routes.py
    │   ├── admin_routes.py
    │   ├── analytics_routes.py     # NEW — Part 6
    │   └── billing_routes.py
    │
    ├── features/                    # Domain logic (non-route)
    │   ├── delivery_channels/      # Already exists — keep
    │   ├── analytics/              # NEW — Part 6
    │   │   ├── __init__.py
    │   │   ├── tracker.py          # Event ingestion
    │   │   ├── sessions.py         # Session reconstruction
    │   │   ├── reports.py          # Aggregations
    │   │   └── export.py           # CSV/PDF export
    │   ├── malware_scanner.py      # Moved from security_scanner_v54.py
    │   ├── secrets.py              # Moved from secrets_v54.py
    │   └── plugin_marketplace_ca.py
    │
    ├── ai_agent/                   # Keep as-is; it's well-organized
    ├── platform_v32/               # Keep, but move storage.py to core/
    └── future_platform_v52/        # Keep
```

## 2.4 Target structure — docs

```
docs/
├── README.md                       # Index of all docs
├── ARCHITECTURE.md                 # High-level architecture (already exists)
├── ROADMAP.md                      # V1 roadmap (archive)
├── ROADMAP-V2.md                   # V2 roadmap (archive)
├── ROADMAP-v0.54-to-v1.0.md        # THIS document
├── LEGACY-VERSION-HISTORY.md       # Pre-0.54 version history
├── security/                       # Already exists
├── ai/                             # Already exists
├── ops/                            # Already exists
├── i18n/                           # Already exists
├── a11y/                           # Already exists
├── certification/                  # Already exists
├── plugins/                        # Already exists
├── collab/                         # Already exists
├── hosted/                         # Already exists
└── analytics/                      # NEW — Part 6 design docs
    ├── EVENT-MODEL.md
    ├── PRIVACY.md
    └── REPORTS.md
```

## 2.5 Reorganization procedure

**Do this as a sequence of scripted moves, not manual edits.** Write one Python script per move so the migration is repeatable and reviewable.

### Task 2.5.1 — Inventory and classify

Write `scripts/audit_file_structure.py` that:

- Walks `src/js/`, `src/css/`, `src/python/`.
- For each file, extracts its top-level declarations (`function X`, `const X`, `class X`, `def X`).
- Prints a CSV: `path, size_bytes, lines, top_level_symbols, references_count` (references = how many other files import/reference it).
- Output goes to `docs/STRUCTURE-AUDIT.csv`.

**Why:** you cannot reorganize what you cannot see. Do the audit first, then propose the mapping.

### Task 2.5.2 — Write the mapping manifest

Create `docs/STRUCTURE-MAPPING.md` with a table for every file that moves:

| Current path | New path | Reason |
|---|---|---|
| `src/js/windows-ui-v16.js` | `src/js/editor/chrome/toolbar.js` | Merged with workspace-experience-v24 — same concern (editor chrome) |
| `src/js/workspace-experience-v24.js` | `src/js/editor/chrome/sidebar.js` | Split by concern; toolbar → toolbar.js, sidebar → sidebar.js |
| ... | ... | ... |

Rules for the mapping:

- Any file whose name matches `*-vNN.js` **must be renamed** to a version-free name.
- Any two files with overlapping symbol sets (e.g. both define `installToolbar`) get **merged**.
- Any file over 1,000 lines gets **split** by concern.
- Any Python module over 800 lines gets **split** by route group (see `routes/`).

### Task 2.5.3 — Execute the moves with a script

Write `scripts/migrate_structure.py` that:

- Reads the mapping manifest.
- For each row, performs `git mv` (preserves history) — do not use plain `mv`.
- For merges, concatenates with a separator comment, deduplicates `'use strict'` and IIFE wrappers, then writes the merged file.
- For splits, uses a configurable line-range or symbol-boundary splitter.
- Prints a summary: moved N, merged M, split K, skipped S.

**Idempotency:** running the script twice must not double-apply. Track applied moves in `docs/.structure-migration-state.json`.

### Task 2.5.4 — Update all imports and references

After the moves:

- Grep every `.js` file for the old paths and rewrite.
- Update `docs/route-bundle-sources-v15.json` (the bundle manifest) — every old path must be replaced.
- Update `src/html/*.html` `<script src>` and `<link href>` tags.
- Update `tests/*.py` that reference source files by path.

### Task 2.5.5 — Rebuild bundles and verify

Run in order:

```
python3 src/python/core/db.py --migrate        # if schema moved
python3 src/python/build_route_bundles.py
python3 src/python/build_editor_bundle.py
python3 src/python/build_page_manifests.py
python3 src/python/sync_frontend_assets.py
python3 src/python/build_route_bundles.py --check
```

All four `--check` commands must pass. The final bundle hashes will change because file order changed — that's fine, but the **content must be byte-identical after concatenation**. Verify with `git diff --stat` on the bundle files: only line offsets should change, never semantics.

### Task 2.5.6 — Run the full test suite

```
python3 -m pytest tests/ -x
```

Every test must still pass. Any failure is a reorg bug — fix before proceeding.

### Task 2.5.7 — Commit

One commit for the reorg, following the format in §1.3. The commit message body lists every file moved (or reference `docs/STRUCTURE-MAPPING.md`).

## 2.6 File consolidation rules (concrete)

When you find multiple files that could be one:

**Merge into one file if:**

- They export complementary helpers for the same feature (e.g. `text-align.js` + `text-format.js` → `text/format.js`).
- The combined file stays under ~800 lines.
- They share more than 3 top-level symbols.
- They are always loaded together.

**Keep separate if:**

- One is a UI component and the other is a data model.
- The combined file would exceed ~800 lines.
- They are loaded on different pages (bundling both would waste bandwidth on one page).
- They have distinct lifecycles (one is initialized once, the other is re-initialized per element).

**Split if:**

- A file exceeds ~1,200 lines.
- A file has more than ~15 top-level exports.
- A file serves more than one page role (e.g. both the editor and the dashboard).

**Naming rules:**

- No version numbers in filenames. Ever. `toolbar.js`, not `toolbar-v54.js`.
- Lowercase, hyphen-separated. `command-palette.js`, not `commandPalette.js` or `CommandPalette.js`.
- Singular for the primary export: `toast.js` exports `EInviteToast`.
- Plural for collections: `guides.js` exports alignment guide helpers.

## 2.7 Acceptance criteria for Part 2

- No file under `src/js/` or `src/css/` has a version number in its name.
- No folder under `src/js/` or `src/css/` has more than 15 direct children.
- The bundle check commands all pass.
- The full test suite passes.
- `docs/STRUCTURE-MAPPING.md` exists and documents every move.
- `scripts/migrate_structure.py` exists and is idempotent.
- A new contributor can find any file by guessing its path from its purpose.

---

# PART 3 — Editor UX/UI Upgrade (Canvas-Class)

## 3.0 Goal statement

The editor must feel **as intuitive as Canva** for a non-technical host — someone planning a wedding, not a designer. Success means: a host who has never used a design tool can create a polished invitation in under 10 minutes without reading documentation.

The current editor has the bones (canvas, toolbar, sidebar, properties panel). It lacks the polish layer that makes Canva feel frictionless: smart guides, inline text editing, layer management, comment threads, and a coherent undo model.

**Reference sites to study before starting:** [canva.com/design](https://canva.com/design), figma.com, framer.com. Open all three in a browser. Note how each handles:

- Dragging an element near another (alignment guides appear)
- Double-clicking a text element (inline editing activates)
- Selecting multiple elements (bounding box + group handles)
- Right-clicking the canvas (context menu)

Do not copy their visuals — match their *interaction quality*.

## 3.1 Canvas interaction layer

### Task 3.1.1 — Smart alignment guides

**What:** When dragging an element, show pink/blue guide lines when the element's edge or center aligns with a sibling's edge, center, or the canvas center. Snap within 6px.

**Technologies:** Pointer Events API (`pointerdown`, `pointermove`, `pointerup`). Use `element.setPointerCapture()` to keep events flowing when the pointer leaves the element. Render guides with an absolutely-positioned SVG overlay (crisper lines than `div` borders, easier to animate).

**Files:**

- `src/js/editor/canvas/guides.js` — new
- `src/js/editor/canvas/snapping.js` — new
- `src/css/editor/canvas.css` — add `.alignment-guide` rules

**Implementation notes:**

- Maintain a list of snap targets: `[{type: 'edge-left'|'edge-right'|'center-x'|'edge-top'|'edge-bottom'|'center-y', value: number, source: elementId}]`.
- On `pointermove`, compute the dragged element's edges + center. Compare against every snap target. If within 6px, snap the drag delta to the target and emit `einvite:alignment-snapped` with the matched target.
- Render matched guides as 1px lines spanning the canvas. Fade out 200ms after `pointerup`.
- If multiple targets match, prefer the closest. If two match equally (rare), show both.

**Accessibility:** Guides are visual only. For keyboard users, expose alignment via the inspector panel (`Align left`, `Align center`, `Align right` buttons). Do not rely on guides for keyboard operations.

**Bilingual strings:**

- `align.snapped.center` → EN `"Aligned to center"` / KH `"តម្រឹមទៅកណ្តាល"`
- `align.snapped.left` → EN `"Aligned to left edge"` / KH `"តម្រឹមទៅគែមឆ្វេង"`
- (etc. for right/top/bottom)

**Test:** `tests/editor_alignment_guides_test.py` — instantiate the guide service with two mock elements, simulate a drag, assert the correct guide is emitted.

### Task 3.1.2 — Multi-select and group operations

**What:** Shift-click to add to selection. Drag a marquee to select multiple. Group/ungroup. Move/resize/delete/duplicate as a unit.

**Technologies:** Pointer Events for marquee. `getBoundingClientRect()` on each element for group bounds.

**Files:**

- `src/js/editor/canvas/selection.js` — extend existing
- `src/js/editor/canvas/transform.js` — extend for multi-element transforms

**Implementation notes:**

- Selection is a `Set<elementId>`. Order matters for z-index reordering.
- Group bounds = union of member bounding boxes, plus 8px padding.
- Group transforms apply the same delta to every member; resize scales each member's position and size proportionally.
- Group/ungroup is a persistent operation (stored in the document), not just a selection state.
- Keyboard: `Ctrl+G` group, `Ctrl+Shift+G` ungroup, `Ctrl+A` select all, `Escape` deselect.

**Bilingual strings:** group/ungroup labels for context menu + inspector.

### Task 3.1.3 — Context menu (right-click)

**What:** Right-click on the canvas or an element shows a context menu with relevant actions (cut, copy, paste, duplicate, delete, bring to front, send to back, group, ungroup, lock, hide, add comment).

**Technologies:** `contextmenu` event. Prevent default. Position a `<div role="menu">` at `event.clientX/clientY`. Close on `Escape`, click outside, or blur.

**Files:**

- `src/js/editor/chrome/context-menu.js` — new

**Implementation notes:**

- Menu contents are context-dependent: on empty canvas → "Paste", "Select all", "Zoom to fit". On a single element → element actions. On multiple → group actions.
- Keyboard navigation: arrow keys move focus, `Enter` activates, `Escape` closes.
- Bilingual: every menu item has EN+KH.

### Task 3.1.4 — Snapping to grid and to page margins

**What:** Optional grid overlay. Elements snap to an 8px grid when enabled. Page margins (configurable, default 40px) are snap targets.

**Files:** `src/js/editor/canvas/snapping.js`

**Implementation notes:**

- Grid toggle in the toolbar. State persisted to `localStorage` per user.
- Grid renders as a repeating SVG pattern (not 10,000 divs).
- Margin guides render as dashed lines when dragging near them.

## 3.2 Text editing layer

### Task 3.2.1 — Inline rich text editing

**What:** Double-click a text element → cursor appears inside it. Type with live formatting (bold/italic/underline via Ctrl+B/I/U). Select a range and apply color, font, size.

**Technologies:** `contenteditable="true"` on a hidden text layer positioned over the canvas text element. Use `document.execCommand` for bold/italic/underline (**deprecated but still universally supported** — do not chase the newer `InputEvent` API yet; browser support is uneven). For richer operations (color, font), manipulate the DOM directly via `Range` and `surroundContents`.

**Files:**

- `src/js/editor/text/inline-editor.js` — new
- `src/js/editor/text/typography.js` — new
- `src/css/editor/canvas.css` — `.inline-editor` styles

**Implementation notes:**

- The contenteditable layer is transparent (no background, no border) and positioned exactly over the rendered text. The underlying canvas text is hidden while editing to avoid double rendering.
- On blur (`Escape` or click outside), commit the HTML to the document model, re-render the canvas text, destroy the contenteditable.
- **Sanitize on commit.** Strip every tag except `<b>`, `<i>`, `<u>`, `<strong>`, `<em>`, `<span style="color:...">`, `<br>`. Use the existing `_RichTextSanitizer` from `server.py` — call it client-side via a small mirror, or sanitize server-side on save. **Do not trust client sanitization alone.**
- Khmer: while editing, do not apply `letter-spacing`. Khmer shaping breaks under letter-spacing. The `:lang(km)` CSS rule from `src/css/base/khmer.css` handles this.

### Task 3.2.2 — Text effects (shadow, outline, gradient)

**What:** Text elements can have a drop shadow, an outline stroke, or a gradient fill.

**Technologies:** CSS `text-shadow` for shadow, `-webkit-text-stroke` for outline, `background-clip: text` + `background: linear-gradient(...)` for gradient.

**Files:** `src/js/editor/text/effects.js` — new

**Implementation notes:**

- The inspector panel shows a "Text effects" section when a text element is selected.
- Shadow: color, blur, offset-x, offset-y. Live preview on the canvas.
- Outline: color, width (1–8px). Only the outline, or fill + outline.
- Gradient: two-stop linear gradient, angle in degrees. Provide 8 preset gradients + custom.
- Every effect persists to the document model as a plain object: `{shadow: {color, blur, dx, dy}, outline: {color, width}, gradient: {from, to, angle}}`.

### Task 3.2.3 — Text on a curve

**What:** Text can follow a circular arc. Common in wedding invitations.

**Technologies:** SVG `<textPath>` referenced from a `<path>` with a computed arc.

**Files:** `src/js/editor/text/typography.js` — extend

**Implementation notes:**

- The inspector gets a "Curve" control (a slider from -180° to +180°).
- 0° = straight. Positive = arc upward. Negative = arc downward.
- Radii derived from the text element's width.
- Not all fonts support `<textPath>` correctly (some break complex shaping). If the current font is Khmer, warn the user that curve support is limited.

## 3.3 Media editing layer

### Task 3.3.1 — Image crop and aspect ratio

**What:** Select an image → click crop → crop handles appear → drag to crop. Preset ratios (1:1, 4:3, 16:9, 3:2, free).

**Technologies:** Canvas 2D for crop preview. `Pointer Events` for handles.

**Files:**

- `src/js/editor/media/crop.js` — new

**Implementation notes:**

- The crop operation modifies the image's `cropRect` in the document model — it does NOT re-upload a cropped file.
- The renderer applies the crop rect via `object-fit: cover` + `object-position` (CSS) or via canvas `drawImage(src, sx, sy, sw, sh, dx, dy, dw, dh)`.
- Reset button restores the full image.

### Task 3.3.2 — Image filters and adjustments

**What:** Brightness, contrast, saturation, blur, grayscale. Non-destructive — applied at render time.

**Technologies:** CSS `filter: brightness() contrast() saturate() blur() grayscale()` for live preview. For export, apply the same filters via Canvas 2D `ctx.filter`.

**Files:**

- `src/js/editor/media/filters.js` — new

**Implementation notes:**

- The inspector shows 5 sliders. Each has a default (100% for brightness/contrast/saturation, 0 for blur/grayscale) and a range.
- Filters are stored as `{brightness: 1.2, contrast: 1.1, ...}` on the image element.
- A "Reset all" button clears them.

### Task 3.3.3 — Image masking (shape crops)

**What:** Crop an image into a circle, rounded rectangle, or custom SVG shape.

**Technologies:** CSS `clip-path: circle()` / `inset()` / `path()`. Or `mask-image` for SVG masks.

**Files:**

- `src/js/editor/media/image.js` — extend

**Implementation notes:**

- The inspector offers 6 presets: none, circle, rounded-4, rounded-12, heart, star.
- Custom SVG mask upload is a stretch goal — document but defer.

## 3.4 Chrome and panels

### Task 3.4.1 — Layer panel with drag-reorder

**What:** A right-side panel listing every element in z-order (top first). Drag to reorder. Click to select. Toggle visibility. Lock.

**Technologies:** HTML5 drag-and-drop (`draggable="true"`, `dragstart`, `dragover`, `drop`). Or Pointer Events for finer control.

**Files:**

- `src/js/editor/chrome/layers.js` — new

**Implementation notes:**

- Each row: visibility eye, lock icon, thumbnail (48×48 canvas render), name (auto-generated from type: "Text 1", "Image 2", or user-set label).
- Double-click the name to rename.
- Locked elements cannot be selected by clicking on the canvas (only via the layer panel).
- Hidden elements are skipped in export.
- Multi-select in the layer panel syncs with canvas selection.

### Task 3.4.2 — Pages sidebar with thumbnails

**What:** A vertical strip of page thumbnails. Click to jump. Drag to reorder. Right-click for duplicate/delete/insert.

**Technologies:** Render each page to a small canvas (150×100 or similar) on every change. Cache thumbnails; regenerate only when the page's element tree changes.

**Files:**

- `src/js/editor/chrome/pages.js` — new

**Implementation notes:**

- Thumbnails render at 150px wide. Use `OffscreenCanvas` if available for performance.
- Regenerate debounced at 300ms after any change.
- Page count, add page button, insert page between two pages (hover between thumbnails, click +).

### Task 3.4.3 — Command palette (Ctrl+K)

**What:** Press Ctrl+K (or Cmd+K on macOS) → a searchable list of every action in the editor. Type to filter, Enter to run.

**Technologies:** The existing `command-palette-v23.js` (renamed during Part 2 to `src/js/editor/chrome/command-palette.js`). Extend the command registry.

**Files:**

- `src/js/editor/chrome/command-palette.js` — extend

**Implementation notes:**

- Every toolbar action, every inspector action, every menu item, and every keyboard shortcut must be registered as a command with `{id, label_en, label_km, category, run()}`.
- Display grouped by category: File, Edit, View, Insert, Format, Arrange, Align, Help.
- Recently used commands appear at the top.
- Fuzzy search (not strict substring) — implement a simple fzf-style scorer.

### Task 3.4.4 — Keyboard shortcut registry

**What:** Every shortcut is registered in one place and displayed in a "Keyboard shortcuts" modal (Shift+?).

**Technologies:** A central `Shortcuts` service that listens on `keydown`, matches against a table, and dispatches commands.

**Files:**

- `src/js/editor/chrome/shortcuts.js` — new

**Implementation notes:**

- Shortcuts table: `{key: 'Ctrl+B', command: 'format.bold', when: 'editor-active'}`.
- `when` clauses prevent shortcuts from firing in text inputs (e.g. Ctrl+B in a text input should bold, not toggle the sidebar).
- Display in a searchable modal, grouped by category.

### Task 3.4.5 — Zoom and view controls

**What:** Zoom in/out/fit/fill/100%. Pan with space+drag or middle-click drag.

**Files:** `src/js/editor/canvas/viewport.js` — extend

**Implementation notes:**

- Fit-to-screen computes scale so the whole page fits in the visible area minus a 40px margin.
- Zoom presets: 25%, 50%, 75%, 100%, 150%, 200%, Fit, Fill.
- Zoom to cursor: hold Ctrl+scroll to zoom toward the pointer position.
- Pan with `Space` held + drag, or with middle mouse button drag.

## 3.5 Collaboration polish

### Task 3.5.1 — Live cursors with names

**What:** See other users' cursors with their name label and a colored dot. Cursors move in real time.

**Files:** `src/js/editor/collab/presence.js` — extend existing `collaboration-presence-v52.js`

**Implementation notes:**

- Y.js awareness protocol handles cursor position + identity.
- Cursor color is derived from the user ID (hash → hue) so it's stable across sessions.
- Label shows the user's display name, or "Guest" if anonymous.
- Cursors fade after 5s of no movement.
- **Performance:** throttle cursor updates to 20Hz. Don't send on every mousemove.

### Task 3.5.2 — Comment threads

**What:** Click the comment tool, click on the canvas → a pin appears. Type a comment. Other users see the pin and can reply. Resolve threads.

**Technologies:** Anchor comments to a coordinate + optional elementId. Store in a new `editor_comments` table. Broadcast via Y.js or via the existing polling channel.

**Files:**

- `src/js/editor/collab/comments.js` — new
- `src/python/features/editor_comments.py` — new
- New table `editor_comments` (`id`, `invitation_id`, `page_id`, `element_id`, `x`, `y`, `author_id`, `body`, `parent_id`, `resolved_at`, `created_at`)

**Implementation notes:**

- Pins render on the canvas as numbered circles. Click a pin → thread opens in the right panel.
- Resolved threads are hidden by default; toggle shows them.
- @ mentions trigger a notification email (reuse `send_platform_email`).

### Task 3.5.3 — Version history timeline

**What:** A timeline of every saved version. Click a version → preview it. Restore from any version.

**Technologies:** The existing snapshot-on-publish mechanism extends to auto-snapshots every 30 minutes of active editing (or on significant change). Store in a new `invitation_versions` table.

**Files:**

- `src/js/editor/history/timeline.js` — new
- `src/python/routes/invitation_routes.py` — new routes

**Implementation notes:**

- Auto-snapshot rules: every 30 minutes of editing OR every 100 change events, whichever first. Capped at 50 snapshots per invitation; oldest pruned.
- Manual snapshot button in the toolbar.
- Timeline shows: timestamp, author, a one-line summary of changes (e.g. "3 elements added, 1 deleted").
- "Restore" replaces the current document with the snapshot's content; the current state is auto-snapshotted first so restore is reversible.

## 3.6 Acceptance criteria for Part 3

- A new user can create a multi-page invitation with text, images, and a background color without reading docs.
- Dragging an element near another shows alignment guides within 6px.
- Double-clicking a text element opens inline editing with a cursor.
- The layer panel reorders elements with drag-and-drop.
- Ctrl+K opens a searchable command palette.
- Shift+? shows a keyboard shortcut reference.
- Live cursors from another browser tab are visible and move smoothly.
- Comment threads can be created, replied to, and resolved.
- Version history shows at least 5 snapshots after 30 minutes of editing.
- Every string has an EN+KH variant. The bilingual CI check passes.
- Every new file has a test.

---

# PART 4 — Backend Security Hardening

## 4.0 Goal statement

Move from "hardened" to "defensible in an audit." The four P1 items from the earlier ASVS analysis are done. This part addresses the next tier: encryption at rest, admin access controls, per-tenant isolation, and observability.

## 4.1 Encryption at rest for sensitive fields

**What:** Encrypt at the application layer (not just disk) the following columns:

- `users.email` (or at least a hash for lookup + encrypted original)
- `guests.email`, `guests.phone`
- `passkeys.public_key` (already public, skip)
- `mfa_recovery_codes.code_hash` (already hashed, skip)
- `delivery_attempts.recipient`
- `audit_events.metadata_json` (contains user data in some events)
- `invitation_edit_history.diff_json` (contains document content)

**Technologies:** `cryptography` library's `Fernet` (AES-128-CBC + HMAC-SHA256). Store the key in `EINVITE_FIELD_ENCRYPTION_KEY` (64-byte urlsafe base64). Use `secrets_v54.ensure_secret('EINVITE_FIELD_ENCRYPTION_KEY', 64)` to generate on first boot.

**Files:**

- `src/python/core/crypto.py` — new
- `src/python/core/db.py` — wrap column reads/writes with `encrypt_field()` / `decrypt_field()`

**Implementation notes:**

- **Lookups:** for columns that need to be queried (e.g. find user by email), store a separate `email_hash` column (SHA-256 of the lowercased email) with an index. Encrypt the original for display. Lookup goes through the hash; decryption only happens when the plaintext is needed.
- **Migration:** write `scripts/migrate_encrypt_sensitive_fields.py` that:

1. Reads every row.
2. Encrypts the target columns.
3. Updates the row.
4. Backs up the pre-migration table to `*_plaintext_backup` (kept for 30 days, then dropped).
- **Rollback:** the script supports `--rollback` to decrypt back.

## 4.2 Admin access controls

**What:** Admin routes need stricter controls than user routes.

**Technologies:** IP allowlist, per-user admin session timeout, step-up authentication (re-enter password + MFA for destructive operations).

**Files:**

- `src/python/routes/admin_routes.py` — new
- `src/python/core/auth.py` — extend with `require_admin_with_stepup()`

**Implementation notes:**

- New env var `EINVITE_ADMIN_IP_ALLOWLIST` — comma-separated CIDRs. Empty = no restriction (dev only; production preflight must require non-empty).
- Admin sessions expire after 30 minutes of inactivity (vs 30 days for regular users).
- Destructive admin operations (delete user, delete invitation, modify feature flags, impersonate user) require **step-up**: re-enter password + MFA within the last 5 minutes. Prompt via a modal.
- Every admin action logs an audit event with `admin=true` tag.

## 4.3 Per-tenant isolation verification

**What:** Prove that user A cannot access user B's data even by crafting raw requests.

**Technologies:** Write a test suite that enumerates every route and attempts cross-tenant access with a hostile session.

**Files:** `tests/security_tenant_isolation_test.py`

**Implementation notes:**

- Register two users. Create resources under A (invitations, guests, materials, AI plans).
- With B's session, attempt every GET/PUT/DELETE/POST that targets A's resources by ID.
- Assert every attempt returns 403 or 404 (never 200, never partial data).
- Assert no error message leaks A's data (e.g. "invitation 42 belongs to user 7" — never reveal owner).
- Run this test in CI. Any new route that breaks it fails the build.

## 4.4 Session management UI

**What:** Users can see their active sessions (device, IP, last active, location) and revoke any of them.

**Technologies:** Sessions already exist in the `sessions` table. Add columns: `user_agent`, `ip_address`, `last_active_at`, `created_at`, `revoked_at`.

**Files:**

- `src/python/routes/account_routes.py` — extend
- `src/js/pages/auth/sessions.js` — new

**Routes:**

- `GET /api/account/sessions` — list all active sessions for the current user
- `DELETE /api/account/sessions/{id}` — revoke a specific session
- `DELETE /api/account/sessions` — revoke all except the current one

**Implementation notes:**

- The current session is marked and cannot be revoked from the list (use the "Sign out" button instead).
- User agent is parsed into a friendly string ("Chrome on macOS") — write a small parser, don't add a dependency.
- Optional: GeoIP lookup for location. Only if the operator configures it; otherwise show the IP only.

## 4.5 API key management

**What:** Users (particularly Pro tier) can generate API keys to automate invitation creation and RSVP retrieval.

**Technologies:** Keys are 32-byte random strings, hashed with Argon2id, prefixed with `einv_` for identification. Store in `api_keys` table.

**Files:**

- `src/python/routes/account_routes.py` — extend
- `src/python/core/auth.py` — extend with `require_api_key()`

**Routes:**

- `GET /api/account/api-keys` — list (with last 4 chars of each key)
- `POST /api/account/api-keys` — generate new (returns plaintext once)
- `DELETE /api/account/api-keys/{id}` — revoke

**Implementation notes:**

- Plaintext key is shown **once**, on creation. Copy it or lose it.
- Each key has a `scopes` array (e.g. `["invitations:read", "rsvps:read"]`).
- Every API request logs an audit event with `auth=api_key`.
- Rate limit per key: 1000 requests / hour default.

## 4.6 Webhook signing

**What:** Outbound webhooks (billing, AI events) are signed with HMAC-SHA256 so the receiver can verify origin.

**Technologies:** Add `X-EInvite-Signature: sha256=<hex>` header computed over the request body + timestamp.

**Files:**

- `src/python/core/webhooks.py` — new

**Implementation notes:**

- Secret per webhook destination, stored encrypted.
- Timestamp included to prevent replay; receiver rejects if timestamp > 5 minutes old.
- Documented in `docs/hosted/WEBHOOKS.md`.

## 4.7 Secrets rotation procedure

**What:** Document and provide a script to rotate every long-lived secret without downtime.

**Files:**

- `scripts/rotate-secrets.sh` — new
- `docs/ops/SECRETS-ROTATION.md` — new

**Secrets to rotate:**

- `EINVITE_SECRET_KEY` (session signing)
- `EINVITE_FIELD_ENCRYPTION_KEY` (requires re-encryption of all rows)
- `EINVITE_BILLING_WEBHOOK_SECRET`
- SMTP credentials
- S3/R2 credentials
- Plugin marketplace CA key

**Implementation notes:**

- Session signing supports dual keys during a rotation window: sign with new, accept both old and new for 7 days.
- Field encryption rotation: encrypt new writes with the new key, re-encrypt old rows in a background job, then remove the old key.
- Documented step-by-step with downtime estimates.

## 4.8 Acceptance criteria for Part 4

- Field-level encryption is live for all listed columns.
- Admin routes require step-up for destructive operations.
- The tenant isolation test suite passes and runs in CI.
- Users can view and revoke their sessions.
- API keys can be generated, scoped, and revoked.
- Outbound webhooks are signed.
- Secrets rotation is documented and scripted.
- `python3 -m pytest tests/security_*` all pass.

---

# PART 5 — Admin & Super Admin Tools

## 5.0 Goal statement

Give the operator (the person running the eInvite instance) every tool needed to run the platform without editing the database or restarting the server.

There are two roles:

- **Admin** — read + moderate. Can view users, invitations, and system status. Can suspend users, hide invitations that violate policy, respond to reports.
- **Super Admin** — full control. Can change feature flags, override quotas, impersonate users (with strict audit), perform bulk operations, restore backups.

## 5.1 Admin dashboard overview

**What:** The landing page for admins. At-a-glance metrics + quick actions.

**Layout:** A grid of stat cards (see below) with a "System status" banner at the top.

**Files:**

- `src/html/admin.html` — extend
- `src/js/pages/admin/admin.js` — new
- `src/python/routes/admin_routes.py` — new
- `src/css/pages/admin.css`

**Stat cards:**

- Total users (with 7-day delta)
- Total invitations (with 7-day delta)
- Active sessions now
- Storage used / total quota
- Failed logins (24h)
- Rate limit hits (24h)
- Background jobs queue depth
- DB response time (p95, last 5 min)

**System status banner:**

- Green: all checks pass.
- Yellow: 1 warning (e.g. backup older than 25h, one scanner unavailable).
- Red: 1 critical (DB unreachable, disk >90% full, backup >48h old).

**Implementation notes:**

- Poll `/api/admin/metrics` every 30 seconds. The endpoint aggregates from existing tables + a small in-memory cache. Do NOT compute p95 latency from scratch on every poll — use a rolling buffer.
- Bilingual labels + numerals formatted via `Intl.NumberFormat` (Khmer uses Arabic numerals by default in modern browsers — accept that; the labels are bilingual).

## 5.2 User management

**What:** Browse, search, filter, and act on users.

**Files:** `src/js/pages/admin/users.js`

**Columns:** Email (masked by default; unmask requires step-up), created, last active, plan, invitation count, status (active/suspended).

**Actions per user:**

- View details (opens a drawer with full history: sessions, audit events, invitations)
- Suspend (blocks login; existing sessions invalidated)
- Unsuspend
- Reset password (sends reset email; does NOT show a new password)
- Force MFA re-enrollment
- Impersonate (super admin only, with step-up, and every action during impersonation is audit-logged as `impersonated_by=<admin_id>`)
- Delete (super admin only, requires typing the user's email to confirm, soft-delete by default; hard delete is a separate audited action)

**Implementation notes:**

- Search by email hash (matches the encrypted lookup from Part 4).
- Pagination: 50 per page, cursor-based (not offset — offsets break with concurrent writes).
- All actions confirm via a modal with a bilingual warning.

## 5.3 Invitation management

**What:** Browse, search, moderate invitations.

**Files:** `src/js/pages/admin/invitations.js`

**Columns:** Slug, owner, created, published, view count (last 30d), RSVP count, status (draft/published/archived/flagged).

**Actions:**

- Preview (opens the public page in a new tab)
- Unpublish (removes from public access; owner is notified)
- Flag (marks for review; moves to a "Flagged" filter view)
- Transfer ownership (super admin only)
- Delete (soft + hard variants)

## 5.4 Feature flags

**What:** Toggle features on/off without deploying. Useful for gradual rollouts, testing, and disabling a broken feature in production.

**Technologies:** A `feature_flags` table (`key`, `value`, `description`, `updated_at`, `updated_by`) + an in-memory cache with a 60s TTL.

**Files:**

- `src/python/features/feature_flags.py` — new
- `src/js/pages/admin/feature-flags.js` — new

**Route:** `GET/PUT /api/admin/feature-flags`

**Initial flags to define:**

- `ai_agent_enabled` — master switch for the AI agent
- `canva_bridge_enabled` — Canva import/export
- `plugin_marketplace_enabled` — install plugins
- `collaboration_v52_enabled` — Y.js CRDT (vs V31)
- `analytics_enabled` — creator analytics tracking
- `guest_album_enabled`, `guest_signup_sheets_enabled`, `guest_polls_enabled`, `guest_gift_registry_enabled`
- `multi_channel_delivery_enabled` — SMS/WhatsApp/Telegram
- `maintenance_mode` — returns 503 to non-admins

**Implementation notes:**

- Every flag has a default value defined in code; the DB row overrides it. If the table is empty, defaults apply.
- Toggling a flag writes an audit event.
- The frontend reads the current flag state from `GET /api/feature-flags` (public, unauthenticated — returns only the flags the current user's tier can use).

## 5.5 Audit log explorer

**What:** Search and filter the `audit_events` table from the UI.

**Files:**

- `src/js/pages/admin/audit-log.js` — new

**Filters:** user, action, target type, target id, date range, IP, admin-only.

**Columns:** Timestamp, actor (user or admin), action, target, IP, metadata (expandable).

**Implementation notes:**

- The audit table is immutable (already enforced by DB triggers). The explorer is read-only.
- Export to CSV for offline analysis.
- Retention: `EINVITE_AUDIT_RETENTION_DAYS` (default 730). Add a manual prune action for super admins.

## 5.6 System health & diagnostics

**What:** A dedicated page showing the state of every subsystem.

**Files:**

- `src/js/pages/admin/system-health.js` — new
- `src/python/routes/admin_routes.py` — `GET /api/admin/health-detail`

**Checks displayed:**

- Database: connection, response time, migration version, table row counts
- Object storage: provider, bucket, connectivity test, last successful write
- Malware scanner: which scanner, last scan result, scanned-24h count
- Redis (if configured): connection, memory, key count
- SMTP: last successful send, queue depth (outbox if implemented)
- Backup: last successful, size, age, next scheduled
- Background jobs: queue depth, workers active, failed jobs (last 24h) with retry buttons
- Disk usage: total/used for data directory
- Runtime: Python version, uptime, memory, thread count

**Implementation notes:**

- Each check runs on demand (endpoint queries the subsystem), with a 60s cache to avoid hammering.
- Failed checks show a "how to fix" hint.

## 5.7 Bulk operations

**What:** Super admins can perform bulk actions.

**Actions:**

- Bulk email to a filtered user segment
- Bulk suspend / unsuspend
- Bulk export (users, invitations, audit events)
- Bulk prune (audit events, old versions, orphaned uploads)

**Files:**

- `src/js/pages/admin/bulk-operations.js` — new
- `src/python/routes/admin_routes.py` — extend

**Implementation notes:**

- Every bulk operation runs as a background job (enqueue into the existing `JobQueue`) with a progress bar.
- Bulk email is rate-limited to avoid being flagged as spam: max 100/minute.
- Bulk operations cannot be undone; confirmation modal requires typing `CONFIRM`.

## 5.8 Impersonation (super admin only)

**What:** Log in as another user to reproduce a bug or provide support.

**Files:**

- `src/python/routes/admin_routes.py` — new routes
- `src/js/pages/admin/impersonate.js` — new

**Routes:**

- `POST /api/admin/impersonate/{user_id}` — starts an impersonation session. Requires step-up.
- `POST /api/admin/impersonate/stop` — ends the session.

**Implementation notes:**

- The original admin's session is preserved in a separate cookie (`einvite_admin_origin`) so it can be restored.
- Every action taken while impersonating writes an audit event with `impersonated_by=<admin_id>` and `impersonated_user=<user_id>`.
- A persistent red banner shows "You are impersonating X — click to stop".
- Impersonation sessions expire after 30 minutes automatically.

## 5.9 Report queue

**What:** Users can report abusive invitations or users. Admins see a queue.

**Files:**

- `src/python/features/reports.py` — new
- `src/js/pages/admin/reports.js` — new

**Route:** `POST /api/reports` (user-facing), `GET /api/admin/reports` (admin), `PUT /api/admin/reports/{id}` (resolution).

**Implementation notes:**

- Report reasons: spam, harassment, impersonation, illegal content, other.
- Rate limit: 5 reports/day per user.
- Status: `open`, `investigating`, `resolved_actioned`, `resolved_no_action`, `duplicate`.
- Resolving a report writes an audit event linking the report to the action taken (e.g. suspension, takedown).

## 5.10 Acceptance criteria for Part 5

- Admin dashboard shows live metrics and a system status banner.
- Users can be searched, viewed, suspended, and impersonated (with full audit).
- Invitations can be browsed and moderated.
- Feature flags can be toggled without a restart.
- Audit log is searchable and exportable.
- System health page shows every subsystem with actionable hints.
- Bulk operations run as background jobs with progress.
- Reports queue exists and is actionable.
- Every admin route requires the admin role + step-up for destructive actions.

---

# PART 6 — Creator Analytics & Insights

## 6.0 Goal statement

Give every host a clear, honest picture of how their invitation performed: how many people opened it, how long they spent, what they clicked, and where they dropped off. This is the feedback loop that makes the platform useful as a business tool — not just a design tool.

**Design principles:**

- **Privacy first.** No third-party trackers. No cookies for tracking. All analytics collected first-party, stored on the operator's own infrastructure.
- **Honest numbers.** Never inflate. Unique opens are unique per recipient link (or per hashed IP + User-Agent for public links). Session duration is measured, not estimated.
- **Bilingual reports.** Every metric label has EN+KH.
- **Exportable.** Hosts can download their raw event data as CSV.
- **Retention-limited.** Analytics events auto-prune after `EINVITE_ANALYTICS_RETENTION_DAYS` (default 365).

## 6.1 Event model

**Define these events. Every other feature consumes from this model.**

| Event | When fired | Payload |
|---|---|---|
| `invitation.view` | The public page loads | `invitation_id`, `recipient_id` (nullable), `session_id`, `referrer`, `viewport` |
| `invitation.view.end` | Page unload or 30s of inactivity | `session_id`, `duration_ms`, `scroll_depth_pct`, `max_scroll_pct` |
| `invitation.gallery.open` | Guest opens the photo gallery | `session_id` |
| `invitation.rsvp.open` | Guest opens the RSVP form | `session_id` |
| `invitation.rsvp.submit` | Guest submits RSVP | `session_id`, `status` (yes/no/maybe) |
| `invitation.rsvp.abandon` | Guest opens RSVP but does not submit within session | `session_id`, `last_field_touched` |
| `invitation.link.click` | Guest clicks an external link | `session_id`, `href` (normalized domain only) |
| `invitation.signup.claim` | Guest claims a sign-up slot | `session_id`, `sheet_id` |
| `invitation.poll.vote` | Guest votes in a poll | `session_id`, `poll_id` |
| `invitation.album.upload` | Guest uploads a photo | `session_id`, `size_bytes` |
| `invitation.gift.claim` | Guest claims a gift | `session_id`, `item_id` |

**Implementation notes:**

- Events are batched client-side (max 20 per batch, flush every 10s or on `visibilitychange` to `hidden`).
- Batches are sent to `POST /api/analytics/events` (public, no auth — but rate-limited to 60 batches/minute per IP + session).
- Every event carries `session_id` (a random 128-bit value stored in `sessionStorage`, so it resets per tab close).
- No PII in event payloads. `recipient_id` is an opaque guest id, not an email.

## 6.2 Storage schema

**New tables:**

```
CREATE TABLE analytics_sessions (
  id                TEXT PRIMARY KEY,           -- 128-bit random hex
  invitation_id     INTEGER NOT NULL,
  recipient_id      INTEGER,                    -- nullable, FK to guests
  started_at        INTEGER NOT NULL,           -- unix ms
  ended_at          INTEGER,                    -- null until view.end
  duration_ms       INTEGER,                    -- computed from ended_at - started_at
  max_scroll_pct    INTEGER,
  country_code      TEXT,                       -- from IP, coarse only
  referrer_domain   TEXT,                       -- normalized, null if direct
  device_type       TEXT,                       -- 'mobile' | 'tablet' | 'desktop'
  created_at        INTEGER NOT NULL
);
CREATE INDEX idx_analytics_sessions_invitation ON analytics_sessions(invitation_id, started_at DESC);
CREATE INDEX idx_analytics_sessions_recipient ON analytics_sessions(recipient_id);

CREATE TABLE analytics_events (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id        TEXT NOT NULL,
  invitation_id     INTEGER NOT NULL,
  event_type        TEXT NOT NULL,
  payload_json      TEXT,                       -- small; capped at 1KB
  created_at        INTEGER NOT NULL
);
CREATE INDEX idx_analytics_events_session ON analytics_events(session_id);
CREATE INDEX idx_analytics_events_invitation_type ON analytics_events(invitation_id, event_type, created_at DESC);
```

**PostgreSQL equivalents** use `BIGINT` for timestamps and `TEXT` for IDs.

## 6.3 Ingestion endpoint

**Route:** `POST /api/analytics/events`

**Body:**

```
{
  "session_id": "abc123...",
  "invitation_id": 42,
  "events": [
    {"type": "invitation.view", "ts": 1695000000000, "payload": {"referrer": "https://facebook.com", "viewport": "mobile"}},
    {"type": "invitation.rsvp.open", "ts": 1695000012000, "payload": {}}
  ]
}
```

**Behavior:**

- Validate `session_id` is a hex string of length 32+.
- Validate `invitation_id` exists.
- Rate limit: 60 batches/min per IP.
- Upsert `analytics_sessions` if a `invitation.view` event is present.
- Insert all events into `analytics_events`.
- If `invitation.view.end` is present, update `analytics_sessions.ended_at` + `duration_ms` + `max_scroll_pct`.
- Return `204 No Content`.

**Implementation notes:**

- Use `navigator.sendBeacon()` for the unload event so the browser doesn't cancel it.
- Use `fetch(..., {keepalive: true})` as a fallback.
- IP is used to derive `country_code` and `device_type`, then **discarded** — never stored.

## 6.4 Session reconstruction

**What:** A background job that runs every 5 minutes and:

- Closes sessions that have been idle for >30 minutes (sets `ended_at = last_event_ts + 30min`, computes `duration_ms`).
- Deletes sessions with no events in the last 24 hours (spam cleanup).
- Aggregates per-invitation counts into a `analytics_summary_daily` table (one row per invitation per day).

**Files:**

- `src/python/features/analytics/sessions.py` — new

**Why:** Raw events are cheap to insert but expensive to query. Daily aggregates make dashboards fast.

**`analytics_summary_daily` schema:**

```
CREATE TABLE analytics_summary_daily (
  invitation_id         INTEGER NOT NULL,
  day                   TEXT NOT NULL,          -- 'YYYY-MM-DD'
  unique_sessions       INTEGER NOT NULL,
  total_views           INTEGER NOT NULL,
  avg_duration_ms       INTEGER NOT NULL,
  p95_duration_ms       INTEGER NOT NULL,
  rsvp_submitted        INTEGER NOT NULL,
  rsvp_abandoned        INTEGER NOT NULL,
  gallery_opens         INTEGER NOT NULL,
  album_uploads         INTEGER NOT NULL,
  PRIMARY KEY (invitation_id, day)
);
```

## 6.5 Creator dashboard — per-invitation analytics

**What:** A new "Analytics" tab on each invitation. Shows:

### Top row — 4 stat cards

1. **Total views** — count of sessions. Delta vs previous 7 days.
2. **Unique recipients** — distinct `recipient_id` count. Delta.
3. **Average time on page** — mean session duration. Delta.
4. **RSVP conversion** — submitted / opened × 100%. Delta.

### Second row — time-series chart

- Line chart: views per day over the last 30 days.
- Toggle: 7 days / 30 days / 90 days / all time.
- Overlay: RSVP submissions as a second line.

### Third row — two panels

- **Drop-off funnel:** View → RSVP open → RSVP submit. Shows counts and percentages at each step.
- **Top referrers:** table of domains that sent traffic, with count. Mask small counts (<3) as "Other".

### Fourth row — engagement detail

- **Average scroll depth** — a horizontal bar showing 0–100%.
- **Device split** — donut chart: mobile / tablet / desktop.
- **Country split** — top 5 countries as a list.

### Fifth row — the invitation list table

This is what the user asked for specifically: a **table of their creations** with metrics.

**Columns:**

| Column ↕▾ | Source ↕▾ |
|---|---|
| −Invitation name | `invitations.title` |
| Event date | `invitations.event_date` |
| Status | draft / published / archived |
| Views | `analytics_summary_daily.unique_sessions` summed |
| Avg time | weighted mean of `avg_duration_ms` |
| RSVPs | `analytics_summary_daily.rsvp_submitted` summed |
| Conversion | RSVPs / views × 100% |
| Last activity | max(`analytics_events.created_at`) |
⚙

**Sortable** by any column. **Filterable** by status and date range. **Exportable** as CSV.

**Files:**

- `src/js/pages/dashboard/analytics.js` — new
- `src/python/routes/analytics_routes.py` — new
- `src/css/pages/dashboard.css` — extend

**Routes:**

- `GET /api/invitations/{id}/analytics` — per-invitation metrics
- `GET /api/account/analytics/creations` — the creations table data
- `GET /api/account/analytics/summary` — account-level rollup

## 6.6 Charts — build them yourself

**No chart library. Write them with Canvas 2D.**

**Files:** `src/js/components/chart.js`

**Charts to implement:**

- `LineChart(canvas, {data: [{x, y}], color, fill})`
- `BarChart(canvas, {data: [{label, value}], color})`
- `DonutChart(canvas, {data: [{label, value, color}]})`
- `Sparkline(canvas, {data: [numbers]})`

**Implementation notes:**

- Handle `devicePixelRatio` (multiply canvas size by DPR, scale context).
- Handle resize via `ResizeObserver`.
- Use CSS custom properties for colors so they adapt to dark mode.
- Provide a `data-*` attribute API so charts can be initialized declaratively: `<canvas data-chart="line" data-chart-data='[...]'></canvas>`.
- Add `aria-label` + a visually-hidden table of the data for screen readers.

## 6.7 Real-time activity (optional, behind a feature flag)

**What:** When the host has the invitation open in the dashboard, show a live count of "X people viewing now".

**Technologies:** Same polling infrastructure as presence. `GET /api/invitations/{id}/analytics/live` returns `{activeSessions: N, lastEventAt: ts}`. Poll every 10s while the dashboard tab is visible.

**Feature flag:** `analytics_live_enabled`.

## 6.8 Privacy controls

**What:** Hosts can turn analytics off per invitation. The public page then sends no events.

**Files:**

- `src/python/routes/invitation_routes.py` — add `analytics_enabled` column to `invitations`
- `src/js/pages/public/invitation.js` — check `analyticsEnabled` before firing events

**Also:**

- A public privacy page explaining what's tracked and why.
- A "Delete my analytics data" button per invitation (purges all sessions + events).

## 6.9 Export

**What:** Hosts can export their raw analytics data.

**Files:**

- `src/python/features/analytics/export.py` — new

**Routes:**

- `GET /api/invitations/{id}/analytics/export?format=csv|json` — per-invitation export
- `GET /api/account/analytics/export?format=csv|json` — all invitations

**Implementation notes:**

- CSV: UTF-8 BOM, RFC-4180 quoting. One row per session with joined event counts.
- JSON: `{invitation, sessions: [...], events: [...]}`.
- Streamed for large exports (use `yield` chunks with `Transfer-Encoding: chunked`).

## 6.10 Retention & cleanup

**What:** Auto-prune analytics older than `EINVITE_ANALYTICS_RETENTION_DAYS` (default 365).

**Files:** `src/python/features/analytics/sessions.py` — extend the background job.

**Implementation notes:**

- Delete from `analytics_events` first, then `analytics_sessions`, then `analytics_summary_daily` older than the cutoff.
- Log the prune count to audit events (admin-actionable).
- Never delete a session that's still active (no `ended_at`).

## 6.11 Acceptance criteria for Part 6

- Every listed event fires on the correct user action.
- Events are batched and sent via `sendBeacon` on unload.
- The creator analytics dashboard renders correctly with real data.
- The creations table is sortable, filterable, and exportable.
- Charts are built with Canvas 2D (no library).
- Every label is bilingual EN+KH.
- Analytics can be disabled per invitation.
- Retention cleanup runs daily and is logged.
- `tests/analytics_ingestion_test.py`, `tests/analytics_reports_test.py`, and `tests/analytics_privacy_test.py` all pass.

---

# PART 7 — Cross-Cutting Concerns

## 7.1 Documentation

Every part produces or updates its docs:

| Part ↕▾ | Docs to create or update ↕▾ |
|---|---|
| −1 | `docs/LEGACY-VERSION-HISTORY.md`, rewritten `VERSION_HISTORY.md` |
| 2 | `docs/STRUCTURE-MAPPING.md`, `docs/STRUCTURE-AUDIT.csv` |
| 3 | `docs/editor/UX-GUIDE.md` (component reference), `docs/editor/KEYBOARD-SHORTCUTS.md` |
| 4 | `docs/security/FIELD-ENCRYPTION.md`, `docs/ops/SECRETS-ROTATION.md`, `docs/hosted/WEBHOOKS.md` |
| 5 | `docs/admin/ADMIN-GUIDE.md`, `docs/admin/FEATURE-FLAGS.md` |
| 6 | `docs/analytics/EVENT-MODEL.md`, `docs/analytics/PRIVACY.md`, `docs/analytics/REPORTS.md` |
⚙

## 7.2 Testing

Every part adds tests. Summary of test files to create:

- Part 2: `tests/structure_migration_test.py` — proves the mapping was applied and no old paths remain.
- Part 3: `tests/editor_*.py` — one per feature (guides, selection, inline editing, layers, palette, comments, history).
- Part 4: `tests/security_tenant_isolation_test.py`, `tests/security_field_encryption_test.py`, `tests/security_api_keys_test.py`, `tests/security_session_management_test.py`.
- Part 5: `tests/admin_*.py` — one per admin feature (users, invitations, feature flags, health, bulk ops, impersonation, reports).
- Part 6: `tests/analytics_ingestion_test.py`, `tests/analytics_reports_test.py`, `tests/analytics_privacy_test.py`, `tests/analytics_export_test.py`.

**Every test must run via `tests/v14_test_utils.app_server`** (real HTTP server). No mocking the HTTP layer.

## 7.3 CI gates

Update `.github/workflows/security.yml` (or create `.github/workflows/ci.yml`) to run on every push:

1. `python3 -m py_compile` on every `.py` file.
2. `python3 src/python/build_route_bundles.py --check` — must print `ROUTE_BUNDLE_CHECK_PASSED`.
3. `python3 scripts/check-bilingual-consistency.py` — exit 0.
4. `python3 scripts/check-rate-limit-coverage.py` — exit 0.
5. `python3 -m pytest tests/ -x` — all pass.
6. `bash scripts/security-scan.sh` — no High findings.

## 7.4 Bilingual discipline

Every part adds strings. The rule:

- Every string in a JS file must be in a `STRINGS` object with `en` and `km` keys.
- Every backend response that includes a user-facing message must have `{message_en, message_km}` (or use the existing `_() ` translation helper).
- Never use `km: en` as a placeholder. The CI check catches this.

**Update the check** to also scan backend Python files for missing `message_km` variants. Extend `scripts/check-bilingual-consistency.py`.

## 7.5 Performance

- Every new feature must not regress editor load time by more than 50ms.
- Every new route must respond in <100ms p95 for reads, <300ms p95 for writes (excluding file uploads).
- Every new chart must render in <16ms per frame.
- Add `tests/performance_editor_boot_test.py` that measures time-to-interactive and fails if it regresses.

## 7.6 Backwards compatibility

- Every schema change is additive (`ALTER TABLE ADD COLUMN` only; never `DROP` or `RENAME`).
- Every removed column is marked deprecated for one minor version before removal.
- Every API change that breaks a client must bump the API version (add `/api/v2/...` routes; keep `/api/...` working for one minor version).

---

# PART 8 — Acceptance & Definition of Done

## 8.1 Definition of Done (global)

A task is done when **all** of the following are true:

1. The code or document exists.
2. A test exists in `tests/` and passes via `python3 tests/<file>.py`.
3. `VERSION_HISTORY.md` has an entry for the task's version.
4. Every user-facing string has an `en` and a `km` variant (not byte-identical).
5. Every new route has a `rate_limit(...)` call.
6. The route bundle check passes: `python3 src/python/build_route_bundles.py --check`.
7. The bilingual CI check passes.
8. The rate-limit coverage check passes.
9. The worklog has a `Task ID` entry for the task.
10. No working code was deleted without a replacement.
11. The commit message follows the format in §1.3.

## 8.2 Part acceptance

Each part ends with:

- A **demo** the operator can run: `python3 src/python/core/server.py --host 127.0.0.1 --port 4175` and click through the new feature in a browser.
- A **summary** in `worklog.md` (Stage Summary section) listing what changed and what tests were added.
- A **version bump** in `VERSION_HISTORY.md`.
- A **tag** in git: `git tag v0.<part>.0`.

## 8.3 1.0.0 release criteria

`1.0.0` is released only when:

1. All six parts of this roadmap are complete.
2. All execution items from `ROADMAP-V2.md` §5 are complete:

- Load test run with real numbers in `docs/certification/LOAD-TEST-PLAN.md`.
- DR drill run with a signed report in `docs/ops/`.
- Native platform matrix executed with pass/fail per gate in `docs/certification/`.
- Browser matrix executed.
- Penetration test commissioned and Critical/High findings remediated.
3. `docs/certification/CERTIFICATION.md` is signed by the maintainer and an external auditor.
4. The tenant isolation test suite passes.
5. Field-level encryption is live in production.
6. Creator analytics has at least 30 days of real data behind it.

Only then: `git tag v1.0.0`, publish the release notes, and update `README.md` to remove the "pre-1.0" disclaimer.

---

# Appendix A — Quick reference: what to build, in order

| # ↕▾ | Part ↕▾ | Deliverable ↕▾ | Version ↕▾ |
|---|---|---|---|
| −1 | 1 | Version reset + `VERSION_HISTORY.md` rewrite + `LEGACY-VERSION-HISTORY.md` | 0.54.0 |
| 2 | 2 | File structure reorg + migration script + updated bundle manifests | 0.55.0 |
| 3 | 3.1 | Alignment guides + snapping + multi-select + context menu | 0.56.0 |
| 4 | 3.2 | Inline text editing + text effects + text on curve | 0.56.1 |
| 5 | 3.3 | Image crop + filters + masks | 0.56.2 |
| 6 | 3.4 | Layer panel + pages sidebar + command palette + shortcuts | 0.57.0 |
| 7 | 3.5 | Live cursors + comments + version history | 0.58.0 |
| 8 | 3.6 | Editor polish pass (empty states, loading, dark mode, mobile) | 0.59.0 |
| 9 | 4.1 | Field-level encryption | 0.61.0 |
| 10 | 4.2 | Admin access controls + step-up auth | 0.61.1 |
| 11 | 4.3 | Tenant isolation test suite | 0.61.2 |
| 12 | 4.4 | Session management UI | 0.61.3 |
| 13 | 4.5 | API keys | 0.62.0 |
| 14 | 4.6 | Webhook signing | 0.62.1 |
| 15 | 4.7 | Secrets rotation | 0.63.0 |
| 16 | 5.1 | Admin dashboard | 0.64.0 |
| 17 | 5.2 | User management | 0.64.1 |
| 18 | 5.3 | Invitation management | 0.64.2 |
| 19 | 5.4 | Feature flags | 0.64.3 |
| 20 | 5.5 | Audit log explorer | 0.65.0 |
| 21 | 5.6 | System health | 0.65.1 |
| 22 | 5.7 | Bulk operations | 0.65.2 |
| 23 | 5.8 | Impersonation | 0.65.3 |
| 24 | 5.9 | Report queue | 0.66.0 |
| 25 | 6.1 | Event model + schema | 0.67.0 |
| 26 | 6.2 | Ingestion endpoint | 0.67.1 |
| 27 | 6.3 | Session reconstruction | 0.67.2 |
| 28 | 6.4 | Creator dashboard | 0.68.0 |
| 29 | 6.5 | Charts (Canvas 2D) | 0.68.1 |
| 30 | 6.6 | Real-time activity | 0.68.2 |
| 31 | 6.7 | Privacy controls | 0.68.3 |
| 32 | 6.8 | Export | 0.69.0 |
| 33 | 6.9 | Retention cleanup | 0.69.1 |
⚙

Then: execution items from `ROADMAP-V2.md` §5 → `1.0.0`.

---

# Appendix B — Technology choices, at a glance

| Need | Use | Why not the alternative |
|---|---|---|
| HTTP server | Python `http.server.ThreadingHTTPServer` (existing) | Already there; Flask/Django would be a rewrite |
| Database | SQLite default, PostgreSQL via `EINVITE_DATABASE_URL` (existing) | Already abstracted; ORM would slow it down |
| Object storage | The existing `ObjectStorage` (local/S3/R2/MinIO) | Already works |
| Frontend framework | None — vanilla JS + custom events | No build step; the project's constraint |
| CSS | Plain CSS + custom properties | No PostCSS/Sass; cascading works |
| Editor canvas | HTML/CSS absolute positioning + SVG overlay for guides | Canvas 2D would complicate text editing; absolute positioning keeps inline editing simple |
| Charts | Canvas 2D, hand-written | No library — keeps bundle small and CSP-simple |
| CRDT | Y.js (vendored) | Already vendored; proven |
| Rich text | `contenteditable` + `execCommand` | No ProseMirror/Quill; adds 200KB+ |
| Encryption | `cryptography` library (Fernet) | Already a dependency |
| Malware scanning | ClamAV (Linux) / Defender (Windows) via `security_scanner_v54.py` | Already works |
| Rate limiting | Redis if available, else in-process (existing) | Already implemented |
| Background jobs | The existing `JobQueue` in `platform_v32/jobs.py` | Already works |
| Email | SMTP via `send_platform_email` (existing) | Already works |
| Bilingual | Custom `{en, km}` string tables | No i18n library — the project already does this |

---

*End of roadmap. Read Part 1 first. Do not skip Part 2 — the reorganization must happen before features so paths stay stable. If any task is ambiguous after reading this document, check the referenced existing file in the repo before guessing.*

