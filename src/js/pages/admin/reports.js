/* v0.66.0 — reports queue (ROADMAP §5.9)
 * Users can report abusive invitations/users. Admins see a queue and resolve.
 */
(function(){
  'use strict';
  if (window.EInviteAdminReports && window.EInviteAdminReports.version >= 66) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Reports queue', description:'Users can report abusive invitations or users. Resolve each report with an audit-logged action.', noReports:'No reports in this view.', reporterId:'Reporter', target:'Target', reason:'Reason', body:'Body', status:'Status', createdAt:'Created', resolve:'Resolve', resolutionNote:'Resolution note', statusOpen:'open', statusInvestigating:'investigating', statusActioned:'resolved (actioned)', statusNoAction:'resolved (no action)', statusDuplicate:'duplicate', loadMore:'Load more', submitTestReport:'Submit a test report', targetTypeInvitation:'invitation', targetTypeUser:'user', reasonSpam:'spam', reasonHarassment:'harassment', reasonImpersonation:'impersonation', reasonIllegal:'illegal content', reasonOther:'other', targetId:'Target id' },
    km: { title:'ជួររាយការណ៍', description:'អ្នកប្រើអាចរាយការណ៍អំពីការអញ្ជើញឬអ្នកប្រើបំពាន។ ដោះស្រាយរាយការណ៍នីមួយៗជាមួយសកម្មភាពដែលបានកត់ត្រាសវនកម្ម។', noReports:'មិនមានរាយការណ៍ក្នុងទិដ្ឋភាពនេះ។', reporterId:'អ្នករាយការណ៍', target:'គោលដៅ', reason:'មូលហេតុ', body:'ខ្លឹងសារ', status:'ស្ថានភាព', createdAt:'បង្កើត', resolve:'ដោះស្រាយ', resolutionNote:'កំណត់ត្រាដោះស្រាយ', statusOpen:'បើក', statusInvestigating:'កំពុងពិនិត្យ', statusActioned:'ដោះស្រាយ (បានអនុវត្ត)', statusNoAction:'ដោះស្រាយ (មិនអនុវត្ត)', statusDuplicate:'ស្ទួន', loadMore:'ផ្ទុកបន្ថែម', submitTestReport:'ដាក់ស្នើរាយការណ៍សាកល្បង', targetTypeInvitation:'ការអញ្ជើញ', targetTypeUser:'អ្នកប្រើ', reasonSpam:'ស្ពាម', reasonHarassment:'ការបំពាន', reasonImpersonation:'ការបន្លំ', reasonIllegal:'មាតិកាមិនស្របច្បាប់', reasonOther:'ផ្សេងទៀត', targetId:'លេខសម្គាល់គោលដៅ' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { items: [], nextCursor: null, hasMore: false, statusFilter: '' };

  async function load(append=false){
    const api = shell().api;
    const params = new URLSearchParams({ limit: '50' });
    if (state.statusFilter) params.set('status', state.statusFilter);
    if (append && state.nextCursor) params.set('cursor', String(state.nextCursor));
    const data = await api.get(`/api/admin/reports?${params}`);
    state.items = append ? state.items.concat(data.items || []) : (data.items || []);
    state.nextCursor = data.nextCursor;
    state.hasMore = !!data.nextCursor;
  }

  const STATUS_LABELS = { open: 'statusOpen', investigating: 'statusInvestigating', resolved_actioned: 'statusActioned', resolved_no_action: 'statusNoAction', duplicate: 'statusDuplicate' };

  function render(){
    const host = document.getElementById('reportsPanel');
    if (!host) return;
    const rows = state.items.map(r => `
      <tr data-report-id="${esc(r.id)}">
        <td>${r.createdAt ? new Date(r.createdAt).toLocaleString() : '—'}</td>
        <td><code>${esc(r.reporterId)}</code></td>
        <td>${esc(r.targetType)}<br><small>${esc(r.targetId)}</small></td>
        <td>${esc(r.reason)}<br><small>${esc(r.body || '')}</small></td>
        <td><span class="ei-tag">${esc(t(STATUS_LABELS[r.status] || r.status))}</span></td>
        <td><button data-action="resolve">${esc(t('resolve'))}</button></td>
      </tr>`).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p>${esc(t('description'))}</p>
      <select id="reportsStatusFilter">
        <option value="">— all —</option>
        <option value="open" ${state.statusFilter==='open'?'selected':''}>${esc(t('statusOpen'))}</option>
        <option value="investigating" ${state.statusFilter==='investigating'?'selected':''}>${esc(t('statusInvestigating'))}</option>
        <option value="resolved_actioned" ${state.statusFilter==='resolved_actioned'?'selected':''}>${esc(t('statusActioned'))}</option>
        <option value="resolved_no_action" ${state.statusFilter==='resolved_no_action'?'selected':''}>${esc(t('statusNoAction'))}</option>
        <option value="duplicate" ${state.statusFilter==='duplicate'?'selected':''}>${esc(t('statusDuplicate'))}</option>
      </select>
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('createdAt'))}</th><th>${esc(t('reporterId'))}</th><th>${esc(t('target'))}</th>
        <th>${esc(t('reason'))} / ${esc(t('body'))}</th><th>${esc(t('status'))}</th><th></th>
      </tr></thead><tbody>${rows || `<tr><td colspan="6">${esc(t('noReports'))}</td></tr>`}</tbody></table>
      <div class="ei-pagination"><button id="reportsLoadMore" ${state.hasMore ? '' : 'disabled'}>${esc(t('loadMore'))}</button></div>`;
    const filter = document.getElementById('reportsStatusFilter');
    if (filter) filter.addEventListener('change', e => { state.statusFilter = e.target.value; load().then(render).catch(()=>{}); });
    const more = document.getElementById('reportsLoadMore');
    if (more) more.addEventListener('click', () => { load(true).then(render).catch(()=>{}); });
    host.querySelectorAll('[data-action="resolve"]').forEach(btn => btn.addEventListener('click', () => handleResolve(btn)));
  }

  async function handleResolve(btn){
    const row = btn.closest('[data-report-id]');
    const reportId = row && row.dataset.reportId;
    if (!reportId) return;
    const status = window.prompt(`New status (open | investigating | resolved_actioned | resolved_no_action | duplicate):`, 'resolved_actioned');
    if (!status) return;
    const note = window.prompt(t('resolutionNote'), '') || '';
    const api = shell().api;
    try { await api.send(`/api/admin/reports/${encodeURIComponent(reportId)}`, 'PUT', { status, resolutionNote: note }); }
    catch(e) { alert(e.message || 'Resolve failed'); }
    await load(); render();
  }

  async function mount(){ try { await load(); } catch(e) {} render(); }
  window.EInviteAdminReports = Object.freeze({ version: 66, mount, render, load });
})();
