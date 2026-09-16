/* v0.64.2 — invitations management (ROADMAP §5.3)
 * Browse, search, unpublish, flag, transfer ownership.
 */
(function(){
  'use strict';
  if (window.EInviteAdminInvitations && window.EInviteAdminInvitations.version >= 64) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Invitations', search:'Search by slug or owner email', preview:'Preview', unpublish:'Unpublish', flag:'Flag', transfer:'Transfer', confirmUnpublish:'Unpublish this invitation? The owner will be notified by email.', confirmFlag:'Flag this invitation for review? Add a reason.', flagReason:'Reason for flagging', transferPrompt:'Enter the new owner user id:', noInvitations:'No invitations found.', slug:'Slug', owner:'Owner', created:'Created', published:'Published', views:'Views', rsvps:'RSVPs', status:'Status', actions:'Actions' },
    km: { title:'ការអញ្ជើញ', search:'ស្វែងរកតាម slug ឬអ៊ីមែលម្ចាស់', preview:'មើល', unpublish:'ឈប់ផ្សាយ', flag:'សម្គាល់', transfer:'ផ្ទេរម្ចាស់', confirmUnpublish:'ឈប់ផ្សាយការអញ្ជើញនេះ? ម្ចាស់នឹងត្រូវបានជូនដំណឹងតាមអ៊ីមែល។', confirmFlag:'សម្គាល់ការអញ្ជើញនេះសម្រាប់ពិនិត្យ? បន្ថែមមូលហេតុ។', flagReason:'មូលហេតុនៃការសម្គាល់', transferPrompt:'បញ្ចូលលេខសម្គាល់អ្នកប្រើម្ចាស់ថ្មី៖', noInvitations:'រកមិនឃើញការអញ្ជើញ។', slug:'Slug', owner:'ម្ចាស់', created:'បង្កើត', published:'ផ្សាយ', views:'មើល', rsvps:'RSVPs', status:'ស្ថានភាព', actions:'សកម្មភាព' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { items: [], q: '', status: '' };

  async function load(){
    const api = shell().api;
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.status) params.set('status', state.status);
    state.items = await api.get(`/api/admin/invitations-v2?${params}`);
  }

  function render(){
    const host = document.getElementById('invitationsPanel');
    if (!host) return;
    const rows = state.items.map(i => {
      const status = i.flaggedAt ? `<span class="ei-tag ei-tag-warn">flagged</span>`
                    : i.archived ? `<span class="ei-tag">archived</span>`
                    : i.published ? `<span class="ei-tag ei-tag-ok">published</span>`
                    : `<span class="ei-tag">draft</span>`;
      return `<tr data-invite-id="${esc(i.id)}">
        <td>${esc(i.slug)}<br><small>${esc(i.title || '')}</small></td>
        <td>${esc(i.ownerEmail || '—')}</td>
        <td>${i.createdAt ? new Date(i.createdAt).toLocaleDateString() : '—'}</td>
        <td>${i.published ? '✓' : '—'}</td>
        <td>${esc(i.views || 0)}</td>
        <td>${esc(i.rsvps || 0)}</td>
        <td>${status}</td>
        <td class="ei-row-actions">
          <a class="button-link" href="/i/${esc(i.slug)}" target="_blank" rel="noopener">${t('preview')}</a>
          ${i.published ? `<button data-action="unpublish">${t('unpublish')}</button>` : ''}
          <button data-action="flag">${t('flag')}</button>
          <button data-action="transfer">${t('transfer')}</button>
        </td>
      </tr>`;
    }).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <input type="search" class="admin-search" id="invitationsSearch" placeholder="${esc(t('search'))}" value="${esc(state.q)}">
      <select id="invitationsStatusFilter">
        <option value="">— all —</option>
        <option value="draft" ${state.status==='draft'?'selected':''}>draft</option>
        <option value="published" ${state.status==='published'?'selected':''}>published</option>
        <option value="archived" ${state.status==='archived'?'selected':''}>archived</option>
        <option value="flagged" ${state.status==='flagged'?'selected':''}>flagged</option>
      </select>
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('slug'))}</th><th>${esc(t('owner'))}</th><th>${esc(t('created'))}</th>
        <th>${esc(t('published'))}</th><th>${esc(t('views'))}</th><th>${esc(t('rsvps'))}</th>
        <th>${esc(t('status'))}</th><th>${esc(t('actions'))}</th>
      </tr></thead><tbody>${rows || `<tr><td colspan="8">${esc(t('noInvitations'))}</td></tr>`}</tbody></table>`;
    const search = document.getElementById('invitationsSearch');
    if (search) search.addEventListener('input', e => { state.q = e.target.value; load().then(render).catch(()=>{}); });
    const filter = document.getElementById('invitationsStatusFilter');
    if (filter) filter.addEventListener('change', e => { state.status = e.target.value; load().then(render).catch(()=>{}); });
    host.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => handleAction(btn)));
  }

  async function handleAction(btn){
    const row = btn.closest('[data-invite-id]');
    const inviteId = row && row.dataset.inviteId;
    const action = btn.dataset.action;
    if (!inviteId || !action) return;
    const api = shell().api;
    try {
      if (action === 'unpublish') {
        if (!confirm(t('confirmUnpublish'))) return;
        await api.send(`/api/admin/invitations/${encodeURIComponent(inviteId)}/unpublish`, 'POST', {});
      } else if (action === 'flag') {
        const reason = window.prompt(t('flagReason'), '') || '';
        if (!confirm(t('confirmFlag'))) return;
        await api.send(`/api/admin/invitations/${encodeURIComponent(inviteId)}/flag`, 'POST', { reason });
      } else if (action === 'transfer') {
        const newOwnerId = window.prompt(t('transferPrompt'), '');
        if (!newOwnerId) return;
        await api.send(`/api/admin/invitations/${encodeURIComponent(inviteId)}/transfer`, 'POST', { newOwnerId });
      }
      await load(); render();
    } catch(e) { alert(e.message || 'Action failed'); }
  }

  async function mount(){ try { await load(); } catch(e) {} render(); }
  window.EInviteAdminInvitations = Object.freeze({ version: 64, mount, render, load });
})();
