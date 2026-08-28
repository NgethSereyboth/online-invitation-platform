(()=>{
'use strict';
if(window.EInviteProfessionalWorkflow?.version>=23.1)return;if(!document.querySelector('link[data-v23-professional-workflow]')){const l=document.createElement('link');l.rel='stylesheet';l.href='professional-workflow-v23.css';l.dataset.v23ProfessionalWorkflow='1';document.head.append(l)}
const registry=window.EInviteCommandRegistry,bridge=window.EInviteEditorBridge,stage=document.querySelector('#stage');
if(!registry||!bridge||!stage)return;
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const clone=v=>{try{return structuredClone(v)}catch{return JSON.parse(JSON.stringify(v))}};
const clamp=(v,min,max)=>Math.min(max,Math.max(min,v));
const px=v=>Number.parseFloat(v)||0;
function activeMap(doc=bridge.getState()){
 const cid=bridge.getActiveCanvasId?.()||'hero';
 if(cid==='hero')return doc.objects||(doc.objects={});
 const page=(doc.designPages||[]).find(p=>`page:${p.id}`===cid);return page?(page.objects||(page.objects={})):doc.objects||{};
}
function selectedIds(){return bridge.getSelectedIds?.()||[]}
function selectedElements(){const set=new Set(selectedIds());return $$('#stage .object').filter(el=>set.has(el.dataset.id))}
function transformHud(){let hud=$('#v23TransformHud');if(!hud){hud=document.createElement('div');hud.id='v23TransformHud';hud.className='v23-transform-hud';hud.hidden=true;document.body.append(hud)}return hud}
function updateTransformHud(){const hud=transformHud();if(!transform){hud.hidden=true;return}const f=transform.frames[0];hud.hidden=false;hud.textContent=`X ${f.x.toFixed(1)}  Y ${f.y.toFixed(1)}  W ${f.w.toFixed(1)}  H ${f.h.toFixed(1)}  R ${f.rotation.toFixed(1)}°`}
function announce(message){window.uiToast?.(message,'⌘');let live=$('#v23WorkflowLive');if(!live){live=document.createElement('div');live.id='v23WorkflowLive';live.className='sr-only';live.setAttribute('aria-live','polite');document.body.append(live)}live.textContent='';requestAnimationFrame(()=>live.textContent=message)}

// Phase 1: transactional keyboard transform mode.
let transform=null;
function frameFromElement(el){const sr=stage.getBoundingClientRect(),r=el.getBoundingClientRect();return{id:el.dataset.id,x:(r.left-sr.left)/sr.width*100,y:(r.top-sr.top)/sr.height*100,w:r.width/sr.width*100,h:r.height/sr.height*100,rotation:px(el.style.rotate||el.dataset.rotation||0)}}
function applyPreview(frame){const el=stage.querySelector(`.object[data-id="${CSS.escape(frame.id)}"]`);if(!el)return;const sr=stage.getBoundingClientRect(),base=frame.base||frame;const dx=(frame.x-base.x)/100*sr.width,dy=(frame.y-base.y)/100*sr.height,sx=base.w?frame.w/base.w:1,sy=base.h?frame.h/base.h:1,dr=frame.rotation-base.rotation;el.style.setProperty('--v23-preview-transform',`translate(${dx}px,${dy}px) rotate(${dr}deg) scale(${sx},${sy})`);el.classList.add('v23-transform-preview')}
function startTransform(){if(transform)return true;const els=selectedElements().filter(el=>el.dataset.locked!=='true');if(!els.length)return false;transform={frames:els.map(el=>{const f=frameFromElement(el);return{...f,base:{...f}}}),original:els.map(el=>({id:el.dataset.id})),changed:false};document.body.classList.add('v23-transform-mode');updateTransformHud();announce('Transform mode. Arrow keys move, Alt plus arrows resize, Ctrl or Command plus Alt plus arrows rotate. Enter commits; Escape cancels.');return true}
function updateTransform(kind,dx=0,dy=0){if(!transform&&!startTransform())return false;for(const frame of transform.frames){if(kind==='move'){frame.x=clamp(frame.x+dx,0,100-frame.w);frame.y=clamp(frame.y+dy,0,100-frame.h)}else if(kind==='resize'){frame.w=clamp(frame.w+dx,0.5,100-frame.x);frame.h=clamp(frame.h+dy,0.5,100-frame.y)}else if(kind==='rotate')frame.rotation=((frame.rotation+dx)%360+360)%360;applyPreview(frame)}transform.changed=true;updateTransformHud();return true}
function restorePreview(){if(!transform)return;for(const original of transform.original){const el=stage.querySelector(`.object[data-id="${CSS.escape(original.id)}"]`);if(el){el.style.removeProperty('--v23-preview-transform');el.classList.remove('v23-transform-preview')}}}
function cancelTransform(){if(!transform)return false;restorePreview();transform=null;document.body.classList.remove('v23-transform-mode');updateTransformHud();window.EInviteProfessionalEditor?.sync?.();announce('Transform cancelled');return true}
function commitTransform(){if(!transform)return false;const payload=clone(transform.frames),changed=transform.changed;restorePreview();transform=null;document.body.classList.remove('v23-transform-mode');updateTransformHud();if(!changed)return true;bridge.transact('Transform objects',doc=>{const map=activeMap(doc);for(const frame of payload){const o=map[frame.id];if(!o)continue;o.left=`${frame.x}%`;o.top=`${frame.y}%`;o.width=`${frame.w}%`;o.height=`${frame.h}%`;o.rotation=frame.rotation}},{capture:false});setTimeout(()=>{bridge.select(payload.map(x=>x.id));window.EInviteProfessionalEditor?.sync?.()},0);announce('Transform applied');return true}
function nudgeTransform(dx,dy){return updateTransform('move',dx,dy)}
function resizeTransform(dw,dh){return updateTransform('resize',dw,dh)}
function rotateTransform(deg){return updateTransform('rotate',deg,0)}

// Phase 2: layer navigation, isolation, and contextual arrange panel.
let isolation=null;
function orderedIds(){const map=activeMap();return Object.keys(map).filter(id=>map[id]?.visible!==false).sort((a,b)=>(Number(map[b]?.zIndex)||0)-(Number(map[a]?.zIndex)||0))}
function selectRelative(delta){const ids=orderedIds();if(!ids.length)return false;const current=selectedIds()[0],index=Math.max(0,ids.indexOf(current));bridge.select([ids[clamp(index+delta,0,ids.length-1)]]);return true}
function toggleIsolation(){const map=activeMap(),ids=selectedIds();if(isolation){bridge.transact('Exit layer isolation',doc=>{const next=activeMap(doc);for(const[id,value]of Object.entries(isolation))if(next[id])next[id].visible=value},{capture:false});isolation=null;document.body.classList.remove('v23-layer-isolation');announce('Layer isolation ended');return true}if(!ids.length)return false;isolation=Object.fromEntries(Object.entries(map).map(([id,o])=>[id,o.visible!==false]));const keep=new Set(ids);bridge.transact('Isolate selected layers',doc=>{const next=activeMap(doc);for(const[id,o]of Object.entries(next))o.visible=keep.has(id)},{capture:false});document.body.classList.add('v23-layer-isolation');announce('Selected layers isolated');return true}
function ensureArrangePanel(){let panel=$('#v23ArrangePanel');if(panel)return panel;panel=document.createElement('section');panel.id='v23ArrangePanel';panel.className='v23-arrange-panel';panel.hidden=true;panel.setAttribute('aria-label','Position and arrange');panel.innerHTML=`<header><strong>Position & Arrange</strong><button type="button" data-close aria-label="Close">×</button></header><div class="v23-arrange-grid"><button data-command-id="align.left">Left</button><button data-command-id="align.center">Center</button><button data-command-id="align.right">Right</button><button data-command-id="align.top">Top</button><button data-command-id="align.middle">Middle</button><button data-command-id="align.bottom">Bottom</button></div><div class="v23-arrange-grid"><button data-command-id="arrange.front">Front</button><button data-command-id="arrange.forward">Forward</button><button data-command-id="arrange.backward">Backward</button><button data-command-id="arrange.back">Back</button></div><div class="v23-arrange-grid"><button data-command-id="distribute.horizontal">Space H</button><button data-command-id="distribute.vertical">Space V</button><button data-command-id="layer.isolate">Isolate</button></div>`;document.body.append(panel);panel.querySelector('[data-close]').onclick=()=>panel.hidden=true;return panel}
function toggleArrange(){const panel=ensureArrangePanel();panel.hidden=!panel.hidden;if(!panel.hidden)panel.querySelector('button:not([data-close])')?.focus();return true}

// Phase 3: page and workspace navigation.
function pages(){return bridge.getState()?.designPages||[]}
function activePageIndex(){const id=window.EInvitePageExperience?.activePageId;return pages().findIndex(p=>p.id===id)}
function activatePage(index){const list=pages();if(!list.length)return false;const page=list[clamp(index,0,list.length-1)];const chip=document.querySelector(`[data-page-id="${CSS.escape(page.id)}"]`);if(chip){chip.click();return true}if(typeof window.setActiveDesignPage==='function'){window.setActiveDesignPage(page.id);return true}return false}
function pageStep(delta){const i=activePageIndex();return activatePage(i<0?(delta>0?0:pages().length-1):i+delta)}
function reorderActivePage(delta){const api=window.EInvitePageExperience,i=activePageIndex(),list=pages();if(!api||i<0)return false;return api.reorderPage(list[i].id,clamp(i+delta,0,list.length-1))}
function cycleWorkspace(delta){const tabs=$$('[data-inspector-tab]:not([hidden])');if(!tabs.length)return false;const active=tabs.findIndex(t=>t.classList.contains('active')||t.getAttribute('aria-selected')==='true'),next=tabs[(active+delta+tabs.length)%tabs.length];next?.click();next?.focus();return!!next}

// Phase 4: guides, frame replacement, and crop positioning.
let guides={visible:false,snap:true,rulers:false};
function assistanceButton(key){return document.querySelector(`[data-pe-toggle="${key}"]`)}
function toggleAssistance(key){const button=assistanceButton(key);if(!button)return false;button.click();const value=button.getAttribute('aria-pressed')==='true';guides[key]=value;announce(`${key[0].toUpperCase()+key.slice(1)} ${value?'enabled':'disabled'}`);return true}
function toggleGuides(){return toggleAssistance('guides')}
function toggleRulers(){return toggleAssistance('rulers')}
function toggleSnap(){return toggleAssistance('snap')}
function selectedImage(){const el=selectedElements()[0];return el?.dataset.type==='image'||el?.querySelector('img')?el:null}
let cropSession=null,cropTimer=0;
function previewCrop(id,x,y){const el=stage.querySelector(`.object[data-id="${CSS.escape(id)}"]`),img=el?.querySelector('img');if(img)img.style.objectPosition=`${x}% ${y}%`}
function flushCrop(){clearTimeout(cropTimer);cropTimer=0;if(!cropSession)return false;const session=cropSession;cropSession=null;if(session.x===session.startX&&session.y===session.startY)return true;bridge.transact('Adjust image crop',doc=>{const item=activeMap(doc)[session.id];if(item){item.imagePositionX=session.x;item.imagePositionY=session.y;item.imagePosition=`${session.x}% ${session.y}%`;item.objectPosition=item.imagePosition}},{capture:false});announce(`Image position ${Math.round(session.x)}%, ${Math.round(session.y)}%`);return true}
function adjustImagePosition(dx,dy){const el=selectedImage();if(!el)return false;const id=el.dataset.id,map=activeMap(),o=map[id];if(!o)return false;if(!cropSession||cropSession.id!==id){flushCrop();const current=String(o.imagePosition||o.objectPosition||`${o.imagePositionX??50}% ${o.imagePositionY??50}%`).match(/([\d.]+)%\s+([\d.]+)%/),x=Number(current?.[1]||50),y=Number(current?.[2]||50);cropSession={id,startX:x,startY:y,x,y}}
cropSession.x=clamp(cropSession.x+dx,0,100);cropSession.y=clamp(cropSession.y+dy,0,100);previewCrop(id,cropSession.x,cropSession.y);clearTimeout(cropTimer);cropTimer=setTimeout(flushCrop,220);return true}
function replaceFrame(){const el=selectedImage();if(!el)return false;if(typeof window.openMaterialPicker==='function'){window.openMaterialPicker('Replace frame image',(url,asset)=>{const id=el.dataset.id;bridge.transact('Replace frame image',doc=>{const item=activeMap(doc)[id];if(item){item.src=url;item.assetId=asset?.id||item.assetId||'';item.framePlaceholder=false}},{capture:false})});return true}el.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));return true}

const commands=[
{id:'transform.mode',title:'Enter keyboard transform mode',category:'Transform',bindings:{standard:['Mod+T'],canva:['Mod+T'],photoshop:['Mod+T']},enabled:()=>selectedIds().length>0,run:startTransform},
{id:'transform.commit',title:'Commit transform',category:'Transform',bindings:{standard:['Enter'],canva:['Enter'],photoshop:['Enter']},visible:()=>!!transform,enabled:()=>!!transform,allowWhileTyping:false,run:commitTransform},
{id:'transform.resizeLeft',title:'Reduce selection width',category:'Transform',bindings:{standard:['Alt+ArrowLeft'],canva:['Alt+ArrowLeft'],photoshop:['Alt+ArrowLeft']},enabled:()=>selectedIds().length>0,repeatable:true,run:e=>resizeTransform(-(e.event?.shiftKey?5:1),0)},
{id:'transform.resizeRight',title:'Increase selection width',category:'Transform',bindings:{standard:['Alt+ArrowRight'],canva:['Alt+ArrowRight'],photoshop:['Alt+ArrowRight']},enabled:()=>selectedIds().length>0,repeatable:true,run:e=>resizeTransform(e.event?.shiftKey?5:1,0)},
{id:'transform.resizeUp',title:'Reduce selection height',category:'Transform',bindings:{standard:['Alt+ArrowUp'],canva:['Alt+ArrowUp'],photoshop:['Alt+ArrowUp']},enabled:()=>selectedIds().length>0,repeatable:true,run:e=>resizeTransform(0,-(e.event?.shiftKey?5:1))},
{id:'transform.resizeDown',title:'Increase selection height',category:'Transform',bindings:{standard:['Alt+ArrowDown'],canva:['Alt+ArrowDown'],photoshop:['Alt+ArrowDown']},enabled:()=>selectedIds().length>0,repeatable:true,run:e=>resizeTransform(0,e.event?.shiftKey?5:1)},
{id:'transform.rotateLeft',title:'Rotate selection left',category:'Transform',bindings:{standard:['Mod+Alt+ArrowLeft'],canva:['Mod+Alt+ArrowLeft'],photoshop:['Mod+Alt+ArrowLeft']},enabled:()=>selectedIds().length>0,repeatable:true,run:e=>rotateTransform(-(e.event?.shiftKey?15:1))},
{id:'transform.rotateRight',title:'Rotate selection right',category:'Transform',bindings:{standard:['Mod+Alt+ArrowRight'],canva:['Mod+Alt+ArrowRight'],photoshop:['Mod+Alt+ArrowRight']},enabled:()=>selectedIds().length>0,repeatable:true,run:e=>rotateTransform(e.event?.shiftKey?15:1)},
{id:'layer.selectAbove',title:'Select layer above',category:'Layers',bindings:{standard:['Alt+PageUp'],canva:['Alt+PageUp'],photoshop:['Alt+PageUp']},run:()=>selectRelative(-1)},
{id:'layer.selectBelow',title:'Select layer below',category:'Layers',bindings:{standard:['Alt+PageDown'],canva:['Alt+PageDown'],photoshop:['Alt+PageDown']},run:()=>selectRelative(1)},
{id:'layer.isolate',title:'Isolate selected layers',category:'Layers',bindings:{standard:['Alt+Shift+I'],canva:['Alt+Shift+I'],photoshop:['Alt+Shift+I']},enabled:()=>selectedIds().length>0||!!isolation,run:toggleIsolation},
{id:'workspace.arrangePanel',title:'Open Position and Arrange panel',category:'Arrange',bindings:{standard:['Alt+Shift+P'],canva:['Alt+Shift+P'],photoshop:['Alt+Shift+P']},run:toggleArrange},
...['left','center','right','top','middle','bottom'].map(mode=>({id:`align.${mode}`,title:`Align ${mode}`,category:'Arrange',bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>selectedIds().length>0,run:()=>window.EInviteProfessionalEditor?.commands?.alignSelection?.(mode)})),
...['horizontal','vertical'].map(axis=>({id:`distribute.${axis}`,title:`Distribute ${axis}`,category:'Arrange',bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>selectedIds().length>2,run:()=>window.EInviteProfessionalEditor?.commands?.distributeSelection?.(axis)})),
{id:'page.previous',title:'Previous design page',category:'Pages',bindings:{standard:['PageUp'],canva:['PageUp'],photoshop:['PageUp']},repeatable:true,run:()=>pageStep(-1)},
{id:'page.next',title:'Next design page',category:'Pages',bindings:{standard:['PageDown'],canva:['PageDown'],photoshop:['PageDown']},repeatable:true,run:()=>pageStep(1)},
{id:'page.movePrevious',title:'Move page earlier',category:'Pages',bindings:{standard:['Shift+PageUp'],canva:['Shift+PageUp'],photoshop:['Shift+PageUp']},run:()=>reorderActivePage(-1)},
{id:'page.moveNext',title:'Move page later',category:'Pages',bindings:{standard:['Shift+PageDown'],canva:['Shift+PageDown'],photoshop:['Shift+PageDown']},run:()=>reorderActivePage(1)},
{id:'workspace.previousPanel',title:'Previous workspace panel',category:'Navigate',bindings:{standard:['Ctrl+Shift+Tab'],canva:['Ctrl+Shift+Tab'],photoshop:['Ctrl+Shift+Tab']},run:()=>cycleWorkspace(-1)},
{id:'workspace.nextPanel',title:'Next workspace panel',category:'Navigate',bindings:{standard:['Ctrl+Tab'],canva:['Ctrl+Tab'],photoshop:['Ctrl+Tab']},run:()=>cycleWorkspace(1)},
{id:'view.rulers',title:'Show or hide rulers',category:'View',bindings:{standard:['Mod+R'],canva:['Mod+R'],photoshop:['Mod+R']},run:toggleRulers},
{id:'view.guides',title:'Show or hide canvas guides',category:'View',bindings:{standard:['Mod+;'],canva:['Mod+;'],photoshop:['Mod+;']},run:toggleGuides},
{id:'view.snapGuides',title:'Toggle guide snapping',category:'View',bindings:{standard:['Mod+Shift+;'],canva:['Mod+Shift+;'],photoshop:['Mod+Shift+;']},run:toggleSnap},
{id:'image.replaceFrame',title:'Replace selected frame image',category:'Image',bindings:{standard:[],canva:[],photoshop:[]},enabled:()=>!!selectedImage(),run:replaceFrame},
{id:'image.cropLeft',title:'Move image left inside frame',category:'Image',bindings:{standard:['Mod+Shift+ArrowLeft'],canva:['Mod+Shift+ArrowLeft'],photoshop:['Mod+Shift+ArrowLeft']},enabled:()=>!!selectedImage(),repeatable:true,run:()=>adjustImagePosition(-2,0)},
{id:'image.cropRight',title:'Move image right inside frame',category:'Image',bindings:{standard:['Mod+Shift+ArrowRight'],canva:['Mod+Shift+ArrowRight'],photoshop:['Mod+Shift+ArrowRight']},enabled:()=>!!selectedImage(),repeatable:true,run:()=>adjustImagePosition(2,0)},
{id:'image.cropUp',title:'Move image up inside frame',category:'Image',bindings:{standard:['Mod+Shift+ArrowUp'],canva:['Mod+Shift+ArrowUp'],photoshop:['Mod+Shift+ArrowUp']},enabled:()=>!!selectedImage(),repeatable:true,run:()=>adjustImagePosition(0,-2)},
{id:'image.cropDown',title:'Move image down inside frame',category:'Image',bindings:{standard:['Mod+Shift+ArrowDown'],canva:['Mod+Shift+ArrowDown'],photoshop:['Mod+Shift+ArrowDown']},enabled:()=>!!selectedImage(),repeatable:true,run:()=>adjustImagePosition(0,2)}
];
registry.registerMany(commands);
// Refine existing movement commands so transform mode previews rather than creating many history entries.
for(const [id,dx,dy] of [['move.left',-1,0],['move.right',1,0],['move.up',0,-1],['move.down',0,1]]){const old=registry.get(id);if(old){registry.unregister(id);registry.register({...old,run:ctx=>transform?nudgeTransform(dx*(ctx.event?.shiftKey?10:1),dy*(ctx.event?.shiftKey?10:1)):window.EInviteProfessionalEditor?.commands?.nudge?.(dx*(ctx.event?.shiftKey?10:1),dy*(ctx.event?.shiftKey?10:1))})}}
// Extend Escape without adding another key listener.
window.EInviteProfessionalWorkflow={version:23.1,transform:{start:startTransform,commit:commitTransform,cancel:cancelTransform,nudge:nudgeTransform,resize:resizeTransform,rotate:rotateTransform,get active(){return!!transform}},layers:{toggleIsolation,selectRelative,get isolated(){return!!isolation}},pages:{step:pageStep,reorder:reorderActivePage},guides:{toggle:toggleGuides,toggleRulers,toggleSnap,get state(){return{...guides}}},images:{adjustPosition:adjustImagePosition,replaceFrame},toggleArrange};
window.addEventListener('einvite:state-applied',()=>{if(transform)cancelTransform()});document.addEventListener('einvite:selection-changed',()=>{if(cropSession&&cropSession.id!==selectedIds()[0])flushCrop()});
window.EInviteLifecycle?.add?.(()=>{flushCrop();cancelTransform();$('#v23ArrangePanel')?.remove();$('#v23TransformHud')?.remove();$('#v23WorkflowLive')?.remove()});
document.body.classList.add('professional-workflow-v23');
})();
