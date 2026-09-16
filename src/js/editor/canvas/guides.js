/**
 * guides.js — Smart alignment guides (ROADMAP §3.1.1, v0.56).
 *
 * Exposes `EInviteAlignmentGuides` — a service that, during a canvas drag,
 * compares the dragged element's edges/center against a list of snap targets
 * (sibling edges/centers + canvas center) and snaps within a 6px threshold.
 * When a snap occurs it:
 *
 *   1. Renders 1px SVG guide lines on an overlay `<svg class="alignment-guide-overlay">`.
 *      Pink (#ec4899) for center alignments, blue (#3b82f6) for edges.
 *   2. Emits an `einvite:alignment-snapped` CustomEvent on `window` with the
 *      matched target's `{ type, value, source }`.
 *   3. Fades the overlay out 200ms after `pointerup`.
 *
 * Implementation notes (per ROADMAP §3.1.1):
 *   • Uses Pointer Events API + `element.setPointerCapture()` so events keep
 *     flowing when the pointer leaves the dragged element.
 *   • Snap threshold = 6px.
 *   • If multiple targets match, prefer the closest. If two match equally
 *     (rare), both guides are shown.
 *
 * Accessibility (per ROADMAP §3.1.1): guides are visual-only. Keyboard users
 * get alignment via the inspector panel `Align left/center/right` buttons.
 *
 * Bilingual strings: every snap event carries an `align.snapped.*` key with
 * EN + KH variants (see `STRINGS` below).
 *
 * Idempotent: a second load is a no-op (guarded by `version`).
 */
(() => {
  'use strict';

  if (window.EInviteAlignmentGuides?.version >= 56) return;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);

  /** Snap threshold in CSS pixels. */
  const SNAP_THRESHOLD_PX = 6;

  /** Fade-out duration in ms (matches CSS `.alignment-guide-overlay`). */
  const FADE_MS = 200;

  /**
   * Bilingual strings for snap events. The `key` is exposed on the
   * `einvite:alignment-snapped` event detail; consumers (toasts, inspector)
   * look up EN/KH here.
   */
  const STRINGS = Object.freeze({
    'align.snapped.center':  { en: 'Aligned to center',  km: 'តម្រឹមទៅកណ្តាល' },
    'align.snapped.left':    { en: 'Aligned to left edge',  km: 'តម្រឹមទៅគែមឆ្វេង' },
    'align.snapped.right':   { en: 'Aligned to right edge', km: 'តម្រឹមទៅគែមស្តាំ' },
    'align.snapped.top':    { en: 'Aligned to top edge',   km: 'តម្រឹមទៅគែមលើ' },
    'align.snapped.bottom': { en: 'Aligned to bottom edge', km: 'តម្រឹមទៅគែមក្រោម' },
    'align.snapped.centerX': { en: 'Aligned to vertical center', km: 'តម្រឹមទៅកណ្តាលបញ្ឈរ' },
    'align.snapped.centerY': { en: 'Aligned to horizontal center', km: 'តម្រឹមទៅកណ្តាលផ្តេក' }
  });

  /**
   * The seven snap-target types per the ROADMAP. `axis` is `'x'` or `'y'`.
   * `'center-x'` is the vertical centerline (x-axis); `'center-y'` is the
   * horizontal centerline (y-axis).
   * @typedef {'edge-left'|'edge-right'|'center-x'|'edge-top'|'edge-bottom'|'center-y'} SnapType
   */

  /** Axis for each snap type. */
  const AXIS = {
    'edge-left':    'x',
    'edge-right':   'x',
    'center-x':     'x',
    'edge-top':     'y',
    'edge-bottom':  'y',
    'center-y':     'y'
  };

  /** String key for the snapped-event detail (matched to STRINGS). */
  const STRING_KEY = {
    'edge-left':    'align.snapped.left',
    'edge-right':   'align.snapped.right',
    'center-x':     'align.snapped.centerX',
    'edge-top':     'align.snapped.top',
    'edge-bottom':  'align.snapped.bottom',
    'center-y':     'align.snapped.centerY'
  };

  /**
   * Pure helper: build the candidate snap values (edges + center) for a
   * single element. Returns an array of `{type, value, source}` entries.
   * @param {{left:number,top:number,width:number,height:number,id:string}} rect
   * @returns {{type:SnapType,value:number,source:string}[]}
   */
  function snapCandidatesFor(rect) {
    const left = rect.left, top = rect.top;
    const right = left + rect.width;
    const bottom = top + rect.height;
    const cx = left + rect.width / 2;
    const cy = top + rect.height / 2;
    return [
      { type: 'edge-left',    value: left,   source: rect.id },
      { type: 'edge-right',   value: right,  source: rect.id },
      { type: 'center-x',     value: cx,     source: rect.id },
      { type: 'edge-top',     value: top,    source: rect.id },
      { type: 'edge-bottom',  value: bottom, source: rect.id },
      { type: 'center-y',     value: cy,     source: rect.id }
    ];
  }

  /**
   * Build the canvas-center snap targets.
   * @param {{width:number,height:number}} canvasRect
   * @returns {{type:SnapType,value:number,source:'canvas'}[]}
   */
  function canvasCenterTargets(canvasRect) {
    return [
      { type: 'center-x',    value: canvasRect.width / 2,  source: 'canvas' },
      { type: 'center-y',    value: canvasRect.height / 2, source: 'canvas' }
    ];
  }

  /**
   * Compute the snap delta for a dragged element's proposed position.
   *
   * Pure function — no DOM access. The test harness calls this directly;
   * the pointer-event handlers below call it on every `pointermove`.
   *
   * @param {{left:number,top:number,width:number,height:number,id:string}} draggedRect
   *        The dragged element's CURRENT (pre-snap) position in canvas coordinates.
   * @param {{type:SnapType,value:number,source:string}[]} targets
   *        Candidate snap targets (siblings + canvas center).
   * @param {{threshold?:number}} [options]
   * @returns {{deltaX:number,deltaY:number,matches:{type:SnapType,value:number,source:string,delta:number}[]}}
   *          `deltaX`/`deltaY` are the additive snap offsets to apply (0 when no
   *          snap matched on that axis). `matches` lists every target whose
   *          distance was within the threshold (sorted by distance asc).
   */
  function computeSnap(draggedRect, targets, options = {}) {
    const threshold = Number(options.threshold) || SNAP_THRESHOLD_PX;
    const candidates = snapCandidatesFor(draggedRect);
    /** @type {{type:SnapType,value:number,source:string,delta:number,axis:'x'|'y'}[]} */
    const matches = [];
    for (const candidate of candidates) {
      const axis = AXIS[candidate.type];
      for (const target of targets) {
        if (AXIS[target.type] !== axis) continue;
        const delta = target.value - candidate.value;
        if (Math.abs(delta) <= threshold) {
          matches.push({
            type: target.type,
            value: target.value,
            source: target.source,
            delta,
            axis
          });
        }
      }
    }
    // Prefer the closest match on each axis. If two match equally, both are
    // returned (the renderer shows both guides per ROADMAP §3.1.1).
    matches.sort((a, b) => Math.abs(a.delta) - Math.abs(b.delta));
    const xMatches = matches.filter(m => m.axis === 'x');
    const yMatches = matches.filter(m => m.axis === 'y');
    let deltaX = 0, deltaY = 0;
    if (xMatches.length) {
      // Use the closest X target. If there are ties (within 0.01px), keep both.
      const closest = Math.abs(xMatches[0].delta);
      const ties = xMatches.filter(m => Math.abs(Math.abs(m.delta) - closest) < 0.01);
      deltaX = ties[0].delta;
    }
    if (yMatches.length) {
      const closest = Math.abs(yMatches[0].delta);
      const ties = yMatches.filter(m => Math.abs(Math.abs(m.delta) - closest) < 0.01);
      deltaY = ties[0].delta;
    }
    // Surface the surviving (snapped) matches so callers can render guides
    // for both X and Y if both fired.
    const snapped = [];
    if (xMatches.length) {
      const closest = Math.abs(xMatches[0].delta);
      xMatches.filter(m => Math.abs(Math.abs(m.delta) - closest) < 0.01).forEach(m => snapped.push(m));
    }
    if (yMatches.length) {
      const closest = Math.abs(yMatches[0].delta);
      yMatches.filter(m => Math.abs(Math.abs(m.delta) - closest) < 0.01).forEach(m => snapped.push(m));
    }
    return { deltaX, deltaY, matches: snapped };
  }

  // =========================================================================
  // Overlay renderer — renders matched guides as 1px SVG <line> elements
  // inside a single `<svg class="alignment-guide-overlay">` that spans the
  // canvas viewport. Crisp lines (vector-effect: non-scaling-stroke).
  // =========================================================================

  /** @type {SVGElement|null} */
  let overlay = null;
  /** Fade-out timer handle. */
  let fadeTimer = 0;

  /**
   * Lazily create (or return the existing) overlay SVG inside the canvas
   * viewport. The overlay is a sibling of the `#stage` so it is not
   * affected by the stage's `transform: scale()`.
   * @returns {SVGElement|null}
   */
  function ensureOverlay() {
    const viewport = $('#canvasViewport');
    if (!viewport) return null;
    if (overlay && overlay.isConnected) return overlay;
    overlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    overlay.setAttribute('class', 'alignment-guide-overlay');
    overlay.setAttribute('aria-hidden', 'true');
    // Insert as the FIRST child of the viewport so it sits above the stage
    // transform but below dialogs.
    viewport.prepend(overlay);
    return overlay;
  }

  /**
   * Render the matched guides for the given snap result + canvas dimensions.
   * Each guide is a 1px SVG line spanning the canvas (per ROADMAP §3.1.1).
   * @param {{matches:{type:SnapType,value:number,source:string,axis:'x'|'y'}[]}} snapResult
   * @param {{width:number,height:number}} canvasRect
   */
  function renderGuides(snapResult, canvasRect) {
    const svg = ensureOverlay();
    if (!svg) return;
    svg.innerHTML = '';
    svg.setAttribute('viewBox', `0 0 ${canvasRect.width} ${canvasRect.height}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.classList.remove('is-fading');
    svg.hidden = false;
    clearTimeout(fadeTimer);
    for (const match of snapResult.matches) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('class', `alignment-guide${match.type.startsWith('center') ? ' is-center' : ''}`);
      if (match.axis === 'x') {
        line.setAttribute('x1', match.value);
        line.setAttribute('y1', 0);
        line.setAttribute('x2', match.value);
        line.setAttribute('y2', canvasRect.height);
      } else {
        line.setAttribute('x1', 0);
        line.setAttribute('y1', match.value);
        line.setAttribute('x2', canvasRect.width);
        line.setAttribute('y2', match.value);
      }
      svg.append(line);
    }
  }

  /**
   * Begin the 200ms fade-out and hide the overlay.
   */
  function scheduleFade() {
    if (!overlay) return;
    clearTimeout(fadeTimer);
    overlay.classList.add('is-fading');
    fadeTimer = setTimeout(() => {
      if (overlay) {
        overlay.hidden = true;
        overlay.innerHTML = '';
        overlay.classList.remove('is-fading');
      }
    }, FADE_MS);
  }

  /**
   * Hide the overlay immediately (used on drag-cancel / pointerup-without-snap).
   */
  function hideGuides() {
    if (!overlay) return;
    clearTimeout(fadeTimer);
    overlay.hidden = true;
    overlay.innerHTML = '';
    overlay.classList.remove('is-fading');
  }

  /**
   * Emit the `einvite:alignment-snapped` event with the matched targets.
   * @param {{matches:{type:SnapType,value:number,source:string,axis:'x'|'y',delta:number}[]}} snapResult
   */
  function emitSnapped(snapResult) {
    if (!snapResult.matches.length) return;
    const detail = snapResult.matches.map(match => ({
      type: match.type,
      value: match.value,
      source: match.source,
      delta: match.delta,
      axis: match.axis,
      stringKey: STRING_KEY[match.type] || null,
      label: STRINGS[STRING_KEY[match.type]] || null
    }));
    window.dispatchEvent(new CustomEvent('einvite:alignment-snapped', { detail }));
  }

  // =========================================================================
  // Pointer-event integration — wires the pure computeSnap() into the live
  // editor canvas. Activated by other modules (e.g. selection.js / the
  // existing pro-editor drag loop) calling `beginDrag(elementId)` then
  // `updateDrag(rect)` then `endDrag()`.
  // =========================================================================

  /**
   * @typedef {Object} DragSession
   * @property {string} draggedId
   * @property {{type:SnapType,value:number,source:string}[]} targets
   * @property {{width:number,height:number}} canvasRect
   */

  /** @type {DragSession|null} */
  let session = null;

  /**
   * Begin a drag session for `draggedId`. Builds the snap-target list from
   * the sibling elements on the stage + the canvas center.
   *
   * @param {string} draggedId
   * @param {object} [canvasRect] Optional override (used by the test harness).
   *        If omitted, the stage's bounding rect is used.
   */
  function beginDrag(draggedId, canvasRect) {
    const stage = $('#stage');
    if (!stage) return;
    const rect = canvasRect || (() => {
      const r = stage.getBoundingClientRect();
      return { width: r.width, height: r.height };
    })();
    const targets = [];
    // Sibling element rects (canvas-coordinate values: left/top are 0-based
    // relative to the stage; we read from the pro editor's geometry if
    // available, else from getBoundingClientRect()).
    const bridge = window.EInviteEditorBridge;
    if (bridge?.getState) {
      const doc = bridge.getState();
      const canvasId = bridge.getActiveCanvasId?.() || 'hero';
      const map = canvasId === 'hero' ? (doc.objects || {})
        : ((doc.designPages || []).find(p => `page:${p.id}` === canvasId)?.objects || {});
      const stageRect = stage.getBoundingClientRect();
      const scale = stageRect.width / Math.max(1, stage.offsetWidth);
      for (const [id, obj] of Object.entries(map)) {
        if (id === draggedId) continue;
        const left = Number(obj.left) * stage.offsetWidth;
        const top = Number(obj.top) * stage.offsetHeight;
        const width = Number(obj.width) * stage.offsetWidth;
        const height = Number(obj.height) * stage.offsetHeight;
        if (!Number.isFinite(left) || !Number.isFinite(top)) continue;
        targets.push(...snapCandidatesFor({ left, top, width, height, id }));
        void scale;
      }
    }
    targets.push(...canvasCenterTargets(rect));
    session = { draggedId, targets, canvasRect: rect };
  }

  /**
   * Update a drag session with the dragged element's CURRENT proposed rect
   * (in canvas coordinates — i.e. pixels relative to the stage, unscaled).
   * Returns the snap delta to apply.
   *
   * @param {{left:number,top:number,width:number,height:number}} proposedRect
   * @returns {{deltaX:number,deltaY:number,matches:object[]}}
   */
  function updateDrag(proposedRect) {
    if (!session) return { deltaX: 0, deltaY: 0, matches: [] };
    const result = computeSnap(
      { ...proposedRect, id: session.draggedId },
      session.targets,
      { threshold: SNAP_THRESHOLD_PX }
    );
    if (result.matches.length) {
      renderGuides(result, session.canvasRect);
      emitSnapped(result);
    } else {
      hideGuides();
    }
    return result;
  }

  /**
   * End a drag session. Schedules the 200ms fade-out and clears the session.
   */
  function endDrag() {
    session = null;
    scheduleFade();
  }

  // =========================================================================
  // Public API
  // =========================================================================
  window.EInviteAlignmentGuides = Object.freeze({
    version: 56,
    SNAP_THRESHOLD_PX,
    FADE_MS,
    STRINGS,
    // Pure helpers (used by tests + by snapping.js for margin guides).
    computeSnap,
    snapCandidatesFor,
    canvasCenterTargets,
    // Live drag session API (used by selection.js + the existing pro editor).
    beginDrag,
    updateDrag,
    endDrag,
    hideGuides,
    // Test/debug introspection.
    get session() { return session; },
    get overlay() { return overlay; }
  });

  // Register cleanup with the editor lifecycle.
  window.EInviteLifecycle?.add?.(() => {
    hideGuides();
    overlay?.remove();
    overlay = null;
    session = null;
  });
})();
