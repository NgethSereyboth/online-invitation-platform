// Small dependency-free helpers shared by the dashboard and the editor.

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

export const uid = (prefix = 'id') =>
  `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export const deepClone = (value) =>
  typeof structuredClone === 'function'
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value));

export function el(tag, props = {}, children = []) {
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

export const svgIcon = (paths, size = 20) => {
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

export const ICONS = {
  home: ['M3.6 10.4 12 3.8l8.4 6.6', 'M5.5 9.4V20h13V9.4', 'M9.6 20v-5.6h4.8V20'],
  grid: ['M4 4h6.4v6.4H4z', 'M13.6 4H20v6.4h-6.4z', 'M4 13.6h6.4V20H4z', 'M13.6 13.6H20V20h-6.4z'],
  folder: ['M3.5 6.6h6l1.8 2.2h9.2v10.4a1.6 1.6 0 0 1-1.6 1.6H5.1a1.6 1.6 0 0 1-1.6-1.6z'],
  template: ['M4 4h16v16H4z', 'M4 9.4h16', 'M9.4 9.4V20'],
  brand: ['M12 3.4 14.7 9l6.1.9-4.4 4.3 1 6.1L12 17.5l-5.4 2.8 1-6.1L3.2 9.9 9.3 9z'],
  upload: ['M12 16.6V4.6', 'm7 9.4 5-5 5 5', 'M4.6 15.6v2.4a1.6 1.6 0 0 0 1.6 1.6h11.6a1.6 1.6 0 0 0 1.6-1.6v-2.4'],
  layers: ['m12 3.4 8.4 4.5-8.4 4.5L3.6 7.9z', 'm4.4 12.4 7.6 4.1 7.6-4.1', 'm4.4 16.6 7.6 4.1 7.6-4.1'],
  search: ['M11 4.4a6.6 6.6 0 1 0 0 13.2 6.6 6.6 0 0 0 0-13.2Z', 'm16 16 4.2 4.2'],
  plus: ['M12 5v14', 'M5 12h14'],
  chevron: ['m7 10 5 5 5-5'],
  more: ['M6 12h.01', 'M12 12h.01', 'M18 12h.01'],
  undo: ['M8.6 7.4 4 12l4.6 4.6', 'M4 12h10.2a5.4 5.4 0 0 1 0 10.8H9.6'],
  redo: ['m15.4 7.4 4.6 4.6-4.6 4.6', 'M20 12H9.8a5.4 5.4 0 0 0 0 10.8h4.6'],
  close: ['m6 6 12 12', 'm18 6-12 12'],
  check: ['m4.5 12.6 4.8 4.8 10.2-10.2'],
  trash: ['M4.6 6.8h14.8', 'M9.4 6.8V4.6h5.2v2.2', 'M6.6 6.8 7.4 20h9.2l.8-13.2'],
  copy: ['M8.4 8.4h11.2v11.2H8.4z', 'M15.6 5.4H4.4v11.2h4'],
  download: ['M12 4v11.4', 'm7 10.4 5 5 5-5', 'M4.6 19.4h14.8'],
  play: ['M8 5.4 18.6 12 8 18.6z'],
  share: ['M8.4 12.8a2.6 2.6 0 1 0 0-1.6', 'm9.6 11 7.4-3.4', 'm9.6 12.8 7.4 3.4', 'M18.4 6.2a2.2 2.2 0 1 0 0 .1', 'M18.4 15.6a2.2 2.2 0 1 0 0 .1'],
  eye: ['M2.8 12s3.4-6.2 9.2-6.2S21.2 12 21.2 12s-3.4 6.2-9.2 6.2S2.8 12 2.8 12Z', 'M12 9.4a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 0-5.2Z'],
  eyeOff: ['M4 4.6 20 19.4', 'M9.8 6.2A9.8 9.8 0 0 1 12 5.8c5.8 0 9.2 6.2 9.2 6.2a17 17 0 0 1-3.2 3.8', 'M6.2 8a17 17 0 0 0-3.4 4s3.4 6.2 9.2 6.2a9.6 9.6 0 0 0 3.4-.6'],
  lock: ['M6.4 10.4h11.2v9.2H6.4z', 'M8.8 10.4V7.6a3.2 3.2 0 0 1 6.4 0v2.8'],
  unlock: ['M6.4 10.4h11.2v9.2H6.4z', 'M8.8 10.4V7.6a3.2 3.2 0 0 1 6.1-1.2'],
  text: ['M5 5.4h14', 'M12 5.4V19', 'M8.6 19h6.8'],
  image: ['M4 4.6h16v14.8H4z', 'M4 15.4 9 10.6l4 3.8 3-2.8 4 3.8', 'M15.4 8.4h.01'],
  shape: ['M3.6 3.6h8v8h-8z', 'M17.6 9.4a4.2 4.2 0 1 0 0 8.4 4.2 4.2 0 0 0 0-8.4Z'],
  sparkle: ['m12 3.4 1.8 5.4 5.4 1.8-5.4 1.8L12 17.8l-1.8-5.4-5.4-1.8 5.4-1.8z', 'M18.4 15.4l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z'],
  fullscreen: ['M4 9V4.4h4.6', 'M20 15v4.6h-4.6', 'M15.4 4.4H20V9', 'M8.6 19.6H4V15'],
  alignLeft: ['M4.4 5.4h15.2', 'M4.4 10.4h9.4', 'M4.4 15.4h15.2', 'M4.4 20h9.4'],
  alignCenter: ['M4.4 5.4h15.2', 'M7.3 10.4h9.4', 'M4.4 15.4h15.2', 'M7.3 20h9.4'],
  alignRight: ['M4.4 5.4h15.2', 'M10.2 10.4h9.4', 'M4.4 15.4h15.2', 'M10.2 20h9.4'],
  alignTop: ['M5.4 4.4v15.2', 'M10.4 4.4v9.4', 'M15.4 4.4v15.2', 'M20 4.4v9.4'],
  alignMiddle: ['M5.4 4.4v15.2', 'M10.4 7.3v9.4', 'M15.4 4.4v15.2', 'M20 7.3v9.4'],
  alignBottom: ['M5.4 4.4v15.2', 'M10.4 10.2v9.4', 'M15.4 4.4v15.2', 'M20 10.2v9.4'],
  toFront: ['M4.6 4.6h14.8', 'M12 20.4V8', 'm7.4 12.6 4.6-4.6 4.6 4.6'],
  forward: ['M12 20.4V5.6', 'm6.8 10.8 5.2-5.2 5.2 5.2'],
  backward: ['M12 3.6v14.8', 'm6.8 13.2 5.2 5.2 5.2-5.2'],
  toBack: ['M4.6 19.4h14.8', 'M12 3.6V16', 'm7.4 11.4 4.6 4.6 4.6-4.6'],
  duplicate: ['M8.4 8.4h11.2v11.2H8.4z', 'M15.6 5.4H4.4v11.2h4'],
  zoomIn: ['M11 4.4a6.6 6.6 0 1 0 0 13.2 6.6 6.6 0 0 0 0-13.2Z', 'm16 16 4.2 4.2', 'M11 8.2v5.6', 'M8.2 11h5.6'],
  zoomOut: ['M11 4.4a6.6 6.6 0 1 0 0 13.2 6.6 6.6 0 0 0 0-13.2Z', 'm16 16 4.2 4.2', 'M8.2 11h5.6'],
  fit: ['M4 8.4V4.4h4', 'M16 4.4h4v4', 'M20 15.6v4h-4', 'M8 19.6H4v-4'],
  page: ['M6.4 3.6h7.2l4 4v12.8H6.4z', 'M13.4 3.6v4.2h4.2'],
};

export function isEditableTarget(target) {
  return Boolean(
    target &&
      (target.isContentEditable ||
        /^(INPUT|TEXTAREA|SELECT|OPTION)$/.test(target.tagName || '')),
  );
}

export function formatRelative(timestamp) {
  const delta = Date.now() - timestamp;
  if (!Number.isFinite(delta)) return '';
  if (delta < 60_000) return 'just now';
  const minutes = Math.floor(delta / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days}d ago`;
  return new Date(timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

let toastHost = null;

export function toast(message, kind = 'default') {
  if (!toastHost) {
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
  }, 2300);
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = el('a', { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 4000);
}

let closeOpenMenu = null;

export function openMenu(anchor, items, options = {}) {
  if (closeOpenMenu) closeOpenMenu();
  const menu = el('div', { class: 'pop-menu', role: 'menu' });
  for (const item of items) {
    if (!item) continue;
    if (item.separator) {
      menu.append(el('div', { class: 'pop-sep' }));
      continue;
    }
    const button = el(
      'button',
      {
        class: `pop-item${item.danger ? ' is-danger' : ''}${item.active ? ' is-active' : ''}`,
        type: 'button',
        role: 'menuitem',
        disabled: item.disabled,
      },
      [
        item.icon ? svgIcon(item.icon, 18) : el('span', { class: 'pop-icon-space' }),
        el('span', { class: 'pop-label', text: item.label }),
        item.hint ? el('span', { class: 'pop-hint', text: item.hint }) : null,
      ],
    );
    button.addEventListener('click', () => {
      close();
      item.onSelect?.();
    });
    menu.append(button);
  }

  document.body.append(menu);

  const rect = anchor.getBoundingClientRect();
  const menuRect = menu.getBoundingClientRect();
  let left = options.align === 'right' ? rect.right - menuRect.width : rect.left;
  let top = rect.bottom + 8;
  if (top + menuRect.height > window.innerHeight - 12) {
    top = Math.max(12, rect.top - menuRect.height - 8);
  }
  left = clamp(left, 12, window.innerWidth - menuRect.width - 12);
  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
  requestAnimationFrame(() => menu.classList.add('is-in'));

  function close() {
    if (closeOpenMenu !== close) return;
    closeOpenMenu = null;
    document.removeEventListener('pointerdown', onOutside, true);
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', close);
    window.removeEventListener('scroll', close, true);
    menu.remove();
  }
  function onOutside(event) {
    if (!menu.contains(event.target)) close();
  }
  function onKey(event) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      close();
    }
  }
  closeOpenMenu = close;
  document.addEventListener('pointerdown', onOutside, true);
  document.addEventListener('keydown', onKey, true);
  window.addEventListener('resize', close);
  window.addEventListener('scroll', close, true);
  return menu;
}

export function openModal({ title, subtitle, content, actions = [] }) {
  const layer = el('div', { class: 'modal-layer', role: 'dialog', 'aria-modal': 'true' });
  const card = el('div', { class: 'modal-card' });
  const header = el('div', { class: 'modal-head' }, [
    el('div', {}, [
      el('h2', { class: 'modal-title', text: title }),
      subtitle ? el('p', { class: 'modal-sub', text: subtitle }) : null,
    ]),
  ]);
  const closeButton = el('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Close' }, svgIcon(ICONS.close));
  header.append(closeButton);
  card.append(header, el('div', { class: 'modal-body' }, content));

  if (actions.length) {
    const footer = el('div', { class: 'modal-foot' });
    for (const action of actions) {
      const button = el('button', {
        class: `btn ${action.variant || 'ghost'}`,
        type: 'button',
        text: action.label,
      });
      button.addEventListener('click', () => {
        if (action.onSelect?.() === false) return;
        close();
      });
      footer.append(button);
    }
    card.append(footer);
  }

  layer.append(card);
  document.body.append(layer);
  requestAnimationFrame(() => layer.classList.add('is-in'));

  function close() {
    document.removeEventListener('keydown', onKey, true);
    layer.classList.remove('is-in');
    window.setTimeout(() => layer.remove(), 160);
  }
  function onKey(event) {
    if (event.key === 'Escape') close();
  }
  closeButton.addEventListener('click', close);
  layer.addEventListener('pointerdown', (event) => {
    if (event.target === layer) close();
  });
  document.addEventListener('keydown', onKey, true);
  return { close, card };
}
