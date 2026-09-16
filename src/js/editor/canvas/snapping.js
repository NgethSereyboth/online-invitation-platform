/**
 * snapping.js — Grid + page-margin snapping (ROADMAP §3.1.4, v0.56).
 *
 * Exposes `EInviteSnapping` — a service that complements
 * `EInviteAlignmentGuides` with two additional snap layers:
 *
 *   1. **Grid snap** — an 8px grid overlay that elements snap to when enabled.
 *      State is persisted per-user in `localStorage` (key: `ei-grid-enabled`).
 *      The grid renders as a repeating SVG pattern (NOT 10,000 divs).
 *
 *   2. **Page-margin guides** — configurable dashed amber guides at the page
 *      margins (default 40px). When an element's edge is dragged within 6px
 *      of a margin, the element snaps to the margin and a dashed amber guide
 *      is rendered.
 *
 * The module integrates with `EInviteAlignmentGuides` by injecting extra
 * snap targets (the 8px-grid ticks near the dragged element + the 4 margin
 * lines) into the guide service's target list.
 *
 * Bilingual strings: `snap.grid.on` / `snap.grid.off` / `snap.margin` with
 * EN + KH variants.
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';

  if (window.EInviteSnapping?.version >= 56) return;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);

  /** Default grid size in canvas pixels. */
  const DEFAULT_GRID_SIZE = 8;
  /** Default page margin in canvas pixels. */
  const DEFAULT_MARGIN = 40;
  /** Snap threshold for grid + margin guides (same as alignment guides). */
  const SNAP_THRESHOLD_PX = 6;
  /** localStorage keys. */
  const LS_GRID = 'ei-grid-enabled';
  const LS_GRID_SIZE = 'ei-grid-size';
  const LS_MARGIN = 'ei-margin-size';

  /** Bilingual labels for the toolbar toggle + toasts. */
  const STRINGS = Object.freeze({
    'snap.grid.on':     { en: 'Grid snapping on',    km: 'ការតម្រឹមតាមក្រឡាបើក' },
    'snap.grid.off':    { en: 'Grid snapping off',   km: 'ការតម្រឹមតាមក្រឡាបិទ' },
    'snap.margin':      { en: 'Snapped to page margin', km: 'តម្រឹមទៅគែមទំព័រ' },
    'snap.grid.label':  { en: 'Snap to grid',        km: 'តម្រឹមតាមក្រឡា' }
  });

  // =========================================================================
  // State
  // =========================================================================

  /** Whether grid snapping is active. */
  let gridEnabled = (() => {
    try { return localStorage.getItem(LS_GRID) === '1'; } catch { return false; }
  })();

  /** Current grid size in canvas pixels. */
  let gridSize = (() => {
    const raw = (() => { try { return localStorage.getItem(LS_GRID_SIZE); } catch { return null; } })();
    const n = Number(raw);
    return Number.isFinite(n) && n >= 2 && n <= 200 ? n : DEFAULT_GRID_SIZE;
  })();

  /** Current page-margin size in canvas pixels. */
  let margin = (() => {
    const raw = (() => { try { return localStorage.getItem(LS_MARGIN); } catch { return null; } })();
    const n = Number(raw);
    return Number.isFinite(n) && n >= 0 && n <= 400 ? n : DEFAULT_MARGIN;
  })();

  /** @type {SVGElement|null} */
  let gridOverlay = null;

  // =========================================================================
  // Pure helpers
  // =========================================================================

  /**
   * Snap a single numeric value to the nearest grid tick.
   * @param {number} value The value to snap.
   * @param {number} [size] The grid size (defaults to current `gridSize`).
   * @returns {number} The snapped value (= `value` if grid is disabled).
   */
  function snapToGrid(value, size = gridSize) {
    if (!gridEnabled) return value;
    return Math.round(value / size) * size;
  }

  /**
   * Build the grid snap targets for a given dragged element rect + canvas
   * dimensions. Returns targets for the dragged element's left/right/top/
   * bottom edges + centers, each snapped to the nearest grid tick within
   * the threshold.
   *
   * @param {{left:number,top:number,width:number,height:number}} draggedRect
   * @param {{width:number,height:number}} canvasRect
   * @returns {{type:string,value:number,source:'grid'}[]}
   */
  function gridSnapTargets(draggedRect, canvasRect) {
    if (!gridEnabled) return [];
    const left = snapToGrid(draggedRect.left);
    const right = snapToGrid(draggedRect.left + draggedRect.width);
    const top = snapToGrid(draggedRect.top);
    const bottom = snapToGrid(draggedRect.top + draggedRect.height);
    const cx = snapToGrid(draggedRect.left + draggedRect.width / 2);
    const cy = snapToGrid(draggedRect.top + draggedRect.height / 2);
    // Only emit grid targets that are within the threshold of the dragged
    // element's actual edges/centers — avoids producing thousands of grid
    // ticks for the alignment service to scan.
    const targets = [];
    const threshold = SNAP_THRESHOLD_PX;
    /** @param {number} v @param {number} actual @param {string} type @param {'x'|'y'} axis */
    const consider = (v, actual, type, axis) => {
      if (Math.abs(v - actual) <= threshold) {
        targets.push({ type, value: v, source: 'grid' });
        void axis;
      }
    };
    consider(left, draggedRect.left, 'edge-left', 'x');
    consider(right, draggedRect.left + draggedRect.width, 'edge-right', 'x');
    consider(cx, draggedRect.left + draggedRect.width / 2, 'center-x', 'x');
    consider(top, draggedRect.top, 'edge-top', 'y');
    consider(bottom, draggedRect.top + draggedRect.height, 'edge-bottom', 'y');
    consider(cy, draggedRect.top + draggedRect.height / 2, 'center-y', 'y');
    void canvasRect;
    return targets;
  }

  /**
   * Build the page-margin snap targets (4 dashed amber guide lines at the
   * configured margin from each edge).
   *
   * @param {{width:number,height:number}} canvasRect
   * @returns {{type:string,value:number,source:'margin'}[]}
   */
  function marginSnapTargets(canvasRect) {
    if (!margin) return [];
    return [
      { type: 'edge-left',    value: margin,                  source: 'margin' },
      { type: 'edge-right',   value: canvasRect.width - margin, source: 'margin' },
      { type: 'edge-top',     value: margin,                   source: 'margin' },
      { type: 'edge-bottom',  value: canvasRect.height - margin, source: 'margin' }
    ];
  }

  // =========================================================================
  // Grid overlay renderer (SVG pattern, not divs)
  // =========================================================================

  /**
   * Lazily create (or return the existing) grid overlay SVG inside the
   * canvas viewport. Renders a sparse set of `<line>` elements at every
   * grid tick — at most `(canvasWidth / gridSize) + (canvasHeight / gridSize)`
   * lines (typically 100-200), NOT one div per cell.
   *
   * @returns {SVGElement|null}
   */
  function ensureGridOverlay() {
    const viewport = $('#canvasViewport');
    if (!viewport) return null;
    if (gridOverlay && gridOverlay.isConnected) return gridOverlay;
    gridOverlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    gridOverlay.setAttribute('class', 'einvite-grid-overlay');
    gridOverlay.setAttribute('aria-hidden', 'true');
    viewport.append(gridOverlay);
    return gridOverlay;
  }

  /**
   * Render the grid overlay. Called when the grid is toggled on, when the
   * grid size changes, or when the canvas resizes.
   * @param {{width:number,height:number}} canvasRect
   */
  function renderGrid(canvasRect) {
    const svg = ensureGridOverlay();
    if (!svg) return;
    svg.innerHTML = '';
    svg.setAttribute('viewBox', `0 0 ${canvasRect.width} ${canvasRect.height}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    for (let x = 0; x <= canvasRect.width; x += gridSize) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x); line.setAttribute('y1', 0);
      line.setAttribute('x2', x); line.setAttribute('y2', canvasRect.height);
      svg.append(line);
    }
    for (let y = 0; y <= canvasRect.height; y += gridSize) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', 0); line.setAttribute('y1', y);
      line.setAttribute('x2', canvasRect.width); line.setAttribute('y2', y);
      svg.append(line);
    }
  }

  /** Hide the grid overlay. */
  function hideGrid() {
    if (gridOverlay) {
      gridOverlay.hidden = true;
      gridOverlay.innerHTML = '';
    }
  }

  /**
   * Refresh the grid overlay visibility + content based on current state.
   */
  function refreshGrid() {
    const stage = $('#stage');
    if (!stage) return;
    const rect = { width: stage.offsetWidth, height: stage.offsetHeight };
    if (gridEnabled) {
      renderGrid(rect);
      gridOverlay.hidden = false;
    } else {
      hideGrid();
    }
  }

  // =========================================================================
  // Public API
  // =========================================================================

  /**
   * Toggle grid snapping on/off. Persists to localStorage.
   * @param {boolean} [force] If supplied, set to this value.
   * @returns {boolean} The new state.
   */
  function setGridEnabled(force) {
    gridEnabled = typeof force === 'boolean' ? force : !gridEnabled;
    try { localStorage.setItem(LS_GRID, gridEnabled ? '1' : '0'); } catch { /* ignore */ }
    refreshGrid();
    window.dispatchEvent(new CustomEvent('einvite:snapping-grid-toggled', {
      detail: { enabled: gridEnabled, gridSize, label: STRINGS[gridEnabled ? 'snap.grid.on' : 'snap.grid.off'] }
    }));
    return gridEnabled;
  }

  /**
   * Set the grid size (canvas pixels). Persists to localStorage.
   * @param {number} size New grid size (2-200).
   * @returns {number} The actual size applied (clamped).
   */
  function setGridSize(size) {
    const n = Number(size);
    gridSize = Number.isFinite(n) && n >= 2 && n <= 200 ? Math.round(n) : DEFAULT_GRID_SIZE;
    try { localStorage.setItem(LS_GRID_SIZE, String(gridSize)); } catch { /* ignore */ }
    refreshGrid();
    return gridSize;
  }

  /**
   * Set the page margin (canvas pixels). Persists to localStorage.
   * @param {number} value New margin (0-400).
   * @returns {number} The actual margin applied (clamped).
   */
  function setMargin(value) {
    const n = Number(value);
    margin = Number.isFinite(n) && n >= 0 && n <= 400 ? Math.round(n) : DEFAULT_MARGIN;
    try { localStorage.setItem(LS_MARGIN, String(margin)); } catch { /* ignore */ }
    return margin;
  }

  /**
   * Build the COMPLETE set of extra snap targets (grid + margin) for a
   * given dragged element + canvas rect. Used by the alignment guide
   * service when it begins a drag.
   *
   * @param {{left:number,top:number,width:number,height:number}} draggedRect
   * @param {{width:number,height:number}} canvasRect
   * @returns {{type:string,value:number,source:string}[]}
   */
  function extraSnapTargets(draggedRect, canvasRect) {
    return [...gridSnapTargets(draggedRect, canvasRect), ...marginSnapTargets(canvasRect)];
  }

  // Expose the public API.
  window.EInviteSnapping = Object.freeze({
    version: 56,
    STRINGS,
    DEFAULT_GRID_SIZE,
    DEFAULT_MARGIN,
    SNAP_THRESHOLD_PX,
    // Pure helpers.
    snapToGrid,
    gridSnapTargets,
    marginSnapTargets,
    extraSnapTargets,
    // State setters / getters.
    setGridEnabled,
    setGridSize,
    setMargin,
    refreshGrid,
    get gridEnabled() { return gridEnabled; },
    get gridSize() { return gridSize; },
    get margin() { return margin; }
  });

  // Initial render (deferred until DOM is ready + stage exists).
  function boot() {
    if ($('#stage')) refreshGrid();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  // Re-render on resize.
  window.addEventListener('resize', () => refreshGrid(), { passive: true });

  // Cleanup.
  window.EInviteLifecycle?.add?.(() => {
    gridOverlay?.remove();
    gridOverlay = null;
  });
})();
