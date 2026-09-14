const $=s=>document.querySelector(s);localStorage.removeItem('sovan-auth-token');const contextInviteId=window.EInviteContext?.getInvitationId({allowRemembered:false})||'';let materials=[],invitations=[];
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
['search','folderFilter'].forEach(id=>$('#'+id).oninput=render);['typeFilter','sort'].forEach(id=>$('#'+id).onchange=render);$('#refreshBtn').onclick=load;load();
