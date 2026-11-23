// Dashboard: quick create, recent designs, templates and search.

import { debounce } from './batch.js';
import { PAGE_PRESETS, TEMPLATES } from './model.js';
import { ensureFonts, paintThumbnail } from './render.js';
import { createNewDesign, deleteDesign, duplicateDesign, listDesigns } from './storage.js';
import {
  $,
  $$,
  el,
  formatRelative,
  openMenu,
  openModal,
  svgIcon,
  toast,
  ICONS,
} from './util.js';

const state = { view: 'home', query: '' };
const quickPresets = ['social', 'story', 'presentation', 'poster', 'card', 'document'];

const recentGrid = $('#recentGrid');
const templateGrid = $('#templateGrid');
const recentSection = $('#recentSection');
const templatesSection = $('#templatesSection');
const heroTitle = $('#heroTitle');

renderQuickCreate();
wireNav();
wireSearch();
wireCreate();
wireHelp();
render();
ensureFonts().then(render);

function render() {
  const designs = listDesigns();
  const query = state.query.trim().toLowerCase();
  const filtered = designs.filter((design) => !query || design.title.toLowerCase().includes(query));
  const templates = TEMPLATES.filter(
    (template) =>
      !query ||
      template.name.toLowerCase().includes(query) ||
      template.category.toLowerCase().includes(query),
  );

  const showDesigns = state.view !== 'templates';
  const showTemplates = state.view !== 'designs';
  recentSection.hidden = !showDesigns;
  templatesSection.hidden = !showTemplates;

  if (state.view === 'templates') heroTitle.textContent = 'Start from a template';
  else if (state.view === 'designs') heroTitle.textContent = 'Your designs';
  else heroTitle.textContent = 'What will you design today?';

  recentGrid.replaceChildren();
  if (showDesigns) renderDesigns(filtered);
  templateGrid.replaceChildren();
  if (showTemplates) renderTemplates(templates);
}

function renderQuickCreate() {
  const row = $('#quickRow');
  for (const id of quickPresets) {
    const preset = PAGE_PRESETS.find((item) => item.id === id);
    if (!preset) continue;
    const button = el('button', { class: 'quick-tile', type: 'button', dataset: { preset: id } }, [
      el('span', { class: 'quick-art', dataset: { preset: id } }),
      el('span', { class: 'quick-copy' }, [
        el('strong', { text: preset.label }),
        el('span', { text: `${preset.w} x ${preset.h}` }),
      ]),
      el('span', { class: 'quick-plus' }, svgIcon(ICONS.plus, 16)),
    ]);
    button.addEventListener('click', () => createDesign(id));
    row.append(button);
  }
}

function renderDesigns(designs) {
  if (!designs.length) {
    recentGrid.append(
      el('div', { class: 'empty-state' }, [
        el('span', { class: 'empty-art' }, svgIcon(ICONS.sparkle, 26)),
        el('h3', { text: state.query ? 'No designs match that search' : 'No designs yet' }),
        el('p', { text: state.query ? 'Try a different word, or start something new.' : 'Create a blank canvas and it will show up here.' }),
        el('button', { class: 'btn btn-primary', type: 'button', text: 'Create a design', on: { click: openCreatePicker } }),
      ]),
    );
    return;
  }

  for (const design of designs) {
    const card = el('article', { class: 'design-card' });
    const open = el('button', { class: 'card-open', type: 'button', 'aria-label': `Open ${design.title}` });
    const media = el('span', { class: 'card-media' });
    const canvas = el('canvas', { class: 'design-thumb' });
    media.append(canvas, el('span', { class: 'card-hover', text: 'Open design' }));
    open.append(media);
    open.addEventListener('click', () => {
      location.href = `editor.html?id=${encodeURIComponent(design.id)}`;
    });

    const meta = el('div', { class: 'card-meta' }, [
      el('div', { class: 'card-copy' }, [
        el('h3', { text: design.title }),
        el('p', { text: `${design.w} x ${design.h} - edited ${formatRelative(design.updatedAt)}` }),
      ]),
    ]);

    const more = el('button', { class: 'card-more', type: 'button', 'aria-label': `Options for ${design.title}` }, svgIcon(ICONS.more, 18));
    more.addEventListener('click', (event) => {
      event.stopPropagation();
      openMenu(more, [
        {
          label: 'Open',
          icon: ICONS.play,
          onSelect: () => {
            location.href = `editor.html?id=${encodeURIComponent(design.id)}`;
          },
        },
        {
          label: 'Duplicate',
          icon: ICONS.copy,
          onSelect: () => {
            duplicateDesign(design.id);
            toast('Design duplicated');
            render();
          },
        },
        { separator: true },
        {
          label: 'Delete',
          icon: ICONS.trash,
          danger: true,
          onSelect: () => confirmDelete(design),
        },
      ], { align: 'right' });
    });
    meta.append(more);
    card.append(open, meta);
    recentGrid.append(card);

    paintThumbnail(canvas, design, design.pages[0], 420, 220).catch(() => null);
  }
}

function renderTemplates(templates) {
  if (!templates.length) {
    templateGrid.append(
      el('div', { class: 'empty-state' }, [
        el('span', { class: 'empty-art' }, svgIcon(ICONS.template, 26)),
        el('h3', { text: 'No templates match that search' }),
        el('p', { text: 'Clear the search to see every template.' }),
      ]),
    );
    return;
  }
  for (const template of templates) {
    const card = el('button', { class: 'template-card', type: 'button' });
    const media = el('span', { class: 'tpl-media' });
    const canvas = el('canvas', { class: 'tpl-thumb' });
    media.append(canvas, el('span', { class: 'tpl-hover', text: 'Use template' }));
    card.append(
      media,
      el('span', { class: 'tpl-meta' }, [
        el('strong', { text: template.name }),
        el('span', { text: `${template.category} - ${template.w} x ${template.h}` }),
      ]),
    );
    card.addEventListener('click', () => {
      location.href = `editor.html?template=${encodeURIComponent(template.id)}`;
    });
    templateGrid.append(card);
    const pages = template.buildPages();
    paintThumbnail(canvas, { w: template.w, h: template.h }, pages[0], 420, 240).catch(() => null);
  }
}

function confirmDelete(design) {
  openModal({
    title: `Delete "${design.title}"?`,
    subtitle: 'This removes the design from this browser. It cannot be undone.',
    content: el('p', { class: 'modal-copy', text: 'Download the pages first if you want to keep a copy.' }),
    actions: [
      { label: 'Cancel' },
      {
        label: 'Delete design',
        variant: 'danger',
        onSelect: () => {
          deleteDesign(design.id);
          toast('Design deleted');
          render();
        },
      },
    ],
  });
}

function createDesign(presetId) {
  const design = createNewDesign(presetId, 'Untitled design');
  location.href = `editor.html?id=${encodeURIComponent(design.id)}`;
}

function openCreatePicker() {
  const grid = el('div', { class: 'preset-grid' });
  const modal = openModal({
    title: 'Create a design',
    subtitle: 'Pick a canvas size. You can change it later from the page settings.',
    content: grid,
  });
  for (const preset of PAGE_PRESETS) {
    const button = el('button', { class: 'preset-tile', type: 'button' }, [
      el('span', {
        class: 'preset-shape',
        style: { aspectRatio: `${preset.w} / ${preset.h}` },
      }),
      el('span', { class: 'preset-copy' }, [
        el('strong', { text: preset.label }),
        el('span', { text: `${preset.w} x ${preset.h}` }),
      ]),
    ]);
    button.addEventListener('click', () => {
      modal.close();
      createDesign(preset.id);
    });
    grid.append(button);
  }
}

function wireNav() {
  $('#dashNav').addEventListener('click', (event) => {
    const button = event.target.closest('[data-view]');
    if (!button) return;
    setView(button.dataset.view);
  });
  const seeAll = document.querySelector('.section-head [data-view]');
  seeAll?.addEventListener('click', () => setView(seeAll.dataset.view));
}

function setView(view) {
  state.view = view;
  $$('#dashNav .nav-item').forEach((item) => item.classList.toggle('is-active', item.dataset.view === view));
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function wireSearch() {
  const input = $('#searchInput');
  input.addEventListener('input', debounce(() => {
    state.query = input.value || '';
    render();
  }, 120));
}

function wireCreate() {
  $('#createBtn').addEventListener('click', openCreatePicker);
}

function wireHelp() {
  $('#helpBtn').addEventListener('click', () => {
    openModal({
      title: 'Studio shortcuts',
      subtitle: 'The board is built for keyboard and pointer, no menus required.',
      content: el('dl', { class: 'shortcut-list' }, [
        el('dt', { text: 'Pan the board' }), el('dd', { text: 'Space + drag, or scroll' }),
        el('dt', { text: 'Zoom to cursor' }), el('dd', { text: 'Ctrl / Cmd + scroll' }),
        el('dt', { text: 'Multi-select' }), el('dd', { text: 'Shift + click, or drag a marquee' }),
        el('dt', { text: 'Nudge' }), el('dd', { text: 'Arrow keys, Shift for 10 px' }),
        el('dt', { text: 'Edit text' }), el('dd', { text: 'Double-click a text element' }),
        el('dt', { text: 'Undo / redo' }), el('dd', { text: 'Ctrl / Cmd + Z, add Shift to redo' }),
      ]),
      actions: [{ label: 'Got it', variant: 'primary' }],
    });
  });
}
