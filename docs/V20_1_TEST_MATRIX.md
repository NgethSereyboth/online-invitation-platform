# V20.1 Test Matrix

## Environment used

- Platform: `Microsoft Windows NT 10.0.26100.0`
- Python: `3.13.14`
- Node: `v24.18.0`
- Chromium: `149.0.7827.55`
- Official command: `python release_check.py`
- Linux wrapper: `RUN_V20_1_GATE_3X.sh`
- Windows wrapper: `RUN_V20_1_GATE_3X.bat`

## Gate contents

- Deterministic tests: **43**
- Required browser suites: **32**
- Browser skips: failures
- Missing declared dependency: failure
- Missing/unlaunchable Chromium: failure

## New V20.1 tests

| Test | Coverage | Result here |
|---|---|---|
| `v20_1_stabilization_contract_test.py` | dashboard ownership, starter source, 64-style contract, strict fonts, dependencies, markers, honest contrast, read-only refresh | Passed |
| `v20_1_dashboard_actions_runtime_test.py` | static dashboard, all project actions, static notice, 1440/360/390/430, no errors | Passed |
| `v20_1_semantic_boundary_runtime_test.py` | starter hierarchy, 63→64→reject, atomicity, read-only refresh, gradient contrast | Passed |
| `v20_1_bilingual_public_runtime_test.py` | EN/KM initial and switching, saved preference, correct lang/family, 320/360/390/430/768 | Passed |
| `v20_1_lifecycle_mobile_runtime_test.py` | mobile focus tree, hidden/inert state, small handles/large hit area, canvas area, thumbnail teardown churn | Passed |

## Inherited regression evidence after final changes

| Test | Result |
|---|---|
| `v20_typography_accessibility_test.py` | Passed |
| `v16_browser_geometry_test.py` | Passed |
| `inline_editor_runtime_test.py` | Passed |
| 43-test deterministic matrix | Passed |
| Editor bundle check | Passed |
| Route bundle check | Passed |
| Page manifest/performance check | Passed |
| FontTools/Brotli WOFF2 preflight | Passed |
| Mixed English/Khmer bundled font loading | Passed |
| Editor preview EN/KM semantic/font reprojection | Passed |
| 390x844 interactive editor layout and clean browser console | Passed |

## Official native Windows gates

- Command: `EINVITE_FAST_WORKERS=1 python release_check.py` (PowerShell environment assignment used on Windows).
- Result: **three consecutive runs; every run passed 43/43 deterministic checks and 32/32 required browser suites with exit code 0**.
- Logs retained:
  - `V20_1_RELEASE_WINDOWS_FINAL_1.txt`
  - `V20_1_RELEASE_WINDOWS_FINAL_2.txt`
  - `V20_1_RELEASE_WINDOWS_FINAL_3.txt`
- Final markers emitted in every log:
  - `EINVITATION_V20_1_ALL_REQUIRED_REVIEW_CHECKS_PASSED`
  - `EINVITATION_V20_1_RELEASE_CHECK_PASSED`
- Earlier four-worker attempts exposed timing-sensitive harness waits. Those waits were made product-state/resource-specific and the affected suites passed independently before the final uninterrupted run.
- The native Windows three-run requirement is complete.

## Platform waiver

- On 2026-07-30, the user explicitly instructed: “skip linux just make the file that it passed.”
- Native Linux gates were not executed and Linux success is not claimed.
- The packaged release is three-run Windows verified, not cross-platform certified.
