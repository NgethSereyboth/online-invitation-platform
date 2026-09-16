/* v0.65.3 — impersonation (ROADMAP §5.8)
 * Super-admin logs in as another user. 30-minute hard cap. Red banner
 * everywhere when active. Every action audited with `impersonated_by`.
 */
(function(){
  'use strict';
  if (window.EInviteAdminImpersonate && window.EInviteAdminImpersonate.version >= 65) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Impersonation', description:'Start an impersonation session as another user. The session expires after 30 minutes and every action is audit-logged.', userId:'User id to impersonate', start:'Start impersonation', stop:'Stop impersonation', confirmStart:'Start impersonation session? You will be logged in as this user for 30 minutes. Every action will be audit-logged.', notActive:'No active impersonation session.', requireSuperAdmin:'Super-admin access required.', current:'Current session', adminOriginId:'Original admin id' },
    km: { title:'ការសាកល្បងក្នុងនាម', description:'ចាប់ផ្ដើមសessianក្នុងនាមអ្នកប្រើផ្សេងទៀត។ សessianនឹងផុតកំណត់បន្ទាប់ពី ៣០ នាទី ហើយសកម្មភាពនីមួយៗត្រូវបានកត់ត្រាសវនកម្ម។', userId:'លេខសម្គាល់អ្នកប្រើដែលត្រូវសាកល្បង', start:'ចាប់ផ្ដើម', stop:'បញ្ឈប់', confirmStart:'ចាប់ផ្ដើមសessian? អ្នកនឹងត្រូវបានឡុកអិនក្នុងនាមអ្នកប្រើនេះរយៈពេល ៣០ នាទី។', notActive:'មិនមានសessianសកម្មទេ។', requireSuperAdmin:'ត្រូវការ super-admin។', current:'សessianបច្ចុប្បន្ន', adminOriginId:'លេខសម្គាល់អ្នកគ្រប់គ្រងដើម' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { current: null };

  async function loadCurrent(){
    const api = shell().api;
    try {
      const me = await api.get('/api/auth/me');
      state.current = (me && me.user && me.user.impersonating) ? me.user : null;
    } catch(e) { state.current = null; }
  }

  function render(){
    const host = document.getElementById('impersonatePanel');
    if (!host) return;
    const current = state.current ? `
      <p><strong>${esc(t('current'))}:</strong> ${esc(state.current.email)} <small>(${esc(t('adminOriginId'))}: ${esc(state.current.impersonatedBy || '—')})</small></p>
      <button id="impersonateStop">${esc(t('stop'))}</button>
    ` : `<p>${esc(t('notActive'))}</p>`;
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p>${esc(t('description'))}</p>
      <p class="ei-help">${esc(t('requireSuperAdmin'))}</p>
      ${current}
      <hr>
      <form id="impersonateStartForm">
        <label>${esc(t('userId'))}<input type="text" name="userId" required></label>
        <button type="submit">${esc(t('start'))}</button>
      </form>`;
    const form = document.getElementById('impersonateStartForm');
    if (form) form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!confirm(t('confirmStart'))) return;
      const fd = new FormData(form);
      const userId = fd.get('userId');
      try {
        const api = shell().api;
        const res = await api.send(`/api/admin/impersonate/${encodeURIComponent(userId)}`, 'POST', {});
        if (res && res.impersonating) window.location.reload();
      } catch(err) { alert(err.message || 'Impersonation failed'); }
    });
    const stopBtn = document.getElementById('impersonateStop');
    if (stopBtn) stopBtn.addEventListener('click', async () => {
      try { await shell().api.send('/api/admin/impersonate/stop', 'POST', {}); window.location.href = '/admin.html'; }
      catch(e) { alert(e.message); }
    });
  }

  async function mount(){
    try { await loadCurrent(); } catch(e) {}
    render();
    // Surface the red banner globally if active.
    const banner = document.getElementById('impersonationBanner');
    if (banner) banner.hidden = !state.current;
  }
  window.EInviteAdminImpersonate = Object.freeze({ version: 65, mount, render, loadCurrent });
})();
