# Wiring the analytics feature, expanding the unanimity sweep, and the Style & Layout residual

This is the report for the pass that ran on branch `main` over base `fbd17d2`. It is
written to the same standard as `docs/reviews/canva-analysis-and-closure-report.md`,
which is the house standard: every number is printed next to the command that produced
it, raw evidence is in `tools/evidence/`, and every experiment that failed is kept with
its reason instead of being deleted.

Re-verify the quotes in this file with
`node tools/report-verify.mjs docs/reviews/analytics-and-unanimity-report.md`; §6.6 records
what that run reported. A block marked with a `<!-- report-verify: \u2026 -->` declaration is one
the gate cannot re-run (it needs a server, a browser, or minutes of wall clock); everything
else in a `$`-block is re-run and byte-compared.

Five goals, in the order the brief put them: wire the analytics feature and turn its 15
red tests green; expand the unanimity sweep until it has something to act on; diagnose
the Style & Layout gap; resolve the Playwright step-0b check; and, if time permitted,
extend the Canva analysis. Goals 1–4 were attempted; Goal 5 was not, and §5 says why.

<!-- report-verify: historical the commit list is this pass's own history; HEAD moves when this report is committed -->

```
$ git log --oneline fbd17d2..HEAD
078e2a0 chore(tools): let the recalc attribution read the traces the other probes write
7f1f504 chore(tools): pin the isolated Playwright install with its own lockfile
72e2abf chore(tools): make the Playwright step-0b check pass without touching package.json
988637f refactor(css): demote an !important the expanded sweep calls unanimously inert
dd64298 feat(analytics): route the creator-analytics feature that was never wired
```

## 1. Goal 1 — the analytics feature was built, and nothing routed to it

### 1.1 The before state

`tools/evidence/analytics-before.txt` is the full `pytest -k analytics` run taken before
any change this pass. The head of the log shows every failure returning
`{"error": "Not found"}`:

```
$ tail -3 tools/evidence/analytics-before.txt
FAILED tests/analytics_reports_test.py::test_phase5_export_account_csv - Asse...
FAILED tests/analytics_reports_test.py::test_phase6_live_endpoint_feature_flag
15 failed, 5 passed, 48 deselected in 45.95s
```

15 failed, 5 passed. The 5 that passed are the two that only import the module
(`test_phase5_background_reconstruction`, `test_phase6_module_declarations` in the
ingestion suite), the JS/static check in the reports suite, and the two documentation
checks in the privacy suite: none of them needs an HTTP route.

### 1.2 The gap, endpoint by endpoint

The prior pass inventoried this in `tools/evidence/analytics-wiring-gap.txt` and
refused to fake a pass. Its method and its conclusion:

```
$ sed -n '1,20p' tools/evidence/analytics-wiring-gap.txt
ANALYTICS_WIRING_GAP — the endpoints the analytics suites call, and whether
src/python/server.py serves them

The feature is fully built in src/python/features/analytics/:
  model.py    schema, record_event_batch, purge_invitation_analytics,
              set_invitation_analytics_enabled, is_invitation_analytics_enabled
  sessions.py close_idle_sessions, delete_spam_sessions, aggregate_daily_summary,
              run_retention_prune, run_session_reconstruction
  queries.py  ten read-model functions, including live activity and account summaries
  export.py   invitation and account CSV + JSON streams
What is missing is the wiring: server.py does not route to most of it.

This column is a literal search of the server source, so it is a lower bound on what
is routed: two paths that work are matched by pattern rather than by literal (below).

path a suite calls                                           literal in server.py?
/api/account/analytics/creations                                                no
/api/account/analytics/creations?sort=views&order=asc                           no
/api/account/analytics/creations?status=draft                                   no
/api/account/analytics/export?format=csv                                        no
```

Reading that inventory against the code: `src/python/features/analytics/` is complete
(`model.py` schema + ingestion, `sessions.py` reconstruction job, `queries.py` read
models, `export.py` CSV/JSON streams) and importing it works — the module-declaration
test proved that before this pass. What did not exist was a single route in
`src/python/server.py` pointing at it. Not one of the feature's public functions was
called from the server.

### 1.3 What was wired

`feat(analytics)` (`dd64298`), +226 lines in `src/python/server.py`, +20 in
`features/analytics/model.py`:

| route | who may call it | behaviour |
| --- | --- | --- |
| `POST /api/analytics/events` | public, unauthenticated | first-party ingestion for the guest page; CSRF-exempt by design, rate-limited 60/min per client IP. 204 on success, 400 for a malformed batch, 404 for an unknown invitation, and 204-with-nothing-stored when the host turned analytics off for that invitation — the guest page must not be able to detect the host's choice (§6.7). |
| `GET /api/invitations/{id}/analytics` | owner | the existing response, unchanged, plus an `"analytics"` key carrying the Part-6 payload (stats, timeseries, funnel, referrers, scroll depth, device + country split) |
| `GET /api/invitations/{id}/analytics/live` | anyone who can read the invitation | gated on the `analytics_live_enabled` flag; 403 with `code=feature_disabled` when off |
| `GET /api/invitations/{id}/analytics/export?format=csv\|json` | owner | streamed CSV/JSON of raw sessions + events |
| `POST /api/invitations/{id}/analytics/disable` | owner | `{"enabled": bool}`; audit-logged; 403 for a non-owner |
| `DELETE /api/invitations/{id}/analytics` | owner | purges sessions + events + daily summaries and reports the counts; 403 for a non-owner |
| `GET /api/account/analytics/creations` | owner | sortable/filterable creations table |
| `GET /api/account/analytics/summary` | owner | account rollup |
| `GET /api/account/analytics/export?format=csv\|json` | owner | the account's analytics concatenated across its invitations |

Two pieces of wiring are not routes:

* **Schema at boot and on first use.** Every handler calls `ensure_analytics_ready()`
  inside its own connection, and boot creates the tables too, so a long-lived process
  that predates this version still works. `ensure_analytics_ready` resolves the one
  dialect difference in the feature's DDL rather than duplicating it.
* **The 5-minute reconstruction job.** `features/analytics/sessions.py` documents that
  "server.py owns the scheduler loop" for closing idle sessions, deleting spam
  sessions, aggregating the daily summary and pruning past the retention window. No
  such loop existed. There is one now (`analytics_reconstruction_loop`, daemon thread,
  300 s), following the same pattern as the existing studio-backup scheduler.

### 1.4 The after state

```
$ tail -2 tools/evidence/analytics-after.txt
....................                                                     [100%]
20 passed, 48 deselected in 47.17s
```

and the suite that contains everything else:

<!-- report-verify: measurement needs .venv and ~135 s, and two of these tests drive a browser -->

```
$ .venv/bin/python -m pytest tests/ -q
....................................................................     [100%]
68 passed in 132.65s (0:02:12)
```

That run predates the `!important` demotion (§6), and a passing run does not cover a
later change to generated bundle CSS that these tests read. Re-run on the final tree —
the demotion and the tools commits applied, the unrelated working-tree files of §9
present in both runs:

<!-- report-verify: measurement needs .venv and ~135 s; the numbers are also in tools/evidence/pytest-full-final-tree.txt -->

```
$ .venv/bin/python -m pytest tests/ -q
....................................................................     [100%]
68 passed in 133.32s (0:02:13)
```

The full suite went from **15 failed / 53 passed** to **68 passed**, and holds after the
demotion.

### 1.5 The one branch the shipped test cannot reach, and how it was proved anyway

`tests/analytics_reports_test.py::test_phase6_live_endpoint_feature_flag` checks the
flag-off branch (403) and then tries to flip the flag by **POSTing** to
`/api/admin/feature-flags`. That write route is PUT-only, requires `role=admin` and
takes `{"updates": [{key, value}]}` — so the test's own 200-branch can never execute and
it prints "skipped" instead. That is a hole in the test, not something to paper over by
weakening the endpoint, and it is left as it is.

`tools/analytics-live-flag-probe.py` exercises that branch against a real server:
register + login, create an invitation, ingest a view, check the 403, promote the user
to admin in the server's own database, PUT the flag, and re-check.

```
$ cat tools/evidence/analytics-live-flag-probe.txt
[ok] ingest accepted (204) before the flag is touched status=204
[ok] live is 403 feature_disabled by default status=403 body={'error': 'Live analytics is not enabled', 'code': 'feature_disabled'}
[ok] admin PUT flips analytics_live_enabled status=200 body=b'{"updated": 1, "flags": [{"key": "ai_agent_enabled", "description": "Master switch for the AI creative agent", "value": true, "tier": null, "updatedAt": null, "'
[ok] live returns 200 with activeSessions + lastEventAt once the flag is on status=200 body={'activeSessions': 1, 'lastEventAt': 1791789991393}
[ok] live is 404 for a non-host status=404
[ok] ingest for an unknown invitation is 404 status=404
[ok] ingest with an invalid sessionId is 400 status=400

ANALYTICS_LIVE_FLAG_PROBE: 7/7 checks passed
```

7/7 checks, including the 200 with `activeSessions`/`lastEventAt` that the shipped test
cannot produce.

### 1.6 The PostgreSQL list is a translation, not a second schema

Making the feature importable on both supported backends needs one token to differ:

```
$ cat tools/evidence/analytics-wiring-extras.txt
sqlite tables: ['analytics_events', 'analytics_sessions', 'analytics_summary_daily']
pg     tables: ['analytics_events', 'analytics_sessions', 'analytics_summary_daily']
DIALECT_LISTS_OK (same 3 tables, no AUTOINCREMENT in the PG list, 1 BIGSERIAL)
run_session_reconstruction -> {'closedIdleSessions': 1, 'deletedSpamSessions': 0, 'aggregatedRows': 0, 'pruned': {'events': 0, 'sessions': 0, 'summaries': 0, 'retentionDays': 365, 'cutoffMs': 1760254001934}}
idle session ended_at: 1791788201925 duration_ms: 3600000 daily rows: 0
RECONSTRUCTION_ENTRYPOINT_OK
```

`PG_SCHEMA_STATEMENTS` is derived from `SCHEMA_STATEMENTS` by that one replacement, so
the two cannot drift; `dialect` defaults to `"sqlite"`, so every existing caller is
unchanged. **UNVERIFIED on this host**: no PostgreSQL server is installed, so the
PostgreSQL statements are verified as *text* (same three tables, no `AUTOINCREMENT`, one
`BIGSERIAL`) and not by execution. That is stated again in §8.

### 1.7 Goal 1 — what was not done

* No test was loosened, skipped or deleted. The 15 red tests are green on the code, not
  on a weakened assertion.
* The feature's own docstrings have two stale references this pass did not fix, because
  they are documentation drift rather than a defect in the routed behaviour:
  `__init__.py` documents `enable_invitation_analytics` where the function is
  `set_invitation_analytics_enabled`, and `model.py` claims `ensure_schema` is called
  by `server.connect_sqlite()` / `_ensure_postgres_schema()` — after this pass it is
  called by the analytics handlers and at boot, once per connection is opened, which is
  what those functions do.
* `docs/postgres_schema.sql` is not read by anything on this host: `server.py` reads
  `ROOT/"postgres_schema.sql"` where `ROOT` is `src/python`, and the file lives in
  `docs/`. That is a pre-existing gap in the PostgreSQL path, unrelated to analytics,
  found while wiring this and left alone rather than silently "fixed" into a different
  behaviour.

## 2. Goal 2 — the unanimity sweep, expanded until it had something to act on

### 2.1 What blocked it

The rule is that no `!important` is demoted on a single run. The prior pass added
`--lift-runs=N` and ran it, and the result was *nothing to act on* — and one declaration
short of nothing: the single candidate it found was load-bearing on `public.html`.

The blocker was not the candidate set. It was coverage. A rule whose selector list mixes
`:hover` with another state — `.final-timeline-row:hover, .final-timeline-row.active` —
was written off as *unmeasured* by construction, because the instrument only ever forced
`:hover`:

| | before | after |
| --- | --- | --- |
| row-instances reported "the rule also targets a non-`:hover` selector" | 19 | 0 |
| declarations those instances belong to | 7 | 0 |
| declarations measured on a non-`:hover` state path, index.html | 0 | 5 |
| declarations reachable only through `:hover`, index.html | 70 candidates | 68 candidates |

### 2.2 The instrument change

`tools/important-lift-test.mjs` now forces the rule's other state parts as well:

* a **class** the selector names is added to every element the part matches
  (`.final-timeline-row.active` → add `active`), then removed;
* a **pseudo-class** it names is forced with CDP `CSS.forcePseudoState`
  (`:focus-visible`, `:focus`, `:active`, `:checked`, `:target`), the same mechanism the
  hover audit already uses for `:hover`;
* the leave-one-out then measures **both** paths, and a declaration is load-bearing if
  *either* path changes a computed value;
* a state part the harness cannot synthesize leaves its declaration unmeasured, and the
  reason is carried out with the row instead of being reported as a bare "no evidence".

The self-check still passes, and the per-rule invariant (the declarations' longhand
expansion must equal the rule's important longhands) reported 0 mismatches over the
whole sweep, so the new enumeration is not mis-grouping anything:

```
$ cat tools/evidence/important-lift-state-expansion.txt
IMPORTANT-LIFT — expanded sweep, N=3, all 16 pages (Goal 2)

$ ARTIFACTS_DIR=artifacts/goal2 python3 tools/hover-verify.py --all --lift --lift-runs=3 --jobs=4
HOVER_VERIFY_TOTAL {"pages": 16, "hoverSelectors": 2107, "elementsTested": 813, "visibleChange": 679, "noVisibleChange": 134, "liftPages": 16, "liftCandidateDeclarations": 424, "liftCandidateLonghands": 1536, "liftRedundant": 40, "liftLoadBearing": 78, "liftUnmeasured": 266, "liftGroupingMismatches": 0, "liftRestoreFailures": 0}

$ ARTIFACTS_DIR=artifacts/goal2 python3 tools/hover-verify.py --cross-page
LIFT_CROSS_PAGE {"pages": 16, "runsPerPage": {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}, "minRunsPerPage": 3, "declarations": 60, "demotable": 1, "keep": 31, "noEvidence": 28, "unstable": 0}
pages: account, admin, analytics, billing, checkin, dashboard, designer, guests, index, materials, privacy, public, reset, responses, templates, verify
runs per page: {"account": 3, "admin": 3, "analytics": 3, "billing": 3, "checkin": 3, "dashboard": 3, "designer": 3, "guests": 3, "index": 3, "materials": 3, "privacy": 3, "public": 3, "reset": 3, "responses": 3, "templates": 3, "verify": 3}
  [demotable / keep / noEvidence / unstable sections: see the report table]

$ tail -3 of the sweep (per-page totals)
checkin      hoverSelectors=64    triggers=45    noMatch=38   tested=22    change=18    noChange=4
templates    hoverSelectors=147   triggers=95    noMatch=81   tested=47    change=40    noChange=7
designer     hoverSelectors=147   triggers=95    noMatch=84   tested=34    change=32    noChange=2
```

### 2.3 The sweep

`python3 tools/hover-verify.py --all --lift --lift-runs=3 --jobs=4`: 16 pages × 3 runs =
**48 lift runs**, plus 16 hover audits. Totals:

| metric | value |
| --- | --- |
| pages / runs per page | 16 / 3 (minimum 3 — unanimity established) |
| candidate declarations across the sweep | 424 |
| inert-here (per page) / load-bearing-here / unmeasured-here | 40 / 78 / 266 |
| distinct declarations after cross-page merge | 60 |
| **demotable** | **1** |
| keep | 31 |
| no evidence | 28 |
| **unstable** (runs of one page disagreed) | **0** |
| grouping mismatches / restore failures | 0 / 0 |

Two things are worth saying plainly. First, the **reproducibility defect the prior pass
documented did not reproduce**: with three runs per page and the state paths forced,
zero declarations came back `unstable`. The prior pass's finding — that a single lift
reading is not reproducible — is what `--lift-runs=3` exists to catch, and this sweep
gives no instance of it. That is evidence about this sweep, not a refutation of the
earlier observation; the earlier run is kept in
`tools/evidence/important-11th-demotion-retraction.txt`.

Second, the 28 "no evidence" declarations are not a tooling failure. They are rules
whose elements do not exist on any page this harness can load, and §2.6 measures why.

### 2.4 The demotion, and the two checks that carried it

The unanimous candidate:

```
$ sed -n '5,7p' tools/evidence/important-demotion-timeline-row.txt
--- DEMOTABLE (inert in EVERY run of every page that measured it) ---
  background             longhands=9  inert on index  unmeasured on 12
      .final-timeline-row:hover, .final-timeline-row.active
```

The edit is one `!important` removed from one declaration, in
`src/css/final-experience.css`:

```
$ sed -n '10,17p' tools/evidence/important-demotion-timeline-row.txt
2. The CSS change — one !important removed, nothing else:
   $ git diff --stat -- src/css/final-experience.css
 src/css/final-experience.css | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
   $ git show HEAD:src/css/final-experience.css | grep -o 'final-timeline-row:hover[^}]*}'
final-timeline-row:hover,.final-timeline-row.active{background:color-mix(in srgb,var(--final-accent) 10%,transparent)!important}
   $ grep -o 'final-timeline-row:hover[^}]*}' src/css/final-experience.css
final-timeline-row:hover,.final-timeline-row.active{background:color-mix(in srgb,var(--final-accent) 10%,transparent)}
```

and the rebuild left the generated bundles in step (`BUILD_OK` twice, mirror check
passed). Two *independent* checks then decided whether it stays:

**Check A — the states the hover audit cannot see.** `tools/state-style-diff.mjs`
snapshots the complete computed style of every `.final-timeline-row` in `plain`,
`active` and `hover`, and compares two snapshots by property name:

```
$ sed -n '23,25p' tools/evidence/important-demotion-timeline-row.txt
4. Independent check A — complete computed style in the plain / active / hover states,
   4 elements x 3 states, before vs after the edit (tools/state-style-diff.mjs):
STATE_STYLE_DIFF {"before":{"url":"http://127.0.0.1:8124/index.html","selector":".final-timeline-row","states":["plain","active","hover"],"elements":4},"after":{"url":"http://127.0.0.1:8124/index.html","selector":".final-timeline-row","states":["plain","active","hover"],"elements":4},"elementsCompared":4,"differences":0,"identical":true}
```

**Check B — the row-level hover diff the prior pass used.** 16 pages, 813 elements,
before vs after:

```
$ sed -n '27,31p' tools/evidence/important-demotion-timeline-row.txt
5. Independent check B — row-level hover diff, 16 pages (tools/hover-regression-diff.py):
HOVER_REGRESSION_TOTALS {"pagesCompared": 16, "pagesMissing": 0, "elementsCompared": 813, "elementsIdentical": 813, "elementsDiffering": 0, "pagesShapeMismatch": 0, "clsDrift": 0}
  index       before=271  after=271  changes 226->226  rows 271 identical 271 differing 0  ok
  dashboard   before=68   after=68   changes 54->54   rows 68 identical 68 differing 0  ok
   (the remaining 13 per-page lines are all 'differing 0  ok')
```

**Why it is safe, not merely inert.** The lift probe *removes* a declaration; a demotion
only drops its priority, and those are different experiments. `tools/css-cascade-winner.mjs`
asks the browser's own matched-style list who wins `background` on those elements:

```
$ sed -n '/^7\. Why the demotion is safe/,$p' tools/evidence/important-demotion-timeline-row.txt
7. Why the demotion is safe, from the browser's own cascade (tools/css-cascade-winner.mjs):
CASCADE_WINNER {"url":"http://127.0.0.1:8124/index.html","selector":".final-timeline-row","property":"background","elements":4,"index":0,"states":["plain","active","hover"]}
  state=plain         computed background="rgb(255, 255, 255) none repeat scroll 0% 0% / auto padding-box border-box"
    order= 7           background         #fff                                                 button
    order=15 IMPORTANT background         transparent!important                                .final-timeline-row
    order=17 IMPORTANT background         var(--app-surface)!important                         body.studio-experience .final-timeline-row
    last-important -> body.studio-experience .final-timeline-row  background:var(--app-surface)!important
  state=active        computed background="rgb(255, 255, 255) none repeat scroll 0% 0% / auto padding-box border-box"
    order= 7           background         #fff                                                 button
    order=15 IMPORTANT background         transparent!important                                .final-timeline-row
    order=17           background         color-mix(in srgb,var(--final-accent) 10%,transparen .final-timeline-row:hover, .final-timeline-row.active
    order=18 IMPORTANT background         var(--app-surface)!important                         body.studio-experience .final-timeline-row
    last-important -> body.studio-experience .final-timeline-row  background:var(--app-surface)!important
  state=hover         computed background="rgb(255, 255, 255) none repeat scroll 0% 0% / auto padding-box border-box"
    order= 7           background         #fff                                                 button
    order=15 IMPORTANT background         transparent!important                                .final-timeline-row
    order=17           background         #fbf7f8                                              button:hover
    order=19           background         color-mix(in srgb,var(--final-accent) 10%,transparen .final-timeline-row:hover, .final-timeline-row.active
    order=20 IMPORTANT background         var(--app-surface)!important                         body.studio-experience .final-timeline-row
    last-important -> body.studio-experience .final-timeline-row  background:var(--app-surface)!important
```

`body.studio-experience .final-timeline-row { background: var(--app-surface) !important }`
wins in every state, so the demoted declaration was never the winner and cannot become
one by losing its priority. This is the difference between a safe demotion and a lucky
one, and it is why the demotion is *verified* rather than *hoped*.

### 2.5 A defect in the new comparison tool, found by using it

The first version of `state-style-diff.mjs --compare` diffed computed properties **by
position**. Chrome enumerates registered custom properties in an order that is not stable
between two loads of the same page, so it reported **32 "differences"** on a change that
moved no value — every one of them the same values in a different order. The comparison
is now by property name, and the same pair of snapshots reports 0. Retained here because
the wrong number was produced by an instrument written in this pass, and a reader is
entitled to know which of its outputs to trust: everything quoted above is from the fixed
version.

### 2.6 What is still out of reach, measured

28 declarations have no evidence. The mechanism is not "the selector is hard": those
components only mount when the page has content, and in this harness the pages have
none. A reachability probe (throwaway, in `/tmp`, output folded into §2.3's table)
measured it on seven pages:

| page | elements | API calls the page made | reachable triggers of the 28 |
| --- | --- | --- | --- |
| index.html | 3934 | 0 | `.final-timeline-row` (4), `.workflow-page-dock-track .v22-workflow-insert` (1) |
| designer.html | 142 | 0 | none |
| templates.html | 292 | 0 | none |
| guests.html | 227 | 0 | none |
| materials.html | 263 | 0 | none |
| dashboard.html | 325 | 0 | none |
| public.html | 259 | 0 | none |

`tools/serve-gzip.py` serves static assets and does not proxy `/api`, so a page that
builds its UI from an API response renders an empty shell: 142–325 elements against
index's 3934. The unreachable rules (`.layer-row`, `.ei-rich-toolbar`, `.template-card`,
`.guest-row`, `.material-card-page`, `.fp-*`, most `.workflow-*`) live in components
those shells would mount with data. Closing this needs an authenticated fixture page, not
a better selector walker; that is the next step for this instrument, and it is named
rather than implied.

### 2.7 The ten earlier demotions stand

Nothing in this pass touched them. They were verified by the row-level check in the
prior pass (813/813 identical, twice), and Check B above re-measured the same 813 rows
against this pass's tree: identical again. The retraction of the eleventh
(`tools/evidence/important-11th-demotion-retraction.txt`) is unchanged history.

## 3. Goal 3 — the Style & Layout residual: measured, attributed, not closed

### 3.1 The measurement

Five fresh traces of `index.html`, captured with the same instrument as the Canva column
(`tools/canva-probe.mjs`) and read by `tools/perf-trace-compare.py`, which reports
**unions** on the busiest thread rather than sums, because recalc events nest:

```
$ sed -n '/^metric /,/^Layouts nested/p' tools/evidence/style-layout-goal3.txt
metric                                                canva              run1              run2              run3              run4              run5
trace events                                         189695            128442            139447            132561            133375            138263
style+layout union ms (main thread)                  805.22           2039.29           2137.55           2152.56           2099.97           2151.75
  style recalc union ms                              525.12           1056.97           1134.54           1142.23           1175.03           1175.14
  layout union ms                                     280.1            982.41           1003.09           1010.42            925.04            976.68
  style recalc union ms (all threads)                525.12           1056.97           1134.54           1142.23           1175.03           1175.14
  layout union ms (all threads)                       280.1            982.41           1003.09           1010.42            925.04            976.68
Script union ms (main thread)                       2604.65            2737.7           2971.32            2792.0           2785.64            2771.6
UpdateLayoutTree events                                 379               152               166               155               162               163
Layout events                                            37               107               114               110               111               109
RunTask events                                        29315             17102             17978             18362             18295             17740
Layouts nested in script (forced proxy)                   6                80                85                79                80                80
```

Median of the five runs, against the Canva column already in `tools/evidence/trace-compare.txt`:

```
$ sed -n '/^median /,/2\.65x/p' tools/evidence/style-layout-goal3.txt
median style+layout union, 5 runs: 2137.55 ms   (min 2039.29, max 2152.56, spread 113.27 ms)
median style recalc union:          1142.23 ms   (5 runs: [1056.97, 1134.54, 1142.23, 1175.03, 1175.14])
median layout union:               982.41 ms   (5 runs: [982.41, 1003.09, 1010.42, 925.04, 976.68])
median / canva 805.22 =            2.65x
```

The gap is real and reproducible: 2137.55 ms against 805.22 ms, **2.65×**, with a spread
of 113 ms across five runs. Two shape differences sit inside that number:

* this project lays out **110** times (median) to Canva's **37**, and **80 of those 110**
  are nested inside a script event against Canva's 6 — the forced-layout proxy the
  analyzer documents and labels as a proxy (the trace carries no `args.stackTrace` on any
  Layout event, in either column);
* this project recalculates style **162** times for 1142 ms where Canva recalculates
  **379** times for 525 ms. Canva recalcs *more often* and pays **1.4 ms** each; this
  project pays **7.1 ms** each.

The Lighthouse bucket for the same page — a different instrument, the one the ≤ 1167 ms
target was set against — was 1472 ms median at the start of this pass
(`tools/evidence/style-layout-before-after.txt`), i.e. 305 ms short of a target that was
itself defined as −30 % from a 1667 ms baseline. Nothing this pass did moved it; §3.3
says why.

### 3.2 The attribution

Who causes the recalcs (`tools/style-recalc-attribution.mjs --from-trace=…` on run 3 —
the same parser, re-run on a saved trace):

```
$ sed -n '/^Who causes the recalculations/,/per-recalc duration/p' tools/evidence/style-layout-goal3.txt
Who causes the recalculations (run3 trace, tools/style-recalc-attribution.mjs):
URL http://127.0.0.1:8124/index.html   main renderer tid=612895   wait=2000ms
main-thread wall clock in trace: 7798 ms
Recalculate Style total:         1119 ms over 131 events  (14.4% of main-thread wall clock)

--- by enclosing TASK (outermost) ---
     1119 ms    131 events  RunTask

--- by nearest non-style cause ---
      591 ms     84 events  FunctionCall
      333 ms     30 events  RunTask
      141 ms      9 events  v8.run
       54 ms      7 events  v8.callFunction
        0 ms      1 events  ParseHTML

--- by innermost JS frame (the actionable one) ---
      369 ms  n=  34 max=  93ms avgEl= 213  (no JS frame)
      141 ms  n=   9 max=  51ms avgEl= 351  EvaluateScript@/bundle-index-v15.js:1
      129 ms  n=  12 max=  24ms avgEl= 271  FunctionCall@/bundle-index-v15.js:9665
      102 ms  n=   9 max=  22ms avgEl= 194  FunctionCall@/bundle-index-v15.js:646
       52 ms  n=   2 max=  43ms avgEl= 294  FunctionCall@/page-experience-v22.js:859 secondary
       50 ms  n=   4 max=  18ms avgEl= 299  FunctionCall@/bundle-index-v15.js:11605
       49 ms  n=  37 max=  19ms avgEl=  24  FunctionCall@/bundle-index-v15.js:2207 initializeV19Typography
       37 ms  n=   2 max=  25ms avgEl= 253  FunctionCall@/bundle-index-v15.js:7490
       25 ms  n=   1 max=  25ms avgEl= 586  FunctionCall@/bundle-index-v15.js:11477 install
       24 ms  n=   1 max=  24ms avgEl= 292  FunctionCall@/rich-text-editing-v21.js:41 snapSelection
       19 ms  n=   1 max=  19ms avgEl= 329  FunctionCall@/interaction-scheduler-v22.js:9 flushIdle

Prior pass's forced-layout attribution (tools/evidence/forced-layout-attribution-index-after.txt):
FORCED_LAYOUT_ATTRIBUTION {"label":"index-after","url":"http://127.0.0.1:8124/index.html","distinctCallSites":1017,"dirty":false,"writes":5458,"reads":1986,"forced":155,"forcedDetached":150,"wrapErrors":0}
  top 8 call sites by forced reads:
     57 forced      95 reads       0 writes  text (http://127.0.0.1:8124/bundle-index-v15.js:5532:37)

Element counts: index.html 3934 elements; Canva's worst layout in the Canva column reports totalObjects=1465/1611.
```

and the worst individual layout passes on run 1 (`tools/perf-trace-compare.py`):

```
$ sed -n '/^Worst layout events/,+11p' tools/evidence/style-layout-goal3.txt
Worst layout events, run1:
--- run1: longest 10 Layout events (ms) ---
     387.86  dirtyObjects=731 totalObjects=731
     183.49  dirtyObjects=393 totalObjects=473
     111.55  dirtyObjects=970 totalObjects=1611
      67.53  dirtyObjects=217 totalObjects=621
      57.16  dirtyObjects=324 totalObjects=361
      37.35  dirtyObjects=103 totalObjects=816
      27.03  dirtyObjects=210 totalObjects=808
      26.80  dirtyObjects=24 totalObjects=482
      15.54  dirtyObjects=558 totalObjects=621
       9.96  dirtyObjects=842 totalObjects=842
```

The attribution says this is **not one hot path**:

* 1119 ms of Recalculate Style over 131 events is driven by the page's own mount-time
  JavaScript — 591 ms inside `FunctionCall`, 333 ms in a top-level `RunTask`, 141 ms in
  `v8.run` — spread across 14 innermost frames whose largest single entry is 369 ms over
  34 events with **no JS frame at all**. There is no loop to point at.
* The worst layout is a single **387.86 ms full-document pass over 731 objects** (0.53 ms
  per object), then 183.49 ms over 393. The comparable Canva pass is 228.46 ms over 1465
  objects (**0.16 ms** per object).

**The prior pass's hypothesis is refuted as the dominant cause.** It suspected the
layers-panel `ResizeObserver` re-arming. The forced-layout attribution measured on this
tree (`tools/evidence/forced-layout-attribution-index-after.txt`) attributes 155 forced
reads, of which **150 are on detached elements** — a read on a detached node cannot force
layout — and the recalc attribution above attributes no measurable time to a
`ResizeObserver` cause. The cost is spread over the page's mount-time script and two
full-document layouts.

### 3.3 The decision

**No fix, and no claim of one.** The cause is not a single addressable site: the style
side is 131 small recalcs driven by many different frames, and the layout side is two
full-document passes whose per-object cost is 3.3× Canva's. The per-object difference is
**UNVERIFIED in cause** — the instrument says *how much* per object, not *why* — and the
one structural explanation the numbers support (a 3934-element DOM rendered by the
browser's layout engine, against a canvas-rendered page that mostly paints) is
architectural, not a fix a CSS edit can make. Acting on a guess here is exactly how the
retracted experiments in the prior report happened, so the honest move is to leave it
measured and name the next bottleneck:

1. the 387.86 ms full-document relayout at 0.53 ms/object — the largest single event, and
   the one a canvas renderer does not pay;
2. the 80 script-nested layouts: each is a DOM mutation that invalidates layout, and a
   batching/`content-visibility` study on the editor's mount path is the concrete next
   experiment. It was not attempted here because verifying it needs a before/after on the
   whole editor (5 traces plus the hover diff plus the suite), and the pass's budget went
   to Goals 1, 2 and 4.

### 3.4 A composition fix the diagnosis needed

`tools/style-recalc-attribution.mjs --from-trace=` accepted only a bare event array,
while `tools/canva-probe.mjs` writes `{traceEvents: [...]}` — so the attribution could not
be run on the very traces the Canva comparison is made from. Both shapes are accepted now
(`078e2a0`).

## 4. Goal 4 — the Playwright step-0b check

### 4.1 Why it could not pass

The brief required `node -e "require('playwright').chromium.launch()"` to pass. Two
reasons it did not:

* the application does not depend on Playwright, so `require('playwright')` throws
  `MODULE_NOT_FOUND` from the repository root;
* the Playwright reachable from inside `.venv` had no browser binary downloaded
  (`Executable doesn't exist at …/chrome-headless-shell`).

Installing it at the repository root would edit the application's `package.json`, which
this pass is forbidden to touch.

### 4.2 What was done instead

An isolated tool install under `tools/playwright-check/`: its own private
`package.json`, its own `package-lock.json`, its own gitignored `node_modules`, and the
browser downloaded to `~/.cache/ms-playwright` — outside the repository. The brief's
expression runs unchanged from that directory, and `launch-check.mjs` additionally loads
a served page and reads its title back, because a browser that launches but cannot render
proves little. It uses Playwright's own Chromium (156.0.8078.4) rather than
`/usr/bin/google-chrome`, so a pass means what was asked for rather than the system
browser answering under a different name.

```
$ cat tools/evidence/playwright-launch-check.txt
PLAYWRIGHT STEP-0B CHECK — resolved without touching the application's package.json

$ cd <repo root> && node -e "require('playwright').chromium.launch()"
node:internal/modules/cjs/loader:1433
  throw err;
  ^

$ node tools/playwright-check/launch-check.mjs
PLAYWRIGHT_LAUNCH_OK version=156.0.8078.4
  url=http://127.0.0.1:8124/index.html  title="E-invitation-website"

$ cd tools/playwright-check && node -e "require('playwright').chromium.launch().then(b=>b.close())"
exit=0 (no output = launched and closed)

installed: 1.64.0
browser:   /home/ngethsereyboth/.cache/ms-playwright/chromium_headless_shell-1248
```

The application's `package.json` and `package-lock.json` are untouched by this pass and
remain exactly as the concurrent session left them (§7).

## 5. Goal 5 — the extended Canva analysis: not attempted

No new Canva surface was analyzed this pass. The reason is budget: Goals 1–4 consumed it
(the sweep alone is 48 browser runs, the traces 5 more), and the brief marks this goal
"if time permits". It is not a gap in what is known — the prior pass analyzed
`https://www.canva.com/` and `https://www.canva.com/templates/` and its comparison table
is in `docs/reviews/canva-analysis-and-closure-report.md` §1.6–§1.10 — and the surfaces it
left unanalyzed are named there: the *editor*, behind a login this pass and the last one
declined to attempt. What a next pass would do: the public template *detail* pages
(`/templates/<category>/`), which mount more of the editor's UI without an account, using
`tools/canva-probe.mjs` and `tools/module-loading-strategy.mjs`.

## 6. Verification battery

Run after the last edit to any tracked file (`078e2a0`).

1. **Build + mirror.** exit 0, `BUILD_OK`, `MIRROR_CHECK_PASSED`, no pipe into `grep`:

```
$ python3 build.py all --check 2>&1 | tail -2
MIRROR_CHECK_PASSED (up_to_date=314)
BUILD_OK editor bundles manifests mirror (check)
```

2. **Mirror by content.** 0 drifted, 0 orphans, 0 unmigrated:

```
$ python3 tools/mirror-diff.py 2>&1 | tail -2
MIRROR_DIFF {"sources": 314, "drifted": 0, "unmigrated": 0, "orphans": 0, "orphansExempt": 19, "generatedExempt": 34}
MIRROR_DIFF_SUMMARY 0 drifted, 0 unmigrated, 0 orphans (19 named and exempt)
```

3. **The full suite.** 68 passed (§1.4), re-run on the final tree after the demotion.
   Before this pass: 15 failed / 53 passed.
4. **`pytest -k analytics`.** 20 passed (§1.4), from 15 failed / 5 passed.
5. **`pytest -k v52_crdt`.** 6 passed — the fixture the prior pass repaired still holds:

<!-- report-verify: measurement needs .venv; the numbers are also in tools/evidence/pytest-full-after-goal1.txt -->

```
$ .venv/bin/python -m pytest tests/ -k v52_crdt -q
......                                                                   [100%]
6 passed, 62 deselected in 8.06s
```

6. **This report re-verified by its own gate.** 0 mismatched, 0 elided, and every block
   either re-run or declared with a reason:

<!-- report-verify: measurement re-runs a report-verify pass over the report itself -->

```
$ node tools/report-verify.mjs docs/reviews/analytics-and-unanimity-report.md
  blocks checked 24 \u2014 match 19, MISMATCH 0, ELIDED 0

  declared, not compared  historical 2, write 0, measurement 3, heavy 0
  still skipped 0   (pass --with-server to verify the server-dependent ones)
```
7. **Bundle budgets.** index ≤ 1 420 000, public ≤ 260 000:

```
$ wc -c src/js/bundle-index-v15.js src/js/bundle-public-v15.js
1136115 src/js/bundle-index-v15.js
 251960 src/js/bundle-public-v15.js
1388075 total
```

8. **`!important` counts.** One `!important` was removed and none added. The audit proves
   the change is exactly that removal — every affected file is byte-identical to its
   predecessor with `!important` stripped:

```
$ python3 tools/important-removal-audit.py --rev=fbd17d2 2>&1 | tail -4
  ok   src/python/build/page-assets-v15.json                    13 size/digest/source-name field(s) moved; pages.account.html.bytes 356415 -> 356405 (-10)
  ok   src/python/route-bundles-v15.json                        26 size/digest/source-name field(s) moved; pages.account.html.styleBytes 256569 -> 256559 (-10)

important-removal-audit: vs fbd17d2 — 32 changed CSS/JSON entry(s) (28 modified, 0 renamed, 4 manifest(s)); 4 change(s) named and not judged (JS, or JSON this pass does not generate); failures=0
```

9. **Versioned files.** 64 versioned CSS files, 94 versioned JS files (bundles excluded):

```
$ find src/css -name '*-v*.css' | wc -l; find src/js -name '*-v*.js' -not -name 'bundle-*' | wc -l
64
94
```

10. **Style & Layout trace on index.html.** Median across 5 runs: 2137.55 ms of
    style+layout union against Canva's 805.22 ms, i.e. **2.65×**, against a 1167 ms
    *Lighthouse-bucket* target that is a different instrument (§3.1). Not met, not
    claimed.
11. **Working tree.** Every file this pass changed is committed; what remains is what was
    already there:

<!-- report-verify: historical untracked files change as this report and the concurrent session's work land -->

```
$ git status --short
 M package-lock.json
 M package.json
?? docs/STRUCTURE-PILOT-AUDIT.md
?? docs/reviews/analytics-and-unanimity-report.md
?? docs/reviews/deploy-02-linux.md
?? scripts/audit_bidi.js
?? scripts/fix_structure_references.py
?? src/python/admin-page-v13.css
?? tests/ac4_2d_audit_test.py
```

## 7. Autonomous decisions, and why

The directive was to decide, document and proceed. The decisions that a reader would
otherwise have to reverse-engineer:

1. **Wire the feature rather than retire the tests.** The feature is complete and
   importable; the gap is routing. Retiring 15 working tests to make a suite green would
   have destroyed the only specification of the ingestion contract.
2. **Leave `test_phase6`'s unreachable branch alone and prove it separately.** Editing the
   test to use PUT would make the suite look stronger while changing what it asserts;
   `tools/analytics-live-flag-probe.py` proves the branch without touching it.
3. **Demote, do not delete, the one unanimous candidate.** A demotion is reversible by
   adding the priority back and is what the rule permits; deleting the declaration would
   discard a rule that exists for a reason, and the sweep only measured its priority.
4. **Make the lift probe measure the second state path instead of excluding it.** The
   alternative — keeping those declarations out of the demotable set forever — would have
   been safe and permanently uninformative.
5. **Declare the Style & Layout cause UNVERIFIED rather than pick a suspect.** The
   instruments attribute cost to no single site; the architectural explanation is
   supported by the numbers but not isolated by an experiment, so it is labelled.
6. **Install Playwright under `tools/` rather than retire the step-0b requirement.** The
   brief offered either; the requirement is a real capability check and it now passes.
7. **Leave `package.json`, `package-lock.json` and the six untracked files alone.** They
   are the concurrent session's, and the brief says so.

## 8. Limitations, stated rather than implied

* **PostgreSQL analytics is unverified.** No server on this host; the dialect statements
  are verified as text only (§1.6).
* **28 `!important` declarations have no evidence** because the pages that mount their
  components need a backend the static harness does not provide (§2.6).
* **The style+layout comparison is between unlike pages.** Canva's column is its public
  marketing page, not its editor, so "2.65×" is a comparison of this project's editor
  page against Canva's public page — the same asymmetry the prior pass recorded, kept
  exact rather than softened.
* **The per-object layout cost difference (0.53 ms vs 0.16 ms) has a measured size and an
  unmeasured cause** (§3.3).
* **The PostgreSQL schema file is not reachable from the server's ROOT** — pre-existing,
  found while wiring analytics, left as found (§1.7).
* **The 5-minute reconstruction loop runs in the server process.** It is verified by
  calling its entry point (`RECONSTRUCTION_ENTRYPOINT_OK`, §1.3 evidence) and by the
  thread starting at boot; a 300-second wall-clock observation of the thread was not
  spent.

## 9. Retained corrections

* **The positional diff in `state-style-diff.mjs`** — 32 phantom differences, fixed to
  compare by property name (§2.5).
* **`--from-trace` could not read `canva-probe.mjs` traces** — both shapes accepted now
  (§3.4).
* **The prior pass's retraction stands unchanged**: the eleventh demotion is still
  retracted, with its reason, in
  `tools/evidence/important-11th-demotion-retraction.txt`. Nothing in this pass re-litigates
  it; the sweep it asked for was run, and this time it had coverage to work with.
