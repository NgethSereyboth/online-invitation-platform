/* v0.64.1 — users management (ROADMAP §5.2)
 * Browse, search, suspend/unsuspend, reset password, force MFA, impersonate.
 */
(function(){
  'use strict';
  if (window.EInviteAdminUsers && window.EInviteAdminUsers.version >= 64) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Users', search:'Search by email, role, or plan', prev:'Previous', next:'Next', suspend:'Suspend', unsuspend:'Unsuspend', resetPw:'Reset password', forceMfa:'Force MFA', impersonate:'Impersonate', confirmSuspend:'Suspend this user? Active sessions will be invalidated.', confirmResetPw:'Send a password-reset email to this user?', confirmForceMfa:'Force this user to re-enroll MFA on next login?', confirmImpersonate:'Start an impersonation session as this user? You will be logged in as them for 30 minutes.', suspendReason:'Reason', noUsers:'No users found.', role:'Role', plan:'Plan', created:'Created', lastActive:'Last active', invitations:'Invitations', status:'Status', actions:'Actions', tipStepUp:'Super-admin (step-up) required' },
    km: { title:'អ្នកប្រើ', search:'ស្វែងរកតាមអ៊ីមែល តួនាទី ឬគម្រោង', prev:'មុន', next:'បន្ទាប់', suspend:'ផ្អាក', unsuspend:'ឈប់ផ្អាក', resetPw:'កំណត់ពាក្យសម្ងាត់ឡើងវិញ', forceMfa:'បង្ខំ MFA', impersonate:'សាកល្បងក្នុងនាម', confirmSuspend:'ផ្អាកអ្នកប្រើនេះ? សessianសកម្មនឹងត្រូវបោះបង់។', confirmResetPw:'ផ្ញើអ៊ីមែលកំណត់ពាក្យសម្ងាត់ឡើងវិញទៅអ្នកប្រើនេះ?', confirmForceMfa:'បង្ខំអ្នកប្រើនេះឱ្យចុះឈ្មោះ MFA ឡើងវិញនៅពេលឡុកអិន下一次?', confirmImpersonate:'ចាប់ផ្ដើមសessianសាកល្បងក្នុងនាមអ្នកប្រើនេះ? អ្នកនឹងត្រូវបានឡុកអិនក្នុងនាមពួកគេរយៈពេល ៣០ នាទី។', suspendReason:'មូលហេតុ', noUsers:'រកមិនឃើញអ្នកប្រើ។', role:'តួនាទី', plan:'គម្រោង', created:'បង្កើត', lastActive:'សកម្មចុងក្រោយ', invitations:'ការអញ្ជើញ', status:'ស្ថានភាព', actions:'សកម្មភាព', tipStepUp:'ត្រូវការ super-admin (step-up)' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { items: [], nextCursor: null, q: '', hasMore: false };

  async function load(){
    const api = shell().api;
    const params = new URLSearchParams({ limit: '50' });
    if (state.q) params.set('q', state.q);
    if (state.nextCursor) params.set('cursor', String(state.nextCursor));
    try {
      const data = await api.get(`/api/admin/users-v2?${params}`);
      state.items = data.items || [];
      state.hasMore = !!data.hasMore;
    } catch(e) {
      state.items = [];
      state.hasMore = false;
      throw e;
    }
  }

  function render(){
    const host = document.getElementById('usersPanel');
    if (!host) return;
    const rows = state.items.map(u => {
      const status = u.suspended ? `<span class="ei-tag ei-tag-warn">${t('suspended')}</span>` : `<span class="ei-tag ei-tag-ok">${t('active')}</span>`;
      const date = u.createdAt ? new Date(u.createdAt).toLocaleDateString() : '—';
      const last = u.lastSeenAt ? new Date(u.lastSeenAt).toLocaleDateString() : '—';
      return `<tr data-user-id="${esc(u.id)}">
        <td>${esc(u.email)}<br><small>${esc(u.role)} · ${esc(u.plan)}</small></td>
        <td>${esc(date)}</td>
        <td>${esc(last)}</td>
        <td>${esc(u.invitationCount || 0)}</td>
        <td>${status}</td>
        <td class="ei-row-actions">
          ${u.suspended
            ? `<button data-action="unsuspend">${t('unsuspend')}</button>`
            : `<button data-action="suspend" data-reason-prompt="${esc(t('suspendReason'))}">${t('suspend')}</button>`}
          <button data-action="reset-password">${t('resetPw')}</button>
          <button data-action="force-mfa">${t('forceMfa')}</button>
          <button data-action="impersonate" title="${esc(t('tipStepUp'))}">${t('impersonate')}</button>
        </td>
      </tr>`;
    }).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <input type="search" class="admin-search" id="usersSearch" placeholder="${esc(t('search'))}" value="${esc(state.q)}">
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('role'))} / ${esc(t('plan'))}</th>
        <th>${esc(t('created'))}</th>
        <th>${esc(t('lastActive'))}</th>
        <th>${esc(t('invitations'))}</th>
        <th>${esc(t('status'))}</th>
        <th>${esc(t('actions'))}</th>
      </tr></thead><tbody>${rows || `<tr><td colspan="6">${esc(t('noUsers'))}</td></tr>`}</tbody></table>
      <div class="ei-pagination">
        <button id="usersPrev" ${state.nextCursor ? '' : 'disabled'}>${esc(t('prev'))}</button>
        <button id="usersNext" ${state.hasMore ? '' : 'disabled'}>${esc(t('next'))}</button>
      </div>`;
    const search = document.getElementById('usersSearch');
    if (search) search.addEventListener('input', e => { state.q = e.target.value; state.nextCursor = null; load().then(render).catch(()=>{}); });
    host.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => handleAction(btn)));
  }

  async function handleAction(btn){
    const row = btn.closest('[data-user-id]');
    const userId = row && row.dataset.userId;
    const action = btn.dataset.action;
    if (!userId || !action) return;
    const api = shell().api;
    try {
      if (action === 'suspend') {
        const reason = window.prompt(t('suspendReason'), '') || '';
        if (!confirm(t('confirmSuspend'))) return;
        await api.send(`/api/admin/users/${encodeURIComponent(userId)}/suspend`, 'POST', { reason });
      } else if (action === 'unsuspend') {
        await api.send(`/api/admin/users/${encodeURIComponent(userId)}/unsuspend`, 'POST', {});
      } else if (action === 'reset-password') {
        if (!confirm(t('confirmResetPw'))) return;
        await api.send(`/api/admin/users/${encodeURIComponent(userId)}/reset-password`, 'POST', {});
      } else if (action === 'force-mfa') {
        if (!confirm(t('confirmForceMfa'))) return;
        await api.send(`/api/admin/users/${encodeURIComponent(userId)}/force-mfa`, 'POST', {});
      } else if (action === 'impersonate') {
        if (!confirm(t('confirmImpersonate'))) return;
        const res = await api.send(`/api/admin/impersonate/${encodeURIComponent(userId)}`, 'POST', {});
        if (res && res.impersonating) window.location.reload();
      }
      await load(); render();
    } catch(e) {
      alert(e.message || 'Action failed');
    }
  }

  async function mount(){
    try { await load(); } catch(e) { /* not authorized */ }
    render();
  }

  window.EInviteAdminUsers = Object.freeze({ version: 64, mount, render, load });
})();
