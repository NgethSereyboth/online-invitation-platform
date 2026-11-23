// Editor shell. Owns the design document, history and selection; wires the
// board, panels, page strip, inspector and top bar together.

import { debounce } from '../batch.js';
import { CANVAS_LIMITS, designFromTemplate, findPreset, PAGE_PRESETS } from '../model.js';
import { canvasToBlob, ensureFonts, renderPageToCanvas } from '../render.js';
import { createNewDesign, getDesign, saveDesign, deleteDesign, duplicateDesign } from '../storage.js';
import { $, deepClone, downloadBlob, el, isEditableTarget, openMenu, svgIcon, toast, ICONS } from '../util.js';
import { History } from '../history.js';
import { Board } from './board.js';
import { mountPages } from './pages.js';
import { mountPanels } from './panels.js';
import { mountInspector } from './properties.js';

class Editor {
  constructor(design) {
    this.doc = design;
    this.pageIndex = 0;
    this.selected = new Set();
    this.listeners = new Map();
    this.history = new History(design, (snapshot) => {
      this.doc = snapshot;
      this.pageIndex = Math.min(this.pageIndex, this.doc.pages.length - 1);
      this.selected = new Set([...this.selected].filter((id) => this.findElement(id)));
      this.board.renderPage();
      this.pageStrip?.render();
      this.inspector?.render();
      this.panels?.refreshLayers();
      this.updateChrome();
      this.requestSave();
    });
    this.history.onChange = () => this.updateChrome();
  }

  get page() {
    return this.doc.pages[this.pageIndex];
  }

  on(event, handler) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(handler);
    return () => this.listeners.get(event)?.delete(handler);
  }

  emit(event, payload) {
    for (const handler of this.listeners.get(event) || []) handler(payload);
  }

  findElement(id) {
    for (const page of this.doc.pages) {
      const element = page.elements.find((item) => item.id === id);
      if (element) return element;
    }
    return null;
  }

  selectedElements() {
    return [...this.selected].map((id) => this.findElement(id)).filter(Boolean);
  }

  select(ids) {
    const next = new Set(ids.filter((id) => this.findElement(id)));
    if (this.board?.editingId && !next.has(this.board.editingId)) this.board.finishTextEdit(true);
    if (next.size === this.selected.size && [...next].every((id) => this.selected.has(id))) return;
    this.selected = next;
    this.board?.refreshOverlay();
    this.inspector?.render();
    this.panels?.refreshLayers();
    this.updateChrome();
  }

  toggleSelection(id) {
    const next = new Set(this.selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    this.select([...next]);
  }

  selectAll() {
    this.select(this.page.elements.filter((element) => element.visible !== false).map((element) => element.id));
  }

  setPage(index, options = {}) {
    if (index < 0 || index >= this.doc.pages.length) return;
    this.pageIndex = index;
    this.selected = options.keepSelection ? this.selected : new Set();
    this.board.renderPage();
    this.pageStrip.render();
    this.inspector.render();
    this.panels.refreshLayers();
    this.updateChrome();
  }

  addPage() {
    const source = this.page;
    const page = deepClone(source);
    page.id = `page-${Date.now().toString(36)}`;
    page.background = '#ffffff';
    page.elements = [];
    this.doc.pages.splice(this.pageIndex + 1, 0, page);
    this.commit('Add page');
    this.setPage(this.pageIndex + 1);
  }

  duplicatePage(index = this.pageIndex) {
    const source = this.doc.pages[index];
    if (!source) return;
    const copy = deepClone(source);
    copy.id = `page-${Date.now().toString(36)}`;
    copy.elements = copy.elements.map((element) => ({ ...element, id: `${element.type}-${Math.random().toString(36).slice(2, 9)}` }));
    this.doc.pages.splice(index + 1, 0, copy);
    this.commit('Duplicate page');
    this.setPage(index + 1);
  }

  deletePage(index = this.pageIndex) {
    if (this.doc.pages.length <= 1) {
      toast('A design needs at least one page');
      return;
    }
    this.doc.pages.splice(index, 1);
    this.pageIndex = Math.max(0, Math.min(index, this.doc.pages.length - 1));
    this.selected = new Set();
    this.commit('Delete page');
    this.setPage(this.pageIndex);
  }

  setPageBackground(color) {
    this.page.background = color;
    this.board.surface.style.background = color;
    this.commit('Page background');
    this.pageStrip.render();
    this.inspector.render();
  }

  setDesignSize(preset) {
    const match = PAGE_PRESETS.find((item) => item.id === preset);
    if (!match) return;
    this.doc.w = match.w;
    this.doc.h = match.h;
    this.commit('Resize design');
    this.board.renderPage();
    this.board.fit();
    this.pageStrip.render();
    this.inspector.render();
  }

  setDesignSizeCustom(width, height) {
    this.doc.w = Math.max(CANVAS_LIMITS.min, Math.min(CANVAS_LIMITS.max, Math.round(width)));
    this.doc.h = Math.max(CANVAS_LIMITS.min, Math.min(CANVAS_LIMITS.max, Math.round(height)));
    this.commit('Resize design');
    this.board.renderPage();
    this.board.fit();
    this.pageStrip.render();
    this.inspector.render();
  }

  updateElement(id, patch, label = 'Update element') {
    const element = this.findElement(id);
    if (!element) return;
    Object.assign(element, patch);
    this.board.refreshNodes([id]);
    this.commit(label);
    this.panels.refreshLayers();
    this.pageStrip.schedule();
  }

  updateSelected(patch, label = 'Update selection') {
    const selected = this.selectedElements();
    if (!selected.length) return;
    for (const element of selected) Object.assign(element, patch);
    this.board.refreshNodes(selected.map((element) => element.id));
    this.commit(label);
    this.panels.refreshLayers();
    this.pageStrip.schedule();
  }

  setTextStyle(patch) {
    const selected = this.selectedElements().filter((element) => element.type === 'text');
    if (!selected.length) return;
    for (const element of selected) Object.assign(element, patch);
    this.board.refreshNodes(selected.map((element) => element.id));
    this.commit('Text style');
  }

  addElement(element, options = {}) {
    this.page.elements.push(element);
    this.board.renderPage();
    this.select([element.id]);
    this.commit(`Add ${element.type}`);
    this.pageStrip.schedule();
    if (options.edit && element.type === 'text') {
      requestAnimationFrame(() => this.board.startTextEdit(element.id));
    }
    return element;
  }

  deleteSelected() {
    const ids = new Set(this.selected);
    if (!ids.size) return;
    this.page.elements = this.page.elements.filter((element) => !ids.has(element.id));
    this.selected = new Set();
    this.board.renderPage();
    this.inspector.render();
    this.panels.refreshLayers();
    this.commit('Delete elements');
    this.pageStrip.schedule();
  }

  duplicateSelected() {
    this.board.duplicateSelection();
    this.pageStrip.schedule();
  }

  arrange(mode) {
    const selected = new Set(this.selected);
    if (!selected.size) return;
    const elements = this.page.elements;
    const chosen = elements.filter((element) => selected.has(element.id));
    const rest = elements.filter((element) => !selected.has(element.id));
    if (mode === 'front') elements.splice(0, elements.length, ...rest, ...chosen);
    else if (mode === 'back') elements.splice(0, elements.length, ...chosen, ...rest);
    else if (mode === 'forward') {
      for (let index = elements.length - 2; index >= 0; index -= 1) {
        if (selected.has(elements[index].id) && !selected.has(elements[index + 1].id)) {
          [elements[index], elements[index + 1]] = [elements[index + 1], elements[index]];
        }
      }
    } else if (mode === 'backward') {
      for (let index = 1; index < elements.length; index += 1) {
        if (selected.has(elements[index].id) && !selected.has(elements[index - 1].id)) {
          [elements[index], elements[index - 1]] = [elements[index - 1], elements[index]];
        }
      }
    }
    this.board.renderPage();
    this.commit('Arrange elements');
    this.panels.refreshLayers();
    this.pageStrip.schedule();
  }

  align(mode) {
    const selected = this.selectedElements();
    if (!selected.length) return;
    const doc = this.doc;
    const box = selected.reduce(
      (acc, element) => ({
        left: Math.min(acc.left, element.x),
        top: Math.min(acc.top, element.y),
        right: Math.max(acc.right, element.x + element.w),
        bottom: Math.max(acc.bottom, element.y + element.h),
      }),
      { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity },
    );
    const relative = selected.length > 1 ? box : { left: 0, top: 0, right: doc.w, bottom: doc.h };
    for (const element of selected) {
      if (mode === 'left') element.x = relative.left;
      if (mode === 'center') element.x = (relative.left + relative.right) / 2 - element.w / 2;
      if (mode === 'right') element.x = relative.right - element.w;
      if (mode === 'top') element.y = relative.top;
      if (mode === 'middle') element.y = (relative.top + relative.bottom) / 2 - element.h / 2;
      if (mode === 'bottom') element.y = relative.bottom - element.h;
    }
    this.board.refreshNodes(selected.map((element) => element.id));
    this.commit('Align elements');
    this.inspector.render();
    this.pageStrip.schedule();
  }

  centerOnPage() {
    const selected = this.selectedElements();
    if (!selected.length) return;
    const box = selected.reduce(
      (acc, element) => ({
        left: Math.min(acc.left, element.x),
        top: Math.min(acc.top, element.y),
        right: Math.max(acc.right, element.x + element.w),
        bottom: Math.max(acc.bottom, element.y + element.h),
      }),
      { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity },
    );
    const dx = this.doc.w / 2 - (box.left + box.right) / 2;
    const dy = this.doc.h / 2 - (box.top + box.bottom) / 2;
    for (const element of selected) {
      element.x += dx;
      element.y += dy;
    }
    this.board.refreshNodes(selected.map((element) => element.id));
    this.commit('Center elements');
    this.inspector.render();
    this.pageStrip.schedule();
  }

  applyTemplate(template) {
    const pages = template.buildPages();
    this.doc.w = template.w;
    this.doc.h = template.h;
    this.doc.pages = pages;
    this.pageIndex = 0;
    this.selected = new Set();
    this.board.renderPage();
    this.board.fit();
    this.pageStrip.render();
    this.inspector.render();
    this.panels.refreshLayers();
    this.commit('Apply template');
    toast('Template applied');
  }

  lockSelected(locked) {
    this.updateSelected({ locked }, locked ? 'Lock elements' : 'Unlock elements');
    this.board.renderPage();
    this.inspector.render();
  }

  toggleVisible(id) {
    const element = this.findElement(id);
    if (!element) return;
    element.visible = element.visible === false;
    this.board.renderPage();
    this.commit('Toggle layer');
    this.panels.refreshLayers();
    this.inspector.render();
    this.pageStrip.schedule();
  }

  commit(label, options = {}) {
    this.history.push(this.doc);
    this.emit('commit', label);
    this.updateChrome();
    this.requestSave();
    if (!options.coalesce) this.inspector?.renderSoon?.();
  }

  requestSave() {
    this.saveSoon?.();
  }

  updateChrome() {
    const undo = $('#undoBtn');
    const redo = $('#redoBtn');
    if (undo) undo.disabled = !this.history.canUndo();
    if (redo) redo.disabled = !this.history.canRedo();
    this.emit('chrome');
  }

  undo() {
    const snapshot = this.history.undo();
    if (!snapshot) return;
    this.doc = snapshot;
    this.pageIndex = Math.min(this.pageIndex, this.doc.pages.length - 1);
    this.selected = new Set([...this.selected].filter((id) => this.findElement(id)));
    this.board.renderPage();
    this.pageStrip.render();
    this.inspector.render();
    this.panels.refreshLayers();
    this.updateChrome();
    this.requestSave();
  }

  redo() {
    const snapshot = this.history.redo();
    if (!snapshot) return;
    this.doc = snapshot;
    this.pageIndex = Math.min(this.pageIndex, this.doc.pages.length - 1);
    this.selected = new Set([...this.selected].filter((id) => this.findElement(id)));
    this.board.renderPage();
    this.pageStrip.render();
    this.inspector.render();
    this.panels.refreshLayers();
    this.updateChrome();
    this.requestSave();
  }
}

/* ------------------------------------------------------------------ */
/* Boot                                                                */
/* ------------------------------------------------------------------ */

function boot() {
  const params = new URLSearchParams(location.search);
  let bootDesign = getDesign(params.get('id') || '');

  if (!bootDesign && params.get('preset')) {
    bootDesign = createNewDesign(params.get('preset'), 'Untitled design');
    history.replaceState(null, '', `editor.html?id=${encodeURIComponent(bootDesign.id)}`);
  }
  if (!bootDesign && params.get('template')) {
    bootDesign = designFromTemplate(params.get('template'));
    saveDesign(bootDesign);
    history.replaceState(null, '', `editor.html?id=${encodeURIComponent(bootDesign.id)}`);
  }

  if (!bootDesign) {
    location.replace('index.html');
    return;
  }
  start(bootDesign);
}

function start(activeDesign) {
  document.body.dataset.state = 'ready';
  const editor = new Editor(activeDesign);
  window.__REA_EDITOR__ = editor;

  editor.saveSoon = debounce(() => {
    editor.doc.updatedAt = Date.now();
    const saved = saveDesign(editor.doc);
    const state = $('#saveState');
    if (!saved) {
      if (state) {
        state.textContent = 'Not saved';
        state.classList.remove('is-saving');
      }
      toast('Browser storage is full. Remove an image or a design copy.');
      return;
    }
    if (state) {
      state.textContent = 'Saved';
      state.classList.remove('is-saving');
    }
    editor.emit('saved');
  }, 320);

  const viewport = $('#board');
  editor.board = new Board(viewport, editor);
  editor.board.onView = (zoom) => {
    const label = $('#zoomValue');
    const slider = $('#zoomSlider');
    if (label) label.textContent = `${Math.round(zoom * 100)}%`;
    if (slider) {
      const min = Math.log(0.05);
      const max = Math.log(8);
      slider.value = String(Math.round(((Math.log(zoom) - min) / (max - min)) * 1000));
    }
  };

  editor.inspector = mountInspector($('#inspector'), editor);
  editor.panels = mountPanels({
    rail: $('#rail'),
    panel: $('#panelHost'),
    editor,
  });
  editor.pageStrip = mountPages($('#pagesStrip'), editor);

  editor.board.renderPage();
  editor.board.fit();
  editor.inspector.render();
  editor.pageStrip.render();
  editor.updateChrome();

  wireTopbar(editor);
  wireZoom(editor);
  wireShortcuts(editor);
  wireDrop(editor);
  wireTitles(editor);

  ensureFonts().then(() => {
    editor.pageStrip.render();
    editor.pageStrip.schedule();
  });

  const loading = $('#bootScreen');
  if (loading) loading.remove();
}

function wireTitles(editor) {
  const title = $('#designTitle');
  if (!title) return;
  title.textContent = editor.doc.title;
  title.setAttribute('contenteditable', 'plaintext-only');
  title.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      title.blur();
    }
    if (event.key === 'Escape') {
      title.textContent = editor.doc.title;
      title.blur();
    }
  });
  title.addEventListener('blur', () => {
    const next = (title.textContent || '').trim().slice(0, 80);
    if (next && next !== editor.doc.title) {
      editor.doc.title = next;
      editor.commit('Rename design');
      document.title = `${next} - Rea Studio`;
    } else {
      title.textContent = editor.doc.title;
    }
  });
}

function wireTopbar(editor) {
  const saveState = $('#saveState');
  editor.on('commit', () => {
    if (saveState) {
      saveState.textContent = 'Saving';
      saveState.classList.add('is-saving');
    }
  });

  $('#undoBtn').addEventListener('click', () => editor.undo());
  $('#redoBtn').addEventListener('click', () => editor.redo());

  $('#fileMenuBtn').addEventListener('click', (event) => {
    openMenu(event.currentTarget, [
      {
        label: 'New blank design',
        icon: ICONS.plus,
        onSelect: () => {
          const preset = findPreset(editor.doc.w, editor.doc.h)?.id || 'social';
          location.href = `index.html?create=${encodeURIComponent(preset)}`;
        },
      },
      {
        label: 'Duplicate this design',
        icon: ICONS.copy,
        onSelect: () => {
          const copy = duplicateDesign(editor.doc.id);
          if (copy) location.href = `editor.html?id=${encodeURIComponent(copy.id)}`;
        },
      },
      { separator: true },
      { label: 'Export PNG', icon: ICONS.download, hint: '2x', onSelect: () => exportPage(editor, 2) },
      { label: 'Export JPG', onSelect: () => exportPage(editor, 1, 'image/jpeg') },
      { separator: true },
      {
        label: 'Delete design',
        icon: ICONS.trash,
        danger: true,
        onSelect: () => {
          deleteDesign(editor.doc.id);
          location.href = 'index.html';
        },
      },
    ]);
  });

  $('#downloadBtn').addEventListener('click', (event) => {
    openMenu(event.currentTarget, [
      { label: 'PNG', hint: 'standard', onSelect: () => exportPage(editor, 1) },
      { label: 'PNG', hint: '2x sharp', onSelect: () => exportPage(editor, 2) },
      { label: 'JPG', hint: 'smaller file', onSelect: () => exportPage(editor, 1, 'image/jpeg') },
    ], { align: 'right' });
  });

  $('#shareBtn').addEventListener('click', async () => {
    const url = `${location.origin}${location.pathname}?id=${encodeURIComponent(editor.doc.id)}`;
    try {
      await navigator.clipboard.writeText(url);
      toast('Design link copied to clipboard');
    } catch {
      toast('Copy this link: ' + url);
    }
  });

  $('#previewBtn').addEventListener('click', () => openPreview(editor));

  const previewLayer = $('#previewLayer');
  previewLayer.addEventListener('pointerdown', (event) => {
    if (event.target === previewLayer || event.target.closest('[data-preview-close]')) {
      previewLayer.classList.remove('is-open');
      previewLayer.replaceChildren();
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && previewLayer.classList.contains('is-open')) {
      previewLayer.classList.remove('is-open');
      previewLayer.replaceChildren();
    }
  });
}

async function exportPage(editor, scale, type = 'image/png') {
  await ensureFonts();
  const canvas = await renderPageToCanvas(editor.doc, editor.page, { scale });
  const blob = await canvasToBlob(canvas, type, type === 'image/jpeg' ? 0.94 : undefined);
  if (!blob) {
    toast('Export failed');
    return;
  }
  const slug = editor.doc.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'design';
  const extension = type === 'image/jpeg' ? 'jpg' : 'png';
  downloadBlob(blob, `${slug}-${editor.pageIndex + 1}@${scale}x.${extension}`);
  toast('Export ready');
}

async function openPreview(editor) {
  const layer = $('#previewLayer');
  await ensureFonts();
  const canvas = await renderPageToCanvas(editor.doc, editor.page, {
    scale: Math.min(2, 1600 / editor.doc.w),
  });
  const close = el('button', { class: 'preview-close', type: 'button', 'data-preview-close': 'true' }, svgIcon(ICONS.close, 22));
  canvas.className = 'preview-canvas';
  layer.replaceChildren(canvas, close, el('span', { class: 'preview-caption', text: `${editor.doc.title} - page ${editor.pageIndex + 1} of ${editor.doc.pages.length}` }));
  layer.classList.add('is-open');
}

function wireZoom(editor) {
  const slider = $('#zoomSlider');
  $('#zoomOutBtn').addEventListener('click', () => editor.board.setZoom(editor.board.zoom / 1.2));
  $('#zoomInBtn').addEventListener('click', () => editor.board.setZoom(editor.board.zoom * 1.2));
  $('#zoomFitBtn').addEventListener('click', () => editor.board.fit());
  slider?.addEventListener('input', () => {
    const min = Math.log(0.05);
    const max = Math.log(8);
    const zoom = Math.exp(min + (Number(slider.value) / 1000) * (max - min));
    editor.board.setZoom(zoom);
  });
}

function wireShortcuts(editor) {
  document.addEventListener('keydown', (event) => {
    if (isEditableTarget(event.target)) return;
    const meta = event.metaKey || event.ctrlKey;
    const board = editor.board;

    if (event.code === 'Space' && !event.repeat) {
      board.setSpace(true);
      event.preventDefault();
      return;
    }
    if (meta && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      if (event.shiftKey) editor.redo();
      else editor.undo();
      return;
    }
    if (meta && event.key.toLowerCase() === 'y') {
      event.preventDefault();
      editor.redo();
      return;
    }
    if (meta && event.key.toLowerCase() === 'a') {
      event.preventDefault();
      editor.selectAll();
      return;
    }
    if (meta && event.key.toLowerCase() === 'd') {
      event.preventDefault();
      editor.duplicateSelected();
      return;
    }
    if (meta && event.key.toLowerCase() === 's') {
      event.preventDefault();
      saveDesign(editor.doc);
      const state = $('#saveState');
      if (state) {
        state.textContent = 'Saved';
        state.classList.remove('is-saving');
      }
      toast('Design saved');
      return;
    }
    if (meta && (event.key === '=' || event.key === '+')) {
      event.preventDefault();
      board.setZoom(board.zoom * 1.2);
      return;
    }
    if (meta && event.key === '-') {
      event.preventDefault();
      board.setZoom(board.zoom / 1.2);
      return;
    }
    if (meta && event.key === '0') {
      event.preventDefault();
      board.fit();
      return;
    }
    if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault();
      editor.deleteSelected();
      return;
    }
    if (event.key === 'Escape') {
      editor.select([]);
      return;
    }
    if (event.key === 'Enter' && editor.selected.size === 1) {
      const element = editor.selectedElements()[0];
      if (element?.type === 'text') {
        event.preventDefault();
        board.startTextEdit(element.id);
      }
      return;
    }
    if (event.key.startsWith('Arrow')) {
      if (!editor.selected.size) return;
      event.preventDefault();
      const step = event.shiftKey ? 10 : 1;
      const dx = event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0;
      const dy = event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0;
      board.nudge(dx, dy);
    }
  });

  document.addEventListener('keyup', (event) => {
    if (event.code === 'Space') editor.board.setSpace(false);
  });
  window.addEventListener('blur', () => editor.board.setSpace(false));
}

function wireDrop(editor) {
  const board = $('#board');
  board.addEventListener('dragover', (event) => {
    if (event.dataTransfer?.types.includes('Files')) {
      event.preventDefault();
      board.classList.add('is-drop-target');
    }
  });
  board.addEventListener('dragleave', (event) => {
    if (event.target === board) board.classList.remove('is-drop-target');
  });
  board.addEventListener('drop', async (event) => {
    board.classList.remove('is-drop-target');
    const file = event.dataTransfer?.files?.[0];
    if (!file || !file.type.startsWith('image/')) return;
    event.preventDefault();
    const src = await fileToDataUrl(file);
    const point = editor.board.worldFromClient(event.clientX, event.clientY);
    const element = editor.createImageElement(src, point);
    editor.addElement(element);
    editor.panels.addUpload(file.name, src);
  });
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

// Expose small helpers used by panels/properties without circular imports.
Editor.prototype.createImageElement = function createImageElement(src, point) {
  const element = {
    id: `image-${Math.random().toString(36).slice(2, 9)}`,
    type: 'image',
    name: 'Image',
    x: 0,
    y: 0,
    w: 480,
    h: 320,
    rotation: 0,
    opacity: 1,
    locked: false,
    visible: true,
    src,
    fit: 'cover',
  };
  const maxW = this.doc.w * 0.42;
  const maxH = this.doc.h * 0.42;
  const fit = Math.min(maxW / element.w, maxH / element.h, 1);
  element.w = Math.round(element.w * fit);
  element.h = Math.round(element.h * fit);
  element.x = Math.round((point?.x ?? this.doc.w / 2) - element.w / 2);
  element.y = Math.round((point?.y ?? this.doc.h / 2) - element.h / 2);
  return element;
};

Editor.prototype.addTextPreset = function addTextPreset(kind) {
  const w = Math.min(this.doc.w * 0.7, 900);
  const presets = {
    heading: { text: 'Add a heading', size: Math.round(this.doc.w * 0.06), font: 'serif', weight: 700, w, h: Math.round(this.doc.w * 0.11) },
    subheading: { text: 'Add a subheading', size: Math.round(this.doc.w * 0.032), font: 'sans', weight: 600, w, h: Math.round(this.doc.w * 0.07) },
    body: { text: 'Add a little bit of body text', size: Math.round(this.doc.w * 0.022), font: 'sans', weight: 400, w, h: Math.round(this.doc.w * 0.08) },
  };
  const preset = presets[kind] || presets.body;
  const element = {
    id: `text-${Math.random().toString(36).slice(2, 9)}`,
    type: 'text',
    name: preset.text,
    x: Math.round((this.doc.w - preset.w) / 2),
    y: Math.round(this.doc.h * 0.42),
    w: Math.round(preset.w),
    h: Math.round(preset.h),
    rotation: 0,
    opacity: 1,
    locked: false,
    visible: true,
    text: preset.text,
    font: preset.font,
    size: preset.size,
    weight: preset.weight,
    italic: false,
    underline: false,
    align: 'center',
    color: '#12161c',
    lineHeight: 1.15,
    letterSpacing: 0,
  };
  this.  addElement(element, { edit: true });
};

boot();

