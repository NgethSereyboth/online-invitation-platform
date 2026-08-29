# V27.3.5 Certification Status

| Area | Status | Evidence / boundary |
|---|---|---|
| Immutable baseline hash | **PASS** | `ee37a64bc02c56b84e467c36d4370a46d5854c51e18198718cc556990709f052` |
| Safe ZIP path validation | **PASS** | No absolute, drive-qualified, traversal, or escaping paths accepted. |
| Schema | **PASS** | Version 14 unchanged; no document migration introduced. |
| README preservation | **PASS** | SHA-256 `f3c158d37f1ab2367a4bd0565c230535369596431709cbbd3cb234c324633330` matches the baseline. |
| Focused Release A contracts | **PASS** | Required AI transaction, rich text, target/revision, layout, accessibility, backend, HUD, and release-evidence tests passed. |
| Deterministic contracts | **PASS — segmented** | 76/76 passed in isolated execution. Uninterrupted runner marker not claimed. |
| Browser contracts | **PARTIAL** | 97/104 passed; 7 blocked by managed loopback policy before assertions; 0 loaded-page assertion failures. |
| Editor route budget | **PASS** | 1,393,850 / 1,420,000 bytes; 26,150 bytes headroom. |
| CSP/security posture | **PASS in exercised contracts** | No CSP weakening or inline assistant style injection added; provider keys remain server-side. |
| Final full-review marker | **PENDING** | `EINVITATION_V27_3_5_ALL_REQUIRED_REVIEW_CHECKS_PASSED` absent. |
| Final release marker | **PENDING** | `EINVITATION_V27_3_5_RELEASE_CHECK_PASSED` absent. |
| Windows 3× marker | **PENDING** | `EINVITATION_V27_3_5_WINDOWS_3X_RELEASE_CHECK_PASSED` absent. |
| Linux 3× certification | **PENDING** | Script labels updated; no complete native run claimed. |
| Release B authorization | **NOT STARTED** | Must begin only after the exact V27.3.5 candidate completes certification and the user replies `continue`. |

## Certification command

On a supported unrestricted Windows environment with all dependencies installed, run:

```powershell
.\RUN_V27_3_5_RELEASE_CHECK_3X_WINDOWS.ps1
```

A valid Windows certification requires the exact final marker:

```text
EINVITATION_V27_3_5_WINDOWS_3X_RELEASE_CHECK_PASSED
```
