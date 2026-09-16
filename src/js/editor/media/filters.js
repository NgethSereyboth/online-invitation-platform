/**
 * filters.js — Non-destructive image filters for EInvite studio (v56).
 *
 * Implements ROADMAP-v0.54-to-v1.0 §3.3.2 — brightness, contrast,
 * saturation, blur, grayscale sliders applied at render time via the CSS
 * `filter` property. For export, the same filter string is applied via
 * Canvas 2D `ctx.filter`.
 *
 * The filter state persists to the document model on the image element as:
 *
 *   filters: { brightness: 1.2, contrast: 1.1, saturate: 1.0, blur: 0, grayscale: 0 }
 *
 * Defaults:
 *   • brightness / contrast / saturate: 1.0 (100% — no change)
 *   • blur: 0 px
 *   • grayscale: 0 (0%)
 *
 * Ranges (sliders):
 *   • brightness: 0.2 — 3.0
 *   • contrast:   0.2 — 3.0
 *   • saturate:   0.0 — 3.0
 *   • blur:       0 — 20 px
 *   • grayscale:  0 — 1
 *
 * Idempotent: second-load is a no-op. Safe on non-designer routes.
 */
(() => {
  'use strict';

  if (window.EInviteImageFilters?.version >= 56) return;

  const api = { version: 56, destroy: null };

  const DEFAULTS = {
    brightness: 1,
    contrast: 1,
    saturate: 1,
    blur: 0,
    grayscale: 0,
  };

  /** Slider ranges — `[min, max, step]`. */
  const RANGES = {
    brightness: [0.2, 3.0, 0.05],
    contrast:   [0.2, 3.0, 0.05],
    saturate:   [0.0, 3.0, 0.05],
    blur:        [0,  20,  0.5],
    grayscale:   [0,  1,   0.01],
  };

  /** Bilingual labels for each slider. */
  const LABELS = {
    brightness: 'Brightness / ពន្លឺ',
    contrast:   'Contrast / កម្រិតពណ៌',
    saturate:   'Saturation / តិត្ថភាព',
    blur:       'Blur / ព្រិល',
    grayscale:  'Grayscale / ខ្មៅស',
  };

  /**
   * Serialise a filters model object into a CSS `filter:` string.
   * Returns an empty string if all values are at defaults (so toggling all
   * filters off produces no inline style pollution).
   * @param {object} filters Filter model object.
   * @returns {string} E.g. `brightness(1.2) contrast(1.1) saturate(1) blur(0px) grayscale(0)`.
   */
  function serializeToCSS(filters) {
    const f = normalize(filters);
    const parts = [];
    if (f.brightness !== 1) parts.push(`brightness(${f.brightness})`);
    if (f.contrast !== 1)   parts.push(`contrast(${f.contrast})`);
    if (f.saturate !== 1)   parts.push(`saturate(${f.saturate})`);
    if (f.blur > 0)         parts.push(`blur(${f.blur}px)`);
    if (f.grayscale > 0)    parts.push(`grayscale(${f.grayscale})`);
    return parts.join(' ');
  }

  /**
   * Serialise a filters model into the equivalent Canvas 2D `ctx.filter`
   * value (the same syntax CSS uses — `ctx.filter` accepts the same string).
   * Returns `'none'` if all defaults.
   */
  function serializeToCanvas(filters) {
    const css = serializeToCSS(filters);
    return css || 'none';
  }

  /** Apply filters directly to a DOM `<img>` element. */
  function applyToElement(imgEl, filters) {
    if (!imgEl) return;
    const css = serializeToCSS(filters);
    if (css) imgEl.style.filter = css;
    else imgEl.style.removeProperty('filter');
  }

  /** Normalize a partial filters object into a full one with defaults. */
  function normalize(filters) {
    const out = { ...DEFAULTS };
    if (!filters) return out;
    for (const key of Object.keys(DEFAULTS)) {
      const v = Number(filters[key]);
      if (Number.isFinite(v)) out[key] = v;
    }
    return out;
  }

  /**
   * Build the inspector panel for image filters.
   * @param {object} current Current filters model.
   * @param {function} onChange Called with the next filters object on each slider input.
   */
  function buildInspectorPanel(current, onChange) {
    const section = document.createElement('section');
    section.className = 'image-filters-panel';
    section.setAttribute('data-section', 'image-filters');
    const heading = document.createElement('h3');
    heading.textContent = 'Filters / តម្រង';
    section.appendChild(heading);

    const state = normalize(current);
    const sliders = {};
    for (const key of Object.keys(DEFAULTS)) {
      const [min, max, step] = RANGES[key];
      const wrap = document.createElement('div');
      wrap.className = 'effect-control';
      const lab = document.createElement('label');
      lab.className = 'effect-control-label';
      lab.textContent = LABELS[key];
      const input = document.createElement('input');
      input.type = 'range';
      input.min = String(min);
      input.max = String(max);
      input.step = String(step);
      input.value = String(state[key]);
      const readout = document.createElement('span');
      readout.className = 'filter-readout';
      readout.textContent = formatReadout(key, state[key]);
      input.addEventListener('input', () => {
        state[key] = Number(input.value);
        readout.textContent = formatReadout(key, state[key]);
        emit();
      });
      wrap.appendChild(lab);
      wrap.appendChild(input);
      wrap.appendChild(readout);
      section.appendChild(wrap);
      sliders[key] = input;
    }

    // Reset all button.
    const resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'effect-reset';
    resetBtn.textContent = 'Reset all / កំណត់ឡើងវិញ';
    resetBtn.addEventListener('click', () => {
      Object.assign(state, DEFAULTS);
      for (const [key, input] of Object.entries(sliders)) {
        input.value = String(state[key]);
      }
      // Update readouts.
      [...section.querySelectorAll('.filter-readout')].forEach((r, i) => {
        const key = Object.keys(DEFAULTS)[i];
        r.textContent = formatReadout(key, state[key]);
      });
      emit();
    });
    section.appendChild(resetBtn);

    function emit() {
      onChange({ ...state });
    }

    return section;
  }

  /** Format a slider's current value as a human-readable readout. */
  function formatReadout(key, value) {
    if (key === 'blur') return `${value.toFixed(1)}px`;
    if (key === 'grayscale') return `${Math.round(value * 100)}%`;
    return `${Math.round(value * 100)}%`;
  }

  // --- Exports --------------------------------------------------------------
  api.DEFAULTS = DEFAULTS;
  api.RANGES = RANGES;
  api.LABELS = LABELS;
  api.serializeToCSS = serializeToCSS;
  api.serializeToCanvas = serializeToCanvas;
  api.applyToElement = applyToElement;
  api.buildInspectorPanel = buildInspectorPanel;
  api.normalize = normalize;
  window.EInviteImageFilters = api;
})();
