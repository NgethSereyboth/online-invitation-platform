# V0.52 Final V17 Reliability Correction Report

## Scope

Baseline: `e-invitation-platform-intelligent-event-ecosystem-v0.52-release-gate-reliability.zip`. Public version remains **0.52**. Invitation schema remains **27**. README is unchanged. No frontend bundle budget was raised and no onboarding/product feature was removed.

## Proven root causes from unrestricted evidence and source inspection

1. **Invalid off-screen nested resize gesture.** At the fixed 1440×900 test viewport, the nested selection's southeast resize handle can land around Y=955–982 after rotation. Playwright therefore begins the pointer gesture outside the viewport, so the application receives no resize pointer-down, produces no geometry change, and correctly creates no resize command/history entry. The test now uses the existing visible V24 **Selection** canvas-navigation control (`[data-v24-zoom="selection"]`) to zoom/center the selected nested group before both rotation and resize. It waits for zoom, canvas scroll, selection overlay and handle geometry to settle across multiple animation frames, then verifies both the handle center and planned pointer destination are within a safe viewport inset before mouse-down. No viewport enlargement, coordinate clamping, direct model mutation or force-click is used.

2. **Pre-rotate history baseline could be sampled before prior history state fully quiesced.** The editor has a 260 ms deferred history capture path for ordinary saves. A later valid V17 professional gesture itself is synchronous and source inspection shows exactly one path: pointer-up → `endInteraction()` → `commitFrames()` → professional `commit()` → `EInviteEditorBridge.transact()` → one `pushHistory()`. The test now refuses to establish `rotate_before` until complete nested object geometry, group graph, selection, undo depth/cursor, redo depth, professional command sequence/last command and the current-history/document fingerprint remain unchanged for **420 ms**. Every probe itself spans two animation frames plus a task turn. This catches a late prior setup/save history entry without weakening the one-gesture/one-history-entry contract.

3. **Gesture diagnostics previously did not distinguish invalid pointer geometry from product history behavior.** Failure diagnostics now include viewport and visualViewport, canvas zoom/scroll, canvas/stage/selection/rotate/resize rectangles, pointer start/destination/modifiers/in-bounds status, pre/post object geometry and group graph, selection IDs, undo/redo state, professional sequence/last command, save/server state and publish state. Undo/Redo still require exact pre/post geometry/group/selection/history equality.

## Product history conclusion

No production V17 history/pointer code was changed. Source inspection confirms one valid V17 rotate/resize gesture commits one professional command and one editor transaction/history entry. The independent failure evidence is consistent with invalid off-screen input plus a stale pre-gesture history baseline, not a duplicate product history push.

## Files changed in this final pass

- `tests/v17_served_editor_test.py` — final V17 reachability, baseline-quiescence and diagnostics correction.
- `BUILD_INFO.json` — truthful independent baseline/current validation evidence only.
- `V0_52_RELEASE_FILE_HASHES.sha256` — regenerated final integrity evidence.
- `V0_52_FINAL_V17_RELIABILITY_REPORT.md` — this report.

No canonical editor/public JavaScript, CSS, schema, server, README, onboarding, autosave, publishing or history implementation changed in this pass.

## Bundle discipline

- Canonical editor bundle: **1,413,344 / 1,420,000 bytes** — **6,656 bytes headroom**.
- Complete editor startup assets: **1,417,331 / 1,420,000 bytes** — **2,669 bytes headroom**.
- Public invitation route: **233,585 / 260,000 bytes** — **26,415 bytes headroom**.

No derived frontend bundle was regenerated because no canonical frontend source changed.

## Local served-browser limitation

The system Chromium in this execution host is enterprise-managed and rejects loopback HTTP navigation at the initial `page.goto()` with `net::ERR_BLOCKED_BY_ADMINISTRATOR`, before application JavaScript executes. A Playwright-managed Chromium binary is not installed; an attempted official browser download failed because outbound DNS is unavailable. Therefore this host cannot truthfully certify the required V17 10/10 or 204/204 served-browser target. The real served workflow remains intact and unmocked for the unrestricted auditor.

## Validation evidence for this pass

### Independent unrestricted input baseline

- Deterministic: **90/90 passed**.
- Browser: **113/114 passed**.
- Total: **203/204 passed**, exit **1**.
- Autosave reliability: **3/3 passed**.
- Mobile inline editor reliability: **10/10 passed**.
- V17 served editor reliability: **1/10 passed**; this was the only registered failure.

### Local validation after the V17 correction

- `python -m compileall -q .`: passed; **246 Python sources** are present.
- Top-level `node --check`: **172/172 passed**.
- `python dependency_preflight.py`: passed, including WOFF2 decode and Chromium launch.
- `python build_editor_bundle.py --check`: passed.
- `python build_route_bundles.py --check`: passed.
- `python build_page_manifests.py --check`: passed.
- `python tests/v27_3_5_release_evidence_test.py`: passed after the final evidence freeze.
- Exact full command `python run_review_checks.py --continue-on-failure --fast-workers 8` was attempted. The execution tool stopped the long-running process after **34/34 completed deterministic entries had reported PASS**; no assertion failure had been reported, and the browser phase had not yet started. A complete local exit code therefore does not exist.
- Six explicitly completed local V17 served attempts all failed before application execution at the first `page.goto()` with managed Chromium `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The official Playwright Chromium binary is not installed in this host and an attempted download failed because outbound DNS is unavailable. These attempts cannot be counted as V17 product passes or failures.

Because this execution host cannot run the unrestricted served-browser workflow, this report does **not** claim the required final 10/10 V17 or 204/204 release certification. The corrected real served test is preserved for the independent unrestricted rerun.
