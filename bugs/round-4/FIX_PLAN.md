# Round 4 — fix plan

Date: 2026-11-02
Target: phase-10 production bundle served on loopback (`127.0.0.1:4180`) with the
isolated backend on `127.0.0.1:4181`. Sites hosting is still suspended, so this
round deliberately did **not** call `sites_deploy` (OBS-R4-1).

## Ordered tasks

| # | ID | Task | Suspected cause | Files changed | Severity | Status |
|---|---|---|---|---|---|---|
| 1 | BUG-R4-1 | Stop the document body from impersonating an inspector tab. | `studio-experience.js` wrote `data-inspector-tab` on `<body>`; every `closest('[data-inspector-tab]')` delegate then classified a tap **anywhere** (including the new mobile bar's Tools button) as an inspector-tab click. | `src/js/studio-experience.js`, `src/css/editor-inspector.css`, `tests/v14_live_layout_test.py`, generated bundle/mirror | P1 | **Fixed** |
| 2 | BUG-R4-2 | Show the mobile creation bar across the whole drawer range, 601–820 px. | `mobile-editor.js` used `max-width: 600px` while `EInviteResponsiveLayout.MOBILE_MAX` is 820, and the bar rules lived only inside `@media (max-width: 600px)`. At 768 the layout was a drawer, the rail sat inert at `x=-351`, and no visible control could open it. | `src/js/mobile-editor.js`, `src/css/editor/editor-styles.css`, `tests/v14_live_layout_test.py`, generated bundle/mirror | P1 | **Fixed** |
| 3 | BUG-R4-3 | A selection refresh must not close the creation drawer. | `syncInspectorDrawer(false)` called `EInviteResponsiveLayout.closeInspector()`, which means “drawer → canvas”, not “close the inspector if open”. A boot/selection refresh ~20 ms after a Tools tap closed the panel; at 360×800 the bar reported `mode=tools` while `editorDrawer=canvas`. | `src/js/editor/editor-core.js`, `tests/v14_live_layout_test.py`, generated bundle/mirror | P1 | **Fixed** |
| 4 | OBS-R4-2 | Make the sweep drive a human-paced, state-verified drawer path and keep partial results. | The sweep tapped Tools inside the boot window BUG-R4-3 closed, then timed out clicking an off-canvas rail; the JSON was written only on success, so the crash left a stale file. | `bugs/round-4/flow_sweep.py`, `bugs/round-4/probe_pane_nav.py` | Tooling | **Done** |
| 5 | — | Re-run the editor contract, the 61-check authenticated flow, the 120-record six-width matrix and the final gates; write `FINDINGS.md`; update `PROGRESS.md`. | — | `bugs/round-4/*`, `PROGRESS.md` | — | **Done** |
| 6 | OBS-R4-1 | Redeploy the production bundle and repeat the live checks. | Sites daily allowance is suspended (10,755 / 10,000); the owner instructed this round not to retry `sites_deploy`. | none (external) | External blocker | **Blocked** |

## Fix detail

### BUG-R4-1 — body attribute reuse

The body carried `data-inspector-tab` as state, the same attribute the tab
buttons use as a contract. Delegated handlers could no longer tell a tab from a
tap on the page. The body state was renamed to `data-active-inspector` and the
three body-scoped CSS selectors follow it. The v14 gate now asserts that every
`[data-inspector-tab]` node is a `.studio-inspector-tab`, and that the bar's
Tools/Quick taps produce `creation`/`inspector` drawers with matching
`aria-hidden` on the two asides.

### BUG-R4-2 — breakpoint mismatch

`mobile-editor.js` now reads `window.EInviteResponsiveLayout?.MOBILE_MAX` (820)
instead of a private 600 px query, so its drawer commands and bar agree with the
layout contract. The bar's existing rules were extended into the existing
`@media (min-width: 601px) and (max-width: 820px)` block with the same
six-column grid the ≤600 px layout uses (Advanced floats above the bar only
below 371 px). The v14 gate gained a 768 px case: bar visible, Tools opens the
creation drawer with the left pane on-screen, Quick opens the inspector, and the
Pages card is visible at that width.

### BUG-R4-3 — “closeInspector” is not “close the inspector”

`syncInspectorDrawer(false)` runs on every selection refresh, including boot.
On mobile it called `closeInspector()`, which sets the drawer to `canvas`
regardless of which drawer was open. The fix restricts that call to the case it
was meant for: the inspector drawer is the open one (or the layout is not the
mobile drawer layout). The v14 gate now clears the selection while Tools is
open and requires the drawer to stay `creation`.

## Verification

| Check | Result |
|---|---|
| `tests/v14_live_layout_test.py` (1440, 768, 390 editor + 1440/390 guest) | **pass** |
| Authenticated flow `bugs/round-4/flow_sweep.py` | **61 checks, 0 failed, 0 console errors** |
| Editor width loop (360/390/768/1024/1280/1440) | Pages pane active with 1 visible card at every width; overflow 0 |
| PNG export | 38,876 bytes, valid signature |
| `python3 build.py all` + `python3 tools/build-sites-bundle.py` | exit 0, `MIRROR_CHECK_PASSED` |
| `python3 build.py all --check` | see `PROGRESS.md` |
| `python3 -m compileall -q src/python tests` | see `PROGRESS.md` |

No `@ts-ignore`, `eslint-disable`, deleted test, weakened assertion or lowered
threshold was used. No personal data or secret was added.

## Remaining

Only the external deployment step is open. The Sites allowance reset is
2026-11-02T00:00:00Z, but the owner asked this round not to retry the deploy, so
the live site has not been shown to run this build. That claim stays open until
a post-reset `sites_deploy` succeeds and the live checks are repeated.
