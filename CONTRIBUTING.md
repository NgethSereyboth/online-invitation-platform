# Contributing

This repository ships a Python server (`src/python/server.py`) and a
statically-served frontend whose JavaScript and CSS are **generated** from
`src/js/` and `src/css/` into per-route bundles. Almost every mistake made here
comes from editing a generated file or forgetting to rebuild, so start with the
rules below.

## 1. Set up

```bash
# Python 3.12+
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # -> docs/requirements-production.txt

# Node (only needed for Lighthouse perf runs and the Playwright-based tests)
nvm use                                  # reads .nvmrc
```

Optional environment variables live in `.env.example`; copy it to `.env` and
fill in what you need. Never commit a filled `.env`.

## 2. Build

`build.py` at the repo root is the only supported entry point.

```bash
python3 build.py all              # regenerate everything (dependency order)
python3 build.py editor           # editor-suite.{js,css}
python3 build.py bundles          # bundle-*.{js,css} for the 16 routes
python3 build.py manifests        # page-assets.json (server + docs)
python3 build.py all --check      # verify, write nothing; non-zero if stale
```

`make build` and `make check` wrap the first and last of those.

**After any edit under `src/js/` or `src/css/` you must run:**

```bash
python3 build.py bundles
python3 build.py bundles --check    # must print ROUTE_BUNDLE_CHECK_PASSED
```

The repo-root `build_editor_bundle.py`, `build_route_bundles.py` and
`build_page_manifests.py` are **deprecated shims** kept so old callers
(tests, `src/python/release_check.py`, CI) keep working. They print a
deprecation notice. Do not add new callers.

### One-command gates (2026-10-21)

`tools/run-gates.py` reproduces the full gate matrix — build, bundles, smoke,
pytest, LHCI and the canvas acceptance harness — in one serial run, with log
directory and lock file, on Linux (no PowerShell renderer pin needed):

```bash
.venv/bin/python tools/run-gates.py --phase all      # everything (heavy)
.venv/bin/python tools/run-gates.py --skip-heavy     # build/bundles/smoke only
```

Use the repo `.venv/bin/python` (system python3 lacks Playwright and would
exclude the browser test modules); the runner exports `PYTHONIOENCODING=utf-8`
itself and never edits the frozen canvas tools or budgets. See `tools/README.md`.

## 3. Test

```bash
python3 -m pytest tests/                       # full suite
python3 tests/v55_route_weight_budget_test.py  # route weight budgets
python3 build.py all --check                   # generated-artifact integrity
make serve                                     # static preview on :8124
make dev                                       # real server
```

Some tests need a browser. They check `EINVITE_REQUIRE_BROWSER` and print
`*_SKIPPED` when Chromium is unavailable; a skip is not a pass. Set
`EINVITE_REQUIRE_BROWSER=1` in CI so a missing browser fails the run.

## 4. Hard rules

1. **Never edit a generated file by hand.** That means:
   - `src/css/bundle-*.css`, `src/js/bundle-*.js`
   - `src/css/editor-suite.{js,css}`, `src/js/editor-suite.js`
   - everything under `src/python/` that mirrors a `src/js/` or `src/css/`
     source (the server's `ROOT` is `src/python/`, so the mirrors are what is
     actually served).
2. **Source of truth is `src/js/`, `src/css/`, `src/html/`.** Edit there, then
   rebuild.
3. **No new `!important` declarations.** The existing ones are legacy; adding
   more makes the cascade unauditable.
4. **Do not fabricate Khmer.** Every Khmer string must already exist in
   `docs/i18n/TRANSLATIONS.csv` or an accepted Khmer review document. Latin text
   that happens to sit in a Khmer context still needs `lang="km"` when it is
   Khmer.
5. **Keep the route budgets honest.** If a change pushes a page over a budget in
   `BUDGETS` (`src/python/build/build_page_manifests.py`), fix the page or raise
   the budget *deliberately* and say so in the commit. Never raise a budget just
   to make a gate green.
6. **No version suffixes in source file names.** A module or stylesheet under
   `src/js/` or `src/css/` must not be named `something-v22.js` or
   `something-v0_52.css`. A version in a *file name* records when the file was
   written, which nobody can act on later; the same number in *data* (a schema
   version, a migration number, a plugin manifest field, a protocol route
   segment) is a contract and belongs where it is. `tests/version_free_source_names_test.py`
   enforces this, and `tests/versioned_name_allowlist.json` carries the short
   list of legacy names still awaiting a human-chosen replacement. Generated
   bundles (`bundle-*.{js,css}`) are named by the generators and are not
   hand-named.
7. **No branching ceremony in this repo:** work happens on `main`.

## 5. Directory structure

```
build.py                     the build entry point
Makefile, .nvmrc             developer entry points
src/
  js/                        JavaScript sources (grouped by concern)
    core/                    i18n, theme, safe-dom — loaded on every page
    editor/                  editor subsystems
    pages/                   per-page controllers
    components/              shared UI primitives
  css/
    tokens.css               design tokens — the single source of truth
    app-shell.css        shell, topbar, rail, card primitives
    bundle-*.css         GENERATED per-route bundles
    editor/  pages/  components/  organized/
  html/                      page sources
  python/
    server.py                the application server (ROOT = src/python/)
    build/                   the generators invoked by build.py
tests/                       Python + browser test suite
docs/                        design history, i18n sources, audits, budgets
scripts/                     one-off maintenance and policy checks
```

## 6. Where does new code go?

```
Is it a design value (colour, size, radius, motion, shadow)?
  -> src/css/tokens.css. Add a token; do not hard-code the value.

Is it styling for one page?
  -> src/css/pages/<page>.css, and add it to that page's `styles` list in
     docs/route-bundle-sources.json, then `python3 build.py bundles`.

Is it styling shared by several pages?
  -> the nearest existing shared sheet (src/css/app-shell.css for shell and
     card primitives, src/css/components/ for smaller primitives), then add it
     to each affected route's `styles` list.

Is it JavaScript for one page?
  -> src/js/pages/<page>/<concern>.js and add it to that page's `scripts` list.

Is it JavaScript used by several pages?
  -> src/js/components/ (UI) or src/js/core/ (load-bearing, always loaded).

Is it a build/verification concern?
  -> a generator under src/python/build/ registered in build.py's STEPS, or a
     policy script under scripts/, or a test under tests/.

Does it change a route's asset set or byte weight?
  -> update docs/route-bundle-sources.json, run `python3 build.py all`, and
     check the page against BUDGETS before you commit.
```

## 7. Reports

Design and optimisation passes write to `docs/reviews/`. If your change is a
fidelity, accessibility, performance or consolidation pass, add a report there
with the before/after numbers that justify it — a claim without a measured pair
is not evidence.
