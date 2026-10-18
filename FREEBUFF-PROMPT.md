# Freebuff prompt — canvas motion fixes + UI visual audit fixes (one work order)

Copy everything below the line into the Freebuff agent. It assumes you are started in
`F:\Project\eInvite\online-invitation-platform` (Windows, PowerShell, python3 + node available).

---

You are fixing the eInvite website (repo root: `F:\Project\eInvite\online-invitation-platform`). Two work orders are in this repo root and BOTH are yours, in this order of priority:

1. `CANVAS-MOTION-FIX-TASK.md` — the canvas motion defects (tasks 1–5). Its gates/thresholds/baselines are frozen: you must make them pass, never weaken, skip, or re-baseline them.
2. `UI-VISUAL-AUDIT-FIX-TASK.md` — a full real-render visual audit (P0/P1/P2/P3 findings with screenshot evidence). Fix every P0 and P1, then P2 items unless an owner decision says otherwise. The "Definition of done" checklist at the end of that file is your acceptance list.

Read both files completely before touching anything. Then read `artifacts/ui-audit/digest.txt` and the raw evidence under `artifacts/ui-audit/capture/` (150+ screenshots + `heuristics.jsonl`). Evidence beats memory: every finding in the audit names a screenshot path and a selector — open the screenshot, reproduce, then fix.

## Environment setup (verify before you start)

```powershell
Set-Location "F:\Project\eInvite\online-invitation-platform"
# Playwright / Chromium (needed by the capture tool and the node tools)
$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE = "$env:LOCALAPPDATA\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
$env:CHROME_PATH = $env:PLAYWRIGHT_CHROMIUM_EXECUTABLE
# App server wrapper ({base} baked into the child env); use it for anything that needs the app:
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- <your command>
# Static server for Lighthouse / DOM tools:
python3 tools/serve-gzip.py --port 8124
```

Hard rules:
- **Never run `git clean -fdx`** — it destroys the visual-baseline snapshot. Do not delete anything under `artifacts/`.
- Do not modify tests, gates, budgets, thresholds, or baselines to make a check pass. If a check is red, fix the cause or report the blocker.
- The app is served from `src/python/` (the tree `tools/serve-gzip.py` and `run-with-server.py` serve). Edit sources in `src/html/`, `src/js/`, `src/css/`, then ensure the served mirror is refreshed (`python3 build.py all` is known to exit 0 without fully refreshing the mirror — verify the served file actually changed; if the mirror is stale, refresh the specific file and say so in your report).
- No source-script edits inside `tests/` unless a test itself is clearly wrong AND the task file allows it; default: don't touch tests.

## Part 1 — canvas motion (CANVAS-MOTION-FIX-TASK.md)

Complete tasks 1–5 exactly as that file specifies (initial framing/`fit()`, batching, zoom, selection toolbar interception, dark-mode checks — see the file for the authoritative list). Verify with the gates that file names (the Playwright acceptance + visual matrix + perf runs). Those gates are currently documented red; your job is to turn them green. Machine must be quiet for perf/visual runs: run them serialized, nothing else running.

## Part 2 — UI findings (UI-VISUAL-AUDIT-FIX-TASK.md)

Work through the findings in this order: **P0-1/P0-2/P0-3 → P1-1…P1-6 → P2-1…P2-4 → P3**. For each finding: reproduce → root-cause in source → fix → re-capture the affected states → keep before/after screenshots under `artifacts/ui-audit/fixes/<issue-id>/` (`before-*.png`, `after-*.png`) → tick the item in a `RESULTS.md` you create in that folder (issue ID → files touched → verification command + result).

Highlights you must not miss (details + evidence in the task file):
- `src/js/gpu-loader.js:1` requests `*-v22.js` files that don't exist (404 + MIME refusal on every editor load; chain abort means none of the 4 GPU scripts load). Fix the names, keep a single friendly `onerror`.
- `src/html/index.html:97` — `#saveState` KM span contains the English string and both render ("Saved locallySaved locally").
- Design page tablet 768/1024: the mobile editor pane host opens as a big empty white panel over the canvas; the selection toolbar floats mid-canvas; toolbars collide and clip (`#v23ContextToolbar`, zoom cluster, "Quick Actions"). Make the 721–1024 responsive contract explicit (desktop editor or closed drawer; an open pane must never be empty).
- Design page desktop 1440: right inspector extends 75px past the viewport (last tab cut, toolbar "Position" clipped under it); two zoom readouts; "MobileTabletDesktop" label collision.
- ≤375px: header language switch overlapped by page content on 13 pages (invisible on admin); design page language card overlapping chips; desktop-hint banner text covered by the bottom bar.
- Horizontal scroll: analytics 375/320, admin 320, privacy 320, templates 320 (digest lists the exact offenders; verify `document.scrollWidth <= innerWidth` afterwards).
- Dark mode invisible text: templates "Built-in" chips 1.03:1; public venue/muted/journey; checkin labels; privacy lang pill; studio status texts.
- `dashboard.html`: intentionally emptied (WIP). DO NOT rebuild it. DO resolve the consequences: (a) silence the dead `dashboard.js` assignments (`$('#authSignInTab')…` null-onclick pageerror), (b) fix `lhci collect` aborting with NO_FCP so `make perf` can run — the cleanest minimal fix is painting a tiny WIP shell on that page; if you choose to exclude it from LHCI instead, mark it clearly in `tools/lighthouserc.js` + budgets and note the owner decision.

## Part 3 — hunt MORE bugs with screenshots (mandatory, every page)

Before fixing: capture a baseline sweep. After fixing: capture again and diff.

```powershell
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/ui-audit-capture.py --out artifacts/ui-audit/fixes/baseline
# narrowed (e.g. one page/combo) — see tools/ui-audit-capture.py --help
python3 ... tools/ui-audit-capture.py --out artifacts/ui-audit/fixes/x --only index.html --states user --themes dark --langs en --viewports 1440x900,375x667
# summarize:
python3 tools/ui-audit-summary.py --section hscroll|overflow|contrast|occlusion|tiny|errors
python3 tools/ui-audit-digest.py --dir artifacts/ui-audit/fixes/baseline --out artifacts/ui-audit/fixes/baseline-digest.txt
```

The sweep covers all 16 pages × {user, guest} × {light, dark} × {en, km} × 5 viewports with a seeded published invitation. Known heuristic caveats are listed in §1 of the UI task file (`.sr-only` rows are false positives; sticky-header overlaps when scrolled are normal; the contrast heuristic misreads gradients/disabled states). **Then go beyond the automatic sweep** — open the screenshots yourself and hunt what a human would call "off", plus scripted interactive states:

- `index.html`: object selected (toolbar + inspector populated), "Flow" panel open, "Position" popover open, mobile "Hide controls" expanded/collapsed, quick inspector at 768/1024, first-run tour dismissed.
- `public.html` (/i/<slug>): cover → hero → schedule → RSVP focused → footer, in dark and km.
- Forms: focus rings, validation errors, empty states (0 guests, no favorites, no materials).
- Every page at 320/375: nothing overlapping, nothing clipped, no horizontal scroll.

Definition of "found and reportable": anything overlapping, clipped at an edge, misaligned within a grid, illegible (contrast/size), duplicated, invisible-but-clickable, unreachable (can't scroll to it), or visually inconsistent with the same component elsewhere in the site. For each new bug: page, state, viewport, screenshot path, selector, computed cause, proposed fix. **Fix what's in scope (P0–P2 style visual defects); if it's a product/owner decision, list it under "Owner decisions" in your report instead of guessing.**

## Verification before you claim anything

1. `make check`, `make test`, `make smoke` — all green (they were green before you started).
2. Canvas gates from `CANVAS-MOTION-FIX-TASK.md` — green (or a precise blocker note; never weakened).
3. Re-run the capture sweep; confirm: no console errors on the 16 pages, no horizontal scroll at 320/375, no occlusion of interactive controls at scroll 0, no clipped text in dark/km.
4. `npx lhci collect --config=tools/lighthouserc.js` completes (needs `tools/serve-gzip.py` on 8124 + `CHROME_PATH`). Accessibility categories may not regress.
5. Every fixed issue has before/after screenshots + a verification command in `artifacts/ui-audit/fixes/RESULTS.md`.

## Report format (final message)

- Done: issue ID → one-line fix summary → files touched → how verified (command + observed result).
- New bugs found beyond the audit (with screenshot paths), fixed or listed.
- Owner decisions needed (with your recommendation).
- Anything you could not verify, and why.
- Commands to reproduce the whole verification from a clean checkout.
