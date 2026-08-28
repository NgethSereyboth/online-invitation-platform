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
})();;(() => {
  'use strict';
  const RESUMABLE_THRESHOLD = 8_000_000;
  const DEFAULT_CHUNK_SIZE = 5_000_000;
  async function readJson(response) {
    return response.json().catch(() => ({}));
  }
  function abortError() {
    try { return new DOMException('Upload cancelled', 'AbortError'); }
    catch { const error = new Error('Upload cancelled'); error.name = 'AbortError'; return error; }
  }
  function cookieValue(name) {
    const prefix = `${name}=`;
    const pair = String(document.cookie || '').split(';').map(value => value.trim()).find(value => value.startsWith(prefix));
    if (!pair) return '';
    try { return decodeURIComponent(pair.slice(prefix.length)); } catch { return pair.slice(prefix.length); }
  }
  function browserMutationHeaders(url, headers = {}) {
    const output = { ...headers };
    const sameOrigin = String(url || '').startsWith('/') || (() => {
      try { return new URL(url, location.href).origin === location.origin; } catch { return false; }
    })();
    if (sameOrigin && !Object.keys(output).some(key => key.toLowerCase() === 'x-csrf-token')) {
      const token = cookieValue('einvite_csrf');
      if (token) output['X-CSRF-Token'] = token;
    }
    return output;
  }
  function xhrRequest(url, { method = 'POST', headers = {}, body = null, signal, onProgress } = {}) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, url, true);
      xhr.withCredentials = true;
      Object.entries(browserMutationHeaders(url, headers)).forEach(([key, value]) => xhr.setRequestHeader(key, value));
      if (xhr.upload && onProgress) xhr.upload.onprogress = event => {
        if (event.lengthComputable) onProgress(event.loaded, event.total);
      };
      xhr.onload = () => {
        let payload = {};
        try { payload = JSON.parse(xhr.responseText || '{}'); } catch {}
        if (xhr.status >= 200 && xhr.status < 300) resolve({ status: xhr.status, payload, xhr });
        else reject(Object.assign(new Error(payload.error || `Upload failed with HTTP ${xhr.status}`), { status: xhr.status, payload }));
      };
      xhr.onerror = () => reject(new Error('The upload connection was interrupted.'));
      xhr.onabort = () => reject(abortError());
      if (signal) {
        if (signal.aborted) return reject(abortError());
        signal.addEventListener('abort', () => xhr.abort(), { once: true });
      }
      xhr.send(body);
    });
  }
  function fontMime(file) {
    const name = String(file?.name || '').toLowerCase();
    if (name.endsWith('.ttf') || name.endsWith('.tff')) return 'font/ttf';
    if (name.endsWith('.otf')) return 'font/otf';
    if (name.endsWith('.woff2')) return 'font/woff2';
    return String(file?.type || 'application/octet-stream').toLowerCase();
  }
  async function uploadFont(invitationId, file, { name, signal, onProgress, licenseAcknowledged = false } = {}) {
    if (!invitationId) throw new Error('Choose an invitation before uploading a font.');
    if (!file) throw new Error('Choose a TTF, OTF, or WOFF2 font file.');
    const result = await xhrRequest(`/api/invitations/${encodeURIComponent(invitationId)}/fonts`, {
      method: 'POST', signal, body: file,
      headers: {
        'Content-Type': fontMime(file),
        'X-File-Name': encodeURIComponent(name || file.name || 'custom-font.ttf'),
        'X-Font-License-Acknowledged': licenseAcknowledged ? 'true' : 'false',
      },
      onProgress: (loaded, total) => onProgress?.({ loaded, total, percent: total ? Math.round(loaded / total * 100) : 0, phase: 'uploading' }),
    });
    onProgress?.({ loaded: file.size, total: file.size, percent: 100, phase: 'processing' });
    return { ...result.payload, uploadMode: 'font-optimized' };
  }
  async function rawUpload(invitationId, file, { name, signal, onProgress, folder = '', importJobId = '' } = {}) {
    const result = await xhrRequest(`/api/invitations/${encodeURIComponent(invitationId)}/assets/raw`, {
      method: 'POST', signal, body: file,
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
        'X-File-Name': encodeURIComponent(name || file.name || 'upload'),
        'X-Material-Folder': encodeURIComponent(folder || ''),
        'X-Material-Import-Job': String(importJobId || ''),
      },
      onProgress: (loaded, total) => onProgress?.({ loaded, total, percent: total ? Math.round(loaded / total * 100) : 0, phase: 'uploading' }),
    });
    return { ...result.payload, uploadMode: 'server' };
  }
  async function directUpload(invitationId, file, { name, signal, onProgress, folder = '', importJobId = '' } = {}) {
    const presign = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/presign`, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || file.name || 'upload', mime: file.type || 'application/octet-stream', size: file.size, folder, importJobId }),
    });
    if (presign.status === 409) return null;
    const signed = await readJson(presign);
    if (!presign.ok) throw new Error(signed.error || 'Could not prepare direct material upload');
    if (!signed.directUpload || !signed.uploadUrl || !signed.claim) return null;
    try {
      await xhrRequest(signed.uploadUrl, {
        method: 'PUT', signal, body: file,
        headers: signed.headers || { 'Content-Type': file.type || 'application/octet-stream' },
        onProgress: (loaded, total) => onProgress?.({ loaded, total, percent: total ? Math.round(loaded / total * 100) : 0, phase: 'uploading' }),
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new Error(`Direct storage upload failed. Check the R2/S3 CORS policy and signed-upload credentials. ${error.message || ''}`.trim());
    }
    onProgress?.({ loaded: file.size, total: file.size, percent: 100, phase: 'processing' });
    const complete = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/complete`, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || file.name || 'upload', claim: signed.claim }),
    });
    const payload = await readJson(complete);
    if (!complete.ok) throw new Error(payload.error || 'The uploaded material could not be verified and registered');
    return { ...payload, uploadMode: 'direct' };
  }
  async function resumableUpload(invitationId, file, { name, signal, onProgress, retries = 2, folder = '', importJobId = '' } = {}) {
    const start = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/uploads/start`, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || file.name || 'upload', mime: file.type || 'application/octet-stream', size: file.size, folder, importJobId }),
    });
    const session = await readJson(start);
    if (!start.ok) throw new Error(session.error || 'Could not start the resumable upload');
    const uploadId = session.uploadId;
    const chunkSize = Number(session.chunkSize || DEFAULT_CHUNK_SIZE);
    let offset = Number(session.received || 0);
    const cancelServerSession = () => fetch(`/api/uploads/${encodeURIComponent(uploadId)}`, { method: 'DELETE', credentials: 'same-origin' }).catch(() => {});
    try {
      while (offset < file.size) {
        if (signal?.aborted) throw abortError();
        const end = Math.min(file.size, offset + chunkSize);
        const chunk = file.slice(offset, end);
        let attempt = 0;
        while (true) {
          try {
            const result = await xhrRequest(`/api/uploads/${encodeURIComponent(uploadId)}`, {
              method: 'PUT', signal, body: chunk,
              headers: { 'Content-Type': 'application/octet-stream', 'X-Upload-Offset': String(offset) },
              onProgress: loaded => onProgress?.({ loaded: offset + loaded, total: file.size, percent: Math.round((offset + loaded) / file.size * 100), phase: 'uploading' }),
            });
            offset = Number(result.payload.received || end);
            break;
          } catch (error) {
            if (error.name === 'AbortError') throw error;
            if (++attempt > retries) throw error;
            const status = await fetch(`/api/uploads/${encodeURIComponent(uploadId)}`, { credentials: 'same-origin', signal }).then(readJson).catch(() => null);
            if (status && Number.isFinite(Number(status.received))) offset = Number(status.received);
            await new Promise(resolve => setTimeout(resolve, 350 * attempt));
          }
        }
      }
      onProgress?.({ loaded: file.size, total: file.size, percent: 100, phase: 'processing' });
      const complete = await fetch(`/api/uploads/${encodeURIComponent(uploadId)}/complete`, { method: 'POST', credentials: 'same-origin', signal, headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const payload = await readJson(complete);
      if (!complete.ok) throw new Error(payload.error || 'The resumable upload could not be finalized');
      return { ...payload, uploadMode: 'resumable' };
    } catch (error) {
      await cancelServerSession();
      throw error;
    }
  }
  async function upload(invitationId, file, options = {}) {
    if (!invitationId) throw new Error('Choose an invitation before uploading a material.');
    if (!file) throw new Error('Choose a file to upload.');
    if (options.signal?.aborted) throw abortError();
    const direct = options.forceServer ? null : await directUpload(invitationId, file, options);
    if (direct) return direct;
    if (file.size >= RESUMABLE_THRESHOLD) return resumableUpload(invitationId, file, options);
    return rawUpload(invitationId, file, options);
  }
  window.EInviteUpload = Object.freeze({ upload, uploadFont, rawUpload, resumableUpload, directUpload });
})();;(()=>{
'use strict';
if(window.EInviteFolderUpload?.version==='53.1')return;
const csrf=()=>{const m=document.cookie.match(/(?:^|;\s*)einvite_csrf=([^;]+)/);return m?decodeURIComponent(m[1]):''};
const abort=()=>new DOMException('Upload cancelled.','AbortError');
const folder=v=>String(v||'').replace(/\\/g,'/').split('/').filter(x=>x&&x!=='.').join('/');
const json=async r=>{try{return await r.json()}catch{return{}}};
const governedHeaders=value=>value&&typeof value==='object'?Object.fromEntries(Object.entries(value).filter(([,item])=>item!=null)):{};
function xhr(path,{body,signal,headers={},onProgress}={}){
 return new Promise((resolve,reject)=>{
  const x=new XMLHttpRequest();x.open('POST',path,true);x.withCredentials=true;
  for(const[k,v]of Object.entries(headers))if(v!=null)x.setRequestHeader(k,v);
  const c=csrf();if(c)x.setRequestHeader('X-CSRF-Token',c);
  x.upload.onprogress=e=>onProgress?.(e.loaded,e.lengthComputable?e.total:0);
  x.onerror=()=>reject(Error('Network error during upload'));
  x.onload=()=>{let p={};try{p=JSON.parse(x.responseText||'{}')}catch{};x.status>=200&&x.status<300?resolve(p):reject(Object.assign(Error(p.error||`Upload failed (${x.status})`),{status:x.status,payload:p}))};
  const stop=()=>{try{x.abort()}catch{}reject(abort())};if(signal?.aborted)return stop();signal?.addEventListener('abort',stop,{once:true});x.send(body)
 })
}
async function uploadFolder(invitationId,files,{signal,onProgress,rootName='',authorizationHeaders={}}={}){
 const list=Array.from(files||[]);if(!list.length)throw Error('Choose a folder with at least one supported material.');
 const manifest=list.map(file=>{const parts=String(file.webkitRelativePath||file.name||'').replace(/\\/g,'/').split('/');parts.pop();return{name:file.name,folder:folder(parts.join('/')),size:file.size,mime:file.type||'application/octet-stream'}});
 const first=String(list[0]?.webkitRelativePath||'').replace(/\\/g,'/'),root=rootName||(first.includes('/')?first.split('/')[0]:'');
 const r=await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/materials/import-jobs`,{method:'POST',credentials:'same-origin',signal,headers:{'Content-Type':'application/json',...(csrf()?{'X-CSRF-Token':csrf()}:{}),...governedHeaders(authorizationHeaders)},body:JSON.stringify({rootName:root,files:manifest,emptyDirectories:[]})}),job=await json(r);
 if(!r.ok)throw Error(job.error||'Could not prepare the folder import');
 let completed=0,failed=0,uploadedBytes=0;const failures=[],failedIndexes=[];
 const cancel=async()=>{try{await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/materials/import-jobs/${encodeURIComponent(job.id)}`,{method:'DELETE',credentials:'same-origin',headers:csrf()?{'X-CSRF-Token':csrf()}:{}})}catch{}};
 for(let i=0;i<list.length;i++){
  const file=list[i];if(signal?.aborted){await cancel();throw abort()}
  const parts=String(file.webkitRelativePath||file.name||'').replace(/\\/g,'/').split('/');parts.pop();const dir=folder(parts.join('/'));
  try{
   await window.EInviteUpload.upload(invitationId,file,{signal,name:file.name,folder:dir,importJobId:job.id,forceServer:true,onProgress:s=>onProgress?.({...s,currentFile:file.name,completedFiles:completed,failedFiles:failed,totalFiles:list.length,uploadedBytes})});completed++;uploadedBytes+=Number(file.size||0)
  }catch(e){
   if(e.name==='AbortError'){await cancel();throw e}failed++;failedIndexes.push(i);const f={name:file.name,folder:dir,size:Number(file.size||0),error:String(e.message||e).slice(0,300)};failures.push(f);
   try{await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/materials/import-jobs/${encodeURIComponent(job.id)}/failure`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json',...(csrf()?{'X-CSRF-Token':csrf()}:{})},body:JSON.stringify(f)})}catch{}
  }
  onProgress?.({phase:'batch',percent:Math.round((completed+failed)/list.length*100),currentFile:file.name,completedFiles:completed,failedFiles:failed,totalFiles:list.length,uploadedBytes})
 }
 return{...job,completedFiles:completed,failedFiles:failed,failures,failedIndexes,status:failed?'completed-with-errors':'completed'}
}
async function importZip(invitationId,file,{signal,onProgress,rootName='',authorizationHeaders={}}={}){
 if(!file)throw Error('Choose a ZIP archive.');
 return xhr(`/api/invitations/${encodeURIComponent(invitationId)}/materials/import-zip`,{body:file,signal,headers:{'Content-Type':'application/zip','X-File-Name':encodeURIComponent(file.name||'materials.zip'),'X-Material-Root':encodeURIComponent(rootName||''),...governedHeaders(authorizationHeaders)},onProgress:(loaded,total)=>onProgress?.({loaded,total,percent:total?Math.round(loaded/total*100):0,phase:'uploading-archive'})})
}
const api=Object.freeze({version:'53.1',uploadFolder,importZip});window.EInviteFolderUpload=api;
if(window.EInviteUpload&&!Object.isFrozen(window.EInviteUpload))Object.assign(window.EInviteUpload,api);else if(window.EInviteUpload)window.EInviteUpload=Object.freeze({...window.EInviteUpload,uploadFolder,importZip});
})();;(()=>{
 'use strict';
 const LAST_KEY='sovan-active-invite';
 const routeMatch=location.pathname.match(/\/invitations\/([^/]+)\/(editor|guests|responses|analytics|materials|checkin)\/?$/i);
 const queryId=new URLSearchParams(location.search).get('invitation');
 const routeId=routeMatch?decodeURIComponent(routeMatch[1]):'';
 const explicitId=routeId||queryId||'';
 const section=routeMatch?.[2]?.toLowerCase()||'';
 const safe=id=>String(id||'').trim();
 function getInvitationId(options={}){const direct=safe(explicitId);if(direct)return direct;if(options.allowRemembered===false)return '';return safe(localStorage.getItem(LAST_KEY))}
 function remember(id){id=safe(id);if(id)localStorage.setItem(LAST_KEY,id);return id}
 function route(id,target='editor'){
   id=safe(id);target=String(target||'editor').toLowerCase();
   if(!id)return target==='materials'?'materials.html':'dashboard.html';
   const allowed=new Set(['editor','guests','responses','analytics','materials','checkin']);if(!allowed.has(target))target='editor';
   if(window.EInviteBackend?.state?.status==='offline')return window.EInviteBackend.staticUrl(id,target);
   return `/invitations/${encodeURIComponent(id)}/${target}`;
 }
 async function navigate(id,target='editor'){remember(id);if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;location.href=route(id,target)}
 if(explicitId)remember(explicitId);
 async function rewriteInvitationLinks(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;const id=getInvitationId({allowRemembered:false});if(!id)return;const map={'index.html':'editor','guests.html':'guests','responses.html':'responses','analytics.html':'analytics','materials.html':'materials','checkin.html':'checkin'};document.querySelectorAll('a[href]').forEach(anchor=>{const raw=anchor.getAttribute('href')||'';const base=raw.split('?')[0].split('#')[0].replace(/^\.\//,'');const target=map[base];if(target)anchor.setAttribute('href',route(id,target))})}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',rewriteInvitationLinks,{once:true});else rewriteInvitationLinks();
 window.EInviteContext={getInvitationId,remember,route,navigate,section,explicitId,rewriteInvitationLinks};
})();;const $=s=>document.querySelector(s);localStorage.removeItem('sovan-auth-token');const contextInviteId=window.EInviteContext?.getInvitationId({allowRemembered:false})||'';let materials=[],invitations=[];
async function api(path,options={}){const response=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}});const payload=await response.json().catch(()=>({}));if(!response.ok)throw Error(payload.error||'Request failed');return payload}
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const formatBytes=n=>{n=Number(n||0);if(n<1024)return`${n} B`;if(n<1024**2)return`${(n/1024).toFixed(1)} KB`;return`${(n/1024**2).toFixed(1)} MB`};
function typeOf(item){return item.mime?.startsWith('image/')?'image':item.mime?.startsWith('audio/')?'audio':item.mime?.startsWith('video/')?'video':item.mime?.startsWith('font/')?'font':'other'}
async function load(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){window.EInviteBackend.message($('#grid'),'Material storage and uploads require the full application server.');$('#uploadBtn').disabled=true;$('#uploadFile').disabled=true;$('#uploadFolderBtn').disabled=true;$('#uploadFolder').disabled=true;$('#uploadZipBtn').disabled=true;$('#uploadZip').disabled=true;return}try{[materials,invitations]=await Promise.all([api('/api/assets'),api('/api/invitations')]);renderInvitationOptions();render()}catch(error){$('#grid').innerHTML=`<div class="empty-library"><h2>Material library unavailable</h2><p>${esc(error.message)}</p></div>`}}
function renderInvitationOptions(){const select=$('#uploadInvitation');select.innerHTML=invitations.filter(i=>!i.archived).map(i=>`<option value="${esc(i.id)}">${esc(i.title||i.slug||'Invitation')}</option>`).join('');if(!select.options.length)select.innerHTML='<option value="">Create an invitation first</option>';if(contextInviteId&&[...select.options].some(o=>o.value===contextInviteId))select.value=contextInviteId}
function filtered(){const q=$('#search').value.trim().toLowerCase(),folder=$('#folderFilter').value.trim().toLowerCase(),type=$('#typeFilter').value,sort=$('#sort').value;let list=materials.filter(item=>{if(contextInviteId&&item.invitationId!==contextInviteId)return false;const kind=typeOf(item),hay=[item.name,item.folder,...(item.tags||[])].join(' ').toLowerCase();return(!q||hay.includes(q))&&(!folder||String(item.folder||'').toLowerCase().includes(folder))&&(type==='all'||type===kind||(type==='favorite'&&item.favorite))});list.sort((a,b)=>sort==='oldest'?a.createdAt-b.createdAt:sort==='name'?String(a.name).localeCompare(String(b.name)):sort==='size'?b.size-a.size:b.createdAt-a.createdAt);return list}
function render(){const list=filtered(),bytes=materials.reduce((sum,x)=>sum+Number(x.size||0),0),favorites=materials.filter(x=>x.favorite).length;$('#summary').innerHTML=`<span>${materials.length} materials</span><span>${formatBytes(bytes)} stored</span><span>${favorites} favorite${favorites===1?'':'s'}</span><span>${list.length} shown</span>`;const grid=$('#grid');if(!list.length){grid.innerHTML='<div class="empty-library"><h2>No matching materials</h2><p>Upload a file or change your filters.</p></div>';return}grid.innerHTML=list.map(item=>{const kind=typeOf(item),thumb=kind==='image'?`<img src="${esc(item.url)}" alt="">`:kind==='video'?`<video src="${esc(item.url)}" muted preload="metadata"></video>`:kind==='font'?`<span class="audio-mark" aria-label="Font file">Aa</span>`:`<span class="audio-mark">♫</span>`;return`<article class="material-card-page"><div class="material-thumb">${thumb}${item.favorite?'<span class="favorite-mark">★</span>':''}</div><div class="material-info"><strong title="${esc(item.name)}">${esc(item.name)}</strong><div class="library-folder">${item.folder?`Folder: ${esc(item.folder)}`:'No folder'} · ${formatBytes(item.size)}</div><div class="material-tags">${(item.tags||[]).slice(0,5).map(tag=>`<span>${esc(tag)}</span>`).join('')}</div></div><div class="actions"><a href="${esc(item.url)}" target="_blank" rel="noopener" class="button-link">Open</a><button data-edit="${esc(item.id)}" type="button">Edit</button></div></article>`}).join('');grid.querySelectorAll('[data-edit]').forEach(button=>button.onclick=()=>openEdit(button.dataset.edit))}
function openEdit(id){const item=materials.find(x=>x.id===id);if(!item)return;$('#editId').value=id;$('#editName').value=item.name||'';$('#editFolder').value=item.folder||'';$('#editTags').value=(item.tags||[]).join(', ');$('#editFavorite').checked=!!item.favorite;$('#editMeta').textContent=`${item.mime} · ${formatBytes(item.size)} · uploaded ${new Date(item.createdAt).toLocaleString()}`;$('#editDialog').showModal()}
$('#editForm').onsubmit=async e=>{e.preventDefault();const id=$('#editId').value,item=materials.find(x=>x.id===id);if(!item)return;try{const updated=await api('/api/assets/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify({name:$('#editName').value.trim(),folder:$('#editFolder').value.trim(),tags:$('#editTags').value.split(',').map(x=>x.trim()).filter(Boolean),favorite:$('#editFavorite').checked})});Object.assign(item,updated);$('#editDialog').close();render()}catch(error){alert(error.message)}};
$('#deleteBtn').onclick=async()=>{const id=$('#editId').value,item=materials.find(x=>x.id===id);if(!item||!(await uiConfirm(`Remove “${item.name}” from this invitation? The stored file is deleted only after its final invitation reference is removed.`,{title:'Delete material',danger:true,confirmText:'Delete permanently'})))return;try{await api(`/api/invitations/${item.invitationId}/assets/${id}`,{method:'DELETE'});materials=materials.filter(x=>x.id!==id);$('#editDialog').close();render()}catch(error){alert(error.message)}};
$('#cancelEdit').onclick=()=>$('#editDialog').close();
const allowedUploadTypes=['image/jpeg','image/png','image/webp','image/gif','audio/mpeg','audio/mp4','video/mp4','video/webm'];
let activeUploadController=null,lastFailedFiles=[],lastFailedMode="files";
async function uploadMaterialFiles(files){
 const inviteId=$('#uploadInvitation').value,list=[...files];
 if(!inviteId)return alert('Create or select an invitation first.');
 if(!list.length)return alert('Choose one or more files to upload.');
 for(const file of list){
  if(!allowedUploadTypes.includes(file.type))return alert(`Unsupported file type: ${file.name}`);
  const limit=file.type.startsWith('video/')?50e6:15e6;
  if(file.size>limit)return alert(`${file.name} exceeds the ${limit/1e6} MB limit.`)
 }
 const progress=$('.progress-line'),status=$('#uploadStatus'),actions=$('#uploadActions'),cancel=$('#cancelUpload'),retry=$('#retryUpload');
 progress.hidden=false;actions.hidden=false;retry.hidden=true;lastFailedFiles=[];lastFailedMode="files";activeUploadController=new AbortController();
 cancel.disabled=false;cancel.textContent='Cancel upload';
 try{
  for(let index=0;index<list.length;index++){
   const file=list[index],base=index/list.length;
   status.textContent=`Uploading ${file.name} (${index+1} of ${list.length})`;
   const payload=await window.EInviteUpload.upload(inviteId,file,{name:file.name,signal:activeUploadController.signal,onProgress:info=>{
    const overall=Math.round((base+(Math.max(0,Math.min(100,Number(info.percent||0)))/100)/list.length)*100);
    $('#uploadProgress').style.width=`${Math.max(2,overall)}%`;
    status.textContent=info.phase==='processing'?`Checking and processing ${file.name}…`:`Uploading ${file.name} · ${info.percent||0}%`;
   }});
   if(payload.duplicate)window.uiToast?.(`${file.name} already existed — reused stored file`,'↻');
   else if(payload.uploadMode==='direct')window.uiToast?.(`${file.name} uploaded directly to object storage`,'↑');
   $('#uploadProgress').style.width=`${Math.round((index+1)/list.length*100)}%`
  }
  status.textContent=`Uploaded ${list.length} file${list.length===1?'':'s'} successfully.`;$('#uploadFile').value='';materials=await api('/api/assets');render();
  setTimeout(()=>{progress.hidden=true;actions.hidden=true;$('#uploadProgress').style.width='0'},800)
 }catch(error){
  const cancelled=error?.name==='AbortError';status.textContent=cancelled?'Upload cancelled.':`Upload failed: ${error.message}`;lastFailedFiles=cancelled?[]:list;retry.hidden=!lastFailedFiles.length;cancel.disabled=true;$('#uploadProgress').style.width='0';
 }finally{activeUploadController=null}
}
async function importMaterialFolder(files){
 const inviteId=$('#uploadInvitation').value,list=[...files];
 if(!inviteId)return alert('Create or select an invitation first.');
 if(!list.length)return alert('Choose a materials folder first.');
 for(const file of list){if(!allowedUploadTypes.includes(file.type))return alert(`Unsupported material in folder: ${file.webkitRelativePath||file.name}`)}
 const progress=$('.progress-line'),status=$('#uploadStatus'),actions=$('#uploadActions'),cancel=$('#cancelUpload'),retry=$('#retryUpload');
 progress.hidden=false;actions.hidden=false;retry.hidden=true;lastFailedFiles=[];lastFailedMode="folder";activeUploadController=new AbortController();cancel.disabled=false;
 try{
  const result=await window.EInviteUpload.uploadFolder(inviteId,list,{signal:activeUploadController.signal,onProgress:info=>{
   $('#uploadProgress').style.width=`${Math.max(2,Number(info.percent||0))}%`;
   status.textContent=info.phase==='batch'?`Folder import: ${info.completedFiles||0} complete, ${info.failedFiles||0} failed of ${info.totalFiles||list.length}.`:`Importing ${info.currentFile||'folder'} · ${info.percent||0}%`;
  }});
  status.textContent=result.failedFiles?`Folder import finished with ${result.failedFiles} failed file(s).`:`Imported ${result.completedFiles} file(s) with folder structure preserved.`;
  $('#uploadFolder').value='';materials=await api('/api/assets');render();
  if(result.failures?.length){console.warn('Folder import failures',result.failures);lastFailedFiles=(result.failedIndexes||[]).map(index=>list[index]).filter(Boolean);lastFailedMode='folder';retry.hidden=!lastFailedFiles.length;}
  if(!lastFailedFiles.length)setTimeout(()=>{progress.hidden=true;actions.hidden=true;$('#uploadProgress').style.width='0'},1000);
 }catch(error){status.textContent=error?.name==='AbortError'?'Folder import cancelled.':`Folder import failed: ${error.message}`;cancel.disabled=true;$('#uploadProgress').style.width='0'}finally{activeUploadController=null}
}
async function importMaterialZip(file){
 const inviteId=$('#uploadInvitation').value;if(!inviteId)return alert('Create or select an invitation first.');if(!file)return alert('Choose a ZIP archive first.');
 const progress=$('.progress-line'),status=$('#uploadStatus'),actions=$('#uploadActions'),cancel=$('#cancelUpload'),retry=$('#retryUpload');
 progress.hidden=false;actions.hidden=false;retry.hidden=true;activeUploadController=new AbortController();cancel.disabled=false;
 try{
  const result=await window.EInviteUpload.importZip(inviteId,file,{signal:activeUploadController.signal,onProgress:info=>{$('#uploadProgress').style.width=`${Math.max(2,Number(info.percent||0))}%`;status.textContent=`Uploading ZIP · ${info.percent||0}%`;}});
  status.textContent=result.failedCount?`ZIP import created ${result.createdCount} material(s); ${result.failedCount} unsupported or invalid file(s) were skipped.`:`ZIP import created ${result.createdCount} material(s) with nested folders preserved.`;
  $('#uploadZip').value='';materials=await api('/api/assets');render();setTimeout(()=>{progress.hidden=true;actions.hidden=true;$('#uploadProgress').style.width='0'},1200);
 }catch(error){status.textContent=error?.name==='AbortError'?'ZIP import cancelled.':`ZIP import failed: ${error.message}`;cancel.disabled=true;$('#uploadProgress').style.width='0'}finally{activeUploadController=null}
}
$('#uploadFolderBtn').onclick=()=>importMaterialFolder($('#uploadFolder').files||[]);
$('#uploadZipBtn').onclick=()=>importMaterialZip($('#uploadZip').files?.[0]);
$('#cancelUpload').onclick=()=>activeUploadController?.abort();
$('#retryUpload').onclick=()=>lastFailedFiles.length&&(lastFailedMode==='folder'?importMaterialFolder(lastFailedFiles):uploadMaterialFiles(lastFailedFiles));
$('#uploadBtn').onclick=()=>uploadMaterialFiles($('#uploadFile').files||[]);
window.uploadMaterialFiles=uploadMaterialFiles;
['search','folderFilter'].forEach(id=>$('#'+id).oninput=render);['typeFilter','sort'].forEach(id=>$('#'+id).onchange=render);$('#refreshBtn').onclick=load;load();;(function(){
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
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
function dashboardFinal(){
  const grid=$('#inviteGrid'),view=$('#dashboardView'),header=$('body>header'); if(!grid||!view)return;
  const getInvites=()=>{try{return Array.isArray(invites)?invites:[]}catch{return[]}};
  const findInvite=id=>getInvites().find(x=>String(x.id)===String(id));
  const localDoc=id=>{try{return JSON.parse(localStorage.getItem(`sovan-invite-draft-v3:${id}`)||'null')}catch{return null}};
  const previewDoc=item=>item?.preview||localDoc(item?.id)||null;
  function buildPreview(item){
    const doc=previewDoc(item)||{},palette=doc.palette||{},fields=doc.fields||{},page0=(doc.designPages||[])[0]||null,objects=page0?.objects||doc.objects||{};
    const bg=page0?.background||doc.masterPageStyle?.background||palette.background||'#fff7f3',text=palette.text||'#342c26',heading=palette.heading||doc.accent||'#9d4555',accent=doc.accent||heading;
    const shell=document.createElement('div');shell.className='fp-project-preview';shell.style.setProperty('--preview-shell',`color-mix(in srgb, ${bg} 52%, var(--app-surface-2))`);
    const art=document.createElement('div');art.className='fp-project-artboard v20-faithful-thumbnail';art.style.setProperty('--preview-bg',bg);art.style.setProperty('--preview-text',text);art.style.setProperty('--preview-heading',heading);art.style.setProperty('--preview-accent',accent);art.style.background=bg;
    if(Object.keys(objects).length&&globalThis.EInviteTypographyRendererAdapters&&!art.closest('.invite-card')){TypographyDocumentModel?.normalizeDocument?.(doc,{mutate:true});art._typographyThumbnailController?.disconnect?.();art._typographyThumbnailController=EInviteTypographyRendererAdapters.renderThumbnail(art,doc,objects,{width:390,height:844})}
    else{const f=document.createElement('div');f.className='fp-thumb-fallback';f.innerHTML=`<small>${esc(doc.eventType||item.type||'Invitation')}</small><strong>${esc(fields.names||item.title||'Untitled invitation')}</strong><span>${esc(fields.date||'')} ${fields.venue?`· ${esc(fields.venue)}`:''}</span>`;art.append(f)}
    shell.append(art);return shell;
  }
  const timeAgo=value=>{const t=Number(value)||Date.parse(value)||0;if(!t)return'';const sec=Math.max(0,Math.round((Date.now()-t)/1000));if(sec<60)return'Edited just now';if(sec<3600)return`Edited ${Math.floor(sec/60)}m ago`;if(sec<86400)return`Edited ${Math.floor(sec/3600)}h ago`;if(sec<604800)return`Edited ${Math.floor(sec/86400)}d ago`;return`Edited ${new Date(t).toLocaleDateString()}`};
  function decorateCard(card){
    if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit;if(!id)return;const item=findInvite(id);if(!item)return;card.dataset.fpReady='1';card.dataset.inviteId=id;
    const cover=$('.invite-cover',card);if(cover){cover.replaceChildren(buildPreview(item));const status=document.createElement('span');status.className='fp-project-status';status.textContent=item.status||'Draft';cover.append(status);cover.onclick=()=>{if(!item.archived)card.querySelector('.actions [data-edit]')?.click()}}
    const body=$('.invite-body',card),stats=$('.stats',card),actions=$('.actions',card);if(!body||!actions)return;
    if(stats)stats.innerHTML=`<span>${esc(item.status||'Draft')}</span><span>${esc(timeAgo(item.updatedAt))}</span>`;
    const more=document.createElement('button');more.type='button';more.className='fp-project-more';more.setAttribute('aria-label','Project actions');more.setAttribute('aria-expanded','false');more.textContent='•••';
    const menu=document.createElement('div');menu.className='fp-project-menu';menu.setAttribute('role','menu');
    const map=[['Edit','[data-edit]'],['Guests','[data-guests]'],['Responses','[data-responses]'],['Analytics','[data-analytics]'],['Duplicate','[data-copy]'],[item.archived?'Restore':'Archive','[data-archive]'],['Delete','[data-delete]']];
    map.forEach(([label,selector])=>{const source=$(selector,actions);if(!source)return;const b=document.createElement('button');b.type='button';b.textContent=label;if(label==='Delete')b.className='danger';b.onclick=e=>{e.stopPropagation();menu.classList.remove('open');more.setAttribute('aria-expanded','false');source.click()};menu.append(b)});
    more.onclick=e=>{e.stopPropagation();$$('.fp-project-menu.open').filter(x=>x!==menu).forEach(x=>x.classList.remove('open'));menu.classList.toggle('open');more.setAttribute('aria-expanded',menu.classList.contains('open')?'true':'false')};
    body.append(more);card.append(menu);
  }
  const refresh=()=>$$('.invite-card',grid).forEach(decorateCard);new MutationObserver(refresh).observe(grid,{childList:true,subtree:true});refresh();
  document.addEventListener('click',()=>$$('.fp-project-menu.open').forEach(x=>x.classList.remove('open')));
  if(header&&!$('.fp-dashboard-profile',header)){
    const wrap=document.createElement('div');wrap.className='fp-dashboard-profile';wrap.innerHTML=`<button type="button" class="fp-profile-button" aria-label="Account menu">U</button><div class="fp-profile-popover"><div class="fp-profile-summary"><strong>Account</strong><small></small></div><a href="account.html">Account settings</a><a href="materials.html">Materials</a><a href="billing.html">Plans & usage</a><a href="designer.html" data-profile-designer hidden>Designer workspace</a><a href="admin.html" data-profile-admin hidden>Administration</a><button type="button" data-signout>Sign out</button></div>`;header.append(wrap);
    const button=$('.fp-profile-button',wrap),pop=$('.fp-profile-popover',wrap);button.onclick=e=>{e.stopPropagation();pop.classList.toggle('open')};pop.onclick=e=>e.stopPropagation();$('[data-signout]',wrap).onclick=()=>$('#logoutBtn')?.click();
    const update=()=>{let a=null;try{a=account}catch{}const email=a?.email||'Account';$('.fp-profile-summary strong',wrap).textContent=email;$('.fp-profile-summary small',wrap).textContent=[a?.role,a?.plan].filter(Boolean).join(' · ');button.textContent=(email[0]||'U').toUpperCase();$('[data-profile-designer]',wrap).hidden=!['designer','admin'].includes(a?.role);$('[data-profile-admin]',wrap).hidden=a?.role!=='admin';wrap.hidden=view.hidden};new MutationObserver(update).observe(view,{attributes:true,attributeFilter:['hidden']});update();document.addEventListener('click',()=>pop.classList.remove('open'));
  }
}
function materialsFinal(){
  const grid=$('#grid');if(!grid)return;
  let dialog=null;
  function itemById(id){try{return materials.find(x=>String(x.id)===String(id))}catch{return null}}
  function inviteName(id){try{return invitations.find(x=>String(x.id)===String(id))?.title||invitations.find(x=>String(x.id)===String(id))?.slug||'Invitation'}catch{return'Invitation'}}
  function ensureDialog(){if(dialog)return dialog;dialog=document.createElement('dialog');dialog.className='fp-material-preview-dialog';document.body.append(dialog);return dialog}
  function openPreview(item){if(!item)return;const kind=item.mime?.startsWith('image/')?'image':item.mime?.startsWith('video/')?'video':item.mime?.startsWith('audio/')?'audio':'file',d=ensureDialog();
    let media=kind==='image'?`<img src="${esc(item.url)}" alt="${esc(item.name)}">`:kind==='video'?`<video src="${esc(item.url)}" controls preload="metadata"></video>`:kind==='audio'?`<div><div class="fp-material-audio-art">♫</div><audio src="${esc(item.url)}" controls preload="metadata"></audio></div>`:`<div class="fp-material-audio-art">◇</div>`;
    d.innerHTML=`<div class="fp-material-preview-shell"><div class="fp-material-stage">${media}</div><aside class="fp-material-detail"><div class="fp-material-detail-head"><h2>${esc(item.name)}</h2><button type="button" class="fp-material-close">×</button></div><div class="fp-material-facts"><div><span>Type</span><strong>${esc(item.mime||'Unknown')}</strong></div><div><span>Size</span><strong>${typeof formatBytes==='function'?formatBytes(item.size):esc(item.size)}</strong></div><div><span>Invitation</span><strong>${esc(inviteName(item.invitationId))}</strong></div><div><span>Folder</span><strong>${esc(item.folder||'No folder')}</strong></div><div><span>Used</span><strong>${Number(item.usageCount||0)} reference${Number(item.usageCount||0)===1?'':'s'}</strong></div></div><div class="fp-material-preview-actions"><button type="button" class="primary" data-use>Use in design</button><div class="fp-material-secondary-actions"><button type="button" data-edit> Edit details</button><a href="${esc(item.url)}" download target="_blank" rel="noopener" class="button-link">Download</a></div><button type="button" class="fp-material-danger" data-delete>Delete material</button></div></aside></div>`;
    $('.fp-material-close',d).onclick=()=>d.close();$('[data-edit]',d).onclick=()=>{d.close();try{openEdit(item.id)}catch{grid.querySelector(`[data-edit="${CSS.escape(String(item.id))}"]`)?.click()}};$('[data-delete]',d).onclick=()=>{d.close();try{openEdit(item.id);setTimeout(()=>$('#deleteBtn')?.click(),40)}catch{}};$('[data-use]',d).onclick=()=>{localStorage.setItem('sovan-active-invite',item.invitationId);localStorage.setItem('einvite-pending-material-insert',JSON.stringify({url:item.url,name:item.name,mime:item.mime,assetId:item.id}));location.href=`/invitations/${encodeURIComponent(item.invitationId)}/editor`};d.showModal();
  }
  function decorate(){
    const empty=$('.empty-library',grid);if(empty&&/Authentication required|sign in|unauthorized/i.test(empty.textContent)){document.body.classList.add('material-auth-required');grid.innerHTML=`<div class="fp-material-auth-state"><div class="fp-material-auth-card"><div class="icon">◌</div><h2>Your session has expired</h2><p>Sign in again to access your photos, videos, audio, folders, and saved materials.</p><a href="dashboard.html" class="button-link primary">Sign in again</a></div></div>`;return}else document.body.classList.remove('material-auth-required');
    $$('.material-card-page',grid).forEach(card=>{if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit,item=itemById(id);if(!item)return;card.dataset.fpReady='1';const thumb=$('.material-thumb',card);if(thumb)thumb.onclick=()=>openPreview(item);const info=$('.material-info',card);if(info){const row=document.createElement('div');row.className='fp-material-meta-row';row.innerHTML=`<span>${item.mime?.split('/')[0]||'file'}</span>${Number(item.usageCount||0)?`<span class="fp-material-usage">Used ${Number(item.usageCount)}</span>`:''}`;info.append(row)}})
  }
  new MutationObserver(decorate).observe(grid,{childList:true,subtree:true});decorate();
}
function editorFinal(){
  const stage=$('#stage'),host=$('.studio-pane-host'),rail=$('.studio-tool-rail');if(!stage||!host||!rail)return;
  const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};const choose=o=>{try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([o])}catch{}};
  const makeId=p=>`${p}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
  const closePaneOnMobile=()=>{if(innerWidth<=820&&document.body.classList.contains('studio-design-mode'))document.body.classList.add('mobile-pane-collapsed')};
  const openPane=()=>document.body.classList.remove('mobile-pane-collapsed');
  rail.addEventListener('click',openPane,true);
  if(!$('.fp-mobile-pane-handle')){const h=document.createElement('button');h.type='button';h.className='fp-mobile-pane-handle';h.textContent='›';h.title='Open creation panel';h.onclick=openPane;document.body.append(h)}
  $$('.studio-pane-heading',host).forEach(head=>{if(head.querySelector('.fp-mobile-pane-close'))return;const b=document.createElement('button');b.type='button';b.className='fp-mobile-pane-close';b.textContent='‹';b.title='Hide panel';b.onclick=closePaneOnMobile;head.append(b)});
  function addSvgAsset(asset){if(typeof createObject!=='function')return;const o=createObject(makeId('graphic'),'image');const data=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(asset.svg)}`;o.style.left=asset.left||'18%';o.style.top=asset.top||'24%';o.style.width=asset.width||'64%';o.style.height=asset.height||'190px';o.dataset.src=data;o.dataset.layerName=asset.name;o.dataset.showInGallery='false';o.dataset.showInHero='true';const img=o.querySelector('img');if(img){img.src=data;img.alt=asset.name}stage.append(o);choose(o);saveNow();window.uiToast?.(`${asset.name} added`,'✦');closePaneOnMobile()}
  const assets=[
    {name:'Khmer lotus corner',cat:'Khmer',width:'38%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220"><g fill="none" stroke="#b48735" stroke-width="5" stroke-linecap="round"><path d="M20 200C82 190 110 154 113 92M20 200c52-42 90-49 154-44"/><path d="M113 92c-29 21-44 51-40 84 28-10 51-31 64-61 12 29 35 49 65 58 1-34-15-63-45-83-1 31-8 57-20 77-13-20-21-45-24-75Z"/><path d="M174 156c38-12 72-9 120 21M205 148c18-18 31-40 36-68"/></g></svg>`},
    {name:'Royal gold flourish',cat:'Wedding',height:'120px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160"><g fill="none" stroke="#c5a15b" stroke-width="5"><path d="M18 82c110 0 124-58 210-58 48 0 57 38 72 58 15-20 24-58 72-58 86 0 100 58 210 58"/><path d="M22 84c110 0 126 54 218 54 32 0 49-18 60-48 11 30 28 48 60 48 92 0 108-54 218-54"/><circle cx="300" cy="82" r="12" fill="#c5a15b"/></g></svg>`},
    {name:'Botanical sprig',cat:'Botanical',width:'34%',height:'250px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 380"><g fill="none" stroke="#527760" stroke-width="5" stroke-linecap="round"><path d="M68 350C102 254 128 162 196 40"/><path d="M111 237c-58 4-84-23-91-59 44-7 76 11 98 44M137 176c-9-52 10-83 49-101 15 40 7 74-31 106M85 293c-43 4-67-15-76-47 34-8 64 2 83 31M169 116c-5-39 10-65 43-79 11 32 4 58-24 82"/></g></svg>`},
    {name:'Wedding arch',cat:'Wedding',width:'66%',height:'300px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 620"><path d="M80 600V270C80 120 145 30 250 30s170 90 170 240v330" fill="none" stroke="#b58a5a" stroke-width="10"/><g fill="#d9aeb3"><circle cx="93" cy="240" r="24"/><circle cx="112" cy="192" r="18"/><circle cx="392" cy="215" r="24"/><circle cx="370" cy="165" r="17"/></g><g fill="#6f8d72"><ellipse cx="126" cy="230" rx="12" ry="34" transform="rotate(45 126 230)"/><ellipse cx="374" cy="240" rx="12" ry="34" transform="rotate(-45 374 240)"/></g></svg>`},
    {name:'Diamond frame',cat:'Frames',width:'58%',height:'320px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500"><path d="M250 18 482 250 250 482 18 250Z" fill="none" stroke="#c6a35b" stroke-width="9"/><path d="M250 46 454 250 250 454 46 250Z" fill="none" stroke="#c6a35b" stroke-width="2" opacity=".7"/></svg>`},
    {name:'Lotus divider',cat:'Khmer',height:'110px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 150"><g fill="none" stroke="#a87616" stroke-width="4"><path d="M20 75h250M430 75h250"/><path d="M350 28c-24 18-36 40-35 66 17-6 29-18 35-36 6 18 18 30 35 36 1-26-11-48-35-66Z"/><path d="M350 44c-12 13-18 28-18 44 8-3 14-9 18-18 4 9 10 15 18 18 0-16-6-31-18-44Z"/></g></svg>`},
    {name:'Celebration confetti',cat:'Celebration',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 320"><g fill="none" stroke-linecap="round" stroke-width="10"><path d="M55 55l32 30M420 44l-28 36M118 258l35-17M380 263l-36-23" stroke="#ff5d8f"/><path d="M158 38l-8 42M328 45l18 39M58 180l44-4M410 170l34 12" stroke="#50b9d6"/><path d="M235 34l8 44M255 263l-5 38" stroke="#7d59d4"/></g><g fill="#f2b84b"><circle cx="101" cy="122" r="10"/><circle cx="395" cy="112" r="9"/><circle cx="205" cy="238" r="8"/></g></svg>`},
    {name:'Executive wave',cat:'Business',height:'150px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 180"><path d="M0 132C120 46 205 36 330 104c109 59 229 45 370-46v122H0Z" fill="#173e58"/><path d="M0 154C140 82 222 76 344 132c104 48 216 38 356-30v78H0Z" fill="#20a49b" opacity=".78"/></svg>`},
    {name:'Rose corner',cat:'Wedding',width:'36%',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 300"><g fill="#d48d9c"><circle cx="82" cy="82" r="38"/><circle cx="120" cy="58" r="30"/><circle cx="131" cy="101" r="34"/></g><g fill="#6d8b70"><ellipse cx="186" cy="85" rx="24" ry="54" transform="rotate(48 186 85)"/><ellipse cx="98" cy="176" rx="22" ry="60" transform="rotate(12 98 176)"/></g><path d="M20 282C66 210 107 151 178 96" fill="none" stroke="#6d8b70" stroke-width="7"/></svg>`},
    {name:'Minimal line frame',cat:'Frames',width:'72%',height:'360px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700"><rect x="18" y="18" width="464" height="664" rx="18" fill="none" stroke="#65535f" stroke-width="3"/><rect x="38" y="38" width="424" height="624" rx="12" fill="none" stroke="#65535f" stroke-width="1" opacity=".55"/></svg>`},
    {name:'Star sparkle cluster',cat:'Celebration',width:'34%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 260"><g fill="#c69d55"><path d="m150 18 14 57 56 14-56 14-14 57-14-57-56-14 56-14Z"/><path d="m240 126 8 30 30 8-30 8-8 30-8-30-30-8 30-8Z" opacity=".72"/><circle cx="66" cy="182" r="12" opacity=".55"/></g></svg>`},
    {name:'Khmer geometric border',cat:'Khmer',height:'88px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 100"><defs><pattern id="p" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M40 4 76 40 40 76 4 40Z" fill="none" stroke="#a87616" stroke-width="4"/><path d="M40 19 61 40 40 61 19 40Z" fill="none" stroke="#a87616" stroke-width="2"/></pattern></defs><rect width="800" height="80" y="10" fill="url(#p)"/></svg>`}
  ];
  const pane=$('[data-studio-pane="elements"]',host);
  if(pane&&!$('.fp-visual-assets',pane)){
    const section=document.createElement('section');section.className='fp-visual-assets';section.innerHTML=`<div class="fp-visual-assets-head"><h3>Visual graphics</h3><small>Invitation-ready SVG</small></div><div class="fp-visual-asset-grid"></div>`;const grid=$('.fp-visual-asset-grid',section);
    assets.forEach(asset=>{const b=document.createElement('button');b.type='button';b.className='fp-visual-asset';b.innerHTML=`<span class="art">${asset.svg}</span><strong>${esc(asset.name)}</strong>`;b.title=`${asset.name} · ${asset.cat}`;b.onclick=()=>addSvgAsset(asset);grid.append(b)});
    const existing=$('.final-element-library',pane);pane.insertBefore(section,existing||pane.firstChild);if(existing&&!existing.closest('.fp-simple-symbols')){const details=document.createElement('details');details.className='fp-simple-symbols';details.innerHTML='<summary>Simple symbols & shapes</summary>';existing.before(details);details.append(existing)}
  }
  const textPane=$('[data-studio-pane="text"]',host);
  if(textPane&&!$('.fp-text-fonts',textPane)){
    const fonts=[
      ['Noto Sans','noto-sans','Modern'],['Modern Sans','sans-arial','Modern'],['Friendly','sans-trebuchet','Modern'],['Noto Serif','noto-serif','Serif'],['Classic Serif','serif-georgia','Serif'],['Khmer Sans','noto-sans-khmer','Khmer'],['Khmer Serif','noto-serif-khmer','Khmer']
    ].map(([name,stack,cat])=>({name,stack,cat}));
    const recent=()=>{try{return JSON.parse(localStorage.getItem('einvite-font-recent-v1')||'[]')}catch{return[]}};
    const section=document.createElement('section');section.className='refine-text-section fp-text-fonts';section.innerHTML=`<div><h3>Fonts</h3><small>Click a font to apply it or create text</small></div><div class="fp-text-category-tabs"></div><div class="fp-inline-font-list"></div>`;
    const combo=document.createElement('section');combo.className='refine-text-section';combo.innerHTML=`<div><h3>Font combinations</h3><small>Ready-made invitation typography</small></div><div class="fp-text-combo-grid">
      <button class="fp-text-combo" data-fp-combo="gold"><span class="hero" style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
      <button class="fp-text-combo" data-fp-combo="editorial"><span class="hero" style="font-family:Didot,Georgia,serif">THE<br><i>MOMENT</i></span><small>Editorial contrast</small></button>
      <button class="fp-text-combo" data-fp-combo="modern"><span class="hero" style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><small>SUBHEADING</small></span><small>Modern clean</small></button>
      <button class="fp-text-combo" data-fp-combo="romance"><span class="hero" style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
      <button class="fp-text-combo" data-fp-combo="khmer"><span class="hero" style="font-family:'Khmer OS Muol Light','Noto Serif Khmer',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      <button class="fp-text-combo" data-fp-combo="minimal"><span class="hero" style="font-family:Inter,Arial,sans-serif;letter-spacing:.12em">SAVE<br>THE DATE</span><small>Minimal spaced</small></button>
    </div>`;
    const fontPlaceholder=$('.refine-text-section',textPane)?.nextElementSibling;textPane.append(section,combo);
    let cat='All',query='';const categories=['All','Recent','Khmer','Serif','Modern'];
    const selected=()=>$('.object.selected,.object.multi-selected',stage);
    const applyFont=font=>{let o=selected();if(!o){$('#addText')?.click();o=selected()}if(!o)return;try{pushHistory(capture())}catch{}o.dataset.font=font.stack;try{applyObjectVisualStyle(o);save()}catch{}const r=[font.stack,...recent().filter(x=>x!==font.stack)].slice(0,12);localStorage.setItem('einvite-font-recent-v1',JSON.stringify(r));closePaneOnMobile()};
    function renderFonts(){const tabs=$('.fp-text-category-tabs',section),list=$('.fp-inline-font-list',section);tabs.innerHTML=categories.map(x=>`<button type="button" class="${x===cat?'active':''}" data-cat="${x}">${x}</button>`).join('');$$('[data-cat]',tabs).forEach(b=>b.onclick=()=>{cat=b.dataset.cat;renderFonts()});let data=fonts.filter(f=>{if(cat==='Recent'&&!recent().includes(f.stack))return false;if(!['All','Recent'].includes(cat)&&f.cat!==cat)return false;return!query||`${f.name} ${f.cat}`.toLowerCase().includes(query)});if(cat==='Recent')data.sort((a,b)=>recent().indexOf(a.stack)-recent().indexOf(b.stack));list.innerHTML='';data.forEach(f=>{const b=document.createElement('button');b.type='button';b.className='fp-inline-font';b.innerHTML=`<span class="sample" style="font-family:${window.EInviteTypography?.stack?.(f.stack)||'serif'}">${f.cat==='Khmer'?'សិរីមង្គល':'Beautiful moments'}</span><small>${esc(f.name)}</small>`;b.onclick=()=>applyFont(f);list.append(b)});if(!data.length)list.innerHTML='<small style="padding:12px;color:var(--app-muted)">No fonts match this view.</small>'}
    renderFonts();
    const search=$('.refine-text-search input',textPane);if(search){const prior=search.oninput;search.oninput=e=>{query=e.target.value.trim().toLowerCase();renderFonts();$$('.refine-text-preset,.fp-text-combo',textPane).forEach(x=>x.hidden=!!query&&!x.textContent.toLowerCase().includes(query));if(typeof prior==='function')prior.call(search,e)}}
    const combos={gold:{font:'serif-georgia',fontSize:'48',color:'#b48a20',text:'Golden Hour',letterSpacing:'1'},editorial:{font:'noto-serif',fontSize:'48',color:'#2c2530',text:'The Moment',fontStyle:'italic'},modern:{font:'sans-arial',fontSize:'44',color:'#202127',text:'Your Celebration',fontWeight:'700'},romance:{font:'serif-georgia',fontSize:'46',color:'#426b52',text:'Bride & Groom',fontStyle:'italic'},khmer:{font:"noto-serif-khmer",fontSize:'38',color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'},minimal:{font:'noto-sans',fontSize:'34',color:'#22242a',text:'SAVE THE DATE',letterSpacing:'5'}};
    $$('.fp-text-combo',combo).forEach(b=>b.onclick=()=>{const c=combos[b.dataset.fpCombo];$('#addText')?.click();setTimeout(()=>{const o=selected();if(!o)return;const content=o.querySelector('.content');if(content)content.textContent=c.text;Object.entries(c).forEach(([k,v])=>{if(k!=='text')o.dataset[k]=v});try{applyObjectVisualStyle(o);save()}catch{}closePaneOnMobile()},30)});
  }
  host.addEventListener('click',e=>{const insert=e.target.closest('.final-element-card,.ei-pack-card,[data-add-element],[data-text-preset],.refine-text-preset,.refine-font-combo,.fp-text-combo,.fp-visual-asset,.material-picker-card');if(insert)setTimeout(closePaneOnMobile,80)},true);
  setTimeout(()=>{let pending=null;try{pending=JSON.parse(localStorage.getItem('einvite-pending-material-insert')||'null')}catch{}if(!pending?.url||typeof createObject!=='function')return;localStorage.removeItem('einvite-pending-material-insert');const o=createObject(makeId('material'),'image');o.style.left='14%';o.style.top='18%';o.style.width='72%';o.style.height='420px';o.dataset.src=pending.url;o.dataset.layerName=pending.name||'Material';const img=o.querySelector('img');if(img){img.src=pending.url;img.alt=pending.name||'Invitation material'}stage.append(o);choose(o);saveNow();window.uiToast?.(`${pending.name||'Material'} added to the canvas`,'↑')},500);
  const context=$('.ei-context-toolbar');if(context){let scheduled=false;const decorate=()=>{scheduled=false;if(context.querySelector('.ei-context-more'))return;const secondary=['effects','animate','flipX','flipY','tidy','ungroup','page-motion','check'];const nodes=secondary.map(a=>context.querySelector(`[data-action="${a}"]`)).filter(Boolean);if(nodes.length){const more=document.createElement('button');more.type='button';more.className='ei-context-more';more.textContent='•••';more.title='More actions';const overflow=document.createElement('div');overflow.className='ei-context-overflow';nodes.forEach(n=>overflow.append(n));more.onclick=e=>{e.stopPropagation();overflow.classList.toggle('open')};context.append(more,overflow);document.addEventListener('click',()=>overflow.classList.remove('open'))}};const observer=new MutationObserver(()=>{if(context.querySelector('.ei-context-more'))return;if(scheduled)return;scheduled=true;queueMicrotask(decorate)});observer.observe(context,{childList:true,subtree:false});decorate()}
}
if(page==='dashboard')setTimeout(dashboardFinal,0);
if(page==='materials')setTimeout(materialsFinal,0);
if(page==='index')setTimeout(editorFinal,120);
})();;(()=>{'use strict';
let lastDialogTrigger=new WeakMap();
const focusable='a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function syncPanel(panel,open,trigger){if(!panel)return;panel.hidden=!open;try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(trigger)trigger.setAttribute('aria-expanded',String(open));if(!open&&panel.contains(document.activeElement))trigger?.focus();}
function trapDialogKey(event,dialog){const nodes=[...dialog.querySelectorAll(focusable)].filter(el=>!el.hidden&&el.getClientRects().length&&!el.closest('[inert],[aria-hidden="true"]'));if(!nodes.length)return;if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}
function observeDialogs(){document.querySelectorAll('dialog').forEach(dialog=>{if(dialog.dataset.a11yBound)return;dialog.dataset.a11yBound='1';dialog.addEventListener('close',()=>{const trigger=lastDialogTrigger.get(dialog);if(trigger?.isConnected)trigger.focus()});dialog.addEventListener('cancel',event=>{event.preventDefault();dialog.close()})});}
function init(){
 document.querySelectorAll('button:not([aria-label])').forEach(b=>{if(!b.textContent.trim())b.setAttribute('aria-label',b.title||'Action')});
 document.querySelectorAll('img:not([alt])').forEach(img=>img.alt='Invitation image');
 document.querySelectorAll('a > button').forEach(button=>{const a=button.parentElement;a.classList.add(...button.classList);a.setAttribute('role','button');a.textContent=button.textContent;button.remove()});
 document.querySelectorAll('.khmer-picker select').forEach(select=>{if(!select.getAttribute('aria-label')){const label=select.closest('label')?.childNodes?.[0]?.textContent?.trim();if(label)select.setAttribute('aria-label',label)}});
 document.addEventListener('click',event=>{const trigger=event.target.closest('button,[role="button"],a');if(!trigger)return;requestAnimationFrame(()=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&!lastDialogTrigger.has(top))lastDialogTrigger.set(top,trigger);observeDialogs()})},true);
 document.addEventListener('keydown',event=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&event.key==='Tab'){trapDialogKey(event,top);return}if(event.key!=='Escape')return;if(top){top.close();event.preventDefault();event.stopPropagation();return}const openDrawer=[...document.querySelectorAll('[data-drawer-open="true"],.is-open[role="dialog"]')].filter(x=>!x.hidden).at(-1);if(openDrawer){const trigger=document.querySelector(`[aria-controls="${CSS.escape(openDrawer.id)}"]`);syncPanel(openDrawer,false,trigger);openDrawer.dataset.drawerOpen='false';event.preventDefault()}});
 document.querySelectorAll('[aria-controls]').forEach(trigger=>{if(trigger.dataset.a11yManaged==='true')return;const panel=document.getElementById(trigger.getAttribute('aria-controls'));if(!panel)return;const update=()=>{const open=trigger.getAttribute('aria-expanded')==='true'||panel.classList.contains('open')||panel.classList.contains('is-open');try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(!open&&panel.contains(document.activeElement))trigger.focus()};trigger.addEventListener('click',()=>setTimeout(update,0));update()});
 observeDialogs();new MutationObserver(observeDialogs).observe(document.body,{childList:true,subtree:true});
}
window.EInviteAccessibility={syncPanel};document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();