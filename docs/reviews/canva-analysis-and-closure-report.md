# Canva analysis and pass closure — report

Pass base `7ce64cc`; ten commits on `main`; every number below carries the command
that produced it. Blocks marked with a `<!-- report-verify: … -->` declaration are
the ones `tools/report-verify.mjs` cannot re-run (they need a server, a browser, or
minutes of wall clock); everything else in a `$`-block is re-run and byte-compared by
`node tools/report-verify.mjs docs/reviews/canva-analysis-and-closure-report.md`.

This pass added a Goal 0 (install REA and a browsing toolchain, analyze Canva's
editor-class site for techniques this project can port) ahead of the five goals from
the prior brief. All six are reported below, including the ones that ended in a
decision not to change anything.

## 0. What changed

| # | commit | what |
| --- | --- | --- |
| 1 | `6583c69` | REA + the Canva analysis toolchain (`canva-probe.mjs`, `perf-trace-compare.py`, `css-feature-inventory.mjs`, `bundle-line-map.py`, `forced-layout-attribution.mjs`) |
| 2 | `5bb5ac7` | `module-loading-strategy.mjs`, and the REA capture of the live page |
| 3 | `2750ceb` | **the one ported technique**: the loader chain declares its fetches before the chain runs |
| 4 | `93df26c` | served mirror: verify and regenerate by content |
| 5 | `1b1adf0` | layers-panel ResizeObserver rewrite guarded by a test |
| 6 | `2f6f6e6` | `organized/` ambiguity resolved |
| 7 | `d61fc61` | `v52_crdt`'s documented `server_url` fixture, and a `collect_ignore` regression this pass caused and repaired |
| 8 | `01fc700` | lift verdicts require unanimity before any `!important` demotion |
| 9 | `863211a` | a missing browser executable is a skip, not a false failure |
| 10 | this report | the analysis, the comparison table, the decisions, the evidence |

<!-- report-verify: historical the commit list is this pass's own history; HEAD moves with each commit -->
```
$ git log --oneline -10
2750ceb perf(index): declare the loader chain's fetches before the chain runs
5bb5ac7 chore(tools): measure the module-loading strategy a page declares
```

## 1. Goal 0 — REA and the Canva analysis

### 1.1 What REA is, and what it is not

REA (`rea-agents@6.4.0`) is a reverse-engineering tool: it captures a page or an
application through CDP or a native provider, keeps the bytes it captured as
*source artifacts with sha256 digests*, statically analyzes them (it does not execute
captured JavaScript — its own limitation line says so), and returns findings tagged
`confidence: observed` or as bounded inferences. Its website side needed for this
pass is `analyze-web-bundle` against a loopback CDP endpoint this pass owns.

What it is **not**: it does not hand back a clean, commented implementation of
Canva's editor, and it cannot see code the page never serves. What came back is a
static reading of minified bundles, and the honest summary of that reading is in
§1.9.

### 1.2 Installation

`npx rea-agents setup` was run and its plan inspected before anything was applied. It
wrote registrations into two clients it detected (VS Code, GitHub Copilot CLI), and
installed its managed skill. Read back from the configs themselves:

```
$ sed -n '1,10p' tools/evidence/rea-registration.txt
REA_REGISTRATION — what the setup changed, checked after the fact

# the skill it installed (tools/evidence/rea-setup.txt recorded the install)
/home/ngethsereyboth/.agents/skills/reverse-engineer-anything

# the managed-skill identities, from tools/evidence/rea-doctor.txt
  expected_skill_version: "37"
    installed_version: "37"
    installed_tool_count: 170
    state: aligned
```

Two honest caveats about "readiness".

* `healthy` **disagrees between the two doctor runs recorded in the same evidence
  file** — line 3 says `false`, line 15 says `true`, with `environment_healthy: false`
  in both. The substantive state (skill version 37 aligned, 170 tools, two client
  registrations aligned) is identical in both runs, so the flag is about which client
  or scope the run was asked about, not about whether the website pipeline works. The
  live capture in §1.9 is the evidence that it works; the flag itself is left
  UNVERIFIED rather than explained away.
* `availableProviders: []`. REA's native providers (Ghidra, IDA) are unconfigured —
  `GHIDRA_INSTALL_DIR is not set`, `IDA MCP registration is not configured` — which is
  irrelevant here and is recorded so nobody later reads "no providers" as "REA is
  broken".

### 1.3 The browsing toolchain

`package.json` is a hard rule in this pass ("do not touch") and it already declares
`puppeteer-core@^25.12.0`, which every instrument in `tools/` already measures with. So
the browser used is the repo's own (`tools/lib/browser.mjs`: `CHROME_PATH`, then the repo's
puppeteer download, then the system browser) rather than a newly installed Playwright.
Measured on this host: `/usr/bin/google-chrome` (used by the Node instruments and, via
`PLAYWRIGHT_CHROMIUM_EXECUTABLE`, by the one pytest that drives a browser).
`canva-probe.mjs` records the resolved browser and Chrome version in its artifact:
`"chrome": "/usr/bin/google-chrome (kind=full)"` (`artifacts/canva-probe-summary.json`).

> Note on the working tree: `package.json` and `package-lock.json` are **modified** in
> this checkout — a single `agent-browser` devDependency added at 09:41, before this
> pass's first Canva run at 12:31 and untouched by every tool this pass wrote. They are
> left uncommitted and unmodified, as the brief requires, and are not part of any commit
> listed in §0.

### 1.4 The bot wall, measured (and why the tool reads the DOM, not `fetch`)

Two measurements of the same URL from this host, minutes apart:

| how | result |
| --- | --- |
| `fetch('https://www.canva.com/')` from Node | **403**, 755 KB body, 3 inline scripts, **0** `src` scripts |
| the repo's Chrome with a desktop UA | **200**, title "Canva: Visual Suite for Everyone", 28 `src` scripts, 261 KB of CSS |

`artifacts/canva-probe-summary.json` records the 200 for the browser; the 403 was
measured while writing `module-loading-strategy.mjs` and is what forced it to read
`document.documentElement.outerHTML` from inside a page instead of fetching text. A
first REA capture on this host hit the same wall in a different form: it analyzed the
Cloudflare challenge instead of the site (246 KB challenge script + a 576 KB
`?__cf_chl_rt_tk=` interstitial). That capture is retained rather than deleted —
`/tmp/rea-bundle.json`'s headline numbers (`4 scripts, 199 047 AST nodes`) were the
challenge page — and the REA run in §1.9 was retaken with a plain desktop UA, which
returned the real document.

### 1.5 The trace comparison

Both traces come from the same instrument (`tools/canva-probe.mjs`), read by the same
analyzer (`tools/perf-trace-compare.py`), so the columns are like-for-like. Union
times, not sums: recalc events nest.

```
$ sed -n '3,13p' tools/evidence/trace-compare.txt
trace events                                         189695            136014
style+layout union ms (main thread)                  805.22           2142.25
  style recalc union ms                              525.12           1178.75
  layout union ms                                     280.1            963.58
  style recalc union ms (all threads)                525.12           1178.75
  layout union ms (all threads)                       280.1            963.58
Script union ms (main thread)                       2604.65           2745.82
UpdateLayoutTree events                                 379               166
Layout events                                            37               111
RunTask events                                        29315             17636
Layouts nested in script (forced proxy)                   6                77
```

Reading it carefully:

* Script time is nearly identical (2746 ms vs 2605 ms) — this is not a page that is
  slow because it runs more code.
* Style & Layout is 2.7× higher on this project's index page, and the shape is
  different: this project runs **166** recalc events for 1179 ms (7.1 ms per event) where
  Canva runs **379** for 525 ms (1.4 ms per event). Canva recalcs more often and pays
  much less per recalc.
* The project lays out 111 times to Canva's 37, and 77 of those layouts are nested
  inside a script event against Canva's 6. This is the *proxy* the analyzer documents:
  the trace carries no `args.stackTrace` on any Layout event even with the stack
  category enabled (`Layouts with stackTrace: 0` in both columns), so "nested in
  script" is the only available signal, and it is labelled a proxy everywhere it is
  used.
* The longest single layout is 391 ms on this project (886/886 objects dirty — a
  full-document relayout) against Canva's 228 ms (1465/1465). Per dirty object that is
  0.44 ms vs 0.16 ms: this project's worst case costs ~2.8× more per object. Cause not
  established by this measurement — see §1.13.

### 1.6 CSS: one instrument, two sites

`tools/css-feature-inventory.mjs` reads the CSS *text* through CDP (cross-origin sheets
included) and counts constructs. Both rows are in
`tools/evidence/canva-css-inventory.txt`; the table:

```
$ sed -n '12,30p' tools/evidence/canva-css-inventory.txt
construct                   canva  project   reading
contentVisibility               0        6   the project uses it (5 of 6 auto); Canva homepage: 0
contain                         0        8   the project uses it; Canva homepage: 0
containIntrinsicSize            0        4   the project pairs it with content-visibility; Canva: 0
willChange                      7        8   comparable
translateZ                      6        2   comparable
isolation                       7        7   identical count
layers                          9       65   the project uses @layer far more (65 vs 9)
containerQueries                1        3   comparable
containerType                   1        1   identical
isSelector                     13        2   Canva flattens specificity with :is() 6.5x more
whereSelector                  73        6   Canva flattens specificity with :where() 12x more
hasSelector                     0       29   the project uses :has(), Canva does not on this page
clamp                           3       22   the project uses clamp() 7x more
colorMix                        0      316   the project uses color-mix() 316x, Canva 0 here
important                       7     2985   the project declares the most: 2985 vs 7 (426x)
mediaBlocks                   324      206   Canva has 1.6x more @media blocks
keyframes                      39       22   Canva has 1.8x more @keyframes
customPropertyDecls          1031      340   Canva declares 3x more custom properties (1031 vs 340)
```

The two findings that matter: containment (row 1–3) is **not** a Canva technique to
port — their public page uses none, this project uses more — and the specificity rows
(`:where` 73 vs 6, `!important` 7 vs 2985) are the same disease seen from two sides.

### 1.7 Module loading (and the instrument bug that was fixed before it was believed)

```
$ python3 -c "import json;d=json.load(open('artifacts/module-loading-canva.json'))['rows'][0];e=json.load(open('artifacts/module-loading-project-index.json'))['rows'][0];print('canva  :', {k:d['declared'][k] for k in ['src','module','async','defer','parserBlocking']});print('project:', {k:e['declared'][k] for k in ['src','module','async','defer','parserBlocking']});print('canva  preloads:', d['preload']['declaredTotal'], 'project preloads:', e['preload']['declaredTotal']);print('canva  DOM src scripts:', d['dom']['srcScripts'], 'injected:', d['dom']['injected']);print('project DOM src scripts:', e['dom']['srcScripts'], 'injected:', e['dom']['injected'])"
canva  : {'src': 8, 'module': 0, 'async': 0, 'defer': 5, 'parserBlocking': 3}
project: {'src': 3, 'module': 0, 'async': 0, 'defer': 0, 'parserBlocking': 3}
canva  preloads: 9 project preloads: 0
canva  DOM src scripts: 28 injected: 20
project DOM src scripts: 37 injected: 34
```

The instrument's first version counted the DOM and reported **37 parser-blocking
scripts** for `index.html`. That was wrong by 12×: the served HTML declares three
(`core/theme.js`, `backend-mode-v14.js`, `bundle-index-v15.js`, all at the end of
`<body>`), and the other 34 are created by `src/js/performance-loader-v22.js` and by
the bundle with `document.createElement('script')` *after* the parser has finished. A
script created that way cannot block a parser that has already parsed the document. The
tool now reports the declared set (from the document's own HTML) and the injected set
(from the DOM) separately, and the file's header keeps the mistake as the reason the
distinction exists.

The real gap in that row is not `async`: it is that this project declares **zero**
preloads where Canva declares nine, and that the loader's 23 script fetches are
strictly serial — each one starts only after the previous script's `onload`.

### 1.8 designlang: what it extracted, and whether it matches

`npx designlang https://www.canva.com --out artifacts/canva-design` produced 34 files.
Extracted and compared against `src/css/tokens.css` in
`tools/evidence/designlang-vs-tokens.txt`:

* **Radii** — Canva's computed set is 8 / 12 / 24 / 50 / 9999 px; this project's is
  `--radius-sm/md:8px`, `--radius-lg/xl:16px`, `--radius-pill:9999px`. They agree at
  8 px and 9999 px, and `tokens.css` already documents 8 px as "Canva's named
  `radiusElement` token" — so the extraction *confirms a decision the project already
  recorded* rather than adding one.
* **Spacing** — both are 4 px based. designlang's list also contains 256/296/315/332/495 px
  because it samples computed gaps of a marketing layout; those are section widths, not
  a scale, and are not ported.
* **Colour and type** — Canva's `#8b3dff` / `#ff6105` purple-orange pair and "Canva Sans,
  Times New Roman" are Canva's brand, not a technique. This project is not Canva, and it
  self-hosts Inter + Noto Sans/Serif Khmer. Nothing ported.

**Caveat, stated because it bounds the whole section**: designlang reads *computed*
styles of the *marketing homepage*. The editor's tokens are behind a login and were not
extracted. Any editor token claim in this report would be UNVERIFIED; there are none.

### 1.9 REA on the live page

`analyze-web-bundle` against a loopback CDP Chrome this pass launched, on the real page
(the UA fix from §1.4):

```
$ python3 -c "import json;d=json.load(open('tools/evidence/rea-canva-bundle.json'));n=d['normalized_result'];print('scripts observed/analyzed:',n['capture']['scripts_observed'],n['capture']['scripts_analyzed']);print('bytes analyzed:',sum(a['bytes'] for a in n['capture']['source_artifacts']));print('AST nodes visited:',n['completeness']['visited_ast_nodes']);print('endpoints:',len(n['observations']['endpoints']),'source maps:',n['observations']['source_maps']['status'])"
scripts observed/analyzed: 8 8
bytes analyzed: 1277175
AST nodes visited: 370759
endpoints: 31 source maps: not_requested
```

What that is worth, honestly:

* **Coverage**: 8 scripts, 1.28 MB. The network delivered **81** scripts and 10.24 MB
  decoded on those two public pages (`artifacts/canva-scripts.json`). REA analyzed 12.5%
  of it — the scripts it retained — so "REA analyzed Canva" would be an overstatement.
* **What it produced**: a chunk graph of those 8 scripts with **0 import edges** between
  them (they are siblings loaded by the page, not an ES-module graph), 31 "endpoints"
  which are WebGL extension capability strings (`WEBGL_multi_draw`,
  `EXT_texture_filter_anisotropic`, …) rather than URLs, and source maps
  `not_requested`.
* **Conclusion**: on minified production bundles, REA's static reconstruction returns
  structure and identifiers, not architecture. The task brief anticipated this ("if the
  output is unhelpful, say so and move on"). What was actually useful came from the
  network inventory and the loader timing in §1.7, which are measurements rather than
  reconstructions.

### 1.10 Step 0g — the comparison table

| Concern | Canva's approach (cited) | Project's approach (measured) | Verdict |
| --- | --- | --- | --- |
| Style & Layout | 805 ms union; 379 recalcs at 1.4 ms each; worst layout 228 ms for 1465 objects (`tools/evidence/trace-compare.txt`) | 2142 ms union; 166 recalcs at 7.1 ms each; worst layout 391 ms for 886 objects (same file) | **GAP, cause UNVERIFIED** — the per-recalc and per-object costs differ 2.8–5×, but the pages differ and the cause is not isolated by this measurement |
| Module loading | 8 declared src scripts, 5 `defer`, 9 `<link rel=preload>`; transfers overlap (span 2866 ms vs 5871 ms summed) (`artifacts/module-loading-canva.json`) | 3 declared src scripts, 0 `defer`, 0 preloads; 23 serial fetches, span 3174 ms vs 1346 ms summed (+1828 ms waiting) (`artifacts/module-loading-project-index.json`, `artifacts/module-loading-project-index-before{,2,3}.json`) | **CLOSE** — ported, §1.11 |
| CSS containment | `content-visibility: 0`, `contain: 0`, `contain-intrinsic-size: 0` on the homepage (`tools/evidence/canva-css-inventory.txt`) | 6 / 8 / 4, five of them `content-visibility: auto` (same file) | **IGNORE** — there is nothing to port; this project already uses more containment than their public page. Whether their *editor* uses containment is UNVERIFIED (§1.13) |
| Specificity / `!important` | 7 `!important` and 73 `:where()` over 4289 rules (same file) | 2985 `!important` and 6 `:where()` over 5245 rules (same file) | **GAP, addressed by Goal 5's mechanism**, not by a mass rewrite: `:where()` flattening is the technique, and the unanimity rule is what makes a demotion safe per declaration (§6) |
| ResizeObserver | 7 observers / 6 callbacks on the homepage; 24 / 24 on `/templates/` (`artifacts/canva-probe-summary.json`) | the panel's observer is now gated on a real box change and guarded by a test (§3) | **IGNORE for now** — Canva's counts say nothing about their *editor*; the measurable part of this concern was already addressed in `a851083` and this pass's guard |
| Font loading | 5 self-hosted font files, detected by designlang (`tools/evidence/designlang-canva.txt`); no preload of them in the declared HTML beyond the generic preloads | self-hosted subset fonts with a payload instrument (`tools/font-payload.py`) and a coverage check | **IGNORE** — no evidence their strategy differs in a way worth porting; nothing in the trace attributes font cost |
| Animation | 39 `@keyframes`, motion tokens exported by designlang (marketing page) | 22 `@keyframes` | **IGNORE** — a marketing page's motion library is not a technique the editor needs |

### 1.11 The one CLOSE gap, implemented and measured

**Technique, in general terms** (not their code): declare the fetches of a deferred
script chain before the chain starts, so the transfers overlap while execution stays
in order. Canva's page does the declaration half (9 preloads; span shorter than the
summed transfer time).

**Implementation in this project's idiom**: `src/js/performance-loader-v22.js` appends
one `<link rel="preload" as="script">` per chain URL before the first
`document.createElement('script')`, and skips the whole declaration when
`navigator.connection.saveData` is set. Execution order is untouched: the chain still
appends one script and waits for its `onload`.

**Before/after**, three runs per side, same instrument, medians
(`tools/evidence/canva-close-module-preload.txt`):

```
$ sed -n '18,24p' tools/evidence/canva-close-module-preload.txt
metric                         before      after      delta
chainSpanMs                      3174       3075        -99
chainTransferMs                  1346       3393      +2047
chainSerialGapMs                 1828       -314      -2142
lastChainScriptEnd               3211       3096       -115
domContentLoaded                 1587       1676        +89
loadEventEnd                     3280       2771       -509
```

The honest reading, which the evidence file also states: `chainSerialGapMs` counts time
the chain spent not transferring, and it is **not** wall clock saved, because the main
thread parses the previous script during much of it. `chainTransferMs` roughly triples
because a resource entry's `duration` includes waiting for a connection, so under
parallelism the *sum* inflates. The end-to-end numbers are the ones that mean something:
chain end −115 ms, load −509 ms, FCP 800 → 780 ms (three samples 920/492/780 against
800/768/828 — noise, claimed as no regression and nothing more). The span barely moves
because it is bounded by serial execution, which is the order guarantee and stays.

Contract checks after the change: 37 script elements, 23 preloads,
`EInvitePerformanceReady` resolves, 0 page errors, 0 console errors, 0 non-2xx
(`tools/evidence/canva-close-module-preload.txt`, last sections).

### 1.12 IGNORE decisions, with reasons

* **Containment** (§1.10 row 3): nothing to port, and the one time this pass tried to
  act on a containment-adjacent hunch (batching the studio search loop) the measurement
  refused to support it — §8.
* **Brand tokens** (§1.8): their brand is theirs.
* **Motion tokens**: a marketing page's animation library, extracted from computed
  styles, is not an editor technique.
* **Serializer/architecture from REA**: not obtainable from minified bundles, and
  copying their minified code into this project is the thing the brief forbids. The
  technique that was ported was stated first and then written from scratch — the loader
  change is 6 lines of this project's own idiom.

### 1.13 UNVERIFIED

* **Canva's *editor* for every row of §1.10** — it is behind a login that this pass
  deliberately did not attempt. Every Canva number above is from
  `https://www.canva.com/` or `https://www.canva.com/templates/`.
* **The cause of the Style & Layout gap** (§1.10 row 1). Measured: this project pays
  7.1 ms per recalc and 0.44 ms per dirty layout object where Canva pays 1.4 and 0.16.
  Not measured: which rule, selector, property or DOM shape produces that. Candidate
  explanations (unbounded selector matching over 5245 rules; text-metric work per
  object; images without intrinsic dimensions) are guesses and are labelled as such.
* **`healthy` in REA's doctor output** (§1.2).
* **Their font strategy** (§1.10 row 6) — nothing in either trace attributes time to
  fonts, so there is no measurement to compare.
* **Source maps**: `source_maps.status: not_requested` in the REA capture (§1.9), so no
  original-name reconstruction was attempted. A follow-up capture with
  `--fetch-source-maps` may be worth an hour; it was not spent here.

## 2. Goal 1 — the served-mirror verification gap

The documented next milestone. Three changes, all in `93df26c`:

1. `tools/mirror-diff.py` — compares `src/python/` (the server's ROOT) against its
   sources **by sha256, not mtime**, and separates `drifted`, `unmigrated` and
   `orphans`; generator-owned artifacts are counted, not silently ignored; hand-added
   serve-root files with no upstream source are exempt **by name and with a reason**,
   printed, never deleted.
2. `src/python/build/sync_frontend_assets.py --check` — a real gate, content-based,
   which is what `build.py`'s `mirror` step now runs.
3. `build.py` — the mirror step runs last and fails the build on drift.

Raw evidence in `tools/evidence/mirror-verification.txt`, including the deliberate-drift
test: baseline green → 24 bytes appended to `src/python/modern-ui.css` →
`MIRROR_CHECK_FAILED 1 stale destination(s)` and `BUILD_FAILED mirror` → sync →
`MIRROR_CHECK_PASSED` → revert to the recorded bytes, byte-identical.

```
$ python3 tools/mirror-diff.py
MIRROR_DIFF {"sources": 314, "drifted": 0, "unmigrated": 0, "orphans": 0, "orphansExempt": 19, "generatedExempt": 34}
MIRROR_DIFF_SUMMARY 0 drifted, 0 unmigrated, 0 orphans (19 named and exempt)
```

The gate found real drift the day it was written: 7 served files were stale against their
sources, including 6 CSS files whose mirror copies were one to three `!important`
declarations behind (that is the whole of the "`!important` decreased" column in §7.7).

## 3. Goal 2 — the layers-panel guard

`a851083` fixed the overlay's ResizeObserver re-arming on its own output and recorded
that caching `renderLayers()`' wholesale `#layersPanel.innerHTML` rewrite was **not**
done, because the behaviour it could break had no guard. This pass wrote the guard:
`tests/layers_panel_guard_test.py`.

* Static half: the schedule is gated on a real box change, and the static assertion
  fails if that gate is removed (negative control A in
  `tools/evidence/layers-panel-guard.txt`).
* Dynamic half: rows == objects, selection marks a row, the panel writes 5 times for one
  sync and 0 times at rest, and the observer is notified 8 times across a real resize —
  `V17_LAYERS_PANEL_GUARD_PASSED` with those numbers.
* **Labelled honestly, because the control says so**: with the guard removed the dynamic
  checks still pass on this host, so the dynamic half is a contract test, not a
  regression detector for that specific defect. The static half is what fails without
  the guard. Both facts are in the evidence file rather than only the flattering one.
* **Repaired in `863211a`**: the dynamic half's skip path covered "playwright is not
  importable" but not "no browser executable", so on this host (playwright installed,
  its bundled Chromium absent) the suite went red for an environmental reason. It now
  skips with the reason, and still raises when `EINVITE_REQUIRE_BROWSER=1`.

## 4. Goal 3 — the `organized/` resolution

`tools/versioned-rename-surface.py` (extended in this pass to answer *which bundle system*
a name is live in) settled it. Two files were `BOTH-LIVE`, not stale:

* `src/css/organized/photo-editor-v13.css` and `src/js/photo-editor-v13.js` are bundle
  sources of the **route-bundles** system (live in `route-bundles`);
* `src/css/photo-editor.css` and `src/js/photo-editor.js` are inputs of the **editor
  bundle** (`editor-bundle`).

So "rename `photo-editor-v13.*` to `photo-editor.*`" would have consumed a name another
shipped artifact needs. Classified as a retirement decision, not a rename, and left
alone. Separately, five **generated** `bundle-*-v15.css` files were sitting in the source
directory at 71–228 KB against 129–309 KB generated (regenerated by `build.py`), inputs
of neither bundle system, and were removed — the one IRREVERSIBLE mark of the pass
(`git show 1b1adf0:src/css/organized/<file>` shows the old bytes if they are ever wanted).
Evidence: `tools/evidence/organized-resolution.txt`.

## 5. Goal 4 — the red tests

**`v52_crdt` — fixed.** The six tests in `tests/v52_crdt_offline_merge_test.py` ask for a
`server_url` fixture that existed nowhere in the tree, and their docstring names the
mechanism it should use (`v14_test_utils.app_server`). The fixture now exists:
`6 passed, 62 deselected`.

**And a regression this pass caused, found by running the suite through its own
interface**: appending that fixture deleted the last line of `tests/conftest.py`,
`collect_ignore = [...]` — the only line that makes the `COLLECT_IGNORE` list above it
mean anything. `python3 -m pytest tests/` went back to dying with an INTERNALERROR while
importing `final_features_test.py`, which is exactly the failure that module exists to
prevent. Restored, with the failure recorded in
`tools/evidence/pytest-conftest-repair.txt`; `--collect-only` reports 68 tests collected.

**`analytics` — inventoried, not built. 15 failed, 5 passed.** The feature is not missing:
`src/python/features/analytics/{model,sessions,queries,export}.py` holds the schema,
`record_event_batch`, session reconstruction, retention pruning, ten read-model queries
and CSV/JSON export streams. What was never done is the **routing**:

```
$ python3 tools/analytics-wiring-gap.py | grep -E "no\s*$"
/api/account/analytics/creations                                                no
/api/account/analytics/creations?sort=views&order=asc                           no
/api/account/analytics/creations?status=draft                                   no
/api/account/analytics/export?format=csv                                        no
/api/account/analytics/summary                                                  no
/api/analytics/events                                                           no
/privacy.html                                                                   no
```

Decision, taken without asking because the brief requires it: **not wired in this
pass.** The GET `/api/invitations/<id>/analytics` route currently answers with the
pre-analytics shape that a dashboard page consumes under its own contract tests; changing
its payload is a feature with a blast radius, not a red-test repair. This pass already
tried the narrow version of that (wiring `POST /api/analytics/events`) and reverted it
when the read model turned out to be part of the same change — see §8. The gap is now
enumerated by a committed tool (`tools/analytics-wiring-gap.py`, added to
`report-verify`'s allow-list so a later report can cite it), so the next pass starts from
a list rather than from 15 failure lines.

## 6. Goal 5 — unanimity before any demotion

`tools/hover-verify.py --cross-page` used to call a declaration `demotable` from **one**
lift run per page, and two runs over identical CSS had already been measured disagreeing
about the same declaration. It now takes `--lift-runs=N`, reads
`lift-<page>.run<N>.json` alongside run 1, and requires **every run of every page that
measured a declaration to agree**: a run that called it load-bearing, or that could not
reach the rule at all, makes the verdict `unstable`, which is never demoted.
`runsPerPage` / `minRunsPerPage` are printed so a weak directory says so.

```
$ sed -n '4,8p' tools/evidence/unanimity-3runs.txt
$ ARTIFACTS_DIR=artifacts/unanimity-demo LIFT_JSON=1 python3 tools/hover-verify.py --cross-page
summary: {"pages": 1, "runsPerPage": {"index": 3}, "minRunsPerPage": 3, "declarations": 60, "demotable": 1, "keep": 23, "noEvidence": 36, "unstable": 0}
demotable: input:hover, textarea:hover, select:hover / border-color longhands=4 diffs=0 redundantOn=['index']
unstable: 0
```

Three runs on `index.html` agreed, so the rule cost nothing there. Its controls are the
point:

* **Control 1** — flip one run's verdict for the demotable declaration to load-bearing:
  verdict becomes `keep`, demotable 1 → 0.
* **Control 2** — delete the declaration from one run's buckets (the "this run could not
  reach the rule" case): verdict becomes `unstable`, `demotable: 0`, and `conflicts`
  names the run that is missing.
* **The sweep** — union of the 16 single-run page artifacts with the three index runs:
  `demotable 0, keep 27`. The one candidate is **load-bearing on `public.html`** (18
  changed values) and redundant on seven other pages, so it must not be demoted. That is
  the rule doing its job: one page's evidence would have removed a declaration another
  page depends on.

Consequence: **this pass demotes nothing**, and the tooling now refuses to demote on
evidence this thin. Both controls and the sweep are in
`tools/evidence/unanimity-3runs.txt`.

## 7. Verification

### 7.1 Build

```
$ python3 build.py all --check | tail -1
BUILD_OK editor bundles manifests mirror (check)
```

Exit status was captured without a pipe: `exit=0`.

### 7.2 Served mirror

```
$ python3 tools/mirror-diff.py
MIRROR_DIFF {"sources": 314, "drifted": 0, "unmigrated": 0, "orphans": 0, "orphansExempt": 19, "generatedExempt": 34}
MIRROR_DIFF_SUMMARY 0 drifted, 0 unmigrated, 0 orphans (19 named and exempt)
```

### 7.3 Deliberate-drift test

<!-- report-verify: historical mutates src/python and reverts; the transcript is in the evidence file -->
Recorded in `tools/evidence/mirror-verification.txt`: 1-byte change → check fails →
sync repairs → check passes → revert byte-identical.

### 7.4 pytest

<!-- report-verify: measurement needs .venv, ~135 s, and a browser for two tests -->
```
$ .venv/bin/python -m pytest tests/ -q
15 failed, 53 passed in 132.10s (0:02:12)
```

68 tests collected. The 15 are exactly `analytics_privacy_test.py` and
`analytics_reports_test.py` (§5).

### 7.5 This report, self-verified

<!-- report-verify: measurement re-runs a report-verify pass over the report itself -->
`node tools/report-verify.mjs docs/reviews/canva-analysis-and-closure-report.md` —
0 mismatched, 0 elided, 0 skipped except the declared blocks above.

### 7.6 Bundle budgets

```
$ wc -c src/js/bundle-index-v15.js src/js/bundle-public-v15.js
1136115 src/js/bundle-index-v15.js
 251960 src/js/bundle-public-v15.js
1388075 total
```

Under budget (1 420 000 and 260 000). The loader change added ~450 bytes to the index
bundle and took it from 1 135 668 to 1 136 115.

### 7.7 `!important` per file

```
$ python3 -c "import subprocess,pathlib,operator;t=subprocess.run(['git','ls-files','*.css'],capture_output=True,text=True).stdout.split();d=[(f,pathlib.Path(f).read_text().count('!important')-subprocess.run(['git','show','HEAD~1:'+f],capture_output=True,text=True).stdout.count('!important')) for f in t if pathlib.Path(f).exists()];inc=[f for f,delta in d if operator.gt(delta,0)];print(f'tracked css files: {len(t)}');print(f'files whose !important count increased vs HEAD~1: {len(inc)}')"
tracked css files: 260
files whose !important count increased vs HEAD~1: 0
```

The comparison uses `operator.gt(delta, 0)` rather than a `>` literal because
`report-verify` is right to refuse a block that looks like it contains a shell
redirection, and this block is worth verifying rather than declaring.

Same result against the pass base `7ce64cc`: 0 files increased. Six mirror CSS files
*decreased* by 1–3 each, which is the mirror repair in §2, not a demotion.

### 7.8 Working tree

<!-- report-verify: historical the tree moves when this report is committed -->
```
$ git status --short
 M package-lock.json                       <- pre-existing (agent-browser, 09:41); not touched
 M package.json                            <- pre-existing; not touched
?? docs/STRUCTURE-PILOT-AUDIT.md           <- §6.3 of the prior report: leave alone
?? docs/reviews/deploy-02-linux.md         <- same
?? scripts/audit_bidi.js                   <- same
?? scripts/fix_structure_references.py     <- same
?? src/python/admin-page-v13.css           <- same
?? tests/ac4_2d_audit_test.py              <- same
```

The `<-` markers are this report's annotations, not git's output. The block was taken
while the pass's own evidence files were still unstaged; after this report's commit the
same command prints the tracked tree clean, with the six untracked files and the two
pre-existing `package*.json` modifications unchanged.

## 8. Retracted experiments and instrument corrections

Kept because a report that only lists what worked is not evidence.

1. **`bundle-line-map.py` was off by one line per chunk.** Joining the bundle's chunks
   with no separator means a chunk's last source line and the next chunk's first line
   share one bundle line. The tool now advances its counter only between source lines and
   `--verify` asserts each mapped source line's text occurs in the mapped bundle line.
   Before the fix it reported `11092 -> editor/editor-core.js:1340`, which is a comment.
2. **`forced-layout-attribution.mjs` over-counted twice**: it treated `.id` reads and
   `window.innerWidth` as layout-forcing, and it counted `classList.toggle(name, force)`
   as a write even when the state already matched. Three corrections before its output
   was acted on.
3. **The studio search fix was measured and retracted.** The top forced-layout site was
   `text()` in `studio-experience.js`, read after each iteration's `classList.toggle` in
   a search filter. Batch-reads implemented → the exercise trace was identical before and
   after (21 forced reads, both), because `classList.toggle` with a matching state is a
   **no-op** and never dirtied layout. Reverted; the retracted experiment remains in the
   evidence as `tools/evidence/forced-layout-exercise-{before,after}.txt`.
4. **`module-loading-strategy.mjs` reported 37 parser-blocking scripts** (§1.7). Fixed
   before anything was concluded from it; the correction is the reason the tool now
   prints `declared` and `DOM` as separate blocks.
5. **The analytics endpoint was wired and reverted.** `POST /api/analytics/events` was
   implemented against the model layer, took the passing set from 5 to 10, and was
   reverted when the remaining five failures turned out to need the same change to the
   dashboard's read model: half of a feature is worse than an honest red suite. §5
   records the decision and the inventory.
6. **`organized-resolution.txt`'s stale-bytes column was wrong in its first draft** — one
   row's number repeated across all five. Re-derived with
   `git show 1b1adf0:src/css/organized/<file> | wc -c`; the file now says so.
7. **Unanimity control 1 did not test what it looked like it tested** (flipping a run to
   load-bearing produces `keep`, not `unstable`, because `keep` is checked first).
   Control 2 was written to exercise the `unstable` branch specifically, and both are
   recorded.
8. **The layers-panel dynamic check did not detect the defect it guards** (§3) — kept as
   a labelled contract test rather than deleted, because the static half does detect it.

## 9. What this pass did not do

* **No analytics routing** (§5), by decision, with the gap enumerated.
* **No `!important` demotion** (§6), because the rule leaves nothing demotable.
* **No Canva editor analysis** (§1.13) — login was not attempted, deliberately.
* **No Style & Layout fix** — the gap is measured (2.7×) and its cause is not; acting on
  a guess here is how the retracted experiments in §8 happened.
* **`package.json` / `package-lock.json` untouched** (§1.3), and the six untracked files
  from §6.3 of the prior report left exactly where they were.

## 10. Commits

Ten commits, all on `main`, listed in §0. The three that change shipped code are
`2750ceb` (loader), `1b1adf0` (layers-panel guard, prior brief) and `2f6f6e6`
(`organized/`, prior brief); the rest are instruments, evidence, tests and this report.
