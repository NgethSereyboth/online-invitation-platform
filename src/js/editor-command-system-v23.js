(()=>{
'use strict';
if(window.EInviteCommandRegistry)return;
const PROFILE_KEY='einvite-shortcut-profile-v23';
const OVERRIDE_KEY='einvite-shortcut-overrides-v23';
const DEFAULT_PROFILE='standard',PROFILES=['standard','canva','photoshop'];
const commands=new Map(),subscribers=new Set(),buttonBypass=new WeakSet();
let activeProfile=localStorage.getItem(PROFILE_KEY)||DEFAULT_PROFILE;if(!PROFILES.includes(activeProfile))activeProfile=DEFAULT_PROFILE;
let overrides=readJson(OVERRIDE_KEY,{}),bindings=new Map(),conflicts=[];
let uiPromise=null,panHeld=false;
const lifecycle=window.EInviteLifecycle;
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const clone=v=>{try{return structuredClone(v)}catch{return JSON.parse(JSON.stringify(v))}};
function readJson(key,fallback){try{return JSON.parse(localStorage.getItem(key)||'null')??fallback}catch{return fallback}}
function notify(type,detail={}){const payload={type,...detail};subscribers.forEach(fn=>{try{fn(payload)}catch{}});dispatchEvent(new CustomEvent('einvite:command-system',{detail:payload}))}
function normalizeCommand(input){
if(!input||typeof input!=='object'||!input.id)throw Error('Command id');
return Object.freeze({
title:input.id,category:'General',keywords:[],visible:()=>true,enabled:()=>true,bindings:{},allowFromControls:false,...input,
keywords:Array.isArray(input.keywords)?input.keywords:String(input.keywords||'').split(/\s+/).filter(Boolean)
});
}
function register(input){const command=normalizeCommand(input);if(commands.has(command.id))throw Error('Duplicate command');commands.set(command.id,command);rebuildBindings();notify('registered',{commandId:command.id});return()=>{commands.delete(command.id);rebuildBindings();notify('unregistered',{commandId:command.id})}}
function registerMany(list){const next=list.map(normalizeCommand),ids=next.map(x=>x.id);if(new Set(ids).size!==ids.length||ids.some(id=>commands.has(id)))throw Error('Duplicate command');for(const command of next)commands.set(command.id,command);rebuildBindings();notify('registered');return ids.map(id=>()=>unregister(id))}
function unregister(id){const existed=commands.delete(id);if(existed){rebuildBindings();notify('unregistered',{commandId:id})}return existed}
function context(event=null){return{event,profile:activeProfile,selection:window.EInviteEditorBridge?.getSelectedIds?.()||[],state:window.EInviteEditorBridge?.getState?.()||window.state||null,stage:$('#stage'),activeElement:document.activeElement}}
function commandState(command,ctx=context()){let visible=true,enabled=true;try{visible=command.visible(ctx)!==false}catch{visible=false}try{enabled=visible&&command.enabled(ctx)!==false}catch{enabled=false}return{visible,enabled}}
async function execute(id,options={}){const command=commands.get(id);if(!command)return false;const ctx={...context(options.event),...options.context};const state=commandState(command,ctx);if(!state.enabled)return false;try{const result=await command.run(ctx);notify('executed',{commandId:id,result});return result!==false}catch(error){console.error('[V23 command]',id,error);window.uiToast?.(error?.message||`Unable to run ${command.title}`,'!');notify('error',{commandId:id,error});return false}}
function list(options={}){const ctx=options.context||context();return[...commands.values()].filter(c=>options.includeHidden||commandState(c,ctx).visible).map(c=>({...c,state:commandState(c,ctx),shortcuts:getShortcuts(c.id,options.profile||activeProfile)}))}
function subscribe(fn){subscribers.add(fn);return()=>subscribers.delete(fn)}
function canonicalKey(raw){const key=String(raw||'');const aliases={' ':'Space','Spacebar':'Space','Esc':'Escape','Del':'Delete','Left':'ArrowLeft','Right':'ArrowRight','Up':'ArrowUp','Down':'ArrowDown','OS':'Meta','Command':'Meta','Control':'Ctrl','Option':'Alt','Plus':'=','+':'=','Add':'=','Subtract':'-'};if(aliases[key])return aliases[key];if(key.length===1)return key.toUpperCase();return key}
function canonicalChord(value){
if(!value)return'';const parts=String(value).split('+').map(x=>x.trim()).filter(Boolean),mods=new Set();let key='';
for(const part of parts){const p=part.toLowerCase();if(['mod','cmdorctrl','ctrlorcmd'].includes(p))mods.add('Mod');else if(['ctrl','control'].includes(p))mods.add('Ctrl');else if(['meta','cmd','command'].includes(p))mods.add('Meta');else if(['alt','option'].includes(p))mods.add('Alt');else if(p==='shift')mods.add('Shift');else key=canonicalKey(part)}
return['Mod','Ctrl','Meta','Alt','Shift'].filter(x=>mods.has(x)).concat(key||[]).join('+');
}
function eventChord(event){const parts=[];if(event.ctrlKey||event.metaKey)parts.push('Mod');if(event.altKey)parts.push('Alt');if(event.shiftKey)parts.push('Shift');const key=canonicalKey(event.key);if(!['Control','Ctrl','Meta','Alt','Shift'].includes(key))parts.push(key);return parts.join('+')}
function profileBindings(command,profile=activeProfile){const custom=overrides?.[profile]?.[command.id];const source=custom!==undefined?custom:(command.bindings?.[profile]??command.bindings?.standard??[]);return(Array.isArray(source)?source:[source]).map(canonicalChord).filter(Boolean)}
function getShortcuts(id,profile=activeProfile){const command=commands.get(id);return command?profileBindings(command,profile):[]}
function rebuildBindings(){bindings=new Map();conflicts=[];for(const command of commands.values())for(const chord of profileBindings(command)){if(bindings.has(chord)){conflicts.push({chord,commands:[bindings.get(chord),command.id]});continue}bindings.set(chord,command.id)}notify('bindings',{profile:activeProfile,conflicts:clone(conflicts)})}
function validateOverride(profile,commandId,shortcuts){const next=clone(overrides);next[profile]={...(next[profile]||{}),[commandId]:(Array.isArray(shortcuts)?shortcuts:[shortcuts]).map(canonicalChord).filter(Boolean)};const seen=new Map(),found=[];for(const command of commands.values()){const source=next?.[profile]?.[command.id]??command.bindings?.[profile]??command.bindings?.standard??[];for(const chord of(Array.isArray(source)?source:[source]).map(canonicalChord).filter(Boolean)){if(seen.has(chord)&&seen.get(chord)!==command.id)found.push({chord,commands:[seen.get(chord),command.id]});else seen.set(chord,command.id)}}return found}
function setOverride(commandId,shortcuts,{profile=activeProfile,allowConflicts=false}={}){if(!commands.has(commandId))throw Error('Unknown');const next=(Array.isArray(shortcuts)?shortcuts:[shortcuts]).map(canonicalChord).filter(Boolean),found=validateOverride(profile,commandId,next);if(found.length&&!allowConflicts)return{ok:false,conflicts:found};overrides[profile]={...(overrides[profile]||{}),[commandId]:next};localStorage.setItem(OVERRIDE_KEY,JSON.stringify(overrides));rebuildBindings();queueMicrotask(bindButtons);return{ok:true,conflicts:found}}
function resetOverrides(profile=activeProfile){delete overrides[profile];localStorage.setItem(OVERRIDE_KEY,JSON.stringify(overrides));rebuildBindings();queueMicrotask(bindButtons);notify('overrides-reset',{profile})}
function setProfile(profile){if(!PROFILES.includes(profile))throw Error('Unknown profile');activeProfile=profile;localStorage.setItem(PROFILE_KEY,profile);rebuildBindings();queueMicrotask(bindButtons);notify('profile',{profile});return profile}
function isTypingTarget(target){return!!target&&(target.matches?.('input,textarea,select,[contenteditable="true"]')||target.isContentEditable||!!target.closest?.('.content[data-rich-text-controlled="true"],.rt-document[contenteditable="true"]'))}
function canvasKeyboardContext(event){const target=event?.target,active=document.activeElement;if(isTypingTarget(target)||isTypingTarget(active))return false;return document.body.dataset.keyboardOwner==='canvas'&&(!active||active===document.body||active.matches?.('#stage,#canvasViewport,.stage-wrap')||active.closest?.('#stage,#canvasViewport,.stage-wrap'))}
function isLocalShortcutTarget(target,event){if(!target)return false;if(target.closest?.('.v23-command-surface[data-capturing="true"]'))return true;if(target.closest?.('.pe-layer-row')&&(event.key==='F2'||event.altKey&&['ArrowUp','ArrowDown','Home','End'].includes(event.key)))return true;if(target.closest?.('[role="menu"],.workflow-v4-popover,.v22-page-menu')&&['ArrowDown','ArrowUp','Home','End','Enter',' '].includes(event.key))return true;return false}
function panelsHidden(){return document.body.classList.contains('v23-panels-hidden')}
function setPanelsHidden(value,{sideOnly=false}={}){document.body.classList.toggle(sideOnly?'v23-side-panels-hidden':'v23-panels-hidden',value);if(!sideOnly&&value)document.body.classList.remove('v23-side-panels-hidden');notify('workspace-panels',{hidden:value,sideOnly})}
function clickNative(selector){const el=typeof selector==='string'?$(selector):selector;if(!el)return false;buttonBypass.add(el);try{el.click();return true}finally{queueMicrotask(()=>buttonBypass.delete(el))}}
function selected(){return window.EInviteEditorBridge?.getSelectedIds?.()||[]}
function pro(name,...args){const fn=window.EInviteProfessionalEditor?.commands?.[name];return typeof fn==='function'?fn(...args):false}
function selectAll(){const ids=$$('#stage .object').filter(el=>el.dataset.visible!=='false'&&el.dataset.locked!=='true').map(el=>el.dataset.id).filter(Boolean);window.EInviteEditorBridge?.select?.(ids);return!!ids.length}
function setZoom(value){const input=$('#zoomLevel');if(!input)return false;input.value=String(value);input.dispatchEvent(new Event('change',{bubbles:true}));return true}
function adjustZoom(delta){const input=$('#zoomLevel');return input?setZoom(Math.max(.25,Math.min(4,Number(input.value||1)+delta))):false}
function activateTool(tool){if(window.EInviteToolController?.setTool)return window.EInviteToolController.setTool(tool);return clickNative(`[data-tool="${CSS.escape(tool)}"]`)}
function toggleSelectedFlag(key){const ids=selected();if(!ids.length)return false;const state=window.EInviteEditorBridge?.getState?.(),canvasId=window.EInviteEditorBridge?.getActiveCanvasId?.()||'hero';let map=state?.objects||{};if(canvasId!=='hero'){const page=(state?.designPages||[]).find(p=>`page:${p.id}`===canvasId);map=page?.objects||{}}const all=ids.every(id=>key==='visible'?map[id]?.visible!==false:map[id]?.[key]===true);return pro('setObjectFlag',ids,key,!all)}
function closeTopLayer(){
if(window.EInviteProfessionalWorkflow?.transform?.active){window.EInviteProfessionalWorkflow.transform.cancel();return true}
const dialog=$$('dialog[open]').at(-1);if(dialog){dialog.close?.();return true}
const palette=$('.v23-command-surface:not([hidden])');if(palette){window.EInviteCommandUI?.close?.();return true}
if(window.EInvitePageExperience?.menuOpen){window.EInvitePageExperience.closeMenu();return true}
const pageMenu=$('.workflow-v4-popover.open');if(pageMenu){pageMenu.classList.remove('open');pageMenu.hidden=true;return true}
const context=$('.ui-context-menu:not([hidden]),.ei-context-menu:not([hidden]),#workflowV5ContextMenu.open');if(context){context.hidden=true;context.classList.remove('open');return true}
const flow=$('#workflowV6Flow.open');if(flow){flow.classList.remove('open');return true}
const position=$('#workflowV6Position.open');if(position){position.classList.remove('open');return true}
if(document.body.classList.contains('inspector-open')){document.body.classList.remove('inspector-open');return true}
if(selected().length){window.EInviteEditorBridge?.select?.([]);return true}
return false;
}
function panStart(){if(panHeld)return true;panHeld=true;document.body.dataset.v23SpacePan='true';return window.EInviteCanvasPanController?.holdStart?.()??true}
function panEnd(){if(!panHeld)return false;panHeld=false;delete document.body.dataset.v23SpacePan;return window.EInviteCanvasPanController?.holdEnd?.()??true}
function openUI(mode='commands'){return loadUI().then(ui=>ui.open(mode))}
function loadUI(){if(window.EInviteCommandUI)return Promise.resolve(window.EInviteCommandUI);if(uiPromise)return uiPromise;uiPromise=new Promise((resolve,reject)=>{if(!document.querySelector('link[data-v23-command-ui]')){const l=document.createElement('link');l.rel='stylesheet';l.href='command-palette-v23.css';l.dataset.v23CommandUi='1';document.head.append(l)}const s=document.createElement('script');s.src='command-palette-v23.js';s.dataset.v23CommandUi='1';s.onload=()=>resolve(window.EInviteCommandUI);s.onerror=()=>{uiPromise=null;reject(Error('Load failed'))};document.head.append(s)});return uiPromise}
function addDefaults(){registerMany([
{id:'ui.quickActions',title:'Open Quick Actions',category:'Workspace',keywords:['search','commands','palette'],bindings:{standard:['Mod+K','/'],canva:['Mod+K','/'],photoshop:['Mod+K','/']},allowWhileTyping:false,run:()=>openUI('commands')},
{id:'ui.shortcutSettings',title:'Keyboard shortcuts and profiles',category:'Workspace',keywords:['keys','profiles','settings'],bindings:{standard:['?','Shift+?'],canva:['?','Shift+?'],photoshop:['?','Shift+?']},run:()=>openUI('shortcuts')},
{id:'ui.escape',title:'Cancel or close',category:'Workspace',bindings:{standard:['Escape'],canva:['Escape'],photoshop:['Escape']},repeatable:true,run:()=>closeTopLayer()},
{id:'history.undo',title:'Undo',category:'Edit',allowWhileTyping:true,bindings:{standard:['Mod+Z'],canva:['Mod+Z'],photoshop:['Mod+Z']},run:()=>pro('undoSelection')||(typeof window.EInviteEditorBridge?.undo==='function'?window.EInviteEditorBridge.undo():clickNative('#undoBtn'))},
{id:'history.redo',title:'Redo',category:'Edit',allowWhileTyping:true,bindings:{standard:['Mod+Shift+Z','Mod+Y'],canva:['Mod+Shift+Z','Mod+Y'],photoshop:['Mod+Shift+Z','Mod+Y']},run:()=>pro('redoSelection')||(typeof window.EInviteEditorBridge?.redo==='function'?window.EInviteEditorBridge.redo():clickNative('#redoBtn'))},
{id:'edit.copy',title:'Copy selection',category:'Edit',bindings:{standard:['Mod+C'],canva:['Mod+C'],photoshop:['Mod+C']},enabled:()=>selected().length>0,run:()=>pro('copySelection')||window.EInviteCommands?.copySelection?.()},
{id:'edit.cut',title:'Cut selection',category:'Edit',bindings:{standard:['Mod+X'],canva:['Mod+X'],photoshop:['Mod+X']},enabled:()=>selected().length>0,run:()=>pro('cutSelection')},
{id:'edit.paste',title:'Paste',category:'Edit',bindings:{standard:['Mod+V'],canva:['Mod+V'],photoshop:['Mod+V']},run:()=>pro('pasteSelection')||window.EInviteCommands?.pasteSelection?.()},
{id:'edit.duplicate',title:'Duplicate selection',category:'Edit',bindings:{standard:['Mod+D','Mod+J'],canva:['Mod+D'],photoshop:['Mod+J']},enabled:()=>selected().length>0,run:()=>pro('duplicateSelection')||window.EInviteCommands?.duplicate?.()},
{id:'edit.delete',title:'Delete selection',category:'Edit',bindings:{standard:['Delete','Backspace'],canva:['Delete','Backspace'],photoshop:['Delete','Backspace']},enabled:()=>selected().length>0,run:()=>pro('deleteSelection')},
{id:'edit.selectAll',title:'Select all objects',category:'Selection',bindings:{standard:['Mod+A'],canva:['Mod+A'],photoshop:['Mod+A']},run:selectAll},
{id:'edit.deselect',title:'Deselect objects',category:'Selection',bindings:{standard:[],canva:[],photoshop:['Mod+D']},enabled:()=>selected().length>0,run:()=>window.EInviteEditorBridge?.select?.([])},
{id:'edit.copyStyle',title:'Copy object style',category:'Edit',bindings:{standard:['Mod+Shift+C'],canva:['Mod+Alt+C'],photoshop:['Mod+Shift+C']},enabled:()=>selected().length>0,run:()=>window.EInviteCommands?.copyStyle?.()},
{id:'edit.pasteStyle',title:'Paste object style',category:'Edit',bindings:{standard:['Mod+Shift+V'],canva:['Mod+Alt+V'],photoshop:['Mod+Shift+V']},enabled:()=>selected().length>0,run:()=>window.EInviteCommands?.pasteStyle?.()},
{id:'object.group',title:'Group selection',category:'Arrange',bindings:{standard:['Mod+G'],canva:['Mod+G'],photoshop:['Mod+G']},enabled:()=>selected().length>1,run:()=>pro('groupSelection')},
{id:'object.ungroup',title:'Ungroup selection',category:'Arrange',bindings:{standard:['Mod+Shift+G'],canva:['Mod+Shift+G'],photoshop:['Mod+Shift+G']},enabled:()=>selected().length>0,run:()=>pro('ungroupSelection')},
{id:'object.toggleLock',title:'Lock or unlock selection',category:'Arrange',bindings:{standard:['Mod+Alt+L'],canva:['Mod+Alt+L'],photoshop:['Mod+/']},enabled:()=>selected().length>0,run:()=>toggleSelectedFlag('locked')},
{id:'object.toggleVisibility',title:'Hide or show selection',category:'Arrange',bindings:{standard:['Mod+,'],canva:['Mod+,'],photoshop:['Mod+,']},enabled:()=>selected().length>0,run:()=>toggleSelectedFlag('visible')},
{id:'arrange.backward',title:'Send backward',category:'Arrange',bindings:{standard:['Mod+['],canva:['Mod+['],photoshop:['Mod+[']},enabled:()=>selected().length>0,run:()=>pro('reorder',selected(),'backward')},
{id:'arrange.forward',title:'Bring forward',category:'Arrange',bindings:{standard:['Mod+]'],canva:['Mod+]'],photoshop:['Mod+]']},enabled:()=>selected().length>0,run:()=>pro('reorder',selected(),'forward')},
{id:'arrange.back',title:'Send to back',category:'Arrange',bindings:{standard:['Mod+Shift+['],canva:['Mod+Shift+['],photoshop:['Mod+Shift+[']},enabled:()=>selected().length>0,run:()=>pro('reorder',selected(),'back')},
{id:'arrange.front',title:'Bring to front',category:'Arrange',bindings:{standard:['Mod+Shift+]'],canva:['Mod+Shift+]'],photoshop:['Mod+Shift+]']},enabled:()=>selected().length>0,run:()=>pro('reorder',selected(),'front')},
...[['left','ArrowLeft',-1,0],['right','ArrowRight',1,0],['up','ArrowUp',0,-1],['down','ArrowDown',0,1]].map(([name,key,dx,dy])=>({id:`move.${name}`,title:`Move selection ${name}`,category:'Transform',bindings:{standard:[key,`Shift+${key}`],canva:[key,`Shift+${key}`],photoshop:[key,`Shift+${key}`]},enabled:()=>selected().length>0,repeatable:true,run:ctx=>pro('nudge',dx*(ctx.event?.shiftKey?10:1),dy*(ctx.event?.shiftKey?10:1))})),
{id:'canvas.zoomIn',title:'Zoom in',category:'Canvas',bindings:{standard:['Mod+=','Mod+Shift+='],canva:['Mod+=','Mod+Shift+='],photoshop:['Mod+=','Mod+Shift+=']},repeatable:true,run:()=>adjustZoom(.25)},
{id:'canvas.zoomOut',title:'Zoom out',category:'Canvas',bindings:{standard:['Mod+-'],canva:['Mod+-'],photoshop:['Mod+-']},repeatable:true,run:()=>adjustZoom(-.25)},
{id:'canvas.fit',title:'Fit canvas to workspace',category:'Canvas',bindings:{standard:['Mod+0'],canva:['Mod+0'],photoshop:['Mod+0']},run:()=>clickNative('#fitCanvas')},
{id:'canvas.actualSize',title:'Zoom to 100%',category:'Canvas',bindings:{standard:['Mod+1'],canva:['Mod+1'],photoshop:['Mod+1']},run:()=>setZoom(1)},
{id:'canvas.panHold',title:'Temporarily pan canvas',category:'Canvas',bindings:{standard:['Space'],canva:['Space'],photoshop:['Space']},repeatable:true,run:panStart,onRelease:panEnd},
{id:'workspace.hidePanels',title:'Hide or show all panels',category:'Workspace',bindings:{standard:['Tab'],canva:['Tab'],photoshop:['Tab']},run:()=>setPanelsHidden(!panelsHidden())},
{id:'workspace.hideSidePanels',title:'Hide or show side panels',category:'Workspace',bindings:{standard:['Shift+Tab'],canva:['Shift+Tab'],photoshop:['Shift+Tab']},run:()=>setPanelsHidden(!document.body.classList.contains('v23-side-panels-hidden'),{sideOnly:true})},
{id:'workspace.focusMode',title:'Toggle focus mode',category:'Workspace',allowFromControls:true,bindings:{standard:['Shift+F'],canva:['Shift+F'],photoshop:['Shift+F']},run:()=>clickNative('#workflowV5Focus')||clickNative('#focusModeBtn')},
...[['select','V'],['text','T'],['frame','F'],['rect','R'],['ellipse','O'],['line','L'],['hand','H'],['zoom','Z']].map(([tool,key])=>({id:`tool.${tool}`,title:`${tool[0].toUpperCase()+tool.slice(1)} tool`,category:'Tools',bindings:{standard:[key],canva:[key],photoshop:[key]},run:()=>activateTool(tool)})),
{id:'page.addBlank',title:'Add blank design page',category:'Pages',bindings:{standard:['Mod+Enter'],canva:['Mod+Enter'],photoshop:['Mod+Enter']},run:()=>window.EInvitePageExperience?.addPage?.({mode:'free-design'})},
{id:'workspace.quickAdd',title:'Open Quick Add',category:'Insert',bindings:{standard:['Mod+/'],canva:['Mod+/'],photoshop:['Mod+Alt+/']},run:()=>window.EInviteWorkflowV4?.openQuickAdd?.()},
...[['design','1'],['elements','2','Shift+E'],['text','3','Shift+T'],['media','4','Shift+U'],['pages','5'],['event','6'],['blocks','7']].map(([section,key,legacy])=>({id:`workspace.${section}`,title:`Open ${section} panel`,category:'Navigate',allowFromControls:true,bindings:{standard:[`Alt+${key}`,legacy].filter(Boolean),canva:[`Alt+${key}`,legacy].filter(Boolean),photoshop:[`Alt+${key}`,legacy].filter(Boolean)},run:()=>window.EInviteWorkflow?.navigate?.(section,{source:'command'})})),
{id:'workspace.toggleInspector',title:'Toggle inspector',category:'Workspace',bindings:{standard:['Alt+I'],canva:['Alt+I'],photoshop:['Alt+I']},run:()=>clickNative('.studio-panel-toggle[aria-label="Toggle inspector"]')},
{id:'workspace.toggleCreation',title:'Toggle creation panel',category:'Workspace',bindings:{standard:['Alt+['],canva:['Alt+['],photoshop:['Alt+[']},run:()=>clickNative('.studio-panel-toggle[aria-label="Toggle creation panel"]')},
{id:'workspace.position',title:'Open Position and Arrange',category:'Arrange',bindings:{standard:['P'],canva:['P'],photoshop:['P']},run:()=>clickNative('#workflowV6PositionBtn')},
{id:'workspace.flow',title:'Open invitation flow',category:'Pages',bindings:{standard:['Q'],canva:['Q'],photoshop:['Q']},run:()=>clickNative('#workflowV6FlowBtn')},
{id:'workspace.elementsSearch',title:'Search elements',category:'Insert',bindings:{standard:['A'],canva:['A'],photoshop:['A']},run:()=>{window.EInviteWorkflow?.navigate?.('elements',{source:'command'});setTimeout(()=>$('.final-library-search input')?.focus(),0)}},
{id:'workspace.themeCycle',title:'Cycle appearance',category:'Workspace',bindings:{standard:['Alt+T'],canva:['Alt+T'],photoshop:['Alt+T']},run:()=>window.EInviteThemeController?.cycle?.()},
{id:'navigate.dashboard',title:'Open dashboard',category:'Navigate',bindings:{standard:['Alt+H'],canva:['Alt+H'],photoshop:['Alt+H']},run:()=>{location.href='dashboard.html'}},
{id:'navigate.materials',title:'Open materials',category:'Navigate',bindings:{standard:['Alt+M'],canva:['Alt+M'],photoshop:['Alt+M']},run:()=>{location.href='materials.html'}},
{id:'navigate.templates',title:'Open templates',category:'Navigate',bindings:{standard:['Alt+P'],canva:['Alt+P'],photoshop:['Alt+P']},run:()=>{location.href='templates.html'}},
{id:'preview.selection',title:'Preview selected objects',category:'View',bindings:{standard:['Shift+P'],canva:['Shift+P'],photoshop:['Shift+P']},enabled:()=>selected().length>0,run:()=>window.EInvitePreviewObjects?.($$('#stage .object.selected,#stage .object.multi-selected'))||false},
{id:'invitation.preview',title:'Preview guest invitation',category:'Publish',keywords:['guest','view'],bindings:{standard:[],canva:[],photoshop:[]},run:()=>clickNative('#previewBtn')},
{id:'invitation.publish',title:'Publish invitation snapshot',category:'Publish',bindings:{standard:[],canva:[],photoshop:[]},run:()=>clickNative('#publishBtn')},
{id:'insert.text',title:'Add text',category:'Insert',keywords:['heading','body'],bindings:{standard:[],canva:[],photoshop:[]},run:()=>clickNative('#addText')},
{id:'insert.rectangle',title:'Add rectangle',category:'Insert',bindings:{standard:[],canva:[],photoshop:[]},run:()=>clickNative('[data-add-element="rectangle"]')},
{id:'insert.circle',title:'Add circle',category:'Insert',bindings:{standard:[],canva:[],photoshop:[]},run:()=>clickNative('[data-add-element="circle"]')},
{id:'insert.line',title:'Add line',category:'Insert',bindings:{standard:[],canva:[],photoshop:[]},run:()=>clickNative('[data-add-element="line"]')}
])}
function keydown(event){
if(event.defaultPrevented||event.isComposing||event.keyCode===229||isLocalShortcutTarget(event.target,event))return;
const chord=eventChord(event),id=bindings.get(chord);if(!id)return;
const command=commands.get(id);if(!command)return;if((id==='canvas.panHold'||id.startsWith('move.'))&&!canvasKeyboardContext(event))return;const interactive=event.target?.closest?.('button,a[href],[role=button],[role=tab],[role=menuitem],[role=checkbox],[role=switch]');if(interactive&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&event.key!=='Escape'&&!command.allowFromControls)return;
const typing=isTypingTarget(event.target);if(typing&&!command.allowWhileTyping)return;
if(event.repeat&&!command.repeatable)return;
const state=commandState(command,context(event));if(!state.enabled)return;
if(command.preventDefault!==false)event.preventDefault();if(command.stopPropagation!==false){event.stopPropagation();event.stopImmediatePropagation()}
execute(id,{event});
}
function keyup(event){const chord=eventChord(event),id=bindings.get(chord);const command=id&&commands.get(id);if(command?.onRelease){event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();try{command.onRelease(context(event))}catch(error){console.error(error)}}else if(event.code==='Space'&&panHeld)panEnd()}
function bindButtons(){const map={undoBtn:'history.undo',redoBtn:'history.redo',copyObjects:'edit.copy',pasteObjects:'edit.paste',duplicate:'edit.duplicate',deleteBtn:'edit.delete',groupObjects:'object.group',ungroupObjects:'object.ungroup',bringForward:'arrange.forward',sendBackward:'arrange.backward'};for(const[id,commandId]of Object.entries(map)){const el=$('#'+id);if(el){el.dataset.commandId=commandId;const shortcut=getShortcuts(commandId)[0];if(shortcut)el.title=`${commands.get(commandId)?.title||el.title} (${formatChord(shortcut)})`}}const commandButton=$('#studioCommandBtn');if(commandButton){commandButton.dataset.commandId='ui.quickActions';commandButton.onclick=null}const status=$('.studio-statusbar>div:last-child');if(status&&!status.querySelector('[data-v23-shortcuts]')){const help=document.createElement('button');help.type='button';help.className='ui-shortcut-help';help.textContent='?';help.dataset.v23Shortcuts='1';help.dataset.commandId='ui.shortcutSettings';help.dataset.uiTooltip='Keyboard shortcuts';status.prepend(help)}}
function clickHandler(event){if(event.target.closest?.('.v23-command-surface'))return;const el=event.target.closest?.('[data-command-id]');if(!el||buttonBypass.has(el))return;const id=el.dataset.commandId;if(!commands.has(id))return;event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();execute(id,{event})}
function formatChord(chord){return String(chord).replace('Mod',/Mac|iPhone|iPad/.test(navigator.platform)?'⌘':'Ctrl').replaceAll('+',' + ')}
addDefaults();
window.__EINVITE_V23_COMMAND_SYSTEM__=true;
window.EInviteCommandRegistry=Object.freeze({version:'23.0.0',register,registerMany,unregister,execute,list,get,subscribe,commandState,formatChord,loadUI,openUI,get profile(){return activeProfile},setProfile,getShortcuts,get conflicts(){return clone(conflicts)},setOverride,resetOverrides,validateOverride,canonicalChord,eventChord});
window.EInviteShortcutManager=Object.freeze({version:'23.0.1',ownsGlobalKeyboard:true,get profile(){return activeProfile},setProfile,get bindings(){return new Map(bindings)},get conflicts(){return clone(conflicts)},setOverride,resetOverrides});
window.addEventListener('keydown',keydown,true);window.addEventListener('keyup',keyup,true);document.addEventListener('click',clickHandler,true);
lifecycle?.add?.(()=>{window.removeEventListener('keydown',keydown,true);window.removeEventListener('keyup',keyup,true);document.removeEventListener('click',clickHandler,true);panEnd()});
const ready=()=>{bindButtons();document.body.classList.add('command-system-v23');notify('ready',{profile:activeProfile})};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();
function get(id){return commands.get(id)||null}
})();
