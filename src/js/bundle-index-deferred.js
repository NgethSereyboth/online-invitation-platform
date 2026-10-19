;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')) return;
const body=document.body, main=$('body.studio-experience>main'), rail=$('.studio-tool-rail'), host=$('.studio-pane-host'), stage=$('#stage');
if(!main||!rail||!host||!stage) return;
const FLOW_VERSION='2026-07-22-canva-flow-v2';
const compact=()=>innerWidth<=1180;
const paneScroll=new Map();
let activeId='';
let switching=false;
function iconSvg(kind){
  const icons={
    design:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5z"/><path d="M7 8h10M7 12h6M7 16h8"/></svg>',
    elements:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.2 5.2L19 10l-4.8 1.8L12 17l-2.2-5.2L5 10l4.8-1.8z"/><circle cx="18" cy="18" r="2"/></svg>',
    text:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M12 6v12M8.5 18h7"/></svg>',
    media:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="14" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="m6.5 17 4.5-4 3 2.5 2.5-2 2 3.5"/></svg>',
    pages:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
    event:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3v3M17 3v3M4 9h16"/><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 13h3M13 13h3M8 17h3"/></svg>',
    blocks:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/></svg>'
  };
  return icons[kind]||icons.design;
}
function ensureDesignHome(){
  let button=$('[data-studio-tab="design"]',rail);
  let pane=$('[data-studio-pane="design"]',host);
  if(!button){
    button=document.createElement('button');
    button.type='button';button.className='studio-rail-button flow-design-tab';button.dataset.studioTab='design';button.title='Design home';
    button.innerHTML=`<span class="studio-nav-icon flow-icon">${iconSvg('design')}</span><span>Design</span>`;
    rail.prepend(button);
  }
  if(!pane){
    pane=document.createElement('section');pane.className='studio-pane flow-design-pane';pane.dataset.studioPane='design';
    pane.innerHTML=`
      <div class="studio-pane-heading flow-pane-heading"><div><small>Create</small><h1>Design</h1></div></div>
      <section class="flow-project-card">
        <div class="flow-project-art" aria-hidden="true"><span>✦</span></div>
        <div><small>Current invitation</small><strong id="flowProjectName">Invitation</strong><span id="flowProjectMeta">Interactive invitation website</span></div>
      </section>
      <div class="flow-design-search"><span>⌕</span><input type="search" placeholder="Search design tools" aria-label="Search design tools"></div>
      <section class="flow-section"><div class="flow-section-head"><h3>Start creating</h3></div>
        <div class="flow-action-grid">
          <button type="button" data-flow-open="elements"><span class="flow-action-icon">${iconSvg('elements')}</span><b>Elements</b><small>Graphics & ornaments</small></button>
          <button type="button" data-flow-open="text"><span class="flow-action-icon">${iconSvg('text')}</span><b>Text</b><small>Fonts & combinations</small></button>
          <button type="button" data-flow-open="media"><span class="flow-action-icon">${iconSvg('media')}</span><b>Uploads</b><small>Photos, video & audio</small></button>
          <button type="button" data-flow-open="pages"><span class="flow-action-icon">${iconSvg('pages')}</span><b>Pages</b><small>Structure & layouts</small></button>
        </div>
      </section>
      <section class="flow-section"><div class="flow-section-head"><h3>Invitation styles</h3><button type="button" data-flow-inspector="theme">View all</button></div>
        <div class="flow-style-grid">
          <button type="button" data-flow-theme="rose"><i class="rose"></i><b>Royal Rose</b></button>
          <button type="button" data-flow-theme="gold"><i class="gold"></i><b>Khmer Gold</b></button>
          <button type="button" data-flow-theme="emerald"><i class="emerald"></i><b>Emerald</b></button>
          <button type="button" data-flow-theme="midnight"><i class="midnight"></i><b>Midnight</b></button>
        </div>
      </section>
      <section class="flow-section"><div class="flow-section-head"><h3>Project setup</h3></div>
        <div class="flow-list-actions">
          <button type="button" data-flow-open="event"><span>${iconSvg('event')}</span><div><b>Event details</b><small>Names, date, venue and RSVP</small></div><em>›</em></button>
          <button type="button" data-flow-open="blocks"><span>${iconSvg('blocks')}</span><div><b>Content blocks</b><small>Story, dress code and notes</small></div><em>›</em></button>
        </div>
      </section>`;
    host.append(pane);
  }
  return {button,pane};
}
function reorderRail(){
  const order=['design','elements','text','media','pages','event','blocks'];
  order.forEach(id=>{const b=$(`[data-studio-tab="${id}"]`,rail);if(b)rail.append(b)});
  $$('[data-studio-tab]',rail).forEach(b=>{
    const id=b.dataset.studioTab;
    const ico=$('.studio-nav-icon',b);
    if(ico&&['design','elements','text','media','pages','event','blocks'].includes(id)){
      ico.classList.add('flow-icon');ico.innerHTML=iconSvg(id);
    }
    const label=b.querySelector('span:last-child');
    if(label&&id==='media')label.textContent='Uploads';
  });
}
function activePane(){return $('.studio-pane.active',host)}
function selectedObjects(){return $$('.object.selected,.object.multi-selected',stage)}
function setInspector(id){
  const btn=$(`[data-inspector-tab="${id}"]`);if(btn){btn.click();return true}return false;
}
function fitCanvasSoon(){
  clearTimeout(fitCanvasSoon.t);
  fitCanvasSoon.t=setTimeout(()=>{
    try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{}
    try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}
    window.dispatchEvent(new CustomEvent('einvite:workspace-resized'));
  },90);
}
function applyMode(id){
  const content=['event','blocks'].includes(id);
  body.classList.toggle('studio-content-mode',content);
  body.classList.toggle('studio-design-mode',!content);
  body.dataset.studioSection=id;
  if(content){
    body.classList.remove('inspector-open','mobile-pane-collapsed');
  }else{
    fitCanvasSoon();
  }
}
function activate(id,{focus=true,collapseMobile=false}={}){
  if(switching)return;
  const target=$(`[data-studio-pane="${id}"]`,host), button=$(`[data-studio-tab="${id}"]`,rail);
  if(!target||!button)return;
  switching=true;
  const current=activePane();
  if(current&&current.dataset.studioPane) paneScroll.set(current.dataset.studioPane,current.scrollTop);
  $$('[data-studio-tab]',rail).forEach(b=>b.classList.toggle('active',b===button));
  $$('.studio-pane',host).forEach(p=>p.classList.toggle('active',p===target));
  localStorage.setItem('einvite-editor-left-tab',id);
  activeId=id;
  applyMode(id);
  requestAnimationFrame(()=>{
    target.scrollTop=paneScroll.get(id)||0;
    if(focus&&compact()&&!['event','blocks'].includes(id)) body.classList.remove('mobile-pane-collapsed');
    if(collapseMobile&&compact())body.classList.add('mobile-pane-collapsed');
    switching=false;
  });
}
function wireRail(){
  rail.addEventListener('click',e=>{
    const b=e.target.closest('[data-studio-tab]');if(!b)return;
    const id=b.dataset.studioTab;
    requestAnimationFrame(()=>activate(id,{focus:true}));
  },true);
}
function wireDesignHome(){
  const pane=$('[data-studio-pane="design"]',host);if(!pane)return;
  pane.addEventListener('click',e=>{
    const open=e.target.closest('[data-flow-open]');if(open){activate(open.dataset.flowOpen);return}
    const inspector=e.target.closest('[data-flow-inspector]');if(inspector){setInspector(inspector.dataset.flowInspector);return}
    const theme=e.target.closest('[data-flow-theme]');if(theme){
      const select=$('#designTheme');if(select){select.value=theme.dataset.flowTheme;select.dispatchEvent(new Event('change',{bubbles:true}));window.uiToast?.(`${theme.textContent.trim()} applied`,'✓')}
      return;
    }
  });
  const search=$('.flow-design-search input',pane);
  search?.addEventListener('input',()=>{
    const q=search.value.trim().toLowerCase();
    $$('[data-flow-open], [data-flow-theme], .flow-list-actions button',pane).forEach(el=>el.hidden=!!q&&!el.textContent.toLowerCase().includes(q));
  });
  const refresh=()=>{
    const name=($('#names')?.value||'').trim()||'Untitled invitation';
    const n=$('#flowProjectName');if(n)n.textContent=name;
    const type=window.state?.eventType||'Invitation';
    const meta=$('#flowProjectMeta');if(meta)meta.textContent=`${type} · interactive invitation website`;
  };
  $('#names')?.addEventListener('input',refresh);window.addEventListener('einvite:state-applied',refresh);refresh();
}
function addPaneBackButtons(){
  $$('.studio-pane',host).forEach(pane=>{
    if(pane.dataset.studioPane==='design'||pane.querySelector('.flow-back-design'))return;
    const heading=$('.studio-pane-heading',pane);if(!heading)return;
    const b=document.createElement('button');b.type='button';b.className='flow-back-design';b.innerHTML='<span>‹</span> Design';b.onclick=()=>activate('design');heading.append(b);
  });
}
function wireObjectFlow(){
}
function wireInsertFlow(){
}
function wireCanvasEmptyClick(){
  $('#canvasViewport')?.addEventListener('pointerdown',e=>{
    if(e.target.closest('.object,.studio-selection-toolbar,.toolbar'))return;
    if(compact())body.classList.remove('inspector-open');
  });
}
function wireEscFlow(){
}
function wireMobileDrawer(){
  let toggle=$('#flowPaneToggle');
  if(!toggle){
    toggle=document.createElement('button');toggle.id='flowPaneToggle';toggle.type='button';toggle.className='flow-pane-toggle';toggle.setAttribute('aria-label','Toggle creation panel');toggle.innerHTML='<span>‹</span>';
    main.append(toggle);
  }
  const sync=()=>{const closed=body.classList.contains('mobile-pane-collapsed');toggle.innerHTML=closed?'<span>›</span>':'<span>‹</span>';toggle.title=closed?'Open creation panel':'Hide creation panel';};
  toggle.onclick=()=>{body.classList.toggle('mobile-pane-collapsed');sync();fitCanvasSoon()};
  new MutationObserver(sync).observe(body,{attributes:true,attributeFilter:['class']});sync();
}
function wirePageFlow(){
}
function normalizeInitialFlow(){
  const requested=sessionStorage.getItem('einvite-open-editor-tab');
  if(requested)sessionStorage.removeItem('einvite-open-editor-tab');
  const saved=localStorage.getItem('einvite-editor-left-tab');
  const valid=id=>!!$(`[data-studio-pane="${id}"]`,host);
  const first=valid(requested)?requested:valid(saved)?saved:'design';
  const sessionActive=sessionStorage.getItem('einvite-editor-session-active')==='1';
  activate(sessionActive?first:'design',{focus:false});
  sessionStorage.setItem('einvite-editor-session-active','1');
}
function decorateTopbar(){
  const top=$('.studio-topbar');if(!top||$('#flowHomeButton'))return;
  const dash=top.querySelector('a[href="dashboard.html"]');
  if(dash){dash.id='flowHomeButton';dash.title='Back to projects'}
  const title=$('.studio-document-title',top);if(title){title.title='Current invitation'}
}
function safetyPass(){
  const p=activePane();
  if(!p||!p.isConnected){activate('design',{focus:false});return}
  applyMode(p.dataset.studioPane||'design');
  p.style.removeProperty('height');
  if(['event','blocks'].includes(p.dataset.studioPane)){
    body.classList.remove('inspector-open','mobile-pane-collapsed');
  }
}
ensureDesignHome();
reorderRail();
addPaneBackButtons();
wireDesignHome();
decorateTopbar();
normalizeInitialFlow();
/* Interaction routing is intentionally centralized in workflow-continuity.js.
   Keeping the older rail/selection/mobile listeners disabled avoids duplicate
   state changes, inspector jumps, and sidebar races. */
setTimeout(safetyPass,400);
localStorage.setItem('einvite-workflow-version',FLOW_VERSION);
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage'))return;
const body=document.body;
const main=$('body.studio-experience>main');
const rail=$('.studio-tool-rail');
const host=$('.studio-pane-host');
const stage=$('#stage');
const viewport=$('#canvasViewport');
const inspector=$('.right');
if(!main||!rail||!host||!stage)return;
const VALID=['design','elements','text','media','pages','event','blocks'];
const CONTENT=new Set(['event','blocks']);
const COMPACT=()=>innerWidth<=1180;
const scrollMemory=new Map();
const history=[];
let current=$('.studio-pane.active',host)?.dataset.studioPane||'design';
let lastDesign=CONTENT.has(current)?'design':current;
let selectedSignature='';
let lastAutoInspected='';
let navigating=false;
let lastUsed=[];
try{lastUsed=JSON.parse(localStorage.getItem('einvite-workflow-recent-tools-v1')||'[]')}catch{lastUsed=[]}
function validSection(id){return VALID.includes(id)&&!!$(`[data-studio-pane="${id}"]`,host)}
function activePane(){return $('.studio-pane.active',host)}
function pane(id){return $(`[data-studio-pane="${id}"]`,host)}
function tab(id){return $(`[data-studio-tab="${id}"]`,rail)}
function rememberScroll(){const p=activePane();if(p?.dataset.studioPane)scrollMemory.set(p.dataset.studioPane,p.scrollTop)}
function restoreScroll(id){requestAnimationFrame(()=>{const p=pane(id);if(!p)return;if(scrollMemory.has(id)){p.scrollTop=scrollMemory.get(id)||0;return}const selector=id==='event'?'#names':id==='blocks'?'#customBlockTitle,button,input,textarea,select':null,anchor=selector?$(selector,p):null;if(anchor){const pr=p.getBoundingClientRect(),ar=anchor.getBoundingClientRect(),head=$('.studio-pane-heading',p),clearance=head?Math.max(72,head.getBoundingClientRect().height+18):18;p.scrollTop=Math.max(0,p.scrollTop+ar.top-pr.top-clearance)}else p.scrollTop=0})}
function emit(name,detail={}){window.dispatchEvent(new CustomEvent(name,{detail}))}
function selected(){return $$('.object.selected,.object.multi-selected',stage)}
function selectionSig(){return selected().map(x=>x.dataset.id||'').sort().join('|')}
function setInspector(id){if(COMPACT()&&window.EInviteProfessionalEditor?.ownsPointerInteractions)return;const b=$(`[data-inspector-tab="${id}"]`);if(b&&!b.classList.contains('active'))b.click()}
function refreshCanvasSoon(delay=90){clearTimeout(refreshCanvasSoon.t);refreshCanvasSoon.t=setTimeout(()=>{try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{};try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};dispatchEvent(new CustomEvent('einvite:workspace-resized'))},delay)}
function clearPanelSearch(){const input=$('.studio-panel-search input',host);if(input&&input.value){input.value='';input.dispatchEvent(new Event('input',{bubbles:true}))}}
function markRecent(id){
  if(!VALID.includes(id)||id==='design')return;
  lastUsed=[id,...lastUsed.filter(x=>x!==id)].slice(0,4);
  localStorage.setItem('einvite-workflow-recent-tools-v1',JSON.stringify(lastUsed));
  renderRecent();
}
function applyMode(id,previousId=current){
  const content=CONTENT.has(id);
  const wasContent=CONTENT.has(previousId);
  body.classList.toggle('studio-content-mode',content);
  body.classList.toggle('studio-design-mode',!content);
  body.dataset.studioSection=id;
  if(content){
    body.classList.remove('inspector-open','mobile-pane-collapsed','workflow-panel-hidden');
  }else{
    lastDesign=id;
    if(wasContent)refreshCanvasSoon(120);
  }
}
function navigate(id,{push=true,focus=true,collapse=false,source='workflow'}={}){
  if(navigating||!validSection(id))return false;
  navigating=true;
  const previous=current;
  rememberScroll();
  if(push&&previous!==id){history.push(previous);if(history.length>16)history.shift()}
  current=id;
  $$('[data-studio-tab]',rail).forEach(b=>b.classList.toggle('active',b.dataset.studioTab===id));
  $$('.studio-pane',host).forEach(p=>p.classList.toggle('active',p.dataset.studioPane===id));
  localStorage.setItem('einvite-editor-left-tab',id);
  clearPanelSearch();
  applyMode(id,previous);
  restoreScroll(id);
  markRecent(id);
  if(COMPACT()&&!CONTENT.has(id)){
    body.classList.toggle('mobile-pane-collapsed',!!collapse);
    if(focus&&!collapse)body.classList.remove('mobile-pane-collapsed');
  }
  updateChrome();
  emit('einvite:workflow-navigation',{from:previous,to:id,source});
  setTimeout(()=>{navigating=false},0);
  return true;
}
function goBack(){
  while(history.length){const id=history.pop();if(validSection(id)&&id!==current){navigate(id,{push:false,source:'back'});return}}
  navigate('design',{push:false,source:'back'});
}
function panelIsCollapsed(){return body.classList.contains('mobile-pane-collapsed')||body.classList.contains('workflow-panel-hidden')}
function setPanelCollapsed(value){
  if(COMPACT())body.classList.toggle('mobile-pane-collapsed',value);
  else body.classList.toggle('workflow-panel-hidden',value);
  updateChrome();refreshCanvasSoon(80);
}
function ensureChrome(){
  if(!$('#workflowPanelToggle')){
    const b=document.createElement('button');b.id='workflowPanelToggle';b.type='button';b.className='workflow-panel-toggle';b.setAttribute('aria-label','Toggle creation panel');
    b.onclick=()=>setPanelCollapsed(!panelIsCollapsed());
    main.append(b);
  }
  if(!$('#workflowTrail')){
    const top=$('.studio-topbar');if(top){
      const trail=document.createElement('div');trail.id='workflowTrail';trail.className='workflow-trail';trail.innerHTML='<span>Design</span><b>›</b><strong>Design</strong>';
      const title=$('.studio-document-title',top);title?.after(trail);
    }
  }
  $$('.studio-pane',host).forEach(p=>{
    const heading=$('.studio-pane-heading',p);if(!heading||heading.querySelector('.workflow-pane-actions'))return;
    const actions=document.createElement('div');actions.className='workflow-pane-actions';
    if(p.dataset.studioPane!=='design'){
      const back=document.createElement('button');back.type='button';back.className='workflow-pane-back';back.innerHTML='‹ <span>Back</span>';back.onclick=goBack;actions.append(back);
    }
    const close=document.createElement('button');close.type='button';close.className='workflow-pane-close';close.textContent='×';close.title='Hide panel';close.onclick=()=>setPanelCollapsed(true);actions.append(close);
    heading.append(actions);
  });
}
function updateChrome(){
  const toggle=$('#workflowPanelToggle');if(toggle){const closed=panelIsCollapsed();toggle.innerHTML=closed?'›':'‹';toggle.title=closed?'Open creation panel':'Hide creation panel';toggle.setAttribute('aria-expanded',String(!closed))}
  const trail=$('#workflowTrail');if(trail){
    const labels={design:'Design',elements:'Elements',text:'Text',media:'Uploads',pages:'Pages',event:'Event details',blocks:'Content blocks'};
    trail.querySelector('strong').textContent=labels[current]||current;
    trail.hidden=current==='design';
  }
}
function renderRecent(){
  const design=pane('design');if(!design)return;
  let section=$('.workflow-recent',design);
  if(!section){
    section=document.createElement('section');section.className='flow-section workflow-recent';
    section.innerHTML='<div class="flow-section-head"><h3>Recent tools</h3></div><div class="workflow-recent-grid"></div>';
    const first=$('.flow-section',design);first?.after(section);
  }
  const grid=$('.workflow-recent-grid',section);
  const labels={elements:['✦','Elements','Graphics & ornaments'],text:['T','Text','Fonts & typography'],media:['⇧','Uploads','Photos, video & audio'],pages:['▣','Pages','Page structure'],event:['◫','Event','Event information'],blocks:['▦','Blocks','Content sections']};
  const items=lastUsed.filter(validSection);
  section.hidden=!items.length;
  grid.innerHTML='';
  items.forEach(id=>{const [icon,name,desc]=labels[id];const b=document.createElement('button');b.type='button';b.dataset.workflowRecent=id;b.innerHTML=`<span>${icon}</span><div><b>${name}</b><small>${desc}</small></div>`;b.onclick=()=>navigate(id,{source:'recent'});grid.append(b)});
}
function improveDesignSearch(){
  const design=pane('design');const input=$('.flow-design-search input',design);if(!input||$('#workflowSearchResults'))return;
  const results=document.createElement('div');results.id='workflowSearchResults';results.className='workflow-search-results';results.hidden=true;input.closest('.flow-design-search').after(results);
  const items=[
    ['elements','Elements','graphics ornaments shapes decorations'],['text','Text','fonts typography heading body'],['media','Uploads','photos images video audio music'],['pages','Pages','layouts structure page builder'],['event','Event details','date venue rsvp schedule guest'],['blocks','Content blocks','story dress code notes quote'],
  ];
  const render=()=>{
    const q=input.value.trim().toLowerCase();results.innerHTML='';results.hidden=!q;if(!q)return;
    const matched=items.filter(x=>`${x[1]} ${x[2]}`.toLowerCase().includes(q)).slice(0,6);
    matched.forEach(([id,name,terms],index)=>{const b=document.createElement('button');b.type='button';b.dataset.searchTarget=id;b.className=index===0?'active':'';b.innerHTML=`<strong>${name}</strong><small>${terms.split(' ').slice(0,4).join(' · ')}</small><span>›</span>`;b.onclick=()=>{input.value='';results.hidden=true;navigate(id,{source:'search'})};results.append(b)});
    if(!matched.length)results.innerHTML='<div class="workflow-search-empty">No matching design tools.</div>';
  };
  input.addEventListener('input',render,true);
  input.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=$('button',results);if(first){e.preventDefault();first.click()}}if(e.key==='Escape'){input.value='';render();input.blur()}});
}
function interceptRail(){
  document.addEventListener('click',e=>{
    const open=e.target.closest('[data-flow-open]');
    if(open&&validSection(open.dataset.flowOpen)){
      e.preventDefault();e.stopImmediatePropagation();
      navigate(open.dataset.flowOpen,{source:'design-home'});return;
    }
    const b=e.target.closest('.studio-tool-rail [data-studio-tab]');if(!b)return;
    const id=b.dataset.studioTab;if(!validSection(id))return;
    e.preventDefault();e.stopImmediatePropagation();
    if(current===id&&COMPACT()&&!CONTENT.has(id)){setPanelCollapsed(!panelIsCollapsed());return}
    navigate(id,{source:'rail'});
  },true);
}
function trackManualInspector(){
  $$('.studio-inspector-tab').forEach(b=>b.addEventListener('click',()=>{body.dataset.workflowInspectorManual='1';setTimeout(()=>delete body.dataset.workflowInspectorManual,500)},true));
}
function selectionFlow(){
  const update=()=>{
    const sig=selectionSig();
    if(sig===selectedSignature)return;
    const was=selectedSignature;selectedSignature=sig;
    if(sig){
      const professionalSelectionOwner=!!window.EInviteProfessionalEditor?.ownsPointerInteractions;
      if(!professionalSelectionOwner&&sig!==lastAutoInspected&&!body.dataset.workflowInspectorManual){setInspector('object');lastAutoInspected=sig}
      if(COMPACT()&&!professionalSelectionOwner)body.classList.add('inspector-open');
      emit('einvite:workflow-selection',{previous:was,current:sig});
    }else{
      if(COMPACT())body.classList.remove('inspector-open');
      lastAutoInspected='';
    }
    updateChrome();
  };
  new MutationObserver(()=>requestAnimationFrame(update)).observe(stage,{subtree:true,attributes:true,attributeFilter:['class']});
  stage.addEventListener('pointerup',()=>setTimeout(update,0),true);
  update();
}
function insertionFlow(){
  const selectors='[data-add-element],[data-add-page],[data-text-preset],.refine-add-text,.refine-text-preset,.refine-font-combo,.ei-pack-card,.final-element-card,.element-library button,.fp-inline-font,.fp-text-combo';
  document.addEventListener('click',e=>{
    const source=e.target.closest(selectors);if(!source)return;
    const before=selectionSig();
    setTimeout(()=>{
      const after=selectionSig();
      if(after&&after!==before){
        setInspector('object');
        lastAutoInspected=after;
        if(COMPACT())setPanelCollapsed(true);
        viewport?.focus?.({preventScroll:true});
        emit('einvite:workflow-inserted',{section:current,selection:after});
      }else if(source.matches('[data-add-page]')){
        refreshCanvasSoon(80);
      }
    },140);
  },true);
}
function pageFlow(){
  document.addEventListener('click',e=>{
    const hit=e.target.closest('#pageNavigator [data-page-id],#designPagesManager [data-edit-page],.workflow-page-chip');if(!hit)return;
    setTimeout(()=>refreshCanvasSoon(60),80);
  },true);
}
function keyboardFlow(){}
function guardLayout(){
  const sync=()=>{
    if(!validSection(current))current='design';
    const p=pane(current);if(p&&!p.classList.contains('active')){
      $$('.studio-pane',host).forEach(x=>x.classList.toggle('active',x===p));
      $$('[data-studio-tab]',rail).forEach(x=>x.classList.toggle('active',x.dataset.studioTab===current));
    }
    applyMode(current,current);updateChrome();
  };
  new MutationObserver(()=>requestAnimationFrame(sync)).observe(host,{subtree:true,attributes:true,attributeFilter:['class']});
  addEventListener('resize',()=>{sync();refreshCanvasSoon(50)});
}
function init(){
  $('#flowPaneToggle')?.remove();
  body.classList.remove('studio-left-collapsed','workflow-panel-hidden');
  ensureChrome();renderRecent();improveDesignSearch();trackManualInspector();interceptRail();selectionFlow();insertionFlow();pageFlow();keyboardFlow();guardLayout();
  const requested=sessionStorage.getItem('einvite-open-editor-tab');
  const saved=localStorage.getItem('einvite-editor-left-tab');
  const sessionActive=sessionStorage.getItem('einvite-editor-session-active')==='1';
  const start=validSection(requested)?requested:(sessionActive&&validSection(saved)?saved:(validSection(current)?current:'design'));
  if(requested)sessionStorage.removeItem('einvite-open-editor-tab');
  navigate(start,{push:false,focus:false,source:'init'});
  sessionStorage.setItem('einvite-editor-session-active','1');
  updateChrome();
  window.EInviteWorkflow={navigate,back:goBack,collapsePanel:setPanelCollapsed,get section(){return current},get history(){return [...history]}};
}
init();
})();;(()=>{
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
let lastRevealedChip=null;
// The observer below fires on every class change under the dock, and a dock
// re-render toggles `active` on many chips in a row. scrollIntoView forces a
// style recalculation + layout, so only a change of WHICH chip is active is
// worth one; an unchanged chip would also be scrolled against the user's wish.
function revealActivePage(){const active=$('.workflow-page-chip.active',dock);if(active===lastRevealedChip)return;lastRevealedChip=active;active?.scrollIntoView?.({behavior:'smooth',block:'nearest',inline:'center'})}
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
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')||$('#workflowV6Position'))return;
const body=document.body,stage=$('#stage'),stageWrap=$('.stage-wrap'),toolbar=$('.stage-wrap .toolbar'),viewport=$('#canvasViewport');
const toast=(m,i='✓')=>window.uiToast?.(m,i);
const chosen=()=>$$('.object.selected,.object.multi-selected',stage).filter(x=>x.isConnected);
const one=()=>chosen().length===1?chosen()[0]:null;
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const refresh=()=>{try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};try{typeof refreshSelectionUI==='function'&&refreshSelectionUI()}catch{};try{typeof renderLayers==='function'&&renderLayers()}catch{}};
const closePopovers=(except)=>$$('.workflow-v6-popover.open').forEach(x=>{if(x!==except)x.classList.remove('open')});
function stageRect(){return stage.getBoundingClientRect()}
function rect(o){return o.getBoundingClientRect()}
function moveBy(o,dx,dy){
  if(!o||o.dataset.locked==='true')return;
  const sr=stageRect(),r=rect(o),left=(r.left-sr.left+dx)/sr.width*100,top=(r.top-sr.top+dy)/sr.height*100;
  o.style.left=`${left.toFixed(3)}%`;o.style.top=`${top.toFixed(3)}%`;
}
function alignToCanvas(mode){
  const items=chosen().filter(o=>o.dataset.locked!=='true');if(!items.length)return toast('Select an unlocked object first.','↔');
  const sr=stageRect(),frames=items.map(o=>({o,r:rect(o)}));
  const minL=Math.min(...frames.map(x=>x.r.left)),maxR=Math.max(...frames.map(x=>x.r.right));
  const minT=Math.min(...frames.map(x=>x.r.top)),maxB=Math.max(...frames.map(x=>x.r.bottom));
  let dx=0,dy=0;
  if(mode==='left')dx=sr.left-minL;
  if(mode==='hcenter')dx=sr.left+sr.width/2-(minL+maxR)/2;
  if(mode==='right')dx=sr.right-maxR;
  if(mode==='top')dy=sr.top-minT;
  if(mode==='vcenter')dy=sr.top+sr.height/2-(minT+maxB)/2;
  if(mode==='bottom')dy=sr.bottom-maxB;
  items.forEach(o=>moveBy(o,dx,dy));saveNow();refresh();toast(mode==='hcenter'?'Centered horizontally':mode==='vcenter'?'Centered vertically':'Aligned to page','↔');
}
function alignSelectionV6(mode){
  const items=chosen().filter(o=>o.dataset.locked!=='true');if(items.length<2)return alignToCanvas(mode==='center'?'hcenter':mode==='middle'?'vcenter':mode);
  const frames=items.map(o=>({o,r:rect(o)})),minL=Math.min(...frames.map(x=>x.r.left)),maxR=Math.max(...frames.map(x=>x.r.right)),minT=Math.min(...frames.map(x=>x.r.top)),maxB=Math.max(...frames.map(x=>x.r.bottom));
  frames.forEach(({o,r})=>{let dx=0,dy=0;
    if(mode==='left')dx=minL-r.left;if(mode==='center')dx=(minL+maxR)/2-(r.left+r.width/2);if(mode==='right')dx=maxR-r.right;
    if(mode==='top')dy=minT-r.top;if(mode==='middle')dy=(minT+maxB)/2-(r.top+r.height/2);if(mode==='bottom')dy=maxB-r.bottom;
    moveBy(o,dx,dy);
  });saveNow();refresh();toast('Selection aligned','↔');
}
function distribute(axis){
  const items=chosen().filter(o=>o.dataset.locked!=='true');if(items.length<3)return toast('Select at least three unlocked objects to distribute.','↔');
  const ordered=items.map(o=>({o,r:rect(o)})).sort((a,b)=>axis==='horizontal'?a.r.left-b.r.left:a.r.top-b.r.top);
  const first=ordered[0].r,last=ordered[ordered.length-1].r;
  if(axis==='horizontal'){
    const totalWidth=ordered.reduce((sum,x)=>sum+x.r.width,0),space=((last.right-first.left)-totalWidth)/(ordered.length-1);
    let cursor=first.left;
    ordered.forEach((entry,index)=>{if(index===0||index===ordered.length-1){cursor=entry.r.right+space;return}moveBy(entry.o,cursor-entry.r.left,0);cursor+=entry.r.width+space});
  }else{
    const totalHeight=ordered.reduce((sum,x)=>sum+x.r.height,0),space=((last.bottom-first.top)-totalHeight)/(ordered.length-1);
    let cursor=first.top;
    ordered.forEach((entry,index)=>{if(index===0||index===ordered.length-1){cursor=entry.r.bottom+space;return}moveBy(entry.o,0,cursor-entry.r.top);cursor+=entry.r.height+space});
  }
  saveNow();refresh();toast(axis==='horizontal'?'Distributed horizontally':'Distributed vertically','↔');
}
function arrange(action){
  const items=chosen();if(!items.length)return toast('Select an object first.','▤');
  const all=$$('.object',stage);
  const unlocked=items.filter(o=>o.dataset.locked!=='true');
  if(!unlocked.length&&action!=='lock')return toast('The selected object is locked.','🔒');
  const ordered=all.slice().sort((a,b)=>Number(a.style.zIndex||0)-Number(b.style.zIndex||0));
  const movable=action==='lock'?items:unlocked;
  const selectedSet=new Set(movable);
  const selectedOrdered=ordered.filter(o=>selectedSet.has(o));
  const rest=ordered.filter(o=>!selectedSet.has(o));
  if(action==='front'||action==='back'){
    const next=action==='front'?[...rest,...selectedOrdered]:[...selectedOrdered,...rest];
    next.forEach((o,index)=>o.style.zIndex=String(index+1));
    saveNow();refresh();toast(action==='front'?'Moved to front':'Moved to back','▤');return;
  }
  if(action==='forward'||action==='backward'){
    const dir=action==='forward'?1:-1;
    const work=[...ordered];
    const scan=dir>0?[...work.keys()].reverse():[...work.keys()];
    scan.forEach(i=>{const o=work[i];if(!selectedSet.has(o))return;const j=i+dir;if(j<0||j>=work.length||selectedSet.has(work[j]))return;[work[i],work[j]]=[work[j],work[i]]});
    work.forEach((o,index)=>o.style.zIndex=String(index+1));
    saveNow();refresh();toast(action==='forward'?'Moved forward':'Moved backward','▤');return;
  }
  if(action==='duplicate'){$('#duplicate')?.click();return}
  if(action==='lock'){
    const shouldLock=items.some(o=>o.dataset.locked!=='true');
    items.forEach(o=>{o.dataset.locked=shouldLock?'true':'false';o.classList.toggle('locked',shouldLock)});
    saveNow();refresh();toast(shouldLock?'Selection locked':'Selection unlocked',shouldLock?'🔒':'✓');
  }
}
const position=document.createElement('section');position.id='workflowV6Position';position.className='workflow-v6-popover workflow-v6-position';position.innerHTML=`
  <header><div><small>Professional layout</small><strong>Position & arrange</strong></div><button type="button" data-v6-close>×</button></header>
  <div class="workflow-v6-position-status">Select an object to use positioning tools.</div>
  <section><h3>Align to page</h3><div class="workflow-v6-icon-grid six">
    <button data-page-align="left" title="Align left edge">⇤</button><button data-page-align="hcenter" title="Center horizontally">↔</button><button data-page-align="right" title="Align right edge">⇥</button>
    <button data-page-align="top" title="Align top edge">⇧</button><button data-page-align="vcenter" title="Center vertically">↕</button><button data-page-align="bottom" title="Align bottom edge">⇩</button>
  </div></section>
  <section class="workflow-v6-selection-align"><h3>Align selection</h3><div class="workflow-v6-icon-grid eight">
    <button data-selection-align="left">Left</button><button data-selection-align="center">Center</button><button data-selection-align="right">Right</button><button data-selection-align="top">Top</button><button data-selection-align="middle">Middle</button><button data-selection-align="bottom">Bottom</button><button data-distribute-v6="horizontal">Space H</button><button data-distribute-v6="vertical">Space V</button>
  </div></section>
  <section><h3>Layers</h3><div class="workflow-v6-arrange-grid"><button data-arrange="front">To front</button><button data-arrange="forward">Forward</button><button data-arrange="backward">Backward</button><button data-arrange="back">To back</button></div></section>
  <section><h3>Quick transform</h3><div class="workflow-v6-transform-grid"><button data-transform-v6="fill">Fill width</button><button data-transform-v6="fit">Fit inside</button><button data-transform-v6="reset">Reset rotation</button><button data-transform-v6="duplicate">Duplicate</button></div></section>`;
document.body.append(position);
function updatePositionStatus(){const items=chosen(),s=$('.workflow-v6-position-status',position);s.textContent=!items.length?'Select an object to use positioning tools.':items.length===1?`Editing ${items[0].dataset.layerName||items[0].dataset.objectType||'object'}`:`${items.length} objects selected`;position.classList.toggle('multi',items.length>1)}
function openPosition(anchor){closePopovers(position);updatePositionStatus();const r=anchor?.getBoundingClientRect?.()||{right:innerWidth-20,bottom:80,left:innerWidth-360};position.classList.add('open');requestAnimationFrame(()=>{position.style.left=`${Math.max(12,Math.min(innerWidth-position.offsetWidth-12,r.right-position.offsetWidth))}px`;position.style.top=`${Math.max(12,Math.min(innerHeight-position.offsetHeight-12,r.bottom+8))}px`})}
position.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.matches('[data-v6-close]'))return position.classList.remove('open');if(b.dataset.pageAlign)return alignToCanvas(b.dataset.pageAlign);if(b.dataset.selectionAlign)return alignSelectionV6(b.dataset.selectionAlign);if(b.dataset.distributeV6)return distribute(b.dataset.distributeV6);if(b.dataset.arrange)return arrange(b.dataset.arrange);if(b.dataset.transformV6){const o=one();if(!o&&b.dataset.transformV6!=='duplicate')return toast('Select one object first.');if(b.dataset.transformV6==='duplicate'){arrange('duplicate');return}const r=rect(o),sr=stageRect();if(b.dataset.transformV6==='fill'){o.style.left='5%';o.style.width='90%'}if(b.dataset.transformV6==='fit'){const w=r.width/sr.width*100,h=r.height/sr.height*100,scale=Math.min(82/Math.max(.001,w),82/Math.max(.001,h),1),nw=w*scale,nh=h*scale;o.style.width=`${nw}%`;o.style.height=`${nh}%`;o.style.left=`${(50-nw/2).toFixed(3)}%`;o.style.top=`${(50-nh/2).toFixed(3)}%`}if(b.dataset.transformV6==='reset'){o.dataset.rotation='0';o.style.transform='rotate(0deg)'}saveNow();refresh()}});
if(toolbar&&!$('#workflowV6PositionBtn')){const b=document.createElement('button');b.id='workflowV6PositionBtn';b.type='button';b.textContent='Position';b.title='Position and arrange';const anchor=$('#activeCanvasLabel')||toolbar.lastElementChild;anchor?.insertAdjacentElement('beforebegin',b);b.onclick=e=>{e.stopPropagation();position.classList.contains('open')?position.classList.remove('open'):openPosition(b)}}
document.addEventListener('click',e=>{const posAction=e.target.closest('[data-action="position"]');if(posAction){e.preventDefault();e.stopImmediatePropagation();openPosition(posAction)}},true);
document.addEventListener('pointerdown',e=>{if(!e.target.closest('.workflow-v6-popover,#workflowV6PositionBtn,[data-action="position"]'))closePopovers()},true);
new MutationObserver(()=>requestAnimationFrame(updatePositionStatus)).observe(stage,{subtree:true,attributes:true,attributeFilter:['class']});
function wireLayerDrag(){
  const list=$('#layersPanel .layer-list');if(!list)return;
  $$('.layer-row',list).forEach(row=>{if(row.dataset.v6LayerDrag)return;row.dataset.v6LayerDrag='1';row.draggable=true;
    row.addEventListener('pointerdown',e=>{if(e.target.closest('button'))row.draggable=false;else row.draggable=true});
    row.addEventListener('pointerup',()=>row.draggable=true);
    row.addEventListener('dragstart',e=>{
      if(e.target.closest('button')){e.preventDefault();return}
      const id=row.dataset.layerId,obj=$(`.object[data-id="${CSS.escape(id)}"]`,stage);
      if(obj&&!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected')){try{clearSelection?.();setSelection?.([obj])}catch{}}
      const panelOrder=$$('.layer-row',list).map(x=>x.dataset.layerId);
      const selectedIds=new Set(chosen().filter(o=>o.dataset.locked!=='true').map(o=>o.dataset.id));
      const ids=panelOrder.filter(x=>selectedIds.has(x));
      const payload=ids.length?ids:(obj?.dataset.locked==='true'?[]:[id]);
      if(!payload.length){e.preventDefault();toast('Unlock the layer before reordering it.','🔒');return}
      e.dataTransfer.setData('application/x-einvite-layer',JSON.stringify(payload));e.dataTransfer.effectAllowed='move';row.classList.add('v6-dragging')
    });
    row.addEventListener('dragend',()=>{$$('.layer-row',list).forEach(x=>x.classList.remove('v6-dragging','v6-drag-over','v6-drag-after'))});
    row.addEventListener('dragover',e=>{if(!e.dataTransfer.types.includes('application/x-einvite-layer'))return;e.preventDefault();const r=row.getBoundingClientRect(),after=e.clientY>r.top+r.height/2;row.classList.toggle('v6-drag-after',after);row.classList.toggle('v6-drag-over',!after)});
    row.addEventListener('dragleave',()=>row.classList.remove('v6-drag-over','v6-drag-after'));
    row.addEventListener('drop',e=>{
      const raw=e.dataTransfer.getData('application/x-einvite-layer');if(!raw)return;e.preventDefault();
      let moving=[];try{moving=JSON.parse(raw)}catch{moving=[raw]}moving=moving.filter(Boolean);
      const target=row.dataset.layerId;if(!target||moving.includes(target))return;
      let ordered=$$('.layer-row',list).map(x=>x.dataset.layerId);const movingSet=new Set(moving);const block=ordered.filter(id=>movingSet.has(id));ordered=ordered.filter(id=>!movingSet.has(id));
      let to=ordered.indexOf(target);if(to<0)return;const r=row.getBoundingClientRect(),after=e.clientY>r.top+r.height/2;if(after)to+=1;ordered.splice(to,0,...block);
      const high=ordered.length;ordered.forEach((id,index)=>{const o=$(`.object[data-id="${CSS.escape(id)}"]`,stage);if(o)o.style.zIndex=String(high-index)});
      saveNow();refresh();toast(block.length>1?`${block.length} layers reordered`:'Layer order updated','▤')
    });
  })
}
const layersPanel=$('#layersPanel');if(layersPanel)new MutationObserver(()=>requestAnimationFrame(wireLayerDrag)).observe(layersPanel,{childList:true,subtree:true});setTimeout(wireLayerDrag,150);
let dragSourceCounter=0;
const genericSources='[data-add-element],.final-element-card,.ei-pack-card,.fp-visual-asset,[data-text-preset],.refine-text-preset,.refine-add-text,.fp-text-combo,.refine-font-combo';
function wireInsertSources(){
  $$(genericSources).forEach(source=>{if(source.dataset.v6DragSource)return;source.dataset.v6DragSource=`v6-source-${++dragSourceCounter}`;source.draggable=true;source.addEventListener('dragstart',e=>{e.dataTransfer.setData('application/x-einvite-insert-source',source.dataset.v6DragSource);e.dataTransfer.effectAllowed='copy';body.classList.add('workflow-v6-dragging')});source.addEventListener('dragend',()=>body.classList.remove('workflow-v6-dragging'))})
}
const sourceHost=$('.studio-pane-host')||$('.left')||document.body;new MutationObserver(()=>requestAnimationFrame(wireInsertSources)).observe(sourceHost,{childList:true,subtree:true});setTimeout(wireInsertSources,150);
function canvasObjectIdsV6(){return new Set($$('.object',stage).map(o=>o.dataset.id).filter(Boolean))}
function repositionNew(beforeIds,x,y){const started=performance.now();const tick=()=>{const created=$$('.object',stage).filter(o=>o.dataset.id&&!beforeIds.has(o.dataset.id));if(created.length){const selectedCreated=created.filter(o=>o.classList.contains('selected')||o.classList.contains('multi-selected')),o=selectedCreated[selectedCreated.length-1]||created[created.length-1],r=rect(o),sr=stageRect(),w=r.width/sr.width*100,h=r.height/sr.height*100;o.style.left=`${Math.max(0,Math.min(100-w,x-w/2)).toFixed(2)}%`;o.style.top=`${Math.max(0,Math.min(100-h,y-h/2)).toFixed(2)}%`;try{clearSelection?.();setSelection?.([o])}catch{}saveNow();refresh();return}if(performance.now()-started<5000)requestAnimationFrame(tick)};requestAnimationFrame(tick)}
stage.addEventListener('dragover',e=>{const types=[...e.dataTransfer.types||[]];if(types.includes('application/x-einvite-insert-source')||types.includes('Files')){e.preventDefault();stage.classList.add('workflow-v6-drop-ready')}},true);
stage.addEventListener('dragleave',e=>{if(!stage.contains(e.relatedTarget))stage.classList.remove('workflow-v6-drop-ready')},true);
stage.addEventListener('drop',e=>{
  const files=[...(e.dataTransfer.files||[])].filter(f=>f.type?.startsWith('image/'));
  if(files.length){
    e.preventDefault();e.stopImmediatePropagation();stage.classList.remove('workflow-v6-drop-ready');
    const sr=stageRect(),x=(e.clientX-sr.left)/sr.width*100,y=(e.clientY-sr.top)/sr.height*100;
    const read=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file)});
    Promise.all(files.slice(0,12).map(async(file,index)=>({file,index,src:await read(file)}))).then(async entries=>{
      const created=[];
      for(const {file,index,src} of entries){
        const o=createObject(`drop-image-${Date.now()}-${index}-${Math.random().toString(36).slice(2,5)}`,'image'),img=o.querySelector('img');
        img.src=src;img.alt=file.name;o.dataset.alt=file.name;o.dataset.layerName=file.name.replace(/\.[^.]+$/,'').slice(0,80);
        const onHero=typeof activeCanvasId==='undefined'||activeCanvasId==='hero';o.dataset.showInHero=onHero?'true':'false';o.dataset.showInGallery=onHero?'true':'false';
        o.style.width='36%';o.style.height='260px';o.style.left=`${Math.max(0,Math.min(64,x-18+index*2))}%`;o.style.top=`${Math.max(0,Math.min(70,y-15+index*2))}%`;stage.append(o);created.push(o);
        if(onHero)try{state.galleryOrder=[...(state.galleryOrder||[]),o.dataset.id]}catch{}
        try{await window.assetStore?.put?.({id:`drop-${Date.now()}-${index}-${Math.random().toString(36).slice(2,6)}`,name:file.name,type:file.type,blob:file,createdAt:Date.now(),folder:'Canvas drops',tags:['canvas-drop']})}catch{}
      }
      try{clearSelection?.();setSelection?.(created)}catch{}
      saveNow();refresh();try{typeof renderAssets==='function'&&renderAssets()}catch{};toast(`${created.length} photo${created.length===1?'':'s'} added to the canvas`,'▧')
    }).catch(err=>{console.error(err);toast('One or more photos could not be added.','!')});return;
  }
  const sourceId=e.dataTransfer.getData('application/x-einvite-insert-source');if(!sourceId)return;
  const source=$(`[data-v6-drag-source="${CSS.escape(sourceId)}"]`);if(!source)return;e.preventDefault();e.stopImmediatePropagation();stage.classList.remove('workflow-v6-drop-ready');const sr=stageRect(),x=(e.clientX-sr.left)/sr.width*100,y=(e.clientY-sr.top)/sr.height*100,before=canvasObjectIdsV6();source.click();repositionNew(before,x,y);
},true);
const sectionMeta={gallery:['Gallery','▧'],video:['Featured video','▶'],countdown:['Countdown','◷'],schedule:['Schedule','☷'],custom:['Content blocks','▦'],venue:['Venue & maps','⌖'],contact:['Contact','☎'],wishes:['Guest wishes','♡'],rsvp:['RSVP','✓']};
function pageForToken(token){if(!String(token).startsWith('page:'))return null;const id=String(token).slice(5);return state?.designPages?.find(p=>p.id===id)||null}
function tokenMeta(token){const page=pageForToken(token);return page?[page.name||'Visual page','▣']:sectionMeta[token]||[String(token),'◇']}
const flow=document.createElement('aside');flow.id='workflowV6Flow';flow.className='workflow-v6-flow';flow.innerHTML=`<header><div><small>Published invitation</small><strong>Invitation flow</strong></div><button type="button" data-flow-close>×</button></header><p>Drag sections and pages to change the order guests see them.</p><div class="workflow-v6-flow-fixed"><span>1</span><b>Opening / main hero</b><small>Fixed opening</small></div><div class="workflow-v6-flow-list"></div>`;document.body.append(flow);
function currentOrder(){try{return [...(state.sectionOrder||[])]}catch{return[]}}
function writeOrder(order){try{
  const unique=[...new Set(order)].filter(Boolean);state.sectionOrder=unique;
  const pageIds=unique.filter(token=>String(token).startsWith('page:')).map(token=>String(token).slice(5));
  const byId=new Map((state.designPages||[]).map(page=>[page.id,page]));
  state.designPages=[...pageIds.map(id=>byId.get(id)).filter(Boolean),...(state.designPages||[]).filter(page=>!pageIds.includes(page.id))];
  const field=$('#sectionOrder');if(field)field.value=unique.join('\n');
  saveNow();typeof renderDesignPagesManager==='function'&&renderDesignPagesManager();typeof renderPageNavigator==='function'&&renderPageNavigator();renderFlow();toast('Invitation flow updated','↕')
}catch(err){console.error(err)}}
function renderFlow(){const list=$('.workflow-v6-flow-list',flow),order=currentOrder();list.innerHTML='';order.forEach((token,index)=>{const [label,icon]=tokenMeta(token),item=document.createElement('article');item.className='workflow-v6-flow-item';item.dataset.token=token;item.innerHTML=`<button class="workflow-v6-grip" draggable="true" title="Drag to reorder">⋮⋮</button><span class="workflow-v6-flow-number">${index+2}</span><span class="workflow-v6-flow-icon">${icon}</span><div><strong></strong><small>${String(token).startsWith('page:')?'Visual page':'Invitation section'}</small></div><div class="workflow-v6-flow-actions"><button data-move="up" title="Move earlier">↑</button><button data-move="down" title="Move later">↓</button></div>`;item.querySelector('strong').textContent=label;
    const grip=item.querySelector('.workflow-v6-grip');grip.addEventListener('dragstart',e=>{e.dataTransfer.setData('application/x-einvite-flow',token);e.dataTransfer.effectAllowed='move';item.classList.add('dragging')});grip.addEventListener('dragend',()=>$$('.workflow-v6-flow-item',list).forEach(x=>x.classList.remove('dragging','drag-over','drag-after')));item.addEventListener('dragover',e=>{if(!e.dataTransfer.types.includes('application/x-einvite-flow'))return;e.preventDefault();const r=item.getBoundingClientRect(),after=e.clientY>r.top+r.height/2;item.classList.toggle('drag-after',after);item.classList.toggle('drag-over',!after)});item.addEventListener('dragleave',()=>item.classList.remove('drag-over','drag-after'));item.addEventListener('drop',e=>{const moving=e.dataTransfer.getData('application/x-einvite-flow');if(!moving||moving===token)return;e.preventDefault();const next=currentOrder(),from=next.indexOf(moving);if(from<0)return;const [moved]=next.splice(from,1);let to=next.indexOf(token);if(to<0)return;const r=item.getBoundingClientRect();if(e.clientY>r.top+r.height/2)to+=1;next.splice(to,0,moved);writeOrder(next)});
    item.addEventListener('dblclick',()=>{if(String(token).startsWith('page:')){switchCanvas?.(token);flow.classList.remove('open')}else window.EInviteWorkflow?.navigate(token==='custom'?'blocks':'event',{source:'flow'})});
    item.querySelector('[data-move="up"]').onclick=e=>{e.stopPropagation();const next=currentOrder();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeOrder(next)};item.querySelector('[data-move="down"]').onclick=e=>{e.stopPropagation();const next=currentOrder();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeOrder(next)};list.append(item)});
  const dock=$('#workflowPageDock');if(dock)$$('.workflow-page-chip',dock).forEach(chip=>{const token=chip.dataset.canvasId,idx=order.indexOf(token);let badge=$('.workflow-v6-order-badge',chip);if(!badge){badge=document.createElement('i');badge.className='workflow-v6-order-badge';chip.append(badge)}badge.textContent=idx>=0?String(idx+2):'–';badge.title=idx>=0?`Invitation position ${idx+2}`:'Not in published flow'})
}
function toggleFlow(force){const open=force??!flow.classList.contains('open');flow.classList.toggle('open',open);if(open){renderFlow();body.classList.remove('inspector-open')}}
flow.querySelector('[data-flow-close]').onclick=()=>toggleFlow(false);
document.addEventListener('pointerdown',e=>{if(flow.classList.contains('open')&&!e.target.closest('#workflowV6Flow,#workflowV6FlowBtn'))toggleFlow(false)},true);
if(toolbar&&!$('#workflowV6FlowBtn')){const b=document.createElement('button');b.id='workflowV6FlowBtn';b.type='button';b.textContent='Flow';b.title='Reorder invitation pages and sections';const pos=$('#workflowV6PositionBtn');pos?.insertAdjacentElement('beforebegin',b);b.onclick=()=>toggleFlow()}
window.addEventListener('einvite:state-applied',()=>setTimeout(renderFlow,80));setTimeout(renderFlow,200);

body.classList.add('workflow-pro-editor-v6');
window.EInviteProEditorV6={openPosition:()=>openPosition($('#workflowV6PositionBtn')),openFlow:()=>toggleFlow(true),alignToCanvas,renderFlow};
})();;(()=>{
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
        <button type="button" class="refine-text-preset khmer" data-v7-text-preset="khmer" lang="km">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section fp-text-fonts"><div><h3>Fonts</h3><small>Apply to selected text</small></div><div class="fp-text-category-tabs"></div><div class="fp-inline-font-list"></div><button type="button" class="refine-browse-fonts">Browse full font library</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Invitation-ready typography</small></div><div class="fp-text-combo-grid">
        <button type="button" class="fp-text-combo" data-v7-combo="gold"><span class="hero" style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="editorial"><span class="hero" style="font-family:Didot,Georgia,serif">THE<br><i>MOMENT</i></span><small>Editorial contrast</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="modern"><span class="hero" style="font-family:Arial,sans-serif;font-weight:800">TITLE<br>DETAILS</span><small>Modern clean</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="romance"><span class="hero" style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button type="button" class="fp-text-combo" data-v7-combo="khmer"><span class="hero" lang="km" style="font-family:'Khmer OS Muol Light','Noto Serif Khmer',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
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
    list.innerHTML='';data.forEach(f=>{const b=document.createElement('button');b.type='button';b.className='fp-inline-font';b.innerHTML=`<span class="sample"></span><small></small>`;$('.sample',b).textContent=f.category==='Khmer'?'សិរីមង្គល':'Beautiful moments';$('.sample',b).lang=f.category==='Khmer'?'km':'en';$('.sample',b).style.fontFamily=window.EInviteTypography?.stack?.(f.stack)||'serif';$('small',b).textContent=f.name;b.onclick=()=>applyFont(f);list.append(b)});if(!data.length)list.innerHTML='<small class="workflow-v7-font-empty">No fonts match this view.</small>';
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
 const nodes=[...(root.matches?.('.studio-pane,.studio-inspector-pane,.studio-tool-rail,.workflow-v6-flow-list')?[root]:[]),...$$('.studio-pane,.studio-inspector-pane,.studio-tool-rail,.workflow-v6-flow-list',root)];
 nodes.forEach(el=>{
    if(el.dataset.v7ScrollWired)return;el.dataset.v7ScrollWired='1';
    el.addEventListener('wheel',e=>{
      if(Math.abs(e.deltaY)<=Math.abs(e.deltaX)||el.scrollHeight<=el.clientHeight+1)return;
      const atTop=el.scrollTop<=0&&e.deltaY<0,atBottom=el.scrollTop+el.clientHeight>=el.scrollHeight-1&&e.deltaY>0;
      if(!atTop&&!atBottom)e.stopPropagation();
    },{passive:true});
  });
}
wireScrollable();new MutationObserver(records=>{const added=[];for(const record of records)for(const node of record.addedNodes)if(node.nodeType===1)added.push(node);if(!added.length)return;requestAnimationFrame(()=>{if(window.EInviteProfessionalEditor?.activeInteraction)return;for(const node of added)if(node.isConnected)wireScrollable(node)})}).observe(document.body,{childList:true,subtree:true});
let lastVisibleChip=null;
function keepActivePageVisible(){
  // scrollIntoView forces a style recalculation + layout, and the observer below
  // fires on every class change anywhere under #pageNavigator — including the
  // class churn of a dock re-render. Only a change of WHICH chip is active needs
  // a scroll; re-scrolling an unchanged chip would also fight a user's own scroll.
  const active=$('.workflow-page-chip.active');
  if(active===lastVisibleChip)return;
  lastVisibleChip=active;
  active?.scrollIntoView?.({block:'nearest',inline:'nearest',behavior:'auto'});
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
})();;(()=>{
'use strict';
const q=s=>document.querySelector(s),qa=s=>[...document.querySelectorAll(s)];let menu;
function close(){if(menu)menu.hidden=true}
function ensureMenu(){if(menu)return menu;menu=document.createElement('div');menu.className='ei-context-menu';menu.hidden=true;menu.setAttribute('role','menu');menu.innerHTML=`<button data-a="copy">Copy objects <kbd>Ctrl/Cmd+C</kbd></button><button data-a="paste">Paste objects <kbd>Ctrl/Cmd+V</kbd></button><button data-a="duplicate">Duplicate</button><button data-a="copy-style">Copy style</button><button data-a="paste-style">Paste style</button><button data-a="group">Group selection</button><button data-a="tidy-h">Tidy horizontally</button><button data-a="tidy-v">Tidy vertically</button><button data-a="lock">Lock / unlock</button><button data-a="hide">Hide / show</button>`;document.body.append(menu);menu.addEventListener('click',e=>{const a=e.target.closest('[data-a]')?.dataset.a;if(!a)return;({copy:()=>EInviteCommands.copySelection(),paste:()=>EInviteCommands.pasteSelection(),duplicate:()=>EInviteCommands.duplicate(),'copy-style':()=>EInviteCommands.copyStyle(),'paste-style':()=>EInviteCommands.pasteStyle(),group:()=>EInviteCommands.groupNested(),'tidy-h':()=>EInviteCommands.tidy('horizontal'),'tidy-v':()=>EInviteCommands.tidy('vertical'),lock:()=>EInviteCommands.toggle('locked'),hide:()=>EInviteCommands.toggle('visible',true)}[a]?.());close()});return menu}
function contextMenu(){const stage=q('#stage');if(!stage)return;stage.addEventListener('contextmenu',e=>{if(!e.target.closest('.object')&&!EInviteCommands.selected().length)return;e.preventDefault();const m=ensureMenu();m.hidden=false;m.style.left=`${Math.min(innerWidth-230,e.clientX)}px`;m.style.top=`${Math.min(innerHeight-390,e.clientY)}px`;m.querySelector('button')?.focus()});document.addEventListener('pointerdown',e=>{if(menu&&!menu.contains(e.target))close()});}
function layerDnD(){const panel=q('#layersPanel');if(!panel)return;const enhance=()=>{const rows=qa('#layersPanel .layer-row');rows.forEach(row=>{if(row.dataset.v13Drag)return;row.dataset.v13Drag='1';row.draggable=true;row.addEventListener('dragstart',e=>{row.classList.add('ei-layer-dragging');e.dataTransfer.setData('text/plain',row.dataset.layerId)});row.addEventListener('dragend',()=>{row.classList.remove('ei-layer-dragging');qa('.ei-layer-drop').forEach(x=>x.classList.remove('ei-layer-drop'))});row.addEventListener('dragover',e=>{e.preventDefault();row.classList.add('ei-layer-drop')});row.addEventListener('dragleave',()=>row.classList.remove('ei-layer-drop'));row.addEventListener('drop',e=>{e.preventDefault();const source=e.dataTransfer.getData('text/plain'),target=row.dataset.layerId;if(!source||source===target)return;EInviteCommands.execute('Reorder layers',doc=>{const canvas=EInviteEditorBridge.getActiveCanvasId(),map=canvas==='hero'?doc.objects:(doc.designPages||[]).find(p=>`page:${p.id}`===canvas)?.objects;if(!map?.[source]||!map?.[target])return;const sorted=Object.entries(map).sort((a,b)=>Number(a[1].zIndex||0)-Number(b[1].zIndex||0)).map(([id])=>id);const si=sorted.indexOf(source),ti=sorted.indexOf(target);sorted.splice(si,1);sorted.splice(ti,0,source);sorted.forEach((id,index)=>map[id].zIndex=index+1)});row.classList.remove('ei-layer-drop')})})};new MutationObserver(enhance).observe(panel,{childList:true,subtree:true});enhance()}
function constraints(){const props=q('#properties');if(!props||q('#eiConstraintPanel'))return;const wrap=document.createElement('section');wrap.id='eiConstraintPanel';wrap.innerHTML='<h2>Responsive constraints <span class="ei-breakpoint-badge">V13</span></h2><div class="ei-constraint-panel"></div><label>Breakpoint override<select id="eiBreakpoint"><option value="mobile">Mobile</option><option value="tablet">Tablet</option><option value="desktop">Desktop</option></select></label><button type="button" id="eiSaveBreakpoint">Save current position for breakpoint</button>';const items=[['pinLeft','Pin left'],['pinRight','Pin right'],['pinTop','Pin top'],['pinBottom','Pin bottom'],['centerX','Center horizontally'],['centerY','Center vertically'],['stretchX','Stretch width'],['stretchY','Stretch height']];wrap.querySelector('.ei-constraint-panel').innerHTML=items.map(([k,l])=>`<label><input type="checkbox" data-constraint="${k}">${l}</label>`).join('');props.append(wrap);wrap.addEventListener('change',e=>{const key=e.target.dataset.constraint;if(key)EInviteCommands.setConstraints({[key]:e.target.checked})});q('#eiSaveBreakpoint').onclick=()=>{const id=EInviteCommands.selected()[0],obj=q(`.object[data-id="${CSS.escape(id||'')}"]`);if(!obj)return alert('Select an object first.');EInviteCommands.saveBreakpoint(q('#eiBreakpoint').value,{left:obj.style.left,top:obj.style.top,width:obj.style.width,height:obj.style.height})}}
function boot(){contextMenu();layerDnD();constraints()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();;(()=>{
'use strict';
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
const dialog=q('.ei-photo-dialog');if(!dialog)return;const controls=q('.ei-photo-controls',dialog);if(!controls||q('.ei-photo-v13',dialog))return;
const section=document.createElement('fieldset');section.className='ei-photo-v13';section.innerHTML=`<legend>Advanced non-destructive edit</legend><div class="ei-photo-before-after"><button type="button" data-v13-before>Hold to compare original</button><button type="button" data-v13-restore>Restore original</button></div><canvas class="ei-photo-histogram" width="480" height="90" aria-label="Image luminance histogram"></canvas><div class="ei-photo-v13-grid"></div><div class="ei-photo-adjustment-layers"><div class="ei-adjustment-head"><strong>Adjustment layers</strong><select data-adjustment-type><option value="brightness">Brightness</option><option value="contrast">Contrast</option><option value="saturation">Saturation</option><option value="vibrance">Vibrance</option><option value="temperature">Temperature</option><option value="hue">Hue</option><option value="grayscale">Grayscale</option><option value="sepia">Sepia</option><option value="blur">Blur</option><option value="gamma">Gamma</option></select><button type="button" data-add-adjustment>Add layer</button></div><div data-adjustment-list></div></div><div class="ei-photo-operation-list" aria-label="Editing operation summary"></div><div class="ei-photo-smart-object"><button type="button" data-v13-smart>Create smart source</button><button type="button" data-v13-smart-restore>Restore smart source</button><span data-v13-smart-status>Not a smart source yet</span></div><p class="ei-photo-advanced-note">The original uploaded source is retained. These controls store editing operations in the invitation document and generate previews without overwriting the source material.</p><div class="ei-photo-export-actions"><button type="button" data-v13-png>Export transparent PNG</button><button type="button" data-v13-webp>Export WebP</button></div>`;controls.append(section);
const defs=[['imageVibrance','Vibrance',-100,100,0],['imageTemperature','Temperature',-100,100,0],['imageGamma','Gamma',.25,3,1],['imageCurveShadows','Curve shadows',-100,100,0],['imageCurveHighlights','Curve highlights',-100,100,0],['imageSharpen','Sharpen',0,100,0],['imageLevelsBlack','Black point',0,80,0],['imageLevelsWhite','White point',20,100,100],['imagePerspectiveX','Perspective X',-60,60,0],['imagePerspectiveY','Perspective Y',-60,60,0],['imageWarpX','Warp X',-30,30,0],['imageWarpY','Warp Y',-30,30,0],['imageMaskFeather','Mask feather',0,50,0],['imageGradientMask','Gradient mask',0,100,0]];
const grid=q('.ei-photo-v13-grid',section);grid.innerHTML=defs.map(([key,label,min,max,def])=>`<label>${label}<input type="range" data-v13-key="${key}" min="${min}" max="${max}" value="${def}"><output>${def}</output></label>`).join('');
const selected=()=>qa('.object.selected,.object.multi-selected').find(x=>x.dataset.objectType==='image');
const operationSummary=item=>{const ops=[];for(const [key,label,,,def] of defs){const v=Number(item?.dataset[key]??def);if(v!==def)ops.push(`${label}: ${v}`)}for(const [key,label,def] of [['imageBrightness','Brightness',100],['imageContrast','Contrast',100],['imageSaturation','Saturation',100],['imageHue','Hue',0],['imageBlur','Blur',0]]){const v=Number(item?.dataset[key]??def);if(v!==def)ops.push(`${label}: ${v}`)}return ops};
const adjustmentRanges={brightness:[-80,120,10],contrast:[-80,120,10],saturation:[-100,150,15],vibrance:[-100,100,15],temperature:[-100,100,15],hue:[-180,180,15],grayscale:[0,100,100],sepia:[0,100,50],blur:[0,20,4],gamma:[.25,3,1.1]};
function adjustmentLayers(item){try{const value=JSON.parse(item?.dataset.imageAdjustmentLayers||'[]');return Array.isArray(value)?value:[]}catch{return[]}}
function setAdjustmentLayers(item,layers){item.dataset.imageAdjustmentLayers=JSON.stringify(layers);apply(item)}
function renderAdjustmentLayers(item){const root=q('[data-adjustment-list]',section),layers=adjustmentLayers(item);root.innerHTML=layers.length?layers.map((layer,index)=>{const range=adjustmentRanges[layer.type]||[-100,100,0];return`<div class="ei-adjustment-row" data-adjustment-index="${index}"><label class="ei-adjustment-enable"><input type="checkbox" ${layer.enabled===false?'':'checked'} aria-label="Enable ${escapeHtml(layer.type)} adjustment"></label><strong>${escapeHtml(layer.type)}</strong><input type="range" min="${range[0]}" max="${range[1]}" step="${layer.type==='gamma'?.05:1}" value="${Number(layer.value??range[2])}" aria-label="${escapeHtml(layer.type)} amount"><output>${Number(layer.value??range[2])}</output><button type="button" data-adjust-up aria-label="Move adjustment up">↑</button><button type="button" data-adjust-down aria-label="Move adjustment down">↓</button><button type="button" data-adjust-delete aria-label="Delete adjustment">×</button></div>`}).join(''):'<p class="ei-adjustment-empty">No adjustment layers. Add one to stack reversible color and effect changes.</p>'}
function smartObject(item){try{const value=JSON.parse(item?.dataset.imageSmartObject||'null');return value&&typeof value==='object'?value:null}catch{return null}}
function sync(){const item=selected();if(!item)return;defs.forEach(([key,,, ,def])=>{const input=q(`[data-v13-key="${key}"]`,section);input.value=String(item.dataset[key]??def);input.nextElementSibling.textContent=input.value});const ops=operationSummary(item);q('.ei-photo-operation-list',section).innerHTML=ops.length?ops.map(x=>`<span>${escapeHtml(x)}</span>`).join(''):'<span>No advanced operations.</span>';item.dataset.imageEditOperations=JSON.stringify(ops);const smart=smartObject(item),smartStatus=q('[data-v13-smart-status]',section),restoreSmart=q('[data-v13-smart-restore]',section);if(smartStatus)smartStatus.textContent=smart?.source?'Smart source preserved':'Not a smart source yet';if(restoreSmart)restoreSmart.disabled=!smart?.source;renderAdjustmentLayers(item);drawHistogram(item)}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function apply(item){if(!item)return;const img=item.querySelector('img');const state={...item.dataset,imageFlipX:item.dataset.imageFlipX==='true',imageFlipY:item.dataset.imageFlipY==='true'};if(img&&window.EInviteRenderer){img.style.filter=EInviteRenderer.imageFilterStyle(state);img.style.transform=EInviteRenderer.imageTransformStyle(state);const mask=EInviteRenderer.imageMaskStyle(state);if(mask){for(const decl of mask.split(';')){const [k,...rest]=decl.split(':');if(k&&rest.length)img.style.setProperty(k,rest.join(':'))}}else{img.style.removeProperty('mask-image');img.style.removeProperty('-webkit-mask-image')}}try{window.EInviteEditorBridge?.save?.()}catch{}sync()}
grid.addEventListener('input',e=>{const input=e.target.closest('[data-v13-key]'),item=selected();if(!input||!item)return;item.dataset[input.dataset.v13Key]=input.value;input.nextElementSibling.textContent=input.value;apply(item)});
q('[data-add-adjustment]',section).onclick=()=>{const item=selected();if(!item)return alert('Select an image first.');const type=q('[data-adjustment-type]',section).value,range=adjustmentRanges[type]||[-100,100,0],layers=adjustmentLayers(item);layers.push({id:crypto.randomUUID?.()||`adjust-${Date.now()}`,type,value:range[2],enabled:true});setAdjustmentLayers(item,layers)};
q('[data-adjustment-list]',section).addEventListener('input',e=>{const row=e.target.closest('[data-adjustment-index]'),item=selected();if(!row||!item)return;const index=Number(row.dataset.adjustmentIndex),layers=adjustmentLayers(item),layer=layers[index];if(!layer)return;if(e.target.type==='checkbox')layer.enabled=e.target.checked;else if(e.target.type==='range'){layer.value=Number(e.target.value);e.target.nextElementSibling.textContent=e.target.value}setAdjustmentLayers(item,layers)});
q('[data-adjustment-list]',section).addEventListener('click',e=>{const row=e.target.closest('[data-adjustment-index]'),item=selected();if(!row||!item)return;const index=Number(row.dataset.adjustmentIndex),layers=adjustmentLayers(item);if(e.target.closest('[data-adjust-delete]'))layers.splice(index,1);else if(e.target.closest('[data-adjust-up]')&&index>0)[layers[index-1],layers[index]]=[layers[index],layers[index-1]];else if(e.target.closest('[data-adjust-down]')&&index<layers.length-1)[layers[index+1],layers[index]]=[layers[index],layers[index+1]];else return;setAdjustmentLayers(item,layers)});
const stage=q('.ei-photo-stage',dialog);const before=q('[data-v13-before]',section);before.addEventListener('pointerdown',()=>stage.classList.add('ei-before-mode'));['pointerup','pointercancel','pointerleave'].forEach(name=>before.addEventListener(name,()=>stage.classList.remove('ei-before-mode')));
q('[data-v13-smart]',section).onclick=()=>{const item=selected(),img=item?.querySelector('img');if(!item||!img)return alert('Select an image first.');const current=smartObject(item),source=current?.source||item.dataset.originalSrc||img.currentSrc||img.src;if(!source)return alert('This image does not have a source to preserve.');item.dataset.originalSrc=item.dataset.originalSrc||source;item.dataset.imageSmartObject=JSON.stringify({enabled:true,source,createdAt:current?.createdAt||Date.now(),updatedAt:Date.now(),revision:Number(current?.revision||0)+1});try{window.EInviteEditorBridge?.save?.()}catch{}sync()};
q('[data-v13-smart-restore]',section).onclick=()=>{const item=selected(),img=item?.querySelector('img'),smart=smartObject(item);if(!item||!img||!smart?.source)return;img.src=smart.source;item.dataset.originalSrc=smart.source;item.dataset.imageGeneratedPreview='';try{window.EInviteEditorBridge?.save?.()}catch{}apply(item)};
q('[data-v13-restore]',section).onclick=()=>{const item=selected();if(!item)return;const img=item.querySelector('img');if(item.dataset.originalSrc&&img)img.src=item.dataset.originalSrc;const defaults={imageBrightness:100,imageContrast:100,imageSaturation:100,imageHue:0,imageSepia:0,imageGrayscale:0,imageBlur:0,imageVibrance:0,imageTemperature:0,imageGamma:1,imageCurveShadows:0,imageCurveHighlights:0,imageSharpen:0,imageLevelsBlack:0,imageLevelsWhite:100,imagePerspectiveX:0,imagePerspectiveY:0,imageWarpX:0,imageWarpY:0,imageMaskFeather:0,imageGradientMask:0,imageFlipX:false,imageFlipY:false};Object.entries(defaults).forEach(([k,v])=>item.dataset[k]=String(v));item.dataset.imageEditOperations='[]';item.dataset.imageRetouchOperations='[]';item.dataset.imageAdjustmentLayers='[]';item.dataset.imageGeneratedPreview='';apply(item)};
let worker;try{worker=new Worker('/photo-worker.js')}catch{}
function drawHistogram(item){const img=item?.querySelector('img'),canvas=q('.ei-photo-histogram',section),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);if(!img?.complete||!img.naturalWidth)return;const temp=document.createElement('canvas');temp.width=160;temp.height=100;const t=temp.getContext('2d',{willReadFrequently:true});try{t.drawImage(img,0,0,temp.width,temp.height);const data=t.getImageData(0,0,temp.width,temp.height).data;if(worker){worker.onmessage=e=>{if(e.data?.type!=='histogram')return;paintHistogram(ctx,e.data.l)};worker.postMessage({type:'histogram',pixels:data.buffer},[data.buffer])}else{const bins=new Array(256).fill(0);for(let i=0;i<data.length;i+=4)bins[Math.round(.2126*data[i]+.7152*data[i+1]+.0722*data[i+2])]++;paintHistogram(ctx,bins)}}catch{ctx.fillStyle='#888';ctx.font='13px sans-serif';ctx.fillText('Histogram unavailable for this image source',12,48)}}
function paintHistogram(ctx,bins){ctx.clearRect(0,0,480,90);const max=Math.max(1,...bins);ctx.beginPath();ctx.moveTo(0,90);bins.forEach((v,i)=>ctx.lineTo(i/255*480,90-v/max*82));ctx.lineTo(480,90);ctx.closePath();ctx.fillStyle='rgba(255,255,255,.78)';ctx.fill()}
async function processPixelsInWorker(imageData,state){if(!worker)return imageData;return await new Promise(resolve=>{const listener=e=>{if(e.data?.type!=='processed')return;worker.removeEventListener('message',listener);resolve(new ImageData(new Uint8ClampedArray(e.data.pixels),e.data.width,e.data.height))};worker.addEventListener('message',listener);worker.postMessage({type:'process',pixels:imageData.data.buffer,width:imageData.width,height:imageData.height,state:{gamma:Number(state.imageGamma||1),shadows:Number(state.imageCurveShadows||0),highlights:Number(state.imageCurveHighlights||0),sharpen:Number(state.imageSharpen||0),black:Number(state.imageLevelsBlack||0),white:Number(state.imageLevelsWhite||100)}},[imageData.data.buffer])})}
async function exportImage(format){const item=selected(),img=item?.querySelector('img');if(!img)return;const canvas=document.createElement('canvas'),w=Math.min(2400,img.naturalWidth||1200),h=Math.round(w/Math.max(.1,(img.naturalWidth||1200)/(img.naturalHeight||800)));canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d',{willReadFrequently:true});const state={...item.dataset,imageFlipX:item.dataset.imageFlipX==='true',imageFlipY:item.dataset.imageFlipY==='true'};ctx.filter=window.EInviteRenderer?.imageFilterStyle({...state,imageGamma:1,imageCurveShadows:0,imageCurveHighlights:0,imageSharpen:0})||'none';ctx.translate(w/2,h/2);ctx.scale(state.imageFlipX?-1:1,state.imageFlipY?-1:1);try{ctx.drawImage(img,-w/2,-h/2,w,h)}catch{return alert('This image cannot be exported because its remote host blocks canvas access. Upload it to Materials first.')}ctx.setTransform(1,0,0,1,0,0);if(worker){try{const processed=await processPixelsInWorker(ctx.getImageData(0,0,w,h),state);ctx.putImageData(processed,0,0)}catch{}}const blob=await new Promise(r=>canvas.toBlob(r,format,format==='image/webp'?.9:1));if(!blob)return;const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`edited-photo.${format==='image/webp'?'webp':'png'}`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
q('[data-v13-png]',section).onclick=()=>exportImage('image/png');q('[data-v13-webp]',section).onclick=()=>exportImage('image/webp');
dialog.addEventListener('toggle',()=>{if(dialog.open)setTimeout(sync,0)});dialog.addEventListener('click',e=>{if(e.target.closest('[data-preset],[data-tool],[data-revert]'))setTimeout(sync,0)});new MutationObserver(()=>{if(dialog.open)sync()}).observe(dialog,{attributes:true,attributeFilter:['open']});
})();;(()=>{
'use strict';
const q=(s,r=document)=>r.querySelector(s),bridge=()=>window.EInviteEditorBridge;
let selectedId='',sourcePoint=null,tool='magic',history=[],operations=[],drawing=false,lastPoint=null;
function selectedImage(){return [...document.querySelectorAll('.object.selected,.object.multi-selected')].find(x=>x.dataset.objectType==='image')||null}
function canvasMap(doc,id){const canvas=bridge()?.getActiveCanvasId?.()||'hero';if(canvas==='hero')return doc.objects||(doc.objects={});const page=(doc.designPages||[]).find(p=>`page:${p.id}`===canvas);return page?(page.objects||(page.objects={})):doc.objects}
function ensure(){if(q('#v13RetouchDialog'))return;const advanced=q('.ei-photo-v13');if(!advanced)return;const open=document.createElement('button');open.type='button';open.className='ei-retouch-open';open.textContent='Retouch: erase, clone & heal';advanced.querySelector('.ei-photo-export-actions')?.prepend(open);const dialog=document.createElement('dialog');dialog.id='v13RetouchDialog';dialog.className='ei-retouch-dialog';dialog.innerHTML=`<form method="dialog" class="ei-retouch-shell"><header><div><small>Non-destructive retouch</small><h2>Pixel retouch workspace</h2></div><button value="cancel" aria-label="Close retouch workspace">×</button></header><div class="ei-retouch-toolbar" role="toolbar" aria-label="Retouch tools"><button type="button" data-retouch-tool="magic" aria-pressed="true">Magic erase</button><button type="button" data-retouch-tool="erase">Erase brush</button><button type="button" data-retouch-tool="clone">Clone stamp</button><button type="button" data-retouch-tool="heal">Heal blend</button><label>Brush <input id="v13RetouchBrush" type="range" min="4" max="120" value="34"><output>34</output></label><label>Tolerance <input id="v13RetouchTolerance" type="range" min="5" max="120" value="42"><output>42</output></label><button type="button" id="v13RetouchUndo">Undo</button><button type="button" id="v13RetouchReset">Reset</button></div><p id="v13RetouchHint" class="ei-retouch-hint">Click a connected background area to erase it. The original source remains unchanged.</p><div class="ei-retouch-stage"><canvas id="v13RetouchCanvas" tabindex="0" aria-label="Retouch image canvas"></canvas></div><footer><span id="v13RetouchStatus" role="status"></span><button value="cancel">Cancel</button><button type="button" class="primary" id="v13RetouchApply">Apply as new preview</button></footer></form>`;document.body.append(dialog);bind(open,dialog)}
function bind(open,dialog){const canvas=q('#v13RetouchCanvas',dialog),brush=q('#v13RetouchBrush',dialog),tol=q('#v13RetouchTolerance',dialog);open.onclick=()=>openWorkspace(dialog);q('.ei-retouch-toolbar',dialog).addEventListener('click',e=>{const b=e.target.closest('[data-retouch-tool]');if(!b)return;tool=b.dataset.retouchTool;sourcePoint=null;dialog.querySelectorAll('[data-retouch-tool]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));updateHint(dialog)});for(const input of [brush,tol])input.oninput=()=>input.nextElementSibling.textContent=input.value;q('#v13RetouchUndo',dialog).onclick=()=>restoreHistory(canvas);q('#v13RetouchReset',dialog).onclick=()=>openWorkspace(dialog,true);q('#v13RetouchApply',dialog).onclick=()=>applyResult(dialog,canvas);canvas.addEventListener('pointerdown',e=>pointerDown(e,canvas,dialog));canvas.addEventListener('pointermove',e=>pointerMove(e,canvas));window.addEventListener('pointerup',()=>{drawing=false;lastPoint=null});dialog.addEventListener('close',()=>{sourcePoint=null;drawing=false})}
function updateHint(dialog){const h=q('#v13RetouchHint',dialog);h.textContent=tool==='magic'?'Click a connected area to erase colors within the selected tolerance.':tool==='erase'?'Drag to erase pixels with a soft circular brush.':tool==='clone'?'Alt/Option-click to choose a source point, then drag to clone pixels.': 'Alt/Option-click to choose a clean source point, then drag to blend it gently over imperfections.'}
async function openWorkspace(dialog,reset=false){const item=selectedImage();if(!item)return alert('Select an image first.');const img=item.querySelector('img');if(!img)return;selectedId=item.dataset.id;sourcePoint=null;tool='magic';operations=[];dialog.querySelectorAll('[data-retouch-tool]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.retouchTool==='magic')));updateHint(dialog);const canvas=q('#v13RetouchCanvas',dialog),ctx=canvas.getContext('2d',{willReadFrequently:true});try{if(img.decode)await img.decode()}catch{}const nw=img.naturalWidth||1200,nh=img.naturalHeight||800,scale=Math.min(1,1400/Math.max(nw,nh));canvas.width=Math.max(1,Math.round(nw*scale));canvas.height=Math.max(1,Math.round(nh*scale));try{ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);ctx.getImageData(0,0,1,1)}catch{return alert('This image source blocks local editing. Upload it to Materials first.')}history=[];pushHistory(canvas);q('#v13RetouchStatus',dialog).textContent=`${canvas.width} × ${canvas.height} working preview`;if(!dialog.open&&!reset)dialog.showModal()}
function point(e,canvas){const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)/r.width*canvas.width,y:(e.clientY-r.top)/r.height*canvas.height}}
function pushHistory(canvas){try{history.push(canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height));if(history.length>12)history.shift()}catch{}}
function restoreHistory(canvas){if(history.length<=1)return;history.pop();canvas.getContext('2d').putImageData(history.at(-1),0,0);operations.push({type:'undo',at:Date.now()})}
function colorDistance(a,b){const dr=a[0]-b[0],dg=a[1]-b[1],db=a[2]-b[2],da=(a[3]-b[3])*.25;return Math.sqrt(dr*dr+dg*dg+db*db+da*da)}
function magicErase(canvas,p,tolerance){const ctx=canvas.getContext('2d',{willReadFrequently:true}),image=ctx.getImageData(0,0,canvas.width,canvas.height),d=image.data,w=canvas.width,h=canvas.height,sx=Math.max(0,Math.min(w-1,Math.floor(p.x))),sy=Math.max(0,Math.min(h-1,Math.floor(p.y))),si=(sy*w+sx)*4,target=[d[si],d[si+1],d[si+2],d[si+3]],seen=new Uint8Array(w*h),stack=[sx,sy];let changed=0;while(stack.length){const y=stack.pop(),x=stack.pop(),pos=y*w+x;if(seen[pos])continue;seen[pos]=1;const i=pos*4;if(colorDistance([d[i],d[i+1],d[i+2],d[i+3]],target)>tolerance)continue;if(d[i+3]){d[i+3]=0;changed++}if(x>0)stack.push(x-1,y);if(x<w-1)stack.push(x+1,y);if(y>0)stack.push(x,y-1);if(y<h-1)stack.push(x,y+1)}ctx.putImageData(image,0,0);operations.push({type:'magic-erase',x:Math.round(p.x),y:Math.round(p.y),tolerance,changed})}
function brushErase(canvas,p,size){const ctx=canvas.getContext('2d');ctx.save();ctx.globalCompositeOperation='destination-out';const grad=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,size/2);grad.addColorStop(0,'rgba(0,0,0,1)');grad.addColorStop(.7,'rgba(0,0,0,.9)');grad.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=grad;ctx.beginPath();ctx.arc(p.x,p.y,size/2,0,Math.PI*2);ctx.fill();ctx.restore()}
function cloneBrush(canvas,p,size,heal=false){if(!sourcePoint)return;const ctx=canvas.getContext('2d',{willReadFrequently:true}),sx=sourcePoint.x+(p.x-(lastPoint?.anchorX??p.x)),sy=sourcePoint.y+(p.y-(lastPoint?.anchorY??p.y)),r=size/2,x=Math.round(p.x-r),y=Math.round(p.y-r),sourceX=Math.round(sx-r),sourceY=Math.round(sy-r);if(sourceX<0||sourceY<0||sourceX+size>canvas.width||sourceY+size>canvas.height)return;const patch=document.createElement('canvas');patch.width=size;patch.height=size;patch.getContext('2d').drawImage(canvas,sourceX,sourceY,size,size,0,0,size,size);ctx.save();ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.clip();ctx.globalAlpha=heal?.48:1;ctx.drawImage(patch,x,y);ctx.restore()}
function pointerDown(e,canvas,dialog){e.preventDefault();const p=point(e,canvas),size=Number(q('#v13RetouchBrush',dialog).value),tolerance=Number(q('#v13RetouchTolerance',dialog).value);if((tool==='clone'||tool==='heal')&&e.altKey){sourcePoint=p;q('#v13RetouchStatus',dialog).textContent='Clone/heal source selected. Drag over the target area.';return}pushHistory(canvas);if(tool==='magic'){magicErase(canvas,p,tolerance);return}drawing=true;lastPoint={...p,anchorX:p.x,anchorY:p.y};if(tool==='erase')brushErase(canvas,p,size);else cloneBrush(canvas,p,size,tool==='heal')}
function pointerMove(e,canvas){if(!drawing)return;const dialog=q('#v13RetouchDialog'),p=point(e,canvas),size=Number(q('#v13RetouchBrush',dialog).value);if(tool==='erase')brushErase(canvas,p,size);else cloneBrush(canvas,p,size,tool==='heal');lastPoint={...(lastPoint||{}),x:p.x,y:p.y}}
async function uploadBlob(blob){const inviteId=window.EInviteContext?.getInvitationId?.()||'';if(!inviteId)return'';const file=new File([blob],`retouched-${Date.now()}.png`,{type:'image/png',lastModified:Date.now()});if(window.EInviteUpload?.upload){const out=await window.EInviteUpload.upload(inviteId,file,{name:file.name});return out?.url||''}const response=await fetch(`/api/invitations/${encodeURIComponent(inviteId)}/assets/raw`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'image/png','X-File-Name':encodeURIComponent(file.name)},body:blob}),data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.error||'Retouched preview could not be uploaded');return data.url||''}
async function applyResult(dialog,canvas){const status=q('#v13RetouchStatus',dialog),button=q('#v13RetouchApply',dialog);button.disabled=true;status.textContent='Saving retouched preview…';try{const blob=await new Promise(r=>canvas.toBlob(r,'image/png',.96));if(!blob)throw Error('Unable to export the retouched preview');let url=await uploadBlob(blob);if(!url)url=canvas.toDataURL('image/png');const current=bridge().getState(),map=canvasMap(current),original=map[selectedId];if(!original)throw Error('The selected image is no longer available');bridge().transact('Apply non-destructive retouch',doc=>{const target=canvasMap(doc)[selectedId];if(!target)return;if(!target.originalSrc)target.originalSrc=target.src||'';target.src=url;target.imageGeneratedPreview=url;target.imageRetouchOperations=[...(Array.isArray(target.imageRetouchOperations)?target.imageRetouchOperations:[]),...operations,{type:'generated-preview',at:Date.now()}]});status.textContent='Retouched preview saved. The original remains restorable.';setTimeout(()=>dialog.close(),450)}catch(e){status.textContent=e.message}finally{button.disabled=false}}
function boot(){ensure()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();;(()=>{
'use strict';const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)],clone=v=>structuredClone?structuredClone(v):JSON.parse(JSON.stringify(v));let animations=[],activeFrame=null;
function ensure(){if(q('#eiTimeline'))return;const launch=document.createElement('button');launch.id='eiTimelineLaunch';launch.className='ei-timeline-launch';launch.type='button';launch.textContent='Timeline';launch.setAttribute('aria-expanded','false');document.body.append(launch);const panel=document.createElement('section');panel.id='eiTimeline';panel.className='ei-timeline';panel.hidden=true;panel.setAttribute('aria-label','Animation timeline');panel.innerHTML=`<div class="ei-timeline-head"><h2>Animation timeline</h2><span class="ei-timeline-marker">V13</span><button data-tl-play>▶ Play</button><button data-tl-stop>■ Stop</button><button data-tl-copy>Copy motion</button><button data-tl-paste>Paste motion</button><button data-tl-close aria-label="Close timeline">×</button></div><div class="ei-timeline-transport"><label>Duration <input data-tl-duration type="number" min="1000" max="120000" step="500"></label><label>Play from <input data-tl-range-start type="number" min="0" step="100"></label><label>Play to <input data-tl-range-end type="number" min="100" step="100"></label><input data-tl-scrub type="range" min="0" max="10000" step="10" value="0" aria-label="Timeline scrubber"><output data-tl-time>0.00s</output><button data-tl-add>Add keyframe</button><button data-tl-stagger>Stagger selected</button><button data-tl-marker>Add section marker</button><label>Audio offset ms <input data-tl-audio-offset type="number" min="0" max="30000" step="100" value="0"></label><button data-tl-health>Performance check</button><button data-tl-export>Export motion JSON</button></div><div class="ei-timeline-body"><div class="ei-timeline-presets"><button data-preset="entrance">Entrance</button><button data-preset="emphasis">Emphasis</button><button data-preset="float">Continuous float</button><button data-preset="exit">Exit</button></div><div data-tl-tracks></div><div class="ei-timeline-fields" data-tl-fields hidden><label>Time ms<input data-kf="time" type="number" min="0" step="50"></label><label>X px<input data-kf="x" type="number" step="1"></label><label>Y px<input data-kf="y" type="number" step="1"></label><label>Scale<input data-kf="scale" type="number" min="0.05" max="8" step="0.05"></label><label>Rotation<input data-kf="rotation" type="number" step="1"></label><label>Opacity<input data-kf="opacity" type="number" min="0" max="1" step="0.05"></label><label>Easing<select data-kf="easing"><option>ease</option><option>linear</option><option>ease-in</option><option>ease-out</option><option>ease-in-out</option><option value="cubic-bezier(.16,1,.3,1)">Elegant</option><option value="cubic-bezier(.34,1.56,.64,1)">Overshoot</option><option value="custom">Custom cubic-bezier…</option></select></label><label>Custom easing<input data-kf="customEasing" placeholder="cubic-bezier(.2,.8,.2,1)"></label><button data-kf-delete class="danger">Delete keyframe</button></div></div>`;document.body.append(panel);bind(launch,panel)}
function state(){const d=EInviteEditorBridge.getState();d.timeline=d.timeline||{duration:10000,fps:30,tracks:{},markers:[],playRange:{start:0,end:10000},reducedMotionFallback:'final-state'};d.timeline.tracks=d.timeline.tracks||{};d.timeline.playRange=d.timeline.playRange||{start:0,end:d.timeline.duration||10000};return d}
function selected(){return EInviteCommands.selected()}
function trackFor(doc,id){return doc.timeline.tracks[id]||(doc.timeline.tracks[id]={kind:'custom',delay:0,duration:Math.min(1600,doc.timeline.duration||10000),iterations:1,direction:'normal',fill:'both',keyframes:[]})}
function captureFrame(time){const id=selected()[0],el=id&&q(`.object[data-id="${CSS.escape(id)}"]`);if(!id||!el)return null;return{time:Number(time||0),x:0,y:0,scale:1,rotation:Number(el.dataset.rotation||0),opacity:Number(el.dataset.opacity||1),easing:'ease'}}
function update(label,fn){EInviteCommands.execute(label,doc=>{doc.timeline=doc.timeline||{duration:10000,tracks:{},markers:[]};doc.timeline.tracks=doc.timeline.tracks||{};fn(doc)});render()}
function render(){const doc=state(),duration=Math.max(1000,Number(doc.timeline.duration||10000)),tracks=q('[data-tl-tracks]'),scrub=q('[data-tl-scrub]'),range=doc.timeline.playRange||{start:0,end:duration};q('[data-tl-duration]').value=duration;q('[data-tl-range-start]').value=Math.max(0,Math.min(duration-100,Number(range.start||0)));q('[data-tl-range-end]').value=Math.max(Number(q('[data-tl-range-start]').value)+100,Math.min(duration,Number(range.end||duration)));q('[data-tl-range-start]').max=duration-100;q('[data-tl-range-end]').max=duration;q('[data-tl-audio-offset]').value=Number(doc.timeline.audioOffset||0);scrub.max=duration;tracks.innerHTML='';const ids=selected().length?selected():Object.keys(doc.timeline.tracks);if(!ids.length)tracks.innerHTML='<p class="hint">Select an object, then add a keyframe or choose a motion preset.</p>';ids.forEach(id=>{const tr=doc.timeline.tracks[id]||{keyframes:[]},row=document.createElement('div');row.className='ei-track';const label=q(`.object[data-id="${CSS.escape(id)}"]`)?.dataset.layerName||id;row.innerHTML=`<div class="ei-track-name" title="${escapeHtml(label)}">${escapeHtml(label)}</div><div class="ei-track-line"></div>`;const line=q('.ei-track-line',row);(tr.keyframes||[]).forEach((f,index)=>{const b=document.createElement('button');b.type='button';b.className='ei-keyframe';b.style.left=`${Math.max(0,Math.min(100,Number(f.time||0)/duration*100))}%`;b.title=`${Number(f.time||0)} ms`;b.onclick=()=>selectFrame(id,index);line.append(b)});tracks.append(row)});highlight()}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function selectFrame(id,index){activeFrame={id,index};const doc=state(),f=doc.timeline.tracks[id]?.keyframes?.[index];if(!f)return;const fields=q('[data-tl-fields]');fields.hidden=false;qa('[data-kf]',fields).forEach(input=>{if(input.dataset.kf==='customEasing')input.value=/^cubic-bezier\(/.test(f.easing||'')?f.easing:'';else input.value=f[input.dataset.kf]??''});q('[data-tl-scrub]').value=f.time||0;q('[data-tl-time]').textContent=`${(Number(f.time||0)/1000).toFixed(2)}s`;highlight()}
function highlight(){qa('.ei-keyframe').forEach(x=>x.classList.remove('active'));if(!activeFrame)return;const rows=qa('.ei-track');const doc=state(),ids=selected().length?selected():Object.keys(doc.timeline.tracks),row=rows[ids.indexOf(activeFrame.id)];row?.querySelectorAll('.ei-keyframe')?.[activeFrame.index]?.classList.add('active')}
function preset(name){const ids=selected();if(!ids.length)return;const map={entrance:[{time:0,x:0,y:35,scale:.96,rotation:0,opacity:0,easing:'cubic-bezier(.16,1,.3,1)'},{time:900,x:0,y:0,scale:1,rotation:0,opacity:1,easing:'ease-out'}],emphasis:[{time:0,x:0,y:0,scale:1,rotation:0,opacity:1,easing:'ease'},{time:450,x:0,y:0,scale:1.08,rotation:0,opacity:1,easing:'ease-out'},{time:900,x:0,y:0,scale:1,rotation:0,opacity:1,easing:'ease-in'}],float:[{time:0,x:0,y:0,scale:1,rotation:0,opacity:1,easing:'ease-in-out'},{time:1500,x:0,y:-10,scale:1.02,rotation:0,opacity:1,easing:'ease-in-out'},{time:3000,x:0,y:0,scale:1,rotation:0,opacity:1,easing:'ease-in-out'}],exit:[{time:0,x:0,y:0,scale:1,rotation:0,opacity:1,easing:'ease-in'},{time:800,x:0,y:-25,scale:.98,rotation:0,opacity:0,easing:'ease-in'}]}[name];update(`Apply ${name} motion`,doc=>ids.forEach((id,i)=>{const t=trackFor(doc,id);t.kind=name;t.keyframes=clone(map);t.duration=map.at(-1).time;t.delay=i*90;t.iterations=name==='float'?'infinite':1}))}
function play(){stop();const doc=state(),range=doc.timeline.playRange||{start:0,end:doc.timeline.duration};animations=window.EInviteTimelineRuntime?.play(q('#stage'),doc,{start:Number(range.start||0),end:Number(range.end||doc.timeline.duration)})||[]}
function stop(){animations.forEach(a=>{try{if(a.__einviteRangeTimer)clearTimeout(a.__einviteRangeTimer);a.cancel()}catch{}});animations=[]}
function bind(launch,panel){launch.onclick=()=>{panel.hidden=!panel.hidden;launch.setAttribute('aria-expanded',String(!panel.hidden));document.body.classList.toggle('ei-timeline-open',!panel.hidden);if(!panel.hidden)render()};q('[data-tl-close]',panel).onclick=()=>launch.click();q('[data-tl-play]',panel).onclick=play;q('[data-tl-stop]',panel).onclick=stop;q('[data-tl-duration]',panel).onchange=e=>update('Change timeline duration',doc=>{doc.timeline.duration=Math.max(1000,Math.min(120000,Number(e.target.value||10000)));doc.timeline.playRange=doc.timeline.playRange||{start:0,end:doc.timeline.duration};doc.timeline.playRange.start=Math.min(doc.timeline.playRange.start||0,doc.timeline.duration-100);doc.timeline.playRange.end=Math.max(doc.timeline.playRange.start+100,Math.min(doc.timeline.duration,doc.timeline.playRange.end||doc.timeline.duration))});const saveRange=()=>{const duration=state().timeline.duration||10000,start=Math.max(0,Math.min(duration-100,Number(q('[data-tl-range-start]').value||0))),end=Math.max(start+100,Math.min(duration,Number(q('[data-tl-range-end]').value||duration)));update('Change timeline play range',doc=>doc.timeline.playRange={start,end})};q('[data-tl-range-start]',panel).onchange=saveRange;q('[data-tl-range-end]',panel).onchange=saveRange;const scrub=q('[data-tl-scrub]',panel);scrub.oninput=e=>{q('[data-tl-time]').textContent=`${(Number(e.target.value)/1000).toFixed(2)}s`;window.EInviteTimelineRuntime?.seek(animations,Number(e.target.value))};q('[data-tl-add]',panel).onclick=()=>{const ids=selected(),time=Number(scrub.value);if(!ids.length)return alert('Select at least one object.');update('Add keyframe',doc=>ids.forEach(id=>{const t=trackFor(doc,id),f=captureFrame(time);if(f){t.keyframes=(t.keyframes||[]).filter(x=>Number(x.time)!==time);t.keyframes.push(f);t.keyframes.sort((a,b)=>a.time-b.time);t.duration=Math.max(t.duration||0,time)}}))};q('[data-tl-stagger]',panel).onclick=()=>{const ids=selected();update('Stagger animation',doc=>ids.forEach((id,index)=>trackFor(doc,id).delay=index*120))};q('[data-tl-marker]',panel).onclick=()=>{const name=prompt('Section marker name:','Section');if(!name)return;update('Add timeline marker',doc=>{doc.timeline.markers.push({id:`marker-${Date.now()}`,name:name.slice(0,80),time:Number(scrub.value)})})};q('[data-tl-audio-offset]',panel).onchange=e=>update('Change audio synchronization',doc=>doc.timeline.audioOffset=Math.max(0,Math.min(30000,Number(e.target.value||0))));q('[data-tl-health]',panel).onclick=()=>{const doc=state(),tracks=Object.values(doc.timeline.tracks||{}),frames=tracks.reduce((n,t)=>n+(t.keyframes?.length||0),0),infinite=tracks.filter(t=>t.iterations==='infinite').length,score=tracks.length*2+frames+infinite*8;alert(score>90?'Performance warning: this invitation has many animated objects/keyframes. Consider simplifying continuous motion for mobile guests.':`Timeline looks healthy: ${tracks.length} animated objects and ${frames} keyframes.`)};q('[data-tl-export]',panel).onclick=()=>{const blob=new Blob([JSON.stringify(state().timeline,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='invitation-motion.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};qa('[data-preset]',panel).forEach(b=>b.onclick=()=>preset(b.dataset.preset));q('[data-tl-copy]',panel).onclick=()=>{const id=selected()[0],t=id&&state().timeline.tracks[id];if(t)localStorage.setItem('einvite-motion-clipboard-v13',JSON.stringify(t))};q('[data-tl-paste]',panel).onclick=()=>{let t;try{t=JSON.parse(localStorage.getItem('einvite-motion-clipboard-v13')||'null')}catch{}const ids=selected();if(t&&ids.length)update('Paste motion',doc=>ids.forEach(id=>doc.timeline.tracks[id]=clone(t)))};q('[data-tl-fields]',panel).addEventListener('input',e=>{if(!activeFrame||!e.target.dataset.kf)return;const key=e.target.dataset.kf;if(key==='customEasing'&&!/^cubic-bezier\(\s*-?\d*\.?\d+\s*,\s*-?\d*\.?\d+\s*,\s*-?\d*\.?\d+\s*,\s*-?\d*\.?\d+\s*\)$/.test(e.target.value.trim()))return;const value=key==='easing'?e.target.value:key==='customEasing'?e.target.value.trim():Number(e.target.value);update('Edit keyframe',doc=>{const f=doc.timeline.tracks[activeFrame.id]?.keyframes?.[activeFrame.index];if(f){if(key==='customEasing')f.easing=value;else if(key==='easing'&&value!=='custom')f.easing=value;else if(key!=='easing')f[key]=value}})});q('[data-kf-delete]',panel).onclick=()=>{if(!activeFrame)return;update('Delete keyframe',doc=>doc.timeline.tracks[activeFrame.id]?.keyframes.splice(activeFrame.index,1));activeFrame=null;q('[data-tl-fields]').hidden=true};window.addEventListener('einvite:editor-command',()=>{if(!panel.hidden)render()})}
function boot(){ensure()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();;(()=>{
'use strict';
const bridge=()=>window.EInviteEditorBridge;
const invitationId=()=>window.EInviteContext?.getInvitationId({allowRemembered:false})||window.EInviteContext?.getInvitationId()||'';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json=async(path,options={})=>{const response=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...(options.headers||{})}}),data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.error||`Request failed (${response.status})`);return data};
const dtValue=value=>{if(!value)return'';const d=new Date(Number(value));if(Number.isNaN(d.getTime()))return'';const local=new Date(d.getTime()-d.getTimezoneOffset()*60000);return local.toISOString().slice(0,16)};
const dtStamp=value=>value?new Date(value).getTime():null;
let dialog,content,title,status,current='events',serverInvite=null;
function ensureOrder(doc,name,before='rsvp'){doc.sectionOrder=Array.isArray(doc.sectionOrder)?doc.sectionOrder:[];if(doc.sectionOrder.includes(name))return;const at=doc.sectionOrder.indexOf(before);doc.sectionOrder.splice(at>=0?at:doc.sectionOrder.length,0,name)}
function mutate(label,fn){if(!bridge())return;bridge().transact(label,doc=>{fn(doc);doc.schemaVersion=Math.max(13,Number(doc.schemaVersion||0))})}
function mount(){if(document.getElementById('v13OperationsBtn'))return;const button=document.createElement('button');button.id='v13OperationsBtn';button.className='v13-ops-launcher';button.textContent='Studio Ops';button.setAttribute('aria-haspopup','dialog');button.dataset.serverOnly='true';button.onclick=open;document.body.append(button);const syncBackend=()=>{const offline=!!window.EInviteBackend&&!window.EInviteBackend.isAvailable();button.disabled=offline;button.setAttribute('aria-disabled',String(offline));button.title=offline?'This feature requires the full application server.':'Open Studio operations'};window.EInviteBackend?.ready?.then(syncBackend);window.EInviteBackend?.onChange?.(syncBackend);syncBackend();
 dialog=document.createElement('dialog');dialog.id='v13OperationsDialog';dialog.setAttribute('aria-labelledby','v13OpsTitle');dialog.innerHTML=`<div class="v13-ops-shell"><nav class="v13-ops-nav" aria-label="Studio operations"><h2>Studio Ops</h2>${[['events','Events'],['guest','Guest info'],['publish','Publish'],['campaigns','Delivery'],['review','Review'],['versions','Versions'],['brand','Brand kit']].map(([id,label])=>`<button data-v13-tab="${id}" role="tab">${label}</button>`).join('')}</nav><section class="v13-ops-main"><header class="v13-ops-head"><strong id="v13OpsTitle">Studio operations</strong><span id="v13OpsStatus" class="v13-status"></span><span class="spacer"></span><button class="v13-ops-close" aria-label="Close Studio operations">×</button></header><div id="v13OpsContent" class="v13-ops-content"></div></section></div>`;document.body.append(dialog);content=dialog.querySelector('#v13OpsContent');title=dialog.querySelector('#v13OpsTitle');status=dialog.querySelector('#v13OpsStatus');dialog.querySelector('.v13-ops-close').onclick=()=>dialog.close();dialog.addEventListener('cancel',()=>{});dialog.querySelectorAll('[data-v13-tab]').forEach(b=>b.onclick=()=>show(b.dataset.v13Tab));
}
async function open(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){window.EInviteBackend.message(document.querySelector('main')||document.body,'Studio Ops, campaigns, comments, approvals, version restore, and check-in require the full application server.');return}dialog.showModal();try{if(invitationId())serverInvite=await json(`/api/invitations/${encodeURIComponent(invitationId())}`)}catch{}await show(current)}
async function show(tab){current=tab;dialog.querySelectorAll('[data-v13-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.v13Tab===tab)));title.textContent=({events:'Events & ceremonies',guest:'Guest experience',publish:'Publishing & domains',campaigns:'Guest delivery',review:'Comments & approval',versions:'Published versions',brand:'Brand kit'}[tab]||'Studio operations');content.innerHTML='<p class="v13-help">Loading…</p>';try{await ({events:renderEvents,guest:renderGuest,publish:renderPublish,campaigns:renderCampaigns,review:renderReview,versions:renderVersions,brand:renderBrand}[tab]||renderEvents)()}catch(e){content.innerHTML=`<div class="v13-card"><strong>Could not load this workspace.</strong><p>${esc(e.message)}</p></div>`}}
function renderEvents(){const doc=bridge().getState(),events=Array.isArray(doc.events)?doc.events:[];content.innerHTML=`<div class="v13-card"><h3>Multiple ceremonies and events</h3><p class="v13-help">These events remain part of the invitation document and can be shown as one guest-facing event itinerary.</p><label class="v13-field">Invitation timezone<input id="v13Timezone" value="${esc(doc.timezone||Intl.DateTimeFormat().resolvedOptions().timeZone||'Asia/Phnom_Penh')}" placeholder="Asia/Phnom_Penh"></label><div id="v13Events">${events.map(eventRow).join('')}</div><div class="v13-row"><button id="v13AddEvent" class="primary">Add event</button><button id="v13SaveEvents">Save events</button></div></div>`;content.querySelector('#v13AddEvent').onclick=()=>{const id=crypto.randomUUID?.()||`event-${Date.now()}`;mutate('Add event',d=>{d.events=Array.isArray(d.events)?d.events:[];d.events.push({id,name:'New ceremony',type:'ceremony',date:d.fields?.date||'',time:d.fields?.time||'',venue:d.fields?.venue||'',mapUrl:'',enabled:true});ensureOrder(d,'events','schedule')});renderEvents()};content.querySelector('#v13SaveEvents').onclick=()=>{const rows=[...content.querySelectorAll('[data-event-id]')];mutate('Update events',d=>{d.timezone=content.querySelector('#v13Timezone').value.trim()||'Asia/Phnom_Penh';d.events=rows.map(row=>({id:row.dataset.eventId,name:row.querySelector('[name=name]').value.trim(),type:row.querySelector('[name=type]').value,date:row.querySelector('[name=date]').value,time:row.querySelector('[name=time]').value,venue:row.querySelector('[name=venue]').value.trim(),mapUrl:row.querySelector('[name=map]').value.trim(),enabled:row.querySelector('[name=enabled]').checked}));if(d.events.some(x=>x.enabled))ensureOrder(d,'events','schedule')});status.textContent='Saved';setTimeout(()=>status.textContent='',1600)};content.querySelectorAll('[data-remove-event]').forEach(b=>b.onclick=()=>{mutate('Remove event',d=>d.events=(d.events||[]).filter(x=>x.id!==b.dataset.removeEvent));renderEvents()})}
function eventRow(e){return`<div class="v13-event-row" data-event-id="${esc(e.id)}"><label>Name<input name="name" value="${esc(e.name||'')}"></label><label>Type<select name="type">${['ceremony','reception','party','meeting','other'].map(x=>`<option ${e.type===x?'selected':''}>${x}</option>`).join('')}</select></label><label>Date<input name="date" type="date" value="${esc(e.date||'')}"></label><label>Time<input name="time" type="time" value="${esc(e.time||'')}"></label><label class="v13-event-wide">Venue<input name="venue" value="${esc(e.venue||'')}"></label><label class="v13-event-wide">Map URL<input name="map" type="url" value="${esc(e.mapUrl||'')}"></label><label><input name="enabled" type="checkbox" ${e.enabled!==false?'checked':''}> Enabled</label><button data-remove-event="${esc(e.id)}" class="danger">Remove</button></div>`}
function renderGuest(){const d=bridge().getState(),g=d.guestExperience||{},gp=d.galleryProtection||{};content.innerHTML=`<div class="v13-grid"><div class="v13-card"><h3>Guest information</h3><label class="v13-field">Dress code<input id="gDress" value="${esc(g.dressCode||'')}"></label><label class="v13-field">Transport<textarea id="gTransport">${esc(g.transport||'')}</textarea></label><label class="v13-field">Accommodation<textarea id="gAccommodation">${esc(g.accommodation||'')}</textarea></label></div><div class="v13-card"><h3>Useful links</h3><label class="v13-field">Gift registry / contribution link<input id="gGift" type="url" value="${esc(g.giftLink||'')}"></label><label class="v13-field">Gift link label<input id="gGiftLabel" value="${esc(g.giftLabel||'Gift registry')}"></label><label class="v13-field">Optional payment link<input id="gPayment" type="url" value="${esc(g.paymentLink||'')}"></label><label class="v13-field">Payment link label<input id="gPaymentLabel" value="${esc(g.paymentLabel||'Contribution / payment')}"></label><label class="v13-field">Additional note<textarea id="gNote">${esc(g.note||'')}</textarea></label></div><div class="v13-card"><h3>Private photo gallery</h3><label class="v13-check"><input id="galleryProtected" type="checkbox" ${gp.enabled?'checked':''}> Require a separate password for gallery-only photos</label><label class="v13-field">New gallery password<input id="galleryPassword" type="password" minlength="8" autocomplete="new-password" placeholder="Leave blank to keep the existing password"></label><p class="v13-help">For strongest protection, set gallery-only photos to <strong>Hide from hero</strong>. Photos also used on public design pages remain public because guests must be able to see those pages.</p></div></div><button id="saveGuestInfo" class="primary">Save guest experience</button>`;content.querySelector('#saveGuestInfo').onclick=async()=>{const protectedGallery=content.querySelector('#galleryProtected').checked,password=content.querySelector('#galleryPassword').value;mutate('Update guest information',d=>{d.guestExperience={...(d.guestExperience||{}),dressCode:content.querySelector('#gDress').value.trim(),transport:content.querySelector('#gTransport').value.trim(),accommodation:content.querySelector('#gAccommodation').value.trim(),giftLink:content.querySelector('#gGift').value.trim(),giftLabel:content.querySelector('#gGiftLabel').value.trim(),paymentLink:content.querySelector('#gPayment').value.trim(),paymentLabel:content.querySelector('#gPaymentLabel').value.trim(),note:content.querySelector('#gNote').value.trim()};d.galleryProtection={...(d.galleryProtection||{}),enabled:protectedGallery,locked:false};if(Object.values(d.guestExperience).some(Boolean))ensureOrder(d,'guest-info','venue')});if(invitationId())await json(`/api/invitations/${encodeURIComponent(invitationId())}/gallery-access`,{method:'PUT',body:JSON.stringify({enabled:protectedGallery,password})});serverInvite={...(serverInvite||{}),galleryProtected:protectedGallery};status.textContent='Saved'}}
async function renderPublish(){const inv=serverInvite||{},doc=bridge().getState(),privacy=doc.privacy||{};content.innerHTML=`<div class="v13-grid"><div class="v13-card"><h3>Publication schedule</h3><label class="v13-field">Publish at<input id="opPublish" type="datetime-local" value="${dtValue(inv.publishAt)}"></label><label class="v13-field">Unpublish at<input id="opUnpublish" type="datetime-local" value="${dtValue(inv.unpublishAt)}"></label><label class="v13-field">Invitation expires at<input id="opExpire" type="datetime-local" value="${dtValue(inv.expiresAt)}"></label></div><div class="v13-card"><h3>Custom domain</h3><label class="v13-field">Domain<input id="opDomain" value="${esc(inv.customDomain||'')}" placeholder="invite.example.com"></label><p class="v13-help">DNS and TLS must be configured by the hosting provider before a custom domain can serve traffic.</p></div><div class="v13-card"><h3>Guest privacy choices</h3><label class="v13-check"><input id="opAnalyticsConsent" type="checkbox" ${privacy.analyticsConsentRequired?'checked':''}> Ask before recording an analytics visit</label><label class="v13-check"><input id="opExternalConsent" type="checkbox" ${privacy.externalMediaConsentRequired?'checked':''}> Ask before loading YouTube or SoundCloud</label><p class="v13-help">Guests can continue without optional consent. External embeds stay unloaded until permission is granted when this option is enabled.</p></div></div><button id="savePublishOps" class="primary">Save publishing settings</button><p class="v13-help">Scheduled publishing stores an immutable snapshot of the current draft. Public access still follows invitation password and expiry rules.</p>`;content.querySelector('#savePublishOps').onclick=async()=>{const payload={customDomain:content.querySelector('#opDomain').value.trim(),publishAt:dtStamp(content.querySelector('#opPublish').value),unpublishAt:dtStamp(content.querySelector('#opUnpublish').value),expiresAt:dtStamp(content.querySelector('#opExpire').value)};mutate('Update guest privacy choices',d=>d.privacy={...(d.privacy||{}),analyticsConsentRequired:content.querySelector('#opAnalyticsConsent').checked,externalMediaConsentRequired:content.querySelector('#opExternalConsent').checked});const result=await json(`/api/invitations/${encodeURIComponent(invitationId())}/operations`,{method:'PUT',body:JSON.stringify(payload)});serverInvite={...(serverInvite||{}),...result};status.textContent='Saved'}}
async function renderCampaigns(){if(!invitationId())return content.innerHTML='<p>Save this invitation to an account before using delivery campaigns.</p>';const list=await json(`/api/invitations/${encodeURIComponent(invitationId())}/campaigns`);content.innerHTML=`<div class="v13-card"><h3>Create delivery campaign</h3><div class="v13-grid"><label class="v13-field">Name<input id="campName" value="Invitation delivery"></label><label class="v13-field">Channel<select id="campChannel"><option>email</option><option>sms</option><option>whatsapp</option><option>telegram</option></select></label><label class="v13-field">Guest group<input id="campGroup" placeholder="Optional"></label><label class="v13-field">Guest tag<input id="campTag" placeholder="Optional"></label></div><label class="v13-field">Message<textarea id="campMessage">You are warmly invited to our celebration.</textarea></label><button id="createCampaign" class="primary">Create campaign</button><p class="v13-help">Email uses the configured SMTP provider. SMS, WhatsApp and Telegram use the optional messaging-provider webhook abstraction. Without credentials, dispatch runs in preview mode rather than pretending to send.</p></div><div class="v13-card"><h3>Campaign history</h3>${list.length?list.map(c=>`<div class="v13-list-item"><div class="v13-row"><strong>${esc(c.name)}</strong><span class="v13-badge">${esc(c.channel)}</span><span class="v13-badge">${esc(c.state)}</span><span class="v13-grow"></span><button data-dispatch-campaign="${esc(c.id)}">Dispatch</button><button data-view-deliveries="${esc(c.id)}">Delivery log</button></div><p>${esc(c.message)}</p></div>`).join(''):'<p>No campaigns yet.</p>'}</div>`;content.querySelector('#createCampaign').onclick=async()=>{await json(`/api/invitations/${encodeURIComponent(invitationId())}/campaigns`,{method:'POST',body:JSON.stringify({name:content.querySelector('#campName').value,channel:content.querySelector('#campChannel').value,message:content.querySelector('#campMessage').value,segment:{group:content.querySelector('#campGroup').value.trim(),tag:content.querySelector('#campTag').value.trim()}})});renderCampaigns()};content.querySelectorAll('[data-dispatch-campaign]').forEach(b=>b.onclick=async()=>{const result=await json(`/api/invitations/${encodeURIComponent(invitationId())}/campaigns/${b.dataset.dispatchCampaign}/dispatch`,{method:'POST',body:'{}'});alert(`Delivery completed: ${result.sent} sent, ${result.preview} preview, ${result.failed} failed.`);renderCampaigns()});content.querySelectorAll('[data-view-deliveries]').forEach(b=>b.onclick=async()=>{const rows=await json(`/api/invitations/${encodeURIComponent(invitationId())}/campaigns/${b.dataset.viewDeliveries}/deliveries`);content.innerHTML=`<button id="backCampaigns">← Campaigns</button><div class="v13-card"><h3>Delivery log</h3>${rows.map(r=>`<div class="v13-list-item"><strong>${esc(r.name||r.guest_id)}</strong> · ${esc(r.status)}<br><small>${esc(r.email||r.phone||'')} ${esc(r.error||'')}</small></div>`).join('')||'<p>No delivery attempts yet.</p>'}</div>`;content.querySelector('#backCampaigns').onclick=renderCampaigns})}
async function renderReview(){const [comments,approvals]=await Promise.all([json(`/api/invitations/${encodeURIComponent(invitationId())}/comments`),json(`/api/invitations/${encodeURIComponent(invitationId())}/approvals`)]);const selected=bridge().getSelectedIds()[0]||'';content.innerHTML=`<div class="v13-grid"><div class="v13-card"><h3>Comments</h3><label class="v13-field">Comment on ${selected?'selected object':'invitation'}<textarea id="reviewComment"></textarea></label><button id="addReviewComment">Add comment</button>${comments.map(c=>`<div class="v13-list-item"><strong>${esc(c.email||'Collaborator')}</strong> ${c.object_id?`<span class="v13-badge">Object ${esc(c.object_id)}</span>`:''}<p>${esc(c.body)}</p>${c.resolved?'<span class="v13-badge">Resolved</span>':`<button data-resolve-comment="${esc(c.id)}">Resolve</button>`}</div>`).join('')||'<p>No comments.</p>'}</div><div class="v13-card"><h3>Approval</h3><label class="v13-field">Reviewer email or account ID<input id="approvalTo"></label><label class="v13-field">Note<textarea id="approvalNote"></textarea></label><button id="requestApproval">Request approval</button>${approvals.map(a=>`<div class="v13-list-item"><strong>${esc(a.requester_email||'Request')}</strong> · <span class="v13-badge">${esc(a.status)}</span><p>${esc(a.note)}</p>${a.status==='pending'?`<div class="v13-row"><button data-approve="${esc(a.id)}">Approve</button><button data-change-request="${esc(a.id)}">Request changes</button></div>`:''}</div>`).join('')||'<p>No approval requests.</p>'}</div></div>`;content.querySelector('#addReviewComment').onclick=async()=>{await json(`/api/invitations/${encodeURIComponent(invitationId())}/comments`,{method:'POST',body:JSON.stringify({body:content.querySelector('#reviewComment').value,objectId:selected})});renderReview()};content.querySelectorAll('[data-resolve-comment]').forEach(b=>b.onclick=async()=>{await json(`/api/invitations/${encodeURIComponent(invitationId())}/comments/${b.dataset.resolveComment}`,{method:'PUT',body:JSON.stringify({resolved:true})});renderReview()});content.querySelector('#requestApproval').onclick=async()=>{await json(`/api/invitations/${encodeURIComponent(invitationId())}/approvals`,{method:'POST',body:JSON.stringify({requestedFrom:content.querySelector('#approvalTo').value,note:content.querySelector('#approvalNote').value})});renderReview()};content.querySelectorAll('[data-approve]').forEach(b=>b.onclick=()=>decide(b.dataset.approve,'approved'));content.querySelectorAll('[data-change-request]').forEach(b=>b.onclick=()=>decide(b.dataset.changeRequest,'changes-requested'));async function decide(id,state){await json(`/api/invitations/${encodeURIComponent(invitationId())}/approvals/${id}`,{method:'PUT',body:JSON.stringify({status:state})});renderReview()}}
async function renderVersions(){const list=await json(`/api/invitations/${encodeURIComponent(invitationId())}/versions`);content.innerHTML=`<div class="v13-card"><h3>Published version history</h3><p class="v13-help">Published snapshots are immutable. Restoring copies a snapshot back into the draft without changing the historical publication.</p>${list.map(v=>`<div class="v13-list-item"><div class="v13-row"><strong>Version ${esc(v.version)}</strong><span>${new Date(v.published_at).toLocaleString()}</span><span class="v13-grow"></span><button data-view-version="${esc(v.version)}">Compare</button><button data-restore-published="${esc(v.version)}">Restore as draft</button></div></div>`).join('')||'<p>No published versions yet.</p>'}</div><div id="versionCompare"></div>`;content.querySelectorAll('[data-view-version]').forEach(b=>b.onclick=()=>compareVersion(b.dataset.viewVersion));content.querySelectorAll('[data-restore-published]').forEach(b=>b.onclick=async()=>{if(!confirm('Replace the current draft with this published snapshot?'))return;const result=await json(`/api/invitations/${encodeURIComponent(invitationId())}/restore-version`,{method:'POST',body:JSON.stringify({version:b.dataset.restorePublished})});bridge().replaceState(result.document,{reason:'restore published version'});status.textContent='Draft restored'})}
async function compareVersion(version){const old=await json(`/api/invitations/${encodeURIComponent(invitationId())}/versions/${encodeURIComponent(version)}`),now=bridge().cloneState(),keys=[...new Set([...Object.keys(old.document||{}),...Object.keys(now||{})])],changed=keys.filter(k=>JSON.stringify(old.document?.[k])!==JSON.stringify(now?.[k]));content.querySelector('#versionCompare').innerHTML=`<div class="v13-card"><h3>Changed areas since version ${esc(version)}</h3><p>${changed.map(k=>`<span class="v13-badge">${esc(k)}</span>`).join(' ')||'No top-level differences.'}</p><div class="v13-diff"><pre>${esc(JSON.stringify(Object.fromEntries(changed.slice(0,12).map(k=>[k,old.document?.[k]])),null,2))}</pre><pre>${esc(JSON.stringify(Object.fromEntries(changed.slice(0,12).map(k=>[k,now?.[k]])),null,2))}</pre></div></div>`}
function renderBrand(){const d=bridge().getState(),b=d.brandKit||{};content.innerHTML=`<div class="v13-grid"><div class="v13-card"><h3>Reusable brand kit</h3><label class="v13-field">Brand name<input id="brandName" value="${esc(b.name||'')}"></label><label class="v13-field">Logo URL<input id="brandLogo" value="${esc(b.logo||'')}"></label><label class="v13-field">Primary color<input id="brandPrimary" type="color" value="${esc(b.primaryColor||d.palette?.primary||'#9d4555')}"></label><label class="v13-field">Accent color<input id="brandAccent" type="color" value="${esc(b.accentColor||d.palette?.accent||'#b58a3a')}"></label></div><div class="v13-card"><h3>Typography pairs</h3><label class="v13-field">Latin heading font<input id="brandHeading" value="${esc(b.headingFont||'')}"></label><label class="v13-field">Latin body font<input id="brandBody" value="${esc(b.bodyFont||'')}"></label><label class="v13-field">Khmer heading font<input id="brandKhHeading" value="${esc(b.khmerHeadingFont||'')}"></label><label class="v13-field">Khmer body font<input id="brandKhBody" value="${esc(b.khmerBodyFont||'')}"></label></div></div><div class="v13-actions"><button id="loadStudioBrand" type="button">Load account studio identity</button><button id="saveBrand" class="primary">Save brand kit</button></div>`;content.querySelector('#loadStudioBrand').onclick=async()=>{try{const s=await json('/api/account/studio'),w=s.whiteLabel||{};content.querySelector('#brandName').value=s.studioName||'';content.querySelector('#brandLogo').value=w.logo||'';if(/^#[0-9a-f]{6}$/i.test(w.primaryColor||''))content.querySelector('#brandPrimary').value=w.primaryColor;if(/^#[0-9a-f]{6}$/i.test(w.accentColor||''))content.querySelector('#brandAccent').value=w.accentColor;status.textContent='Studio identity loaded. Save the brand kit to apply it to this invitation.'}catch(e){status.textContent=e.message}};content.querySelector('#saveBrand').onclick=()=>mutate('Update brand kit',doc=>doc.brandKit={...(doc.brandKit||{}),name:content.querySelector('#brandName').value.trim(),logo:content.querySelector('#brandLogo').value.trim(),primaryColor:content.querySelector('#brandPrimary').value,accentColor:content.querySelector('#brandAccent').value,headingFont:content.querySelector('#brandHeading').value.trim(),bodyFont:content.querySelector('#brandBody').value.trim(),khmerHeadingFont:content.querySelector('#brandKhHeading').value.trim(),khmerBodyFont:content.querySelector('#brandKhBody').value.trim()})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();