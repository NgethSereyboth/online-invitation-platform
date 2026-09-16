/**
 * src/js/editor/chrome/pages.js — Editor pages sidebar with thumbnails (ROADMAP §3.4.2, v0.57.0).
 *
 * Vertical strip of page thumbnails, 150px wide:
 *   • Click thumbnail → jump to that page.
 *   • Drag thumbnail → reorder pages.
 *   • Right-click → context menu (duplicate / delete / insert above / below).
 *   • "+" button → add a new blank page.
 *   • Hover between two thumbnails → reveal a small "insert here" affordance.
 *
 * Thumbnails render at 150px wide using `OffscreenCanvas` when available
 * (the editor's typography renderer is used to draw the page contents at a
 * small scale). Re-rendering is debounced 300ms after any editor-state change
 * so dragging sliders doesn't thrash the canvas. Each page's thumbnail is
 * cached by an object-fingerprint of that page's element tree, so unchanged
 * pages skip the re-render entirely.
 *
 * Public API:
 *   EInviteChromePages.mount(container?) → mounts the sidebar
 *   EInviteChromePages.refresh()         → debounced re-render
 *   EInviteChromePages.addPage()         → appends a new blank page
 *   EInviteChromePages.duplicate(id)     → duplicates a page
 *   EInviteChromePages.delete(id)        → deletes a page
 *   EInviteChromePages.insertAt(idx)     → inserts a blank page at index
 *   EInviteChromePages.activate(id)      → jumps to a page
 *   EInviteChromePages.reorder(srcId, dstId) → moves srcId before dstId
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteChromePages) return;

  const THUMB_WIDTH = 150;
  const THUMB_HEIGHT = 100;
  const DEBOUNCE_MS = 300;

  const STRINGS = {
    en: {
      title: 'Pages', add: 'Add page', duplicate: 'Duplicate page',
      delete: 'Delete page', insertAbove: 'Insert page above',
      insertBelow: 'Insert page below', empty: 'No design pages yet',
      pageLabel: (n) => `Page ${n}`, mainHero: 'Main hero',
      thumbnail: 'Page thumbnail', active: 'Active page'
    },
    km: {
      title: 'ទំព័រ', add: 'បន្ថែមទំព័រ', duplicate: 'ចម្លងទំព័រ',
      delete: 'លុបទំព័រ', insertAbove: 'បញ្ចូលទំព័រខាងលើ',
      insertBelow: 'បញ្ចូលទំព័រខាងក្រោម', empty: 'មិនទាន់មានទំព័រទេ',
      pageLabel: (n) => `ទំព័រ ${n}`, mainHero: 'ទំព័រមេ',
      thumbnail: 'រូបភាពទំព័រតូច', active: 'ទំព័រសកម្ម'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key, ...args) {
    const v = (STRINGS[locale()] || STRINGS.en)[key];
    return typeof v === 'function' ? v(...args) : (v || key);
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function bridge() { return window.EInviteEditorBridge || null; }
  function registry() { return window.EInviteCommandRegistry || null; }

  /** Module state. */
  const state = {
    host: null,
    root: null,
    stripEl: null,
    emptyEl: null,
    collapsed: false,
    debounceTimer: 0,
    cache: new Map(),     // pageId → { fingerprint, dataUrl }
    dragSrcId: null,
    menuEl: null
  };

  /** Fingerprint a page's element tree so we can cache its thumbnail. */
  function fingerprint(page) {
    try {
      const objects = page?.objects || {};
      const sig = JSON.stringify({
        n: Object.keys(objects).length,
        bg: page?.background, bgImg: page?.backgroundImage,
        overlay: page?.backgroundOverlay, size: page?.backgroundSize,
        keys: Object.keys(objects).sort(),
        // include a shallow per-object signature so position changes invalidate.
        objs: Object.values(objects).map((o) => `${o.type || o.kind || 'el'}:${o.x || 0}:${o.y || 0}:${o.w || o.width || 0}:${o.h || o.height || 0}:${o.text || ''}`.slice(0, 120))
      });
      let h = 5381;
      for (let i = 0; i < sig.length; i++) h = ((h << 5) + h + sig.charCodeAt(i)) >>> 0;
      return h.toString(36);
    } catch { return Math.random().toString(36).slice(2); }
  }

  /** Render a page to a thumbnail data URL. Uses OffscreenCanvas if available. */
  function renderThumbnail(page) {
    const fp = fingerprint(page);
    const cached = state.cache.get(page?.id);
    if (cached && cached.fingerprint === fp) return cached.dataUrl;
    const canvas = (typeof OffscreenCanvas !== 'undefined')
      ? new OffscreenCanvas(THUMB_WIDTH, THUMB_HEIGHT)
      : Object.assign(document.createElement('canvas'), { width: THUMB_WIDTH, height: THUMB_HEIGHT });
    const ctx = canvas.getContext('2d');
    // Background.
    ctx.fillStyle = page?.background || '#ffffff';
    ctx.fillRect(0, 0, THUMB_WIDTH, THUMB_HEIGHT);
    if (page?.backgroundImage) {
      try {
        ctx.fillStyle = 'rgba(0,0,0,0.2)';
        ctx.fillRect(0, 0, THUMB_WIDTH, THUMB_HEIGHT);
      } catch { /* ignore */ }
    }
    // Render objects via the typography renderer if available.
    try {
      if (window.EInviteTypographyRendererAdapters?.renderPage) {
        window.EInviteTypographyRendererAdapters.renderPage(canvas, page, { width: THUMB_WIDTH, height: THUMB_HEIGHT });
      } else {
        drawFallbackObjects(ctx, page);
      }
    } catch { drawFallbackObjects(ctx, page); }
    let dataUrl;
    try { dataUrl = canvas.toDataURL ? canvas.toDataURL('image/png') : ''; }
    catch { dataUrl = ''; }
    state.cache.set(page?.id, { fingerprint: fp, dataUrl });
    return dataUrl;
  }

  function drawFallbackObjects(ctx, page) {
    const objects = page?.objects || {};
    for (const obj of Object.values(objects)) {
      const x = (Number(obj.x) || 0) * (THUMB_WIDTH / 390);
      const y = (Number(obj.y) || 0) * (THUMB_HEIGHT / 844);
      const w = (Number(obj.w || obj.width) || 40) * (THUMB_WIDTH / 390);
      const h = (Number(obj.h || obj.height) || 40) * (THUMB_HEIGHT / 844);
      ctx.fillStyle = obj.background || obj.color || '#94a3b8';
      ctx.fillRect(x, y, Math.max(2, w), Math.max(2, h));
      if (obj.text) {
        ctx.fillStyle = '#ffffff';
        ctx.font = '6px sans-serif';
        ctx.fillText(String(obj.text).slice(0, 12), x + 2, y + 8);
      }
    }
  }

  function build() {
    if (state.root) return state.root;
    const host = document.getElementById('pagesSidebar');
    state.host = host || null;
    const root = state.host || document.createElement('aside');
    if (!state.host) {
      root.id = 'pagesSidebar';
      root.className = 'ei-chrome-panel ei-pages-sidebar';
      root.setAttribute('aria-label', t('title'));
    }
    root.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" data-action="add" aria-label="${t('add')}">＋</button>
      </header>
      <div class="ei-pages-strip" role="list" aria-label="${t('title')}"></div>
      <div class="ei-pages-empty" hidden>${t('empty')}</div>
    `;
    if (!state.host) document.body.appendChild(root);
    state.root = root;
    state.stripEl = $('.ei-pages-strip', root);
    state.emptyEl = $('.ei-pages-empty', root);
    $('[data-action="add"]', root).addEventListener('click', addPage);
    state.stripEl.addEventListener('contextmenu', onContextMenu);
    return root;
  }

  function buildRow(page, idx, isActive) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'ei-page-row';
    row.dataset.id = page.id;
    row.setAttribute('role', 'listitem');
    row.draggable = true;
    row.tabIndex = 0;
    row.setAttribute('aria-label', `${page.name || t('pageLabel', idx + 1)} — ${t('thumbnail')}`);
    row.classList.toggle('is-active', isActive);
    const dataUrl = renderThumbnail(page);
    row.innerHTML = `
      <img class="ei-page-thumb" alt="" width="${THUMB_WIDTH}" height="${THUMB_HEIGHT}" ${dataUrl ? `src="${dataUrl}"` : 'hidden'}>
      <span class="ei-page-label"></span>
    `;
    $('.ei-page-label', row).textContent = page.name || t('pageLabel', idx + 1);
    bindRow(row, page.id);
    return row;
  }

  function buildInsertBetween(idx) {
    const slot = document.createElement('div');
    slot.className = 'ei-pages-insert-slot';
    slot.setAttribute('aria-hidden', 'true');
    slot.dataset.insertAt = String(idx);
    slot.innerHTML = '<span class="ei-pages-insert-plus" hidden>＋</span>';
    slot.addEventListener('mouseenter', () => $('.ei-pages-insert-plus', slot).hidden = false);
    slot.addEventListener('mouseleave', () => $('.ei-pages-insert-plus', slot).hidden = true);
    slot.addEventListener('click', () => insertAt(idx));
    return slot;
  }

  function bindRow(row, id) {
    row.addEventListener('click', () => activate(id));
    row.addEventListener('dragstart', (event) => {
      state.dragSrcId = id;
      row.classList.add('is-dragging');
      event.dataTransfer?.setData('text/plain', id);
      event.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => {
      row.classList.remove('is-dragging');
      state.dragSrcId = null;
    });
    row.addEventListener('dragover', (event) => {
      if (!state.dragSrcId || state.dragSrcId === id) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      row.classList.add('is-drop-target');
    });
    row.addEventListener('dragleave', () => row.classList.remove('is-drop-target'));
    row.addEventListener('drop', (event) => {
      event.preventDefault();
      row.classList.remove('is-drop-target');
      if (!state.dragSrcId || state.dragSrcId === id) return;
      reorder(state.dragSrcId, id);
    });
    row.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(id); }
    });
  }

  function onContextMenu(event) {
    const row = event.target.closest('.ei-page-row');
    if (!row) return;
    event.preventDefault();
    const id = row.dataset.id;
    ensureMenu().then((menu) => {
      menu.dataset.pageId = id;
      menu.style.left = `${event.clientX}px`;
      menu.style.top = `${event.clientY}px`;
      menu.hidden = false;
    });
  }

  function ensureMenu() {
    if (state.menuEl) return Promise.resolve(state.menuEl);
    const menu = document.createElement('div');
    menu.className = 'ei-pages-context-menu';
    menu.hidden = true;
    menu.setAttribute('role', 'menu');
    menu.innerHTML = `
      <button role="menuitem" data-action="duplicate">${t('duplicate')}</button>
      <button role="menuitem" data-action="insertAbove">${t('insertAbove')}</button>
      <button role="menuitem" data-action="insertBelow">${t('insertBelow')}</button>
      <button role="menuitem" data-action="delete" class="danger">${t('delete')}</button>
    `;
    document.body.appendChild(menu);
    menu.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-action]'); if (!btn) return;
      const id = menu.dataset.pageId; if (!id) return;
      const idx = pageIdx(id);
      if (btn.dataset.action === 'duplicate') duplicate(id);
      else if (btn.dataset.action === 'delete') deletePage(id);
      else if (btn.dataset.action === 'insertAbove') insertAt(idx);
      else if (btn.dataset.action === 'insertBelow') insertAt(idx + 1);
      menu.hidden = true;
    });
    document.addEventListener('click', (event) => {
      if (!menu.hidden && !menu.contains(event.target)) menu.hidden = true;
    }, { once: true });
    state.menuEl = menu;
    return Promise.resolve(menu);
  }

  function pageIdx(id) {
    const b = bridge(); if (!b) return -1;
    const state_ = b.getState?.() || {};
    const pages = state_.designPages || [];
    return pages.findIndex((p) => p.id === id);
  }

  function activeCanvasId() {
    return bridge()?.getActiveCanvasId?.() || 'hero';
  }

  /** Build the strip with hero + design pages. */
  function refresh() {
    if (!state.root) build();
    const b = bridge();
    const doc = b?.getState?.() || {};
    const pages = doc.designPages || [];
    const active = activeCanvasId();
    state.stripEl.replaceChildren();
    // Hero canvas row.
    const heroRow = document.createElement('button');
    heroRow.type = 'button';
    heroRow.className = 'ei-page-row is-hero';
    heroRow.dataset.id = 'hero';
    heroRow.setAttribute('role', 'listitem');
    heroRow.draggable = false;
    heroRow.tabIndex = 0;
    heroRow.classList.toggle('is-active', active === 'hero');
    heroRow.innerHTML = `
      <div class="ei-page-thumb ei-page-thumb--hero" aria-hidden="true">M</div>
      <span class="ei-page-label">${t('mainHero')}</span>
    `;
    heroRow.addEventListener('click', () => activate('hero'));
    state.stripEl.appendChild(heroRow);
    state.stripEl.appendChild(buildInsertBetween(0));
    pages.forEach((page, idx) => {
      const row = buildRow(page, idx, active === `page:${page.id}`);
      state.stripEl.appendChild(row);
      state.stripEl.appendChild(buildInsertBetween(idx + 1));
    });
    state.emptyEl.hidden = pages.length > 0;
  }

  /** Debounced refresh — called on every editor-state change. */
  function scheduleRefresh() {
    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(refresh, DEBOUNCE_MS);
  }

  function activate(id) {
    const b = bridge(); if (!b) return;
    const token = id === 'hero' ? 'hero' : `page:${id}`;
    if (window.switchCanvas) window.switchCanvas(token);
    else if (typeof b.setActiveCanvasId === 'function') b.setActiveCanvasId(token);
    refresh();
  }

  function addPage() {
    if (window.EInvitePageExperience?.addPage) return window.EInvitePageExperience.addPage({ mode: 'free-design' });
    const b = bridge(); if (!b) return;
    b.transact?.('Add page', (state_) => {
      const id = `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      (state_.designPages = state_.designPages || []).push({ id, name: '', objects: {} });
    });
    scheduleRefresh();
  }

  function insertAt(idx) {
    const b = bridge(); if (!b) return;
    b.transact?.('Insert page', (state_) => {
      const id = `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const pages = state_.designPages = state_.designPages || [];
      pages.splice(Math.max(0, Math.min(idx, pages.length)), 0, { id, name: '', objects: {} });
    });
    scheduleRefresh();
  }

  function duplicate(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Duplicate page', (state_) => {
      const pages = state_.designPages = state_.designPages || [];
      const srcIdx = pages.findIndex((p) => p.id === id);
      if (srcIdx < 0) return;
      const src = pages[srcIdx];
      const copy = JSON.parse(JSON.stringify(src));
      copy.id = `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      copy.name = `${src.name || 'Page'} copy`;
      // Remap object ids so duplicates remain editable.
      const remap = {};
      copy.objects = Object.fromEntries(Object.entries(src.objects || {}).map(([k, v], i) => {
        const nk = `${copy.id}-o${i}-${Math.random().toString(36).slice(2, 5)}`;
        remap[k] = nk;
        return [nk, JSON.parse(JSON.stringify(v))];
      }));
      pages.splice(srcIdx + 1, 0, copy);
    });
    scheduleRefresh();
  }

  function deletePage(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Delete page', (state_) => {
      state_.designPages = (state_.designPages || []).filter((p) => p.id !== id);
    });
    scheduleRefresh();
  }

  function reorder(srcId, dstId) {
    const b = bridge(); if (!b) return;
    b.transact?.('Reorder pages', (state_) => {
      const pages = state_.designPages = state_.designPages || [];
      const from = pages.findIndex((p) => p.id === srcId);
      const to = pages.findIndex((p) => p.id === dstId);
      if (from < 0 || to < 0 || from === to) return;
      const [moved] = pages.splice(from, 1);
      pages.splice(to, 0, moved);
    });
    scheduleRefresh();
  }

  function mount(container) {
    build();
    if (container && state.root.parentElement !== container) container.appendChild(state.root);
    refresh();
    window.addEventListener('einvite:editor-command', scheduleRefresh);
    window.addEventListener('einvite:editor-state-replaced', scheduleRefresh);
    return state.root;
  }

  function registerCommands() {
    const r = registry(); if (!r?.register) return;
    try {
      r.register({
        id: 'pages.toggleSidebar', title: 'Toggle pages sidebar',
        category: 'View', keywords: ['pages', 'sidebar', 'thumbnails'],
        bindings: { standard: ['Alt+P'], canva: ['Alt+P'], photoshop: ['Alt+P'] },
        run: () => { if (state.root) state.root.hidden = !state.root.hidden; }
      });
      r.register({
        id: 'pages.add', title: 'Add new page',
        category: 'Insert', keywords: ['page', 'add', 'new'],
        bindings: { standard: ['Mod+Enter'], canva: ['Mod+Enter'], photoshop: ['Mod+Enter'] },
        run: addPage
      });
    } catch { /* duplicate — ignore */ }
  }

  window.EInviteChromePages = Object.freeze({
    version: 57, STRINGS, mount, refresh: scheduleRefresh, addPage,
    duplicate, delete: deletePage, insertAt, activate, reorder, registerCommands
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { mount(); registerCommands(); });
  } else {
    queueMicrotask(() => { mount(); registerCommands(); });
  }
})();
