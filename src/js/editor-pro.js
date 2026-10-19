(()=>{
'use strict';
// Shared motion primitives initialize before the editor-only DOM guard.
const MOTION=Object.freeze({TWEEN_MAX_MS:150,WHEEL_REARM_MS:80,WHEEL_SETTLE_MS:140,ZOOM_COMMIT_MS:200,FLICK_LOCK_MS:250,LONG_PRESS_MS:251,TRANSITION_MAX_MS:400,IDLE_MAX_MS:100,NUDGE_COMMIT_MS:500});
const motionBatchers=new Set();
const perfDebug=typeof location!=='undefined'&&new URLSearchParams(location.search).get('_perfdebug')==='1';
const perfTotals={commits:0,commitMs:0,maximumCommitMs:0,layoutReads:0,decoded:0,decodeFailures:0};
function finishPerfSpan(name){performance.mark(`${name}:end`);performance.measure(name,`${name}:start`,`${name}:end`);performance.clearMarks(`${name}:start`);performance.clearMarks(`${name}:end`);if(performance.getEntriesByName(name).length>200)performance.clearMeasures(name)};
if(perfDebug)window.__einvitePerf=perfTotals;
function measureMotionCommit(run){if(!perfDebug)return run();const start=performance.now();performance.mark('einvite:commit:start');try{return run()}finally{const duration=performance.now()-start;perfTotals.commits++;perfTotals.commitMs+=duration;perfTotals.maximumCommitMs=Math.max(perfTotals.maximumCommitMs,duration);finishPerfSpan('einvite:commit')}}
function createFrameBatcher(reduce,commit){
 let pending=false,value,frame=0,destroyed=false;
 function flush(){
  if(frame){cancelAnimationFrame(frame);frame=0}
  if(!pending)return;
  const next=value;pending=false;value=undefined;measureMotionCommit(()=>commit(next));
 }
 const batcher={
  accumulate(next){if(destroyed)return;value=pending?reduce(value,next):next;pending=true;if(!frame)frame=requestAnimationFrame(()=>{frame=0;flush()})},
  flush,
  destroy(){if(frame)cancelAnimationFrame(frame);frame=0;pending=false;value=undefined;destroyed=true;motionBatchers.delete(batcher)}
 };
 motionBatchers.add(batcher);return batcher;
}
function debounce(fn,ms){
 let timer=0,args,receiver;
 function flush(){if(!timer)return;clearTimeout(timer);timer=0;const next=args;args=undefined;fn.apply(receiver,next)}
 function debounced(...next){args=next;receiver=this;clearTimeout(timer);timer=setTimeout(flush,ms)}
 debounced.flush=flush;debounced.cancel=()=>{clearTimeout(timer);timer=0;args=undefined};return debounced;
}
function flushMotion(){motionBatchers.forEach(batcher=>batcher.flush())}
document.addEventListener('visibilitychange',flushMotion);
const motionAPI={MOTION,createFrameBatcher,debounce,flush:flushMotion,viewport:null};
window.EInviteMotion=motionAPI;
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const escapeMarkup=value=>String(value??'').replace(/[&<>\"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch]));
const stage=$('#stage'),viewport=$('#canvasViewport'),toolbar=$('.toolbar');if(!stage||!viewport||!toolbar)return;
const transform=$('#stageTransform'),frame=$('#canvasFrame'),zoomControl=$('#zoomLevel');
const view={x:0,y:0,zoom:Number(window.EInviteCanvasViewController?.zoom)||1};
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
let viewRect=null,stageSize={width:390,height:844},viewportSize={width:0,height:0,left:0,top:0},tweenFrame=0,gestureCount=0;
if(perfDebug){
 const restore=[];
 function warn(name){perfTotals.layoutReads++;if(perfTotals.layoutReads<=20)console.warn(`eInvite layout read during gesture: ${name}`)}
 function guardMethod(owner,name){const original=owner[name];const guarded=function(...args){if(gestureCount)warn(name);return original.apply(this,args)};owner[name]=guarded;restore.push(()=>{if(owner[name]===guarded)owner[name]=original})}
 guardMethod(Element.prototype,'getBoundingClientRect');guardMethod(Element.prototype,'getClientRects');guardMethod(window,'getComputedStyle');
 for(const [owner,names] of [[HTMLElement.prototype,['offsetWidth','offsetHeight','offsetLeft','offsetTop']],[Element.prototype,['clientWidth','clientHeight','clientLeft','clientTop','scrollWidth','scrollHeight']]])for(const name of names){const descriptor=Object.getOwnPropertyDescriptor(owner,name);if(!descriptor?.get||!descriptor.configurable)continue;const get=function(){if(gestureCount)warn(name);return descriptor.get.call(this)};Object.defineProperty(owner,name,{...descriptor,get});restore.push(()=>{if(Object.getOwnPropertyDescriptor(owner,name)?.get===get)Object.defineProperty(owner,name,descriptor)})}
 window.EInviteLifecycle?.add?.(()=>restore.reverse().forEach(run=>run()));
}
const clampZoom=z=>Math.max(.1,Math.min(5,Number(z)||1));
function cacheViewGeometry(){viewRect=viewport.getBoundingClientRect();viewportSize={width:viewport.clientWidth,height:viewport.clientHeight,left:viewport.clientLeft,top:viewport.clientTop};stageSize={width:stage.offsetWidth||390,height:stage.offsetHeight||844};return viewRect}
function clientToWorld(x,y){const r=viewRect||cacheViewGeometry();return{x:(x-r.left-viewportSize.left+viewport.scrollLeft-view.x)/view.zoom,y:(y-r.top-viewportSize.top+viewport.scrollTop-view.y)/view.zoom}}
function syncZoomReadout(){
 editorZoom=view.zoom;
 if(zoomControl){if(zoomControl.tagName==='SELECT'&&![...zoomControl.options].some(o=>Number(o.value)===view.zoom))zoomControl.add(new Option(`${Math.round(view.zoom*100)}%`,String(view.zoom)));zoomControl.value=String(view.zoom)}
 if(zoomSlider)zoomSlider.value=String(zoomToSlider(view.zoom));
 if(zoomReadout)zoomReadout.textContent=`${Math.round(view.zoom*100)}%`;
 localStorage.setItem('sovan-editor-zoom',String(view.zoom));
}
function applyView(source='editor'){
 if(!transform)return;
 transform.style.transform=`translate3d(${view.x}px,${view.y}px,0) scale(${view.zoom})`;
 window.dispatchEvent(new CustomEvent('einvite:view-changed',{detail:{...view,source}}));
}
function zoomToSlider(z){return(Math.log2(clampZoom(z)+10)-Math.log2(10.1))/(Math.log2(15)-Math.log2(10.1))*40}
function sliderToZoom(p){return 2**(Math.log2(10.1)+Math.max(0,Math.min(40,p))/40*(Math.log2(15)-Math.log2(10.1)))-10}
function stopTween(){if(tweenFrame)cancelAnimationFrame(tweenFrame);tweenFrame=0}
function setView(next,{source='editor',animate=false,readout=true}={}){
 stopTween();const target={x:Number.isFinite(next.x)?next.x:view.x,y:Number.isFinite(next.y)?next.y:view.y,zoom:clampZoom(next.zoom??view.zoom)};
 const duration=animate&&!reducedMotion.matches?MOTION.TWEEN_MAX_MS:0;
 if(!duration){Object.assign(view,target);applyView(source);if(readout)syncZoomReadout();window.dispatchEvent(new CustomEvent('einvite:zoom-changed',{detail:{zoom:view.zoom,source}}));return view.zoom}
 const before={...view},start=performance.now();
 function tick(time){const p=Math.min(1,(time-start)/duration),t=1-(1-p)**3;view.x=before.x+(target.x-before.x)*t;view.y=before.y+(target.y-before.y)*t;view.zoom=2**(Math.log2(before.zoom)+(Math.log2(target.zoom)-Math.log2(before.zoom))*t);applyView(source);if(p<1)tweenFrame=requestAnimationFrame(tick);else{tweenFrame=0;syncZoomReadout();window.dispatchEvent(new CustomEvent('einvite:zoom-changed',{detail:{zoom:view.zoom,source}}))}}
 tweenFrame=requestAnimationFrame(tick);return target.zoom;
}
function setZoomModel(value,options={}){
 const zoom=clampZoom(value),r=viewRect||cacheViewGeometry();
 const cursor=options.cursor||{x:Number.isFinite(options.clientX)?options.clientX:r.left+viewport.clientWidth/2,y:Number.isFinite(options.clientY)?options.clientY:r.top+viewport.clientHeight/2};
 const world=clientToWorld(cursor.x,cursor.y),ratio=zoom-view.zoom;
 return setView({zoom,x:view.x-world.x*ratio,y:view.y-world.y*ratio},{source:options.source||'editor',animate:options.animate??!['wheel','slider','gesture'].includes(options.source)});
}
function fitView(){cacheViewGeometry();const zoom=Math.max(.35,Math.min(1,(viewport.clientWidth-70)/stageSize.width,(viewport.clientHeight-70)/stageSize.height));return setView({zoom,x:viewport.scrollLeft,y:viewport.scrollTop},{source:'fit',animate:true})}
function refreshView(){cacheViewGeometry();applyView('resize');syncZoomReadout()}
function beginViewGesture(){stopTween();if(!gestureCount){cacheViewGeometry();if(perfDebug)performance.mark('einvite:gesture:start')}gestureCount++;transform?.classList.add('gesture')}
function endViewGesture(){if(!gestureCount)return;gestureCount--;if(!gestureCount){transform?.classList.remove('gesture');syncZoomReadout();if(perfDebug)finishPerfSpan('einvite:gesture');scheduleImageWarmup()}}
function zoomSelection(){const ids=new Set(window.EInviteEditorBridge?.getSelectedIds?.()||[]),items=$$('.object',stage).filter(n=>ids.has(n.dataset.id));if(!items.length)return fitView();cacheViewGeometry();const boxes=items.map(n=>n.getBoundingClientRect()),a=clientToWorld(Math.min(...boxes.map(r=>r.left)),Math.min(...boxes.map(r=>r.top))),b=clientToWorld(Math.max(...boxes.map(r=>r.right)),Math.max(...boxes.map(r=>r.bottom))),zoom=clampZoom(Math.min((viewport.clientWidth-100)/Math.max(1,b.x-a.x),(viewport.clientHeight-100)/Math.max(1,b.y-a.y)));return setView({zoom,x:viewport.clientWidth/2+viewport.scrollLeft-(a.x+b.x)/2*zoom,y:viewport.clientHeight/2+viewport.scrollTop-(a.y+b.y)/2*zoom},{source:'selection',animate:true})}
const zoomSlider=document.createElement('input'),zoomReadout=document.createElement('output');
zoomSlider.id='canvasZoomSlider';zoomSlider.type='range';zoomSlider.min='0';zoomSlider.max='40';zoomSlider.step='.01';zoomSlider.setAttribute('aria-label','Canvas zoom / ពង្រីកផ្ទាំង');zoomReadout.htmlFor=zoomSlider.id;zoomReadout.id='canvasZoomReadout';zoomControl?.after(zoomSlider,zoomReadout);
const sliderBatcher=createFrameBatcher((a,b)=>b,value=>setZoomModel(sliderToZoom(value),{source:'slider'}));zoomSlider.addEventListener('input',()=>sliderBatcher.accumulate(Number(zoomSlider.value)));zoomSlider.addEventListener('change',()=>sliderBatcher.flush());zoomSlider.addEventListener('pointerup',()=>sliderBatcher.flush());
if(transform){
 stage.style.transform='none';stage.style.transformOrigin='0 0';
 Object.assign(stage.style,{left:'0',top:'0'});cacheViewGeometry();
 view.x=(viewport.clientWidth-stageSize.width*view.zoom)/2;view.y=40;
 motionAPI.viewport=Object.freeze({view,refresh:refreshView,setZoom:setZoomModel,setView,fit:fitView,clientToWorld,cacheGeometry:cacheViewGeometry,beginGesture:beginViewGesture,endGesture:endViewGesture,get size(){return{...stageSize}},get gesturing(){return gestureCount>0},get reducedMotion(){return reducedMotion.matches}});
 window.EInviteCanvasViewController=Object.freeze({version:25,get zoom(){return view.zoom},setZoom:setZoomModel,fit:fitView,actual:()=>setZoomModel(1,{source:'actual'}),zoomToSelection:zoomSelection});
 $('#zoomIn').onclick=()=>setZoomModel(view.zoom*1.25,{source:'button'});$('#zoomOut').onclick=()=>setZoomModel(view.zoom/1.25,{source:'button'});$('#fitCanvas').onclick=fitView;zoomControl.onchange=e=>setZoomModel(e.target.value,{source:'select'});
 const ro=new ResizeObserver(()=>{if(!gestureCount)refreshView()});ro.observe(stage);ro.observe(viewport);window.EInviteLifecycle?.add?.(()=>{ro.disconnect();stopTween();sliderBatcher.destroy()});refreshView();
}
// Pure world-space snap resolver: providers are additive; no layout access here.
function snapCandidates({page,others=[],guides={x:[],y:[]},grid=0,box}){
 const result=[],add=(axis,value,kind,source)=>result.push({axis,value,kind,source});
 for(const axis of ['x','y']){const extent=axis==='x'?page.width:page.height;[0,extent/2,extent].forEach((value,i)=>add(axis,value,['start','center','end'][i],'page'));
  for(const item of others.slice(0,100)){const start=item[axis],size=axis==='x'?item.w:item.h;[start,start+size/2,start+size].forEach((value,i)=>add(axis,value,['start','center','end'][i],item.id))}
  for(const guide of guides[axis]||[])add(axis,typeof guide==='number'?guide/100*extent:guide.value,'start',typeof guide==='number'?'guide':guide.id);
  if(grid>0){const start=box[axis];for(let i=-1;i<=1;i++)add(axis,(Math.round(start/grid)+i)*grid,'start','grid')}
 }
 return result;
}
function resolveSnap({box,dx=0,dy=0,page,others=[],guides,grid=0,zoom=1,previous={}}){
 const tolerance=6/zoom,moved={...box,x:box.x+dx,y:box.y+dy},candidates=snapCandidates({page,others,guides,grid,box:moved}),hits={};
 for(const axis of ['x','y']){
  const size=axis==='x'?box.w:box.h,anchors=[0,size/2,size];let best=null;
  for(const candidate of candidates.filter(c=>c.axis===axis))for(const anchor of anchors){const distance=candidate.value-(moved[axis]+anchor),sticky=previous[axis]?.source===candidate.source&&previous[axis]?.value===candidate.value&&previous[axis]?.anchor===anchor,limit=tolerance*(sticky?1.5:1);if(Math.abs(distance)<=limit&&(!best||sticky||Math.abs(distance)<Math.abs(best.distance)))best={...candidate,anchor,distance}}
  // Equal-spacing provider: center the moving box in the nearest enclosing gap.
  const before=others.filter(o=>o[axis]+(axis==='x'?o.w:o.h)<=moved[axis]).sort((a,b)=>b[axis]-a[axis])[0],after=others.filter(o=>o[axis]>=moved[axis]+size).sort((a,b)=>a[axis]-b[axis])[0];
  if(before&&after){const start=before[axis]+(axis==='x'?before.w:before.h),target=(start+after[axis]-size)/2,distance=target-moved[axis];if(Math.abs(distance)<=tolerance&&(!best||Math.abs(distance)<Math.abs(best.distance)))best={axis,value:target,anchor:0,distance,source:'spacing',kind:'spacing'}}
  if(best)hits[axis]=best;
 }
 return{dx:dx+(hits.x?.distance||0),dy:dy+(hits.y?.distance||0),hits,box:{...moved,x:moved.x+(hits.x?.distance||0),y:moved.y+(hits.y?.distance||0)}};
}
const measureRoot=$('#canvasMeasurements');
let measureState=null,guideDrag=null;
const language=()=>document.documentElement.lang==='km'||document.documentElement.dataset.language==='km';
const uiText=(en,kh)=>language()?kh:en;
const guideData=()=>window.EInviteEditorBridge?.getState?.().editorModel?.guides||{x:[],y:[]};
function guidesInWorld(){const data=guideData(),result={x:[],y:[]};for(const axis of ['x','y'])result[axis]=(data[axis]||[]).map((g,i)=>typeof g==='number'?{id:`legacy-${axis}-${i}`,value:g/100*(axis==='x'?stageSize.width:stageSize.height),locked:false}:{...g});return result}
function mutateMeasurements(label,change){window.EInviteEditorBridge?.transact?.(label,doc=>{doc.editorModel={...(doc.editorModel||{})};change(doc.editorModel)},{render:false,capture:false});renderMeasurements()}
function updateGuide(axis,id,value,remove=false){const next=guidesInWorld();next[axis]=remove?next[axis].filter(g=>g.id!==id):next[axis].map(g=>g.id===id?{...g,value}:g);mutateMeasurements('Move guide / ផ្លាស់ទីបន្ទាត់ណែនាំ',model=>{model.guides=next})}
function addGuide(axis,value){const next=guidesInWorld();next[axis].push({id:crypto.randomUUID(),value,locked:false});mutateMeasurements('Add guide / បន្ថែមបន្ទាត់ណែនាំ',model=>{model.guides=next})}
function measurementLine(axis,value,kind='snap',label=''){
 if(!measureRoot)return;
 const node=document.createElement('div');node.className=`motion-line motion-${axis} motion-${kind}`;
 const position=axis==='x'?view.x+value*view.zoom:view.y+value*view.zoom;
 if(axis==='x'){node.style.left=`${position}px`;node.style.top=`${view.y}px`;node.style.height=`${stageSize.height*view.zoom}px`}else{node.style.top=`${position}px`;node.style.left=`${view.x}px`;node.style.width=`${stageSize.width*view.zoom}px`}
 if(label){const badge=document.createElement('span');badge.className='motion-distance';badge.textContent=label;node.append(badge)}measureRoot.append(node);return node;
}
const measurementPool=[];let measurementPoolUsed=0;
function measurementDynamicLine(axis,value,kind,label){
 let node=measurementPool[measurementPoolUsed];
 if(!node){node=measurementPool[measurementPoolUsed]=document.createElement('div');measureRoot.append(node)}
 measurementPoolUsed++;
 node.hidden=false;
 const className=`motion-line motion-${axis} motion-${kind}`;if(node.className!==className)node.className=className;
 const position=axis==='x'?view.x+value*view.zoom:view.y+value*view.zoom;
 if(axis==='x'){node.style.left=`${position}px`;node.style.top=`${view.y}px`;node.style.height=`${stageSize.height*view.zoom}px`;node.style.width=''}
 else{node.style.top=`${position}px`;node.style.left=`${view.x}px`;node.style.width=`${stageSize.width*view.zoom}px`;node.style.height=''}
 let badge=node.firstChild;
 if(label){if(!badge){badge=document.createElement('span');node.append(badge)}badge.className='motion-distance';if(badge.textContent!==label)badge.textContent=label}
 else if(badge)badge.remove();
}
function renderRuler(axis){
 if(!measureRoot||!$('#canvasFrame')?.classList.contains('show-rulers')||viewportSize.width<300)return;
 const ruler=document.createElement('div');ruler.className=`motion-ruler motion-ruler-${axis}`;ruler.dataset.axis=axis;ruler.setAttribute('role','group');ruler.setAttribute('aria-label',uiText('Drag to add a guide','អូសដើម្បីបន្ថែមបន្ទាត់ណែនាំ'));
 const extent=axis==='x'?stageSize.width:stageSize.height,step=[1,5,10,50,100,500,1000].find(n=>n*view.zoom>=8)||1000;
 for(let value=0,count=0;value<=extent&&count<180;value+=step,count++){const tick=document.createElement('span');tick.className='motion-ruler-tick';const pos=(axis==='x'?view.x:view.y)+value*view.zoom;tick.style[axis==='x'?'left':'top']=`${pos}px`;if(count%5===0){tick.textContent=String(value);tick.classList.add('major')}ruler.append(tick)}
 ruler.addEventListener('pointerdown',event=>{if(event.button!==0)return;beginGuideDrag(event,axis==='x'?'y':'x',null)});measureRoot.append(ruler);
}
let measurementStaticKey='';
function renderMeasurements(){
 if(!measureRoot)return;
 const model=window.EInviteEditorBridge?.getState?.().editorModel||{},guides=guidesInWorld(),show=model.guidesVisible!==false;
 const staticKey=[show?1:0,model.marginVisible?1:0,model.margin??24,view.x,view.y,view.zoom,stageSize.width,stageSize.height,viewportSize.width,$('#canvasFrame')?.classList.contains('show-rulers')?1:0,JSON.stringify(guides)].join('|');
 if(staticKey!==measurementStaticKey){
  measurementStaticKey=staticKey;measureRoot.replaceChildren();measureRoot.removeAttribute('aria-hidden');
  if(show)for(const axis of ['x','y'])for(const guide of guides[axis]){
   const line=measurementLine(axis,guide.value,'guide');line.tabIndex=0;line.setAttribute('role','slider');line.setAttribute('aria-valuenow',String(Math.round(guide.value)));line.setAttribute('aria-label',uiText('Guide position','ទីតាំងបន្ទាត់ណែនាំ'));line.classList.toggle('locked',guide.locked===true);
   line.addEventListener('pointerdown',event=>{if(!guide.locked)beginGuideDrag(event,axis,guide)});
   line.addEventListener('keydown',event=>{if(guide.locked)return;if(event.key==='Delete'||event.key==='Backspace'){event.preventDefault();updateGuide(axis,guide.id,guide.value,true)}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const direction=['ArrowLeft','ArrowUp'].includes(event.key)?-1:1;updateGuide(axis,guide.id,guide.value+direction*(event.shiftKey?10:1))}});
  }
  if(model.marginVisible){const margin=Math.max(0,Math.min(Math.min(stageSize.width,stageSize.height)/2,Number(model.margin??24)));const box=document.createElement('div');box.className='motion-margin';Object.assign(box.style,{left:`${view.x+margin*view.zoom}px`,top:`${view.y+margin*view.zoom}px`,width:`${Math.max(0,stageSize.width-2*margin)*view.zoom}px`,height:`${Math.max(0,stageSize.height-2*margin)*view.zoom}px`});measureRoot.append(box)}
  renderRuler('x');renderRuler('y');
  for(const node of measurementPool)measureRoot.append(node);
 }
 measurementPoolUsed=0;
 if(measureState){for(const hit of Object.values(measureState.hits))measurementDynamicLine(hit.axis,hit.value,'snap',hit.kind==='spacing'?uiText('Equal spacing','ចន្លោះស្មើគ្នា'):'');const box=measureState.box;measurementDynamicLine('x',box.x,'distance',`${Math.round(box.x)} px`);measurementDynamicLine('y',box.y,'distance',`${Math.round(box.y)} px`)}
 for(let index=measurementPoolUsed;index<measurementPool.length;index++)measurementPool[index].hidden=true;
}
function beginGuideDrag(event,axis,guide){
 if(event.button!==0)return;cacheViewGeometry();guideDrag={axis,guide,startX:event.clientX,startY:event.clientY,value:guide?.value??0,started:false};event.stopPropagation();
}
const guideBatcher=createFrameBatcher((a,b)=>b,event=>{
 if(!guideDrag)return;const p=clientToWorld(event.clientX,event.clientY);guideDrag.value=p[guideDrag.axis];measureState={hits:{guide:{axis:guideDrag.axis,value:guideDrag.value}},box:{x:p.x,y:p.y,w:0,h:0}};renderMeasurements();
});
window.addEventListener('pointermove',event=>{if(!guideDrag)return;if(!guideDrag.started){if(Math.abs(event.clientX-guideDrag.startX)<3&&Math.abs(event.clientY-guideDrag.startY)<3)return;guideDrag.started=true;guideDrag.transaction=window.EInviteEditorBridge?.beginUndoTransaction?.('Move guide / ផ្លាស់ទីបន្ទាត់ណែនាំ')}event.preventDefault();guideBatcher.accumulate(event)},{passive:false});
function finishGuideDrag(event,cancel=false){if(!guideDrag)return;guideBatcher.flush();const drag=guideDrag;guideDrag=null;measureState=null;if(drag.started){if(cancel)drag.transaction?.cancel();else{const r=viewRect||cacheViewGeometry(),back=drag.axis==='x'?event.clientX<r.left+24:event.clientY<r.top+24;if(drag.guide)updateGuide(drag.axis,drag.guide.id,drag.value,back);else if(!back)addGuide(drag.axis,drag.value);drag.transaction?.commit()}}renderMeasurements()}
window.addEventListener('pointerup',event=>finishGuideDrag(event));window.addEventListener('pointercancel',event=>finishGuideDrag(event,true));window.addEventListener('keydown',event=>{if(event.key==='Escape'&&guideDrag){event.preventDefault();finishGuideDrag(event,true)}},true);
const measurementSettings=document.createElement('details');measurementSettings.className='motion-measurement-settings';const summary=document.createElement('summary');summary.textContent=uiText('Precision tools','ឧបករណ៍ភាពជាក់លាក់');measurementSettings.append(summary);
function measurementControl(en,kh,type,change){const label=document.createElement('label'),input=document.createElement('input');label.append(document.createTextNode(uiText(en,kh)),input);input.type=type;input.addEventListener('change',()=>change(input));measurementSettings.append(label);return input}
const guideVisibility=measurementControl('Show guides','បង្ហាញបន្ទាត់ណែនាំ','checkbox',input=>mutateMeasurements('Show guides / បង្ហាញបន្ទាត់ណែនាំ',model=>{model.guidesVisible=input.checked}));guideVisibility.checked=true;
measurementControl('Lock guides','ចាក់សោបន្ទាត់ណែនាំ','checkbox',input=>{const next=guidesInWorld();for(const axis of ['x','y'])next[axis]=next[axis].map(g=>({...g,locked:input.checked}));mutateMeasurements('Lock guides / ចាក់សោបន្ទាត់ណែនាំ',model=>{model.guides=next})});
const marginInput=measurementControl('Safe margin (px)','រឹមសុវត្ថិភាព (px)','number',input=>mutateMeasurements('Set margin / កំណត់រឹម',model=>{model.margin=Math.max(0,Number(input.value)||0);model.marginVisible=true}));marginInput.min='0';marginInput.value='24';
$('#properties')?.append(measurementSettings);
const oldRulers=$('#rulersToggle')?.onclick;if($('#rulersToggle'))$('#rulersToggle').onclick=()=>{oldRulers?.();renderMeasurements()};
if($('#safeMarginToggle'))$('#safeMarginToggle').onclick=()=>mutateMeasurements('Show margins / បង្ហាញរឹម',model=>{model.marginVisible=!model.marginVisible;$('#safeMarginToggle').setAttribute('aria-pressed',String(model.marginVisible))});
motionAPI.snap=Object.freeze({candidates:snapCandidates,resolve:resolveSnap});
motionAPI.measurements=Object.freeze({render:renderMeasurements,show(value){measureState=value;renderMeasurements()},clear(){measureState=null;renderMeasurements()},addGuide,clearGuides(){mutateMeasurements('Clear guides / លុបបន្ទាត់ណែនាំ',model=>{model.guides={x:[],y:[]}})}});
window.addEventListener('einvite:view-changed',renderMeasurements);window.addEventListener('einvite:state-applied',renderMeasurements);window.addEventListener('einvite:editor-command',renderMeasurements);renderMeasurements();
// Gesture ownership: native plain wheel remains untouched; only ctrl/cmd zoom is captured.
let wheelActive=false,panSession=null,inertiaFrame=0,inertiaDistance=0;
function stopInertia(){if(inertiaFrame)cancelAnimationFrame(inertiaFrame);inertiaFrame=0;viewport.classList.remove('motion-inertia');scheduleImageWarmup()}
const zoomReadoutCommit=debounce(syncZoomReadout,MOTION.ZOOM_COMMIT_MS);
const wheelEnd=debounce(()=>{wheelZoomBatcher.flush();if(wheelActive){wheelActive=false;endViewGesture()}},MOTION.WHEEL_SETTLE_MS);
const wheelRearm=debounce(()=>viewport.classList.remove('motion-plain-wheel'),MOTION.WHEEL_REARM_MS);
const wheelZoomBatcher=createFrameBatcher((a,b)=>({delta:a.delta+b.delta,cx:b.cx,cy:b.cy}),value=>{
 const zoom=clampZoom(view.zoom*2**(-.01*Math.max(-25,Math.min(25,value.delta)))),world=clientToWorld(value.cx,value.cy),difference=zoom-view.zoom;
 setView({zoom,x:view.x-world.x*difference,y:view.y-world.y*difference},{source:'wheel',readout:false});zoomReadoutCommit();
});
function wheelInput(event){
 if(!(event.ctrlKey||event.metaKey)){viewport.classList.add('motion-plain-wheel');wheelRearm();return false}
 if(event.target.closest?.('input,select,textarea,[contenteditable=true]'))return false;
 if(event.cancelable)event.preventDefault();event.stopImmediatePropagation();stopInertia();
 if(!wheelActive){wheelActive=true;beginViewGesture()}
 const unit=event.deltaMode===1?40:event.deltaMode===2?800:1;
 wheelZoomBatcher.accumulate({delta:event.deltaY*unit,cx:event.clientX,cy:event.clientY});wheelEnd();return true;
}
const panBatcher=createFrameBatcher((a,b)=>b,point=>{
 if(!panSession?.started)return;
 const dx=point.x-panSession.startX,dy=point.y-panSession.startY;
 setView({x:panSession.beforeX+dx,y:panSession.beforeY+dy},{source:'pan',readout:false});
});
function panDown(event){
 const wasMoving=!!inertiaFrame;stopInertia();if(wasMoving){event.preventDefault();event.stopImmediatePropagation();return}
 if(panSession||event.target.closest?.('button,input,select,textarea,[contenteditable=true],.motion-guide,.motion-ruler'))return;
 const touch=event.pointerType==='touch',mode=window.EInviteCanvasPanController,eligible=event.button===1||event.button===0&&(mode?.held||mode?.pinned||activeTool==='hand'||touch&&!event.target.closest('.object'));
 if(!eligible)return;
 panSession={id:event.pointerId,startX:event.clientX,startY:event.clientY,beforeX:view.x,beforeY:view.y,started:false,touch,samples:[{x:event.clientX,y:event.clientY,time:event.timeStamp}]};
 if(event.button===1)event.preventDefault();event.stopImmediatePropagation();
}
function panMove(event){
 const session=panSession;if(!session||session.id!==event.pointerId)return;
 if(!session.started){if(Math.abs(event.clientX-session.startX)<3&&Math.abs(event.clientY-session.startY)<3)return;session.started=true;beginViewGesture();if(event.pointerType!=='touch')viewport.setPointerCapture?.(event.pointerId);viewport.classList.add('motion-panning')}
 event.preventDefault();event.stopImmediatePropagation();const point={x:event.clientX,y:event.clientY,time:event.timeStamp};session.samples.push(point);session.samples=session.samples.filter(p=>point.time-p.time<=100);panBatcher.accumulate(point);
}
function startInertia(session){
 if(reducedMotion.matches||!session.touch||session.samples.length<2)return;
 const a=session.samples[0],b=session.samples.at(-1),elapsed=Math.max(1,b.time-a.time);let vx=(b.x-a.x)/elapsed,vy=(b.y-a.y)/elapsed,speed=Math.hypot(vx,vy);if(speed<.05)return;if(speed>3){vx*=3/speed;vy*=3/speed}
 let last=performance.now();inertiaDistance=0;const maximum=1.5*Math.max(viewportSize.width,viewportSize.height);viewport.classList.add('motion-inertia');
 function tick(time){const dt=time-last;last=time;if(dt>32||Math.hypot(vx,vy)<.05||inertiaDistance>=maximum){stopInertia();return}const length=Math.hypot(vx,vy)*dt,ratio=Math.min(1,(maximum-inertiaDistance)/Math.max(.001,length));inertiaDistance+=length*ratio;setView({x:view.x+vx*dt*ratio,y:view.y+vy*dt*ratio},{source:'inertia',readout:false});const decay=.94**(dt/16.7);vx*=decay;vy*=decay;inertiaFrame=requestAnimationFrame(tick)}
 inertiaFrame=requestAnimationFrame(tick);
}
function panEnd(event,cancel=false){
 const session=panSession;if(!session||session.id!==event.pointerId)return;
 panBatcher.flush();panSession=null;if(viewport.hasPointerCapture?.(event.pointerId))viewport.releasePointerCapture(event.pointerId);viewport.classList.remove('motion-panning');
 if(session.started){if(cancel)setView({x:session.beforeX,y:session.beforeY},{source:'pan-cancel'});endViewGesture();if(!cancel)startInertia(session)}
}
viewport.addEventListener('wheel',wheelInput,{capture:true,passive:false});viewport.addEventListener('pointerdown',panDown,true);window.addEventListener('pointermove',panMove,{capture:true,passive:false});window.addEventListener('pointerup',event=>panEnd(event),true);window.addEventListener('pointercancel',event=>panEnd(event,true),true);
viewport.addEventListener('contextmenu',event=>{if(panSession?.started)event.preventDefault()});viewport.addEventListener('auxclick',event=>{if(event.button===1)event.preventDefault()});
window.addEventListener('keydown',event=>{if(event.key==='Escape'&&panSession){event.preventDefault();event.stopImmediatePropagation();panEnd({pointerId:panSession.id},true)}},true);
reducedMotion.addEventListener('change',()=>{stopInertia();if(reducedMotion.matches&&tweenFrame){stopTween();applyView('reduced-motion');syncZoomReadout()}});
document.addEventListener('visibilitychange',()=>{wheelEnd.flush();zoomReadoutCommit.flush();stopInertia();if(panSession)panEnd({pointerId:panSession.id},true)});
motionAPI.input=Object.freeze({wheel:wheelInput,stopInertia,get panning(){return!!panSession?.started},get inertia(){return!!inertiaFrame},edgePaging:false});
// Decode current/next-page media off the gesture path. Detached Images retain
// decoded surfaces directly; no unused ImageBitmap copies or new blob URLs.
const DECODE=Object.freeze({MAX_IMAGES:8,MAX_BYTES:24*1024*1024,CONCURRENCY:2,ROOT_MARGIN:'240px'});
const decodedImages=new Map(),decodeQueue=new Map(),decodeInFlight=new Set();
let decodeBytes=0,decodeActive=0,decodeIdle=0,decodeTimer=0,decodeFrame=0,decodeDisposed=false;
function queueImage(source,image=null){
 if(!source||decodeDisposed||decodeQueue.size>=DECODE.MAX_IMAGES)return;
 let url;try{url=new URL(source,location.href);if(!['http:','https:','blob:'].includes(url.protocol)&&!(url.protocol==='data:'&&/^data:image\//i.test(source)))return}catch{return}
 const key=url.href;if(decodedImages.has(key)){const entry=decodedImages.get(key);decodedImages.delete(key);decodedImages.set(key,entry);return}
 if(decodeInFlight.has(key))return;
 decodeQueue.set(key,image);scheduleImageWarmup();
}
function scheduleImageWarmup(){
 if(decodeDisposed||document.hidden||gestureCount||inertiaFrame||decodeIdle||decodeTimer||decodeFrame||!decodeQueue.size||decodeActive>=DECODE.CONCURRENCY)return;
 if('requestIdleCallback'in window)decodeIdle=window.requestIdleCallback(runImageWarmup,{timeout:MOTION.IDLE_MAX_MS});
 else decodeTimer=setTimeout(()=>{decodeTimer=0;decodeFrame=requestAnimationFrame(()=>{decodeFrame=0;runImageWarmup()})},MOTION.IDLE_MAX_MS);
}
function runImageWarmup(){
 decodeIdle=0;if(decodeDisposed||document.hidden)return;
 if(gestureCount||inertiaFrame)return;
 while(decodeActive<DECODE.CONCURRENCY&&decodeQueue.size){
  const [key,live]=decodeQueue.entries().next().value;decodeQueue.delete(key);
  const image=live?.isConnected&&live.currentSrc===key?live:new Image();image.decoding='async';
  if(typeof image.decode!=='function')continue;
  if(image!==live){image.fetchPriority='low';image.src=key}
  decodeActive++;decodeInFlight.add(key);
  image.decode().then(()=>{
   if(decodeDisposed)return;const bytes=image.naturalWidth*image.naturalHeight*4;
   if(perfDebug)perfTotals.decoded++;
   if(!bytes||bytes>DECODE.MAX_BYTES)return;
   while(decodedImages.size&&(decodedImages.size>=DECODE.MAX_IMAGES||decodeBytes+bytes>DECODE.MAX_BYTES)){const oldest=decodedImages.keys().next().value;decodeBytes-=decodedImages.get(oldest).bytes;decodedImages.delete(oldest)}
   decodedImages.set(key,{image,bytes});decodeBytes+=bytes;
  },()=>{if(perfDebug)perfTotals.decodeFailures++}).finally(()=>{decodeActive--;decodeInFlight.delete(key);scheduleImageWarmup()});
 }
}
const observedImages=new WeakSet();
const imageVisibility='IntersectionObserver'in window?new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting&&entry.intersectionRatio>=.9){queueImage(entry.target.currentSrc||entry.target.src,entry.target);imageVisibility.unobserve(entry.target)}},{root:viewport,rootMargin:DECODE.ROOT_MARGIN,threshold:.9}):null;
function warmPageImages(){
 if(decodeDisposed||document.hidden)return;
 for(const image of $$('img',stage)){image.decoding='async';if(!imageVisibility)queueImage(image.currentSrc||image.src,image);else if(!observedImages.has(image)){observedImages.add(image);imageVisibility.observe(image)}}
 const bridge=window.EInviteEditorBridge,doc=bridge?.getState?.();if(!doc)return;
 const pages=[{id:'hero',objects:doc.objects},...(doc.designPages||[]).filter(page=>page.enabled!==false)],active=bridge.getActiveCanvasId?.()||'hero',index=pages.findIndex(page=>(page.id==='hero'?'hero':`page:${page.id}`)===active);
 for(const page of pages.slice(Math.max(0,index),Math.max(0,index)+2)){
  const background=page.useMasterBackground&&doc.masterPageStyle?.enabled?doc.masterPageStyle:page;queueImage(background.backgroundImage);
  for(const object of Object.values(page.objects||{}).slice(0,100))if(object.type==='image')queueImage(object.src);
 }
}
const warmPageSoon=debounce(warmPageImages,MOTION.IDLE_MAX_MS);
const imageMutations=new MutationObserver(records=>{for(const record of records)if(record.type==='attributes'){imageVisibility?.unobserve(record.target);observedImages.delete(record.target)}warmPageSoon()});
imageMutations.observe(stage,{subtree:true,childList:true,attributes:true,attributeFilter:['src','srcset']});
function imageVisibilityChanged(){if(!document.hidden){warmPageSoon();scheduleImageWarmup()}else{if(decodeIdle)window.cancelIdleCallback(decodeIdle);clearTimeout(decodeTimer);if(decodeFrame)cancelAnimationFrame(decodeFrame);decodeIdle=decodeTimer=decodeFrame=0;warmPageSoon.cancel()}}
window.addEventListener('einvite:state-applied',warmPageSoon);window.addEventListener('einvite:editor-command',warmPageSoon);document.addEventListener('visibilitychange',imageVisibilityChanged);
window.EInviteLifecycle?.add?.(()=>{decodeDisposed=true;imageVisibilityChanged();if(decodeIdle)window.cancelIdleCallback(decodeIdle);clearTimeout(decodeTimer);if(decodeFrame)cancelAnimationFrame(decodeFrame);warmPageSoon.cancel();imageMutations.disconnect();imageVisibility?.disconnect();decodedImages.clear();decodeQueue.clear();decodeBytes=0;window.removeEventListener('einvite:state-applied',warmPageSoon);window.removeEventListener('einvite:editor-command',warmPageSoon);document.removeEventListener('visibilitychange',imageVisibilityChanged)});
motionAPI.images=Object.freeze({warm:warmPageImages,get cached(){return decodedImages.size},get bytes(){return decodeBytes},get pending(){return decodeQueue.size},get active(){return decodeActive}});warmPageSoon();
const selected=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
const primary=()=>selected()[0]||null;
const applyInput=(id,value,event='input')=>{const el=$('#'+id);if(!el)return;if(value!==undefined)el.value=value;el.dispatchEvent(new Event(event,{bubbles:true}))};
const click=id=>$('#'+id)?.click();
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const choose=(items)=>{try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection(items)}catch{}};
const makeId=p=>`${p}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
const currentZoom=()=>view.zoom;

const toolDefs=[['select','V','↖','Select / Move'],['text','T','T','Text'],['frame','Shift+B','▣','Photo frame'],['rect','R','□','Rectangle'],['ellipse','O','○','Ellipse'],['line','L','╱','Line'],['hand','H','✋','Hand / Pan'],['zoom','Z','⌕','Zoom']];
const rail=document.createElement('nav');rail.className='ei-tool-rail';rail.setAttribute('aria-label','Design tools');
toolDefs.forEach(([id,key,icon,label],i)=>{if(i===6){const sep=document.createElement('div');sep.className='sep';rail.append(sep)}const b=document.createElement('button');b.type='button';b.dataset.tool=id;b.title=`${label} (${key})`;b.setAttribute('aria-label',label);b.innerHTML=`${icon}<span>${key}</span>`;rail.append(b)});viewport.prepend(rail);
let activeTool=localStorage.getItem('einvite-active-tool')||'select';
function setTool(tool,{announce=true}={}){if(!toolDefs.some(x=>x[0]===tool))tool='select';activeTool=tool;localStorage.setItem('einvite-active-tool',tool);document.body.dataset.activeTool=tool;$$('[data-tool]',rail).forEach(b=>b.classList.toggle('active',b.dataset.tool===tool));viewport.classList.toggle('ei-tool-crosshair',['text','frame','rect','ellipse','line'].includes(tool));viewport.classList.toggle('ei-tool-zoom',tool==='zoom');viewport.classList.toggle('ei-tool-hand',tool==='hand');if(tool==='hand'&&$('#panToggle')?.getAttribute('aria-pressed')!=='true')$('#panToggle')?.click();if(tool!=='hand'&&$('#panToggle')?.getAttribute('aria-pressed')==='true')$('#panToggle')?.click();if(announce&&window.uiToast)uiToast(`${toolDefs.find(x=>x[0]===tool)?.[3]||tool} tool`,'⌘')}
rail.addEventListener('click',e=>{const b=e.target.closest('[data-tool]');if(b)setTool(b.dataset.tool)});setTool(activeTool,{announce:false});
window.EInviteToolController=Object.freeze({version:'23.0.0',setTool,get activeTool(){return activeTool},tools:toolDefs.map(item=>item[0])});
function canvasPoint(e){cacheViewGeometry();const p=clientToWorld(e.clientX,e.clientY);return{x:Math.max(0,Math.min(98,p.x/stageSize.width*100)),y:Math.max(0,Math.min(98,p.y/stageSize.height*100))}}
function createTextAt(point){if(typeof createObject!=='function')return;const o=createObject(makeId('text'),'text');o.style.left=`${Math.min(72,point.x)}%`;o.style.top=`${Math.min(90,point.y)}%`;o.style.width='40%';o.style.height='90px';o.dataset.fontSize='32';o.dataset.layerName='Text';o.querySelector('.content').textContent='Type your text';stage.append(o);choose([o]);saveNow();setTimeout(()=>{const c=o.querySelector('.content');c.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));},50)}
function createShapeAt(kind,point){if(typeof createObject!=='function')return;const o=createObject(makeId(kind), 'shape');o.dataset.shapeKind=kind==='ellipse'?'circle':kind;o.dataset.layerName=kind==='ellipse'?'Ellipse':kind[0].toUpperCase()+kind.slice(1);o.dataset.fillColor=$('#accent')?.value||'#9d4555';if(kind==='line'){o.style.width='34%';o.style.height='8px'}else{o.style.width='28%';o.style.height=kind==='ellipse'?'150px':'130px'}o.style.left=`${Math.min(80,point.x)}%`;o.style.top=`${Math.min(90,point.y)}%`;if(kind==='ellipse')o.dataset.borderRadius='120';stage.append(o);try{applyObjectVisualStyle(o)}catch{}choose([o]);saveNow()}
const frameSvg=`data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#eceef5"/><stop offset="1" stop-color="#d7dae5"/></linearGradient></defs><rect width="800" height="600" rx="30" fill="url(#g)"/><path d="M210 390l120-125 90 92 70-67 110 100" fill="none" stroke="#9499a9" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/><circle cx="560" cy="180" r="55" fill="#b9bdca"/></svg>`)}`;
function createFrameAt(point){if(typeof createObject!=='function')return;const o=createObject(makeId('frame'),'image');o.style.left=`${Math.min(70,point.x)}%`;o.style.top=`${Math.min(82,point.y)}%`;o.style.width='42%';o.style.height='260px';o.dataset.layerName='Photo frame';o.dataset.showInGallery='false';o.dataset.originalSrc='';o.dataset.framePlaceholder='true';o.classList.add('ei-frame-placeholder');const img=o.querySelector('img');img.src=frameSvg;img.alt='Empty photo frame';stage.append(o);choose([o]);saveNow()}
stage.addEventListener('pointerdown',e=>{if(activeTool==='select'||activeTool==='hand')return;if(e.target.closest('.object,.selection-bounds,.safe-margin-overlay'))return;if(e.button!==0)return;if(activeTool==='zoom'){e.preventDefault();const zoom=currentZoom();setZoomModel(zoom*1.25,{cursor:{x:e.clientX,y:e.clientY},source:'tool'});return}const point=canvasPoint(e);e.preventDefault();e.stopImmediatePropagation();if(activeTool==='text')createTextAt(point);else if(activeTool==='frame')createFrameAt(point);else if(activeTool==='rect')createShapeAt('rectangle',point);else if(activeTool==='ellipse')createShapeAt('ellipse',point);else if(activeTool==='line')createShapeAt('line',point)},true);
stage.addEventListener('dblclick',e=>{const frame=e.target.closest('.ei-frame-placeholder');if(!frame)return;if(typeof openMaterialPicker!=='function')return;openMaterialPicker('Choose photo for frame',(url,asset)=>{frame.classList.remove('ei-frame-placeholder');frame.dataset.framePlaceholder='false';frame.dataset.originalSrc=frame.querySelector('img')?.src||'';frame.dataset.src=url;const img=frame.querySelector('img');if(img){img.src=url;img.alt=asset?.name||'Invitation photo'}saveNow()})},true);

const context=document.createElement('div');context.className='ei-context-toolbar';toolbar.insertBefore(context,$('#activeCanvasLabel'));
const divider=()=>'<span class="divider"></span>';
function valueOf(id,fallback=''){return $('#'+id)?.value??fallback}
function selectOptions(id){return $('#'+id)?.innerHTML||''}
function renderContext(){const items=selected(),o=items[0];context.innerHTML='';if(!items.length){context.classList.add('visible');context.innerHTML=`<span class="ei-context-name">No selection</span>${divider()}<button type="button" data-action="design">Design</button><button type="button" data-action="page-motion">Animate page</button><button type="button" data-action="check">Design check</button>`;wireContext();return}context.classList.add('visible');const type=o.dataset.objectType||'text',name=o.dataset.layerName||o.querySelector('.content')?.textContent?.trim()?.slice(0,30)||type,safeName=escapeMarkup(name);let html=`<span class="ei-context-name" title="${safeName}">${items.length>1?`${items.length} selected`:safeName}</span>${divider()}`;
 if(items.length>1){html+=`<div class="group"><button data-action="group">Group</button><button data-action="ungroup">Ungroup</button><button data-action="align">Align</button><button data-action="tidy">Tidy</button></div>`}
 else if(type==='text'||type==='decoration'){html+=`<div class="group"><select data-ctx="font" title="Font">${selectOptions('font')}</select><input data-ctx="fontSize" type="number" min="8" max="200" value="${o.dataset.fontSize||32}" title="Font size"><input data-ctx="color" type="color" value="${o.dataset.color||'#342c26'}" title="Text color"><button class="icon-button ${o.dataset.fontWeight==='700'?'active':''}" data-action="bold"><b>B</b></button><button class="icon-button ${o.dataset.fontStyle==='italic'?'active':''}" data-action="italic"><i>I</i></button><button class="icon-button" data-action="alignText" title="Text alignment">≡</button></div>${divider()}<div class="group"><button data-action="effects">Effects</button><button data-action="animate">Animate</button></div>`}
 else if(type==='image'){html+=`<div class="group"><button data-action="replace">Replace</button><button data-action="removeBg">Remove BG</button><button data-action="crop">Crop</button><button class="icon-button" data-action="flipX">↔</button><button class="icon-button" data-action="flipY">↕</button></div>${divider()}<div class="group"><button data-action="position">Position</button><button data-action="animate">Animate</button></div>`}
 else if(type==='shape'){html+=`<div class="group"><input data-ctx="fill" type="color" value="${o.dataset.fillColor||'#9d4555'}" title="Fill"><input data-ctx="border" type="color" value="${o.dataset.borderColor||'#ffffff'}" title="Border"><button data-action="position">Position</button><button data-action="animate">Animate</button></div>`}
 context.innerHTML=html;const font=context.querySelector('[data-ctx=font]');if(font)font.value=o.dataset.font||valueOf('font');wireContext()}
function openInspector(target){document.querySelector('[data-inspector-tab="object"]')?.click();setTimeout(()=>$(target)?.scrollIntoView({behavior:'smooth',block:'nearest'}),60)}
function wireContext(){context.querySelector('[data-ctx=font]')?.addEventListener('change',e=>applyInput('font',e.target.value,'change'));context.querySelector('[data-ctx=fontSize]')?.addEventListener('change',e=>applyInput('fontSize',e.target.value));context.querySelector('[data-ctx=color]')?.addEventListener('input',e=>applyInput('color',e.target.value));context.querySelector('[data-ctx=fill]')?.addEventListener('input',e=>applyInput('fillColor',e.target.value));context.querySelector('[data-ctx=border]')?.addEventListener('input',e=>applyInput('borderColor',e.target.value));context.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>{const a=b.dataset.action,o=primary();if(a==='bold')click('fontBold');if(a==='italic')click('fontItalic');if(a==='alignText'){const modes=['left','center','right'],next=modes[(modes.indexOf(o?.dataset.textAlign||'center')+1)%modes.length];applyInput('textAlign',next,'change')}if(a==='editText')o?.querySelector('.content')?.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));if(a==='effects')openInspector('#finalTextTransform');if(a==='animate')openInspector('#animation');if(a==='crop')openInspector('#cropPreview');if(a==='replace')click('aiReplaceImage');if(a==='removeBg')click('aiBgCut');if(a==='flipX')click('aiFlipX');if(a==='flipY')click('aiFlipY');if(a==='position')openInspector('#canvasPlusTransform');if(a==='group')click('groupObjects');if(a==='ungroup')click('ungroupObjects');if(a==='tidy')click('studioTidy');if(a==='align')openInspector('.alignment-grid');if(a==='design')document.querySelector('[data-inspector-tab="design"]')?.click();if(a==='page-motion')openInspector('#sectionAnimationsManager');if(a==='check')click('studioDesignCheck')})}
const selectionObserver=new MutationObserver(()=>renderContext());selectionObserver.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','data-font-size','data-color','data-fill-color','data-font-weight','data-font-style']});document.addEventListener('pointerup',()=>setTimeout(renderContext,0),true);renderContext();

})();
