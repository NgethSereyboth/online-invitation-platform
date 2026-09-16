/**
 * crop.js — Image crop + aspect ratio for EInvite studio (v56).
 *
 * Implements ROADMAP-v0.54-to-v1.0 §3.3.1 — selecting an image element
 * shows crop handles. The user picks a preset aspect ratio (1:1, 4:3, 16:9,
 * 3:2, free) and drags the handles to refine.
 *
 * The crop is **non-destructive** — only the `cropRect` field on the image
 * element changes. The renderer applies the crop at render time via
 * `object-fit: cover` + `object-position` (CSS) or, for export, via the
 * `drawImage(src, sx, sy, sw, sh, dx, dy, dw, dh)` overload on Canvas 2D.
 *
 * Model:
 *   cropRect: { x: 0..1, y: 0..1, w: 0..1, h: 0..1, ratio: '1:1' | '4:3' | ... | 'free' }
 *
 * Coordinates are normalised 0..1 against the source image's natural
 * dimensions so the crop survives resize / orientation changes.
 *
 * Idempotent: second-load is a no-op. Safe on non-designer routes.
 */
(() => {
  'use strict';

  if (window.EInviteImageCrop?.version >= 56) return;

  const api = { version: 56, destroy: null };

  /** Preset ratios — `null` = free. */
  const PRESETS = [
    { id: 'free', label: 'Free / សេរី', ratio: null },
    { id: '1:1',  label: '1:1', ratio: 1 },
    { id: '4:3',  label: '4:3', ratio: 4 / 3 },
    { id: '16:9', label: '16:9', ratio: 16 / 9 },
    { id: '3:2',  label: '3:2', ratio: 3 / 2 },
  ];

  /** Default = full image. */
  const DEFAULT_CROP = { x: 0, y: 0, w: 1, h: 1, ratio: 'free' };

  /**
   * Convert a cropRect (normalised 0..1) into CSS `object-fit` / `object-position`
   * values for live preview rendering.
   *
   * @param {object} cropRect The crop rectangle from the document model.
   * @returns {{objectFit: string, objectPosition: string, transform?: string}}
   */
  function serializeToCSS(cropRect) {
    if (!cropRect || !cropRect.w || !cropRect.h) {
      return { objectFit: 'cover', objectPosition: '50% 50%' };
    }
    // `object-fit: cover` already crops the image to the element's box. We
    // additionally use `object-position` to slide the image so the chosen
    // crop rect's centre aligns with the box centre. This gives a faithful
    // preview for non-square element boxes.
    const cx = (cropRect.x + cropRect.w / 2) * 100;
    const cy = (cropRect.y + cropRect.h / 2) * 100;
    return {
      objectFit: 'cover',
      objectPosition: `${cx}% ${cy}%`,
    };
  }

  /**
   * Convert a cropRect into source-rect arguments for Canvas 2D `drawImage`
   * with the 9-arg signature: `drawImage(src, sx, sy, sw, sh, dx, dy, dw, dh)`.
   *
   * @param {object} cropRect Crop rectangle (normalised 0..1).
   * @param {{naturalWidth: number, naturalHeight: number}} img Image natural size.
   * @returns {{sx:number, sy:number, sw:number, sh:number}}
   */
  function serializeToCanvas(cropRect, img) {
    const natW = img?.naturalWidth || img?.width || 1;
    const natH = img?.naturalHeight || img?.height || 1;
    const crop = cropRect || DEFAULT_CROP;
    return {
      sx: Math.round(crop.x * natW),
      sy: Math.round(crop.y * natH),
      sw: Math.max(1, Math.round(crop.w * natW)),
      sh: Math.max(1, Math.round(crop.h * natH)),
    };
  }

  /**
   * Apply a cropRect to a DOM `<img>` element by setting the appropriate
   * CSS object-fit / object-position values.
   */
  function applyToElement(imgEl, cropRect) {
    if (!imgEl) return;
    const css = serializeToCSS(cropRect);
    imgEl.style.objectFit = css.objectFit;
    imgEl.style.objectPosition = css.objectPosition;
  }

  // --- Inspector panel ------------------------------------------------------
  /**
   * Build the crop inspector section.
   * @param {object} current Current cropRect (or null for full image).
   * @param {function} onChange Called with the next cropRect on every change.
   */
  function buildInspectorPanel(current, onChange) {
    const section = document.createElement('section');
    section.className = 'image-crop-panel';
    section.setAttribute('data-section', 'image-crop');
    const heading = document.createElement('h3');
    heading.textContent = 'Crop / កាត់រូប';
    section.appendChild(heading);

    const state = { crop: normalize(current) };

    // Preset ratio chips.
    const ratioRow = document.createElement('div');
    ratioRow.className = 'crop-ratio-presets';
    PRESETS.forEach(preset => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'crop-ratio-chip';
      chip.textContent = preset.label;
      chip.dataset.ratio = preset.id;
      if (state.crop.ratio === preset.id) chip.classList.add('active');
      chip.addEventListener('click', () => {
        state.crop.ratio = preset.id;
        // Apply preset: keep crop centered, lock aspect ratio.
        state.crop = applyRatio(state.crop, preset.ratio);
        [...ratioRow.children].forEach(c => c.classList.toggle('active', c.dataset.ratio === preset.id));
        emit();
      });
      ratioRow.appendChild(chip);
    });
    section.appendChild(ratioRow);

    // Sliders for x, y, w, h (each 0..1).
    const xSlider = slider(section, 'X position', state.crop.x, 0, 0.95, 0.01);
    const ySlider = slider(section, 'Y position', state.crop.y, 0, 0.95, 0.01);
    const wSlider = slider(section, 'Width', state.crop.w, 0.05, 1, 0.01);
    const hSlider = slider(section, 'Height', state.crop.h, 0.05, 1, 0.01);

    [xSlider, ySlider, wSlider, hSlider].forEach(s => {
      s.addEventListener('input', () => {
        state.crop.x = clamp(Number(xSlider.value), 0, 1 - state.crop.w);
        state.crop.y = clamp(Number(ySlider.value), 0, 1 - state.crop.h);
        state.crop.w = clamp(Number(wSlider.value), 0.05, 1 - state.crop.x);
        state.crop.h = clamp(Number(hSlider.value), 0.05, 1 - state.crop.y);
        // If a preset ratio is active, preserve it on w/h changes.
        const preset = PRESETS.find(p => p.id === state.crop.ratio);
        if (preset?.ratio) {
          state.crop = applyRatio(state.crop, preset.ratio);
        }
        syncSliders();
        emit();
      });
    });

    // Reset button — restores full image.
    const resetBtn = document.createElement('button');
    resetBtn.type = 'button';
    resetBtn.className = 'effect-reset';
    resetBtn.textContent = 'Reset / កំណត់ឡើងវិញ';
    resetBtn.addEventListener('click', () => {
      state.crop = { ...DEFAULT_CROP };
      state.crop.ratio = 'free';
      syncSliders();
      [...ratioRow.children].forEach(c => c.classList.toggle('active', c.dataset.ratio === 'free'));
      emit();
    });
    section.appendChild(resetBtn);

    function syncSliders() {
      xSlider.value = String(state.crop.x);
      ySlider.value = String(state.crop.y);
      wSlider.value = String(state.crop.w);
      hSlider.value = String(state.crop.h);
    }
    function emit() { onChange(JSON.parse(JSON.stringify(state.crop))); }

    return section;
  }

  /** Apply a fixed aspect ratio to a cropRect while preserving its centre. */
  function applyRatio(crop, ratio) {
    if (!ratio) return { ...crop, ratio: crop.ratio === 'free' ? 'free' : crop.ratio };
    const cx = crop.x + crop.w / 2;
    const cy = crop.y + crop.h / 2;
    // Largest w (<=1) such that w*ratio <= 1, then clamp to <=1.
    let w = Math.min(crop.w, 1 / ratio);
    let h = w * ratio;
    if (h > 1) { h = 1; w = h / ratio; }
    if (w > crop.w) w = crop.w; // never grow on ratio switch
    h = w * ratio;
    let x = cx - w / 2;
    let y = cy - h / 2;
    x = clamp(x, 0, 1 - w);
    y = clamp(y, 0, 1 - h);
    return { x, y, w, h, ratio: crop.ratio };
  }

  function normalize(crop) {
    if (!crop || typeof crop !== 'object') return { ...DEFAULT_CROP };
    return {
      x: clamp(Number(crop.x) || 0, 0, 1),
      y: clamp(Number(crop.y) || 0, 0, 1),
      w: clamp(Number(crop.w) || 1, 0.05, 1),
      h: clamp(Number(crop.h) || 1, 0.05, 1),
      ratio: crop.ratio || 'free',
    };
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function slider(parent, label, value, min, max, step) {
    const wrap = document.createElement('div');
    wrap.className = 'effect-control';
    const lab = document.createElement('label');
    lab.className = 'effect-control-label';
    lab.textContent = label;
    const input = document.createElement('input');
    input.type = 'range';
    input.min = String(min);
    input.max = String(max);
    input.step = String(step);
    input.value = String(value);
    wrap.appendChild(lab);
    wrap.appendChild(input);
    parent.appendChild(wrap);
    return input;
  }

  // --- Crop handles (overlay) ----------------------------------------------
  /**
   * Mount crop handles on the given image element. Returns a `destroy()`
   * callable that removes the overlay.
   */
  function mountHandles(imgEl, cropRect, onChange) {
    if (!imgEl) return () => {};
    const overlay = document.createElement('div');
    overlay.className = 'crop-overlay';
    const handles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
    const handleEls = {};
    handles.forEach(pos => {
      const h = document.createElement('div');
      h.className = `crop-handle crop-handle-${pos}`;
      h.dataset.pos = pos;
      h.setAttribute('aria-label', `Crop handle ${pos}`);
      overlay.appendChild(h);
      handleEls[pos] = h;
    });
    // The shaded area outside the crop rect.
    const shade = document.createElement('div');
    shade.className = 'crop-shade';
    overlay.appendChild(shade);
    imgEl.parentElement.appendChild(overlay);
    function position() {
      const rect = imgEl.getBoundingClientRect();
      const parent = overlay.parentElement.getBoundingClientRect();
      overlay.style.left = `${rect.left - parent.left}px`;
      overlay.style.top = `${rect.top - parent.top}px`;
      overlay.style.width = `${rect.width}px`;
      overlay.style.height = `${rect.height}px`;
      const crop = normalize(cropRect);
      // Position the shade (4 trapezoid strips would be nicer; here we use a
      // single inset overlay using box-shadow).
      Object.entries(handleEls).forEach(([pos, el]) => {
        const [hx, hy] = handlePos(pos, crop);
        el.style.left = `calc(${hx * 100}% - 6px)`;
        el.style.top = `calc(${hy * 100}% - 6px)`;
      });
    }
    position();
    const ro = new ResizeObserver(position);
    ro.observe(imgEl);

    // Dragging — naive implementation that mutates cropRect in place.
    let dragPos = null;
    let dragStart = null;
    let cropStart = null;
    Object.entries(handleEls).forEach(([pos, el]) => {
      el.addEventListener('pointerdown', event => {
        event.preventDefault();
        dragPos = pos;
        dragStart = { x: event.clientX, y: event.clientY };
        cropStart = normalize(cropRect);
        el.setPointerCapture(event.pointerId);
      });
      el.addEventListener('pointermove', event => {
        if (!dragPos) return;
        const dx = (event.clientX - dragStart.x) / imgEl.getBoundingClientRect().width;
        const dy = (event.clientY - dragStart.y) / imgEl.getBoundingClientRect().height;
        const next = dragRect(cropStart, dragPos, dx, dy);
        Object.assign(cropRect, next);
        position();
        onChange?.(normalize(cropRect));
      });
      el.addEventListener('pointerup', () => { dragPos = null; });
      el.addEventListener('pointercancel', () => { dragPos = null; });
    });

    return function destroy() {
      ro.disconnect();
      overlay.remove();
    };
  }

  function handlePos(pos, crop) {
    const x = crop.x, y = crop.y, w = crop.w, h = crop.h;
    const map = {
      nw: [x, y], n: [x + w / 2, y], ne: [x + w, y],
      e: [x + w, y + h / 2], se: [x + w, y + h], s: [x + w / 2, y + h],
      sw: [x, y + h], w: [x, y + h / 2],
    };
    return map[pos];
  }

  function dragRect(start, pos, dx, dy) {
    const next = { ...start };
    switch (pos) {
      case 'nw': next.x = clamp(start.x + dx, 0, start.x + start.w - 0.05); next.y = clamp(start.y + dy, 0, start.y + start.h - 0.05); next.w = start.x + start.w - next.x; next.h = start.y + start.h - next.y; break;
      case 'n':  next.y = clamp(start.y + dy, 0, start.y + start.h - 0.05); next.h = start.y + start.h - next.y; break;
      case 'ne': next.y = clamp(start.y + dy, 0, start.y + start.h - 0.05); next.w = clamp(start.w + dx, 0.05, 1 - start.x); next.h = start.y + start.h - next.y; break;
      case 'e':  next.w = clamp(start.w + dx, 0.05, 1 - start.x); break;
      case 'se': next.w = clamp(start.w + dx, 0.05, 1 - start.x); next.h = clamp(start.h + dy, 0.05, 1 - start.y); break;
      case 's':  next.h = clamp(start.h + dy, 0.05, 1 - start.y); break;
      case 'sw': next.x = clamp(start.x + dx, 0, start.x + start.w - 0.05); next.w = start.x + start.w - next.x; next.h = clamp(start.h + dy, 0.05, 1 - start.y); break;
      case 'w':  next.x = clamp(start.x + dx, 0, start.x + start.w - 0.05); next.w = start.x + start.w - next.x; break;
    }
    return next;
  }

  // --- Exports --------------------------------------------------------------
  api.PRESETS = PRESETS;
  api.DEFAULT_CROP = DEFAULT_CROP;
  api.serializeToCSS = serializeToCSS;
  api.serializeToCanvas = serializeToCanvas;
  api.applyToElement = applyToElement;
  api.buildInspectorPanel = buildInspectorPanel;
  api.mountHandles = mountHandles;
  api.normalize = normalize;
  window.EInviteImageCrop = api;
})();
