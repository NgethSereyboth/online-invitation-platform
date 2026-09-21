# eInvite — test suite repair context

## What this is
A Python stdlib backend + vanilla JS frontend. The test suite lives in `tests/`
and is invoked by `src/python/run_review_checks.py`.

## The problem
Commit `5ed591e` reorganized the repo:
- JS moved to `src/js/`
- CSS moved to `src/css/`
- HTML moved to `src/html/`
- Backend Python moved to `src/python/`
- Build scripts moved to `src/python/build/`
- Contract JSONs moved to `docs/`
- Vendor libs moved to `vendor/`

The test suite was never updated. Tests still do `(ROOT / 'foo.js').read_text()`,
which looks at the repo root. The files are now under `src/`.

`FILE_MANIFEST.txt` lists every file in the repo with its current path.
Use it to find where each referenced file actually lives.

## Critical rules
1. **`has()` calls do NOT get prefixes.** `tests/route_bundle_sources.py`
   defines `has(page, name)` which checks membership in
   `docs/route-bundle-sources-v15.json`. That manifest uses BARE filenames
   (e.g. `workflow-pro-editor-v6.js`, not `src/js/...`). Do not add prefixes
   to `has()` arguments.

2. **`(ROOT / 'name.ext').read_text()` DOES get prefixes.** This hits the
   filesystem. Prefix by extension:
   - `.js` → `src/js/`
   - `.css` → `src/css/` (or `src/css/organized/` — check the manifest)
   - `.html` → `src/html/`
   - `.py` → `src/python/` (or `src/python/build/` — check the manifest)
   - `.json` contract files → `docs/`

3. **`subprocess.run(['python', 'server.py'])`** — a forwarder now exists
   at the repo root (`server.py`) that delegates to `src/python/server.py`.
   These tests do not need editing.

4. **`(ROOT / 'server.py').read_text()`** — tests that READ server.py as
   text to assert on its contents. These DO need editing. Change to
   `(ROOT / 'src' / 'python' / 'server.py')`. The root `server.py` is
   only an 8-line forwarder.

5. **Do not change assertions.** Only change paths. If a test asserts
   `'foo' in source`, and `source` was loaded from the wrong file, fix
   the path — do not weaken the assertion.

6. **Report failures, don't skip them.** If a file genuinely does not exist
   anywhere, say so. Do not comment out the test.