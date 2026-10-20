(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage'))return;
const body=document.body, main=$('body.studio-experience>main');
const rail=$('.studio-tool-rail'), host=$('.studio-pane-host');
const stageWrap=$('.stage-wrap',main), inspector=$('.right',main);
const status=$('.studio-statusbar'), selection=$('.studio-selection-toolbar');
const version='2026-07-22-scroll-sidebar-stability-v1';
if(localStorage.getItem('einvite-layout-stability-version')!==version){
  localStorage.setItem('einvite-left-width','370');
  localStorage.setItem('einvite-right-width','330');
  localStorage.removeItem('einvite-left-collapsed');
  localStorage.removeItem('einvite-right-collapsed');
  body.classList.remove('studio-left-collapsed','studio-right-collapsed','mobile-pane-collapsed','inspector-open');
  localStorage.setItem('einvite-layout-stability-version',version);
}
function clampPanelWidths(){
  const rawL=Number(localStorage.getItem('einvite-left-width'))||370;
  const rawR=Number(localStorage.getItem('einvite-right-width'))||330;
  const viewport=Math.max(1000,window.innerWidth||1000);
  const maxL=Math.min(520,Math.max(330,viewport*.32));
  const maxR=Math.min(460,Math.max(290,viewport*.28));
  const left=Math.max(300,Math.min(maxL,rawL));
  const right=Math.max(280,Math.min(maxR,rawR));
  document.documentElement.style.setProperty('--studio-left-width',`${Math.round(left)}px`);
  document.documentElement.style.setProperty('--studio-right-width',`${Math.round(right)}px`);
  if(left!==rawL)localStorage.setItem('einvite-left-width',String(Math.round(left)));
  if(right!==rawR)localStorage.setItem('einvite-right-width',String(Math.round(right)));
}
function activeSection(){return $('.studio-pane.active',host)?.dataset.studioPane||'event'}
function applyLayout(){
  const section=activeSection();
  const content=section==='event'||section==='blocks';
  body.classList.toggle('studio-content-mode',content);
  body.classList.toggle('studio-design-mode',!content);
  body.dataset.studioSection=section;
  if(main){main.style.removeProperty('display');main.style.removeProperty('grid-template-columns')}
  if(stageWrap)stageWrap.hidden=content;
  if(inspector)inspector.hidden=content;
  if(selection)selection.hidden=content;
  if(status)status.hidden=content||innerWidth<=1180;
  $$('.studio-panel-resizer',main).forEach(x=>x.hidden=content||innerWidth<=1180);
  // P2 fix (DESIGN-FIX-TASK 2026-10-19): never hide the canvas because an
  // Event/Blocks/content panel is active. The canvas is the product here —
  // users were losing their poster the moment they opened Event or Blocks.
  // Content mode now only collapses the inspector; the stage stays visible
  // at every viewport width (mobile included, where the drawers overlay it).
  if(stageWrap)stageWrap.hidden=false;
  if(inspector)inspector.hidden=false;
  if(selection)selection.hidden=content;
  if(status)status.hidden=innerWidth<=1180;
  $$('.studio-panel-resizer',main).forEach(x=>x.hidden=innerWidth<=1180);
  if(content){
    body.classList.remove('mobile-pane-collapsed');
  }else{
    requestAnimationFrame(()=>{
      try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{}
      window.dispatchEvent(new Event('einvite:layout-stable'));
    });
  }
}
clampPanelWidths();
applyLayout();
  // Owner decision (CANVA-UI §5, accepted 2026-10-20): poster documents have
  // no event data — hide the Event/Blocks rail buttons, the RSVP + countdown
  // left-panel groups ([data-poster-hide] wrappers in index.html) and the
  // Design-home Event/Blocks cards (workflow-refine flow); auto-open the
  // Elements pane once; the canvas itself now always stays visible.
  function posterPanelTreatments(){
    $$('.studio-tool-rail [data-studio-tab="event"],.studio-tool-rail [data-studio-tab="blocks"]').forEach(b=>{b.hidden=true});
    $$('[data-poster-hide]').forEach(node=>{node.hidden=true});
    $$('[data-flow-open="event"],[data-flow-open="blocks"]').forEach(el=>{
      if(el.closest('[data-studio-pane="design"]'))el.hidden=true; // flow cards
    });
    if(['event','blocks'].includes(activeSection())){ // never leave a hidden pane active
      document.querySelector('.studio-tool-rail [data-studio-tab="elements"]')?.click();
    }
  }
  // workflow-refine (Design home) rebuilds/reorders the rail after this script
  // runs; re-apply the treatments whenever those surfaces change.
  const posterTreatWatcher=new MutationObserver(()=>{
    if(body.dataset.posterPaneApplied)posterPanelTreatments();
  });
  for(const target of [rail,host]){
    if(target)posterTreatWatcher.observe(target,{childList:true,subtree:target!==rail});
  }
  // Public hook: app.js (connectServer) re-migrates `state` from the fetched
  // server document and calls this; it re-drives posterAutoPane without assuming
  // load order beyond app.js loading later in the bundle.
  window.EInvitePosterTreat=()=>{try{window.__posterPaneWaitDone=false;applyLayout();posterAutoPane()}catch{}};
  function posterAutoPane(){
  const st=window.EInviteEditorBridge?.getState?.();
  if(!st||st.eventType!=='Poster'||body.dataset.posterPaneApplied)return;
  body.dataset.posterPaneApplied='1';
  posterPanelTreatments();
  if(activeSection()==='event'){
    // Route the switch through the public tab button (click) — direct class
    // toggles get re-applied back by the pane watchers.
    document.querySelector('.studio-tool-rail [data-studio-tab="elements"]')?.click();
  }
}
posterAutoPane();
for(const n of ['einvite:editor-ready','einvite:editor-state-replaced'])document.addEventListener(n,posterAutoPane);
(function posterPanePoll(attempt){ // panes are built later by studio-experience; poll briefly
  if(body.dataset.posterPaneApplied||attempt>600){const st=window.EInviteEditorBridge?.getState?.();if(st&&st.eventType==='Poster'&&attempt<=600&&!window.__posterPaneWaitDone){window.__posterPaneWaitDone=true;setTimeout(()=>posterAutoPane(),100);return}return}
  window.__posterPaneWaitDone=false;requestAnimationFrame(()=>posterPanePoll(attempt+1));
})(0);
rail?.addEventListener('click',()=>requestAnimationFrame(applyLayout));
new MutationObserver(applyLayout).observe(host,{subtree:true,attributes:true,attributeFilter:['class']});
addEventListener('resize',()=>{clampPanelWidths();applyLayout()});
for(const el of $$('.studio-pane,.studio-inspector-pane,.studio-tool-rail')){
  el.addEventListener('wheel',event=>{
    if(Math.abs(event.deltaY)<=Math.abs(event.deltaX))return;
    const canScroll=el.scrollHeight>el.clientHeight+1;
    if(!canScroll)return;
    const atTop=el.scrollTop<=0&&event.deltaY<0;
    const atBottom=el.scrollTop+el.clientHeight>=el.scrollHeight-1&&event.deltaY>0;
    if(!atTop&&!atBottom)event.stopPropagation();
  },{passive:true});
}
})();
