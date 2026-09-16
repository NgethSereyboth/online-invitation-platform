;(()=>{
'use strict';
const ensureStack=()=>{let stack=document.querySelector('.ei-toast-stack');if(!stack){stack=document.createElement('div');stack.className='ei-toast-stack';stack.setAttribute('aria-live','polite');document.body.append(stack)}return stack};
function toast(message,options={}){
  const text=String(message??'');if(!text)return;
  const stack=ensureStack(),item=document.createElement('div');item.className=`ei-toast ${options.type||''}`.trim();
  const icon=options.icon||(options.type==='error'?'!':options.type==='success'?'✓':'✦');
  item.innerHTML=`<span class="ei-toast-icon"></span><strong></strong><button type="button" aria-label="Dismiss">×</button>`;
  item.querySelector('.ei-toast-icon').textContent=icon;item.querySelector('strong').textContent=text;
  const close=()=>{if(item.classList.contains('out'))return;item.classList.add('out');setTimeout(()=>item.remove(),190)};item.querySelector('button').onclick=close;stack.append(item);setTimeout(close,Math.max(1500,Number(options.duration||3600)));return item
}
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label>Value</label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('.ei-dialog-message').textContent=message;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input');host.hidden=false;field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';host.append(field)}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel'});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};
})();;const $=s=>document.querySelector(s);localStorage.removeItem('sovan-auth-token');let state={users:[],templates:[],invitations:[],ai:{providers:[],modelRoles:{},modelDirectory:{}},tab:'users'};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,options={}){const r=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data}
function matches(...values){const q=$('#adminSearch').value.trim().toLowerCase();return !q||values.join(' ').toLowerCase().includes(q)}
function renderUsers(){const items=state.users.filter(u=>matches(u.email,u.role,u.plan,u.uploadEnabled?'uploads allowed':'uploads disabled'));$('#usersPanel').innerHTML=items.map(u=>`<article class="admin-row" data-user="${esc(u.id)}"><div><h3>${esc(u.email)}</h3><small>${new Date(u.createdAt).toLocaleDateString()}</small></div><span>${u.invitationCount} invitations</span><span>${u.templateCount} templates</span><select data-role title="Account role"><option value="customer" ${u.role==='customer'?'selected':''}>Customer</option><option value="designer" ${u.role==='designer'?'selected':''}>Designer</option><option value="admin" ${u.role==='admin'?'selected':''}>Administrator</option></select><select data-plan title="Account plan"><option value="free" ${u.plan==='free'?'selected':''}>Free</option><option value="creator" ${u.plan==='creator'?'selected':''}>Creator</option><option value="studio" ${u.plan==='studio'?'selected':''}>Studio</option></select><label class="admin-upload-toggle"><input type="checkbox" data-upload-enabled ${u.uploadEnabled?'checked':''}> Allow uploads</label><div><button data-save-role>Save role</button> <button data-save-plan>Save plan</button> <button data-save-uploads>Save uploads</button></div></article>`).join('')||'<p>No users found.</p>';document.querySelectorAll('[data-save-role]').forEach(b=>b.onclick=()=>saveRole(b.closest('[data-user]')));document.querySelectorAll('[data-save-plan]').forEach(b=>b.onclick=()=>savePlan(b.closest('[data-user]')));document.querySelectorAll('[data-save-uploads]').forEach(b=>b.onclick=()=>saveUploads(b.closest('[data-user]')))}
function renderTemplates(){const items=state.templates.filter(t=>matches(t.name,t.category,t.ownerEmail,t.visibility));$('#templatesPanel').innerHTML=items.map(t=>`<article class="admin-row" data-template="${esc(t.id)}"><div><h3>${esc(t.name)}</h3><small>${esc(t.ownerEmail)} · v${t.currentVersion}</small></div><span>${esc(t.category)}</span><span>${t.visibility==='public'?'Marketplace':'Private'}</span><select data-visibility><option value="private" ${t.visibility!=='public'?'selected':''}>Private</option><option value="public" ${t.visibility==='public'?'selected':''}>Marketplace</option></select><button data-save-template>Save</button></article>`).join('')||'<p>No templates found.</p>';document.querySelectorAll('[data-save-template]').forEach(b=>b.onclick=()=>saveTemplate(b.closest('[data-template]')))}
function renderInvitations(){const items=state.invitations.filter(i=>matches(i.title,i.slug,i.ownerEmail,i.accessMode));$('#invitationsPanel').innerHTML=items.map(i=>`<article class="admin-row" data-invite="${esc(i.id)}"><div><h3>${esc(i.title)}</h3><small>${esc(i.ownerEmail||'Unknown owner')} · /i/${esc(i.slug)}</small></div><span>${i.views} views</span><span>${esc(i.accessMode)}</span><span>${i.published?'Published':'Offline'}</span><button data-toggle-published>${i.published?'Unpublish':'Republish'}</button></article>`).join('')||'<p>No invitations found.</p>';document.querySelectorAll('[data-toggle-published]').forEach(b=>b.onclick=()=>toggleInvitation(b.closest('[data-invite]')))}
function renderAI(){
 const host=$('#aiPanel'),ai=state.ai||{},providers=(ai.providers||[]).filter(p=>matches(p.label,p.id,p.kind,p.endpointLabel,p.healthy?'healthy':'unavailable'));
 const roles=Object.entries(ai.modelRoles||{}).map(([role,value])=>`<span><b>${esc(role)}</b>: ${esc(value.selection||'not selected')} · ${value.available?'available':'unavailable'}</span>`).join(' · ');
 const directory=ai.modelDirectory||{},directoryText=!directory.configured?'not configured':directory.available?`${(directory.files||[]).length} compatible file(s) discovered; runtime registration still required.`:'configured but unavailable';
 const cards=providers.map(provider=>{const modelLines=(provider.models||[]).slice(0,30).map(model=>{const context=model.contextLength?` · context ${esc(model.contextLength)}`:'';return `<small><b>${esc(model.name||model.id)}</b> · ${esc(model.type||'text')} · tools ${model.toolCalling?'yes':'no'} · vision ${model.vision?'yes':'no'} · structured ${model.structuredOutput?'yes':'no'}${context}</small>`}).join('<br>')||'<small>No models discovered.</small>';return `<article class="admin-row"><div><h3>${esc(provider.label||provider.id)}</h3><small>${esc(provider.endpointLabel||'Server configured')} · ${esc(provider.kind||'local')}</small></div><span>${provider.healthy?'Healthy':'Unavailable'}</span><span>${(provider.models||[]).length} models</span><span>Checked ${provider.checkedAt?new Date(provider.checkedAt).toLocaleString():'—'}</span><div>${modelLines}</div></article>`}).join('');
 host.innerHTML=`<div class="provider-note"><b>Model routing</b><p>${roles||'No local model roles selected.'}</p><p>Local model directory: ${directoryText}</p></div>${cards||'<p>No local AI providers are enabled. Configure them with server environment variables; browser users cannot set arbitrary endpoints.</p>'}`;
}
function render(){renderUsers();renderTemplates();renderInvitations();renderAI()}
async function saveRole(row){try{const id=row.dataset.user,role=row.querySelector('[data-role]').value;await api(`/api/admin/users/${id}/role`,{method:'PUT',body:JSON.stringify({role})});const item=state.users.find(x=>x.id===id);if(item)item.role=role;renderUsers()}catch(e){alert(e.message)}}
async function savePlan(row){try{const id=row.dataset.user,plan=row.querySelector('[data-plan]').value;await api(`/api/admin/users/${id}/plan`,{method:'PUT',body:JSON.stringify({plan})});const item=state.users.find(x=>x.id===id);if(item)item.plan=plan;renderUsers()}catch(e){alert(e.message)}}
async function saveUploads(row){try{const id=row.dataset.user,enabled=row.querySelector('[data-upload-enabled]').checked;const result=await api(`/api/admin/users/${id}/uploads`,{method:'PUT',body:JSON.stringify({enabled})});const item=state.users.find(x=>x.id===id);if(item)item.uploadEnabled=result.uploadEnabled;renderUsers()}catch(e){alert(e.message)}}
async function saveTemplate(row){try{const id=row.dataset.template,visibility=row.querySelector('[data-visibility]').value;await api(`/api/admin/templates/${id}/visibility`,{method:'PUT',body:JSON.stringify({visibility})});const item=state.templates.find(x=>x.id===id);if(item)item.visibility=visibility;renderTemplates()}catch(e){alert(e.message)}}
async function toggleInvitation(row){try{const id=row.dataset.invite,item=state.invitations.find(x=>x.id===id),published=!item.published;await api(`/api/admin/invitations/${id}/published`,{method:'PUT',body:JSON.stringify({published})});item.published=published;renderInvitations()}catch(e){alert(e.message)}}
document.querySelectorAll('[data-admin-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.adminTab;document.querySelectorAll('[data-admin-tab]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.admin-panel').forEach(x=>x.classList.remove('active'));$(`#${state.tab}Panel`).classList.add('active')});$('#adminSearch').oninput=render;
async function init(){try{const me=await api('/api/auth/me');if(me.user?.role!=='admin')throw Error('Administrator access required');const [overview,users,templates,invitations,ai]=await Promise.all([api('/api/admin/overview'),api('/api/admin/users'),api('/api/admin/templates'),api('/api/admin/invitations'),api('/api/admin/ai/providers')]);state={...state,users,templates,invitations,ai};$('#adminMetrics').innerHTML=Object.entries(overview).map(([key,value])=>`<div class="admin-metric"><strong>${value}</strong>${esc(key.replace(/([A-Z])/g,' $1').replace(/^./,x=>x.toUpperCase()))}</div>`).join('');render()}catch(e){document.querySelector('.admin-page').innerHTML=`<h1>Administration unavailable</h1><p>${esc(e.message)}</p><a href="dashboard.html" class="button-link">Back to dashboard</a>`}}
init();;/* v0.64.0 — admin shell (ROADMAP-v0.54-to-v1.0 §5.1)
 *
 * Orchestrates the admin page: stat cards grid + system status banner +
 * tab navigation between the 9 admin modules. Polls /api/admin/metrics-v2
 * + /api/admin/system-status every 30s.
 *
 * Replaces the legacy admin.js (kept for backward-compat with the old
 * users/templates/invitations/ai panels — the new modules layer on top).
 */
(function(){
  'use strict';
  if (window.EInviteAdminShell && window.EInviteAdminShell.version >= 64) return;

  const STRINGS = {
    en: {
      title:'Administration',
      loading:'Loading…',
      noData:'No data yet.',
      masked:'masked',
      polling:'Polling every 30s',
      suspended:'Suspended',
      active:'Active',
      notAvailable:'n/a',
      refresh:'Refresh now',
      error:'Failed to load admin data',
      unauthorized:'Administrator access required',
    },
    km: {
      title:'ការគ្រប់គ្រង',
      loading:'កំពុងផ្ទុក…',
      noData:'មិនមានទិន្នន័យនៅឡើយ។',
      masked:'បិទបាំង',
      polling:'ធ្វើបច្ចុប្បន្នភាពរៀងរាល់ ៣០ វិនាទី',
      suspended:'បានផ្អាក',
      active:'សកម្ម',
      notAvailable:'គ្មាន',
      refresh:'ធ្វើបច្ចុប្បន្នភាព',
      error:'បរាជ័យក្នុងការផ្ទុកទិន្នន័យអ្នកគ្រប់គ្រង',
      unauthorized:'ត្រូវការសិទ្ធិអ្នកគ្រប់គ្រង',
    }
  };

  function locale(){ return (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; }
  function t(key){ const l = locale(); return (STRINGS[l] && STRINGS[l][key]) || STRINGS.en[key] || key; }
  function esc(v){ return String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function formatNumber(n){
    if (n == null) return '—';
    try { return new Intl.NumberFormat(locale()==='km' ? 'en-US' : 'en-US').format(n); }
    catch(e){ return String(n); }
  }
  function formatBytes(b){
    if (!b) return '0 B';
    const units = ['B','KB','MB','GB','TB'];
    let i=0; let v=b;
    while (v >= 1024 && i < units.length-1){ v/=1024; i++; }
    return `${v.toFixed(i===0?0:1)} ${units[i]}`;
  }
  function formatDelta(card){
    if (card.delta7d == null) return '';
    const sign = card.delta7d > 0 ? '+' : '';
    return `<small class="ei-stat-card-delta">7d: ${sign}${formatNumber(card.delta7d)}</small>`;
  }

  const api = window.EInviteAdminAPI || {
    async get(path){
      const r = await fetch(path, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
      if (!r.ok) {
        if (r.status === 401 || r.status === 403) throw new Error(t('unauthorized'));
        throw new Error(`${r.status} ${r.statusText}`);
      }
      const ct = r.headers.get('Content-Type') || '';
      if (ct.includes('application/json')) return r.json();
      return r.text();
    },
    async send(path, method, body){
      const r = await fetch(path, {
        method, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: body == null ? undefined : JSON.stringify(body),
      });
      let data;
      try { data = await r.json(); } catch(e){ data = {}; }
      if (!r.ok) throw new Error(data.error || `${r.status} ${r.statusText}`);
      return data;
    },
  };

  function renderStatCards(payload){
    const host = document.getElementById('statCardsGrid');
    if (!host || !payload || !payload.cards) return;
    host.innerHTML = payload.cards.map(card => {
      const valueDisplay = card.unit === 'bytes' ? formatBytes(card.value)
                         : card.unit === 'ms' ? `${formatNumber(card.value)} ms`
                         : formatNumber(card.value);
      const totalDisplay = card.unit === 'bytes' && card.total ? ` / ${formatBytes(card.total)}` : '';
      const label = locale() === 'km' ? (card.label_km || card.label) : card.label;
      return `<div class="ei-stat-card" data-key="${esc(card.key)}">
        <span class="ei-stat-card-label">${esc(label)}</span>
        <strong class="ei-stat-card-value">${esc(valueDisplay)}${totalDisplay}</strong>
        ${formatDelta(card)}
      </div>`;
    }).join('');
  }

  function renderSystemStatus(payload){
    const banner = document.getElementById('systemStatusBanner');
    if (!banner) return;
    const level = (payload && payload.level) || 'green';
    banner.dataset.status = level;
    const text = (payload && payload.messages && payload.messages[0]) || t('noData');
    const el = banner.querySelector('[data-i18n="en"]');
    if (el) el.textContent = text;
    const km = banner.querySelector('[data-i18n="km"]');
    if (km) km.textContent = text;
  }

  function showImpersonationBanner(){
    // The server sets the `einvite_admin_origin` cookie when an admin
    // starts an impersonation session. We can't read it directly (HttpOnly),
    // so we rely on the session payload from /api/auth/me to surface
    // impersonation state — server returns `impersonating` if the cookie
    // is present. If absent, hide the banner.
    const banner = document.getElementById('impersonationBanner');
    if (!banner) return;
    api.get('/api/auth/me').then(me => {
      const u = me && me.user;
      if (u && u.impersonating) {
        banner.hidden = false;
        const emailEl = document.getElementById('impersonationEmail');
        if (emailEl) emailEl.textContent = u.email || '—';
      } else {
        banner.hidden = true;
      }
    }).catch(()=>{ banner.hidden = true; });
  }

  let pollTimer = null;
  async function pollOnce(){
    try {
      const [metrics, status] = await Promise.all([api.get('/api/admin/metrics-v2'), api.get('/api/admin/system-status')]);
      renderStatCards(metrics);
      renderSystemStatus(status);
    } catch(e) {
      // Don't spam the console on every poll; first failure clears the cards.
      const host = document.getElementById('statCardsGrid');
      if (host) host.innerHTML = `<p class="ei-error">${esc(e.message || t('error'))}</p>`;
    }
  }
  function startPolling(){
    if (pollTimer) return;
    pollTimer = setInterval(pollOnce, 30_000);
  }
  function stopPolling(){ if (pollTimer){ clearInterval(pollTimer); pollTimer = null; } }

  function initTabs(){
    const buttons = document.querySelectorAll('[data-admin-tab]');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.adminTab;
        buttons.forEach(b => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.admin-panel').forEach(p => p.classList.remove('active'));
        const panel = document.getElementById(`${tab === 'feature-flags' ? 'featureFlags'
                                              : tab === 'audit-log' ? 'auditLog'
                                              : tab === 'system-health' ? 'systemHealth'
                                              : tab === 'bulk-ops' ? 'bulkOps'
                                              : tab}Panel`);
        if (panel) panel.classList.add('active');
        // Lazy-mount each module on first show.
        mountModule(tab);
      });
    });
  }

  function mountModule(tab){
    const map = {
      'users':         () => window.EInviteAdminUsers,
      'invitations':   () => window.EInviteAdminInvitations,
      'feature-flags': () => window.EInviteAdminFeatureFlags,
      'audit-log':     () => window.EInviteAdminAuditLog,
      'system-health': () => window.EInviteAdminSystemHealth,
      'bulk-ops':      () => window.EInviteAdminBulkOps,
      'impersonate':   () => window.EInviteAdminImpersonate,
      'reports':       () => window.EInviteAdminReports,
    };
    const getter = map[tab];
    if (!getter) return;
    const mod = getter();
    if (mod && typeof mod.mount === 'function' && !mod._mounted) {
      mod._mounted = true;
      try { mod.mount(); } catch(e) { console.warn('[admin] module mount failed', tab, e); }
    }
  }

  async function init(){
    initTabs();
    showImpersonationBanner();
    await pollOnce();
    startPolling();
    // Lazy-mount the default tab (users).
    mountModule('users');
  }

  window.EInviteAdminShell = Object.freeze({
    version: 64,
    STRINGS,
    api,
    pollOnce,
    startPolling,
    stopPolling,
    formatNumber,
    formatBytes,
    renderStatCards,
    renderSystemStatus,
    showImpersonationBanner,
    init,
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();;/* v0.64.1 — users management (ROADMAP §5.2)
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
})();;/* v0.64.2 — invitations management (ROADMAP §5.3)
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
})();;/* v0.64.3 — feature flags (ROADMAP §5.4)
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
})();;/* v0.65.0 — audit log explorer (ROADMAP §5.5)
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
})();;/* v0.65.1 — system health & diagnostics (ROADMAP §5.6)
 * Per-subsystem status with "how to fix" hints. 60s server cache.
 */
(function(){
  'use strict';
  if (window.EInviteAdminSystemHealth && window.EInviteAdminSystemHealth.version >= 65) return;
  const shell = () => window.EInviteAdminShell || {};
  const esc = v => String(v==null?'':v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STRINGS = {
    en: { title:'System health', refresh:'Refresh', cached:'60s cache — values may be up to 60s old', ok:'OK', fail:'FAIL', warn:'WARN', howToFix:'How to fix', subsystem:'Subsystem', detail:'Detail', uptime:'Uptime', computedAt:'Computed at', loadFailed:'Failed to load health detail' },
    km: { title:'សុខភាពប្រព័ន្ធ', refresh:'ធ្វើបច្ចុប្បន្នភាព', cached:'ឃ្លាំងសម្ងាត់ ៦០ វិ — តម្លៃអាចចាស់រហូតដល់ ៦០ វិ', ok:'ល្អ', fail:'បរាជ័យ', warn:'ព្រមាន', howToFix:'របៀបជួសជុល', subsystem:'ប្រព័ន្ធរង', detail:'លម្អិត', uptime:'ពេលវេលាដំណើរការ', computedAt:'គណនានៅ', loadFailed:'បរាជ័យក្នុងការផ្ទុកសុខភាពលម្អិត' }
  };
  function t(k){ const l = (document.documentElement.lang || 'en').startsWith('km') ? 'km' : 'en'; return (STRINGS[l] && STRINGS[l][k]) || STRINGS.en[k] || k; }
  let state = { payload: null };

  async function load(){
    const api = shell().api;
    state.payload = await api.get('/api/admin/health-detail');
  }

  function render(){
    const host = document.getElementById('systemHealthPanel');
    if (!host) return;
    const p = state.payload || {};
    const checks = p.checks || {};
    const rows = Object.entries(checks).map(([name, c]) => {
      const ok = c.ok === true;
      const klass = ok ? 'ei-tag-ok' : (c.note ? 'ei-tag-warn' : 'ei-tag-fail');
      const status = ok ? t('ok') : (c.note ? t('warn') : t('fail'));
      const detail = c.note ? esc(c.note)
                    : c.error ? esc(c.error)
                    : Object.entries(c).filter(([k]) => !['ok','howToFix'].includes(k)).map(([k,v]) => `<small>${esc(k)}: ${esc(v)}</small>`).join(' ');
      const fix = c.howToFix ? `<details><summary>${esc(t('howToFix'))}</summary><p>${esc(c.howToFix)}</p></details>` : '';
      return `<tr>
        <td><strong>${esc(name)}</strong></td>
        <td><span class="ei-tag ${klass}">${status}</span></td>
        <td>${detail}</td>
        <td>${fix}</td>
      </tr>`;
    }).join('');
    host.innerHTML = `
      <h2>${esc(t('title'))}</h2>
      <p class="ei-help">${esc(t('cached'))}</p>
      <p><small>${esc(t('uptime'))}: ${esc(p.uptimeSeconds || 0)}s · ${esc(t('computedAt'))}: ${p.computedAt ? new Date(p.computedAt).toLocaleString() : '—'}</small></p>
      <button id="systemHealthRefresh">${esc(t('refresh'))}</button>
      <table class="ei-admin-table"><thead><tr>
        <th>${esc(t('subsystem'))}</th><th>${esc(t('ok'))}</th><th>${esc(t('detail'))}</th><th>${esc(t('howToFix'))}</th>
      </tr></thead><tbody>${rows || `<tr><td colspan="4">${esc(t('loadFailed'))}</td></tr>`}</tbody></table>`;
    const btn = document.getElementById('systemHealthRefresh');
    if (btn) btn.addEventListener('click', () => { load().then(render).catch(e => alert(e.message)); });
  }

  async function mount(){ try { await load(); } catch(e) {} render(); }
  window.EInviteAdminSystemHealth = Object.freeze({ version: 65, mount, render, load });
})();;/* v0.65.2 — bulk operations (ROADMAP §5.7)
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
})();;/* v0.65.3 — impersonation (ROADMAP §5.8)
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
})();;/* v0.66.0 — reports queue (ROADMAP §5.9)
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
})();;(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const html=document.documentElement, body=document.body;
body.classList.add('ui-boot');requestAnimationFrame(()=>requestAnimationFrame(()=>{body.classList.remove('ui-boot');body.classList.add('ui-ready')}));
function currentMode(){return localStorage.getItem('einvite-theme-mode')==='dark'?'dark':'light'}
function applyTheme(mode,announce=false){
  const resolved=mode==='dark'?'dark':'light';
  if(announce){html.classList.add('theme-transition');setTimeout(()=>html.classList.remove('theme-transition'),340)}
  html.dataset.theme=resolved;html.dataset.themeMode=mode;html.style.colorScheme=resolved;
  localStorage.setItem('einvite-theme-mode',mode);
  $$('.ui-theme-menu button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  const icon=$('.ui-theme-icon');if(icon)icon.textContent=resolved==='dark'?'☾':'☀';
  if(announce)toast(`${resolved[0].toUpperCase()+resolved.slice(1)} appearance`,'◐');
}
applyTheme(currentMode());
function installThemeControl(){
  const header=$('body:not(:has(.guest))>header');if(header&&$('.ui-theme',header))return;
  const wrap=document.createElement('div');wrap.className='ui-theme'+(header?'':' floating');
  wrap.innerHTML=`<button type="button" class="ui-theme-button" aria-label="Appearance" aria-haspopup="menu" aria-expanded="false" data-ui-tooltip="Appearance (Alt+T)"><span class="ui-theme-icon">◐</span></button><div class="ui-theme-menu" role="menu" hidden>
  <button type="button" data-mode="light"><span>☀</span><b>Light</b><span class="check">✓</span></button>
  <button type="button" data-mode="dark"><span>☾</span><b>Dark</b><span class="check">✓</span></button></div>`;
  if(header){const logout=$('#logoutBtn',header); if(logout)header.insertBefore(wrap,logout); else header.append(wrap)}else document.body.append(wrap);
  const trigger=$('.ui-theme-button',wrap),menu=$('.ui-theme-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  $$('[data-mode]',menu).forEach(b=>b.onclick=()=>{applyTheme(b.dataset.mode,true);menu.hidden=true;trigger.setAttribute('aria-expanded','false')});
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  applyTheme(currentMode());
}
installThemeControl();
window.EInviteThemeController=Object.freeze({currentMode,applyTheme,cycle(){const modes=['light','dark'],i=modes.indexOf(currentMode());const next=modes[(i+1)%2];applyTheme(next,true);return next}});
function installAppLauncher(){
  const header=$('body:not(:has(.guest))>header');if(!header||$('.ui-app-launcher',header))return;
  const brand=header.querySelector('strong');if(!brand)return;
  const wrap=document.createElement('div');wrap.className='ui-app-launcher';
  wrap.innerHTML=`<button type="button" class="ui-app-launcher-button" aria-label="Open workspace navigation" aria-expanded="false" data-ui-tooltip="Workspace navigation"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></button><div class="ui-app-launcher-menu" hidden><header><strong>Workspace</strong></header><div class="ui-app-grid">
  <a href="dashboard.html"><span>⌂</span><div><b>Dashboard</b><small>Your invitations</small></div></a>
  <a href="templates.html"><span>✦</span><div><b>Templates</b><small>Reusable designs</small></div></a>
  <a href="materials.html"><span>▣</span><div><b>Materials</b><small>Photos, audio & video</small></div></a>
  <a href="designer.html"><span>◇</span><div><b>Designer</b><small>Professional workspace</small></div></a>
  <a href="billing.html"><span>◎</span><div><b>Plans</b><small>Usage & limits</small></div></a>
  <a href="account.html"><span>◉</span><div><b>Account</b><small>Profile & security</small></div></a></div></div>`;
  brand.after(wrap);const trigger=$('.ui-app-launcher-button',wrap),menu=$('.ui-app-launcher-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
}
installAppLauncher();
const page=location.pathname.split('/').pop()||'dashboard.html';$$('body:not(:has(.guest))>header a').forEach(a=>{const href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];if(href===page)a.classList.add('ui-current')});
addEventListener('pointerdown',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;const r=b.getBoundingClientRect(),s=document.createElement('span');s.className='ui-ripple';const size=Math.max(r.width,r.height);s.style.width=s.style.height=size+'px';s.style.left=(e.clientX-r.left)+'px';s.style.top=(e.clientY-r.top)+'px';b.append(s);setTimeout(()=>s.remove(),560)},true);
const spotlightSelectors='.invite-card,.metric,.response-card,.wish-card,.usage-card,.plan,.studio-card,.material-card-page,.template-choice,.page-nav-card,.studio-quick-grid button,.page-builder-library button,.element-library button,.block-library button';
$$(spotlightSelectors).forEach(el=>{el.classList.add('ui-spotlight');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)})});
const stack=document.createElement('div');stack.className='ui-toast-stack';document.body.append(stack);
function toast(message,icon='✓'){const el=document.createElement('div');el.className='ui-toast';el.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),240)},2200)}
window.einviteToast=toast;
const tip=document.createElement('div');tip.className='ui-tooltip';document.body.append(tip);let tipTimer;
document.addEventListener('pointerover',e=>{const el=e.target.closest('[data-ui-tooltip],button[title]');if(!el)return;const txt=el.dataset.uiTooltip||el.getAttribute('title');if(!txt)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{const r=el.getBoundingClientRect();tip.textContent=txt;tip.style.left=Math.max(8,Math.min(innerWidth-200,r.left+r.width/2))+'px';tip.style.top=Math.max(8,r.bottom+8)+'px';tip.classList.add('show')},350)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-ui-tooltip],button[title]')){clearTimeout(tipTimer);tip.classList.remove('show')}});
if(body.classList.contains('studio-experience')){
  const main=$('body.studio-experience>main'),toolbar=$('.studio-canvas-toolbar');
  const canvasViewport=$('.canvas-viewport');
  canvasViewport?.addEventListener('pointermove',e=>{const r=canvasViewport.getBoundingClientRect();canvasViewport.style.setProperty('--canvas-pointer-x',`${e.clientX-r.left}px`);canvasViewport.style.setProperty('--canvas-pointer-y',`${e.clientY-r.top}px`)});
  let leftWidth=Math.max(300,Math.min(520,Number(localStorage.getItem('einvite-left-width'))||370)),rightWidth=Math.max(280,Math.min(460,Number(localStorage.getItem('einvite-right-width'))||330));
  function setWidths(){const available=Math.max(900,window.innerWidth||1440),stageMin=360;leftWidth=Math.max(290,Math.min(560,leftWidth,available-rightWidth-stageMin));rightWidth=Math.max(280,Math.min(520,rightWidth,available-leftWidth-stageMin));for(const target of [html,body]){target.style.setProperty('--studio-left-width',`${leftWidth}px`);target.style.setProperty('--einvite-left-width',`${leftWidth}px`);target.style.setProperty('--studio-right-width',`${rightWidth}px`);target.style.setProperty('--einvite-inspector-width',`${rightWidth}px`)}}setWidths();window.addEventListener('resize',setWidths);
  function addToggle(side,label,symbol){if(!toolbar)return;const b=document.createElement('button');b.type='button';b.className='studio-panel-toggle';b.innerHTML=symbol;b.setAttribute('aria-label',label);b.dataset.uiTooltip=label;b.onclick=()=>{const cls=`studio-${side}-collapsed`;body.classList.toggle(cls);b.setAttribute('aria-pressed',String(body.classList.contains(cls)));localStorage.setItem(`einvite-${side}-collapsed`,body.classList.contains(cls)?'1':'0')};toolbar.prepend(b);if(localStorage.getItem(`einvite-${side}-collapsed`)==='1'){body.classList.add(`studio-${side}-collapsed`);b.setAttribute('aria-pressed','true')}return b}
  addToggle('right','Toggle inspector','▥');addToggle('left','Toggle creation panel','▤');
  function resizer(side){if(!main)return;const h=document.createElement('div');h.className=`studio-panel-resizer ${side[0]}`;main.append(h);h.addEventListener('pointerdown',e=>{h.setPointerCapture(e.pointerId);h.classList.add('dragging');body.style.userSelect='none';const start=e.clientX,startL=leftWidth,startR=rightWidth;const move=ev=>{if(side==='left'){leftWidth=Math.max(290,Math.min(560,startL+(ev.clientX-start)))}else{rightWidth=Math.max(280,Math.min(520,startR-(ev.clientX-start)))}setWidths()};const up=()=>{h.classList.remove('dragging');body.style.userSelect='';localStorage.setItem('einvite-left-width',leftWidth);localStorage.setItem('einvite-right-width',rightWidth);h.removeEventListener('pointermove',move);h.removeEventListener('pointerup',up)};h.addEventListener('pointermove',move);h.addEventListener('pointerup',up)})}
  resizer('left');resizer('right');
  const context=document.createElement('div');context.className='ui-context-menu';context.hidden=true;
  context.innerHTML=`<button data-cmd="duplicate"><span>⧉</span><b>Duplicate</b><kbd>Ctrl+D</kbd></button><button data-cmd="copy"><span>□</span><b>Copy</b><kbd>Ctrl+C</kbd></button><button data-cmd="paste"><span>▣</span><b>Paste</b><kbd>Ctrl+V</kbd></button><div class="ui-context-sep"></div><button data-cmd="forward"><span>↑</span><b>Bring forward</b><kbd></kbd></button><button data-cmd="backward"><span>↓</span><b>Send backward</b><kbd></kbd></button><button data-cmd="lock"><span>◇</span><b>Lock / unlock</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="addText"><span>T</span><b>Add text</b><kbd></kbd></button><button data-cmd="fit"><span>⌗</span><b>Fit canvas</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="delete" class="danger"><span>×</span><b>Delete</b><kbd>Del</kbd></button>`;
  document.body.append(context);
  const cmdMap={duplicate:'duplicate',copy:'copyObjects',paste:'pasteObjects',forward:'bringForward',backward:'sendBackward',addText:'addText',fit:'fitCanvas',delete:'deleteBtn'};
  context.addEventListener('click',e=>{const b=e.target.closest('[data-cmd]');if(!b)return;const cmd=b.dataset.cmd;if(cmd==='lock'){const lock=$('#objectLocked');if(lock){lock.checked=!lock.checked;lock.dispatchEvent(new Event('change',{bubbles:true}))}}else document.getElementById(cmdMap[cmd])?.click();context.hidden=true});
  $('#stage')?.addEventListener('contextmenu',e=>{e.preventDefault();const obj=e.target.closest('.object');if(obj&&!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected'))obj.click();context.hidden=false;const w=220,h=390;context.style.left=Math.min(e.clientX,innerWidth-w-8)+'px';context.style.top=Math.min(e.clientY,innerHeight-h-8)+'px'});
  document.addEventListener('pointerdown',e=>{if(!context.contains(e.target))context.hidden=true});
}
addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname===location.pathname&&u.hash)return;if(a.closest('dialog'))return;e.preventDefault();body.classList.add('ui-page-leaving');setTimeout(()=>location.href=u.href,115)});
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const editor=!!$('#stage')&&!!$('.studio-left-panel');
document.documentElement.classList.add('final-ui-ready');
const progress=document.createElement('div'); progress.className='final-route-progress'; document.body.append(progress);
addEventListener('beforeunload',()=>progress.classList.add('active'));
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href]'); if(!a||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  try{const u=new URL(a.href,location.href);if(u.origin===location.origin&&u.href!==location.href)progress.classList.add('active')}catch{}
},true);
if(!document.body.classList.contains('guest')) requestAnimationFrame(()=>document.body.classList.add('final-page-entered'));
const globalObserver=new MutationObserver(()=>{
  $$('.empty:not([data-final-empty])').forEach(el=>{el.dataset.finalEmpty='1';el.classList.add('final-empty-state')});
  $$('dialog:not([data-final-dialog])').forEach(el=>{el.dataset.finalDialog='1';el.classList.add('final-dialog')});
});
globalObserver.observe(document.body,{subtree:true,childList:true});
if(!editor)return;
const stage=$('#stage');
const objectPane=$('[data-inspector-pane="object"]');
const elementsPane=$('[data-studio-pane="elements"]');
const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const applyNow=items=>{items.forEach(item=>{try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(item)}catch{}});try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};try{typeof refreshSelectionUI==='function'&&refreshSelectionUI()}catch{}};
const setData=(key,value,{apply=true}={})=>{const items=activeObjects();if(!items.length)return;items.forEach(item=>item.dataset[key]=String(value));if(apply)applyNow(items);saveNow();refreshAdvancedControls();refreshTimeline()};
const boolData=(key,value)=>setData(key,value?'true':'false');
const selectedType=()=>activeObjects()[0]?.dataset.objectType||'';
const safeText=node=>(node?.querySelector('.content')?.textContent||node?.dataset.alt||node?.dataset.objectType||'Object').trim().slice(0,38);
function toast(message,icon='✦'){
  if(typeof window.uiToast==='function')return window.uiToast(message,icon);
  let stack=$('.final-toast-stack');if(!stack){stack=document.createElement('div');stack.className='final-toast-stack';document.body.append(stack)}
  const t=document.createElement('div');t.className='final-toast';t.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(t);setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),220)},1900)
}
function selectOnly(item){try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([item])}catch{item.click()}setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0)}
function makeId(prefix='object'){return`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`}
const advanced=document.createElement('section'); advanced.className='final-advanced-inspector';
advanced.innerHTML=`
  <div class="final-panel-title"><div><small>Creative controls</small><h2>Effects & motion</h2></div><span class="final-beta">Advanced</span></div>
  <details open class="final-control-group" data-final-group="surface"><summary>Surface & blending</summary>
    <label class="final-toggle-row"><span>Object background</span><input id="finalBgEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Background<input id="finalBgColor" type="color" value="#ffffff"></label><label>Opacity <span id="finalBgOpacityValue">100%</span><input id="finalBgOpacity" type="range" min="0" max="100" value="100"></label></div>
    <label>Blend mode<select id="finalBlendMode"><option value="normal">Normal</option><option value="multiply">Multiply</option><option value="screen">Screen</option><option value="overlay">Overlay</option><option value="soft-light">Soft light</option><option value="darken">Darken</option><option value="lighten">Lighten</option></select></label>
  </details>
  <details class="final-control-group" data-final-group="shape"><summary>Gradient fill</summary>
    <label>Fill type<select id="finalFillMode"><option value="solid">Solid</option><option value="gradient">Gradient</option></select></label>
    <div class="final-two-col"><label>Start<input id="finalGradientStart" type="color" value="#d9a6ad"></label><label>End<input id="finalGradientEnd" type="color" value="#9d4555"></label></div>
    <label>Angle <span id="finalGradientAngleValue">135°</span><input id="finalGradientAngle" type="range" min="0" max="360" value="135"></label>
    <div class="final-gradient-preview" id="finalGradientPreview"></div>
  </details>
  <details class="final-control-group" data-final-group="text"><summary>Text effects</summary>
    <label>Transform<select id="finalTextTransform"><option value="none">As typed</option><option value="uppercase">UPPERCASE</option><option value="lowercase">lowercase</option><option value="capitalize">Capitalize</option></select></label>
    <label class="final-toggle-row"><span>Gradient text</span><input id="finalTextGradientEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Start<input id="finalTextGradientStart" type="color" value="#9d4555"></label><label>End<input id="finalTextGradientEnd" type="color" value="#b58a3a"></label></div>
    <label>Gradient angle <span id="finalTextGradientAngleValue">90°</span><input id="finalTextGradientAngle" type="range" min="0" max="360" value="90"></label>
    <div class="final-two-col"><label>Outline <span id="finalStrokeValue">0px</span><input id="finalStrokeWidth" type="range" min="0" max="8" step="0.5" value="0"></label><label>Outline color<input id="finalStrokeColor" type="color" value="#ffffff"></label></div>
    <div class="final-two-col"><label>Text shadow <span id="finalTextShadowValue">0px</span><input id="finalTextShadowBlur" type="range" min="0" max="40" value="0"></label><label>Shadow color<input id="finalTextShadowColor" type="color" value="#000000"></label></div>
    <div class="final-style-presets">
      <button type="button" data-final-text-style="luxury">Luxury Gold</button><button type="button" data-final-text-style="editorial">Editorial</button><button type="button" data-final-text-style="soft">Soft Glow</button><button type="button" data-final-text-style="minimal">Minimal</button>
    </div>
  </details>
  <details open class="final-control-group" data-final-group="motion"><summary>Motion timing</summary>
    <label>Animation delay <span id="finalDelayValue">0ms</span><input id="finalAnimationDelay" type="range" min="0" max="5000" step="50" value="0"></label>
    <div class="final-inline-actions"><button type="button" id="finalPreviewSelection">▶ Preview selected</button><button type="button" id="finalPreviewPage">▶ Preview page</button><button type="button" id="finalStagger">Stagger selected</button></div>
  </details>
  <details class="final-control-group" data-final-group="layout"><summary>Smart layout</summary>
    <div class="final-layout-grid"><button data-final-layout="horizontal">Horizontal stack</button><button data-final-layout="vertical">Vertical stack</button><button data-final-layout="grid">Smart grid</button><button data-final-layout="center">Center selection</button><button data-final-layout="equal-width">Equal width</button><button data-final-layout="equal-height">Equal height</button></div>
  </details>`;
if(objectPane)objectPane.append(advanced);
const controls={
 bgEnabled:$('#finalBgEnabled'),bgColor:$('#finalBgColor'),bgOpacity:$('#finalBgOpacity'),blend:$('#finalBlendMode'),fillMode:$('#finalFillMode'),gradientStart:$('#finalGradientStart'),gradientEnd:$('#finalGradientEnd'),gradientAngle:$('#finalGradientAngle'),textGradientEnabled:$('#finalTextGradientEnabled'),textGradientStart:$('#finalTextGradientStart'),textGradientEnd:$('#finalTextGradientEnd'),textGradientAngle:$('#finalTextGradientAngle'),strokeWidth:$('#finalStrokeWidth'),strokeColor:$('#finalStrokeColor'),textShadowBlur:$('#finalTextShadowBlur'),textShadowColor:$('#finalTextShadowColor'),textTransform:$('#finalTextTransform'),delay:$('#finalAnimationDelay')
};
function refreshAdvancedControls(){
  const item=activeObjects()[0],has=!!item,type=item?.dataset.objectType||'';
  advanced.classList.toggle('is-disabled',!has);
  $$('[data-final-group="shape"]',advanced).forEach(x=>x.hidden=type!=='shape');
  $$('[data-final-group="text"]',advanced).forEach(x=>x.hidden=!['text','decoration'].includes(type));
  if(!item)return;
  controls.bgEnabled.checked=item.dataset.backgroundEnabled==='true';controls.bgColor.value=item.dataset.backgroundColor||'#ffffff';controls.bgOpacity.value=item.dataset.backgroundOpacity??100;$('#finalBgOpacityValue').textContent=`${controls.bgOpacity.value}%`;controls.blend.value=item.dataset.blendMode||'normal';
  controls.fillMode.value=item.dataset.fillMode||'solid';controls.gradientStart.value=item.dataset.gradientStart||'#d9a6ad';controls.gradientEnd.value=item.dataset.gradientEnd||'#9d4555';controls.gradientAngle.value=item.dataset.gradientAngle||135;$('#finalGradientAngleValue').textContent=`${controls.gradientAngle.value}°`;$('#finalGradientPreview').style.background=`linear-gradient(${controls.gradientAngle.value}deg,${controls.gradientStart.value},${controls.gradientEnd.value})`;
  controls.textGradientEnabled.checked=item.dataset.textGradientEnabled==='true';controls.textGradientStart.value=item.dataset.textGradientStart||'#9d4555';controls.textGradientEnd.value=item.dataset.textGradientEnd||'#b58a3a';controls.textGradientAngle.value=item.dataset.textGradientAngle||90;$('#finalTextGradientAngleValue').textContent=`${controls.textGradientAngle.value}°`;controls.strokeWidth.value=item.dataset.textStrokeWidth||0;$('#finalStrokeValue').textContent=`${controls.strokeWidth.value}px`;controls.strokeColor.value=item.dataset.textStrokeColor||'#ffffff';controls.textShadowBlur.value=item.dataset.textShadowBlur||0;$('#finalTextShadowValue').textContent=`${controls.textShadowBlur.value}px`;controls.textShadowColor.value=item.dataset.textShadowColor||'#000000';controls.textTransform.value=item.dataset.textTransform||'none';controls.delay.value=item.dataset.animationDelay||0;$('#finalDelayValue').textContent=`${controls.delay.value}ms`;
}
controls.bgEnabled.onchange=e=>boolData('backgroundEnabled',e.target.checked);controls.bgColor.oninput=e=>setData('backgroundColor',e.target.value);controls.bgOpacity.oninput=e=>{$('#finalBgOpacityValue').textContent=`${e.target.value}%`;setData('backgroundOpacity',e.target.value)};controls.blend.onchange=e=>setData('blendMode',e.target.value);
controls.fillMode.onchange=e=>setData('fillMode',e.target.value);controls.gradientStart.oninput=e=>{setData('gradientStart',e.target.value);refreshAdvancedControls()};controls.gradientEnd.oninput=e=>{setData('gradientEnd',e.target.value);refreshAdvancedControls()};controls.gradientAngle.oninput=e=>{$('#finalGradientAngleValue').textContent=`${e.target.value}°`;setData('gradientAngle',e.target.value);refreshAdvancedControls()};
controls.textGradientEnabled.onchange=e=>boolData('textGradientEnabled',e.target.checked);controls.textGradientStart.oninput=e=>setData('textGradientStart',e.target.value);controls.textGradientEnd.oninput=e=>setData('textGradientEnd',e.target.value);controls.textGradientAngle.oninput=e=>{$('#finalTextGradientAngleValue').textContent=`${e.target.value}°`;setData('textGradientAngle',e.target.value)};controls.strokeWidth.oninput=e=>{$('#finalStrokeValue').textContent=`${e.target.value}px`;setData('textStrokeWidth',e.target.value)};controls.strokeColor.oninput=e=>setData('textStrokeColor',e.target.value);controls.textShadowBlur.oninput=e=>{$('#finalTextShadowValue').textContent=`${e.target.value}px`;setData('textShadowBlur',e.target.value)};controls.textShadowColor.oninput=e=>setData('textShadowColor',e.target.value);controls.textTransform.onchange=e=>setData('textTransform',e.target.value);controls.delay.oninput=e=>{$('#finalDelayValue').textContent=`${e.target.value}ms`;setData('animationDelay',e.target.value,{apply:false})};
const textStyles={
 luxury:{textGradientEnabled:'true',textGradientStart:'#7a5718',textGradientEnd:'#e9c86e',textGradientAngle:'90',textStrokeWidth:'0',textShadowBlur:'10',textShadowColor:'#5b3a0b',fontWeight:'700',letterSpacing:'1'},
 editorial:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'italic',letterSpacing:'0.5',textTransform:'none'},
 soft:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'18',textShadowColor:'#9d4555',fontWeight:'400',letterSpacing:'0'},
 minimal:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'normal',letterSpacing:'2',textTransform:'uppercase'}
};
$$('[data-final-text-style]').forEach(b=>b.onclick=()=>{const preset=textStyles[b.dataset.finalTextStyle];const items=activeObjects().filter(x=>['text','decoration'].includes(x.dataset.objectType));items.forEach(item=>Object.entries(preset).forEach(([k,v])=>item.dataset[k]=v));applyNow(items);saveNow();refreshAdvancedControls();toast(`${b.textContent.trim()} style applied`)});
function keyframesFor(name){return({
 'fade-up':[{opacity:0,transform:'translateY(24px)'},{opacity:1,transform:'translateY(0)'}],
 'soft-zoom':[{opacity:0,transform:'scale(.9)'},{opacity:1,transform:'scale(1)'}],
 'slide-left':[{opacity:0,transform:'translateX(45px)'},{opacity:1,transform:'translateX(0)'}],
 'blur-in':[{opacity:0,filter:'blur(14px)'},{opacity:1,filter:'blur(0)'}],
 'bounce-in':[{opacity:0,transform:'scale(.72)'},{opacity:1,transform:'scale(1.05)',offset:.72},{opacity:1,transform:'scale(1)'}],
 'flip-in':[{opacity:0,transform:'rotateY(80deg)'},{opacity:1,transform:'rotateY(0)'}],
 'float':[{transform:'translateY(0)'},{transform:'translateY(-12px)'},{transform:'translateY(0)'}],
 none:[{opacity:1},{opacity:1}]
})[name]||[{opacity:0},{opacity:1}]}
function previewObjects(items){items.forEach(item=>{const duration=Math.max(300,Math.min(3000,Number(item.dataset.duration||900))),delay=Math.max(0,Math.min(5000,Number(item.dataset.animationDelay||0))),rotation=`rotate(${Number(item.dataset.rotation||0)}deg)`,frames=keyframesFor(item.dataset.animation||'fade-up').map(frame=>({...frame,transform:frame.transform?`${frame.transform} ${rotation}`:rotation}));item.animate(frames,{duration,delay,easing:'cubic-bezier(.2,.8,.2,1)',fill:'none',iterations:item.dataset.animation==='float'?2:1})})}
window.EInvitePreviewObjects=items=>previewObjects(Array.isArray(items)?items:[]);
$('#finalPreviewSelection').onclick=()=>previewObjects(activeObjects());$('#finalPreviewPage').onclick=()=>previewObjects($$('.object'));$('#finalStagger').onclick=()=>{const items=activeObjects();if(items.length<2)return toast('Select two or more objects to stagger','!');items.sort((a,b)=>(parseFloat(a.style.top)||0)-(parseFloat(b.style.top)||0)||(parseFloat(a.style.left)||0)-(parseFloat(b.style.left)||0)).forEach((item,i)=>item.dataset.animationDelay=String(i*140));saveNow();refreshAdvancedControls();refreshTimeline();previewObjects(items);toast(`Staggered ${items.length} objects`)};
const timeline=document.createElement('section');timeline.className='final-timeline';timeline.innerHTML=`<div class="final-panel-title"><div><small>Sequence</small><h2>Motion timeline</h2></div><button id="finalTimelinePlay" type="button">▶ Play all</button></div><div id="finalTimelineRows"></div>`;if(objectPane)objectPane.append(timeline);
function refreshTimeline(){const host=$('#finalTimelineRows');if(!host)return;const items=$$('.object').sort((a,b)=>Number(a.style.zIndex||0)-Number(b.style.zIndex||0));host.innerHTML=items.length?'':'<p class="hint">Add objects to build a motion sequence.</p>';const maxEnd=Math.max(1000,...items.map(x=>Number(x.dataset.animationDelay||0)+Number(x.dataset.duration||900)));items.forEach(item=>{const row=document.createElement('button');row.type='button';row.className=`final-timeline-row${item.classList.contains('selected')||item.classList.contains('multi-selected')?' active':''}`;const delay=Number(item.dataset.animationDelay||0),duration=Number(item.dataset.duration||900);row.innerHTML=`<span class="final-timeline-icon">${item.dataset.objectType==='image'?'▣':item.dataset.objectType==='shape'?'□':'T'}</span><span class="final-timeline-name">${safeText(item)||'Object'}</span><span class="final-timeline-track"><i style="left:${delay/maxEnd*100}%;width:${Math.max(4,duration/maxEnd*100)}%"></i></span><small>${delay}ms</small>`;row.onclick=()=>selectOnly(item);host.append(row)})}
$('#finalTimelinePlay').onclick=()=>previewObjects($$('.object'));
function stagePercentFrame(item){return{left:parseFloat(item.style.left)||0,top:parseFloat(item.style.top)||0,width:item.getBoundingClientRect().width/stage.getBoundingClientRect().width*100,height:item.getBoundingClientRect().height/stage.getBoundingClientRect().height*100}}
function smartLayout(kind){const items=activeObjects().filter(x=>x.dataset.locked!=='true');if(!items.length)return toast('Select objects first','!');const frames=items.map(x=>({item:x,...stagePercentFrame(x)}));if(kind==='center'){const minL=Math.min(...frames.map(x=>x.left)),maxR=Math.max(...frames.map(x=>x.left+x.width)),minT=Math.min(...frames.map(x=>x.top)),maxB=Math.max(...frames.map(x=>x.top+x.height)),dx=50-(minL+maxR)/2,dy=50-(minT+maxB)/2;frames.forEach(x=>{x.item.style.left=`${x.left+dx}%`;x.item.style.top=`${x.top+dy}%`})}
 else if(kind==='horizontal'){const gap=3,total=frames.reduce((s,x)=>s+x.width,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.left-b.left).forEach(x=>{x.item.style.left=`${cur}%`;x.item.style.top='45%';cur+=x.width+gap})}
 else if(kind==='vertical'){const gap=2,total=frames.reduce((s,x)=>s+x.height,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.top-b.top).forEach(x=>{x.item.style.top=`${cur}%`;x.item.style.left=`${Math.max(4,(100-x.width)/2)}%`;cur+=x.height+gap})}
 else if(kind==='grid'){const cols=Math.ceil(Math.sqrt(frames.length)),gap=3,cell=(92-gap*(cols-1))/cols;frames.forEach((x,i)=>{const row=Math.floor(i/cols),col=i%cols;x.item.style.left=`${4+col*(cell+gap)}%`;x.item.style.top=`${8+row*22}%`;x.item.style.width=`${cell}%`})}
 else if(kind==='equal-width'){const w=Math.max(...frames.map(x=>x.width));frames.forEach(x=>x.item.style.width=`${w}%`)}
 else if(kind==='equal-height'){const h=Math.max(...frames.map(x=>x.height));frames.forEach(x=>x.item.style.height=`${h}%`)}
 try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}saveNow();toast('Layout updated')}
$$('[data-final-layout]').forEach(b=>b.onclick=()=>smartLayout(b.dataset.finalLayout));
const library=[
 {id:'flourish-1',name:'Classic flourish',cat:'Ornaments',glyph:'❦'},{id:'flourish-2',name:'Fine flourish',cat:'Ornaments',glyph:'❧'},{id:'sparkle-1',name:'Four-point sparkle',cat:'Ornaments',glyph:'✦'},{id:'sparkle-2',name:'Soft sparkle',cat:'Ornaments',glyph:'✧'},{id:'star-1',name:'Decorative star',cat:'Ornaments',glyph:'✶'},{id:'diamond-1',name:'Open diamond',cat:'Ornaments',glyph:'◇'},{id:'diamond-2',name:'Solid diamond',cat:'Ornaments',glyph:'◆'},
 {id:'heart-1',name:'Classic heart',cat:'Romance',glyph:'♥'},{id:'heart-2',name:'Outline heart',cat:'Romance',glyph:'♡'},{id:'rings',name:'Wedding rings',cat:'Romance',glyph:'◯◯'},{id:'infinity',name:'Forever mark',cat:'Romance',glyph:'∞'},{id:'love-spark',name:'Love sparkle',cat:'Romance',glyph:'♡ ✦ ♡'},
 {id:'leaf-1',name:'Botanical leaf',cat:'Botanical',glyph:'❧'},{id:'flower-1',name:'Flower mark',cat:'Botanical',glyph:'✿'},{id:'flower-2',name:'Elegant flower',cat:'Botanical',glyph:'❀'},{id:'petal',name:'Petal cluster',cat:'Botanical',glyph:'❋'},{id:'branch',name:'Leaf branch',cat:'Botanical',glyph:'☘'},
 {id:'crown',name:'Royal crown',cat:'Ceremonial',glyph:'♛'},{id:'royal',name:'Royal emblem',cat:'Ceremonial',glyph:'♔'},{id:'sun',name:'Ceremonial sun',cat:'Ceremonial',glyph:'☼'},{id:'blessing',name:'Blessing mark',cat:'Ceremonial',glyph:'✺'},{id:'lotus',name:'Lotus-inspired mark',cat:'Ceremonial',glyph:'✾'},
 {id:'quote',name:'Quote mark',cat:'Editorial',glyph:'“'},{id:'bullet',name:'Editorial bullet',cat:'Editorial',glyph:'•'},{id:'section',name:'Section divider',cat:'Editorial',glyph:'— ✦ —'},{id:'roman',name:'Roman divider',cat:'Editorial',glyph:'I · II · III'},
 {id:'rect',name:'Rectangle',cat:'Shapes',shape:'rectangle'},{id:'circle',name:'Circle',cat:'Shapes',shape:'circle'},{id:'line',name:'Line',cat:'Shapes',shape:'line'},{id:'panel',name:'Glass panel',cat:'Shapes',shape:'panel'},
 {id:'title-luxury',name:'Luxury title',cat:'Text styles',text:'YOUR CELEBRATION',preset:'luxury'},{id:'title-editorial',name:'Editorial title',cat:'Text styles',text:'A beautiful beginning',preset:'editorial'},{id:'khmer-title',name:'Khmer ceremonial title',cat:'Text styles',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',preset:'khmer'},{id:'date-badge',name:'Date badge',cat:'Text styles',text:'27 · 12 · 2026',preset:'date'},
 {id:'khmer-diamond-row',name:'Khmer diamond row',cat:'Khmer motifs',glyph:'◇ ◆ ◇ ◆ ◇'},{id:'khmer-gold-divider',name:'Ceremonial divider',cat:'Khmer motifs',glyph:'✦ ◇ ✦'},{id:'khmer-lotus-row',name:'Lotus row',cat:'Khmer motifs',glyph:'✾  ✾  ✾'},{id:'khmer-blessing-row',name:'Blessing ornament',cat:'Khmer motifs',glyph:'✺ ✦ ✺'},{id:'khmer-temple-line',name:'Temple line',cat:'Khmer motifs',glyph:'⌂ ◇ ⌂'},{id:'khmer-royal-row',name:'Royal row',cat:'Khmer motifs',glyph:'♔  ◆  ♔'},
 {id:'confetti-1',name:'Confetti sparkle',cat:'Celebration',glyph:'✦ ✧ ✶ ✦'},{id:'party-stars',name:'Party stars',cat:'Celebration',glyph:'★ ☆ ★'},{id:'balloon-pair',name:'Balloon pair',cat:'Celebration',glyph:'◯  ◯'},{id:'gift-mark',name:'Gift mark',cat:'Celebration',glyph:'▣'},{id:'cake-mark',name:'Cake mark',cat:'Celebration',glyph:'♨'},{id:'music-notes',name:'Music notes',cat:'Celebration',glyph:'♪ ♫ ♪'},
 {id:'business-arrow',name:'Forward arrow',cat:'Business',glyph:'→'},{id:'business-grid',name:'Executive grid',cat:'Business',glyph:'□ □ □'},{id:'business-dots',name:'Modern dots',cat:'Business',glyph:'• • • •'},{id:'business-plus',name:'Modern plus',cat:'Business',glyph:'+  +  +'},{id:'business-chevron',name:'Chevron line',cat:'Business',glyph:'› › ›'},{id:'business-rule',name:'Executive rule',cat:'Business',glyph:'━━━'},
 {id:'corner-top-left',name:'Corner flourish',cat:'Borders',glyph:'⌜❦'},{id:'corner-top-right',name:'Reverse corner',cat:'Borders',glyph:'❦⌝'},{id:'thin-rule',name:'Thin divider',cat:'Borders',glyph:'────────'},{id:'diamond-rule',name:'Diamond divider',cat:'Borders',glyph:'── ◇ ──'},{id:'spark-rule',name:'Spark divider',cat:'Borders',glyph:'── ✦ ──'},{id:'dot-rule',name:'Dotted divider',cat:'Borders',glyph:'· · · · · ·'},
 {id:'leaf-pair',name:'Leaf pair',cat:'Botanical',glyph:'❧  ❧'},{id:'flower-row',name:'Flower row',cat:'Botanical',glyph:'❀ ✿ ❀'},{id:'garden-spark',name:'Garden sparkle',cat:'Botanical',glyph:'❧ ✦ ❧'},{id:'clover-row',name:'Clover row',cat:'Botanical',glyph:'☘ ☘ ☘'},{id:'small-bloom',name:'Small bloom',cat:'Botanical',glyph:'✽'},{id:'floral-divider',name:'Floral divider',cat:'Botanical',glyph:'❀ ─ ❀'},
 {id:'love-divider',name:'Heart divider',cat:'Romance',glyph:'── ♡ ──'},{id:'heart-cluster',name:'Heart cluster',cat:'Romance',glyph:'♡ ♥ ♡'},{id:'promise-mark',name:'Promise mark',cat:'Romance',glyph:'∞ ♡'},{id:'ring-divider',name:'Ring divider',cat:'Romance',glyph:'─ ◯◯ ─'},{id:'love-quote',name:'Love quote',cat:'Text styles',text:'A lifetime begins here',preset:'editorial'},{id:'thank-you',name:'Thank-you title',cat:'Text styles',text:'WITH LOVE & GRATITUDE',preset:'luxury'},
 {id:'circle-outline',name:'Circle outline',cat:'Shapes',shape:'circle'},{id:'soft-panel',name:'Soft panel',cat:'Shapes',shape:'panel'},{id:'wide-line',name:'Wide line',cat:'Shapes',shape:'line'},{id:'square-card',name:'Square card',cat:'Shapes',shape:'rectangle'}
];
const librarySection=document.createElement('section');librarySection.className='final-element-library';librarySection.innerHTML=`<div class="final-panel-title"><div><small>Invitation library</small><h2>Design elements</h2></div><span class="final-library-count"></span></div><div class="final-library-search"><span>⌕</span><input type="search" placeholder="Search ornaments, flowers, text…"></div><div class="final-library-cats"></div><div class="final-library-grid"></div>`;
if(elementsPane)elementsPane.insertBefore(librarySection,elementsPane.querySelector('.studio-pane-heading')?.nextSibling||elementsPane.firstChild);
let libraryCat='All',libraryQuery='';const favKey='einvite-element-favorites-v1',recentKey='einvite-element-recent-v1';let favorites=new Set(JSON.parse(localStorage.getItem(favKey)||'[]')),recent=JSON.parse(localStorage.getItem(recentKey)||'[]');
const cats=['All','Favorites','Recent',...new Set(library.map(x=>x.cat))];
function addCustomElement(item,drop){if(item.shape){if(typeof addDesignElement==='function')addDesignElement(item.shape);return}
 const type='decoration',obj=typeof createObject==='function'?createObject(makeId('library'),type):null;if(!obj)return;const content=obj.querySelector('.content');content.textContent=item.text||item.glyph||'✦';obj.dataset.color=(window.state?.accent||$('#accent')?.value||'#9d4555');obj.dataset.fontSize=item.text?'34':'64';obj.style.width=item.text?'76%':'150px';obj.style.height=item.text?'110px':'120px';obj.style.left=drop?`${drop.x}%`:(item.text?'12%':'32%');obj.style.top=drop?`${drop.y}%`:'38%';if(item.preset==='luxury'){obj.dataset.textGradientEnabled='true';obj.dataset.textGradientStart='#7a5718';obj.dataset.textGradientEnd='#e9c86e';obj.dataset.fontWeight='700';obj.dataset.letterSpacing='2'}if(item.preset==='editorial'){obj.dataset.fontStyle='italic';obj.dataset.font='serif-georgia';obj.dataset.fontSize='38'}if(item.preset==='khmer'){obj.dataset.font="noto-serif-khmer";obj.dataset.fontSize='34';obj.dataset.color='#a87616'}if(item.preset==='date'){obj.dataset.letterSpacing='4';obj.dataset.fontSize='26';obj.dataset.backgroundEnabled='true';obj.dataset.backgroundColor='#ffffff';obj.dataset.backgroundOpacity='78';obj.dataset.borderRadius='28'}applyObjectVisualStyle(obj);stage.append(obj);clearSelection();setSelection([obj]);saveNow();
 recent=[item.id,...recent.filter(x=>x!==item.id)].slice(0,10);localStorage.setItem(recentKey,JSON.stringify(recent));renderLibrary();toast(`${item.name} added`)}
function filteredLibrary(){return library.filter(x=>{if(libraryCat==='Favorites'&&!favorites.has(x.id))return false;if(libraryCat==='Recent'&&!recent.includes(x.id))return false;if(!['All','Favorites','Recent'].includes(libraryCat)&&x.cat!==libraryCat)return false;return!libraryQuery||`${x.name} ${x.cat}`.toLowerCase().includes(libraryQuery)})}
function renderLibrary(){const catHost=$('.final-library-cats',librarySection),grid=$('.final-library-grid',librarySection);catHost.innerHTML=cats.map(c=>`<button type="button" class="${c===libraryCat?'active':''}" data-cat="${c}">${c}</button>`).join('');catHost.querySelectorAll('button').forEach(b=>b.onclick=()=>{libraryCat=b.dataset.cat;renderLibrary()});const items=filteredLibrary();$('.final-library-count',librarySection).textContent=`${items.length} items`;grid.innerHTML='';items.forEach(item=>{const card=document.createElement('article');card.className='final-element-card';card.draggable=true;card.innerHTML=`<button type="button" class="final-fav ${favorites.has(item.id)?'active':''}" aria-label="Favorite">★</button><div class="final-element-preview">${item.shape?`<i class="shape-${item.shape}"></i>`:`<span>${item.text||item.glyph}</span>`}</div><strong>${item.name}</strong><small>${item.cat}</small>`;card.onclick=e=>{if(e.target.closest('.final-fav'))return;addCustomElement(item)};card.querySelector('.final-fav').onclick=e=>{e.stopPropagation();favorites.has(item.id)?favorites.delete(item.id):favorites.add(item.id);localStorage.setItem(favKey,JSON.stringify([...favorites]));renderLibrary()};card.ondragstart=e=>{e.dataTransfer.setData('application/x-einvite-library-item',item.id);e.dataTransfer.effectAllowed='copy'};grid.append(card)})}
$('.final-library-search input',librarySection).oninput=e=>{libraryQuery=e.target.value.trim().toLowerCase();renderLibrary()};renderLibrary();
stage.addEventListener('dragover',e=>{if(Array.from(e.dataTransfer.types||[]).includes('application/x-einvite-library-item')){e.preventDefault();stage.classList.add('final-library-drop')}});stage.addEventListener('dragleave',()=>stage.classList.remove('final-library-drop'));stage.addEventListener('drop',e=>{const id=e.dataTransfer.getData('application/x-einvite-library-item');if(!id)return;e.preventDefault();stage.classList.remove('final-library-drop');const r=stage.getBoundingClientRect(),item=library.find(x=>x.id===id);if(item)addCustomElement(item,{x:Math.max(0,Math.min(85,(e.clientX-r.left)/r.width*100)),y:Math.max(0,Math.min(85,(e.clientY-r.top)/r.height*100))})});
const observer=new MutationObserver(()=>{refreshAdvancedControls();refreshTimeline()});observer.observe(stage,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-animation-delay','data-fill-mode','data-text-gradient-enabled']});
document.addEventListener('pointerup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);document.addEventListener('keyup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);
refreshAdvancedControls();refreshTimeline();
const tour=document.createElement('dialog');tour.className='final-tour';tour.innerHTML=`<form method="dialog"><button class="final-tour-close" aria-label="Close">×</button></form><div class="final-tour-art">✦</div><p class="invite-kicker">Creation Studio</p><h1>Design the invitation. Run the event.</h1><p>This workspace combines free-form visual creation with pages, animation, guest RSVP, publishing, Khmer dates and event operations.</p><div class="final-tour-grid"><article><b>1</b><strong>Create</strong><span>Drag elements, upload media and style every object.</span></article><article><b>2</b><strong>Build pages</strong><span>Mix free-form artboards with functional event sections.</span></article><article><b>3</b><strong>Animate</strong><span>Sequence motion with delay, duration and stagger controls.</span></article><article><b>4</b><strong>Publish</strong><span>Run the Design Check, publish a snapshot and manage guests.</span></article></div><div class="final-tour-actions"><button type="button" id="finalTourExplore">Explore studio</button><button type="button" id="finalTourDismiss" class="primary">Start creating</button></div>`;document.body.append(tour);
const TOUR_VERSION='studio-v27',LEGACY_TOUR_KEY='einvite-final-tour-seen-v1';let tourKey='',tourAutomatic=false,tourLauncher=null,tourSessionSeen=false,tourOpenGeneration=0;
async function resolveTourIdentity(){try{await window.EInviteBackend?.ready;if(window.EInviteBackend?.isAvailable?.()){const response=await fetch('/api/auth/me',{credentials:'same-origin'}),data=response.ok?await response.json():null,user=data?.user;if(user?.id||user?.email)return String(user.id||user.email)}}catch{}try{const user=JSON.parse(localStorage.getItem('sovan-account-v1')||'null');if(user?.id||user?.email)return String(user.id||user.email)}catch{}return'local-anonymous'}
function persistTourSeen(){tourSessionSeen=true;if(tourKey)localStorage.setItem(tourKey,'1')}
function workspaceFocus(){const target=$('#stage')||$('#canvasViewport')||$('.stage-wrap');target?.setAttribute?.('tabindex','-1');setTimeout(()=>{target?.focus?.({preventScroll:true});if(target)document.body.dataset.keyboardOwner='canvas'},0)}
function closeTour({explore=false}={}){tourOpenGeneration++;persistTourSeen();if(tour.open)tour.close();if(explore){document.querySelector('[data-studio-tab="elements"]')?.click();setTimeout(()=>$('.final-element-library')?.scrollIntoView({behavior:'smooth'}),100)}}
$('#finalTourDismiss').onclick=()=>closeTour();$('#finalTourExplore').onclick=()=>closeTour({explore:true});tour.addEventListener('cancel',event=>{event.preventDefault();closeTour()});tour.addEventListener('close',()=>{persistTourSeen();const automatic=tourAutomatic,launcher=tourLauncher;tourAutomatic=false;tourLauncher=null;if(automatic)workspaceFocus();else requestAnimationFrame(()=>launcher?.focus?.({preventScroll:true}))});
const status=$('.studio-statusbar>div:last-child');if(status){const b=document.createElement('button');b.type='button';b.className='final-tour-trigger';b.textContent='✦ Tour';b.onclick=()=>{tourAutomatic=false;tourLauncher=b;tour.showModal()};status.prepend(b)}
window.EInviteOnboardingReady=(async()=>{const generation=++tourOpenGeneration,identity=await resolveTourIdentity();tourKey=`einvite-final-tour-seen-v2:${encodeURIComponent(identity)}:${TOUR_VERSION}`;if(localStorage.getItem(LEGACY_TOUR_KEY)==='1'&&!localStorage.getItem(tourKey))localStorage.setItem(tourKey,'1');if(generation!==tourOpenGeneration||tourSessionSeen||localStorage.getItem(tourKey)==='1')return{shown:false,identity};tourAutomatic=true;tourLauncher=null;tour.showModal();await new Promise(resolve=>requestAnimationFrame(resolve));return{shown:true,identity}})();
})();;(()=>{'use strict';if(!document.querySelector('.admin-tabs'))return;const $=s=>document.querySelector(s);localStorage.removeItem('sovan-auth-token');async function api(path){const r=await fetch(path,{credentials:'same-origin',headers:{}});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'Request failed');return d}
const tabs=$('.admin-tabs'),btn=document.createElement('button');btn.type='button';btn.dataset.adminTab='system';btn.textContent='System';tabs.append(btn);const panel=document.createElement('section');panel.id='systemPanel';panel.className='admin-panel';panel.innerHTML='<div class="ei-system-grid" id="eiSystemMetrics"></div><div class="ei-system-table" id="eiSystemServices"></div>';document.querySelector('.admin-page').append(panel);
function fmtBytes(v){v=Number(v||0);for(const u of ['B','KB','MB','GB']){if(v<1024)return`${v.toFixed(v<10&&u!=='B'?1:0)} ${u}`;v/=1024}return`${v.toFixed(1)} TB`}
async function load(){try{const [health,m]=await Promise.all([api('/api/health'),api('/api/admin/metrics')]);const cards=[['Uptime',`${Math.floor(m.uptimeSeconds/3600)}h ${Math.floor(m.uptimeSeconds%3600/60)}m`],['Users',m.users],['Invitations',m.invitations],['Publications',m.publications],['RSVPs',m.rsvps],['Assets',m.assets],['Material storage',fmtBytes(m.assetBytes)]];$('#eiSystemMetrics').innerHTML=cards.map(([a,b])=>`<article class="ei-system-card"><small>${a}</small><strong>${b}</strong></article>`).join('');const services=[['API','Healthy'],['Database',health.database],['Asset storage',health.assetStorage],['Redis rate limiting',health.redis?'Connected':'In-memory fallback'],['AI provider',health.aiConfigured?'Configured':'Local assistant'],['SMTP',health.smtpConfigured?'Configured':'Not configured'],['Billing webhook',health.billingWebhookConfigured?'Configured':'Not configured']];$('#eiSystemServices').innerHTML=services.map(([a,b])=>`<div class="ei-system-row"><span>${a}</span><strong class="ei-system-status">${b}</strong></div>`).join('')}catch(e){$('#eiSystemServices').innerHTML=`<div class="empty">${e.message}</div>`}}
btn.addEventListener('click',()=>{document.querySelectorAll('[data-admin-tab]').forEach(x=>x.classList.toggle('active',x===btn));document.querySelectorAll('.admin-panel').forEach(x=>x.classList.remove('active'));panel.classList.add('active');setTimeout(load,0)});
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
if(document.body&&!document.body.dataset.page)document.body.dataset.page=page;
function dashboard(){
  const view=$('#dashboardView'),login=$('#loginView');if(!view)return;
  view.classList.add('dashboard-home');
  const rail=document.createElement('nav');rail.className='dashboard-home-rail';rail.innerHTML=`
    <button type="button" class="rail-create" title="Create invitation"><span>＋</span>Create</button>
    <a href="dashboard.html" class="active"><span>⌂</span>Home</a>
    <a href="templates.html"><span>▣</span>Templates</a>
    <a href="materials.html"><span>▧</span>Materials</a>
    <a href="billing.html"><span>◉</span>Plans</a>
    <div class="rail-spacer"></div>
    <a href="account.html"><span>◌</span>Account</a>`;
  document.body.append(rail);
  $('.rail-create',rail).onclick=()=>$('#newBtn')?.click();
  const hero=document.createElement('section');hero.className='dashboard-home-hero';hero.innerHTML=`
    <h1>What will you create today?</h1>
    <label class="dashboard-home-search"><span>⌕</span><input type="search" placeholder="Search your invitations"></label>
    <div class="dashboard-quick-create">
      <button type="button" class="create"><i>＋</i><span>Create</span></button>
      <a href="templates.html" class="template"><i>▣</i><span>Templates</span></a>
      <button type="button" class="wedding"><i>♡</i><span>Wedding</span></button>
      <button type="button" class="birthday"><i>✦</i><span>Birthday</span></button>
      <button type="button" class="business"><i>◇</i><span>Business</span></button>
      <a href="materials.html" class="upload"><i>⇧</i><span>Uploads</span></a>
    </div>`;
  view.prepend(hero);
  const createByType=(type)=>{const btn=$('#newBtn');btn?.click();setTimeout(()=>{const typeEl=$('#newType');if(typeEl){typeEl.value=type;typeEl.dispatchEvent(new Event('change',{bubbles:true}))}},40)};
  $('.create',hero).onclick=()=>$('#newBtn')?.click();$('.wedding',hero).onclick=()=>createByType('Wedding');$('.birthday',hero).onclick=()=>createByType('Birthday');$('.business',hero).onclick=()=>createByType('Business');
  const homeSearch=$('.dashboard-home-search input',hero);
  homeSearch.oninput=()=>{const old=$('#dashboardSearch');if(old){old.value=homeSearch.value;old.dispatchEvent(new Event('input',{bubbles:true}))}else{$$('.invite-card','#inviteGrid').forEach(card=>card.hidden=!card.textContent.toLowerCase().includes(homeSearch.value.toLowerCase()))}};
  const recent=document.createElement('div');recent.className='dashboard-recent-head';recent.innerHTML='<h2>Recent invitations</h2>';
  const filter=$('.dashboard-filter-tabs');if(filter)recent.append(filter);
  const grid=$('#inviteGrid');grid?.before(recent);
  grid?.addEventListener('click',e=>{const cover=e.target.closest('.invite-cover');if(!cover)return;const card=cover.closest('.invite-card');card?.querySelector('[data-edit]')?.click()});
  const header=$('body>header');
  function authState(){const signed=view.hidden===false;rail.hidden=!signed;if(header){header.querySelectorAll('a[href="materials.html"],a[href="billing.html"],a[href="account.html"]').forEach(a=>a.hidden=!signed);const logout=$('#logoutBtn');if(logout)logout.hidden=!signed}}
  new MutationObserver(authState).observe(view,{attributes:true,attributeFilter:['hidden']});authState();
}
function materials(){
  const head=$('.library-head'),upload=$('.upload-box');if(!head||!upload)return;
  const toggle=document.createElement('button');toggle.type='button';toggle.className='material-upload-toggle primary';toggle.innerHTML='<span>⇧</span> Upload files';head.append(toggle);upload.hidden=true;
  toggle.onclick=()=>{upload.hidden=!upload.hidden;toggle.innerHTML=upload.hidden?'<span>⇧</span> Upload files':'<span>×</span> Close upload';if(!upload.hidden)setTimeout(()=>$('#uploadFile')?.focus(),50)};
  const grid=$('#grid');
  const observer=new MutationObserver(()=>{
    const empty=$('.empty-library',grid);if(empty&&/Authentication required/i.test(empty.textContent)&&!empty.querySelector('.material-auth-action')){const a=document.createElement('a');a.href='dashboard.html';a.className='material-auth-action';a.innerHTML='<button type="button" class="primary">Sign in to use materials</button>';empty.append(a)}
  });observer.observe(grid,{childList:true,subtree:true});
}
function editor(){
  const main=$('body.studio-experience>main'),rail=$('.studio-tool-rail'),host=$('.studio-pane-host'),stage=$('#stage');if(!main||!rail||!host||!stage)return;
  if(!$('[data-studio-tab="text"]',rail)){
    const elementsBtn=$('[data-studio-tab="elements"]',rail);
    const b=document.createElement('button');b.type='button';b.className='studio-rail-button';b.dataset.studioTab='text';b.innerHTML='<span class="studio-nav-icon">T</span><span>Text</span>';b.title='Text, fonts and typography';rail.insertBefore(b,elementsBtn||null);
    const pane=document.createElement('section');pane.className='studio-pane studio-text-pane';pane.dataset.studioPane='text';pane.innerHTML=`
      <div class="studio-pane-heading"><div><small>Create</small><h1>Text</h1></div></div>
      <label class="refine-text-search"><span>⌕</span><input type="search" placeholder="Search fonts and combinations"></label>
      <button type="button" class="refine-add-text">T &nbsp; Add a text box</button>
      <button type="button" class="refine-magic-write">✦ Magic invitation writing</button>
      <section class="refine-text-section"><div><h3>Default text styles</h3></div><div class="refine-text-presets">
        <button class="refine-text-preset heading" data-refine-text="heading">Add a heading</button>
        <button class="refine-text-preset subheading" data-refine-text="subheading">Add a subheading</button>
        <button class="refine-text-preset body" data-refine-text="body">Add a little bit of body text</button>
        <button class="refine-text-preset khmer" data-refine-text="khmer">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section"><div><h3>Fonts</h3><small>Search · Khmer · Favorites</small></div><button type="button" class="refine-browse-fonts">Browse all fonts</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Quick invitation styles</small></div><div class="refine-font-combos">
        <button class="refine-font-combo" data-combo="gold"><span style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button class="refine-font-combo" data-combo="modern"><span style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><i>HEADING</i></span><small>Modern contrast</small></button>
        <button class="refine-font-combo" data-combo="romance"><span style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button class="refine-font-combo" data-combo="khmer"><span style="font-family:'Noto Serif Khmer','Khmer OS Muol Light',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      </div></section>`;
    host.append(pane);
    function activate(id){
      $$('[data-studio-tab]',rail).forEach(x=>x.classList.toggle('active',x.dataset.studioTab===id));
      $$('[data-studio-pane]',host).forEach(x=>x.classList.toggle('active',x.dataset.studioPane===id));
      localStorage.setItem('einvite-editor-left-tab',id);applyMode();
    }
    b.onclick=()=>activate('text');
    $('.refine-add-text',pane).onclick=()=>$('#addText')?.click();
    $$('.refine-text-preset',pane).forEach(btn=>btn.onclick=()=>{const source=$(`[data-text-preset="${btn.dataset.refineText}"]`);if(source)source.click();else $('#addText')?.click()});
    $('.refine-browse-fonts',pane).onclick=()=>$('.ei-font-launch')?.click();
    $('.refine-magic-write',pane).onclick=()=>{const ebtn=$('[data-studio-tab="event"]',rail);ebtn?.click();setTimeout(()=>$('#eiAiStudio textarea,.ei-ai-studio textarea')?.focus(),80)};
    const comboMap={gold:{font:'serif-georgia',size:48,color:'#b48a20',text:'Golden Hour'},modern:{font:'sans-arial',size:44,color:'#202127',text:'Your Celebration'},romance:{font:'serif-georgia',size:46,color:'#426b52',text:'Bride & Groom'},khmer:{font:"noto-serif-khmer",size:38,color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'}};
    $$('.refine-font-combo',pane).forEach(btn=>btn.onclick=()=>{const c=comboMap[btn.dataset.combo];$('#addText')?.click();setTimeout(()=>{const sel=$('.object.selected,.object.multi-selected');if(!sel)return;const content=sel.querySelector('.content');if(content)content.textContent=c.text;sel.dataset.font=c.font;sel.dataset.fontSize=String(c.size);sel.dataset.color=c.color;try{applyObjectVisualStyle(sel);save()}catch{}},40)});
    $('.refine-text-search input',pane).oninput=e=>{const q=e.target.value.toLowerCase();$$('.refine-text-preset,.refine-font-combo',pane).forEach(x=>x.hidden=!!q&&!x.textContent.toLowerCase().includes(q))};
  }
  function applyMode(){ /* centralized elsewhere */ }
  const openInspector=()=>{if(innerWidth<=1180&&$('.object.selected,.object.multi-selected',stage))document.body.classList.add('inspector-open')};
  stage.addEventListener('pointerup',()=>setTimeout(openInspector,0));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.body.classList.remove('inspector-open')});
  const inspector=$('.right');if(inspector&&!inspector.querySelector('.refine-inspector-close')){const c=document.createElement('button');c.type='button';c.className='refine-inspector-close';c.textContent='×';c.title='Close inspector';c.onclick=()=>document.body.classList.remove('inspector-open');inspector.prepend(c)}
}
if(page==='dashboard')dashboard();
if(page==='materials')materials();
if(page==='index')setTimeout(editor,0);
})();