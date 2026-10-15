# Phase 2 final report — einvite-platform UI remediation (2026-10-13)

Server: `http://127.0.0.1:4175` (already listening, HTTP 200). Tree not committed; nothing staged.

## Gate results

| Check | Command | Result |
|---|---|---|
| Page errors | `node tools/page-errors.mjs --all` | PASS — pages=16 consoleErrors=0 non2xx=0 |
| UI sweep + click pass | `BASE_URL=http://127.0.0.1:4175 node tools/ui-sweep.mjs --click --quiet` (the sweep defaults to port 8124; it must be pointed at 4175) | rows=80 overflow=0 escapes=0 console=0 netfail=0 brokenLinks=0 overlays=6 deadControls=11 inputRequiredControls=19 resetReloads=61. The `SWEEP` summary line printed; the wrapper's exit code was not captured, because the node process hung on exit after writing its JSON. |
| Build / mirror check | `python3 build.py all --check` | PASS — exit 0, MIRROR_CHECK_PASSED (up_to_date=323) |
| Pytest | `.venv/bin/python -m pytest tests/ -q` | 85 passed, 1 xfailed (exit 0) |

Sweep detail: the counts move between runs (earlier runs reported `deadControls` 12 and 13, and `overlays` 1). Dead controls are *candidates* (see [D4-residuals-2026-10-13.md](D4-residuals-2026-10-13.md)), not confirmed defects. The sweep's `NAV-FAIL` on every route in an earlier attempt was the port mismatch above, not a product fault.

## Task status

- **A1, D4a (AI button stub)** — marked Fixed in [bug-inventory.md](bug-inventory.md). Covered by the gate above; the per-item evidence files were not re-measured this session.
- **D1b (`•••` popover overlap)** — **measured fixed** in the inventory. With the menu open, the popover overlaps no panel and stays inside the viewport at 1024 (x 344–630), 1280 (x 406–692) and 1440 (x 446–732). The upward flip on short viewports is not verified.
- **D4 detector** — fixed this session. The reset check no longer closes the app's default-open `<details>` or counts boot-time mobile drawers. `contaminated` dropped 76 → 0 on index.html @1280; dead-control candidates 15 → 8. Details in [D4-residuals-2026-10-13.md](D4-residuals-2026-10-13.md). Inventory row updated in [bug-inventory.md](bug-inventory.md).
- **Task 6 — skipped browser tests** — Playwright and Chromium were already installed. Results:
  - `v22_2_page_mobile_test` — **PASS** (under the origin shim below).
  - `v20_semantic_style_parity_test` — **PASS** (under the origin shim below).
  - `v0_52_final_ux_refinement_browser_test` — **FAIL, stale test.** Line 41 waits for `.v24-footer-tools`. That class was renamed to `v54-footer-tools` and nothing in `src/` uses the `v24-` selectors any more (`v24-footer-tools`, `v24-inspector-empty`, `v24-has-selection`, `v24-advanced-control`, `v24-inspector-toggle`, `v24-zoom-value` all have zero hits). Fixing it means editing the test's selectors and assertions, which constraint 5 does not allow without approval.

## Harness findings (not product defects)

1. `tests/inline_editor_runtime_test.py::build_inline_editor` is loaded with `page.set_content`. On the current Playwright Chromium, that gives an opaque origin, and the page throws `Access is denied` on `localStorage` at boot. The editor never mounts (`#mobileToolsMode` count 0, `EInviteCommands` undefined). Serving the same HTML from a routed `http://` origin mounts it correctly (`#mobileToolsMode` 1, `EInviteCommands` object).
   - Verified with `/tmp/run_with_origin.py`, which patches `Page.set_content` only for the run and leaves the test files untouched. It is not in the repo.
   - Proposed permanent fix (needs approval, touches tests): replace `set_content` with a routed `goto` in `build_inline_editor` callers.
2. `v0_52` is stale against the renamed `v54-` UI (see Task 6).

## Open items

- **Overlay: `button.fp-mobile-pane-handle` (1024px):** the sweep flags a 34×42 px geometric overlap at bottom-left (rect 16,710). Hit-testing at three points on the handle returns the handle itself, so it is topmost (z 97) and clickable. The overlap is with a neighbour beneath it. Whether that is the intended pull-tab placement needs the owner to confirm; it is not changed in this phase.
- **Overlay: `.guest-demo-badge` on public.html (all widths):** the sweep flags it because `#openCover` (the opening scene, a full-viewport `fixed` layer) covers it before the guest opens the invitation. After the cover is clicked, the badge is uncovered and hit-tests as itself. This is intentional, not a defect.
- **Dead-control candidates (11 in the final run):** triaged, not fixed.
  - `public.html` `›` — a false positive. Its handler is `go(active+1)` in [guest-journey.js](../../src/js/guest-journey.js), which scrolls to the next section, so the sweep's state fingerprint can't see it.
  - `materials.html` `#refreshBtn` — a false positive. It is wired to `load()`, and a refetch with unchanged data looks like no change.
  - `index.html` (9 candidates) — not verified. Several are zero-size or off-screen at 1440 (`Design`, `Flow`, `Bindings`, `Photo styles`, `History`, `Graphics diagnostics`, `TT`), so they sit in collapsed panels. `Layers` is off-screen at 1440 (x 1563). `View all` is at x −16. Verifying them needs each panel opened first; they are not confirmed dead.
- **Input-required controls (19):** these need form input before they can be exercised. Not tested.
- **xfail:** `tests/admin_tools_v2_gap_test.py::test_admin_metrics_v2_route_exists`. Reason is written in the file: `/api/admin/*-v2` routes are not implemented (404). The file is untracked (`??`).
- **v0_52 test** and **harness origin fix** — need the user's go-ahead to edit tests.
