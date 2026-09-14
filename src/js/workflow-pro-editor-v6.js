(()=>{
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
})();
