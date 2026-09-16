# V23.6.3 Focused Verification Record

## Passed build and dependency gates

- Typography contract generation.
- Rich-text contract generation.
- Deterministic editor bundle build and source-integrity check.
- Sixteen deterministic route bundle builds and source-integrity check.
- Page asset manifest build and budget check.
- Initial editor route: 1,419,964 bytes against a 1,420,000-byte budget.
- Python compilation.
- All top-level JavaScript syntax checks.
- Pillow, qrcode, Argon2, cryptography, Playwright, FontTools, Brotli, WOFF2 decode, and Chromium launch preflight.

## Passed V23.6 gates

- `v23_6_photo_style_library_contract_test.py`
- `v23_6_photo_style_library_browser_test.py`
- `v23_6_photo_style_library_mobile_test.py`
- `v23_6_photo_style_library_performance_test.py`

Latest focused performance sample:

- Library open: approximately 111.9 ms.
- Seed 36 custom styles: approximately 379.6 ms.
- Search/filter interaction: approximately 76.9 ms.
- Registry conflicts: zero.

## Passed cumulative V23 editor gates

- V23.5 photo workflow contract/browser/performance.
- V23.4 asset workflow contract/browser/performance.
- V23.3 style history contract/browser/performance.
- V23.2 navigation/history contract/browser/performance.
- V23.1 professional workflow contract/browser.
- V23 command registry, lazy-loader, browser, and performance checks.

## Passed V22 compatibility and performance gates

- V22.2 page architecture contract.
- V22.2 pointer reorder, page manager, mobile, refinement, and 120-page performance checks.
- V22.1 WebGL backend, texture cache, GPU projection, adaptive quality, editor integration, fallback, real runtime, worker rendering, and interaction-performance checks.

## Passed product-integrity gates

- All 58 deterministic scripts in `FAST_CHECKS`, executed in isolated serial batches.
- Build integrity and static integrity.
- Route performance budget.
- Security regression and security maintenance.
- Private-access headers.
- Workflow continuity.
- Final workflow audit V7.

## Environment-qualified items

- One uninterrupted all-generation runner did not finish inside the available container execution window; the same deterministic test list passed as isolated serial executions.
- Long browser groups were also split when the container execution window ended; their individual tests passed when rerun.
- Three native Windows runs, three native Linux runs, and physical-GPU benchmarking remain pending.
