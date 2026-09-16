# V18 Stabilization Release Report

**Build:** `professional-transform-layers-v18-stabilization`  
**Date:** 2026-07-28  
**Input baseline:** `e-invitation-platform-professional-transform-layers-v17(1).zip`  
**Input SHA-256:** `76e4e005285dfc7eee995b0eb7997cb47b17897423f2aa9755b4fcc2c680eed0`  
**Document compatibility:** invitation `schemaVersion: 13`

## Release status

V18 is complete as a Linux-verified stabilization artifact. Three consecutive complete Linux release-gate executions passed on the identical final source. Windows three-run certification is not claimed because this build environment is Linux; the included PowerShell runner preserves the required Windows logs and markers.

No V19+ masks, vector paths, effects stacks, collaboration phase, or other large product feature was started.

## Preserved workflows

The V17 baseline was upgraded in place. V18 preserves invitation creation and editing, Khmer/English text, Khmer date behavior, media and uploads, uploaded/YouTube/SoundCloud audio, optional RSVP, guest links and QR codes, publishing and public snapshots, analytics, check-in, privacy, account security, local/server operation, themes, and responsive desktop/mobile workflows.

## Corrected defects

1. **Layer reorder and accessibility**
   - Deterministic pointer/touch source state replaces fragile data-transfer-type dependence.
   - Exact before/after targets, visible insertion line, edge auto-scroll, nested-group/search behavior, keyboard move up/down/front/back, accessible announcements, focus restoration, inline rename, and undo/redo are covered.
   - One reorder gesture produces one history command.

2. **Mobile canvas-preserving selection**
   - Selecting an object does not automatically open a full-screen inspector.
   - A compact contextual bottom bar appears while the canvas remains visible.
   - Full property editing opens only through an explicit user action.

3. **Mobile transform targets**
   - Transform handles use screen-space interaction geometry with minimum 44×44 CSS-pixel targets independent of canvas zoom.
   - Real pointer resize and rotation are verified at 360×800, 390×844, and 430×932.

4. **Clipboard validation and scope**
   - Version 18 payload validation covers serialized bytes, object count, IDs, allowed object types, numeric transforms, rich text, groups, dangling references, and cycles.
   - Old-version, malformed, oversized, and cyclic payloads are rejected safely with no exception or partial document mutation.
   - Cross-page and cross-project paste behavior is deliberate and rejected rather than sharing one origin-global payload silently.

5. **Template loading states**
   - Template Studio exposes explicit loading, loaded, empty, and error states.
   - Browser tests wait for a defined terminal state rather than asserting immediately after `body` appears.

6. **Normal client cancellation**
   - JSON response writes are centralized.
   - `BrokenPipeError`, `ConnectionResetError`, and `ConnectionAbortedError` are treated as normal client cancellation after response start.
   - Integration tests assert all three paths without an uncaught traceback.

7. **Geometry hardening**
   - Differently rotated multi-selections and nested groups use coherent transform geometry.
   - Tests cover all eight group handles, rotate followed by resize, Shift aspect ratio, Alt/Option center resize, undo, redo, autosave, reload, Khmer text persistence, and publish-snapshot isolation.

## Files changed

See `V18_CHANGELOG.md` for the source, test, and generated-bundle list.

## Compatibility filenames

`professional-editor-v17.js/css` and generated `bundle-*-v15.js/css` filenames remain intentionally unchanged. Renaming them during stabilization would require an atomic route, manifest, deployment, and cache migration. The follow-up plan is to introduce version-neutral aliases, update every route atomically, retain one-release compatibility fallbacks, verify deployment, and only then remove the legacy names.

## Exact release command

Executed from the project root for each run:

```text
python release_check.py
```

The logging wrapper used `python -u release_check.py` only to flush console output immediately into the retained files. It runs the same `release_check.py` entry point and does not alter test selection or behavior.

The command performs:

1. deterministic editor-bundle regeneration;
2. editor source/bundle integrity verification;
3. deterministic route-bundle regeneration;
4. route-bundle verification;
5. page-asset manifest regeneration;
6. manifest/performance-budget verification;
7. Python compilation;
8. syntax checks for 90 top-level JavaScript files;
9. dependency and Chromium launch preflight;
10. 39 deterministic checks and 17 required live-browser suites.

## Three consecutive Linux results

| Run | Log | Exit | Deterministic | Browser | Result |
|---:|---|---:|---:|---:|---|
| 1 | `V18_RELEASE_LINUX_FINAL_1.txt` | 0 | 39/39 | 17/17 | PASS |
| 2 | `V18_RELEASE_LINUX_FINAL_2.txt` | 0 | 39/39 | 17/17 | PASS |
| 3 | `V18_RELEASE_LINUX_FINAL_3.txt` | 0 | 39/39 | 17/17 | PASS |

Log SHA-256 values:

```text
7846cf7e420d8d2d43dbf853fa0fa00c90dd1293add6a1bfd4e3a8f2b0a94e23  V18_RELEASE_LINUX_FINAL_1.txt
0b7bea483cfd6597dd7d29bea1ea2de175788ea521c0abd37fb1cd40b615bef6  V18_RELEASE_LINUX_FINAL_2.txt
ee274b6c9a8b65373ff0373a0b38986ef4a25717413dc81c25020118361601a8  V18_RELEASE_LINUX_FINAL_3.txt
```

Each log contains these unedited terminal markers:

```text
EINVITATION_V18_ALL_REQUIRED_REVIEW_CHECKS_PASSED

EINVITATION_V18_RELEASE_CHECK_PASSED
```

Automated scans of all three logs found no `FAIL`, `FAILED`, `ERROR`, `Traceback`, uncaught page-error, or normal-disconnect traceback marker.

## Windows validation

Windows certification remains **pending external execution**. Run from PowerShell in the extracted project directory:

```text
powershell -ExecutionPolicy Bypass -File .\RUN_V18_RELEASE_CHECK_3X_WINDOWS.ps1
```

The script runs `python release_check.py` three consecutive times, saves each unedited Windows log, checks both V18 success markers, and prints:

```text
EINVITATION_V18_WINDOWS_3X_RELEASE_CHECK_PASSED
```

Do not mark Windows validation complete unless that marker is produced on the target Windows machine.

## Production-only external requirements

Local/server review works without production credentials. A real public deployment still needs environment-specific secrets and services such as production TLS/domain configuration, durable database/storage configuration, SMTP or transactional email where enabled, object storage/CDN credentials if using external media storage, monitoring/backup destinations, and any third-party authentication or media-provider credentials selected by the operator. No fake production credentials are included.
