/* Rea Board core — helpers, the element model, DOM styling and canvas export.
 *
 * The board is a second design surface inside the invitation editor. It edits
 * the same `designPages` objects the classic editor edits, so nothing here
 * persists on its own: board-app.js maps these elements to and from the
 * invitation document through window.EInviteEditorBridge.
 *
 * Loaded as a classic script by the index route bundle (see
 * docs/route-bundle-sources.json). No ES modules, no bundler.
 */
(() => {
  'use strict';

  const RB = (window.ReaBoardCore = window.ReaBoardCore || {});

  /* ---------------------------------------------------------------- */
  /* DOM helpers                                                       */
  /* ---------------------------------------------------------------- */

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const uid = (prefix = 'rb') =>
    `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  const deepClone = (value) => {
    if (typeof structuredClone === 'function') return structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  };

  const escapeHtml = (value) =>
    String(value ?? '').replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    })[ch]);

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value === undefined || value === null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key === 'style') Object.assign(node.style, value);
      else if (key === 'dataset') Object.assign(node.dataset, value);
      else if (key === 'on') {
        for (const [event, handler] of Object.entries(value)) node.addEventListener(event, handler);
      } else if (key in node && key !== 'list' && key !== 'type') {
        node[key] = value;
      } else {
        node.setAttribute(key, value === true ? '' : String(value));
      }
    }
    for (const child of [].concat(children)) {
      if (child !== null && child !== undefined) node.append(child);
    }
    return node;
  }

  const svgIcon = (paths, size = 20) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', String(size));
    svg.setAttribute('height', String(size));
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '1.7');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    for (const d of [].concat(paths)) {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      svg.append(path);
    }
    return svg;
  };

  const ICONS = {
    close: ['m6 6 12 12', 'm18 6-12 12'],
    plus: ['M12 5v14', 'M5 12h14'],
    minus: ['M5 12h14'],
    undo: ['M8.6 7.4 4 12l4.6 4.6', 'M4 12h10.2a5.4 5.4 0 0 1 0 10.8H9.6'],
    redo: ['m15.4 7.4 4.6 4.6-4.6 4.6', 'M20 12H9.8a5.4 5.4 0 0 0 0 10.8h4.6'],
    text: ['M5 5.4h14', 'M12 5.4V19', 'M8.6 19h6.8'],
    shape: ['M3.6 3.6h8v8h-8z', 'M17.6 9.4a4.2 4.2 0 1 0 0 8.4 4.2 4.2 0 0 0 0-8.4Z'],
    image: ['M4 4.6h16v14.8H4z', 'M4 15.4 9 10.6l4 3.8 3-2.8 4 3.8', 'M15.4 8.4h.01'],
    layers: ['m12 3.4 8.4 4.5-8.4 4.5L3.6 7.9z', 'm4.4 12.4 7.6 4.1 7.6-4.1', 'm4.4 16.6 7.6 4.1 7.6-4.1'],
    page: ['M6.4 3.6h7.2l4 4v12.8H6.4z', 'M13.4 3.6v4.2h4.2'],
    download: ['M12 4v11.4', 'm7 10.4 5 5 5-5', 'M4.6 19.4h14.8'],
    play: ['M8 5.4 18.6 12 8 18.6z'],
    fit: ['M4 8.4V4.4h4', 'M16 4.4h4v4', 'M20 15.6v4h-4', 'M8 19.6H4v-4'],
    eye: ['M2.8 12s3.4-6.2 9.2-6.2S21.2 12 21.2 12s-3.4 6.2-9.2 6.2S2.8 12 2.8 12Z', 'M12 9.4a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 0-5.2Z'],
    eyeOff: ['M4 4.6 20 19.4', 'M9.8 6.2A9.8 9.8 0 0 1 12 5.8c5.8 0 9.2 6.2 9.2 6.2a17 17 0 0 1-3.2 3.8', 'M6.2 8a17 17 0 0 0-3.4 4s3.4 6.2 9.2 6.2a9.6 9.6 0 0 0 3.4-.6'],
    lock: ['M6.4 10.4h11.2v9.2H6.4z', 'M8.8 10.4V7.6a3.2 3.2 0 0 1 6.4 0v2.8'],
    unlock: ['M6.4 10.4h11.2v9.2H6.4z', 'M8.8 10.4V7.6a3.2 3.2 0 0 1 6.1-1.2'],
    trash: ['M4.6 6.8h14.8', 'M9.4 6.8V4.6h5.2v2.2', 'M6.6 6.8 7.4 20h9.2l.8-13.2'],
    copy: ['M8.4 8.4h11.2v11.2H8.4z', 'M15.6 5.4H4.4v11.2h4'],
    alignLeft: ['M4.4 5.4h15.2', 'M4.4 10.4h9.4', 'M4.4 15.4h15.2', 'M4.4 20h9.4'],
    alignCenter: ['M4.4 5.4h15.2', 'M7.3 10.4h9.4', 'M4.4 15.4h15.2', 'M7.3 20h9.4'],
    alignRight: ['M4.4 5.4h15.2', 'M10.2 10.4h9.4', 'M4.4 15.4h15.2', 'M10.2 20h9.4'],
    toFront: ['M4.6 4.6h14.8', 'M12 20.4V8', 'm7.4 12.6 4.6-4.6 4.6 4.6'],
    forward: ['M12 20.4V5.6', 'm6.8 10.8 5.2-5.2 5.2 5.2'],
    backward: ['M12 3.6v14.8', 'm6.8 13.2 5.2 5.2 5.2-5.2'],
    toBack: ['M4.6 19.4h14.8', 'M12 3.6V16', 'm7.4 11.4 4.6 4.6 4.6-4.6'],
    more: ['M6 12h.01', 'M12 12h.01', 'M18 12h.01'],
    check: ['m4.5 12.6 4.8 4.8 10.2-10.2'],
    arrowLeft: ['M19 12H5', 'm11 6-6 6 6 6'],
    bold: ['M7 4.6h6.4a4 4 0 0 1 0 8H7z', 'M7 12.6h7.2a4.2 4.2 0 0 1 0 8.4H7z'],
    italic: ['M15.4 4.6h-4.8', 'M13.4 4.6 10.6 19.4', 'M13.4 19.4H8.6'],
    underline: ['M7 4.6v6.6a5 5 0 0 0 10 0V4.6', 'M5.4 20.4h13.2'],
  };

  let toastHost = null;

  function toast(message, kind = 'default') {
    if (!toastHost || !document.documentElement.contains(toastHost)) {
      toastHost = $('#toasts');
      if (!toastHost) {
        toastHost = el('div', { id: 'toasts', class: 'toasts' });
        document.body.append(toastHost);
      }
    }
    const node = el('div', { class: `toast toast-${kind}`, role: 'status' }, message);
    toastHost.append(node);
    requestAnimationFrame(() => node.classList.add('is-in'));
    window.setTimeout(() => {
      node.classList.remove('is-in');
      window.setTimeout(() => node.remove(), 220);
    }, 2400);
  }

  async function downloadBlob(blob, filename) {
    // Blob-URL downloads are refused in some CSP/sandbox setups and fall back
    // to navigating the tab to the image. Exported pages are small enough to
    // hand the browser a data URL, which downloads everywhere.
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error || new Error('read-failed'));
      reader.readAsDataURL(blob);
    });
    if (!dataUrl) throw new Error('empty-blob');
    const link = el('a', { href: dataUrl, download: filename });
    document.body.append(link);
    link.click();
    link.remove();
  }

  /* ---------------------------------------------------------------- */
  /* Fonts and fills                                                   */
  /* ---------------------------------------------------------------- */

  const FALLBACK_FONTS = [
    { id: 'noto-serif', label: 'Noto Serif', stack: "Georgia, 'Times New Roman', serif" },
    { id: 'noto-sans', label: 'Noto Sans', stack: 'Arial, system-ui, sans-serif' },
    { id: 'serif-georgia', label: 'Classic Serif', stack: 'Georgia, serif' },
    { id: 'sans-arial', label: 'Modern Sans', stack: 'Arial, sans-serif' },
  ];

  function fontList() {
    const registry = window.EInviteFontRegistry;
    const fonts = registry && registry.data && registry.data.fonts;
    if (fonts) {
      const list = Object.entries(fonts)
        .filter(([, meta]) => meta && meta.label)
        .map(([id, meta]) => ({ id, label: meta.label, stack: meta.stack }));
      if (list.length) return list;
    }
    return FALLBACK_FONTS;
  }

  function fontStack(id) {
    const found = fontList().find((font) => font.id === id);
    return (found || FALLBACK_FONTS[0]).stack;
  }

  const SWATCHES = [
    '#ffffff', '#f6f3ee', '#fef3e2', '#ffe8d6', '#ffd166', '#ff8a5b',
    '#ef476f', '#c9184a', '#8b3dff', '#5e5cff', '#00c4cc', '#2ec4b6',
    '#06d6a0', '#118ab2', '#141821', '#3d4451', '#8b93a1', '#d9dee6',
  ];

  const GRADIENTS = [
    { id: 'aurora', name: 'Aurora', from: '#00c4cc', to: '#7d2ae8', angle: 135 },
    { id: 'sunset', name: 'Sunset', from: '#ffd166', to: '#ef476f', angle: 120 },
    { id: 'ember', name: 'Ember', from: '#ff8a5b', to: '#c9184a', angle: 100 },
    { id: 'midnight', name: 'Midnight', from: '#1b2140', to: '#0b0b12', angle: 160 },
    { id: 'mint', name: 'Mint', from: '#d9f7ef', to: '#2ec4b6', angle: 130 },
    { id: 'blush', name: 'Blush', from: '#ffe8d6', to: '#ef476f', angle: 125 },
  ];

  function isGradient(fill) {
    return Boolean(fill && typeof fill === 'object' && fill.from && fill.to);
  }

  function fillCss(fill) {
    if (!fill) return 'transparent';
    if (typeof fill === 'string') return fill;
    return `linear-gradient(${fill.angle ?? 135}deg, ${fill.from}, ${fill.to})`;
  }

  function hexColor(value, fallback = '#ffffff') {
    return /^#[0-9a-f]{6}$/i.test(String(value || '')) ? String(value) : fallback;
  }

  /* ---------------------------------------------------------------- */
  /* Element model                                                     */
  /* ---------------------------------------------------------------- */

  const BASE = {
    x: 0, y: 0, w: 240, h: 240,
    rotation: 0, opacity: 1, locked: false, visible: true,
  };

  const TEXT_DEFAULTS = {
    text: 'Add your text',
    font: 'noto-serif',
    size: 40,
    weight: 400,
    italic: false,
    underline: false,
    align: 'left',
    color: '#141821',
    lineHeight: 1.25,
    letterSpacing: 0,
  };

  function createElement(type, overrides = {}) {
    let kind = type;
    let specific;
    if (type === 'text') {
      specific = { ...TEXT_DEFAULTS, w: 420, h: 170 };
    } else if (type === 'image') {
      specific = { src: '', fit: 'cover', radius: 0, w: 360, h: 260, alt: '' };
    } else {
      kind = 'shape';
      if (type === 'line') {
        specific = { shape: 'line', fill: '#141821', w: 300, h: 4 };
      } else if (type === 'circle') {
        specific = { shape: 'circle', fill: '#7d2ae8', w: 200, h: 200 };
      } else {
        specific = { shape: 'rectangle', fill: '#7d2ae8', radius: 0, w: 300, h: 200 };
      }
    }
    return {
      ...BASE,
      id: uid(kind),
      type: kind,
      name: '',
      ...specific,
      ...overrides,
    };
  }

  function elementName(element) {
    if (element.type === 'text') {
      const line = String(element.text || '').split('\n')[0].trim();
      return line ? line.slice(0, 34) : 'Text';
    }
    if (element.type === 'image') return element.alt || 'Image';
    return element.shape === 'circle' ? 'Circle' : element.shape === 'line' ? 'Line' : 'Rectangle';
  }

  /* ---------------------------------------------------------------- */
  /* DOM nodes                                                         */
  /* ---------------------------------------------------------------- */

  function createElementNode(element) {
    const node = document.createElement('div');
    node.className = `rb-el rb-el-${element.type}`;
    // Namespaced so the classic editor's global [data-id] lookups never match
    // (and update) board nodes while the board is open or after it closes.
    node.dataset.reaId = element.id;
    node.dataset.type = element.type;

    if (element.type === 'text') {
      node.append(el('div', { class: 'rb-text-body' }));
    } else if (element.type === 'image') {
      node.append(el('img', { class: 'rb-image', alt: '', draggable: false }));
    } else {
      node.append(el('div', { class: 'rb-shape-body' }));
    }
    styleElementNode(node, element);
    return node;
  }

  function styleElementNode(node, element) {
    node.style.left = `${element.x}px`;
    node.style.top = `${element.y}px`;
    node.style.width = `${Math.max(0, element.w)}px`;
    node.style.height = `${Math.max(0, element.h)}px`;
    node.style.transform = `rotate(${element.rotation || 0}deg)`;
    node.style.opacity = String(element.opacity ?? 1);
    node.hidden = element.visible === false;
    node.classList.toggle('is-locked', Boolean(element.locked));

    if (element.type === 'text') {
      const body = node.firstElementChild;
      body.textContent = element.text ?? '';
      body.style.fontFamily = fontStack(element.font);
      body.style.fontSize = `${element.size || 40}px`;
      body.style.fontWeight = String(element.weight || 400);
      body.style.fontStyle = element.italic ? 'italic' : 'normal';
      body.style.textDecoration = element.underline ? 'underline' : 'none';
      body.style.textAlign = element.align || 'left';
      body.style.color = element.color || '#141821';
      body.style.lineHeight = String(element.lineHeight || 1.25);
      body.style.letterSpacing = `${element.letterSpacing || 0}px`;
      body.style.justifyContent = 'flex-start';
    } else if (element.type === 'image') {
      const image = node.firstElementChild;
      if (image.getAttribute('src') !== (element.src || '')) image.src = element.src || '';
      image.style.objectFit = element.fit === 'contain' ? 'contain' : 'cover';
      image.style.borderRadius = `${element.radius || 0}px`;
      node.classList.toggle('is-empty', !element.src);
    } else {
      const shape = node.firstElementChild;
      shape.style.background = fillCss(element.fill);
      shape.style.borderRadius = element.shape === 'circle'
        ? '50%'
        : `${element.radius || 0}px`;
    }
  }

  /* ---------------------------------------------------------------- */
  /* Canvas export                                                     */
  /* ---------------------------------------------------------------- */

  const imageCache = new Map();

  function loadImage(src) {
    if (!src) return Promise.resolve(null);
    if (imageCache.has(src)) return imageCache.get(src);
    const promise = new Promise((resolve) => {
      const image = new Image();
      image.decoding = 'async';
      image.onload = () => resolve(image);
      image.onerror = () => resolve(null);
      image.src = src;
    });
    imageCache.set(src, promise);
    return promise;
  }

  function paint(ctx, fill, w, h) {
    if (isGradient(fill)) {
      const angle = ((fill.angle ?? 135) * Math.PI) / 180;
      const length = Math.abs(w * Math.sin(angle)) + Math.abs(h * Math.cos(angle));
      const dx = (Math.sin(angle) * length) / 2;
      const dy = (-Math.cos(angle) * length) / 2;
      const gradient = ctx.createLinearGradient(w / 2 - dx, h / 2 - dy, w / 2 + dx, h / 2 + dy);
      gradient.addColorStop(0, fill.from);
      gradient.addColorStop(1, fill.to);
      return gradient;
    }
    return fill || 'transparent';
  }

  function roundedRect(ctx, x, y, w, h, radius) {
    const r = Math.max(0, Math.min(radius || 0, Math.min(w, h) / 2));
    ctx.beginPath();
    if (r <= 0.01) {
      ctx.rect(x, y, w, h);
      return;
    }
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function wrapLines(ctx, text, maxWidth) {
    const lines = [];
    for (const paragraph of String(text ?? '').split('\n')) {
      if (!paragraph) {
        lines.push('');
        continue;
      }
      let line = '';
      for (const word of paragraph.split(' ')) {
        const candidate = line ? `${line} ${word}` : word;
        if (line && ctx.measureText(candidate).width > maxWidth) {
          lines.push(line);
          line = word;
        } else {
          line = candidate;
        }
      }
      lines.push(line);
    }
    return lines;
  }

  function drawText(ctx, element, w) {
    const size = element.size || 40;
    const lineHeight = size * (element.lineHeight || 1.25);
    const weight = element.weight || 400;
    ctx.font = `${element.italic ? 'italic ' : ''}${weight} ${size}px ${fontStack(element.font)}`;
    ctx.textBaseline = 'top';
    ctx.fillStyle = element.color || '#141821';
    if ('letterSpacing' in ctx) ctx.letterSpacing = `${element.letterSpacing || 0}px`;
    wrapLines(ctx, element.text, w).forEach((line, index) => {
      const y = index * lineHeight;
      const width = ctx.measureText(line).width;
      const x = element.align === 'center' ? (w - width) / 2 : element.align === 'right' ? w - width : 0;
      ctx.fillText(line, x, y);
      if (element.underline) ctx.fillRect(x, y + size * 1.02, width, Math.max(1, size * 0.055));
    });
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
  }

  function drawImage(ctx, image, element, w, h) {
    const iw = image.naturalWidth || image.width;
    const ih = image.naturalHeight || image.height;
    if (!iw || !ih) return;
    const fit = element.fit === 'contain' ? Math.min(w / iw, h / ih) : Math.max(w / iw, h / ih);
    const dw = iw * fit;
    const dh = ih * fit;
    ctx.save();
    roundedRect(ctx, 0, 0, w, h, element.radius || 0);
    ctx.clip();
    ctx.drawImage(image, (w - dw) / 2, (h - dh) / 2, dw, dh);
    ctx.restore();
  }

  function drawElement(ctx, element, image) {
    const w = Math.max(0, element.w);
    const h = Math.max(0, element.h);
    if (!w || !h) return;
    ctx.save();
    ctx.globalAlpha = element.opacity ?? 1;
    ctx.translate(element.x + w / 2, element.y + h / 2);
    ctx.rotate(((element.rotation || 0) * Math.PI) / 180);
    ctx.translate(-w / 2, -h / 2);

    if (element.type === 'text') {
      drawText(ctx, element, w);
    } else if (element.type === 'image') {
      if (image) drawImage(ctx, image, element, w, h);
    } else if (element.shape === 'circle') {
      ctx.beginPath();
      ctx.ellipse(w / 2, h / 2, Math.max(w / 2, 0.01), Math.max(h / 2, 0.01), 0, 0, Math.PI * 2);
      ctx.fillStyle = paint(ctx, element.fill, w, h);
      ctx.fill();
    } else {
      roundedRect(ctx, 0, 0, w, h, element.radius || 0);
      ctx.fillStyle = paint(ctx, element.fill, w, h);
      ctx.fill();
    }
    ctx.restore();
  }

  async function renderPageToCanvas(doc, page, options = {}) {
    const scale = options.scale || 1;
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(doc.w * scale));
    canvas.height = Math.max(1, Math.round(doc.h * scale));
    const ctx = canvas.getContext('2d');
    ctx.scale(scale, scale);
    ctx.fillStyle = page.background || '#ffffff';
    ctx.fillRect(0, 0, doc.w, doc.h);

    const images = await Promise.all(
      page.elements.map((element) =>
        element.type === 'image' && element.visible ? loadImage(element.src) : Promise.resolve(null),
      ),
    );
    page.elements.forEach((element, index) => {
      if (element.visible === false) return;
      drawElement(ctx, element, images[index]);
    });
    return canvas;
  }

  function canvasToBlob(canvas, type = 'image/png', quality) {
    return new Promise((resolve) => canvas.toBlob(resolve, type, quality));
  }

  async function paintThumbnail(canvas, doc, page, maxW = 58, maxH = 74) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const fit = Math.min(maxW / doc.w, maxH / doc.h);
    const cssW = Math.max(1, Math.round(doc.w * fit));
    const cssH = Math.max(1, Math.round(doc.h * fit));
    const source = await renderPageToCanvas(doc, page, { scale: (cssW * dpr) / doc.w });
    canvas.width = source.width;
    canvas.height = source.height;
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    canvas.getContext('2d').drawImage(source, 0, 0);
    return canvas;
  }

  Object.assign(RB, {
    $, $$, uid, clamp, deepClone, escapeHtml, el, svgIcon, ICONS,
    toast, downloadBlob,
    fontList, fontStack, SWATCHES, GRADIENTS, isGradient, fillCss, hexColor,
    createElement, elementName,
    createElementNode, styleElementNode,
    loadImage, renderPageToCanvas, canvasToBlob, paintThumbnail,
  });
})();
