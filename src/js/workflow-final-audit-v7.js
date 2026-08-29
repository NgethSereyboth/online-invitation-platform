(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')||!window.EInviteWorkflow)return;
const body=document.body;
const stage=$('#stage');
const viewport=$('#canvasViewport');
const frame=$('#canvasFrame');
const host=$('.studio-pane-host');
const DESIGN_SECTIONS=new Set(['design','elements','text','media','pages']);
const CONTENT_SECTIONS=new Set(['event','blocks']);
const VERSION='2026-07-22-final-workflow-audit-v7';
let lastDesignSection='design';
let lastCanvasView=null;
let pendingChromeView=null;
let restoreTimer=0;
function toast(message,icon='✓'){window.uiToast?.(message,icon)}
function currentCanvasId(){
  try{return typeof activeCanvasId!=='undefined'?activeCanvasId:($('.workflow-page-chip.active')?.dataset.canvasId||'hero')}catch{return'hero'}
}
function captureView(){
  if(!viewport)return null;
  return {canvas:currentCanvasId(),left:viewport.scrollLeft,top:viewport.scrollTop,zoom:$('#zoomLevel')?.value||'1'};
}
function restoreView(view,{sameCanvasOnly=true}={}){
  if(!view||!viewport)return;
  if(sameCanvasOnly&&view.canvas!==currentCanvasId())return;
  clearTimeout(restoreTimer);
  restoreTimer=setTimeout(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
    try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{}
    viewport.scrollLeft=view.left;
    viewport.scrollTop=view.top;
    try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}
  })),45);
}
function closeTransientUi({keepFlow=false}={}){
  $$('.workflow-v4-popover.open').forEach(x=>x.classList.remove('open'));
  $$('.workflow-v6-popover.open').forEach(x=>x.classList.remove('open'));
  $('#workflowV5ContextMenu')?.classList.remove('open');
  if(!keepFlow)$('#workflowV6Flow')?.classList.remove('open');
}
function openFlow(){
  closeTransientUi({keepFlow:true});
  window.EInviteProEditorV6?.openFlow?.();
}
if(localStorage.getItem('einvite-final-audit-version')!==VERSION){
  body.classList.remove('inspector-open','workflow-panel-hidden','studio-left-collapsed','studio-right-collapsed');
  if(innerWidth>1180)body.classList.remove('mobile-pane-collapsed');
  localStorage.removeItem('einvite-left-collapsed');
  localStorage.removeItem('einvite-right-collapsed');
  localStorage.setItem('einvite-final-audit-version',VERSION);
}
function ensureTextWorkspace(){
  const rail=$('.studio-tool-rail'),panelHost=$('.studio-pane-host');if(!rail||!panelHost)return;
  let tab=$('[data-studio-tab="text"]',rail),pane=$('[data-studio-pane="text"]',panelHost);
  if(!tab){
    tab=document.createElement('button');tab.type='button';tab.className='studio-rail-button';tab.dataset.studioTab='text';tab.title='Text, fonts and typography';tab.innerHTML='<span class="studio-nav-icon flow-icon">T</span><span>Text</span>';
    const media=$('[data-studio-tab="media"]',rail);rail.insertBefore(tab,media||null);
  }
  if(!pane){
    pane=document.createElement('section');pane.className='studio-pane studio-text-pane workflow-v7-text-pane';pane.dataset.studioPane='text';
    pane.innerHTML=`
      <div class="studio-pane-heading"><div><small>Create</small><h1>Text</h1></div><div class="workflow-pane-actions"><button type="button" class="workflow-pane-back">‹ <span>Back</span></button><button type="button" class="workflow-pane-close" title="Hide panel">×</button></div></div>
      <label class="refine-text-search"><span>⌕</span><input type="search" placeholder="Search fonts and text styles" aria-label="Search fonts and text styles"></label>
      <button type="button" class="refine-add-text">T &nbsp; Add a text box</button>
      <button type="button" class="refine-magic-write">✦ Write with AI</button>
      <section class="refine-text-section"><div><h3>Default text styles</h3><small>Drag or click to add</small></div><div class="refine-text-presets">
        <button type="button" class="refine-text-preset heading" data-v7-text-preset="heading">Add a heading</button>
        <button type="button" class="refine-text-preset subheading" data-v7-text-preset="subheading">Add a subheading</button>
        <button type="button" class="refine-text-preset body" data-v7-text-preset="body">Add body text</button>
        <button type="button" class="refine-text-preset khmer" data-v7-text-preset="khmer">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section fp-text-fonts"><div><h3>Fonts</h3><small>Apply to selected text</small></div><div class="fp-text-category-tabs"></div><div class="fp-inline-font-list"></div><button type="button" class="refine-browse-fonts">Browse full font library</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Invitation-ready typography</small></div><div class="fp-text-combo-grid">
        <button type="button" class="fp-text-combo" data-v7-combo="gold"><span class="hero" style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="editorial"><span class="hero" style="font-family:Didot,Georgia,serif">THE<br><i>MOMENT</i></span><small>Editorial contrast</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="modern"><span class="hero" style="font-family:Arial,sans-serif;font-weight:800">TITLE<br>DETAILS</span><small>Modern clean</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="romance"><span class="hero" style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="khmer"><span class="hero" style="font-family:'Khmer OS Muol Light','Noto Serif Khmer',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="minimal"><span class="hero" style="font-family:Inter,Arial,sans-serif;letter-spacing:.12em">SAVE<br>THE DATE</span><small>Minimal spaced</small></button>
      </div></section>`;
    panelHost.append(pane);
  }
  pane.classList.add('workflow-v7-text-pane');
  let heading=$('.studio-pane-heading',pane);
  if(!heading){
    heading=document.createElement('div');heading.className='studio-pane-heading';heading.innerHTML='<div><small>Create</small><h1>Text</h1></div>';pane.prepend(heading);
  }
  let actions=$('.workflow-pane-actions',heading);
  if(!actions){actions=document.createElement('div');actions.className='workflow-pane-actions';heading.append(actions)}
  let back=$('.workflow-pane-back',actions);
  if(!back){back=document.createElement('button');back.type='button';back.className='workflow-pane-back';back.innerHTML='‹ <span>Back</span>';actions.append(back)}
  let close=$('.workflow-pane-close',actions);
  if(!close){close=document.createElement('button');close.type='button';close.className='workflow-pane-close';close.title='Hide panel';close.textContent='×';actions.append(close)}
  if(pane.dataset.v7TextWired)return;pane.dataset.v7TextWired='1';
  const selectedText=()=>$$('.object.selected,.object.multi-selected',stage).find(o=>['text','decoration'].includes(o.dataset.objectType||'text'))||null;
  function createText(config={}){
    $('#addText')?.click();const o=selectedText();if(!o)return null;const content=o.querySelector('.content');if(content&&config.text!=null)content.textContent=config.text;
    const mapping={font:'font',fontSize:'fontSize',color:'color',fontWeight:'fontWeight',fontStyle:'fontStyle',letterSpacing:'letterSpacing',lineHeight:'lineHeight',textAlign:'textAlign'};
    Object.entries(mapping).forEach(([key,dataKey])=>{if(config[key]!=null)o.dataset[dataKey]=String(config[key])});
    o.dataset.layerName=config.layerName||String(config.text||'Text').slice(0,50)||'Text';
    try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(o);typeof save==='function'&&save()}catch{}
    return o;
  }
  function applyFont(font){
    let o=selectedText();if(!o)o=createText({text:font.category==='Khmer'?'សិរីមង្គល':'Beautiful moments',font:font.stack,fontSize:30});
    if(!o)return;
    if(window.EInviteEditorState?.applyTextProperty){window.EInviteEditorState.applyTextProperty('font',font.stack)}
    else{o.dataset.font=font.stack;try{applyObjectVisualStyle?.(o);refreshSelectionUI?.();save?.()}catch{}}
    let recent=[];try{recent=JSON.parse(localStorage.getItem('einvite-font-recent-v1')||'[]')}catch{}recent=[font.stack,...recent.filter(x=>x!==font.stack)].slice(0,12);localStorage.setItem('einvite-font-recent-v1',JSON.stringify(recent));renderFonts();
  }
  const presets={
    heading:{text:'Your Heading',font:'serif-georgia',fontSize:48,fontWeight:'700',layerName:'Heading'},
    subheading:{text:'Add a subheading',font:'noto-sans',fontSize:28,fontWeight:'600',layerName:'Subheading'},
    body:{text:'Add a little bit of body text',font:'noto-sans',fontSize:18,lineHeight:1.55,layerName:'Body text'},
    khmer:{text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',font:"noto-serif-khmer",fontSize:36,color:'#9b6b13',layerName:'Khmer ceremonial title'}
  };
  const combos={
    gold:{text:'Golden Hour',font:'serif-georgia',fontSize:48,color:'#b48a20',letterSpacing:1},
    editorial:{text:'The Moment',font:'noto-serif',fontSize:48,color:'#2c2530',fontStyle:'italic'},
    modern:{text:'Your Celebration',font:'sans-arial',fontSize:44,color:'#202127',fontWeight:'700'},
    romance:{text:'Bride & Groom',font:'serif-georgia',fontSize:46,color:'#426b52',fontStyle:'italic'},
    khmer:{text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',font:"noto-serif-khmer",fontSize:38,color:'#9b6b13'},
    minimal:{text:'SAVE THE DATE',font:'noto-sans',fontSize:34,color:'#22242a',letterSpacing:5}
  };
  const fonts=[
    {name:'Noto Sans',stack:'noto-sans',category:'Modern'},
    {name:'Modern Sans',stack:'sans-arial',category:'Modern'},
    {name:'Friendly',stack:'sans-trebuchet',category:'Modern'},
    {name:'Noto Serif',stack:'noto-serif',category:'Serif'},
    {name:'Classic Serif',stack:'serif-georgia',category:'Serif'},
    {name:'Khmer Sans',stack:'noto-sans-khmer',category:'Khmer'},
    {name:'Khmer Serif',stack:'noto-serif-khmer',category:'Khmer'}
  ];
  let category='All',query='';const categories=['All','Recent','Khmer','Serif','Modern'];
  function recentFonts(){try{return JSON.parse(localStorage.getItem('einvite-font-recent-v1')||'[]')}catch{return[]}}
  function renderFonts(){
    const tabs=$('.fp-text-category-tabs',pane),list=$('.fp-inline-font-list',pane);if(!tabs||!list)return;
    tabs.innerHTML=categories.map(x=>`<button type="button" class="${x===category?'active':''}" data-v7-font-cat="${x}">${x}</button>`).join('');
    $$('[data-v7-font-cat]',tabs).forEach(b=>b.onclick=()=>{category=b.dataset.v7FontCat;renderFonts()});
    const recent=recentFonts();let data=fonts.filter(f=>{if(category==='Recent'&&!recent.includes(f.stack))return false;if(!['All','Recent'].includes(category)&&f.category!==category)return false;return!query||`${f.name} ${f.category}`.toLowerCase().includes(query)});if(category==='Recent')data.sort((a,b)=>recent.indexOf(a.stack)-recent.indexOf(b.stack));
    list.innerHTML='';data.forEach(f=>{const b=document.createElement('button');b.type='button';b.className='fp-inline-font';b.innerHTML=`<span class="sample"></span><small></small>`;$('.sample',b).textContent=f.category==='Khmer'?'សិរីមង្គល':'Beautiful moments';$('.sample',b).style.fontFamily=window.EInviteTypography?.stack?.(f.stack)||'serif';$('small',b).textContent=f.name;b.onclick=()=>applyFont(f);list.append(b)});if(!data.length)list.innerHTML='<small class="workflow-v7-font-empty">No fonts match this view.</small>';
  }
  back?.addEventListener('click',()=>window.EInviteWorkflow?.back?.());
  close?.addEventListener('click',()=>window.EInviteWorkflow?.collapsePanel?.(true));
  $('.refine-add-text',pane)?.addEventListener('click',()=>{const o=createText({text:'Start typing',font:'noto-sans',fontSize:24});const c=o?.querySelector('.content');setTimeout(()=>{c?.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));c?.focus?.()},30)});
  $('.refine-magic-write',pane)?.addEventListener('click',()=>window.EInviteAI?.open?.());
  $$('.refine-text-preset',pane).forEach(b=>b.addEventListener('click',()=>createText(presets[b.dataset.v7TextPreset]||{})));
  $$('.fp-text-combo',pane).forEach(b=>b.addEventListener('click',()=>createText(combos[b.dataset.v7Combo]||{})));
  $('.refine-browse-fonts',pane)?.addEventListener('click',()=>$('.ei-font-launch')?.click());
  const search=$('.refine-text-search input',pane);if(search)search.addEventListener('input',()=>{query=search.value.trim().toLowerCase();renderFonts();$$('.refine-text-preset,.fp-text-combo',pane).forEach(x=>x.hidden=!!query&&!x.textContent.toLowerCase().includes(query))});
  renderFonts();
}
ensureTextWorkspace();
$$('.flow-back-design').forEach(x=>x.remove());
function ensureFlowAffordances(){
  const design=$('[data-studio-pane="design"]');
  const projectActions=design?$('.flow-list-actions',design):null;
  if(projectActions&&!$('#workflowV7DesignFlow')){
    const b=document.createElement('button');
    b.type='button';b.id='workflowV7DesignFlow';b.className='workflow-v7-flow-entry';
    b.innerHTML='<span>↕</span><div><b>Invitation flow</b><small>Reorder pages and published sections</small></div><em>›</em>';
    b.onclick=openFlow;projectActions.append(b);
  }
  const dock=$('#workflowPageDock');
  const add=dock?$('.workflow-page-add',dock):null;
  if(dock&&add&&!$('#workflowV7DockFlow',dock)){
    const b=document.createElement('button');b.type='button';b.id='workflowV7DockFlow';b.className='workflow-v7-dock-flow';
    b.innerHTML='<span>↕</span><b>Flow</b>';b.title='Reorder invitation pages and sections';b.onclick=openFlow;
    add.insertAdjacentElement('beforebegin',b);
  }
}
ensureFlowAffordances();
function ensureMoreMenuActions(){
  const menu=$('.canvas-header-more-menu');if(!menu||$('#workflowV7MoreActions',menu))return;
  const add=(id,label,run)=>{const b=document.createElement('button');b.type='button';b.id=id;b.textContent=label;b.onclick=()=>{menu.hidden=true;$('.canvas-header-more-trigger')?.setAttribute('aria-expanded','false');run()};menu.append(b)};
  add('workflowV7MoreActions','Quick actions',()=>$('#studioCommandBtn')?.click());
  add('workflowV7MoreCheck','Design check',()=>$('#studioCheckBtn')?.click());
  add('workflowV7MoreAI','AI assistant',()=>window.EInviteAI?.open?.());
  add('workflowV7MorePreview','Preview invitation',()=>$('#previewBtn')?.click());
  add('workflowV7MoreUndo','Undo',()=>$('#undoBtn')?.click());
  add('workflowV7MoreRedo','Redo',()=>$('#redoBtn')?.click());
}
ensureMoreMenuActions();
function ensureBackToCanvas(){
  for(const id of CONTENT_SECTIONS){
    const pane=$(`[data-studio-pane="${id}"]`,host);const heading=$('.studio-pane-heading',pane);if(!heading||$('.workflow-v7-back-canvas',heading))continue;
    const actions=$('.workflow-pane-actions',heading)||heading;
    const b=document.createElement('button');b.type='button';b.className='workflow-v7-back-canvas';b.innerHTML='← <span>Back to canvas</span>';
    b.onclick=()=>window.EInviteWorkflow.navigate(DESIGN_SECTIONS.has(lastDesignSection)?lastDesignSection:'design',{source:'back-to-canvas'});
    actions.prepend(b);
  }
}
ensureBackToCanvas();
document.addEventListener('pointerdown',e=>{
  if(e.target.closest('.studio-tool-rail [data-studio-tab],#workflowPanelToggle,.workflow-pane-close,#flowPaneToggle,.workflow-pane-back,.workflow-v7-back-canvas,[data-flow-open]')){
    pendingChromeView=captureView();
  }
  if(e.target.closest('.workflow-page-chip')){
    lastCanvasView=captureView();
  }
},true);
window.addEventListener('einvite:workflow-navigation',e=>{
  const from=e.detail?.from,to=e.detail?.to;
  if(DESIGN_SECTIONS.has(from))lastDesignSection=from;
  if(CONTENT_SECTIONS.has(to))lastCanvasView=captureView();
  closeTransientUi();
  ensureBackToCanvas();ensureFlowAffordances();
  if(DESIGN_SECTIONS.has(to))restoreView(pendingChromeView||lastCanvasView,{sameCanvasOnly:true});
  pendingChromeView=null;
});
const chromeObserver=new MutationObserver(mutations=>{
  if(!pendingChromeView)return;
  if(!mutations.some(m=>m.attributeName==='class'))return;
  restoreView(pendingChromeView,{sameCanvasOnly:true});pendingChromeView=null;
});
chromeObserver.observe(body,{attributes:true,attributeFilter:['class']});
const dock=$('#workflowPageDock'),dockTrack=dock?$('.workflow-page-dock-track',dock):null;
if(dockTrack)new MutationObserver(()=>requestAnimationFrame(()=>window.EInviteProEditorV6?.renderFlow?.())).observe(dockTrack,{childList:true});
window.addEventListener('einvite:state-applied',()=>setTimeout(()=>window.EInviteProEditorV6?.renderFlow?.(),120));
function wireScrollable(root=document){
  $$('.studio-pane,.studio-inspector-pane,.studio-tool-rail,.workflow-v6-flow-list',root).forEach(el=>{
    if(el.dataset.v7ScrollWired)return;el.dataset.v7ScrollWired='1';
    el.addEventListener('wheel',e=>{
      if(Math.abs(e.deltaY)<=Math.abs(e.deltaX)||el.scrollHeight<=el.clientHeight+1)return;
      const atTop=el.scrollTop<=0&&e.deltaY<0,atBottom=el.scrollTop+el.clientHeight>=el.scrollHeight-1&&e.deltaY>0;
      if(!atTop&&!atBottom)e.stopPropagation();
    },{passive:true});
  });
}
wireScrollable();new MutationObserver(()=>requestAnimationFrame(()=>wireScrollable())).observe(document.body,{childList:true,subtree:true});
function keepActivePageVisible(){
  $('.workflow-page-chip.active')?.scrollIntoView?.({block:'nearest',inline:'nearest',behavior:'auto'});
}
const pageNav=$('#pageNavigator');
if(pageNav)new MutationObserver(()=>requestAnimationFrame(keepActivePageVisible)).observe(pageNav,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
function improveDiscoverability(){
  const design=$('[data-studio-pane="design"]');
  if(design&&!$('#workflowV7ProTip',design)){
    const tip=document.createElement('div');tip.id='workflowV7ProTip';tip.className='workflow-v7-pro-tip';
    tip.innerHTML='<span>⌘</span><div><strong>Professional canvas controls</strong><small>Drag assets onto the artboard, use Position for alignment, Layers for stacking, and Flow to reorder the invitation.</small></div>';
    $('.flow-project-card',design)?.after(tip);
  }
  const shortcuts=$('.ui-shortcut-grid');
  if(shortcuts&&!$('[data-v7-shortcuts]',shortcuts)){
    const rows=document.createElement('div');rows.dataset.v7Shortcuts='1';rows.style.display='contents';
    rows.innerHTML='<div class="ui-shortcut-row"><span>Position & arrange</span><kbd>P</kbd></div><div class="ui-shortcut-row"><span>Invitation flow</span><kbd>Q</kbd></div><div class="ui-shortcut-row"><span>Quick add</span><kbd>Ctrl / Cmd + /</kbd></div>';
    shortcuts.append(rows);
  }
}
improveDiscoverability();

body.classList.add('workflow-final-audit-v7');
window.EInviteFinalAuditV7={openFlow,captureView,restoreView,ensureFlowAffordances};
})();
