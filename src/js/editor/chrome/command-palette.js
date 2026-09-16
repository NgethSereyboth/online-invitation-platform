/**
 * src/js/editor/chrome/command-palette.js — Unified command palette (ROADMAP §3.4.3, v0.57.0).
 *
 * Press Ctrl+K (or Cmd+K on macOS) → a searchable list of every action in
 * the editor. Type to filter; Enter to run. Fuzzy search (fzf-style scorer)
 * ranks matches by tightness and recency.
 *
 * The palette aggregates three sources:
 *   • `window.EInviteCommandRegistry.list()` — every registered command
 *     (toolbar actions, inspector actions, menu items, keyboard shortcuts).
 *   • Pages — quick-jump to any design page.
 *   • Layers — quick-select any layer on the active canvas.
 *
 * Display grouped by category: File, Edit, View, Insert, Format, Arrange,
 * Align, Help. Recently used commands appear at the top (capped at 8).
 *
 * Bilingual EN+KH labels — every command carries `label_en` + `label_km`.
 *
 * Public API:
 *   EInviteChromeCommandPalette.open()         → opens in command mode
 *   EInviteChromeCommandPalette.openShortcuts() → opens in shortcuts mode
 *   EInviteChromeCommandPalette.close()         → closes
 *   EInviteChromeCommandPalette.toggle()        → open/close
 *
 * The existing `command-palette-v23.js` surface (EInviteCommandUI) is left
 * in place for backwards compatibility; this module wraps + extends it
 * with the fuzzy scorer + bilingual labels + layer/page aggregations.
 */
(() => {
  'use strict';
  if (window.EInviteChromeCommandPalette) return;

  const RECENT_KEY = 'ei-command-palette-recent-v57';
  const RECENT_MAX = 8;

  const STRINGS = {
    en: {
      title: 'Quick Actions',
      placeholder: 'Search actions, pages, layers…',
      empty: 'No matching commands',
      recent: 'Recently used',
      shortcuts: 'Keyboard shortcuts',
      runLabel: 'Run',
      closeLabel: 'Close',
      navigating: '↑↓ Navigate · Enter Run · Esc Close',
      noShortcuts: 'No shortcuts registered'
    },
    km: {
      title: 'សកម្មភាពរហ័ស',
      placeholder: 'ស្វែងរកសកម្មភាព ទំព័រ ស្រទាប់…',
      empty: 'មិនមានសកម្មភាពត្រូវគ្នាទេ',
      recent: 'បានប្រើថ្មីៗ',
      shortcuts: 'ផ្លូវកាត់ក្ដារចុច',
      runLabel: 'ដំណើរការ',
      closeLabel: 'បិទ',
      navigating: '↑↓ រុករក · Enter ដំណើរការ · Esc បិទ',
      noShortcuts: 'មិនមានផ្លូវកាត់ទេ'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function registry() { return window.EInviteCommandRegistry || null; }
  function bridge() { return window.EInviteEditorBridge || null; }

  /** fzf-style fuzzy scorer. Returns -1 if no match, else a non-negative
   *  score (higher = better). Bonus for consecutive matches + start-of-word. */
  function fuzzyScore(query, text) {
    if (!query) return 0;
    const q = String(query).toLowerCase();
    const s = String(text || '').toLowerCase();
    if (!q) return 0;
    if (s.includes(q)) {
      // Tight substring match → high score.
      const tightness = q.length / s.length;
      const startBonus = s.startsWith(q) ? 100 : 0;
      return 50 + Math.floor(tightness * 100) + startBonus;
    }
    // Fuzzy: every char of q must appear in s, in order.
    let qi = 0, lastIdx = -1, score = 0, run = 0;
    for (let si = 0; si < s.length && qi < q.length; si++) {
      if (s[si] === q[qi]) {
        if (lastIdx === si - 1) run++; else run = 0;
        score += 10 + run * 5 + (si === 0 ? 5 : 0);
        lastIdx = si; qi++;
      }
    }
    return qi === q.length ? score : -1;
  }

  /** Load recently-used command ids from localStorage. */
  function loadRecent() {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); }
    catch { return []; }
  }
  function saveRecent(ids) {
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(ids.slice(0, RECENT_MAX))); }
    catch { /* storage disabled — silent */ }
  }
  function pushRecent(id) {
    if (!id) return;
    const ids = loadRecent().filter((x) => x !== id);
    ids.unshift(id);
    saveRecent(ids);
  }

  /** Collect every registered command, decorated with bilingual labels. */
  function collectCommands() {
    const r = registry(); if (!r) return [];
    const list = r.list ? r.list({ includeHidden: false }) : [];
    return list.map((c) => ({
      id: c.id,
      label_en: c.title || c.label_en || c.id,
      label_km: c.label_km || c.title || c.id,
      category: c.category || 'General',
      keywords: c.keywords || [],
      icon: c.icon || '·',
      shortcuts: (c.shortcuts || []).map((s) => r.formatChord ? r.formatChord(s) : s),
      run: () => r.execute ? r.execute(c.id) : c.run?.()
    }));
  }

  function collectPages() {
    const b = bridge(); if (!b) return [];
    const doc = b.getState?.() || {};
    const pages = doc.designPages || [];
    return [
      { id: 'page:hero', label_en: 'Main hero', label_km: 'ទំព័រមេ', category: 'Pages', icon: '▣',
        keywords: ['page', 'hero', 'main'], run: () => activateCanvas('hero') },
      ...pages.map((p, idx) => ({
        id: `page:${p.id}`, label_en: p.name || `Page ${idx + 1}`,
        label_km: p.name || `ទំព័រ ${idx + 1}`, category: 'Pages', icon: '▤',
        keywords: ['page', p.name, p.id], run: () => activateCanvas(`page:${p.id}`)
      }))
    ];
  }

  function collectLayers() {
    const b = bridge(); if (!b) return [];
    const doc = b.getState?.() || {};
    const canvasId = b.getActiveCanvasId?.() || 'hero';
    let map = doc.objects || {};
    if (canvasId !== 'hero') {
      const id = String(canvasId).replace(/^page:/, '');
      const page = (doc.designPages || []).find((p) => p.id === id);
      map = page?.objects || {};
    }
    return Object.entries(map).map(([id, obj], idx) => ({
      id: `layer:${id}`, label_en: obj.layerName || `${obj.type || 'Element'} ${idx + 1}`,
      label_km: obj.layerName || `${obj.type || 'ធាតុ'} ${idx + 1}`,
      category: 'Layers', icon: '◇',
      keywords: ['layer', id, obj.type, obj.layerName],
      run: () => b.select?.([id])
    }));
  }

  function activateCanvas(token) {
    if (window.switchCanvas) return window.switchCanvas(token);
    const b = bridge();
    if (typeof b.setActiveCanvasId === 'function') b.setActiveCanvasId(token);
  }

  /** Aggregate all sources into one list, ranked by fuzzy score. */
  function search(query) {
    const all = [...collectCommands(), ...collectPages(), ...collectLayers()];
    if (!query) {
      // No query → recently used first, then commands in category order.
      const recent = loadRecent();
      const recentItems = recent
        .map((id) => all.find((x) => x.id === id))
        .filter(Boolean);
      return [...recentItems, ...all.filter((x) => !recent.includes(x.id))].slice(0, 80);
    }
    const scored = all.map((item) => {
      const label = locale() === 'km' ? item.label_km : item.label_en;
      const hay = `${label} ${item.category} ${(item.keywords || []).join(' ')} ${(item.shortcuts || []).join(' ')}`;
      const score = Math.max(
        fuzzyScore(query, label),
        fuzzyScore(query, item.label_en) - 1,
        fuzzyScore(query, item.label_km) - 1,
        fuzzyScore(query, hay) - 2
      );
      return { item, score };
    }).filter((x) => x.score >= 0)
      .sort((a, b) => b.score - a.score)
      .map((x) => x.item);
    return scored.slice(0, 60);
  }

  /** Module state. */
  const state = {
    root: null,
    inputEl: null,
    listEl: null,
    hintEl: null,
    active: 0,
    items: [],
    mode: 'commands'  // 'commands' | 'shortcuts'
  };

  function build() {
    if (state.root) return state.root;
    const root = document.createElement('div');
    root.className = 'ei-command-palette';
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'eiPaletteTitle');
    root.innerHTML = `
      <div class="ei-command-palette__backdrop" data-close></div>
      <section class="ei-command-palette__dialog">
        <header>
          <div><small>EInvite Studio</small><h2 id="eiPaletteTitle">${t('title')}</h2></div>
          <button type="button" data-close aria-label="${t('closeLabel')}">×</button>
        </header>
        <div class="ei-command-palette__search">
          <span aria-hidden="true">⌕</span>
          <input type="search" autocomplete="off" placeholder="${t('placeholder')}" aria-label="${t('placeholder')}">
          <kbd>Esc</kbd>
        </div>
        <div class="ei-command-palette__list" role="listbox" aria-label="${t('title')}"></div>
        <footer>${t('navigating')}</footer>
      </section>
    `;
    document.body.appendChild(root);
    state.root = root;
    state.inputEl = $('input', root);
    state.listEl = $('.ei-command-palette__list', root);
    state.hintEl = $('footer kbd', root);
    $$('[data-close]', root).forEach((b) => b.addEventListener('click', close));
    state.inputEl.addEventListener('input', () => { state.active = 0; render(); });
    root.addEventListener('keydown', onKey);
    return root;
  }

  function open(mode = 'commands') {
    build();
    state.mode = mode;
    state.root.hidden = false;
    document.body.classList.add('ei-command-palette-open');
    state.inputEl.value = '';
    state.active = 0;
    render();
    setTimeout(() => state.inputEl.focus(), 0);
  }

  function close() {
    if (!state.root || state.root.hidden) return;
    state.root.hidden = true;
    document.body.classList.remove('ei-command-palette-open');
  }

  function toggle() {
    if (!state.root || state.root.hidden) open(); else close();
  }

  function openShortcuts() { open('shortcuts'); }

  function onKey(event) {
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'ArrowDown') { event.preventDefault(); state.active = Math.min(state.items.length - 1, state.active + 1); syncActive(); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); state.active = Math.max(0, state.active - 1); syncActive(); }
    else if (event.key === 'Enter') {
      event.preventDefault();
      const item = state.items[state.active];
      if (item) run(item);
    }
  }

  function run(item) {
    pushRecent(item.id);
    close();
    try { Promise.resolve(item.run?.()).catch((e) => window.uiToast?.(e?.message || 'Action failed', '!')); }
    catch (e) { window.uiToast?.(e?.message || 'Action failed', '!'); }
  }

  function render() {
    if (state.mode === 'shortcuts') return renderShortcuts();
    const q = state.inputEl.value.trim();
    state.items = search(q);
    state.active = Math.max(0, Math.min(state.active, Math.max(0, state.items.length - 1)));
    state.listEl.replaceChildren();
    if (!state.items.length) {
      const empty = document.createElement('div');
      empty.className = 'ei-command-palette__empty';
      empty.textContent = t('empty');
      state.listEl.appendChild(empty);
      return;
    }
    let lastCategory = '';
    const recentIds = new Set(loadRecent());
    let recentHeaderShown = q.length === 0;
    if (recentHeaderShown) {
      const h = document.createElement('div');
      h.className = 'ei-command-palette__category';
      h.textContent = t('recent');
      state.listEl.appendChild(h);
    }
    state.items.forEach((item, idx) => {
      if (!recentHeaderShown && item.category !== lastCategory) {
        lastCategory = item.category;
        const h = document.createElement('div');
        h.className = 'ei-command-palette__category';
        h.textContent = item.category;
        state.listEl.appendChild(h);
      }
      const row = document.createElement('button');
      row.type = 'button';
      row.className = `ei-command-palette__row${idx === state.active ? ' is-active' : ''}`;
      row.dataset.idx = String(idx);
      const label = locale() === 'km' ? item.label_km : item.label_en;
      row.innerHTML = `<span class="ei-command-palette__icon" aria-hidden="true">${item.icon || '·'}</span>
        <span class="ei-command-palette__label"></span>
        <kbd class="ei-command-palette__shortcut"></kbd>`;
      $('.ei-command-palette__label', row).textContent = label;
      $('.ei-command-palette__shortcut', row).textContent = (item.shortcuts || []).slice(0, 2).join(' ');
      row.addEventListener('mouseenter', () => { state.active = idx; syncActive(); });
      row.addEventListener('click', () => run(item));
      state.listEl.appendChild(row);
    });
  }

  function renderShortcuts() {
    const r = registry(); if (!r) return;
    const list = r.list ? r.list({ includeHidden: true }) : [];
    state.listEl.replaceChildren();
    if (!list.length) {
      const empty = document.createElement('div');
      empty.className = 'ei-command-palette__empty';
      empty.textContent = t('noShortcuts');
      state.listEl.appendChild(empty);
      return;
    }
    let lastCat = '';
    list.forEach((c) => {
      if (c.category !== lastCat) {
        lastCat = c.category;
        const h = document.createElement('div');
        h.className = 'ei-command-palette__category';
        h.textContent = c.category;
        state.listEl.appendChild(h);
      }
      const row = document.createElement('div');
      row.className = 'ei-command-palette__shortcut-row';
      const shortcut = (c.shortcuts || []).map((s) => r.formatChord ? r.formatChord(s) : s).join(' · ') || '—';
      row.innerHTML = `<span class="ei-command-palette__label"></span><kbd></kbd>`;
      $('.ei-command-palette__label', row).textContent = c.title;
      $('kbd', row).textContent = shortcut;
      state.listEl.appendChild(row);
    });
  }

  function syncActive() {
    $$('.ei-command-palette__row', state.root).forEach((row, idx) => {
      row.classList.toggle('is-active', idx === state.active);
    });
    const activeRow = $$('.ei-command-palette__row', state.root)[state.active];
    activeRow?.scrollIntoView({ block: 'nearest' });
  }

  /** Register commands + keyboard shortcuts. */
  function register() {
    const r = registry(); if (!r) return;
    try {
      r.register({
        id: 'palette.open', title: 'Open command palette',
        category: 'View', keywords: ['quick', 'actions', 'search', 'palette'],
        bindings: { standard: ['Mod+K'], canva: ['Mod+K'], photoshop: ['Mod+K'] },
        allowWhileTyping: false,
        run: () => open('commands')
      });
      r.register({
        id: 'palette.shortcuts', title: 'Show keyboard shortcuts',
        category: 'Help', keywords: ['shortcuts', 'help', 'keyboard'],
        bindings: { standard: ['Shift+?'], canva: ['Shift+?'], photoshop: ['Shift+?'] },
        run: () => openShortcuts()
      });
    } catch { /* duplicate — ignore */ }
    // Wire the global keydown for Ctrl+K / Cmd+K / Shift+? as a fallback in
    // case the registry isn't initialized early enough.
    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && (event.key === 'k' || event.key === 'K')) {
        event.preventDefault();
        toggle();
      } else if (event.shiftKey && (event.key === '?' || event.key === '/')) {
        if (isTypingTarget(event.target)) return;
        event.preventDefault();
        openShortcuts();
      }
    });
  }

  function isTypingTarget(target) {
    if (!target) return false;
    return !!target.matches && target.matches('input,textarea,select,[contenteditable="true"]');
  }

  window.EInviteChromeCommandPalette = Object.freeze({
    version: 57, STRINGS, open, openShortcuts, close, toggle, register,
    search, collectCommands, collectPages, collectLayers
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', register);
  } else {
    queueMicrotask(register);
  }
})();
