# Repairing the instruments: the lift probe's three defects, the trace's own stack, and the flag test's dead branch

This is the report for the pass that ran on branch `main` over base `7e97f57`. It is
written to the standard of `docs/reviews/analytics-and-unanimity-report.md`, the house
standard: every number is printed next to the command that produced it, raw evidence is
in `tools/evidence/`, and every experiment that failed or was retracted is kept with its
reason instead of being deleted.

Re-verify the quotes in this file with
`node tools/report-verify.mjs docs/reviews/instrument-repair-report.md`; §7 records what
that run reported. A block marked with a `<!-- report-verify: … -->` declaration is one
the gate cannot re-run (it needs a server, a browser, or minutes of wall clock);
everything else in a `$`-block is re-run and byte-compared.

The brief this pass answers opened with its predecessor's own diagnosis, and it was
right:

> The instrumentation itself is now the limiting factor: two of this pass's three
> blocked goal-3 paths failed because a probe measures at the wrong moment, not because
> the code is wrong. The codebase is in better shape than its measuring devices are.

Four goals, in the brief's priority order: make the lift probe's verdict stable and act
on what it says; make the performance trace attribute the Style & Layout gap; resolve the
flag test's unreachable 200-branch; and, if time permitted, extend the Canva analysis to
the public template surfaces. All four were attempted.

What happened is mostly **instrument repair, and one demotion**: the lift probe had
three defects, not one. The sampling defect the brief named; a second defect in which
the probe swept its own self-check fixture as a live target; and a third in which it
called a declaration inert on elements that have no box and so cannot be observed at all.
The third one had produced a unanimous, reproducible, and completely wrong "demotable"
verdict on the prior pass's own tooling — the exact class of finding this pass existed to
catch. Fixing all three produced a different candidate, which is demoted in §1.6 on four
independent checks, and the theme-menu declaration the sweep had called unanimous is
retracted in §1.7 with the measurement that retracts it.

## 1. Goal 1 — the lift probe, and the one declaration it authorizes

### 1.1 The before state: a verdict that was a function of when it was read

`tools/important-lift-test.mjs` forced a state with CDP `CSS.forcePseudoState` and read
the complete computed style on the next line, undoing the force on the line after that.
A property with a running transition is then read **mid-interpolation**, so the
per-declaration verdict is a per-run observation rather than a property of the tree.
`lib/browser.mjs`'s `freezeMotion()` zeroes `transition-duration`, but the route bundles
re-declare `transition:…!important` at a higher specificity and win that cascade — which
is why `tools/hover-audit.mjs` had already been taught to wait for animations.

Two runs of the defective probe on the same page and the same tree:

```
$ python3 tools/lift-verdict-compare.py --max-selector=64 artifacts/lift-index-before-run1.json artifacts/lift-index-before-run2.json | head -8
LIFT_VERDICT_COMPARE files=2 declarations=59 flips=3
  artifacts/lift-index-before-run1.json                redundant=8 loadBearing=23 unmeasured=33
  artifacts/lift-index-before-run2.json                redundant=5 loadBearing=26 unmeasured=33

R = redundant here (removal changed nothing)   L = load-bearing (removal changed a value)
U = unmeasured here (no element on the page reaches the rule)   ? = absent from that file

          L4    L4   background    .ei-context-overflow button:hover
```

Five runs over the same page and tree split on three declarations
(`.studio-rail-button:hover` `background`, the same rule's `color`, and
`.flow-action-grid button:hover` `transform`), and the diff counts of the declarations
that did *not* flip wobbled too — 9 to 98 on one `transform`. The full record, including
the prior pass's three runs on the pre-demotion tree, is
`tools/evidence/instrument-repair-lift-stability.txt`.

### 1.2 The fix: WHEN the read happens, not what is measured

`tools/lib/motion-settle.mjs` — one frame, every *finite* running animation on the
elements about to be read, then two more frames — is injected the same way
`lib/css-decl.js` is, and `settleAll()` is called inside `CAPTURE` and `CAPTURE_STATE`
before any value is read. Infinite animations (spinners, `forwards` ripples) are
excluded, and a per-element cap keeps one stuck element from stalling the sweep.

The probe reports how often motion was actually in flight, so "the fix ran" is a
measurement rather than an assumption:

```
$ python3 tools/lift-verdict-compare.py --max-selector=64 artifacts/goal1/lift-index-after-run1.json artifacts/goal1/lift-index-after-run2.json artifacts/goal1/lift-index-after-run3.json | head -4
LIFT_VERDICT_COMPARE files=3 declarations=59 flips=0
  artifacts/goal1/lift-index-after-run1.json           redundant=5 loadBearing=26 unmeasured=33 settle={"calls": 544, "elementsSettled": 53023, "motionFound": 1216}
  artifacts/goal1/lift-index-after-run2.json           redundant=5 loadBearing=26 unmeasured=33 settle={"calls": 544, "elementsSettled": 53023, "motionFound": 1210}
  artifacts/goal1/lift-index-after-run3.json           redundant=5 loadBearing=26 unmeasured=33 settle={"calls": 544, "elementsSettled": 53023, "motionFound": 1216}
```

Zero flips, and not merely agreement on the verdict: every diff count is identical
across the three runs. `motionFound` 1216/1210/1216 says the wait was exercised on every
run rather than merely present in the source. Three runs, same verdict — the pass's own
stability rule, satisfied before anything was acted on.

### 1.3 A second defect, found by chasing the first one's output

The fixed probe's demotable set had exactly one declaration in it, and it was
`.ui-theme-menu button:hover` `transform`. Chasing that row produced a defect nobody was
looking for: **the probe was sweeping its own self-check fixture.** The self-check reads a
real rule out of `src/css/modern-ui.css`, injects it, and synthesizes a DOM for it —
`div.ui-theme-menu.decl-fixture-host > button`. That element matches the very selector the
fixture is about, so it joined the sweep's target set, and the fixture's copy of the rule
was enumerated as a second candidate with the same selector text:

```
$ sed -n '20,25p' tools/evidence/instrument-repair-lift-visibility.txt
v3 (before) lift-dashboard.json: rows=4 [transform affected=3 rendered=n/a] [background affected=3 rendered=n/a] [transform affected=3 rendered=n/a] [background affected=3 rendered=n/a]
v3 (before) lift-dashboard.run2.json: rows=4 [transform affected=3 rendered=n/a] [background affected=3 rendered=n/a] [transform affected=3 rendered=n/a] [background affected=3 rendered=n/a]
v3 (before) lift-dashboard.run3.json: rows=4 [transform affected=3 rendered=n/a] [background affected=3 rendered=n/a] [transform affected=3 rendered=n/a] [background affected=3 rendered=n/a]
v4 (after) lift-dashboard.json: rows=2 [background affected=2 rendered=0] [transform affected=2 rendered=0]
v4 (after) lift-dashboard.run2.json: rows=2 [background affected=2 rendered=0] [transform affected=2 rendered=0]
v4 (after) lift-dashboard.run3.json: rows=2 [background affected=2 rendered=0] [transform affected=2 rendered=0]
```

Before the fix the probe reported each declaration twice and counted one element more than
the page has; after it, each declaration once, on the page's own two elements. The fixture
is now torn down before the sweep runs, and the probe asserts it is gone (1 sheet + 1 host
removed, 0 left) or exits non-zero:

```
$ grep -n 'decl-fixture-host' tools/important-lift-test.mjs
250:  wrap.className = 'ui-theme-menu decl-fixture-host';
255:  return { selector: '.decl-fixture-host button', ok: !!document.querySelector('.decl-fixture-host button') };
387:// synthesized host is `div.ui-theme-menu.decl-fixture-host > button` — a REAL,
392:// `button rects=1 hidden=false parent=div.ui-theme-menu.decl-fixture-host`, i.e. the
401:  for (const el of [...document.querySelectorAll('.decl-fixture-host')]) { el.remove(); removed.hosts++; }
406:    fixtureHostsLeft: document.querySelectorAll('.decl-fixture-host').length,
```

The effect was not cosmetic. Across the 16-page sweep the fixture inflated the candidate
count (424 → 363 declarations) and moved verdicts in **both** directions: on dashboard it
had manufactured a `load-bearing` verdict for `background` out of a diff on the scaffold
button, and on the theme rule it hid the real elements behind a rendered one.

### 1.4 A third defect: a verdict read where nothing is observable

Every element `.ui-theme-menu button:hover` reaches is inside a `display:none` subtree —
the theme menu carries `[hidden]` until a user opens it. **Chrome does not resolve used
values for an element with no box**: `transform` reads `none` whatever the cascade says,
so removing the declaration returned an identical snapshot in every run, on every page,
every time. The unanimity was real and the verdict was still wrong:

```
$ sed -n '62,72p' tools/evidence/instrument-repair-lift-visibility.txt
cmd: python3 - (the declaration's row, per sweep, with the new fields)
v3 (before) lift-index.json: bucket=redundant diffs=0 affected=3 rendered=n/a note=
v3 (before) lift-index.json: bucket=redundant diffs=0 affected=3 rendered=n/a note=
v3 (before) lift-index.run2.json: bucket=redundant diffs=0 affected=3 rendered=n/a note=
v3 (before) lift-index.run2.json: bucket=redundant diffs=0 affected=3 rendered=n/a note=
v3 (before) lift-index.run3.json: bucket=redundant diffs=0 affected=3 rendered=n/a note=
v3 (before) lift-index.run3.json: bucket=redundant diffs=0 affected=3 rendered=n/a note=
v4 (after) lift-index.json: bucket=unmeasured diffs=0 affected=2 rendered=0 note=2 element(s) reached, none rendered (no box: a display:none subtree),
v4 (after) lift-index.run2.json: bucket=unmeasured diffs=0 affected=2 rendered=0 note=2 element(s) reached, none rendered (no box: a display:none subtree),
v4 (after) lift-index.run3.json: bucket=unmeasured diffs=0 affected=2 rendered=0 note=2 element(s) reached, none rendered (no box: a display:none subtree),

```

The probe now counts which of the elements a rule reaches have a box, reports it on every
row (`rendered`), and classifies a declaration whose elements are all boxless as
**unmeasured** with the reason — so it can never be pooled into a unanimous demotion
again. The gate is on the *trigger*, the element whose state is forced: a subject without
a box cannot produce a diff either, so it cannot turn an unobservable read into an
observable one. (The first version of this gate also counted a target whose *subjects* had
a box; that over-counted on index.html, where the page has 340 form controls and 3 with a
box. Corrected before the demotion in §1.6 was decided, and the corrected counts are in
§1.5.)

This is a precondition on the *observation*, not a change to what is measured: every read
is the same complete computed style, at the same settled moment, as in §1.2.

### 1.5 The sweep on the corrected probe

`python3 tools/hover-verify.py --all --lift --lift-runs=3 --jobs=4` and
`python3 tools/hover-verify.py --cross-page`: 16 pages × 3 runs = 48 lift runs, plus 16
hover audits. Three sweeps are worth stating, because each isolates one change:

| sweep | probe / tree | declarations (distinct) | demotable | keep | no evidence | unstable |
| --- | --- | --- | --- | --- | --- | --- |
| prior pass | v2 | 60 | 1 | 31 | 28 | 0 |
| this pass, sampling fixed | v3 | 59 | 1 (`.ui-theme-menu button:hover` `transform`) | 30 | 28 | 0 |
| this pass, fixture + visibility fixed | v4, pre-demotion | 59 | 1 (`input:hover, textarea:hover, select:hover` `border-color`) | 20 | 38 | 0 |
| this pass, final tree | v4b + the demotion of §1.6 | 58 | **0** | 17 | 41 | 0 |

The last row is the end state: with the two probe defects fixed *and* the one verified
demotion applied, there is no unanimous demotable declaration left in the sweep's reach,
and the demoted rule is no longer a candidate at all (it has no priority to weigh).

Per-page totals across the sweep (`HOVER_VERIFY_TOTAL`), and the cross-page verdict on
the v4 sweep that produced the candidate of §1.6:

```
$ sed -n '147,150p' tools/evidence/instrument-repair-demotion-applied.txt
LIFT_CROSS_PAGE {"pages": 16, "runsPerPage": {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}, "minRunsPerPage": 3, "declarations": 59, "demotable": 1, "keep": 20, "noEvidence": 38, "unstable": 0}
--- DEMOTABLE (inert in EVERY run of every page that measured it) ---
  border-color           longhands=4  inert on dashboard+guests+index+materials+reset+templates  unmeasured on 8
      input:hover, textarea:hover, select:hover
```

and the verdict on this pass's final tree, where nothing is demotable:

```
$ sed -n '96,104p' tools/evidence/instrument-repair-verification.txt
cmd: ARTIFACTS_DIR=artifacts/instrument-repair-sweep python3 tools/hover-verify.py --cross-page
LIFT_CROSS_PAGE {"pages": 16, "runsPerPage": {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}, "minRunsPerPage": 3, "declarations": 58, "demotable": 0, "keep": 17, "noEvidence": 41, "unstable": 0}
pages: account, admin, analytics, billing, checkin, dashboard, designer, guests, index, materials, privacy, public, reset, responses, templates, verify
runs per page: {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}

--- DEMOTABLE (inert in EVERY run of every page that measured it) ---

--- UNSTABLE (runs of the same page disagreed: 0) — never demoted ---

```

Read the *keep* column carefully, because it moved for a reason that is not a CSS change:
the fixture teardown removed a rendered `<button>` from the measured set, and most of the
declarations that had been called load-bearing were being called that on the scaffold's
behaviour, not the page's. 38 declarations now have no evidence rather than a verdict,
which is the honest state of a sweep whose measured elements are mostly inside closed
panels. Zero declarations came back `unstable` in any sweep — the sampling fix holds
across 48 runs.

### 1.6 The demotion, and the four checks that carried it

The candidate the corrected probe produces, on every page and run that can measure it:

```
$ grep -n "redundant" tools/evidence/instrument-repair-demotion-applied.txt | head -6
19:  lift-dashboard         redundant   diffs=0 affected=8 rendered=8
20:  lift-dashboard.run2    redundant   diffs=0 affected=8 rendered=8
21:  lift-dashboard.run3    redundant   diffs=0 affected=8 rendered=8
25:  lift-guests            redundant   diffs=0 affected=11 rendered=11
26:  lift-guests.run2       redundant   diffs=0 affected=11 rendered=11
27:  lift-guests.run3       redundant   diffs=0 affected=11 rendered=11
```

6 pages × 3 runs, 18 measurements, every one `redundant` with 0 differences; the other 10
pages report that no element on the page reaches the rule at all. The edit is one
`!important` removed from one declaration, in commit `2edcad8`:

```
$ git show --stat 2edcad8 | head -5
commit 2edcad883f3b23927466a1930359d1148ba53a18
Author: Ngeth Sereyboth <ngethsereyboth@gmail.com>
Date:   Mon Oct 12 17:44:48 2026 +0700

    refactor(css): demote the one !important the repaired sweep calls unanimously inert
```

and the declaration itself, before and after, in the source and in the bundle that
index.html serves:

```
$ grep -o 'input:hover,textarea:hover,select:hover{[^}]*}' src/css/modern-ui.css src/css/bundle-index-v15.css
src/css/modern-ui.css:input:hover,textarea:hover,select:hover{border-color:color-mix(in srgb,var(--app-accent) 42%,var(--app-line-2))}
src/css/bundle-index-v15.css:input:hover,textarea:hover,select:hover{border-color:color-mix(in srgb,var(--app-accent) 42%,var(--app-line-2))}
```

```
$ sed -n '120,122p' tools/evidence/instrument-repair-demotion-applied.txt
cmd: grep -o 'input:hover,textarea:hover,select:hover{[^}]*}' src/css/bundle-index-v15.css
input:hover,textarea:hover,select:hover{border-color:color-mix(in srgb,var(--app-accent) 42%,var(--app-line-2))}

```

**Check A — the browser's own cascade.** `tools/css-cascade-winner.mjs` asks which
declaration actually wins the property, per state:

```
$ sed -n '57,66p' tools/evidence/instrument-repair-demotion-applied.txt
CASCADE_HOVER_MEDIA {"hoverCapableByDefault":false,"clausesFound":2,"rewritten":2,"stillInactiveAfter":0}
CASCADE_WINNER {"url":"http://127.0.0.1:8124/index.html","selector":"input","property":"border-color","elements":260,"index":0,"states":["plain","hover"]}
  state=plain         computed border-color="rgb(211, 213, 220)"
    order=12           border-color       var(--ui-line-strong)                                input, textarea, select
    order=13 IMPORTANT border-color       var(--app-line-2)!important                          input, textarea, select
    order=18 IMPORTANT border-color       var(--app-line-2)!important                          body:not(.guest) input, body:not(.guest) textarea, body:not(.guest) select
    last-important -> body:not(.guest) input, body:not(.guest) textarea, body:not(.guest) select  border-color:var(--app-line-2)!important
  state=hover         computed border-color="rgb(211, 213, 220)"
    order=12           border-color       var(--ui-line-strong)                                input, textarea, select
    order=13 IMPORTANT border-color       var(--app-line-2)!important                          input, textarea, select
```

`body:not(.guest) input, … { border-color: var(--app-line-2) !important }` wins in both
states, at higher specificity (0,2,1 against 0,1,1) and later in the cascade. A
declaration that is not the winner cannot become one by losing its priority — that is the
difference between a safe demotion and a lucky one.

**Check B — the before/after computed styles.** `tools/state-style-diff.mjs` snapshots the
complete computed style of every form control in `plain` and `hover`, before and after:

```
$ sed -n '127,130p' tools/evidence/instrument-repair-demotion-applied.txt
cmd: node tools/state-style-diff.mjs --compare=ssd-inputs-index-before.json,ssd-inputs-index-after.json
  STATE_STYLE_DIFF {"before":{"url":"http://127.0.0.1:8124/index.html","selector":"input, textarea, select","states":["plain","hover"],"elements":340},"after":{"url":"http://127.0.0.1:8124/index.html","selector":"input, textarea, select","states":["plain","hover"],"elements":340},"elementsCompared":340,"differences":0,"identical":true}
cmd: node tools/state-style-diff.mjs --compare=ssd-inputs-dashboard-before.json,ssd-inputs-dashboard-after.json
  STATE_STYLE_DIFF {"before":{"url":"http://127.0.0.1:8124/dashboard.html","selector":"input, textarea, select","states":["plain","hover"],"elements":8},"after":{"url":"http://127.0.0.1:8124/dashboard.html","selector":"input, textarea, select","states":["plain","hover"],"elements":8},"elementsCompared":8,"differences":0,"identical":true}
```

340 element-states on index and 8 on dashboard, all identical by property name.

**Check C — the rebuild and the budgets.** `python3 build.py all --check` exits 0 and
prints `BUILD_OK … MIRROR_CHECK_PASSED` (§7). Both bundles stay under budget.

**Check D — no file's `!important` count went up.** 105 files compared, HEAD 26,425 →
26,410 in the tree: one declaration in `src/css/modern-ui.css` and its copy in each of the
14 route bundles, 0 files increased (§7).

One honest caveat, and it is a finding in its own right: the hover border-color affine
being demoted **was already dead** before the demotion — `body:not(.guest) input` wins the
property in both states, so the accent-on-hover affordance this declaration describes does
not currently exist. Demoting it changes nothing in either state (Check B). Restoring the
affordance would mean changing a competing `!important`, which is a behaviour change the
brief does not authorize, so it is recorded here for the next pass rather than made.

### 1.7 The candidate that is NOT demoted, and the measurement that retracts it

The brief asked for the retracted eleventh demotion (§1.8) to be re-run, and the fixed
sweep's first candidate (`.ui-theme-menu button:hover` `transform`) is retracted instead.
`tools/demotion-recheck.mjs` is the instrument that answers the question the sweep cannot:
it measures the declaration in the state a user is actually in when they can hover the
thing, with the `hidden` attributes removed and motion settled:

```
$ sed -n '41,46p' tools/evidence/instrument-repair-demotion-recheck.txt
cmd: node tools/demotion-recheck.mjs <index.html> --selector='.ui-theme-menu button:hover' --property=transform --reveal      (three runs)
REVEALED ["div.ui-theme-menu"]
VALUES_BASELINE [{"element":0,"value":"none","rendered":true},{"element":1,"value":"none","rendered":true}]
VALUES_AFTER_DEMOTION [{"element":0,"value":"none","rendered":true},{"element":1,"value":"none","rendered":true}]
VALUES_AFTER_DELETION [{"element":0,"value":"matrix(1.012, 0, 0, 1.012, 0, -2)","rendered":true},{"element":1,"value":"matrix(1.012, 0, 0, 1.012, 0, -2)","rendered":true}]
DEMOTION_VERDICT {"url":"http://127.0.0.1:8124/index.html","selector":".ui-theme-menu button:hover","property":"transform","reveal":true,"elements":2,"elementsReadable":2,"demotion":[],"deletion":[{"element":0,"from":"none","to":"matrix(1.012, 0, 0, 1.012, 0, -2)"},{"element":1,"from":"none","to":"matrix(1.012, 0, 0, 1.012, 0, -2)"}],"verdict":"LOAD-BEARING"}
```

Identical in all six runs (three on index.html, three on dashboard.html): with a rendered
menu, deleting the declaration hands the property to
`@media(hover:hover){button:not(:disabled):hover{transform:translateY(-2px) scale(1.012)}}`
and the row visibly lifts. The declaration is load-bearing in the only state where the
rule can apply; the unanimous "demotable" verdict was an artifact of §1.4. **It is not
demoted**, and the sweep now reports it as unmeasured rather than inert.

The same instrument separates the two transformations, which is why the sweep's model of
the change matters: dropping only the priority leaves the declaration winning its
specificity tie by source order (`VALUES_AFTER_DEMOTION` unchanged), while deleting it is
observable. The sweep deletes; deletion is the stronger test; a declaration that fails it
is not demoted on the strength of a page state where nothing is observable.

### 1.8 The retracted eleventh demotion does not come back

`tools/evidence/important-11th-demotion-retraction.txt` records
`.studio-rail-button:hover { background }` being retracted. On the fixed probe it is
unanimously load-bearing, with identical diff counts in all three runs:

```
$ python3 tools/lift-verdict-compare.py --max-selector=64 artifacts/goal1/lift-index-after-run1.json artifacts/goal1/lift-index-after-run2.json artifacts/goal1/lift-index-after-run3.json | grep studio-rail-button
         L12   L12   L12   background    .studio-rail-button:hover
         L24   L24   L24   color         .studio-rail-button:hover
         L24   L24   L24   transform     .studio-rail-button:hover, .studio-inspector-tab:hover
```

The row-level before/after check that failed that demotion then, and the fixed probe now,
agree. The retraction stands.

### 1.9 What was repaired, in one table

| instrument | defect | fixed by |
| --- | --- | --- |
| `important-lift-test.mjs` | read mid-transition | `lib/motion-settle.mjs`, injected; `settleStats` reports it was exercised |
| `important-lift-test.mjs` | swept its own self-check fixture | fixture torn down before the sweep, with an assertion |
| `important-lift-test.mjs` | called boxless elements inert | `rendered` per row; boxless-only declarations are unmeasured |
| `lift-verdict-compare.py` | (new) N runs of one page were compared by eye | prints per-declaration verdict and diff count per run, `FLIP` on disagreement |
| `lib/motion-settle.mjs` | (new) | the shared settle helper |
| `demotion-recheck.mjs` | (new) | measures a declaration the sweep cannot observe, with `--reveal` |
| `css-cascade-winner.mjs` | read the cascade on a page where `@media(hover:hover)` was inactive | hover emulation on by default, verified in the run, `--no-hover-emulation` for the old behaviour |
| `perf-trace-compare.py` | looked for the stack at `args.stackTrace` only | searches `args` at any depth (§2) |
| `canva-probe.mjs` | reported `withStackTrace: 0` from the same wrong key | same reader fix |
| `report-verify.mjs` | dropped uncheckable blocks silently | counts and names them (§6) |
| `forced-layout-attribution.mjs` | header repeated the false "no stack traces" claim | header corrected to the measured location |
| `phase6-flag-mutations.py` | (new) the flag test's fixed branch had no proof it could fail | three mutations, one per assertion seam; all killed (§3.3) |
| `report-verify.mjs` | its own allow-list skipped a read-only tool the report relies on | `lift-verdict-compare.py` allow-listed; 3 skipped blocks became 3 verified ones |

## 2. Goal 2 — the trace's stack, and where the Style & Layout gap goes

### 2.1 The premise, checked

The prior pass concluded "the trace carries no `args.stackTrace` on Layout events … the
cause is UNVERIFIED". That is true of the **top-level** key, on the very traces it was
concluded from — and false of the trace:

```
$ sed -n '20,27p' tools/evidence/instrument-repair-layout-attribution.txt
cmd: python3 tools/layout-stack-attribution.py --paths artifacts/goal3-index-run1-trace.json
LAYOUT_STACK_PATHS {"file": "artifacts/goal3-index-run1-trace.json"}
  Layout               107 events   most common path: args.beginData.stackTrace
         79  args.beginData.stackTrace
         28  (none)
  UpdateLayoutTree     128 events   most common path: args.beginData.stackTrace
         98  args.beginData.stackTrace
         30  (none)
```

28,451 occurrences of `stackTrace` in that trace, 79 of 107 Layout events carrying one
level down at `args.beginData.stackTrace`. No trace-config change was needed at all: the
category was already enabled, the reader was looking in the wrong place. The 28 without a
stack are the signal, not a coverage hole — Blink attaches a stack when the work begins
from script, and the analyzer's independent "nested inside a script event" proxy gives 80
against 79 stacked.

### 2.2 Sources

* the category name is current: `disabled-by-default-devtools.timeline.stack` —
  <https://chromium.googlesource.com/chromium/src/+/main/base/trace_event/builtin_categories.h>
* Blink's `SetCallStack` checks that category and writes the stack into the event's own
  data dictionary, which is why Layout carries it under `beginData` —
  <https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/core/inspector/inspector_trace_events.cc>
* DevTools' own recorder for the transfer mode and record mode used —
  <https://chromium.googlesource.com/devtools/devtools-frontend/+/refs/heads/main/front_end/services/tracing/TracingManager.ts>

`stack_of()` in `tools/perf-trace-compare.py` now searches `args` at any depth and prefers
the documented top-level location if a future Chrome emits it there; the comparison
table's `Layouts with stackTrace` row went from 0/0 to 79 and 80 on the same two traces.

### 2.3 The attribution, and its stability

`tools/layout-stack-attribution.py` (new, 291 lines) aggregates Layout time by innermost
and outermost caller. Five traces of index.html, five runs:

```
$ sed -n '221,231p' tools/evidence/instrument-repair-layout-attribution.txt
cmd: python3 tools/layout-stack-attribution.py --top=5 --event=Layout artifacts/goal3-index-run{1,2,3,4,5}-trace.json
goal3-index-run1-trace       183.49 ms  n=1    max=183.49 ms  rememberScroll@bundle-index-v15.js:7651:113
goal3-index-run1-trace       115.37 ms  n=5    max=111.55 ms  updateCanvasView@bundle-index-v15.js:4763:54
goal3-index-run1-trace        67.53 ms  n=1    max=67.53 ms  HTMLDialogElement.showModal@bundle-index-v15.js:9713:4866
goal3-index-run1-trace        57.16 ms  n=1    max=57.16 ms  activate@bundle-index-v15.js:7513:93
goal3-index-run1-trace        48.82 ms  n=47   max=27.03 ms  availableSpace@bundle-index-v15.js:602:91
      ---
goal3-index-run2-trace       204.11 ms  n=1    max=204.11 ms  rememberScroll@bundle-index-v15.js:7651:113
goal3-index-run2-trace        72.67 ms  n=5    max=68.75 ms  updateCanvasView@bundle-index-v15.js:4763:54
goal3-index-run2-trace        66.79 ms  n=1    max=66.79 ms  HTMLDialogElement.showModal@bundle-index-v15.js:9713:4866
goal3-index-run2-trace        66.60 ms  n=1    max=66.60 ms  activate@bundle-index-v15.js:7513:93
```

The same five callers appear in all five runs in a nearly fixed order. Mapped back to
source by `bundle-line-map.py`: `availableSpace` → `src/js/typography-layout-service.js`
(line 35), `rememberScroll` → `workflow-continuity.js:29`, `updateCanvasView` →
`app.js:2614`, `activate` → `editor/ui-layout.js:157`, `keepActivePageVisible` →
`editor/ui-layout.js:157`'s region.

### 2.4 The decision: the cost is distributed, so nothing is closed

Per caller, with the size of the layout each forced, on the same trace:

| caller | events | total ms | largest | dirty/total objects (first four) |
| --- | --- | --- | --- | --- |
| `rememberScroll` | 1 | 183.49 | 183.49 | 393/473 |
| `updateCanvasView` | 7 | 115.98 | 111.55 | 970/1611, 7/1611, 7/621, 8/621 |
| `HTMLDialogElement.showModal` | 1 | 67.53 | 67.53 | 217/621 |
| `activate` | 1 | 57.16 | 57.16 | 324/361 |
| `availableSpace` | 47 | 48.82 | 27.03 | 210/808, 13/808, 13/808, 13/808 |
| no stack (frame-scheduled) | 28 | 406.20 | 387.86 | 731/731 |

Three things follow, and they are the reason no fix is implemented:

1. **The largest single item has no stack at all** — 387.86 ms in one frame-scheduled
   layout, `dirtyObjects=731, totalObjects=731`. That is a whole-tree relayout begun by
   the rendering pipeline, not by a statement this pass can point at. Naming a caller for
   it would be a guess.
2. **The script-forced cost is spread across five callers**, four of them one-shot
   (`HTMLDialogElement.showModal`, `activate`, `rememberScroll`, `updateCanvasView`). No
   single addressable caller owns a meaningful share: the biggest, `rememberScroll`, is
   183 ms of a 982 ms layout total, and it is `activePane()` + a remembered `scrollTop`.
3. **The only high-count caller, `availableSpace`, is already cheap per event** — 47
   events, 48.82 ms total, 1.04 ms average, on a function that reads
   `clientWidth`/computed padding in a loop. Optimising it is a micro-optimisation with no
   measurable share of the gap, and changing it risks the typography fit that 8
   `!important`-free rules and a controller depend on.

So the gap is attributed and **not closed**, which is the honest end of this goal: the
instrument now answers the question, and the answer is "no single caller to fix".

### 2.5 The residual, measured

Five stored traces of index.html put the style+layout union at a median of **2137.55 ms**
(2039.29, 2099.97, 2137.55, 2151.75, 2152.56) — but those were captured with four
concurrent browsers running, so they are a *contended* measurement. Re-measured on this
pass's final tree with a quiet machine, five runs, the same instrument:

```
$ sed -n '79,85p' tools/evidence/instrument-repair-verification.txt
cmd: python3 - <<'PY'   (median of the five 'style+layout union ms' values above, and the brief's target)
  five runs: [1761.2, 1839.77, 1721.94, 1783.51, 1652.74]
  sorted:    [1652.74, 1721.94, 1761.2, 1783.51, 1839.77]
  median:    1761.20 ms
  target:    1167.0 ms (30% below the 1667.0 ms baseline the earlier pass started from)
  vs target: ABOVE by 594.20 ms

```

Median 1761.20 ms against the brief's 1,167 ms target — a target that is 30 % below the
1,667 ms this project started from — i.e. still **594 ms above it**, and the residual is
labelled rather than closed. The spread across the five runs is 1652.74-1839.77 ms, which
is wider than this pass's changes could plausibly account for, so no before/after claim is
made about the demotion's effect on this number.

The asymmetry with Canva is now measured directly rather than through the nesting proxy:

```
$ sed -n '85,100p' tools/evidence/instrument-repair-canva-public-templates.txt
cmd: python3 tools/perf-trace-compare.py --label mine=artifacts/goal3-index-run1-trace.json --label canva-home=artifacts/canva-trace.json --label canva-invitations=artifacts/goal4-invitations-trace.json
TRACE_COMPARE {"mine": 128442, "canva-home": 189695, "canva-invitations": 150325}
metric                                                 mine        canva-home canva-invitations
trace events                                         128442            189695            150325
style+layout union ms (main thread)                 2039.29            805.22           1347.22
  style recalc union ms                             1056.97            525.12           1175.44
  layout union ms                                    982.41             280.1            171.78
  style recalc union ms (all threads)               1056.97            525.12           1175.44
  layout union ms (all threads)                      982.41             280.1            171.78
Script union ms (main thread)                        2737.7           2604.65           5379.64
UpdateLayoutTree events                                 152               379                68
Layout events                                           107                37                35
RunTask events                                        17102             29315             25181
Layouts nested in script (forced proxy)                  80                 6                12
Layouts with stackTrace                                  79                 6                12

```

`Layouts with stackTrace` was `0`/`0` in the prior pass's own table. It is 79 and 6 now,
from the same instrument and the same traces: **the gap is a style-recalc gap and a
whole-tree-layout gap, not a script-forced-layout gap** — the project forces more layouts
from script than Canva does *and* spends 1.8× Canva's total in layout, with Canva's single
largest layout at 6 events against the project's 37.

## 3. Goal 3 — the flag test's unreachable 200-branch

### 3.1 Why it was unreachable

The test POSTed `{"key": …, "value": …}` to `/api/admin/feature-flags`. That route is
PUT-only, admin-only, and takes `{"updates": [{"key": …, "value": …}]}`:

```
$ sed -n '6,12p' tools/evidence/instrument-repair-flag-branch.txt
cmd: grep -n 'path == "/api/admin/feature-flags"' src/python/server.py
3509:        if path == "/api/admin/feature-flags": return self.admin_feature_flags()
3598:            if path == "/api/admin/feature-flags": return self.admin_update_feature_flags()

  3509 is in do_GET, 3598 is in do_PUT. There is no do_POST arm for this path, so
  the test's POST reached the 404 catch-all and never the flag handler.

```

So the request 404'd, the test took its `else` branch, printed "skipped" and passed. A
green test asserting nothing: the 200 branch, the `activeSessions`/`lastEventAt` payload
and the 403-vs-200 distinction were never executed by any run of the suite.

### 3.2 The decision, and the fixture fix

The branch **should** be reachable — the endpoint that flips the flag exists and works, and
the defect is in the fixture, not the server. `tests/analytics_reports_test.py` now
promotes the host to admin in the server's own SQLite file (the harness has no
admin-registration route; `role` is a column on `users`) and PUTs the documented body, and
the silently-passing `else` branch is **deleted** rather than kept: a branch that passes
without asserting is how this survived.

### 3.3 Verification: the branch runs, and three mutations prove it

```
$ sed -n '147,153p' tools/evidence/instrument-repair-flag-branch.txt
cmd: EINVITE_ALLOW_NO_SCANNER=1 .venv/bin/python -m pytest tests/analytics_reports_test.py -k phase6 -q -p no:randomly
.                                                                        [100%]
1 passed, 6 deselected in 4.18s

cmd: .venv/bin/python tools/phase6-flag-mutations.py
     (the output below was produced by this script while it was still a /tmp throwaway; it
      graduated to tools/ unchanged, and re-running it from there prints the same three kills)
```

The three mutations — the admin PUT returning 500, the PUT flipping a different flag, and
the user never being promoted to admin — all kill the test, at the exact seam each one
targets. A surviving mutation would have meant the branch was still not under test.

## 4. Goal 4 — the Canva public template surfaces

No login was attempted, nothing was copied, and every number is a measurement of a public
page taken by the tools in this repository.

### 4.1 The surface the prior report named is not a page

```
$ sed -n '10,26p' tools/evidence/instrument-repair-canva-public-templates.txt
cmd: node tools/canva-probe.mjs --targets=https://www.canva.com/templates/,https://www.canva.com/templates/invitations/ --prefix=goal4-templates --wait=6000
     (both targets are visited; the trace covers the first)
  200  https://www.canva.com/templates/
      finalUrl   https://www.canva.com/templates/
      title      Free templates | Canva
      responses=189 resources=183 traceEvents=181065 elapsedMs=12809
  200  https://www.canva.com/templates/invitations/
      finalUrl   https://www.canva.com/templates/?query=invitations
      title      Customize 20,077+ Invitations Templates Online - Canva
      responses=74 resources=72 traceEvents=0 elapsedMs=8403

  FINDING: the category PATH /templates/invitations/ is not a page. It 301/302s to
  /templates/?query=invitations — Canva's template categories are a filtered listing,
  addressed by query string. So 'the public template detail page' the prior report
  named as the next surface is, on this site, the same listing route with a filter.
  The filtered listing is what was traced next.

```

### 4.2 What the same instruments measured there

The filtered listing, traced and inventoried:

```
$ sed -n '34,44p' tools/evidence/instrument-repair-canva-public-templates.txt
    200  https://www.canva.com/templates/?query=invitations  title="Customize 20,077+ Invitations Templates Online - Canva"  responses=103  resources=98  traceEvents=150325  13788ms
  CANVA_SCRIPTS {"count": 40, "totalDecodedBytes": 5002142, "totalTransferBytes": 1715616}
  CANVA_LAYOUT {"layoutEvents": 35, "withStackTrace": 0}
  MODULE_LOADING_STRATEGY label=goal4-canva-invitations targets=1
    200 https://www.canva.com/templates/?query=invitations
      DECLARED scripts=11 (inline=4 src=7) module=0 async=0 defer=4 parserBlocking=3
      DOM srcScripts=19 parserCreated=17 injected=12
      preload(declared) module=0 script=6 style=0 other=0 prefetch=0 total=6
      TIMING dcl=1645 load=5630 paint={"first-paint":1644,"first-contentful-paint":1644} scriptsTimed=19
      CHAIN span=5948ms transfer=4844ms serialGap=1104ms lastEnd=6437ms
    200 https://www.canva.com/templates/?query=invitations
```

Two results matter. First, `CANVA_LAYOUT … withStackTrace: 0` on this surface is a
*measurement*, not the old reader bug: of 35 Layout events on the public listing, none
begins from script. The 12 "forced proxy" counts in §2.5's table are the same asymmetry
seen two ways. Second, Canva's public listing declares 11 scripts (7 `src`, 4 `defer`, 3
parser-blocking, 0 `module`) and injects 12 more; the project's index declares 3 and
injects 34 after the parser finishes — the comparison the prior pass's
`module-loading-strategy.mjs` was built to make, now on a third surface.

### 4.3 The new rows, and what was not ported

The construct inventory gained a Canva listing column, and the trace comparison a third
label (§2.5). Where the two sites differ on a technique the project could adopt, the
decision is:

| gap | direction | decision |
| --- | --- | --- |
| `:where()` selectors — 6 (project) vs 73 (Canva listing) | Canva ahead | **Not ported.** `:where()` is a zero-specificity tool for resets; this project's resets are already ordered by source, and rewriting them is a large diff with no measurement that attributes any of the 2.65× to specificity. Recorded, not attempted. |
| `:is()` — 2 vs 13 | Canva ahead | **Not ported**, same reason. |
| custom properties — 340 vs 1031-1385 | Canva ahead | **Not ported.** More declarations is not a technique; the project's own count already grew in an earlier pass, and nothing measures a cost either way. |
| `@keyframes` — 22 vs 39-92, `@media` blocks — 206 vs 324-429, style rules — 5,245 vs 4,289-7,434 | Canva ahead on volume | **Ignored**: volume is a property of Canva's 20,077-template listing, not a technique to copy. |
| `content-visibility` — 6 vs 0, `contain` — 8 vs 0, `contain-intrinsic-size` — 4 vs 0 | **project ahead** | **Nothing to port.** |
| `!important` — 2,985 vs 7 | project ahead | The project's own count fell by 15 in this pass (§1.6) and the sweep is the instrument for more; no Canva technique involved. |
| layout cost of a listing | Canva ahead | **Not closeable here**: the gap is style recalc over a bigger DOM (§2.5), and no single caller owns it (§2.4). |

Nothing was ported from these surfaces, and the reason is stated per row rather than
implied: the one technique that is genuinely Canva's (`:where()`-based zero-specificity
resets) has no measurement behind it in this codebase, and the brief's rule is that a
technique is ported only against a measured gap.

## 5. The gate that verifies these quotes had a blind spot

`tools/report-verify.mjs` only mechanically checks a fenced block with exactly one leading
`$ ` line, and it used to drop every other block with a bare `continue`. A report could
carry any number of uncheckable blocks and still print "0 skipped" — honest and incomplete
at the same time. The checking rules are unchanged; the hole is now counted, named and
printed (`not mechanically checkable N`). The change is additive:

```
$ sed -n '79,92p' tools/evidence/instrument-repair-report-verify-hole.txt
  <   blocks checked 25 — match 19, MISMATCH 0, ELIDED 0
  ---
  >   blocks checked 27 — match 19, MISMATCH 0, ELIDED 0
  5a6
  >   not mechanically checkable 2   (no `$ ` command line, or not the "one command, then its output" shape)
  23a25,30
  >
  >   uncheckable line 255: cat tools/evidence/important-lift-state-expansion.txt
  >             4 `$ ` lines: only the "one command, then its output" shape is checkable
  >
  >   uncheckable line 613: cat tools/evidence/playwright-launch-check.txt
  >             4 `$ ` lines: only the "one command, then its output" shape is checkable

  Reading: the previous tool reported 25 blocks and 0 skipped; this one reports the
```

No block changed status, no match became a mismatch, and the exit status is unchanged.

## 6. Verification battery

Every item the brief lists, in its order, run once on the final tree and recorded in
`tools/evidence/instrument-repair-verification.txt`. The blocks below quote that file (the
commands are named in its `cmd:` lines); nothing here is re-run by the gate's own timeout,
and nothing is elided.

**1. Build.** `python3 build.py all --check`, no pipe:

```
$ sed -n '9,13p' tools/evidence/instrument-repair-verification.txt
cmd: python3 build.py all --check > /tmp/check.log 2>&1; echo "exit=$?"; tail -3 /tmp/check.log
exit=0
organized: drifted=0 up_to_date=15
MIRROR_CHECK_PASSED (up_to_date=314)
BUILD_OK editor bundles manifests mirror (check)
```

**2. Mirror.** `python3 tools/mirror-diff.py`:

```
$ sed -n '15,17p' tools/evidence/instrument-repair-verification.txt
cmd: python3 tools/mirror-diff.py | tail -2
MIRROR_DIFF {"sources": 314, "drifted": 0, "unmigrated": 0, "orphans": 0, "orphansExempt": 19, "generatedExempt": 34}
MIRROR_DIFF_SUMMARY 0 drifted, 0 unmigrated, 0 orphans (19 named and exempt)
```

**3. The suite.** `pytest tests/`:

```
$ sed -n '22,24p' tools/evidence/instrument-repair-verification.txt
cmd: EINVITE_ALLOW_NO_SCANNER=1 .venv/bin/python -m pytest tests/ -q | tail -2
....................................................................     [100%]
68 passed in 109.66s (0:01:49)
```

68 passed / 0 failed, the same counts as the prior pass's final tree.

**4. The budgets and the versioned-file counts:**

```
$ sed -n '29,36p' tools/evidence/instrument-repair-verification.txt
cmd: wc -c src/js/bundle-index-v15.js src/js/bundle-public-v15.js
1136115 src/js/bundle-index-v15.js
 251960 src/js/bundle-public-v15.js
1388075 total
cmd: find src/css -name '*-v*.css' | wc -l
64
cmd: find src/js -name '*-v*.js' -not -name 'bundle-*' | wc -l
94
```

**5. `!important`, per file, HEAD vs this tree** — the pass's hard rule:

```
$ sed -n '41,58p' tools/evidence/instrument-repair-verification.txt
cmd: python3 - <<'PY'   (per-file !important count: git show HEAD:FILE vs the working tree, both counted for the literal '!important')
files=105 HEAD=26425 tree=26410 increased=0 []
changed (file, HEAD, tree):
  src/css/bundle-account-v15.css  1522 -> 1521
  src/css/bundle-admin-v15.css  1522 -> 1521
  src/css/bundle-analytics-v15.css  1557 -> 1556
  src/css/bundle-billing-v15.css  1528 -> 1527
  src/css/bundle-dashboard-v15.css  1805 -> 1804
  src/css/bundle-designer-v15.css  1646 -> 1645
  src/css/bundle-guests-v15.css  1557 -> 1556
  src/css/bundle-index-v15.css  2887 -> 2886
  src/css/bundle-materials-v15.css  1774 -> 1773
  src/css/bundle-privacy-v15.css  465 -> 464
  src/css/bundle-reset-v15.css  1522 -> 1521
  src/css/bundle-responses-v15.css  1558 -> 1557
  src/css/bundle-templates-v15.css  1681 -> 1680
  src/css/bundle-verify-v15.css  1522 -> 1521
  src/css/modern-ui.css  297 -> 296
```

**6. Style & Layout on index.html, five runs on a quiet machine**, against the brief's
1,167 ms target:

```
$ sed -n '71,85p' tools/evidence/instrument-repair-verification.txt
cmd: python3 tools/perf-trace-compare.py --label run1=artifacts/verif-index-run1-trace.json --label run2=artifacts/verif-index-run2-trace.json --label run3=artifacts/verif-index-run3-trace.json --label run4=artifacts/verif-index-run4-trace.json --label run5=artifacts/verif-index-run5-trace.json
style+layout union ms (main thread)                  1761.2           1839.77           1721.94           1783.51           1652.74
  style recalc union ms                               940.0            993.81            921.29            943.15            845.99
  layout union ms                                    821.28            846.05            800.74            840.42            806.87
  style recalc union ms (all threads)                 940.0            993.81            921.29            943.15            845.99
  layout union ms (all threads)                      821.28            846.05            800.74            840.42            806.87
Layout events                                           114               114               109               109               102

cmd: python3 - <<'PY'   (median of the five 'style+layout union ms' values above, and the brief's target)
  five runs: [1761.2, 1839.77, 1721.94, 1783.51, 1652.74]
  sorted:    [1652.74, 1721.94, 1761.2, 1783.51, 1839.77]
  median:    1761.20 ms
  target:    1167.0 ms (30% below the 1667.0 ms baseline the earlier pass started from)
  vs target: ABOVE by 594.20 ms

```

**7. The sweep on the final tree**, and its cross-page verdict:

```
$ sed -n '89,104p' tools/evidence/instrument-repair-verification.txt
cmd: ARTIFACTS_DIR=artifacts/instrument-repair-sweep python3 tools/hover-verify.py --all --lift --lift-runs=3 --jobs=4
hoverSelectors=147   triggers=95    noMatch=81   tested=47    change=40    noChange=7
             lift: rules=15 decls=24 (longhands=76) redundant=1 loadBearing=2 unmeasured=18
designer     hoverSelectors=147   triggers=95    noMatch=84   tested=34    change=32    noChange=2
             lift: rules=15 decls=24 (longhands=76) redundant=1 loadBearing=0 unmeasured=20
HOVER_VERIFY_TOTAL {"pages": 16, "hoverSelectors": 2107, "elementsTested": 813, "visibleChange": 679, "noVisibleChange": 134, "liftPages": 16, "liftCandidateDeclarations": 349, "liftCandidateLonghands": 1139, "liftRedundant": 15, "liftLoadBearing": 17, "liftUnmeasured": 277, "liftGroupingMismatches": 0, "liftRestoreFailures": 0}

cmd: ARTIFACTS_DIR=artifacts/instrument-repair-sweep python3 tools/hover-verify.py --cross-page
LIFT_CROSS_PAGE {"pages": 16, "runsPerPage": {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}, "minRunsPerPage": 3, "declarations": 58, "demotable": 0, "keep": 17, "noEvidence": 41, "unstable": 0}
pages: account, admin, analytics, billing, checkin, dashboard, designer, guests, index, materials, privacy, public, reset, responses, templates, verify
runs per page: {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}

--- DEMOTABLE (inert in EVERY run of every page that measured it) ---

--- UNSTABLE (runs of the same page disagreed: 0) — never demoted ---

```

The lift-probe stability proof (§1.2), the trace's `args.stackTrace` proof (§2.1) and the
demotion's four checks (§1.6) are quoted in their sections. **8. The tree:**

```
$ sed -n '154,170p' tools/evidence/instrument-repair-verification.txt

cmd: git status --short
 M docs/page-assets-v15.json
 M docs/route-bundles-v15.json
 M package-lock.json
 M package.json
 M src/css/bundle-account-v15.css
 M src/css/bundle-admin-v15.css
 M src/css/bundle-analytics-v15.css
 M src/css/bundle-billing-v15.css
 M src/css/bundle-dashboard-v15.css
 M src/css/bundle-designer-v15.css
 M src/css/bundle-guests-v15.css
 M src/css/bundle-index-v15.css
 M src/css/bundle-materials-v15.css
 M src/css/bundle-privacy-v15.css
 M src/css/bundle-reset-v15.css
```

## 7. The gate on this file

```
$ sed -n '141,149p' tools/evidence/instrument-repair-verification.txt
cmd: node tools/report-verify.mjs docs/reviews/instrument-repair-report.md --with-server
report-verify: docs/reviews/instrument-repair-report.md
  blocks checked 33 — match 33, MISMATCH 0, ELIDED 0

  declared, not compared  historical 0, write 0, measurement 0, heavy 0
  still skipped 0
  not mechanically checkable 0   (no `$ ` command line, or not the "one command, then its output" shape)

=====================================================================
```

Self-referential by construction: the count above is the gate's report on this file, taken
after the last block was added. `blocks checked` moves by one for every block a later edit
adds; `MISMATCH`, `ELIDED`, `still skipped` and `not mechanically checkable` are the numbers
that matter, and they are zero.

## 8. Autonomous decisions, and why

* **The brief's own goal order was kept, and Goal 1 was allowed to take the whole pass.**
  Three probe defects, not one, meant the sweep had to be re-run three times (48 lift runs
  each, ~10 minutes) before its output was worth acting on. The brief's rule — a tool's
  verdict is not evidence until it is stable — made that mandatory rather than optional.
* **The first candidate was retracted and the second demoted**, both on measurement: the
  first because its evidence came from a state where nothing is observable, the second
  because 18 measured runs, the browser's own cascade, and a 348-element-state before/after
  all agree. Retracting a unanimous verdict and demoting on a different one is the point of
  the pass, not a failure of it.
* **The dead hover affordance was not restored.** `body:not(.guest) input` wins
  border-color in both states, so the accent-on-hover this rule describes never appears.
  Restoring it means changing a competing `!important` and is a visible behaviour change;
  it is recorded in §1.6 instead.
* **The 28 boxless-target declarations were reclassified as unmeasured rather than
  measured some other way.** Revealing every closed panel or menu and measuring there is
  possible (`tools/demotion-recheck.mjs --reveal` does exactly that for one rule) but doing
  it sweep-wide would mean driving each page into states no measurement has validated, and
  the numbers would then be about the harness's state machine rather than the page. The
  honest output is "unmeasured, with the reason", and the instrument to answer a specific
  declaration is one command.
* **No source fix was made for the Style & Layout gap** (§2.4). Distributed cost, and the
  largest single item has no stack at all.
* **The fixture teardown asserts rather than assumes** — the probe exits 3 if the fixture
  sheet or host is still present, so a future edit cannot silently reintroduce §1.3.

## 9. Limitations, stated rather than implied

* The sweep measures `:hover` rules with `!important` declarations only: 3,911 elements
  and 32,832 other `!important` declarations are out of its reach, unchanged from the prior
  pass's statement.
* 38 declarations have no evidence because their elements are inside closed panels, menus
  and dialogs that a page load does not open. That is a harness limit, now reported per row
  with the element count and the reason.
* The 5-run style+layout figures in §2.5 were captured under load (4 concurrent browsers);
  §7 carries the quiet re-measurement. Neither is a Lighthouse-equivalent number.
* Canva's numbers come from one page load per surface, on a shared network, and are quoted
  as ratios against a same-machine baseline only.
* No claim is made about Canva's internals beyond what the traces show; nothing was
  logged into, copied, or guessed.

## 10. Retained corrections

Kept because a reader is entitled to know which outputs changed and why.

1. **`important-lift-test.mjs` v2 → v3.** The prior pass's "0 unstable" sweep was taken
   with a probe that read mid-transition; the same probe on the same page disagreed with
   itself on 3 of 59 declarations when run twice. §1.1.
2. **`important-lift-test.mjs` v3 → v4.** The fixture contamination (§1.3) and the boxless
   verdicts (§1.4) were found by chasing the v3 sweep's single demotable row. Both were
   present in the prior pass's sweep too.
3. **`perf-trace-compare.py` and `canva-probe.mjs`.** The prior pass's
   "the trace carries no `args.stackTrace`" conclusion was a reader defect, not a Chrome
   limitation. §2.1. `forced-layout-attribution.mjs`'s header repeated that claim and is
   corrected.
4. **`css-cascade-winner.mjs`.** The tool that justifies a demotion was reading a page
   where `@media(hover:hover)` was inactive — i.e. in a different environment from the
   probe that proposed the demotion. Hover emulation is now on by default and verified.
5. **`state-style-diff.mjs`'s positional diff** (prior pass, retained): positional
   comparison reported 32 phantom differences on a change that moved no value.
6. **The prior report's own gate quote** ("blocks checked 24 … measurement 3") went stale
   the moment a block quoting it was added; §5's A/B confirms the gate's statuses are
   unchanged and only the coverage line is new.
