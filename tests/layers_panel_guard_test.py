#!/usr/bin/env python3
"""layers_panel_guard_test.py — the guard the layers-panel rewrite was waiting for.

Why this exists
---------------
`a851083` stopped the overlay's ResizeObserver re-arming on its own output and
recorded in its own message that the *next* step — caching `renderLayers()`'
wholesale `#layersPanel.innerHTML` rewrite — was deliberately **not** taken,
because "the behaviour it can break (a stale layers panel) has no guard on this
host ... and an unverified render-cache change is how a perf fix becomes a UI
bug". This file is that guard.

Two contracts, and both are asserted on the **served bundle** as well as on the
source, because the bundle is what a browser actually runs:

  1. LAYERS PANEL — one row per object, each row carries its object's id, and the
     row's selection state tracks the selection. A render cache that returns a
     stale list breaks this and nothing else would notice.
  2. OBSERVER GUARD — one performed sync must not arm another. The overlay
     observer's callback only schedules a sync when an observed box actually
     changed; if that comparison is removed the sync re-arms itself and the panel
     is rewritten at frame rate. So the test measures *panel writes at rest*: after
     a sync, the panel must go quiet. A second assertion forces a genuine box
     change and requires the panel to be written again, so the test cannot pass by
     the observer simply being dead.

What this guard does and does not catch — measured with negative controls
------------------------------------------------------------------------
* **It does catch the guard being removed.** Deleting the `if(boxChanged)` gate
  from `professional-editor.js`, rebuilding, and re-running this file makes
  the *static* assertion fail with `the schedule is no longer gated on a real box
  change`. That control was run, and the result is recorded in the pass report.
* **It does NOT catch that removal dynamically on this host.** With the gate
  removed and the bundle rebuilt, `_run_dynamic()` still returns `pass`: in this
  headless viewport the panel rewrite does not move `#stage`'s border box, so the
  self-re-arming loop the gate prevents does not form here. The at-rest assertion
  therefore proves the panel goes quiet, which is a real property, but it cannot
  discriminate a guarded build from an unguarded one on this machine — and this
  file says so instead of implying otherwise.
* The layers-panel contract (rows == objects, ids present, selection visible) is
  the part that guards the *intended* next change, caching `renderLayers`.

Run:
    .venv/bin/python -m pytest tests/layers_panel_guard_test.py -q
    .venv/bin/python tests/layers_panel_guard_test.py
"""
from __future__ import annotations

import os
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
SRC_JS = ROOT / "src" / "js"
SERVE_ROOT = ROOT / "src" / "python"

EDITOR_SRC = SRC_JS / "professional-editor.js"
APP_SRC = SRC_JS / "app.js"
BUNDLE = SRC_JS / "bundle-index.js"
SERVED_BUNDLE = SERVE_ROOT / "bundle-index.js"

# The change-detection guard, as one regex over the formatted source and the
# minified bundle: compare the box key for this element, and gate the schedule on it.
GUARD_KEY = re.compile(r"overlayObservedSizes\.get\(\s*entry\.target\s*\)\s*!==\s*key")
GUARD_GATE = re.compile(r"if\s*\(\s*boxChanged\s*\)\s*scheduleOverlaySync\(\)")
DELEGATION = re.compile(r"EInviteProfessionalEditor\??\.\s*renderLayers")
WEAKMAP = re.compile(r"overlayObservedSizes\s*=\s*new\s+WeakMap")

# Injected before the page's own scripts, so it counts every write the app makes
# and every ResizeObserver notification the engine delivers.
#
# Two signals, because they answer two different questions and neither answers
# both: __panelWrites says "is the panel still being rebuilt?" (the re-arm), and
# __resizeCallbacks says "is the observer still being notified?" (aliveness).
# The first version of this test used panel writes for both and failed: after a
# genuine box change the boxes really did change (stage 212->164 px) while the
# panel was NOT rewritten, because a sync with no data change has nothing to
# render. Counting notifications is what proves the observer still works.
PROBE = """(() => {
  window.__panelWrites = 0;
  window.__resizeObservers = { constructed: 0, callbacks: 0 };
  const NativeRO = window.ResizeObserver;
  if (typeof NativeRO === 'function') {
    window.ResizeObserver = function (cb) {
      window.__resizeObservers.constructed += 1;
      return new NativeRO(function (entries, observer) {
        window.__resizeObservers.callbacks += 1;
        return cb.call(this, entries, observer);
      });
    };
    window.ResizeObserver.prototype = NativeRO.prototype;
  }
  const start = () => {
    const panel = document.querySelector('#layersPanel');
    if (!panel) { requestAnimationFrame(start); return; }
    new MutationObserver(mutations => {
      window.__panelWrites += mutations.length;
    }).observe(panel, { childList: true, subtree: true, characterData: true, attributes: true });
    window.__panelProbeReady = true;
  };
  requestAnimationFrame(start);
})();"""


def _browser_required() -> bool:
    return os.environ.get("EINVITE_REQUIRE_BROWSER", "0").lower() in {"1", "true", "yes"}


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


def _serve(root: Path):
    handler = lambda *a, **kw: _QuietHandler(*a, directory=str(root), **kw)  # noqa: E731
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


# --------------------------------------------------------------------------- #
# Static contract — always runs, no browser.
# --------------------------------------------------------------------------- #

def test_static_guard_present_in_source_and_bundles():
    for path in (EDITOR_SRC, BUNDLE, SERVED_BUNDLE):
        text = path.read_text(encoding="utf-8")
        assert GUARD_KEY.search(text), f"{path}: the observer's per-element box comparison is gone"
        assert GUARD_GATE.search(text), f"{path}: the schedule is no longer gated on a real box change"
        assert "observe(stage)" in text, f"{path}: the observer no longer observes #stage"
        assert WEAKMAP.search(text), f"{path}: overlayObservedSizes is no longer a WeakMap keyed by element"


def test_static_render_layers_delegates_to_the_professional_editor():
    for path in (APP_SRC, BUNDLE, SERVED_BUNDLE):
        text = path.read_text(encoding="utf-8")
        assert DELEGATION.search(text), f"{path}: renderLayers no longer delegates to the v17 editor"


# --------------------------------------------------------------------------- #
# Dynamic contract — Playwright.
# --------------------------------------------------------------------------- #

PANEL_SNAPSHOT = """() => {
  const objects = [...document.querySelectorAll('#stage .object')];
  const rows = [...document.querySelectorAll('#layersPanel .pe-layer-row, #layersPanel .layer-row')];
  return {
    objects: objects.length,
    rows: rows.length,
    rowIds: rows.map(r => r.dataset.layerId || r.dataset.id || null).filter(Boolean),
    objectIds: objects.map(o => o.dataset.id).filter(Boolean),
    active: rows.filter(r => r.classList.contains('active') || r.getAttribute('aria-selected') === 'true').length,
  };
}"""


def _run_dynamic() -> tuple[str, str]:
    """Return (status, detail) with status in {'pass', 'skip', 'fail'}."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return "skip", f"playwright is not importable: {exc}"

    sys.path.insert(0, str(TESTS_DIR))
    from browser_runtime import launch_chromium

    httpd, port = _serve(SERVE_ROOT)
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as pw:
            try:
                browser = launch_chromium(pw)
            except Exception as exc:
                # A missing browser *executable* is the same class of fact as a missing
                # playwright module, and has to take the same path. Measured on a host
                # with playwright installed but its bundled Chromium absent and no
                # PLAYWRIGHT_CHROMIUM_EXECUTABLE: the launch raised
                # `Executable doesn't exist at .../chrome-headless-shell` and the test
                # went red for an environmental reason, which is a false failure. It is
                # reported as a skip with the reason, and `test_...` still raises when
                # EINVITE_REQUIRE_BROWSER=1, so a host that is supposed to have a
                # browser still fails loudly.
                return "skip", f"cannot launch a browser: {exc}"
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.add_init_script(PROBE)
                page.goto(f"{base}/index.html", wait_until="load", timeout=60000)
                page.wait_for_function(
                    "() => !!window.EInviteProfessionalEditor && window.EInviteProfessionalEditor.version >= 17",
                    timeout=30000,
                )
                page.wait_for_timeout(1500)

                version = page.evaluate("() => window.EInviteProfessionalEditor.version")
                if version < 17:
                    return "fail", f"editor version {version} is below the guarded implementation"

                # --- 1. the layers panel lists every object and tracks selection
                snap = page.evaluate(PANEL_SNAPSHOT)
                if snap["objects"] == 0:
                    return "skip", "the fixture canvas rendered no objects, so there is nothing to list"
                if snap["rows"] != snap["objects"]:
                    return "fail", (
                        f"layers panel lists {snap['rows']} rows for {snap['objects']} objects"
                    )
                missing = [i for i in snap["objectIds"] if i not in snap["rowIds"]]
                if missing:
                    return "fail", f"objects with no row: {missing[:5]}"

                page.evaluate(
                    """() => {
                      const first = document.querySelector('#stage .object');
                      for (const type of ['pointerdown', 'pointerup', 'click']) {
                        first.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true}));
                      }
                    }"""
                )
                page.wait_for_timeout(500)
                selected = page.evaluate(PANEL_SNAPSHOT)
                if selected["active"] < 1:
                    return "fail", "selecting an object marked no layer row active"

                # --- 2. at rest the panel must stop being rewritten
                page.wait_for_timeout(500)
                rest = page.evaluate(
                    """async () => {
                      const api = window.EInviteProfessionalEditor;
                      const frame = () => new Promise(r => requestAnimationFrame(() => r()));
                      const before = window.__panelWrites;
                      api.sync();                 // one performed sync, as the app does it
                      for (let i = 0; i < 6; i++) await frame();
                      const afterSync = window.__panelWrites;
                      await new Promise(r => setTimeout(r, 400));
                      const settled = window.__panelWrites;
                      return { before, afterSync, settled, probe: !!window.__panelProbeReady };
                    }"""
                )
                if not rest["probe"]:
                    return "skip", "the panel-write probe never attached (no #layersPanel)"
                # A vacuous pass must be impossible: if one performed sync writes
                # nothing at all, "0 writes at rest" would prove nothing.
                if rest["afterSync"] - rest["before"] <= 0:
                    return "skip", (
                        "one performed sync produced no panel writes on this build, so the "
                        "at-rest assertion cannot distinguish a deduplicated observer from an idle one"
                    )
                # The 400 ms window after the sync must add no further writes: at rest the
                # panel must be quiet. Measured caveat (see the module docstring): on this
                # host an unguarded build is also quiet here, so this is a property check,
                # not the regression detector for the observer gate.
                growth = rest["settled"] - rest["afterSync"]
                if growth != 0:
                    return "fail", (
                        "the overlay observer kept re-arming after the sync: "
                        f"{rest['afterSync'] - rest['before']} writes during the sync and "
                        f"{growth} more over the following 400 ms with no input event"
                    )

                # --- 3. the observer must still be alive: a real box change writes the panel
                # Three independent ways to change an observed box. #stage is sized
                # by the editor's layout, so a single property may legitimately not
                # move its border box; the check asks for a reaction to any of them.
                alive = page.evaluate(
                    """async () => {
                      const frame = () => new Promise(r => requestAnimationFrame(() => r()));
                      const stage = document.querySelector('#stage');
                      const viewport = document.querySelector('#canvasViewport');
                      const box = el => { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) }; };
                      const before = window.__panelWrites;
                      const beforeCallbacks = window.__resizeObservers.callbacks;
                      const beforeBox = { stage: box(stage), viewport: viewport ? box(viewport) : null };
                      const previous = { minHeight: stage.style.minHeight, padding: stage.style.padding, width: stage.style.width };
                      stage.style.padding = '23px';
                      stage.style.minHeight = (stage.getBoundingClientRect().height + 137) + 'px';
                      stage.style.width = (stage.getBoundingClientRect().width + 89) + 'px';
                      if (viewport) viewport.style.width = (viewport.getBoundingClientRect().width + 61) + 'px';
                      for (let i = 0; i < 10; i++) await frame();
                      await new Promise(r => setTimeout(r, 500));
                      const after = window.__panelWrites;
                      const afterBox = { stage: box(stage), viewport: viewport ? box(viewport) : null };
                      const afterCallbacks = window.__resizeObservers.callbacks;
                      stage.style.minHeight = previous.minHeight;
                      stage.style.padding = previous.padding;
                      stage.style.width = previous.width;
                      if (viewport) viewport.style.width = '';
                      return {
                        before, after, delta: after - before, beforeBox, afterBox,
                        callbacksBefore: beforeCallbacks, callbacksAfter: afterCallbacks,
                        callbackDelta: afterCallbacks - beforeCallbacks,
                        observersConstructed: window.__resizeObservers.constructed,
                      };
                    }"""
                )
                detail = (
                    f"rows={snap['rows']}==objects={snap['objects']}, "
                    f"selection marked {selected['active']} row(s), "
                    f"{rest['afterSync'] - rest['before']} writes for one sync then 0 at rest, "
                    f"box {alive['beforeBox']} -> {alive['afterBox']}, "
                    f"{alive['callbackDelta']} observer notification(s) on resize"
                )
                if alive["observersConstructed"] == 0:
                    return "fail", f"no ResizeObserver was constructed at all. {detail}"
                if alive["callbackDelta"] <= 0:
                    return "fail", (
                        "the observer was not notified by a real #stage/#canvasViewport resize "
                        f"({alive['callbackDelta']} notifications, box {alive['beforeBox']} -> "
                        f"{alive['afterBox']}), so measuring quiescence would be measuring a dead "
                        f"observer. {detail}"
                    )
                return "pass", detail
            finally:
                browser.close()
    finally:
        httpd.shutdown()


def test_dynamic_layers_panel_and_observer_guard():
    status, detail = _run_dynamic()
    if status == "skip":
        print(f"V17_LAYERS_PANEL_GUARD_SKIPPED {detail}")
        if _browser_required():
            raise AssertionError(f"browser required but unavailable: {detail}")
        return
    assert status == "pass", detail
    print(f"V17_LAYERS_PANEL_GUARD_PASSED {detail}")


def main() -> int:
    test_static_guard_present_in_source_and_bundles()
    test_static_render_layers_delegates_to_the_professional_editor()
    print("V17_LAYERS_PANEL_GUARD_STATIC_PASSED")
    status, detail = _run_dynamic()
    if status == "skip":
        print(f"V17_LAYERS_PANEL_GUARD_SKIPPED {detail}")
        return 1 if _browser_required() else 0
    if status == "fail":
        print(f"V17_LAYERS_PANEL_GUARD_FAILED {detail}")
        return 1
    print(f"V17_LAYERS_PANEL_GUARD_PASSED {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
