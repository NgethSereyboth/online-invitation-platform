/*
 * Khmer events gallery (TP-1.4).
 *
 * Renders the 36 template-pack designs as a dedicated section above the Template
 * Studio grid. The catalogue and every document stay out of all bundles: this
 * module loads on demand, then the loader fetches what the visitor opens.
 *
 * A card click hands the chosen built document to the studio through a custom
 * event, so the existing "create an invitation from a document" flow stays in one
 * place (src/js/templates.js).
 */
(() => {
  'use strict';
  if (window.EInvitePackGallery) return;
  const SECTION_ID = 'templatePackGallery';
  const LOADER_SRC = 'template-pack-loader.js';
  const STYLE_HREF = 'template-pack-gallery.css';
  const CATEGORY_ORDER = ['wedding', 'birthday', 'ceremony', 'greeting', 'business'];
  const state = { catalog: null, category: 'all', query: '' };

  const esc = (value) =>
    String(value == null ? '' : value).replace(/[&<>"']/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[character]));
  const isKm = () => (window.EInviteI18n && window.EInviteI18n.get
    ? window.EInviteI18n.get()
    : document.documentElement.lang || '').toLowerCase().startsWith('km');
  const text = (en, km) => (isKm() && km ? km : en);

  function ensureStyles() {
    if (document.querySelector('link[data-pack-gallery]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = STYLE_HREF;
    link.dataset.packGallery = '1';
    document.head.append(link);
  }

  function ensureLoader() {
    if (window.EInviteTemplatePack) return Promise.resolve(window.EInviteTemplatePack);
    return new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-pack-loader]');
      if (existing) {
        existing.addEventListener('load', () => resolve(window.EInviteTemplatePack));
        existing.addEventListener('error', () => reject(new Error('loader failed')));
        return;
      }
      const script = document.createElement('script');
      script.src = LOADER_SRC;
      script.dataset.packLoader = '1';
      script.onload = () => resolve(window.EInviteTemplatePack);
      script.onerror = () => reject(new Error('loader failed'));
      document.head.append(script);
    });
  }

  function matches(entry) {
    if (state.category !== 'all' && entry.category !== state.category) return false;
    if (!state.query) return true;
    const haystack = [entry.name.en, entry.name.km, entry.categoryLabel, entry.canvasLabel]
      .concat(entry.tags || []).join(' ').toLowerCase();
    return haystack.includes(state.query);
  }

  function card(entry) {
    const name = text(entry.name.en, entry.name.km);
    const other = text(entry.name.km, entry.name.en);
    const pages = entry.pages === 1
      ? text('1 page', '1 page')
      : text(`${entry.pages} pages`, `${entry.pages} pages`);
    const label = text(
      `Use ${entry.name.en} — ${entry.canvasLabel}, ${pages}`,
      `Use ${entry.name.km} — ${entry.canvasLabel}, ${pages}`,
    );
    return `<article class="pack-card" role="listitem">
      <button type="button" class="pack-card-open" data-pack-template="${esc(entry.id)}" aria-label="${esc(label)}">
        <img src="${esc(entry.thumb)}" width="${Number(entry.thumbWidth) || 420}" height="${Number(entry.thumbHeight) || 420}"
             loading="lazy" decoding="async" alt="">
        <span class="pack-name">
          <span class="pack-name-primary" lang="${isKm() ? 'km' : 'en'}">${esc(name)}</span>
          <span class="pack-name-secondary" lang="${isKm() ? 'en' : 'km'}" aria-hidden="true">${esc(other)}</span>
        </span>
        <span class="pack-meta">${esc(entry.canvasLabel)} · ${esc(pages)}</span>
      </button>
    </article>`;
  }

  function render(host) {
    const catalog = state.catalog;
    if (!catalog) return;
    const grid = host.querySelector('[data-pack-grid]');
    const count = host.querySelector('[data-pack-count]');
    const visible = catalog.templates.filter(matches);
    grid.innerHTML = visible.map(card).join('');
    if (count) {
      count.textContent = text(
        `${visible.length} of ${catalog.count} designs`,
        `${visible.length} of ${catalog.count} designs`,
      );
    }
    host.querySelector('[data-pack-empty]').hidden = visible.length > 0;
    host.querySelectorAll('[data-pack-filter]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.packFilter === state.category));
    });
  }

  function buildSection() {
    const section = document.createElement('section');
    section.id = SECTION_ID;
    section.className = 'pack-gallery';
    section.setAttribute('aria-labelledby', 'packGalleryTitle');
    const filters = [['all', text('All', 'All')]]
      .concat(CATEGORY_ORDER.map((key) => [key, key === 'ceremony' ? 'Ceremony' : key === 'greeting' ? 'Greetings' : key.charAt(0).toUpperCase() + key.slice(1)]))
      .map(([key, label]) => `<button type="button" class="pack-filter" data-pack-filter="${key}" aria-pressed="${key === 'all'}">${esc(label)}</button>`)
      .join('');
    section.innerHTML = `<header class="pack-head">
        <div>
          <h2 id="packGalleryTitle">${esc(text('Khmer events', 'Khmer events'))}</h2>
          <p class="pack-hint">${esc(text(
            'Thirty-six ready-made designs for Khmer weddings, birthdays, ceremonies, greetings and business events. Pick one to start an invitation you can edit.',
            'Thirty-six ready-made designs for Khmer weddings, birthdays, ceremonies, greetings and business events. Pick one to start an invitation you can edit.',
          ))}</p>
        </div>
        <span class="pack-count" data-pack-count aria-live="polite"></span>
      </header>
      <div class="pack-toolbar">
        <label class="sr-only" for="packSearch">${esc(text('Search Khmer event designs', 'Search Khmer event designs'))}</label>
        <input id="packSearch" type="search" data-pack-search
               placeholder="${esc(text('Search these designs…', 'Search these designs…'))}"
               autocomplete="off">
        <div class="pack-filters" role="group" aria-label="${esc(text('Filter by event', 'Filter by event'))}">${filters}</div>
      </div>
      <p class="pack-status" data-pack-status role="status"></p>
      <div class="pack-grid" data-pack-grid role="list"></div>
      <p class="pack-empty" data-pack-empty hidden>${esc(text('No designs match this filter.', 'No designs match this filter.'))}</p>`;
    return section;
  }

  async function mount() {
    const studio = document.querySelector('#studioGrid');
    if (!studio || document.querySelector(`#${SECTION_ID}`)) return null;
    ensureStyles();
    const section = buildSection();
    studio.before(section);
    const status = section.querySelector('[data-pack-status]');
    try {
      const pack = await ensureLoader();
      state.catalog = await pack.loadCatalog();
      render(section);
      status.textContent = '';
    } catch (error) {
      status.textContent = window.EInviteTemplatePack
        ? window.EInviteTemplatePack.catalogErrorText
        : 'Could not load the template list. Try again.';
      return section;
    }
    section.addEventListener('click', async (event) => {
      const filter = event.target.closest('[data-pack-filter]');
      if (filter) {
        state.category = filter.dataset.packFilter || 'all';
        render(section);
        return;
      }
      const open = event.target.closest('[data-pack-template]');
      if (!open) return;
      const id = open.dataset.packTemplate;
      open.setAttribute('aria-busy', 'true');
      try {
        const loaded = await window.EInviteTemplatePack.loadTemplate(id);
        window.dispatchEvent(new CustomEvent('einvite:pack-template', { detail: { id, built: loaded } }));
      } catch (error) {
        status.textContent = (window.EInviteTemplatePack && window.EInviteTemplatePack.errorText)
          || 'Could not load this template. Try again.';
      } finally {
        open.removeAttribute('aria-busy');
      }
    });
    section.addEventListener('input', (event) => {
      if (!event.target.matches('[data-pack-search]')) return;
      state.query = event.target.value.trim().toLowerCase();
      render(section);
    });
    if (window.EInviteI18n && typeof window.EInviteI18n.subscribe === 'function') {
      window.EInviteI18n.subscribe(() => render(section));
    }
    return section;
  }

  window.EInvitePackGallery = Object.freeze({ mount, get state() { return { ...state }; } });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
