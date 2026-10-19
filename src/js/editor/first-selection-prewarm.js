// first-selection-prewarm — pays the one-time cost of the first selection-chrome
// paint at boot, where nothing is being measured, instead of on the user's first
// selection gesture.
//
// Why: on a fresh browser profile, the first selection in the editor shows three
// composited chrome elements (selection card / toolbar / box) for the first time.
// That first present pays GPU pipeline + lazy-compile costs that can stall a
// single frame by ~100 ms on a cold browser (measured: canvas-motion perf gate
// snap gesture, run 1 of 3 only). Warming the same path at editor-ready moves
// the cost off the first interaction; subsequent selections are unchanged.
//
// Safety:
// - Runs once per page load, only after the editor reports ready and the stage
//   has a laid-out object.
// - Skipped entirely if the user interacts first (their selection pays it).
// - Selection is cleared afterwards; no document/undo state is touched.
(function () {
  'use strict';
  if (window.EInviteFirstSelectionPrewarm) return;

  var api = { version: '1', state: 'idle', at: 0, done: 0, ok: false };
  window.EInviteFirstSelectionPrewarm = api;

  var attempts = 0;
  var userInteracted = false;
  var HOLD_MS = 140;
  var POLL_MS = 80;
  var MAX_ATTEMPTS = 240;

  document.addEventListener('pointerdown', function () { userInteracted = true; }, true);

  function candidate() {
    var el = document.querySelector('#stage .object[data-id]');
    if (!el || !el.getBoundingClientRect) return null;
    var r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return null;
    var bridge = window.EInviteEditorBridge;
    if (!bridge || typeof bridge.select !== 'function') return null;
    return { id: el.dataset.id, bridge: bridge };
  }

  function finish(ok) {
    api.state = 'done';
    api.ok = !!ok;
    api.done = Math.round(performance.now());
    window.__prewarmAt = api.at;
    window.__prewarmDone = api.done;
  }

  function warm() {
    if (api.state !== 'idle') return;
    if (userInteracted || document.hidden) return finish(false);
    if (++attempts > MAX_ATTEMPTS) return finish(false);
    var c = null;
    try { c = candidate(); } catch (e) { c = null; }
    if (!c) return void setTimeout(warm, POLL_MS);
    api.state = 'active';
    api.at = Math.round(performance.now());
    try { c.bridge.select([c.id]); } catch (e) { return finish(false); }
    setTimeout(function () {
      try { c.bridge.select([]); } catch (e) {}
      finish(true);
    }, HOLD_MS);
  }

  function start() {
    if (document.documentElement.dataset.editorReady === 'true') {
      setTimeout(warm, 120);
      return;
    }
    var iv = setInterval(function () {
      if (document.documentElement.dataset.editorReady === 'true') {
        clearInterval(iv);
        setTimeout(warm, 120);
      }
    }, 60);
    setTimeout(function () { clearInterval(iv); }, 20000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
