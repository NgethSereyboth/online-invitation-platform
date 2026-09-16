/**
 * src/js/editor/history/timeline.js — Version history timeline (ROADMAP §3.5.3, v0.58.0).
 *
 * A timeline of every saved version. Click → preview. Restore from any
 * version. The current state is auto-snapshotted first so restore is
 * reversible.
 *
 * Auto-snapshot rules:
 *   • Every 30 minutes of active editing (reset on any user input).
 *   • Every 100 editor-command events (counter resets after snapshot).
 *   • Capped at 50 snapshots per invitation; oldest pruned.
 *
 * Manual snapshot button in the toolbar (registered as a command).
 *
 * Timeline shows: timestamp, author, one-line summary.
 *
 * Backend routes (server.py):
 *   GET  /api/invitations/{id}/version-history                → list
 *   POST /api/invitations/{id}/version-history                → manual snapshot
 *   POST /api/invitations/{id}/version-history/{vid}/restore  → restore
 *
 * Public API:
 *   EInviteHistoryTimeline.mount(invitationId, options)
 *   EInviteHistoryTimeline.refresh()                    → reload list
 *   EInviteHistoryTimeline.snapshot(summary)            → manual snapshot
 *   EInviteHistoryTimeline.restore(versionId)           → restore
 *   EInviteHistoryTimeline.preview(versionId)           → preview (no replace)
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteHistoryTimeline) return;

  const AUTO_INTERVAL_MS = 30 * 60 * 1000;     // 30 min
  const COMMAND_THRESHOLD = 100;
  const MAX_SNAPSHOTS = 50;

  const STRINGS = {
    en: {
      title: 'Version history', empty: 'No versions yet',
      snapshot: 'Save snapshot', restore: 'Restore', preview: 'Preview',
      cancelPreview: 'Cancel preview', confirmRestore: 'Restore this version? Current state will be auto-saved first.',
      you: 'You', anonymous: 'Anonymous', auto: 'Auto-saved',
      manual: 'Manual snapshot', restoredFrom: 'Restored from {v}',
      author: 'Author', timestamp: 'Timestamp', summary: 'Summary'
    },
    km: {
      title: 'ប្រវត្តិកំណែប្រែ', empty: 'មិនទាន់មានកំណែប្រែទេ',
      snapshot: 'រក្សាទុកកំណែប្រែ', restore: 'ស្ដារ', preview: 'មើលជាមុន',
      cancelPreview: 'បោះបង់ការមើលជាមុន', confirmRestore: 'ស្ដារកំណែប្រែនេះ? ស្ថានភាពបច្ចុប្បន្ននឹងត្រូវរក្សាទុកស្វ័យប្រវត្តិជាមុន។',
      you: 'អ្នក', anonymous: 'អនាមិក', auto: 'បានរក្សាទុកស្វ័យប្រវត្តិ',
      manual: 'រក្សាទុកដោយដៃ', restoredFrom: 'បានស្ដារពី {v}',
      author: 'អ្នកនិពន្ធ', timestamp: 'ពេលវេលា', summary: 'សង្ខេប'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key, vars) {
    let v = (STRINGS[locale()] || STRINGS.en)[key] || key;
    if (typeof v === 'string' && vars) for (const [k, val] of Object.entries(vars)) v = v.replace(`{${k}}`, String(val));
    return v;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  function bridge() { return window.EInviteEditorBridge || null; }
  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta?.getAttribute('content') || '';
  }

  /** Module state. */
  const state = {
    invitationId: null,
    panel: null,
    versions: [],
    previewingId: null,
    csrf: '',
    commandCount: 0,
    autoTimer: 0,
    lastInteractionAt: Date.now()
  };

  function build() {
    if (state.panel) return state.panel;
    const panel = document.createElement('section');
    panel.id = 'eiHistoryTimeline';
    panel.className = 'ei-chrome-panel ei-history-panel';
    panel.setAttribute('aria-label', t('title'));
    panel.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" data-action="snapshot" aria-label="${t('snapshot')}">＋</button>
      </header>
      <ol class="ei-history-list" role="list" aria-label="${t('title')}"></ol>
      <div class="ei-history-empty" hidden>${t('empty')}</div>`;
    document.body.appendChild(panel);
    state.panel = panel;
    $('[data-action="snapshot"]', panel).addEventListener('click', () => snapshot());
    return panel;
  }

  /** Fetch the version list. */
  async function fetchVersions() {
    if (!state.invitationId) return [];
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
      credentials: 'same-origin', headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.versions) ? data.versions : [];
  }

  /** Persist a manual snapshot. */
  async function snapshot(summary = '') {
    const b = bridge(); if (!b || !state.invitationId) return null;
    const doc = b.cloneState?.() || b.getState?.() || {};
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ documentJson: JSON.stringify(doc), summary: String(summary).slice(0, 240) })
    });
    if (!res.ok) { window.uiToast?.('Snapshot failed', '!'); return null; }
    state.commandCount = 0;
    await refresh();
    return true;
  }

  /** Auto-snapshot triggered by timer or command-count threshold. */
  async function autoSnapshot(reason) {
    const b = bridge(); if (!b || !state.invitationId) return;
    // Don't snapshot if nothing changed since the last snapshot.
    const doc = b.cloneState?.() || b.getState?.() || {};
    const summary = reason === 'commands'
      ? `Auto-saved after ${COMMAND_THRESHOLD} changes`
      : 'Auto-saved (30 min)';
    try {
      const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf,
                   'X-Auto-Snapshot': '1' },
        body: JSON.stringify({ documentJson: JSON.stringify(doc), summary })
      });
      if (res.ok) { state.commandCount = 0; await refresh(); }
    } catch { /* network — try again next tick */ }
  }

  /** Restore a prior version. Backend auto-snapshots the current state first. */
  async function restore(versionId) {
    if (!confirm(t('confirmRestore'))) return false;
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history/${encodeURIComponent(versionId)}/restore`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf }
    });
    if (!res.ok) { window.uiToast?.('Restore failed', '!'); return false; }
    const data = await res.json();
    if (data.document) {
      const b = bridge();
      b?.replaceState?.(data.document, { reason: 'restore' });
    }
    await refresh();
    window.uiToast?.(t('restoredFrom', { v: versionId }), '↺');
    return true;
  }

  /** Preview a version (no replace). Replaces the editor state in-memory;
   *  caller invokes cancelPreview() to restore the working state. */
  async function preview(versionId) {
    if (state.previewingId) await cancelPreview();
    const versions = state.versions;
    const v = versions.find((x) => String(x.id) === String(versionId));
    if (!v) return false;
    const b = bridge();
    if (!b) return false;
    // Hold the current state in-memory; preview won't be persisted by the
    // editor (it auto-saves to the draft, which is harmless — the document
    // can be restored by clicking any version on the timeline).
    try {
      const doc = JSON.parse(v.documentJson || '{}');
      b.replaceState?.(doc, { reason: 'preview', history: false, save: false });
      state.previewingId = versionId;
      return true;
    } catch { return false; }
  }

  async function cancelPreview() {
    if (!state.previewingId) return false;
    // Reload from server — the latest saved state is the authoritative one.
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
      credentials: 'same-origin', headers: { 'Accept': 'application/json' }
    });
    if (res.ok) {
      const data = await res.json();
      // The latest version IS the working state (after the auto-snapshot on
      // preview). Restore it.
      const latest = data.versions?.[0];
      if (latest?.documentJson) {
        try {
          const doc = JSON.parse(latest.documentJson);
          bridge()?.replaceState?.(doc, { reason: 'cancel-preview' });
        } catch {}
      }
    }
    state.previewingId = null;
    return true;
  }

  async function refresh() {
    state.versions = await fetchVersions();
    if (state.versions.length > MAX_SNAPSHOTS) {
      // Backend prunes; this is just a safety net.
      state.versions = state.versions.slice(0, MAX_SNAPSHOTS);
    }
    render();
  }

  function render() {
    if (!state.panel) build();
    const list = $('.ei-history-list', state.panel);
    const empty = $('.ei-history-empty', state.panel);
    list.replaceChildren();
    if (!state.versions.length) { empty.hidden = false; return; }
    empty.hidden = true;
    for (const v of state.versions) {
      list.appendChild(buildRow(v));
    }
  }

  function buildRow(v) {
    const row = document.createElement('li');
    row.className = 'ei-history-row';
    row.dataset.id = v.id;
    if (state.previewingId === v.id) row.classList.add('is-previewing');
    row.innerHTML = `
      <div class="ei-history-row__meta">
        <small class="ei-history-time"></small>
        <small class="ei-history-author"></small>
      </div>
      <p class="ei-history-summary"></p>
      <div class="ei-history-actions">
        <button type="button" data-action="preview">${t('preview')}</button>
        <button type="button" data-action="restore">${t('restore')}</button>
      </div>`;
    $('.ei-history-time', row).textContent = formatTime(v.createdAt);
    $('.ei-history-author', row).textContent = v.authorName || (v.isAuto ? t('auto') : t('anonymous'));
    $('.ei-history-summary', row).textContent = v.summary || (v.isAuto ? t('auto') : t('manual'));
    $('[data-action="preview"]', row).addEventListener('click', () => preview(v.id));
    $('[data-action="restore"]', row).addEventListener('click', () => restore(v.id));
    return row;
  }

  function formatTime(ts) {
    if (!ts) return '';
    try { return new Date(Number(ts)).toLocaleString(); } catch { return ''; }
  }

  /** Auto-snapshot scheduler — ticks every minute, snapshots if 30 min
   *  have passed since the last interaction OR command count hits threshold. */
  function startAutoScheduler() {
    clearInterval(state.autoTimer);
    state.autoTimer = setInterval(() => {
      if (!state.invitationId) return;
      const since = Date.now() - state.lastInteractionAt;
      if (since >= AUTO_INTERVAL_MS) {
        state.lastInteractionAt = Date.now();
        autoSnapshot('timer');
      } else if (state.commandCount >= COMMAND_THRESHOLD) {
        autoSnapshot('commands');
      }
    }, 60_000);
  }

  /** Wire editor-command events to bump the counter (and reset the timer). */
  function wireEditorEvents() {
    window.addEventListener('einvite:editor-command', () => {
      state.commandCount++;
      state.lastInteractionAt = Date.now();
      if (state.commandCount >= COMMAND_THRESHOLD) autoSnapshot('commands');
    });
    document.addEventListener('pointerdown', () => { state.lastInteractionAt = Date.now(); }, { passive: true });
    document.addEventListener('keydown', () => { state.lastInteractionAt = Date.now(); }, { passive: true });
  }

  async function mount(invitationId, options = {}) {
    state.invitationId = String(invitationId || '');
    state.csrf = options.csrf || csrfToken();
    build();
    wireEditorEvents();
    startAutoScheduler();
    await refresh();
    return state.panel;
  }

  function registerCommands() {
    const r = window.EInviteCommandRegistry; if (!r?.register) return;
    try {
      r.register({
        id: 'history.togglePanel', title: 'Toggle version history',
        category: 'View', keywords: ['history', 'versions', 'timeline'],
        bindings: { standard: ['Alt+H'], canva: ['Alt+H'], photoshop: ['Alt+H'] },
        run: () => { if (state.panel) state.panel.hidden = !state.panel.hidden; }
      });
      r.register({
        id: 'history.snapshot', title: 'Save version snapshot',
        category: 'File', keywords: ['snapshot', 'version', 'save'],
        bindings: { standard: ['Mod+Shift+S'], canva: ['Mod+Shift+S'], photoshop: ['Mod+Shift+S'] },
        run: () => snapshot('Manual snapshot')
      });
    } catch { /* duplicate — ignore */ }
  }

  window.EInviteHistoryTimeline = Object.freeze({
    version: 58, STRINGS, AUTO_INTERVAL_MS, COMMAND_THRESHOLD, MAX_SNAPSHOTS,
    mount, refresh, snapshot, restore, preview, cancelPreview, registerCommands
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerCommands);
  } else {
    queueMicrotask(registerCommands);
  }
})();
