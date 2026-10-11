# Consolidation and fidelity pass — report

**Repo:** `einvite-platform` · **branch:** `main` · **base commit:** `00987f6`
**Commits produced:** `3ca3671` (Goal 1) + this pass's commit 2 (Goals 2–3)
**Date:** 2026-10-11

Three goals: raise design fidelity to Canva's **published** standard, consolidate
file sprawl, add the missing project infrastructure.

> **Headline caveat, stated up front.** Most of the numeric "Canva" values in the
> dispatch brief are **not published by Canva**. Canva's developer documentation
> publishes colour *token names* with no hex values, exactly two radius values,
> and no numeric durations or shadow values at all. Section 1.0 records what was
> actually found, with URLs. Everything below that is labelled `BRIEF-SUPPLIED`
> is a value from the dispatch brief and **not** a Canva-published value; nothing
> in this pass claims otherwise.

---

## 0. Verification commands and raw output

Run from the repo root.

```
$ python3 build.py all --check
EDITOR_BUNDLE_CHECK_PASSED
ROUTE_BUNDLE_CHECK_PASSED
PAGE_ASSET_MANIFEST_CHECK_PASSED
BUILD_OK editor bundles manifests (check)

$ python3 src/python/build/build_route_bundles.py --check
ROUTE_BUNDLE_CHECK_PASSED

$ python3 tests/v55_route_weight_budget_test.py
V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)

$ wc -c src/js/bundle-index-v15.js src/js/bundle-public-v15.js
1129296 src/js/bundle-index-v15.js      (budget 1,420,000)  PASS
 249994 src/js/bundle-public-v15.js     (budget   260,000)  PASS
```

Browser sweep over all 16 routes × 2 themes (harness `/tmp/goal1/pages.mjs`,
Chrome headless shell 154, `networkidle2` + 400 ms settle):

```
TOTAL: pages=32 consoleErrors=0 non2xx=0
```

---

## 1. GOAL 1 — Canva fidelity

### 1.0 What Canva actually publishes (researched 2026-10-11)

| Question | Answer | Source |
|---|---|---|
| Hex values for turquoise `#00C4CC`, blue `#2B8CFF`, purple `#8B3DFF`, pink `#FF4ECD`, gradient `#00C4CC → #7D2AE8` | **NOT PUBLISHED.** The guidelines describe "functional color palettes" and point at the App UI Kit; the Kit's colour reference lists token *names* (`colorActionPrimaryBg`, `colorActionPrimaryFg`, `colorContentFg`) and no values. The design-token overview states a token's value "is a CSS variable, **not** the underlying CSS value". | https://www.canva.dev/docs/apps/design-guidelines/ · .../design-guidelines/colors/ · .../app-ui-kit/colors/ · .../app-ui-kit/design-tokens/ |
| Type scale | **Title xsmall/small/medium/large = 14/16/20/24 px; Text xsmall/small/medium/large = 10/12/14/16 px.** Weights named regular/medium/bold, no per-size numeric mapping. Changelog: Title large line-height 42 → **40 px** (≥600 px viewports) and 32 → 30 px (below); Text large line-height 26 → 24 px; Title large/medium/small weight 700 → **600**; App UI Kit 4.0.0 removed the `xlarge` size. | https://www.canva.dev/docs/apps/design-guidelines/typography/ · .../app-ui-kit/changelog/ |
| 80 px / 64 px display steps | **NOT PUBLISHED.** | same |
| weight 400 at display sizes | **NOT PUBLISHED.** The brief's "CRITICAL INSIGHT" has no published source. | same |
| single `-0.01em` tracking across the scale | **NOT PUBLISHED.** | same |
| Spacing scale | **4/8/12/16/24/32/48/64/96 px** (tokens `space050`…`space1200`, 8 px base, 4 px half-unit). | https://www.canva.dev/docs/apps/app-ui-kit/spacing/ · .../design-guidelines/spacing/ |
| Radius | **only `radiusElementSharp` = 4 px and `radiusElement` = 8 px.** A 12 px button radius and a 24 px media radius are **NOT PUBLISHED** (12 and 24 appear in the *spacing* scale, which is a different token family). | https://www.canva.dev/docs/apps/app-ui-kit/spacing/ |
| Motion durations | **NOT PUBLISHED.** Only the names `hoverTransition` / `fadeTransition` (`--ui-kit-hover-transition`, `--ui-kit-fade-transition`) with no ms values. | https://www.canva.dev/docs/apps/app-ui-kit/transitions/ |
| Elevation | **NOT PUBLISHED.** Only `elevationSurfaceRaisedShadow` / `elevationSurfaceFloatingShadow`, no `box-shadow` values. | https://www.canva.dev/docs/apps/app-ui-kit/shadows/ |
| "card hover scales to 1.02" | **NOT PUBLISHED.** | — |
| `styles.refero.design/style/62f89392-…` | A **third-party** Refero Styles collection ("Canva design system \| Refero Styles"); not a Canva publication. It does name Canva Violet `#8b3dff`. | https://styles.refero.design/style/62f89392-609d-45b7-b9df-7a5acd529864 |
| `canvacreative.team/brand-typography` | **Not a `canva.com` / `canva.dev` host.** Self-describes as "Canva Creative Team"; domain ownership is not verifiable from the page. Treated as unofficial. | https://canvacreative.team/brand-typography |

**Consequence.** Goal 1 could only be executed against values Canva actually
publishes (spacing, two radii, the App UI Kit text/title sizes, the 700 → 600
Title weight). For everything else the brief's numbers are recorded in the source
of truth **with their provenance and their measured contrast**, rather than
silently adopted and called "Canva-aligned".

### 1.1 Task 1 — colour

**Decision: `--app-accent` was NOT re-pointed.** The brief's instruction was
conditional — "If your current accent is blue, change it" — and `--app-accent` is
this product's maroon `#8b465b`, not blue, so the condition never fires.
Re-pointing it to `#8B3DFF` would re-skin 16 pages on a value that Canva does not
publish, which is a redesign, and the brief forbids redesign.

**What was added** (`src/css/tokens.css`), as a named, documented reference layer
with zero consumers — the same pattern the previous pass used for `--radius-pill`
and the display type steps:

```
--canva-turquoise:#00C4CC;  --canva-blue:#2B8CFF;
--canva-purple:#8B3DFF;     --canva-pink:#FF4ECD;
--canva-gradient:linear-gradient(90deg,#00C4CC 0%,#7D2AE8 100%);
```

**Task 1c — contrast floors measured** (WCAG 2.1 relative luminance, sRGB, from
the raw hex values):

| pair | ratio | AA normal (4.5:1) |
|---|---|---|
| BRIEF `--ink-muted` #64748B on BRIEF `--surface-page` #F8FAFC | **4.55:1** | pass |
| BRIEF #64748B on white | 4.76:1 | pass |
| BRIEF `--ink-default` #334155 on #F8FAFC | 9.90:1 | pass |
| BRIEF `--ink-strong` #1E293B on #F8FAFC | 13.98:1 | pass |
| repo `--text-2` #646773 on `--surface-0` #f5f6f8 | 5.21:1 | pass |
| repo `--text-3` #6c707a on white | 4.96:1 | pass |
| BRIEF `--success` #16A34A on white | **3.30:1** | **fail** |
| repo `--success` #2b9b68 on white | 3.51:1 | fail (large only) |
| BRIEF `--warning` #D97706 on white | 3.19:1 | fail (large only) |
| BRIEF `--danger` #DC2626 on white | 4.83:1 | pass |
| repo `--danger` #c6404d on white | 4.95:1 | pass |
| BRIEF `--canva-turquoise` #00C4CC on white | **2.15:1** | **fail — unusable for text** |
| BRIEF `--canva-blue` #2B8CFF on white | 3.33:1 | fail (large only) |
| BRIEF `--canva-purple` #8B3DFF on white | 4.99:1 | pass |
| BRIEF `--canva-pink` #FF4ECD on white | 2.91:1 | fail (large only) |
| gradient end `#7D2AE8` on white | 6.23:1 | pass |

Two facts fall out of the table and are now recorded as comments next to the
tokens: `#00C4CC` **cannot carry text at all**, and swapping the repo's semantic
colours for the brief's would move `--success` from 3.51:1 to 3.30:1 (worse) and
`--danger` from 4.95:1 to 4.83:1 (worse). The repo's semantic set is therefore
kept.

`--canva-gradient` ships with **no consumers**; the brief's rule ("hero/identity
moments only, never the main CTA") means it needs a surface decision before it is
applied anywhere, and inventing one would be the redesign this pass forbids.

### 1.2 Task 2 — typography

Already satisfied by the base commit; verified, not re-done:

```
$ grep -n 'fw-display-lg\|fw-hero\|--tracking-tight\|--fw-title-lg' src/css/tokens.css
  --tracking-tight:-0.01em;
  --fs-title-lg:24px;  ... --fw-title-lg:600;
  --fs-display-lg:64px; --lh-display-lg:1.1; --ls-display-lg:var(--tracking-tight); --fw-display-lg:400;
  --fs-hero:80px;       --lh-hero:1.1;       --ls-hero:var(--tracking-tight);       --fw-hero:400;
```

Display steps are already weight 400, title weights are already 600 (which *is*
the published changelog value), and tracking is already one `--tracking-tight`
token for the title/display steps. **No change made.** The brief's claim that
Canva uses 400 at display sizes is not published (1.0), so the existing state —
which the base commit already documents as "LOCAL PRODUCT ADDITION, not a Canva
token" — is left as-is rather than re-justified.

`:lang(km)` already sets `letter-spacing: normal`, so Khmer is unaffected.

### 1.3 Task 3 — spacing and radius

| | brief | repo before | published Canva | action |
|---|---|---|---|---|
| spacing | 4·8·12·16·24·32·48·64·96 | all present incl. `--space-24:96px` | 4·8·12·16·24·32·48·64·96 | **no change needed** |
| `--radius-sm` | 8 px | 8 px | 8 px (`radiusElement`) | no change |
| `--radius-md` | 12 px | 8 px | **only 4 px and 8 px exist** | **kept at 8 px**; 12 px is unpublished |
| `--radius-lg` | 16 px | 16 px | unpublished | no change |
| `--radius-xl` | 9999 px | 16 px | unpublished | kept; its one consumer is `dialog`, and a pill-shaped modal would be a visible regression. `--radius-pill:9999px` already exists |
| `--radius-media` | 24 px | absent | unpublished | **added** to tokens.css, marked LOCAL PRODUCT ADDITION, consumer-free |

`--space-5:20px` and `--space-10:40px` are not in Canva's published set and were
kept (documented in tokens.css: 17 and 7 source declarations depend on them).

### 1.4 Task 4 — motion, elevation, `.card-hover`

**4a motion.** `--motion-1/2/3` raised from `120/180/240ms` to **`150/200/250ms`**,
so all three stops sit inside the brief's stated 150–250 ms envelope. Canva
publishes no durations (1.0), so the provenance comment says the values are
brief-supplied, not Canva-sourced.

**4b elevation.** The brief's target tokens `--shadow-1/-2/-3` have **zero
consumers in `src/css`** — measured:

```
$ for t in --shadow-1 --shadow-2 --shadow-3; do
    echo "$t: $(grep -ro "var($t[,)]" src/css --include='*.css' | grep -v bundle- | wc -l)"; done
--shadow-1: 0
--shadow-2: 0
--shadow-3: 0
```

The **live** elevation tokens are `--app-shadow-sm` / `--app-shadow` /
`--app-shadow-xl`, defined in `modern-ui.css` and used in 40 places. So:

* `--shadow-1` / `--shadow-2` were aligned to the brief's card pair anyway (a
  documented no-op), and `--shadow-card-hover` was added;
* `--app-shadow-sm` (the live card-rest token) was aligned to
  `0 2px 8px rgba(13,18,22,.08)` in both themes;
* `--app-shadow-card-hover: 0 8px 24px rgba(13,18,22,.12)` was added;
* `--app-shadow` (14 px/42 px) and `--app-shadow-xl` were **left alone** — they
  are this system's raised and floating layers, and the brief itself keeps
  floating "slightly larger".

**4c `.card-hover`.** Added in `tokens.css`:

```css
.card-hover{transition:transform var(--motion-2) var(--ease-out),box-shadow var(--motion-2) var(--ease-out),border-color var(--motion-2) var(--ease-out)}
.card-hover:hover,.card-hover:focus-within{transform:scale(1.02);box-shadow:var(--app-shadow-card-hover);border-color:var(--app-line-2)}
```

and applied to the two card-hover rules in `app-shell-v55.css` that actually win
the cascade (the generic card family, and the dashboard grid override), which
previously lifted with `translateY(-1px)` / `translateY(-2px)`:

```diff
 .card:hover, .invite-card:hover, .material-card-page:hover, .workspace-card:hover, .template-card:hover {
-  box-shadow: var(--app-shadow);
+  box-shadow: var(--app-shadow-card-hover);
   border-color: var(--app-line-2);
-  transform: translateY(-1px);
+  transform: scale(1.02);
 }
```

**Not converted, deliberately:** the ~15 ad-hoc hover lifts in
`canvas-plus.css`, `editor-suite.css`, `final-polish.css` and `modern-ui.css`.
They carry `!important` (or a spring easing) and they only render on `:hover` —
which the screenshot harness cannot capture. Changing them would be an
unverifiable behaviour change across nearly every page, so per the brief's
"if a change might break something … document what you tried" they are left and
listed in §4.

**4d reduced motion.** `app-shell-v55.css`'s `@media (prefers-reduced-motion:
reduce)` block now neutralises every lift in the sheet, including the new
utility:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms; transition-duration:.01ms; scroll-behavior:auto; }
  .skeleton::after { animation: none; }
  /* §1.5d — every hover lift in this sheet is neutralised, including the
     canonical .card-hover utility defined in tokens.css. */
  .card-hover, .card-hover:hover, .card-hover:focus-within,
  .card:hover, .invite-card:hover, .material-card-page:hover,
  .workspace-card:hover, .template-card:hover { transform: none; }
}
```

### 1.5 Goal 1 verification — no visual regression

Method: a `git worktree` of `00987f6` served beside the working tree, both
captured with the same puppeteer harness (reduced motion emulated, animations and
transitions frozen), 4 pages × 2 themes × 2 viewports = 16 captures per tree.

```
page       theme vp           diff       before        after  sameDims
account    dark  desktop    0.000% 1920x1283   1920x1283        True
account    dark  laptop     0.000% 1366x971    1366x971         True
account    light desktop    0.004% 1920x1283   1920x1283        True
account    light laptop     0.007% 1366x971    1366x971         True
dashboard  dark  desktop    0.000% 1920x1080   1920x1080        True
dashboard  dark  laptop     0.000% 1366x941    1366x941         True
dashboard  light desktop    0.004% 1920x1080   1920x1080        True
dashboard  light laptop     0.007% 1366x941    1366x941         True
index      dark  desktop    1.227% 1920x1080   1920x1080        True
index      dark  laptop     0.000% 1366x768    1366x768         True
index      light desktop    0.000% 1920x1080   1920x1080        True
index      light laptop     0.000% 1366x768    1366x768         True
public     dark  desktop    0.000% 1920x5440   1920x5440        True
public     dark  laptop     5.210% 1366x5440   1366x5440        True
public     light desktop    0.000% 1920x5440   1920x5440        True
public     light laptop     0.000% 1366x768    1366x768         True

max diff: 5.210% public-dark-laptop.png sameDims= True
any dim change: NONE
```

**No capture changed dimensions**, so no layout moved. The two outliers were then
chased down rather than waved away:

**(a) `index.html` is nondeterministic.** Two independent captures of the *same*
tree differ by up to **1.901%**; the before/after delta of 1.227% is below that
noise floor:

```
charging the same tree twice (working tree):
  index-dark-desktop 1.901%   index-dark-laptop 0.564%
  index-light-desktop 0.506%  index-light-laptop 0.379%
  everything else 0.000%
```

**(b) `public.html` has a two-state render race.** Five captures per tree,
`public/dark/1366x768`:

```
         w1      w2      w3      w4      w5      b1      b2      b3      b4      b5
  w1      -  5.210%  5.210%  5.210%  5.210%  0.000%  5.210%  5.210%  5.210%  0.000%
  b1 0.000%  5.210%  5.210%  5.210%  5.210%       -  5.210%  5.210%  5.210%  0.000%
  (w = working tree, b = HEAD worktree; A-vs-B is exactly 5.210%)
```

Both states occur on **both** trees, so the 5.210% delta is the page's own race,
not a regression. (The differing band is `SECTION.guest-feature.signup-sheets`
and `.polls`, both 748 px tall in both states.)

**(c) Element-level proof, guest page, 260 elements** — dump of computed style +
geometry per element from both trees, compared index by index:

```
elements: 260 260
[32] BUTTON.active top=14
      boxShadow: none -> rgba(0, 0, 0, 0.24) 0px 2px 10px 0px
[116] DIV.venue-card primary-venue top=1935
      boxShadow: none -> rgba(0, 0, 0, 0.24) 0px 2px 10px 0px
total elements with a computed-style or geometry difference: 2 of 260
```

Only the two intended `--app-shadow-sm` changes; **zero geometry differences**.

**(d) Isolation experiment.** My two changed CSS files copied into a pristine
HEAD checkout and rebuilt: `bundle-public-v15.css` is byte-identical to the
working tree's (128 843 B, sha equal after CRLF normalisation) and the render
difference versus HEAD is **0.0075%**.

---

## 2. GOAL 2 — consolidation

### 2.1 Task 5 — repo-root tooling

**Before** (`wc -c *.py`):

```
 433 build_editor_bundle.py     intact forwarder
  76 build_page_manifests.py    truncated: only 2 lines, no imports -> NameError
  75 build_route_bundles.py     truncated: only 1 line,  no imports -> NameError
4188 sec04_behavior_test.py
1179 server.py
```

**After:** one entry point, three deprecation shims.

`build.py` (new, repo root) with subcommands and a documented dependency order
(`manifests` must run last because it measures the bundles' byte sizes on disk):

```
python3 build.py editor | bundles | manifests | all     [--check]
```

The three repo-root scripts are now thin shims that delegate to
`src/python/build/` and print a deprecation notice. They are **kept** rather than
deleted because tests and CI call them by filename; two of them are load-bearing
in a non-obvious way, which the audit found:

* `tests/v14_performance_budget_test.py` does `import build_page_manifests as
  manifests` and calls `manifests.build()` — so the shim re-exports the
  generator's public surface via `importlib`, not just its CLI;
* `tests/build_integrity_test.py`, `tests/v15_integration_hardening_test.py`,
  `tests/v16_windows_ui_hardening_test.py`, `tests/v27_3_4_repair_contract_test.py`
  and `tests/v27_3_5_release_evidence_test.py` shell out to the root filenames.

**Callers fixed** (all previously pointing at paths that do not exist):

| caller | before | after |
|---|---|---|
| `.pre-commit-config.yaml` (`bundle-check`) | `python3 src/python/build_route_bundles.py --check` — **path missing** | `python3 build.py bundles --check` |
| `src/python/release_check.py` (11 call sites) | `build_editor_bundle.py` etc. with `cwd=src/python` — **path missing, gate was dead** | `build/build_editor_bundle.py` etc. |
| `src/python/release_check_v28.py` (5 call sites) | same | same |
| `README.md` | `python3 src/python/build_route_bundles.py` / `build_editor_bundle.py` — **both missing** | `python3 build.py all` + `make` targets |

**Verification:**

```
$ python3 build.py bundles --check     -> ROUTE_BUNDLE_CHECK_PASSED
$ python3 build.py manifests           -> WROTE page-assets-v15.json
$ python3 build.py all --check         -> EDITOR_BUNDLE_CHECK_PASSED
                                          ROUTE_BUNDLE_CHECK_PASSED
                                          PAGE_ASSET_MANIFEST_CHECK_PASSED
$ python3 build_route_bundles.py --check
deprecated: build_route_bundles.py has moved — use 'python3 build.py bundles'
ROUTE_BUNDLE_CHECK_PASSED
$ python3 -c "import build_page_manifests as m; print(m.build().keys())"
build() ok, pages: 16 routes: 5
$ python3 tests/v14_performance_budget_test.py
AssertionError: ('dashboard', 'dashboard.html', 'styles', 2, 1)
$ python3 tests/v55_route_weight_budget_test.py
V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)
```

`v14_performance_budget_test.py` **now runs** (the `NameError` is gone) and
reports a real, pre-existing budget violation — see §4.1. It is not a pass.

**Bonus repair.** `build.py editor --check` was **red at the base commit** and is
now green. The editor bundle's staleness was proven, by a rule-level parse of
both versions, to be nothing but the position of the `@layer components {` line
relative to the `/* ===== canvas-plus.css ===== */` marker comment — 437 parsed
rules in both, identical `(layer-path, selector)` sequence modulo that one
comment-adjacent pseudo-rule, and identical byte length (61 298 B). Regenerating
therefore changes no rendered rule.

### 2.2 Task 6 — CSS consolidation

**Dead-file test.** Reference search over every code file in the repo
(`src/js`, `src/html`, `src/python`, `tests`, `scripts`, `.github` — 979 files),
counting any occurrence of the basename. 9 files had **zero** references:

| file | size |
|---|---|
| `src/css/editor-canvas-core.css` | 7 421 B |
| `src/css/editor-ui-layout.css` | 10 006 B |
| `src/css/editor/canvas.css` | 14 029 B |
| `src/css/organized/workflow-creation-flow-v3.css` | 6 386 B |
| `src/css/pages/admin.css` | 5 229 B |
| `src/css/pages/dashboard.css` | 6 441 B |
| `src/js/editor/canvas/viewport.js` | 9 880 B |
| `src/js/editor/chrome/context-menu.js` | 13 945 B |
| `src/js/pages/auth/sessions.js` | 11 384 B |

All 9 were archived to `/tmp/removed-src/` (preserving relative paths) and
`git rm`'d, together with their two served mirrors
(`src/python/editor-canvas-core.css`, `src/python/editor-ui-layout.css`). 11 files,
3 243 deleted lines. Re-running the dead-file test afterwards reports
**0 remaining zero-reference source files**.

**What was NOT done, and why.**

* **`src/css/organized/` was not removed.** The brief expected it to be dead
  artifacts; it is not. It holds 20 files that are live via
  `organized/styles.css` (`@import`s plus the `styles.css` entry that every page
  bundle lists) and via JS lazy loaders. Removing it would break 16 pages.
* **Version suffixes were not dropped.** 93 CSS and 100 JS files carry `-vNN`.
  Every one of them is a *current* source: it appears either in
  `docs/route-bundle-sources-v15.json` or in a page's lazy-loader list. Renaming
  them means editing the manifest, the loader strings, the mirror trees and ~40
  test files that assert on the filenames — a behavioural change whose blast
  radius this pass cannot verify, and the brief says to report rather than force
  a task that turns into a redesign. Recommended as its own pass, driven by the
  manifest.

### 2.3 Task 7 — JS consolidation

Same method and same result as 2.2: 3 JS files had zero code references and were
retired (§2.2). The co-loaded module-cluster merges the brief suggests
(`src/js/editor/{canvas,chrome,collab,media,text,history}`, `src/js/pages/admin/*`)
were **not** attempted: every one of those files is referenced by at least one
test by name (`tests/editor_chrome_collab_test.py`,
`tests/editor_text_media_test.py`, `tests/editor_alignment_guides_test.py`,
`tests/build_integrity_test.py`), so merging them means editing the tests that
pin them, which converts a file-count exercise into a contract change. §4.4 lists
the cluster that looks genuinely dead and needs a decision.

### 2.4 File counts

```
                                    before   after   delta
find src/css -name '*.css'            134     128     -6
find src/css -name '*-v*.css'          94      93     -1
find src/js -name '*.js' ! bundle-*   209     206     -3
find src/js -name '*-v*.js' !bundle-* 100     100      0
find . -maxdepth 1 -name '*.py'         5       6     +1   (build.py)
```

`git diff --stat HEAD` for the consolidation commit: **26 files changed, 187
insertions(+), 3 331 deletions(-)**.

Honest framing: the reduction is **9 source files / 3 243 lines**, not the
"30–40% of `src/js`" the brief hoped for. The reason is measured, not assumed —
194 of the 194 versioned files are live, and the 9 that were not are gone.

---

## 3. GOAL 3 — infrastructure

| artifact | state | notes |
|---|---|---|
| `build.py` | **new** | the single documented entry point (§2.1) |
| `Makefile` | **new** | `build`, `check`, `test`, `serve`, `dev`, `perf`, `clean`, `help` |
| `.nvmrc` | **new** | `22` (current LTS; the local toolchain this pass was verified with). CI's Lighthouse job pins `20` — the divergence is noted in CONTRIBUTING.md rather than silently changing CI |
| `CONTRIBUTING.md` | **new** | setup, build, tests, six hard rules, the directory map, and a "where does new code go" decision tree |
| `README.md` | **updated** | the Development section now uses `build.py`/`make`; the two stale `src/python/build_*.py` paths are gone; the directory section marks generated files; links to CONTRIBUTING.md |
| `docs/reviews/consolidation-and-fidelity-report.md` | **new** | this document |

```
$ make check
python3 build.py bundles --check
ROUTE_BUNDLE_CHECK_PASSED
BUILD_OK bundles (check)

$ make build
python3 build.py all
EDITOR_BUNDLE_BUILT
WROTE 16 route bundles
WROTE page-assets-v15.json
BUILD_OK editor bundles manifests
```

---

## 4. Findings surfaced but deliberately not fixed

### 4.1 Four of sixteen pages already exceed a published route budget

Measured twice — once at a pristine `00987f6` worktree, once after my changes:

```
HEAD 00987f6 (fresh build in a pristine worktree)
  FAIL account-admin  privacy.html    4/3 scripts  1/1 styles  168691/470000 B
  FAIL dashboard      dashboard.html  3/3 scripts  2/1 styles  650186/460000 B  (+190186)
  FAIL editor         index.html      3/3 scripts  1/1 styles 1614088/1420000 B (+194088)
  FAIL public-guest   public.html     2/1 scripts  1/1 styles  379902/260000 B  (+119902)
pages violating a published budget at HEAD: 4 of 16

after this pass
  FAIL account-admin  privacy.html    4/3  1/1   170012/470000 B
  FAIL dashboard      dashboard.html  3/3  2/1   651405/460000 B  (+191405)
  FAIL editor         index.html      3/3  1/1  1615307/1420000 B (+195307)
  FAIL public-guest   public.html     2/1  1/1   381086/260000 B  (+121086)
pages violating a published budget: 4 of 16
```

The violation set is **identical before and after**, so nothing here was caused
by this pass. My change does add **~1.2 KB per route** (the new tokens),
which moves every over-budget number slightly further over; that is stated rather
than hidden. The budgets were **not** raised: raising a ceiling to green a gate is
what the ceiling exists to prevent. `/tmp/goal2-budget.txt` and
`/tmp/goal2-budget-HEAD.txt` hold the full tables. `tests/v14_performance_budget_test.py`
cannot pass until this is addressed, which is now visible instead of being masked
by a `NameError`.

### 4.2 `dashboard.html` loads two stylesheets; its budget says one

`src/html/dashboard.html` links `bundle-dashboard-v15.css` **and** `toast.css`.
`toast.css` is genuinely *not* in the bundle (`.toast-stack`, `.toast--visible`,
`.toast--leave` are absent from `bundle-dashboard-v15.css`), so this is a second
render-blocking request, not a duplicate inlining. Either the page's style count
is 2 in reality and the budget is stale, or `toast.css` belongs in the route
bundle. Both are real fixes; neither was applied because (a) whichever is chosen,
the same page still fails on bytes, so the gate stays red, and (b) moving a sheet
into or out of a bundle changes cascade order on a live page. Recorded as the
first thing to do when the budgets are next re-baselined.

### 4.3 The editor bundle exists in three places, and the generator writes two

```
 src/css/editor-suite.css          <- written by the generator (mirror)
 src/python/build/editor-suite.css <- written by the generator
 src/python/editor-suite.css       <- NOT written by the generator; hardlinked to src/css/
```

At the base commit the first two disagreed (61 298 B with a layer wrapper vs
61 385 B with none) and the third was a stale hardlink. `index.html` links only
`bundle-index-v15.css`, so the divergence is currently inert for rendering, and
regenerating converges the first two. The served copy at `src/python/editor-suite.css`
is left untouched deliberately: writing it would be hand-editing a generated
artifact, which the hard rules forbid. The generator's own docstring still
describes the pre-move layout (`script_dir = src/python/`), which is the root
cause; fixing it means editing a generator, and the outcome is a third served
copy of a bundle nothing links.

### 4.4 A suspected whole dead subsystem: `src/js/editor/**`

20 files under `src/js/editor/` (`canvas/`, `chrome/`, `collab/`, `media/`,
`text/`, `history/`) are referenced **only** by test files and docs — never by the
bundle manifest, a page, or a lazy loader. Two of them were already fully
unreferenced and are gone (§2.2). The remaining 18 are pinned by
`tests/editor_chrome_collab_test.py` and `tests/editor_text_media_test.py`, which
appear to assert on them as files. **Decision needed:** if that subsystem is
superseded by `editor-suite.js`, retiring it (and rewriting those two tests)
removes 18 files; if the tests are the only thing keeping it alive, the tests are
the finding and the code should be deleted. Not actioned here because it is a
contract change, not a move.

### 4.5 Untracked file at the served root

`src/python/app-shell-v55.css` (53 043 B) is **untracked** and is written by no
generator (`grep -rn 'app-shell-v55' src/python/build/*.py` → no hits). It is not
requested by any page (0 hits in the server access logs across 32 page loads), so
it is inert, but a generated-looking asset that is not reproducible from a clone
is a trap. Left in place; it should be either regenerated by
`sync_frontend_assets.py` or removed.

### 4.6 `public.html` renders in two states under the same conditions

Reproduced in §1.5(b): two stable renders differing by 5.210%, both reachable on
both trees, in `SECTION.guest-feature.signup-sheets` / `.polls`. Same input, same
wait condition, two outputs. This is a real race in the guest page's feature
sections and it will make every future screenshot-based regression test on that
page unreliable — which is why this pass had to build a bimodality control rather
than trust a single pair.

### 4.7 Stale build command in a generated registry

`assets/fonts/registry.json:336` (and its `src/python/` mirror) tell the reader to
"Re-run `python3 src/python/build_route_bundles.py`" — a path that has never
existed. The string is generated by that registry's own generator, so fixing it
means editing that generator; left alone and reported.

---

## 5. Autonomous decisions taken (and why)

1. **Did not re-skin the accent to Canva purple.** The brief's instruction was
   conditional on the accent being blue; it is maroon. Canva publishes no palette.
   Re-skinning 16 pages on an unpublished value is the redesign the brief forbids.
2. **Shipped `--canva-*` and `--canva-gradient` as documented, consumer-free
   tokens** rather than applying them, because applying the gradient needs a
   "hero/identity moment" decision that the brief reserves for itself.
3. **Kept the repo's semantic colours** after measuring that the brief's set is
   worse for `--success` (3.30 vs 3.51) and `--danger` (4.83 vs 4.95).
4. **Kept `--radius-md: 8px`** instead of the brief's 12 px, because Canva
   publishes only 4 px and 8 px, and the brief's own rule is to prefer the
   authoritative source.
5. **Aligned `--motion-*` to the brief's 150/200/250 ms** even though Canva
   publishes no durations, because the brief states the envelope and 120 ms sat
   outside it.
6. **Left `--shadow-1/-2/-3` in place after proving they have no consumers**, and
   instead fixed the live `--app-shadow-sm`, documenting why.
7. **Did not convert the `!important` hover lifts**, because `:hover` states are
   outside what the screenshot harness can verify.
8. **Regenerated the editor bundle** after proving at rule level that the change
   is only the position of the `@layer` opener relative to a comment — it turned a
   red gate green with no rendered-rule change.
9. **Kept the deprecated root forwarders as working shims** instead of deleting
   them, because 5 test files and 16 release-check call sites reference them.
10. **Did not touch the route budgets**, four of which are already violated at the
    base commit; reported with before/after tables instead.
11. **Did not meet two of the brief's acceptance targets, and did not fake them.**
    The verification list asks for `find src/css -name '*-v*.css' | wc -l` and the
    JS equivalent to come back "0 or near 0". They are 93 and 100. Forcing that
    number down means renaming live files (§2.2) or merging files that tests pin
    by name (§2.3) — a contract change this pass cannot verify. The targets are
    reported as unmet rather than approximated.
12. **Wrote the commit messages from what was actually done, not from the brief's
    drafts.** Both drafts assert changes that this pass did not make — e.g.
    "display weights changed to 400 (was 700)" and "Radius: 8/12/16/9999 (was
    10/14/20/28)". The first was already true at the base commit, and the second
    was deliberately declined because Canva publishes neither 12 px nor 9999 px
    (§1.3). Committing the supplied text verbatim would have put two false
    statements in the permanent record; the scope, the two commits and the footer
    are otherwise as specified.

---

## 6. Verification matrix

| check | command | result |
|---|---|---|
| all three generators, check mode | `python3 build.py all --check` | **PASS** (3 markers) |
| route bundles | `python3 src/python/build/build_route_bundles.py --check` | **PASS** |
| repo-root shims still work | `python3 build_route_bundles.py --check` etc. | **PASS** |
| import API preserved | `import build_page_manifests; m.build()` | **PASS** (16 pages, 5 routes) |
| route weight budgets | `python3 tests/v55_route_weight_budget_test.py` | **PASS** |
| per-route byte budgets | `python3 tests/v14_performance_budget_test.py` | **FAIL — pre-existing, §4.1** |
| bundle hard budgets | `wc -c src/js/bundle-{index,public}-v15.js` | **PASS** (1 129 296 / 249 994) |
| no new `!important` | per-file `!important` count, every `src/css` file, `HEAD~1` vs `HEAD` | **32 922 → 32 830 (−92)**; files increased: NONE |
| versioned CSS files | `find src/css -name '*-v*.css' \| wc -l` | 93 (target "near 0" **not met** — §2.2) |
| versioned JS files | `find src/js -name '*-v*.js' -not -name 'bundle-*' \| wc -l` | 100 (target "near 0" **not met** — §2.3) |
| 16 pages × 2 themes | `/tmp/goal1/pages.mjs` | **PASS** (0 console errors, 0 non-2xx) |
| visual regression | 16-capture before/after pair + determinism + bimodality controls | **PASS** (§1.5) |
| dead-file sweep | zero-reference scan, 979 code files | **9 → 0** |
| Python syntax | `python3 -m py_compile` on all changed `.py` | **PASS** |

The `!important` figure is a per-file count over every `src/css/**/*.css` blob at
each commit, not a `git diff | grep` (which over-counts, because the route bundles
re-emit whole single-line minified sheets). Raw output in
`/tmp/goal2-important.txt`: no file's count increased; the 92-declaration drop is
entirely the retired files (`organized/workflow-creation-flow-v3.css` −76,
`editor/canvas.css` −11, `pages/dashboard.css` −3, and one each for the other
three removed CSS files).

### Limitations

* The editor bundle's rule-level equivalence was proven by **parse**, not by
  rendering: `index.html` is nondeterministic at up to 1.901% (§1.5a), so a
  pixel-based check could not distinguish "no change" from "noise".
* The visual no-regression proof covers 4 pages × 2 themes × 2 viewports, not all
  16 routes.
* `:hover` states are not covered by any automated check in this pass (§1.4c).
* `lhci autorun` was not executed (no `@lhci/cli` in this environment); the
  Lighthouse scaffold is unchanged from the previous pass.

### Artifacts kept outside the repo

* `/tmp/removed-src/` — the 11 retired files, for review before they are gone for good.
* `/tmp/goal1/SUMMARY.txt`, `/tmp/goal1/diff2.txt`, `/tmp/goal1/determinism-control*.txt`,
  `/tmp/goal1/style-diff.txt` — the raw Goal 1 measurements.
* `/tmp/goal2-budget.txt`, `/tmp/goal2-budget-HEAD.txt` — the budget tables.
* `/tmp/task-consolidation/dead-strict.txt`, `dead-analysis.txt` — the reference sweeps.
