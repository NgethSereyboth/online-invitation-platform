/* v55 — AI provider status panel (ROADMAP §5.4/§5.9)
 *
 * The "AI providers" tab shipped in admin.html with no renderer inside the route
 * bundle, so the tab opened an empty region: no request, no empty state, no error
 * (dogfood ISSUE-002, 2026-10-15). The only renderer was in the monolithic
 * src/js/admin.js, which no page bundle includes. This module mounts the existing
 * GET /api/admin/ai/providers payload (version 53.1) into #aiPanel: model routing
 * per role, local model-directory status, and one card per configured provider.
 *
 * Read-only by design — endpoints, allowlists and model roles are server
 * environment configuration, so there is nothing here for a browser user to edit.
 *
 * Khmer: no trusted Khmer translation exists for these strings in
 * docs/i18n/TRANSLATIONS.csv, so the English text is kept (KH_PENDING) rather than
 * inventing Khmer, per repo convention.
 */
(function(){
  'use strict';
  if (window.EInviteAdminAiProviders && window.EInviteAdminAiProviders.version >= 55) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: {
      title:'AI providers',
      intro:'Local AI providers are configured with server environment variables. Endpoints, allowlists and model roles cannot be set from the browser.',
      routing:'Model routing',
      noRoles:'No local model roles are selected.',
      roleAvailable:'available', roleUnavailable:'unavailable', notSelected:'not selected',
      directory:'Local model directory',
      directoryNotConfigured:'not configured',
      directoryUnavailable:'configured but unavailable',
      directoryAvailable:'{count} compatible file(s) discovered; runtime registration is still required.',
      providers:'Providers',
      disabled:'Local AI providers are disabled on this server (EINVITE_LOCAL_AI is off).',
      none:'No local AI providers are enabled. Configure them with server environment variables; browser users cannot set arbitrary endpoints.',
      healthy:'Healthy', unavailable:'Unavailable',
      models:'{count} models', modelOne:'1 model', modelsNone:'No models discovered.',
      checked:'Checked {when}',
      columns:'Model · type · tools · vision · structured output · context',
      loadFailed:'AI provider status is unavailable right now.',
      retry:'Retry'
    },
    km: {
      /* KH_PENDING — no trusted Khmer translation; English text kept. */
      title:'AI providers',
      intro:'Local AI providers are configured with server environment variables. Endpoints, allowlists and model roles cannot be set from the browser.',
      routing:'Model routing',
      noRoles:'No local model roles are selected.',
      roleAvailable:'available', roleUnavailable:'unavailable', notSelected:'not selected',
      directory:'Local model directory',
      directoryNotConfigured:'not configured',
      directoryUnavailable:'configured but unavailable',
      directoryAvailable:'{count} compatible file(s) discovered; runtime registration is still required.',
      providers:'Providers',
      disabled:'Local AI providers are disabled on this server (EINVITE_LOCAL_AI is off).',
      none:'No local AI providers are enabled. Configure them with server environment variables; browser users cannot set arbitrary endpoints.',
      healthy:'Healthy', unavailable:'Unavailable',
      models:'{count} models', modelOne:'1 model', modelsNone:'No models discovered.',
      checked:'Checked {when}',
      columns:'Model · type · tools · vision · structured output · context',
      loadFailed:'AI provider status is unavailable right now.',
      retry:'Retry'
    }
  };
  function t(key, ...args) {
    var out = window.EInviteI18n
      ? window.EInviteI18n.t(key, STRINGS, ...args)
      : ((STRINGS[(document.documentElement.lang || 'en').toString().toLowerCase().startsWith('km') ? 'km' : 'en'] || STRINGS.en)[key] || key);
    return typeof out === 'function' ? out(...args) : out;
  }
  let state = { payload: null, failed: false };

  async function load(){
    try {
      state.payload = await shell().api.get('/api/admin/ai/providers');
      state.failed = false;
    } catch(e) {
      state.payload = null;
      state.failed = true;
      throw e;
    }
  }

  function rolesMarkup(payload){
    const roles = Object.entries((payload && payload.modelRoles) || {});
    if (!roles.length) return `<p class="ei-help">${esc(t('noRoles'))}</p>`;
    return `<dl class="ei-admin-defs">${roles.map(([role, value]) => `
      <dt>${esc(role)}</dt>
      <dd>${esc((value && value.selection) || t('notSelected'))} · ${esc(value && value.available ? t('roleAvailable') : t('roleUnavailable'))}</dd>`).join('')}</dl>`;
  }

  function directoryLine(payload){
    const dir = (payload && payload.modelDirectory) || {};
    if (!dir.configured) return t('directoryNotConfigured');
    if (!dir.available) return t('directoryUnavailable');
    return t('directoryAvailable', { count: (dir.files || []).length });
  }

  /* "1 model", not "1 models" — the count is a plural form, not a template. */
  function modelsLabel(count){ return count === 1 ? t('modelOne') : t('models', { count }); }

  function modelLines(provider){
    const models = (provider.models || []).slice(0, 30);
    if (!models.length) return `<p class="ei-help">${esc(t('modelsNone'))}</p>`;
    return `<details class="ei-admin-details"><summary>${esc(modelsLabel((provider.models || []).length))}</summary>
      <p class="ei-help">${esc(t('columns'))}</p>
      <ul class="ei-admin-model-list">${models.map(model => `
        <li><strong>${esc(model.name || model.id)}</strong> · ${esc(model.type || 'text')} · tools ${model.toolCalling ? 'yes' : 'no'} · vision ${model.vision ? 'yes' : 'no'} · structured ${model.structuredOutput ? 'yes' : 'no'}${model.contextLength ? ` · context ${esc(model.contextLength)}` : ''}</li>`).join('')}</ul></details>`;
  }

  function providerCards(payload){
    const providers = (payload && payload.providers) || [];
    if (!providers.length) return `<p>${esc(payload && payload.enabled === false ? t('disabled') : t('none'))}</p>`;
    return providers.map(provider => `
      <article class="admin-row" data-provider-id="${esc(provider.id)}">
        <div>
          <h3>${esc(provider.label || provider.id)}</h3>
          <small>${esc(provider.endpointLabel || 'Server configured')} · ${esc(provider.kind || 'local')}</small>
        </div>
        <span class="ei-tag ${provider.healthy ? 'ei-tag-ok' : 'ei-tag-warn'}">${esc(provider.healthy ? t('healthy') : t('unavailable'))}</span>
        <span>${esc(modelsLabel((provider.models || []).length))}</span>
        <span>${esc(t('checked', { when: provider.checkedAt ? new Date(provider.checkedAt).toLocaleString() : '—' }))}</span>
        <div>${modelLines(provider)}${provider.error ? `<p class="ei-error">${esc(provider.error)}</p>` : ''}</div>
      </article>`).join('');
  }

  function render(){
    const host = document.getElementById('aiPanel');
    if (!host) return;
    if (state.failed) {
      host.innerHTML = `
        <h2>${esc(t('title'))}</h2>
        <p class="ei-error" role="alert">${esc(t('loadFailed'))}</p>
        <p class="ei-help">${esc(t('intro'))}</p>
        <button type="button" data-action="retry">${esc(t('retry'))}</button>`;
      host.querySelector('[data-action="retry"]').addEventListener('click', () => refresh());
      return;
    }
    const payload = state.payload || {};
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p class="ei-help">${esc(t('intro'))}</p>
      <section class="ei-admin-section">
        <h3>${esc(t('routing'))}</h3>
        ${rolesMarkup(payload)}
        <p><strong>${esc(t('directory'))}:</strong> ${esc(directoryLine(payload))}</p>
      </section>
      <section class="ei-admin-section">
        <h3>${esc(t('providers'))}</h3>
        ${providerCards(payload)}
      </section>
      <p class="ei-admin-live" role="status" aria-live="polite"></p>`;
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
  window.EInviteAdminAiProviders = Object.freeze({ version: 55, mount, render, load });
})();
