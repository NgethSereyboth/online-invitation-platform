/* v0.64.3 — feature flags (ROADMAP §5.4)
 * Super-admin toggles features on/off without deploying.
 */
(function(){
  'use strict';
  if (window.EInviteAdminFeatureFlags && window.EInviteAdminFeatureFlags.version >= 64) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Feature flags', description:'Toggle platform features on or off. Changes take effect immediately — no restart required.', save:'Save', on:'On', off:'Off', updatedAt:'Updated', updatedBy:'by', noFlags:'No flags defined.', tier:'Tier', confirmSave:'Save this flag value?', requireSuperAdmin:'Super-admin access required to modify flags.' },
    km: { title:'ទងជម្រើសមុខងារ', description:'បិទ/បើកមុខងារ។ ការផ្លាស់ប្ដូរមានប្រសិទ្ធភាពភ្លាមៗ — មិនចាំបាច់រេស្តាតឡើងវិញ។', save:'រក្សាទុក', on:'បើក', off:'បិទ', updatedAt:'បានធ្វើបច្ចុប្បន្នភាព', updatedBy:'ដោយ', noFlags:'មិនមានទងជម្រើស។', tier:'ថ្នាក់', confirmSave:'រក្សាទុកតម្លៃនេះ?', requireSuperAdmin:'ត្រូវការសិទ្ធិ super-admin ដើម្បីកែប្រែ។' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { flags: [] };

  async function load(){
    const api = shell().api;
    const data = await api.get('/api/admin/feature-flags');
    state.flags = data.flags || [];
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
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p>${esc(t('description'))}</p>
      <p class="ei-help">${esc(t('requireSuperAdmin'))}</p>
      <table class="ei-admin-table"><thead><tr>
        <th>Flag</th><th>${esc(t('tier'))}</th><th>${esc(t('on'))}/${esc(t('off'))}</th><th>${esc(t('updatedAt'))}</th><th></th>
      </tr></thead><tbody>${rows || `<tr><td colspan="5">${esc(t('noFlags'))}</td></tr>`}</tbody></table>`;
    host.querySelectorAll('[data-action="save"]').forEach(btn => btn.addEventListener('click', () => handleSave(btn)));
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

  async function mount(){ try { await load(); } catch(e) {} render(); }
  window.EInviteAdminFeatureFlags = Object.freeze({ version: 64, mount, render, load });
})();
