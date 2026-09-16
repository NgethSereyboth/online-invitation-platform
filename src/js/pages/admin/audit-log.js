/* v0.65.0 — audit log explorer (ROADMAP §5.5)
 * Read-only search + filters + CSV export. Audit table is immutable.
 */
(function(){
  'use strict';
  if (window.EInviteAdminAuditLog && window.EInviteAdminAuditLog.version >= 65) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Audit log', search:'Filter by user, action, target', user:'User', action:'Action', targetType:'Target type', targetId:'Target id', ip:'IP', adminOnly:'Admin only', since:'Since (ms)', until:'Until (ms)', exportCsv:'Export CSV', loadMore:'Load more', noEvents:'No audit events match the filters.', timestamp:'Timestamp', metadata:'Metadata', expand:'Expand', immutable:'The audit log is immutable — this view is read-only.' },
    km: { title:'កំណត់ហេតុសវនកម្ម', search:'តម្រងតាមអ្នកប្រើ សកម្មភាព គោលដៅ', user:'អ្នកប្រើ', action:'សកម្មភាព', targetType:'ប្រភេទគោលដៅ', targetId:'លេខសម្គាល់គោលដៅ', ip:'IP', adminOnly:'អ្នកគ្រប់គ្រងប៉ុណ្ណោះ', since:'ចាប់ពី (ms)', until:'រហូតដល់ (ms)', exportCsv:'នាំចេញ CSV', loadMore:'ផ្ទុកបន្ថែម', noEvents:'មិនមានព្រឹត្តិការណ៍សវនកម្មត្រូវគ្នាទេ។', timestamp:'ពេលវេលា', metadata:'ទិន្នន័យមេតា', expand:'ពង្រីក', immutable:'កំណត់ហេតុសវនកម្មមិនអាចកែប្រែបាន — ទិដ្ឋភាពនេះគ្រាន់តែអាន។' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { items: [], nextCursor: null, hasMore: false, filters: {} };

  async function load(append=false){
    const api = shell().api;
    const params = new URLSearchParams({ limit: '50' });
    Object.entries(state.filters).forEach(([k,v]) => { if (v) params.set(k, v); });
    if (append && state.nextCursor) params.set('cursor', String(state.nextCursor));
    const data = await api.get(`/api/admin/audit-events?${params}`);
    state.items = append ? state.items.concat(data.items || []) : (data.items || []);
    state.nextCursor = data.nextCursor;
    state.hasMore = !!data.hasMore;
  }

  function render(){
    const host = document.getElementById('auditLogPanel');
    if (!host) return;
    const rows = state.items.map(ev => `
      <tr data-event-id="${esc(ev.id)}">
        <td>${ev.createdAt ? new Date(ev.createdAt).toISOString() : '—'}</td>
        <td>${esc(ev.userId || '—')}</td>
        <td><code>${esc(ev.action)}</code></td>
        <td>${esc(ev.targetType || '')}<br><small>${esc(ev.targetId || '')}</small></td>
        <td>${esc(ev.ip || '')}</td>
        <td><details><summary>${esc(t('expand'))}</summary><pre>${esc(JSON.stringify(ev.metadata || {}, null, 2))}</pre></details></td>
      </tr>`).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p class="ei-help">${esc(t('immutable'))}</p>
      <div class="ei-audit-filters">
        <input type="text" placeholder="${esc(t('user'))}" data-filter="user" value="${esc(state.filters.user || '')}">
        <input type="text" placeholder="${esc(t('action'))}" data-filter="action" value="${esc(state.filters.action || '')}">
        <input type="text" placeholder="${esc(t('targetType'))}" data-filter="targetType" value="${esc(state.filters.targetType || '')}">
        <input type="text" placeholder="${esc(t('ip'))}" data-filter="ip" value="${esc(state.filters.ip || '')}">
        <label><input type="checkbox" data-filter="adminOnly" ${state.filters.adminOnly ? 'checked' : ''}> ${esc(t('adminOnly'))}</label>
      </div>
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('timestamp'))}</th><th>${esc(t('user'))}</th><th>${esc(t('action'))}</th>
        <th>${esc(t('targetType'))} / ${esc(t('targetId'))}</th><th>${esc(t('ip'))}</th><th>${esc(t('metadata'))}</th>
      </tr></thead><tbody>${rows || `<tr><td colspan="6">${esc(t('noEvents'))}</td></tr>`}</tbody></table>
      <div class="ei-pagination">
        <button id="auditExport" disabled>${esc(t('exportCsv'))}</button>
        <button id="auditLoadMore" ${state.hasMore ? '' : 'disabled'}>${esc(t('loadMore'))}</button>
      </div>`;
    host.querySelectorAll('[data-filter]').forEach(inp => inp.addEventListener('change', e => {
      const key = e.target.dataset.filter;
      state.filters[key] = e.target.type === 'checkbox' ? (e.target.checked ? '1' : '') : e.target.value;
      load().then(render).catch(()=>{});
    }));
    const exportBtn = document.getElementById('auditExport');
    if (exportBtn) {
      exportBtn.disabled = false;
      exportBtn.addEventListener('click', () => {
        const params = new URLSearchParams(Object.entries(state.filters).filter(([_,v]) => v).reduce((a,[k,v])=>{a[k]=v;return a;},{}));
        params.set('format', 'csv');
        window.open(`/api/admin/audit-events?${params}`, '_blank');
      });
    }
    const moreBtn = document.getElementById('auditLoadMore');
    if (moreBtn) moreBtn.addEventListener('click', () => { load(true).then(render).catch(()=>{}); });
  }

  async function mount(){ try { await load(); } catch(e) {} render(); }
  window.EInviteAdminAuditLog = Object.freeze({ version: 65, mount, render, load });
})();
