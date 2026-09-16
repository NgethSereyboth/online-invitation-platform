/**
 * viewport.js — Zoom + view controls (ROADMAP §3.1.5 + §3.4.5, v0.56).
 *
 * Exposes `EInviteViewport` — a service that adds zoom presets + cursor-zoom +
 * pan-with-Space/middle-mouse to the editor canvas. It does NOT replace the
 * existing `EInviteCanvasViewController` (defined in app.js) — it layers the
 * new behaviour on top, delegating to the controller's `setZoom(value, opts)`
 * whenever possible so existing zoom HUD chrome keeps working.
 *
 * Capabilities:
 *   • Zoom presets: 25%, 50%, 75%, 100%, 150%, 200%, Fit, Fill.
 *   • Zoom to cursor: hold Ctrl+scroll wheel.
 *   • Fit-to-screen computes scale so whole page fits minus 40px margin
 *     (per ROADMAP §3.4.5). Existing fit() uses 70px margin; this Fit preset
 *     uses 40px to match the ROADMAP spec.
 *   • Fill: scale so the page fills the viewport (one axis may overflow).
 *   • Pan with Space held + drag, or with middle mouse button drag.
 *     (The existing `EInviteCanvasPanController` handles the Space key;
 *      this module wires the middle-mouse path + ensures both work
 *      regardless of whether the existing controller is active.)
 *
 * Bilingual strings: `zoom.preset.fit` / `zoom.preset.fill` etc.
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';

  if (window.EInviteViewport?.version >= 56) return;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);

  /** Zoom presets (per ROADMAP §3.4.5). */
  const PRESETS = Object.freeze([0.25, 0.50, 0.75, 1.00, 1.50, 2.00]);
  /** Fit-to-screen margin (per ROADMAP §3.4.5: "minus a 40px margin"). */
  const FIT_MARGIN_PX = 40;
  /** Zoom step for Ctrl+scroll. */
  const SCROLL_STEP = 0.10;
  /** Min/max zoom (matches app.js: 0.35-2). */
  const MIN_ZOOM = 0.35, MAX_ZOOM = 2.0;

  /** Bilingual labels. */
  const STRINGS = Object.freeze({
    'zoom.preset.fit':   { en: 'Fit',  km: 'ជាប់' },
    'zoom.preset.fill':  { en: 'Fill', km: 'ពេញ' },
    'zoom.preset.actual':{ en: '100%', km: '១០០%' },
    'zoom.zoomIn':       { en: 'Zoom in',  km: 'ពង្រីក' },
    'zoom.zoomOut':      { en: 'Zoom out', km: 'បន្ថយ' },
    'zoom.fit':          { en: 'Fit to screen', km: 'ជាប់នឹងផ្ទៃតាមរូប' },
    'zoom.fill':         { en: 'Fill screen',  km: 'បំពេញផ្ទៃតាមរូប' },
    'pan.label':         { en: 'Pan', km: 'អូស' }
  });

  /** @returns {ReturnType<typeof Object.freeze> & {setZoom?: (value: number, options?: object) => number, zoom?: number, fit?: () => number, actual?: () => number, zoomToSelection?: () => number}} */
  const controller = () => window.EInviteCanvasViewController;

  /**
   * Apply a zoom value via the existing controller. Falls back to direct
   * stage transform when the controller is unavailable (shouldn't happen
   * on the editor page, but kept defensive).
   *
   * @param {number} value
   * @param {{clientX?:number,clientY?:number,source?:string,anchor?:boolean}} [options]
   * @returns {number} The applied zoom value (clamped).
   */
  function applyZoom(value, options = {}) {
    const ctrl = controller();
    if (ctrl?.setZoom) {
      return ctrl.setZoom(value, options);
    }
    const stage = $('#stage');
    if (stage) {
      const clamped = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Number(value) || 1));
      stage.style.transform = `scale(${clamped})`;
      window.dispatchEvent(new CustomEvent('einvite:zoom-changed', {
        detail: { zoom: clamped, source: options.source || 'viewport' }
      }));
      return clamped;
    }
    return Number(value) || 1;
  }

  /**
   * Fit-to-screen: scale so whole page fits in the visible area minus 40px.
   * @returns {number} The applied zoom.
   */
  function fit() {
    const viewport = $('#canvasViewport');
    const stage = $('#stage');
    if (!viewport || !stage) return controller()?.zoom ?? 1;
    const sw = stage.offsetWidth, sh = stage.offsetHeight;
    if (!sw || !sh) return controller()?.zoom ?? 1;
    const scale = Math.min(
      (viewport.clientWidth  - 2 * FIT_MARGIN_PX) / sw,
      (viewport.clientHeight - 2 * FIT_MARGIN_PX) / sh
    );
    return applyZoom(Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, scale)), { anchor: false, source: 'fit' });
  }

  /**
   * Fill: scale so the page fills the viewport (one axis may overflow).
   * @returns {number} The applied zoom.
   */
  function fill() {
    const viewport = $('#canvasViewport');
    const stage = $('#stage');
    if (!viewport || !stage) return controller()?.zoom ?? 1;
    const sw = stage.offsetWidth, sh = stage.offsetHeight;
    if (!sw || !sh) return controller()?.zoom ?? 1;
    const scale = Math.max(
      (viewport.clientWidth  - 2 * FIT_MARGIN_PX) / sw,
      (viewport.clientHeight - 2 * FIT_MARGIN_PX) / sh
    );
    return applyZoom(Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, scale)), { anchor: false, source: 'fill' });
  }

  /**
   * Apply one of the named presets. `Fit` and `Fill` are computed live.
   * @param {number|'fit'|'fill'|'actual'} preset
   * @returns {number} The applied zoom.
   */
  function preset(p) {
    if (p === 'fit') return fit();
    if (p === 'fill') return fill();
    if (p === 'actual') return applyZoom(1, { anchor: false, source: 'actual' });
    const value = Number(p);
    if (!Number.isFinite(value)) return controller()?.zoom ?? 1;
    return applyZoom(value, { anchor: false, source: 'preset' });
  }

  /**
   * Zoom in/out by a fixed step.
   * @param {number} direction +1 for in, -1 for out.
   * @param {{clientX?:number,clientY?:number}} [anchor]
   */
  function step(direction, anchor = {}) {
    const current = controller()?.zoom ?? 1;
    const next = current + direction * SCROLL_STEP;
    applyZoom(next, { ...anchor, source: 'step' });
  }

  /**
   * Zoom to cursor — Ctrl+scroll wheel handler.
   * @param {WheelEvent} event
   */
  function onWheel(event) {
    if (!event.ctrlKey && !event.metaKey) return;   // only Ctrl+scroll
    event.preventDefault();
    const direction = event.deltaY < 0 ? +1 : -1;
    step(direction, { clientX: event.clientX, clientY: event.clientY });
  }

  // =========================================================================
  // Middle-mouse pan — pan the viewport when the middle button is held
  // + dragged. Space+drag pan is already handled by the existing
  // EInviteCanvasPanController; this module adds the middle-mouse path.
  // =========================================================================

  /** @type {{pointerId:number,startX:number,startY:number,left:number,top:number}|null} */
  let pan = null;

  /**
   * @param {PointerEvent} event
   */
  function onPointerDown(event) {
    if (event.button !== 1) return;   // only middle button
    const viewport = $('#canvasViewport');
    if (!viewport) return;
    pan = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      left: viewport.scrollLeft,
      top: viewport.scrollTop
    };
    try { viewport.setPointerCapture(event.pointerId); } catch { /* ignore */ }
    document.body.classList.add('ei-pan-mode', 'ei-panning');
    event.preventDefault();
    event.stopPropagation();
  }

  /**
   * @param {PointerEvent} event
   */
  function onPointerMove(event) {
    if (!pan || event.pointerId !== pan.pointerId) return;
    const viewport = $('#canvasViewport');
    if (!viewport) return;
    viewport.scrollLeft = pan.left - (event.clientX - pan.startX);
    viewport.scrollTop  = pan.top  - (event.clientY - pan.startY);
  }

  /**
   * @param {PointerEvent} event
   */
  function onPointerUp(event) {
    if (!pan || event.pointerId !== pan.pointerId) return;
    pan = null;
    document.body.classList.remove('ei-pan-mode', 'ei-panning');
  }

  // =========================================================================
  // Install / destroy
  // =========================================================================
  let installed = false;
  const cleanup = [];
  /**
   * @param {EventTarget|null} target
   * @param {string} type
   * @param {EventListenerOrEventListenerObject} fn
   * @param {AddEventListenerOptions|boolean} [options]
   */
  function on(target, type, fn, options) {
    target?.addEventListener?.(type, fn, options);
    cleanup.push(() => target?.removeEventListener?.(type, fn, options));
  }

  function install() {
    if (installed) return;
    const viewport = $('#canvasViewport');
    if (!viewport) return;
    on(viewport, 'wheel', onWheel, { capture: true, passive: false });
    on(viewport, 'pointerdown', onPointerDown, true);
    on(window, 'pointermove', onPointerMove, true);
    on(window, 'pointerup', onPointerUp, true);
    on(window, 'pointercancel', onPointerUp, true);
    installed = true;
  }

  function destroy() {
    if (!installed) return;
    cleanup.splice(0).forEach(fn => { try { fn(); } catch { /* ignore */ } });
    pan = null;
    document.body.classList.remove('ei-pan-mode', 'ei-panning');
    installed = false;
  }

  // Public API.
  window.EInviteViewport = Object.freeze({
    version: 56,
    STRINGS,
    PRESETS,
    FIT_MARGIN_PX,
    MIN_ZOOM,
    MAX_ZOOM,
    // Zoom operations.
    fit,
    fill,
    preset,
    step,
    applyZoom,
    // Install / destroy.
    install,
    destroy,
    get pan() { return pan; }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();

  window.EInviteLifecycle?.add?.(destroy);
})();
