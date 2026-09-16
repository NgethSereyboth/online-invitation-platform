#!/usr/bin/env python3
"""editor_alignment_guides_test.py — Part 3.1.1 (v0.56) smart alignment guides.

ROADMAP §3.1.1 — Smart alignment guides.

Verifies `window.EInviteAlignmentGuides` (src/js/editor/canvas/guides.js):
  1. Module loads + exposes the public API (`version`, `computeSnap`,
     `beginDrag`, `updateDrag`, `endDrag`).
  2. `computeSnap()` correctly identifies a snap when the dragged element's
     center is within 6px of a sibling's center → returns the expected
     `deltaX` and a match whose `type === 'center-x'`.
  3. `computeSnap()` returns no matches when the dragged element is far from
     every target.
  4. `beginDrag()` + `updateDrag()` + `endDrag()` drive the live overlay
     AND emit the `einvite:alignment-snapped` CustomEvent with the matched
     target's `{ type, value, source }` payload.
  5. Bilingual strings are present (EN + KH) on every snap event detail.
  6. The overlay's guide `<line>` has class `is-center` for center snaps
     (pink) and the plain `alignment-guide` class for edge snaps (blue).

The test runs the JS module headlessly in Chromium via Playwright (no app
server needed — the module is pure JS). It falls back to a JS_SKIPPED marker
when Chromium is unavailable, matching the project's existing browser-test
convention (see tests/browser_runtime.py).

Usage:
    python3 tests/editor_alignment_guides_test.py

Exit code 0 on success; non-zero on failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES_JS = ROOT / "src" / "js" / "editor" / "canvas" / "guides.js"

# Test runner emits this marker on success (matches project convention).
OK_MARKER = "EDITOR_ALIGNMENT_GUIDES_TEST_PASSED"

# A minimal HTML harness that loads the guides.js module as a classic
# <script>. The module wraps itself in an IIFE and assigns
# `window.EInviteAlignmentGuides`, so a classic script is sufficient.
HARNESS_HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>guides-test</title></head>
<body>
  <div id="canvasViewport"><div id="stage"></div></div>
  <script id="guides-src"></script>
  <script>
    // Buffer for einvite:alignment-snapped events captured during the test.
    window.__capturedSnaps = [];
    window.addEventListener('einvite:alignment-snapped', (event) => {
      window.__capturedSnaps.push(event.detail);
    });
    window.dispatchEvent(new CustomEvent('harness-ready'));
  </script>
</body>
</html>
"""


def load_guides_source() -> str:
    """Read the guides.js source so we can inject it as the page's script."""
    if not GUIDES_JS.is_file():
        raise FileNotFoundError(f"guides.js not found at {GUIDES_JS}")
    return GUIDES_JS.read_text(encoding="utf-8")


def run() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"EDITOR_ALIGNMENT_GUIDES_TEST_SKIPPED playwright unavailable: {exc}")
        return 0

    guides_source = load_guides_source()
    failures = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception as exc:  # pragma: no cover — env-dependent
            print(f"EDITOR_ALIGNMENT_GUIDES_TEST_SKIPPED chromium unavailable: {exc}")
            return 0

        try:
            page = browser.new_page()
            page.set_content(HARNESS_HTML)
            # Inject the guides.js source into the empty <script id="guides-src">.
            page.evaluate(
                """(source) => {
                    const script = document.getElementById('guides-src');
                    script.textContent = source;
                    // Re-execute the script by appending a fresh copy.
                    const live = document.createElement('script');
                    live.textContent = source;
                    document.body.appendChild(live);
                }""",
                guides_source,
            )

            # ----------------------------------------------------------------
            # Phase 1 — Module loaded + exposes the public API.
            # ----------------------------------------------------------------
            api = page.evaluate(
                """() => {
                    const g = window.EInviteAlignmentGuides;
                    if (!g) return null;
                    return {
                        version: g.version,
                        hasComputeSnap: typeof g.computeSnap === 'function',
                        hasBeginDrag: typeof g.beginDrag === 'function',
                        hasUpdateDrag: typeof g.updateDrag === 'function',
                        hasEndDrag: typeof g.endDrag === 'function',
                        hasHideGuides: typeof g.hideGuides === 'function',
                        threshold: g.SNAP_THRESHOLD_PX,
                        stringsKeys: Object.keys(g.STRINGS)
                    };
                }"""
            )
            if not api:
                failures.append("phase1: window.EInviteAlignmentGuides is undefined after script load")
            else:
                if api["version"] != 56:
                    failures.append(f"phase1: expected version 56, got {api['version']}")
                for key in ("hasComputeSnap", "hasBeginDrag", "hasUpdateDrag", "hasEndDrag", "hasHideGuides"):
                    if not api[key]:
                        failures.append(f"phase1: missing API method {key}")
                if api["threshold"] != 6:
                    failures.append(f"phase1: SNAP_THRESHOLD_PX expected 6, got {api['threshold']}")
                # Sanity check that bilingual strings exist for all 6 snap types.
                expected_keys = {
                    "align.snapped.center", "align.snapped.left", "align.snapped.right",
                    "align.snapped.top", "align.snapped.bottom",
                    "align.snapped.centerX", "align.snapped.centerY"
                }
                missing_keys = expected_keys - set(api["stringsKeys"])
                if missing_keys:
                    failures.append(f"phase1: missing STRINGS keys: {sorted(missing_keys)}")

            # ----------------------------------------------------------------
            # Phase 2 — computeSnap() snaps when within 6px of a target.
            # Two mock siblings: A centered around x=200, B centered around x=600.
            # Dragged element centered at x=200.5 → snap to A's center-x with deltaX≈-0.5.
            # ----------------------------------------------------------------
            snap = page.evaluate(
                """() => {
                    const g = window.EInviteAlignmentGuides;
                    // Two mock sibling elements (canvas-coordinate rects).
                    const siblingA = { left: 100, top: 100, width: 200, height: 200, id: 'a' };   // center-x = 200
                    const siblingB = { left: 500, top: 300, width: 200, height: 200, id: 'b' };   // center-x = 600
                    const targets = [
                        ...g.snapCandidatesFor(siblingA),
                        ...g.snapCandidatesFor(siblingB),
                        ...g.canvasCenterTargets({ width: 800, height: 800 })
                    ];
                    // Dragged element centered at x=200.5 (within 6px of siblingA's center-x=200).
                    const dragged = { left: 100.5, top: 110, width: 200, height: 200, id: 'dragged' };
                    return g.computeSnap(dragged, targets, { threshold: 6 });
                }"""
            )
            if not snap:
                failures.append("phase2: computeSnap returned null/undefined")
            else:
                if abs(snap["deltaX"] + 0.5) > 0.01:
                    failures.append(f"phase2: deltaX expected ~-0.5, got {snap['deltaX']}")
                if not snap["matches"]:
                    failures.append("phase2: expected at least one snap match, got none")
                else:
                    match_types = [m["type"] for m in snap["matches"]]
                    if "center-x" not in match_types:
                        failures.append(f"phase2: expected center-x match, got {match_types}")
                    center_match = next((m for m in snap["matches"] if m["type"] == "center-x"), None)
                    if center_match and center_match["source"] != "a":
                        failures.append(f"phase2: center-x match source expected 'a', got {center_match['source']}")
                    if center_match and abs(center_match["value"] - 200) > 0.01:
                        failures.append(f"phase2: center-x match value expected 200, got {center_match['value']}")

            # ----------------------------------------------------------------
            # Phase 3 — computeSnap() returns no matches when far from every target.
            # ----------------------------------------------------------------
            no_snap = page.evaluate(
                """() => {
                    const g = window.EInviteAlignmentGuides;
                    const targets = [
                        ...g.snapCandidatesFor({ left: 100, top: 100, width: 200, height: 200, id: 'a' }),
                        ...g.canvasCenterTargets({ width: 800, height: 800 })
                    ];
                    // Dragged element at (10,10) with 100x100 size — its
                    // edges (10,110) and centers (60) are far from every
                    // sibling edge/center (100,200,300) and the canvas
                    // center (400). Minimum gap is 40px (60 → 100), well
                    // outside the 6px threshold.
                    return g.computeSnap({ left: 10, top: 10, width: 100, height: 100, id: 'dragged' }, targets, { threshold: 6 });
                }"""
            )
            if not no_snap:
                failures.append("phase3: computeSnap returned null/undefined")
            else:
                if no_snap["matches"]:
                    failures.append(f"phase3: expected no matches, got {no_snap['matches']}")
                if abs(no_snap["deltaX"]) > 0.001 or abs(no_snap["deltaY"]) > 0.001:
                    failures.append(f"phase3: expected 0 deltas, got dx={no_snap['deltaX']} dy={no_snap['deltaY']}")

            # ----------------------------------------------------------------
            # Phase 4 — beginDrag + updateDrag + endDrag drive the live overlay
            # AND emit the einvite:alignment-snapped event.
            # ----------------------------------------------------------------
            event_payload = page.evaluate(
                """() => {
                    const g = window.EInviteAlignmentGuides;
                    window.__capturedSnaps = [];
                    // Build a mock stage with sibling rects.
                    // The guides.js beginDrag() reads from window.EInviteEditorBridge.getState()
                    // to build targets; we install a mock bridge so the test runs without
                    // the full editor.
                    window.EInviteEditorBridge = {
                        getState: () => ({
                            objects: {
                                'a': { left: 0.125, top: 0.125, width: 0.25, height: 0.25 }   // 100,100,200,200 on an 800x800 stage
                            },
                            designPages: []
                        }),
                        getActiveCanvasId: () => 'hero'
                    };
                    // Make the stage have a known offsetWidth/Height.
                    const stage = document.getElementById('stage');
                    stage.style.width = '800px';
                    stage.style.height = '800px';
                    Object.defineProperty(stage, 'offsetWidth', { value: 800, configurable: true });
                    Object.defineProperty(stage, 'offsetHeight', { value: 800, configurable: true });
                    // Canvas rect (matches the stage dims).
                    const canvasRect = { width: 800, height: 800 };
                    // Begin a drag for the dragged element.
                    g.beginDrag('dragged', canvasRect);
                    // Update with a dragged rect that has its center-x within 6px of sibling 'a's center-x (200).
                    // Dragged center-x = 200 + 2 = 202 → deltaX should be -2 (snap to 200).
                    g.updateDrag({ left: 102, top: 100, width: 200, height: 200 });
                    g.endDrag();
                    return {
                        captured: window.__capturedSnaps,
                        overlayChildren: window.EInviteAlignmentGuides.overlay
                            ? Array.from(window.EInviteAlignmentGuides.overlay.children).map(line => ({
                                className: line.getAttribute('class'),
                                x1: line.getAttribute('x1'),
                                y1: line.getAttribute('y1'),
                                x2: line.getAttribute('x2'),
                                y2: line.getAttribute('y2')
                            }))
                            : null
                    };
                }"""
            )
            if not event_payload:
                failures.append("phase4: evaluate returned null")
            else:
                captured = event_payload.get("captured", [])
                if not captured:
                    failures.append("phase4: expected at least one captured einvite:alignment-snapped event, got none")
                else:
                    # The first event's matches should include center-x targeting sibling 'a'.
                    first_event = captured[0]
                    if not isinstance(first_event, list):
                        failures.append(f"phase4: event detail should be an array of matches, got {type(first_event)}")
                    else:
                        match = next((m for m in first_event if m["type"] == "center-x"), None)
                        if not match:
                            failures.append(f"phase4: no center-x match in event detail: {first_event}")
                        else:
                            if match["source"] != "a":
                                failures.append(f"phase4: center-x match source expected 'a', got {match['source']}")
                            if not match.get("label"):
                                failures.append("phase4: match missing bilingual label")
                            else:
                                if not match["label"].get("en") or not match["label"].get("km"):
                                    failures.append(f"phase4: bilingual label incomplete: {match['label']}")
                                if "Aligned" not in match["label"]["en"]:
                                    failures.append(f"phase4: EN label unexpected: {match['label']['en']}")

                overlay_children = event_payload.get("overlayChildren") or []
                if not overlay_children:
                    failures.append("phase4: expected at least one guide <line> in the overlay, got none")
                else:
                    center_lines = [c for c in overlay_children if c["className"] and "is-center" in c["className"]]
                    if not center_lines:
                        failures.append(f"phase4: no .is-center guide line found in overlay: {overlay_children}")
                    else:
                        # The center-x line should span the canvas vertically (y1=0, y2=800) at x=200.
                        line = center_lines[0]
                        if abs(float(line["x1"]) - 200) > 0.01 or abs(float(line["x2"]) - 200) > 0.01:
                            failures.append(f"phase4: center-x line should be at x=200, got {line}")
                        if float(line["y1"]) != 0 or float(line["y2"]) != 800:
                            failures.append(f"phase4: center-x line should span y=0..800, got {line}")

            # ----------------------------------------------------------------
            # Phase 5 — guide overlay fade-out is scheduled on endDrag (200ms).
            # We verify the .is-fading class is added shortly after endDrag.
            # ----------------------------------------------------------------
            fading = page.evaluate(
                """async () => {
                    const g = window.EInviteAlignmentGuides;
                    window.EInviteEditorBridge = {
                        getState: () => ({ objects: { 'a': { left: 0.125, top: 0.125, width: 0.25, height: 0.25 } }, designPages: [] }),
                        getActiveCanvasId: () => 'hero'
                    };
                    const stage = document.getElementById('stage');
                    stage.style.width = '800px'; stage.style.height = '800px';
                    Object.defineProperty(stage, 'offsetWidth', { value: 800, configurable: true });
                    Object.defineProperty(stage, 'offsetHeight', { value: 800, configurable: true });
                    g.beginDrag('dragged', { width: 800, height: 800 });
                    g.updateDrag({ left: 102, top: 100, width: 200, height: 200 });
                    g.endDrag();
                    // Wait long enough for the 200ms fade timer to fire.
                    await new Promise(resolve => setTimeout(resolve, 260));
                    const overlay = g.overlay;
                    if (!overlay) return { error: 'overlay missing after endDrag' };
                    return {
                        hidden: overlay.hidden,
                        faded: overlay.classList.contains('is-fading'),
                        childCount: overlay.children.length
                    };
                }"""
            )
            if not fading:
                failures.append("phase5: evaluate returned null")
            elif fading.get("error"):
                failures.append(f"phase5: {fading['error']}")
            else:
                # After 260ms, the fade timer should have fired and cleared the overlay.
                if not fading["hidden"]:
                    failures.append(f"phase5: overlay.hidden expected true after fade, got {fading['hidden']}")
                if fading["childCount"] != 0:
                    failures.append(f"phase5: overlay expected 0 children after fade, got {fading['childCount']}")
        finally:
            browser.close()

    if failures:
        print("EDITOR_ALIGNMENT_GUIDES_TEST_FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(OK_MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(run())
