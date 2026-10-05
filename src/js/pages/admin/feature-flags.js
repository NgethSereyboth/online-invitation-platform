/* v0.65.0 — feature flags (ROADMAP §5.4)
 * Super-admin toggles features on/off without deploying.
 * Adds non-admin session idle window selector (7/15/30 days).
 */
(function(){
  'use strict';
  if (window.EInviteAdminFeatureFlags && window.EInviteAdminFeatureFlags.version >= 65) return;
  const shell = () => window.EInviteAdminShell || {};
          const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: {
      title:'Feature flags',
      description:'Toggle platform features on or off. Changes take effect immediately — no restart required.',
      save:'Save',
      on:'On',
      off:'Off',
      updatedAt:'Updated',
      updatedBy:'by',
      flag:'Flag',
      noFlags:'No flags defined.',
      tier:'Tier',
      confirmSave:'Save this flag value?',
      requireSuperAdmin:'Super-admin access required to modify flags.',
      sessionPolicyTitle:'Non-admin session idle window',
      sessionPolicyDesc:'How long a non-admin session may sit idle before it expires. Changing this affects all non-admin users.',
      sessionPolicyLabel:'Idle window (days)',
      sessionPolicySave:'Save idle window',
      sessionPolicyConfirm:'Change the non-admin session idle window to {days} days?',
      sessionPolicySaved:'Idle window updated to {days} days.',
      sessionPolicyError:'Failed to update idle window: {error}'
    },
    km: {
      title:'ទងជម្រើសមុខងារ',
      description:'បិទ/បើកមុខងារ។ ការផ្លាស់ប្ដូរមានប្រសិទ្ធភាពភ្លាមៗ — មិនចាំបាច់រេស្តាតឡើងវិញ។',
      save:'រក្សាទុក',
      on:'បើក',
      off:'បិទ',
      updatedAt:'បានធ្វើបច្ចុប្គន្នភាព',
      updatedBy:'ដោយ',
      flag:'Flag',
      noFlags:'No flags defined.',
      tier:'Tier',
      confirmSave:'Save this flag value?',
      requireSuperAdmin:'Super-admin access required to modify flags.',
      sessionPolicyTitle:'Non-admin session idle window',
      sessionPolicyDesc:'How long a non-admin session may sit idle before it expires. Changing this affects all non-admin users.',
      sessionPolicyLabel:'Idle window (days)',
      sessionPolicySave:'Save idle window',
      sessionPolicyConfirm:'Change the non-admin session idle window to {days} days?',
      sessionPolicySaved:'Idle window updated to {days} days.',
      sessionPolicyError:'Failed to update idle window: {error}'
    }
  };
  function t(key, ...args) {
    var out = window.EInviteI18n
      ? window.EInviteI18n.t(key, STRINGS, ...args)
      : ((STRINGS[(document.documentElement.lang || 'en').toString().toLowerCase().startsWith('km') ? 'km' : 'en'] || STRINGS.en)[key] || key);
    return typeof out === 'function' ? out(...args) : out;
  }
  let state = { flags: [], sessionIdleDays: 7 };

  async function load(){
    const api = shell().api;
    const [flagsData, settingsData] = await Promise.all([
      api.get('/api/admin/feature-flags'),
      api.get('/api/admin/settings')
    ]);
    state.flags = flagsData.flags || [];
    state.sessionIdleDays = settingsData.session_idle_days_nonadmin ?? 7;
  }

  function render(){
    const host = document.getElementById('featureFlagsPanel');
    if (!host) return;
    const rows = state.flags.map(f => `
      <tr data-flag-key="${esc(f.key)}">
        <td><strong>${esc(f.key)}</strong><br><small>${esc(f.description || '')}</small></td>
        <td>${esc(f.tier || '—')}</td>
        <td>
          <label class="ei-toggle">
            <input type="checkbox" data-flag-value ${f.value ? 'checked' : ''}>
            <span>${f.value ? t('on') : t('off')}</span>
          </label>
        </td>
        <td>${f.updatedAt ? new Date(f.updatedAt).toLocaleString() : '—'} ${f.updatedBy ? `<br><small>${esc(t('updatedBy'))} ${esc(f.updatedBy)}</small>` : ''}</td>
        <td><button data-action="save">${t('save')}</button></td>
      </tr>`).join('');
    const sessionOptions = [7, 15, 30].map(d => `<option value="${d}" ${state.sessionIdleDays === d ? 'selected' : ''}>${d}</option>`).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p>${esc(t('description'))}</p>
      <p class="ei-help">${esc(t('requireSuperAdmin'))}</p>
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('flag'))}</th><th>${esc(t('tier'))}</th><th>${esc(t('on'))}/${esc(t('off'))}</th><th>${esc(t('updatedAt'))}</th><th></th>
      </tr></thead><tbody>${rows || `<tr><td colspan="5">${esc(t('noFlags'))}</td></tr>`}</tbody></table>
      <section class="ei-admin-section" style="margin-top:24px;">
        <h3>${esc(t('sessionPolicyTitle'))}</h3>
        <p class="ei-help">${esc(t('sessionPolicyDesc'))}</p>
        <div class="ei-form-row" style="align-items:center; gap:12px; flex-wrap:wrap;">
          <label for="sessionIdleSelect" style="display:flex; align-items:center; gap:8px;">${esc(t('sessionPolicyLabel'))} <select id="sessionIdleSelect" data-setting="sessionIdleDays">${sessionOptions}</select></label>
          <button id="sessionIdleSave" data-action="save-session-idle">${esc(t('sessionPolicySave'))}</button>
        </div>
      </section>`;
    host.querySelectorAll('[data-action="save"]').forEach(btn => btn.addEventListener('click', () => handleSave(btn)));
    const saveBtn = host.querySelector('#sessionIdleSave');
    if (saveBtn) saveBtn.addEventListener('click', handleSaveSessionIdle);
  }

  async function handleSave(btn){
    const row = btn.closest('[data-flag-key]');
    const key = row && row.dataset.flagKey;
    const checkbox = row && row.querySelector('[data-flag-value]');
    if (!key || !checkbox) return;
    if (!confirm(t('confirmSave'))) return;
    const api = shell().api;
    try {
      await api.send('/api/admin/feature-flags', 'PUT', { updates: [{ key, value: checkbox.checked }] });
      await load(); render();
    } catch(e) { alert(e.message || 'Save failed'); }
  }

  async function handleSaveSessionIdle(){
    const select = document.getElementById('sessionIdleSelect');
    if (!select) return;
    const days = Number(select.value);
    if (![7, 15, 30].includes(days)) return;
    if (!confirm(t('sessionPolicyConfirm', { days: String(days) }))) return;
    const api = shell().api;
    try {
      await api.send('/api/admin/settings/session-idle-days-nonadmin', 'PUT', { days });
      await load(); render();
      alert(t('sessionPolicySaved', { days: String(days) }));
    } catch(e) {
      alert(t('sessionPolicyError', { error: e.message || 'Save failed' }));
    }
  }

  let _langUnsub = null;
  async function mount(){
    try { await load(); } catch(e) {}
    render();
    // POC (v0.68.3): re-render the (already-loaded) flag list on language switch
    // without re-fetching — t() now reads the active language from EInviteI18n.
    if (!_langUnsub && window.EInviteI18n && typeof window.EInviteI18n.subscribe === 'function') {
      _langUnsub = window.EInviteI18n.subscribe(render);
    }
  }
  window.EInviteAdminFeatureFlags = Object.freeze({ version: 65, mount, render, load });
})();