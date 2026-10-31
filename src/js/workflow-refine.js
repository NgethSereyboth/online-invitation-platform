(()=>{
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
    elements:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.2 5.2L19 10l-4.8 1.8L12 17l-2.2-5.2L5 10l4.8-1.8z"/><circle cx="18" cy="18" r="2"/></svg>',
    text:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M12 6v12M8.5 18h7"/></svg>',
    media:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="14" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="m6.5 17 4.5-4 3 2.5 2.5-2 2 3.5"/></svg>',
    pages:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
    event:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3v3M17 3v3M4 9h16"/><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 13h3M13 13h3M8 17h3"/></svg>',
    blocks:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/></svg>'
  };
  return icons[kind]||icons.pages;
}
/* The left "Design" home pane was retired on the owner's instruction. The tool
   rail's own tabs are the navigation, and the pane's remaining content already
   exists elsewhere: invitation styles and the palette live in the inspector's
   Page group, Event details / Content blocks are rail tabs, and canvas
   background controls mount into the same Page group. Pages is the default
   rail item; no home pane is created. */
function reorderRail(){
  const order=['pages','elements','text','media','event','blocks'];
  order.forEach(id=>{const b=$(`[data-studio-tab="${id}"]`,rail);if(b)rail.append(b)});
  $$('[data-studio-tab]',rail).forEach(b=>{
    const id=b.dataset.studioTab;
    const ico=$('.studio-nav-icon',b);
    if(ico&&order.includes(id)){ico.classList.add('flow-icon');ico.innerHTML=iconSvg(id)}
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
  // DESIGN-FIX P2: content mode keeps the canvas visible; only the inspector collapses.
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
  const first=valid(requested)?requested:valid(saved)?saved:'pages';
  const sessionActive=sessionStorage.getItem('einvite-editor-session-active')==='1';
  activate(sessionActive?first:'pages',{focus:false});
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
  if(!p||!p.isConnected){activate('pages',{focus:false});return}
  applyMode(p.dataset.studioPane||'pages');
  p.style.removeProperty('height');
  if(['event','blocks'].includes(p.dataset.studioPane)){
    body.classList.remove('inspector-open','mobile-pane-collapsed');
  }
}
reorderRail();
decorateTopbar();
normalizeInitialFlow();
/* Interaction routing is intentionally centralized in workflow-continuity.js.
   Keeping the older rail/selection/mobile listeners disabled avoids duplicate
   state changes, inspector jumps, and sidebar races. */
setTimeout(safetyPass,400);
localStorage.setItem('einvite-workflow-version',FLOW_VERSION);
})();
