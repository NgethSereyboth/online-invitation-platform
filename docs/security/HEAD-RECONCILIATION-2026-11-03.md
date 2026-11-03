# HEAD security reconciliation — 2026-11-03

**Source commit audited:** `ebb96d4` (the last commit that changes source or build output).
**Evidence HEAD:** `286080e` (this document and the round-8 evidence; it changes no `src/` file).

Fresh, fully paginated `gh api --paginate` results: **92 open Dependabot alerts (49 unique advisories)**, **118 open CodeQL alerts**, **0 open secret-scanning alerts**. All 118 CodeQL alerts carry `most_recent_instance.commit_sha = 50721ef`; none was produced from `ebb96d4`, so their line numbers are the old map. The hosted ledger is not cleared by a local edit; a push and rescan is owner-held. This file reconciles every Dependabot advisory against the committed pins and lists every non-generated CodeQL location.

**Audit performed at this evidence HEAD.** Each of the 49 advisory rows was recomputed from the API payload and compared with the committed pins: package, severity, `vulnerable_version_range` and the alert-number set all match, with no advisory missing and none extra (49 rows cover all 92 alerts exactly once). Each of the 32 non-generated CodeQL rows was re-checked against the committed tree: all 32 paths exist and every cited line number is still inside its file. Line numbers are the `50721ef` map and each disposition says so where the current line no longer contains the reported construct. `docs/requirements-test.txt` is a dev-only range file and is not a Dependabot manifest; production resolution is the exact pins in `docs/requirements-production.txt`.

## Dependabot per-advisory reconciliation

| Advisory | Package | Severity | Affected range | Committed pin / lock state | Disposition | Alert(s) |
|---|---|---|---|---|---|---|
| GHSA-9v8h-qqgm-4m35 | brotli | critical | >= 1.0.3, < 1.2.1 | docs/requirements-production.txt: 1.2.1; requirements.txt: `-r` include; tools/requirements.txt: 1.2.1 | resolved: outside affected range | 96,93,48 |
| GHSA-7pqw-9j4j-h8q3 | extract-zip | high | <= 2.0.1 | package-lock.json: absent | resolved: package absent | 6 |
| GHSA-jmr9-qjv8-65gv | extract-zip | high | <= 2.0.1 | package-lock.json: absent | resolved: package absent | 5 |
| GHSA-g3hv-75wg-m249 | minimatch | medium | < 11.0.1 | package-lock.json: absent | resolved: package absent | 98 |
| GHSA-22hg-r758-rrw9 | Pillow | high | >= 7.2.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 70,25 |
| GHSA-24rc-8hj2-v98c | pillow | medium | >= 9.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 84,39 |
| GHSA-254f-3936-288h | Pillow | medium | >= 5.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 74,29 |
| GHSA-27h8-gf7j-v5hc | Pillow | high | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 68,23 |
| GHSA-332p-7hrc-92wf | Pillow | critical | >= 2.0.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 80,35 |
| GHSA-3j72-p6qg-6xp7 | Pillow | high | < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 88,43 |
| GHSA-4558-3h8r-v8xp | Pillow | medium | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 64,19 |
| GHSA-462x-pgg6-55fp | pillow | medium | >= 8.2.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 56,13 |
| GHSA-4rm8-3hmm-39fg | pillow | medium | < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 87,42 |
| GHSA-4rr5-89j8-mwwm | pillow | medium | >= 11.3.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 79,34 |
| GHSA-58r4-6rv3-gfh8 | Pillow | high | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 62,9 |
| GHSA-5x8w-8jj5-q52h | pillow | critical | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 95,50 |
| GHSA-5xm2-6676-qcp9 | Pillow | high | >= 8.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 77,32 |
| GHSA-654x-cwwv-5j9c | Pillow | medium | >= 11.2.1, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 94,49 |
| GHSA-65qm-jvmh-6pqg | Pillow | high | >= 9.2.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 61,12 |
| GHSA-74r2-7ff9-mjj2 | Pillow | medium | >= 5.4.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 71,26 |
| GHSA-78g4-xqwv-q3g8 | pillow | high | >= 11.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 92,47 |
| GHSA-7mwm-ghpf-9vrm | Pillow | high | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 65,20 |
| GHSA-8g5g-8vmr-9782 | Pillow | critical | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 54,10 |
| GHSA-9v9v-9qvf-h2hj | Pillow | high | < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 90,45 |
| GHSA-c6hw-5grf-ff96 | Pillow | high | >= 8.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 55,14 |
| GHSA-cp9v-662q-vvx9 | pillow | high | >= 12.0.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 67,22 |
| GHSA-f2g6-542v-9j58 | Pillow | high | >= 5.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 78,33 |
| GHSA-fc9g-5qg7-mf45 | pillow | medium | >= 9.2.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 69,24 |
| GHSA-g4qv-2jxx-769h | Pillow | high | >= 11.0.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 89,44 |
| GHSA-g7cr-3p24-7wf7 | Pillow | high | >= 9.4.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 91,46 |
| GHSA-g842-9rc4-69pw | pillow | high | < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 83,38 |
| GHSA-gg2r-wvfm-q9rx | pillow | high | >= 4.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 76,31 |
| GHSA-j4m9-6w36-pw47 | pillow | high | >= 10.0.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 66,21 |
| GHSA-jg86-v3jv-hrpm | Pillow | high | >= 5.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 75,30 |
| GHSA-mrfp-p49p-3hf2 | Pillow | high | >= 5.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 86,41 |
| GHSA-p4wg-p73j-c528 | pillow | high | >= 5.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 57,16 |
| GHSA-p8hx-v2p6-rp84 | Pillow | medium | < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 82,37 |
| GHSA-pchr-8j38-3x4p | Pillow | high | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 58,11 |
| GHSA-q45j-58j2-45rg | Pillow | high | >= 5.3.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 59,15 |
| GHSA-rfgq-q3w2-pmv2 | Pillow | medium | >= 9.1.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 72,27 |
| GHSA-v9pv-5gc8-w2m6 | Pillow | critical | >= 11.0.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 85,40 |
| GHSA-vx6w-vv9f-6gvg | Pillow | medium | >= 2.3.0, <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 60,17 |
| GHSA-w889-685w-c8fh | Pillow | critical | >= 2.6.0, < 13.0.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 63,18 |
| GHSA-xgh8-jp6q-p5x8 | Pillow | medium | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 73,28 |
| GHSA-xvh5-g6gv-559v | Pillow | high | <= 12.3.0 | docs/requirements-production.txt: 13.0.0; requirements.txt: `-r` include | resolved: outside affected range | 81,36 |
| GHSA-6pq8-jhm2-2vcw | qs | medium | >= 6.7.0, <= 6.16.0 | package-lock.json: absent | resolved: package absent | 97 |
| GHSA-52f5-9888-hmc6 | tmp | low | <= 0.2.3 | package-lock.json: absent | resolved: package absent | 2 |
| GHSA-ph9p-34f9-6g65 | tmp | high | < 0.2.6 | package-lock.json: absent | resolved: package absent | 4 |
| GHSA-w5hq-g745-h8pq | uuid | medium | < 11.1.1 | package-lock.json: absent | resolved: package absent | 3 |

**Result:** 49 unique advisories, 92 alerts, **0 current vulnerable packages**. The 42 Python advisory rows resolve to Pillow 13.0.0 / Brotli 1.2.1; all seven npm advisories name packages absent from the committed lock.

## CodeQL non-generated reconciliation

**32 alerts** are outside generated mirrors; **86 alerts** are generated bundle/build mirrors and are handled by rebuilding from source. The generated set is exactly `src/python/build/*`, `src/python/bundle-*.js`, `src/js/bundle-*.js`, `src/js/editor-suite.js`, and the `src/python/{app,canvas-plus,editor-suite,workflow-creation-flow-v4}.js` runtime mirrors — each produced by `python3 build.py` from a `src/js` source and never hand-edited.

| Rule | Committed location | Alert(s) | Disposition |
|---|---|---|---|
| actions/missing-workflow-permissions | .github/workflows/lighthouse.yml:44 | 123 | fixed: explicit `permissions: contents: read` is present in both workflows |
| actions/missing-workflow-permissions | .github/workflows/security.yml:35 | 118 | fixed: explicit `permissions: contents: read` is present in both workflows |
| js/xss-through-dom | src/js/app.js:1198 | 35 | static creation markup only; no user-controlled value at the alert; line map is stale |
| js/xss-through-dom | src/js/canvas-plus.js:29 | 42 | same-origin DOM text (`h1`/`p` copy) inserted into the sign-in shell; no external input |
| js/xss-through-dom | src/js/workflow-creation-flow-v4.js:178 | 44 | static page-library labels read from trusted DOM; no external input |
| py/bad-tag-filter | tests/inline_editor_runtime_test.py:49 | 8 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/public_guest_feature_runtime_test.py:24 | 9 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/static_integrity_test.py:38 | 128 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/theme_launcher_runtime_test.py:17 | 11 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/v12_browser_stabilization_test.py:45 | 12 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/v13_browser_runtime_test.py:34 | 13 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/v20_1_bilingual_public_runtime_test.py:20 | 14 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/bad-tag-filter | tests/v20_1_dashboard_actions_runtime_test.py:12 | 15 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/clear-text-logging-sensitive-data | src/python/core/preflight.py:313 | 119 | fixed at call site via `redact_preflight_message`; static analyzer does not model the helper |
| py/clear-text-logging-sensitive-data | src/python/core/preflight.py:317 | 80 | fixed at call site via `redact_preflight_message`; static analyzer does not model the helper |
| py/http-response-splitting | src/python/server.py:3261 | 16 | fixed: all current header sinks use `safe_header_value` or `_safe_inline_filename`; old line map is stale |
| py/http-response-splitting | src/python/server.py:3348 | 124 | fixed: all current header sinks use `safe_header_value` or `_safe_inline_filename`; old line map is stale |
| py/http-response-splitting | src/python/server.py:3426 | 75 | fixed: all current header sinks use `safe_header_value` or `_safe_inline_filename`; old line map is stale |
| py/http-response-splitting | src/python/server.py:9500 | 137 | fixed: all current header sinks use `safe_header_value` or `_safe_inline_filename`; old line map is stale |
| py/http-response-splitting | src/python/server.py:9533 | 19 | fixed: all current header sinks use `safe_header_value` or `_safe_inline_filename`; old line map is stale |
| py/http-response-splitting | src/python/server.py:9537 | 138 | fixed: all current header sinks use `safe_header_value` or `_safe_inline_filename`; old line map is stale |
| py/incomplete-url-substring-sanitization | tests/v12_media_source_test.py:51 | 6 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/incomplete-url-substring-sanitization | tests/v27_3_5_ai_rich_text_browser_test.py:16 | 7 | test-only fixture/assertion; not shipped in server or browser bundle |
| py/path-injection | src/python/security_scanner_v54.py:373 | 74 | fixed/stale: scanner uses fixed `.bin` mkstemp; server paths are basenamed; old mapped line is Host parsing |
| py/path-injection | src/python/server.py:3674 | 3 | fixed/stale: scanner uses fixed `.bin` mkstemp; server paths are basenamed; old mapped line is Host parsing |
| py/path-injection | src/python/server.py:3675 | 4 | fixed/stale: scanner uses fixed `.bin` mkstemp; server paths are basenamed; old mapped line is Host parsing |
| py/path-injection | src/python/server.py:3676 | 5 | fixed/stale: scanner uses fixed `.bin` mkstemp; server paths are basenamed; old mapped line is Host parsing |
| py/polynomial-redos | src/python/rich_text_document_model.py:112 | 21 | fixed/stale: rich-text regexes replaced; old server lines no longer contain regexes |
| py/polynomial-redos | src/python/rich_text_document_model.py:387 | 22 | fixed/stale: rich-text regexes replaced; old server lines no longer contain regexes |
| py/polynomial-redos | src/python/server.py:3062 | 23 | fixed/stale: rich-text regexes replaced; old server lines no longer contain regexes |
| py/polynomial-redos | src/python/server.py:6366 | 24 | fixed/stale: rich-text regexes replaced; old server lines no longer contain regexes |
| py/polynomial-redos | src/python/server.py:6521 | 25 | fixed/stale: rich-text regexes replaced; old server lines no longer contain regexes |

The 86 generated-mirror alerts are deliberately not table rows: they are duplicate copies of reviewed source files and are regenerated by `python3 build.py all`. No suppression, ignore comment, or threshold change was used.
