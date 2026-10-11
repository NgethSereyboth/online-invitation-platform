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
})();
