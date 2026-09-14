# V20.1 Stabilization Report

## Release identity

- Product: **E-invitation-website**
- Release: **V20.1 Typography Stabilization**
- Date: **2026-07-30**
- Sole baseline: `e-invitation-platform-typography-system-v20-completed.zip`
- Invitation compatibility: **schemaVersion 13**
- Typography model version: **1**
- Status: **repaired and verified by three consecutive native Windows gates; Linux explicitly waived by the user and not claimed**

## Verification summary

- Native Windows deterministic matrix: **43/43 passed in each of three consecutive retained release runs**.
- Native Windows required Chromium matrix: **32/32 passed in each of three consecutive retained release runs**, with browser skips treated as failures.
- New V20.1 Chromium suites passed: dashboard actions, semantic/style boundary including editor-preview EN/KM reprojection, bilingual public switching, lifecycle/mobile.
- Interactive browser verification also passed at desktop and 390x844: starter semantic hierarchy, EN/KM preview semantics and paired fonts, mobile editor layout, and a clean warning/error console.
- Generation and checks passed: typography contract, editor bundle, route bundles, page manifest, unchanged performance budgets, Python compile, JavaScript syntax, dependency preflight and WOFF2 decode.
- Three consecutive official `python release_check.py` runs completed with exit code 0 using `EINVITE_FAST_WORKERS=1`; every log contains both authoritative V20.1 release markers.
- Native Linux three-run certification was explicitly waived by the user on 2026-07-30. Linux success is not claimed.

## Numbered defect record

### 1. P0 dashboard missing function

- **Changed files:** dashboard.js
- **Migration/behavior:** Added one lifecycle-safe dashboard thumbnail owner; essential action binding happens before optional thumbnail hydration.
- **Before/after evidence:** Static Chromium dashboard action test passes at 1440/360/390/430.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Connected served-dashboard execution remains pending outside the sandbox.

### 2. Competing dashboard thumbnail paths

- **Changed files:** dashboard.js, final-polish.js
- **Migration/behavior:** dashboard.js owns card thumbnails; final-polish explicitly excludes invite cards.
- **Before/after evidence:** Static source and browser ownership assertions pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None in implementation.

### 3. Thumbnail exception aborted actions

- **Changed files:** dashboard.js
- **Migration/behavior:** Hydration is queued after handlers and wrapped in an optional-error boundary.
- **Before/after evidence:** All seven action handlers remain bound in the runtime test.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Connected failure injection is pending unrestricted server execution.

### 4. Controller teardown

- **Changed files:** dashboard.js, final-polish.js, typography-layout-service.js
- **Migration/behavior:** Controllers are stored and disconnected on rerender/pagehide; non-dashboard fallback stores its controller.
- **Before/after evidence:** Observer churn test records two creates and two disconnects.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Browser GC itself is not asserted.

### 5. Dashboard action regression coverage

- **Changed files:** tests/v20_1_dashboard_actions_runtime_test.py
- **Migration/behavior:** Added desktop and 360/390/430 action coverage and static notice assertion.
- **Before/after evidence:** Runtime test passes with no console/page errors.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Connected server mode still requires unrestricted HTTP navigation.

### 6. Fresh project serialized as Body/18

- **Changed files:** app.js, index.html
- **Migration/behavior:** Added authoritative starter objects with Display/Subheading/Body and retained hero image.
- **Before/after evidence:** Semantic boundary runtime test sees Display 64, Subheading 28, Body 18.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Full connected account lifecycle pending external gate.

### 7. Legacy starter DOM caused wrong defaults

- **Changed files:** index.html, app.js
- **Migration/behavior:** Starter DOM now carries semantic IDs/model data; initial.objects is authoritative.
- **Before/after evidence:** Inline editor no longer collapses all starter text to Body.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 8. Starter hierarchy

- **Changed files:** app.js, index.html
- **Migration/behavior:** Title=Display, subtitle=Subheading, details=Body.
- **Before/after evidence:** Verified in real Chromium.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 9. Premature model-version stamping

- **Changed files:** app.js, typography-document-model.js
- **Migration/behavior:** Serialization stamps model version only when semantic data exists; existing V20 styles are preserved.
- **Before/after evidence:** Migration/refresh tests pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Historical malformed drafts continue through explicit migration rules.

### 10. Fresh lifecycle testing

- **Changed files:** tests/v20_1_semantic_boundary_runtime_test.py and inherited persistence/server suites
- **Migration/behavior:** Static starter and inherited save/publish paths retained.
- **Before/after evidence:** Inline starter and deterministic persistence suites pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Connected new-account/reload/publish test awaits unrestricted server gate.

### 11. Combined hidden EN/KM locale inference

- **Changed files:** public-page.js
- **Migration/behavior:** Visible content is reprojected with an explicit locale; no locale inference from concatenated variants.
- **Before/after evidence:** Initial EN and KM assertions pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Non-hero bilingual custom rich-text variants remain governed by existing i18n markup.

### 12. Language switch did not reproject/refit

- **Changed files:** public-page.js
- **Migration/behavior:** Switch now updates content, lang, paired font, waits for font readiness, and refits.
- **Before/after evidence:** EN→KM→EN passes at five widths.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 13. Language-specific font/locale

- **Changed files:** public-page.js, renderer-core.js
- **Migration/behavior:** Explicit locale is passed to the shared model for visible content.
- **Before/after evidence:** English uses Latin family/lang=en; Khmer uses Khmer family/lang=km.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 14. Saved guest language

- **Changed files:** public-page.js
- **Migration/behavior:** Existing preference key retained and applied before final projection.
- **Before/after evidence:** Reload with saved Khmer preference passes.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 15. Shared renderer/model path

- **Changed files:** public-page.js and existing renderer adapters
- **Migration/behavior:** Public reprojection uses TypographyDocumentModel, FontRegistry and LayoutService.
- **Before/after evidence:** Bilingual and existing semantic parity suites pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Connected modal/public route parity remains part of official browser gate.

### 16. Mixed-language font loading

- **Changed files:** generate_typography_contract.py, typography-fonts.css
- **Migration/behavior:** Generated @font-face rules now include Latin and Khmer unicode ranges.
- **Before/after evidence:** FontTools/Brotli WOFF2 decode and bilingual computed-family tests pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Native Windows mixed-language font test not executed here.

### 17. Bilingual regression coverage

- **Changed files:** tests/v20_1_bilingual_public_runtime_test.py
- **Migration/behavior:** Covers initial EN/KM, switching, saved preference and five widths.
- **Before/after evidence:** Passes in Chromium 144.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Delayed/offline served-font cases remain covered by inherited tests; local served cases are sandbox-blocked.

### 18. 65th style data loss

- **Changed files:** typography-document-model.js, typography_document_model.py
- **Migration/behavior:** Creation rejects before mutation at the shared limit.
- **Before/after evidence:** 63→64 succeeds; 65th rejects atomically in Chromium and Python server rejects 65.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 19. Shared MAX_TEXT_STYLES

- **Changed files:** typography-contract.json and generated JS/Python
- **Migration/behavior:** Added maxTextStyles=64 and generated constants.
- **Before/after evidence:** Contract test confirms JS/Python value 64.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 20. UI limit behavior

- **Changed files:** typography-editor-v20.js
- **Migration/behavior:** Create/Duplicate are disabled with aria-disabled and live announcement at 64.
- **Before/after evidence:** Boundary runtime and source tests pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Full dialog-level undo/autosave at boundary remains in external complete gate.

### 21. Boundary lifecycle testing

- **Changed files:** tests/v20_1_semantic_boundary_runtime_test.py and server contract test
- **Migration/behavior:** Atomic browser/Python boundary assertions added.
- **Before/after evidence:** Passes.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Connected autosave/reload server boundary awaits unrestricted gate.

### 22. Missing FontTools/Brotli

- **Changed files:** requirements-test.txt, dependency_preflight.py
- **Migration/behavior:** Added bounded dependencies and minimal WOFF2 decode before browser suites.
- **Before/after evidence:** Dependency preflight passes.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Installer must install updated requirements-test.txt.

### 23. Stale font selector label

- **Changed files:** tests/v14_live_server_acceptance_test.py
- **Migration/behavior:** Selector now uses stable value noto-serif-khmer.
- **Before/after evidence:** Static audit passes.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Served acceptance test still requires unrestricted HTTP.

### 24. Stale gate markers

- **Changed files:** release_check.py, run_review_checks.py, inherited marker assertion
- **Migration/behavior:** Only authoritative V20.1 final markers remain in gate code.
- **Before/after evidence:** Contract test passes.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Individual inherited tests retain historical test-name markers, not release markers.

### 25. No skip-as-pass

- **Changed files:** run_review_checks.py, dependency_preflight.py
- **Migration/behavior:** Required browser skips are failures and missing dependencies/browser fail preflight.
- **Before/after evidence:** Source audit and preflight pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Sandbox prevents completing all served suites.

### 26. Modern hostile font silently repaired

- **Changed files:** typography_document_model.py
- **Migration/behavior:** Modern font values are validated strictly; exact legacy mappings remain explicit.
- **Before/after evidence:** Arial;position:fixed is rejected; exact Arial legacy stack migrates.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** None.

### 27. False contrast certainty

- **Changed files:** typography-layout-service.js
- **Migration/behavior:** Images, gradients, transparency, overlays and blend modes return contrast-undetermined.
- **Before/after evidence:** Chromium test confirms no false insufficient/precise ratio claim.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** No pixel-sampling compositor was introduced.

### 28. Thumbnail observer leaks

- **Changed files:** dashboard.js, final-polish.js, typography-layout-service.js
- **Migration/behavior:** Added controller registries and teardown.
- **Before/after evidence:** Churn test confirms disconnect calls.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Long-duration heap profiling is not included.

### 29. refresh mutated document/history

- **Changed files:** typography-editor-v20.js
- **Migration/behavior:** refresh is read-only; normalization remains at migration/command/server boundaries.
- **Before/after evidence:** State/history snapshot remains unchanged after refresh.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Ordinary command normalization remains scoped by existing command model.

### 30. Desktop duplicated controls/zoom

- **Changed files:** typography-system-v20.css, typography-editor-v20.js and inherited editor layout
- **Migration/behavior:** Common actions remain in one contextual bar; advanced controls stay inspector-side; existing persisted zoom/Fit behavior retained.
- **Before/after evidence:** 1440 inherited geometry and inline editor suites pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** A formal before/after canvas-area screenshot set was not produced in this sandbox.

### 31. Mobile toolbar/focus/handles

- **Changed files:** typography-system-v20.css, typography-editor-v20.js
- **Migration/behavior:** Desktop typography bar is hidden on mobile; closed surfaces become inert; handles are 9px with 45px hit region.
- **Before/after evidence:** 390×844 lifecycle/mobile test passes; canvas height 592px in test fixture.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** 360/430 visual review is covered by dashboard test, but full editor screenshots require external review.

### 32. Avoid unrelated restyle

- **Changed files:** Only typography/dashboard stabilization integration files changed
- **Migration/behavior:** No unrelated product feature phase was added.
- **Before/after evidence:** Inherited deterministic and key browser suites pass.
- **Tests:** See `V20_1_TEST_MATRIX.md` and the named evidence above.
- **Remaining limitation:** Native visual review remains pending.

### 33. Opaque colors were reported as contrast-undetermined

- **Changed files:** typography-layout-service.js
- **Migration/behavior:** Parsed hex/rgb colors now carry an explicit alpha channel; opaque solid backgrounds receive numeric contrast analysis while gradients and uncertain composites remain undetermined.
- **Before/after evidence:** The editor runtime reports `insufficient-contrast` for the low-contrast solid fixture and `contrast-undetermined` only for the gradient fixture.
- **Tests:** `v20_typography_editor_runtime_test.py`, `v20_1_semantic_boundary_runtime_test.py`.
- **Remaining limitation:** Complex compositing still intentionally avoids false precision.

### 34. Generated Khmer font faces used Latin unicode ranges

- **Changed files:** generate_typography_contract.py, typography-contract.json, generated typography contract/font assets, tests/v20_font_registry_loading_test.py
- **Migration/behavior:** Generation reads the contract's `scripts` array, emits four Khmer and four Latin unicode-range rules, and orders bundled paired faces before system fallbacks.
- **Before/after evidence:** Both bundled English and Khmer faces load for mixed text; offline/delayed font and Khmer shaping suites pass.
- **Tests:** `v19_font_loading_test.py`, `v20_font_registry_loading_test.py`, `v20_khmer_shaping_test.py`.
- **Remaining limitation:** The bundled catalog remains English/Khmer only.

### 35. Editor guest preview retained the wrong locale/font

- **Changed files:** app.js, generated editor/route bundles, tests/v20_1_semantic_boundary_runtime_test.py
- **Migration/behavior:** Preview EN/KM switching now reprojects visible content, updates guest/object language semantics and aria-pressed state, resolves the paired face, waits for font readiness, and refits through the shared typography services.
- **Before/after evidence:** EN uses `lang=en` and the Latin-first bundled face; Khmer uses `lang=km`, Khmer content, and the Khmer-first bundled face.
- **Tests:** `v20_1_semantic_boundary_runtime_test.py` plus interactive desktop preview verification.
- **Remaining limitation:** None.

### 36. Preview repair exceeded the editor route budget

- **Changed files:** app.js and generated bundles/manifests
- **Migration/behavior:** The implementation was compacted without raising the established 1,420,000-byte editor-route ceiling.
- **Before/after evidence:** The editor route is within its original cap and the performance suite passes.
- **Tests:** `v14_performance_budget_test.py`.
- **Remaining limitation:** The route remains close to its cap; future features should remove or split code before adding weight.

### 37. Timing-sensitive browser gate waits

- **Changed files:** tests/v14_static_server_test.py, tests/v14_live_layout_test.py, tests/v17_served_editor_test.py, tests/v19_font_loading_test.py
- **Migration/behavior:** Static mode waits for the actual offline editor-ready condition instead of global network-idle; layout failures include hydration diagnostics; served-editor diagnostics begin after authenticated hydration; the font harness ignores only its exact build placeholder/favicons and still fails missing font resources.
- **Before/after evidence:** The final low-contention native Windows sequence passes all 32 required browser suites without skips.
- **Tests:** The complete `release_check.py` gate.
- **Remaining limitation:** Windows client-aborted socket traces can still appear during forced browser teardown but do not represent failed requests.

### 38. Native Windows release verification

- **Changed files:** BUILD_INFO.json, V20_1_STABILIZATION_REPORT.md, V20_1_TEST_MATRIX.md
- **Migration/behavior:** Verification metadata records three retained native Windows logs and the explicit user waiver of Linux certification.
- **Before/after evidence:** Three consecutive uninterrupted low-contention runs each passed 43/43 deterministic and 32/32 required browser suites and emitted both final markers.
- **Tests:** `python release_check.py` with `EINVITE_FAST_WORKERS=1`.
- **Remaining limitation:** Native Linux was not run and is not claimed.

## Final markers

The gate prints these only after every required suite completes:

```text
EINVITATION_V20_1_ALL_REQUIRED_REVIEW_CHECKS_PASSED
EINVITATION_V20_1_RELEASE_CHECK_PASSED
```

Both markers were emitted by all three consecutive complete native Windows runs on the final packaged source. Native Linux certification was waived and is not claimed.
