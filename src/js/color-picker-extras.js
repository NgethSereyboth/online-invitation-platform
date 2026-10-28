/* LT-4.3: the editor's native colour inputs get a small popover with recents, an
   eyedropper where the browser has one, and a contrast hint for text colours.
   The native input stays the source of truth: every choice is written back to it
   and both `input` and `change` are dispatched, so the existing editor handlers
   keep doing the applying. No new colour logic in app.js, no HTML change. */
(() => {
  'use strict';
  const body = document.body;
  if (!body || (!document.querySelector('#stage') && !document.querySelector('#main'))) return;
  if (window.EInviteColorExtras) return;
  const RECENTS_KEY = 'einvite-color-recents-v1';
  const MAX_RECENTS = 8;
  const HEX = /^#[0-9a-f]{6}$/i;

  function recents() {
    try {
      const list = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
      return Array.isArray(list) ? list.filter((x) => HEX.test(String(x))).slice(0, MAX_RECENTS) : [];
    } catch { return []; }
  }
  function remember(hex) {
    const value = String(hex || '').toLowerCase();
    if (!HEX.test(value)) return recents();
    const next = [value, ...recents().filter((x) => x !== value)].slice(0, MAX_RECENTS);
    try { localStorage.setItem(RECENTS_KEY, JSON.stringify(next)); } catch {}
    return next;
  }

  // --- contrast -------------------------------------------------------------
  function toRgb(color) {
    const value = String(color || '').trim();
    const hex = value.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hex) {
      const raw = hex[1].length === 3 ? hex[1].replace(/(.)/g, '$1$1') : hex[1];
      const n = parseInt(raw, 16);
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    const rgb = value.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
    return rgb ? [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])] : null;
  }
  function luminance(color) {
    const rgb = toRgb(color);
    if (!rgb) return null;
    const [r, g, b] = rgb.map((channel) => {
      const c = channel / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  function contrastRatio(foreground, background) {
    const a = luminance(foreground), b = luminance(background);
    if (a === null || b === null) return null;
    const light = Math.max(a, b), dark = Math.min(a, b);
    return (light + 0.05) / (dark + 0.05);
  }
  // The page surface the text is read on: the document palette, then the stage,
  // then white. Shapes/text both sit on that surface in this editor.
  function pageBackground() {
    const palette = window.state?.palette;
    const stage = document.querySelector('#stage');
    const stageColor = stage ? getComputedStyle(stage).backgroundColor : '';
    for (const candidate of [palette?.background, stageColor, '#ffffff']) {
      if (toRgb(candidate)) return candidate;
    }
    return '#ffffff';
  }
  function contrastHint(hex) {
    const ratio = contrastRatio(hex, pageBackground());
    if (ratio === null) return '';
    const rounded = `${ratio.toFixed(1)}:1`;
    if (ratio >= 4.5) return `AA text — ${rounded}`;
    if (ratio >= 3) return `Large text only — ${rounded}`;
    return `Below AA — ${rounded}`;
  }

  // --- popover --------------------------------------------------------------
  let host = null;
  let dialog = null;
  let restoreFocus = null;

  function apply(hex) {
    if (!host || !HEX.test(hex)) return;
    const value = hex.toLowerCase();
    host.value = value;
    if (dialog) {
      dialog.querySelector('[data-cp-value]').value = value;
      dialog.querySelector('[data-cp-native]').value = value;
      renderDetails(value);
    }
    host.dispatchEvent(new Event('input', { bubbles: true }));
    host.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function renderDetails(hex) {
    if (!dialog) return;
    const hint = dialog.querySelector('[data-cp-contrast]');
    // Only text colours get a contrast verdict; a shape border on a page has no
    // readable text to judge, and a wrong hint is worse than none.
    const role = host?.dataset.ctx || host?.id || '';
    const isText = /(^|-)color$|^color$|text|accent|heading/i.test(role) && !/fill|border|shadow|background/i.test(role);
    hint.hidden = !isText;
    hint.textContent = isText ? contrastHint(hex) : '';
    hint.dataset.level = isText ? (contrastHint(hex).startsWith('AA') ? 'pass' : contrastHint(hex).startsWith('Large') ? 'large' : 'fail') : '';
    const list = dialog.querySelector('[data-cp-recents]');
    const recent = recents();
    list.replaceChildren();
    recent.forEach((value) => {
      const swatch = document.createElement('button');
      swatch.type = 'button';
      swatch.className = 'cp-recent';
      swatch.dataset.color = value;
      swatch.style.setProperty('--cp-swatch', value);
      swatch.setAttribute('aria-label', `Use recent colour ${value}`);
      swatch.addEventListener('click', () => { apply(value); remember(value); renderDetails(value); });
      list.append(swatch);
    });
    const empty = dialog.querySelector('[data-cp-empty]');
    empty.hidden = recent.length > 0;
  }

  function close({ focus = false } = {}) {
    if (!dialog) return;
    const closing = dialog;
    dialog = null;
    closing.remove();
    if (focus && restoreFocus && typeof restoreFocus.focus === 'function') restoreFocus.focus();
    restoreFocus = null;
    host = null;
  }

  // Editor JS builds no HTML strings (repo rule): the popover is nodes only.
  function el(tag, attrs = {}, text = '') {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([name, value]) => {
      if (name === 'class') node.className = value; else node.setAttribute(name, value);
    });
    if (text) node.textContent = text;
    return node;
  }

  function build() {
    const node = el('div', { class: 'cp-extras', role: 'dialog', 'aria-label': 'Colour picker extras' });
    const head = el('div', { class: 'cp-extras-head' });
    head.append(
      el('span', { class: 'cp-extras-title' }, 'Colour'),
      el('button', { type: 'button', class: 'cp-extras-close', 'data-cp-close': '', 'aria-label': 'Close colour picker' }, '×'),
    );
    const row = el('div', { class: 'cp-extras-row' });
    row.append(
      el('input', { 'data-cp-native': '', type: 'color', 'aria-label': 'Pick a colour' }),
      el('input', { 'data-cp-value': '', type: 'text', inputmode: 'text', spellcheck: 'false', maxlength: '7', 'aria-label': 'Hex colour value', placeholder: '#9d4555' }),
    );
    const actions = el('div', { class: 'cp-extras-actions' });
    actions.append(el('button', { type: 'button', class: 'cp-extras-pick', 'data-cp-eyedropper': '', hidden: '' }, 'Eyedropper'));
    node.append(
      head,
      row,
      el('p', { class: 'cp-extras-label' }, 'Recent colours'),
      el('div', { class: 'cp-extras-recents', 'data-cp-recents': '', role: 'group', 'aria-label': 'Recent colours' }),
      el('p', { class: 'cp-extras-empty', 'data-cp-empty': '', hidden: '' }, 'No recent colours yet.'),
      el('p', { class: 'cp-extras-contrast', 'data-cp-contrast': '', hidden: '' }),
      actions,
    );
    body.append(node);
    return node;
  }

  function open(input) {
    if (!input || input.type !== 'color') return false;
    if (dialog && host === input) { close({ focus: true }); return false; }
    close();
    host = input;
    restoreFocus = input;
    dialog = build();
    dialog.querySelector('[data-cp-native]').value = input.value;
    dialog.querySelector('[data-cp-value]').value = input.value;
    dialog.querySelector('[data-cp-native]').addEventListener('input', (event) => { apply(event.target.value); remember(event.target.value); });
    dialog.querySelector('[data-cp-value]').addEventListener('change', (event) => {
      const value = event.target.value.trim();
      if (!HEX.test(value)) { event.target.value = host?.value || ''; return; }
      apply(value); remember(value); renderDetails(value);
    });
    dialog.querySelector('[data-cp-close]').addEventListener('click', () => close({ focus: true }));
    const picker = dialog.querySelector('[data-cp-eyedropper]');
    if ('EyeDropper' in window) {
      picker.hidden = false;
      picker.addEventListener('click', async () => {
        try {
          const result = await new window.EyeDropper().open();
          if (result?.sRGBHex) { apply(result.sRGBHex); remember(result.sRGBHex); renderDetails(result.sRGBHex); }
        } catch { /* the user cancelled the eyedropper; nothing to apply */ }
      });
    }
    renderDetails(input.value);
    position(input);
    dialog.querySelector('[data-cp-value]').focus({ preventScroll: true });
    return true;
  }

  function position(input) {
    if (!dialog) return;
    const anchor = input.getBoundingClientRect();
    const box = dialog.getBoundingClientRect();
    const gap = 8;
    let left = Math.min(anchor.left, window.innerWidth - box.width - 12);
    left = Math.max(12, left);
    let top = anchor.bottom + gap;
    if (top + box.height > window.innerHeight - 12) top = Math.max(12, anchor.top - box.height - gap);
    dialog.style.left = `${Math.round(left)}px`;
    dialog.style.top = `${Math.round(top)}px`;
  }

  // Delegated: every colour input in the editor, including ones the panels and
  // the studio build later. `preventDefault` keeps the OS dialog closed while
  // the popover owns the interaction; the native input inside is one click away.
  document.addEventListener('click', (event) => {
    const input = event.target.closest?.('input[type="color"]');
    if (!input || !input.closest('#main, #stage, body[data-page="index"]')) return;
    if (input.closest('.cp-extras')) return;
    event.preventDefault();
    open(input);
  }, true);
  // Window capture: the editor's own Escape handlers sit on document and some stop
  // immediate propagation there, so the popover listens one level earlier.
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && dialog) { event.preventDefault(); close({ focus: true }); }
  }, true);
  document.addEventListener('pointerdown', (event) => {
    if (!dialog || event.target.closest('.cp-extras') || event.target.closest('input[type="color"]')) return;
    close();
  }, true);
  window.addEventListener('resize', () => close(), { passive: true });

  window.EInviteColorExtras = Object.freeze({
    version: 1,
    open,
    close,
    recents,
    remember,
    contrast: { ratio: contrastRatio, hint: contrastHint, background: pageBackground },
  });
})();
