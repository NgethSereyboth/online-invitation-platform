# V0.52 Release-Gate Stabilization Report

## Baseline and scope

- Baseline: `e-invitation-platform-intelligent-event-ecosystem-v0.52-repaired-final.zip`
- Baseline SHA-256: `bf1c92d9a17f1bd4931cb6200874fbb5e31ed20f6ae25f8200c36695d89e060b`
- Public version: `0.52` — unchanged.
- Document schema: `27` — unchanged.
- README: unchanged.
- Production/canonical application source changed in this narrow pass: **none**.
- Bundle budgets: unchanged.

## Four release-check root causes and fixes

1. **AI served-browser test onboarding interception**
   - Root cause: a fresh editor legitimately opens the production onboarding tour after editor readiness; the test attempted to click the AI launcher underneath it.
   - Fix: `tests/browser_runtime.py` now owns one `dismiss_editor_onboarding()` helper. It waits for `document.documentElement.dataset.editorReady === 'true'`, awaits onboarding initialization when exposed, semantically clicks visible `#finalTourDismiss`, and waits until the real tour is closed/hidden. `tests/v0_52_ai_live_browser_test.py` uses that helper before opening the real AI panel.

2. **UI smoke onboarding interception after dark-mode reload**
   - Root cause: the fresh-profile editor reload can still present the intended onboarding layer before the smoke test uses the text-tool/canvas path.
   - Fix: `tests/ui_smoke_test.py` uses the same centralized helper after its dark-mode reload. The production tour remains enabled; no force-click, hidden-control bypass, or pre-seeded unrelated state was introduced.

3. **Autosave regression targeted hidden legacy Event controls**
   - Root cause: the regression test still drove hidden legacy `#rsvpEnabled` / venue controls rather than the current visible Event settings contract.
   - Fix: `tests/v0_52_autosave_status_test.py` now waits for editor readiness/onboarding, opens visible **Event details**, toggles the accessible **Enable RSVP attendance form** checkbox, fills **Venue — English**, keeps both edits inside one normal debounce window, verifies the newest SQLite draft/status/network contract, reloads, and verifies both values again through the same visible Event UI.

4. **V17 served Undo/Redo timing race in the assertion**
   - Root cause: the served regression used fixed 320/420 ms sleeps as its primary Undo/Redo oracle even though history, nested transforms, selection, redraw, and autosave are asynchronous. The independent audit observed one matrix failure followed by four isolated passes, which is consistent with a stale observation race rather than evidence of a product transaction defect.
   - Fix: `tests/v17_served_editor_test.py` captures the complete pre/post nested object geometry, group graph, history depth/cursor, redo depth, and selection. It waits for the resize transaction to commit, then waits after Undo and Redo until every expected field/state is restored. Timeout failures include structured expected/actual diagnostics. No professional-editor/history production source was changed because a product race was not proven.

## Exact files changed in this stabilization pass

### Canonical production source

- **None.**

### Shared browser test tooling

- `tests/browser_runtime.py`

### Browser tests

- `tests/v0_52_ai_live_browser_test.py`
- `tests/ui_smoke_test.py`
- `tests/v0_52_autosave_status_test.py`
- `tests/v0_52_dashboard_cover_navigation_test.py` — adopts the same helper because it also creates a fresh served editor profile.
- `tests/v17_served_editor_test.py`

### Release evidence / documentation

- `BUILD_INFO.json`
- `V0_52_RELEASE_FILE_HASHES.sha256`
- `V0_52_RELEASE_GATE_STABILIZATION_REPORT.md` (new)

No application JavaScript/CSS/Python source, schema file, README, route budget, or generated bundle source was changed in this pass.

## Exact complete registered-gate result in this environment

Command:

`python run_review_checks.py --continue-on-failure --fast-workers 8`

Result:

- Deterministic: **90/90 passed**.
- Browser: **102/114 passed**.
- Total: **192/204 passed**.
- Exit code: **1**.

The local browser count is not presented as release certification. Eleven failed entries are real HTTP-served browser suites that stop at the first navigation with Chromium `net::ERR_BLOCKED_BY_ADMINISTRATOR`, before application code executes. This includes the four targeted served checks where applicable. The remaining local browser failure is `tests/v17_professional_editor_core_test.py`, which is not modified in this pass: the same untouched test also fails when run directly from the pristine supplied baseline in this container, while the independent audit reported it green. Diagnostic probing showed the model-space centered resize remains centered; the local Chromium selection-overlay metric differs.

## Required V17 repeated served regression

Five fresh isolated executions of `tests/v17_served_editor_test.py` were attempted:

- Run 1: blocked at initial `page.goto()` — `ERR_BLOCKED_BY_ADMINISTRATOR`.
- Run 2: blocked at initial `page.goto()` — `ERR_BLOCKED_BY_ADMINISTRATOR`.
- Run 3: blocked at initial `page.goto()` — `ERR_BLOCKED_BY_ADMINISTRATOR`.
- Run 4: blocked at initial `page.goto()` — `ERR_BLOCKED_BY_ADMINISTRATOR`.
- Run 5: blocked at initial `page.goto()` — `ERR_BLOCKED_BY_ADMINISTRATOR`.

Therefore **0/5 reached application or history code in this container**. These are environment-blocked attempts, not V17 assertion failures. The stabilized test remains a real served-browser test and must be rerun at least five times in the unrestricted independent audit environment.

## Bundle measurements

No production source changed, so derived route bundles/manifests were not regenerated solely for this test-only pass.

- Canonical editor bundle: **1,413,344 / 1,420,000 bytes** — **6,656 bytes headroom**.
- Complete `index.html` startup assets: **1,417,331 / 1,420,000 bytes** — **2,669 bytes headroom**.
- Public invitation route: **233,585 / 260,000 bytes** — **26,415 bytes headroom**.

## Preserved behavior

The 90/90 deterministic gate remains green, including the repaired AI context/backend flow, canonical asset/publication rules, dashboard navigation contracts, autosave persistence/revision behavior, pure-invitation RSVP publishing, immutable snapshots, Khmer/date contracts, V29–V0.52 modules, raster worker, security/authorization/provider boundaries, and generated-bundle/release-evidence integrity.

## Remaining limitation

This container's Chromium policy blocks real HTTP navigation to loopback/container-hosted test servers with `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Because the task explicitly forbids replacing served-browser checks with mocks or force-click bypasses, the required **114/114 browser and 204/204 total release certification cannot be truthfully claimed here**. The package is prepared for the unrestricted independent browser environment, where the four originally reported failures should be rerun along with the full registered matrix and five V17 repetitions.
