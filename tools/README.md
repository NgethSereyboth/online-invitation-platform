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
| `important-lift-test.mjs` | demotes one `!important` declaration at a time and compares the **full** computed style — decides whether a priority is load-bearing. |
| `hover-verify.py` | entry point for both, across every page; `--all`, `--lift`. |
| `computed-style-probe.mjs` | prove a CSS refactor changed no computed value: snapshot selectors before/after, or `--compare=` two saved runs. |

### Performance tracing

| file | what it does |
| --- | --- |
| `style-layout-trace.mjs` | CDP trace around a page load: Recalculate Style vs Layout totals, the longest individual events with their `beginData`, and per-selector stats. |
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

### Served mirror

| file | what it does |
| --- | --- |
| `mirror-diff.py` | verify `src/python/` (the server's ROOT) against its sources **by sha256, not mtime**: `drifted`, `unmigrated`, `orphans`. Imports `SYNC_PLAN` from the syncer so the two cannot disagree about what is mirrored. Generator-owned artifacts (`bundle-*-v15.*`, `editor-suite.*`, the manifests) are excluded and counted separately; serve-root files with no upstream source are exempt **by name and with a reason**, printed, never deleted. Exit 1 on any real drift. |

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
  to report unless the patched arm was verified patched.
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
