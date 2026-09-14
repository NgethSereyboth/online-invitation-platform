(()=>{
'use strict';
if(window.EInviteCommandUI)return;
const registry=window.EInviteCommandRegistry;if(!registry)return;
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
let surface=null,mode='commands',active=0,previousFocus=null,captureCommand='',currentItems=[],renderNonce=0,searchTimer=0,assetCache=[],assetCacheAt=0,assetPromise=null;
function build(){
 if(surface)return surface;
 surface=document.createElement('div');surface.className='v23-command-surface';surface.hidden=true;surface.innerHTML=`
 <div class="v23-command-backdrop" data-close></div>
 <section class="v23-command-dialog" role="dialog" aria-modal="true" aria-labelledby="v23CommandTitle">
  <header><div><small>Creation Studio</small><h2 id="v23CommandTitle">Quick Actions</h2></div><button type="button" data-close aria-label="Close">×</button></header>
  <nav aria-label="Command interface"><button type="button" data-mode="commands">Quick Actions</button><button type="button" data-mode="shortcuts">Shortcuts</button></nav>
  <div class="v23-command-search"><span>⌕</span><input type="search" autocomplete="off" placeholder="Search commands, pages, layers, templates, materials…"><kbd>Esc</kbd></div>
  <div class="v23-command-content"></div>
  <footer><span>↑↓ Navigate</span><span>Enter Run</span><span data-profile-label></span></footer>
 </section>`;
 document.body.append(surface);
 $$('[data-close]',surface).forEach(node=>node.onclick=closeSurface);$$('[data-mode]',surface).forEach(node=>node.onclick=()=>{mode=node.dataset.mode;active=0;render()});
 surface.addEventListener('keydown',keydown);
 $('input',surface).addEventListener('input',()=>{active=0;clearTimeout(searchTimer);searchTimer=setTimeout(render,70)});
 return surface;
}
function query(){return $('input',surface)?.value.trim().toLowerCase()||''}
function matches(value,q){return!q||String(value||'').toLowerCase().includes(q)}
function activeMap(state){const canvas=window.EInviteEditorBridge?.getActiveCanvasId?.()||'hero';if(canvas==='hero')return state?.objects||{};const id=String(canvas).replace(/^page:/,'');return(state?.designPages||[]).find(page=>String(page.id)===id)?.objects||{}}
function commandItems(q){return registry.list().filter(item=>item.state.visible&&(!q||matches(`${item.title} ${item.category} ${item.description||''} ${(item.keywords||[]).join(' ')}`,q))).map(item=>({...item,kind:'command',commandId:item.id}))}
function readList(key){try{const value=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(value)?value:[]}catch{return[]}}
function loadAssets(){if(Date.now()-assetCacheAt<5000)return Promise.resolve(assetCache);if(assetPromise)return assetPromise;assetPromise=(window.assetStore?.list?Promise.resolve(window.assetStore.list()).catch(()=>[]):Promise.resolve([])).then(list=>{assetCache=Array.isArray(list)?list.slice(0,300):[];assetCacheAt=Date.now();assetPromise=null;return assetCache});return assetPromise}
function contextualItems(q){
 if(q.length<2)return Promise.resolve([]);
 const state=window.EInviteEditorBridge?.getState?.()||{},items=[];
 const pages=[{id:'hero',name:'Main hero',token:'hero'},...(state.designPages||[]).map((page,index)=>({id:page.id,name:page.name||page.title||page.preset||`Page ${index+1}`,token:`page:${page.id}`}))];
 for(const page of pages)if(matches(`${page.name} page canvas`,q))items.push({kind:'page',category:'Pages',title:page.name,description:'Open design page',icon:'▣',run:()=>window.switchCanvas?.(page.token)});
 for(const [id,object]of Object.entries(activeMap(state))) {const name=object.layerName||object.name||object.label||object.text||object.type||id;if(matches(`${name} ${id} layer object`,q))items.push({kind:'layer',category:'Layers',title:String(name).slice(0,100),description:'Select layer on the active page',icon:'◇',run:()=>{window.EInviteEditorBridge?.select?.([id]);window.EInviteWorkflow?.navigate?.('design',{source:'quick-actions'})}})}
 const pageTemplates=readList('sovan-reusable-page-templates-v1');
 for(const template of pageTemplates)if(matches(`${template.name} ${template.category||''} template`,q))items.push({kind:'template',category:'Templates',title:template.name||'Saved page template',description:'Open saved page template',icon:'▤',run:()=>{window.EInviteWorkflow?.navigate?.('pages',{source:'quick-actions'});setTimeout(()=>{const row=$$('#savedPageTemplates .saved-page-template-row').find(node=>$('strong',node)?.textContent.trim()===(template.name||''));row?.querySelector('button')?.click()},100)}});
 return loadAssets().then(list=>{for(const asset of list){const hay=`${asset.name||''} ${asset.folder||''} ${(asset.tags||[]).join(' ')} ${asset.type||''} material asset`;if(!matches(hay,q))continue;items.push({kind:'asset',category:'Materials',title:asset.name||'Stored material',description:'Reveal in the Media workspace',icon:asset.type?.startsWith('audio/')?'♫':asset.type?.startsWith('video/')?'▶':'▧',run:()=>{window.EInviteWorkflow?.navigate?.('media',{source:'quick-actions'});setTimeout(()=>{const input=$('#assetSearch');if(input){input.value=asset.name||'';input.dispatchEvent(new Event('input',{bubbles:true}));input.focus()}setTimeout(()=>{const node=$(`[data-asset-id="${CSS.escape(String(asset.id||''))}"]`);node?.scrollIntoView?.({block:'nearest'});node?.focus?.()},100)},70)}})}return items.slice(0,40)})
}
async function items(){const q=query(),commands=commandItems(q),context=await contextualItems(q);return[...commands,...context]}
function rows(){return $$('.v23-command-row',surface)}
async function renderCommands(){
 const token=++renderNonce,content=$('.v23-command-content',surface);content.innerHTML='<div class="v23-command-empty">Searching…</div>';
 const found=await items();if(token!==renderNonce||mode!=='commands')return;currentItems=found;content.innerHTML='';active=Math.max(0,Math.min(active,Math.max(0,found.length-1)));
 if(!found.length){content.innerHTML='<div class="v23-command-empty">No matching commands or project items.</div>';return}
 let category='';found.forEach((item,index)=>{if(item.category!==category){category=item.category;const h=document.createElement('div');h.className='v23-command-category';h.textContent=category;content.append(h)}const row=document.createElement('button');row.type='button';row.className=`v23-command-row${index===active?' active':''}`;row.dataset.resultIndex=String(index);if(item.commandId)row.dataset.commandId=item.commandId;row.disabled=item.state?.enabled===false;const shortcuts=(item.shortcuts||[]).slice(0,2).map(registry.formatChord).join('  ');row.innerHTML='<span class="v23-command-icon"></span><span><strong></strong><small></small></span><kbd></kbd>';$('.v23-command-icon',row).textContent=item.icon||'·';$('strong',row).textContent=item.title;$('small',row).textContent=item.description||item.category;$('kbd',row).textContent=shortcuts;row.onmouseenter=()=>{active=index;syncActive()};row.onclick=()=>runItem(index);content.append(row)})
}
function renderShortcuts(){
 ++renderNonce;currentItems=[];const content=$('.v23-command-content',surface);content.innerHTML='';const settings=document.createElement('section');settings.className='v23-shortcut-settings';settings.innerHTML='<div class="v23-profile-row"><label>Shortcut profile<select data-profile><option value="standard">E-Invitation Standard</option><option value="canva">Canva-like</option><option value="photoshop">Photoshop-like</option></select></label><button type="button" data-reset>Reset custom shortcuts</button></div><div class="v23-conflicts" hidden></div><div class="v23-shortcut-list"></div>';content.append(settings);$('[data-profile]',settings).value=registry.profile;$('[data-profile]',settings).onchange=event=>registry.setProfile(event.target.value);$('[data-reset]',settings).onclick=()=>{registry.resetOverrides();render()};
 const q=query(),list=registry.list({includeHidden:true}).filter(item=>!q||matches(`${item.title} ${item.category} ${(item.keywords||[]).join(' ')}`,q));const host=$('.v23-shortcut-list',settings);let category='';for(const item of list){if(item.category!==category){category=item.category;const h=document.createElement('h3');h.textContent=category;host.append(h)}const row=document.createElement('div');row.className='v23-shortcut-item';row.dataset.commandId=item.id;const shortcuts=item.shortcuts.length?item.shortcuts.map(registry.formatChord).join(' · '):'Not assigned';row.innerHTML='<span><strong></strong><small></small></span><kbd></kbd><button type="button" data-record>Change</button>';$('strong',row).textContent=item.title;$('small',row).textContent=item.id;$('kbd',row).textContent=shortcuts;$('[data-record]',row).onclick=()=>beginCapture(item.id);host.append(row)}showConflicts()
}
function showConflicts(extra=[]){const box=$('.v23-conflicts',surface);if(!box)return;const conflicts=[...registry.conflicts,...extra];box.hidden=!conflicts.length;box.textContent=conflicts.length?`Shortcut conflict: ${conflicts.map(x=>`${registry.formatChord(x.chord)} (${x.commands.join(' / ')})`).join(', ')}`:''}
function render(){if(!surface)return;surface.dataset.mode=mode;$$('[data-mode]',surface).forEach(button=>button.classList.toggle('active',button.dataset.mode===mode));$('#v23CommandTitle').textContent=mode==='commands'?'Quick Actions':'Keyboard shortcuts';$('[data-profile-label]',surface).textContent=`Profile: ${profileTitle(registry.profile)}`;if(mode==='commands')renderCommands();else renderShortcuts()}
function profileTitle(profile){return profile==='photoshop'?'Photoshop-like':profile==='canva'?'Canva-like':'E-Invitation Standard'}
function syncActive(){rows().forEach((row,index)=>row.classList.toggle('active',index===active));rows()[active]?.scrollIntoView({block:'nearest'})}
function runItem(index){const item=currentItems[index];if(!item)return;closeSurface();if(item.commandId)registry.execute(item.commandId);else Promise.resolve(item.run?.()).catch(error=>window.uiToast?.(error?.message||'Action failed','!'))}
function trapTab(event){const focusable=$$('button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])',surface).filter(node=>node.offsetParent!==null);if(!focusable.length)return;const first=focusable[0],last=focusable.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
function keydown(event){
 if(captureCommand){captureKey(event);return}
 if(event.key==='Escape'){event.preventDefault();closeSurface();return}
 if(event.key==='Tab'){trapTab(event);return}
 if(mode!=='commands')return;
 const list=rows();if(event.key==='ArrowDown'){event.preventDefault();active=Math.min(list.length-1,active+1);syncActive()}else if(event.key==='ArrowUp'){event.preventDefault();active=Math.max(0,active-1);syncActive()}else if(event.key==='Enter'&&list[active]&&!list[active].disabled){event.preventDefault();runItem(active)}
}
function beginCapture(commandId){captureCommand=commandId;const row=$(`.v23-shortcut-item[data-command-id="${CSS.escape(commandId)}"]`,surface);row?.classList.add('recording');const key=row?.querySelector('kbd');if(key)key.textContent='Press shortcut…';surface.dataset.capturing='true'}
function captureKey(event){event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();if(event.key==='Escape'){captureCommand='';delete surface.dataset.capturing;render();return}if(['Control','Meta','Alt','Shift'].includes(event.key))return;const chord=registry.eventChord(event),conflicts=registry.validateOverride(registry.profile,captureCommand,[chord]);if(conflicts.length){showConflicts(conflicts);const row=$(`.v23-shortcut-item[data-command-id="${CSS.escape(captureCommand)}"]`,surface);row?.classList.add('conflict');const key=row?.querySelector('kbd');if(key)key.textContent=`${registry.formatChord(chord)} conflicts`;return}registry.setOverride(captureCommand,[chord]);captureCommand='';delete surface.dataset.capturing;render()}
function open(next='commands'){build();mode=next==='shortcuts'?'shortcuts':'commands';previousFocus=document.activeElement;surface.hidden=false;document.body.classList.add('v23-command-open');$('input',surface).value='';active=0;render();requestAnimationFrame(()=>$('input',surface)?.focus())}
function closeSurface(){if(!surface||surface.hidden)return;++renderNonce;clearTimeout(searchTimer);captureCommand='';delete surface.dataset.capturing;surface.hidden=true;document.body.classList.remove('v23-command-open');previousFocus?.focus?.({preventScroll:true})}
function onChange(){if(surface&&!surface.hidden)render()}
registry.subscribe(onChange);window.addEventListener('einvite:assets-changed',()=>{assetCache=[];assetCacheAt=0});
window.EInviteCommandUI=Object.freeze({version:'23.0.3',open,close:closeSurface,get openState(){return!!surface&&!surface.hidden},get mode(){return mode}});
})();
