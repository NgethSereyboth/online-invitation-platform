// Canvas renderer used for export, page thumbnails and dashboard previews.

import { fontStack, isGradient, normalizedPoints } from './model.js';

const imageCache = new Map();
const FONT_FAMILIES = ['Rea Sans', 'Rea Serif'];

export function loadImage(src) {
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

export async function ensureFonts() {
  if (!document.fonts) return;
  const loads = [];
  for (const family of FONT_FAMILIES) {
    for (const weight of [400, 700, 800]) {
      loads.push(document.fonts.load(`${weight} 32px "${family}"`).catch(() => null));
    }
  }
  await Promise.all(loads);
  await document.fonts.ready;
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

function shapePath(ctx, element, w, h) {
  const { type } = element;
  if (type === 'ellipse') {
    ctx.beginPath();
    ctx.ellipse(w / 2, h / 2, Math.max(w / 2, 0.01), Math.max(h / 2, 0.01), 0, 0, Math.PI * 2);
    return;
  }
  if (type === 'rect' || type === 'line') {
    ctx.beginPath();
    ctx.rect(0, 0, w, h);
    return;
  }
  if (type === 'roundRect') {
    roundedRect(ctx, 0, 0, w, h, element.radius);
    return;
  }
  const points = normalizedPoints(type);
  ctx.beginPath();
  points.forEach(([x, y], index) => {
    if (index === 0) ctx.moveTo(x * w, y * h);
    else ctx.lineTo(x * w, y * h);
  });
  ctx.closePath();
}

function wrapLines(ctx, text, maxWidth) {
  const paragraphs = String(text ?? '').split('\n');
  const lines = [];
  for (const paragraph of paragraphs) {
    if (!paragraph) {
      lines.push('');
      continue;
    }
    const words = paragraph.split(' ');
    let line = '';
    for (const word of words) {
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
  const size = element.size || 48;
  const lineHeight = size * (element.lineHeight || 1.2);
  const leading = (lineHeight - size) / 2;
  const weight = element.weight || 400;
  ctx.font = `${element.italic ? 'italic ' : ''}${weight} ${size}px ${fontStack(element.font)}`;
  ctx.textBaseline = 'top';
  ctx.fillStyle = element.color || '#12161c';
  if ('letterSpacing' in ctx) ctx.letterSpacing = `${element.letterSpacing || 0}px`;
  const lines = wrapLines(ctx, element.text, w);
  lines.forEach((line, index) => {
    const y = index * lineHeight + leading;
    const width = ctx.measureText(line).width;
    let x = 0;
    if (element.align === 'center') x = (w - width) / 2;
    else if (element.align === 'right') x = w - width;
    ctx.fillText(line, x, y);
    if (element.underline) {
      ctx.fillRect(x, y + size * 1.02, width, Math.max(1, size * 0.055));
    }
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
  ctx.drawImage(image, (w - dw) / 2, (h - dh) / 2, dw, dh);
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
  } else {
    shapePath(ctx, element, w, h);
    ctx.fillStyle = paint(ctx, element.fill, w, h);
    ctx.fill();
    const strokeWidth = element.strokeWidth || 0;
    if (element.stroke && element.stroke !== 'transparent' && strokeWidth > 0) {
      ctx.lineWidth = strokeWidth;
      ctx.strokeStyle = element.stroke;
      ctx.stroke();
    }
  }
  ctx.restore();
}

export async function renderPageToCanvas(design, page, options = {}) {
  const scale = options.scale || 1;
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(design.w * scale));
  canvas.height = Math.max(1, Math.round(design.h * scale));
  const ctx = canvas.getContext('2d');
  ctx.scale(scale, scale);
  ctx.fillStyle = page.background || '#ffffff';
  ctx.fillRect(0, 0, design.w, design.h);

  const images = await Promise.all(
    page.elements.map((element) =>
      element.type === 'image' && element.visible ? loadImage(element.src) : Promise.resolve(null),
    ),
  );
  page.elements.forEach((element, index) => {
    if (!element.visible) return;
    drawElement(ctx, element, images[index]);
  });
  return canvas;
}

export async function paintThumbnail(canvas, design, page, maxW = 420, maxH = 320) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const fit = Math.min(maxW / design.w, maxH / design.h);
  const cssW = Math.max(1, Math.round(design.w * fit));
  const cssH = Math.max(1, Math.round(design.h * fit));
  const source = await renderPageToCanvas(design, page, {
    scale: (cssW * dpr) / design.w,
  });
  canvas.width = source.width;
  canvas.height = source.height;
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${cssH}px`;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(source, 0, 0);
  return canvas;
}

export async function canvasToBlob(canvas, type = 'image/png', quality) {
  return new Promise((resolve) => canvas.toBlob(resolve, type, quality));
}
