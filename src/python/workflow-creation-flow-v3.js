(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')||!window.EInviteWorkflow)return;
const body=document.body, stage=$('#stage'), viewport=$('#canvasViewport'), host=$('.studio-pane-host'), toolbar=$('.studio-canvas-toolbar,.toolbar');
const compact=()=>innerWidth<=980;
let lastSelection='';
function selected(){return $$('.object.selected,.object.multi-selected',stage)}
function selectedOne(){const s=selected();return s.length===1?s[0]:null}
function sig(){return selected().map(x=>x.dataset.id||'').sort().join('|')}
function typeOf(o){return o?.dataset.objectType||o?.dataset.type||(o?.classList.contains('image-object')?'image':o?.classList.contains('shape-object')?'shape':'text')}
function toast(message,icon='✓'){window.uiToast?.(message,icon)}
function fitSoon(){clearTimeout(fitSoon.t);fitSoon.t=setTimeout(()=>{try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{};try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};dispatchEvent(new CustomEvent('einvite:workspace-resized'))},120)}
function activateTool(name){
  const b=$(`[data-ei-tool="${name}"]`);
  if(b&&!b.classList.contains('active'))b.click();
}
function ensurePageDock(){
  let dock=$('#workflowPageDock');
  if(dock)return dock;
  dock=document.createElement('nav');dock.id='workflowPageDock';dock.className='workflow-page-dock';dock.setAttribute('aria-label','Invitation pages');
  dock.innerHTML='<div class="workflow-page-dock-track"></div><button type="button" class="workflow-page-add" title="Add a page">＋</button>';
  $('.stage-wrap')?.append(dock);
  $('.workflow-page-add',dock).onclick=()=>{window.EInviteWorkflow.navigate('pages');if(compact())window.EInviteWorkflow.collapsePanel(false)};
  return dock;
}
function renderPageDock(){
  const source=$('#pageNavigator');if(!source)return;
  const dock=ensurePageDock(),track=$('.workflow-page-dock-track',dock);track.innerHTML='';
  const cards=$$('.page-nav-card',source);
  cards.forEach((card,index)=>{
    const button=document.createElement('button');button.type='button';button.className=`workflow-page-chip${card.classList.contains('active')?' active':''}`;
    const thumb=card.querySelector('.page-thumb')?.cloneNode(true);if(thumb){thumb.removeAttribute('id');thumb.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));}
    const label=card.querySelector('strong')?.textContent?.trim()||`Page ${index+1}`;
    button.innerHTML=`<span class="workflow-page-number">${index+1}</span><span class="workflow-page-mini"></span><strong></strong>`;
    $('.workflow-page-mini',button).append(thumb||document.createElement('span'));$('strong',button).textContent=label;
    button.dataset.pageId=card.dataset.pageId||'';
    button.dataset.canvasId=card.dataset.pageId?(typeof designPageToken==='function'?designPageToken(card.dataset.pageId):`page:${card.dataset.pageId}`):'hero';
    button.onclick=()=>{try{typeof switchCanvas==='function'&&switchCanvas(button.dataset.canvasId)}catch{};setTimeout(()=>{renderPageDock()},60)};
    track.append(button);
  });
  const active=$('.workflow-page-chip.active',track);active?.scrollIntoView?.({block:'nearest',inline:'center'});
}
const pageSource=$('#pageNavigator');if(pageSource){new MutationObserver(()=>requestAnimationFrame(renderPageDock)).observe(pageSource,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});renderPageDock()}
function beginInlineText(o){
  if(!o||!['text','decoration'].includes(typeOf(o)))return;
  const content=o.querySelector('.content');if(!content)return;
  setTimeout(()=>{
    content.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true}));
    content.focus?.({preventScroll:true});
    try{const range=document.createRange(),sel=getSelection();range.selectNodeContents(content);sel.removeAllRanges();sel.addRange(range)}catch{}
    toast('Text added — start typing','T');
  },90);
}
function centerNewObject(o){
  if(!o||o.dataset.workflowPositioned==='1')return;
  const left=parseFloat(o.style.left),top=parseFloat(o.style.top);
  if(Number.isNaN(left)||Number.isNaN(top))return;
  if(left>=28&&left<=42&&top>=30&&top<=48){o.style.left='50%';o.style.top='50%';o.style.transform=`translate(-50%,-50%) rotate(${Number(o.dataset.rotation||0)}deg)`;o.dataset.workflowPositioned='1'}
}
function afterInsertion(source,before){
  setTimeout(()=>{
    const now=sig(),o=selectedOne();
    if(!now||now===before||!o)return;
    centerNewObject(o);
    const type=typeOf(o);
    body.dataset.workflowObjectType=type;
    if(type==='text'&&(source.matches('[data-text-preset],.refine-add-text,.refine-text-preset,.fp-text-combo')||source.closest('[data-studio-pane="text"]'))){beginInlineText(o)}
    else if(type==='image')toast('Photo added — use Edit photo for adjustments','▣');
    else toast('Element added to the canvas','✦');
    activateTool('select');
    if(compact())window.EInviteWorkflow.collapsePanel(true);
  },170);
}
const insertionSelector='[data-add-element],[data-text-preset],.refine-add-text,.refine-text-preset,.refine-font-combo,.fp-text-combo,.ei-pack-card,.final-element-card,.fp-visual-asset,.material-picker-card';
document.addEventListener('pointerdown',e=>{const source=e.target.closest(insertionSelector);if(source)source.dataset.workflowBefore=sig()},true);
document.addEventListener('click',e=>{const source=e.target.closest(insertionSelector);if(!source)return;afterInsertion(source,source.dataset.workflowBefore||'')},true);
function ensureQuickStrip(){
  let strip=$('#workflowQuickStrip');if(strip)return strip;
  strip=document.createElement('div');strip.id='workflowQuickStrip';strip.className='workflow-quick-strip';strip.hidden=true;
  $('.stage-wrap')?.append(strip);return strip;
}
function actionButton(label,action,primary=false){return `<button type="button" data-workflow-action="${action}"${primary?' class="primary"':''}>${label}</button>`}
function renderQuickStrip(){
  const strip=ensureQuickStrip(),items=selected(),o=items[0];
  if(!items.length||body.classList.contains('studio-content-mode')){strip.hidden=true;return}
  strip.hidden=false;
  if(items.length>1){strip.innerHTML=`<span>${items.length} selected</span>${actionButton('Group','group',true)}${actionButton('Align','align')}${actionButton('Tidy','tidy')}${actionButton('Duplicate','duplicate')}${actionButton('Delete','delete')}`;return wireQuickStrip(strip)}
  const type=typeOf(o),name=(o.dataset.layerName||o.querySelector('.content')?.textContent?.trim()||type).slice(0,24);
  if(type==='image')strip.innerHTML=`<span title="${name}">${name}</span>${actionButton('Edit photo','photo',true)}${actionButton('Remove BG','remove-bg')}${actionButton('Crop','crop')}${actionButton('Replace','replace')}${actionButton('Position','position')}${actionButton('Animate','animate')}`;
  else if(type==='shape')strip.innerHTML=`<span title="${name}">${name}</span>${actionButton('Color','color',true)}${actionButton('Position','position')}${actionButton('Animate','animate')}${actionButton('Duplicate','duplicate')}${actionButton('Delete','delete')}`;
  else strip.innerHTML=`<span title="${name}">${name}</span>${actionButton('Edit text','edit-text',true)}${actionButton('Font','font')}${actionButton('Effects','effects')}${actionButton('Animate','animate')}${actionButton('Position','position')}`;
  wireQuickStrip(strip);
}
function clickExisting(selector){$(selector)?.click()}
function wireQuickStrip(strip){
  $$('[data-workflow-action]',strip).forEach(b=>b.onclick=()=>{
    const a=b.dataset.workflowAction,o=selectedOne();
    if(a==='edit-text')return beginInlineText(o);
    if(a==='photo')return window.openEInvitePhotoEditor?.();
    if(a==='remove-bg')return clickExisting('#aiBgCut');
    if(a==='crop')return clickExisting('[data-action="crop"]')||clickExisting('#cropPreview');
    if(a==='replace')return clickExisting('#aiReplaceImage');
    if(a==='position')return clickExisting('[data-action="position"]')||document.querySelector('[data-inspector-tab="object"]')?.click();
    if(a==='animate')return clickExisting('[data-action="animate"]')||document.querySelector('[data-inspector-tab="object"]')?.click();
    if(a==='font')return clickExisting('.ei-font-launch');
    if(a==='effects')return clickExisting('[data-action="effects"]');
    if(a==='color'){const input=$('#fillColor');input?.click();return}
    if(a==='group')return clickExisting('#groupObjects');
    if(a==='align')return document.querySelector('[data-inspector-tab="object"]')?.click();
    if(a==='tidy'){const tidy=$('[data-float-action="tidy"]');return tidy?.click()}
    if(a==='duplicate')return clickExisting('#duplicate');
    if(a==='delete')return clickExisting('#deleteBtn');
  })
}
new MutationObserver(()=>requestAnimationFrame(()=>{const s=sig();if(s!==lastSelection){lastSelection=s;renderQuickStrip()}})).observe(stage,{subtree:true,attributes:true,attributeFilter:['class']});
stage.addEventListener('pointerup',()=>setTimeout(renderQuickStrip,0),true);renderQuickStrip();
function ensureCanvasWelcome(){
  let empty=$('#workflowCanvasWelcome');if(empty)return empty;
  empty=document.createElement('div');empty.id='workflowCanvasWelcome';empty.className='workflow-canvas-welcome';empty.hidden=true;
  empty.innerHTML='<strong>Start designing</strong><span>Add text, photos, elements, or pages from the left panel.</span><div><button data-open="elements">Add elements</button><button data-open="text">Add text</button><button data-open="media">Upload photo</button></div>';
  viewport?.append(empty);
  empty.addEventListener('click',e=>{const b=e.target.closest('[data-open]');if(b)window.EInviteWorkflow.navigate(b.dataset.open)});
  return empty;
}
function updateCanvasWelcome(){const w=ensureCanvasWelcome();const count=$$('.object',stage).length;w.hidden=count>0||body.classList.contains('studio-content-mode')}
new MutationObserver(updateCanvasWelcome).observe(stage,{childList:true,subtree:false});updateCanvasWelcome();
window.addEventListener('einvite:workflow-navigation',e=>{
  const to=e.detail?.to;
  if(to==='pages')setTimeout(renderPageDock,80);
  if(['elements','text','media'].includes(to)&&compact())body.classList.remove('inspector-open');
  if(to==='design')renderQuickStrip();
});
window.addEventListener('einvite:state-applied',()=>setTimeout(()=>{renderPageDock();renderQuickStrip();updateCanvasWelcome()},120));
body.classList.add('workflow-creation-flow-v3');
})();
