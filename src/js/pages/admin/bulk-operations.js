/* v0.65.2 — bulk operations (ROADMAP §5.7)
 * Super-admin bulk email / bulk suspend / bulk export / bulk prune.
 * All run as background jobs via the existing JobQueue. Confirmation modal
 * requires typing CONFIRM. Bulk email rate-limited to 100/min.
 */
(function(){
  'use strict';
  if (window.EInviteAdminBulkOps && window.EInviteAdminBulkOps.version >= 65) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'Bulk operations', danger:'These actions are irreversible. Each operation runs as a background job.', confirm:'Type CONFIRM to proceed', cancel:'Cancel', run:'Run', bulkEmail:'Bulk email', bulkSuspend:'Bulk suspend', bulkExport:'Bulk export', bulkPrune:'Bulk prune', subject:'Subject', body:'Body', userIds:'User IDs (comma-separated)', reason:'Reason', what:'What', format:'Format', days:'Days', jobStarted:'Job started', jobId:'Job id', status:'Status', refresh:'Refresh jobs', requireSuperAdmin:'Super-admin access required.', jobsTrackedBelow:'Recently enqueued jobs are listed below; use the job id to track progress.' },
    km: { title:'ប្រតិបត្តិការច្រើន', danger:'សកម្មភាពទាំងនេះមិនអាចបញ្ច្រាសបានទេ។ ប្រតិបត្តិការនីមួយៗដំណើរការជាការងារផ្ទៃខាងក្រោយ។', confirm:'វាយ CONFIRM ដើម្បីបន្ត', cancel:'បោះបង់', run:'ដំណើរការ', bulkEmail:'អ៊ីមែលច្រើន', bulkSuspend:'ផ្អាកច្រើន', bulkExport:'នាំចេញច្រើន', bulkPrune:'កាត់ច្រើន', subject:'ប្រធានបទ', body:'ខ្លឹងសារ', userIds:'លេខសម្គាល់អ្នកប្រើ (ផ្ដាច់ដោយក្បៀស)', reason:'មូលហេតុ', what:'អ្វី', format:'ទម្រង់', days:'ថ្ងៃ', jobStarted:'ការងារបានចាប់ផ្ដើម', jobId:'លេខសម្គាល់ការងារ', status:'ស្ថានភាព', refresh:'ធ្វើបច្ចុប្បន្នភាព', requireSuperAdmin:'ត្រូវការ super-admin។', jobsTrackedBelow:'ការងារដែលបានដាក់បញ្ជូនថ្មីៗបង្ហាញខាងក្រោម; ប្រើលេខសម្គាល់ការងារដើម្បីតាមដាន។' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { jobs: [] };

  function confirmDialog(message, fields=[]){
    return new Promise((resolve, reject) => {
      const dlg = document.createElement('dialog');
      dlg.className = 'ei-dialog';
      const fieldHtml = fields.map(f => `<label>${esc(f.label)}<input type="${f.type || 'text'}" name="${esc(f.name)}" ${f.value ? `value="${esc(f.value)}"` : ''}></label>`).join('');
      dlg.innerHTML = `<form method="dialog" class="ei-dialog-card">
        <h2>${esc(t('confirm'))}</h2>
        <p>${esc(message)}</p>
        ${fieldHtml}
        <input type="text" name="__confirm" placeholder="${esc(t('confirm'))}" autocomplete="off">
        <div class="ei-dialog-actions">
          <button type="button" data-cancel>${esc(t('cancel'))}</button>
          <button type="submit" value="ok">${esc(t('run'))}</button>
        </div></form>`;
      document.body.append(dlg);
      dlg.showModal();
      dlg.querySelector('[data-cancel]').addEventListener('click', () => { dlg.close(); resolve(null); });
      dlg.addEventListener('close', () => {
        if (dlg.returnValue !== 'ok') { dlg.remove(); resolve(null); return; }
        const fd = new FormData(dlg.querySelector('form'));
        if (fd.get('__confirm') !== 'CONFIRM') { dlg.remove(); resolve(null); return; }
        const out = {};
        for (const f of fields) out[f.name] = fd.get(f.name);
        dlg.remove();
        resolve(out);
      });
    });
  }

  async function trackJob(jobId){
    state.jobs.unshift({ jobId, status: 'queued' });
    if (state.jobs.length > 10) state.jobs.length = 10;
    pollJob(jobId);
    render();
  }

  async function pollJob(jobId){
    const api = shell().api;
    try {
      const data = await api.get(`/api/admin/jobs/${encodeURIComponent(jobId)}`);
      const existing = state.jobs.find(j => j.jobId === jobId);
      if (existing) { existing.status = data.state; existing.kind = data.kind; existing.updatedAt = data.updatedAt; }
      render();
    } catch(e) { /* swallow */ }
  }

  function render(){
    const host = document.getElementById('bulkOpsPanel');
    if (!host) return;
    const jobRows = state.jobs.map(j => `<tr><td><code>${esc(j.jobId)}</code></td><td>${esc(j.kind || '—')}</td><td>${esc(j.status || '—')}</td></tr>`).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p class="ei-help">${esc(t('danger'))}</p>
      <p class="ei-help">${esc(t('requireSuperAdmin'))}</p>
      <div class="ei-bulk-actions">
        <button data-bulk="email">${esc(t('bulkEmail'))}</button>
        <button data-bulk="suspend">${esc(t('bulkSuspend'))}</button>
        <button data-bulk="export">${esc(t('bulkExport'))}</button>
        <button data-bulk="prune">${esc(t('bulkPrune'))}</button>
      </div>
      <p class="ei-help">${esc(t('jobsTrackedBelow'))}</p>
      <table class="ei-admin-table"><thead><tr><th>${esc(t('jobId'))}</th><th>Kind</th><th>${esc(t('status'))}</th></tr></thead><tbody>${jobRows || `<tr><td colspan="3">—</td></tr>`}</tbody></table>`;
    host.querySelectorAll('[data-bulk]').forEach(btn => btn.addEventListener('click', () => handleBulk(btn.dataset.bulk)));
  }

  async function handleBulk(kind){
    const api = shell().api;
    try {
      if (kind === 'email') {
        const f = await confirmDialog(t('bulkEmail'), [
          { name: 'subject', label: t('subject') },
          { name: 'body', label: t('body'), type: 'textarea' },
          { name: 'total', label: 'Total recipients', type: 'number', value: '0' },
        ]);
        if (!f) return;
        const res = await api.send('/api/admin/bulk-email', 'POST', { subject: f.subject, body: f.body, total: parseInt(f.total, 10) || 0 });
        await trackJob(res.jobId);
      } else if (kind === 'suspend') {
        const f = await confirmDialog(t('bulkSuspend'), [
          { name: 'userIds', label: t('userIds') },
          { name: 'reason', label: t('reason') },
        ]);
        if (!f) return;
        const ids = (f.userIds || '').split(',').map(s => s.trim()).filter(Boolean);
        const res = await api.send('/api/admin/bulk-suspend', 'POST', { userIds: ids, reason: f.reason });
        await trackJob(res.jobId);
      } else if (kind === 'export') {
        const f = await confirmDialog(t('bulkExport'), [
          { name: 'what', label: t('what'), value: 'users' },
          { name: 'format', label: t('format'), value: 'csv' },
        ]);
        if (!f) return;
        const res = await api.send('/api/admin/bulk-export', 'POST', { what: f.what, format: f.format });
        await trackJob(res.jobId);
      } else if (kind === 'prune') {
        const f = await confirmDialog(t('bulkPrune'), [
          { name: 'what', label: t('what'), value: 'audit_events' },
          { name: 'days', label: t('days'), value: '730', type: 'number' },
        ]);
        if (!f) return;
        const res = await api.send('/api/admin/bulk-prune', 'POST', { what: f.what, days: parseInt(f.days, 10) || 730 });
        await trackJob(res.jobId);
      }
    } catch(e) { alert(e.message || 'Bulk op failed'); }
  }

  async function mount(){ render(); }
  window.EInviteAdminBulkOps = Object.freeze({ version: 65, mount, render, trackJob });
})();
