const $=s=>document.querySelector(s);const token=localStorage.getItem('sovan-auth-token');let materials=[],invitations=[];
async function api(path,options={}){const make=withToken=>fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(withToken&&token?{Authorization:`Bearer ${token}`}:{ }),...(options.headers||{})}});let response=await make(true);if(response.status===401&&token)response=await make(false);const payload=await response.json().catch(()=>({}));if(!response.ok)throw Error(payload.error||'Request failed');return payload}
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const formatBytes=n=>{n=Number(n||0);if(n<1024)return`${n} B`;if(n<1024**2)return`${(n/1024).toFixed(1)} KB`;return`${(n/1024**2).toFixed(1)} MB`};
function typeOf(item){return item.mime?.startsWith('image/')?'image':item.mime?.startsWith('audio/')?'audio':item.mime?.startsWith('video/')?'video':'other'}
async function load(){try{[materials,invitations]=await Promise.all([api('/api/assets'),api('/api/invitations')]);renderInvitationOptions();render()}catch(error){$('#grid').innerHTML=`<div class="empty-library"><h2>Material library unavailable</h2><p>${esc(error.message)}</p></div>`}}
function renderInvitationOptions(){const select=$('#uploadInvitation');select.innerHTML=invitations.filter(i=>!i.archived).map(i=>`<option value="${esc(i.id)}">${esc(i.title||i.slug||'Invitation')}</option>`).join('');if(!select.options.length)select.innerHTML='<option value="">Create an invitation first</option>'}
function filtered(){const q=$('#search').value.trim().toLowerCase(),folder=$('#folderFilter').value.trim().toLowerCase(),type=$('#typeFilter').value,sort=$('#sort').value;let list=materials.filter(item=>{const kind=typeOf(item),hay=[item.name,item.folder,...(item.tags||[])].join(' ').toLowerCase();return(!q||hay.includes(q))&&(!folder||String(item.folder||'').toLowerCase().includes(folder))&&(type==='all'||type===kind||(type==='favorite'&&item.favorite))});list.sort((a,b)=>sort==='oldest'?a.createdAt-b.createdAt:sort==='name'?String(a.name).localeCompare(String(b.name)):sort==='size'?b.size-a.size:b.createdAt-a.createdAt);return list}
function render(){const list=filtered(),bytes=materials.reduce((sum,x)=>sum+Number(x.size||0),0),favorites=materials.filter(x=>x.favorite).length;$('#summary').innerHTML=`<span>${materials.length} materials</span><span>${formatBytes(bytes)} stored</span><span>${favorites} favorite${favorites===1?'':'s'}</span><span>${list.length} shown</span>`;const grid=$('#grid');if(!list.length){grid.innerHTML='<div class="empty-library"><h2>No matching materials</h2><p>Upload a file or change your filters.</p></div>';return}grid.innerHTML=list.map(item=>{const kind=typeOf(item),thumb=kind==='image'?`<img src="${esc(item.url)}" alt="">`:kind==='video'?`<video src="${esc(item.url)}" muted preload="metadata"></video>`:`<span class="audio-mark">♫</span>`;return`<article class="material-card-page"><div class="material-thumb">${thumb}${item.favorite?'<span class="favorite-mark">★</span>':''}</div><div class="material-info"><strong title="${esc(item.name)}">${esc(item.name)}</strong><div class="library-folder">${item.folder?`Folder: ${esc(item.folder)}`:'No folder'} · ${formatBytes(item.size)}</div><div class="material-tags">${(item.tags||[]).slice(0,5).map(tag=>`<span>${esc(tag)}</span>`).join('')}</div></div><div class="actions"><a href="${esc(item.url)}" target="_blank" rel="noopener"><button type="button">Open</button></a><button data-edit="${esc(item.id)}" type="button">Edit</button></div></article>`}).join('');grid.querySelectorAll('[data-edit]').forEach(button=>button.onclick=()=>openEdit(button.dataset.edit))}
function openEdit(id){const item=materials.find(x=>x.id===id);if(!item)return;$('#editId').value=id;$('#editName').value=item.name||'';$('#editFolder').value=item.folder||'';$('#editTags').value=(item.tags||[]).join(', ');$('#editFavorite').checked=!!item.favorite;$('#editMeta').textContent=`${item.mime} · ${formatBytes(item.size)} · uploaded ${new Date(item.createdAt).toLocaleString()}`;$('#editDialog').showModal()}
$('#editForm').onsubmit=async e=>{e.preventDefault();const id=$('#editId').value,item=materials.find(x=>x.id===id);if(!item)return;try{const updated=await api('/api/assets/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify({name:$('#editName').value.trim(),folder:$('#editFolder').value.trim(),tags:$('#editTags').value.split(',').map(x=>x.trim()).filter(Boolean),favorite:$('#editFavorite').checked})});Object.assign(item,updated);$('#editDialog').close();render()}catch(error){alert(error.message)}};
$('#deleteBtn').onclick=async()=>{const id=$('#editId').value,item=materials.find(x=>x.id===id);if(!item||!(await uiConfirm(`Permanently delete “${item.name}” from storage? Existing published invitations that reference it may stop displaying the material.`,{title:'Delete material',danger:true,confirmText:'Delete permanently'})))return;try{await api(`/api/invitations/${item.invitationId}/assets/${id}`,{method:'DELETE'});materials=materials.filter(x=>x.id!==id);$('#editDialog').close();render()}catch(error){alert(error.message)}};
$('#cancelEdit').onclick=()=>$('#editDialog').close();
const allowedUploadTypes=['image/jpeg','image/png','image/webp','image/gif','audio/mpeg','audio/mp4','video/mp4','video/webm'];
async function uploadMaterialFiles(files){
 const inviteId=$('#uploadInvitation').value,list=[...files];
 if(!inviteId)return alert('Create or select an invitation first.');
 if(!list.length)return alert('Choose one or more files to upload.');
 for(const file of list){
  if(!allowedUploadTypes.includes(file.type))return alert(`Unsupported file type: ${file.name}`);
  const limit=file.type.startsWith('video/')?50e6:15e6;
  if(file.size>limit)return alert(`${file.name} exceeds the ${limit/1e6} MB limit.`)
 }
 const progress=$('.progress-line');progress.hidden=false;
 try{
  for(let index=0;index<list.length;index++){
   const file=list[index];
   $('#uploadProgress').style.width=`${Math.max(8,Math.round(index/list.length*100))}%`;
   const payload=await window.EInviteUpload.upload(inviteId,file,{token,name:file.name});
   if(payload.duplicate)window.uiToast?.(`${file.name} already existed — reused stored file`,'↻');
   else if(payload.uploadMode==='direct')window.uiToast?.(`${file.name} uploaded directly to object storage`,'↑');
   $('#uploadProgress').style.width=`${Math.round((index+1)/list.length*100)}%`
  }
  $('#uploadFile').value='';materials=await api('/api/assets');render();
  setTimeout(()=>{progress.hidden=true;$('#uploadProgress').style.width='0'},500)
 }catch(error){progress.hidden=true;alert(error.message)}
}
$('#uploadBtn').onclick=()=>uploadMaterialFiles($('#uploadFile').files||[]);
window.uploadMaterialFiles=uploadMaterialFiles;
['search','folderFilter'].forEach(id=>$('#'+id).oninput=render);['typeFilter','sort'].forEach(id=>$('#'+id).onchange=render);$('#refreshBtn').onclick=load;load();
