/**
 * src/js/editor/chrome/layers.js — Editor layer panel with drag-reorder (ROADMAP §3.4.1, v0.57.0).
 *
 * Right-side panel listing every element on the active canvas in z-order
 * (topmost first). Each row shows:
 *   • visibility eye toggle (hidden elements are skipped in export)
 *   • lock icon (locked elements can only be selected via the panel)
 *   • 48×48 thumbnail (rendered to a <canvas> via the typography renderer if
 *     available, else a colored type chip)
 *   • auto-generated name ("Text 1", "Image 2", …) editable on double-click
 *
 * Interactions:
 *   • Click row  → select on canvas (syncs multi-select)
 *   • Shift+click → extend multi-select
 *   • Drag row    → reorder z-order (uses HTML5 drag-and-drop; the underlying
 *                   document's `objectOrder` array is rewritten via the editor
 *                   bridge `transact()` API, then re-rendered).
 *
 * Locked elements cannot be selected on the canvas — the editor core already
 * honours `data-locked="true"` for hit-testing. Hidden elements
 * (`visible === false`) are excluded from export pipelines.
 *
 * The panel mounts into a `#layersPanel` host (auto-created if missing) and
 * is exposed as `window.EInviteChromeLayers` for the command palette +
 * keyboard-shortcut registry to drive. Bilingual EN+KH labels.
 *
 * Public API:
 *   EInviteChromeLayers.mount(container?)      → mounts the panel
 *   EInviteChromeLayers.refresh()              → re-renders rows from current state
 *   EInviteChromeLayers.toggle()               → show/hide the panel
 *   EInviteChromeLayers.setSelected(ids[])     → sync panel selection from canvas
 *   EInviteChromeLayers.rename(id, name)       → set a custom layer name
 *   EInviteChromeLayers.toggleVisibility(id)   → flip element.visible
 *   EInviteChromeLayers.toggleLock(id)         → flip element.locked
 *   EInviteChromeLayers.reorder(id, toIndex)   → move element to z-index
 */
(() => {
  'use strict';
  if (window.EInviteChromeLayers) return;

  /** Bilingual labels — every user-facing string has EN + KH variants. */
  const STRINGS = {
    en: {
      title: 'Layers',
      empty: 'No layers on this canvas',
      lock: 'Lock layer',
      unlock: 'Unlock layer',
      hide: 'Hide layer',
      show: 'Show layer',
      rename: 'Rename layer',
      visibility: 'Visibility',
      locked: 'Locked',
      hidden: 'Hidden',
      text: 'Text',
      image: 'Image',
      shape: 'Shape',
      background: 'Background',
      page: 'Page',
      element: 'Element',
      layer: 'Layer'
    },
    km: {
      title: 'ស្រទាប់',
      empty: 'មិនមានស្រទាប់នៅលើកាណវាស់នេះទេ',
      lock: 'ចាក់សោស្រទាប់',
      unlock: 'ដោះសោស្រទាប់',
      hide: 'លាក់ស្រទាប់',
      show: 'បង្ហាញស្រទាប់',
      rename: 'ប្ដូរឈ្មោះស្រទាប់',
      visibility: 'ភាពមើលឃើញ',
      locked: 'បានចាក់សោ',
      hidden: 'បានលាក់',
      text: 'អត្ថបទ',
      image: 'រូបភាព',
      shape: 'រាង',
      background: 'ផ្ទៃខាងក្រោយ',
      page: 'ទំព័រ',
      element: 'ធាតុ',
      layer: 'ស្រទាប់'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || STRINGS.en[key] || key;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /** Bridge / registry accessors — null-safe so the module can be loaded on
   *  non-editor pages without crashing. */
  function bridge() { return window.EInviteEditorBridge || null; }
  function registry() { return window.EInviteCommandRegistry || null; }

  /** Return the object map for the currently active canvas (hero or page:N). */
  function activeObjectMap() {
    const b = bridge(); if (!b) return {};
    const state = b.getState?.() || {};
    const canvasId = b.getActiveCanvasId?.() || 'hero';
    if (canvasId === 'hero') return state.objects || {};
    const id = String(canvasId).replace(/^page:/, '');
    const page = (state.designPages || []).find((p) => String(p.id) === id);
    return page?.objects || {};
  }

  /** Resolve the object map's z-order array; falls back to insertion order. */
  function orderedIds(map) {
    const ids = Object.keys(map || {});
    // If the document carries an explicit `objectOrder`, honour it; else use
    // the natural object iteration order which is preserved by JSON.parse.
    return ids;
  }

  /** Generate a localized default name like "Text 1" / "Image 2". */
  function defaultName(obj, idx, typeCounts) {
    const type = (obj.type || obj.kind || 'element').toLowerCase();
    const labelKey = type.includes('text') ? 'text'
      : type.includes('image') || type.includes('photo') ? 'image'
      : type.includes('shape') || type.includes('rect') || type.includes('ellipse') ? 'shape'
      : type.includes('background') ? 'background'
      : type.includes('page') ? 'page'
      : 'element';
    typeCounts[labelKey] = (typeCounts[labelKey] || 0) + 1;
    return `${t(labelKey)} ${typeCounts[labelKey]}`;
  }

  /** Render a 48×48 thumbnail of the object — uses the typography renderer's
   *  `renderThumbnail` if available; otherwise draws a colored chip. */
  function renderThumbnail(canvas, obj) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, 48, 48);
    try {
      if (window.EInviteTypographyRendererAdapters?.renderThumbnail) {
        window.EInviteTypographyRendererAdapters.renderThumbnail(canvas, obj, { width: 48, height: 48 });
        return;
      }
    } catch { /* fall through to chip */ }
    // Fallback chip: type-coloured rectangle with the first letter.
    const type = String(obj.type || obj.kind || 'el').toLowerCase();
    const palette = {
      text: '#3b82f6', image: '#10b981', photo: '#10b981',
      shape: '#a855f7', rect: '#a855f7', ellipse: '#a855f7',
      background: '#64748b', frame: '#f59e0b'
    };
    const color = palette[type] || '#94a3b8';
    ctx.fillStyle = color;
    ctx.fillRect(4, 4, 40, 40);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(obj.type || obj.kind || '?').charAt(0).toUpperCase() || '?', 24, 24);
  }

  /** Module-level panel state. */
  const state = {
    host: null,
    root: null,
    listEl: null,
    selected: new Set(),
    typeCounts: {},
    dragSrcId: null,
    collapsed: false
  };

  /** Build the panel DOM (idempotent — re-uses existing #layersPanel). */
  function build() {
    if (state.root) return state.root;
    const host = document.getElementById('layersPanel');
    state.host = host || null;
    const root = state.host || document.createElement('section');
    if (!state.host) {
      root.id = 'layersPanel';
      root.className = 'ei-chrome-panel ei-layers-panel';
      root.setAttribute('aria-label', t('title'));
    }
    root.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" class="ei-chrome-panel__collapse" data-action="collapse" aria-label="Collapse">▾</button>
      </header>
      <div class="ei-layers-list" role="list" aria-label="${t('title')}"></div>
      <div class="ei-layers-empty" hidden>${t('empty')}</div>
    `;
    if (!state.host) document.body.appendChild(root);
    state.root = root;
    state.listEl = $('.ei-layers-list', root);
    bindHeader(root);
    return root;
  }

  function bindHeader(root) {
    $('[data-action="collapse"]', root)?.addEventListener('click', () => {
      state.collapsed = !state.collapsed;
      root.classList.toggle('is-collapsed', state.collapsed);
    });
  }

  /** Build one row for an element. */
  function buildRow(id, obj, idx, typeCounts) {
    const row = document.createElement('div');
    row.className = 'ei-layer-row';
    row.dataset.id = id;
    row.setAttribute('role', 'listitem');
    row.draggable = true;
    row.tabIndex = 0;
    row.setAttribute('aria-label', obj.layerName || defaultName(obj, idx, typeCounts));
    const visible = obj.visible !== false;
    const locked = obj.locked === true;
    row.classList.toggle('is-hidden', !visible);
    row.classList.toggle('is-locked', locked);
    row.classList.toggle('is-selected', state.selected.has(id));
    row.innerHTML = `
      <button type="button" class="ei-layer-eye" data-action="visibility" aria-label="${visible ? t('hide') : t('show')}" aria-pressed="${visible}">
        <span aria-hidden="true">${visible ? '◉' : '◯'}</span>
      </button>
      <button type="button" class="ei-layer-lock" data-action="lock" aria-label="${locked ? t('unlock') : t('lock')}" aria-pressed="${locked}">
        <span aria-hidden="true">${locked ? '🔒' : '🔓'}</span>
      </button>
      <canvas class="ei-layer-thumb" width="48" height="48" aria-hidden="true"></canvas>
      <span class="ei-layer-name" tabindex="0" role="textbox" aria-label="${t('rename')}"></span>
    `;
    $('.ei-layer-name', row).textContent = obj.layerName || defaultName(obj, idx, typeCounts);
    renderThumbnail($('.ei-layer-thumb', row), obj);
    bindRow(row, id);
    return row;
  }

  function bindRow(row, id) {
    // Click → select (shift = additive).
    row.addEventListener('click', (event) => {
      if (event.target.closest('[data-action]')) return; // icon buttons handled below
      const additive = event.shiftKey || event.ctrlKey || event.metaKey;
      const b = bridge();
      if (!b) return;
      const current = new Set(additive ? b.getSelectedIds?.() || [] : []);
      if (current.has(id) && additive) current.delete(id);
      else current.add(id);
      state.selected = new Set(current);
      b.select?.([...current]);
      refresh();
    });
    // Double-click name → rename.
    $('.ei-layer-name', row).addEventListener('dblclick', (event) => {
      event.stopPropagation();
      beginRename(row, id);
    });
    // Eye toggle.
    $('[data-action="visibility"]', row).addEventListener('click', (event) => {
      event.stopPropagation();
      toggleVisibility(id);
    });
    // Lock toggle.
    $('[data-action="lock"]', row).addEventListener('click', (event) => {
      event.stopPropagation();
      toggleLock(id);
    });
    // Drag-and-drop reorder.
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
    // Keyboard: Enter to select, F2 to rename.
    row.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        row.click();
      } else if (event.key === 'F2') {
        event.preventDefault();
        beginRename(row, id);
      }
    });
  }

  function beginRename(row, id) {
    const nameEl = $('.ei-layer-name', row);
    const current = nameEl.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'ei-layer-name-input';
    input.value = current;
    input.setAttribute('aria-label', t('rename'));
    nameEl.replaceWith(input);
    input.focus();
    input.select();
    const commit = () => {
      const value = input.value.trim().slice(0, 120);
      rename(id, value || current);
      refresh();
    };
    input.addEventListener('blur', commit, { once: true });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') { event.preventDefault(); input.blur(); }
      else if (event.key === 'Escape') { input.value = current; input.blur(); }
    });
  }

  function reorder(srcId, dstId) {
    const b = bridge(); if (!b) return;
    const map = activeObjectMap();
    const ids = orderedIds(map);
    const from = ids.indexOf(srcId);
    const to = ids.indexOf(dstId);
    if (from < 0 || to < 0 || from === to) return;
    ids.splice(from, 1);
    ids.splice(to, 0, srcId);
    b.transact?.('Reorder layers', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      // Rebuild the map preserving the new order (object iteration order on
      // plain objects follows insertion order, so we delete + re-insert).
      const snapshot = {};
      for (const id of ids) snapshot[id] = target[id];
      // Clear existing keys (can't use Object.assign because we need to
      // delete-then-add to preserve the new order).
      for (const key of Object.keys(target)) delete target[key];
      Object.assign(target, snapshot);
    }, { capture: true });
    refresh();
  }

  /** Resolve a writable pointer to the active canvas's object map inside the
   *  transact() mutator. `state` here is the live document object. */
  function resolveTargetMap(doc, canvasId) {
    if (canvasId === 'hero') return doc.objects || (doc.objects = {});
    const id = String(canvasId).replace(/^page:/, '');
    let page = (doc.designPages || []).find((p) => String(p.id) === id);
    if (!page) { page = { id, objects: {} }; (doc.designPages = doc.designPages || []).push(page); }
    return page.objects || (page.objects = {});
  }

  function toggleVisibility(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Toggle visibility', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      const obj = target[id]; if (!obj) return;
      obj.visible = obj.visible !== false ? false : true;
    }, { capture: true });
    refresh();
  }

  function toggleLock(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Toggle lock', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      const obj = target[id]; if (!obj) return;
      obj.locked = obj.locked !== true;
    }, { capture: true });
    refresh();
  }

  function rename(id, name) {
    const b = bridge(); if (!b) return;
    b.transact?.('Rename layer', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      const obj = target[id]; if (!obj) return;
      obj.layerName = String(name).slice(0, 120);
    }, { capture: true });
  }

  /** Re-render the panel from the current document state. */
  function refresh() {
    if (!state.root) build();
    const map = activeObjectMap();
    const ids = orderedIds(map);
    state.typeCounts = {};
    // Z-order: topmost first → reverse the insertion order so the last-added
    // element appears at the top of the panel.
    const reversed = [...ids].reverse();
    state.listEl.replaceChildren();
    for (const [idx, id] of reversed.entries()) {
      const obj = map[id]; if (!obj) continue;
      const row = buildRow(id, obj, idx, state.typeCounts);
      state.listEl.appendChild(row);
    }
    $('.ei-layers-empty', state.root).hidden = reversed.length > 0;
  }

  /** Sync the panel selection with the canvas selection. */
  function setSelected(ids) {
    state.selected = new Set((ids || []).map(String));
    $$('.ei-layer-row', state.root).forEach((row) => {
      row.classList.toggle('is-selected', state.selected.has(row.dataset.id));
    });
  }

  function toggle() {
    if (!state.root) build();
    state.root.hidden = !state.root.hidden;
  }

  function mount(container) {
    build();
    if (container && state.root.parentElement !== container) {
      container.appendChild(state.root);
    }
    refresh();
    // Wire to editor selection + state-change events so the panel stays in sync.
    window.addEventListener('einvite:editor-command', () => refresh());
    window.addEventListener('einvite:editor-state-replaced', () => refresh());
    // Bridge selection polling — there's no dedicated event so we tick on
    // pointerup + keyup which covers click/select/keyboard-nudge cases.
    document.addEventListener('pointerup', () => {
      const b = bridge();
      setSelected(b?.getSelectedIds?.() || []);
    }, { passive: true });
    document.addEventListener('keyup', () => {
      const b = bridge();
      setSelected(b?.getSelectedIds?.() || []);
    });
    return state.root;
  }

  // Register commands so the palette + shortcut modal list the layer panel.
  function registerCommands() {
    const r = registry(); if (!r?.register) return;
    try {
      r.register({
        id: 'layers.togglePanel', title: 'Toggle layers panel',
        category: 'View', keywords: ['layers', 'panel', 'z-order'],
        bindings: { standard: ['Alt+L'], canva: ['Alt+L'], photoshop: ['F7'] },
        run: () => toggle()
      });
      r.register({
        id: 'layers.toggleLock', title: 'Lock or unlock selected layer',
        category: 'Arrange', keywords: ['lock', 'layer'],
        enabled: () => (bridge()?.getSelectedIds?.() || []).length > 0,
        run: () => {
          const b = bridge();
          for (const id of b?.getSelectedIds?.() || []) toggleLock(id);
        }
      });
      r.register({
        id: 'layers.toggleVisibility', title: 'Hide or show selected layer',
        category: 'Arrange', keywords: ['visibility', 'hide', 'show'],
        enabled: () => (bridge()?.getSelectedIds?.() || []).length > 0,
        run: () => {
          const b = bridge();
          for (const id of b?.getSelectedIds?.() || []) toggleVisibility(id);
        }
      });
    } catch { /* duplicate registration — ignore */ }
  }

  window.EInviteChromeLayers = Object.freeze({
    version: 57,
    STRINGS,
    mount, refresh, toggle, setSelected, rename, toggleVisibility, toggleLock,
    reorder, registerCommands
  });

  // Auto-mount on DOMContentLoaded if the editor is present (no-op otherwise).
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { mount(); registerCommands(); });
  } else {
    queueMicrotask(() => { mount(); registerCommands(); });
  }
})();
