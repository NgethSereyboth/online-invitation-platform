/**
 * src/js/editor/chrome/shortcuts.js — Central keyboard-shortcut registry (ROADMAP §3.4.4, v0.57.0).
 *
 * A single `Shortcuts` service that listens on `keydown`, matches against a
 * table of `{key, command, when}`, and dispatches to the command registry.
 *
 * Design goals:
 *   • One source of truth for every keyboard shortcut in the editor.
 *   • `when` clauses prevent shortcuts from firing inside text inputs (so
 *     Ctrl+B inside a textarea bolds the text instead of toggling a sidebar).
 *   • The table is searchable via the Shift+? modal (which opens the unified
 *     command palette in "shortcuts" mode — see command-palette.js).
 *
 * Existing keyboard handling in `editor-command-system-v23.js` is preserved
 * (it is the source of the binding table). This module wraps it with a
 * cleaner API for the chrome layer to consume and adds the `when` clauses.
 *
 * Public API:
 *   EInviteShortcuts.register({ key, command, when })    → add a binding
 *   EInviteShortcuts.unregister(id)                       → remove a binding
 *   EInviteShortcuts.list()                               → all bindings
 *   EInviteShortcuts.match(event)                         → resolve command id
 *   EInviteShortcuts.openShortcutsModal()                 → open the modal
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteShortcuts) return;

  const STRINGS = {
    en: {
      title: 'Keyboard shortcuts', empty: 'No shortcuts registered',
      category: 'Category', all: 'All', filter: 'Filter shortcuts…',
      close: 'Close', command: 'Command', shortcut: 'Shortcut'
    },
    km: {
      title: 'ផ្លូវកាត់ក្ដារចុច', empty: 'មិនមានផ្លូវកាត់ទេ',
      category: 'ប្រភេទ', all: 'ទាំងអស់', filter: 'ត្រង់ផ្លូវកាត់…',
      close: 'បិទ', command: 'ពាក្យបញ្ជា', shortcut: 'ផ្លូវកាត់'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  function registry() { return window.EInviteCommandRegistry || null; }
  function palette() { return window.EInviteChromeCommandPalette || null; }

  /** Canonicalize a chord string the same way the registry does.
   *  'Mod+K' / 'Ctrl+K' / 'Cmd+K' / 'Command+K' → 'Mod+K' (the registry's
   *  `Mod` resolves to Ctrl on Win/Linux, Cmd on macOS). */
  function canonicalChord(value) {
    if (!value) return '';
    const parts = String(value).split('+').map((s) => s.trim()).filter(Boolean);
    const mods = new Set(); let key = '';
    for (const part of parts) {
      const p = part.toLowerCase();
      if (['mod', 'cmdorctrl', 'ctrlorcmd'].includes(p)) mods.add('Mod');
      else if (['ctrl', 'control'].includes(p)) mods.add('Ctrl');
      else if (['meta', 'cmd', 'command'].includes(p)) mods.add('Meta');
      else if (['alt', 'option'].includes(p)) mods.add('Alt');
      else if (p === 'shift') mods.add('Shift');
      else if (part.length === 1) key = part.toUpperCase();
      else key = part;
    }
    return ['Mod', 'Ctrl', 'Meta', 'Alt', 'Shift'].filter((x) => mods.has(x)).concat(key || []).join('+');
  }

  /** Test whether the keydown event is "in a text input" — used for `when`
   *  clauses. `editor-active` matches when the canvas/stage has focus OR no
   *  input has focus; `never` always rejects; `always` always accepts. */
  function isTypingTarget(target) {
    if (!target) return false;
    return !!target.matches && target.matches('input,textarea,select,[contenteditable="true"]');
  }
  function evaluateWhen(when, event) {
    if (!when || when === 'always') return true;
    if (when === 'never') return false;
    if (when === 'editor-active') return !isTypingTarget(event.target);
    if (when === 'text-input') return isTypingTarget(event.target);
    // Custom: pass through.
    return true;
  }

  /** Module state. */
  const state = {
    bindings: new Map(),  // id → {key, command, when, label_en, label_km, category}
    nextId: 1,
    modal: null
  };

  function register(binding) {
    if (!binding || !binding.key || !binding.command) return null;
    const id = `s${state.nextId++}`;
    const record = {
      id,
      key: canonicalChord(binding.key),
      command: String(binding.command),
      when: binding.when || 'editor-active',
      label_en: binding.label_en || binding.command,
      label_km: binding.label_km || binding.label_en || binding.command,
      category: binding.category || 'General'
    };
    state.bindings.set(id, record);
    return id;
  }

  function registerMany(list) {
    if (!Array.isArray(list)) return [];
    return list.map(register);
  }

  function unregister(id) { return state.bindings.delete(id); }

  function list() { return [...state.bindings.values()]; }

  /** Match a keydown event against the table; return the command id (or null). */
  function match(event) {
    const r = registry();
    const eventChord = r?.eventChord ? r.eventChord(event) : eventToChord(event);
    let best = null;
    for (const binding of state.bindings.values()) {
      if (binding.key !== eventChord) continue;
      if (!evaluateWhen(binding.when, event)) continue;
      best = binding.command; break;
    }
    return best;
  }

  function eventToChord(event) {
    const parts = [];
    if (event.ctrlKey || event.metaKey) parts.push('Mod');
    if (event.altKey) parts.push('Alt');
    if (event.shiftKey) parts.push('Shift');
    let key = event.key;
    if (key === ' ') key = 'Space';
    if (key.length === 1) key = key.toUpperCase();
    if (!['Control', 'Meta', 'Alt', 'Shift'].includes(key)) parts.push(key);
    return parts.join('+');
  }

  /** Global keydown listener. */
  function onKeyDown(event) {
    if (event.defaultPrevented) return;
    const commandId = match(event);
    if (!commandId) return;
    const r = registry();
    if (!r?.execute) return;
    // Execute the command. If it returns false (disabled), let the event
    // propagate normally so the browser default action still fires.
    try {
      event.preventDefault();
      r.execute(commandId, { event });
    } catch (e) { console.warn('[shortcuts] failed', e); }
  }

  /** Open the shortcuts modal — delegates to the chrome command palette
   *  which already has a shortcuts mode. Falls back to a built-in modal. */
  function openShortcutsModal() {
    const p = palette();
    if (p?.openShortcuts) return p.openShortcuts();
    buildModal();
    state.modal.hidden = false;
    document.body.classList.add('ei-shortcuts-modal-open');
  }
  function closeShortcutsModal() {
    if (!state.modal) return;
    state.modal.hidden = true;
    document.body.classList.remove('ei-shortcuts-modal-open');
  }

  function buildModal() {
    if (state.modal) return state.modal;
    const modal = document.createElement('div');
    modal.className = 'ei-shortcuts-modal';
    modal.hidden = true;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML = `
      <div class="ei-shortcuts-modal__backdrop" data-close></div>
      <section class="ei-shortcuts-modal__dialog">
        <header><h2>${t('title')}</h2><button type="button" data-close aria-label="${t('close')}">×</button></header>
        <input type="search" class="ei-shortcuts-modal__filter" placeholder="${t('filter')}" aria-label="${t('filter')}">
        <div class="ei-shortcuts-modal__list"></div>
      </section>
    `;
    document.body.appendChild(modal);
    state.modal = modal;
    modal.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', closeShortcutsModal));
    modal.querySelector('input').addEventListener('input', () => renderModalList());
    return modal;
  }

  function renderModalList() {
    if (!state.modal) return;
    const q = state.modal.querySelector('input').value.trim().toLowerCase();
    const list = state.modal.querySelector('.ei-shortcuts-modal__list');
    list.replaceChildren();
    let bindings = list && state.bindings.size ? list : list;
    bindings = [...state.bindings.values()].filter((b) => {
      if (!q) return true;
      const hay = `${b.label_en} ${b.label_km} ${b.command} ${b.key} ${b.category}`.toLowerCase();
      return hay.includes(q);
    });
    if (!bindings.length) {
      const empty = document.createElement('div');
      empty.className = 'ei-shortcuts-modal__empty';
      empty.textContent = t('empty');
      list.appendChild(empty);
      return;
    }
    let lastCat = '';
    for (const b of bindings) {
      if (b.category !== lastCat) {
        lastCat = b.category;
        const h = document.createElement('div');
        h.className = 'ei-shortcuts-modal__category';
        h.textContent = b.category;
        list.appendChild(h);
      }
      const row = document.createElement('div');
      row.className = 'ei-shortcuts-modal__row';
      row.innerHTML = `<span class="ei-shortcuts-modal__label"></span><kbd class="ei-shortcuts-modal__key"></kbd>`;
      row.querySelector('.ei-shortcuts-modal__label').textContent = locale() === 'km' ? b.label_km : b.label_en;
      row.querySelector('kbd').textContent = formatChord(b.key);
      list.appendChild(row);
    }
  }

  function formatChord(chord) {
    return String(chord || '').replace(/Mod/g, navigator.platform.includes('Mac') ? '⌘' : 'Ctrl')
      .replace(/\+/g, ' + ');
  }

  /** Default set of shortcuts to register on load. Each command id is
   *  executed via the registry — these mirror the existing bindings in
   *  editor-command-system-v23.js but are now centralized. */
  const DEFAULT_BINDINGS = [
    { key: 'Mod+K', command: 'palette.open', when: 'always', label_en: 'Open command palette', label_km: 'បើកផ្លូវកាត់សកម្មភាព', category: 'View' },
    { key: 'Shift+?', command: 'palette.shortcuts', when: 'editor-active', label_en: 'Show keyboard shortcuts', label_km: 'បង្ហាញផ្លូវកាត់', category: 'Help' },
    { key: 'Mod+B', command: 'format.bold', when: 'editor-active', label_en: 'Bold (toggle)', label_km: 'ដិត (បិទ/បើក)', category: 'Format' },
    { key: 'Mod+I', command: 'format.italic', when: 'editor-active', label_en: 'Italic (toggle)', label_km: 'ទ្រេត (បិទ/បើក)', category: 'Format' },
    { key: 'Mod+U', command: 'format.underline', when: 'editor-active', label_en: 'Underline (toggle)', label_km: 'បន្ទាត់ពីក្រោម (បិទ/បើក)', category: 'Format' },
    { key: 'Mod+Z', command: 'history.undo', when: 'always', label_en: 'Undo', label_km: 'មិនធ្វើវិញ', category: 'Edit' },
    { key: 'Mod+Shift+Z', command: 'history.redo', when: 'always', label_en: 'Redo', label_km: 'ធ្វើវិញ', category: 'Edit' },
    { key: 'Mod+S', command: 'file.save', when: 'always', label_en: 'Save', label_km: 'រក្សាទុក', category: 'File' },
    { key: 'Mod+D', command: 'edit.duplicate', when: 'editor-active', label_en: 'Duplicate selection', label_km: 'ចម្លងធាតុដែលបានជ្រើស', category: 'Edit' },
    { key: 'Delete', command: 'edit.delete', when: 'editor-active', label_en: 'Delete selection', label_km: 'លុបធាតុដែលបានជ្រើស', category: 'Edit' },
    { key: 'Mod+A', command: 'edit.selectAll', when: 'editor-active', label_en: 'Select all', label_km: 'ជ្រើសទាំងអស់', category: 'Edit' },
    { key: 'Mod+G', command: 'object.group', when: 'editor-active', label_en: 'Group selection', label_km: 'ដាក់ជាក្រុម', category: 'Arrange' },
    { key: 'Mod+Shift+G', command: 'object.ungroup', when: 'editor-active', label_en: 'Ungroup selection', label_km: 'ដកក្រុម', category: 'Arrange' },
    { key: 'Mod+]', command: 'arrange.forward', when: 'editor-active', label_en: 'Bring forward', label_km: 'នាំឡើងលើ', category: 'Arrange' },
    { key: 'Mod+[', command: 'arrange.backward', when: 'editor-active', label_en: 'Send backward', label_km: 'ផ្ញើចុះក្រោម', category: 'Arrange' },
    { key: 'Alt+L', command: 'layers.togglePanel', when: 'editor-active', label_en: 'Toggle layers panel', label_km: 'បិទ/បើកស្រទាប់', category: 'View' },
    { key: 'Alt+P', command: 'pages.toggleSidebar', when: 'editor-active', label_en: 'Toggle pages sidebar', label_km: 'បិទ/បើកទំព័រ', category: 'View' }
  ];

  /** Register a no-op command for each unknown command id so the registry
   *  won't reject the dispatch. This is purely for the modal to be useful
   *  even when the editor bundle hasn't registered all commands. */
  function ensureCommandStubs() {
    const r = registry(); if (!r?.register) return;
    for (const b of DEFAULT_BINDINGS) {
      try {
        if (!r.list) continue;
        const exists = r.list({ includeHidden: true }).some((c) => c.id === b.command);
        if (exists) continue;
        r.register({
          id: b.command, title: b.label_en, category: b.category,
          keywords: [b.label_km, b.key], visible: () => false, run: () => false
        });
      } catch { /* duplicate — ignore */ }
    }
  }

  function init() {
    document.addEventListener('keydown', onKeyDown, true);
    registerMany(DEFAULT_BINDINGS);
    ensureCommandStubs();
  }

  window.EInviteShortcuts = Object.freeze({
    version: 57, STRINGS, register, registerMany, unregister, list,
    match, canonicalChord, openShortcutsModal, closeShortcutsModal
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    queueMicrotask(init);
  }
})();
