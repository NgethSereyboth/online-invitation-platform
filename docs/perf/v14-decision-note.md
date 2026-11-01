# V14 performance-budget gate — quarantine decision note (FB-11)

Date: 2026-10-22 · Status: NON-BLOCKING, deliberate, owner-approved
Decision register: OD-6 (owner answer 2026-10-22: **keep v14 non-blocking for
now** — do not retire the step, do not change the budget).

## What the gate measures

`tests/v14_performance_budget_test.py` is the repo's layer-2 (build-time)
aspirational route budget: for every route in
`src/python/build/build_page_manifests.py::BUDGETS` it asserts the built page
manifest's script count, stylesheet count, and total byte size stay at or
under the per-route ceiling. For the `editor` route (`index.html`) the
ceiling is `{"scripts": 3, "styles": 1, "bytes": 1_700_000}`.

## Current failure (reproduced 2026-10-22)

```
$ python tests/v14_performance_budget_test.py
AssertionError: ('editor', 'index.html', 'styles', 2, 1)
```

All other routes pass; the script count (3) and byte ceilings are happy. The
gate genuinely executes — it is not an import failure and the truncation is
not involved (see the stale-comment history in
[.github/workflows/lighthouse.yml](../../.github/workflows/lighthouse.yml),
corrected in the layer-2 comment).

## HTML inspection: are the two stylesheets a duplicate?

No. Build a fresh manifest and look inside the served HTML:

```
$ python -c "import sys; sys.path.insert(0,'src/python'); \
  import build_page_manifests as m; print(m.build()['pages']['index.html']['styles'])"
['bundle-index.css', 'design-fix.css']
```

- `bundle-index.css` (448,636 B) — the route bundle the route-bundle build
  produces for index.html; contains all 30 appended route styles per
  [docs/route-bundle-sources.json](../route-bundle-sources.json).
- `design-fix.css` (1,632 B) — the 2026-10-19 DESIGN-FIX polish layer
  (DESIGN-FIX-TASK P4): calmer canvas dot-grid, grouped toolbar, poster-size
  picker and designer recovery cards. Documented in
  [DESIGN-FIX-REPORT.md](../HISTORY.md) §5 as "loaded by
  index.html".

The two files share **zero content** (different owner, different scope, and
index.html is the only page that loads design-fix.css: `grep -rn design-fix
src/html/*.html` → exactly one hit). Merging design-fix.css into the bundle
would remove the second `<link>` but only by regenerating the bundle — a
bundle-content change, not a duplicate removal, and one that changes served
bytes (1.6 kB) against the budget file. That is a payload decision under
OD-6, so it is **not done here**. The duplicate-check always passes:
`len(styles)==len(set(styles))`.

## Statement of record

- `styles: 1` is **aspirational and currently unsatisfiable** — the gate is
  red by construction, not by regression, and has been since design-fix.css
  landed (2026-10-19).
- Owner answer 2026-10-22 (OD-6 response): **keep non-blocking**. The gate
  runs everywhere (`tools/run-gates.py` does NOT include it as a blocking
  phase; CI's `[.github/workflows/lighthouse.yml]` layer-2 step and
  `[.github/workflows/tests.yml]` v14 step both carry
  `continue-on-error: true` + an explicit NON-BLOCKING/known-red label;
  both log its output).
- Nothing here weakens any test, assertion, budget, or threshold (OD-6:
  never propose a change).

## What would remove `continue-on-error` later

1. An explicit owner decision (new OD register entry) either
   re-baselining `editor.styles: 1 → 2` in the BUDGETS map or approving a
   single-file scan-in of the DESIGN-FIX layer; then
2. `tests/v14_performance_budget_test.py` re-run green everywhere it is
   wired (CI layer 2, tests.yml v14 step) — **with the output archived**;
   then
3. Remove `continue-on-error: true` + the NON-BLOCKING labels from both
   workflows in the same commit, so the gate flips to blocking atomically.

## References

- Budget file (single source of truth):
  [docs/perf/lighthouse-budgets.json](lighthouse-budgets.json) — layers 1/3.
- Optimisation report context:
  [docs/reviews/optimisation-report.md](../HISTORY.md)
  (aspirational ceilings rationale, §"three-layer budget").
