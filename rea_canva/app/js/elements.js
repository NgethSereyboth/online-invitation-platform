// DOM rendering for one design element. The DOM is the interactive surface;
// render.js mirrors these rules on a canvas for export.

import { fillCss, fontStack, polygonCss } from './model.js';

export function createElementNode(element) {
  const node = document.createElement('div');
  node.className = `canvas-el el-${element.type}`;
  node.dataset.id = element.id;
  node.dataset.type = element.type;

  if (element.type === 'text') {
    const body = document.createElement('div');
    body.className = 'text-body';
    node.append(body);
  } else if (element.type === 'image') {
    const image = document.createElement('img');
    image.className = 'el-image';
    image.alt = '';
    image.draggable = false;
    node.append(image);
  } else {
    const shape = document.createElement('div');
    shape.className = 'shape-body';
    node.append(shape);
  }

  styleElementNode(node, element);
  return node;
}

export function styleElementNode(node, element) {
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
    body.style.fontSize = `${element.size || 48}px`;
    body.style.fontWeight = String(element.weight || 400);
    body.style.fontStyle = element.italic ? 'italic' : 'normal';
    body.style.textDecoration = element.underline ? 'underline' : 'none';
    body.style.textAlign = element.align || 'left';
    body.style.color = element.color || '#12161c';
    body.style.lineHeight = String(element.lineHeight || 1.2);
    body.style.letterSpacing = `${element.letterSpacing || 0}px`;
  } else if (element.type === 'image') {
    const image = node.firstElementChild;
    if (image.getAttribute('src') !== (element.src || '')) {
      image.src = element.src || '';
    }
    image.style.objectFit = element.fit === 'contain' ? 'contain' : 'cover';
    node.classList.toggle('is-empty', !element.src);
  } else {
    const shape = node.firstElementChild;
    shape.style.background = fillCss(element.fill);
    shape.style.boxShadow =
      element.stroke && element.stroke !== 'transparent' && element.strokeWidth
        ? `inset 0 0 0 ${element.strokeWidth}px ${element.stroke}`
        : 'none';
    shape.style.borderRadius =
      element.type === 'ellipse'
        ? '50%'
        : element.type === 'roundRect' || (element.type === 'rect' && element.radius)
          ? `${element.radius || 0}px`
          : '0';
    const clip = ['triangle', 'diamond', 'hexagon', 'star', 'arrow'].includes(element.type)
      ? polygonCss(element.type)
      : '';
    shape.style.clipPath = clip;
  }
}

export function updateElementNode(node, element) {
  styleElementNode(node, element);
}
