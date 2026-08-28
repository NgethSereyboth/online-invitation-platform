# V19 Advanced Typography Release Report

## Release identity

- Product: **E-invitation-website**
- Release: **V19 Advanced Typography**
- Date: **2026-07-28**
- Input baseline: `e-invitation-platform-stabilized-v18.zip`
- Baseline SHA-256: `969d6bbee9e48a9520a5c094e7861e09d4495ac3b478be72e651d5f9b7106276`
- Invitation document compatibility: **`schemaVersion: 13`**

V19 was developed directly from the finalized V18 stabilization artifact. The V18 ZIP was not overwritten, the product was not restarted or replaced with a mockup, and no unrelated masks, vector paths, effects-stack, or collaboration phase was introduced.

## Implemented scope

### Non-destructive auto-fit

Text objects can use automatic font fitting. The editor stores a maximum font size independently from the currently rendered font size and uses a bounded binary search against the actual rendered text box. This allows long text to shrink safely while permitting shorter text or a larger box to grow back toward the selected maximum.

Persistent fields:

- `textAutoFit`
- `textAutoFitMax`
- `textMinFontSize`

Auto-fit is recalculated after text edits, relevant inspector changes, object resizing, professional transform commits, state application, and viewport changes. A manual **Fit now** command is also available.

### Advanced wrapping and columns

Text objects now support:

- normal wrapping;
- balanced wrapping;
- pretty wrapping;
- one, two, or three columns;
- configurable column gaps;
- justified alignment.

Persistent fields:

- `textWrap`
- `textColumns`
- `textColumnGap`

### Khmer-aware font fallback

When Khmer Unicode characters are detected, the editor and published renderer append Khmer-capable fallback families while preserving the selected primary typeface. Existing English-only text and invitations without V19 fields remain unchanged.

### Full renderer and persistence path

The V19 fields are normalized by `editor-schema-v13.js`, rendered in the editor, included in generated bundles, and interpreted by `renderer-core.js`. Browser coverage verifies persistence through undo, redo, autosave, reload, preview, and immutable published snapshots.

### Layer focus stabilization

A full-gate intermittent issue revealed that a delayed Layers-panel rerender could detach a focused row between `focus()` and an Alt+Arrow command. The global canvas keyboard owner could then interpret the command as an object nudge. V19 now:

- restores a replacement layer row synchronously after rendering;
- retries focus restoration across later rerenders;
- routes layer movement and F2 rename through the remembered layer identity only during the detached-focus window;
- clears remembered identity on deliberate pointer or focus navigation.

The affected layer suite passed eight consecutive stress repetitions before the final release sequence.

## Tests added or expanded

- `tests/v19_typography_model_test.py`
  - schema normalization and clamping;
  - optional-field compatibility;
  - renderer layout contract;
  - Khmer fallback behavior;
  - safe non-browser rich-text degradation.
- `tests/v19_typography_runtime_test.py`
  - real Chromium inspector interaction;
  - Khmer content and fallback fonts;
  - auto-fit and manual fitting;
  - box resize recalculation;
  - justify, wrapping, columns, and gap;
  - undo/redo;
  - published renderer persistence;
  - mobile inspector reachability at 390×844.
- `tests/v17_layers_clipboard_history_test.py`
  - delayed-rerender focus stability for keyboard movement and inline rename.

The official gate now runs **40 deterministic checks** and **18 required browser suites**.

## Exact release command

The release was executed from the project root with the environment interpreter:

```text
/opt/pyvenv/bin/python release_check.py
```

The portable command for a configured machine is:

```text
python release_check.py
```

## Consecutive Linux results

Three consecutive runs were performed on the identical final source and generated bundles.

| Run | Deterministic | Browser | Exit | Log |
|---|---:|---:|---:|---|
| 1 | 40/40 | 18/18 | 0 | `V19_RELEASE_LINUX_FINAL_1.txt` |
| 2 | 40/40 | 18/18 | 0 | `V19_RELEASE_LINUX_FINAL_2.txt` |
| 3 | 40/40 | 18/18 | 0 | `V19_RELEASE_LINUX_FINAL_3.txt` |

Every retained log ends with the unedited markers:

```text
EINVITATION_V19_ALL_REQUIRED_REVIEW_CHECKS_PASSED

EINVITATION_V19_RELEASE_CHECK_PASSED
```

No retained final log contains `REVIEW_CHECK_FAILED`, `RELEASE_CHECK_FAILED`, an uncaught page-error marker, or a normal client-disconnect server traceback.

## Generated bundle compatibility

The generated editor and route bundles were rebuilt and verified during every release run. V15/V17 filenames remain deliberately unchanged because current HTML routes, browser caches, deployment tooling, and historical reports reference them. A future migration must update manifests and all routes atomically and provide a compatibility window.

## Windows status

Windows certification is **not claimed** from this Linux environment. Extract the V19 ZIP on the target Windows computer and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V19_RELEASE_CHECK_3X_WINDOWS.ps1
```

Windows acceptance is reached only when the script prints:

```text
EINVITATION_V19_WINDOWS_3X_RELEASE_CHECK_PASSED
```

If any Windows run fails, correct the smallest reproducible defect, add regression coverage, rebuild bundles, and restart all three Windows runs from zero.
