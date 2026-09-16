/**
 * typography.js — Text-on-a-curve for EInvite studio (v56).
 *
 * Implements ROADMAP-v0.54-to-v1.0 §3.2.3 — a text element can be laid out
 * along a circular arc via SVG `<textPath>`.
 *
 *   • Inspector slider goes from -180° to +180°.
 *   • 0° = straight (no path used).
 *   • Positive = arc upward (smile ⟘).
 *   • Negative = arc downward (frown ⟄).
 *
 * The arc path is computed from the text element's width — radius derived
 * from chord length + chosen arc angle. See `arcPath()` for the geometry.
 *
 * Khmer caveat: complex shaping (subjoiners, coeng) sometimes breaks under
 * `<textPath>`. If the active font family is a Khmer font, the inspector
 * surfaces a warning that curve support is limited. The user can still
 * apply it, but they get a heads-up.
 *
 * Idempotent: second-load is a no-op. Safe on non-designer routes — pure
 * helpers (`arcPath`, `svgForCurve`) are exposed for unit testing.
 */
(() => {
  'use strict';

  if (window.EInviteTypography?.version >= 56) return;

  const api = { version: 56, destroy: null };

  /** Khmer font family substrings (lower-cased) that trigger the warning. */
  const KHMER_FONT_HINTS = ['khmer', 'battambang', 'siemreap', 'nimbus', 'noto sans khmer', 'kantumruy', 'bayon'];

  /**
   * Compute the SVG arc path string for a text element of `width` at `angle`.
   *
   * Convention:
   *   • 0° → return null (no curve; caller renders straight text).
   *   • Positive angle → arc upward (smile): the path dips down in the middle.
   *   • Negative angle → arc downward (frown): the path rises in the middle.
   *
   * Geometry: the text element's bounding box has width W and an effective
   * chord length W. Given the arc angle θ (in degrees), the circle radius is
   *   r = (W / 2) / sin(θ/2)
   * and the sagitta (rise/fall of the arc above/below the chord) is
   *   s = r − r·cos(θ/2) = r(1 − cos(θ/2))
   *
   * The path is drawn left-to-right with the arc starting at the left edge
   * of the text element. We sweep in the direction that puts the text on the
   * outside of the arc (so it reads correctly).
   *
   * @param {number} width Element width in px.
   * @param {number} angle -180 to 180 (degrees).
   * @returns {{d: string, radius: number, sagitta: number, sweep: 0|1}|null}
   */
  function arcPath(width, angle) {
    const w = Number(width);
    const a = Number(angle);
    if (!Number.isFinite(w) || w <= 0) return null;
    if (!Number.isFinite(a) || Math.abs(a) < 0.001) return null;
    const absA = Math.min(180, Math.abs(a));
    const halfRad = (absA / 2) * Math.PI / 180;
    // Cap radius at a sane value when the angle is very small to avoid
    // enormous arc paths (text on a near-straight arc looks identical to
    // straight text, so we let the caller render straight instead).
    if (absA < 1) return null;
    const radius = Math.max(1, (w / 2) / Math.sin(halfRad));
    const sagitta = radius * (1 - Math.cos(halfRad));
    // Start point at (0, sagitta) so the arc dips above the baseline for
    // upward arcs (positive angle) and below for downward (negative).
    // SVG y-axis grows downward, so a positive-angle (smile / upward arc)
    // path needs its midpoint at the BOTTOM, i.e. with the control dip DOWN.
    // We accomplish this by choosing sweep-flag appropriately.
    const x0 = 0, y0 = 0; // chord start at origin (caller translates).
    const x1 = w, y1 = 0; // chord end.
    // Sweep flag 1 = clockwise in user-space (downward arc). For positive
    // angle (smile, arc upward) we want the path to dip below the chord in
    // the middle — so we use sweep flag 1 (large arc 0, sweep 1).
    // For negative angle (frown, arc downward) the path rises above the
    // chord in the middle — sweep flag 0.
    const sweep = a > 0 ? 1 : 0;
    const d = `M ${x0} ${y0} A ${radius} ${radius} 0 0 ${sweep} ${x1} ${y1}`;
    return { d, radius, sagitta, sweep };
  }

  /**
   * Build the SVG markup needed to render `text` along an arc.
   * Returns an SVG element ready to be appended to the text node's container.
   *
   * @param {object} opts { text, fontFamily, fontSize, fill, width, angle }
   * @returns {SVGSVGElement|null} SVG element with a `<path>` + `<textPath>`,
   *   or null if `angle` is 0 (caller should render straight text instead).
   */
  function svgForCurve(opts) {
    if (!opts || !opts.text) return null;
    const width = opts.width || 200;
    const angle = Number(opts.angle) || 0;
    const path = arcPath(width, angle);
    if (!path) return null;
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('xmlns', svgNS);
    svg.setAttribute('viewBox', `0 ${path.sweep === 1 ? -path.sagitta : 0} ${width} ${path.sagitta + (opts.fontSize || 16)}`);
    svg.setAttribute('width', String(width));
    svg.setAttribute('height', String(path.sagitta + (opts.fontSize || 16) + 4));
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    const defs = document.createElementNS(svgNS, 'defs');
    const pathEl = document.createElementNS(svgNS, 'path');
    pathEl.setAttribute('id', `curve-${Math.random().toString(36).slice(2, 9)}`);
    pathEl.setAttribute('d', path.d);
    pathEl.setAttribute('fill', 'none');
    defs.appendChild(pathEl);
    svg.appendChild(defs);

    const text = document.createElementNS(svgNS, 'text');
    text.setAttribute('font-family', opts.fontFamily || 'inherit');
    text.setAttribute('font-size', String(opts.fontSize || 16));
    text.setAttribute('fill', opts.fill || '#000000');
    // `startOffset` of 50% + `text-anchor=middle` centres the text on the path.
    text.setAttribute('text-anchor', 'middle');
    const textPath = document.createElementNS(svgNS, 'textPath');
    textPath.setAttribute('href', `#${pathEl.id}`);
    textPath.setAttribute('startOffset', '50%');
    textPath.textContent = opts.text;
    text.appendChild(textPath);
    svg.appendChild(text);
    svg.dataset.curveAngle = String(angle);
    svg.dataset.curveRadius = String(path.radius);
    svg.dataset.curveSagitta = String(path.sagitta.toFixed(2));
    return svg;
  }

  /**
   * Returns true if the given font family name looks like a Khmer font.
   * Used by the inspector to surface the curve-support warning.
   */
  function isKhmerFont(fontFamily) {
    const f = String(fontFamily || '').toLowerCase();
    if (!f) return false;
    return KHMER_FONT_HINTS.some(hint => f.includes(hint));
  }

  // --- Inspector panel ------------------------------------------------------
  /**
   * Build the inspector panel section for text-on-a-curve.
   * @param {object} current Current typography model — `{ curve: { angle } }` or `{}`.
   * @param {function} onChange Called with the next state on slider change.
   * @param {object} meta Extra context — `{ fontFamily }` so we can warn on Khmer.
   */
  function buildInspectorPanel(current, onChange, meta) {
    const section = document.createElement('section');
    section.className = 'typography-curve-panel';
    section.setAttribute('data-section', 'typography-curve');
    const heading = document.createElement('h3');
    heading.textContent = 'Curve / ពង្រីកតាមធ្នឹង';
    section.appendChild(heading);

    const state = { curve: { angle: current?.curve?.angle ?? 0 } };

    const wrap = document.createElement('div');
    wrap.className = 'effect-control';
    const lab = document.createElement('label');
    lab.className = 'effect-control-label';
    lab.textContent = 'Curve (-180° to +180°) / ធ្នឹង';
    const input = document.createElement('input');
    input.type = 'range';
    input.min = '-180';
    input.max = '180';
    input.step = '1';
    input.value = String(state.curve.angle);
    const readout = document.createElement('span');
    readout.className = 'curve-readout';
    readout.textContent = `${state.curve.angle}°`;
    wrap.appendChild(lab);
    wrap.appendChild(input);
    wrap.appendChild(readout);
    section.appendChild(wrap);

    // Reset to straight.
    const resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'effect-reset';
    resetBtn.textContent = 'Straighten / កំណត់ត្រង់';
    resetBtn.addEventListener('click', () => {
      state.curve.angle = 0;
      input.value = '0';
      readout.textContent = '0°';
      emit();
    });
    section.appendChild(resetBtn);

    // Khmer warning.
    const ff = meta?.fontFamily || '';
    if (isKhmerFont(ff)) {
      const warn = document.createElement('p');
      warn.className = 'curve-warning';
      warn.setAttribute('role', 'note');
      warn.textContent = '⚠ Khmer fonts have limited curve support — complex shaping may break along the path. / ពុម្ពអក្សរខ្មែរមានការគាំទ្រកំណត់តាមធ្នឹង។';
      section.appendChild(warn);
    }

    input.addEventListener('input', () => {
      state.curve.angle = Number(input.value);
      readout.textContent = `${state.curve.angle}°`;
      emit();
    });

    function emit() {
      onChange({ curve: { angle: state.curve.angle } });
    }

    return section;
  }

  // --- Apply curve to a text element ----------------------------------------
  /**
   * Apply a curve to a DOM node representing a text element.
   * If `angle` is 0, removes any previously-applied curve SVG.
   */
  function applyToElement(node, opts) {
    if (!node) return;
    const existingSvg = node.querySelector('svg[data-curve-angle]');
    if (existingSvg) existingSvg.remove();
    const angle = Number(opts?.angle) || 0;
    if (angle === 0) return;
    const svg = svgForCurve({
      text: opts.text ?? node.textContent ?? '',
      fontFamily: opts.fontFamily || window.getComputedStyle(node).fontFamily,
      fontSize: opts.fontSize || parseFloat(window.getComputedStyle(node).fontSize) || 16,
      fill: opts.fill || window.getComputedStyle(node).color,
      width: opts.width || node.getBoundingClientRect().width || 200,
      angle,
    });
    if (svg) node.appendChild(svg);
  }

  // --- Exports --------------------------------------------------------------
  api.arcPath = arcPath;
  api.svgForCurve = svgForCurve;
  api.isKhmerFont = isKhmerFont;
  api.buildInspectorPanel = buildInspectorPanel;
  api.applyToElement = applyToElement;
  api.KHMER_FONT_HINTS = KHMER_FONT_HINTS;
  window.EInviteTypography = api;
})();
