/* Rea Board shell — the Canva-style design surface inside the invitation editor.
 *
 * Data flow: the board edits a mirror of the invitation's visual pages. Every
 * committed change is written back through window.EInviteEditorBridge.transact,
 * so the classic editor re-renders, autosaves, keeps its undo stack and keeps
 * publishing the same document. Nothing is stored separately.
 */
(() => {
  'use strict';

  const Core = window.ReaBoardCore;
  const Surface = window.ReaBoardSurface;
  if (!Core || !Surface) return;

  const bridge = () => window.EInviteEditorBridge;

  let root = null;
  let board = null;
  let opened = false;
  let pageIndex = 0;
  let doc = null;
  let activeTab = 'elements';
  let history = [];
  let future = [];
  let pendingBefore = null;
  let quietCommit = false;
  let fileInput = null;
  let replaceTargetId = null;
  let previewOpen = false;

  const selected = new Set();

  function strings() {
    return window.ReaBoardStrings || { en: {}, km: {} };
  }

  function t(key, vars) {
    const dict = strings();
    const km = document.documentElement.lang === 'km';
    let text = (km ? dict.km : dict.en)?.[key] || dict.en?.[key] || key;
    if (vars) {
      for (const [name, value] of Object.entries(vars)) {
        text = text.replace(`{${name}}`, String(value));
      }
    }
    return text;
  }

  /* ---------------------------------------------------------------- */
  /* Document mapping                                                  */
  /* ---------------------------------------------------------------- */

  const round = (value, places = 2) => {
    const factor = 10 ** places;
    return Math.round(Number(value || 0) * factor) / factor;
  };

  const percent = (value, total) => `${round((Number(value || 0) / Math.max(1, total)) * 100, 3)}%`;

  function measure(value, total, fallback = 0) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    const text = String(value ?? '');
    const number = parseFloat(text);
    if (!Number.isFinite(number)) return fallback;
    return text.includes('%') ? (number / 100) * total : number;
  }

  function plainText(html) {
    if (window.EInviteRenderer?.plainText) return window.EInviteRenderer.plainText(html || '');
    const div = document.createElement('div');
    div.innerHTML = String(html || '');
    return div.textContent || '';
  }

  function fontId(value) {
    const registry = window.EInviteFontRegistry;
    if (registry?.fontId) {
      try {
        return registry.fontId(value);
      } catch {
        return registry.data?.defaultFontId || 'noto-serif';
      }
    }
    return value || 'noto-serif';
  }

  function toBoardElement(id, object, width, height) {
    if (!object || typeof object !== 'object') return null;
    const type = object.type === 'image' ? 'image' : object.type === 'shape' ? 'shape' : 'text';
    if (!['text', 'image', 'shape', 'decoration'].includes(String(object.type || 'text'))) return null;

    const base = {
      id: String(id),
      docType: String(object.type || 'text'),
      type,
      x: measure(object.left, width, 0),
      y: measure(object.top, height, 0),
      w: Math.max(8, measure(object.width, width, width * 0.4)),
      h: Math.max(8, measure(object.height, height, 60)),
      rotation: Number(object.rotation || 0),
      opacity: Math.max(0.05, Math.min(1, Number(object.opacity ?? 1))),
      locked: object.locked === true,
      visible: object.visible !== false,
    };

    if (type === 'text') {
      return {
        ...base,
        text: plainText(object.html || object.text || ''),
        font: fontId(object.font),
        size: Math.max(8, Math.min(240, Number(object.fontSize || 32))),
        weight: Number(object.fontWeight || 400),
        italic: object.fontStyle === 'italic',
        underline: String(object.textDecoration || '').includes('underline'),
        align: ['left', 'center', 'right', 'justify'].includes(object.textAlign) ? object.textAlign : 'left',
        color: Core.hexColor(object.color, '#141821'),
        lineHeight: Math.max(0.8, Math.min(2.4, Number(object.lineHeight || 1.35))),
        letterSpacing: Number(object.letterSpacing || 0),
      };
    }

    if (type === 'image') {
      return {
        ...base,
        src: String(object.src || ''),
        alt: String(object.alt || ''),
        fit: object.imageFit === 'contain' ? 'contain' : 'cover',
        radius: Math.max(0, Number(object.borderRadius || 0)),
      };
    }

    const gradient = object.fillMode === 'gradient';
    return {
      ...base,
      shape: ['rectangle', 'circle', 'line'].includes(object.shapeKind) ? object.shapeKind : 'rectangle',
      fill: gradient
        ? {
            from: object.gradientStart || '#00c4cc',
            to: object.gradientEnd || '#7d2ae8',
            angle: Number(object.gradientAngle ?? 135),
          }
        : object.fillColor || '#7d2ae8',
      radius: Math.max(0, Number(object.borderRadius || 0)),
      docType: 'shape',
    };
  }

  function boardElementObject(element, zIndex, previous) {
    const base = {
      ...(previous || {}),
      type: element.type === 'image'
        ? 'image'
        : element.type === 'shape'
          ? 'shape'
          : (element.docType === 'decoration' ? 'decoration' : 'text'),
      left: percent(element.x, doc.w),
      top: percent(element.y, doc.h),
      width: percent(element.w, doc.w),
      height: percent(element.h, doc.h),
      rotation: round(element.rotation, 1),
      zIndex: Math.max(1, zIndex + 1),
      opacity: Math.max(0.05, Math.min(1, Number(element.opacity ?? 1))),
      visible: element.visible !== false,
      locked: element.locked === true,
    };

    if (element.type === 'text') {
      // A saved rich-text model wins over `html` when the document normalizes.
      // Drop it only when the plain text actually changed, so moving or
      // restyling a text box keeps its inline formatting.
      const previousText = previous ? plainText(previous.html || '') : '';
      const textChanged = Boolean(previous) && previousText !== (element.text ?? '');
      const cleaned = { ...base };
      if (textChanged) {
        delete cleaned.richText;
        delete cleaned.richTextModelVersion;
        delete cleaned.text;
      }
      return {
        ...cleaned,
        html: Core.escapeHtml(element.text ?? '').replace(/\n/g, '<br>'),
        font: element.font,
        fontSize: Math.round(element.size || 32),
        fontWeight: String(element.weight || 400),
        fontStyle: element.italic ? 'italic' : 'normal',
        textDecoration: element.underline ? 'underline' : 'none',
        textAlign: element.align || 'left',
        color: Core.hexColor(element.color, '#141821'),
        lineHeight: round(element.lineHeight || 1.35, 2),
        letterSpacing: round(element.letterSpacing || 0, 2),
        textVerticalAlign: 'top',
        textPadding: 0,
        textAutoFit: 'none',
        textWrap: 'normal',
      };
    }

    if (element.type === 'image') {
      return {
        ...base,
        src: element.src || '',
        alt: element.alt || '',
        imageFit: element.fit === 'contain' ? 'contain' : 'cover',
        borderRadius: Math.round(element.radius || 0),
      };
    }

    const gradient = Core.isGradient(element.fill);
    return {
      ...base,
      shapeKind: element.shape || 'rectangle',
      fillMode: gradient ? 'gradient' : 'solid',
      fillColor: gradient ? (previous?.fillColor || '#7d2ae8') : Core.hexColor(element.fill, '#7d2ae8'),
      gradientStart: gradient ? element.fill.from : (previous?.gradientStart || '#00c4cc'),
      gradientEnd: gradient ? element.fill.to : (previous?.gradientEnd || '#7d2ae8'),
      gradientAngle: gradient ? Number(element.fill.angle ?? 135) : Number(previous?.gradientAngle ?? 135),
      borderRadius: Math.round(element.radius || 0),
    };
  }

  function hydrate() {
    const state = bridge()?.getState?.() || {};
    const stage = document.querySelector('#stage');
    const width = Math.max(240, Math.round(stage?.clientWidth || 720));
    const height = Math.max(240, Math.round(stage?.clientHeight || 960));
    const title = String(state.fields?.names || state.fields?.namesKm || 'Invitation');

    const pages = (Array.isArray(state.designPages) ? state.designPages : []).map((page) => {
      const elements = [];
      let unsupported = 0;
      const entries = Object.entries(page.objects || {}).sort(
        (a, b) => Number(a[1]?.zIndex || 0) - Number(b[1]?.zIndex || 0),
      );
      for (const [id, object] of entries) {
        const element = toBoardElement(id, object, width, height);
        if (element) elements.push(element);
        else unsupported += 1;
      }
      return {
        id: String(page.id),
        sourceId: String(page.id),
        name: String(page.name || 'Page'),
        background: Core.hexColor(page.background, '#fffaf6'),
        elements,
        managedIds: elements.map((element) => element.id),
        unsupported,
      };
    });

    doc = { w: width, h: height, title, pages };
    pageIndex = Math.min(pageIndex, Math.max(0, pages.length - 1));

    const active = bridge()?.getActiveCanvasId?.() || '';
    if (String(active).startsWith('page:')) {
      const index = pages.findIndex((page) => page.sourceId === String(active).slice(5));
      if (index >= 0) pageIndex = index;
    }
    history = [];
    future = [];
    pendingBefore = null;
    select([]);
  }

  function currentPage() {
    return doc?.pages?.[pageIndex] || null;
  }

  /* ---------------------------------------------------------------- */
  /* Committing to the invitation                                      */
  /* ---------------------------------------------------------------- */

  function beginChange() {
    if (!doc || pendingBefore) return;
    pendingBefore = Core.deepClone(doc);
  }

  function writeToDocument(label) {
    const api = bridge();
    if (!api?.transact || !doc) return;
    api.transact(label || 'Board edit', (state) => {
      const existing = new Map(
        (Array.isArray(state.designPages) ? state.designPages : []).map((page) => [String(page.id), page]),
      );
      const next = [];

      for (const page of doc.pages) {
        const source = page.sourceId ? existing.get(String(page.sourceId)) : null;
        const base = source || {
          id: page.sourceId || Core.uid('page'),
          name: page.name,
          preset: 'custom',
          enabled: true,
          objects: {},
        };
        const objects = { ...(base.objects || {}) };
        const keep = new Set();

        page.elements.forEach((element, index) => {
          objects[element.id] = boardElementObject(element, index, objects[element.id]);
          keep.add(element.id);
        });
        for (const id of page.managedIds || []) {
          if (!keep.has(id)) delete objects[id];
        }

        const normalized = {
          ...base,
          name: page.name || base.name,
          background: Core.hexColor(page.background, base.background || '#fffaf6'),
          objects,
        };
        page.sourceId = String(normalized.id);
        page.managedIds = [...keep];
        next.push(normalized);
      }

      state.designPages = next;
      const tokens = next.map((page) => `page:${page.id}`);
      const order = (Array.isArray(state.sectionOrder) ? state.sectionOrder : []).filter(
        (token) => !String(token).startsWith('page:'),
      );
      state.sectionOrder = [...tokens, ...order];
    });
  }

  let pagesTimer = 0;

  function schedulePages() {
    window.clearTimeout(pagesTimer);
    pagesTimer = window.setTimeout(() => refreshPages(), 180);
  }

  function commit(label) {
    if (!doc) return;
    const quiet = quietCommit;
    quietCommit = false;
    if (pendingBefore) {
      history.push(pendingBefore);
      if (history.length > 60) history.shift();
      future = [];
      pendingBefore = null;
    }
    writeToDocument(label);
    schedulePages();
    refreshSaveState();
    if (!quiet) {
      refreshInspector();
      refreshLayers();
    }
  }

  function undo() {
    if (!history.length) return;
    const previous = history.pop();
    future.push(Core.deepClone(doc));
    doc = previous;
    pageIndex = Math.min(pageIndex, Math.max(0, doc.pages.length - 1));
    select([]);
    writeToDocument('Undo board edit');
    renderAll();
  }

  function redo() {
    if (!future.length) return;
    const next = future.pop();
    history.push(Core.deepClone(doc));
    doc = next;
    pageIndex = Math.min(pageIndex, Math.max(0, doc.pages.length - 1));
    select([]);
    writeToDocument('Redo board edit');
    renderAll();
  }

  /* ---------------------------------------------------------------- */
  /* Selection and rendering                                           */
  /* ---------------------------------------------------------------- */

  const editor = {
    get doc() {
      return doc;
    },
    get page() {
      return currentPage();
    },
    selected,
    findElement(id) {
      return currentPage()?.elements.find((element) => element.id === id) || null;
    },
    selectedElements() {
      const page = currentPage();
      if (!page) return [];
      return page.elements.filter((element) => selected.has(element.id));
    },
    select(ids) {
      selected.clear();
      for (const id of ids || []) selected.add(id);
      root?.classList.toggle('rb-has-selection', selected.size > 0);
      board?.refreshOverlay();
      refreshInspector();
      refreshLayers();
    },
    toggleSelection(id) {
      if (selected.has(id)) selected.delete(id);
      else selected.add(id);
      root?.classList.toggle('rb-has-selection', selected.size > 0);
      board?.refreshOverlay();
      refreshInspector();
      refreshLayers();
    },
    beginChange,
    commit,
    emit(name, payload) {
      if (name === 'replace-image') pickReplacement(payload);
      if (name === 'selection') refreshInspector();
    },
  };

  function select(ids) {
    editor.select(ids);
  }

  /* ---------------------------------------------------------------- */
  /* Shell                                                             */
  /* ---------------------------------------------------------------- */

  function iconButton(icon, label, attributes = {}, hint) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'rb-icon-btn';
    button.append(Core.svgIcon(Core.ICONS[icon] || Core.ICONS.plus, 19));
    button.setAttribute('aria-label', label);
    if (hint) button.title = hint;
    for (const [key, value] of Object.entries(attributes)) button.setAttribute(key, value);
    return button;
  }

  function buildShell() {
    root = document.createElement('div');
    root.className = 'rea-board';
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');

    const topbar = document.createElement('header');
    topbar.className = 'rb-topbar';

    const back = document.createElement('button');
    back.type = 'button';
    back.className = 'rb-back';
    back.setAttribute('aria-label', t('back'));
    back.title = t('back');
    back.append(Core.svgIcon(Core.ICONS.arrowLeft, 18), Core.el('span', { text: t('back') }));
    back.addEventListener('click', close);

    const brand = document.createElement('div');
    brand.className = 'rb-brand';
    brand.append(
      Core.el('span', { class: 'rb-brand-mark', text: 'Rea' }),
      Core.el('span', { class: 'rb-brand-name', text: t('board') }),
      Core.el('span', { class: 'rb-doc-title', text: doc?.title || '' , dataset: { rbTitle: 'true' } }),
    );

    const actions = document.createElement('div');
    actions.className = 'rb-top-actions';

    const save = Core.el('span', { class: 'rb-save', text: t('saved'), dataset: { rbSave: 'true' } });
    const undoBtn = iconButton('undo', t('undo'), { 'data-rb-undo': 'true' }, t('undo'));
    const redoBtn = iconButton('redo', t('redo'), { 'data-rb-redo': 'true' }, t('redo'));
    const previewBtn = Core.el('button', { class: 'rb-text-btn', type: 'button', dataset: { rbPreviewBtn: 'true' } }, [
      Core.svgIcon(Core.ICONS.play, 17),
      Core.el('span', { text: t('preview') }),
    ]);
    const exportBtn = Core.el('button', { class: 'rb-text-btn rb-primary', type: 'button', dataset: { rbExport: 'true' } }, [
      Core.svgIcon(Core.ICONS.download, 17),
      Core.el('span', { text: t('export') }),
    ]);
    actions.append(save, undoBtn, redoBtn, previewBtn, exportBtn);

    topbar.append(back, brand, actions);

    const body = document.createElement('div');
    body.className = 'rb-body';

    const rail = document.createElement('nav');
    rail.className = 'rb-rail';
    rail.setAttribute('aria-label', t('board'));

    const tabs = [
      ['elements', 'shape', 'elements'],
      ['text', 'text', 'text'],
      ['layers', 'layers', 'layers'],
    ];
    for (const [key, icon, label] of tabs) {
      const button = Core.el('button', { class: 'rb-rail-btn', type: 'button', dataset: { rbTab: key } }, [
        Core.svgIcon(Core.ICONS[icon], 21),
        Core.el('span', { text: t(label) }),
      ]);
      button.addEventListener('click', () => setTab(key));
      rail.append(button);
    }

    const panel = document.createElement('aside');
    panel.className = 'rb-panel';
    panel.dataset.rbPanel = 'true';

    const viewport = document.createElement('main');
    viewport.className = 'rb-viewport';
    viewport.tabIndex = 0;
    viewport.dataset.reaViewport = 'true';

    const stage = Core.el('div', { class: 'rb-stage', dataset: { reaStage: 'true' } });
    const surface = Core.el('div', { class: 'rb-surface', dataset: { reaSurface: 'true' } });
    const elements = Core.el('div', { class: 'rb-elements', dataset: { reaElements: 'true' } });
    surface.append(elements);
    stage.append(surface);

    const guides = Core.el('div', { class: 'rb-guides', dataset: { reaGuides: 'true' } });
    const marquee = Core.el('div', { class: 'rb-marquee', dataset: { reaMarquee: 'true' } });
    marquee.hidden = true;
    const selectionNode = Core.el('div', { class: 'rb-selection', dataset: { reaSelection: 'true' } });
    selectionNode.hidden = true;

    const empty = Core.el('div', { class: 'rb-empty', dataset: { rbEmpty: 'true' } });
    empty.hidden = true;
    const emptyCard = Core.el('div', { class: 'rb-empty-card' }, [
      Core.el('span', { class: 'rb-empty-icon' }, Core.svgIcon(Core.ICONS.page, 30)),
      Core.el('h2', { text: t('emptyBoard') }),
      Core.el('p', { text: t('emptyCopy') }),
    ]);
    const createFirst = Core.el('button', { class: 'rb-primary', type: 'button', text: t('createPage') });
    createFirst.addEventListener('click', () => addPage(true));
    emptyCard.append(createFirst);
    empty.append(emptyCard);

    const pages = Core.el('div', { class: 'rb-pages', dataset: { rbPages: 'true' } });

    const zoom = Core.el('div', { class: 'rb-zoom' });
    const zoomOut = iconButton('minus', t('zoom'));
    const zoomIn = iconButton('plus', t('zoom'));
    const zoomRange = Core.el('input', {
      type: 'range',
      min: '5',
      max: '400',
      value: '100',
      class: 'rb-zoom-range',
      'aria-label': t('zoom'),
      dataset: { rbZoom: 'true' },
    });
    const zoomValue = Core.el('span', { class: 'rb-zoom-value', text: '100%', dataset: { rbZoomValue: 'true' } });
    const fit = Core.el('button', { class: 'rb-text-btn rb-ghost', type: 'button', text: t('fit') });
    zoomOut.addEventListener('click', () => board?.setZoom(board.zoom / 1.2));
    zoomIn.addEventListener('click', () => board?.setZoom(board.zoom * 1.2));
    fit.addEventListener('click', () => board?.fit());
    zoomRange.addEventListener('input', () => board?.setZoom(Number(zoomRange.value) / 100));
    zoom.append(zoomOut, zoomRange, zoomValue, zoomIn, fit);

    const hint = Core.el('div', { class: 'rb-hint', text: t('spaceHint') });

    viewport.append(stage, guides, marquee, selectionNode, empty, pages, zoom, hint);

    const inspector = document.createElement('aside');
    inspector.className = 'rb-inspector';
    inspector.dataset.rbInspector = 'true';

    body.append(rail, panel, viewport, inspector);

    const preview = Core.el('div', { class: 'rb-preview', dataset: { rbPreview: 'true' } });
    preview.hidden = true;
    const previewCard = Core.el('div', { class: 'rb-preview-card' });
    const closePreview = Core.el('button', { class: 'rb-preview-close', type: 'button', 'aria-label': t('close') }, Core.svgIcon(Core.ICONS.close, 20));
    closePreview.addEventListener('click', () => hidePreview());
    previewCard.append(closePreview);
    preview.append(previewCard);
    preview.addEventListener('click', (event) => {
      if (event.target === preview) hidePreview();
    });

    fileInput = Core.el('input', { type: 'file', accept: 'image/png,image/jpeg,image/webp,image/gif', hidden: true, dataset: { rbFile: 'true' } });
    fileInput.addEventListener('change', () => {
      const file = fileInput.files?.[0];
      fileInput.value = '';
      if (file) handleImageFile(file);
    });

    root.append(topbar, body, preview, fileInput);
    document.body.append(root);

    board = new Surface(root, editor);
    board.onView = (zoomValueCurrent) => {
      const percentage = Math.round(zoomValueCurrent * 100);
      const value = root.querySelector('[data-rb-zoom-value]');
      const range = root.querySelector('[data-rb-zoom]');
      if (value) value.textContent = `${percentage}%`;
      if (range && document.activeElement !== range) range.value = String(percentage);
    };

    root.querySelector('[data-rb-undo]').addEventListener('click', undo);
    root.querySelector('[data-rb-redo]').addEventListener('click', redo);
    root.querySelector('[data-rb-export]').addEventListener('click', exportPng);
    root.querySelector('[data-rb-preview-btn]').addEventListener('click', showPreview);
  }

  function setTab(tab) {
    const narrow = window.matchMedia('(max-width: 720px)').matches;
    if (narrow && activeTab === tab && root.classList.contains('rb-panel-open')) {
      root.classList.remove('rb-panel-open');
      return;
    }
    activeTab = tab;
    root.classList.add('rb-panel-open');
    for (const button of Core.$$('[data-rb-tab]', root)) {
      button.classList.toggle('is-active', button.dataset.rbTab === tab);
    }
    refreshPanel();
  }

  function refreshPanel() {
    const host = root?.querySelector('[data-rb-panel]');
    if (!host) return;
    host.replaceChildren();
    if (activeTab === 'text') buildTextPanel(host);
    else if (activeTab === 'layers') buildLayersPanel(host);
    else buildElementsPanel(host);
  }

  function panelTitle(host, key) {
    host.append(Core.el('h2', { class: 'rb-panel-title', text: t(key) }));
  }

  function buildElementsPanel(host) {
    panelTitle(host, 'elements');

    host.append(Core.el('h3', { class: 'rb-group-title', text: t('shapes') }));
    const shapes = Core.el('div', { class: 'rb-shape-grid' });
    const shapeButtons = [
      ['rectangle', 'rectangle', 'M4 6h16v12H4z'],
      ['circle', 'circle', 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z'],
      ['line', 'line', 'M4 18 20 6'],
    ];
    for (const [shape, label, path] of shapeButtons) {
      const button = Core.el('button', { class: 'rb-tile', type: 'button', title: t(label), 'aria-label': t(label) }, [
        Core.svgIcon(path, 24),
      ]);
      button.addEventListener('click', () => insertShape(shape));
      shapes.append(button);
    }
    host.append(shapes);

    host.append(Core.el('h3', { class: 'rb-group-title', text: t('gradients') }));
    const gradients = Core.el('div', { class: 'rb-gradient-grid' });
    for (const gradient of Core.GRADIENTS) {
      const button = Core.el('button', {
        class: 'rb-gradient',
        type: 'button',
        title: gradient.name,
        'aria-label': gradient.name,
        style: { background: Core.fillCss(gradient) },
      });
      button.addEventListener('click', () => insertShape('rectangle', { ...gradient }));
      gradients.append(button);
    }
    host.append(gradients);

    host.append(Core.el('h3', { class: 'rb-group-title', text: t('image') }));
    const upload = Core.el('button', { class: 'rb-wide-btn', type: 'button' }, [
      Core.svgIcon(Core.ICONS.image, 18),
      Core.el('span', { text: t('addImage') }),
    ]);
    upload.addEventListener('click', () => pickImage(false));
    host.append(upload);
    host.append(Core.el('p', { class: 'rb-note', text: t('uploadNote') }));
  }

  function buildTextPanel(host) {
    panelTitle(host, 'text');
    const presets = [
      ['heading', 'Add a heading', { size: 64, weight: 700, w: 420, h: 170 }],
      ['subheading', 'Add a subheading', { size: 36, weight: 600, w: 380, h: 100 }],
      ['body', 'Add body text', { size: 22, weight: 400, w: 340, h: 130 }],
    ];
    for (const [key, label, overrides] of presets) {
      const button = Core.el('button', { class: 'rb-text-preset', type: 'button' }, [
        Core.el('strong', { text: t(key), style: { fontSize: key === 'heading' ? '19px' : key === 'subheading' ? '16px' : '14px' } }),
        Core.el('span', { text: t('text') }),
      ]);
      button.addEventListener('click', () => insertText(overrides, key));
      host.append(button);
    }
    host.append(Core.el('p', { class: 'rb-note', text: t('textHint') }));
  }

  function buildLayersPanel(host) {
    panelTitle(host, 'layers');
    const list = Core.el('div', { class: 'rb-layer-list', dataset: { rbLayerList: 'true' } });
    host.append(list);
    fillLayers(list);
  }

  function fillLayers(list) {
    list.replaceChildren();
    const page = currentPage();
    if (!page) {
      list.append(Core.el('p', { class: 'rb-note', text: t('noPage') }));
      return;
    }
    if (!page.elements.length) {
      list.append(Core.el('p', { class: 'rb-note', text: t('noLayers') }));
      return;
    }
    const stack = [...page.elements].reverse();
    for (const element of stack) {
      const row = Core.el('div', {
        class: `rb-layer${selected.has(element.id) ? ' is-active' : ''}`,
        dataset: { rbLayer: element.id },
      });
      const label = Core.el('button', { class: 'rb-layer-name', type: 'button' }, [
        Core.svgIcon(
          element.type === 'text' ? Core.ICONS.text : element.type === 'image' ? Core.ICONS.image : Core.ICONS.shape,
          16,
        ),
        Core.el('span', { text: Core.elementName(element) }),
      ]);
      label.addEventListener('click', () => {
        select([element.id]);
        board.refreshOverlay();
      });
      label.addEventListener('dblclick', () => {
        if (element.type === 'text') board.startTextEdit(element.id);
      });

      const eye = iconButton(element.visible === false ? 'eyeOff' : 'eye', t('visibility'));
      eye.classList.toggle('is-off', element.visible === false);
      eye.addEventListener('click', () => {
        beginChange();
        element.visible = element.visible === false;
        quietCommit = true;
        commit('Toggle layer visibility');
        board.renderPage();
        refreshLayers();
      });

      const lock = iconButton(element.locked ? 'lock' : 'unlock', element.locked ? t('unlock') : t('lock'));
      lock.classList.toggle('is-off', !element.locked);
      lock.addEventListener('click', () => {
        beginChange();
        element.locked = !element.locked;
        quietCommit = true;
        commit('Toggle layer lock');
        refreshLayers();
      });

      row.append(label, eye, lock);
      list.append(row);
    }
  }

  function refreshLayers() {
    const list = root?.querySelector('[data-rb-layer-list]');
    if (list) fillLayers(list);
  }

  /* ---------------------------------------------------------------- */
  /* Insertion                                                         */
  /* ---------------------------------------------------------------- */

  function viewportCenter() {
    const rect = board.viewport.getBoundingClientRect();
    return board.worldFromClient(rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  function insertElement(element, label) {
    if (!currentPage()) {
      addPage(true);
      if (!currentPage()) return;
    }
    beginChange();
    element.w = Math.max(24, Math.min(element.w, doc.w - 48));
    element.h = Math.max(16, Math.min(element.h, doc.h - 48));
    const center = viewportCenter();
    element.x = Math.round(Math.max(24, Math.min(doc.w - element.w - 24, center.x - element.w / 2)));
    element.y = Math.round(Math.max(24, Math.min(doc.h - element.h - 24, center.y - element.h / 2)));
    currentPage().elements.push(element);
    currentPage().managedIds.push(element.id);
    commit(label || 'Add element');
    board.renderPage();
    select([element.id]);
    setTab(activeTab);
  }

  function insertShape(shape, gradient) {
    const element = Core.createElement(shape);
    if (shape === 'circle') {
      element.w = 220;
      element.h = 220;
    } else if (shape === 'line') {
      element.w = 320;
      element.h = 6;
      element.fill = '#141821';
    } else {
      element.w = 320;
      element.h = 220;
    }
    if (gradient) element.fill = { from: gradient.from, to: gradient.to, angle: gradient.angle };
    element.name = t(shape === 'circle' ? 'circle' : shape === 'line' ? 'line' : 'rectangle');
    insertElement(element, 'Add shape');
  }

  function insertText(overrides, preset) {
    const element = Core.createElement('text', overrides);
    element.name = t(preset || 'text');
    element.text = t(preset || 'body');
    element.font = 'noto-serif';
    element.color = '#141821';
    insertElement(element, 'Add text');
  }

  function insertImage(src, alt = '') {
    const element = Core.createElement('image', {
      src,
      alt,
      w: Math.min(doc.w * 0.5, 360),
      h: Math.min(doc.h * 0.4, 300),
    });
    insertElement(element, 'Add image');
  }

  /* ---------------------------------------------------------------- */
  /* Images                                                            */
  /* ---------------------------------------------------------------- */

  function pickImage(replaceId) {
    replaceTargetId = replaceId || null;
    fileInput?.click();
  }

  function pickReplacement(id) {
    if (selected.size !== 1) select([id]);
    pickImage(id);
  }

  async function handleImageFile(file) {
    if (!file || !/^image\//.test(file.type)) return;
    if (file.size > 12 * 1024 * 1024) {
      Core.toast(t('uploadTooLarge'), 'error');
      return;
    }
    const invitationId = window.EInviteContext?.getInvitationId?.() || '';
    if (!invitationId || !window.EInviteUpload?.upload) {
      Core.toast(t('uploadFailed'), 'error');
      return;
    }
    Core.toast(t('uploading'));
    try {
      const result = await window.EInviteUpload.upload(invitationId, file, {});
      const url = result?.url || result?.src || result?.path || '';
      if (!url) throw new Error('No upload URL');
      if (replaceTargetId) {
        const element = editor.findElement(replaceTargetId);
        if (element) {
          beginChange();
          element.src = url;
          element.alt = file.name || element.alt || '';
          commit('Replace image');
          board.renderPage();
          select([element.id]);
        }
      } else {
        insertImage(url, file.name || '');
      }
    } catch {
      Core.toast(t('uploadFailed'), 'error');
    } finally {
      replaceTargetId = null;
    }
  }

  /* ---------------------------------------------------------------- */
  /* Pages                                                             */
  /* ---------------------------------------------------------------- */

  function pageCount() {
    return doc?.pages?.length || 0;
  }

  function addPage(selectIt = true) {
    if (!doc) return;
    beginChange();
    const id = Core.uid('page');
    doc.pages.push({
      id,
      sourceId: null,
      name: t('page') + ' ' + (doc.pages.length + 1),
      background: '#fffaf6',
      elements: [],
      managedIds: [],
      unsupported: 0,
    });
    if (selectIt) pageIndex = doc.pages.length - 1;
    commit('Add page');
    renderAll();
    board.fit();
  }

  function duplicatePage() {
    const page = currentPage();
    if (!doc || !page) return;
    beginChange();
    const copy = Core.deepClone(page);
    copy.id = Core.uid('page');
    copy.sourceId = null;
    copy.name = `${page.name} ${t('copySuffix')}`;
    copy.elements = copy.elements.map((element) => ({ ...element, id: Core.uid(element.type) }));
    copy.managedIds = copy.elements.map((element) => element.id);
    doc.pages.splice(pageIndex + 1, 0, copy);
    pageIndex += 1;
    commit('Duplicate page');
    renderAll();
  }

  function deletePage() {
    const page = currentPage();
    if (!doc || !page) return;
    if (!window.confirm(t('deletePageConfirm'))) return;
    beginChange();
    doc.pages.splice(pageIndex, 1);
    pageIndex = Math.max(0, Math.min(pageIndex, doc.pages.length - 1));
    commit('Delete page');
    select([]);
    renderAll();
  }

  function switchPage(index) {
    if (!doc || index === pageIndex || !doc.pages[index]) return;
    board.finishTextEdit(true);
    pageIndex = index;
    select([]);
    board.renderPage();
    board.fit();
    refreshPages();
    refreshInspector();
    refreshLayers();
  }

  function refreshPages() {
    const host = root?.querySelector('[data-rb-pages]');
    if (!host) return;
    host.replaceChildren();
    const page = currentPage();
    if (!page) {
      host.hidden = true;
      return;
    }
    host.hidden = false;

    doc.pages.forEach((item, index) => {
      const button = Core.el('button', {
        class: `rb-page-chip${index === pageIndex ? ' is-active' : ''}`,
        type: 'button',
        'aria-label': `${t('page')} ${index + 1}`,
        title: item.name,
      });
      const canvas = document.createElement('canvas');
      button.append(canvas);
      button.addEventListener('click', () => switchPage(index));
      host.append(button);
      Core.paintThumbnail(canvas, doc, item, 46, 58).catch(() => null);
    });

    const add = Core.el('button', { class: 'rb-page-add', type: 'button', 'aria-label': t('addPage'), title: t('addPage') }, Core.svgIcon(Core.ICONS.plus, 18));
    add.addEventListener('click', () => addPage(true));
    host.append(add);
  }

  /* ---------------------------------------------------------------- */
  /* Inspector                                                         */
  /* ---------------------------------------------------------------- */

  function field(label, control, className = '') {
    return Core.el('label', { class: `rb-field ${className}`.trim() }, [
      Core.el('span', { class: 'rb-field-label', text: label }),
      control,
    ]);
  }

  function numberInput(value, onInput, onCommit, options = {}) {
    const input = Core.el('input', {
      type: 'number',
      value: String(Math.round(value)),
      class: 'rb-input',
      inputmode: 'decimal',
      min: options.min !== undefined ? String(options.min) : undefined,
      max: options.max !== undefined ? String(options.max) : undefined,
      step: options.step !== undefined ? String(options.step) : '1',
    });
    input.addEventListener('focus', () => beginChange());
    input.addEventListener('input', () => {
      const number = Number(input.value);
      if (Number.isFinite(number)) onInput(number);
    });
    input.addEventListener('change', () => onCommit());
    return input;
  }

  function colorRow(value, apply) {
    const row = Core.el('div', { class: 'rb-colors' });
    for (const color of Core.SWATCHES) {
      const swatch = Core.el('button', {
        class: `rb-swatch${String(value).toLowerCase() === color ? ' is-active' : ''}`,
        type: 'button',
        'aria-label': color,
        style: { background: color },
      });
      swatch.addEventListener('click', () => {
        beginChange();
        apply(color);
        quietCommit = true;
        commit('Set color');
        refreshInspector();
      });
      row.append(swatch);
    }
    return row;
  }

  function alignSelection(mode) {
    const elements = editor.selectedElements();
    if (!elements.length) return;
    beginChange();
    const minX = Math.min(...elements.map((element) => element.x));
    const maxX = Math.max(...elements.map((element) => element.x + element.w));
    const minY = Math.min(...elements.map((element) => element.y));
    const maxY = Math.max(...elements.map((element) => element.y + element.h));
    for (const element of elements) {
      if (mode === 'left') element.x = minX;
      if (mode === 'right') element.x = maxX - element.w;
      if (mode === 'center') element.x = (minX + maxX) / 2 - element.w / 2;
      if (mode === 'top') element.y = minY;
      if (mode === 'bottom') element.y = maxY - element.h;
      if (mode === 'middle') element.y = (minY + maxY) / 2 - element.h / 2;
    }
    quietCommit = true;
    commit('Align elements');
    board.refreshNodes();
    refreshInspector();
  }

  function refreshInspector() {
    const host = root?.querySelector('[data-rb-inspector]');
    if (!host) return;
    host.replaceChildren();

    const page = currentPage();
    if (!page) {
      host.append(Core.el('p', { class: 'rb-note', text: t('noPage') }));
      return;
    }

    const chosen = editor.selectedElements();

    if (!chosen.length) {
      host.append(Core.el('h2', { class: 'rb-inspector-title', text: t('pageSettings') }));
      const name = Core.el('input', { class: 'rb-input', type: 'text', value: page.name, maxlength: '80' });
      name.addEventListener('focus', () => beginChange());
      name.addEventListener('change', () => {
        page.name = name.value.trim() || page.name;
        quietCommit = true;
        commit('Rename page');
        refreshPages();
      });
      host.append(field(t('pageName'), name));

      host.append(Core.el('h3', { class: 'rb-group-title', text: t('background') }));
      host.append(colorRow(page.background, (color) => {
        page.background = color;
        board.renderPage();
      }));

      if (page.unsupported) {
        host.append(Core.el('p', { class: 'rb-note', text: t('unsupported', { n: page.unsupported }) }));
      }

      const actions = Core.el('div', { class: 'rb-stack' });
      const duplicate = Core.el('button', { class: 'rb-wide-btn', type: 'button', text: t('duplicatePage') });
      duplicate.addEventListener('click', duplicatePage);
      const remove = Core.el('button', { class: 'rb-wide-btn is-danger', type: 'button', text: t('deletePage') });
      remove.addEventListener('click', deletePage);
      actions.append(duplicate, remove);
      host.append(actions);
      return;
    }

    if (chosen.length > 1) {
      host.append(Core.el('h2', { class: 'rb-inspector-title', text: t('elementsCount', { n: chosen.length }) }));
      host.append(alignButtons());
      host.append(arrangeButtons());
      host.append(elementActions());
      return;
    }

    const element = chosen[0];
    host.append(Core.el('h2', { class: 'rb-inspector-title', text: Core.elementName(element) }));

    host.append(Core.el('h3', { class: 'rb-group-title', text: t('position') }));
    const grid = Core.el('div', { class: 'rb-grid-2' });
    const x = numberInput(element.x, (value) => { element.x = value; board.refreshNodes([element.id]); }, () => commitFromInspector('Move element'));
    const y = numberInput(element.y, (value) => { element.y = value; board.refreshNodes([element.id]); }, () => commitFromInspector('Move element'));
    const w = numberInput(element.w, (value) => { element.w = Math.max(8, value); board.refreshNodes([element.id]); }, () => commitFromInspector('Resize element'), { min: 8 });
    const h = numberInput(element.h, (value) => { element.h = Math.max(8, value); board.refreshNodes([element.id]); }, () => commitFromInspector('Resize element'), { min: 8 });
    grid.append(field('X', x), field('Y', y), field('W', w), field('H', h));
    host.append(grid);

    const rotation = numberInput(element.rotation || 0, (value) => {
      element.rotation = value;
      board.refreshNodes([element.id]);
    }, () => commitFromInspector('Rotate element'), { min: -360, max: 360 });
    host.append(field(t('rotation'), rotation));

    const opacity = Core.el('input', { type: 'range', min: '5', max: '100', value: String(Math.round((element.opacity ?? 1) * 100)), class: 'rb-range' });
    opacity.addEventListener('focus', () => beginChange());
    opacity.addEventListener('input', () => {
      element.opacity = Number(opacity.value) / 100;
      board.refreshNodes([element.id]);
    });
    opacity.addEventListener('change', () => commitFromInspector('Set opacity'));
    host.append(field(t('opacity'), opacity));

    if (element.type === 'text') host.append(textControls(element));
    if (element.type === 'shape') host.append(shapeControls(element));
    if (element.type === 'image') host.append(imageControls(element));

    host.append(arrangeButtons());
    host.append(elementActions());
  }

  function commitFromInspector(label) {
    quietCommit = true;
    commit(label);
  }

  function textControls(element) {
    const frag = document.createDocumentFragment();
    frag.append(Core.el('h3', { class: 'rb-group-title', text: t('typography') }));

    const font = Core.el('select', { class: 'rb-input' });
    for (const option of Core.fontList()) {
      font.append(Core.el('option', { value: option.id, text: option.label, selected: option.id === element.font }));
    }
    font.addEventListener('focus', () => beginChange());
    font.addEventListener('change', () => {
      element.font = font.value;
      commitFromInspector('Set font');
      board.refreshNodes([element.id]);
    });
    frag.append(field(t('font'), font));

    const size = numberInput(element.size, (value) => {
      element.size = value;
      board.refreshNodes([element.id]);
    }, () => commitFromInspector('Set font size'), { min: 8, max: 240 });
    frag.append(field(t('size'), size));

    const weight = Core.el('select', { class: 'rb-input' });
    for (const [value, label] of [['400', 'Regular'], ['500', 'Medium'], ['600', 'Semibold'], ['700', 'Bold'], ['800', 'Extrabold']]) {
      weight.append(Core.el('option', { value, text: label, selected: String(element.weight) === value }));
    }
    weight.addEventListener('focus', () => beginChange());
    weight.addEventListener('change', () => {
      element.weight = Number(weight.value);
      commitFromInspector('Set font weight');
      board.refreshNodes([element.id]);
    });
    frag.append(field(t('weight'), weight));

    const alignRow = Core.el('div', { class: 'rb-btn-row' });
    for (const mode of ['left', 'center', 'right']) {
      const button = iconButton(`align${mode[0].toUpperCase()}${mode.slice(1)}`, mode);
      button.classList.toggle('is-active', element.align === mode);
      button.addEventListener('click', () => {
        beginChange();
        element.align = mode;
        commitFromInspector('Set text alignment');
        board.refreshNodes([element.id]);
        refreshInspector();
      });
      alignRow.append(button);
    }
    const bold = iconButton('bold', t('bold'));
    bold.classList.toggle('is-active', Number(element.weight) >= 700);
    bold.addEventListener('click', () => {
      beginChange();
      element.weight = Number(element.weight) >= 700 ? 400 : 700;
      commitFromInspector('Toggle bold');
      board.refreshNodes([element.id]);
      refreshInspector();
    });
    const italic = iconButton('italic', t('italic'));
    italic.classList.toggle('is-active', element.italic);
    italic.addEventListener('click', () => {
      beginChange();
      element.italic = !element.italic;
      commitFromInspector('Toggle italic');
      board.refreshNodes([element.id]);
      refreshInspector();
    });
    const underline = iconButton('underline', t('underline'));
    underline.classList.toggle('is-active', element.underline);
    underline.addEventListener('click', () => {
      beginChange();
      element.underline = !element.underline;
      commitFromInspector('Toggle underline');
      board.refreshNodes([element.id]);
      refreshInspector();
    });
    frag.append(field(t('align'), alignRow));

    const styleRow = Core.el('div', { class: 'rb-btn-row' });
    styleRow.append(bold, italic, underline);
    frag.append(field(t('style'), styleRow));

    frag.append(Core.el('h3', { class: 'rb-group-title', text: t('color') }));
    frag.append(colorRow(element.color, (color) => {
      element.color = color;
      board.refreshNodes([element.id]);
    }));
    return frag;
  }

  function shapeControls(element) {
    const frag = document.createDocumentFragment();
    frag.append(Core.el('h3', { class: 'rb-group-title', text: t('fill') }));
    frag.append(colorRow(Core.isGradient(element.fill) ? '#7d2ae8' : element.fill, (color) => {
      element.fill = color;
      board.refreshNodes([element.id]);
    }));

    const gradients = Core.el('div', { class: 'rb-gradient-grid' });
    for (const gradient of Core.GRADIENTS) {
      const button = Core.el('button', {
        class: 'rb-gradient',
        type: 'button',
        title: gradient.name,
        style: { background: Core.fillCss(gradient) },
      });
      button.addEventListener('click', () => {
        beginChange();
        element.fill = { from: gradient.from, to: gradient.to, angle: gradient.angle };
        commitFromInspector('Set gradient');
        board.refreshNodes([element.id]);
      });
      gradients.append(button);
    }
    frag.append(gradients);

    if (element.shape !== 'circle') {
      const radius = Core.el('input', { type: 'range', min: '0', max: '120', value: String(element.radius || 0), class: 'rb-range' });
      radius.addEventListener('focus', () => beginChange());
      radius.addEventListener('input', () => {
        element.radius = Number(radius.value);
        board.refreshNodes([element.id]);
      });
      radius.addEventListener('change', () => commitFromInspector('Set corner radius'));
      frag.append(field(t('corners'), radius));
    }
    return frag;
  }

  function imageControls(element) {
    const frag = document.createDocumentFragment();
    frag.append(Core.el('h3', { class: 'rb-group-title', text: t('image') }));

    const fit = Core.el('select', { class: 'rb-input' });
    fit.append(Core.el('option', { value: 'cover', text: t('fillFrame'), selected: element.fit !== 'contain' }));
    fit.append(Core.el('option', { value: 'contain', text: t('fitInside'), selected: element.fit === 'contain' }));
    fit.addEventListener('focus', () => beginChange());
    fit.addEventListener('change', () => {
      element.fit = fit.value;
      commitFromInspector('Set image fit');
      board.refreshNodes([element.id]);
    });
    frag.append(field(t('fit'), fit));

    const radius = Core.el('input', { type: 'range', min: '0', max: '200', value: String(element.radius || 0), class: 'rb-range' });
    radius.addEventListener('focus', () => beginChange());
    radius.addEventListener('input', () => {
      element.radius = Number(radius.value);
      board.refreshNodes([element.id]);
    });
    radius.addEventListener('change', () => commitFromInspector('Set image corners'));
    frag.append(field(t('corners'), radius));

    const replace = Core.el('button', { class: 'rb-wide-btn', type: 'button', text: t('replaceImage') });
    replace.addEventListener('click', () => pickImage(element.id));
    frag.append(replace);
    return frag;
  }

  function alignButtons() {
    const row = Core.el('div', { class: 'rb-btn-row rb-btn-row-wide' });
    for (const mode of ['left', 'center', 'right', 'top', 'middle', 'bottom']) {
      const button = iconButton(`align${mode[0].toUpperCase()}${mode.slice(1)}`, mode);
      button.addEventListener('click', () => alignSelection(mode));
      row.append(button);
    }
    return row;
  }

  function arrangeButtons() {
    const frag = document.createDocumentFragment();
    frag.append(Core.el('h3', { class: 'rb-group-title', text: t('arrange') }));
    const row = Core.el('div', { class: 'rb-btn-row' });
    for (const [icon, mode, label] of [
      ['toFront', 'front', 'toFront'],
      ['forward', 'forward', 'forward'],
      ['backward', 'backward', 'backward'],
      ['toBack', 'back', 'toBack'],
    ]) {
      const button = iconButton(icon, t(label));
      button.addEventListener('click', () => {
        board.arrange(mode);
        refreshLayers();
        refreshInspector();
      });
      row.append(button);
    }
    frag.append(row);
    return frag;
  }

  function elementActions() {
    const frag = document.createDocumentFragment();
    const actions = Core.el('div', { class: 'rb-btn-row' });
    const single = editor.selectedElements()[0];
    const duplicate = iconButton('copy', t('duplicate'));
    duplicate.addEventListener('click', () => {
      board.duplicateSelection();
      refreshLayers();
      refreshInspector();
    });
    actions.append(duplicate);

    if (single) {
      const lock = iconButton(single.locked ? 'lock' : 'unlock', single.locked ? t('unlock') : t('lock'));
      lock.classList.toggle('is-active', single.locked);
      lock.addEventListener('click', () => {
        beginChange();
        single.locked = !single.locked;
        commitFromInspector('Toggle lock');
        refreshInspector();
      });
      actions.append(lock);
    }

    const remove = iconButton('trash', t('remove'));
    remove.classList.add('is-danger');
    remove.addEventListener('click', () => {
      board.deleteSelection();
      refreshLayers();
      refreshInspector();
    });
    actions.append(remove);
    frag.append(actions);
    return frag;
  }

  /* ---------------------------------------------------------------- */
  /* Preview and export                                                */
  /* ---------------------------------------------------------------- */

  function hidePreview() {
    const layer = root?.querySelector('[data-rb-preview]');
    if (layer) {
      layer.hidden = true;
      layer.querySelector('canvas')?.remove();
    }
    previewOpen = false;
  }

  async function showPreview() {
    const page = currentPage();
    if (!page || previewOpen) return;
    try {
      const canvas = await Core.renderPageToCanvas(doc, page, { scale: 1 });
      canvas.className = 'rb-preview-canvas';
      const layer = root.querySelector('[data-rb-preview]');
      layer.querySelector('canvas')?.remove();
      layer.querySelector('.rb-preview-card').append(canvas);
      layer.hidden = false;
      previewOpen = true;
    } catch {
      Core.toast(t('exportFailed'), 'error');
    }
  }

  async function exportPng() {
    const page = currentPage();
    if (!page) return;
    try {
      const canvas = await Core.renderPageToCanvas(doc, page, { scale: 2 });
      const blob = await Core.canvasToBlob(canvas, 'image/png');
      if (!blob) throw new Error('No blob');
      const name = String(page.name || 'invitation-page')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '') || 'invitation-page';
      await Core.downloadBlob(blob, `${name}.png`);
    } catch {
      Core.toast(t('exportFailed'), 'error');
    }
  }

  /* ---------------------------------------------------------------- */
  /* Open, close, keyboard                                             */
  /* ---------------------------------------------------------------- */

  function refreshSaveState() {
    const save = root?.querySelector('[data-rb-save]');
    if (!save) return;
    save.textContent = t('saved');
  }

  function renderAll() {
    if (!doc) return;
    board.renderPage();
    refreshPages();
    refreshInspector();
    refreshLayers();
    refreshPanel();
    const empty = root.querySelector('[data-rb-empty]');
    if (empty) empty.hidden = pageCount() > 0;
    const title = root.querySelector('[data-rb-title]');
    if (title) title.textContent = doc.title;
  }

  function setBackgroundInert(on) {
    for (const child of Array.from(document.body.children)) {
      if (child === root || child.id === 'toasts') continue;
      if (/^(SCRIPT|STYLE|LINK|TEMPLATE)$/.test(child.tagName)) continue;
      if (on) child.setAttribute('inert', '');
      else child.removeAttribute('inert');
    }
  }

  function open() {
    if (!bridge()?.getState) {
      Core.toast(t('editorNotReady'), 'error');
      return;
    }
    if (!root) buildShell();
    hydrate();
    opened = true;
    pageIndex = Math.min(pageIndex, Math.max(0, pageCount() - 1));
    root.hidden = false;
    document.body.classList.add('rb-open');
    setBackgroundInert(true);
    setTab(activeTab);
    renderAll();
    board.fit();
    root.querySelector('[data-rea-viewport]')?.focus({ preventScroll: true });
  }

  function close() {
    if (!root) return;
    hidePreview();
    board?.finishTextEdit(true);
    root.hidden = true;
    opened = false;
    root.classList.remove('rb-panel-open');
    document.body.classList.remove('rb-open');
    setBackgroundInert(false);
    document.getElementById('reaBoardBtn')?.focus({ preventScroll: true });
  }

  function isTypingTarget(target) {
    return Boolean(
      target &&
        (target.isContentEditable ||
          /^(INPUT|TEXTAREA|SELECT|OPTION)$/.test(target.tagName || '')),
    );
  }

  function onKeyDown(event) {
    if (!opened) return;
    if (event.key === 'Escape') {
      if (previewOpen) {
        hidePreview();
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      if (selected.size) {
        select([]);
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      close();
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (isTypingTarget(event.target)) return;

    const mod = event.ctrlKey || event.metaKey;
    if (mod && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      event.stopPropagation();
      if (event.shiftKey) redo();
      else undo();
      return;
    }
    if (mod && event.key.toLowerCase() === 'y') {
      event.preventDefault();
      event.stopPropagation();
      redo();
      return;
    }
    if (mod && event.key.toLowerCase() === 'd') {
      event.preventDefault();
      event.stopPropagation();
      board.duplicateSelection();
      refreshLayers();
      refreshInspector();
      return;
    }
    if (mod && event.key.toLowerCase() === 'a') {
      event.preventDefault();
      event.stopPropagation();
      board.selectAll();
      return;
    }
    if (event.key === 'Backspace' || event.key === 'Delete') {
      event.preventDefault();
      event.stopPropagation();
      board.deleteSelection();
      refreshLayers();
      refreshInspector();
      return;
    }
    if (event.key === ' ') {
      event.preventDefault();
      event.stopPropagation();
      board.setSpace(true);
      return;
    }
    const step = event.shiftKey ? 10 : 1;
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      event.stopPropagation();
      board.nudge(-step, 0);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      event.stopPropagation();
      board.nudge(step, 0);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      event.stopPropagation();
      board.nudge(0, -step);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      event.stopPropagation();
      board.nudge(0, step);
    }
  }

  function onKeyUp(event) {
    if (opened && event.key === ' ') board?.setSpace(false);
  }

  function wireEntry() {
    const button = document.getElementById('reaBoardBtn');
    if (!button || button.dataset.rbWired === 'true') return;
    button.dataset.rbWired = 'true';
    button.addEventListener('click', open);
  }

  document.addEventListener('keydown', onKeyDown, true);
  document.addEventListener('keyup', onKeyUp, true);
  document.addEventListener('einvite:lang-changed', () => {
    if (!root) return;
    root.querySelector('.rb-back span').textContent = t('back');
    const brand = root.querySelector('.rb-brand-name');
    if (brand) brand.textContent = t('board');
    refreshSaveState();
    renderAll();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireEntry, { once: true });
  } else {
    wireEntry();
  }

  window.ReaBoardApp = { open, close, isOpen: () => opened };
})();
