// Left tool panels: templates, elements, text, brand, uploads, layers.

import { SHAPES, TEMPLATES, FONTS, GRADIENTS, SHAPE_LABELS, fillCss, polygonCss } from '../model.js';
import { loadImage, paintThumbnail } from '../render.js';
import {
  addUpload,
  getBrand as readBrand,
  listUploads,
  readFileAsDataUrl,
  saveBrand,
} from '../storage.js';
import { el, openModal, svgIcon, toast, uid, ICONS } from '../util.js';

const TABS = [
  { id: 'templates', label: 'Templates', icon: 'template' },
  { id: 'elements', label: 'Elements', icon: 'shape' },
  { id: 'text', label: 'Text', icon: 'text' },
  { id: 'brand', label: 'Brand', icon: 'brand' },
  { id: 'uploads', label: 'Uploads', icon: 'upload' },
  { id: 'layers', label: 'Layers', icon: 'layers' },
];

export function mountPanels({ rail, panel, editor }) {
  let active = null;
  const templatePages = new Map();
  const railButtons = new Map();

  const title = el('h2', { class: 'panel-title', id: 'panelTitle', text: 'Templates' });
  const close = el('button', { class: 'icon-btn panel-close', type: 'button', 'aria-label': 'Close panel' }, svgIcon(ICONS.close, 18));
  close.addEventListener('click', () => setActive(null));
  const body = el('div', { class: 'panel-body', id: 'panelBody' });
  panel.append(el('div', { class: 'panel-head' }, [title, close]), body);

  for (const tab of TABS) {
    const button = el('button', { class: 'rail-btn', type: 'button', 'data-tab': tab.id }, [
      svgIcon(ICONS[tab.icon], 22),
      el('span', { class: 'rail-label', text: tab.label }),
    ]);
    button.addEventListener('click', () => setActive(active === tab.id ? null : tab.id));
    railButtons.set(tab.id, button);
    rail.append(button);
  }

  const api = { refreshLayers, addUpload: storeUpload, setTab: setActive };

  function setActive(id) {
    active = id;
    document.body.classList.toggle('panel-open', Boolean(id));
    for (const [tabId, button] of railButtons) button.classList.toggle('is-active', tabId === id);
    if (!id) {
      body.replaceChildren();
      return;
    }
    const tab = TABS.find((item) => item.id === id);
    title.textContent = tab.label;
    body.replaceChildren();
    body.scrollTop = 0;
    if (id === 'templates') body.append(renderTemplates());
    if (id === 'elements') body.append(renderElements());
    if (id === 'text') body.append(renderText());
    if (id === 'brand') body.append(renderBrand());
    if (id === 'uploads') body.append(renderUploads());
    if (id === 'layers') body.append(renderLayers());
  }

  function group(heading, children) {
    return el('section', { class: 'panel-section' }, [
      el('h3', { class: 'panel-heading', text: heading }),
      ...children,
    ]);
  }

  /* ---------------------------- Templates --------------------------- */

  function pagesFor(template) {
    if (!templatePages.has(template.id)) templatePages.set(template.id, template.buildPages());
    return templatePages.get(template.id);
  }

  function renderTemplates() {
    const grid = el('div', { class: 'template-list' });
    for (const template of TEMPLATES) {
      const card = el('button', { class: 'template-tile', type: 'button' });
      const media = el('span', { class: 'template-media' });
      const canvas = el('canvas', { class: 'template-thumb' });
      media.append(canvas);
      card.append(media, el('span', { class: 'template-name', text: template.name }), el('span', { class: 'template-tag', text: template.category }));
      card.addEventListener('click', () => confirmTemplate(template));
      grid.append(card);
      paintThumbnail(canvas, { w: template.w, h: template.h }, pagesFor(template)[0], 240, 150).catch(() => null);
    }
    return el('div', {}, [
      el('p', { class: 'panel-note', text: 'Applying a template replaces the current pages. Undo brings them back.' }),
      grid,
    ]);
  }

  function confirmTemplate(template) {
    openModal({
      title: `Apply "${template.name}"?`,
      subtitle: 'This replaces every page in this design. You can undo it afterwards.',
      content: el('p', { class: 'modal-copy', text: `${template.w} x ${template.h} px - ${template.category}` }),
      actions: [
        { label: 'Cancel' },
        { label: 'Apply template', variant: 'primary', onSelect: () => editor.applyTemplate(template) },
      ],
    });
  }

  /* ---------------------------- Elements ---------------------------- */

  function insertShape(shape) {
    const base = Math.min(editor.doc.w, editor.doc.h);
    const size = Math.round(base * (shape.type === 'line' ? 0.06 : 0.32));
    const width = shape.type === 'line' ? Math.round(base * 0.42) : size;
    const height = shape.type === 'line' ? Math.max(4, Math.round(base * 0.008)) : size;
    const fill = shape.gradient || readBrand().colors[0] || '#7d2ae8';
    editor.addElement({
      id: `${shape.type}-${uid('s').slice(-5)}`,
      type: shape.type,
      name: shape.label || SHAPE_LABELS[shape.type],
      x: Math.round((editor.doc.w - width) / 2),
      y: Math.round((editor.doc.h - height) / 2),
      w: width,
      h: height,
      rotation: 0,
      opacity: 1,
      locked: false,
      visible: true,
      fill,
      stroke: 'transparent',
      strokeWidth: 0,
      radius: shape.radius || 0,
    });
  }

  function renderElements() {
    const grid = el('div', { class: 'shape-grid' });
    for (const shape of SHAPES) {
      const tile = el('button', { class: 'shape-tile', type: 'button', title: shape.label });
      const preview = el('span', { class: 'shape-preview' });
      if (shape.type === 'line') preview.style.cssText = 'height:4px;border-radius:2px;background:#12161c;width:56%';
      else {
        preview.style.background = 'linear-gradient(135deg,#8b3dff,#00c4cc)';
        if (shape.type === 'ellipse') preview.style.borderRadius = '50%';
        else if (shape.type === 'roundRect') preview.style.borderRadius = '26%';
        else if (['triangle', 'star', 'diamond', 'hexagon', 'arrow'].includes(shape.type)) {
          preview.style.clipPath = polygonCss(shape.type);
        }
      }
      tile.append(preview, el('span', { class: 'shape-label', text: shape.label }));
      tile.addEventListener('click', () => insertShape(shape));
      grid.append(tile);
    }

    const gradients = el('div', { class: 'gradient-grid' });
    for (const preset of GRADIENTS) {
      const card = el('button', { class: 'gradient-tile', type: 'button', title: preset.name });
      card.style.background = fillCss(preset);
      card.append(el('span', { class: 'gradient-name', text: preset.name }));
      card.addEventListener('click', () => insertShape({ type: 'rect', label: 'Gradient panel', gradient: { ...preset } }));
      gradients.append(card);
    }

    return el('div', {}, [
      group('Shapes', [grid]),
      group('Gradient panels', [gradients]),
      el('p', { class: 'panel-note', text: 'Tip: hold Shift while resizing a corner to keep proportions.' }),
    ]);
  }

  /* ------------------------------ Text ------------------------------ */

  function renderText() {
    const presets = [
      ['heading', 'Add a heading', 'preset-heading'],
      ['subheading', 'Add a subheading', 'preset-subheading'],
      ['body', 'Add body text', 'preset-body'],
    ];
    const list = el('div', { class: 'text-presets' });
    for (const [kind, label, className] of presets) {
      const button = el('button', { class: `text-preset ${className}`, type: 'button' }, el('span', { text: label }));
      button.addEventListener('click', () => editor.addTextPreset(kind));
      list.append(button);
    }

    const selectedText = editor.selectedElements().some((element) => element.type === 'text');
    const fonts = el('div', { class: 'font-list' });
    for (const font of FONTS) {
      const button = el('button', { class: 'font-tile', type: 'button' }, [
        el('span', { class: 'font-aa', text: 'Aa', style: { fontFamily: font.stack } }),
        el('span', { class: 'font-name', text: font.name }),
        el('span', { class: 'font-kind', text: font.kind }),
      ]);
      button.addEventListener('click', () => {
        if (selectedText) editor.setTextStyle({ font: font.id });
        else editor.addElement({
          id: `text-${uid('t').slice(-5)}`,
          type: 'text',
          name: `${font.name} heading`,
          x: Math.round(editor.doc.w * 0.1),
          y: Math.round(editor.doc.h * 0.4),
          w: Math.round(editor.doc.w * 0.72),
          h: Math.round(editor.doc.h * 0.16),
          rotation: 0,
          opacity: 1,
          locked: false,
          visible: true,
          text: 'Add a heading',
          font: font.id,
          size: Math.round(editor.doc.w * 0.06),
          weight: 700,
          italic: false,
          underline: false,
          align: 'left',
          color: '#12161c',
          lineHeight: 1.1,
          letterSpacing: 0,
        }, { edit: true });
      });
      fonts.append(button);
    }

    return el('div', {}, [
      group('Text styles', [list]),
      group('Fonts', [fonts, el('p', { class: 'panel-note', text: selectedText ? 'Click a font to apply it to the selected text.' : 'Click a font to place a heading in it.' })]),
    ]);
  }

  /* ------------------------------ Brand ----------------------------- */

  function renderBrand() {
    const brand = readBrand();
    const colors = el('div', { class: 'brand-colors' });
    for (const color of brand.colors) {
      const swatch = el('button', {
        class: 'brand-swatch',
        type: 'button',
        title: color,
        style: { background: color },
      });
      swatch.addEventListener('click', () => applyBrandColor(color));
      colors.append(swatch);
    }

    const colorInput = el('input', { class: 'color-input', type: 'color', value: brand.colors[0] || '#7d2ae8', 'aria-label': 'Add brand colour' });
    const addColor = el('button', { class: 'wide-btn', type: 'button', text: 'Add colour from picker' });
    addColor.addEventListener('click', () => {
      const color = colorInput.value;
      if (!brand.colors.includes(color)) {
        brand.colors = [...brand.colors, color].slice(0, 12);
        saveBrand(brand);
        setActive('brand');
      }
    });

    const headingSelect = fontSelect(brand.heading, (value) => {
      brand.heading = value;
      saveBrand(brand);
    });
    const bodySelect = fontSelect(brand.body, (value) => {
      brand.body = value;
      saveBrand(brand);
    });

    const applyHeading = el('button', { class: 'wide-btn', type: 'button', text: 'Apply heading font to selection' });
    applyHeading.addEventListener('click', () => {
      if (!editor.selectedElements().some((element) => element.type === 'text')) {
        toast('Select a text element first');
        return;
      }
      editor.setTextStyle({ font: brand.heading });
    });

    return el('div', {}, [
      group('Brand colours', [colors, el('div', { class: 'brand-add' }, [colorInput, addColor])]),
      group('Brand type', [
        el('label', { class: 'field field-full' }, [el('span', { class: 'field-label', text: 'Heading' }), headingSelect]),
        el('label', { class: 'field field-full' }, [el('span', { class: 'field-label', text: 'Body' }), bodySelect]),
        applyHeading,
      ]),
      el('p', { class: 'panel-note', text: 'Brand colours apply to the selection, or to the page background when nothing is selected.' }),
    ]);
  }

  function fontSelect(current, onChange) {
    const select = el('select', { class: 'field-input' });
    for (const font of FONTS) {
      const option = el('option', { value: font.id, text: font.name });
      if (font.id === current) option.selected = true;
      select.append(option);
    }
    select.addEventListener('change', () => onChange(select.value));
    return select;
  }

  function applyBrandColor(color) {
    const selected = editor.selectedElements();
    if (!selected.length) editor.setPageBackground(color);
    else if (selected.every((element) => element.type === 'text')) editor.setTextStyle({ color });
    else editor.updateSelected({ fill: color }, 'Set brand fill');
  }

  /* ----------------------------- Uploads ---------------------------- */

  async function insertImage(src) {
    const image = await loadImage(src);
    const maxW = editor.doc.w * 0.42;
    const maxH = editor.doc.h * 0.42;
    let width = image?.naturalWidth || 800;
    let height = image?.naturalHeight || 600;
    const fit = Math.min(maxW / width, maxH / height, 1);
    width = Math.round(width * fit);
    height = Math.round(height * fit);
    editor.addElement({
      id: `image-${uid('i').slice(-5)}`,
      type: 'image',
      name: 'Image',
      x: Math.round((editor.doc.w - width) / 2),
      y: Math.round((editor.doc.h - height) / 2),
      w: width,
      h: height,
      rotation: 0,
      opacity: 1,
      locked: false,
      visible: true,
      src,
      fit: 'cover',
    });
  }

  async function handleFile(file) {
    if (!file.type.startsWith('image/')) {
      toast('Choose an image file');
      return;
    }
    if (file.size > 2_000_000) {
      toast('Keep uploads under 2 MB so the design fits in browser storage');
      return;
    }
    const src = await readFileAsDataUrl(file);
    if (!addUpload(file.name, src)) {
      toast('Browser storage is full - this image was not saved');
      return;
    }
    await insertImage(src);
    if (active === 'uploads') setActive('uploads');
  }

  function storeUpload(name, src) {
    addUpload(name, src);
    if (active === 'uploads') setActive('uploads');
  }

  function renderUploads() {
    const input = el('input', { type: 'file', accept: 'image/*', class: 'visually-hidden' });
    input.addEventListener('change', async () => {
      const file = input.files?.[0];
      input.value = '';
      if (file) await handleFile(file);
    });
    const drop = el('button', { class: 'upload-drop', type: 'button' }, [
      svgIcon(ICONS.upload, 22),
      el('span', { class: 'upload-title', text: 'Upload an image' }),
      el('span', { class: 'upload-hint', text: 'PNG, JPG or WebP up to 2 MB' }),
    ]);
    drop.addEventListener('click', () => input.click());
    drop.addEventListener('dragover', (event) => {
      event.preventDefault();
      drop.classList.add('is-over');
    });
    drop.addEventListener('dragleave', () => drop.classList.remove('is-over'));
    drop.addEventListener('drop', async (event) => {
      event.preventDefault();
      drop.classList.remove('is-over');
      const file = event.dataTransfer?.files?.[0];
      if (file) await handleFile(file);
    });

    const uploads = listUploads();
    const grid = el('div', { class: 'upload-grid' });
    if (!uploads.length) {
      grid.append(el('p', { class: 'panel-empty', text: 'Nothing uploaded yet. Images you add are kept in this browser.' }));
    }
    for (const upload of uploads) {
      const tile = el('button', { class: 'upload-tile', type: 'button', title: upload.name });
      const image = el('img', { src: upload.src, alt: upload.name, loading: 'lazy' });
      tile.append(image, el('span', { class: 'upload-name', text: upload.name }));
      tile.addEventListener('click', () => insertImage(upload.src));
      grid.append(tile);
    }

    return el('div', {}, [drop, input, el('p', { class: 'panel-note', text: 'Or drag an image straight onto the board.' }), grid]);
  }

  /* ------------------------------ Layers ---------------------------- */

  function renderLayers() {
    const list = el('div', { class: 'layer-list' });
    const elements = [...editor.page.elements].reverse();
    if (!elements.length) {
      list.append(el('p', { class: 'panel-empty', text: 'This page is empty. Add an element from Elements or Text.' }));
    }
    for (const element of elements) {
      const row = el('div', {
        class: `layer-row${editor.selected.has(element.id) ? ' is-active' : ''}${element.visible === false ? ' is-hidden' : ''}`,
        tabindex: '0',
        dataset: { id: element.id },
      });
      const eye = el('button', {
        class: 'layer-icon',
        type: 'button',
        title: element.visible === false ? 'Show layer' : 'Hide layer',
        'aria-label': element.visible === false ? 'Show layer' : 'Hide layer',
      }, svgIcon(element.visible === false ? ICONS.eyeOff : ICONS.eye, 16));
      eye.addEventListener('click', (event) => {
        event.stopPropagation();
        editor.toggleVisible(element.id);
      });
      const lock = el('button', {
        class: 'layer-icon',
        type: 'button',
        title: element.locked ? 'Unlock layer' : 'Lock layer',
        'aria-label': element.locked ? 'Unlock layer' : 'Lock layer',
      }, svgIcon(element.locked ? ICONS.lock : ICONS.unlock, 16));
      lock.addEventListener('click', (event) => {
        event.stopPropagation();
        const next = !element.locked;
        element.locked = next;
        editor.board.renderPage();
        editor.commit(next ? 'Lock layer' : 'Unlock layer');
        editor.inspector.render();
        refreshLayers();
      });
      row.append(
        eye,
        el('span', { class: 'layer-name', text: element.name || SHAPE_LABELS[element.type] || 'Element' }),
        lock,
      );
      row.addEventListener('click', () => editor.select([element.id]));
      row.addEventListener('dblclick', () => {
        if (element.type === 'text') editor.board.startTextEdit(element.id);
      });
      row.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') editor.select([element.id]);
      });
      list.append(row);
    }
    return el('div', {}, [
      list,
      el('p', { class: 'panel-note', text: 'Reorder with Arrange in the inspector. Click a layer to select it on the board.' }),
    ]);
  }

  function refreshLayers() {
    if (active === 'layers') {
      body.replaceChildren(renderLayers());
    }
  }

  setActive(null);
  return api;
}
