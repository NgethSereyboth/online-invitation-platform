# `tools/` — the measurement harness

Every script that produced a number in `docs/reviews/*.md` used to live in
`/tmp`. That made the reports reproducible only until the machine restarted, and
it made an absolute path to one developer's checkout part of the evidence. This
directory is that harness, in the repository, with no machine-specific paths.

## Getting started

```bash
npm install                              # puppeteer-core + @lhci/cli (root package.json)
pip install -r tools/requirements.txt    # fonttools + brotli (fonts only)
make reproduce                           # everything, against a gzip server it starts itself
```

Nothing else is required. Python scripts are standard-library-only except
`subset-fonts.py`.

### Gate runner (NW-5.3, 2026-10-21)

| file | what it does |
| --- | --- |
| `run-gates.py` | one-command reproduction of the Phase-0 gate matrix (Linux portable; `argparse`, no PowerShell). `--phase all\|build\|bundles\|smoke\|pytest\|lhci\|canvas`, `--skip-heavy`, `--port` (default 8124). Starts/stops `serve-gzip.py` for smoke+lhci in `finally`; lock file `artifacts/next-work/gates/.run-gates.lock` serializes heavy runs (exit 3 if busy); logs command/exit/key-line under `artifacts/next-work/gates/<timestamp>/` and stops the chain at the first failure. Requirements: run through the repo `.venv/bin/python` (system python lacks Playwright), `PYTHONIOENCODING=utf-8` (set internally). The `canvas` phase calls the frozen `tests/canvas_motion_playwright.py` as-is (its `--output` **must be absolute** — the harness uses `path.relative_to(ROOT)`); the canvas *visual* gate is NOT RUN by this runner — the frozen baseline lives on the Windows box. |

Example: `.venv/bin/python tools/run-gates.py --phase all`.

## The server rule

**Every Lighthouse number must be measured against `tools/serve-gzip.py`.**
The first Lighthouse run in this project served files uncompressed from a
throwaway `http.server`; index.html then reads **54** instead of **73**, and
every byte-based budget assertion looks violated. Real static hosts compress.

```bash
python3 tools/serve-gzip.py --port 8124          # foreground
make serve-gzip                                  # same thing
```

The layout/DOM harnesses are transport-independent, so they reproduce against
either server. Only the byte numbers depend on compression.

## Files

### Server

| file | what it does |
| --- | --- |
| `serve-gzip.py` | static server for `src/python/` with gzip on compressible types, `Cache-Control: no-store`, `gzip mtime=0` for byte-identical output. `--port`, `--root`. |

### Page geometry and stability

| file | what it does |
| --- | --- |
| `capture.mjs` | N captures of document/section geometry in one browser process → a distribution. The determinism instrument. |
| `determinism-50x.py` | documented entry point for the above; exit 1 when more than one state appears. |
| `layout-shift-probe.mjs` | Layout Instability API collector: per-load CLS plus the nodes that shifted and by how much. |
| `page-errors.mjs` | all 16 pages: console errors and non-2xx responses. |

### CSS correctness

| file | what it does |
| --- | --- |
| `hover-audit.mjs` | forces `:hover` on each rule's trigger via CDP `CSS.forcePseudoState` and diffs the computed style of trigger + subjects. |
| `important-lift-test.mjs` | removes one authored `!important` **declaration** at a time and compares the **full** computed style — decides whether a priority is load-bearing. A rule whose selector mixes `:hover` with another state (`.x:hover, .x.active`) is measured on **both** paths: the class the selector names is added, a pseudo-class it names is forced over CDP. A declaration is load-bearing if either path changes a value; only a state the instrument cannot synthesize leaves it unmeasured, and that reason is carried out with the row. |
| `hover-verify.py` | entry point for both, across every page; `--all`, `--lift`, `--lift-runs=N` (a `demotable` verdict then needs every run of every page to agree), `--cross-page`. |
| `lift-verdict-compare.py` | compare per-declaration lift verdicts across an explicit list of `lift-*.json` artifacts for ONE page, flagging `FLIP` where runs disagree. `--cross-page` cannot do this: it aggregates by page name, so N runs of one page read as N different pages. |
| `state-style-diff.mjs` | snapshot the full computed style of everything matching a selector in the states you name (`plain`, `active`, `focus-visible`, `hover`) and `--compare=` two snapshots. This is the before/after check for a declaration whose only reachable path is a non-`:hover` state, which the hover row-level diff cannot cover. Comparison is by property **name**: Chrome enumerates registered custom properties in an unstable order, and a positional diff reports dozens of phantom changes. |
| `css-cascade-winner.mjs` | who actually WINS a property for an element in each state, from the browser's matched-style list (cascade order, values, `!important` flags, the last important entry). Answers "is this declaration inert because it is overridden", which is the difference between a safe demotion and a lucky one. Runs with `@media(hover:hover)` **re-enabled and verified** by default (`--no-hover-emulation` keeps the old behaviour): a cascade read from a touch-first page cannot explain a hover declaration, and headless Chrome reports `(hover: hover)` as false. |
| `demotion-recheck.mjs` | decide a demotion the sweep could not observe. Reads one rule's property with `:hover` forced and motion settled, then re-reads after the declaration loses its `!important` and after it is removed — in the page's default state and, with `--reveal`, with the `hidden` attributes removed so the element a user actually hovers has a box. Prints `elementsReadable`, and reads a verdict only on rendered elements. 
| `lift-verdict-compare.py` | compare N `lift-*.json` runs of ONE page: per declaration, the verdict and diff count in each run, with `FLIP` where they disagree. The stability proof for a lift verdict. |
| `computed-style-probe.mjs` | prove a CSS refactor changed no computed value: snapshot selectors before/after, or `--compare=` two saved runs. |

### Performance tracing

| file | what it does |
| --- | --- |
| `style-layout-trace.mjs` | CDP trace around a page load: Recalculate Style vs Layout totals, the longest individual events with their `beginData`, and per-selector stats. |
| `layout-stack-attribution.py` | attribute `Layout` / `UpdateLayoutTree` time to the JS frame that caused it, from the stack traces the trace already carries. The stack is at `args.beginData.stackTrace` (Blink's `SetCallStack` writes it into the event's own data dictionary), NOT at `args.stackTrace` — a reader that checks only the top level reports 0 and concludes the cause is unattributable. `--paths` prints where the stack actually is, which is the measurement that settles that question. |
| `loader-ab.mjs` | A/B the deferred loader's serial promise chain against `Promise.all`, asserting the arm was actually patched. |

### Fonts

| file | what it does |
| --- | --- |
| `subset-fonts.py` | `inventory` / `codepoints` / `subset` / `verify` — the used character set, pyftsubset, and a coverage check that catches a dropped glyph. |

### Lighthouse

| file | what it does |
| --- | --- |
| `lighthouserc.js` | the only Lighthouse CI config. Run from the repo root: `npx lhci autorun --config=tools/lighthouserc.js`. |

### Suites and routing

| file | what it does |
| --- | --- |
| `analytics-wiring-gap.py` | collect every path the three analytics suites call and report whether the same literal appears in `src/python/server.py`. The feature itself is built in `src/python/features/analytics/`; this prints what was never wired. Read-only. |
| `phase6-flag-mutations.py` | three mutations injected at the fixed flag test's own seams (500 from the admin PUT, the PUT flipping the wrong flag, the user never promoted). Every one must make `test_phase6_live_endpoint_feature_flag` fail; a survivor means the branch runs without being asserted, which is exactly how its 200-branch stayed unreachable. Exit 0 = all killed. |
| `analytics-live-flag-probe.py` | boot the app server with the repo's own harness and exercise the analytics paths the shipped suites cannot reach: the live endpoint 403 → admin PUT flips `analytics_live_enabled` → 200 with `activeSessions`/`lastEventAt`, plus non-host 404, unknown-invitation 404 and invalid-sessionId 400 on ingestion. `test_phase6` cannot reach its own 200 branch because the admin write it tries is PUT-only and admin-only; this does. Exit 0 means all seven checks held. |
| `playwright-check/` | the brief's `playwright.chromium.launch()` check, in its own directory with its own manifest, so the application's `package.json` is never touched. `node tools/playwright-check/launch-check.mjs` launches Playwright's own Chromium, loads a served page and prints `PLAYWRIGHT_LAUNCH_OK`. See its README. |

### Served mirror

| file | what it does |
| --- | --- |
| `mirror-diff.py` | verify `src/python/` (the server's ROOT) against its sources **by sha256, not mtime**: `drifted`, `unmigrated`, `orphans`. Imports `SYNC_PLAN` from the syncer so the two cannot disagree about what is mirrored. Generator-owned artifacts (`bundle-*.*`, `editor-suite.*`, the manifests) are excluded and counted separately; serve-root files with no upstream source are exempt **by name and with a reason**, printed, never deleted. Exit 1 on any real drift. |

### Cross-site / attribution

| file | what it does |
| --- | --- |
| `canva-probe.mjs` | CDP trace + JS/stylesheet inventory of any URL (`--prefix` names the three artifacts). Takes the same measurements on Canva's public pages and on this project's served pages so one analyzer can compare them. Never logs in; records the HTTP status so a wall is visible. |
| `perf-trace-compare.py` | read two `*-trace.json` files and print one table: style-recalc / layout / script **union** time (union, not sum — recalc events nest), the longest tasks and layouts, and the count of layouts nested inside a script event (the forced-layout proxy). |
| `forced-layout-attribution.mjs` | name the JS call sites that force synchronous layout, by instrumenting writes and layout-forcing reads in the DOM and recording the first non-probe stack frame. `--exercise=SELECTOR` measures one interaction (types into it) instead of the load. |
| `css-feature-inventory.mjs` | count the modern-CSS constructs a URL ships (`content-visibility`, `contain`, `@layer`, `@container`, `:has(`, `color-mix(`, `!important`, …) from the CSS **text**, read via CDP so cross-origin sheets work. One instrument, both sites. |
| `bundle-line-map.py` | map a bundle line number back to `src/<dir>/<file>:<line>`, replaying the generator's own concatenation. `--verify` re-derives every bundle and asserts each mapped source line's text occurs in the bundle line it was mapped to. |
| `module-loading-strategy.mjs` | the **declared** loading strategy of a page (`async` / `defer` / `type=module` / `preload` counts, parser-blocking srcs) read from the document's own HTML, plus the **injected** set read from the DOM, plus each script's fetch timing and the chain's span / transfer / serial gap. Reports the two sets separately because counting the DOM as "parser-blocking" overstated this project's index page 12× (3 declared, 34 injected after the parser finished). |

## Conventions

* **Outputs go to `artifacts/`** (gitignored), never to `/tmp`.
* **Paths come from `tools/lib/repo.mjs`**, derived from the script's own
  location. Override with `REPO_ROOT`, `SERVE_ROOT`, `BASE_URL`, `PORT`,
  `ARTIFACTS_DIR`, `CHROME_PATH`.
* **Chrome is resolved**, never hard-coded — see `tools/lib/browser.mjs`.
  `CHROME_PATH` wins; then the repo's `.cache/puppeteer` download; then the
  system browser.
* **A single measurement is not a measurement.** Geometry claims use
  `determinism-50x.py`; layout-shift claims use `--n=5`; the loader A/B refuses
  to report unless the patched arm was verified patched; a lift verdict needs every
  run of every page to agree (`--lift-runs=N`), and `lift-verdict-compare.py` is how
  N runs of ONE page are compared with each other.
* **A verdict is not evidence where nothing is observable.** `important-lift-test.mjs` no
  longer calls a declaration inert when every element its rule reaches has no box: inside
  a `display:none` subtree Chrome stops resolving used values, so `transform` reads `none`
  whatever the cascade says and the leave-one-out returns an identical snapshot in every
  run. Such a declaration is reported **unmeasured** (`rendered` = 0), with the count of
  elements reached, and `tools/demotion-recheck.mjs --reveal` is what measures it in the
  state a user can hover in. Repeating an observation that cannot observe anything does
  not make it evidence — the expanded sweep's one unanimous candidate was exactly that.
  The same probe also tears its own self-check fixture out of the page before the sweep:
  the synthesized `div.ui-theme-menu.decl-fixture-host > button` matched the very rule used
  as the fixture, so the probe was sweeping its own scaffolding.
* **A probe must read at a settled moment.** `lib/motion-settle.mjs` — one frame,
  every finite running animation on the elements about to be read, then two frames —
  is injected into any probe that samples a computed style after forcing a state. A
  property with a running transition makes `getComputedStyle` return the
  *interpolated* value, so a read taken at the wrong moment is a per-run observation
  rather than a property of the tree. `freezeMotion()` in `lib/browser.mjs` is not
  enough on its own: route bundles re-declare `transition:…!important` and win that
  cascade. The lift probe read immediately after `CSS.forcePseudoState` until this
  was added, and disagreed with itself on 3 of 59 declarations across 5 runs of one
  page.
* **Every claim in a report carries the command that produced it.**
* **An instrument that reports a wrong number gets fixed before its output is
  acted on.** `forced-layout-attribution.mjs` needed three corrections before
  its top entries were real (detached-node reads, `.id`/`window.inner*` reads,
  and `classList.toggle` no-ops that dirty nothing) — each is recorded in the
  tool's own header, and in the pass report that used it.

## Node dependencies

Declared in the repo-root `package.json`, so there is exactly one
`node_modules`:

```
@lhci/cli        ^0.15.1
puppeteer-core   ^25.12.0
```

`puppeteer-core` is used rather than `puppeteer` because the browser is resolved
from `CHROME_PATH` or the system install; `puppeteer-core` will not silently
download and use a different Chrome than the one being measured.
