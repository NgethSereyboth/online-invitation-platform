/**
 * effects.js — Text effects (shadow, outline, gradient) for EInvite studio (v56).
 *
 * Implements ROADMAP-v0.54-to-v1.0 §3.2.2 — text elements can have:
 *
 *   • Drop shadow — color, blur, offset-x, offset-y (CSS `text-shadow`).
 *   • Outline — color + width 1–8px (`-webkit-text-stroke`).
 *   • Gradient fill — two-stop linear gradient at an angle, 8 presets + custom
 *     (`background-clip: text`).
 *
 * The effects persist to the document model as a plain object on the text
 * element:
 *
 *   {
 *     shadow:   { color, blur, dx, dy },
 *     outline:  { color, width },
 *     gradient: { from, to, angle }
 *   }
 *
 * The module exposes:
 *
 *   • `TextEffects.serializeToCSS(effects)` — pure function turning the model
 *     object into a CSS string (`text-shadow`, `-webkit-text-stroke`,
 *     `background: linear-gradient(...); background-clip: text;`). This is
 *     called by the canvas renderer whenever a text element is (re)drawn.
 *   • `TextEffects.buildInspectorPanel(targetEl, current, onChange)` — builds
 *     the inspector DOM for the active text element and calls `onChange`
 *     with the next effects object on every slider / picker change.
 *   • `TextEffects.applyToElement(node, effects)` — convenience wrapper that
 *     writes the serialised CSS to a DOM node.
 *   • `TextEffects.presets` — the 8 gradient presets (exported for tests).
 *
 * Idempotent: second-load is a no-op. Safe on non-designer routes.
 */
(() => {
  'use strict';

  if (window.EInviteTextEffects?.version >= 56) return;

  const api = { version: 56, destroy: null };

  // --- Defaults + presets ---------------------------------------------------
  const DEFAULT_EFFECTS = {
    shadow: { color: 'rgba(0,0,0,0.5)', blur: 4, dx: 0, dy: 2 },
    outline: { color: '#000000', width: 0 },
    gradient: { from: '', to: '', angle: 90 },
  };

  /** 8 gradient presets — color pairs (from, to) at fixed angles. */
  const GRADIENT_PRESETS = [
    { name: 'Sunset',  from: '#ff7e5f', to: '#feb47b', angle: 90 },
    { name: 'Ocean',   from: '#2193b0', to: '#6dd5ed', angle: 90 },
    { name: 'Purple',  from: '#834d9b', to: '#d04ed6', angle: 90 },
    { name: 'Gold',    from: '#d4af37', to: '#f9d976', angle: 90 },
    { name: 'Forest',  from: '#134e5e', to: '#71b280', angle: 90 },
    { name: 'Rose',    from: '#ff6e7f', to: '#bfe9ff', angle: 90 },
    { name: 'Khmer',   from: '#c1272d', to: '#fbb034', angle: 90 }, // Cambodian flag colors
    { name: 'Mono',    from: '#444444', to: '#888888', angle: 90 },
  ];

  // --- Pure serialiser ------------------------------------------------------
  /**
   * Serialise an effects object into a CSS style string.
   *
   * Effects that are unset (zero width, empty gradient colors) produce no CSS
   * so the underlying text renders cleanly. Returns an object of CSS
   * property → value so callers can merge into existing styles.
   *
   * @param {object} effects Effects model object (may be partial).
   * @returns {object} Map of CSS property → value (empty strings omitted).
   */
  function serializeToCSS(effects) {
    const css = {};
    if (!effects || typeof effects !== 'object') return css;
    const shadow = effects.shadow;
    if (shadow && (shadow.blur > 0 || shadow.dx !== 0 || shadow.dy !== 0)) {
      const color = shadow.color || 'rgba(0,0,0,0.5)';
      css['text-shadow'] = `${shadow.dx || 0}px ${shadow.dy || 0}px ${shadow.blur || 0}px ${color}`;
    }
    const outline = effects.outline;
    if (outline && outline.width > 0) {
      css['-webkit-text-stroke'] = `${outline.width}px ${outline.color || '#000000'}`;
      // Standard property (Firefox, future specs).
      css['text-stroke'] = `${outline.width}px ${outline.color || '#000000'}`;
    }
    const grad = effects.gradient;
    if (grad && grad.from && grad.to) {
      const angle = Number.isFinite(grad.angle) ? grad.angle : 90;
      css['background'] = `linear-gradient(${angle}deg, ${grad.from}, ${grad.to})`;
      css['-webkit-background-clip'] = 'text';
      css['background-clip'] = 'text';
      css['color'] = 'transparent';
      // Required for Firefox to actually clip the background to the text glyphs.
      css['-webkit-text-fill-color'] = 'transparent';
    }
    return css;
  }

  /**
   * Apply an effects model object directly to a DOM node by writing the
   * serialised CSS into its inline `style` attribute. Existing inline styles
   * are preserved except for the effect-controlled properties.
   */
  function applyToElement(node, effects) {
    if (!node) return;
    const css = serializeToCSS(effects);
    // Clear previously-applied effect properties first so toggling an effect
    // off actually removes it.
    const effectProps = [
      'text-shadow', '-webkit-text-stroke', 'text-stroke',
      'background', '-webkit-background-clip', 'background-clip',
      '-webkit-text-fill-color',
    ];
    effectProps.forEach(prop => node.style.removeProperty(prop));
    // If gradient was on, also reset color back to its inherited value.
    if (!css.color) node.style.removeProperty('color');
    Object.entries(css).forEach(([prop, value]) => {
      node.style.setProperty(prop, value);
    });
  }

  // --- Inspector panel ------------------------------------------------------
  /**
   * Build the inspector panel DOM for the active text element's effects.
   *
   * @param {object} current Current effects model (may be {}).
   * @param {function} onChange Called with the next effects object on each
   *   slider / picker change.
   * @returns {HTMLElement} The inspector section element (already mounted
   *   by the caller).
   */
  function buildInspectorPanel(current, onChange) {
    const section = document.createElement('section');
    section.className = 'text-effects-panel';
    section.setAttribute('data-section', 'text-effects');
    const state = normalize(current);

    // Heading (bilingual).
    const heading = document.createElement('h3');
    heading.textContent = 'Text effects / បែបផែនអក្សរ';
    section.appendChild(heading);

    // --- Shadow subgroup ---
    const shadowGroup = document.createElement('div');
    shadowGroup.className = 'effect-group';
    shadowGroup.innerHTML = '<label class="effect-label">Shadow / ស្រមោល</label>';
    const shadowColor = slider(shadowGroup, 'Color', 'color', state.shadow.color, 'color');
    const shadowBlur  = slider(shadowGroup, 'Blur', 'range', state.shadow.blur, 0, 24, 1);
    const shadowDx    = slider(shadowGroup, 'Offset X', 'range', state.shadow.dx, -24, 24, 1);
    const shadowDy    = slider(shadowGroup, 'Offset Y', 'range', state.shadow.dy, -24, 24, 1);
    section.appendChild(shadowGroup);

    // --- Outline subgroup ---
    const outlineGroup = document.createElement('div');
    outlineGroup.className = 'effect-group';
    outlineGroup.innerHTML = '<label class="effect-label">Outline / ខ្សែព្រំ</label>';
    const outlineColor = slider(outlineGroup, 'Color', 'color', state.outline.color, 'color');
    const outlineWidth = slider(outlineGroup, 'Width (1-8)', 'range', state.outline.width, 0, 8, 1);
    section.appendChild(outlineGroup);

    // --- Gradient subgroup ---
    const gradGroup = document.createElement('div');
    gradGroup.className = 'effect-group';
    gradGroup.innerHTML = '<label class="effect-label">Gradient / ម៉្យាងពណ៌</label>';
    // Preset chips.
    const presetRow = document.createElement('div');
    presetRow.className = 'gradient-presets';
    GRADIENT_PRESETS.forEach((preset, idx) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'gradient-chip';
      chip.style.background = `linear-gradient(90deg, ${preset.from}, ${preset.to})`;
      chip.title = preset.name;
      chip.setAttribute('aria-label', `Gradient preset ${preset.name}`);
      chip.addEventListener('click', () => {
        state.gradient = { from: preset.from, to: preset.to, angle: preset.angle };
        gradFrom.value = preset.from;
        gradTo.value = preset.to;
        gradAngle.value = String(preset.angle);
        emit();
      });
      presetRow.appendChild(chip);
    });
    gradGroup.appendChild(presetRow);
    const gradFrom  = slider(gradGroup, 'From', 'color', state.gradient.from, 'color');
    const gradTo    = slider(gradGroup, 'To', 'color', state.gradient.to, 'color');
    const gradAngle = slider(gradGroup, 'Angle (°)', 'range', state.gradient.angle, 0, 360, 1);
    section.appendChild(gradGroup);

    // Reset button.
    const resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'effect-reset';
    resetBtn.textContent = 'Reset all / កំណត់ឡើងវិញ';
    resetBtn.addEventListener('click', () => {
      state.shadow = { ...DEFAULT_EFFECTS.shadow, blur: 0, dx: 0, dy: 0 };
      state.outline = { color: '#000000', width: 0 };
      state.gradient = { from: '', to: '', angle: 90 };
      shadowColor.value = state.shadow.color;
      shadowBlur.value = String(state.shadow.blur);
      shadowDx.value = String(state.shadow.dx);
      shadowDy.value = String(state.shadow.dy);
      outlineColor.value = state.outline.color;
      outlineWidth.value = String(state.outline.width);
      gradFrom.value = state.gradient.from;
      gradTo.value = state.gradient.to;
      gradAngle.value = String(state.gradient.angle);
      emit();
    });
    section.appendChild(resetBtn);

    // Wire slider change events.
    bind(shadowColor, 'input', () => { state.shadow.color = shadowColor.value; emit(); });
    bind(shadowBlur,  'input', () => { state.shadow.blur  = Number(shadowBlur.value);  emit(); });
    bind(shadowDx,    'input', () => { state.shadow.dx    = Number(shadowDx.value);    emit(); });
    bind(shadowDy,    'input', () => { state.shadow.dy    = Number(shadowDy.value);    emit(); });
    bind(outlineColor,'input', () => { state.outline.color = outlineColor.value;      emit(); });
    bind(outlineWidth,'input', () => { state.outline.width = Number(outlineWidth.value); emit(); });
    bind(gradFrom,    'input', () => { state.gradient.from = gradFrom.value;          emit(); });
    bind(gradTo,      'input', () => { state.gradient.to = gradTo.value;              emit(); });
    bind(gradAngle,   'input', () => { state.gradient.angle = Number(gradAngle.value);emit(); });

    function emit() {
      // Deep clone so callers see a fresh object (no shared references).
      const next = JSON.parse(JSON.stringify(state));
      // Drop empty gradient so unset state round-trips.
      if (!next.gradient.from && !next.gradient.to) next.gradient = { from: '', to: '', angle: next.gradient.angle };
      onChange(next);
    }

    return section;
  }

  /** Build a labelled slider / color input. Returns the input element. */
  function slider(parent, label, type, value, min, max, step) {
    const wrap = document.createElement('div');
    wrap.className = 'effect-control';
    const lab = document.createElement('label');
    lab.className = 'effect-control-label';
    lab.textContent = label;
    const input = document.createElement('input');
    input.type = type;
    if (type === 'range') {
      input.min = String(min); input.max = String(max); input.step = String(step);
    }
    input.value = value == null ? '' : String(value);
    wrap.appendChild(lab);
    wrap.appendChild(input);
    parent.appendChild(wrap);
    return input;
  }

  function bind(target, type, fn) {
    target.addEventListener(type, fn);
  }

  /** Normalize a partial effects object into a full one with defaults. */
  function normalize(effects) {
    const out = JSON.parse(JSON.stringify(DEFAULT_EFFECTS));
    if (!effects) return out;
    if (effects.shadow) {
      out.shadow = { ...out.shadow, ...effects.shadow };
    }
    if (effects.outline) {
      out.outline = { ...out.outline, ...effects.outline };
    }
    if (effects.gradient) {
      out.gradient = { ...out.gradient, ...effects.gradient };
    }
    return out;
  }

  // --- Exports --------------------------------------------------------------
  api.serializeToCSS = serializeToCSS;
  api.applyToElement = applyToElement;
  api.buildInspectorPanel = buildInspectorPanel;
  api.normalize = normalize;
  api.presets = GRADIENT_PRESETS;
  api.DEFAULT_EFFECTS = DEFAULT_EFFECTS;
  window.EInviteTextEffects = api;
})();
