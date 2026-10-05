(()=>{
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
})();
