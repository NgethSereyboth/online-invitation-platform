/* v55 — templates administration (ROADMAP §5.3)
 *
 * The "Templates" tab shipped in admin.html with no renderer inside the route
 * bundle: the panel existed but nothing ever mounted into it, so the tab opened a
 * completely empty region with no request, no empty state and no error (dogfood
 * ISSUE-002, 2026-10-15). The old renderer lives in the monolithic src/js/admin.js,
 * which is not part of any page bundle. This module follows the shipped
 * users/invitations modules instead — its own search input, `ei-admin-table`
 * markup, a polite live region for results — and uses the existing
 * GET /api/admin/templates + PUT /api/admin/templates/{id}/visibility endpoints.
 *
 * Khmer: strings with a trusted translation in docs/i18n/TRANSLATIONS.csv reuse
 * it; everything else keeps the English text (KH_PENDING), per repo convention.
 */
(function(){
  'use strict';
  if (window.EInviteAdminTemplates && window.EInviteAdminTemplates.version >= 55) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: {
      title:'Templates',
      shown:'{count} shown',
      search:'Search templates by name, category, owner, or visibility',
      name:'Template', category:'Category', owner:'Owner', version:'Version',
      visibility:'Visibility', updated:'Updated', actions:'Actions',
      marketplace:'Marketplace', private:'Private', save:'Save',
      noTemplates:'No templates found. A template appears here once a user saves one from the editor.',
      loadFailed:'Templates could not be loaded. Refresh the page or try again.',
      retry:'Retry',
      confirmVisibility:'Change marketplace visibility for “{name}”?',
      saved:'Visibility saved for “{name}”.',
      saveFailed:'Could not save the change. Try again.',
      readOnly:'Administrator access is required to change template visibility.'
    },
    km: {
      /* Trusted Khmer from docs/i18n/TRANSLATIONS.csv. */
      title:'ពុម្ពអត្ថបទ', category:'ប្រភេទ', owner:'ម្ចាស់', version:'កំណែ',
      visibility:'ភាពមើលឃើញ', updated:'បានធ្វើបច្ចុប្គន្នភាព', actions:'សកម្មភាព',
      save:'រក្សាទុក', retry:'ព្យាយាមម្ដងទៀត',
      /* KH_PENDING — no trusted Khmer translation; English text kept. */
      shown:'{count} shown',
      search:'Search templates by name, category, owner, or visibility',
      name:'Template', marketplace:'Marketplace', private:'Private',
      noTemplates:'No templates found. A template appears here once a user saves one from the editor.',
      loadFailed:'Templates could not be loaded. Refresh the page or try again.',
      confirmVisibility:'Change marketplace visibility for “{name}”?',
      saved:'Visibility saved for “{name}”.',
      saveFailed:'Could not save the change. Try again.',
      readOnly:'Administrator access is required to change template visibility.'
    }
  };
  function t(key, ...args) {
    var out = window.EInviteI18n
      ? window.EInviteI18n.t(key, STRINGS, ...args)
      : ((STRINGS[(document.documentElement.lang || 'en').toString().toLowerCase().startsWith('km') ? 'km' : 'en'] || STRINGS.en)[key] || key);
    return typeof out === 'function' ? out(...args) : out;
  }
  let state = { items: [], q: '', failed: false };

  async function load(){
    try {
      const rows = await shell().api.get('/api/admin/templates');
      state.items = Array.isArray(rows) ? rows : [];
      state.failed = false;
    } catch(e) {
      state.items = [];
      state.failed = true;
      throw e;
    }
  }

  function visible(){
    const q = (state.q || '').trim().toLowerCase();
    if (!q) return state.items;
    return state.items.filter(x => [x.name, x.category, x.ownerEmail, x.visibility]
      .some(v => String(v == null ? '' : v).toLowerCase().includes(q)));
  }

  function render(){
    const host = document.getElementById('templatesPanel');
    if (!host) return;
    if (state.failed) {
      host.innerHTML = `
        <h2>${esc(t('title'))}</h2>
        <p class="ei-error" role="alert">${esc(t('loadFailed'))}</p>
        <p class="ei-help">${esc(t('readOnly'))}</p>
        <button type="button" data-action="retry">${esc(t('retry'))}</button>`;
      host.querySelector('[data-action="retry"]').addEventListener('click', () => refresh());
      return;
    }
    const rows = visible().map(x => `
      <tr data-template-id="${esc(x.id)}">
        <td>${esc(x.name || 'Untitled template')}<br><small>${esc(x.ownerEmail || '—')} · v${esc(x.currentVersion || 1)}</small></td>
        <td>${esc(x.category || '—')}</td>
        <td>
          <label class="sr-only" for="visibility-${esc(x.id)}">${esc(t('visibility'))} — ${esc(x.name || '')}</label>
          <select id="visibility-${esc(x.id)}" data-visibility>
            <option value="private" ${x.visibility === 'public' ? '' : 'selected'}>${esc(t('private'))}</option>
            <option value="public" ${x.visibility === 'public' ? 'selected' : ''}>${esc(t('marketplace'))}</option>
          </select>
        </td>
        <td>${x.updatedAt ? esc(new Date(x.updatedAt).toLocaleString()) : '—'}</td>
        <td class="ei-row-actions"><button type="button" data-action="save-template">${esc(t('save'))}</button></td>
      </tr>`).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p class="ei-help">${esc(t('readOnly'))}</p>
      <label class="sr-only" for="templatesSearch">${esc(t('search'))}</label>
      <input type="search" class="admin-search" id="templatesSearch" placeholder="${esc(t('search'))}" value="${esc(state.q)}">
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('name'))}</th><th>${esc(t('category'))}</th><th>${esc(t('visibility'))}</th><th>${esc(t('updated'))}</th><th>${esc(t('actions'))}</th>
      </tr></thead><tbody>${rows || `<tr><td colspan="5">${esc(t('noTemplates'))}</td></tr>`}</tbody></table>
      <p class="ei-help">${esc(t('shown', { count: visible().length }))}</p>
      <p class="ei-admin-live" role="status" aria-live="polite"></p>`;
    const search = document.getElementById('templatesSearch');
    if (search) search.addEventListener('input', e => { state.q = e.target.value; render(); });
    host.querySelectorAll('[data-action="save-template"]').forEach(btn => btn.addEventListener('click', () => save(btn)));
  }

  function status(message, isError){
    const live = document.querySelector('#templatesPanel .ei-admin-live');
    if (live) { live.textContent = message; live.classList.toggle('ei-error', !!isError); return; }
    /* No live region (e.g. the panel was re-rendered): fall back to the toast. */
    if (window.EInviteToast && typeof window.EInviteToast.show === 'function') {
      window.EInviteToast.show({ type: isError ? 'error' : 'success', message_en: message, message_km: '' });
    }
  }

  async function save(btn){
    const row = btn.closest('[data-template-id]');
    const id = row && row.dataset.templateId;
    const select = row && row.querySelector('[data-visibility]');
    if (!id || !select) return;
    const item = state.items.find(x => String(x.id) === String(id)) || {};
    if (!confirm(t('confirmVisibility', { name: item.name || 'this template' }))) return;
    btn.disabled = true;
    try {
      await shell().api.send(`/api/admin/templates/${encodeURIComponent(id)}/visibility`, 'PUT', { visibility: select.value });
      item.visibility = select.value;
      render();
      status(t('saved', { name: item.name || 'this template' }), false);
    } catch(e) {
      btn.disabled = false;
      status(`${t('saveFailed')} (${e.message || 'error'})`, true);
    }
  }

  async function refresh(){
    try { await load(); } catch(e) { /* rendered as the failed state */ }
    render();
  }

  let _langUnsub = null;
  async function mount(){
    try { await load(); } catch(e) { /* rendered as the failed state */ }
    render();
    if (!_langUnsub && window.EInviteI18n && typeof window.EInviteI18n.subscribe === 'function') {
      _langUnsub = window.EInviteI18n.subscribe(render);
    }
  }
  window.EInviteAdminTemplates = Object.freeze({ version: 55, mount, render, load });
})();
