# V0.52 Release-Gate Reliability Stabilization Report

## Scope

Baseline: `e-invitation-platform-intelligent-event-ecosystem-v0.52-release-gate-stabilized.zip`.
Public version remains **0.52**. Invitation schema remains **27**. README is unchanged. No bundle budget was raised and no production onboarding behavior was disabled.

## Root causes and fixes

1. **Autosave Event-details navigation was not idempotent.** The test used an exact accessible name `Event details`, while the production launcher exposes `Event details Names, date, venue and RSVP`; after reload the Event workspace may already be open and the launcher may not exist. `tests/browser_runtime.py` now provides `open_event_details()`: it first returns the already-visible exact RSVP/venue controls, otherwise uses the stable `[data-flow-open="event"]` launcher (falling back to a `^Event details\b` accessible-name prefix), then waits for both visible controls. The autosave regression uses it before the initial edit and after reload. No hidden legacy control or JavaScript mutation is used.

2. **V17 gesture checks inspected history before proving the pointer gesture actually transformed the model.** Product inspection confirmed the professional pointer-up path commits synchronously through one professional command and one editor transaction/history push. The served test now captures object geometry, group graph, selection, history, professional command sequence, selection/handle geometry and pointer destination; uses geometry-driven rotate/resize destinations; waits first for observable model transformation; then requires exactly one matching professional command and one history entry. No production history code was changed.

3. **V17 Undo/Redo and publish checks lacked sufficient state/network diagnostics.** Undo and Redo now wait for exact pre/post object geometry, group graph, selection and history/redo depth equality. Publish waits for `Saved`, `Server connected`, no pending/in-flight/conflict save, an enabled non-busy publish button, and the real POST response; failures include structured UI/history/network diagnostics. The threaded test server suppresses only expected client disconnect exceptions (`BrokenPipeError`, reset/aborted connection, Windows 10053/10054) while preserving genuine server errors.

4. **Mobile Quick Edit hit testing was synchronized to visibility but not to final drawer/scroll geometry.** The shared helper now waits until the creation drawer is hidden and inspector visible, scrolls each control into view, requires a stable bounding rectangle across two animation frames, and verifies `elementFromPoint()` reachability. On timeout it reports viewport/visualViewport, drawer classes/attributes/scrolls, control/canvas rectangles, computed display/visibility/position/z-index/pointer-events and the full hit-test stack. Ten successful fresh-process runs found no reproducible canvas-over-inspector CSS defect, so no mobile production CSS was changed and no force-click is used.

## Files changed

Canonical/runtime:
- `server.py` — expected browser client-disconnect traceback filtering only.

Tests/helpers:
- `tests/browser_runtime.py`
- `tests/v0_52_autosave_status_test.py`
- `tests/v17_served_editor_test.py`
- `tests/inline_editor_runtime_test.py`

Release evidence:
- `BUILD_INFO.json`
- `V0_52_RELEASE_FILE_HASHES.sha256`
- `V0_52_RELEASE_GATE_RELIABILITY_REPORT.md`

README and all editor/public canonical JS/CSS/schema sources remain unchanged.

## Validation

- Python compilation: **246/246** sources passed.
- Top-level JavaScript syntax: **172/172** passed.
- `python dependency_preflight.py`: passed, including WOFF2 validation and Chromium launch.
- `python build_editor_bundle.py --check`: passed.
- `python build_route_bundles.py --check`: passed.
- `python build_page_manifests.py --check`: passed.
- `tests/v0_52_remaining_fixes_contract_test.py`: passed.
- `tests/v0_52_ai_real_server_test.py`: passed.
- `tests/v17_layers_clipboard_history_test.py`: passed.
- `tests/v20_1_stabilization_contract_test.py`: passed.
- Mobile Quick Edit reliability: **10 successful fresh-process passes**. One additional non-counted Playwright process hung during teardown before reporting; a subsequent fresh process passed and no browser process remained.
- Local exact registered deterministic runner: **63/63 completed entries reported PASS** before the execution tool wall-clock ceiling terminated the command; no deterministic assertion failure was reported.

### Served-browser limitation of this execution host

This container's system Chromium is enterprise-managed with `URLBlocklist: ["*"]`. Real HTTP navigation to the local test server is rejected at the initial `page.goto()` with `net::ERR_BLOCKED_BY_ADMINISTRATOR` before application JavaScript executes. Direct autosave and V17 served attempts therefore cannot reach the code under test here. The tests remain real served-browser tests; they were not mocked, force-clicked, skipped, or converted to inline fixtures.

The user-provided independent unrestricted pre-pass result was **90/90 deterministic, 111/114 browser, 201/204 total, exit 1**. The required final unrestricted rerun target remains **90/90 deterministic, 114/114 browser, 204/204 total, exit 0**. This report does not claim that target was executed in this managed-browser container.

## Bundle discipline

No frontend canonical source changed; derived bundles were not regenerated solely for test changes.

- Canonical editor bundle: **1,413,344 / 1,420,000 bytes** — **6,656 bytes headroom**.
- Complete editor startup assets: **1,417,331 / 1,420,000 bytes** — **2,669 bytes headroom**.
- Public invitation route: **233,585 / 260,000 bytes** — **26,415 bytes headroom**.

## Remaining limitation

Final release certification requires the exact 204-check matrix and the required 3x autosave / 10x V17 served repetitions in an unrestricted browser environment. External-provider/native-platform/security/load/GPU/disaster-recovery validations remain pending as previously documented.
