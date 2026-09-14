(()=>{
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
})();
