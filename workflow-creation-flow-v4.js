(()=>{
'use strict';
const existing=window.EInviteWorkflowV4;if(existing?.refresh){existing.refresh();return}
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')||!window.EInviteWorkflow)return;
const body=document.body, stage=$('#stage'), viewport=$('#canvasViewport'), stageWrap=$('.stage-wrap'), host=$('.studio-pane-host'), toolbar=$('.studio-canvas-toolbar,.toolbar');
const compact=()=>innerWidth<=1180;
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
  const add=$('.workflow-page-add',dock);if(add&&!add.dataset.workflowBaseWired){add.dataset.workflowBaseWired='1';add.onclick=()=>{window.EInviteWorkflow.navigate('pages');if(compact())window.EInviteWorkflow.collapsePanel(false)}};
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
const ownedPageDock=ensurePageDock();
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
});
window.addEventListener('einvite:state-applied',()=>setTimeout(()=>{renderPageDock();updateCanvasWelcome()},120));
function clickFirst(...selectors){for(const selector of selectors){const el=$(selector);if(el){el.click();return true}}return false}
function closeTransientMenus(except){$$('.workflow-v4-popover.open').forEach(menu=>{if(menu!==except)menu.classList.remove('open')})}
function placePopover(menu,anchor,{align='start',placement='above',gap=10}={}){
  menu.classList.add('open');menu.style.visibility='hidden';menu.style.left='12px';menu.style.top='12px';
  const anchorRect=anchor.getBoundingClientRect(),menuRect=menu.getBoundingClientRect(),margin=12;
  const preferredLeft=align==='end'?anchorRect.right-menuRect.width:anchorRect.left;
  const left=Math.max(margin,Math.min(innerWidth-menuRect.width-margin,preferredLeft));
  const above=anchorRect.top-menuRect.height-gap,below=anchorRect.bottom+gap;
  const preferredTop=placement==='below'?below:above;
  const fallbackTop=placement==='below'?above:below;
  const fitsPreferred=preferredTop>=margin&&preferredTop+menuRect.height<=innerHeight-margin;
  const top=Math.max(margin,Math.min(innerHeight-menuRect.height-margin,fitsPreferred?preferredTop:fallbackTop));
  menu.style.left=`${left}px`;menu.style.top=`${top}px`;menu.style.visibility='';
}
document.addEventListener('pointerdown',e=>{if(!e.target.closest('.workflow-v4-popover,.workflow-v4-trigger,.workflow-page-chip'))closeTransientMenus()},true);
function pageLabelFromId(id){
  if(!id)return'Main hero';
  try{return state?.designPages?.find(p=>p.id===id)?.name||'Visual page'}catch{return'Visual page'}
}
function ensurePageMenu(){
  let menu=$('#workflowV4PageMenu');if(menu)return menu;
  menu=document.createElement('div');menu.id='workflowV4PageMenu';menu.className='workflow-v4-popover workflow-v4-page-menu';menu.innerHTML=`
    <button type="button" data-page-action="rename">Rename page</button>
    <button type="button" data-page-action="duplicate">Duplicate page</button>
    <button type="button" data-page-action="template">Save as template</button>
    <hr>
    <button type="button" class="danger" data-page-action="delete">Delete page</button>`;
  document.body.append(menu);
  menu.addEventListener('click',async e=>{
    const b=e.target.closest('[data-page-action]');if(!b)return;
    const id=menu.dataset.pageId;if(!id)return;
    menu.classList.remove('open');
    const action=b.dataset.pageAction;
    if(action==='rename'){
      const page=state?.designPages?.find(p=>p.id===id);if(!page)return;
      const value=await window.uiPrompt?.('Choose a page name:',page.name||'Visual Page',{title:'Rename page',confirmText:'Rename'});
      if(value==null||!value.trim())return;
      page.name=value.trim().slice(0,80);save?.();renderPageNavigator?.();renderDesignPagesManager?.();toast('Page renamed');
    }
    if(action==='duplicate'){duplicateDesignPage?.(id);toast('Page duplicated')}
    if(action==='template'){savePageTemplate?.(id)}
    if(action==='delete'){removeDesignPage?.(id)}
  });
  return menu;
}
function openPageMenu(button){
  const id=button.dataset.pageId;if(!id)return;
  const menu=ensurePageMenu();closeTransientMenus(menu);menu.dataset.pageId=id;
  placePopover(menu,button,{placement:'above'});
}
function enhancePageDock(){
  const dock=$('#workflowPageDock');if(!dock)return;
  $$('.workflow-page-chip',dock).forEach(button=>{
    if(button.dataset.v4Wired==='1')return;button.dataset.v4Wired='1';
    const id=button.dataset.pageId;
    if(id){
      button.draggable=true;
      button.addEventListener('dragstart',e=>{e.dataTransfer.setData('application/x-einvite-page',id);e.dataTransfer.effectAllowed='move';button.classList.add('dragging')});
      button.addEventListener('dragend',()=>button.classList.remove('dragging'));
      button.addEventListener('dragover',e=>{if(e.dataTransfer.types.includes('application/x-einvite-page')){e.preventDefault();button.classList.add('drag-over')}});
      button.addEventListener('dragleave',()=>button.classList.remove('drag-over'));
      button.addEventListener('drop',e=>{const moving=e.dataTransfer.getData('application/x-einvite-page');button.classList.remove('drag-over');if(moving&&moving!==id){e.preventDefault();reorderVisualPages?.(moving,id);toast('Pages reordered','↕')}});
      const more=document.createElement('span');more.className='workflow-page-more';more.textContent='•••';more.title='Page actions';more.onclick=e=>{e.preventDefault();e.stopPropagation();openPageMenu(button)};button.append(more);
      button.addEventListener('contextmenu',e=>{e.preventDefault();openPageMenu(button)});
    }
  });
  const add=$('.workflow-page-add',dock);if(add&&!add.dataset.v4Wired){add.dataset.v4Wired='1';add.onclick=e=>{e.preventDefault();e.stopPropagation();openPageAddMenu(add)}}
}
const dock=$('#workflowPageDock');
if(dock)new MutationObserver(()=>requestAnimationFrame(enhancePageDock)).observe(dock,{childList:true,subtree:true});
setTimeout(enhancePageDock,100);
function ensurePageAddMenu(){
  let menu=$('#workflowV4PageAdd');if(menu)return menu;
  menu=document.createElement('div');menu.id='workflowV4PageAdd';menu.className='workflow-v4-popover workflow-v4-page-add';
  document.body.append(menu);return menu;
}
function renderPageAddMenu(){
  const menu=ensurePageAddMenu();menu.innerHTML='<header><strong>Add a page</strong><button type="button" data-close>×</button></header><div class="workflow-v4-page-grid"></div>';
  const grid=$('.workflow-v4-page-grid',menu),seen=new Set();
  $$('[data-add-page]').forEach(source=>{
    const type=source.dataset.addPage;if(!type||seen.has(type))return;seen.add(type);
    const button=document.createElement('button');button.type='button';button.dataset.addPageType=type;
    button.innerHTML=`<span>${source.querySelector('span')?.textContent||'▣'}</span><strong>${source.querySelector('strong')?.textContent||type}</strong>`;
    button.onclick=()=>{menu.classList.remove('open');source.click();setTimeout(()=>{toast('Page added — continue designing','＋')},100)};grid.append(button);
  });
  $('[data-close]',menu).onclick=()=>menu.classList.remove('open');
  return menu;
}
function openPageAddMenu(anchor){
  const menu=renderPageAddMenu();closeTransientMenus(menu);placePopover(menu,anchor,{align:'end',placement:'above'});
}
function ensureQuickAdd(){
  if($('#workflowV4QuickAdd'))return;
  const trigger=document.createElement('button');trigger.id='workflowV4QuickAdd';trigger.type='button';trigger.className='workflow-v4-trigger workflow-v4-quick-add-trigger';trigger.innerHTML='<span>＋</span><b>Add</b>';trigger.title='Quick add';
  const menu=document.createElement('div');menu.id='workflowV4QuickAddMenu';menu.className='workflow-v4-popover workflow-v4-quick-add';menu.innerHTML=`
    <header><strong>Add to your invitation</strong><small>Quick insert</small></header>
    <div class="workflow-v4-add-grid">
      <button data-quick-add="heading"><span>T</span><b>Heading</b><small>Large title text</small></button>
      <button data-quick-add="text"><span>t</span><b>Text box</b><small>Start typing</small></button>
      <button data-quick-add="elements"><span>✦</span><b>Elements</b><small>Graphics & ornaments</small></button>
      <button data-quick-add="uploads"><span>⇧</span><b>Uploads</b><small>Photos, video & audio</small></button>
      <button data-quick-add="page"><span>▣</span><b>Page</b><small>Add another page</small></button>
      <button data-quick-add="blocks"><span>▦</span><b>Content block</b><small>Story, note & details</small></button>
    </div>`;
  stageWrap?.append(trigger);document.body.append(menu);
  trigger.onclick=e=>{e.stopPropagation();const open=!menu.classList.contains('open');closeTransientMenus(menu);if(!open)return;placePopover(menu,trigger,{placement:'above'})};
  menu.addEventListener('click',e=>{const b=e.target.closest('[data-quick-add]');if(!b)return;menu.classList.remove('open');const action=b.dataset.quickAdd;
    if(action==='heading'){if(!clickFirst('[data-text-preset="heading"]','.refine-text-preset.heading')){window.EInviteWorkflow.navigate('text')}}
    if(action==='text'){if(!clickFirst('.refine-add-text','#addText'))window.EInviteWorkflow.navigate('text')}
    if(action==='elements')window.EInviteWorkflow.navigate('elements',{source:'quick-add'});
    if(action==='uploads')window.EInviteWorkflow.navigate('media',{source:'quick-add'});
    if(action==='blocks')window.EInviteWorkflow.navigate('blocks',{source:'quick-add'});
    if(action==='page')openPageAddMenu(trigger);
  });
}
ensureQuickAdd();
let lastCanvas='';
function currentCanvas(){
  const active=$('.workflow-page-chip.active');return active?.dataset.canvasId||'';
}
function watchCanvas(){
  const next=currentCanvas();if(!next||next===lastCanvas)return;lastCanvas=next;
  setTimeout(()=>{try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{};try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}},60);
}
const pageDock=$('#workflowPageDock');if(pageDock)new MutationObserver(watchCanvas).observe(pageDock,{subtree:true,attributes:true,attributeFilter:['class']});
watchCanvas();
function refreshWorkflowV4(){
  ensurePageDock();renderPageDock();enhancePageDock();ensureQuickAdd();updateCanvasWelcome();watchCanvas();
}
body.classList.remove('workflow-creation-flow-v3');
body.classList.add('workflow-creation-flow-v4');
window.EInviteWorkflowV4={version:4,stage,refresh:refreshWorkflowV4,openQuickAdd:()=>$('#workflowV4QuickAdd')?.click(),openPageMenu,openPageAddMenu};
refreshWorkflowV4();
})();
