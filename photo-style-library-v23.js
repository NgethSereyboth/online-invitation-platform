(()=>{
'use strict';
const VERSION='23.6.3';
if(window.EInvitePhotoStyleLibrary?.version===VERSION)return;
const registry=window.EInviteCommandRegistry,bridge=window.EInviteEditorBridge,photo=window.EInvitePhotoWorkflow,stage=document.querySelector('#stage');
if(!registry||!bridge||!photo||!stage)return;
if(!document.querySelector('link[data-v23-photo-styles]')){const link=document.createElement('link');link.rel='stylesheet';link.href='photo-style-library-v23.css';link.dataset.v23PhotoStyles='1';document.head.append(link)}
const $=(selector,root=document)=>root.querySelector(selector),$$=(selector,root=document)=>[...root.querySelectorAll(selector)];
const clone=value=>{try{return structuredClone(value)}catch{return JSON.parse(JSON.stringify(value))}};
const clean=(value,max=120)=>String(value??'').replace(/[\u0000-\u001f\u007f]/g,'').trim().slice(0,max);
const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const safeId=(value,fallback='photo-style')=>String(value||'').toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,64)||fallback;
const uid=prefix=>`${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
const STORAGE_KEY='einvite-photo-styles-v23',PREF_KEY='einvite-photo-style-pref-v23',SCHEMA_VERSION=1,MAX_STYLES=36,MAX_LIBRARY_BYTES=900000,MAX_IMPORT_BYTES=1000000;
const cleanup=[],unregister=[];
let dialog=null,opener=null,preview=null,memoryLibrary=[],destroyed=false,storageWarningShown=false;
const feedback=window.EInviteFeedback||Object.freeze({toast:(message,tone='info')=>{window.uiToast?.(message,tone==='error'?'!':'✦');return true}});
function on(target,type,handler,options){target?.addEventListener?.(type,handler,options);cleanup.push(()=>target?.removeEventListener?.(type,handler,options))}
function canvasMap(documentState,canvasId=bridge.getActiveCanvasId?.()||'hero'){
 if(canvasId==='hero')return documentState?.objects||{};
 const pageId=String(canvasId).replace(/^page:/,'');
 return(documentState?.designPages||[]).find(page=>String(page.id)===pageId)?.objects||{};
}
function isImage(object){return object?.type==='image'||object?.objectType==='image'}
function selectedImageIds(documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero'){
 const map=canvasMap(documentState,canvasId);return(bridge.getSelectedIds?.()||[]).map(String).filter(id=>isImage(map[id]));
}
function pageImageIds(documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero'){
 const map=canvasMap(documentState,canvasId);return Object.entries(map).filter(([,object])=>isImage(object)).sort((a,b)=>Number(a[1]?.zIndex||0)-Number(b[1]?.zIndex||0)).map(([id])=>String(id));
}
function targetIds(scope,documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero'){
 return scope==='page'?pageImageIds(documentState,canvasId):selectedImageIds(documentState,canvasId);
}
function selectedSource(){const documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero',map=canvasMap(documentState,canvasId),id=selectedImageIds(documentState,canvasId)[0],object=id?map[id]:null;return object?.src||object?.originalSrc||''}
function safeImageUrl(value){const url=String(value||'').trim();return /^(?:https?:\/\/|blob:|data:image\/(?:png|jpe?g|webp|gif|avif);base64,|\/(?:uploads|api\/|data\/uploads\/))/i.test(url)?url:''}
function normalizeLook(input={}){return photo.normalizeLook?.(clone(input))||clone(input||{})}
function normalizeStyle(input={},builtin=false){
 const name=clean(input.name)||'Untitled photo style';
 return{id:safeId(input.id||uid('photo-style')),name,description:clean(input.description,260),category:clean(input.category,60)||(builtin?'Built-in':'Custom'),tags:Array.isArray(input.tags)?input.tags.map(tag=>clean(tag,30)).filter(Boolean).slice(0,12):[],builtin:builtin||input.builtin===true,createdAt:Number(input.createdAt)||Date.now(),updatedAt:Number(input.updatedAt)||Date.now(),look:normalizeLook(input.look||input.values||{})};
}
function builtinStyles(){return(photo.presets||[]).map(preset=>normalizeStyle({id:`builtin-${preset.id}`,name:preset.label,description:preset.description,category:'Built-in',tags:['preset',preset.id],look:preset.values||{}},true))}
function readStored(){
 try{const value=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');memoryLibrary=Array.isArray(value)?value.map(item=>normalizeStyle(item,false)).filter(item=>!item.builtin).slice(0,MAX_STYLES):[];return clone(memoryLibrary)}catch{return clone(memoryLibrary)}
}
function writeStored(items){
 const normalized=items.map(item=>normalizeStyle(item,false)).filter(item=>!item.builtin).slice(0,MAX_STYLES),text=JSON.stringify(normalized);
 if(new Blob([text]).size>MAX_LIBRARY_BYTES)throw Error('The photo-style library is too large. Delete unused styles before saving more.');
 memoryLibrary=clone(normalized);
 try{localStorage.setItem(STORAGE_KEY,text)}catch{if(!storageWarningShown){storageWarningShown=true;feedback.toast('Photo styles will remain available only for this session because browser storage is restricted.','error')}}
 window.dispatchEvent(new CustomEvent('einvite:photo-styles-changed',{detail:{count:normalized.length}}));return clone(normalized);
}
function allStyles(){return[...builtinStyles(),...readStored()]}
function styleById(id){return allStyles().find(style=>style.id===id)||null}
function uniqueName(name,items=readStored()){const base=clean(name)||'Photo style',used=new Set(items.map(item=>item.name.toLowerCase()));if(!used.has(base.toLowerCase()))return base;let suffix=2;while(used.has(`${base} ${suffix}`.toLowerCase()))suffix++;return`${base} ${suffix}`}
function selectedObject(){const documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero',map=canvasMap(documentState,canvasId),id=selectedImageIds(documentState,canvasId)[0];return id?{id,canvasId,object:map[id]}:null}
function saveSelected(name){
 const context=selectedObject();if(!context)throw Error('Select an image before saving a photo style.');
 const items=readStored();if(items.length>=MAX_STYLES)throw Error(`The custom photo-style limit (${MAX_STYLES}) has been reached.`);
 const style=normalizeStyle({id:uid('photo-style'),name:uniqueName(name,items),description:'Captured from the selected invitation image',category:'Custom',look:photo.extractLook?.(context.object)||context.object,createdAt:Date.now(),updatedAt:Date.now()});
 writeStored([style,...items]);feedback.toast(`Saved “${style.name}”`);renderDialog();return style;
}
function duplicateStyle(id){const source=styleById(id);if(!source)throw Error('The photo style is unavailable.');const items=readStored();if(items.length>=MAX_STYLES)throw Error(`The custom photo-style limit (${MAX_STYLES}) has been reached.`);const copy=normalizeStyle({...source,id:uid('photo-style'),name:uniqueName(`${source.name} copy`,items),builtin:false,category:'Custom',createdAt:Date.now(),updatedAt:Date.now()});writeStored([copy,...items]);feedback.toast(`Duplicated “${source.name}”`);renderDialog();return copy}
function renameStyle(id,name){const items=readStored(),index=items.findIndex(item=>item.id===id);if(index<0)return false;items[index]={...items[index],name:uniqueName(name,items.filter((_,position)=>position!==index)),updatedAt:Date.now()};writeStored(items);feedback.toast('Photo style renamed');renderDialog();return true}
function deleteStyle(id){const items=readStored(),style=items.find(item=>item.id===id);if(!style)return false;writeStored(items.filter(item=>item.id!==id));feedback.toast(`Deleted “${style.name}”`);renderDialog();return true}
function restorePreviewNodes(current=preview){if(!current)return;for(const[id,look]of current.originals){const node=stage.querySelector(`.object[data-id="${CSS.escape(String(id))}"]`);if(node)photo.projectLookToNode?.(node,look)}}
function cancelPreview({render=true,announce=false}={}){if(!preview)return false;restorePreviewNodes(preview);preview=null;document.body.classList.remove('v23-photo-style-previewing');if(render)renderDialog();if(announce)feedback.toast('Photo-style preview cancelled');return true}
function beginPreview(id,scope){
 const style=styleById(id);if(!style)throw Error('The photo style is unavailable.');cancelPreview({render:false});
 const documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero',map=canvasMap(documentState,canvasId),ids=targetIds(scope,documentState,canvasId);
 if(!ids.length)throw Error(scope==='page'?'This page has no images.':'Select one or more images first.');
 const originals=new Map();for(const targetId of ids){const object=map[targetId];if(!object)continue;originals.set(targetId,photo.extractLook?.(object)||normalizeLook(object));const node=stage.querySelector(`.object[data-id="${CSS.escape(String(targetId))}"]`);if(node)photo.projectLookToNode?.(node,style.look)}
 preview={styleId:style.id,scope,canvasId,ids:[...originals.keys()],originals};document.body.classList.add('v23-photo-style-previewing');renderDialog();return true;
}
function applyStyle(id,scope){
 const style=styleById(id);if(!style)throw Error('The photo style is unavailable.');
 const documentState=bridge.getState?.()||{},canvasId=bridge.getActiveCanvasId?.()||'hero',ids=preview?.styleId===style.id&&preview.scope===scope&&preview.canvasId===canvasId?[...preview.ids]:targetIds(scope,documentState,canvasId);
 if(!ids.length)throw Error(scope==='page'?'This page has no images.':'Select one or more images first.');
 cancelPreview({render:false});
 bridge.transact(`Apply photo style: ${style.name}`,nextDocument=>{const map=canvasMap(nextDocument,canvasId);for(const targetId of ids){const target=map[targetId];if(!isImage(target))continue;photo.applyLookToObject?.(target,style.look)}},{capture:false});
 if(scope==='selection')bridge.select?.(ids);feedback.toast(`Applied “${style.name}” to ${ids.length} image${ids.length===1?'':'s'}`);renderDialog();return ids.length;
}
function styleSummary(style){const look=style.look||{},parts=[];if(Number(look.imageTemperature||0)>12)parts.push('Warm');else if(Number(look.imageTemperature||0)<-12)parts.push('Cool');if(Number(look.imageContrast||100)>112)parts.push('Contrast');if(Number(look.imageSaturation||100)>115)parts.push('Color');if(Number(look.imageGrayscale||0)>50)parts.push('Mono');if(Number(look.imageBlur||0)>.25)parts.push('Soft');return parts.slice(0,3).join(' · ')||'Balanced'}
function filteredStyles(){const query=clean($('[data-photo-style-search]',dialog)?.value,120).toLowerCase(),styles=allStyles();if(!query)return styles;return styles.filter(style=>[style.name,style.description,style.category,...style.tags].join(' ').toLowerCase().includes(query))}
function ensureDialog(){
 if(dialog)return dialog;
 dialog=document.createElement('dialog');dialog.id='v23PhotoStyleLibrary';dialog.className='v23-photo-style-dialog v23-command-surface';dialog.innerHTML=`<header><div><small>Reusable image treatment</small><h2>Photo styles</h2></div><button type="button" data-close aria-label="Close">×</button></header><div class="v23-photo-style-toolbar"><label><span>Search</span><input type="search" data-photo-style-search placeholder="Search photo styles"></label><label><span>Apply to</span><select data-photo-style-scope><option value="selection">Selected images</option><option value="page">Every image on this page</option></select></label><form data-save-style><label><span>Save selected image as a style</span><input name="name" maxlength="120" placeholder="Style name"></label><button type="submit">Save style</button></form><div class="v23-photo-style-io"><button type="button" data-export-styles>Export</button><button type="button" data-import-styles>Import</button><input type="file" data-import-file accept="application/json,.json" hidden></div></div><div class="v23-photo-style-preview-banner" data-preview-banner hidden><span></span><button type="button" data-cancel-preview>Cancel preview</button></div><div class="v23-photo-style-list" data-photo-style-list></div><footer><span data-photo-style-count></span><button type="button" data-close>Close</button></footer>`;
 document.body.append(dialog);
 dialog.querySelectorAll('[data-close]').forEach(button=>button.onclick=()=>dialog.close());
 $('[data-photo-style-search]',dialog).addEventListener('input',renderDialog);
 $('[data-photo-style-scope]',dialog).addEventListener('change',event=>{if(preview)beginPreview(preview.styleId,event.target.value)});
 $('[data-save-style]',dialog).addEventListener('submit',event=>{event.preventDefault();try{const input=event.currentTarget.elements.name,style=saveSelected(input.value);input.value='';input.placeholder=`Saved ${style.name}`}catch(error){feedback.toast(error.message,'error')}});
 $('[data-export-styles]',dialog).onclick=exportLibrary;
 $('[data-import-styles]',dialog).onclick=()=> $('[data-import-file]',dialog).click();
 $('[data-import-file]',dialog).onchange=async event=>{const file=event.target.files?.[0];event.target.value='';if(!file)return;try{await importLibrary(file)}catch(error){feedback.toast(error.message,'error')}};
 $('[data-cancel-preview]',dialog).onclick=()=>cancelPreview({announce:true});
 $('[data-photo-style-list]',dialog).addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button)return;
  try{
   const scope=$('[data-photo-style-scope]',dialog).value;
   if(button.dataset.previewStyle)beginPreview(button.dataset.previewStyle,scope);
   else if(button.dataset.applyStyle)applyStyle(button.dataset.applyStyle,scope);
   else if(button.dataset.duplicateStyle)duplicateStyle(button.dataset.duplicateStyle);
   else if(button.dataset.renameStyle){const style=styleById(button.dataset.renameStyle),name=prompt('Photo style name:',style?.name||'');if(name!==null&&clean(name))renameStyle(button.dataset.renameStyle,name)}
   else if(button.dataset.deleteStyle){const style=styleById(button.dataset.deleteStyle),approved=await(window.uiConfirm?.(`Delete photo style “${style?.name||''}”?`,{title:'Delete photo style',danger:true,confirmText:'Delete'})??Promise.resolve(confirm('Delete this photo style?')));if(approved)deleteStyle(button.dataset.deleteStyle)}
  }catch(error){feedback.toast(error.message,'error')}
 });
 dialog.addEventListener('close',()=>{cancelPreview({render:false});opener?.focus?.();opener=null});
 return dialog;
}
function renderDialog(){
 if(!dialog)return;const styles=filteredStyles(),list=$('[data-photo-style-list]',dialog),source=safeImageUrl(selectedSource()),banner=$('[data-preview-banner]',dialog),scope=$('[data-photo-style-scope]',dialog)?.value||'selection';
 banner.hidden=!preview;if(preview){const style=styleById(preview.styleId);banner.querySelector('span').textContent=`Previewing “${style?.name||'Photo style'}” on ${preview.ids.length} image${preview.ids.length===1?'':'s'}`}
 list.innerHTML=styles.length?styles.map(style=>`<article class="v23-photo-style-card ${preview?.styleId===style.id&&preview?.scope===scope?'is-previewing':''}" data-style-card="${esc(style.id)}"><div class="v23-photo-style-sample">${source?`<img alt="" loading="lazy">`:'<span>✦</span>'}<b>${esc(styleSummary(style))}</b></div><div class="v23-photo-style-copy"><small>${style.builtin?'Built-in':esc(style.category)}</small><strong>${esc(style.name)}</strong><span>${esc(style.description||'Reusable non-destructive photo adjustments')}</span></div><div class="v23-photo-style-actions"><button type="button" data-preview-style="${esc(style.id)}">Preview</button><button type="button" class="primary" data-apply-style="${esc(style.id)}">Apply</button><button type="button" data-duplicate-style="${esc(style.id)}">Duplicate</button>${style.builtin?'':`<button type="button" data-rename-style="${esc(style.id)}">Rename</button><button type="button" data-delete-style="${esc(style.id)}" aria-label="Delete ${esc(style.name)}">×</button>`}</div></article>`).join(''):'<div class="v23-photo-style-empty"><strong>No matching photo styles</strong><span>Change the search or save the selected image as a new style.</span></div>';
 if(source){for(const card of $$('[data-style-card]',list)){const style=styleById(card.dataset.styleCard),image=$('img',card);if(!style||!image)continue;image.src=source;image.style.filter=window.EInviteRenderer?.imageFilterStyle?.(style.look)||'';image.style.transform=window.EInviteRenderer?.imageTransformStyle?.(style.look)||''}}
 $('[data-photo-style-count]',dialog).textContent=`${styles.length} style${styles.length===1?'':'s'} · ${targetIds(scope).length} target image${targetIds(scope).length===1?'':'s'}`;
}
function openLibrary(options={}){const d=ensureDialog();opener=document.activeElement;const selectionCount=selectedImageIds().length;$('[data-photo-style-scope]',d).value=options.scope||(selectionCount?'selection':'page');$('[data-photo-style-search]',d).value=options.query||'';renderDialog();if(!d.open)d.showModal();setTimeout(()=> $('[data-photo-style-search]',d)?.focus(),0);return true}
function exportLibrary(){const styles=readStored(),payload={schemaVersion:SCHEMA_VERSION,exportedAt:new Date().toISOString(),styles};if(!styles.length){feedback.toast('There are no custom photo styles to export.','error');return false}const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download='e-invitation-photo-styles.json';document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);feedback.toast(`Exported ${styles.length} photo style${styles.length===1?'':'s'}`);return true}
async function importLibrary(file){
 if(Number(file?.size||0)>MAX_IMPORT_BYTES)throw Error('Choose a photo-style file smaller than 1 MB.');
 let data;try{data=JSON.parse(await file.text())}catch{throw Error('The selected file is not valid JSON.')}
 const incoming=Array.isArray(data)?data:Array.isArray(data?.styles)?data.styles:null;if(!incoming)throw Error('The selected file does not contain a photo-style library.');
 let items=readStored(),added=0;for(const raw of incoming.slice(0,MAX_STYLES)){if(items.length>=MAX_STYLES)break;const style=normalizeStyle({...raw,id:uid('photo-style'),name:uniqueName(raw?.name||'Imported photo style',items),builtin:false,category:'Imported',createdAt:Date.now(),updatedAt:Date.now()});items.push(style);added++}
 if(!added)throw Error('No additional photo styles could be imported.');writeStored(items);feedback.toast(`Imported ${added} photo style${added===1?'':'s'}`);renderDialog();return added;
}
function installStatusButton(){const host=$('.studio-statusbar>div:last-child')||$('.studio-statusbar');if(host&&!host.querySelector('[data-v23-photo-styles]')){const button=document.createElement('button');button.type='button';button.dataset.v23PhotoStyles='1';button.dataset.commandId='photoStyles.open';button.textContent='Photo styles';button.title='Reusable photo-style library';host.prepend(button)}}
function installPhotoDialogButton(){const header=$('#v23PhotoWorkflow .v23-photo-panel>header');if(!header||header.querySelector('[data-open-photo-styles]'))return;const button=document.createElement('button');button.type='button';button.dataset.openPhotoStyles='1';button.textContent='Styles';button.title='Open reusable photo styles';button.onclick=()=>openLibrary({scope:'selection'});const close=$('[data-close]',header);header.insertBefore(button,close||null)}
function registerCommands(){unregister.push(...registry.registerMany([
 {id:'photoStyles.open',title:'Open photo styles',category:'Photo',keywords:['preset','look','filter','batch','library'],bindings:{standard:['Mod+Alt+Shift+L'],canva:['Mod+Alt+Shift+L'],photoshop:['Mod+Alt+Shift+L']},run:openLibrary},
 {id:'photoStyles.saveSelected',title:'Save selected image as photo style',category:'Photo',keywords:['preset','capture','look'],bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>!!selectedImageIds().length,run:()=>saveSelected(prompt('Photo style name:')||'')},
 {id:'photoStyles.applyPage',title:'Apply photo style to current page',category:'Photo',keywords:['batch','all images','page'],bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>pageImageIds().length>0,run:()=>openLibrary({scope:'page'})}
 ]))}
function onExternalState(event){const reason=String(event.detail?.reason||'');if(preview&&!/photo style/i.test(reason))cancelPreview({render:dialog?.open===true})}
const observer=new MutationObserver(records=>{if(records.some(record=>[...record.addedNodes].some(node=>node.nodeType===1&&(node.matches?.('#v23PhotoWorkflow,.studio-statusbar')||node.querySelector?.('#v23PhotoWorkflow,.studio-statusbar'))))){requestAnimationFrame(()=>{installStatusButton();installPhotoDialogButton()})}});
function init(){if(destroyed)return;registerCommands();installStatusButton();installPhotoDialogButton();observer.observe(document.body,{childList:true,subtree:true});on(document,'einvite:selection-changed',()=>{if(preview)cancelPreview({render:dialog?.open===true});else if(dialog?.open)renderDialog()});on(window,'einvite:editor-state-replaced',onExternalState);on(window,'einvite:editor-command',()=>{if(dialog?.open&&!preview)renderDialog()});on(window,'einvite:photo-styles-changed',()=>{if(dialog?.open)renderDialog()});document.body.classList.add('photo-style-library-v23');document.dispatchEvent(new CustomEvent('einvite:selection-changed',{detail:{source:'photo-style-library'}}))}
window.EInvitePhotoStyleLibrary=Object.freeze({version:VERSION,open:openLibrary,list:allStyles,get:styleById,saveSelected,duplicate:duplicateStyle,rename:renameStyle,remove:deleteStyle,preview:beginPreview,cancelPreview,apply:applyStyle,export:exportLibrary,import:importLibrary,get customCount(){return readStored().length},get activePreview(){return preview?{styleId:preview.styleId,scope:preview.scope,count:preview.ids.length}:null}});
window.EInviteLifecycle?.add?.(()=>{destroyed=true;observer.disconnect();cancelPreview({render:false});cleanup.splice(0).forEach(dispose=>{try{dispose()}catch{}});unregister.splice(0).forEach(dispose=>{try{dispose()}catch{}});dialog?.remove();delete window.EInvitePhotoStyleLibrary});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
