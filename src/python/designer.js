const $=s=>document.querySelector(s);localStorage.removeItem('sovan-auth-token');
const _isKm=()=>(window.EInviteI18n&&window.EInviteI18n.get?window.EInviteI18n.get():(document.documentElement.lang||'').toLowerCase()).startsWith('km');
const _txt=(en,km)=>_isKm()?(km!=null?km:en):en;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const b=(en,km)=>`<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km!=null?km:en)}</span>`;
async function api(path){const r=await fetch(path,{credentials:'same-origin',headers:{}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data}
const bytes=n=>n>=1e9?`${(n/1e9).toFixed(1)} GB`:n>=1e6?`${(n/1e6).toFixed(1)} MB`:`${Math.round(n/1e3)} KB`;
let _metricsState=null;
async function init(){
  if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;
  if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){
    window.EInviteBackend.message(document.querySelector('.designer-page')||document.querySelector('main')||document.body,'<span class="i18n i18n-en">The designer workspace requires the full application server.</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">The designer workspace requires the full application server.</span>');
    return;
  }
  try{const [me,usage,templates,assets]=await Promise.all([api('/api/auth/me'),api('/api/account/usage'),api('/api/templates'),api('/api/assets')]);if(!me.user||!['designer','admin'].includes(me.user.role))throw Error('Designer or administrator access is required');_metricsState={invitations:usage.usage.invitations,templates:templates.length,materials:assets.length,storage:bytes(usage.usage.storageBytes),plan:usage.plan,enforced:usage.enforced};renderMetrics()}catch(e){
    // DESIGN-FIX P3: friendly recovery page instead of a terse dead end.
    const page=document.querySelector('.designer-page');const message=esc(e.message||'The designer workspace could not be loaded.');
    const signin=/<auth/i.test(message)||message.includes('Designer or administrator');
    page.innerHTML=`<h1>${b('Designer Workspace unavailable','កន្លែងធ្វើការអ្នករចនាមិនអាចប្រើបាន')}</h1><p class="designer-error-note">${message}</p><div class="designer-error-actions">
      ${signin?`<a href="index.html" class="button-link primary">${b('Open the design studio','Open the design studio')}</a>`:''}
      <a href="dashboard.html" class="button-link">${b('Back to dashboard','ត្រឡប់ទៅផ្ទាំងគ្រប់គ្រង')}</a>
    </div>${signin?`<p class="hint">${b('The designer workspace needs a Designer or Admin account. You can still create invitations and posters from the design studio.','The designer workspace needs a Designer or Admin account. You can still create invitations and posters from the design studio.')}</p>`:''}`}}
function renderMetrics(){if(!_metricsState)return;$('#designerMetrics').innerHTML=`<div class="workspace-metric"><strong>${_metricsState.invitations}</strong>${b('Active invitations','ការអញ្ជើញសកម្ម')}</div><div class="workspace-metric"><strong>${_metricsState.templates}</strong>${b('Reusable templates','ពុម្ពអត្ថបទ')}</div><div class="workspace-metric"><strong>${_metricsState.materials}</strong>${b('Stored materials','សម្ភារែ')}</div><div class="workspace-metric"><strong>${_metricsState.storage}</strong>${b('Storage used','បន្ទុកបានប្រើ')}</div>`;$('#designerPlanNote').textContent=_txt(`Current account plan: ${_metricsState.plan}. Usage limits are ${_metricsState.enforced?'enforced':'informational in this development build'}`,`Current account plan: ${_metricsState.plan}. Usage limits are ${_metricsState.enforced?'enforced':'informational in this development build'}`)}
function render(){renderMetrics()}
if(window.EInviteI18n&&typeof window.EInviteI18n.subscribe==='function'){window.EInviteI18n.subscribe(render)}
init();
