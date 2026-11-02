# Round 4 — production-bundle sweep findings

Date: 2026-11-02
Target: **the phase-10 production bundle** served on loopback through
`bugs/round-4/serve_bundle.py` (`127.0.0.1:4180`, static files from
`artifacts/sites-public`) with the isolated backend at `127.0.0.1:4181`
(`EINVITE_DATA_DIR=artifacts/round4-data`). Sites hosting is suspended, so this
round did **not** call `sites_deploy` (owner instruction; OBS-R4-1).

## Result

Three product defects were confirmed and fixed. Two are mobile/tablet editor
defects that made the new bottom bar or the whole 601–820 px drawer range
unusable; the third let a selection refresh close the creation drawer just after
a tap.

| Measure | Result |
|---|---|
| Authenticated flow (`flow_sweep.py`) | **61 checks, 0 failed, 0 application console errors** |
| Editor width loop | 360 / 390 / 768 / 1024 / 1280 / 1440 — Pages pane active, **1 visible card**, overflow 0 at every width |
| Public matrix (`live_sweep.py`) | **120 records** (20 routes × 6 widths), **120 screenshots** |
| Public statuses | 108 × 200, 12 × **expected 404** (missing slug + missing route at every width) |
| Horizontal overflow > 4 px | **0 records** |
| Page errors | **0** |
| Console errors | **18**, all deliberate missing-route resource 404s |
| Failed requests / console warnings | **0 / 0** |
| Unlabelled inputs / unnamed buttons | **0 / 0** |
| PNG export | **38,876 bytes**, valid PNG signature, 0 CSP/console errors |
| RSVP submit | thank-you state reached with placeholder guest name |
| Gallery form 390 / 1440 | fields 220 / 330 px, button matches field within 2 px, label not clipped, load-more hidden, overflow 0 |
| Template filter | 36 → 1 on `royal` |
| Khmer digits | present at 360, 390 and 1440 on the public invitation |
| `tests/v14_live_layout_test.py` | **pass** (1440/768/390 editor, 1440/390 guest) |

## Product findings

| ID | Route | Viewport | Repro | Expected | Actual | Severity | Status |
|---|---|---|---|---|---|---|---|
| **BUG-R4-1** | `/invitations/<id>/editor` | all ≤820 (measured 390, 768) | Open the editor and tap any chrome — e.g. **Tools** in the bottom bar. | The tapped control does what it says; the drawer opens for that control. | `<body>` carried `data-inspector-tab`, so every delegated `closest('[data-inspector-tab]')` matched a tap **anywhere**, and the bottom bar's own taps were classified as inspector-tab clicks. | P1 | **Fixed** — body state renamed `data-active-inspector`; v14 asserts only `.studio-inspector-tab` carries the attribute and that Tools/Quick yield `creation`/`inspector`. |
| **BUG-R4-2** | `/invitations/<id>/editor` | **601–820** (measured 768) | Load the editor at 768. | A visible control opens the creation drawer, as at ≤600. | Layout was mobile (drawer, rail off-canvas at `x=-351`, `inert`), but `mobile-editor.js` still used 600 px and the bar was only styled ≤600: bar `display:none`, `0×0`. Pages/Elements/Text were unreachable. | P1 | **Fixed** — both breakpoints use `EInviteResponsiveLayout.MOBILE_MAX` (820); bar rules extended to 601–820 with the six-column grid. After: bar `768×64`, `display:grid`, Tools → `creation`, rail `x=0`, Pages card visible. |
| **BUG-R4-3** | `/invitations/<id>/editor` | mobile (measured 360×800) | Open the editor, tap **Tools** while boot is finishing (≈600 ms after `editor-ready`). | The drawer stays open. | `syncInspectorDrawer(false)` called `EInviteResponsiveLayout.closeInspector()` — which means “drawer → canvas” — on every selection refresh, so a boot/selection update closed the panel ~20 ms after the tap. Measured `mode="tools"` with `editorDrawer="canvas"`; trace: `closeInspector ← syncInspectorDrawer ← updateSelectionCard`. The same call is what reverted a programmatic `openCreation()` during boot (old OBS-R4-2). | P1 | **Fixed** — on mobile the inspector is closed only when it is the open drawer. Drawer now survives 1 s of samples and `openCreation()` at `editor-ready` persists; the 360/390/768 flow checks pass. |

## Observations

| ID | Kind | Scope | Detail | Status |
|---|---|---|---|---|
| OBS-R4-1 | Hosting allowance | every deployed route | `sites_inspect` records `state: suspended`, 10,755 / 10,000 daily requests, reset 2026-11-02T00:00Z. The owner instructed this round not to retry `sites_deploy`. | **Open, external** — no deploy attempted; the live site has **not** been shown to run this build. |
| OBS-R4-2 | Boot race (resolved) | editor ≤820 | A drawer opened in the first few hundred ms after `editor-ready` used to be closed by the selection refresh. Root cause is BUG-R4-3; after the fix `openCreation()` at `editor-ready` stays open (`probe-drawer3`, T0 → 3 s). | **Closed by BUG-R4-3** |
| OBS-R4-3 | Finder false positives | 120 public records | 337 `clipped` hits are `.sr-only` headings/labels, the 1 px skip link, hidden alternate-language spans and ellipsis in the editor title. 310 `smallTargets` are skip links, the brand menu, native checkboxes and off-canvas controls. 5 `rightEdge` hits are the off-canvas `#workflowV5Focus` rail (`scrollWidth - clientWidth = 0` everywhere). | Not defects — same classes triaged in round 3; no new interaction failure observed. |
| OBS-R4-4 | Sweep tooling | `flow_sweep.py` | The first two runs crashed on an off-canvas rail after tapping inside the boot window, and the JSON was written only at the end, leaving a stale file. The sweep now waits for the settled editor (600 ms), requires `[data-studio-tab="pages"]:visible`, and persists partial results via `atexit`. | **Done** |

## Earlier-round regression checks

| ID | Check | Result |
|---|---|---|
| BUG-R1-1 | Signed-out editor navigation | **Pass** — `/invitations/<id>/editor` → `/dashboard.html?next=…`. |
| BUG-R1-2 | Published vs missing slug | **Pass** — published slug 200 and missing slug 404 at all six widths; missing route 404. |
| BUG-R1-3 | Export / CSP regression | **Pass** — valid 38,876-byte PNG, 0 CSP/console errors during export. |
| BUG-R1-4 | Manual-runner fixture | **Pass** — refreshed to the v17 model (settled rects, revealed Transform panel, `.motion-line.motion-snap`, persisted Guides toggle, mobile quick inspector + numeric transform); `V18_PROFESSIONAL_EDITOR_TEST_PASSED`. `v0_52` also passes with the live selection outline. |
| BUG-R2-1 | Empty guest features | **Pass** — 0 unconfigured sign-up/poll/album panels. |
| BUG-R2-2 | Album form reflow | **Pass** — 390: 220 px fields, form 270 px; 1440: 330 px, form 380 px; label not clipped; load-more hidden; overflow 0. |
| BUG-R2-3 | Duplicate platform credit | **Pass** — exactly one credit. |
| Phase-10 | Pages-manager grouping | **Pass** — every width shows the active Pages pane with 1 real page card; 0 overflow. |
| P1 CLS | Editor first paint | **Improved to 0.3927** (from 0.4959 phase 10, 0.4840 at the start of this pass) on the built bundle, 1440×900, 15 shifts, 0 page errors. Two causes fixed: a wrapping toolbar and a late open typography disclosure. Remaining ramps are listed in the close-out section; the ≤0.1 target is not met. |

## Live-matrix triage

The 12 deliberate 404 records produce 18 console errors (two subresources on the
missing slug, one on the missing route) and no page errors. There are no failed
requests, no console warnings, no unlabelled inputs, no unnamed buttons and no
page-level horizontal scroll. Public routes exercised: `/`, `/privacy`,
`/templates`, `/public`, `/verify`, `/reset`, `/billing`, `/admin`, `/dashboard`,
`/designer`, `/guests`, `/responses`, `/analytics`, `/materials`, `/checkin`,
`/account`, the published invitation, the missing slug, the missing route and
the signed-out editor — each at 360, 390, 768, 1024, 1280 and 1440.

## Evidence

- `flow-sweep.json` — 61 checks with details; `flow-run.log` — full run.
- `live-sweep.json` — 120 records with the per-record audit; `live-run.log`.
- `shots/` — 120 public screenshots plus the flow and probe frames
  (workspace only, not committed because of size).
- `shots/probe-panenav-360.png` — drawer open at 360 with the final build.
- `probe_pane_nav.py`, `probe_tablet.py`, `probe_drawer3.py` — the probes behind
  the BUG-R4-2/3 measurements.

## Deployment status

Superseded on 2026-11-02: the allowance reset and `sites_deploy` succeeded
(`state: succeeded`, `published: true`). The build verified here is now live at
https://site-607d0a9e087e425b9946eae2ab964d24.freebuff.page and round 5 checks
the deployed origin.

## Close-out (2026-11-02)

- **CLS:** measured with `artifacts/verify/cls_bundle_probe.py` against the built
  bundle at 1440×900, `waitUntil:load`, 7 s settle, buffered Layout Instability
  API. Before this pass **0.4840** (15 shifts, 0 errors); after **0.3927**
  (15 shifts, 0 errors). Phase-10 reference was 0.4959.
- **What changed:** `body.studio-experience .stage-wrap > .studio-canvas-toolbar`
  is now `flex-wrap:nowrap!important` (computed wrap made the 20+ toolbar
  children, and later `#v23ContextToolbar`, take second rows: 118 → 60 → 106 px),
  and `#advancedTextLayout` is injected closed instead of open.
- **What remains:** a 62 px toolbar/topbar ramp in the first ~1.7 s, the
  `.ei-section-order-builder` remount at ~2.4 s (~0.05), a 6 px layout step at
  ~2.7 s, and a late inspector-group growth/revert around 6 s. Each is an
  async module replacing first-paint geometry, not a missing reservation.
- **Manual-runner drift found:** v17 renders snaps as `.motion-line.motion-snap`
  (not `.pe-smart-guide`), routes guides through
  `EInviteMotion.measurements.addGuide()` (not `.pe-user-guide`), opens the quick
  inspector on mobile by default (not canvas mode), and needs the Transform
  panel revealed before filling `[data-pe-transform]`. `v0_52` needed the live
  (visible) selection outline. Those were fixture assumptions, not product bugs.
