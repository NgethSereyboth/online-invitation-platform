/**
 * image.js — Image masking (shape crops) for EInvite studio (v56).
 *
 * Implements ROADMAP-v0.54-to-v1.0 §3.3.3 — 6 preset masks: none, circle,
 * rounded-4, rounded-12, heart, star. Applied via CSS `clip-path`.
 *
 * Model: `mask: 'none' | 'circle' | 'rounded-4' | 'rounded-12' | 'heart' | 'star'`
 *
 * Stretch goal (deferred per the roadmap): custom SVG path mask upload.
 *
 * Idempotent: second-load is a no-op. Safe on non-designer routes.
 */
(() => {
  'use strict';

  if (window.EInviteImageMask?.version >= 56) return;

  const api = { version: 56, destroy: null };

  /** Preset mask definitions. Each `value` is a valid `clip-path` CSS string. */
  const MASKS = [
    {
      id: 'none', label: 'None / គ្មាន',
      value: 'none',
      preview: '',
    },
    {
      id: 'circle', label: 'Circle / រង្វង់',
      // A 50% radius circle centered in the element box.
      value: 'circle(50% at 50% 50%)',
      preview: 'border-radius: 50%;',
    },
    {
      id: 'rounded-4', label: 'Rounded 4 / មូល 4',
      value: 'inset(0 round 4px)',
      preview: 'border-radius: 4px;',
    },
    {
      id: 'rounded-12', label: 'Rounded 12 / មូល 12',
      value: 'inset(0 round 12px)',
      preview: 'border-radius: 12px;',
    },
    {
      id: 'heart', label: 'Heart / បេះដូង',
      // A heart-shaped SVG path. The path is written against a 100x100 box
      // and uses `path()` (supported in Chrome 88+, Firefox 71+, Safari 13.1+).
      value: 'path("M50 88 C 35 70 5 55 5 32 C 5 17 17 5 32 5 C 41 5 47 11 50 18 C 53 11 59 5 68 5 C 83 5 95 17 95 32 C 95 55 65 70 50 88 Z")',
      preview: 'clip-path: path("M50 88 C 35 70 5 55 5 32 C 5 17 17 5 32 5 C 41 5 47 11 50 18 C 53 11 59 5 68 5 C 83 5 95 17 95 32 C 95 55 65 70 50 88 Z");',
    },
    {
      id: 'star', label: 'Star / ផ្កាយ',
      // A 5-point star centered in a 100x100 box.
      value: 'path("M50 5 L61 38 L96 38 L68 59 L79 92 L50 72 L21 92 L32 59 L4 38 L39 38 Z")',
      preview: 'clip-path: path("M50 5 L61 38 L96 38 L68 59 L79 92 L50 72 L21 92 L32 59 L4 38 L39 38 Z");',
    },
  ];

  /**
   * Look up a mask preset by id. Returns the preset object or null.
   */
  function getMask(id) {
    return MASKS.find(m => m.id === id) || null;
  }

  /**
   * Get the CSS `clip-path` value for a mask id. Returns `'none'` for
   * unknown ids (so the renderer always produces a valid value).
   */
  function serializeToCSS(maskId) {
    const mask = getMask(maskId);
    return mask ? mask.value : 'none';
  }

  /** Apply a mask to a DOM element by setting `clip-path`. */
  function applyToElement(el, maskId) {
    if (!el) return;
    const value = serializeToCSS(maskId);
    if (value === 'none') {
      el.style.clipPath = 'none';
      el.style.removeProperty('clip-path');
    } else {
      el.style.clipPath = value;
    }
  }

  /**
   * Build the inspector panel for mask selection.
   * @param {string} current Current mask id (or null/empty).
   * @param {function} onChange Called with the next mask id.
   */
  function buildInspectorPanel(current, onChange) {
    const section = document.createElement('section');
    section.className = 'image-mask-panel';
    section.setAttribute('data-section', 'image-mask');
    const heading = document.createElement('h3');
    heading.textContent = 'Mask / រូបរាង';
    section.appendChild(heading);

    const grid = document.createElement('div');
    grid.className = 'mask-preset-grid';
    MASKS.forEach(mask => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'mask-preset-chip';
      if (current === mask.id) chip.classList.add('active');
      chip.dataset.mask = mask.id;
      chip.setAttribute('aria-label', mask.label);
      chip.setAttribute('title', mask.label);
      // Preview — a 32x32 box with the mask applied (where possible).
      const preview = document.createElement('span');
      preview.className = 'mask-preview';
      preview.setAttribute('aria-hidden', 'true');
      if (mask.preview) preview.style.cssText = mask.preview;
      else if (mask.id === 'none') preview.style.cssText = 'border: 1px dashed currentColor;';
      chip.appendChild(preview);
      const label = document.createElement('span');
      label.className = 'mask-label';
      label.textContent = mask.label;
      chip.appendChild(label);
      chip.addEventListener('click', () => {
        [...grid.children].forEach(c => c.classList.toggle('active', c.dataset.mask === mask.id));
        onChange(mask.id);
      });
      grid.appendChild(chip);
    });
    section.appendChild(grid);

    return section;
  }

  // --- Exports --------------------------------------------------------------
  api.MASKS = MASKS;
  api.getMask = getMask;
  api.serializeToCSS = serializeToCSS;
  api.applyToElement = applyToElement;
  api.buildInspectorPanel = buildInspectorPanel;
  window.EInviteImageMask = api;
})();
