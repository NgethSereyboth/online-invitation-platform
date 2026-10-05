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
  if(content){
    body.classList.remove('inspector-open','mobile-pane-collapsed');
  }else{
    requestAnimationFrame(()=>{
      try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{}
      window.dispatchEvent(new Event('einvite:layout-stable'));
    });
  }
}
clampPanelWidths();
applyLayout();
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
