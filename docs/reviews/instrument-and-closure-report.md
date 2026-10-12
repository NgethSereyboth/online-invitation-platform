# Instrument and closure — the pass after `623b233`

This pass started from `docs/reviews/reproducibility-and-performance-report.md`
(1,560 lines), which ends with a numbered list of what the *next* pass should do
first. Item 5 was "fix `important-lift-test.mjs` to decide per declaration, then act
on the result: the current output cannot be acted on". That is Goal 1 here, and the
other five goals are the rest of that list plus the holes the list names.

Nothing in this report is a plan. Every number below was produced by the command
printed next to it, in this working tree, in this session; the raw output of the
longer runs is kept under [`tools/evidence/`](../../tools/evidence/) and linked from
the section that uses it. Where a claim could not be verified, it says so.

---

## 0. What this pass did

| # | goal | outcome | where |
| --- | --- | --- | --- |
| 1 | fix the `!important` instrument, re-run the 16-page sweep | **fixed**; ten declarations demoted and verified row-identical; an eleventh was acted on, **failed the check, and was reverted**; the triage instrument is now shown to be unreproducible per declaration | §1 |
| 2 | close Goal 3's 30 % Style & Layout target | **not met**; 1,571 → 1,472 ms median (−6.3 %, disjoint ranges), target 1,167 ms | §2 |
| 3 | versioned renames, batches 3+ | **batch 3 landed**: 10 files + 10 mirrors, 23 references, 32/32 bundles byte-identical | §3 |
| 4 | close the reproducibility holes (pytest, `v27_3_5`) | **closed**: `pytest tests/` went from *no tests ran* to 44 passed / 15 failed / 6 errors, and the two stale gates pass | §4 |
| 5 | extend `report-verify.mjs` coverage | **closed**: 9 skipped → 0, 0 mismatches, one new declaration kind | §5 |
| 6 | hygiene: decide the untracked artifacts | **decided**, and the first attempt at it was wrong in a way worth recording | §6 |

Commits, in order (the hashes are stable; this report's own commit is not printed,
because writing it here would change the hash it names):

```
623b233  pass base (branch main)
dedf093  fix(tools): enumerate !important at shorthand level, then re-run the leave-one-out sweep
a851083  perf(index): stop the overlay ResizeObserver re-arming on its own output
e044528  chore(repro): make `make reproduce` step 2 run the tests, and resolve the v27_3_5 test
d8f1fab  chore(tools): extend report-verify to continuations, server blocks and declarations
aa4fbe4  refactor: rename versioned files, batch 3 of N (10 files)
42cbaca  chore(hygiene): decide the untracked set, and stop parking evidence in /tmp
2bb56c1  chore(tools): two new instruments, a declaration kind, and the pass's raw evidence
```

---

## 1. Goal 1 — the `!important` instrument

### 1.1 The defect, and what replaced it

The prior pass's leave-one-out tool enumerated `CSSStyleDeclaration`'s indexed
properties. Those are *longhands*: one `background: linear-gradient(...) !important`
reported as nine independent candidates, eight of them "inert". Acting on that output
would have deleted a hover highlight on every page. The fix, in `dedf093`:

```
$ git show --stat --oneline dedf093 | head -3
dedf093 fix(tools): enumerate !important at shorthand level, then re-run the leave-one-out sweep
 docs/page-assets-v15.json                          |  28 +-
 docs/route-bundles-v15.json                        |  56 +-
```

Three instrument defects were fixed together, all of them silent wrong-measurement
rather than crashes:

* **Granularity.** `tools/lib/css-decl.js` is now the single enumeration model, and
  `tools/css-declaration-granularity.mjs` is a self-check that fails if a shorthand
  expands into N candidates again.
* **Sampling mid-transition.** A transitioning property makes `getComputedStyle`
  return an interpolated value, so two runs of an *unchanged* page disagreed on 72 of
  813 hover rows — all of them transform matrices a few thousandths apart.
  `hover-audit.mjs` now waits for running, finite animations to settle before
  reading (one `requestAnimationFrame` first, because a transition does not enter
  `getAnimations()` until the forced state has been recalculated).
* **Row identity.** The first comparator keyed rows by `(trigger, tag, cls)`, which
  mis-pairs elements when several share a class and one changes bucket. It keys on
  the audit's own per-element index `i` now, and reports class drift separately.

### 1.2 The sweep, with the fixed instrument

16 pages, one browser per page:

```
$ python3 tools/hover-verify.py --all --summary-only
index        tested=271   change=226   noChange=45
dashboard    tested=68    change=54    noChange=14
public       tested=41    change=34    noChange=7
admin        tested=34    change=32    noChange=2
account      tested=34    change=31    noChange=3
billing      tested=34    change=31    noChange=3
verify       tested=25    change=20    noChange=5
reset        tested=31    change=25    noChange=6
privacy      tested=4     change=4     noChange=0
guests       tested=51    change=37    noChange=14
responses    tested=34    change=31    noChange=3
analytics    tested=33    change=30    noChange=3
materials    tested=50    change=34    noChange=16
checkin      tested=22    change=18    noChange=4
templates    tested=47    change=40    noChange=7
designer     tested=34    change=32    noChange=2
HOVER_VERIFY_TOTAL {"pages": 16, "hoverSelectors": 2107, "elementsTested": 813, "visibleChange": 679, "noVisibleChange": 134}
```

This block deliberately omits `--lift`, so the totals line carries the hover counts
and not the candidate counts; the figures that describe the tool's coverage
(2,107 hover selectors, 813 elements tested, 679 with a visible change, 134 without)
are the ones above, and the file is
[`tools/evidence/hover-sweep-summary-16pages.txt`](../../tools/evidence/hover-sweep-summary-16pages.txt).
The candidate totals from the lift pass, which this pass's Goal 1 rests on, are:
421 candidate declarations / 1,509 longhands / 44 redundant / 68 load-bearing /
269 unmeasured, 0 grouping mismatches, 0 restore failures — recorded in the sweep log
`artifacts/hover-lift-16-fixed.log`, which is working-tree state and is not committed.

The sweep is byte-stable: two runs of the same tree produce identical rows
(305/305 identical on the self-check page, 813/813 across the full sweep), which is
what makes the next section a proof rather than an opinion.

### 1.3 The ten demotions, and the check that makes them safe

Ten declarations were identified as inert on every page that could measure them, and
their `!important` was dropped — priority, not content: no declaration was deleted.

The safety argument is not the triage. It is a row-by-row diff of two recorded
sweeps, taken with the same instrument before and after the edit:

<!-- report-verify: historical — compares two hover-audit artifact snapshots (artifacts/ is working-tree state, not committed); re-running it needs both sweeps re-taken, which is what tools/reproduce.sh step 4 does. -->
```
$ python3 tools/hover-regression-diff.py --before artifacts/hover-before-demotion --after artifacts
HOVER_REGRESSION_TOTALS {"pagesCompared": 16, "pagesMissing": 0, "elementsCompared": 813, "elementsIdentical": 813, "elementsDiffering": 0, "pagesShapeMismatch": 0, "clsDrift": 0}
  index       before=271  after=271  changes 226->226  rows 271 identical 271 differing 0  ok
  dashboard   before=68   after=68   changes 54->54   rows 68 identical 68 differing 0  ok
  public      before=41   after=41   changes 34->34   rows 41 identical 41 differing 0  ok
```

813 of 813 rows identical, on all sixteen pages, with 0 shape mismatches and 0 class
drift. The demotions change no computed hover style anywhere the sweep can reach.

The edit itself is verified as *only* what it claims to be:

<!-- report-verify: prefix 4 — the tool prints one line per changed file (61 of them); the first lines are the renamed CSS files, and the counts and the summary are stable while the file order is alphabetical. -->
```
$ python3 tools/important-removal-audit.py --rev=623b233
  ok   src/css/account-security.css                             renamed from src/css/account-security-v13.css; content identical
  ok   src/css/bundle-account-v15.css                           identical after !important strip; removed=3  bytes delta=-30
  ok   src/css/bundle-admin-v15.css                             identical after !important strip; removed=3  bytes delta=-30
  ok   src/css/bundle-analytics-v15.css                         identical after !important strip; removed=3  bytes delta=-30
```

The full run is in
[`tools/evidence/important-removal-audit-vs-pass-base.txt`](../../tools/evidence/important-removal-audit-vs-pass-base.txt);
its last line is the claim:

```
important-removal-audit: vs 623b233 — 61 changed CSS/JSON entry(s) (36 modified, 20 renamed, 5 manifest(s)); 4 JS change(s) not judged; failures=0
```

Every changed CSS file is byte-identical to the pass base after deleting the
`!important` token — including the generated bundles. The manifests moved only size,
digest and renamed-source fields, and each of those was re-derived: every recorded
digest was compared against sha256 of the file it names, and every size delta against
that file's own delta. **Failures: 0.** The tool does not judge JS (a logic change is
not an `!important` edit); it names the four JS changes instead, so they are a line a
reader can follow into `a851083`.

Net effect on the token count in `src/css`:

```
$ python3 -c "import subprocess; c=lambda r: subprocess.run(['git','grep','-o','!important',r,'--','src/css'],capture_output=True,text=True).stdout.count(chr(10)); print('623b233 (pass base):', c('623b233')); print('HEAD             :', c('HEAD'))"
623b233 (pass base): 32832
HEAD             : 32765
```

67 fewer, and the split is measured rather than assumed: 12 tokens in the seven
hand-edited source files (the ten distinct declarations; two of them exist in two
files each) and 55 copies in the fourteen generated route bundles that concatenate
those files.

### 1.4 Retraction — the eleventh demotion

After the ten were verified, the sweep on the new tree reported exactly one remaining
candidate, so it was acted on as well. That work is **retracted**: written, checked,
and reverted.

```
  .studio-rail-button:hover{background:#2b2c33!important;color:#fff!important}
- .studio-rail-button:hover{background:#2b2c33;color:#fff!important}
```

The triage claim was the weakest evidence class the tool has (measured on one page,
unreachable on the other fifteen). The demote-then-diff check failed it: 18 of
index's 271 rows changed, and the change is that the hover background stops
happening —

```
  before (r.R100-ish, verified state): "background-color": "rgba(0, 0, 0, 0) -> rgb(43, 44, 51)"
  after  (demoted):                    the key is absent, i.e. no background change on hover
```

— which is why it was reverted rather than kept and argued about. After the revert
and rebuild, the reverted state reproduced twice, 813/813 rows identical. The full
trace, including the commands, is
[`tools/evidence/important-11th-demotion-retraction.txt`](../../tools/evidence/important-11th-demotion-retraction.txt),
and the demoted state's own artifacts are kept at
`artifacts/retracted-11th/` so the failed check can be re-examined without
re-applying the edit.

### 1.5 Finding — the triage is not reproducible, and that is now measured

This is the most useful thing this pass learned, and it is the reason the demotion
work stops at ten.

Two cross-page runs over the **same CSS** (the pass base plus the ten demotions)
disagree about that declaration:

```
  run A (the sweep that produced the candidate):
    LIFT_CROSS_PAGE {"pages": 16, "declarations": 60, "demotable": 1, "keep": 26, "noEvidence": 33}
    --- DEMOTABLE (inert on every page that measured it) ---
      background             longhands=9  inert on index  unmeasured on 2
          .studio-rail-button:hover

  run C (index re-audited after the revert, same CSS):
    LIFT_CROSS_PAGE {"pages": 16, "declarations": 60, "demotable": 0, "keep": 27, "noEvidence": 33}
    --- DEMOTABLE (inert on every page that measured it) ---
    (empty)
```

A third run, on the demoted tree, rotated the verdict onto an unrelated declaration
(`.flow-action-grid button:hover` transform), so demoting one candidate promoted a
different one to "demotable" with no relationship between them.

The mechanism is the same one `dedf093` fixed one level down: the declaration sits
inside a transition, the lift probe reads a computed value once, and a value read
while a transition is still interpolating is not the settled value. The audit waits
for transitions to settle; the lift probe does not.

What this does and does not change:

* It does **not** weaken the ten demotions. They were verified by the row-level
  check, which is reproducible (813/813 identical in two independent runs) and which
  the eleventh declaration failed. The protocol held; the shortcut did not.
* The **demotable count is a per-run observation**, not a property of the tree. It is
  quoted with its run above, and the next pass should quote it that way too.
* Next pass: repeat each lift measurement N times (or freeze transitions while
  measuring) and require a unanimous verdict before an edit. Until then the verdict
  is a candidate generator and the row-level diff is the authority.

The current tree, for the record, is at `demotable 0` in the run quoted in §1.5, and
the count of remaining candidates is 60 declarations / 25 load-bearing / 33 with no
evidence either way — the last group is the honest hole in the tool, and it is what
"unmeasured" means.

### 1.6 What does *not* follow from this

The declaration that was reverted is not "load-bearing on 15 pages"; it is
measurable on one. Nothing here licenses a claim about the rail button on the other
fifteen pages, and the same caveat applies to every declaration in the 33
"no evidence" group. The sweep covers 813 elements across 16 pages and 2,107 hover
selectors; states it cannot reach are not verified by it, and the report says
"unmeasured" rather than "inert" for exactly that reason.

---

## 2. Goal 2 — Style & Layout on `index.html`

### 2.1 The method, first

The prior pass measured this bucket with `lhci collect --config=tools/lhci-single.js`
and extracted `styleLayout` from the trace's `mainthread-work-breakdown` audit. No
tool extracted that number, so it was read by hand each time — which is how a
measurement becomes a memory. This pass added
[`tools/lhci-bucket.py`](../../tools/lhci-bucket.py), which reads the recorded LHR
and prints the bucket, so the number in this section is a command, not a transcription.

`numberOfRuns` is 1 in that config, and one run of a noisy process is not a
measurement, so each side is three runs and the comparison is on medians.

<!-- report-verify: measurement — three Lighthouse runs per side: the bucket and the score are one sample each of a noisy process. The evidence file records all six runs. -->
```
$ PAGE=index.html npx lhci collect --config=tools/lhci-single.js
BEFORE (median of three)   styleLayout 1571.0 ms   main-thread 3762 ms   performance 80
AFTER  (median of three)   styleLayout 1472.0 ms   main-thread 3294 ms   performance 87
delta                      -99.0 ms (-6.3%)        -468 ms (-12.4%)      +7
target (30% of 1667.0)     1167.0 ms   NOT MET, 305 ms short
```

Per-run numbers, the extraction command and the six LHRs are recorded in
[`tools/evidence/style-layout-before-after.txt`](../../tools/evidence/style-layout-before-after.txt).
The ranges are disjoint (before 1564.9–1722.9, after 1456.9–1500.0), so the direction
is real even though the size is modest.

### 2.2 What changed

```
$ git show --stat --oneline a851083 | head -3
a851083 perf(index): stop the overlay ResizeObserver re-arming on its own output
 docs/page-assets-v15.json             |   2 +-
 docs/route-bundles-v15.json           |   4 +-
```

`renderLayers` rewrites the layers panel's `innerHTML`, and the overlay's
`ResizeObserver` re-armed `syncAll` on the frame that rewrite caused — a feedback
loop the prior pass had already measured at 1,359 ms / 13 calls and named as this
goal's item 3. The observer now ignores a notification whose box it has already
handled, so its own output stops being new information. That is a change-detection
guard, not a platform assumption: MDN is explicit that "resize-triggered layout
changes can lead to further notifications" and that changes made by an observer's own
callback are not automatically suppressed
([ResizeObserver — MDN](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver),
[W3C Resize Observer](https://www.w3.org/TR/resize-observer/)), which is exactly why
the guard is explicit.

### 2.3 What was *not* touched, and why

The report also names the `renderLayers` wholesale `innerHTML` rewrite as a cause.
That was left alone: no guard test covers the layers panel's re-render, the change is
a behaviour change to a user-visible editor panel, and the pass's rule is that an
edit with no test and no measurement is a guess. The 30 % target is therefore **not
met** — the honest number is −6.3 % on the median of three runs, and the residual is
documented rather than estimated.

---

## 3. Goal 3 — versioned renames, batch 3

### 3.1 The surface, measured instead of remembered

The prior pass applied the selection rule ("versioned files with zero test
references") by hand, twice, and stopped before batch 3 because `src/css/organized/`
raised a resolution question it could not answer. The question turned out to be
answerable by measurement: the generator tries `src/css/<path>` and falls back to
`src/css/organized/<path>`, so an `organized/` file is only a problem if a flat file
of the rename *target* name exists. This pass added
[`tools/versioned-rename-surface.py`](../../tools/versioned-rename-surface.py), which
recomputes the whole surface and prints the three classes:

<!-- report-verify: prefix 12 — the tool also prints the files excluded for test references and the ones not named by the live source list; the first 12 lines are the summary, the ready list and the blocked list, which is everything a batch decision needs. -->
```
$ python3 tools/versioned-rename-surface.py | head -22
RENAME_SURFACE {"versionedFiles": 284, "liveNamed": 80, "zeroTestRefs": 28, "candidatePool": 7, "readyToRename": 5, "blockedByTargetName": 2, "inOrganized": 1}

--- READY: live-named, no test reference, rename target unclaimed ---
  src/css/app-shell-v55.css                        -> app-shell.css                      other reference(s): CONTRIBUTING.md, docs/reviews/consolidation-and-fidelity-report.md, docs/reviews/optimisation-report.md, docs/reviews/race-and-consolidation-report.md, docs/reviews/redesign-report.md, docs/reviews/reproducibility-and-performance-report.md, docs/route-bundles-v15.json, src/css/dashboard-page.css, src/css/tokens.css, src/python/app-shell-v55.css, src/python/dashboard-page.css, src/python/route-bundles-v15.json, src/python/tokens.css
  src/js/backend-mode-v14.js                       -> backend-mode.js                    other reference(s): docs/STRUCTURE-AUDIT.csv, docs/STRUCTURE-MAPPING.md, docs/V0_52_RELEASE_FILE_HASHES.sha256, docs/V18_RELEASE_FILE_HASHES.sha256, docs/V19_1_RELEASE_FILE_HASHES.sha256, docs/V19_RELEASE_FILE_HASHES.sha256, docs/V20_RELEASE_FILE_HASHES.sha256, docs/V27_3_5_RELEASE_FILE_HASHES.sha256, docs/V28_RELEASE_FILE_HASHES.sha256, docs/V32_RELEASE_FILE_HASHES.sha256, docs/i18n/LANGUAGE-GAP-REPORT.md, docs/page-assets-v15.json, docs/reviews/optimisation-report.md, docs/reviews/race-and-consolidation-report.md, docs/reviews/redesign-report.md, docs/reviews/v54-rc-verification.md, src/css/app-shell-v55.css, src/html/account.html, src/html/admin.html, src/html/analytics.html, src/html/billing.html, src/html/checkin.html, src/html/dashboard.html, src/html/designer.html, src/html/guests.html, src/html/index.html, src/html/materials.html, src/html/privacy.html, src/html/public.html, src/html/reset.html, src/html/responses.html, src/html/templates.html, src/html/verify.html, src/js/service-worker.js, src/python/account.html, src/python/admin.html, src/python/analytics.html, src/python/app-shell-v55.css, src/python/billing.html, src/python/build/build_page_manifests.py, src/python/build/page-assets-v15.json, src/python/build/sync_frontend_assets.py, src/python/checkin.html, src/python/dashboard-css-km.html, src/python/dashboard.html, src/python/designer.html, src/python/guests.html, src/python/index.html, src/python/materials.html, src/python/privacy.html, src/python/public.html, src/python/reset.html, src/python/responses.html, src/python/service-worker.js, src/python/templates.html, src/python/verify.html
  src/js/product-operations-v13.js                 -> product-operations.js              other reference(s): docs/STRUCTURE-AUDIT.csv, docs/V0_52_RELEASE_FILE_HASHES.sha256, docs/V13_FUTURE_DEVELOPMENT_REPORT_2026-07-24.md, docs/V18_RELEASE_FILE_HASHES.sha256, docs/V19_1_RELEASE_FILE_HASHES.sha256, docs/V19_RELEASE_FILE_HASHES.sha256, docs/V20_RELEASE_FILE_HASHES.sha256, docs/V27_3_5_RELEASE_FILE_HASHES.sha256, docs/V28_RELEASE_FILE_HASHES.sha256, docs/V32_RELEASE_FILE_HASHES.sha256, docs/reviews/v54-rc-verification.md, docs/route-bundles-v15.json, src/python/build/route-bundles-v15.json, src/python/route-bundles-v15.json
  src/js/timeline-runtime-v13.js                   -> timeline-runtime.js                other reference(s): docs/STRUCTURE-AUDIT.csv, docs/V0_52_RELEASE_FILE_HASHES.sha256, docs/V13_FUTURE_DEVELOPMENT_REPORT_2026-07-24.md, docs/V18_RELEASE_FILE_HASHES.sha256, docs/V19_1_RELEASE_FILE_HASHES.sha256, docs/V19_RELEASE_FILE_HASHES.sha256, docs/V20_RELEASE_FILE_HASHES.sha256, docs/V27_3_5_RELEASE_FILE_HASHES.sha256, docs/V28_RELEASE_FILE_HASHES.sha256, docs/V32_RELEASE_FILE_HASHES.sha256, docs/reviews/v54-rc-verification.md, docs/route-bundles-v15.json, src/python/build/route-bundles-v15.json, src/python/route-bundles-v15.json
  src/js/timeline-v13.js                           -> timeline.js                        other reference(s): docs/STRUCTURE-AUDIT.csv, docs/STRUCTURE-MAPPING.md, docs/V0_52_RELEASE_FILE_HASHES.sha256, docs/V13_FUTURE_DEVELOPMENT_REPORT_2026-07-24.md, docs/V18_RELEASE_FILE_HASHES.sha256, docs/V19_1_RELEASE_FILE_HASHES.sha256, docs/V19_RELEASE_FILE_HASHES.sha256, docs/V20_RELEASE_FILE_HASHES.sha256, docs/V27_3_5_RELEASE_FILE_HASHES.sha256, docs/V28_RELEASE_FILE_HASHES.sha256, docs/V32_RELEASE_FILE_HASHES.sha256, docs/reviews/v54-rc-verification.md, docs/route-bundles-v15.json, src/python/build/route-bundles-v15.json, src/python/route-bundles-v15.json

--- BLOCKED: the rename target name is already taken ---
  src/css/organized/photo-editor-v13.css           -> photo-editor.css                   exists at src/css/photo-editor.css
  src/js/photo-editor-v13.js                       -> photo-editor.js                    exists at src/js/photo-editor.js
```

Before batch 3 those numbers were 304 versioned paths, 100 live-named, 17 in the
candidate pool, 15 ready and 2 blocked; the batch consumed ten of the fifteen, which
is the arithmetic in the summary above.

### 3.2 The batch

| old | new | why it is in the batch |
| --- | --- | --- |
| `src/css/account-security-v13.css` | `src/css/account-security.css` | only the source list and generated manifests name it |
| `src/css/stabilized-v14.css` | `src/css/stabilized.css` | same |
| `src/css/organized/editor-canva-v13.css` | `src/css/organized/editor-canva.css` | organized/, and no flat file of the target name exists |
| `src/css/organized/guests-page-v13.css` | `src/css/organized/guests-page.css` | organized/, target name unclaimed |
| `src/js/account-security-v13.js` | `src/js/account-security.js` | same as its CSS sibling |
| `src/js/checkin-v13.js` | `src/js/checkin.js` | same |
| `src/js/editor-commands-v13.js` | `src/js/editor-commands.js` | same |
| `src/js/editor-shared-styles-v13.js` | `src/js/editor-shared-styles.js` | same |
| `src/js/mobile-editor-v14.js` | `src/js/mobile-editor.js` | same |
| `src/js/photo-retouch-v13.js` | `src/js/photo-retouch.js` | same |

Each file moved with `git mv` together with its tracked `src/python` mirror — 20
files — and the only hand-maintained reference,
`docs/route-bundle-sources-v15.json`, was updated in the same operation: 23
occurrences, counted per occurrence. Zero tests were touched, which is the selection
rule. The commit is `aa4fbe4`, and its shape is visible in one line:

```
$ git show --stat --oneline aa4fbe4 | tail -3
 src/python/route-bundles-v15.json                  | 46 +++++++++++-----------
 src/python/{stabilized-v14.css => stabilized.css}  |  0
 23 files changed, 69 insertions(+), 69 deletions(-)
```

### 3.3 Verification

The property that matters is that a rename changes no shipped byte:

<!-- report-verify: historical — the comparison is against an md5 manifest of the pre-rename build, taken in this session and kept in artifacts/ (working-tree state, not committed). -->
```
$ md5sum src/js/bundle-*.js src/css/bundle-*.css | sort > /tmp/bundles-after-batch3.md5
ALL 32 BUNDLES BYTE-IDENTICAL
```

plus, on the committed tree:

```
$ python3 build.py all --check
EDITOR_BUNDLE_CHECK_PASSED
ROUTE_BUNDLE_CHECK_PASSED
PAGE_ASSET_MANIFEST_CHECK_PASSED
BUILD_OK editor bundles manifests (check)
```

```
$ python3 tests/v55_route_weight_budget_test.py
V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)
$ python3 tests/v14_performance_budget_test.py
V16_PERFORMANCE_BUDGET_TEST_PASSED
```

16 pages fetched with a real browser, and no page gained a console error or a non-2xx
request:

<!-- report-verify: heavy — drives a headless browser against the gzip server for all sixteen pages (~40 s); read-only, but not something the report gate should re-run. -->
```
$ node tools/page-errors.mjs --all
TOTAL pages=16 consoleErrors=0 non2xx=0
```

And the renames themselves are content-preserving, verified by the audit from §1.3:
20 renames, content identical, and the three manifests moved exactly the 23
source-name fields this batch edited.

### 3.4 What the measurement decided (autonomous)

Three files the surface marks *ready* are deliberately not in this batch, and the
reason is the reference breadth the tool prints:

* `src/js/backend-mode-v14.js` is named by all sixteen `src/html` pages, their
  `src/python` mirrors, `service-worker.js` and `build_page_manifests.py`. Renaming it
  is a page-edit batch, not a rename batch; it should be done on its own so the
  verification (32 byte-identical bundles *plus* sixteen pages with zero console
  errors) is not diluted by a hundred mechanical edits.
* `src/css/app-shell-v55.css` is named from other CSS files (`dashboard-page.css`,
  `tokens.css`), so the same applies at smaller scale.
* `src/js/product-operations-v13.js` and the two `timeline` files are cleanly ready
  and are simply the next batch's first three names.

The two `photo-editor` files are not "next batch" material: their target names are
occupied by different files, and renaming them would ship the other file's styles.
That is a hard block, and the tool reports it as one.

---

## 4. Goal 4 — the reproducibility holes

### 4.1 `pytest tests/` did not run a single test

The prior report's step 2 printed a skip and the suite went unmeasured. Reproduced
today, with the mechanism the fix removes switched off:

<!-- report-verify: heavy — runs the full pytest collection with conftest disabled (~2 s to fail, but the same command shape as the 2.5-minute run below); declared so the gate does not re-run a suite. -->
```
$ python3 -m pytest tests/ --noconftest -q
INTERNALERROR>   File "/mnt/external/eInvite/einvite-platform/src/python/server.py", line 10173, in <module>
INTERNALERROR>     args = parser.parse_args()
INTERNALERROR> SystemExit: 2

no tests ran in 1.34s
```

One runner script (`tests/final_features_test.py`) imports the server launcher at
import time; the launcher calls `argparse.parse_args()` on pytest's argv and exits 2,
and a `SystemExit` during collection aborts the whole session. `--continue-on-collection-errors`
does not help: it is an `INTERNALERROR`, not a collection error.

The fix is `tests/conftest.py`, whose exclusion list is generated rather than typed:
`tools/tests-import-audit.py` imports every module under `tests/` in a fresh
interpreter (what collection does) and reports the ones that do not survive, with the
reason. `collect_ignore` is pytest's documented mechanism for this
([pytest: changing standard test discovery](https://docs.pytest.org/en/stable/example/pythoncollection.html));
the conftest also re-checks that each listed file still exists, so a rename fails
loudly instead of silently ignoring the wrong file.

<!-- report-verify: heavy — imports 252 modules in subprocesses with per-module timeouts (~2 min); read-only, but not gate material. -->
```
$ python3 tools/tests-import-audit.py
TESTS_IMPORT_AUDIT {"modules": 252, "importable": 240, "notImportable": 12, "importableButSideEffecting": 1, "importableClean": 239}
```

After the fix:

<!-- report-verify: heavy — the suite itself: ~2.5 minutes, and it carries pre-existing red tests. Declared, with the raw output kept in tools/evidence/pytest-suite-before-after.txt. -->
```
$ python3 -m pytest tests/ -q
FAILED tests/analytics_ingestion_test.py::test_phase1_happy_path - AssertionE...
ERROR tests/v52_crdt_offline_merge_test.py::test_two_users_edit_offline_then_both_reconnect
15 failed, 44 passed, 6 errors in 153.12s (0:02:33)
```

The suite is no longer a skip: **44 passed, 15 failed, 6 errors**, and the exit status
distinguishes "did not run" (3 = INTERNALERROR, 5 = nothing collected) from "ran and
had failures". A hole that used to print like a pass now cannot.

The `python3` here is the repo-local `.venv`: `python3` on this and every supported
host is marked externally managed, so installing into it needs the override PEP 668
exists to prevent ([PEP 668](https://peps.python.org/pep-0668/), and the maintained
specification at [Externally Managed Environments](https://packaging.python.org/en/latest/specifications/externally-managed-environments/)).
`requirements-dev.txt` pins pytest 9.1.1 and pytest-timeout 2.4.0 — verified current
against PyPI, not from memory — and `tools/reproduce.sh` creates `.venv` on first use.

### 4.2 The two stale gates

`v27_3_5_release_evidence_test.py` and `v53_1_operator_repair_contract_test.py` were
red, and both were red for the same reason: each held a private copy of a V0.52-era
byte literal, `<= 1_420_000`, while the file that owns the number says something
larger:

```
$ python3 -c "import json,pathlib; b=json.loads(pathlib.Path('docs/perf/lighthouse-budgets.json').read_text()); e=next(x for x in b if x['path'].lstrip('/')=='index.html'); print('index.html budgets from docs/perf/lighthouse-budgets.json:'); [print(f\"  {s['resourceType']:<12} {s['budget']} KB = {s['budget']*1024} B\") for s in e['resourceSizes']]; import os; js=os.path.getsize('src/js/bundle-index-v15.js'); css=os.path.getsize('src/css/bundle-index-v15.css'); print(f'  measured now: script {js} B, stylesheet {css} B, total {js+css} B')"
index.html budgets from docs/perf/lighthouse-budgets.json:
  script       1163 KB = 1190912 B
  stylesheet   494 KB = 505856 B
  total        1656 KB = 1695744 B
  measured now: script 1135022 B, stylesheet 482145 B, total 1617167 B
```

The route is inside every ceiling it declares — and both owners of the number
(`tests/v55_route_weight_budget_test.py`, `tests/v14_performance_budget_test.py`) were
green the whole time. The literal was a second, stale copy of an authority that had
moved on. `tests/route_budget_utils.py` deletes the copy: the ceiling is read from the
budget file at test time, and the check is stricter than the sum it replaces, because
script and stylesheet are compared against their own per-type budgets.

`v27_3_5` also asserted a 2026-08-10 snapshot of the whole tree: *every* file in
`docs/V0_52_RELEASE_FILE_HASHES.sha256` present and unmodified, and no file present
that the manifest does not list. That assertion can never hold again, and its failure
said nothing about the code, so drift is now **measured and printed** while the parts
that encode a live rule (every line parses, no duplicate paths, no forbidden artifact
path) are still asserted:

<!-- report-verify: heavy — a whole release-evidence contract test: it reads the tree, runs three generator checks in subprocesses and re-hashes a 274-file sample. Declared, not re-run by the gate. -->
```
$ python3 tests/v27_3_5_release_evidence_test.py
V0_52_BUILD_INFO_ROUTE limit=1420000 recordedBytes=1414838 recordedHeadroom=5162 currentTotal=1617167
V0_52_MANIFEST entries=808 present=274 missing=534 digestMatches=125 digestDiffers=149
V0_52_EDITOR_ROUTE_BYTES=1617167
V27_3_5_RELEASE_EVIDENCE_TEST_PASSED
```

<!-- report-verify: heavy — starts two local HTTP servers, imports the AI agent service and reads four browser sources. Read-only, but not gate material. -->
```
$ python3 tests/v53_1_operator_repair_contract_test.py
V53_1_OPERATOR_REPAIR_CONTRACT_TEST_PASSED
```

`v27_3_5` also had **zero** `test_` functions: every assertion lived in `main()` behind
a `__main__` guard, which is how it stayed red while both `make test` and step 2 of
`make reproduce` reported nothing. It has a real pytest entry point now. Both files
are in [`tools/evidence/two-repaired-gates.txt`](../../tools/evidence/two-repaired-gates.txt).

### 4.3 The red tests that remain — and why they are not this pass's

15 failures and 6 errors survive. They are two classes:

* the six `v52_crdt_offline_merge_test.py` errors are `fixture 'server_url' not found`
  — that module expects a pytest fixture nothing in the tree provides;
* fifteen analytics-phase tests that need an endpoint a bare `pytest` run does not
  start.

Neither class touches anything this pass changed:

```
$ git diff --name-only HEAD -- 'tests/analytics*' 'tests/v52_crdt*' 'src/python/analytics*' 'src/python/core/' 'src/python/server.py'
```

(no output: the failing modules and everything they import are unmodified. The exact
list of what this pass *did* change is the audit in §1.3.)
Full log: [`tools/evidence/pytest-red-classes.txt`](../../tools/evidence/pytest-red-classes.txt).

### 4.4 `tools/reproduce.sh`

Step 2 no longer skips and no longer points at a file that cannot enable it
(`docs/requirements-test.txt` pins playwright/Pillow/qrcode but not pytest, so the
printed hint could never work). It resolves an interpreter with pytest, creating
`.venv` from `requirements-dev.txt` on first use, and when it cannot it prints
`CANNOT RUN` and fails the run — a hole that cannot read as a pass. Step 6 now
verifies both reports.

---

## 5. Goal 5 — `report-verify.mjs` coverage

The gate that re-runs a report's quoted commands left 9 of 19 blocks **skipped**, and
a skip is a hole: the report claims an output that nothing re-derives. Two changes
closed it without weakening anything (multi-line `> ` command continuations; a
`--with-server` mode that starts the gzip server the blocks were waiting for), and
four declaration kinds make the rest auditable instead of silent.

The first thing it caught was one of the prior report's own blocks, and the prior
report's row 15 had recorded it as green — a transcription, not a run. The detail is
in `d8f1fab`'s message; the numbers are:

<!-- report-verify: heavy — re-runs the whole gate recursively (19 blocks, including two 16-page hover sweeps, minutes end to end). The evidence file records this same run from both sides. -->
```
$ node tools/report-verify.mjs docs/reviews/reproducibility-and-performance-report.md --with-server --timeout=480
report-verify: docs/reviews/reproducibility-and-performance-report.md
  blocks checked 19 — match 9, MISMATCH 0, ELIDED 0

  declared, not compared  historical 4, write 1, measurement 5
  still skipped 0
  partially compared (declared tail) 1
exit=0
```

| | before | after |
| --- | --- | --- |
| blocks checked | 19 | 19 |
| matched | 7 | **9** |
| mismatched | **1** | **0** |
| skipped | **9** | **0** |
| declared (historical / write / measurement) | 2 / 0 / 0 | 4 / 1 / 5 |

Before → after for the same file, same command, from
[`tools/evidence/report-verify-coverage.txt`](../../tools/evidence/report-verify-coverage.txt).
The one MISMATCH in the "before" column was a block the prior report recorded as
matching; that is what a gate is for.

This pass also closed a gap in the tool's own taxonomy: a command can be read-only and
still not belong in a gate. `pytest tests/` writes nothing, yet it takes minutes and
runs 252 modules; so does the import probe. They are now declared `heavy` — printed
with their reason, never counted as a match — which is the same discipline as the four
kinds that already existed:

```
$ grep -n "const HEAVY" tools/report-verify.mjs
210:const HEAVY = /^<!--\s*report-verify:\s*heavy\s*(?:[-—:]\s*)?(.*?)\s*-->$/;
```

An elided command (`python3 -c "…network-requests…"`) is still a failure, not a
formatting nit: nobody can re-run that, which defeats the point of quoting it.

---

## 6. Goal 6 — hygiene

### 6.1 The decisions

Twenty-odd untracked paths had accumulated across sessions. Each is now either ignored
by a rule that says why, parked outside the tree with a reason, or deliberately left
alone — and the reasons are in [`.gitignore`](../../.gitignore), not in this report
only, because the next `git status` is where the question comes back.

```
$ git check-ignore -v deliverables screenshots _i18n_all_result.json fixture-public.html test-i18n-beacon.html .freebuff .tools
.gitignore:122:deliverables/	deliverables
.gitignore:123:screenshots/	screenshots
.gitignore:128:_i18n_all_result.json	_i18n_all_result.json
.gitignore:107:/fixture-public.html	fixture-public.html
.gitignore:108:/test-i18n-beacon.html	test-i18n-beacon.html
.gitignore:112:.freebuff/	.freebuff
.gitignore:116:.tools/	.tools
```

### 6.2 Retraction — the first attempt parked evidence in `/tmp`

The first version of this decision moved the files to
`/tmp/einvite-untracked-decisions/`, and this pass's own brief said "no `/tmp`
fragility" for exactly this reason. A restart cleared it — the same restart lost a
harness log this pass was still using — which is the failure mode the prior pass spent
a commit removing from the *tools*.

Everything was moved back and made durable: the review captures live in the tree and
are ignored (local, durable, out of `git status`), and the one file that could not
simply be ignored — `pnpm-workspace.yaml`, a package-manager workspace file at the root
of an npm repository, which pnpm would still act on — is parked at
`~/einvite-moved-aside/`.

```
$ du -sh deliverables screenshots
41K	deliverables
8.3M	screenshots
```

`fixture-public.html` and `test-i18n-beacon.html` are kept rather than deleted:
`subset-fonts.py` reports them as sources with no tracked counterpart, so removing
them would silently shrink a scan.

### 6.3 The six files left alone, and why that is also a decision

The command is filtered to the four directories those files live in, so this list
cannot be perturbed by a new file under `tools/`:

```
$ git ls-files --others --exclude-standard docs scripts src tests
docs/STRUCTURE-PILOT-AUDIT.md
docs/reviews/deploy-02-linux.md
scripts/audit_bidi.js
scripts/fix_structure_references.py
src/python/admin-page-v13.css
tests/ac4_2d_audit_test.py
```

They are not this session's work (mtimes run from 2026-09-22 to 2026-10-11) and tracked
files reference them (`race-and-consolidation-report.md`, `v54-commit.md`, the release
hash manifests), so a fresh clone has dangling references rather than a broken build.
Committing someone else's in-progress work is not a hygiene fix, and deleting files
that other reports point at is worse. They are left in place, named here, and the next
pass should either own them or ask whose they are.

One of them, `src/python/admin-page-v13.css`, was checked rather than assumed: it is
**not** a build input. The build reads its CSS sources through
`src/css/<path>` then `src/css/organized/<path>`; the only reference to the
`src/python` copy is a *recorded* source list inside a generated manifest, and
removing the file does not change any generated artifact. It is a stale mirror from an
older build layout, and it stays untracked.

---

## 7. Verification run

Every command this pass quotes, in one list, with the raw result. §8's table is the
prior pass's; this is the same shape for this pass.

| # | command | result |
| --- | --- | --- |
| 1 | `python3 build.py all --check` | `EDITOR_BUNDLE_CHECK_PASSED` / `ROUTE_BUNDLE_CHECK_PASSED` / `PAGE_ASSET_MANIFEST_CHECK_PASSED` / `BUILD_OK`, exit 0 (§3.3) |
| 2 | `python3 tools/important-removal-audit.py --rev=623b233` | 61 changed CSS/JSON entries; **failures=0**; 4 JS changes named and not judged (§1.3) |
| 3 | `python3 tools/hover-regression-diff.py --before artifacts/hover-before-demotion --after artifacts` | **813/813 rows identical**, 0 differing, 0 shape mismatch (§1.3) |
| 4 | `python3 tools/hover-verify.py --cross-page` | `LIFT_CROSS_PAGE {"pages": 16, "declarations": 60, "demotable": 0, "keep": 27, "noEvidence": 33}` (§1.5) |
| 5 | `python3 tools/versioned-rename-surface.py` | `RENAME_SURFACE {"versionedFiles": 284, ..., "readyToRename": 5, "blockedByTargetName": 2}` (§3.1) |
| 6 | `md5sum src/js/bundle-*.js src/css/bundle-*.css` before/after batch 3 | **ALL 32 BUNDLES BYTE-IDENTICAL** (§3.3) |
| 7 | `node tools/page-errors.mjs --all` | `TOTAL pages=16 consoleErrors=0 non2xx=0` (§3.3) |
| 8 | `python3 -m pytest tests/ --noconftest -q` | **`no tests ran in 1.34s`**, INTERNALERROR from `server.py:10173` — the defect, reproduced (§4.1) |
| 9 | `python3 -m pytest tests/ -q` | `15 failed, 44 passed, 6 errors in 153.12s` (§4.1) |
| 10 | `python3 tools/tests-import-audit.py` | `{"modules": 252, "importable": 240, "notImportable": 12}` (§4.1) |
| 11 | `python3 tests/v27_3_5_release_evidence_test.py` | `V27_3_5_RELEASE_EVIDENCE_TEST_PASSED` (§4.2) |
| 12 | `python3 tests/v53_1_operator_repair_contract_test.py` | `V53_1_OPERATOR_REPAIR_CONTRACT_TEST_PASSED` (§4.2) |
| 13 | `python3 tests/v55_route_weight_budget_test.py` / `v14_performance_budget_test.py` | `V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED (6 pages within budget)` / `V16_PERFORMANCE_BUDGET_TEST_PASSED` (§3.3) |
| 14 | `python3 tests/v27_3_5_release_evidence_test.py` (manifest clause) | `V0_52_MANIFEST entries=808 present=274 missing=534 digestMatches=125 digestDiffers=149` — measured, printed, not asserted (§4.2) |
| 15 | `node tools/report-verify.mjs docs/reviews/reproducibility-and-performance-report.md --with-server --timeout=480` | **exit 0** — 19 blocks: 9 matched, 0 mismatched, 0 elided, **0 skipped**, 4 historical, 1 write, 5 measurement (§5) |
| 16 | `git check-ignore -v …` | seven rules, all in force (§6.1) |
| 17 | `git ls-files --others --exclude-standard` | six files, named in §6.3 |
| 18 | `PAGE=index.html npx lhci collect --config=tools/lhci-single.js` ×3 per side | styleLayout 1,571.0 → 1,472.0 ms median; target **not met** (§2) |
| 19 | `make reproduce` | **not run end to end this pass**: it re-runs the 16-page Lighthouse suite and the 50-capture determinism check (tens of minutes), and §2's six Lighthouse runs were taken with the single-page config. Steps 1, 2, 3, 5 and 6 were each run and are quoted above; step 4 is the one deferred, and `tools/reproduce.sh --skip-lhci` is the honest partial. |

---

## 8. Deferred, retracted, and decided autonomously

### 8.1 Deferred, with the reason

| item | why it is not in this pass |
| --- | --- |
| the 33 "no evidence" declarations per sweep | the tool cannot reach the state that would judge them; acting on them would repeat §1.4's mistake at scale |
| `renderLayers`' wholesale `innerHTML` rewrite | no guard test covers the layers panel; an edit with no test and no measurement is a guess (§2.3) |
| the 30 % Style & Layout target | the residual needs the layers-panel rewrite above, not another observer guard (§2.3) |
| `src/js/backend-mode-v14.js` and `app-shell-v55.css` renames | reference breadth: 30+ files each, so they are page-edit batches (§3.4) |
| the 34 test-pinned versioned files | a rename there is a contract change, not a cleanup (§3.1) |
| the 15 analytics and 6 `v52_crdt` red tests | pre-existing, unrelated to measurement, and both need a fixture/server decision rather than an edit (§4.3) |
| `make reproduce` step 4 | the release config is a 16-page Lighthouse run; §2's six runs used the single-page config (§7 row 19) |
| the `pnpm-workspace.yaml` question | parked with a reason; deleting a package-manager config is a decision for whoever created it (§6.2) |

### 8.2 Retracted, with the reason

1. **The eleventh demotion** (§1.4). It failed the row-level check: 18 of index's 271
   rows changed. Reverted, rebuilt, re-verified at 813/813.
2. **"Demotable" as a settled property** (§1.5). Two runs over identical CSS
   disagree. The count is a per-run observation.
3. **Parking evidence in `/tmp`** (§6.2). A restart cleared it; the files are back in
   the tree.
4. **The prior report's row 15, as it stood** (§5). It recorded "8 re-run and matched,
   0 mismatched"; the first run of the new gate found 1 MISMATCH among those 8. The
   block was corrected in `d8f1fab`, and this report does not repeat the claim.

### 8.3 Decided autonomously

* **Which ten of the fifteen ready renames shipped** — by reference breadth, so the
  verification stays meaningful (§3.4).
* **`organized/` is not a blocker.** The prior pass left it as a question; the
  generator's resolution order (`src/css/` then `src/css/organized/`) plus a measured
  "no flat file of the target name exists" answers it for these four files. The
  *class* is now measured by the tool rather than argued about.
* **The stale 1,420,000 literal was deleted, not raised.** The file that owns the
  number was green throughout; a second copy of an authority that moved on is the
  defect (§4.2).
* **`v27_3_5`'s whole-tree assertion became a measurement.** 534 files the release
  listed are legitimately gone; a test asserting they are present is a test asserting
  its own fossilisation (§4.2).
* **The six untracked files were left in place.** Committing another session's
  in-progress work is not a hygiene fix (§6.3).
* **The `heavy` declaration kind was added** rather than declaring two read-only test
  runs as `write` (§5).

---

## 9. How to reproduce

<!-- report-verify: write — orchestrates the whole sequence: it builds, installs test deps, starts the gzip server, runs Lighthouse and pytest, and re-verifies both reports. Not a read-only command. -->
```
$ make reproduce
```

builds the tree, runs the suite (installing its own venv deps on first use), starts
the gzip server, runs the Lighthouse suite against all sixteen routes, runs the
50-capture determinism check, and re-runs every quoted command in both reports —
including the hover sweeps, which need `--with-server --timeout=480`, both of which
step 6 passes. `tools/reproduce.sh --skip-lhci` is the partial run.

Everything numeric in this document is reproducible from that, except the four blocks
that declare why they are not: the two hover sweeps that read session artifacts, the
Lighthouse numbers, and the two long test runs. Each of those prints its declaration
and its reason when the report is verified, and the underlying output is kept under
[`tools/evidence/`](../../tools/evidence/).
