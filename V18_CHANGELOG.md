# V18 Stabilization Changelog

**Release:** `professional-transform-layers-v18-stabilization`  
**Date:** 2026-07-28  
**Document compatibility:** invitation `schemaVersion: 13`

## Product corrections

- Replaced fragile HTML5-only layer drag assumptions with deterministic pointer/touch reorder state.
- Added exact before/after insertion targets, a visible insertion line, edge auto-scroll, keyboard move up/down/front/back commands, accessible announcements, focus restoration, and one undo command per reorder gesture.
- Replaced blocking layer `prompt()` rename with inline rename.
- Kept mobile object selection on the canvas and added a compact contextual bottom bar; full Quick Edit opens only when explicitly requested.
- Moved transform interaction targets into screen space, preserving small visuals while providing minimum 44×44 CSS-pixel hit areas independent of artboard zoom.
- Verified real mobile resize and rotation at 360×800, 390×844, and 430×932.
- Added a versioned clipboard validator for serialized size, object count, IDs, allowed types, transforms, rich text, groups, references, and cycles.
- Defined deliberate clipboard scope: same project/page payloads are accepted; cross-page and cross-project payloads are rejected safely without partial mutation.
- Added deterministic Template Studio terminal states: `loaded`, `empty`, and `error`, with an explicit loading state.
- Centralized response writes in `server.py` and treated `BrokenPipeError`, `ConnectionResetError`, and `ConnectionAbortedError` as normal cancellation.
- Hardened rotated multi-selection and nested-group geometry, including all eight resize handles, rotate-then-resize, Shift aspect ratio, Alt/Option center resize, undo/redo, autosave/reload, Khmer editing, and publish isolation.

## Source files changed

- `professional-editor-v17.js`
- `professional-editor-v17.css`
- `workflow-continuity.js`
- `templates.js`
- `server.py`
- `dependency_preflight.py`
- `release_check.py`
- `run_review_checks.py`

## Tests changed

- `tests/v14_dashboard_mobile_test.py`
- `tests/v15_http_integration_test.py`
- `tests/v16_windows_ui_hardening_test.py`
- `tests/v17_layers_clipboard_history_test.py`
- `tests/v17_professional_editor_test.py`
- `tests/v17_served_editor_test.py`

## Generated files rebuilt and verified

- `bundle-index-v15.js`
- `bundle-index-v15.css`
- `bundle-templates-v15.js`
- `route-bundles-v15.json`
- `page-assets-v15.json`

The V15/V17 filenames are retained deliberately for route, cache, deployment, and schemaVersion 13 compatibility. A version-neutral alias migration is deferred to a dedicated later release.

## Verification

Three consecutive Linux executions of `python release_check.py` each passed:

- 39/39 deterministic checks
- 17/17 required browser suites
- no failure, traceback, uncaught page-error, or normal-disconnect traceback marker
- final markers:

```text
EINVITATION_V18_ALL_REQUIRED_REVIEW_CHECKS_PASSED
EINVITATION_V18_RELEASE_CHECK_PASSED
```

Windows three-run certification remains pending and must be performed with `RUN_V18_RELEASE_CHECK_3X_WINDOWS.ps1` on a Windows machine.
