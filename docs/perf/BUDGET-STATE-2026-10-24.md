# Performance budget state (2026-10-27, LT-6.2)

Read-only measurement of the tree that closed Phase 4 (`f05ee2e` plus the uncommitted Phase 4
work). No file, budget, threshold or asset changed for this document.

Sources:

- route weights: `docs/page-assets.json` resolved against `src/python/` exactly as
  `tests/v55_route_weight_budget_test.py` does, ceilings from `docs/perf/lighthouse-budgets.json`
  (uncompressed bytes, KB ceilings);
- Lighthouse: the 16 `LHR` reports from the Phase 4 close run (`.lighthouseci/lhr-*.json`,
  collected 16:35–16:39 local by `tools/run-gates.py --phase all`, gate log
  `artifacts/next-work/gates/20261027-162311/gates.log`);
- editor readiness and viewer LCP: `artifacts/next-work/lt-6-2/measure.py`, three fresh runs
  against a fresh-data app server, raw `artifacts/next-work/lt-6-2/measure.json`.

## 1. Route weight against budget

Uncompressed bytes of every script and stylesheet the route manifest lists; budget numbers are the
same ones the gate enforces (script / style / total KB).

| route | scripts | script KB | style sheets | style KB | total KB | budget (script/style/total) | headroom |
|---|---:|---:|---:|---:|---:|---|---|
| account.html | 3 | 110.3 | 1 | 259.0 | 369.3 | — (unbudgeted) | n/a |
| admin.html | 3 | 151.6 | 1 | 259.9 | 411.5 | 159/263/422 | 10.5 KB |
| analytics.html | 3 | 97.8 | 1 | 259.6 | 357.4 | — (unbudgeted) | n/a |
| billing.html | 3 | 94.0 | 1 | 261.1 | 355.1 | — (unbudgeted) | n/a |
| checkin.html | 3 | 48.5 | 1 | 131.3 | 179.7 | — (unbudgeted) | n/a |
| dashboard.html | 3 | 342.1 | 1 | 309.0 | 651.1 | 349/319/667 | 15.9 KB |
| designer.html | 3 | 89.9 | 1 | 285.2 | 375.1 | — (unbudgeted) | n/a |
| guests.html | 3 | 132.0 | 1 | 259.7 | 391.7 | — (unbudgeted) | n/a |
| index.html | 3 | 1077.4 | 1 | 439.1 | 1516.5 | 1163/494/1656 | 139.5 KB |
| materials.html | 3 | 143.8 | 1 | 278.7 | 422.5 | 144/283/427 | 4.5 KB |
| privacy.html | 1 | 19.1 | 1 | 153.2 | 172.3 | 20/154/174 | 1.7 KB |
| public.html | 2 | 258.6 | 1 | 131.0 | 389.6 | 259/131/390 | 0.4 KB |
| reset.html | 3 | 88.2 | 1 | 257.0 | 345.3 | — (unbudgeted) | n/a |
| responses.html | 3 | 102.7 | 1 | 259.6 | 362.4 | — (unbudgeted) | n/a |
| templates.html | 3 | 115.6 | 1 | 289.2 | 404.9 | — (unbudgeted) | n/a |
| verify.html | 3 | 86.2 | 1 | 256.9 | 343.1 | — (unbudgeted) | n/a |

Six routes carry a budget and all six are inside it. The thin ones are **public.html (0.4 KB)** —
258.6 of its 259 KB script ceiling — **privacy.html (1.7 KB)**, **materials.html (4.5 KB)**,
**admin.html (10.5 KB)** and **dashboard.html (15.9 KB)**. Any addition to the public route has to
be paired with an equal removal, the same constraint LT-4.1 hit (the first cut was 1,673 B over and
was compacted). The other ten routes have no budget entry at all; that is the existing shape of
`lighthouse-budgets.json`, recorded here rather than changed.

## 2. Lighthouse scores, CLS and interaction

Mobile Lighthouse from the Phase 4 close (`minA11y 1.00` across all 16):

| route | perf | LCP | TBT | TTI | CLS |
|---|---:|---:|---:|---:|---:|
| index.html | 73 | 1.3 s | 310 ms | 1.9 s | 0.15 |
| dashboard.html | 99 | 0.7 s | 70 ms | 0.8 s | 0.018 |
| public.html | 99 | 0.7 s | 70 ms | 0.7 s | 0 |
| admin.html | 100 | 0.5 s | 0 ms | 0.5 s | 0.001 |
| account.html | 100 | 0.6 s | 0 ms | 0.6 s | 0.05 |
| billing.html | 100 | 0.5 s | 0 ms | 0.5 s | 0.001 |
| verify.html | 100 | 0.5 s | 0 ms | 0.5 s | 0.001 |
| reset.html | 100 | 0.5 s | 0 ms | 0.5 s | 0.002 |
| privacy.html | 100 | 0.4 s | 0 ms | 0.4 s | 0.001 |
| guests.html | 100 | 0.5 s | 0 ms | 0.5 s | 0.005 |
| responses.html | 100 | 0.5 s | 0 ms | 0.6 s | 0.001 |
| analytics.html | 100 | 0.5 s | 0 ms | 0.5 s | 0.001 |
| materials.html | 100 | 0.5 s | 0 ms | 0.6 s | 0.006 |
| checkin.html | 100 | 0.4 s | 0 ms | 0.4 s | 0.023 |
| templates.html | 77 | 0.8 s | 0 ms | 0.8 s | 0.604 |
| designer.html | 100 | 0.6 s | 0 ms | 0.6 s | 0.003 |

Two outliers, both recorded and neither fixed here:

- **templates.html CLS 0.604** — the gallery's first paint shifts the document, by far the worst
  layout stability on the site. It is the only score that keeps the route at 77 besides its 0.8 s
  LCP.
- **index.html perf 73** — 310 ms TBT and CLS 0.15 from the editor boot; consistent with LT-6.1's
  420 ms worst long task on the same route. Both are inside the gate's tolerances.

Every other route is 99–100 with CLS ≤ 0.05.

## 3. Editor interactive time

Fresh account → create → editor, measured from the editor document's navigation start to the
editor's own `documentElement.dataset.editorReady === 'true'`:

| run | editorReady | DOMContentLoaded | load |
|---|---:|---:|---:|
| 1 | 2,060 ms | 1,007 ms | 1,884 ms |
| 2 | 2,311 ms | — | — |
| 3 | 2,153 ms | — | — |
| **median** | **2,153 ms** | | |

The editor becomes interactive about 1.1 s after `DOMContentLoaded`; that second is the startup
bundle's parse/execute, which is also the 310 ms TBT and the 420 ms long task LT-6.1 measured. No
regression target is set for this number yet — the roadmap's proposed
`tests/performance_editor_boot_test.py` is still `absent`.

## 4. Viewer LCP on the throttled profile

Published invitation (`/i/<slug>`), Slow-4G-like profile (1.6 Mbps down / 750 kbps up / 150 ms RTT)
plus 4× CPU throttling, and the same page unthrottled as a control:

| run | throttled LCP | throttled CLS | unthrottled LCP | unthrottled CLS |
|---|---:|---:|---:|---:|
| 1 | 4,828 ms | 0 | 832 ms | 0 |
| 2 | 4,716 ms | 0 | 828 ms | 0 |
| 3 | 4,656 ms | 0 | 868 ms | 0 |
| **median** | **4,716 ms** | 0 | **832 ms** | 0 |

At 4,716 ms the guest viewer is well outside the 2,500 ms "good" LCP band on a throttled mobile
profile, and its CLS is clean. The page ships one stylesheet plus two scripts (~390 KB uncompressed
on the public route); the throttled gap is transfer-bound, not script-execution-bound. Recorded as
the viewer's known LCP gap — a fix (critical CSS, smaller critical JS, or an image strategy) is a
product decision for a later phase, not part of this read-only item.

## 5. What to watch

1. **public.html budget** — 0.4 KB of script headroom; compact before adding.
2. **templates.html CLS 0.604** — the strongest layout-stability signal on the site.
3. **index.html boot** — 310 ms TBT, 420 ms long task, 2.15 s to editor-ready; half of the route's
   1.9 s TTI is after DCL.
4. **viewer LCP on slow mobile** — 4.7 s median; needs a product-shaped fix, not a budget tweak.
5. Ten routes have no budget entry; if any of them starts growing, the gate will not catch it.

## Reproduce

```
# route weights (uncompressed, budget semantics)
.venv/bin/python artifacts/next-work/lt-6-2/budget-table.py

# editor readiness + viewer LCP (needs the app server: 8161 in this run)
.venv/bin/python artifacts/next-work/lt-6-2/measure.py http://127.0.0.1:8161

# Lighthouse numbers: the last 16 reports in .lighthouseci/ from the gate run
```
