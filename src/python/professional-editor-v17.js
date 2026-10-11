(() => {
'use strict';
if (window.EInviteProfessionalEditor?.version >= 17) return;
const bridge = () => window.EInviteEditorBridge;
const stage = document.querySelector('#stage');
if (!stage || !bridge()) return;
const viewport = document.querySelector('#canvasViewport');
const $ = (s,r=document) => r.querySelector(s);
const $$ = (s,r=document) => [...r.querySelectorAll(s)];
const clone = value => window.EInviteEditorSchema?.clone?.(value) ?? JSON.parse(JSON.stringify(value));
const clamp = (v,min,max) => Math.min(max,Math.max(min,Number.isFinite(v)?v:min));
const finite = (v,fallback=0) => Number.isFinite(Number(v)) ? Number(v) : fallback;
const uid = prefix => `${prefix}-${crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
const CLIPBOARD = 'einvite-professional-clipboard-v18';
const CLIPBOARD_VERSION = 18;
const CLIPBOARD_MAX_OBJECTS = 200;
const CLIPBOARD_MAX_BYTES = 1024 * 1024;
const CLIPBOARD_ALLOWED_TYPES = new Set(['text','image','shape','decoration','button','video','audio','map','qr','date','rsvp','gallery']);
const SETTINGS = 'einvite-professional-layout-v17';
const MIN_SIZE = 8;
const expandedGroups = new Set();
let selectedGroupId = '';
let memoryClipboard = null;
let overlay, marquee, interaction = null, layersRendering = false;
let layerDragState = null;
let layerAnnouncement = '';
let layerFocusIdentity = null;
let layerFocusTimer = 0;
let settings = readSettings();
let selectionUndoStack = [], selectionRedoStack = [], lastDocumentCommitAt = 0, lastSelectionUndoAt = 0;
let commandSequence = 0, lastCommand = null;
let overlaySyncFrame=0,overlaySyncFull=false,overlaySyncLifecycle=null,overlayResizeObserver=null,lastRevealAdjustAt=0;
function readSettings(){
try { return {grid:false,rulers:false,snap:true,guides:true,gridSize:20,...JSON.parse(localStorage.getItem(SETTINGS)||'{}')}; }
catch { return {grid:false,rulers:false,snap:true,guides:true,gridSize:20}; }
}
function saveSettings(){ try{localStorage.setItem(SETTINGS,JSON.stringify(settings))}catch{} applyAssistanceState(); }
function activeMap(doc=bridge().getState()){
const canvas=bridge().getActiveCanvasId();
if(canvas==='hero') return doc.objects||(doc.objects={});
const page=(doc.designPages||[]).find(p=>`page:${p.id}`===canvas);
return page ? (page.objects||(page.objects={})) : (doc.objects||(doc.objects={}));
}
function groups(doc=bridge().getState()){
doc.sceneGraph=doc.sceneGraph||{};
return doc.sceneGraph.groups||(doc.sceneGraph.groups={});
}
function activeObjects(){ return $$('.object',stage).filter(el=>el.dataset.visible!=='false' && getComputedStyle(el).display!=='none'); }
function allObjectElements(){ return $$('.object',stage); }
function selectedIds(){ return bridge().getSelectedIds().filter(id=>stage.querySelector(`.object[data-id="${CSS.escape(id)}"]`)); }
function selectedElements(){ const wanted=new Set(selectedIds()); return allObjectElements().filter(el=>wanted.has(el.dataset.id)); }
function isLocked(id){ return stage.querySelector(`.object[data-id="${CSS.escape(id)}"]`)?.dataset.locked==='true'; }
function px(value,total,fallback=0){
const text=String(value??'').trim(); const n=parseFloat(text);
if(!Number.isFinite(n)) return fallback;
return text.endsWith('%') ? n/100*total : n;
}
function pct(value,total,bounded=true){ const n=value/Math.max(1,total)*100,resolved=bounded?clamp(n,0,100):finite(n);return `${resolved.toFixed(4).replace(/0+$/,'').replace(/\.$/,'')}%`; }
function frameOf(el,sr=stage.getBoundingClientRect()){
const style=el.style, rect=el.getBoundingClientRect();
const w=clamp(px(style.width,sr.width,el.offsetWidth||rect.width),MIN_SIZE,sr.width);
const h=clamp(px(style.height,sr.height,el.offsetHeight||rect.height),MIN_SIZE,sr.height);
return {
id:el.dataset.id,
x:finite(px(style.left,sr.width,el.offsetLeft)),
y:finite(px(style.top,sr.height,el.offsetTop)),
w,h,r:finite(el.dataset.rotation,0)
};
}
function visibleRect(el,sr=stage.getBoundingClientRect()){
const r=el.getBoundingClientRect();
return {x:r.left-sr.left,y:r.top-sr.top,w:r.width,h:r.height,right:r.right-sr.left,bottom:r.bottom-sr.top};
}
function bbox(frames){
if(!frames.length) return {x:0,y:0,w:0,h:0,right:0,bottom:0};
const x=Math.min(...frames.map(f=>f.x)),y=Math.min(...frames.map(f=>f.y));
const right=Math.max(...frames.map(f=>f.x+f.w)),bottom=Math.max(...frames.map(f=>f.y+f.h));
return {x,y,w:right-x,h:bottom-y,right,bottom};
}
function visibleBBox(elements,sr=stage.getBoundingClientRect()){
const frames=elements.map(el=>visibleRect(el,sr));
return bbox(frames);
}
function safeFrame(frame,sr){
const w=clamp(finite(frame.w,MIN_SIZE),MIN_SIZE,sr.width);
const h=clamp(finite(frame.h,MIN_SIZE),MIN_SIZE,sr.height);
return {id:String(frame.id),x:finite(frame.x),y:finite(frame.y),w,h,r:clamp(finite(frame.r),-36000,36000)};
}
function previewFrames(frames,sr=stage.getBoundingClientRect(),mode='layout'){
if(interaction)interaction.previewFrames=frames.map(raw=>safeFrame(raw,sr));
frames.forEach(raw=>{
const f=safeFrame(raw,sr), el=stage.querySelector(`.object[data-id="${CSS.escape(f.id)}"]`); if(!el)return;
const base=interaction?.frames?.find(item=>item.id===f.id);
if(mode==='compositor'&&base){el.dataset.peTransformPreview='true';el.style.willChange='transform';el.style.transform=`translate3d(${f.x-base.x}px,${f.y-base.y}px,0) rotate(${f.r}deg)`}
else{el.style.left=pct(f.x,sr.width,false);el.style.top=pct(f.y,sr.height,false);el.style.width=pct(f.w,sr.width);el.style.height=pct(f.h,sr.height);el.style.transform=`rotate(${f.r}deg)`}
el.dataset.rotation=String(Math.round(f.r*100)/100);
});
syncOverlay(); syncTransformInputs();
}
function clearInteractionPreview(value,restore=true){for(const frame of value?.frames||[]){const el=stage.querySelector(`.object[data-id="${CSS.escape(frame.id)}"]`);if(!el)continue;delete el.dataset.peTransformPreview;el.style.willChange='';if(restore){el.style.left=pct(frame.x,value.sr.width,false);el.style.top=pct(frame.y,value.sr.height,false);el.style.width=pct(frame.w,value.sr.width);el.style.height=pct(frame.h,value.sr.height);el.dataset.rotation=String(frame.r);el.style.transform=`rotate(${frame.r}deg)`}}}
function commit(label, mutator, nextSelection=selectedIds(), renderOptions={}){
lastDocumentCommitAt=performance.now();selectionRedoStack=[];
const ids=[...new Set(nextSelection.map(String))];
const inspectorTab=document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab||'';
const restoreInspector=!matchMedia('(max-width:600px)').matches||document.body.classList.contains('mobile-inspector-open');
bridge().transact(label,doc=>{
mutator(activeMap(doc),doc);
const map=activeMap(doc);
Object.entries(map).forEach(([id,o],index)=>{
o.zIndex=Math.max(1,finite(o.zIndex,index+1)); o.visible=o.visible!==false; o.locked=o.locked===true;
o.left=validPosition(o.left,'0%'); o.top=validPosition(o.top,'0%'); o.width=validSize(o.width,'10%'); o.height=validSize(o.height,'10%');
o.rotation=finite(o.rotation,0);
});
doc.editorModel={...(doc.editorModel||{}),professionalTransformVersion:1};
delete doc.editorModel.selectionIds;
assertValidDocument(doc);
},renderOptions.incremental===true?{incremental:true,patch:{type:renderOptions.patchType||'TRANSFORM_ONLY',ids:[...ids]}}:{});
commandSequence+=1;lastCommand={sequence:commandSequence,label:String(label||'Edit'),selection:[...ids],committedAt:Date.now()};
window.dispatchEvent(new CustomEvent('einvite:professional-command-committed',{detail:clone(lastCommand)}));
bridge().select(ids);syncAll();
requestAnimationFrame(()=>{ if(restoreInspector&&inspectorTab)document.querySelector(`[data-inspector-tab="${CSS.escape(inspectorTab)}"]`)?.click(); syncAll(); });
}
function validPosition(value,fallback){ const n=parseFloat(value); return Number.isFinite(n)?String(value):fallback; }
function validSize(value,fallback){ const n=parseFloat(value); return Number.isFinite(n)&&n>0?String(value):fallback; }
function assertValidDocument(doc){
const map=activeMap(doc),gs=groups(doc);
for(const [id,o] of Object.entries(map)){
for(const key of ['left','top'])if(!Number.isFinite(parseFloat(o[key])))throw new Error(`Invalid ${key} for ${id}`);
for(const key of ['width','height'])if(!Number.isFinite(parseFloat(o[key]))||parseFloat(o[key])<=0)throw new Error(`Invalid ${key} for ${id}`);
if(!Number.isFinite(Number(o.rotation))||!Number.isFinite(Number(o.zIndex)))throw new Error(`Invalid transform for ${id}`);
}
for(const [gid,g] of Object.entries(gs)){
const seen=new Set([gid]);let parent=g.parentId||'',guard=0;while(parent&&gs[parent]&&guard++<100){if(seen.has(parent))throw new Error(`Group cycle at ${gid}`);seen.add(parent);parent=gs[parent].parentId||''}
for(const child of g.children||[])if(!map[child]&&!gs[child])throw new Error(`Missing group child ${child}`);
}
if(window.EInviteEditorSchema?.buildSceneGraph&&window.EInviteEditorSchema?.validate){const projected={...doc,sceneGraph:window.EInviteEditorSchema.buildSceneGraph(doc)},result=window.EInviteEditorSchema.validate(projected);if(!result.ok)throw new Error(result.error||'Invalid scene graph')}
}
function commitFrames(label,frames,nextSelection=frames.map(f=>f.id)){
const sr=stage.getBoundingClientRect(), safe=frames.map(f=>safeFrame(f,sr));
commit(label,map=>safe.forEach(f=>{const o=map[f.id];if(!o)return;o.left=pct(f.x,sr.width,false);o.top=pct(f.y,sr.height,false);o.width=pct(f.w,sr.width);o.height=pct(f.h,sr.height);o.rotation=Math.round(f.r*100)/100;}),nextSelection,{incremental:true,patchType:'TRANSFORM_ONLY'});
}
function revealSelection(){
const v=$('#canvasViewport'),b=overlay;if(!v||!b||b.hidden)return;
const adjust=()=>{if(interaction||b.hidden)return;const now=Date.now();if(now-lastRevealAdjustAt<200)return;const r=v.getBoundingClientRect(),q=b.getBoundingClientRect(),m=48,w=window.visualViewport,l=Math.max(r.left,w?.offsetLeft||0),t=Math.max(r.top,w?.offsetTop||0),rr=Math.min(r.right,(w?.offsetLeft||0)+(w?.width||innerWidth)),bb=Math.min(r.bottom,(w?.offsetTop||0)+(w?.height||innerHeight));let x=0,y=0;if(q.left<l+m)x=q.left-l-m;else if(q.right>rr-m)x=q.right-rr+m;if(q.top<t+m)y=q.top-t-m;else if(q.bottom>bb-m)y=q.bottom-bb+m;if(x||y){lastRevealAdjustAt=now;v.scrollBy(x,y);scheduleOverlaySync()}};
adjust();setTimeout(adjust,0);setTimeout(adjust,120);
}
function sameIds(a,b){return a.length===b.length&&a.every((id,index)=>id===b[index])}
function sameIdSet(a,b){return a.length===b.length&&a.every(id=>b.includes(id))}
function overlaySelectionIds(){
try{return JSON.parse(ensureOverlay().dataset.peSelectionIds||'[]').map(String).filter(id=>stage.querySelector(`.object[data-id="${CSS.escape(id)}"]`))}
catch{return[]}
}
function holdInteractionSelection(value=interaction){
if(!value||value.type==='marquee')return false;
const current=selectedIds();if(sameIdSet(current,value.ids))return false;
bridge().select([...value.ids]);return true;
}
function setSelection(ids,{canvas=true,history=true}={}){
const before=selectedIds();let next=[...new Set(ids.map(String))];
if(canvas) next=expandCanvasGroups(next).filter(id=>!isLocked(id));
selectedGroupId='';
if(history&&!sameIds(before,next)){selectionUndoStack.push({before:[...before],after:[...next],at:performance.now()});if(selectionUndoStack.length>80)selectionUndoStack.shift();selectionRedoStack=[]}
bridge().select(next); syncAll();revealSelection();
}
function clearSelection(options){ setSelection([],{canvas:false,...(options||{})}); }
function undoSelection(){const entry=selectionUndoStack.at(-1);if(!entry||entry.at<lastDocumentCommitAt)return false;selectionUndoStack.pop();selectionRedoStack.push(entry);lastSelectionUndoAt=performance.now();setSelection(entry.before,{canvas:false,history:false});return true}
function redoSelection(){const entry=selectionRedoStack.at(-1);if(!entry||lastSelectionUndoAt<lastDocumentCommitAt)return false;selectionRedoStack.pop();selectionUndoStack.push(entry);setSelection(entry.after,{canvas:false,history:false});return true}
function groupAncestors(groupId,gs=groups()){ const out=[];let id=groupId,guard=0;while(id&&gs[id]&&guard++<50){out.push(id);id=gs[id].parentId||''}return out; }
function descendantIds(groupId,gs=groups(),seen=new Set()){
if(!groupId||seen.has(groupId))return[];seen.add(groupId);const group=gs[groupId];if(!group)return[];
return [...new Set((group.children||[]).flatMap(child=>gs[child]?descendantIds(child,gs,seen):[String(child)]))];
}
function topGroupForObject(id,doc=bridge().getState()){
const o=activeMap(doc)[id]; if(!o?.groupId)return''; const chain=groupAncestors(o.groupId,groups(doc));return chain.at(-1)||o.groupId;
}
function expandCanvasGroups(ids){ const gs=groups();return [...new Set(ids.flatMap(id=>{const gid=topGroupForObject(id);return gid?descendantIds(gid,gs):[id]}))]; }
function toggleSelection(ids){ const current=new Set(selectedIds()), expanded=expandCanvasGroups(ids);const remove=expanded.every(id=>current.has(id));expanded.forEach(id=>remove?current.delete(id):current.add(id));setSelection([...current]); }
function ensureOverlay(){
if(overlay?.isConnected)return overlay;
overlay=document.createElement('div');overlay.id='peSelectionBox';overlay.className='pe-selection-box';overlay.hidden=true;overlay.innerHTML=`<span class="pe-selection-label"></span>${['nw','n','ne','e','se','s','sw','w'].map(h=>`<button type="button" class="pe-handle pe-${h}" data-pe-handle="${h}" aria-label="Resize ${h}"></button>`).join('')}<button type="button" class="pe-rotate" data-pe-handle="rotate" aria-label="Rotate selection"></button>`;document.body.append(overlay);overlay.addEventListener('pointerdown',pointerDown,true);overlay.addEventListener('pointermove',pointerMove,true);overlay.addEventListener('pointerup',pointerUp,true);overlay.addEventListener('pointercancel',pointerUp,true);return overlay;
}
function syncOverlay(){
const box=ensureOverlay(),items=selectedElements(); if(!items.length){box.hidden=true;delete box.dataset.peSelectionIds;return}
box.dataset.peSelectionIds=JSON.stringify(items.map(item=>item.dataset.id));
const sr=stage.getBoundingClientRect(),live=interaction?.type==='move'&&interaction.previewFrames?.length?interaction.previewFrames:null;box.hidden=false;
if(live&&interaction.overlayStart){const first=interaction.frames[0],current=live.find(frame=>frame.id===first?.id),scaleX=sr.width/Math.max(1,stage.offsetWidth),scaleY=sr.height/Math.max(1,stage.offsetHeight),dx=(current&&first?current.x-first.x:0)*scaleX+(sr.left-interaction.sr.left),dy=(current&&first?current.y-first.y:0)*scaleY+(sr.top-interaction.sr.top),start=interaction.overlayStart;Object.assign(box.style,{left:`${start.left+dx}px`,top:`${start.top+dy}px`,width:`${start.width}px`,height:`${start.height}px`,transform:start.transform});box.classList.toggle('pe-tiny-selection',start.width<56||start.height<56);}
else if(items.length===1){const f=frameOf(items[0],sr);Object.assign(box.style,{left:`${sr.left+f.x}px`,top:`${sr.top+f.y}px`,width:`${f.w}px`,height:`${f.h}px`,transform:`rotate(${f.r}deg)`});box.classList.toggle('pe-tiny-selection',f.w<56||f.h<56);}
else {const b=visibleBBox(items,sr);Object.assign(box.style,{left:`${sr.left+b.x}px`,top:`${sr.top+b.y}px`,width:`${b.w}px`,height:`${b.h}px`,transform:'none'});box.classList.toggle('pe-tiny-selection',b.w<56||b.h<56);}
$('.pe-selection-label',box).textContent=items.length>1?`${items.length} objects`:items[0].dataset.layerName||items[0].dataset.objectType||'Object';
if(!interaction)revealSelection();
}
function ensureTransformPanel(){
const properties=$('#properties');if(!properties||$('#peTransformPanel'))return;
const panel=document.createElement('section');panel.id='peTransformPanel';panel.className='pe-transform-panel';panel.innerHTML=`<h2>Transform</h2><div class="pe-transform-grid"><label>X <input data-pe-transform="x" type="number" step="1"></label><label>Y <input data-pe-transform="y" type="number" step="1"></label><label>W <input data-pe-transform="w" type="number" step="1" min="1"></label><label>H <input data-pe-transform="h" type="number" step="1" min="1"></label><label>Rotation <input data-pe-transform="r" type="number" step="1"></label></div>`;
properties.querySelector('.selection-summary')?.insertAdjacentElement('afterend',panel);
panel.addEventListener('change',event=>{const input=event.target.closest('[data-pe-transform]');if(!input)return;applyNumericTransform(input.dataset.peTransform,finite(input.value));});
}
function ensureMobileContextBar(){
let bar=$('#peMobileContextBar');if(bar)return bar;
bar=document.createElement('div');bar.id='peMobileContextBar';bar.className='pe-mobile-context';bar.hidden=true;bar.setAttribute('role','toolbar');bar.setAttribute('aria-label','Selected object actions');
bar.innerHTML='<strong data-pe-mobile-label>Object</strong><button type="button" data-pe-mobile-action="edit">Quick Edit</button><button type="button" data-pe-mobile-action="duplicate">Duplicate</button><button type="button" data-pe-mobile-action="delete">Delete</button>';
document.body.append(bar);
bar.addEventListener('click',event=>{
const action=event.target.closest('[data-pe-mobile-action]')?.dataset.peMobileAction;if(!action)return;
if(action==='edit'){$('#mobileQuickMode')?.click();setTimeout(syncMobileContextBar,0)}
else if(action==='duplicate')duplicateSelection();
else if(action==='delete')deleteSelection();
});
return bar;
}
function syncMobileContextBar(){
const bar=ensureMobileContextBar(),ids=selectedIds(),mobile=matchMedia('(max-width:600px)').matches;
const drawerOpen=document.body.classList.contains('mobile-inspector-open')||document.body.classList.contains('mobile-creation-open')||document.body.classList.contains('mobile-advanced-open');
const visible=mobile&&ids.length>0&&!drawerOpen;
bar.hidden=!visible;bar.setAttribute('aria-hidden',String(!visible));
if(visible){const items=selectedElements();const label=items.length>1?`${items.length} objects`:(items[0]?.dataset.layerName||items[0]?.dataset.objectType||'Object');$('[data-pe-mobile-label]',bar).textContent=label;}
}
function syncTransformInputs(){
const panel=$('#peTransformPanel');if(!panel)return;const items=selectedElements();if(!items.length)return;
const sr=stage.getBoundingClientRect();let f;if(items.length===1)f=frameOf(items[0],sr);else{const b=visibleBBox(items,sr);f={...b,r:0}};
for(const key of ['x','y','w','h','r']){const input=$(`[data-pe-transform="${key}"]`,panel);if(input&&document.activeElement!==input)input.value=String(Math.round(f[key]*10)/10)}
}
function applyNumericTransform(key,value){
const items=selectedElements().filter(el=>el.dataset.locked!=='true');if(!items.length)return;
const sr=stage.getBoundingClientRect(),frames=items.map(el=>frameOf(el,sr)),old=bbox(frames);let next={...old};
if(key==='x')next.x=value;if(key==='y')next.y=value;if(key==='w')next.w=Math.max(MIN_SIZE,value);if(key==='h')next.h=Math.max(MIN_SIZE,value);
if(key==='r'&&items.length===1){frames[0].r=value;return commitFrames('Set rotation',frames)}
next.w=clamp(next.w,MIN_SIZE,sr.width);next.h=clamp(next.h,MIN_SIZE,sr.height);
const sx=next.w/Math.max(1,old.w),sy=next.h/Math.max(1,old.h);const transformed=frames.map(f=>({...f,x:next.x+(f.x-old.x)*sx,y:next.y+(f.y-old.y)*sy,w:f.w*sx,h:f.h*sy}));commitFrames('Set transform',transformed);
}
function ensureAssistancePanel(){
if($('#peLayoutAssistance'))return;
const panel=document.createElement('section');panel.id='peLayoutAssistance';panel.className='pe-layout-assistance';panel.innerHTML=`<h2>Layout assistance</h2><div class="pe-toggle-grid"><button type="button" data-pe-toggle="grid" aria-pressed="false">Grid</button><button type="button" data-pe-toggle="rulers" aria-pressed="false">Rulers</button><button type="button" data-pe-toggle="snap" aria-pressed="true">Snap</button><button type="button" data-pe-toggle="guides" aria-pressed="true">Guides</button></div><div class="pe-guide-actions"><button type="button" data-pe-guide="x">+ Vertical guide</button><button type="button" data-pe-guide="y">+ Horizontal guide</button><button type="button" data-pe-guide="clear">Clear guides</button></div><div class="pe-align-grid">${[['left','Left'],['center','Center'],['right','Right'],['top','Top'],['middle','Middle'],['bottom','Bottom']].map(([v,l])=>`<button type="button" data-pe-align="${v}">${l}</button>`).join('')}<button type="button" data-pe-distribute="horizontal">Distribute H</button><button type="button" data-pe-distribute="vertical">Distribute V</button></div>`;
const layers=$('#layersPanel');layers?.insertAdjacentElement('beforebegin',panel);
panel.addEventListener('click',event=>{
const toggle=event.target.closest('[data-pe-toggle]');if(toggle){settings[toggle.dataset.peToggle]=!settings[toggle.dataset.peToggle];saveSettings();return}
const guide=event.target.closest('[data-pe-guide]');if(guide){manageGuide(guide.dataset.peGuide);return}
const align=event.target.closest('[data-pe-align]');if(align){alignSelection(align.dataset.peAlign);return}
const distribute=event.target.closest('[data-pe-distribute]');if(distribute)distributeSelection(distribute.dataset.peDistribute);
});applyAssistanceState();
}
function applyAssistanceState(){
stage.classList.toggle('pe-grid-enabled',!!settings.grid);$('#canvasFrame')?.classList.toggle('show-rulers',!!settings.rulers);
$$('[data-pe-toggle]').forEach(b=>b.setAttribute('aria-pressed',String(!!settings[b.dataset.peToggle])));renderUserGuides();
}
function manageGuide(axis){
const doc=bridge().getState();doc.editorModel=doc.editorModel||{};const current=clone(doc.editorModel.guides||{x:[],y:[]});
if(axis==='clear'){current.x=[];current.y=[]}
else {const raw=prompt(`Guide position in percent (0–100):`,'50');if(raw===null)return;const n=clamp(parseFloat(raw),0,100);current[axis]=[...new Set([...(current[axis]||[]),n])].sort((a,b)=>a-b)}
commit('Update guides',(map,nextDoc)=>{nextDoc.editorModel={...(nextDoc.editorModel||{}),guides:current}},selectedIds());
}
function renderUserGuides(){
$$('.pe-user-guide',stage).forEach(el=>el.remove());if(!settings.guides)return;
const guideData=bridge().getState().editorModel?.guides||{x:[],y:[]};
(guideData.x||[]).forEach(v=>{const el=document.createElement('div');el.className='pe-user-guide pe-vertical';el.style.left=`${v}%`;stage.append(el)});
(guideData.y||[]).forEach(v=>{const el=document.createElement('div');el.className='pe-user-guide pe-horizontal';el.style.top=`${v}%`;stage.append(el)});
}
function clearSmartGuides(){ $$('.pe-smart-guide,.pe-measurement',stage).forEach(el=>el.remove()); }
function smartGuide(axis,position,label=''){
const el=document.createElement('div');el.className=`pe-smart-guide pe-${axis}`;if(axis==='vertical')el.style.left=`${position}px`;else el.style.top=`${position}px`;stage.append(el);
if(label){const tag=document.createElement('span');tag.className='pe-measurement';tag.textContent=label;if(axis==='vertical')tag.style.left=`${position+4}px`;else tag.style.top=`${position+4}px`;stage.append(tag)}
}
function snapDelta(selectionBox,others,dx,dy,sr){
if(!settings.snap)return{dx,dy};clearSmartGuides();const threshold=6;let bestX={d:dx,dist:threshold+1,guide:null},bestY={d:dy,dist:threshold+1,guide:null};
const moved={x:selectionBox.x+dx,y:selectionBox.y+dy,w:selectionBox.w,h:selectionBox.h};
const xFeatures=[['left',moved.x],['center',moved.x+moved.w/2],['right',moved.x+moved.w]];
const yFeatures=[['top',moved.y],['middle',moved.y+moved.h/2],['bottom',moved.y+moved.h]];
const xTargets=[0,sr.width/2,sr.width,...others.flatMap(f=>[f.x,f.x+f.w/2,f.x+f.w]),...(bridge().getState().editorModel?.guides?.x||[]).map(v=>v/100*sr.width)];
const yTargets=[0,sr.height/2,sr.height,...others.flatMap(f=>[f.y,f.y+f.h/2,f.y+f.h]),...(bridge().getState().editorModel?.guides?.y||[]).map(v=>v/100*sr.height)];
xFeatures.forEach(([,v])=>xTargets.forEach(t=>{const dist=Math.abs(v-t);if(dist<bestX.dist)bestX={d:dx+(t-v),dist,guide:t}}));
yFeatures.forEach(([,v])=>yTargets.forEach(t=>{const dist=Math.abs(v-t);if(dist<bestY.dist)bestY={d:dy+(t-v),dist,guide:t}}));
if(settings.grid){const gx=Math.round((selectionBox.x+dx)/settings.gridSize)*settings.gridSize,gy=Math.round((selectionBox.y+dy)/settings.gridSize)*settings.gridSize;if(Math.abs(gx-(selectionBox.x+dx))<bestX.dist)bestX={d:gx-selectionBox.x,dist:Math.abs(gx-(selectionBox.x+dx)),guide:gx};if(Math.abs(gy-(selectionBox.y+dy))<bestY.dist)bestY={d:gy-selectionBox.y,dist:Math.abs(gy-(selectionBox.y+dy)),guide:gy}}
if(bestX.dist<=threshold)smartGuide('vertical',bestX.guide);if(bestY.dist<=threshold)smartGuide('horizontal',bestY.guide);
const left=others.filter(f=>f.x+f.w<=moved.x+bestX.d-dx).sort((a,b)=>(b.x+b.w)-(a.x+a.w))[0];const right=others.filter(f=>f.x>=moved.x+moved.w+bestX.d-dx).sort((a,b)=>a.x-b.x)[0];if(left&&right){const a=(moved.x+bestX.d-dx)-(left.x+left.w),b=right.x-(moved.x+moved.w+bestX.d-dx);if(Math.abs(a-b)<=5)smartGuide('horizontal',moved.y+moved.h/2,`${Math.round((a+b)/2)} px equal spacing`)}
const top=others.filter(f=>f.y+f.h<=moved.y+bestY.d-dy).sort((a,b)=>(b.y+b.h)-(a.y+a.h))[0];const bottom=others.filter(f=>f.y>=moved.y+moved.h+bestY.d-dy).sort((a,b)=>a.y-b.y)[0];if(top&&bottom){const a=(moved.y+bestY.d-dy)-(top.y+top.h),b=bottom.y-(moved.y+moved.h+bestY.d-dy);if(Math.abs(a-b)<=5)smartGuide('vertical',moved.x+moved.w/2,`${Math.round((a+b)/2)} px equal spacing`)}
return{dx:bestX.dist<=threshold?bestX.d:dx,dy:bestY.dist<=threshold?bestY.d:dy};
}
function startInteraction(type,event,handle='',ownerIds=[]){
const wanted=ownerIds.length?[...new Set(ownerIds.map(String))]:selectedIds();
const wantedSet=new Set(wanted),items=allObjectElements().filter(el=>wantedSet.has(el.dataset.id)&&el.dataset.locked!=='true');if(!items.length)return;
const sr=stage.getBoundingClientRect(),frames=items.map(el=>frameOf(el,sr)),selection=items.length>1?visibleBBox(items,sr):bbox(frames);
const overlayBox=ensureOverlay(),overlayRect=overlayBox.getBoundingClientRect(),overlayStart={left:finite(parseFloat(overlayBox.style.left),overlayRect.left),top:finite(parseFloat(overlayBox.style.top),overlayRect.top),width:finite(parseFloat(overlayBox.style.width),overlayRect.width),height:finite(parseFloat(overlayBox.style.height),overlayRect.height),transform:overlayBox.style.transform||'none'};
const captureOwner=event.target.closest?.('[data-pe-handle]')?overlayBox:stage;
const ids=Object.freeze(items.map(el=>el.dataset.id));
interaction={type,handle,pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,sr,frames,selection,ids,moved:false,captureOwner,overlayStart,scrollLeft:viewport?.scrollLeft||0,scrollTop:viewport?.scrollTop||0};
if(!sameIdSet(selectedIds(),ids))bridge().select([...ids]);
if(type==='rotate'){interaction.center={x:selection.x+selection.w/2,y:selection.y+selection.h/2};interaction.startAngle=Math.atan2(event.clientY-(sr.top+interaction.center.y),event.clientX-(sr.left+interaction.center.x));}
document.body.classList.add('pe-pointer-interaction');document.body.dataset.pePointerInteraction=type;
captureOwner.setPointerCapture?.(event.pointerId);clearSmartGuides();event.preventDefault();event.stopImmediatePropagation();
}
function edgePan(event){
if(!viewport||interaction?.type!=='move')return;const r=viewport.getBoundingClientRect(),e=56,s=24;viewport.scrollBy(event.clientX<r.left+e?-s:event.clientX>r.right-e?s:0,event.clientY<r.top+e?-s:event.clientY>r.bottom-e?s:0);
}
function moveInteraction(event){
if(!interaction||event.pointerId!==interaction.pointerId)return;event.preventDefault();event.stopImmediatePropagation();interaction.moved=true;
const i=interaction;holdInteractionSelection(i);edgePan(event);const dx=event.clientX-i.startX+(viewport?.scrollLeft||0)-i.scrollLeft,dy=event.clientY-i.startY+(viewport?.scrollTop||0)-i.scrollTop;
if(i.type==='move'){
const other=activeObjects().filter(el=>!i.ids.includes(el.dataset.id)).map(el=>frameOf(el,i.sr));const snapped=snapDelta(i.selection,other,dx,dy,i.sr);
previewFrames(i.frames.map(f=>({...f,x:f.x+snapped.dx,y:f.y+snapped.dy})),i.sr,'compositor');return;
}
if(i.type==='rotate'){
let delta=(Math.atan2(event.clientY-(i.sr.top+i.center.y),event.clientX-(i.sr.left+i.center.x))-i.startAngle)*180/Math.PI;if(event.shiftKey)delta=Math.round(delta/15)*15;const rad=delta*Math.PI/180;
previewFrames(i.frames.map(f=>{const cx=f.x+f.w/2,cy=f.y+f.h/2,rx=i.center.x+(cx-i.center.x)*Math.cos(rad)-(cy-i.center.y)*Math.sin(rad),ry=i.center.y+(cx-i.center.x)*Math.sin(rad)+(cy-i.center.y)*Math.cos(rad);return{...f,x:rx-f.w/2,y:ry-f.h/2,r:f.r+delta}}),i.sr,'compositor');return;
}
const h=i.handle,center=event.altKey;let x1=i.selection.x,y1=i.selection.y,x2=i.selection.right,y2=i.selection.bottom;
if(h.includes('w'))x1+=dx;if(h.includes('e'))x2+=dx;if(h.includes('n'))y1+=dy;if(h.includes('s'))y2+=dy;
if(center){if(h.includes('w'))x2-=dx;if(h.includes('e'))x1-=dx;if(h.includes('n'))y2-=dy;if(h.includes('s'))y1-=dy}
if(event.shiftKey){const ratio=i.selection.w/Math.max(1,i.selection.h),w=Math.max(MIN_SIZE,x2-x1),hh=Math.max(MIN_SIZE,y2-y1);if(Math.abs(dx)>=Math.abs(dy)){const nh=w/ratio;const cy=(y1+y2)/2;y1=cy-nh/2;y2=cy+nh/2}else{const nw=hh*ratio,cx=(x1+x2)/2;x1=cx-nw/2;x2=cx+nw/2}}
if(x2<x1)[x1,x2]=[x2,x1];if(y2<y1)[y1,y2]=[y2,y1];let next={x:x1,y:y1,w:Math.max(MIN_SIZE,x2-x1),h:Math.max(MIN_SIZE,y2-y1)};
if(center){
const cx=i.selection.x+i.selection.w/2,cy=i.selection.y+i.selection.h/2,maxW=Math.max(MIN_SIZE,2*Math.min(cx,i.sr.width-cx)),maxH=Math.max(MIN_SIZE,2*Math.min(cy,i.sr.height-cy));
if(event.shiftKey){const scale=Math.min(1,maxW/Math.max(MIN_SIZE,next.w),maxH/Math.max(MIN_SIZE,next.h));next.w=Math.max(MIN_SIZE,next.w*scale);next.h=Math.max(MIN_SIZE,next.h*scale)}else{next.w=Math.min(next.w,maxW);next.h=Math.min(next.h,maxH)}
next.x=cx-next.w/2;next.y=cy-next.h/2;
}else{next.x=clamp(next.x,0,i.sr.width-next.w);next.y=clamp(next.y,0,i.sr.height-next.h);next.w=Math.min(next.w,i.sr.width-next.x);next.h=Math.min(next.h,i.sr.height-next.y)}
const sx=next.w/Math.max(1,i.selection.w),sy=next.h/Math.max(1,i.selection.h);
const transformed=i.frames.map(f=>{
if(i.frames.length===1)return{...f,x:next.x+(f.x-i.selection.x)*sx,y:next.y+(f.y-i.selection.y)*sy,w:f.w*sx,h:f.h*sy};
const cx=f.x+f.w/2,cy=f.y+f.h/2,ncx=next.x+(cx-i.selection.x)*sx,ncy=next.y+(cy-i.selection.y)*sy,rad=f.r*Math.PI/180;
const ux=Math.cos(rad)*f.w/2,uy=Math.sin(rad)*f.w/2,vx=-Math.sin(rad)*f.h/2,vy=Math.cos(rad)*f.h/2;
const sux=ux*sx,suy=uy*sy,svx=vx*sx,svy=vy*sy,nw=Math.max(MIN_SIZE,2*Math.hypot(sux,suy)),nh=Math.max(MIN_SIZE,2*Math.hypot(svx,svy)),nr=Math.atan2(suy,sux)*180/Math.PI;
return{...f,x:ncx-nw/2,y:ncy-nh/2,w:nw,h:nh,r:nr};
});previewFrames(transformed,i.sr);
}
function endInteraction(event,cancelled=false){
if(!interaction||event.pointerId!==interaction.pointerId)return;event.preventDefault?.();event.stopImmediatePropagation?.();const i=interaction;interaction=null;clearSmartGuides();
document.body.classList.remove('pe-pointer-interaction');delete document.body.dataset.pePointerInteraction;
const frames=(i.previewFrames?.length?i.previewFrames:i.ids.map(id=>{const el=stage.querySelector(`.object[data-id="${CSS.escape(id)}"]`);return el?frameOf(el,i.sr):null}).filter(Boolean));
clearInteractionPreview(i,true);
if(cancelled){syncAll();window.EInvitePerformance?.record?.('gestureCancelled',1,{type:i.type});return}
if(window.__DEBUG_RESIZE)console.log('END_DEBUG',JSON.stringify({type:i.type,moved:i.moved,ids:i.ids,frames,selection:i.selection,previewFramesLen:i.previewFrames?.length}));if(i.moved)commitFrames(i.type==='move'?'Move objects':i.type==='rotate'?'Rotate objects':'Resize objects',frames,i.ids);else syncAll();
}
function startMarquee(event){
const sr=stage.getBoundingClientRect(),start={x:clamp(event.clientX-sr.left,0,sr.width),y:clamp(event.clientY-sr.top,0,sr.height)};
marquee=document.createElement('div');marquee.className='pe-marquee';marquee.style.left=`${start.x}px`;marquee.style.top=`${start.y}px`;stage.append(marquee);interaction={type:'marquee',pointerId:event.pointerId,sr,start,startSelection:event.shiftKey||event.ctrlKey||event.metaKey?selectedIds():[],moved:false};stage.setPointerCapture?.(event.pointerId);event.preventDefault();event.stopImmediatePropagation();
}
function moveMarquee(event){
const i=interaction;if(!i||i.type!=='marquee'||event.pointerId!==i.pointerId)return;const x=clamp(event.clientX-i.sr.left,0,i.sr.width),y=clamp(event.clientY-i.sr.top,0,i.sr.height),left=Math.min(i.start.x,x),top=Math.min(i.start.y,y),w=Math.abs(x-i.start.x),h=Math.abs(y-i.start.y);i.moved=w>3||h>3;Object.assign(marquee.style,{left:`${left}px`,top:`${top}px`,width:`${w}px`,height:`${h}px`});const indexed=window.EInviteIncrementalRenderer?.queryRect?.({x:left,y:top,w,h});const hits=indexed?indexed.map(item=>item.id).filter(id=>!isLocked(id)):activeObjects().filter(el=>el.dataset.locked!=='true').filter(el=>{const r=visibleRect(el,i.sr);return r.right>=left&&r.x<=left+w&&r.bottom>=top&&r.y<=top+h}).map(el=>el.dataset.id);i.hits=hits;event.preventDefault?.();event.stopImmediatePropagation?.();
}
function endMarquee(event){const i=interaction;if(!i||i.type!=='marquee'||event.pointerId!==i.pointerId)return;interaction=null;marquee?.remove();marquee=null;if(i.moved)setSelection([...i.startSelection,...(i.hits||[])]);else if(!i.startSelection.length)clearSelection();event.preventDefault();event.stopImmediatePropagation();}
function pointerDown(event){
if(event.button!==0||$('#panToggle')?.getAttribute('aria-pressed')==='true')return;
if(interaction){event.preventDefault();event.stopImmediatePropagation();return}
const handle=event.target.closest('[data-pe-handle]');if(handle){event.preventDefault();event.stopImmediatePropagation();startInteraction(handle.dataset.peHandle==='rotate'?'rotate':'resize',event,handle.dataset.peHandle,overlaySelectionIds());return}
const object=event.target.closest('.object');
if(object&&stage.contains(object)){
if(object.dataset.locked==='true'){
const prior=document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab||'';
setTimeout(()=>{if(prior)document.querySelector(`[data-inspector-tab="${CSS.escape(prior)}"]`)?.click()},20);
event.preventDefault();event.stopImmediatePropagation();return
}
if(event.shiftKey||event.ctrlKey||event.metaKey){toggleSelection([object.dataset.id]);event.preventDefault();event.stopImmediatePropagation();return}
if(!selectedIds().includes(object.dataset.id))setSelection([object.dataset.id]);
startInteraction('move',event);return;
}
if(event.target.closest('button,input,select,textarea,[contenteditable=true]'))return;
startMarquee(event);
}
function pointerMove(event){
if(!interaction||event.pointerId!==interaction.pointerId)return;event.preventDefault();event.stopImmediatePropagation();
const run=value=>{if(interaction?.type==='marquee')moveMarquee(value);else moveInteraction(value)};
const scheduler=window.EInviteInteractionScheduler;scheduler?.pointer?scheduler.pointer(event,run,`editor-gesture:${event.pointerId}`):run(event);
}
function pointerUp(event){const scheduler=window.EInviteInteractionScheduler;if(event.type==='pointercancel')scheduler?.cancel?.(`editor-gesture:${event.pointerId}`);else scheduler?.flush?.();if(interaction?.type==='marquee')endMarquee(event);else endInteraction(event,event.type==='pointercancel')}
function selectionChangedDuringInteraction(){
if(!interaction){syncAll();revealSelection();return}
if(interaction.type!=='marquee')holdInteractionSelection(interaction);
}
function alignSelection(mode){
const items=selectedElements().filter(el=>el.dataset.locked!=='true');if(items.length<1)return;const sr=stage.getBoundingClientRect(),frames=items.map(el=>frameOf(el,sr)),b=bbox(frames);let target=b;
const next=frames.map(f=>{let x=f.x,y=f.y;if(mode==='left')x=b.x;if(mode==='center')x=b.x+(b.w-f.w)/2;if(mode==='right')x=b.right-f.w;if(mode==='top')y=b.y;if(mode==='middle')y=b.y+(b.h-f.h)/2;if(mode==='bottom')y=b.bottom-f.h;return{...f,x,y}});commitFrames(`Align ${mode}`,next);
}
function distributeSelection(axis){
const items=selectedElements().filter(el=>el.dataset.locked!=='true');if(items.length<3)return;const sr=stage.getBoundingClientRect(),frames=items.map(el=>frameOf(el,sr)),key=axis==='horizontal'?'x':'y',size=axis==='horizontal'?'w':'h';frames.sort((a,b)=>a[key]-b[key]);const start=frames[0][key],end=frames.at(-1)[key]+frames.at(-1)[size],total=frames.reduce((n,f)=>n+f[size],0),gap=Math.max(0,(end-start-total)/(frames.length-1));let pos=start;frames.forEach(f=>{f[key]=pos;pos+=f[size]+gap});commitFrames(`Distribute ${axis}`,frames);
}
function reorder(ids,mode){
commit(`Arrange ${mode}`,map=>{const order=Object.keys(map).sort((a,b)=>finite(map[a].zIndex)-finite(map[b].zIndex));const selected=new Set(ids);const moving=order.filter(id=>selected.has(id));let rest=order.filter(id=>!selected.has(id));if(mode==='front')rest=[...rest,...moving];else if(mode==='back')rest=[...moving,...rest];else if(mode==='forward'){moving.forEach(id=>{const idx=rest.findIndex(other=>finite(map[other].zIndex)>finite(map[id].zIndex));if(idx<0)rest.push(id);else rest.splice(Math.min(rest.length,idx+1),0,id)})}else if(mode==='backward'){moving.slice().reverse().forEach(id=>{const idx=rest.findIndex(other=>finite(map[other].zIndex)>=finite(map[id].zIndex));rest.splice(Math.max(0,idx<0?0:idx-1),0,id)})}rest.forEach((id,index)=>map[id].zIndex=index+1)},ids);
}
function setObjectFlag(ids,key,value,groupId=''){const nextSelection=key==='visible'&&value===false?selectedIds().filter(id=>!ids.includes(id)):selectedIds();commit(`${key==='visible'?(value?'Show':'Hide'):(value?'Lock':'Unlock')} objects`,(map,doc)=>{ids.forEach(id=>{if(map[id])map[id][key]=value});if(groupId&&groups(doc)[groupId])groups(doc)[groupId][key]=value},nextSelection);}
function layerIdentity(row){if(!row)return null;return row.dataset.groupId?{id:row.dataset.groupId,isGroup:true}:{id:row.dataset.layerId||'',isGroup:false}}
function sameLayerIdentity(a,b){return!!a&&!!b&&String(a.id)===String(b.id)&&(a.isGroup===true)===(b.isGroup===true)}
function rememberLayerFocus(identity){if(!identity?.id)return;layerFocusIdentity={id:String(identity.id),isGroup:identity.isGroup===true};clearTimeout(layerFocusTimer);const remembered=layerFocusIdentity;layerFocusTimer=setTimeout(()=>{if(sameLayerIdentity(layerFocusIdentity,remembered))layerFocusIdentity=null},4000)}
function clearRememberedLayerFocus(){clearTimeout(layerFocusTimer);layerFocusIdentity=null}
function layerRowFor(id,isGroup=false,panel=$('#layersPanel')){if(!panel||!id)return null;const escaped=window.CSS?.escape?CSS.escape(id):String(id).replace(/["']/g,'\$&');return panel.querySelector(isGroup?`.pe-layer-row[data-group-id="${escaped}"]`:`.pe-layer-row[data-layer-id="${escaped}"]`)}
function restoreLayerFocus(panel,identity){
if(!panel||!identity?.id)return;
const expected={id:String(identity.id),isGroup:identity.isGroup===true};
const attempt=()=>{
if(!panel.isConnected)return;
const active=document.activeElement,activeInside=active?.closest?.('#layersPanel'),activeRow=active?.closest?.('.pe-layer-row'),activeIdentity=layerIdentity(activeRow);
if(sameLayerIdentity(activeIdentity,expected))return;
if(activeInside&&!activeRow&&!active?.matches?.('.pe-layer-tree,#layersPanel'))return;
if(layerFocusIdentity&&!sameLayerIdentity(layerFocusIdentity,expected))return;
const row=layerRowFor(expected.id,expected.isGroup,panel);if(!row)return;
try{row.focus({preventScroll:true})}catch{row.focus()}
};
attempt();requestAnimationFrame(attempt);[40,120,260,520].forEach(delay=>setTimeout(attempt,delay));
}
function announceLayer(message){layerAnnouncement=String(message||'');const live=$('.pe-layer-live');if(live){live.textContent='';requestAnimationFrame(()=>{live.textContent=layerAnnouncement})}}
function layerName(id,isGroup=false){const doc=bridge().getState();return String(isGroup?groups(doc)[id]?.name:activeMap(doc)[id]?.layerName||plainText(activeMap(doc)[id]?.html)||id||'Layer')}
function commitLayerName(id,isGroup,name){const value=String(name||'').trim().slice(0,80);if(!value)return false;const current=layerName(id,isGroup);rememberLayerFocus({id,isGroup});if(value===current){requestAnimationFrame(()=>layerRowFor(id,isGroup)?.focus());return false}announceLayer(`${current} renamed to ${value}.`);commit('Rename layer',(map,nextDoc)=>{if(isGroup&&groups(nextDoc)[id])groups(nextDoc)[id].name=value;else if(map[id])map[id].layerName=value},selectedIds());return true}
function beginLayerRename(row,id,isGroup=false){row=row||layerRowFor(id,isGroup);if(!row||row.querySelector('.pe-layer-rename'))return;const strong=row.querySelector('.pe-layer-main strong');if(!strong)return;const current=layerName(id,isGroup),input=document.createElement('input');input.className='pe-layer-rename';input.type='text';input.maxLength=80;input.value=current;input.setAttribute('aria-label',`Rename ${current}`);strong.hidden=true;strong.after(input);let finished=false;const finish=save=>{if(finished)return;finished=true;const value=input.value;input.remove();strong.hidden=false;if(save&&String(value).trim())commitLayerName(id,isGroup,value);else{rememberLayerFocus({id,isGroup});requestAnimationFrame(()=>layerRowFor(id,isGroup)?.focus())}};input.addEventListener('keydown',event=>{event.stopPropagation();if(event.key==='Enter'){event.preventDefault();finish(true)}else if(event.key==='Escape'){event.preventDefault();finish(false)}});input.addEventListener('blur',()=>finish(true),{once:true});requestAnimationFrame(()=>{input.focus();input.select()})}
function cleanGroups(map,gs){let changed=true;while(changed){changed=false;Object.values(gs).forEach(g=>{const before=(g.children||[]).length;g.children=(g.children||[]).filter(child=>map[child]||gs[child]);if(g.children.length!==before)changed=true});Object.keys(gs).forEach(gid=>{if(!(gs[gid].children||[]).length){delete gs[gid];changed=true}})}}
function deleteSelection(){const ids=selectedIds();if(!ids.length)return;commit('Delete objects',(map,doc)=>{ids.forEach(id=>delete map[id]);const gs=groups(doc);Object.values(gs).forEach(g=>g.children=(g.children||[]).filter(child=>!ids.includes(child)));cleanGroups(map,gs)},[]);}
function clipboardSerializedBytes(payload){try{return new TextEncoder().encode(JSON.stringify(payload)).length}catch{return Infinity}}
function validateClipboardPayload(payload){
if(!payload||typeof payload!=='object'||Array.isArray(payload))return{ok:false,error:'Clipboard data is invalid.'};
if(payload.version!==CLIPBOARD_VERSION)return{ok:false,error:'Clipboard data uses an unsupported version.'};
if(typeof payload.projectId!=='string'||payload.projectId.length>160||typeof payload.canvasId!=='string'||!payload.canvasId||payload.canvasId.length>160)return{ok:false,error:'Clipboard origin is invalid.'};
if(!Array.isArray(payload.objects)||!payload.objects.length||payload.objects.length>CLIPBOARD_MAX_OBJECTS)return{ok:false,error:'Clipboard object count is invalid.'};
if(clipboardSerializedBytes(payload)>CLIPBOARD_MAX_BYTES)return{ok:false,error:'Clipboard data is too large.'};
const groupsValue=payload.groups==null?{}:payload.groups;if(!groupsValue||typeof groupsValue!=='object'||Array.isArray(groupsValue))return{ok:false,error:'Clipboard groups are invalid.'};
const objectIds=new Set(),groupIds=new Set(Object.keys(groupsValue));
for(const entry of payload.objects){
if(!Array.isArray(entry)||entry.length!==2)return{ok:false,error:'Clipboard object shape is invalid.'};
const [id,obj]=entry;if(typeof id!=='string'||!id||id.length>160||objectIds.has(id))return{ok:false,error:'Clipboard object IDs are invalid.'};objectIds.add(id);
if(!obj||typeof obj!=='object'||Array.isArray(obj))return{ok:false,error:'Clipboard object data is invalid.'};
if(!CLIPBOARD_ALLOWED_TYPES.has(String(obj.type||'')))return{ok:false,error:'Clipboard contains an unsupported object type.'};
for(const key of ['left','top','width','height']){const value=String(obj[key]??'');if(!/^-?\d+(?:\.\d+)?(?:px|%)?$/.test(value)||!Number.isFinite(parseFloat(value)))return{ok:false,error:'Clipboard transform data is invalid.'}}
if(!Number.isFinite(Number(obj.rotation??0))||Math.abs(Number(obj.rotation??0))>36000)return{ok:false,error:'Clipboard rotation is invalid.'};
if(obj.html!=null&&(typeof obj.html!=='string'||obj.html.length>200000))return{ok:false,error:'Clipboard rich text is invalid.'};
}
for(const [gid,g] of Object.entries(groupsValue)){
if(!gid||gid.length>160||!g||typeof g!=='object'||Array.isArray(g)||!Array.isArray(g.children))return{ok:false,error:'Clipboard group data is invalid.'};
if(g.parentId&& !groupIds.has(String(g.parentId)))return{ok:false,error:'Clipboard group parent is invalid.'};
for(const child of g.children)if(!objectIds.has(String(child))&&!groupIds.has(String(child)))return{ok:false,error:'Clipboard group child is invalid.'};
}
const visiting=new Set(),visited=new Set();
function visit(gid){if(visiting.has(gid))return false;if(visited.has(gid))return true;visiting.add(gid);const g=groupsValue[gid];for(const child of g.children||[])if(groupIds.has(String(child))&&!visit(String(child)))return false;visiting.delete(gid);visited.add(gid);return true}
for(const gid of groupIds)if(!visit(gid))return{ok:false,error:'Clipboard groups contain a cycle.'};
return{ok:true,payload};
}
function notifyClipboardError(message){try{window.showToast?.(message,'error')}catch{};document.dispatchEvent(new CustomEvent('einvite:clipboard-error',{detail:{message}}))}
function copyPayload(ids=selectedIds()){
const doc=bridge().getState(),map=activeMap(doc),gs=groups(doc),objects=ids.filter(id=>map[id]).map(id=>[id,clone(map[id])]);if(!objects.length)return null;
const groupIds=new Set();objects.forEach(([id,o])=>{let gid=o.groupId;while(gid&&gs[gid]&&!groupIds.has(gid)){groupIds.add(gid);gid=gs[gid].parentId}});
return{version:CLIPBOARD_VERSION,projectId:String(doc.id||doc.invitationId||''),canvasId:bridge().getActiveCanvasId(),objects,groups:Object.fromEntries([...groupIds].map(id=>[id,clone(gs[id])])),copiedAt:Date.now()};
}
function copySelection(){const payload=copyPayload();if(!payload)return false;memoryClipboard=clone(payload);try{sessionStorage.setItem(CLIPBOARD,JSON.stringify(payload))}catch{}return true;}
function pastePayload(rawPayload,offset=14){
const checked=validateClipboardPayload(rawPayload);if(!checked.ok){notifyClipboardError(checked.error);return false}const payload=checked.payload;
const current=bridge().getState(),currentProject=String(current.id||current.invitationId||'');if(String(payload.projectId)!==currentProject){notifyClipboardError('Clipboard content belongs to another project.');return false}
const activeCanvas=bridge().getActiveCanvasId();if(payload.canvasId!==activeCanvas){notifyClipboardError('Clipboard content belongs to another page.');return false}
const idMap=new Map(payload.objects.map(([id])=>[id,uid('obj')])),groupMap=new Map(Object.keys(payload.groups||{}).map(id=>[id,uid('group')])),newIds=[...idMap.values()],sr=stage.getBoundingClientRect();
commit('Paste objects',(map,doc)=>{
payload.objects.forEach(([oldId,obj])=>{const next=clone(obj),id=idMap.get(oldId),frame=safeFrame({id,x:px(next.left,sr.width)+offset,y:px(next.top,sr.height)+offset,w:px(next.width,sr.width,MIN_SIZE),h:px(next.height,sr.height,MIN_SIZE),r:finite(next.rotation)},sr);next.left=pct(frame.x,sr.width);next.top=pct(frame.y,sr.height);next.width=pct(frame.w,sr.width);next.height=pct(frame.h,sr.height);next.rotation=frame.r;next.legacyId=id;delete next.id;delete next.canvasId;next.groupId=groupMap.get(next.groupId)||'';next.parentGroupId=groupMap.get(next.parentGroupId)||'';next.zIndex=Math.max(...Object.values(map).map(o=>finite(o.zIndex,0)),0)+1;map[id]=next});
const gs=groups(doc);Object.entries(payload.groups||{}).forEach(([oldId,g])=>{const id=groupMap.get(oldId);gs[id]={...clone(g),id,name:g.name||'Group',parentId:groupMap.get(g.parentId)||'',children:(g.children||[]).map(child=>groupMap.get(child)||idMap.get(child)).filter(Boolean)}});cleanGroups(map,gs);
},newIds);return true;
}
function pasteSelection(){let payload=memoryClipboard?clone(memoryClipboard):null;try{payload=payload||JSON.parse(sessionStorage.getItem(CLIPBOARD)||'null')}catch{}return pastePayload(payload)}
function duplicateSelection(){return pastePayload(copyPayload(),14)}
function cutSelection(){if(!copySelection())return false;deleteSelection();return true}
function groupSelection(){
const ids=selectedIds();if(ids.length<2)return;const gid=uid('group');expandedGroups.add(gid);
commit('Group objects',(map,doc)=>{const gs=groups(doc),roots=[],covered=new Set();ids.forEach(id=>{const existing=topGroupForObject(id,doc);if(existing&&!covered.has(existing)){roots.push(existing);descendantIds(existing,gs).forEach(x=>covered.add(x))}else if(!covered.has(id))roots.push(id)});gs[gid]={id:gid,name:'Group',children:roots,parentId:'',locked:false,visible:true};roots.forEach(child=>{if(gs[child])gs[child].parentId=gid;else if(map[child]){map[child].groupId=gid;map[child].parentGroupId=gid}})},ids);selectedGroupId=gid;requestAnimationFrame(syncAll);
}
function ungroupSelection(){
const ids=selectedIds();if(!ids.length)return;const doc=bridge().getState(),gs=groups(doc);let gid=selectedGroupId||topGroupForObject(ids[0],doc);if(!gid||!gs[gid])return;const parent=gs[gid].parentId||'',children=[...(gs[gid].children||[])];
commit('Ungroup objects',(map,nextDoc)=>{const nextGroups=groups(nextDoc);children.forEach(child=>{if(nextGroups[child])nextGroups[child].parentId=parent;else if(map[child]){map[child].groupId=parent;map[child].parentGroupId=parent}});if(parent&&nextGroups[parent])nextGroups[parent].children=(nextGroups[parent].children||[]).flatMap(child=>child===gid?children:[child]);delete nextGroups[gid]},ids);selectedGroupId=parent;
}
function descendantsForLayer(groupId){return descendantIds(groupId,groups()).filter(id=>activeMap()[id]);}
function renderLayers(panel=$('#layersPanel')){
if(!panel||layersRendering||layerDragState?.active)return;layersRendering=true;try{
const priorTree=panel.querySelector('.pe-layer-tree'),priorScroll=priorTree?.scrollTop||0,active=document.activeElement,activeRow=active?.closest?.('.pe-layer-row'),activeIdentity=layerFocusIdentity||layerIdentity(activeRow),searchFocused=active?.matches?.('[data-pe-layer-search]'),searchSelection=searchFocused?[active.selectionStart,active.selectionEnd]:null;
const doc=bridge().getState(),map=activeMap(doc),gs=groups(doc),selection=new Set(selectedIds()),query=panel.querySelector('[data-pe-layer-search]')?.value||'';
panel.innerHTML=`<div class="pe-layer-toolbar"><input data-pe-layer-search type="search" placeholder="Search layers" value=""><button data-pe-arrange="front" title="Bring to front">Front</button><button data-pe-arrange="forward" title="Bring forward">↑</button><button data-pe-arrange="backward" title="Send backward">↓</button><button data-pe-arrange="back" title="Send to back">Back</button></div><div class="pe-layer-tree" role="tree" aria-label="Layers"></div><div class="pe-layer-live" aria-live="polite" aria-atomic="true"></div>`;
const search=$('[data-pe-layer-search]',panel);search.value=query;search.addEventListener('focus',clearRememberedLayerFocus);const tree=$('.pe-layer-tree',panel);tree.scrollTop=priorScroll;
const objectOrder=Object.keys(map).sort((a,b)=>finite(map[b].zIndex)-finite(map[a].zIndex));const objectInGroup=new Set(Object.values(gs).flatMap(g=>g.children||[]).filter(id=>map[id]));const topGroups=Object.keys(gs).filter(id=>!gs[id].parentId);
const layerRank=id=>map[id]?finite(map[id].zIndex):Math.max(0,...descendantIds(id,gs).map(child=>finite(map[child]?.zIndex)));
function matches(id,isGroup){const label=(isGroup?gs[id]?.name:map[id]?.layerName||map[id]?.html||id)||'';return !query||String(label).toLowerCase().includes(query.toLowerCase())}
function objectRow(id,depth){const o=map[id];if(!o||!matches(id,false))return null;const row=document.createElement('div');row.className=`pe-layer-row${selection.has(id)?' active':''}`;row.dataset.layerId=id;row.dataset.layerIds=id;row.style.setProperty('--depth',depth);row.setAttribute('role','treeitem');row.setAttribute('aria-keyshortcuts','F2 Alt+ArrowUp Alt+ArrowDown Alt+Home Alt+End');row.innerHTML=`<span class="pe-layer-indent"></span><button data-layer-visible aria-label="${o.visible===false?'Show':'Hide'} layer">${o.visible===false?'○':'◉'}</button><button class="pe-layer-main"><span>${o.type==='image'?'▧':o.type==='shape'?'□':'T'}</span><strong></strong></button><button data-layer-lock aria-label="${o.locked?'Unlock':'Lock'} layer">${o.locked?'🔒':'◇'}</button><button data-layer-more aria-label="Layer actions">⋯</button><button data-layer-drag aria-label="Reorder layer" title="Drag to reorder">↕</button>`;row.querySelector('strong').textContent=o.layerName||plainText(o.html)||id;wireLayerRow(row,id,false);return row}
function groupRow(id,depth){const g=gs[id];if(!g)return null;const ids=descendantsForLayer(id),match=matches(id,true)||ids.some(child=>matches(child,false));if(!match)return null;const wrap=document.createElement('div');wrap.className='pe-layer-group';const row=document.createElement('div');row.className=`pe-layer-row pe-group-row${ids.some(x=>selection.has(x))?' active':''}`;row.dataset.groupId=id;row.dataset.layerIds=ids.join(',');row.style.setProperty('--depth',depth);row.setAttribute('role','treeitem');row.setAttribute('aria-keyshortcuts','F2 Alt+ArrowUp Alt+ArrowDown Alt+Home Alt+End');const open=expandedGroups.has(id);row.innerHTML=`<span class="pe-layer-indent"></span><button data-group-expand aria-label="${open?'Collapse':'Expand'} group">${open?'▾':'▸'}</button><button data-layer-visible aria-label="${ids.every(x=>map[x]?.visible===false)?'Show':'Hide'} group">${ids.every(x=>map[x]?.visible===false)?'○':'◉'}</button><button class="pe-layer-main"><span>◫</span><strong></strong></button><button data-layer-lock aria-label="Toggle group lock">${ids.every(x=>map[x]?.locked)?'🔒':'◇'}</button><button data-layer-more aria-label="Group actions">⋯</button><button data-layer-drag aria-label="Reorder group" title="Drag to reorder">↕</button>`;row.querySelector('strong').textContent=g.name||'Group';wireLayerRow(row,id,true);wrap.append(row);if(open){const childBox=document.createElement('div');childBox.className='pe-layer-children';(g.children||[]).slice().sort((a,b)=>layerRank(b)-layerRank(a)).forEach(child=>{const node=gs[child]?groupRow(child,depth+1):objectRow(child,depth+1);if(node)childBox.append(node)});wrap.append(childBox)}return wrap}
const topEntries=[...topGroups.map(id=>({id,group:true,rank:layerRank(id)})),...objectOrder.filter(id=>!objectInGroup.has(id)).map(id=>({id,group:false,rank:layerRank(id)}))].sort((a,b)=>b.rank-a.rank);topEntries.forEach(entry=>{const node=entry.group?groupRow(entry.id,0):objectRow(entry.id,0);if(node)tree.append(node)});
search.addEventListener('input',()=>renderLayers(panel));panel.querySelectorAll('[data-pe-arrange]').forEach(b=>b.onclick=()=>{rememberLayerFocus(layerIdentity(document.activeElement?.closest?.('.pe-layer-row')));reorder(selectedIds(),b.dataset.peArrange);announceLayer(`Selected layers moved ${b.title.toLowerCase()}.`)});$('.pe-layer-live',panel).textContent=layerAnnouncement;
tree.scrollTop=priorScroll;if(searchFocused){search.focus();if(searchSelection)search.setSelectionRange(...searchSelection)}else if(activeIdentity)restoreLayerFocus(panel,activeIdentity);
} finally {layersRendering=false}
}
function plainText(html){const el=document.createElement('div');el.innerHTML=html||'';return(el.textContent||'').trim().slice(0,36)}
function clearLayerDropIndicator(){document.querySelectorAll('.pe-layer-row.drop-before,.pe-layer-row.drop-after,.pe-layer-row.drop-target').forEach(row=>row.classList.remove('drop-before','drop-after','drop-target'))}
function layerScroller(row){let node=row?.closest?.('.pe-layer-tree')||row?.closest?.('#layersPanel');while(node&&node!==document.body){const style=getComputedStyle(node);if(/auto|scroll/.test(style.overflowY)&&node.scrollHeight>node.clientHeight+2)return node;node=node.parentElement}return row?.closest?.('#layersPanel')||null}
function updateLayerDragTarget(event){if(!layerDragState?.active)return;const hit=document.elementFromPoint(event.clientX,event.clientY),row=hit?.closest?.('.pe-layer-row');clearLayerDropIndicator();layerDragState.targetIds=[];layerDragState.position='';if(row&&row!==layerDragState.source){const targetIds=String(row.dataset.layerIds||'').split(',').filter(Boolean);if(targetIds.length&&!targetIds.some(id=>layerDragState.ids.includes(id))){const rr=row.getBoundingClientRect(),position=event.clientY<rr.top+rr.height/2?'before':'after';row.classList.add(position==='before'?'drop-before':'drop-after');layerDragState.targetIds=targetIds;layerDragState.position=position;layerDragState.targetRow=row}}const scroller=layerDragState.scroller,rect=scroller?.getBoundingClientRect?.();if(scroller&&rect){const edge=Math.min(48,rect.height/4);if(event.clientY<rect.top+edge)scroller.scrollTop-=Math.max(8,(rect.top+edge-event.clientY)/2);else if(event.clientY>rect.bottom-edge)scroller.scrollTop+=Math.max(8,(event.clientY-(rect.bottom-edge))/2)}}
function startLayerPointerDrag(event,row,ids){if(event.button!==0||!ids.length)return;event.preventDefault();event.stopPropagation();rememberLayerFocus(layerIdentity(row));layerDragState={pointerId:event.pointerId,ids:[...ids],source:row,startX:event.clientX,startY:event.clientY,active:false,targetIds:[],position:'',targetRow:null,scroller:layerScroller(row)};try{event.currentTarget.setPointerCapture(event.pointerId)}catch{}}
function layerPointerMove(event){const drag=layerDragState;if(!drag||event.pointerId!==drag.pointerId)return;if(!drag.active&&Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<5)return;if(!drag.active){drag.active=true;drag.source.classList.add('dragging');document.body.classList.add('pe-layer-dragging')}event.preventDefault();updateLayerDragTarget(event)}
function finishLayerPointerDrag(event){const drag=layerDragState;if(!drag||event.pointerId!==drag.pointerId)return;event.preventDefault();if(drag.active&&drag.targetIds.length&&drag.position)reorderRelative(drag.ids,drag.targetIds,drag.position,layerIdentity(drag.source),layerIdentity(drag.targetRow));drag.source?.classList.remove('dragging');document.body.classList.remove('pe-layer-dragging');clearLayerDropIndicator();layerDragState=null}
function wireLayerRow(row,id,isGroup){
const ids=()=>isGroup?descendantsForLayer(id):[id];row.addEventListener('pointerdown',()=>rememberLayerFocus({id,isGroup}),true);row.addEventListener('focus',()=>rememberLayerFocus({id,isGroup}));row.querySelector('.pe-layer-main').onclick=event=>{document.body.dataset.workflowInspectorManual='1';setTimeout(()=>delete document.body.dataset.workflowInspectorManual,700);selectedGroupId=isGroup?id:'';const next=ids();if(event.shiftKey||event.ctrlKey||event.metaKey){const set=new Set(selectedIds()),remove=next.every(x=>set.has(x));next.forEach(x=>remove?set.delete(x):set.add(x));setSelection([...set],{canvas:false})}else setSelection(next,{canvas:false})};
row.querySelector('[data-group-expand]')?.addEventListener('click',()=>{rememberLayerFocus({id,isGroup});expandedGroups.has(id)?expandedGroups.delete(id):expandedGroups.add(id);renderLayers()});
row.querySelector('[data-layer-visible]')?.addEventListener('click',()=>{rememberLayerFocus({id,isGroup});const map=activeMap(),next=!ids().every(x=>map[x]?.visible!==false);setObjectFlag(ids(),'visible',next,isGroup?id:'')});
row.querySelector('[data-layer-lock]')?.addEventListener('click',()=>{rememberLayerFocus({id,isGroup});const map=activeMap(),next=!ids().every(x=>map[x]?.locked===true);setObjectFlag(ids(),'locked',next,isGroup?id:'')});
row.querySelector('[data-layer-more]').onclick=event=>openLayerMenu(event.currentTarget,id,isGroup);
row.querySelector('.pe-layer-main').ondblclick=()=>beginLayerRename(row,id,isGroup);
row.tabIndex=0;
row.querySelector('[data-layer-drag]')?.addEventListener('pointerdown',event=>startLayerPointerDrag(event,row,ids()));
row.addEventListener('keydown',event=>{if(event.key==='F2'){event.preventDefault();beginLayerRename(row,id,isGroup);return}if(!event.altKey&&!event.ctrlKey&&!event.metaKey)return;let mode='';if(event.key==='ArrowUp')mode='forward';else if(event.key==='ArrowDown')mode='backward';else if(event.key==='Home')mode='front';else if(event.key==='End')mode='back';if(!mode)return;event.preventDefault();event.stopPropagation();rememberLayerFocus({id,isGroup});reorder(ids(),mode);announceLayer(`${layerName(id,isGroup)} moved ${mode==='front'?'to front':mode==='back'?'to back':mode==='forward'?'up':'down'}.`)});
}
function reorderRelative(moving,targetIds,position,sourceIdentity=null,targetIdentity=null){const map=activeMap(),movingSet=new Set(moving.filter(id=>map[id])),targetSet=new Set(targetIds.filter(id=>map[id]&&!movingSet.has(id)));if(!movingSet.size||!targetSet.size)return false;const visual=Object.keys(map).sort((a,b)=>finite(map[b].zIndex)-finite(map[a].zIndex)),movingVisual=visual.filter(id=>movingSet.has(id)),rest=visual.filter(id=>!movingSet.has(id)),indices=rest.map((id,index)=>targetSet.has(id)?index:-1).filter(index=>index>=0);if(!indices.length)return false;const insertAt=position==='after'?Math.max(...indices)+1:Math.min(...indices),next=[...rest.slice(0,insertAt),...movingVisual,...rest.slice(insertAt)];if(next.every((id,index)=>id===visual[index]))return false;rememberLayerFocus(sourceIdentity);const sourceLabel=sourceIdentity?layerName(sourceIdentity.id,sourceIdentity.isGroup):`${movingVisual.length} layer${movingVisual.length===1?'':'s'}`,targetLabel=targetIdentity?layerName(targetIdentity.id,targetIdentity.isGroup):'target';announceLayer(`${sourceLabel} moved ${position} ${targetLabel}.`);commit('Reorder layers',nextMap=>{[...next].reverse().forEach((id,index)=>{if(nextMap[id])nextMap[id].zIndex=index+1})},movingVisual);return true}
function openLayerMenu(anchor,id,isGroup){
document.querySelector('.pe-layer-menu')?.remove();const menu=document.createElement('div');menu.className='pe-layer-menu';menu.innerHTML=`<button data-a="rename">Rename</button><button data-a="duplicate">Duplicate</button><button data-a="front">Bring to front</button><button data-a="back">Send to back</button><button data-a="delete">Delete</button>`;document.body.append(menu);const r=anchor.getBoundingClientRect();menu.style.left=`${Math.min(innerWidth-180,r.right-170)}px`;menu.style.top=`${Math.min(innerHeight-220,r.bottom+4)}px`;const ids=isGroup?descendantsForLayer(id):[id];menu.onclick=e=>{const a=e.target.dataset.a;if(a==='rename')beginLayerRename(layerRowFor(id,isGroup),id,isGroup);if(a==='duplicate'){setSelection(ids,{canvas:false});duplicateSelection()}if(a==='front')reorder(ids,'front');if(a==='back')reorder(ids,'back');if(a==='delete'){setSelection(ids,{canvas:false});deleteSelection()}menu.remove()};setTimeout(()=>document.addEventListener('pointerdown',function close(e){if(!menu.contains(e.target)&&e.target!==anchor){menu.remove();document.removeEventListener('pointerdown',close)}},true),0);
}
function nudge(dx,dy){const items=selectedElements().filter(el=>el.dataset.locked!=='true');if(!items.length)return;const sr=stage.getBoundingClientRect(),frames=items.map(el=>{const f=frameOf(el,sr);return{...f,x:f.x+dx,y:f.y+dy}});commitFrames('Nudge objects',frames)}
function interceptLegacyButtons(event){
const button=event.target.closest('button');if(!button)return;let handled=true;
if(button.id==='groupObjects')groupSelection();else if(button.id==='ungroupObjects')ungroupSelection();else if(button.id==='duplicate')duplicateSelection();else if(button.id==='deleteBtn')deleteSelection();else if(button.id==='bringForward')reorder(selectedIds(),'forward');else if(button.id==='sendBackward')reorder(selectedIds(),'backward');else if(button.dataset.align)alignSelection(button.dataset.align);else if(button.dataset.distribute)distributeSelection(button.dataset.distribute);else handled=false;
if(handled){event.preventDefault();event.stopImmediatePropagation()}
}
let heavySyncFrame=0;
function syncAll(){ensureTransformPanel();ensureAssistancePanel();ensureMobileContextBar();syncOverlay();syncTransformInputs();syncMobileContextBar();if(heavySyncFrame)return;heavySyncFrame=requestAnimationFrame(()=>{heavySyncFrame=0;renderUserGuides();renderLayers()})}
function scheduleOverlaySync(full=false){
if(full===true)overlaySyncFull=true;
if(overlaySyncFrame)return;
overlaySyncFrame=setTimeout(()=>{overlaySyncFrame=0;const runFull=overlaySyncFull;overlaySyncFull=false;if(runFull)syncAll();else{syncOverlay();syncTransformInputs()}},0);
}
function teardownOverlaySync(){
if(overlaySyncFrame)clearTimeout(overlaySyncFrame);overlaySyncFrame=0;overlaySyncFull=false;
overlayResizeObserver?.disconnect();overlayResizeObserver=null;
overlaySyncLifecycle?.abort();overlaySyncLifecycle=null;
}
function installOverlaySync(){
if(overlaySyncLifecycle)return;
const controller=new AbortController(),viewport=$('#canvasViewport');overlaySyncLifecycle=controller;const signal=controller.signal;
window.addEventListener('einvite:zoom-changed',scheduleOverlaySync,{signal});
window.addEventListener('einvite:workspace-resized',()=>scheduleOverlaySync(true),{signal});
window.addEventListener('resize',()=>scheduleOverlaySync(true),{signal});
viewport?.addEventListener('scroll',scheduleOverlaySync,{passive:true,signal});
window.addEventListener('pagehide',event=>{if(!event.persisted)teardownOverlaySync()},{signal});
if('ResizeObserver'in window){overlayResizeObserver=new ResizeObserver(()=>scheduleOverlaySync());overlayResizeObserver.observe(stage);if(viewport)overlayResizeObserver.observe(viewport)}
}
function boot(){
window.EInviteProfessionalEditor={version:17,ownsPointerInteractions:true,ownsKeyboardInteractions:true,renderLayers,sync:syncAll,get commandSequence(){return commandSequence},get lastCommand(){return lastCommand?clone(lastCommand):null},get activeInteraction(){return interaction?{type:interaction.type,handle:interaction.handle,pointerId:interaction.pointerId,ids:interaction.ids?[...interaction.ids]:[]}:null},commands:{alignSelection,distributeSelection,groupSelection,ungroupSelection,copySelection,cutSelection,pasteSelection,pastePayload,validateClipboardPayload,duplicateSelection,deleteSelection,reorder,reorderRelative,nudge,clearSelection,setSelection,setObjectFlag,undoSelection,redoSelection}};
document.body.classList.add('professional-editor-v17');stage.style.overflow='visible';ensureOverlay();ensureTransformPanel();ensureAssistancePanel();ensureMobileContextBar();applyAssistanceState();installOverlaySync();
stage.addEventListener('pointerdown',pointerDown,true);stage.addEventListener('pointermove',pointerMove,true);stage.addEventListener('pointerup',pointerUp,true);stage.addEventListener('pointercancel',pointerUp,true);
document.addEventListener('pointerdown',event=>{if(!event.target.closest?.('#layersPanel'))clearRememberedLayerFocus()},true);document.addEventListener('focusin',event=>{const row=event.target?.closest?.('.pe-layer-row');if(row)rememberLayerFocus(layerIdentity(row));else if(event.target!==document.body&&event.target!==document.documentElement)clearRememberedLayerFocus()},true);window.addEventListener('pointermove',layerPointerMove,true);window.addEventListener('pointerup',finishLayerPointerDrag,true);window.addEventListener('pointercancel',finishLayerPointerDrag,true);document.addEventListener('click',interceptLegacyButtons,true);document.addEventListener('einvite:selection-changed',selectionChangedDuringInteraction);window.addEventListener('einvite:state-applied',()=>setTimeout(()=>{if(interaction)holdInteractionSelection(interaction);else{syncAll();revealSelection()}},0));
new MutationObserver(()=>requestAnimationFrame(syncMobileContextBar)).observe(document.body,{attributes:true,attributeFilter:['class']});
new MutationObserver(mutations=>{
if(interaction)return;
const relevant=mutations.some(mutation=>{
if(mutation.type==='attributes') return mutation.target?.classList?.contains('object');
return [...mutation.addedNodes,...mutation.removedNodes].some(node=>node.nodeType===1&&(node.classList?.contains('object')||node.querySelector?.('.object')));
});
if(relevant)requestAnimationFrame(syncAll);
}).observe(stage,{childList:true,subtree:true,attributes:true,attributeFilter:['data-locked','data-visible']});
setTimeout(()=>{const remembered=bridge().getSelectedIds();if(remembered.length)bridge().select(remembered);syncAll()},100);
}
boot();
})();
