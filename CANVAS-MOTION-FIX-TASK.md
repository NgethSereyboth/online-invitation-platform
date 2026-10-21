# Canvas-motion fix task (handoff work order)

This is the work order for the next agent. The canvas-motion implementation is committed
but **NOT accepted**: independent verification found the defects below. Fix the app
source; do not weaken any test, gate, threshold, or baseline.

- Repo: `F:\Project\eInvite\online-invitation-platform`
- Committed baseline: the commit that added this file (`git log -1`).
- Specification (frozen): `docs/CANVA-SMOOTHNESS-BRIEF.md` — hash pinned in
  `artifacts/canvas-motion/baseline/frozen-brief.sha256`. Never edit the brief.
- Implementation notes: `docs/CANVA-MOTION.md`.
- Full verification evidence and numbers: `artifacts/canvas-motion/ledger.md`, section
  **"Verification (orchestrator) — fresh evidence, 2026-10-17"** — read it first.
- `artifacts/` is git-ignored by repo convention; the evidence stays on disk there and is
  the authoritative record. Do not move or delete it.

## Frozen inputs — never modify

| Path | Role |
|---|---|
| `docs/CANVA-SMOOTHNESS-BRIEF.md` | acceptance spec (frozen hash) |
| `tests/canvas_motion_playwright.py` | acceptance runner (real-input checks) |
| `tools/canvas-motion-perf.mjs` | perf gate (p95 ≤ 20 ms, no task > 100 ms, no gesture frame ≥ 50 ms, commits ≤ 1.2×frames, crop leg must engage) |
| `tools/canvas-motion-visual.py` | visual gate (≤ 3.5 % pixel difference) |
| `artifacts/canvas-motion/baseline/` | captured baselines + pre-change snapshot — read-only |

## Current status (what must change)

- **Status after the 2026-10-19 re-verification (see `artifacts/canvas-motion/ledger.md`, "fresh evidence, 2026-10-19"): ACCEPTED.** The fix set committed as `d9818a6` passes every gate on this machine:
  - Acceptance: **22 pass / 0 fail / 2 skipped** (the 2 skips are by design).
  - Perf (renderer pinned per the ledger procedure): exit 0, zero ≥50 ms frames, zero long tasks, all gestures `engaged:true` (all 3 runs × 4 gestures).
  - The unpinned "hitch" (max ~65-151 ms first-gesture frame) is the environment amplifier already documented in the ledger — the DoD procedure pins the renderer, and fresh evidence reproduces it unpinned and eliminates it pinned.
- 2026-10-20 update: the dark-width visual failure recorded below was resolved by the owner-approved baseline re-anchor (`artifacts/canvas-motion/baseline/REBASELINE-2026-10-20.md`). 6/6 pairs pass at 0.109–0.279 %; the 3.5 % threshold and comparison logic are untouched. The loopback register-rate fix (`af2b723`) lets the frozen visual gate complete in one command (6/6, 0.06–1.26 %).
- Status at the time this work order was written (superseded): 20 pass / 2 fail / 2 skipped; snap-drag ≥50 ms in 3/3; crop never engaged.
- Visual: light passes all 3 widths; **dark fails all 3 widths**
  (5.52 % / 10.67 % / 6.62 % vs the 3.5 % limit).
- pytest baseline: `pytest tests/ -q -s` → **14 F / 127 P**, all 14 failures pre-existing
  (environment/mirror related; identities in the ledger). This count must not grow.
  On this machine the suite must be run **with `-q -s`** (pytest capture breaks
  `subprocess.Popen` here — WinError 6/50 — and turns passing tests into spurious failures).

## Task 1 — exactly one undo entry per drag  (acceptance FAIL)

- Failing check: `drag-30px-one-undo-entry` — a single 30 px drag on a text object pushed
  **+2 undo entries** (depth 1 → 3); the spec requires exactly **one**.
- Verified mechanism: one snapshot is pushed when the gesture crosses the drag threshold
  (~3 px), a second snapshot is pushed on commit.
- Code area: `src/js/app.js` (begin/commit/cancel transaction APIs),
  `src/js/professional-editor.js` (`startInteraction` / `moveInteraction` / `endInteraction`),
  `src/js/direct-manipulation.js` (`beginPointerGesture`).
- Do: exactly one undo entry per completed gesture.
- Verify: the check above passes in `tests/canvas_motion_playwright.py` unchanged.

## Task 2 — Escape abort leaves no undo entry  (acceptance FAIL)

- Failing check: `escape-abort-no-undo-entry` — drag started (threshold crossed), then
  Escape aborted: position unchanged but depth 1 → 2 (+1 residual entry).
- Do: an aborted gesture must leave **zero** entries (cancel the in-flight transaction).
- Same code area as Task 1; likely fixed by the same change.

## Task 3 — initial view framing  (visual gate FAIL; app defect)

- Current build opens at **zoom 0.1 @1366** and per-viewport zoom on small screens
  (0.2109 @375, 0.4467 @768, 0.4277 @1366) vs the baseline's fitted **35 %** view for all
  widths. This changes the entire initial canvas framing; dark mode unmasks it as a large
  pixel difference (light 1.5–2.3 % passes; dark 5.5–10.7 % fails).
- Do: restore baseline-equivalent initial framing (fit-on-open) so the visual gate passes
  **without** any change to the tool, its 3.5 % threshold, or the baseline snapshot.
- Verify: full visual matrix passes (6/6 pairs). Previous before/after PNGs for reference
  live in `F:\Project\eInvite\_canva-verify\visual-matrix\`.

## Task 4 — crop focal-point drag must engage  (perf gate FAIL + real user-visible bug)

- Currently a pointerdown on a crop-active image is consumed by `professional-editor.js`'s
  `#stage`-capture `pointerDown` → `startInteraction` → `stopImmediatePropagation()` before
  `direct-manipulation.js`'s `beginCropDrag` (registered later on the same node) can run.
  Dragging the image in crop mode **never** changes `imagePositionX/Y` or
  `style.objectPosition` — in the baseline build too (pre-existing), which is why the
  perf gate's crop leg cannot measure anything.
- Do: when the target object is crop-active (`.v24-crop-active`), let the crop path win
  (early-return before starting the professional interaction, or route the event so
  `beginCropDrag` runs first). Dragging in crop mode must move the focal point.
- Also fixes a real user-facing bug (drag-to-reposition focal point does nothing today).
- Verify: perf gate crop leg reports `engaged: true` with input-to-paint sampled.
- Note: the crop leg also recorded ≥ 50 ms frames (max 81.3 ms) while the drag was being
  consumed by the interaction path — recheck frames after Tasks 4–5.

## Task 5 — snap-drag drag-start hitch  (perf gate FAIL)

- 3/3 runs show one **≥ 50 ms frame at drag start** (62.4–68.8 ms; long-task family
  ~63–70 ms). The brief's M9 gate allows none.
- Likely the one-time interaction-start cost (overlay ensure / snap-candidate snapshots —
  `startInteraction` precomputes frames for up to 100 sibling objects / guides setup).
  Profile with `?_perfdebug=1` on a 30-object page.
- Do: drag start under 50 ms without weakening the gate.
- Verify: all 3 runs of the perf gate show zero ≥ 50 ms frames for snap-drag.

## How to run the gates

From the repo root (`F:\Project\eInvite\online-invitation-platform`), PowerShell:

```powershell
# 0) environment
$env:CHROME_PATH = "$env:LOCALAPPDATA\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

# 1) acceptance (all phases, ~25 s)
python3 tests\canvas_motion_playwright.py --phase all --output artifacts\canvas-motion\verify\acceptance-next

# 2) perf gate (needs a server; run on a quiet machine, serialized)
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- node tools/canvas-motion-perf.mjs --phase=P1 --output=artifacts/canvas-motion/verify/perf-next

# 3) visual gate (needs a server; creates one editor identity per pair — the register
#    endpoint rate-limits around ~10 identities/burst, so do not run other matrices concurrently)
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 tools/canvas-motion-visual.py --base "{base}" --phase P1 --out artifacts/canvas-motion/verify/visual-next

# 3b) optional diagnostic: full before/after matrix without the 3.5 % assertion
python3 "F:\Project\eInvite\_canva-verify\run-with-server.py" -- python3 "F:\Project\eInvite\_canva-verify\probe-visual-matrix.py" --base "{base}"

# 4) pytest baseline (must stay 14 F / 127 P — note the -s)
pytest tests/ -q -s
```

- `run-with-server.py` lives outside the repo (keep it on this machine); it starts the
  editor server on a temp data dir and substitutes `{base}` with the real origin.
- After source changes, run `python3 build.py all` so the served mirrors/bundles regenerate
  before steps 1–3. Known pre-existing generator wrinkle: `build.py all` exits 0 but does
  not fully refresh `src/python/editor-suite.js` and never writes `src/python/page-assets.json`
  — that is an owner-decision item, do NOT "fix" it as part of this task. If unsure whether
  the served app actually has your code, the acceptance runner's `require_motion` canary
  and the checks themselves will tell you.
- The visual gate reads its "before" content from the pre-change snapshot at
  `artifacts/canvas-motion/baseline/before/` (read-only). Never edit it.
- The gates are frozen; make the app pass them, not the other way round.

## Definition of done

1. `python3 tests\canvas_motion_playwright.py --phase all` → 22 pass / 0 fail / 2 skipped.
2. Perf gate exit 0: wheel, pan, snap-drag, crop all pass (crop engaged; zero ≥ 50 ms
   frames in every run).
3. Visual gate passes all 6 before/after pairs (≤ 3.5 %).
4. `pytest tests/ -q -s` → no new failures (14 F / 127 P baseline).
5. `artifacts/canvas-motion/ledger.md` updated with the new evidence; frozen brief hash
   unchanged.
6. Fixes committed.

## Out of scope (owner-decision items — do not touch)

- Stale `src/python/editor-suite.js` mirror + missing `src/python/page-assets.json`
  (generator output-root bug; pre-existing).
- The two by-design skipped acceptance checks.
- Any refactoring beyond these five tasks.
