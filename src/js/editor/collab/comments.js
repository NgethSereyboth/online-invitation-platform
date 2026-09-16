/**
 * src/js/editor/collab/comments.js — Comment threads (ROADMAP §3.5.2, v0.58.0).
 *
 * Click the comment tool, click on the canvas → a pin appears at that
 * coordinate. Type a comment. Other users see the pin and can reply.
 * Resolved threads are hidden by default (toggle to show).
 *
 * @ mentions trigger a notification email via the backend
 * (`send_platform_email`) — the JS scans the comment body for `@name`
 * tokens and the backend re-validates + sends.
 *
 * Public API:
 *   EInviteCollabComments.mount(invitationId, options)
 *   EInviteCollabComments.refresh()                       → reload from server
 *   EInviteCollabComments.activateTool()                  → enter comment tool
 *   EInviteCollabComments.openThread(commentId)           → open thread panel
 *   EInviteCollabComments.create({ x, y, pageId, body })
 *   EInviteCollabComments.reply(commentId, body)
 *   EInviteCollabComments.resolve(commentId)
 *   EInviteCollabComments.toggleResolved()
 *
 * Backend routes (server.py):
 *   GET    /api/invitations/{id}/comments      → list threads
 *   POST   /api/invitations/{id}/comments      → create root comment
 *   PUT    /api/invitations/{id}/comments/{cid} → resolve/unresolve
 *   DELETE /api/invitations/{id}/comments/{cid} → delete
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteCollabComments) return;

  const STRINGS = {
    en: {
      title: 'Comments', empty: 'No comments yet',
      addPlaceholder: 'Write a comment…', replyPlaceholder: 'Reply…',
      send: 'Send', reply: 'Reply', resolve: 'Resolve', unresolve: 'Reopen',
      delete: 'Delete', cancel: 'Cancel', toolActive: 'Click on canvas to add comment',
      resolved: 'Resolved', showResolved: 'Show resolved', hideResolved: 'Hide resolved',
      mention: 'Mentioned user', pinLabel: (n) => `Comment ${n}`,
      you: 'You', anonymous: 'Anonymous'
    },
    km: {
      title: 'មតិយោបល់', empty: 'មិនទាន់មានមតិយោបល់ទេ',
      addPlaceholder: 'សរសេរមតិយោបល់…', replyPlaceholder: 'ឆ្លើយតប…',
      send: 'ផ្ញើ', reply: 'ឆ្លើយតប', resolve: 'បិទបញ្ហា', unresolve: 'បើកឡើងវិញ',
      delete: 'លុប', cancel: 'បោះបង់', toolActive: 'ចុចលើកាណវាស់ដើម្បីបន្ថែមមតិយោបល់',
      resolved: 'បានបិទ', showResolved: 'បង្ហាញដែលបានបិទ', hideResolved: 'លាក់ដែលបានបិទ',
      mention: 'បានផ្ដល់់សំគាល់អ្នកប្រើ', pinLabel: (n) => `មតិយោបល់ ${n}`,
      you: 'អ្នក', anonymous: 'អនាមិក'
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

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta?.getAttribute('content') || '';
  }

  /** Module state. */
  const state = {
    invitationId: null,
    panel: null,
    pinLayer: null,
    comments: [],            // flat list (root + replies)
    showResolved: false,
    toolActive: false,
    selectedPin: null,
    csrf: ''
  };

  /** Build the side panel + pin layer (idempotent). */
  function build() {
    if (state.panel) return state.panel;
    const panel = document.createElement('section');
    panel.id = 'eiCollabComments';
    panel.className = 'ei-chrome-panel ei-comments-panel';
    panel.setAttribute('aria-label', t('title'));
    panel.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" data-action="toggle-resolved" aria-pressed="false">${t('showResolved')}</button>
      </header>
      <div class="ei-comments-list" role="list" aria-label="${t('title')}"></div>
      <div class="ei-comments-empty" hidden>${t('empty')}</div>
    `;
    document.body.appendChild(panel);
    state.panel = panel;
    const pinLayer = document.createElement('div');
    pinLayer.id = 'eiCollabCommentPins';
    pinLayer.className = 'ei-comment-pins';
    pinLayer.setAttribute('aria-hidden', 'true');
    const stage = document.getElementById('stage');
    (stage || document.body).appendChild(pinLayer);
    state.pinLayer = pinLayer;
    $('[data-action="toggle-resolved"]', panel).addEventListener('click', toggleResolved);
    return panel;
  }

  /** Activate the comment tool — canvas clicks add pins. */
  function activateTool() {
    state.toolActive = !state.toolActive;
    document.body.classList.toggle('is-comment-tool-active', state.toolActive);
    window.uiToast?.(state.toolActive ? t('toolActive') : '', '');
  }

  /** API: list comments. */
  async function fetchComments() {
    if (!state.invitationId) return [];
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments`, {
      credentials: 'same-origin', headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.comments) ? data.comments : [];
  }

  /** Persist a new root comment. */
  async function create({ x, y, pageId = 'hero', elementId = null, body }) {
    if (!state.invitationId || !body) return null;
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ x, y, pageId, elementId, body: String(body).slice(0, 4000) })
    });
    if (!res.ok) { window.uiToast?.('Comment failed', '!'); return null; }
    const data = await res.json();
    await refresh();
    return data;
  }

  /** Reply to an existing thread. */
  async function reply(commentId, body) {
    if (!state.invitationId || !body) return null;
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ parentId: commentId, body: String(body).slice(0, 4000) })
    });
    if (!res.ok) { window.uiToast?.('Reply failed', '!'); return null; }
    const data = await res.json();
    await refresh();
    return data;
  }

  /** Resolve or reopen a thread. */
  async function resolve(commentId, resolved = true) {
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments/${encodeURIComponent(commentId)}`, {
      method: 'PUT', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ resolved })
    });
    if (!res.ok) { window.uiToast?.('Resolve failed', '!'); return null; }
    await refresh();
    return true;
  }

  async function remove(commentId) {
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments/${encodeURIComponent(commentId)}`, {
      method: 'DELETE', credentials: 'same-origin',
      headers: { 'X-CSRF-Token': state.csrf }
    });
    if (!res.ok) { window.uiToast?.('Delete failed', '!'); return null; }
    await refresh();
    return true;
  }

  function toggleResolved() {
    state.showResolved = !state.showResolved;
    const btn = $('[data-action="toggle-resolved"]', state.panel);
    btn.textContent = state.showResolved ? t('hideResolved') : t('showResolved');
    btn.setAttribute('aria-pressed', String(state.showResolved));
    render();
  }

  /** Group comments into threads: root → replies. */
  function threads() {
    const roots = state.comments.filter((c) => !c.parentId);
    const repliesByRoot = new Map();
    for (const c of state.comments) {
      if (c.parentId) {
        const list = repliesByRoot.get(c.parentId) || [];
        list.push(c); repliesByRoot.set(c.parentId, list);
      }
    }
    return roots.map((root) => ({ root, replies: repliesByRoot.get(root.id) || [] }));
  }

  function render() {
    if (!state.panel) build();
    const list = $('.ei-comments-list', state.panel);
    const empty = $('.ei-comments-empty', state.panel);
    list.replaceChildren();
    const pins = state.pinLayer;
    if (pins) pins.replaceChildren();
    const all = threads();
    const visible = state.showResolved ? all : all.filter((t) => !t.root.resolvedAt);
    if (!visible.length) { empty.hidden = false; return; }
    empty.hidden = true;
    for (const [idx, thread] of visible.entries()) {
      list.appendChild(buildThreadRow(thread, idx + 1));
      if (pins) pins.appendChild(buildPin(thread.root, idx + 1));
    }
  }

  function buildThreadRow(thread, n) {
    const row = document.createElement('article');
    row.className = 'ei-comment-thread';
    row.dataset.id = thread.root.id;
    if (thread.root.resolvedAt) row.classList.add('is-resolved');
    row.innerHTML = `
      <header><span class="ei-comment-pin-marker" aria-hidden="true">${n}</span>
        <strong class="ei-comment-author"></strong>
        <small class="ei-comment-time"></small></header>
      <p class="ei-comment-body"></p>
      <div class="ei-comment-replies" role="list"></div>
      <form class="ei-comment-reply-form"><input type="text" placeholder="${t('replyPlaceholder')}" aria-label="${t('replyPlaceholder')}">
        <button type="submit">${t('reply')}</button></form>
      <footer class="ei-comment-actions">
        <button type="button" data-action="resolve"></button>
        <button type="button" data-action="delete" class="danger">${t('delete')}</button>
      </footer>`;
    $('.ei-comment-author', row).textContent = thread.root.authorName || t('anonymous');
    $('.ei-comment-time', row).textContent = formatTime(thread.root.createdAt);
    $('.ei-comment-body', row).textContent = thread.root.body;
    const replyList = $('.ei-comment-replies', row);
    for (const r of thread.replies) {
      const item = document.createElement('div');
      item.className = 'ei-comment-reply';
      item.setAttribute('role', 'listitem');
      item.innerHTML = `<strong></strong> <span></span>`;
      item.querySelector('strong').textContent = r.authorName || t('anonymous');
      item.querySelector('span').textContent = r.body;
      replyList.appendChild(item);
    }
    const resolveBtn = $('[data-action="resolve"]', row);
    resolveBtn.textContent = thread.root.resolvedAt ? t('unresolve') : t('resolve');
    resolveBtn.addEventListener('click', () => resolve(thread.root.id, !thread.root.resolvedAt));
    $('[data-action="delete"]', row).addEventListener('click', () => remove(thread.root.id));
    $('.ei-comment-reply-form', row).addEventListener('submit', (event) => {
      event.preventDefault();
      const input = $('input', event.target);
      const value = input.value.trim(); if (!value) return;
      reply(thread.root.id, value); input.value = '';
    });
    return row;
  }

  function buildPin(root, n) {
    const pin = document.createElement('button');
    pin.type = 'button';
    pin.className = 'ei-comment-pin';
    pin.dataset.id = root.id;
    pin.setAttribute('aria-label', t('pinLabel', n));
    if (root.resolvedAt) pin.classList.add('is-resolved');
    const x = Math.max(0, Math.min(1, Number(root.x) || 0));
    const y = Math.max(0, Math.min(1, Number(root.y) || 0));
    pin.style.left = `${x * 100}%`;
    pin.style.top = `${y * 100}%`;
    pin.textContent = String(n);
    pin.addEventListener('click', () => openThread(root.id));
    return pin;
  }

  function openThread(commentId) {
    const row = $(`.ei-comment-thread[data-id="${CSS.escape(commentId)}"]`, state.panel);
    if (row) {
      row.scrollIntoView({ block: 'nearest' });
      row.classList.add('is-open');
      setTimeout(() => row.classList.remove('is-open'), 2000);
    }
  }

  function formatTime(ts) {
    if (!ts) return '';
    try { return new Date(Number(ts)).toLocaleString(); }
    catch { return ''; }
  }

  /** Wire canvas click → pin placement when the tool is active. */
  function wireCanvas() {
    const stage = document.getElementById('stage');
    if (!stage) return;
    stage.addEventListener('click', (event) => {
      if (!state.toolActive) return;
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;
      const b = bridge();
      const pageId = b?.getActiveCanvasId?.() || 'hero';
      const text = window.prompt?.(t('addPlaceholder'), '');
      if (text) create({ x, y, pageId, body: text });
      state.toolActive = false;
      document.body.classList.remove('is-comment-tool-active');
    });
  }

  /** Reload from server + re-render. */
  async function refresh() {
    state.comments = await fetchComments();
    render();
  }

  /** Mount + initial fetch. */
  async function mount(invitationId, options = {}) {
    state.invitationId = String(invitationId || '');
    state.csrf = options.csrf || csrfToken();
    build();
    wireCanvas();
    await refresh();
    // Poll every 5s for new comments (in addition to any Y.js broadcast).
    setInterval(refresh, 5000);
    return state.panel;
  }

  function registerCommands() {
    const r = window.EInviteCommandRegistry; if (!r?.register) return;
    try {
      r.register({
        id: 'comments.togglePanel', title: 'Toggle comments panel',
        category: 'View', keywords: ['comments', 'panel', 'threads'],
        bindings: { standard: ['Alt+C'], canva: ['Alt+C'], photoshop: ['Alt+C'] },
        run: () => { if (state.panel) state.panel.hidden = !state.panel.hidden; }
      });
      r.register({
        id: 'comments.activateTool', title: 'Add a comment (click canvas)',
        category: 'Insert', keywords: ['comment', 'pin', 'annotate'],
        bindings: { standard: ['C'], canva: ['C'], photoshop: ['C'] },
        run: () => activateTool()
      });
    } catch { /* duplicate — ignore */ }
  }

  window.EInviteCollabComments = Object.freeze({
    version: 58, STRINGS, mount, refresh, activateTool, openThread,
    create, reply, resolve, remove, toggleResolved, registerCommands
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerCommands);
  } else {
    queueMicrotask(registerCommands);
  }
})();
