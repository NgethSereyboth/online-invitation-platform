(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')||!window.EInviteWorkflow||$('#workflowV5ContextMenu'))return;
const body=document.body,stage=$('#stage'),main=$('body.studio-experience>main'),viewport=$('#canvasViewport'),toolbar=$('.stage-wrap .toolbar');
const toast=(m,i='✓')=>window.uiToast?.(m,i);
const selected=()=>$$('.object.selected,.object.multi-selected',stage);
const selectedOne=()=>selected().length===1?selected()[0]:null;
const isText=o=>!!o&&(o.classList.contains('text-object')||o.classList.contains('decoration-object'));
const typeOf=o=>o?.dataset.objectType||(o?.classList.contains('image-object')?'image':o?.classList.contains('shape-object')?'shape':isText(o)?'text':'object');
const clickFirst=(...sels)=>{for(const s of sels){const el=$(s);if(el){el.click();return true}}return false};
let focusMode=false,previousPanelHidden=false;
const status=document.createElement('div');status.id='workflowV5Status';status.className='workflow-v5-status';status.innerHTML='<span class="page">Main hero</span><b>·</b><span class="selection">Nothing selected</span>';
$('.stage-wrap')?.append(status);
function selectionLabel(){
  const items=selected();if(!items.length)return'Nothing selected';if(items.length>1)return`${items.length} objects selected`;
  const o=items[0],type=typeOf(o),name=o.dataset.layerName||o.dataset.id||type;return`${type[0].toUpperCase()+type.slice(1)} · ${name}`
}
function pageLabel(){return $('#activeCanvasLabel')?.textContent?.trim()||'Main hero'}
function refreshStatus(){
  $('.page',status).textContent=pageLabel();$('.selection',status).textContent=selectionLabel();
  const o=selectedOne();status.classList.toggle('has-selection',!!o);status.title=o?'Click to edit the selected object':'Current canvas';
}
status.onclick=()=>{if(selected().length){document.querySelector('[data-inspector-tab="object"]')?.click();if(innerWidth<=1180)body.classList.add('inspector-open')}};
new MutationObserver(()=>requestAnimationFrame(refreshStatus)).observe(stage,{subtree:true,attributes:true,attributeFilter:['class']});
window.addEventListener('einvite:workflow-navigation',()=>setTimeout(refreshStatus,80));setTimeout(refreshStatus,120);
function setFocusMode(value){
  if(body.classList.contains('studio-content-mode'))value=false;
  if(value===focusMode)return;focusMode=value;
  if(value){previousPanelHidden=body.classList.contains('workflow-panel-hidden');body.classList.add('workflow-focus-canvas');body.classList.remove('inspector-open');}
  else{body.classList.remove('workflow-focus-canvas');if(!previousPanelHidden)body.classList.remove('workflow-panel-hidden')}
  $('#workflowV5Focus')?.classList.toggle('active',focusMode);$('#workflowV5Focus')?.setAttribute('aria-pressed',String(focusMode));
  setTimeout(()=>{try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{};try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}},90);
}
if(toolbar&&!$('#workflowV5Focus')){
  const b=document.createElement('button');b.id='workflowV5Focus';b.type='button';b.textContent='Focus';b.title='Focus canvas (Shift+F)';b.setAttribute('aria-pressed','false');
  const fit=$('#fitCanvas');fit?.insertAdjacentElement('afterend',b);
  b.onclick=()=>setFocusMode(!focusMode);
}
window.addEventListener('einvite:workflow-navigation',e=>{if(['event','blocks'].includes(e.detail?.to))setFocusMode(false)});
const menu=document.createElement('div');menu.id='workflowV5ContextMenu';menu.className='workflow-v5-context';document.body.append(menu);
function hideMenu(){menu.classList.remove('open')}
function selectObject(o){
  if(!o||o.classList.contains('selected')||o.classList.contains('multi-selected'))return;
  try{clearSelection?.();setSelection?.([o])}catch{try{o.dispatchEvent(new MouseEvent('pointerdown',{bubbles:true}))}catch{}}
}
function menuItems(){
  const items=selected(),o=selectedOne();
  if(!items.length)return[];
  if(items.length>1)return[['duplicate','Duplicate'],['group','Group'],['align','Align & distribute'],['front','Bring forward'],['back','Send backward'],['copy','Copy'],['delete','Delete']];
  const type=typeOf(o),base=[['duplicate','Duplicate'],['front','Bring forward'],['back','Send backward'],['copy','Copy']];
  if(type==='text')return[['edit-text','Edit text'],['ai','Rewrite with AI'],...base,['lock',o.dataset.locked==='true'?'Unlock':'Lock'],['delete','Delete']];
  if(type==='image')return[['edit-photo','Edit photo'],['remove-bg','Remove background'],['replace-image','Replace image'],['ai','Ask AI about this image'],...base,['lock',o.dataset.locked==='true'?'Unlock':'Lock'],['delete','Delete']];
  return[['color','Edit appearance'],...base,['lock',o.dataset.locked==='true'?'Unlock':'Lock'],['delete','Delete']];
}
function runAction(a){
  hideMenu();const o=selectedOne();
  if(a==='duplicate')clickFirst('#duplicate');
  if(a==='group')clickFirst('#groupObjects');
  if(a==='align')document.querySelector('[data-inspector-tab="object"]')?.click();
  if(a==='front')clickFirst('#bringForward');
  if(a==='back')clickFirst('#sendBackward');
  if(a==='copy')clickFirst('#copyObjects');
  if(a==='delete')clickFirst('#deleteBtn');
  if(a==='edit-text'){const c=o?.querySelector('.content');c?.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));setTimeout(()=>c?.focus(),30)}
  if(a==='edit-photo')clickFirst('[data-action="crop"]','#photoEditorOpen','.ei-photo-open');
  if(a==='remove-bg')clickFirst('#aiBgCut');
  if(a==='replace-image')clickFirst('#aiReplaceImage');
  if(a==='color')document.querySelector('[data-inspector-tab="object"]')?.click();
  if(a==='ai')window.EInviteAI?.open(isText(o)?'rewrite-formal':'design-review');
  if(a==='lock'&&o){o.dataset.locked=o.dataset.locked==='true'?'false':'true';try{save?.()}catch{};toast(o.dataset.locked==='true'?'Object locked':'Object unlocked',o.dataset.locked==='true'?'◈':'✓')}
}
function openMenu(x,y){
  const items=menuItems();if(!items.length)return;menu.innerHTML=items.map(([id,label])=>`${id==='delete'?'<hr>':''}<button type="button" data-v5-action="${id}"${id==='delete'?' class="danger"':''}>${label}</button>`).join('');
  menu.onclick=e=>{const b=e.target.closest('[data-v5-action]');if(b)runAction(b.dataset.v5Action)};
  menu.classList.add('open');const w=190,h=Math.min(430,menu.scrollHeight||320);menu.style.left=`${Math.max(8,Math.min(innerWidth-w-8,x))}px`;menu.style.top=`${Math.max(8,Math.min(innerHeight-h-8,y))}px`;
}
stage.addEventListener('contextmenu',e=>{const o=e.target.closest('.object');if(!o)return;e.preventDefault();e.stopPropagation();selectObject(o);setTimeout(()=>openMenu(e.clientX,e.clientY),0)},true);
document.addEventListener('pointerdown',e=>{if(!e.target.closest('#workflowV5ContextMenu'))hideMenu()},true);addEventListener('blur',hideMenu);

const dock=$('#workflowPageDock');
function revealActivePage(){const active=$('.workflow-page-chip.active',dock);active?.scrollIntoView?.({behavior:'smooth',block:'nearest',inline:'center'})}
if(dock){new MutationObserver(()=>requestAnimationFrame(revealActivePage)).observe(dock,{subtree:true,attributes:true,attributeFilter:['class']});dock.addEventListener('wheel',e=>{const track=$('.workflow-page-dock-track',dock);if(!track||Math.abs(e.deltaY)<=Math.abs(e.deltaX))return;e.preventDefault();track.scrollLeft+=e.deltaY},{passive:false})}
function extendQuickAdd(){
  const grid=$('#workflowV4QuickAddMenu .workflow-v4-add-grid');if(!grid||grid.querySelector('[data-quick-add="ai"]'))return;
  const b=document.createElement('button');b.type='button';b.dataset.quickAdd='ai';b.innerHTML='<span>✦</span><b>AI assistant</b><small>Write, plan & review</small>';b.onclick=e=>{e.stopPropagation();$('#workflowV4QuickAddMenu')?.classList.remove('open');window.EInviteAI?.open()};grid.append(b)
}
new MutationObserver(()=>requestAnimationFrame(extendQuickAdd)).observe(document.body,{childList:true,subtree:true});setTimeout(extendQuickAdd,150);
function showCoach(){
  if(localStorage.getItem('einvite-v5-coach-seen'))return;
  const tip=document.createElement('div');tip.className='workflow-v5-coach';tip.innerHTML='<strong>Faster editing</strong><span>Right-click any object for quick actions. Press <kbd>Enter</kbd> to edit selected text or <kbd>Ctrl/⌘ + .</kbd> for AI.</span><button type="button">Got it</button>';$('.stage-wrap')?.append(tip);
  const close=()=>{tip.remove();localStorage.setItem('einvite-v5-coach-seen','1')};tip.querySelector('button').onclick=close;setTimeout(()=>tip.classList.add('visible'),100);setTimeout(close,12000)
}
setTimeout(showCoach,900);
body.classList.add('workflow-ux-v5');
window.EInviteUXV5={focus:setFocusMode,contextMenu:openMenu};
})();
