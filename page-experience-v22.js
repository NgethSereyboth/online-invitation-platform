(()=>{
'use strict';
if(window.__einvitePageExperienceV22)return;
window.__einvitePageExperienceV22=true;

const VERSION='22.2.8';
const MAX_THUMBS=72;
const EVENT_ROLES=['title','details','ceremony','photo','story','thankyou','quote','collage','split'];
const ROLE_LABELS={title:'Event title',details:'Event details',ceremony:'Ceremony',photo:'Photo feature',story:'Story',thankyou:'Thank you',quote:'Quote',collage:'Photo collage',split:'Split feature',custom:'Custom event page'};
const EVENT_TEXT_SPECS={
  title:{left:'10%',top:'12%',width:'80%',height:'110px',fontSize:42,fontWeight:'600',lineHeight:1.35,textAlign:'center'},
  date:{left:'16%',top:'35%',width:'68%',height:'88px',fontSize:29,fontWeight:'400',lineHeight:1.45,textAlign:'center'},
  venue:{left:'12%',top:'51%',width:'76%',height:'132px',fontSize:24,fontWeight:'400',lineHeight:1.55,textAlign:'center'},
  body:{left:'14%',top:'31%',width:'72%',height:'270px',fontSize:23,fontWeight:'400',lineHeight:1.65,textAlign:'center'}
};

const bridge=()=>window.EInviteEditorBridge;
const clone=value=>window.EInviteEditorSchema?.clone?.(value)??(typeof structuredClone==='function'?structuredClone(value):JSON.parse(JSON.stringify(value)));
const token=id=>`page:${id}`;
const pageIdFromCanvas=canvas=>String(canvas||'').startsWith('page:')?String(canvas).slice(5):'';
const state=()=>bridge()?.getState?.()||{};
const pages=()=>Array.isArray(state().designPages)?state().designPages:[];
const activeId=()=>pageIdFromCanvas(bridge()?.getActiveCanvasId?.()||'hero');
const cache=new Map();
const thumbTimers=new Map();
const thumbJobs=new Map();
const lifecycle=new AbortController();
const signal=lifecycle.signal;

let manager=null;
let grid=null;
let inspector=null;
let sourceNav=null;
let thumbObserver=null;
let dockObserver=null;
let managerIdle=0;
let renderQueued=false;
let renderSequence=0;
let filter='all';
let enhancingDock=false;
let saveTimer=0;
let dockRetryTimer=0;
let openMenuState=null;
let pointerReorder=null;
let dockPointerReorder=null;
let pointerGestureCleanup=null;
let lastListSignature='';
let lastChromeSignature='';
let pendingRenderOptions={force:false,focusId:'',preserveScroll:true};

function uid(prefix='page'){return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`}
function pageMode(page){if(page?.editMode==='free-design'||page?.editMode==='event-template')return page.editMode;return EVENT_ROLES.includes(String(page?.preset||''))?'event-template':'free-design'}
function pageRole(page){return String(page?.eventRole||page?.preset||'custom')}
function activePage(){return pages().find(page=>page.id===activeId())||null}
function pageListSignature(){return `${filter}|${pages().map(page=>page.id).join('|')}`}
function pageChromeSignature(){return pages().map(page=>[page.id,page.name,page.enabled!==false,pageMode(page),pageRole(page),page.useMasterBackground===true].join(':')).join('|')}
function activeInsertIndex(){const list=pages(),index=list.findIndex(page=>page.id===activeId());return index<0?list.length:index+1}
function uniquePageName(base,list=pages()){
  const normalized=String(base||'Untitled page').trim()||'Untitled page';
  const names=new Set(list.map(page=>String(page.name||'').trim().toLocaleLowerCase()));
  if(!names.has(normalized.toLocaleLowerCase()))return normalized;
  let number=2;
  while(names.has(`${normalized} ${number}`.toLocaleLowerCase()))number++;
  return `${normalized} ${number}`;
}
function roleLabel(role){return ROLE_LABELS[role]||ROLE_LABELS.custom}
function fnvStep(hash,value){const text=String(value??'');for(let i=0;i<text.length;i++){hash^=text.charCodeAt(i);hash=Math.imul(hash,16777619)}return hash>>>0}
function pageFingerprint(page){
  const master=state().masterPageStyle||{};
  const source=page?.useMasterBackground&&master.enabled?master:page||{};
  let hash=2166136261;
  [source.background,source.backgroundImage,source.backgroundSize,source.backgroundOverlay,page?.enabled,pageMode(page),pageRole(page)].forEach(value=>{hash=fnvStep(hash,value)});
  const entries=Object.entries(page?.objects||{}).sort(([a],[b])=>a.localeCompare(b));
  for(const [id,o] of entries){
    hash=fnvStep(hash,id);
    for(const key of ['type','left','top','width','height','rotation','src','html','fillColor','color','font','fontFamily','fontId','fontSize','fontWeight','lineHeight','letterSpacing','opacity','visible','zIndex','imageMask','imageFrame','borderRadius','shadowBlur','blendMode'])hash=fnvStep(hash,o?.[key]);
  }
  return hash.toString(36);
}
function rememberThumb(key,html){cache.delete(key);cache.set(key,html);while(cache.size>MAX_THUMBS)cache.delete(cache.keys().next().value)}
function invalidatePageCache(id){const prefix=`${id}:`;for(const key of [...cache.keys()])if(key.startsWith(prefix))cache.delete(key)}
function thumbnailRenderer(){try{if(typeof pageThumbnailObjects==='function')return pageThumbnailObjects}catch{}return window.pageThumbnailObjects}
function cancelThumbJob(root){const job=thumbJobs.get(root);if(job==null)return;if('cancelIdleCallback'in window)cancelIdleCallback(job);else clearTimeout(job);thumbJobs.delete(root)}
function hydrateThumbnail(root,page,{immediate=false}={}){
  if(!root||!page||root.dataset.hydrated==='true')return;
  renderQuickThumbnail(root,page);
  cancelThumbJob(root);
  const key=`${page.id}:${pageFingerprint(page)}`;
  const hit=cache.get(key);
  if(hit!=null){root.innerHTML=hit;root.dataset.hydrated='true';delete root.dataset.quickFingerprint;return}
  const run=()=>{
    thumbJobs.delete(root);
    if(document.hidden||!root.isConnected||root.dataset.hydrated==='true')return;
    try{
      const renderer=thumbnailRenderer();
      if(renderer){root.innerHTML='';renderer(page,root);root.dataset.hydrated='true';delete root.dataset.quickFingerprint;rememberThumb(key,root.innerHTML)}
      else root.dataset.hydrated='unavailable';
    }catch{root.dataset.hydrated='error'}
  };
  if(immediate){run();return}
  const handle='requestIdleCallback'in window?requestIdleCallback(run,{timeout:320}):setTimeout(run,24);
  thumbJobs.set(root,handle);
}
function observeThumbs(container){
  thumbObserver?.disconnect();
  if(!container)return;
  thumbObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{
    if(!entry.isIntersecting)return;
    const id=entry.target.dataset.pageThumbId;
    const page=pages().find(item=>item.id===id);
    if(page){renderQuickThumbnail(entry.target,page);hydrateThumbnail(entry.target,page,{immediate:page.id===activeId()})}
  }),{root:container,rootMargin:'180px'});
  container.querySelectorAll('[data-page-thumb-id]').forEach(node=>thumbObserver.observe(node));
}
function transact(label,mutator,options={}){return window.EInviteCommands?.execute?.(label,mutator,{render:false,capture:false,...options})}
function syncPageTokens(doc){
  const ordered=(doc.designPages||[]).map(page=>token(page.id));
  let cursor=0;
  const previous=Array.isArray(doc.sectionOrder)?doc.sectionOrder:[];
  doc.sectionOrder=previous.map(item=>String(item).startsWith('page:')?(ordered[cursor++]||null):item).filter(Boolean);
  while(cursor<ordered.length)doc.sectionOrder.push(ordered[cursor++]);
  const field=document.querySelector('#sectionOrder');
  if(field)field.value=doc.sectionOrder.join('\n');
}
function presetFactory(){try{return typeof designPagePreset==='function'?designPagePreset:window.designPagePreset}catch{return window.designPagePreset}}
function pageObjectFactory(){try{return typeof pageObject==='function'?pageObject:window.pageObject}catch{return window.pageObject}}
function defaultPage(mode='free-design',role='custom',existing=pages()){
  if(mode==='event-template'){
    const create=presetFactory();
    if(create){
      const normalized=role==='custom'?'title':role;
      const page=create(normalized);
      page.editMode='event-template';
      page.eventRole=normalized;
      page.name=uniquePageName(page.name||roleLabel(normalized),existing);
      return page;
    }
  }
  return{id:uid(),name:uniquePageName('Untitled design',existing),preset:'blank',editMode:'free-design',eventRole:'',enabled:true,background:'#fffaf6',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0,useMasterBackground:false,animation:{preset:'fade-up',duration:900},transition:{preset:'soft',duration:600},objects:{}};
}
function updateActiveChrome(){
  const id=activeId();
  document.querySelectorAll('.v22-page-card[data-page-id]').forEach(card=>card.classList.toggle('active',card.dataset.pageId===id));
  document.querySelectorAll('#workflowPageDock .workflow-page-chip[data-page-id]').forEach(chip=>chip.classList.toggle('active',chip.dataset.pageId===id));
  document.querySelectorAll('.page-nav-card').forEach(card=>card.classList.toggle('active',card.dataset.pageId?card.dataset.pageId===id:!id));
}
function prewarmActiveThumbnail(){
  const page=activePage();
  if(!page)return;
  const node=grid?.querySelector(`[data-page-thumb-id="${CSS.escape(page.id)}"]`);
  if(node)hydrateThumbnail(node,page,{immediate:true});
}
function activateCanvas(canvas){
  try{if(typeof switchCanvas==='function')switchCanvas(canvas);else window.switchCanvas?.(canvas)}catch{}
  requestAnimationFrame(()=>{updateActiveChrome();renderInspector();prewarmActiveThumbnail()});
}
function addPage({mode='free-design',role='custom',index}={}){
  let created;
  const insertion=index==null?activeInsertIndex():Math.max(0,Math.min(Number(index)||0,pages().length));
  transact(mode==='free-design'?'Add blank design page':'Add event page',doc=>{
    const list=[...(doc.designPages||[])];
    created=defaultPage(mode,role,list);
    list.splice(Math.max(0,Math.min(insertion,list.length)),0,created);
    doc.designPages=list;
    syncPageTokens(doc);
  });
  renderAll({force:true,focusId:created?.id});
  if(created)setTimeout(()=>activateCanvas(token(created.id)),0);
  return created;
}
function duplicatePage(id){
  let copy;
  transact('Duplicate page',doc=>{
    const list=[...(doc.designPages||[])],at=list.findIndex(page=>page.id===id);
    if(at<0)return;
    copy=clone(list[at]);
    copy.id=uid();
    copy.name=uniquePageName(`${copy.name||'Page'} Copy`,list);
    copy.objects=Object.fromEntries(Object.entries(copy.objects||{}).map(([key,value],i)=>{const suffix=key.split('-').pop()||Math.random().toString(36).slice(2,6);const next=clone(value);return [`${copy.id}-object-${i}-${suffix}`,next]}));
    list.splice(at+1,0,copy);
    doc.designPages=list;
    syncPageTokens(doc);
  });
  renderAll({force:true,focusId:copy?.id});
  if(copy)setTimeout(()=>activateCanvas(token(copy.id)),0);
  return copy;
}
async function deletePage(id){
  const list=pages();
  const index=list.findIndex(page=>page.id===id);
  if(index<0)return false;
  const fallback=list[index+1]?.id||list[index-1]?.id||'';
  const ask=window.uiConfirm?await window.uiConfirm('Remove this page from the invitation?',{title:'Remove page',danger:true,confirmText:'Remove'}):confirm('Remove this page from the invitation?');
  if(!ask)return false;
  transact('Delete page',doc=>{
    doc.designPages=(doc.designPages||[]).filter(page=>page.id!==id);
    doc.sectionOrder=(doc.sectionOrder||[]).filter(item=>item!==token(id));
    syncPageTokens(doc);
  });
  invalidatePageCache(id);
  renderAll({force:true,focusId:fallback});
  if(activeId()===id)setTimeout(()=>activateCanvas(fallback?token(fallback):'hero'),0);
  return true;
}
function reorderPage(id,to){
  let changed=false;
  transact('Reorder pages',doc=>{
    const list=[...(doc.designPages||[])],from=list.findIndex(page=>page.id===id);
    if(from<0)return;
    const target=Math.max(0,Math.min(Number(to)||0,list.length-1));
    if(from===target)return;
    const [moved]=list.splice(from,1);
    list.splice(Math.max(0,Math.min(target,list.length)),0,moved);
    doc.designPages=list;
    syncPageTokens(doc);
    changed=true;
  });
  if(changed)renderAll({force:true,focusId:id,preserveScroll:true});
  return changed;
}
function renamePage(id,name){
  const clean=String(name||'').trim().slice(0,120)||'Untitled page';
  transact('Rename page',doc=>{const page=(doc.designPages||[]).find(item=>item.id===id);if(page)page.name=clean},{coalesceKey:`page-name:${id}`,coalesceDelay:350});
  refreshPageChrome();
}
function applyPresetToPage(page,preset,role){
  const keep={id:page.id,name:page.name,enabled:page.enabled,editMode:'event-template',eventRole:role,preset:role};
  Object.assign(page,clone(preset),keep);
  const remapped={};
  Object.entries(page.objects||{}).forEach(([key,value],index)=>{const suffix=key.split('-').pop()||`object-${index}`;if(['title','date','venue','body'].includes(suffix))value.eventField=suffix;remapped[`${page.id}-preset-${index}-${suffix}`]=value});
  page.objects=remapped;
}
async function applyEventPreset(id,role=pageRole(pages().find(page=>page.id===id))){
  const current=pages().find(page=>page.id===id);
  if(!current)return false;
  const hasObjects=Object.keys(current.objects||{}).length>0;
  if(hasObjects){
    const ask=window.uiConfirm?await window.uiConfirm('Replace the current page objects and background with this event layout? This is undoable.',{title:'Apply event layout',confirmText:'Apply layout'}):confirm('Replace this page with the selected event layout?');
    if(!ask)return false;
  }
  const create=presetFactory();
  if(!create)return false;
  transact('Apply event page layout',doc=>{
    const page=(doc.designPages||[]).find(item=>item.id===id);
    if(!page)return;
    const normalized=role==='custom'?'title':role;
    applyPresetToPage(page,create(normalized),normalized);
  });
  invalidatePageCache(id);
  renderAll({force:true,focusId:id});
  setTimeout(()=>activateCanvas(token(id)),0);
  return true;
}
function setPageMode(id,mode,role){
  let changed=false;
  transact('Change page editing mode',doc=>{
    const page=(doc.designPages||[]).find(item=>item.id===id);
    if(!page)return;
    const nextRole=role||page.eventRole||page.preset||'title';
    if(mode==='event-template'&&!Object.keys(page.objects||{}).length){
      const create=presetFactory();
      if(create)applyPresetToPage(page,create(nextRole==='custom'?'title':nextRole),nextRole==='custom'?'title':nextRole);
    }else{
      page.editMode=mode;
      page.eventRole=mode==='event-template'?nextRole:'';
      if(mode==='event-template')page.preset=nextRole;
    }
    changed=true;
  });
  if(changed){invalidatePageCache(id);renderAll({force:true,focusId:id})}
}
function patchPage(id,patch,label='Update page'){
  transact(label,doc=>{const page=(doc.designPages||[]).find(item=>item.id===id);if(page)Object.assign(page,patch)},{coalesceKey:`page-settings:${id}`,coalesceDelay:300});
  invalidatePageCache(id);
  if(label==='Toggle page visibility'||label==='Use master page background')refreshPageChrome();
  schedulePageThumbnail(id);
}
function isEventFieldEntry(key,object,suffix){return object?.eventField===suffix||key.endsWith(`-${suffix}`)||key.includes(`-${suffix}-`)}
function createEventTextObject(suffix,value){
  const spec=EVENT_TEXT_SPECS[suffix]||EVENT_TEXT_SPECS.body;
  const factory=pageObjectFactory();
  const options={...spec,html:String(value||''),color:'#3d292f',font:'Georgia,serif',zIndex:20,eventField:suffix};
  return factory?factory('text',options):{type:'text',...options,fontStyle:'normal',letterSpacing:0,opacity:1,locked:false,rotation:0,visible:true};
}
function setObjectTextBySuffix(id,suffix,value){
  transact('Update event page content',doc=>{
    const page=(doc.designPages||[]).find(item=>item.id===id);
    if(!page)return;
    const entry=Object.entries(page.objects||{}).find(([key,o])=>isEventFieldEntry(key,o,suffix)&&['text','decoration'].includes(o.type));
    if(entry)entry[1].html=String(value||'');
    else page.objects[`${page.id}-event-${suffix}`]=createEventTextObject(suffix,value);
  },{coalesceKey:`page-content:${id}:${suffix}`,coalesceDelay:320});
  invalidatePageCache(id);
  schedulePageThumbnail(id);
  if(id===activeId())requestAnimationFrame(()=>bridge()?.render?.());
}
function makeButton(text,label,action,className=''){
  const button=document.createElement('button');
  button.type='button';
  button.textContent=text;
  button.className=className;
  button.setAttribute('aria-label',label);
  button.title=label;
  button.onclick=event=>{event.preventDefault();event.stopPropagation();action(event)};
  return button;
}
function closeMenu({restoreFocus=true}={}){
  if(!openMenuState)return;
  const {menu,anchor,controller}=openMenuState;
  openMenuState=null;
  controller.abort();
  menu.remove();
  anchor?.removeAttribute('aria-expanded');
  if(restoreFocus&&anchor?.isConnected)anchor.focus({preventScroll:true});
}
function positionMenu(menu,anchor,{preferAbove=false,width=250}={}){
  const rect=anchor.getBoundingClientRect();
  const viewportPadding=8;
  const menuWidth=Math.min(width,innerWidth-viewportPadding*2);
  menu.style.width=`${menuWidth}px`;
  menu.style.left=`${Math.max(viewportPadding,Math.min(innerWidth-menuWidth-viewportPadding,rect.left))}px`;
  const height=Math.min(menu.scrollHeight||430,innerHeight-viewportPadding*2);
  const above=rect.top-height-8;
  const below=rect.bottom+8;
  const top=preferAbove&&above>=viewportPadding?above:(below+height<=innerHeight-viewportPadding?below:Math.max(viewportPadding,above));
  menu.style.top=`${top}px`;
}
function openMenu(menu,anchor,options={}){
  closeMenu({restoreFocus:false});
  const controller=new AbortController();
  openMenuState={menu,anchor,controller};
  menu.classList.add('v22-page-menu');
  menu.setAttribute('role','dialog');
  menu.setAttribute('aria-modal','false');
  anchor.setAttribute('aria-expanded','true');
  document.body.append(menu);
  positionMenu(menu,anchor,options);
  const buttons=()=>[...menu.querySelectorAll('button:not([disabled])')];
  menu.addEventListener('keydown',event=>{
    const items=buttons();
    if(event.key==='Escape'){event.preventDefault();closeMenu();return}
    if(!['ArrowDown','ArrowUp','Home','End'].includes(event.key))return;
    event.preventDefault();
    const current=Math.max(0,items.indexOf(document.activeElement));
    const next=event.key==='Home'?0:event.key==='End'?items.length-1:(current+(event.key==='ArrowDown'?1:-1)+items.length)%items.length;
    items[next]?.focus();
  },{signal:controller.signal});
  document.addEventListener('pointerdown',event=>{if(!menu.contains(event.target)&&event.target!==anchor)closeMenu({restoreFocus:false})},{capture:true,signal:controller.signal});
  window.addEventListener('resize',()=>positionMenu(menu,anchor,options),{signal:controller.signal});
  requestAnimationFrame(()=>buttons()[0]?.focus());
}
function addMenuButton(menu,{label,description='',role='',mode='',icon=''}){
  const button=document.createElement('button');
  button.type='button';
  if(role)button.dataset.role=role;
  if(mode)button.dataset.addMode=mode;
  if(description){button.className='v22-page-menu-rich';button.innerHTML='<span aria-hidden="true"></span><b></b><small></small>';button.querySelector('span').textContent=icon||'＋';button.querySelector('b').textContent=label;button.querySelector('small').textContent=description}
  else button.textContent=label;
  menu.append(button);
  return button;
}
function openAddMenu(anchor,index=activeInsertIndex()){
  const menu=document.createElement('div');
  const header=document.createElement('header');
  const title=document.createElement('div');
  title.innerHTML='<strong>Add page</strong><small></small>';
  title.querySelector('small').textContent=index>=pages().length?'At the end':`Before page ${index+1}`;
  const close=makeButton('×','Close add page menu',()=>closeMenu());
  header.append(title,close);
  menu.append(header);
  addMenuButton(menu,{label:'Blank free design',description:'Unrestricted poster-style canvas',mode:'free-design',icon:'＋'});
  const divider=document.createElement('hr');menu.append(divider);
  const section=document.createElement('small');section.className='v22-menu-label';section.textContent='Event page templates';menu.append(section);
  for(const role of EVENT_ROLES)addMenuButton(menu,{label:roleLabel(role),role});
  menu.addEventListener('click',event=>{
    const button=event.target.closest('button');
    if(!button||button===close)return;
    if(button.dataset.addMode)addPage({mode:'free-design',index});
    else if(button.dataset.role)addPage({mode:'event-template',role:button.dataset.role,index});
    closeMenu({restoreFocus:false});
  });
  openMenu(menu,anchor,{preferAbove:anchor.closest('#workflowPageDock')!=null,width:268});
}
function openPageMenu(page,anchor){
  const menu=document.createElement('div');
  const actions=[
    ['open','Open canvas'],['rename','Rename'],['duplicate','Duplicate'],['first','Move to first page'],['last','Move to last page'],
    [pageMode(page)==='free-design'?'event':'free',pageMode(page)==='free-design'?'Convert to event page':'Convert to free design'],
    ...(pageMode(page)==='event-template'?[['layout','Apply event layout']]:[])
  ];
  actions.forEach(([action,label])=>{const button=document.createElement('button');button.type='button';button.dataset.a=action;button.textContent=label;menu.append(button)});
  const divider=document.createElement('hr');menu.append(divider);
  const remove=document.createElement('button');remove.type='button';remove.dataset.a='delete';remove.className='danger';remove.textContent='Delete';menu.append(remove);
  menu.addEventListener('click',async event=>{
    const action=event.target.closest('button')?.dataset.a;
    if(!action)return;
    closeMenu({restoreFocus:false});
    if(action==='open')activateCanvas(token(page.id));
    else if(action==='rename'){
      const promptFn=window.uiPrompt;
      const next=promptFn?await promptFn('Choose a page name:',page.name||'Untitled page',{title:'Rename page',confirmText:'Rename'}):prompt('Page name',page.name||'Untitled page');
      if(next!=null)renamePage(page.id,next);
    }else if(action==='duplicate')duplicatePage(page.id);
    else if(action==='first')reorderPage(page.id,0);
    else if(action==='last')reorderPage(page.id,pages().length-1);
    else if(action==='event')setPageMode(page.id,'event-template',pageRole(page)==='custom'?'title':pageRole(page));
    else if(action==='free')setPageMode(page.id,'free-design','');
    else if(action==='layout')applyEventPreset(page.id,pageRole(page));
    else if(action==='delete')deletePage(page.id);
  });
  openMenu(menu,anchor,{width:220});
}
function applyThumbBackground(thumb,page){
  const master=state().masterPageStyle||{},source=page?.useMasterBackground&&master.enabled?master:page||{};
  thumb.style.backgroundColor=source.background||'#fffaf6';
  thumb.style.backgroundImage='';
  if(source.backgroundImage){
    thumb.style.backgroundImage=`linear-gradient(rgba(0,0,0,${Number(source.backgroundOverlay||0)/100}),rgba(0,0,0,${Number(source.backgroundOverlay||0)/100})),url("${String(source.backgroundImage).replace(/"/g,'%22')}")`;
    thumb.style.backgroundSize=source.backgroundSize==='contain'?'contain':'cover';
    thumb.style.backgroundPosition='center';
  }
}
function thumbPercent(value,axis='x'){
  const raw=String(value??'').trim();
  if(raw.endsWith('%')){const number=parseFloat(raw);return `${Math.max(-20,Math.min(120,Number.isFinite(number)?number:0))}%`}
  const number=parseFloat(raw);if(!Number.isFinite(number))return'0%';
  const base=axis==='y'?844:390;
  return `${Math.max(-20,Math.min(120,number/base*100))}%`;
}
function quickText(value){
  const host=document.createElement('div');host.innerHTML=String(value||'');
  return (host.textContent||'').replace(/\s+/g,' ').trim().slice(0,72);
}
function renderQuickThumbnail(root,page){
  if(!root||!page||root.dataset.hydrated==='true')return;
  const fingerprint=pageFingerprint(page);
  if(root.dataset.quickFingerprint===fingerprint&&root.querySelector('.v22-quick-preview'))return;
  root.querySelector('.v22-quick-preview')?.remove();
  const layer=document.createElement('div');layer.className='v22-quick-preview';layer.setAttribute('aria-hidden','true');
  const objects=Object.values(page.objects||{}).filter(object=>object&&object.visible!==false).sort((a,b)=>Number(a.zIndex||0)-Number(b.zIndex||0)).slice(-8);
  for(const object of objects){
    const node=document.createElement('span');
    const type=String(object.type||'text');
    node.className=`v22-quick-object v22-quick-${type}`;
    node.style.left=thumbPercent(object.left,'x');node.style.top=thumbPercent(object.top,'y');
    node.style.width=thumbPercent(object.width,'x');node.style.height=thumbPercent(object.height,'y');
    node.style.opacity=String(Math.max(.12,Math.min(1,Number(object.opacity??1))));
    const rotation=Number(object.rotation||0);if(rotation)node.style.transform=`rotate(${rotation}deg)`;
    if(type==='image'){
      node.style.background=object.dominantColor||'#d9d2cc';node.textContent='▧';
    }else if(type==='shape'||type==='decoration'){
      node.style.background=object.fillColor||object.color||'#c8a7af';
      if(type==='decoration'){const text=quickText(object.html);if(text){node.textContent=text;node.style.color=object.color||'#6f4652'}}
    }else{
      node.textContent=quickText(object.html||object.text)||'Text';
      node.style.color=object.color||'#4b3a3e';node.style.fontWeight=String(object.fontWeight||500);
      node.style.textAlign=object.textAlign||'center';
    }
    layer.append(node);
  }
  if(!objects.length){const empty=document.createElement('span');empty.className='v22-quick-empty';empty.textContent=pageMode(page)==='free-design'?'Blank design':'Event page';layer.append(empty)}
  root.append(layer);root.dataset.quickFingerprint=fingerprint;
}
function updateSourceCard(card,page,index){
  card.classList.toggle('active',page.id===activeId());
  card.classList.toggle('disabled',page.enabled===false);
  const thumb=card.querySelector('.page-thumb');
  applyThumbBackground(thumb,page);
  let icon=thumb.querySelector('span');
  if(!icon){icon=document.createElement('span');thumb.append(icon)}
  const nextIcon=pageMode(page)==='free-design'?'✦':'▣';
  if(icon.textContent!==nextIcon)icon.textContent=nextIcon;
  const label=card.querySelector('strong');
  const nextLabel=page.name||`Page ${index+1}`;
  if(label.textContent!==nextLabel)label.textContent=nextLabel;
}
function renderSourceNavigator(){
  sourceNav=document.querySelector('#pageNavigator');
  if(!sourceNav)return;
  const list=pages(),signature=`hero|${list.map(page=>page.id).join('|')}`;
  const existing=new Map([...sourceNav.querySelectorAll('.page-nav-card')].map(card=>[card.dataset.pageId||'hero',card]));
  let hero=existing.get('hero');
  if(!hero){hero=document.createElement('button');hero.type='button';hero.className='page-nav-card hero-card';hero.innerHTML='<div class="page-thumb hero-thumb"><span>MAIN</span></div><strong>Main hero</strong>';hero.onclick=()=>activateCanvas('hero')}
  hero.classList.toggle('active',!activeId());
  if(sourceNav.dataset.v22Structure!==signature){
    const fragment=document.createDocumentFragment();fragment.append(hero);
    list.forEach((page,index)=>{
      let card=existing.get(page.id);
      if(!card){
        card=document.createElement('div');card.className='page-nav-card';card.dataset.pageId=page.id;
        const thumb=document.createElement('button');thumb.type='button';thumb.className='page-thumb';thumb.dataset.pageDockThumbId=page.id;thumb.onclick=()=>activateCanvas(token(page.id));
        const label=document.createElement('strong');card.append(thumb,label);
      }
      updateSourceCard(card,page,index);fragment.append(card);
    });
    sourceNav.replaceChildren(fragment);sourceNav.dataset.v22Structure=signature;
  }else list.forEach((page,index)=>{const card=existing.get(page.id);if(card)updateSourceCard(card,page,index)});
  sourceNav.hidden=true;
  enhanceWorkflowDockSoon();
}
function clearDropIndicators(){grid?.querySelectorAll('.v22-drop-before,.v22-drop-after,.v22-drop-target').forEach(node=>node.classList.remove('v22-drop-before','v22-drop-after','v22-drop-target'))}
function cardDropIndex(card,clientX,clientY){
  const visibleCards=[...grid.querySelectorAll('.v22-page-card[data-page-id]')];
  const index=visibleCards.indexOf(card);
  const rect=card.getBoundingClientRect();
  const columns=getComputedStyle(grid).gridTemplateColumns.split(' ').length;
  const after=columns>1?clientX>rect.left+rect.width/2:clientY>rect.top+rect.height/2;
  const pageIndex=pages().findIndex(page=>page.id===card.dataset.pageId);
  return Math.max(0,pageIndex+(after?1:0));
}
function autoScrollGrid(clientY){if(!grid)return;const rect=grid.getBoundingClientRect(),edge=54;if(clientY<rect.top+edge)grid.scrollTop-=18;else if(clientY>rect.bottom-edge)grid.scrollTop+=18}
function beginPointerReorder(event,page,card,handle){
  if(event.button!=null&&event.button!==0)return;
  event.preventDefault();
  pointerGestureCleanup?.();
  closeMenu({restoreFocus:false});
  const pointerId=event.pointerId;
  handle.setPointerCapture?.(pointerId);
  pointerReorder={id:page.id,card,handle,pointerId,target:null,moved:false,startX:event.clientX,startY:event.clientY};
  card.classList.add('v22-pointer-armed');
  const move=moveEvent=>{
    if(!pointerReorder||moveEvent.pointerId!==pointerId)return;
    autoScrollGrid(moveEvent.clientY);
    const distance=Math.hypot(moveEvent.clientX-pointerReorder.startX,moveEvent.clientY-pointerReorder.startY);
    if(distance<5&&!pointerReorder.moved)return;
    pointerReorder.moved=true;
    card.classList.add('dragging');
    clearDropIndicators();
    const target=document.elementFromPoint(moveEvent.clientX,moveEvent.clientY)?.closest('.v22-page-card[data-page-id]');
    if(!target||target===card){pointerReorder.target=null;return}
    const index=cardDropIndex(target,moveEvent.clientX,moveEvent.clientY);
    pointerReorder.target=index;
    const targetPageIndex=pages().findIndex(item=>item.id===target.dataset.pageId);
    target.classList.add(index>targetPageIndex?'v22-drop-after':'v22-drop-before');
  };
  const finish=finishEvent=>{
    if(!pointerReorder||finishEvent.pointerId!==pointerId)return;
    const drag=pointerReorder;
    pointerReorder=null;
    handle.releasePointerCapture?.(pointerId);
    card.classList.remove('v22-pointer-armed','dragging');
    clearDropIndicators();
    document.removeEventListener('pointermove',move,true);
    document.removeEventListener('pointerup',finish,true);
    document.removeEventListener('pointercancel',cancel,true);pointerGestureCleanup=null;
    if(drag.moved&&drag.target!=null){
      const from=pages().findIndex(item=>item.id===drag.id);
      const target=drag.target-(from>=0&&from<drag.target?1:0);
      reorderPage(drag.id,target);
    }
  };
  const cancel=cancelEvent=>{if(cancelEvent&&cancelEvent.pointerId!==pointerId)return;pointerReorder=null;card.classList.remove('v22-pointer-armed','dragging');clearDropIndicators();document.removeEventListener('pointermove',move,true);document.removeEventListener('pointerup',finish,true);document.removeEventListener('pointercancel',cancel,true);pointerGestureCleanup=null};
  document.addEventListener('pointermove',move,true);
  document.addEventListener('pointerup',finish,true);
  document.addEventListener('pointercancel',cancel,true);
  pointerGestureCleanup=()=>cancel(null);
}
function createGridCard(page,index){
  const card=document.createElement('article');
  card.dataset.pageId=page.id;
  card.draggable=false;
  card.tabIndex=0;
  card.setAttribute('role','listitem');
  const thumb=document.createElement('button');
  thumb.type='button';
  thumb.className='v22-page-thumb';
  thumb.dataset.pageThumbId=page.id;
  thumb.onclick=()=>activateCanvas(token(page.id));
  const label=document.createElement('div');
  label.className='v22-page-label';
  label.innerHTML='<strong></strong><small></small>';
  const actions=document.createElement('div');
  actions.className='v22-page-actions';
  const dragHandle=makeButton('⠿','Drag to reorder page',()=>{},'v22-page-drag-handle');
  dragHandle.draggable=false;
  dragHandle.onclick=event=>{event.preventDefault();event.stopPropagation()};
  dragHandle.addEventListener('pointerdown',event=>beginPointerReorder(event,page,card,dragHandle));
  actions.append(dragHandle,makeButton('⧉','Duplicate page',()=>duplicatePage(page.id)),makeButton('⋯','Page actions',event=>openPageMenu(page,event.currentTarget)));
  card.append(thumb,label,actions);
  card.onclick=event=>{if(!event.target.closest('button'))activateCanvas(token(page.id))};
  card.onkeydown=event=>{
    if(event.key==='Enter'||event.key===' '){event.preventDefault();activateCanvas(token(page.id))}
    if(event.altKey&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
      event.preventDefault();
      const current=pages().findIndex(item=>item.id===page.id);
      const to=event.key==='Home'?0:event.key==='End'?pages().length-1:Math.max(0,Math.min(pages().length-1,current+(event.key==='ArrowLeft'?-1:1)));
      reorderPage(page.id,to);
      setTimeout(()=>grid?.querySelector(`[data-page-id="${CSS.escape(page.id)}"]`)?.focus(),0);
    }
  };
  updateGridCard(card,page,index);
  return card;
}
function updateGridCard(card,page,index){
  card.className=`v22-page-card${page.id===activeId()?' active':''}${page.enabled===false?' disabled':''}`;
  card.dataset.pageId=page.id;
  card.setAttribute('aria-label',`${page.name||`Page ${index+1}`}, ${pageMode(page)==='free-design'?'free design':roleLabel(pageRole(page))}`);
  const thumb=card.querySelector('.v22-page-thumb');
  thumb.dataset.pageThumbId=page.id;
  applyThumbBackground(thumb,page);
  if(thumb.dataset.hydrated!=='true')renderQuickThumbnail(thumb,page);
  const label=card.querySelector('.v22-page-label');
  label.querySelector('strong').textContent=page.name||`Page ${index+1}`;
  label.querySelector('small').textContent=pageMode(page)==='free-design'?'Free design':`Event · ${roleLabel(pageRole(page)).replace(/^Event /,'')}`;
  return card;
}
function renderGrid({focusId='',preserveScroll=true}={}){
  if(!grid)return;
  const scrollTop=grid.scrollTop;
  const activeElement=document.activeElement;
  const activeCard=activeElement?.closest?.('.v22-page-card[data-page-id]')||null;
  const focusedId=focusId||activeCard?.dataset.pageId||'';
  const existing=new Map([...grid.querySelectorAll('.v22-page-card[data-page-id]')].map(card=>[card.dataset.pageId,card]));
  const focusedCard=focusedId?existing.get(focusedId)||null:null;
  const visible=pages().filter(page=>filter==='all'||pageMode(page)===filter);
  const fragment=document.createDocumentFragment();
  visible.forEach(page=>{
    const index=pages().findIndex(item=>item.id===page.id);
    const card=existing.get(page.id)||createGridCard(page,index);
    updateGridCard(card,page,index);
    fragment.append(card);
  });
  let add=grid.querySelector('.v22-grid-add');
  if(!add){add=document.createElement('button');add.type='button';add.className='v22-grid-add';add.innerHTML='<span>＋</span><strong>Add page</strong><small>Blank or event template</small>'}
  add.onclick=event=>openAddMenu(event.currentTarget,activeInsertIndex());
  fragment.append(add);
  grid.replaceChildren(fragment);
  if(preserveScroll)grid.scrollTop=scrollTop;
  observeThumbs(grid);
  if(focusedId){const reconciled=grid.querySelector(`[data-page-id="${CSS.escape(focusedId)}"]`);if(reconciled?.isConnected&&(focusId||focusedCard===activeCard||focusedCard===activeElement))reconciled.focus({preventScroll:true})}
  prewarmActiveThumbnail();
}
function findText(page,suffix){const entry=Object.entries(page?.objects||{}).find(([key,o])=>isEventFieldEntry(key,o,suffix)&&['text','decoration'].includes(o.type));return entry?.[1]?.html||''}
function renderEventFields(host,page){
  if(pageMode(page)==='free-design'){
    host.innerHTML='<p class="hint">Free design keeps text, images, poster backgrounds, shapes, masks, and composition completely manual.</p>';
    return;
  }
  const role=pageRole(page),fields=[];
  if(['title','details','ceremony','story','thankyou','photo'].includes(role))fields.push(['title',role==='photo'?'Photo caption':'Page title']);
  if(['details','ceremony'].includes(role))fields.push(['date','Date text'],['venue','Venue text']);
  if(role==='story')fields.push(['body','Story text']);
  if(role==='thankyou')fields.push(['body','Message']);
  if(!fields.length){host.innerHTML='<p class="hint">This event page remains fully editable on the canvas. Use Apply layout to replace it with the selected event template.</p>';return}
  host.innerHTML='<strong class="v22-event-fields-title">Event content</strong>';
  fields.forEach(([suffix,label])=>{
    const control=document.createElement('label');
    control.textContent=label;
    const input=suffix==='body'?document.createElement('textarea'):document.createElement('input');
    input.value=findText(page,suffix);
    input.placeholder=`Enter ${label.toLocaleLowerCase()}`;
    input.oninput=()=>{clearTimeout(input.__timer);input.__timer=setTimeout(()=>setObjectTextBySuffix(page.id,suffix,input.value),180)};
    control.append(input);
    host.append(control);
  });
}
function renderInspector(){
  if(!inspector)return;
  const page=activePage();
  if(!page){inspector.innerHTML='<div class="v22-page-inspector-empty"><div><strong>Main hero canvas</strong><span>Add an event page or unrestricted free-design page.</span></div></div>';return}
  const mode=pageMode(page),role=pageRole(page),hasObjects=Object.keys(page.objects||{}).length>0;
  inspector.innerHTML=`<div class="v22-page-inspector-head"><div><strong>Current page</strong><span>${mode==='free-design'?'Free design canvas':roleLabel(role)}</span></div></div><div class="v22-page-inspector-body"><label>Page name<input data-name maxlength="120"></label><div class="v22-mode-switch"><button type="button" data-mode="event-template">Event template</button><button type="button" data-mode="free-design">Free design</button></div><label data-role-wrap>Event page type<select data-role></select></label><label>Background<input data-background type="color"></label><label class="toggle-row"><span>Use master background</span><input data-master type="checkbox"></label><label class="toggle-row"><span>Published</span><input data-enabled type="checkbox"></label><p class="v22-mode-note" data-mode-note></p><div data-event-fields></div><div class="v22-inspector-actions"><button type="button" data-open>Open canvas</button><button type="button" data-apply-layout>Apply layout</button><button type="button" data-duplicate>Duplicate</button><button type="button" data-delete class="danger">Delete</button></div></div>`;
  const name=inspector.querySelector('[data-name]');
  name.value=page.name||'';
  name.oninput=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>renamePage(page.id,name.value),160)};
  inspector.querySelectorAll('[data-mode]').forEach(button=>{button.classList.toggle('active',button.dataset.mode===mode);button.onclick=()=>setPageMode(page.id,button.dataset.mode,role)});
  const roleWrap=inspector.querySelector('[data-role-wrap]'),roleSelect=inspector.querySelector('[data-role]');
  for(const optionRole of [...EVENT_ROLES,'custom']){const option=document.createElement('option');option.value=optionRole;option.textContent=roleLabel(optionRole);roleSelect.append(option)}
  roleWrap.hidden=mode==='free-design';
  roleSelect.value=[...EVENT_ROLES,'custom'].includes(role)?role:'custom';
  roleSelect.onchange=()=>setPageMode(page.id,'event-template',roleSelect.value);
  const background=inspector.querySelector('[data-background]');
  background.value=page.background||'#fffaf6';
  background.disabled=page.useMasterBackground===true;
  background.oninput=()=>patchPage(page.id,{background:background.value,useMasterBackground:false},'Change page background');
  const master=inspector.querySelector('[data-master]');
  master.checked=page.useMasterBackground===true;
  master.onchange=()=>{background.disabled=master.checked;patchPage(page.id,{useMasterBackground:master.checked},'Use master page background')};
  const enabled=inspector.querySelector('[data-enabled]');
  enabled.checked=page.enabled!==false;
  enabled.onchange=()=>patchPage(page.id,{enabled:enabled.checked},'Toggle page visibility');
  const note=inspector.querySelector('[data-mode-note]');
  note.textContent=mode==='event-template'&&hasObjects?'Changing the event type preserves the current design. Apply layout only when you want to replace the page objects.':'Mode changes keep your existing objects unless an empty page receives a template.';
  inspector.querySelector('[data-open]').onclick=()=>activateCanvas(token(page.id));
  const apply=inspector.querySelector('[data-apply-layout]');
  apply.hidden=mode==='free-design';
  apply.onclick=()=>applyEventPreset(page.id,roleSelect.value);
  inspector.querySelector('[data-duplicate]').onclick=()=>duplicatePage(page.id);
  inspector.querySelector('[data-delete]').onclick=()=>deletePage(page.id);
  renderEventFields(inspector.querySelector('[data-event-fields]'),page);
}
function buildManager(){
  const host=document.querySelector('#designPagesManager');
  if(!host)return false;
  const pane=host.closest('[data-studio-pane="pages"]');
  if(pane){
    const anchor=pane.querySelector('.studio-tip-card')||pane.firstElementChild;
    if(anchor&&host.previousElementSibling!==anchor)anchor.after(host);
    pane.querySelector('.page-builder-library')?.setAttribute('hidden','');
    pane.querySelector('.page-builder-actions')?.setAttribute('hidden','');
  }
  if(host.dataset.v22Managed==='true'){
    manager=host.querySelector('.v22-page-manager');
    grid=host.querySelector('.v22-page-grid');
    inspector=host.querySelector('.v22-page-inspector');
    return true;
  }
  host.dataset.v22Managed='true';
  host.innerHTML=`<section class="v22-page-manager"><div class="v22-page-manager-toolbar"><div><strong>Design pages</strong><span data-page-count></span></div><div class="v22-page-filter"><button type="button" data-filter="all" class="active">All</button><button type="button" data-filter="event-template">Event</button><button type="button" data-filter="free-design">Free design</button></div><button type="button" data-add-page>＋ Add page</button></div><div class="v22-page-grid" role="list"></div><div class="v22-page-inspector"></div></section>`;
  manager=host.querySelector('.v22-page-manager');
  grid=host.querySelector('.v22-page-grid');
  inspector=host.querySelector('.v22-page-inspector');
  host.querySelector('[data-add-page]').onclick=event=>openAddMenu(event.currentTarget,activeInsertIndex());
  host.querySelectorAll('[data-filter]').forEach(button=>button.onclick=()=>{
    filter=button.dataset.filter;
    host.querySelectorAll('[data-filter]').forEach(item=>item.classList.toggle('active',item===button));
    renderGrid({preserveScroll:false});
  });
  return true;
}
function renderManager(options={}){
  if(!buildManager())return;
  const count=manager.querySelector('[data-page-count]');
  if(count)count.textContent=`${pages().length} visual page${pages().length===1?'':'s'}`;
  renderGrid(options);
  renderInspector();
}
function workflowTrack(){return document.querySelector('#workflowPageDock .workflow-page-dock-track')}
function pageChipIndex(chip){const id=chip?.dataset.pageId;return pages().findIndex(page=>page.id===id)}
function addDockInsert(index){const button=makeButton('＋','Add page here',event=>openAddMenu(event.currentTarget,index),'v22-workflow-insert');button.dataset.insertIndex=String(index);return button}
function autoScrollDock(clientX){const track=workflowTrack();if(!track)return;const rect=track.getBoundingClientRect(),edge=60;if(clientX<rect.left+edge)track.scrollLeft-=20;else if(clientX>rect.right-edge)track.scrollLeft+=20}
function dockDropIndex(clientX){
  const track=workflowTrack();if(!track)return null;
  const insert=document.elementFromPoint(clientX,Math.min(innerHeight-1,Math.max(1,track.getBoundingClientRect().top+18)))?.closest('.v22-workflow-insert');
  if(insert)return Number(insert.dataset.insertIndex);
  const chips=[...track.querySelectorAll('.workflow-page-chip[data-page-id]')];
  for(let index=0;index<chips.length;index++){const rect=chips[index].getBoundingClientRect();if(clientX<rect.left+rect.width/2)return index;if(clientX<=rect.right)return index+1}
  return chips.length;
}
function beginDockPointerReorder(event,chip,handle){
  if(event.button!=null&&event.button!==0)return;
  event.preventDefault();event.stopPropagation();pointerGestureCleanup?.();
  const pointerId=event.pointerId,id=chip.dataset.pageId;handle.setPointerCapture?.(pointerId);
  dockPointerReorder={id,chip,handle,pointerId,target:null,moved:false,startX:event.clientX,startY:event.clientY};chip.classList.add('v22-pointer-armed');
  const move=moveEvent=>{
    if(!dockPointerReorder||moveEvent.pointerId!==pointerId)return;
    autoScrollDock(moveEvent.clientX);
    if(Math.hypot(moveEvent.clientX-dockPointerReorder.startX,moveEvent.clientY-dockPointerReorder.startY)<5&&!dockPointerReorder.moved)return;
    dockPointerReorder.moved=true;chip.classList.add('dragging');
    const target=dockDropIndex(moveEvent.clientX);dockPointerReorder.target=target;
    const track=workflowTrack();track?.querySelectorAll('.v22-drop-target').forEach(node=>node.classList.remove('v22-drop-target'));
    track?.querySelector(`.v22-workflow-insert[data-insert-index="${target}"]`)?.classList.add('v22-drop-target');
  };
  const cleanup=()=>{handle.releasePointerCapture?.(pointerId);chip.classList.remove('v22-pointer-armed','dragging');workflowTrack()?.querySelectorAll('.v22-drop-target').forEach(node=>node.classList.remove('v22-drop-target'));document.removeEventListener('pointermove',move,true);document.removeEventListener('pointerup',finish,true);document.removeEventListener('pointercancel',cancel,true);pointerGestureCleanup=null};
  const finish=finishEvent=>{if(!dockPointerReorder||finishEvent.pointerId!==pointerId)return;const drag=dockPointerReorder;dockPointerReorder=null;cleanup();if(drag.moved&&drag.target!=null){const from=pages().findIndex(page=>page.id===drag.id);const target=drag.target-(from>=0&&from<drag.target?1:0);reorderPage(drag.id,target)}};
  const cancel=cancelEvent=>{if(cancelEvent&&cancelEvent.pointerId!==pointerId)return;dockPointerReorder=null;cleanup()};
  document.addEventListener('pointermove',move,true);document.addEventListener('pointerup',finish,true);document.addEventListener('pointercancel',cancel,true);pointerGestureCleanup=()=>cancel(null);
}
function ensureDockPointerHandle(chip){
  chip.draggable=false;chip.setAttribute('draggable','false');
  let handle=chip.querySelector('.v22-dock-drag-handle');
  if(!handle){
    handle=document.createElement('span');handle.className='v22-dock-drag-handle';handle.textContent='⠿';handle.title='Drag to reorder page';handle.setAttribute('aria-hidden','true');
    handle.addEventListener('pointerdown',event=>beginDockPointerReorder(event,chip,handle));handle.addEventListener('click',event=>{event.preventDefault();event.stopPropagation()});chip.append(handle);
  }
  return handle;
}
function enhanceWorkflowDock(){
  if(enhancingDock)return;
  const dock=document.querySelector('#workflowPageDock'),track=workflowTrack();
  if(!dock||!track)return;
  const chips=[...track.querySelectorAll('.workflow-page-chip')],pageChips=chips.filter(chip=>chip.dataset.pageId);
  const signature=pageChips.map(chip=>chip.dataset.pageId).join('|');
  const inserts=track.querySelectorAll('.v22-workflow-insert');
  const complete=track.dataset.v22Signature===signature&&inserts.length===pageChips.length+1;
  if(complete){pageChips.forEach(chip=>{ensureDockPointerHandle(chip);chip.dataset.pageMode=pageMode(pages().find(page=>page.id===chip.dataset.pageId));chip.classList.toggle('active',chip.dataset.pageId===activeId())});return}
  enhancingDock=true;
  track.dataset.v22Signature=signature;
  inserts.forEach(node=>node.remove());
  pageChips.forEach((chip,index)=>{
    chip.before(addDockInsert(index));
    ensureDockPointerHandle(chip);
    chip.dataset.pageMode=pageMode(pages().find(page=>page.id===chip.dataset.pageId));
    if(chip.dataset.v22Keyboard!=='true'){
      chip.dataset.v22Keyboard='true';
      chip.addEventListener('keydown',event=>{
        if(!event.altKey||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
        event.preventDefault();
        const current=pageChipIndex(chip),to=event.key==='Home'?0:event.key==='End'?pages().length-1:Math.max(0,Math.min(pages().length-1,current+(event.key==='ArrowLeft'?-1:1)));
        reorderPage(chip.dataset.pageId,to);
        setTimeout(()=>workflowTrack()?.querySelector(`[data-page-id="${CSS.escape(chip.dataset.pageId)}"]`)?.focus(),80);
      });
    }
  });
  track.append(addDockInsert(pages().length));
  const add=dock.querySelector('.workflow-page-add');
  if(add&&add.dataset.v22Capture!=='true'){
    add.dataset.v22Capture='true';
    add.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();openAddMenu(add,activeInsertIndex())},true);
  }
  track.dataset.v22Drag='pointer';
  enhancingDock=false;
}
function enhanceWorkflowDockSoon(){if(typeof queueMicrotask==='function')queueMicrotask(enhanceWorkflowDock);else Promise.resolve().then(enhanceWorkflowDock)}
function installDockObserver(){
  dockObserver?.disconnect();clearTimeout(dockRetryTimer);
  const dock=document.querySelector('#workflowPageDock');
  if(!dock){dockRetryTimer=setTimeout(installDockObserver,80);return}
  dockObserver=new MutationObserver(()=>enhanceWorkflowDockSoon());
  dockObserver.observe(dock,{childList:true,subtree:true});
  enhanceWorkflowDockSoon();
}
function refreshPageChrome(){
  const list=pages();
  for(const page of list){
    const label=page.name||'Untitled page';
    document.querySelectorAll(`[data-page-id="${CSS.escape(page.id)}"]`).forEach(node=>{
      node.classList.toggle('disabled',page.enabled===false);
      node.dataset.pageMode=pageMode(page);
      const strong=node.querySelector('.v22-page-label strong, strong');
      if(strong)strong.textContent=label;
      const small=node.querySelector('.v22-page-label small');
      if(small)small.textContent=pageMode(page)==='free-design'?'Free design':`Event · ${roleLabel(pageRole(page)).replace(/^Event /,'')}`;
    });
  }
  updateActiveChrome();
  lastChromeSignature=pageChromeSignature();
  enhanceWorkflowDockSoon();
}
function resetThumbnailNode(node,page,immediate=false){
  if(!node||!page)return;
  cancelThumbJob(node);
  node.innerHTML='';delete node.dataset.hydrated;delete node.dataset.quickFingerprint;applyThumbBackground(node,page);renderQuickThumbnail(node,page);
  if(immediate)hydrateThumbnail(node,page,{immediate:true});
  else{const rect=node.getBoundingClientRect();if(rect.bottom>=0&&rect.top<=innerHeight)hydrateThumbnail(node,page)}
}
function refreshPageThumbnail(id){
  const page=pages().find(item=>item.id===id);
  if(!page)return;
  invalidatePageCache(id);
  document.querySelectorAll(`[data-page-dock-thumb-id="${CSS.escape(id)}"]`).forEach(node=>applyThumbBackground(node,page));
  document.querySelectorAll(`.v22-page-grid [data-page-thumb-id="${CSS.escape(id)}"]`).forEach(node=>resetThumbnailNode(node,page,page.id===activeId()));
  enhanceWorkflowDockSoon();
}
function schedulePageThumbnail(id=activeId()){
  if(!id)return;
  const previous=thumbTimers.get(id);if(previous)clearTimeout(previous);
  thumbTimers.set(id,setTimeout(()=>{thumbTimers.delete(id);refreshPageThumbnail(id)},220));
}
function onEditorCommand(event){
  const label=String(event?.detail?.label||'');
  if(/^(Add blank design page|Add event page|Duplicate page|Delete page|Reorder pages|Change page editing mode|Apply event page layout)$/.test(label)){renderAll({force:true});return}
  if(label==='Rename page'||label==='Toggle page visibility'||label==='Use master page background'){refreshPageChrome();return}
  schedulePageThumbnail(activeId());
}
function deferredManagers(){
  try{if(typeof renderLayers==='function')renderLayers();if(typeof updateCanvasContextUI==='function')updateCanvasContextUI()}catch{}
  if(managerIdle){if('cancelIdleCallback'in window)cancelIdleCallback(managerIdle);else clearTimeout(managerIdle)}
  const secondary=()=>{
    managerIdle=0;
    try{
      if(typeof renderGalleryManager==='function')renderGalleryManager();
      if(typeof renderCustomBlocksManager==='function')renderCustomBlocksManager();
      if(typeof renderRsvpFieldsManager==='function')renderRsvpFieldsManager();
      if(typeof renderSavedBlockTemplates==='function')renderSavedBlockTemplates();
      renderManager();renderSourceNavigator();
      if(typeof renderSavedPageTemplates==='function')renderSavedPageTemplates();
      if(typeof renderSectionAnimationsManager==='function')renderSectionAnimationsManager();
      if(typeof renderSectionStylesManager==='function')renderSectionStylesManager();
    }catch(error){console.error(error)}
  };
  managerIdle='requestIdleCallback'in window?requestIdleCallback(secondary,{timeout:650}):setTimeout(secondary,70);
}
function renderAll({force=false,focusId='',preserveScroll=true}={}){
  pendingRenderOptions.force=pendingRenderOptions.force||force;
  if(focusId)pendingRenderOptions.focusId=focusId;
  if(preserveScroll===false)pendingRenderOptions.preserveScroll=false;
  if(renderQueued)return;
  renderQueued=true;
  requestAnimationFrame(()=>{
    const options=pendingRenderOptions;
    pendingRenderOptions={force:false,focusId:'',preserveScroll:true};
    renderQueued=false;
    const listSignature=pageListSignature();
    const chromeSignature=pageChromeSignature();
    const structureChanged=options.force||listSignature!==lastListSignature;
    const chromeChanged=structureChanged||chromeSignature!==lastChromeSignature;
    renderSourceNavigator();
    if(structureChanged){renderManager({focusId:options.focusId,preserveScroll:options.preserveScroll});lastListSignature=listSignature;lastChromeSignature=chromeSignature}
    else if(chromeChanged){renderGrid({focusId:options.focusId,preserveScroll:options.preserveScroll});renderInspector();refreshPageChrome()}
    else{updateActiveChrome();renderInspector();prewarmActiveThumbnail()}
    enhanceWorkflowDockSoon();
    document.documentElement.dataset.pageExperienceVersion=VERSION;renderSequence+=1;
  });
}
function scheduleRender(){schedulePageThumbnail(activeId())}
function hideLegacyNavigatorHeading(){
  const old=document.querySelector('#pageNavigator');
  if(!old)return;
  const hint=old.previousElementSibling,heading=hint?.previousElementSibling;
  if(hint?.classList.contains('hint'))hint.hidden=true;
  if(heading?.tagName==='H3')heading.hidden=true;
  old.hidden=true;
}
function installCss(){
  if(document.querySelector('link[data-v22-page-experience]'))return;
  const link=document.createElement('link');link.rel='stylesheet';link.href='page-experience-v22.css';link.dataset.v22PageExperience='';document.head.append(link);
}
function installOverrides(){
  try{window.renderPageNavigator=renderSourceNavigator;window.renderDesignPagesManager=renderManager;window.renderEditorManagers=deferredManagers}catch{}
  window.addEventListener('einvite:editor-command',onEditorCommand,{signal});
  window.addEventListener('einvite:editor-state-replaced',()=>renderAll({force:true}),{signal});
  document.addEventListener('einvite:professional-command-committed',scheduleRender,{signal});
  document.addEventListener('click',event=>{if(event.target.closest('[data-studio-tab="pages"],[data-studio-pane="pages"]'))setTimeout(()=>renderAll({force:true}),40)},{capture:true,signal});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)prewarmActiveThumbnail()},{signal});
}
function destroy(){
  closeMenu({restoreFocus:false});
  lifecycle.abort();
  thumbObserver?.disconnect();dockObserver?.disconnect();thumbObserver=dockObserver=null;
  clearTimeout(saveTimer);clearTimeout(dockRetryTimer);
  for(const timer of thumbTimers.values())clearTimeout(timer);thumbTimers.clear();
  for(const [node] of thumbJobs)cancelThumbJob(node);thumbJobs.clear();
  if(managerIdle){if('cancelIdleCallback'in window)cancelIdleCallback(managerIdle);else clearTimeout(managerIdle)}
  cache.clear();
  pointerGestureCleanup?.();pointerGestureCleanup=null;
  pointerReorder=null;dockPointerReorder=null;
}
function init(){
  installCss();hideLegacyNavigatorHeading();buildManager();installOverrides();installDockObserver();renderAll({force:true});
  window.EInvitePageExperience={
    version:VERSION,render:options=>renderAll(options||{}),addPage,duplicatePage,deletePage,reorderPage,setPageMode,applyEventPreset,hydrateThumbnail,closeMenu,destroy,
    get menuOpen(){return !!openMenuState},
    get cacheSize(){return cache.size},
    get activeMode(){const page=activePage();return page?pageMode(page):'hero'},
    get activePageId(){return activeId()},
    get pendingThumbnailJobs(){return thumbJobs.size+thumbTimers.size},
    get pointerReorderState(){const drag=pointerReorder||dockPointerReorder;return drag?{id:drag.id,target:drag.target,moved:drag.moved}:null},
    get renderSequence(){return renderSequence}
  };
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
