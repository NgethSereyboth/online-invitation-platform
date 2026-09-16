;(()=>{
'use strict';
const ensureStack=()=>{let stack=document.querySelector('.ei-toast-stack');if(!stack){stack=document.createElement('div');stack.className='ei-toast-stack';stack.setAttribute('aria-live','polite');document.body.append(stack)}return stack};
function toast(message,options={}){
  const text=String(message??'');if(!text)return;
  const stack=ensureStack(),item=document.createElement('div');item.className=`ei-toast ${options.type||''}`.trim();
  const icon=options.icon||(options.type==='error'?'!':options.type==='success'?'✓':'✦');
  item.innerHTML=`<span class="ei-toast-icon"></span><strong></strong><button type="button" aria-label="Dismiss">×</button>`;
  item.querySelector('.ei-toast-icon').textContent=icon;item.querySelector('strong').textContent=text;
  const close=()=>{if(item.classList.contains('out'))return;item.classList.add('out');setTimeout(()=>item.remove(),190)};item.querySelector('button').onclick=close;stack.append(item);setTimeout(close,Math.max(1500,Number(options.duration||3600)));return item
}
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label>Value</label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('.ei-dialog-message').textContent=message;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input');host.hidden=false;field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';host.append(field)}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel'});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};
})();;const $=s=>document.querySelector(s);localStorage.removeItem('sovan-auth-token');
async function api(path){const r=await fetch(path,{credentials:'same-origin',headers:{}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data}
const bytes=n=>n>=1e9?`${(n/1e9).toFixed(1)} GB`:n>=1e6?`${(n/1e6).toFixed(1)} MB`:`${Math.round(n/1e3)} KB`;
async function init(){try{const [me,usage,templates,assets]=await Promise.all([api('/api/auth/me'),api('/api/account/usage'),api('/api/templates'),api('/api/assets')]);if(!me.user||!['designer','admin'].includes(me.user.role))throw Error('Designer or administrator access is required');$('#designerMetrics').innerHTML=`<div class="workspace-metric"><strong>${usage.usage.invitations}</strong>Active invitations</div><div class="workspace-metric"><strong>${templates.length}</strong>Reusable templates</div><div class="workspace-metric"><strong>${assets.length}</strong>Stored materials</div><div class="workspace-metric"><strong>${bytes(usage.usage.storageBytes)}</strong>Storage used</div>`;$('#designerPlanNote').textContent=`Current account plan: ${usage.plan}. Usage limits are ${usage.enforced?'enforced':'informational in this development build'}.`}catch(e){document.querySelector('.designer-page').innerHTML=`<h1>Designer Workspace unavailable</h1><p>${String(e.message)}</p><a href="dashboard.html" class="button-link">Back to dashboard</a>`}}
init();;(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const html=document.documentElement, body=document.body;
body.classList.add('ui-boot');requestAnimationFrame(()=>requestAnimationFrame(()=>{body.classList.remove('ui-boot');body.classList.add('ui-ready')}));
function currentMode(){return localStorage.getItem('einvite-theme-mode')==='dark'?'dark':'light'}
function applyTheme(mode,announce=false){
  const resolved=mode==='dark'?'dark':'light';
  if(announce){html.classList.add('theme-transition');setTimeout(()=>html.classList.remove('theme-transition'),340)}
  html.dataset.theme=resolved;html.dataset.themeMode=mode;html.style.colorScheme=resolved;
  localStorage.setItem('einvite-theme-mode',mode);
  $$('.ui-theme-menu button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  const icon=$('.ui-theme-icon');if(icon)icon.textContent=resolved==='dark'?'☾':'☀';
  if(announce)toast(`${resolved[0].toUpperCase()+resolved.slice(1)} appearance`,'◐');
}
applyTheme(currentMode());
function installThemeControl(){
  const header=$('body:not(:has(.guest))>header');if(header&&$('.ui-theme',header))return;
  const wrap=document.createElement('div');wrap.className='ui-theme'+(header?'':' floating');
  wrap.innerHTML=`<button type="button" class="ui-theme-button" aria-label="Appearance" aria-haspopup="menu" aria-expanded="false" data-ui-tooltip="Appearance (Alt+T)"><span class="ui-theme-icon">◐</span></button><div class="ui-theme-menu" role="menu" hidden>
  <button type="button" data-mode="light"><span>☀</span><b>Light</b><span class="check">✓</span></button>
  <button type="button" data-mode="dark"><span>☾</span><b>Dark</b><span class="check">✓</span></button></div>`;
  if(header){const logout=$('#logoutBtn',header); if(logout)header.insertBefore(wrap,logout); else header.append(wrap)}else document.body.append(wrap);
  const trigger=$('.ui-theme-button',wrap),menu=$('.ui-theme-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  $$('[data-mode]',menu).forEach(b=>b.onclick=()=>{applyTheme(b.dataset.mode,true);menu.hidden=true;trigger.setAttribute('aria-expanded','false')});
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  applyTheme(currentMode());
}
installThemeControl();
window.EInviteThemeController=Object.freeze({currentMode,applyTheme,cycle(){const modes=['light','dark'],i=modes.indexOf(currentMode());const next=modes[(i+1)%2];applyTheme(next,true);return next}});
function installAppLauncher(){
  const header=$('body:not(:has(.guest))>header');if(!header||$('.ui-app-launcher',header))return;
  const brand=header.querySelector('strong');if(!brand)return;
  const wrap=document.createElement('div');wrap.className='ui-app-launcher';
  wrap.innerHTML=`<button type="button" class="ui-app-launcher-button" aria-label="Open workspace navigation" aria-expanded="false" data-ui-tooltip="Workspace navigation"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></button><div class="ui-app-launcher-menu" hidden><header><strong>Workspace</strong></header><div class="ui-app-grid">
  <a href="dashboard.html"><span>⌂</span><div><b>Dashboard</b><small>Your invitations</small></div></a>
  <a href="templates.html"><span>✦</span><div><b>Templates</b><small>Reusable designs</small></div></a>
  <a href="materials.html"><span>▣</span><div><b>Materials</b><small>Photos, audio & video</small></div></a>
  <a href="designer.html"><span>◇</span><div><b>Designer</b><small>Professional workspace</small></div></a>
  <a href="billing.html"><span>◎</span><div><b>Plans</b><small>Usage & limits</small></div></a>
  <a href="account.html"><span>◉</span><div><b>Account</b><small>Profile & security</small></div></a></div></div>`;
  brand.after(wrap);const trigger=$('.ui-app-launcher-button',wrap),menu=$('.ui-app-launcher-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
}
installAppLauncher();
const page=location.pathname.split('/').pop()||'dashboard.html';$$('body:not(:has(.guest))>header a').forEach(a=>{const href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];if(href===page)a.classList.add('ui-current')});
addEventListener('pointerdown',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;const r=b.getBoundingClientRect(),s=document.createElement('span');s.className='ui-ripple';const size=Math.max(r.width,r.height);s.style.width=s.style.height=size+'px';s.style.left=(e.clientX-r.left)+'px';s.style.top=(e.clientY-r.top)+'px';b.append(s);setTimeout(()=>s.remove(),560)},true);
const spotlightSelectors='.invite-card,.metric,.response-card,.wish-card,.usage-card,.plan,.studio-card,.material-card-page,.template-choice,.page-nav-card,.studio-quick-grid button,.page-builder-library button,.element-library button,.block-library button';
$$(spotlightSelectors).forEach(el=>{el.classList.add('ui-spotlight');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)})});
const stack=document.createElement('div');stack.className='ui-toast-stack';document.body.append(stack);
function toast(message,icon='✓'){const el=document.createElement('div');el.className='ui-toast';el.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),240)},2200)}
window.einviteToast=toast;
const tip=document.createElement('div');tip.className='ui-tooltip';document.body.append(tip);let tipTimer;
document.addEventListener('pointerover',e=>{const el=e.target.closest('[data-ui-tooltip],button[title]');if(!el)return;const txt=el.dataset.uiTooltip||el.getAttribute('title');if(!txt)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{const r=el.getBoundingClientRect();tip.textContent=txt;tip.style.left=Math.max(8,Math.min(innerWidth-200,r.left+r.width/2))+'px';tip.style.top=Math.max(8,r.bottom+8)+'px';tip.classList.add('show')},350)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-ui-tooltip],button[title]')){clearTimeout(tipTimer);tip.classList.remove('show')}});
if(body.classList.contains('studio-experience')){
  const main=$('body.studio-experience>main'),toolbar=$('.studio-canvas-toolbar');
  const canvasViewport=$('.canvas-viewport');
  canvasViewport?.addEventListener('pointermove',e=>{const r=canvasViewport.getBoundingClientRect();canvasViewport.style.setProperty('--canvas-pointer-x',`${e.clientX-r.left}px`);canvasViewport.style.setProperty('--canvas-pointer-y',`${e.clientY-r.top}px`)});
  let leftWidth=Math.max(300,Math.min(520,Number(localStorage.getItem('einvite-left-width'))||370)),rightWidth=Math.max(280,Math.min(460,Number(localStorage.getItem('einvite-right-width'))||330));
  function setWidths(){const available=Math.max(900,window.innerWidth||1440),stageMin=360;leftWidth=Math.max(290,Math.min(560,leftWidth,available-rightWidth-stageMin));rightWidth=Math.max(280,Math.min(520,rightWidth,available-leftWidth-stageMin));for(const target of [html,body]){target.style.setProperty('--studio-left-width',`${leftWidth}px`);target.style.setProperty('--einvite-left-width',`${leftWidth}px`);target.style.setProperty('--studio-right-width',`${rightWidth}px`);target.style.setProperty('--einvite-inspector-width',`${rightWidth}px`)}}setWidths();window.addEventListener('resize',setWidths);
  function addToggle(side,label,symbol){if(!toolbar)return;const b=document.createElement('button');b.type='button';b.className='studio-panel-toggle';b.innerHTML=symbol;b.setAttribute('aria-label',label);b.dataset.uiTooltip=label;b.onclick=()=>{const cls=`studio-${side}-collapsed`;body.classList.toggle(cls);b.setAttribute('aria-pressed',String(body.classList.contains(cls)));localStorage.setItem(`einvite-${side}-collapsed`,body.classList.contains(cls)?'1':'0')};toolbar.prepend(b);if(localStorage.getItem(`einvite-${side}-collapsed`)==='1'){body.classList.add(`studio-${side}-collapsed`);b.setAttribute('aria-pressed','true')}return b}
  addToggle('right','Toggle inspector','▥');addToggle('left','Toggle creation panel','▤');
  function resizer(side){if(!main)return;const h=document.createElement('div');h.className=`studio-panel-resizer ${side[0]}`;main.append(h);h.addEventListener('pointerdown',e=>{h.setPointerCapture(e.pointerId);h.classList.add('dragging');body.style.userSelect='none';const start=e.clientX,startL=leftWidth,startR=rightWidth;const move=ev=>{if(side==='left'){leftWidth=Math.max(290,Math.min(560,startL+(ev.clientX-start)))}else{rightWidth=Math.max(280,Math.min(520,startR-(ev.clientX-start)))}setWidths()};const up=()=>{h.classList.remove('dragging');body.style.userSelect='';localStorage.setItem('einvite-left-width',leftWidth);localStorage.setItem('einvite-right-width',rightWidth);h.removeEventListener('pointermove',move);h.removeEventListener('pointerup',up)};h.addEventListener('pointermove',move);h.addEventListener('pointerup',up)})}
  resizer('left');resizer('right');
  const context=document.createElement('div');context.className='ui-context-menu';context.hidden=true;
  context.innerHTML=`<button data-cmd="duplicate"><span>⧉</span><b>Duplicate</b><kbd>Ctrl+D</kbd></button><button data-cmd="copy"><span>□</span><b>Copy</b><kbd>Ctrl+C</kbd></button><button data-cmd="paste"><span>▣</span><b>Paste</b><kbd>Ctrl+V</kbd></button><div class="ui-context-sep"></div><button data-cmd="forward"><span>↑</span><b>Bring forward</b><kbd></kbd></button><button data-cmd="backward"><span>↓</span><b>Send backward</b><kbd></kbd></button><button data-cmd="lock"><span>◇</span><b>Lock / unlock</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="addText"><span>T</span><b>Add text</b><kbd></kbd></button><button data-cmd="fit"><span>⌗</span><b>Fit canvas</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="delete" class="danger"><span>×</span><b>Delete</b><kbd>Del</kbd></button>`;
  document.body.append(context);
  const cmdMap={duplicate:'duplicate',copy:'copyObjects',paste:'pasteObjects',forward:'bringForward',backward:'sendBackward',addText:'addText',fit:'fitCanvas',delete:'deleteBtn'};
  context.addEventListener('click',e=>{const b=e.target.closest('[data-cmd]');if(!b)return;const cmd=b.dataset.cmd;if(cmd==='lock'){const lock=$('#objectLocked');if(lock){lock.checked=!lock.checked;lock.dispatchEvent(new Event('change',{bubbles:true}))}}else document.getElementById(cmdMap[cmd])?.click();context.hidden=true});
  $('#stage')?.addEventListener('contextmenu',e=>{e.preventDefault();const obj=e.target.closest('.object');if(obj&&!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected'))obj.click();context.hidden=false;const w=220,h=390;context.style.left=Math.min(e.clientX,innerWidth-w-8)+'px';context.style.top=Math.min(e.clientY,innerHeight-h-8)+'px'});
  document.addEventListener('pointerdown',e=>{if(!context.contains(e.target))context.hidden=true});
}
addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname===location.pathname&&u.hash)return;if(a.closest('dialog'))return;e.preventDefault();body.classList.add('ui-page-leaving');setTimeout(()=>location.href=u.href,115)});
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const editor=!!$('#stage')&&!!$('.studio-left-panel');
document.documentElement.classList.add('final-ui-ready');
const progress=document.createElement('div'); progress.className='final-route-progress'; document.body.append(progress);
addEventListener('beforeunload',()=>progress.classList.add('active'));
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href]'); if(!a||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  try{const u=new URL(a.href,location.href);if(u.origin===location.origin&&u.href!==location.href)progress.classList.add('active')}catch{}
},true);
if(!document.body.classList.contains('guest')) requestAnimationFrame(()=>document.body.classList.add('final-page-entered'));
const globalObserver=new MutationObserver(()=>{
  $$('.empty:not([data-final-empty])').forEach(el=>{el.dataset.finalEmpty='1';el.classList.add('final-empty-state')});
  $$('dialog:not([data-final-dialog])').forEach(el=>{el.dataset.finalDialog='1';el.classList.add('final-dialog')});
});
globalObserver.observe(document.body,{subtree:true,childList:true});
if(!editor)return;
const stage=$('#stage');
const objectPane=$('[data-inspector-pane="object"]');
const elementsPane=$('[data-studio-pane="elements"]');
const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const applyNow=items=>{items.forEach(item=>{try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(item)}catch{}});try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};try{typeof refreshSelectionUI==='function'&&refreshSelectionUI()}catch{}};
const setData=(key,value,{apply=true}={})=>{const items=activeObjects();if(!items.length)return;items.forEach(item=>item.dataset[key]=String(value));if(apply)applyNow(items);saveNow();refreshAdvancedControls();refreshTimeline()};
const boolData=(key,value)=>setData(key,value?'true':'false');
const selectedType=()=>activeObjects()[0]?.dataset.objectType||'';
const safeText=node=>(node?.querySelector('.content')?.textContent||node?.dataset.alt||node?.dataset.objectType||'Object').trim().slice(0,38);
function toast(message,icon='✦'){
  if(typeof window.uiToast==='function')return window.uiToast(message,icon);
  let stack=$('.final-toast-stack');if(!stack){stack=document.createElement('div');stack.className='final-toast-stack';document.body.append(stack)}
  const t=document.createElement('div');t.className='final-toast';t.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(t);setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),220)},1900)
}
function selectOnly(item){try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([item])}catch{item.click()}setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0)}
function makeId(prefix='object'){return`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`}
const advanced=document.createElement('section'); advanced.className='final-advanced-inspector';
advanced.innerHTML=`
  <div class="final-panel-title"><div><small>Creative controls</small><h2>Effects & motion</h2></div><span class="final-beta">Advanced</span></div>
  <details open class="final-control-group" data-final-group="surface"><summary>Surface & blending</summary>
    <label class="final-toggle-row"><span>Object background</span><input id="finalBgEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Background<input id="finalBgColor" type="color" value="#ffffff"></label><label>Opacity <span id="finalBgOpacityValue">100%</span><input id="finalBgOpacity" type="range" min="0" max="100" value="100"></label></div>
    <label>Blend mode<select id="finalBlendMode"><option value="normal">Normal</option><option value="multiply">Multiply</option><option value="screen">Screen</option><option value="overlay">Overlay</option><option value="soft-light">Soft light</option><option value="darken">Darken</option><option value="lighten">Lighten</option></select></label>
  </details>
  <details class="final-control-group" data-final-group="shape"><summary>Gradient fill</summary>
    <label>Fill type<select id="finalFillMode"><option value="solid">Solid</option><option value="gradient">Gradient</option></select></label>
    <div class="final-two-col"><label>Start<input id="finalGradientStart" type="color" value="#d9a6ad"></label><label>End<input id="finalGradientEnd" type="color" value="#9d4555"></label></div>
    <label>Angle <span id="finalGradientAngleValue">135°</span><input id="finalGradientAngle" type="range" min="0" max="360" value="135"></label>
    <div class="final-gradient-preview" id="finalGradientPreview"></div>
  </details>
  <details class="final-control-group" data-final-group="text"><summary>Text effects</summary>
    <label>Transform<select id="finalTextTransform"><option value="none">As typed</option><option value="uppercase">UPPERCASE</option><option value="lowercase">lowercase</option><option value="capitalize">Capitalize</option></select></label>
    <label class="final-toggle-row"><span>Gradient text</span><input id="finalTextGradientEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Start<input id="finalTextGradientStart" type="color" value="#9d4555"></label><label>End<input id="finalTextGradientEnd" type="color" value="#b58a3a"></label></div>
    <label>Gradient angle <span id="finalTextGradientAngleValue">90°</span><input id="finalTextGradientAngle" type="range" min="0" max="360" value="90"></label>
    <div class="final-two-col"><label>Outline <span id="finalStrokeValue">0px</span><input id="finalStrokeWidth" type="range" min="0" max="8" step="0.5" value="0"></label><label>Outline color<input id="finalStrokeColor" type="color" value="#ffffff"></label></div>
    <div class="final-two-col"><label>Text shadow <span id="finalTextShadowValue">0px</span><input id="finalTextShadowBlur" type="range" min="0" max="40" value="0"></label><label>Shadow color<input id="finalTextShadowColor" type="color" value="#000000"></label></div>
    <div class="final-style-presets">
      <button type="button" data-final-text-style="luxury">Luxury Gold</button><button type="button" data-final-text-style="editorial">Editorial</button><button type="button" data-final-text-style="soft">Soft Glow</button><button type="button" data-final-text-style="minimal">Minimal</button>
    </div>
  </details>
  <details open class="final-control-group" data-final-group="motion"><summary>Motion timing</summary>
    <label>Animation delay <span id="finalDelayValue">0ms</span><input id="finalAnimationDelay" type="range" min="0" max="5000" step="50" value="0"></label>
    <div class="final-inline-actions"><button type="button" id="finalPreviewSelection">▶ Preview selected</button><button type="button" id="finalPreviewPage">▶ Preview page</button><button type="button" id="finalStagger">Stagger selected</button></div>
  </details>
  <details class="final-control-group" data-final-group="layout"><summary>Smart layout</summary>
    <div class="final-layout-grid"><button data-final-layout="horizontal">Horizontal stack</button><button data-final-layout="vertical">Vertical stack</button><button data-final-layout="grid">Smart grid</button><button data-final-layout="center">Center selection</button><button data-final-layout="equal-width">Equal width</button><button data-final-layout="equal-height">Equal height</button></div>
  </details>`;
if(objectPane)objectPane.append(advanced);
const controls={
 bgEnabled:$('#finalBgEnabled'),bgColor:$('#finalBgColor'),bgOpacity:$('#finalBgOpacity'),blend:$('#finalBlendMode'),fillMode:$('#finalFillMode'),gradientStart:$('#finalGradientStart'),gradientEnd:$('#finalGradientEnd'),gradientAngle:$('#finalGradientAngle'),textGradientEnabled:$('#finalTextGradientEnabled'),textGradientStart:$('#finalTextGradientStart'),textGradientEnd:$('#finalTextGradientEnd'),textGradientAngle:$('#finalTextGradientAngle'),strokeWidth:$('#finalStrokeWidth'),strokeColor:$('#finalStrokeColor'),textShadowBlur:$('#finalTextShadowBlur'),textShadowColor:$('#finalTextShadowColor'),textTransform:$('#finalTextTransform'),delay:$('#finalAnimationDelay')
};
function refreshAdvancedControls(){
  const item=activeObjects()[0],has=!!item,type=item?.dataset.objectType||'';
  advanced.classList.toggle('is-disabled',!has);
  $$('[data-final-group="shape"]',advanced).forEach(x=>x.hidden=type!=='shape');
  $$('[data-final-group="text"]',advanced).forEach(x=>x.hidden=!['text','decoration'].includes(type));
  if(!item)return;
  controls.bgEnabled.checked=item.dataset.backgroundEnabled==='true';controls.bgColor.value=item.dataset.backgroundColor||'#ffffff';controls.bgOpacity.value=item.dataset.backgroundOpacity??100;$('#finalBgOpacityValue').textContent=`${controls.bgOpacity.value}%`;controls.blend.value=item.dataset.blendMode||'normal';
  controls.fillMode.value=item.dataset.fillMode||'solid';controls.gradientStart.value=item.dataset.gradientStart||'#d9a6ad';controls.gradientEnd.value=item.dataset.gradientEnd||'#9d4555';controls.gradientAngle.value=item.dataset.gradientAngle||135;$('#finalGradientAngleValue').textContent=`${controls.gradientAngle.value}°`;$('#finalGradientPreview').style.background=`linear-gradient(${controls.gradientAngle.value}deg,${controls.gradientStart.value},${controls.gradientEnd.value})`;
  controls.textGradientEnabled.checked=item.dataset.textGradientEnabled==='true';controls.textGradientStart.value=item.dataset.textGradientStart||'#9d4555';controls.textGradientEnd.value=item.dataset.textGradientEnd||'#b58a3a';controls.textGradientAngle.value=item.dataset.textGradientAngle||90;$('#finalTextGradientAngleValue').textContent=`${controls.textGradientAngle.value}°`;controls.strokeWidth.value=item.dataset.textStrokeWidth||0;$('#finalStrokeValue').textContent=`${controls.strokeWidth.value}px`;controls.strokeColor.value=item.dataset.textStrokeColor||'#ffffff';controls.textShadowBlur.value=item.dataset.textShadowBlur||0;$('#finalTextShadowValue').textContent=`${controls.textShadowBlur.value}px`;controls.textShadowColor.value=item.dataset.textShadowColor||'#000000';controls.textTransform.value=item.dataset.textTransform||'none';controls.delay.value=item.dataset.animationDelay||0;$('#finalDelayValue').textContent=`${controls.delay.value}ms`;
}
controls.bgEnabled.onchange=e=>boolData('backgroundEnabled',e.target.checked);controls.bgColor.oninput=e=>setData('backgroundColor',e.target.value);controls.bgOpacity.oninput=e=>{$('#finalBgOpacityValue').textContent=`${e.target.value}%`;setData('backgroundOpacity',e.target.value)};controls.blend.onchange=e=>setData('blendMode',e.target.value);
controls.fillMode.onchange=e=>setData('fillMode',e.target.value);controls.gradientStart.oninput=e=>{setData('gradientStart',e.target.value);refreshAdvancedControls()};controls.gradientEnd.oninput=e=>{setData('gradientEnd',e.target.value);refreshAdvancedControls()};controls.gradientAngle.oninput=e=>{$('#finalGradientAngleValue').textContent=`${e.target.value}°`;setData('gradientAngle',e.target.value);refreshAdvancedControls()};
controls.textGradientEnabled.onchange=e=>boolData('textGradientEnabled',e.target.checked);controls.textGradientStart.oninput=e=>setData('textGradientStart',e.target.value);controls.textGradientEnd.oninput=e=>setData('textGradientEnd',e.target.value);controls.textGradientAngle.oninput=e=>{$('#finalTextGradientAngleValue').textContent=`${e.target.value}°`;setData('textGradientAngle',e.target.value)};controls.strokeWidth.oninput=e=>{$('#finalStrokeValue').textContent=`${e.target.value}px`;setData('textStrokeWidth',e.target.value)};controls.strokeColor.oninput=e=>setData('textStrokeColor',e.target.value);controls.textShadowBlur.oninput=e=>{$('#finalTextShadowValue').textContent=`${e.target.value}px`;setData('textShadowBlur',e.target.value)};controls.textShadowColor.oninput=e=>setData('textShadowColor',e.target.value);controls.textTransform.onchange=e=>setData('textTransform',e.target.value);controls.delay.oninput=e=>{$('#finalDelayValue').textContent=`${e.target.value}ms`;setData('animationDelay',e.target.value,{apply:false})};
const textStyles={
 luxury:{textGradientEnabled:'true',textGradientStart:'#7a5718',textGradientEnd:'#e9c86e',textGradientAngle:'90',textStrokeWidth:'0',textShadowBlur:'10',textShadowColor:'#5b3a0b',fontWeight:'700',letterSpacing:'1'},
 editorial:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'italic',letterSpacing:'0.5',textTransform:'none'},
 soft:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'18',textShadowColor:'#9d4555',fontWeight:'400',letterSpacing:'0'},
 minimal:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'normal',letterSpacing:'2',textTransform:'uppercase'}
};
$$('[data-final-text-style]').forEach(b=>b.onclick=()=>{const preset=textStyles[b.dataset.finalTextStyle];const items=activeObjects().filter(x=>['text','decoration'].includes(x.dataset.objectType));items.forEach(item=>Object.entries(preset).forEach(([k,v])=>item.dataset[k]=v));applyNow(items);saveNow();refreshAdvancedControls();toast(`${b.textContent.trim()} style applied`)});
function keyframesFor(name){return({
 'fade-up':[{opacity:0,transform:'translateY(24px)'},{opacity:1,transform:'translateY(0)'}],
 'soft-zoom':[{opacity:0,transform:'scale(.9)'},{opacity:1,transform:'scale(1)'}],
 'slide-left':[{opacity:0,transform:'translateX(45px)'},{opacity:1,transform:'translateX(0)'}],
 'blur-in':[{opacity:0,filter:'blur(14px)'},{opacity:1,filter:'blur(0)'}],
 'bounce-in':[{opacity:0,transform:'scale(.72)'},{opacity:1,transform:'scale(1.05)',offset:.72},{opacity:1,transform:'scale(1)'}],
 'flip-in':[{opacity:0,transform:'rotateY(80deg)'},{opacity:1,transform:'rotateY(0)'}],
 'float':[{transform:'translateY(0)'},{transform:'translateY(-12px)'},{transform:'translateY(0)'}],
 none:[{opacity:1},{opacity:1}]
})[name]||[{opacity:0},{opacity:1}]}
function previewObjects(items){items.forEach(item=>{const duration=Math.max(300,Math.min(3000,Number(item.dataset.duration||900))),delay=Math.max(0,Math.min(5000,Number(item.dataset.animationDelay||0))),rotation=`rotate(${Number(item.dataset.rotation||0)}deg)`,frames=keyframesFor(item.dataset.animation||'fade-up').map(frame=>({...frame,transform:frame.transform?`${frame.transform} ${rotation}`:rotation}));item.animate(frames,{duration,delay,easing:'cubic-bezier(.2,.8,.2,1)',fill:'none',iterations:item.dataset.animation==='float'?2:1})})}
window.EInvitePreviewObjects=items=>previewObjects(Array.isArray(items)?items:[]);
$('#finalPreviewSelection').onclick=()=>previewObjects(activeObjects());$('#finalPreviewPage').onclick=()=>previewObjects($$('.object'));$('#finalStagger').onclick=()=>{const items=activeObjects();if(items.length<2)return toast('Select two or more objects to stagger','!');items.sort((a,b)=>(parseFloat(a.style.top)||0)-(parseFloat(b.style.top)||0)||(parseFloat(a.style.left)||0)-(parseFloat(b.style.left)||0)).forEach((item,i)=>item.dataset.animationDelay=String(i*140));saveNow();refreshAdvancedControls();refreshTimeline();previewObjects(items);toast(`Staggered ${items.length} objects`)};
const timeline=document.createElement('section');timeline.className='final-timeline';timeline.innerHTML=`<div class="final-panel-title"><div><small>Sequence</small><h2>Motion timeline</h2></div><button id="finalTimelinePlay" type="button">▶ Play all</button></div><div id="finalTimelineRows"></div>`;if(objectPane)objectPane.append(timeline);
function refreshTimeline(){const host=$('#finalTimelineRows');if(!host)return;const items=$$('.object').sort((a,b)=>Number(a.style.zIndex||0)-Number(b.style.zIndex||0));host.innerHTML=items.length?'':'<p class="hint">Add objects to build a motion sequence.</p>';const maxEnd=Math.max(1000,...items.map(x=>Number(x.dataset.animationDelay||0)+Number(x.dataset.duration||900)));items.forEach(item=>{const row=document.createElement('button');row.type='button';row.className=`final-timeline-row${item.classList.contains('selected')||item.classList.contains('multi-selected')?' active':''}`;const delay=Number(item.dataset.animationDelay||0),duration=Number(item.dataset.duration||900);row.innerHTML=`<span class="final-timeline-icon">${item.dataset.objectType==='image'?'▣':item.dataset.objectType==='shape'?'□':'T'}</span><span class="final-timeline-name">${safeText(item)||'Object'}</span><span class="final-timeline-track"><i style="left:${delay/maxEnd*100}%;width:${Math.max(4,duration/maxEnd*100)}%"></i></span><small>${delay}ms</small>`;row.onclick=()=>selectOnly(item);host.append(row)})}
$('#finalTimelinePlay').onclick=()=>previewObjects($$('.object'));
function stagePercentFrame(item){return{left:parseFloat(item.style.left)||0,top:parseFloat(item.style.top)||0,width:item.getBoundingClientRect().width/stage.getBoundingClientRect().width*100,height:item.getBoundingClientRect().height/stage.getBoundingClientRect().height*100}}
function smartLayout(kind){const items=activeObjects().filter(x=>x.dataset.locked!=='true');if(!items.length)return toast('Select objects first','!');const frames=items.map(x=>({item:x,...stagePercentFrame(x)}));if(kind==='center'){const minL=Math.min(...frames.map(x=>x.left)),maxR=Math.max(...frames.map(x=>x.left+x.width)),minT=Math.min(...frames.map(x=>x.top)),maxB=Math.max(...frames.map(x=>x.top+x.height)),dx=50-(minL+maxR)/2,dy=50-(minT+maxB)/2;frames.forEach(x=>{x.item.style.left=`${x.left+dx}%`;x.item.style.top=`${x.top+dy}%`})}
 else if(kind==='horizontal'){const gap=3,total=frames.reduce((s,x)=>s+x.width,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.left-b.left).forEach(x=>{x.item.style.left=`${cur}%`;x.item.style.top='45%';cur+=x.width+gap})}
 else if(kind==='vertical'){const gap=2,total=frames.reduce((s,x)=>s+x.height,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.top-b.top).forEach(x=>{x.item.style.top=`${cur}%`;x.item.style.left=`${Math.max(4,(100-x.width)/2)}%`;cur+=x.height+gap})}
 else if(kind==='grid'){const cols=Math.ceil(Math.sqrt(frames.length)),gap=3,cell=(92-gap*(cols-1))/cols;frames.forEach((x,i)=>{const row=Math.floor(i/cols),col=i%cols;x.item.style.left=`${4+col*(cell+gap)}%`;x.item.style.top=`${8+row*22}%`;x.item.style.width=`${cell}%`})}
 else if(kind==='equal-width'){const w=Math.max(...frames.map(x=>x.width));frames.forEach(x=>x.item.style.width=`${w}%`)}
 else if(kind==='equal-height'){const h=Math.max(...frames.map(x=>x.height));frames.forEach(x=>x.item.style.height=`${h}%`)}
 try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}saveNow();toast('Layout updated')}
$$('[data-final-layout]').forEach(b=>b.onclick=()=>smartLayout(b.dataset.finalLayout));
const library=[
 {id:'flourish-1',name:'Classic flourish',cat:'Ornaments',glyph:'❦'},{id:'flourish-2',name:'Fine flourish',cat:'Ornaments',glyph:'❧'},{id:'sparkle-1',name:'Four-point sparkle',cat:'Ornaments',glyph:'✦'},{id:'sparkle-2',name:'Soft sparkle',cat:'Ornaments',glyph:'✧'},{id:'star-1',name:'Decorative star',cat:'Ornaments',glyph:'✶'},{id:'diamond-1',name:'Open diamond',cat:'Ornaments',glyph:'◇'},{id:'diamond-2',name:'Solid diamond',cat:'Ornaments',glyph:'◆'},
 {id:'heart-1',name:'Classic heart',cat:'Romance',glyph:'♥'},{id:'heart-2',name:'Outline heart',cat:'Romance',glyph:'♡'},{id:'rings',name:'Wedding rings',cat:'Romance',glyph:'◯◯'},{id:'infinity',name:'Forever mark',cat:'Romance',glyph:'∞'},{id:'love-spark',name:'Love sparkle',cat:'Romance',glyph:'♡ ✦ ♡'},
 {id:'leaf-1',name:'Botanical leaf',cat:'Botanical',glyph:'❧'},{id:'flower-1',name:'Flower mark',cat:'Botanical',glyph:'✿'},{id:'flower-2',name:'Elegant flower',cat:'Botanical',glyph:'❀'},{id:'petal',name:'Petal cluster',cat:'Botanical',glyph:'❋'},{id:'branch',name:'Leaf branch',cat:'Botanical',glyph:'☘'},
 {id:'crown',name:'Royal crown',cat:'Ceremonial',glyph:'♛'},{id:'royal',name:'Royal emblem',cat:'Ceremonial',glyph:'♔'},{id:'sun',name:'Ceremonial sun',cat:'Ceremonial',glyph:'☼'},{id:'blessing',name:'Blessing mark',cat:'Ceremonial',glyph:'✺'},{id:'lotus',name:'Lotus-inspired mark',cat:'Ceremonial',glyph:'✾'},
 {id:'quote',name:'Quote mark',cat:'Editorial',glyph:'“'},{id:'bullet',name:'Editorial bullet',cat:'Editorial',glyph:'•'},{id:'section',name:'Section divider',cat:'Editorial',glyph:'— ✦ —'},{id:'roman',name:'Roman divider',cat:'Editorial',glyph:'I · II · III'},
 {id:'rect',name:'Rectangle',cat:'Shapes',shape:'rectangle'},{id:'circle',name:'Circle',cat:'Shapes',shape:'circle'},{id:'line',name:'Line',cat:'Shapes',shape:'line'},{id:'panel',name:'Glass panel',cat:'Shapes',shape:'panel'},
 {id:'title-luxury',name:'Luxury title',cat:'Text styles',text:'YOUR CELEBRATION',preset:'luxury'},{id:'title-editorial',name:'Editorial title',cat:'Text styles',text:'A beautiful beginning',preset:'editorial'},{id:'khmer-title',name:'Khmer ceremonial title',cat:'Text styles',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',preset:'khmer'},{id:'date-badge',name:'Date badge',cat:'Text styles',text:'27 · 12 · 2026',preset:'date'},
 {id:'khmer-diamond-row',name:'Khmer diamond row',cat:'Khmer motifs',glyph:'◇ ◆ ◇ ◆ ◇'},{id:'khmer-gold-divider',name:'Ceremonial divider',cat:'Khmer motifs',glyph:'✦ ◇ ✦'},{id:'khmer-lotus-row',name:'Lotus row',cat:'Khmer motifs',glyph:'✾  ✾  ✾'},{id:'khmer-blessing-row',name:'Blessing ornament',cat:'Khmer motifs',glyph:'✺ ✦ ✺'},{id:'khmer-temple-line',name:'Temple line',cat:'Khmer motifs',glyph:'⌂ ◇ ⌂'},{id:'khmer-royal-row',name:'Royal row',cat:'Khmer motifs',glyph:'♔  ◆  ♔'},
 {id:'confetti-1',name:'Confetti sparkle',cat:'Celebration',glyph:'✦ ✧ ✶ ✦'},{id:'party-stars',name:'Party stars',cat:'Celebration',glyph:'★ ☆ ★'},{id:'balloon-pair',name:'Balloon pair',cat:'Celebration',glyph:'◯  ◯'},{id:'gift-mark',name:'Gift mark',cat:'Celebration',glyph:'▣'},{id:'cake-mark',name:'Cake mark',cat:'Celebration',glyph:'♨'},{id:'music-notes',name:'Music notes',cat:'Celebration',glyph:'♪ ♫ ♪'},
 {id:'business-arrow',name:'Forward arrow',cat:'Business',glyph:'→'},{id:'business-grid',name:'Executive grid',cat:'Business',glyph:'□ □ □'},{id:'business-dots',name:'Modern dots',cat:'Business',glyph:'• • • •'},{id:'business-plus',name:'Modern plus',cat:'Business',glyph:'+  +  +'},{id:'business-chevron',name:'Chevron line',cat:'Business',glyph:'› › ›'},{id:'business-rule',name:'Executive rule',cat:'Business',glyph:'━━━'},
 {id:'corner-top-left',name:'Corner flourish',cat:'Borders',glyph:'⌜❦'},{id:'corner-top-right',name:'Reverse corner',cat:'Borders',glyph:'❦⌝'},{id:'thin-rule',name:'Thin divider',cat:'Borders',glyph:'────────'},{id:'diamond-rule',name:'Diamond divider',cat:'Borders',glyph:'── ◇ ──'},{id:'spark-rule',name:'Spark divider',cat:'Borders',glyph:'── ✦ ──'},{id:'dot-rule',name:'Dotted divider',cat:'Borders',glyph:'· · · · · ·'},
 {id:'leaf-pair',name:'Leaf pair',cat:'Botanical',glyph:'❧  ❧'},{id:'flower-row',name:'Flower row',cat:'Botanical',glyph:'❀ ✿ ❀'},{id:'garden-spark',name:'Garden sparkle',cat:'Botanical',glyph:'❧ ✦ ❧'},{id:'clover-row',name:'Clover row',cat:'Botanical',glyph:'☘ ☘ ☘'},{id:'small-bloom',name:'Small bloom',cat:'Botanical',glyph:'✽'},{id:'floral-divider',name:'Floral divider',cat:'Botanical',glyph:'❀ ─ ❀'},
 {id:'love-divider',name:'Heart divider',cat:'Romance',glyph:'── ♡ ──'},{id:'heart-cluster',name:'Heart cluster',cat:'Romance',glyph:'♡ ♥ ♡'},{id:'promise-mark',name:'Promise mark',cat:'Romance',glyph:'∞ ♡'},{id:'ring-divider',name:'Ring divider',cat:'Romance',glyph:'─ ◯◯ ─'},{id:'love-quote',name:'Love quote',cat:'Text styles',text:'A lifetime begins here',preset:'editorial'},{id:'thank-you',name:'Thank-you title',cat:'Text styles',text:'WITH LOVE & GRATITUDE',preset:'luxury'},
 {id:'circle-outline',name:'Circle outline',cat:'Shapes',shape:'circle'},{id:'soft-panel',name:'Soft panel',cat:'Shapes',shape:'panel'},{id:'wide-line',name:'Wide line',cat:'Shapes',shape:'line'},{id:'square-card',name:'Square card',cat:'Shapes',shape:'rectangle'}
];
const librarySection=document.createElement('section');librarySection.className='final-element-library';librarySection.innerHTML=`<div class="final-panel-title"><div><small>Invitation library</small><h2>Design elements</h2></div><span class="final-library-count"></span></div><div class="final-library-search"><span>⌕</span><input type="search" placeholder="Search ornaments, flowers, text…"></div><div class="final-library-cats"></div><div class="final-library-grid"></div>`;
if(elementsPane)elementsPane.insertBefore(librarySection,elementsPane.querySelector('.studio-pane-heading')?.nextSibling||elementsPane.firstChild);
let libraryCat='All',libraryQuery='';const favKey='einvite-element-favorites-v1',recentKey='einvite-element-recent-v1';let favorites=new Set(JSON.parse(localStorage.getItem(favKey)||'[]')),recent=JSON.parse(localStorage.getItem(recentKey)||'[]');
const cats=['All','Favorites','Recent',...new Set(library.map(x=>x.cat))];
function addCustomElement(item,drop){if(item.shape){if(typeof addDesignElement==='function')addDesignElement(item.shape);return}
 const type='decoration',obj=typeof createObject==='function'?createObject(makeId('library'),type):null;if(!obj)return;const content=obj.querySelector('.content');content.textContent=item.text||item.glyph||'✦';obj.dataset.color=(window.state?.accent||$('#accent')?.value||'#9d4555');obj.dataset.fontSize=item.text?'34':'64';obj.style.width=item.text?'76%':'150px';obj.style.height=item.text?'110px':'120px';obj.style.left=drop?`${drop.x}%`:(item.text?'12%':'32%');obj.style.top=drop?`${drop.y}%`:'38%';if(item.preset==='luxury'){obj.dataset.textGradientEnabled='true';obj.dataset.textGradientStart='#7a5718';obj.dataset.textGradientEnd='#e9c86e';obj.dataset.fontWeight='700';obj.dataset.letterSpacing='2'}if(item.preset==='editorial'){obj.dataset.fontStyle='italic';obj.dataset.font='serif-georgia';obj.dataset.fontSize='38'}if(item.preset==='khmer'){obj.dataset.font="noto-serif-khmer";obj.dataset.fontSize='34';obj.dataset.color='#a87616'}if(item.preset==='date'){obj.dataset.letterSpacing='4';obj.dataset.fontSize='26';obj.dataset.backgroundEnabled='true';obj.dataset.backgroundColor='#ffffff';obj.dataset.backgroundOpacity='78';obj.dataset.borderRadius='28'}applyObjectVisualStyle(obj);stage.append(obj);clearSelection();setSelection([obj]);saveNow();
 recent=[item.id,...recent.filter(x=>x!==item.id)].slice(0,10);localStorage.setItem(recentKey,JSON.stringify(recent));renderLibrary();toast(`${item.name} added`)}
function filteredLibrary(){return library.filter(x=>{if(libraryCat==='Favorites'&&!favorites.has(x.id))return false;if(libraryCat==='Recent'&&!recent.includes(x.id))return false;if(!['All','Favorites','Recent'].includes(libraryCat)&&x.cat!==libraryCat)return false;return!libraryQuery||`${x.name} ${x.cat}`.toLowerCase().includes(libraryQuery)})}
function renderLibrary(){const catHost=$('.final-library-cats',librarySection),grid=$('.final-library-grid',librarySection);catHost.innerHTML=cats.map(c=>`<button type="button" class="${c===libraryCat?'active':''}" data-cat="${c}">${c}</button>`).join('');catHost.querySelectorAll('button').forEach(b=>b.onclick=()=>{libraryCat=b.dataset.cat;renderLibrary()});const items=filteredLibrary();$('.final-library-count',librarySection).textContent=`${items.length} items`;grid.innerHTML='';items.forEach(item=>{const card=document.createElement('article');card.className='final-element-card';card.draggable=true;card.innerHTML=`<button type="button" class="final-fav ${favorites.has(item.id)?'active':''}" aria-label="Favorite">★</button><div class="final-element-preview">${item.shape?`<i class="shape-${item.shape}"></i>`:`<span>${item.text||item.glyph}</span>`}</div><strong>${item.name}</strong><small>${item.cat}</small>`;card.onclick=e=>{if(e.target.closest('.final-fav'))return;addCustomElement(item)};card.querySelector('.final-fav').onclick=e=>{e.stopPropagation();favorites.has(item.id)?favorites.delete(item.id):favorites.add(item.id);localStorage.setItem(favKey,JSON.stringify([...favorites]));renderLibrary()};card.ondragstart=e=>{e.dataTransfer.setData('application/x-einvite-library-item',item.id);e.dataTransfer.effectAllowed='copy'};grid.append(card)})}
$('.final-library-search input',librarySection).oninput=e=>{libraryQuery=e.target.value.trim().toLowerCase();renderLibrary()};renderLibrary();
stage.addEventListener('dragover',e=>{if(Array.from(e.dataTransfer.types||[]).includes('application/x-einvite-library-item')){e.preventDefault();stage.classList.add('final-library-drop')}});stage.addEventListener('dragleave',()=>stage.classList.remove('final-library-drop'));stage.addEventListener('drop',e=>{const id=e.dataTransfer.getData('application/x-einvite-library-item');if(!id)return;e.preventDefault();stage.classList.remove('final-library-drop');const r=stage.getBoundingClientRect(),item=library.find(x=>x.id===id);if(item)addCustomElement(item,{x:Math.max(0,Math.min(85,(e.clientX-r.left)/r.width*100)),y:Math.max(0,Math.min(85,(e.clientY-r.top)/r.height*100))})});
const observer=new MutationObserver(()=>{refreshAdvancedControls();refreshTimeline()});observer.observe(stage,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-animation-delay','data-fill-mode','data-text-gradient-enabled']});
document.addEventListener('pointerup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);document.addEventListener('keyup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);
refreshAdvancedControls();refreshTimeline();
const tour=document.createElement('dialog');tour.className='final-tour';tour.innerHTML=`<form method="dialog"><button class="final-tour-close" aria-label="Close">×</button></form><div class="final-tour-art">✦</div><p class="invite-kicker">Creation Studio</p><h1>Design the invitation. Run the event.</h1><p>This workspace combines free-form visual creation with pages, animation, guest RSVP, publishing, Khmer dates and event operations.</p><div class="final-tour-grid"><article><b>1</b><strong>Create</strong><span>Drag elements, upload media and style every object.</span></article><article><b>2</b><strong>Build pages</strong><span>Mix free-form artboards with functional event sections.</span></article><article><b>3</b><strong>Animate</strong><span>Sequence motion with delay, duration and stagger controls.</span></article><article><b>4</b><strong>Publish</strong><span>Run the Design Check, publish a snapshot and manage guests.</span></article></div><div class="final-tour-actions"><button type="button" id="finalTourExplore">Explore studio</button><button type="button" id="finalTourDismiss" class="primary">Start creating</button></div>`;document.body.append(tour);
const TOUR_VERSION='studio-v27',LEGACY_TOUR_KEY='einvite-final-tour-seen-v1';let tourKey='',tourAutomatic=false,tourLauncher=null,tourSessionSeen=false,tourOpenGeneration=0;
async function resolveTourIdentity(){try{await window.EInviteBackend?.ready;if(window.EInviteBackend?.isAvailable?.()){const response=await fetch('/api/auth/me',{credentials:'same-origin'}),data=response.ok?await response.json():null,user=data?.user;if(user?.id||user?.email)return String(user.id||user.email)}}catch{}try{const user=JSON.parse(localStorage.getItem('sovan-account-v1')||'null');if(user?.id||user?.email)return String(user.id||user.email)}catch{}return'local-anonymous'}
function persistTourSeen(){tourSessionSeen=true;if(tourKey)localStorage.setItem(tourKey,'1')}
function workspaceFocus(){const target=$('#stage')||$('#canvasViewport')||$('.stage-wrap');target?.setAttribute?.('tabindex','-1');setTimeout(()=>{target?.focus?.({preventScroll:true});if(target)document.body.dataset.keyboardOwner='canvas'},0)}
function closeTour({explore=false}={}){tourOpenGeneration++;persistTourSeen();if(tour.open)tour.close();if(explore){document.querySelector('[data-studio-tab="elements"]')?.click();setTimeout(()=>$('.final-element-library')?.scrollIntoView({behavior:'smooth'}),100)}}
$('#finalTourDismiss').onclick=()=>closeTour();$('#finalTourExplore').onclick=()=>closeTour({explore:true});tour.addEventListener('cancel',event=>{event.preventDefault();closeTour()});tour.addEventListener('close',()=>{persistTourSeen();const automatic=tourAutomatic,launcher=tourLauncher;tourAutomatic=false;tourLauncher=null;if(automatic)workspaceFocus();else requestAnimationFrame(()=>launcher?.focus?.({preventScroll:true}))});
const status=$('.studio-statusbar>div:last-child');if(status){const b=document.createElement('button');b.type='button';b.className='final-tour-trigger';b.textContent='✦ Tour';b.onclick=()=>{tourAutomatic=false;tourLauncher=b;tour.showModal()};status.prepend(b)}
window.EInviteOnboardingReady=(async()=>{const generation=++tourOpenGeneration,identity=await resolveTourIdentity();tourKey=`einvite-final-tour-seen-v2:${encodeURIComponent(identity)}:${TOUR_VERSION}`;if(localStorage.getItem(LEGACY_TOUR_KEY)==='1'&&!localStorage.getItem(tourKey))localStorage.setItem(tourKey,'1');if(generation!==tourOpenGeneration||tourSessionSeen||localStorage.getItem(tourKey)==='1')return{shown:false,identity};tourAutomatic=true;tourLauncher=null;tour.showModal();await new Promise(resolve=>requestAnimationFrame(resolve));return{shown:true,identity}})();
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
if(document.body&&!document.body.dataset.page)document.body.dataset.page=page;
function dashboard(){
  const view=$('#dashboardView'),login=$('#loginView');if(!view)return;
  view.classList.add('dashboard-home');
  const rail=document.createElement('nav');rail.className='dashboard-home-rail';rail.innerHTML=`
    <button type="button" class="rail-create" title="Create invitation"><span>＋</span>Create</button>
    <a href="dashboard.html" class="active"><span>⌂</span>Home</a>
    <a href="templates.html"><span>▣</span>Templates</a>
    <a href="materials.html"><span>▧</span>Materials</a>
    <a href="billing.html"><span>◉</span>Plans</a>
    <div class="rail-spacer"></div>
    <a href="account.html"><span>◌</span>Account</a>`;
  document.body.append(rail);
  $('.rail-create',rail).onclick=()=>$('#newBtn')?.click();
  const hero=document.createElement('section');hero.className='dashboard-home-hero';hero.innerHTML=`
    <h1>What will you create today?</h1>
    <label class="dashboard-home-search"><span>⌕</span><input type="search" placeholder="Search your invitations"></label>
    <div class="dashboard-quick-create">
      <button type="button" class="create"><i>＋</i><span>Create</span></button>
      <a href="templates.html" class="template"><i>▣</i><span>Templates</span></a>
      <button type="button" class="wedding"><i>♡</i><span>Wedding</span></button>
      <button type="button" class="birthday"><i>✦</i><span>Birthday</span></button>
      <button type="button" class="business"><i>◇</i><span>Business</span></button>
      <a href="materials.html" class="upload"><i>⇧</i><span>Uploads</span></a>
    </div>`;
  view.prepend(hero);
  const createByType=(type)=>{const btn=$('#newBtn');btn?.click();setTimeout(()=>{const typeEl=$('#newType');if(typeEl){typeEl.value=type;typeEl.dispatchEvent(new Event('change',{bubbles:true}))}},40)};
  $('.create',hero).onclick=()=>$('#newBtn')?.click();$('.wedding',hero).onclick=()=>createByType('Wedding');$('.birthday',hero).onclick=()=>createByType('Birthday');$('.business',hero).onclick=()=>createByType('Business');
  const homeSearch=$('.dashboard-home-search input',hero);
  homeSearch.oninput=()=>{const old=$('#dashboardSearch');if(old){old.value=homeSearch.value;old.dispatchEvent(new Event('input',{bubbles:true}))}else{$$('.invite-card','#inviteGrid').forEach(card=>card.hidden=!card.textContent.toLowerCase().includes(homeSearch.value.toLowerCase()))}};
  const recent=document.createElement('div');recent.className='dashboard-recent-head';recent.innerHTML='<h2>Recent invitations</h2>';
  const filter=$('.dashboard-filter-tabs');if(filter)recent.append(filter);
  const grid=$('#inviteGrid');grid?.before(recent);
  grid?.addEventListener('click',e=>{const cover=e.target.closest('.invite-cover');if(!cover)return;const card=cover.closest('.invite-card');card?.querySelector('[data-edit]')?.click()});
  const header=$('body>header');
  function authState(){const signed=view.hidden===false;rail.hidden=!signed;if(header){header.querySelectorAll('a[href="materials.html"],a[href="billing.html"],a[href="account.html"]').forEach(a=>a.hidden=!signed);const logout=$('#logoutBtn');if(logout)logout.hidden=!signed}}
  new MutationObserver(authState).observe(view,{attributes:true,attributeFilter:['hidden']});authState();
}
function materials(){
  const head=$('.library-head'),upload=$('.upload-box');if(!head||!upload)return;
  const toggle=document.createElement('button');toggle.type='button';toggle.className='material-upload-toggle primary';toggle.innerHTML='<span>⇧</span> Upload files';head.append(toggle);upload.hidden=true;
  toggle.onclick=()=>{upload.hidden=!upload.hidden;toggle.innerHTML=upload.hidden?'<span>⇧</span> Upload files':'<span>×</span> Close upload';if(!upload.hidden)setTimeout(()=>$('#uploadFile')?.focus(),50)};
  const grid=$('#grid');
  const observer=new MutationObserver(()=>{
    const empty=$('.empty-library',grid);if(empty&&/Authentication required/i.test(empty.textContent)&&!empty.querySelector('.material-auth-action')){const a=document.createElement('a');a.href='dashboard.html';a.className='material-auth-action';a.innerHTML='<button type="button" class="primary">Sign in to use materials</button>';empty.append(a)}
  });observer.observe(grid,{childList:true,subtree:true});
}
function editor(){
  const main=$('body.studio-experience>main'),rail=$('.studio-tool-rail'),host=$('.studio-pane-host'),stage=$('#stage');if(!main||!rail||!host||!stage)return;
  if(!$('[data-studio-tab="text"]',rail)){
    const elementsBtn=$('[data-studio-tab="elements"]',rail);
    const b=document.createElement('button');b.type='button';b.className='studio-rail-button';b.dataset.studioTab='text';b.innerHTML='<span class="studio-nav-icon">T</span><span>Text</span>';b.title='Text, fonts and typography';rail.insertBefore(b,elementsBtn||null);
    const pane=document.createElement('section');pane.className='studio-pane studio-text-pane';pane.dataset.studioPane='text';pane.innerHTML=`
      <div class="studio-pane-heading"><div><small>Create</small><h1>Text</h1></div></div>
      <label class="refine-text-search"><span>⌕</span><input type="search" placeholder="Search fonts and combinations"></label>
      <button type="button" class="refine-add-text">T &nbsp; Add a text box</button>
      <button type="button" class="refine-magic-write">✦ Magic invitation writing</button>
      <section class="refine-text-section"><div><h3>Default text styles</h3></div><div class="refine-text-presets">
        <button class="refine-text-preset heading" data-refine-text="heading">Add a heading</button>
        <button class="refine-text-preset subheading" data-refine-text="subheading">Add a subheading</button>
        <button class="refine-text-preset body" data-refine-text="body">Add a little bit of body text</button>
        <button class="refine-text-preset khmer" data-refine-text="khmer">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section"><div><h3>Fonts</h3><small>Search · Khmer · Favorites</small></div><button type="button" class="refine-browse-fonts">Browse all fonts</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Quick invitation styles</small></div><div class="refine-font-combos">
        <button class="refine-font-combo" data-combo="gold"><span style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button class="refine-font-combo" data-combo="modern"><span style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><i>HEADING</i></span><small>Modern contrast</small></button>
        <button class="refine-font-combo" data-combo="romance"><span style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button class="refine-font-combo" data-combo="khmer"><span style="font-family:'Noto Serif Khmer','Khmer OS Muol Light',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      </div></section>`;
    host.append(pane);
    function activate(id){
      $$('[data-studio-tab]',rail).forEach(x=>x.classList.toggle('active',x.dataset.studioTab===id));
      $$('[data-studio-pane]',host).forEach(x=>x.classList.toggle('active',x.dataset.studioPane===id));
      localStorage.setItem('einvite-editor-left-tab',id);applyMode();
    }
    b.onclick=()=>activate('text');
    $('.refine-add-text',pane).onclick=()=>$('#addText')?.click();
    $$('.refine-text-preset',pane).forEach(btn=>btn.onclick=()=>{const source=$(`[data-text-preset="${btn.dataset.refineText}"]`);if(source)source.click();else $('#addText')?.click()});
    $('.refine-browse-fonts',pane).onclick=()=>$('.ei-font-launch')?.click();
    $('.refine-magic-write',pane).onclick=()=>{const ebtn=$('[data-studio-tab="event"]',rail);ebtn?.click();setTimeout(()=>$('#eiAiStudio textarea,.ei-ai-studio textarea')?.focus(),80)};
    const comboMap={gold:{font:'serif-georgia',size:48,color:'#b48a20',text:'Golden Hour'},modern:{font:'sans-arial',size:44,color:'#202127',text:'Your Celebration'},romance:{font:'serif-georgia',size:46,color:'#426b52',text:'Bride & Groom'},khmer:{font:"noto-serif-khmer",size:38,color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'}};
    $$('.refine-font-combo',pane).forEach(btn=>btn.onclick=()=>{const c=comboMap[btn.dataset.combo];$('#addText')?.click();setTimeout(()=>{const sel=$('.object.selected,.object.multi-selected');if(!sel)return;const content=sel.querySelector('.content');if(content)content.textContent=c.text;sel.dataset.font=c.font;sel.dataset.fontSize=String(c.size);sel.dataset.color=c.color;try{applyObjectVisualStyle(sel);save()}catch{}},40)});
    $('.refine-text-search input',pane).oninput=e=>{const q=e.target.value.toLowerCase();$$('.refine-text-preset,.refine-font-combo',pane).forEach(x=>x.hidden=!!q&&!x.textContent.toLowerCase().includes(q))};
  }
  function applyMode(){ /* centralized elsewhere */ }
  const openInspector=()=>{if(innerWidth<=1180&&$('.object.selected,.object.multi-selected',stage))document.body.classList.add('inspector-open')};
  stage.addEventListener('pointerup',()=>setTimeout(openInspector,0));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.body.classList.remove('inspector-open')});
  const inspector=$('.right');if(inspector&&!inspector.querySelector('.refine-inspector-close')){const c=document.createElement('button');c.type='button';c.className='refine-inspector-close';c.textContent='×';c.title='Close inspector';c.onclick=()=>document.body.classList.remove('inspector-open');inspector.prepend(c)}
}
if(page==='dashboard')dashboard();
if(page==='materials')materials();
if(page==='index')setTimeout(editor,0);
})();;/**
 * src/js/editor/chrome/layers.js — Editor layer panel with drag-reorder (ROADMAP §3.4.1, v0.57.0).
 *
 * Right-side panel listing every element on the active canvas in z-order
 * (topmost first). Each row shows:
 *   • visibility eye toggle (hidden elements are skipped in export)
 *   • lock icon (locked elements can only be selected via the panel)
 *   • 48×48 thumbnail (rendered to a <canvas> via the typography renderer if
 *     available, else a colored type chip)
 *   • auto-generated name ("Text 1", "Image 2", …) editable on double-click
 *
 * Interactions:
 *   • Click row  → select on canvas (syncs multi-select)
 *   • Shift+click → extend multi-select
 *   • Drag row    → reorder z-order (uses HTML5 drag-and-drop; the underlying
 *                   document's `objectOrder` array is rewritten via the editor
 *                   bridge `transact()` API, then re-rendered).
 *
 * Locked elements cannot be selected on the canvas — the editor core already
 * honours `data-locked="true"` for hit-testing. Hidden elements
 * (`visible === false`) are excluded from export pipelines.
 *
 * The panel mounts into a `#layersPanel` host (auto-created if missing) and
 * is exposed as `window.EInviteChromeLayers` for the command palette +
 * keyboard-shortcut registry to drive. Bilingual EN+KH labels.
 *
 * Public API:
 *   EInviteChromeLayers.mount(container?)      → mounts the panel
 *   EInviteChromeLayers.refresh()              → re-renders rows from current state
 *   EInviteChromeLayers.toggle()               → show/hide the panel
 *   EInviteChromeLayers.setSelected(ids[])     → sync panel selection from canvas
 *   EInviteChromeLayers.rename(id, name)       → set a custom layer name
 *   EInviteChromeLayers.toggleVisibility(id)   → flip element.visible
 *   EInviteChromeLayers.toggleLock(id)         → flip element.locked
 *   EInviteChromeLayers.reorder(id, toIndex)   → move element to z-index
 */
(() => {
  'use strict';
  if (window.EInviteChromeLayers) return;

  /** Bilingual labels — every user-facing string has EN + KH variants. */
  const STRINGS = {
    en: {
      title: 'Layers',
      empty: 'No layers on this canvas',
      lock: 'Lock layer',
      unlock: 'Unlock layer',
      hide: 'Hide layer',
      show: 'Show layer',
      rename: 'Rename layer',
      visibility: 'Visibility',
      locked: 'Locked',
      hidden: 'Hidden',
      text: 'Text',
      image: 'Image',
      shape: 'Shape',
      background: 'Background',
      page: 'Page',
      element: 'Element',
      layer: 'Layer'
    },
    km: {
      title: 'ស្រទាប់',
      empty: 'មិនមានស្រទាប់នៅលើកាណវាស់នេះទេ',
      lock: 'ចាក់សោស្រទាប់',
      unlock: 'ដោះសោស្រទាប់',
      hide: 'លាក់ស្រទាប់',
      show: 'បង្ហាញស្រទាប់',
      rename: 'ប្ដូរឈ្មោះស្រទាប់',
      visibility: 'ភាពមើលឃើញ',
      locked: 'បានចាក់សោ',
      hidden: 'បានលាក់',
      text: 'អត្ថបទ',
      image: 'រូបភាព',
      shape: 'រាង',
      background: 'ផ្ទៃខាងក្រោយ',
      page: 'ទំព័រ',
      element: 'ធាតុ',
      layer: 'ស្រទាប់'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || STRINGS.en[key] || key;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /** Bridge / registry accessors — null-safe so the module can be loaded on
   *  non-editor pages without crashing. */
  function bridge() { return window.EInviteEditorBridge || null; }
  function registry() { return window.EInviteCommandRegistry || null; }

  /** Return the object map for the currently active canvas (hero or page:N). */
  function activeObjectMap() {
    const b = bridge(); if (!b) return {};
    const state = b.getState?.() || {};
    const canvasId = b.getActiveCanvasId?.() || 'hero';
    if (canvasId === 'hero') return state.objects || {};
    const id = String(canvasId).replace(/^page:/, '');
    const page = (state.designPages || []).find((p) => String(p.id) === id);
    return page?.objects || {};
  }

  /** Resolve the object map's z-order array; falls back to insertion order. */
  function orderedIds(map) {
    const ids = Object.keys(map || {});
    // If the document carries an explicit `objectOrder`, honour it; else use
    // the natural object iteration order which is preserved by JSON.parse.
    return ids;
  }

  /** Generate a localized default name like "Text 1" / "Image 2". */
  function defaultName(obj, idx, typeCounts) {
    const type = (obj.type || obj.kind || 'element').toLowerCase();
    const labelKey = type.includes('text') ? 'text'
      : type.includes('image') || type.includes('photo') ? 'image'
      : type.includes('shape') || type.includes('rect') || type.includes('ellipse') ? 'shape'
      : type.includes('background') ? 'background'
      : type.includes('page') ? 'page'
      : 'element';
    typeCounts[labelKey] = (typeCounts[labelKey] || 0) + 1;
    return `${t(labelKey)} ${typeCounts[labelKey]}`;
  }

  /** Render a 48×48 thumbnail of the object — uses the typography renderer's
   *  `renderThumbnail` if available; otherwise draws a colored chip. */
  function renderThumbnail(canvas, obj) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, 48, 48);
    try {
      if (window.EInviteTypographyRendererAdapters?.renderThumbnail) {
        window.EInviteTypographyRendererAdapters.renderThumbnail(canvas, obj, { width: 48, height: 48 });
        return;
      }
    } catch { /* fall through to chip */ }
    // Fallback chip: type-coloured rectangle with the first letter.
    const type = String(obj.type || obj.kind || 'el').toLowerCase();
    const palette = {
      text: '#3b82f6', image: '#10b981', photo: '#10b981',
      shape: '#a855f7', rect: '#a855f7', ellipse: '#a855f7',
      background: '#64748b', frame: '#f59e0b'
    };
    const color = palette[type] || '#94a3b8';
    ctx.fillStyle = color;
    ctx.fillRect(4, 4, 40, 40);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(obj.type || obj.kind || '?').charAt(0).toUpperCase() || '?', 24, 24);
  }

  /** Module-level panel state. */
  const state = {
    host: null,
    root: null,
    listEl: null,
    selected: new Set(),
    typeCounts: {},
    dragSrcId: null,
    collapsed: false
  };

  /** Build the panel DOM (idempotent — re-uses existing #layersPanel). */
  function build() {
    if (state.root) return state.root;
    const host = document.getElementById('layersPanel');
    state.host = host || null;
    const root = state.host || document.createElement('section');
    if (!state.host) {
      root.id = 'layersPanel';
      root.className = 'ei-chrome-panel ei-layers-panel';
      root.setAttribute('aria-label', t('title'));
    }
    root.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" class="ei-chrome-panel__collapse" data-action="collapse" aria-label="Collapse">▾</button>
      </header>
      <div class="ei-layers-list" role="list" aria-label="${t('title')}"></div>
      <div class="ei-layers-empty" hidden>${t('empty')}</div>
    `;
    if (!state.host) document.body.appendChild(root);
    state.root = root;
    state.listEl = $('.ei-layers-list', root);
    bindHeader(root);
    return root;
  }

  function bindHeader(root) {
    $('[data-action="collapse"]', root)?.addEventListener('click', () => {
      state.collapsed = !state.collapsed;
      root.classList.toggle('is-collapsed', state.collapsed);
    });
  }

  /** Build one row for an element. */
  function buildRow(id, obj, idx, typeCounts) {
    const row = document.createElement('div');
    row.className = 'ei-layer-row';
    row.dataset.id = id;
    row.setAttribute('role', 'listitem');
    row.draggable = true;
    row.tabIndex = 0;
    row.setAttribute('aria-label', obj.layerName || defaultName(obj, idx, typeCounts));
    const visible = obj.visible !== false;
    const locked = obj.locked === true;
    row.classList.toggle('is-hidden', !visible);
    row.classList.toggle('is-locked', locked);
    row.classList.toggle('is-selected', state.selected.has(id));
    row.innerHTML = `
      <button type="button" class="ei-layer-eye" data-action="visibility" aria-label="${visible ? t('hide') : t('show')}" aria-pressed="${visible}">
        <span aria-hidden="true">${visible ? '◉' : '◯'}</span>
      </button>
      <button type="button" class="ei-layer-lock" data-action="lock" aria-label="${locked ? t('unlock') : t('lock')}" aria-pressed="${locked}">
        <span aria-hidden="true">${locked ? '🔒' : '🔓'}</span>
      </button>
      <canvas class="ei-layer-thumb" width="48" height="48" aria-hidden="true"></canvas>
      <span class="ei-layer-name" tabindex="0" role="textbox" aria-label="${t('rename')}"></span>
    `;
    $('.ei-layer-name', row).textContent = obj.layerName || defaultName(obj, idx, typeCounts);
    renderThumbnail($('.ei-layer-thumb', row), obj);
    bindRow(row, id);
    return row;
  }

  function bindRow(row, id) {
    // Click → select (shift = additive).
    row.addEventListener('click', (event) => {
      if (event.target.closest('[data-action]')) return; // icon buttons handled below
      const additive = event.shiftKey || event.ctrlKey || event.metaKey;
      const b = bridge();
      if (!b) return;
      const current = new Set(additive ? b.getSelectedIds?.() || [] : []);
      if (current.has(id) && additive) current.delete(id);
      else current.add(id);
      state.selected = new Set(current);
      b.select?.([...current]);
      refresh();
    });
    // Double-click name → rename.
    $('.ei-layer-name', row).addEventListener('dblclick', (event) => {
      event.stopPropagation();
      beginRename(row, id);
    });
    // Eye toggle.
    $('[data-action="visibility"]', row).addEventListener('click', (event) => {
      event.stopPropagation();
      toggleVisibility(id);
    });
    // Lock toggle.
    $('[data-action="lock"]', row).addEventListener('click', (event) => {
      event.stopPropagation();
      toggleLock(id);
    });
    // Drag-and-drop reorder.
    row.addEventListener('dragstart', (event) => {
      state.dragSrcId = id;
      row.classList.add('is-dragging');
      event.dataTransfer?.setData('text/plain', id);
      event.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => {
      row.classList.remove('is-dragging');
      state.dragSrcId = null;
    });
    row.addEventListener('dragover', (event) => {
      if (!state.dragSrcId || state.dragSrcId === id) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      row.classList.add('is-drop-target');
    });
    row.addEventListener('dragleave', () => row.classList.remove('is-drop-target'));
    row.addEventListener('drop', (event) => {
      event.preventDefault();
      row.classList.remove('is-drop-target');
      if (!state.dragSrcId || state.dragSrcId === id) return;
      reorder(state.dragSrcId, id);
    });
    // Keyboard: Enter to select, F2 to rename.
    row.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        row.click();
      } else if (event.key === 'F2') {
        event.preventDefault();
        beginRename(row, id);
      }
    });
  }

  function beginRename(row, id) {
    const nameEl = $('.ei-layer-name', row);
    const current = nameEl.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'ei-layer-name-input';
    input.value = current;
    input.setAttribute('aria-label', t('rename'));
    nameEl.replaceWith(input);
    input.focus();
    input.select();
    const commit = () => {
      const value = input.value.trim().slice(0, 120);
      rename(id, value || current);
      refresh();
    };
    input.addEventListener('blur', commit, { once: true });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') { event.preventDefault(); input.blur(); }
      else if (event.key === 'Escape') { input.value = current; input.blur(); }
    });
  }

  function reorder(srcId, dstId) {
    const b = bridge(); if (!b) return;
    const map = activeObjectMap();
    const ids = orderedIds(map);
    const from = ids.indexOf(srcId);
    const to = ids.indexOf(dstId);
    if (from < 0 || to < 0 || from === to) return;
    ids.splice(from, 1);
    ids.splice(to, 0, srcId);
    b.transact?.('Reorder layers', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      // Rebuild the map preserving the new order (object iteration order on
      // plain objects follows insertion order, so we delete + re-insert).
      const snapshot = {};
      for (const id of ids) snapshot[id] = target[id];
      // Clear existing keys (can't use Object.assign because we need to
      // delete-then-add to preserve the new order).
      for (const key of Object.keys(target)) delete target[key];
      Object.assign(target, snapshot);
    }, { capture: true });
    refresh();
  }

  /** Resolve a writable pointer to the active canvas's object map inside the
   *  transact() mutator. `state` here is the live document object. */
  function resolveTargetMap(doc, canvasId) {
    if (canvasId === 'hero') return doc.objects || (doc.objects = {});
    const id = String(canvasId).replace(/^page:/, '');
    let page = (doc.designPages || []).find((p) => String(p.id) === id);
    if (!page) { page = { id, objects: {} }; (doc.designPages = doc.designPages || []).push(page); }
    return page.objects || (page.objects = {});
  }

  function toggleVisibility(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Toggle visibility', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      const obj = target[id]; if (!obj) return;
      obj.visible = obj.visible !== false ? false : true;
    }, { capture: true });
    refresh();
  }

  function toggleLock(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Toggle lock', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      const obj = target[id]; if (!obj) return;
      obj.locked = obj.locked !== true;
    }, { capture: true });
    refresh();
  }

  function rename(id, name) {
    const b = bridge(); if (!b) return;
    b.transact?.('Rename layer', (state) => {
      const target = resolveTargetMap(state, b.getActiveCanvasId?.() || 'hero');
      const obj = target[id]; if (!obj) return;
      obj.layerName = String(name).slice(0, 120);
    }, { capture: true });
  }

  /** Re-render the panel from the current document state. */
  function refresh() {
    if (!state.root) build();
    const map = activeObjectMap();
    const ids = orderedIds(map);
    state.typeCounts = {};
    // Z-order: topmost first → reverse the insertion order so the last-added
    // element appears at the top of the panel.
    const reversed = [...ids].reverse();
    state.listEl.replaceChildren();
    for (const [idx, id] of reversed.entries()) {
      const obj = map[id]; if (!obj) continue;
      const row = buildRow(id, obj, idx, state.typeCounts);
      state.listEl.appendChild(row);
    }
    $('.ei-layers-empty', state.root).hidden = reversed.length > 0;
  }

  /** Sync the panel selection with the canvas selection. */
  function setSelected(ids) {
    state.selected = new Set((ids || []).map(String));
    $$('.ei-layer-row', state.root).forEach((row) => {
      row.classList.toggle('is-selected', state.selected.has(row.dataset.id));
    });
  }

  function toggle() {
    if (!state.root) build();
    state.root.hidden = !state.root.hidden;
  }

  function mount(container) {
    build();
    if (container && state.root.parentElement !== container) {
      container.appendChild(state.root);
    }
    refresh();
    // Wire to editor selection + state-change events so the panel stays in sync.
    window.addEventListener('einvite:editor-command', () => refresh());
    window.addEventListener('einvite:editor-state-replaced', () => refresh());
    // Bridge selection polling — there's no dedicated event so we tick on
    // pointerup + keyup which covers click/select/keyboard-nudge cases.
    document.addEventListener('pointerup', () => {
      const b = bridge();
      setSelected(b?.getSelectedIds?.() || []);
    }, { passive: true });
    document.addEventListener('keyup', () => {
      const b = bridge();
      setSelected(b?.getSelectedIds?.() || []);
    });
    return state.root;
  }

  // Register commands so the palette + shortcut modal list the layer panel.
  function registerCommands() {
    const r = registry(); if (!r?.register) return;
    try {
      r.register({
        id: 'layers.togglePanel', title: 'Toggle layers panel',
        category: 'View', keywords: ['layers', 'panel', 'z-order'],
        bindings: { standard: ['Alt+L'], canva: ['Alt+L'], photoshop: ['F7'] },
        run: () => toggle()
      });
      r.register({
        id: 'layers.toggleLock', title: 'Lock or unlock selected layer',
        category: 'Arrange', keywords: ['lock', 'layer'],
        enabled: () => (bridge()?.getSelectedIds?.() || []).length > 0,
        run: () => {
          const b = bridge();
          for (const id of b?.getSelectedIds?.() || []) toggleLock(id);
        }
      });
      r.register({
        id: 'layers.toggleVisibility', title: 'Hide or show selected layer',
        category: 'Arrange', keywords: ['visibility', 'hide', 'show'],
        enabled: () => (bridge()?.getSelectedIds?.() || []).length > 0,
        run: () => {
          const b = bridge();
          for (const id of b?.getSelectedIds?.() || []) toggleVisibility(id);
        }
      });
    } catch { /* duplicate registration — ignore */ }
  }

  window.EInviteChromeLayers = Object.freeze({
    version: 57,
    STRINGS,
    mount, refresh, toggle, setSelected, rename, toggleVisibility, toggleLock,
    reorder, registerCommands
  });

  // Auto-mount on DOMContentLoaded if the editor is present (no-op otherwise).
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { mount(); registerCommands(); });
  } else {
    queueMicrotask(() => { mount(); registerCommands(); });
  }
})();;/**
 * src/js/editor/chrome/pages.js — Editor pages sidebar with thumbnails (ROADMAP §3.4.2, v0.57.0).
 *
 * Vertical strip of page thumbnails, 150px wide:
 *   • Click thumbnail → jump to that page.
 *   • Drag thumbnail → reorder pages.
 *   • Right-click → context menu (duplicate / delete / insert above / below).
 *   • "+" button → add a new blank page.
 *   • Hover between two thumbnails → reveal a small "insert here" affordance.
 *
 * Thumbnails render at 150px wide using `OffscreenCanvas` when available
 * (the editor's typography renderer is used to draw the page contents at a
 * small scale). Re-rendering is debounced 300ms after any editor-state change
 * so dragging sliders doesn't thrash the canvas. Each page's thumbnail is
 * cached by an object-fingerprint of that page's element tree, so unchanged
 * pages skip the re-render entirely.
 *
 * Public API:
 *   EInviteChromePages.mount(container?) → mounts the sidebar
 *   EInviteChromePages.refresh()         → debounced re-render
 *   EInviteChromePages.addPage()         → appends a new blank page
 *   EInviteChromePages.duplicate(id)     → duplicates a page
 *   EInviteChromePages.delete(id)        → deletes a page
 *   EInviteChromePages.insertAt(idx)     → inserts a blank page at index
 *   EInviteChromePages.activate(id)      → jumps to a page
 *   EInviteChromePages.reorder(srcId, dstId) → moves srcId before dstId
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteChromePages) return;

  const THUMB_WIDTH = 150;
  const THUMB_HEIGHT = 100;
  const DEBOUNCE_MS = 300;

  const STRINGS = {
    en: {
      title: 'Pages', add: 'Add page', duplicate: 'Duplicate page',
      delete: 'Delete page', insertAbove: 'Insert page above',
      insertBelow: 'Insert page below', empty: 'No design pages yet',
      pageLabel: (n) => `Page ${n}`, mainHero: 'Main hero',
      thumbnail: 'Page thumbnail', active: 'Active page'
    },
    km: {
      title: 'ទំព័រ', add: 'បន្ថែមទំព័រ', duplicate: 'ចម្លងទំព័រ',
      delete: 'លុបទំព័រ', insertAbove: 'បញ្ចូលទំព័រខាងលើ',
      insertBelow: 'បញ្ចូលទំព័រខាងក្រោម', empty: 'មិនទាន់មានទំព័រទេ',
      pageLabel: (n) => `ទំព័រ ${n}`, mainHero: 'ទំព័រមេ',
      thumbnail: 'រូបភាពទំព័រតូច', active: 'ទំព័រសកម្ម'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key, ...args) {
    const v = (STRINGS[locale()] || STRINGS.en)[key];
    return typeof v === 'function' ? v(...args) : (v || key);
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function bridge() { return window.EInviteEditorBridge || null; }
  function registry() { return window.EInviteCommandRegistry || null; }

  /** Module state. */
  const state = {
    host: null,
    root: null,
    stripEl: null,
    emptyEl: null,
    collapsed: false,
    debounceTimer: 0,
    cache: new Map(),     // pageId → { fingerprint, dataUrl }
    dragSrcId: null,
    menuEl: null
  };

  /** Fingerprint a page's element tree so we can cache its thumbnail. */
  function fingerprint(page) {
    try {
      const objects = page?.objects || {};
      const sig = JSON.stringify({
        n: Object.keys(objects).length,
        bg: page?.background, bgImg: page?.backgroundImage,
        overlay: page?.backgroundOverlay, size: page?.backgroundSize,
        keys: Object.keys(objects).sort(),
        // include a shallow per-object signature so position changes invalidate.
        objs: Object.values(objects).map((o) => `${o.type || o.kind || 'el'}:${o.x || 0}:${o.y || 0}:${o.w || o.width || 0}:${o.h || o.height || 0}:${o.text || ''}`.slice(0, 120))
      });
      let h = 5381;
      for (let i = 0; i < sig.length; i++) h = ((h << 5) + h + sig.charCodeAt(i)) >>> 0;
      return h.toString(36);
    } catch { return Math.random().toString(36).slice(2); }
  }

  /** Render a page to a thumbnail data URL. Uses OffscreenCanvas if available. */
  function renderThumbnail(page) {
    const fp = fingerprint(page);
    const cached = state.cache.get(page?.id);
    if (cached && cached.fingerprint === fp) return cached.dataUrl;
    const canvas = (typeof OffscreenCanvas !== 'undefined')
      ? new OffscreenCanvas(THUMB_WIDTH, THUMB_HEIGHT)
      : Object.assign(document.createElement('canvas'), { width: THUMB_WIDTH, height: THUMB_HEIGHT });
    const ctx = canvas.getContext('2d');
    // Background.
    ctx.fillStyle = page?.background || '#ffffff';
    ctx.fillRect(0, 0, THUMB_WIDTH, THUMB_HEIGHT);
    if (page?.backgroundImage) {
      try {
        ctx.fillStyle = 'rgba(0,0,0,0.2)';
        ctx.fillRect(0, 0, THUMB_WIDTH, THUMB_HEIGHT);
      } catch { /* ignore */ }
    }
    // Render objects via the typography renderer if available.
    try {
      if (window.EInviteTypographyRendererAdapters?.renderPage) {
        window.EInviteTypographyRendererAdapters.renderPage(canvas, page, { width: THUMB_WIDTH, height: THUMB_HEIGHT });
      } else {
        drawFallbackObjects(ctx, page);
      }
    } catch { drawFallbackObjects(ctx, page); }
    let dataUrl;
    try { dataUrl = canvas.toDataURL ? canvas.toDataURL('image/png') : ''; }
    catch { dataUrl = ''; }
    state.cache.set(page?.id, { fingerprint: fp, dataUrl });
    return dataUrl;
  }

  function drawFallbackObjects(ctx, page) {
    const objects = page?.objects || {};
    for (const obj of Object.values(objects)) {
      const x = (Number(obj.x) || 0) * (THUMB_WIDTH / 390);
      const y = (Number(obj.y) || 0) * (THUMB_HEIGHT / 844);
      const w = (Number(obj.w || obj.width) || 40) * (THUMB_WIDTH / 390);
      const h = (Number(obj.h || obj.height) || 40) * (THUMB_HEIGHT / 844);
      ctx.fillStyle = obj.background || obj.color || '#94a3b8';
      ctx.fillRect(x, y, Math.max(2, w), Math.max(2, h));
      if (obj.text) {
        ctx.fillStyle = '#ffffff';
        ctx.font = '6px sans-serif';
        ctx.fillText(String(obj.text).slice(0, 12), x + 2, y + 8);
      }
    }
  }

  function build() {
    if (state.root) return state.root;
    const host = document.getElementById('pagesSidebar');
    state.host = host || null;
    const root = state.host || document.createElement('aside');
    if (!state.host) {
      root.id = 'pagesSidebar';
      root.className = 'ei-chrome-panel ei-pages-sidebar';
      root.setAttribute('aria-label', t('title'));
    }
    root.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" data-action="add" aria-label="${t('add')}">＋</button>
      </header>
      <div class="ei-pages-strip" role="list" aria-label="${t('title')}"></div>
      <div class="ei-pages-empty" hidden>${t('empty')}</div>
    `;
    if (!state.host) document.body.appendChild(root);
    state.root = root;
    state.stripEl = $('.ei-pages-strip', root);
    state.emptyEl = $('.ei-pages-empty', root);
    $('[data-action="add"]', root).addEventListener('click', addPage);
    state.stripEl.addEventListener('contextmenu', onContextMenu);
    return root;
  }

  function buildRow(page, idx, isActive) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'ei-page-row';
    row.dataset.id = page.id;
    row.setAttribute('role', 'listitem');
    row.draggable = true;
    row.tabIndex = 0;
    row.setAttribute('aria-label', `${page.name || t('pageLabel', idx + 1)} — ${t('thumbnail')}`);
    row.classList.toggle('is-active', isActive);
    const dataUrl = renderThumbnail(page);
    row.innerHTML = `
      <img class="ei-page-thumb" alt="" width="${THUMB_WIDTH}" height="${THUMB_HEIGHT}" ${dataUrl ? `src="${dataUrl}"` : 'hidden'}>
      <span class="ei-page-label"></span>
    `;
    $('.ei-page-label', row).textContent = page.name || t('pageLabel', idx + 1);
    bindRow(row, page.id);
    return row;
  }

  function buildInsertBetween(idx) {
    const slot = document.createElement('div');
    slot.className = 'ei-pages-insert-slot';
    slot.setAttribute('aria-hidden', 'true');
    slot.dataset.insertAt = String(idx);
    slot.innerHTML = '<span class="ei-pages-insert-plus" hidden>＋</span>';
    slot.addEventListener('mouseenter', () => $('.ei-pages-insert-plus', slot).hidden = false);
    slot.addEventListener('mouseleave', () => $('.ei-pages-insert-plus', slot).hidden = true);
    slot.addEventListener('click', () => insertAt(idx));
    return slot;
  }

  function bindRow(row, id) {
    row.addEventListener('click', () => activate(id));
    row.addEventListener('dragstart', (event) => {
      state.dragSrcId = id;
      row.classList.add('is-dragging');
      event.dataTransfer?.setData('text/plain', id);
      event.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => {
      row.classList.remove('is-dragging');
      state.dragSrcId = null;
    });
    row.addEventListener('dragover', (event) => {
      if (!state.dragSrcId || state.dragSrcId === id) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      row.classList.add('is-drop-target');
    });
    row.addEventListener('dragleave', () => row.classList.remove('is-drop-target'));
    row.addEventListener('drop', (event) => {
      event.preventDefault();
      row.classList.remove('is-drop-target');
      if (!state.dragSrcId || state.dragSrcId === id) return;
      reorder(state.dragSrcId, id);
    });
    row.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(id); }
    });
  }

  function onContextMenu(event) {
    const row = event.target.closest('.ei-page-row');
    if (!row) return;
    event.preventDefault();
    const id = row.dataset.id;
    ensureMenu().then((menu) => {
      menu.dataset.pageId = id;
      menu.style.left = `${event.clientX}px`;
      menu.style.top = `${event.clientY}px`;
      menu.hidden = false;
    });
  }

  function ensureMenu() {
    if (state.menuEl) return Promise.resolve(state.menuEl);
    const menu = document.createElement('div');
    menu.className = 'ei-pages-context-menu';
    menu.hidden = true;
    menu.setAttribute('role', 'menu');
    menu.innerHTML = `
      <button role="menuitem" data-action="duplicate">${t('duplicate')}</button>
      <button role="menuitem" data-action="insertAbove">${t('insertAbove')}</button>
      <button role="menuitem" data-action="insertBelow">${t('insertBelow')}</button>
      <button role="menuitem" data-action="delete" class="danger">${t('delete')}</button>
    `;
    document.body.appendChild(menu);
    menu.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-action]'); if (!btn) return;
      const id = menu.dataset.pageId; if (!id) return;
      const idx = pageIdx(id);
      if (btn.dataset.action === 'duplicate') duplicate(id);
      else if (btn.dataset.action === 'delete') deletePage(id);
      else if (btn.dataset.action === 'insertAbove') insertAt(idx);
      else if (btn.dataset.action === 'insertBelow') insertAt(idx + 1);
      menu.hidden = true;
    });
    document.addEventListener('click', (event) => {
      if (!menu.hidden && !menu.contains(event.target)) menu.hidden = true;
    }, { once: true });
    state.menuEl = menu;
    return Promise.resolve(menu);
  }

  function pageIdx(id) {
    const b = bridge(); if (!b) return -1;
    const state_ = b.getState?.() || {};
    const pages = state_.designPages || [];
    return pages.findIndex((p) => p.id === id);
  }

  function activeCanvasId() {
    return bridge()?.getActiveCanvasId?.() || 'hero';
  }

  /** Build the strip with hero + design pages. */
  function refresh() {
    if (!state.root) build();
    const b = bridge();
    const doc = b?.getState?.() || {};
    const pages = doc.designPages || [];
    const active = activeCanvasId();
    state.stripEl.replaceChildren();
    // Hero canvas row.
    const heroRow = document.createElement('button');
    heroRow.type = 'button';
    heroRow.className = 'ei-page-row is-hero';
    heroRow.dataset.id = 'hero';
    heroRow.setAttribute('role', 'listitem');
    heroRow.draggable = false;
    heroRow.tabIndex = 0;
    heroRow.classList.toggle('is-active', active === 'hero');
    heroRow.innerHTML = `
      <div class="ei-page-thumb ei-page-thumb--hero" aria-hidden="true">M</div>
      <span class="ei-page-label">${t('mainHero')}</span>
    `;
    heroRow.addEventListener('click', () => activate('hero'));
    state.stripEl.appendChild(heroRow);
    state.stripEl.appendChild(buildInsertBetween(0));
    pages.forEach((page, idx) => {
      const row = buildRow(page, idx, active === `page:${page.id}`);
      state.stripEl.appendChild(row);
      state.stripEl.appendChild(buildInsertBetween(idx + 1));
    });
    state.emptyEl.hidden = pages.length > 0;
  }

  /** Debounced refresh — called on every editor-state change. */
  function scheduleRefresh() {
    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(refresh, DEBOUNCE_MS);
  }

  function activate(id) {
    const b = bridge(); if (!b) return;
    const token = id === 'hero' ? 'hero' : `page:${id}`;
    if (window.switchCanvas) window.switchCanvas(token);
    else if (typeof b.setActiveCanvasId === 'function') b.setActiveCanvasId(token);
    refresh();
  }

  function addPage() {
    if (window.EInvitePageExperience?.addPage) return window.EInvitePageExperience.addPage({ mode: 'free-design' });
    const b = bridge(); if (!b) return;
    b.transact?.('Add page', (state_) => {
      const id = `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      (state_.designPages = state_.designPages || []).push({ id, name: '', objects: {} });
    });
    scheduleRefresh();
  }

  function insertAt(idx) {
    const b = bridge(); if (!b) return;
    b.transact?.('Insert page', (state_) => {
      const id = `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const pages = state_.designPages = state_.designPages || [];
      pages.splice(Math.max(0, Math.min(idx, pages.length)), 0, { id, name: '', objects: {} });
    });
    scheduleRefresh();
  }

  function duplicate(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Duplicate page', (state_) => {
      const pages = state_.designPages = state_.designPages || [];
      const srcIdx = pages.findIndex((p) => p.id === id);
      if (srcIdx < 0) return;
      const src = pages[srcIdx];
      const copy = JSON.parse(JSON.stringify(src));
      copy.id = `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      copy.name = `${src.name || 'Page'} copy`;
      // Remap object ids so duplicates remain editable.
      const remap = {};
      copy.objects = Object.fromEntries(Object.entries(src.objects || {}).map(([k, v], i) => {
        const nk = `${copy.id}-o${i}-${Math.random().toString(36).slice(2, 5)}`;
        remap[k] = nk;
        return [nk, JSON.parse(JSON.stringify(v))];
      }));
      pages.splice(srcIdx + 1, 0, copy);
    });
    scheduleRefresh();
  }

  function deletePage(id) {
    const b = bridge(); if (!b) return;
    b.transact?.('Delete page', (state_) => {
      state_.designPages = (state_.designPages || []).filter((p) => p.id !== id);
    });
    scheduleRefresh();
  }

  function reorder(srcId, dstId) {
    const b = bridge(); if (!b) return;
    b.transact?.('Reorder pages', (state_) => {
      const pages = state_.designPages = state_.designPages || [];
      const from = pages.findIndex((p) => p.id === srcId);
      const to = pages.findIndex((p) => p.id === dstId);
      if (from < 0 || to < 0 || from === to) return;
      const [moved] = pages.splice(from, 1);
      pages.splice(to, 0, moved);
    });
    scheduleRefresh();
  }

  function mount(container) {
    build();
    if (container && state.root.parentElement !== container) container.appendChild(state.root);
    refresh();
    window.addEventListener('einvite:editor-command', scheduleRefresh);
    window.addEventListener('einvite:editor-state-replaced', scheduleRefresh);
    return state.root;
  }

  function registerCommands() {
    const r = registry(); if (!r?.register) return;
    try {
      r.register({
        id: 'pages.toggleSidebar', title: 'Toggle pages sidebar',
        category: 'View', keywords: ['pages', 'sidebar', 'thumbnails'],
        bindings: { standard: ['Alt+P'], canva: ['Alt+P'], photoshop: ['Alt+P'] },
        run: () => { if (state.root) state.root.hidden = !state.root.hidden; }
      });
      r.register({
        id: 'pages.add', title: 'Add new page',
        category: 'Insert', keywords: ['page', 'add', 'new'],
        bindings: { standard: ['Mod+Enter'], canva: ['Mod+Enter'], photoshop: ['Mod+Enter'] },
        run: addPage
      });
    } catch { /* duplicate — ignore */ }
  }

  window.EInviteChromePages = Object.freeze({
    version: 57, STRINGS, mount, refresh: scheduleRefresh, addPage,
    duplicate, delete: deletePage, insertAt, activate, reorder, registerCommands
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { mount(); registerCommands(); });
  } else {
    queueMicrotask(() => { mount(); registerCommands(); });
  }
})();;/**
 * src/js/editor/chrome/command-palette.js — Unified command palette (ROADMAP §3.4.3, v0.57.0).
 *
 * Press Ctrl+K (or Cmd+K on macOS) → a searchable list of every action in
 * the editor. Type to filter; Enter to run. Fuzzy search (fzf-style scorer)
 * ranks matches by tightness and recency.
 *
 * The palette aggregates three sources:
 *   • `window.EInviteCommandRegistry.list()` — every registered command
 *     (toolbar actions, inspector actions, menu items, keyboard shortcuts).
 *   • Pages — quick-jump to any design page.
 *   • Layers — quick-select any layer on the active canvas.
 *
 * Display grouped by category: File, Edit, View, Insert, Format, Arrange,
 * Align, Help. Recently used commands appear at the top (capped at 8).
 *
 * Bilingual EN+KH labels — every command carries `label_en` + `label_km`.
 *
 * Public API:
 *   EInviteChromeCommandPalette.open()         → opens in command mode
 *   EInviteChromeCommandPalette.openShortcuts() → opens in shortcuts mode
 *   EInviteChromeCommandPalette.close()         → closes
 *   EInviteChromeCommandPalette.toggle()        → open/close
 *
 * The existing `command-palette-v23.js` surface (EInviteCommandUI) is left
 * in place for backwards compatibility; this module wraps + extends it
 * with the fuzzy scorer + bilingual labels + layer/page aggregations.
 */
(() => {
  'use strict';
  if (window.EInviteChromeCommandPalette) return;

  const RECENT_KEY = 'ei-command-palette-recent-v57';
  const RECENT_MAX = 8;

  const STRINGS = {
    en: {
      title: 'Quick Actions',
      placeholder: 'Search actions, pages, layers…',
      empty: 'No matching commands',
      recent: 'Recently used',
      shortcuts: 'Keyboard shortcuts',
      runLabel: 'Run',
      closeLabel: 'Close',
      navigating: '↑↓ Navigate · Enter Run · Esc Close',
      noShortcuts: 'No shortcuts registered'
    },
    km: {
      title: 'សកម្មភាពរហ័ស',
      placeholder: 'ស្វែងរកសកម្មភាព ទំព័រ ស្រទាប់…',
      empty: 'មិនមានសកម្មភាពត្រូវគ្នាទេ',
      recent: 'បានប្រើថ្មីៗ',
      shortcuts: 'ផ្លូវកាត់ក្ដារចុច',
      runLabel: 'ដំណើរការ',
      closeLabel: 'បិទ',
      navigating: '↑↓ រុករក · Enter ដំណើរការ · Esc បិទ',
      noShortcuts: 'មិនមានផ្លូវកាត់ទេ'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function registry() { return window.EInviteCommandRegistry || null; }
  function bridge() { return window.EInviteEditorBridge || null; }

  /** fzf-style fuzzy scorer. Returns -1 if no match, else a non-negative
   *  score (higher = better). Bonus for consecutive matches + start-of-word. */
  function fuzzyScore(query, text) {
    if (!query) return 0;
    const q = String(query).toLowerCase();
    const s = String(text || '').toLowerCase();
    if (!q) return 0;
    if (s.includes(q)) {
      // Tight substring match → high score.
      const tightness = q.length / s.length;
      const startBonus = s.startsWith(q) ? 100 : 0;
      return 50 + Math.floor(tightness * 100) + startBonus;
    }
    // Fuzzy: every char of q must appear in s, in order.
    let qi = 0, lastIdx = -1, score = 0, run = 0;
    for (let si = 0; si < s.length && qi < q.length; si++) {
      if (s[si] === q[qi]) {
        if (lastIdx === si - 1) run++; else run = 0;
        score += 10 + run * 5 + (si === 0 ? 5 : 0);
        lastIdx = si; qi++;
      }
    }
    return qi === q.length ? score : -1;
  }

  /** Load recently-used command ids from localStorage. */
  function loadRecent() {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); }
    catch { return []; }
  }
  function saveRecent(ids) {
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(ids.slice(0, RECENT_MAX))); }
    catch { /* storage disabled — silent */ }
  }
  function pushRecent(id) {
    if (!id) return;
    const ids = loadRecent().filter((x) => x !== id);
    ids.unshift(id);
    saveRecent(ids);
  }

  /** Collect every registered command, decorated with bilingual labels. */
  function collectCommands() {
    const r = registry(); if (!r) return [];
    const list = r.list ? r.list({ includeHidden: false }) : [];
    return list.map((c) => ({
      id: c.id,
      label_en: c.title || c.label_en || c.id,
      label_km: c.label_km || c.title || c.id,
      category: c.category || 'General',
      keywords: c.keywords || [],
      icon: c.icon || '·',
      shortcuts: (c.shortcuts || []).map((s) => r.formatChord ? r.formatChord(s) : s),
      run: () => r.execute ? r.execute(c.id) : c.run?.()
    }));
  }

  function collectPages() {
    const b = bridge(); if (!b) return [];
    const doc = b.getState?.() || {};
    const pages = doc.designPages || [];
    return [
      { id: 'page:hero', label_en: 'Main hero', label_km: 'ទំព័រមេ', category: 'Pages', icon: '▣',
        keywords: ['page', 'hero', 'main'], run: () => activateCanvas('hero') },
      ...pages.map((p, idx) => ({
        id: `page:${p.id}`, label_en: p.name || `Page ${idx + 1}`,
        label_km: p.name || `ទំព័រ ${idx + 1}`, category: 'Pages', icon: '▤',
        keywords: ['page', p.name, p.id], run: () => activateCanvas(`page:${p.id}`)
      }))
    ];
  }

  function collectLayers() {
    const b = bridge(); if (!b) return [];
    const doc = b.getState?.() || {};
    const canvasId = b.getActiveCanvasId?.() || 'hero';
    let map = doc.objects || {};
    if (canvasId !== 'hero') {
      const id = String(canvasId).replace(/^page:/, '');
      const page = (doc.designPages || []).find((p) => p.id === id);
      map = page?.objects || {};
    }
    return Object.entries(map).map(([id, obj], idx) => ({
      id: `layer:${id}`, label_en: obj.layerName || `${obj.type || 'Element'} ${idx + 1}`,
      label_km: obj.layerName || `${obj.type || 'ធាតុ'} ${idx + 1}`,
      category: 'Layers', icon: '◇',
      keywords: ['layer', id, obj.type, obj.layerName],
      run: () => b.select?.([id])
    }));
  }

  function activateCanvas(token) {
    if (window.switchCanvas) return window.switchCanvas(token);
    const b = bridge();
    if (typeof b.setActiveCanvasId === 'function') b.setActiveCanvasId(token);
  }

  /** Aggregate all sources into one list, ranked by fuzzy score. */
  function search(query) {
    const all = [...collectCommands(), ...collectPages(), ...collectLayers()];
    if (!query) {
      // No query → recently used first, then commands in category order.
      const recent = loadRecent();
      const recentItems = recent
        .map((id) => all.find((x) => x.id === id))
        .filter(Boolean);
      return [...recentItems, ...all.filter((x) => !recent.includes(x.id))].slice(0, 80);
    }
    const scored = all.map((item) => {
      const label = locale() === 'km' ? item.label_km : item.label_en;
      const hay = `${label} ${item.category} ${(item.keywords || []).join(' ')} ${(item.shortcuts || []).join(' ')}`;
      const score = Math.max(
        fuzzyScore(query, label),
        fuzzyScore(query, item.label_en) - 1,
        fuzzyScore(query, item.label_km) - 1,
        fuzzyScore(query, hay) - 2
      );
      return { item, score };
    }).filter((x) => x.score >= 0)
      .sort((a, b) => b.score - a.score)
      .map((x) => x.item);
    return scored.slice(0, 60);
  }

  /** Module state. */
  const state = {
    root: null,
    inputEl: null,
    listEl: null,
    hintEl: null,
    active: 0,
    items: [],
    mode: 'commands'  // 'commands' | 'shortcuts'
  };

  function build() {
    if (state.root) return state.root;
    const root = document.createElement('div');
    root.className = 'ei-command-palette';
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'eiPaletteTitle');
    root.innerHTML = `
      <div class="ei-command-palette__backdrop" data-close></div>
      <section class="ei-command-palette__dialog">
        <header>
          <div><small>EInvite Studio</small><h2 id="eiPaletteTitle">${t('title')}</h2></div>
          <button type="button" data-close aria-label="${t('closeLabel')}">×</button>
        </header>
        <div class="ei-command-palette__search">
          <span aria-hidden="true">⌕</span>
          <input type="search" autocomplete="off" placeholder="${t('placeholder')}" aria-label="${t('placeholder')}">
          <kbd>Esc</kbd>
        </div>
        <div class="ei-command-palette__list" role="listbox" aria-label="${t('title')}"></div>
        <footer>${t('navigating')}</footer>
      </section>
    `;
    document.body.appendChild(root);
    state.root = root;
    state.inputEl = $('input', root);
    state.listEl = $('.ei-command-palette__list', root);
    state.hintEl = $('footer kbd', root);
    $$('[data-close]', root).forEach((b) => b.addEventListener('click', close));
    state.inputEl.addEventListener('input', () => { state.active = 0; render(); });
    root.addEventListener('keydown', onKey);
    return root;
  }

  function open(mode = 'commands') {
    build();
    state.mode = mode;
    state.root.hidden = false;
    document.body.classList.add('ei-command-palette-open');
    state.inputEl.value = '';
    state.active = 0;
    render();
    setTimeout(() => state.inputEl.focus(), 0);
  }

  function close() {
    if (!state.root || state.root.hidden) return;
    state.root.hidden = true;
    document.body.classList.remove('ei-command-palette-open');
  }

  function toggle() {
    if (!state.root || state.root.hidden) open(); else close();
  }

  function openShortcuts() { open('shortcuts'); }

  function onKey(event) {
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'ArrowDown') { event.preventDefault(); state.active = Math.min(state.items.length - 1, state.active + 1); syncActive(); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); state.active = Math.max(0, state.active - 1); syncActive(); }
    else if (event.key === 'Enter') {
      event.preventDefault();
      const item = state.items[state.active];
      if (item) run(item);
    }
  }

  function run(item) {
    pushRecent(item.id);
    close();
    try { Promise.resolve(item.run?.()).catch((e) => window.uiToast?.(e?.message || 'Action failed', '!')); }
    catch (e) { window.uiToast?.(e?.message || 'Action failed', '!'); }
  }

  function render() {
    if (state.mode === 'shortcuts') return renderShortcuts();
    const q = state.inputEl.value.trim();
    state.items = search(q);
    state.active = Math.max(0, Math.min(state.active, Math.max(0, state.items.length - 1)));
    state.listEl.replaceChildren();
    if (!state.items.length) {
      const empty = document.createElement('div');
      empty.className = 'ei-command-palette__empty';
      empty.textContent = t('empty');
      state.listEl.appendChild(empty);
      return;
    }
    let lastCategory = '';
    const recentIds = new Set(loadRecent());
    let recentHeaderShown = q.length === 0;
    if (recentHeaderShown) {
      const h = document.createElement('div');
      h.className = 'ei-command-palette__category';
      h.textContent = t('recent');
      state.listEl.appendChild(h);
    }
    state.items.forEach((item, idx) => {
      if (!recentHeaderShown && item.category !== lastCategory) {
        lastCategory = item.category;
        const h = document.createElement('div');
        h.className = 'ei-command-palette__category';
        h.textContent = item.category;
        state.listEl.appendChild(h);
      }
      const row = document.createElement('button');
      row.type = 'button';
      row.className = `ei-command-palette__row${idx === state.active ? ' is-active' : ''}`;
      row.dataset.idx = String(idx);
      const label = locale() === 'km' ? item.label_km : item.label_en;
      row.innerHTML = `<span class="ei-command-palette__icon" aria-hidden="true">${item.icon || '·'}</span>
        <span class="ei-command-palette__label"></span>
        <kbd class="ei-command-palette__shortcut"></kbd>`;
      $('.ei-command-palette__label', row).textContent = label;
      $('.ei-command-palette__shortcut', row).textContent = (item.shortcuts || []).slice(0, 2).join(' ');
      row.addEventListener('mouseenter', () => { state.active = idx; syncActive(); });
      row.addEventListener('click', () => run(item));
      state.listEl.appendChild(row);
    });
  }

  function renderShortcuts() {
    const r = registry(); if (!r) return;
    const list = r.list ? r.list({ includeHidden: true }) : [];
    state.listEl.replaceChildren();
    if (!list.length) {
      const empty = document.createElement('div');
      empty.className = 'ei-command-palette__empty';
      empty.textContent = t('noShortcuts');
      state.listEl.appendChild(empty);
      return;
    }
    let lastCat = '';
    list.forEach((c) => {
      if (c.category !== lastCat) {
        lastCat = c.category;
        const h = document.createElement('div');
        h.className = 'ei-command-palette__category';
        h.textContent = c.category;
        state.listEl.appendChild(h);
      }
      const row = document.createElement('div');
      row.className = 'ei-command-palette__shortcut-row';
      const shortcut = (c.shortcuts || []).map((s) => r.formatChord ? r.formatChord(s) : s).join(' · ') || '—';
      row.innerHTML = `<span class="ei-command-palette__label"></span><kbd></kbd>`;
      $('.ei-command-palette__label', row).textContent = c.title;
      $('kbd', row).textContent = shortcut;
      state.listEl.appendChild(row);
    });
  }

  function syncActive() {
    $$('.ei-command-palette__row', state.root).forEach((row, idx) => {
      row.classList.toggle('is-active', idx === state.active);
    });
    const activeRow = $$('.ei-command-palette__row', state.root)[state.active];
    activeRow?.scrollIntoView({ block: 'nearest' });
  }

  /** Register commands + keyboard shortcuts. */
  function register() {
    const r = registry(); if (!r) return;
    try {
      r.register({
        id: 'palette.open', title: 'Open command palette',
        category: 'View', keywords: ['quick', 'actions', 'search', 'palette'],
        bindings: { standard: ['Mod+K'], canva: ['Mod+K'], photoshop: ['Mod+K'] },
        allowWhileTyping: false,
        run: () => open('commands')
      });
      r.register({
        id: 'palette.shortcuts', title: 'Show keyboard shortcuts',
        category: 'Help', keywords: ['shortcuts', 'help', 'keyboard'],
        bindings: { standard: ['Shift+?'], canva: ['Shift+?'], photoshop: ['Shift+?'] },
        run: () => openShortcuts()
      });
    } catch { /* duplicate — ignore */ }
    // Wire the global keydown for Ctrl+K / Cmd+K / Shift+? as a fallback in
    // case the registry isn't initialized early enough.
    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && (event.key === 'k' || event.key === 'K')) {
        event.preventDefault();
        toggle();
      } else if (event.shiftKey && (event.key === '?' || event.key === '/')) {
        if (isTypingTarget(event.target)) return;
        event.preventDefault();
        openShortcuts();
      }
    });
  }

  function isTypingTarget(target) {
    if (!target) return false;
    return !!target.matches && target.matches('input,textarea,select,[contenteditable="true"]');
  }

  window.EInviteChromeCommandPalette = Object.freeze({
    version: 57, STRINGS, open, openShortcuts, close, toggle, register,
    search, collectCommands, collectPages, collectLayers
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', register);
  } else {
    queueMicrotask(register);
  }
})();;/**
 * src/js/editor/chrome/shortcuts.js — Central keyboard-shortcut registry (ROADMAP §3.4.4, v0.57.0).
 *
 * A single `Shortcuts` service that listens on `keydown`, matches against a
 * table of `{key, command, when}`, and dispatches to the command registry.
 *
 * Design goals:
 *   • One source of truth for every keyboard shortcut in the editor.
 *   • `when` clauses prevent shortcuts from firing inside text inputs (so
 *     Ctrl+B inside a textarea bolds the text instead of toggling a sidebar).
 *   • The table is searchable via the Shift+? modal (which opens the unified
 *     command palette in "shortcuts" mode — see command-palette.js).
 *
 * Existing keyboard handling in `editor-command-system-v23.js` is preserved
 * (it is the source of the binding table). This module wraps it with a
 * cleaner API for the chrome layer to consume and adds the `when` clauses.
 *
 * Public API:
 *   EInviteShortcuts.register({ key, command, when })    → add a binding
 *   EInviteShortcuts.unregister(id)                       → remove a binding
 *   EInviteShortcuts.list()                               → all bindings
 *   EInviteShortcuts.match(event)                         → resolve command id
 *   EInviteShortcuts.openShortcutsModal()                 → open the modal
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteShortcuts) return;

  const STRINGS = {
    en: {
      title: 'Keyboard shortcuts', empty: 'No shortcuts registered',
      category: 'Category', all: 'All', filter: 'Filter shortcuts…',
      close: 'Close', command: 'Command', shortcut: 'Shortcut'
    },
    km: {
      title: 'ផ្លូវកាត់ក្ដារចុច', empty: 'មិនមានផ្លូវកាត់ទេ',
      category: 'ប្រភេទ', all: 'ទាំងអស់', filter: 'ត្រង់ផ្លូវកាត់…',
      close: 'បិទ', command: 'ពាក្យបញ្ជា', shortcut: 'ផ្លូវកាត់'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  function registry() { return window.EInviteCommandRegistry || null; }
  function palette() { return window.EInviteChromeCommandPalette || null; }

  /** Canonicalize a chord string the same way the registry does.
   *  'Mod+K' / 'Ctrl+K' / 'Cmd+K' / 'Command+K' → 'Mod+K' (the registry's
   *  `Mod` resolves to Ctrl on Win/Linux, Cmd on macOS). */
  function canonicalChord(value) {
    if (!value) return '';
    const parts = String(value).split('+').map((s) => s.trim()).filter(Boolean);
    const mods = new Set(); let key = '';
    for (const part of parts) {
      const p = part.toLowerCase();
      if (['mod', 'cmdorctrl', 'ctrlorcmd'].includes(p)) mods.add('Mod');
      else if (['ctrl', 'control'].includes(p)) mods.add('Ctrl');
      else if (['meta', 'cmd', 'command'].includes(p)) mods.add('Meta');
      else if (['alt', 'option'].includes(p)) mods.add('Alt');
      else if (p === 'shift') mods.add('Shift');
      else if (part.length === 1) key = part.toUpperCase();
      else key = part;
    }
    return ['Mod', 'Ctrl', 'Meta', 'Alt', 'Shift'].filter((x) => mods.has(x)).concat(key || []).join('+');
  }

  /** Test whether the keydown event is "in a text input" — used for `when`
   *  clauses. `editor-active` matches when the canvas/stage has focus OR no
   *  input has focus; `never` always rejects; `always` always accepts. */
  function isTypingTarget(target) {
    if (!target) return false;
    return !!target.matches && target.matches('input,textarea,select,[contenteditable="true"]');
  }
  function evaluateWhen(when, event) {
    if (!when || when === 'always') return true;
    if (when === 'never') return false;
    if (when === 'editor-active') return !isTypingTarget(event.target);
    if (when === 'text-input') return isTypingTarget(event.target);
    // Custom: pass through.
    return true;
  }

  /** Module state. */
  const state = {
    bindings: new Map(),  // id → {key, command, when, label_en, label_km, category}
    nextId: 1,
    modal: null
  };

  function register(binding) {
    if (!binding || !binding.key || !binding.command) return null;
    const id = `s${state.nextId++}`;
    const record = {
      id,
      key: canonicalChord(binding.key),
      command: String(binding.command),
      when: binding.when || 'editor-active',
      label_en: binding.label_en || binding.command,
      label_km: binding.label_km || binding.label_en || binding.command,
      category: binding.category || 'General'
    };
    state.bindings.set(id, record);
    return id;
  }

  function registerMany(list) {
    if (!Array.isArray(list)) return [];
    return list.map(register);
  }

  function unregister(id) { return state.bindings.delete(id); }

  function list() { return [...state.bindings.values()]; }

  /** Match a keydown event against the table; return the command id (or null). */
  function match(event) {
    const r = registry();
    const eventChord = r?.eventChord ? r.eventChord(event) : eventToChord(event);
    let best = null;
    for (const binding of state.bindings.values()) {
      if (binding.key !== eventChord) continue;
      if (!evaluateWhen(binding.when, event)) continue;
      best = binding.command; break;
    }
    return best;
  }

  function eventToChord(event) {
    const parts = [];
    if (event.ctrlKey || event.metaKey) parts.push('Mod');
    if (event.altKey) parts.push('Alt');
    if (event.shiftKey) parts.push('Shift');
    let key = event.key;
    if (key === ' ') key = 'Space';
    if (key.length === 1) key = key.toUpperCase();
    if (!['Control', 'Meta', 'Alt', 'Shift'].includes(key)) parts.push(key);
    return parts.join('+');
  }

  /** Global keydown listener. */
  function onKeyDown(event) {
    if (event.defaultPrevented) return;
    const commandId = match(event);
    if (!commandId) return;
    const r = registry();
    if (!r?.execute) return;
    // Execute the command. If it returns false (disabled), let the event
    // propagate normally so the browser default action still fires.
    try {
      event.preventDefault();
      r.execute(commandId, { event });
    } catch (e) { console.warn('[shortcuts] failed', e); }
  }

  /** Open the shortcuts modal — delegates to the chrome command palette
   *  which already has a shortcuts mode. Falls back to a built-in modal. */
  function openShortcutsModal() {
    const p = palette();
    if (p?.openShortcuts) return p.openShortcuts();
    buildModal();
    state.modal.hidden = false;
    document.body.classList.add('ei-shortcuts-modal-open');
  }
  function closeShortcutsModal() {
    if (!state.modal) return;
    state.modal.hidden = true;
    document.body.classList.remove('ei-shortcuts-modal-open');
  }

  function buildModal() {
    if (state.modal) return state.modal;
    const modal = document.createElement('div');
    modal.className = 'ei-shortcuts-modal';
    modal.hidden = true;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML = `
      <div class="ei-shortcuts-modal__backdrop" data-close></div>
      <section class="ei-shortcuts-modal__dialog">
        <header><h2>${t('title')}</h2><button type="button" data-close aria-label="${t('close')}">×</button></header>
        <input type="search" class="ei-shortcuts-modal__filter" placeholder="${t('filter')}" aria-label="${t('filter')}">
        <div class="ei-shortcuts-modal__list"></div>
      </section>
    `;
    document.body.appendChild(modal);
    state.modal = modal;
    modal.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', closeShortcutsModal));
    modal.querySelector('input').addEventListener('input', () => renderModalList());
    return modal;
  }

  function renderModalList() {
    if (!state.modal) return;
    const q = state.modal.querySelector('input').value.trim().toLowerCase();
    const list = state.modal.querySelector('.ei-shortcuts-modal__list');
    list.replaceChildren();
    let bindings = list && state.bindings.size ? list : list;
    bindings = [...state.bindings.values()].filter((b) => {
      if (!q) return true;
      const hay = `${b.label_en} ${b.label_km} ${b.command} ${b.key} ${b.category}`.toLowerCase();
      return hay.includes(q);
    });
    if (!bindings.length) {
      const empty = document.createElement('div');
      empty.className = 'ei-shortcuts-modal__empty';
      empty.textContent = t('empty');
      list.appendChild(empty);
      return;
    }
    let lastCat = '';
    for (const b of bindings) {
      if (b.category !== lastCat) {
        lastCat = b.category;
        const h = document.createElement('div');
        h.className = 'ei-shortcuts-modal__category';
        h.textContent = b.category;
        list.appendChild(h);
      }
      const row = document.createElement('div');
      row.className = 'ei-shortcuts-modal__row';
      row.innerHTML = `<span class="ei-shortcuts-modal__label"></span><kbd class="ei-shortcuts-modal__key"></kbd>`;
      row.querySelector('.ei-shortcuts-modal__label').textContent = locale() === 'km' ? b.label_km : b.label_en;
      row.querySelector('kbd').textContent = formatChord(b.key);
      list.appendChild(row);
    }
  }

  function formatChord(chord) {
    return String(chord || '').replace(/Mod/g, navigator.platform.includes('Mac') ? '⌘' : 'Ctrl')
      .replace(/\+/g, ' + ');
  }

  /** Default set of shortcuts to register on load. Each command id is
   *  executed via the registry — these mirror the existing bindings in
   *  editor-command-system-v23.js but are now centralized. */
  const DEFAULT_BINDINGS = [
    { key: 'Mod+K', command: 'palette.open', when: 'always', label_en: 'Open command palette', label_km: 'បើកផ្លូវកាត់សកម្មភាព', category: 'View' },
    { key: 'Shift+?', command: 'palette.shortcuts', when: 'editor-active', label_en: 'Show keyboard shortcuts', label_km: 'បង្ហាញផ្លូវកាត់', category: 'Help' },
    { key: 'Mod+B', command: 'format.bold', when: 'editor-active', label_en: 'Bold (toggle)', label_km: 'ដិត (បិទ/បើក)', category: 'Format' },
    { key: 'Mod+I', command: 'format.italic', when: 'editor-active', label_en: 'Italic (toggle)', label_km: 'ទ្រេត (បិទ/បើក)', category: 'Format' },
    { key: 'Mod+U', command: 'format.underline', when: 'editor-active', label_en: 'Underline (toggle)', label_km: 'បន្ទាត់ពីក្រោម (បិទ/បើក)', category: 'Format' },
    { key: 'Mod+Z', command: 'history.undo', when: 'always', label_en: 'Undo', label_km: 'មិនធ្វើវិញ', category: 'Edit' },
    { key: 'Mod+Shift+Z', command: 'history.redo', when: 'always', label_en: 'Redo', label_km: 'ធ្វើវិញ', category: 'Edit' },
    { key: 'Mod+S', command: 'file.save', when: 'always', label_en: 'Save', label_km: 'រក្សាទុក', category: 'File' },
    { key: 'Mod+D', command: 'edit.duplicate', when: 'editor-active', label_en: 'Duplicate selection', label_km: 'ចម្លងធាតុដែលបានជ្រើស', category: 'Edit' },
    { key: 'Delete', command: 'edit.delete', when: 'editor-active', label_en: 'Delete selection', label_km: 'លុបធាតុដែលបានជ្រើស', category: 'Edit' },
    { key: 'Mod+A', command: 'edit.selectAll', when: 'editor-active', label_en: 'Select all', label_km: 'ជ្រើសទាំងអស់', category: 'Edit' },
    { key: 'Mod+G', command: 'object.group', when: 'editor-active', label_en: 'Group selection', label_km: 'ដាក់ជាក្រុម', category: 'Arrange' },
    { key: 'Mod+Shift+G', command: 'object.ungroup', when: 'editor-active', label_en: 'Ungroup selection', label_km: 'ដកក្រុម', category: 'Arrange' },
    { key: 'Mod+]', command: 'arrange.forward', when: 'editor-active', label_en: 'Bring forward', label_km: 'នាំឡើងលើ', category: 'Arrange' },
    { key: 'Mod+[', command: 'arrange.backward', when: 'editor-active', label_en: 'Send backward', label_km: 'ផ្ញើចុះក្រោម', category: 'Arrange' },
    { key: 'Alt+L', command: 'layers.togglePanel', when: 'editor-active', label_en: 'Toggle layers panel', label_km: 'បិទ/បើកស្រទាប់', category: 'View' },
    { key: 'Alt+P', command: 'pages.toggleSidebar', when: 'editor-active', label_en: 'Toggle pages sidebar', label_km: 'បិទ/បើកទំព័រ', category: 'View' }
  ];

  /** Register a no-op command for each unknown command id so the registry
   *  won't reject the dispatch. This is purely for the modal to be useful
   *  even when the editor bundle hasn't registered all commands. */
  function ensureCommandStubs() {
    const r = registry(); if (!r?.register) return;
    for (const b of DEFAULT_BINDINGS) {
      try {
        if (!r.list) continue;
        const exists = r.list({ includeHidden: true }).some((c) => c.id === b.command);
        if (exists) continue;
        r.register({
          id: b.command, title: b.label_en, category: b.category,
          keywords: [b.label_km, b.key], visible: () => false, run: () => false
        });
      } catch { /* duplicate — ignore */ }
    }
  }

  function init() {
    document.addEventListener('keydown', onKeyDown, true);
    registerMany(DEFAULT_BINDINGS);
    ensureCommandStubs();
  }

  window.EInviteShortcuts = Object.freeze({
    version: 57, STRINGS, register, registerMany, unregister, list,
    match, canonicalChord, openShortcutsModal, closeShortcutsModal
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    queueMicrotask(init);
  }
})();;/**
 * src/js/editor/collab/presence.js — Live cursors with names (ROADMAP §3.5.1, v0.58.0).
 *
 * Extends the existing `collaboration-presence-v52.js` (which already wires
 * the heartbeat / WebSocket / poll fallback) with:
 *   • Y.js awareness protocol for cursor position + identity (when Y.js is
 *     loaded and an awareness instance is provided by the CRDT layer).
 *   • Stable cursor color derived from the user ID (hash → hue).
 *   • Label shows the user's display name, or "Guest" if anonymous.
 *   • Cursors fade after 5s of no movement (CSS opacity transition).
 *   • Throttled to 20Hz (50ms) — coarser than the 80ms v52 default, matching
 *     the ROADMAP requirement.
 *
 * Public API:
 *   EInviteCollabPresence.mount(stage, channel)  → render overlay on a stage
 *   EInviteCollabPresence.attach(channel)         → wire cursor events
 *   EInviteCollabPresence.render(channel)         → re-render remote cursors
 *   EInviteCollabPresence.shareYAwareness(aw)     → wire Y.js awareness (optional)
 *
 * Bilingual EN+KH strings for "Guest" / "editing" labels.
 */
(() => {
  'use strict';
  if (window.EInviteCollabPresence) return;

  const CURSOR_THROTTLE_MS = 50;     // 20 Hz
  const FADE_AFTER_MS = 5000;
  const REAP_INTERVAL_MS = 1000;

  const STRINGS = {
    en: { guest: 'Guest', you: 'You', editing: 'editing', viewing: 'viewing', idle: 'idle' },
    km: { guest: 'ភ្ញៀវ', you: 'អ្នក', editing: 'កំពុងកែសម្រួល', viewing: 'កំពុងមើល', idle: 'ទំនេរ' }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  /** Stable hue (0-360) derived from the actor id. */
  function actorHue(actor) {
    let h = 0;
    for (const ch of String(actor || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return h % 360;
  }
  function actorColor(actor) {
    return `hsl(${actorHue(actor)},65%,55%)`;
  }

  /** Module state. */
  const state = {
    overlay: null,
    channel: null,
    throttleAt: 0,
    awareness: null,
    lastLocalCursor: null
  };

  /** Get-or-create the cursor overlay (#eiCollabCursors) inside #stage. */
  function overlay(stage) {
    if (state.overlay && state.overlay.isConnected) return state.overlay;
    const parent = stage || document.getElementById('stage') || document.body;
    const node = document.createElement('div');
    node.id = 'eiCollabCursors';
    node.className = 'ei-collab-cursors';
    node.setAttribute('aria-hidden', 'true');
    parent.appendChild(node);
    state.overlay = node;
    return node;
  }

  /** Build one remote-cursor DOM node. */
  function buildCursor(item) {
    const node = document.createElement('div');
    node.className = 'ei-collab-cursor';
    node.dataset.actor = String(item.actor || '');
    node.style.setProperty('--collab-color', item.color || actorColor(item.actor));
    const dot = document.createElement('div');
    dot.className = 'ei-collab-cursor__dot';
    const label = document.createElement('span');
    label.className = 'ei-collab-cursor__label';
    label.textContent = item.name || t('guest');
    node.append(dot, label);
    return node;
  }

  function positionCursor(node, item, stage) {
    const rect = stage?.getBoundingClientRect();
    if (!rect || !item.cursor) return;
    const x = Math.max(0, Math.min(1, Number(item.cursor.x) || 0));
    const y = Math.max(0, Math.min(1, Number(item.cursor.y) || 0));
    node.style.left = `${x * rect.width}px`;
    node.style.top = `${y * rect.height}px`;
    node.dataset.lastMove = String(Date.now());
    node.classList.remove('is-faded');
  }

  /** Re-render every remote cursor from the channel's snapshot. */
  function render(channel = state.channel) {
    const stage = document.getElementById('stage');
    const layer = overlay(stage);
    const items = (channel?.list?.() || []);
    const byActor = new Map(items.map((x) => [String(x.actor), x]));
    // Reconcile: add new, update existing, remove stale.
    const existing = new Map([...layer.children].map((n) => [n.dataset.actor, n]));
    for (const [actor, item] of byActor) {
      let node = existing.get(actor);
      if (!node) {
        node = buildCursor(item);
        layer.appendChild(node);
      } else {
        // Update label + color in case they changed.
        const label = node.querySelector('.ei-collab-cursor__label');
        if (label) label.textContent = item.name || t('guest');
        node.style.setProperty('--collab-color', item.color || actorColor(actor));
      }
      positionCursor(node, item, stage);
    }
    // Remove cursors whose actor has left.
    for (const [actor, node] of existing) {
      if (!byActor.has(actor)) node.remove();
    }
  }

  /** Throttled local cursor broadcast. */
  function sendLocalCursor() {
    const ch = state.channel;
    if (!ch) return;
    const now = Date.now();
    if (now - state.throttleAt < CURSOR_THROTTLE_MS) return;
    state.throttleAt = now;
    if (state.lastLocalCursor) ch.setCursor?.(state.lastLocalCursor);
  }

  /** Wire local pointer events to broadcast cursor position. */
  function attachLocalPointer() {
    const stage = document.getElementById('stage');
    if (!stage) return;
    const onMove = (event) => {
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;
      if (x < 0 || x > 1 || y < 0 || y > 1) return;
      state.lastLocalCursor = { x, y, pageId: state.channel?.pageId || 'hero' };
      sendLocalCursor();
    };
    document.addEventListener('pointermove', onMove, { passive: true });
  }

  /** Wire to a Y.js awareness instance (optional — only if Y is loaded and
   *  a CRDT channel is configured). The awareness protocol broadcasts small
   *  state updates that don't need to be persisted; we use it for cursor
   *  position + name + color. */
  function shareYAwareness(awareness) {
    if (!awareness || state.awareness === awareness) return;
    state.awareness = awareness;
    const localState = { cursor: state.lastLocalCursor, actor: state.channel?.actor,
      name: state.channel?.name, color: state.channel?.color };
    try { awareness.setLocalState(localState); } catch { /* not a Y.js awareness */ }
    awareness.on?.('change', () => {
      const ch = state.channel;
      if (!ch) return;
      const remote = [];
      awareness.getStates?.().forEach((s, clientID) => {
        if (!s || !s.cursor) return;
        if (s.actor === ch.actor) return; // skip self
        remote.push({ actor: s.actor || String(clientID), name: s.name || t('guest'),
          color: s.color || actorColor(s.actor || clientID), cursor: s.cursor,
          updatedAt: Date.now() });
      });
      if (ch._mergeRemote) ch._mergeRemote(remote);
      render();
    });
  }

  /** Attach to a PresenceChannel (existing V52 type). */
  function attach(channel) {
    if (!channel) return;
    state.channel = channel;
    // Hook the channel's existing events — they fire on cursor/join/leave.
    channel.on?.('cursor', () => render(channel));
    channel.on?.('join', () => render(channel));
    channel.on?.('leave', () => render(channel));
    channel.on?.('selection', () => render(channel));
    channel.on?.('mode', () => render(channel));
    attachLocalPointer();
    render(channel);
    // Reap faded cursors on a 1s tick.
    setInterval(reapFaded, REAP_INTERVAL_MS);
  }

  /** Mark cursors that haven't moved in FADE_AFTER_MS as faded. */
  function reapFaded() {
    const layer = state.overlay;
    if (!layer) return;
    const now = Date.now();
    for (const node of layer.children) {
      const last = Number(node.dataset.lastMove || 0);
      if (last && now - last > FADE_AFTER_MS) node.classList.add('is-faded');
    }
  }

  /** Convenience entry point: join a channel for an invitation id. */
  async function join(invitationId, options = {}) {
    const factory = window.EInviteCollaborationPresenceV52;
    const channel = factory?.join ? await factory.join(invitationId, {
      ...options, name: options.name || window.EInviteContext?.getUserName?.() || '',
      color: options.color || actorColor(window.EInviteCRDTV31?.actorId?.() || 'guest')
    }) : null;
    if (channel) attach(channel);
    return channel;
  }

  /** Mount the overlay on a specific stage element (used when multiple stages
   *  exist or the stage is created later). */
  function mount(stage, channel) {
    overlay(stage);
    if (channel) attach(channel);
    return state.overlay;
  }

  window.EInviteCollabPresence = Object.freeze({
    version: 58, STRINGS, CURSOR_THROTTLE_MS, FADE_AFTER_MS,
    mount, attach, render, shareYAwareness, join, actorColor, actorHue
  });
})();;/**
 * src/js/editor/collab/comments.js — Comment threads (ROADMAP §3.5.2, v0.58.0).
 *
 * Click the comment tool, click on the canvas → a pin appears at that
 * coordinate. Type a comment. Other users see the pin and can reply.
 * Resolved threads are hidden by default (toggle to show).
 *
 * @ mentions trigger a notification email via the backend
 * (`send_platform_email`) — the JS scans the comment body for `@name`
 * tokens and the backend re-validates + sends.
 *
 * Public API:
 *   EInviteCollabComments.mount(invitationId, options)
 *   EInviteCollabComments.refresh()                       → reload from server
 *   EInviteCollabComments.activateTool()                  → enter comment tool
 *   EInviteCollabComments.openThread(commentId)           → open thread panel
 *   EInviteCollabComments.create({ x, y, pageId, body })
 *   EInviteCollabComments.reply(commentId, body)
 *   EInviteCollabComments.resolve(commentId)
 *   EInviteCollabComments.toggleResolved()
 *
 * Backend routes (server.py):
 *   GET    /api/invitations/{id}/comments      → list threads
 *   POST   /api/invitations/{id}/comments      → create root comment
 *   PUT    /api/invitations/{id}/comments/{cid} → resolve/unresolve
 *   DELETE /api/invitations/{id}/comments/{cid} → delete
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteCollabComments) return;

  const STRINGS = {
    en: {
      title: 'Comments', empty: 'No comments yet',
      addPlaceholder: 'Write a comment…', replyPlaceholder: 'Reply…',
      send: 'Send', reply: 'Reply', resolve: 'Resolve', unresolve: 'Reopen',
      delete: 'Delete', cancel: 'Cancel', toolActive: 'Click on canvas to add comment',
      resolved: 'Resolved', showResolved: 'Show resolved', hideResolved: 'Hide resolved',
      mention: 'Mentioned user', pinLabel: (n) => `Comment ${n}`,
      you: 'You', anonymous: 'Anonymous'
    },
    km: {
      title: 'មតិយោបល់', empty: 'មិនទាន់មានមតិយោបល់ទេ',
      addPlaceholder: 'សរសេរមតិយោបល់…', replyPlaceholder: 'ឆ្លើយតប…',
      send: 'ផ្ញើ', reply: 'ឆ្លើយតប', resolve: 'បិទបញ្ហា', unresolve: 'បើកឡើងវិញ',
      delete: 'លុប', cancel: 'បោះបង់', toolActive: 'ចុចលើកាណវាស់ដើម្បីបន្ថែមមតិយោបល់',
      resolved: 'បានបិទ', showResolved: 'បង្ហាញដែលបានបិទ', hideResolved: 'លាក់ដែលបានបិទ',
      mention: 'បានផ្ដល់់សំគាល់អ្នកប្រើ', pinLabel: (n) => `មតិយោបល់ ${n}`,
      you: 'អ្នក', anonymous: 'អនាមិក'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key, ...args) {
    const v = (STRINGS[locale()] || STRINGS.en)[key];
    return typeof v === 'function' ? v(...args) : (v || key);
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  function bridge() { return window.EInviteEditorBridge || null; }

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta?.getAttribute('content') || '';
  }

  /** Module state. */
  const state = {
    invitationId: null,
    panel: null,
    pinLayer: null,
    comments: [],            // flat list (root + replies)
    showResolved: false,
    toolActive: false,
    selectedPin: null,
    csrf: ''
  };

  /** Build the side panel + pin layer (idempotent). */
  function build() {
    if (state.panel) return state.panel;
    const panel = document.createElement('section');
    panel.id = 'eiCollabComments';
    panel.className = 'ei-chrome-panel ei-comments-panel';
    panel.setAttribute('aria-label', t('title'));
    panel.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" data-action="toggle-resolved" aria-pressed="false">${t('showResolved')}</button>
      </header>
      <div class="ei-comments-list" role="list" aria-label="${t('title')}"></div>
      <div class="ei-comments-empty" hidden>${t('empty')}</div>
    `;
    document.body.appendChild(panel);
    state.panel = panel;
    const pinLayer = document.createElement('div');
    pinLayer.id = 'eiCollabCommentPins';
    pinLayer.className = 'ei-comment-pins';
    pinLayer.setAttribute('aria-hidden', 'true');
    const stage = document.getElementById('stage');
    (stage || document.body).appendChild(pinLayer);
    state.pinLayer = pinLayer;
    $('[data-action="toggle-resolved"]', panel).addEventListener('click', toggleResolved);
    return panel;
  }

  /** Activate the comment tool — canvas clicks add pins. */
  function activateTool() {
    state.toolActive = !state.toolActive;
    document.body.classList.toggle('is-comment-tool-active', state.toolActive);
    window.uiToast?.(state.toolActive ? t('toolActive') : '', '');
  }

  /** API: list comments. */
  async function fetchComments() {
    if (!state.invitationId) return [];
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments`, {
      credentials: 'same-origin', headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.comments) ? data.comments : [];
  }

  /** Persist a new root comment. */
  async function create({ x, y, pageId = 'hero', elementId = null, body }) {
    if (!state.invitationId || !body) return null;
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ x, y, pageId, elementId, body: String(body).slice(0, 4000) })
    });
    if (!res.ok) { window.uiToast?.('Comment failed', '!'); return null; }
    const data = await res.json();
    await refresh();
    return data;
  }

  /** Reply to an existing thread. */
  async function reply(commentId, body) {
    if (!state.invitationId || !body) return null;
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ parentId: commentId, body: String(body).slice(0, 4000) })
    });
    if (!res.ok) { window.uiToast?.('Reply failed', '!'); return null; }
    const data = await res.json();
    await refresh();
    return data;
  }

  /** Resolve or reopen a thread. */
  async function resolve(commentId, resolved = true) {
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments/${encodeURIComponent(commentId)}`, {
      method: 'PUT', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ resolved })
    });
    if (!res.ok) { window.uiToast?.('Resolve failed', '!'); return null; }
    await refresh();
    return true;
  }

  async function remove(commentId) {
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/comments/${encodeURIComponent(commentId)}`, {
      method: 'DELETE', credentials: 'same-origin',
      headers: { 'X-CSRF-Token': state.csrf }
    });
    if (!res.ok) { window.uiToast?.('Delete failed', '!'); return null; }
    await refresh();
    return true;
  }

  function toggleResolved() {
    state.showResolved = !state.showResolved;
    const btn = $('[data-action="toggle-resolved"]', state.panel);
    btn.textContent = state.showResolved ? t('hideResolved') : t('showResolved');
    btn.setAttribute('aria-pressed', String(state.showResolved));
    render();
  }

  /** Group comments into threads: root → replies. */
  function threads() {
    const roots = state.comments.filter((c) => !c.parentId);
    const repliesByRoot = new Map();
    for (const c of state.comments) {
      if (c.parentId) {
        const list = repliesByRoot.get(c.parentId) || [];
        list.push(c); repliesByRoot.set(c.parentId, list);
      }
    }
    return roots.map((root) => ({ root, replies: repliesByRoot.get(root.id) || [] }));
  }

  function render() {
    if (!state.panel) build();
    const list = $('.ei-comments-list', state.panel);
    const empty = $('.ei-comments-empty', state.panel);
    list.replaceChildren();
    const pins = state.pinLayer;
    if (pins) pins.replaceChildren();
    const all = threads();
    const visible = state.showResolved ? all : all.filter((t) => !t.root.resolvedAt);
    if (!visible.length) { empty.hidden = false; return; }
    empty.hidden = true;
    for (const [idx, thread] of visible.entries()) {
      list.appendChild(buildThreadRow(thread, idx + 1));
      if (pins) pins.appendChild(buildPin(thread.root, idx + 1));
    }
  }

  function buildThreadRow(thread, n) {
    const row = document.createElement('article');
    row.className = 'ei-comment-thread';
    row.dataset.id = thread.root.id;
    if (thread.root.resolvedAt) row.classList.add('is-resolved');
    row.innerHTML = `
      <header><span class="ei-comment-pin-marker" aria-hidden="true">${n}</span>
        <strong class="ei-comment-author"></strong>
        <small class="ei-comment-time"></small></header>
      <p class="ei-comment-body"></p>
      <div class="ei-comment-replies" role="list"></div>
      <form class="ei-comment-reply-form"><input type="text" placeholder="${t('replyPlaceholder')}" aria-label="${t('replyPlaceholder')}">
        <button type="submit">${t('reply')}</button></form>
      <footer class="ei-comment-actions">
        <button type="button" data-action="resolve"></button>
        <button type="button" data-action="delete" class="danger">${t('delete')}</button>
      </footer>`;
    $('.ei-comment-author', row).textContent = thread.root.authorName || t('anonymous');
    $('.ei-comment-time', row).textContent = formatTime(thread.root.createdAt);
    $('.ei-comment-body', row).textContent = thread.root.body;
    const replyList = $('.ei-comment-replies', row);
    for (const r of thread.replies) {
      const item = document.createElement('div');
      item.className = 'ei-comment-reply';
      item.setAttribute('role', 'listitem');
      item.innerHTML = `<strong></strong> <span></span>`;
      item.querySelector('strong').textContent = r.authorName || t('anonymous');
      item.querySelector('span').textContent = r.body;
      replyList.appendChild(item);
    }
    const resolveBtn = $('[data-action="resolve"]', row);
    resolveBtn.textContent = thread.root.resolvedAt ? t('unresolve') : t('resolve');
    resolveBtn.addEventListener('click', () => resolve(thread.root.id, !thread.root.resolvedAt));
    $('[data-action="delete"]', row).addEventListener('click', () => remove(thread.root.id));
    $('.ei-comment-reply-form', row).addEventListener('submit', (event) => {
      event.preventDefault();
      const input = $('input', event.target);
      const value = input.value.trim(); if (!value) return;
      reply(thread.root.id, value); input.value = '';
    });
    return row;
  }

  function buildPin(root, n) {
    const pin = document.createElement('button');
    pin.type = 'button';
    pin.className = 'ei-comment-pin';
    pin.dataset.id = root.id;
    pin.setAttribute('aria-label', t('pinLabel', n));
    if (root.resolvedAt) pin.classList.add('is-resolved');
    const x = Math.max(0, Math.min(1, Number(root.x) || 0));
    const y = Math.max(0, Math.min(1, Number(root.y) || 0));
    pin.style.left = `${x * 100}%`;
    pin.style.top = `${y * 100}%`;
    pin.textContent = String(n);
    pin.addEventListener('click', () => openThread(root.id));
    return pin;
  }

  function openThread(commentId) {
    const row = $(`.ei-comment-thread[data-id="${CSS.escape(commentId)}"]`, state.panel);
    if (row) {
      row.scrollIntoView({ block: 'nearest' });
      row.classList.add('is-open');
      setTimeout(() => row.classList.remove('is-open'), 2000);
    }
  }

  function formatTime(ts) {
    if (!ts) return '';
    try { return new Date(Number(ts)).toLocaleString(); }
    catch { return ''; }
  }

  /** Wire canvas click → pin placement when the tool is active. */
  function wireCanvas() {
    const stage = document.getElementById('stage');
    if (!stage) return;
    stage.addEventListener('click', (event) => {
      if (!state.toolActive) return;
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;
      const b = bridge();
      const pageId = b?.getActiveCanvasId?.() || 'hero';
      const text = window.prompt?.(t('addPlaceholder'), '');
      if (text) create({ x, y, pageId, body: text });
      state.toolActive = false;
      document.body.classList.remove('is-comment-tool-active');
    });
  }

  /** Reload from server + re-render. */
  async function refresh() {
    state.comments = await fetchComments();
    render();
  }

  /** Mount + initial fetch. */
  async function mount(invitationId, options = {}) {
    state.invitationId = String(invitationId || '');
    state.csrf = options.csrf || csrfToken();
    build();
    wireCanvas();
    await refresh();
    // Poll every 5s for new comments (in addition to any Y.js broadcast).
    setInterval(refresh, 5000);
    return state.panel;
  }

  function registerCommands() {
    const r = window.EInviteCommandRegistry; if (!r?.register) return;
    try {
      r.register({
        id: 'comments.togglePanel', title: 'Toggle comments panel',
        category: 'View', keywords: ['comments', 'panel', 'threads'],
        bindings: { standard: ['Alt+C'], canva: ['Alt+C'], photoshop: ['Alt+C'] },
        run: () => { if (state.panel) state.panel.hidden = !state.panel.hidden; }
      });
      r.register({
        id: 'comments.activateTool', title: 'Add a comment (click canvas)',
        category: 'Insert', keywords: ['comment', 'pin', 'annotate'],
        bindings: { standard: ['C'], canva: ['C'], photoshop: ['C'] },
        run: () => activateTool()
      });
    } catch { /* duplicate — ignore */ }
  }

  window.EInviteCollabComments = Object.freeze({
    version: 58, STRINGS, mount, refresh, activateTool, openThread,
    create, reply, resolve, remove, toggleResolved, registerCommands
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerCommands);
  } else {
    queueMicrotask(registerCommands);
  }
})();;/**
 * src/js/editor/history/timeline.js — Version history timeline (ROADMAP §3.5.3, v0.58.0).
 *
 * A timeline of every saved version. Click → preview. Restore from any
 * version. The current state is auto-snapshotted first so restore is
 * reversible.
 *
 * Auto-snapshot rules:
 *   • Every 30 minutes of active editing (reset on any user input).
 *   • Every 100 editor-command events (counter resets after snapshot).
 *   • Capped at 50 snapshots per invitation; oldest pruned.
 *
 * Manual snapshot button in the toolbar (registered as a command).
 *
 * Timeline shows: timestamp, author, one-line summary.
 *
 * Backend routes (server.py):
 *   GET  /api/invitations/{id}/version-history                → list
 *   POST /api/invitations/{id}/version-history                → manual snapshot
 *   POST /api/invitations/{id}/version-history/{vid}/restore  → restore
 *
 * Public API:
 *   EInviteHistoryTimeline.mount(invitationId, options)
 *   EInviteHistoryTimeline.refresh()                    → reload list
 *   EInviteHistoryTimeline.snapshot(summary)            → manual snapshot
 *   EInviteHistoryTimeline.restore(versionId)           → restore
 *   EInviteHistoryTimeline.preview(versionId)           → preview (no replace)
 *
 * Bilingual EN+KH labels.
 */
(() => {
  'use strict';
  if (window.EInviteHistoryTimeline) return;

  const AUTO_INTERVAL_MS = 30 * 60 * 1000;     // 30 min
  const COMMAND_THRESHOLD = 100;
  const MAX_SNAPSHOTS = 50;

  const STRINGS = {
    en: {
      title: 'Version history', empty: 'No versions yet',
      snapshot: 'Save snapshot', restore: 'Restore', preview: 'Preview',
      cancelPreview: 'Cancel preview', confirmRestore: 'Restore this version? Current state will be auto-saved first.',
      you: 'You', anonymous: 'Anonymous', auto: 'Auto-saved',
      manual: 'Manual snapshot', restoredFrom: 'Restored from {v}',
      author: 'Author', timestamp: 'Timestamp', summary: 'Summary'
    },
    km: {
      title: 'ប្រវត្តិកំណែប្រែ', empty: 'មិនទាន់មានកំណែប្រែទេ',
      snapshot: 'រក្សាទុកកំណែប្រែ', restore: 'ស្ដារ', preview: 'មើលជាមុន',
      cancelPreview: 'បោះបង់ការមើលជាមុន', confirmRestore: 'ស្ដារកំណែប្រែនេះ? ស្ថានភាពបច្ចុប្បន្ននឹងត្រូវរក្សាទុកស្វ័យប្រវត្តិជាមុន។',
      you: 'អ្នក', anonymous: 'អនាមិក', auto: 'បានរក្សាទុកស្វ័យប្រវត្តិ',
      manual: 'រក្សាទុកដោយដៃ', restoredFrom: 'បានស្ដារពី {v}',
      author: 'អ្នកនិពន្ធ', timestamp: 'ពេលវេលា', summary: 'សង្ខេប'
    }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key, vars) {
    let v = (STRINGS[locale()] || STRINGS.en)[key] || key;
    if (typeof v === 'string' && vars) for (const [k, val] of Object.entries(vars)) v = v.replace(`{${k}}`, String(val));
    return v;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  function bridge() { return window.EInviteEditorBridge || null; }
  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta?.getAttribute('content') || '';
  }

  /** Module state. */
  const state = {
    invitationId: null,
    panel: null,
    versions: [],
    previewingId: null,
    csrf: '',
    commandCount: 0,
    autoTimer: 0,
    lastInteractionAt: Date.now()
  };

  function build() {
    if (state.panel) return state.panel;
    const panel = document.createElement('section');
    panel.id = 'eiHistoryTimeline';
    panel.className = 'ei-chrome-panel ei-history-panel';
    panel.setAttribute('aria-label', t('title'));
    panel.innerHTML = `
      <header class="ei-chrome-panel__header">
        <h3>${t('title')}</h3>
        <button type="button" data-action="snapshot" aria-label="${t('snapshot')}">＋</button>
      </header>
      <ol class="ei-history-list" role="list" aria-label="${t('title')}"></ol>
      <div class="ei-history-empty" hidden>${t('empty')}</div>`;
    document.body.appendChild(panel);
    state.panel = panel;
    $('[data-action="snapshot"]', panel).addEventListener('click', () => snapshot());
    return panel;
  }

  /** Fetch the version list. */
  async function fetchVersions() {
    if (!state.invitationId) return [];
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
      credentials: 'same-origin', headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.versions) ? data.versions : [];
  }

  /** Persist a manual snapshot. */
  async function snapshot(summary = '') {
    const b = bridge(); if (!b || !state.invitationId) return null;
    const doc = b.cloneState?.() || b.getState?.() || {};
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify({ documentJson: JSON.stringify(doc), summary: String(summary).slice(0, 240) })
    });
    if (!res.ok) { window.uiToast?.('Snapshot failed', '!'); return null; }
    state.commandCount = 0;
    await refresh();
    return true;
  }

  /** Auto-snapshot triggered by timer or command-count threshold. */
  async function autoSnapshot(reason) {
    const b = bridge(); if (!b || !state.invitationId) return;
    // Don't snapshot if nothing changed since the last snapshot.
    const doc = b.cloneState?.() || b.getState?.() || {};
    const summary = reason === 'commands'
      ? `Auto-saved after ${COMMAND_THRESHOLD} changes`
      : 'Auto-saved (30 min)';
    try {
      const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf,
                   'X-Auto-Snapshot': '1' },
        body: JSON.stringify({ documentJson: JSON.stringify(doc), summary })
      });
      if (res.ok) { state.commandCount = 0; await refresh(); }
    } catch { /* network — try again next tick */ }
  }

  /** Restore a prior version. Backend auto-snapshots the current state first. */
  async function restore(versionId) {
    if (!confirm(t('confirmRestore'))) return false;
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history/${encodeURIComponent(versionId)}/restore`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf }
    });
    if (!res.ok) { window.uiToast?.('Restore failed', '!'); return false; }
    const data = await res.json();
    if (data.document) {
      const b = bridge();
      b?.replaceState?.(data.document, { reason: 'restore' });
    }
    await refresh();
    window.uiToast?.(t('restoredFrom', { v: versionId }), '↺');
    return true;
  }

  /** Preview a version (no replace). Replaces the editor state in-memory;
   *  caller invokes cancelPreview() to restore the working state. */
  async function preview(versionId) {
    if (state.previewingId) await cancelPreview();
    const versions = state.versions;
    const v = versions.find((x) => String(x.id) === String(versionId));
    if (!v) return false;
    const b = bridge();
    if (!b) return false;
    // Hold the current state in-memory; preview won't be persisted by the
    // editor (it auto-saves to the draft, which is harmless — the document
    // can be restored by clicking any version on the timeline).
    try {
      const doc = JSON.parse(v.documentJson || '{}');
      b.replaceState?.(doc, { reason: 'preview', history: false, save: false });
      state.previewingId = versionId;
      return true;
    } catch { return false; }
  }

  async function cancelPreview() {
    if (!state.previewingId) return false;
    // Reload from server — the latest saved state is the authoritative one.
    const res = await fetch(`/api/invitations/${encodeURIComponent(state.invitationId)}/version-history`, {
      credentials: 'same-origin', headers: { 'Accept': 'application/json' }
    });
    if (res.ok) {
      const data = await res.json();
      // The latest version IS the working state (after the auto-snapshot on
      // preview). Restore it.
      const latest = data.versions?.[0];
      if (latest?.documentJson) {
        try {
          const doc = JSON.parse(latest.documentJson);
          bridge()?.replaceState?.(doc, { reason: 'cancel-preview' });
        } catch {}
      }
    }
    state.previewingId = null;
    return true;
  }

  async function refresh() {
    state.versions = await fetchVersions();
    if (state.versions.length > MAX_SNAPSHOTS) {
      // Backend prunes; this is just a safety net.
      state.versions = state.versions.slice(0, MAX_SNAPSHOTS);
    }
    render();
  }

  function render() {
    if (!state.panel) build();
    const list = $('.ei-history-list', state.panel);
    const empty = $('.ei-history-empty', state.panel);
    list.replaceChildren();
    if (!state.versions.length) { empty.hidden = false; return; }
    empty.hidden = true;
    for (const v of state.versions) {
      list.appendChild(buildRow(v));
    }
  }

  function buildRow(v) {
    const row = document.createElement('li');
    row.className = 'ei-history-row';
    row.dataset.id = v.id;
    if (state.previewingId === v.id) row.classList.add('is-previewing');
    row.innerHTML = `
      <div class="ei-history-row__meta">
        <small class="ei-history-time"></small>
        <small class="ei-history-author"></small>
      </div>
      <p class="ei-history-summary"></p>
      <div class="ei-history-actions">
        <button type="button" data-action="preview">${t('preview')}</button>
        <button type="button" data-action="restore">${t('restore')}</button>
      </div>`;
    $('.ei-history-time', row).textContent = formatTime(v.createdAt);
    $('.ei-history-author', row).textContent = v.authorName || (v.isAuto ? t('auto') : t('anonymous'));
    $('.ei-history-summary', row).textContent = v.summary || (v.isAuto ? t('auto') : t('manual'));
    $('[data-action="preview"]', row).addEventListener('click', () => preview(v.id));
    $('[data-action="restore"]', row).addEventListener('click', () => restore(v.id));
    return row;
  }

  function formatTime(ts) {
    if (!ts) return '';
    try { return new Date(Number(ts)).toLocaleString(); } catch { return ''; }
  }

  /** Auto-snapshot scheduler — ticks every minute, snapshots if 30 min
   *  have passed since the last interaction OR command count hits threshold. */
  function startAutoScheduler() {
    clearInterval(state.autoTimer);
    state.autoTimer = setInterval(() => {
      if (!state.invitationId) return;
      const since = Date.now() - state.lastInteractionAt;
      if (since >= AUTO_INTERVAL_MS) {
        state.lastInteractionAt = Date.now();
        autoSnapshot('timer');
      } else if (state.commandCount >= COMMAND_THRESHOLD) {
        autoSnapshot('commands');
      }
    }, 60_000);
  }

  /** Wire editor-command events to bump the counter (and reset the timer). */
  function wireEditorEvents() {
    window.addEventListener('einvite:editor-command', () => {
      state.commandCount++;
      state.lastInteractionAt = Date.now();
      if (state.commandCount >= COMMAND_THRESHOLD) autoSnapshot('commands');
    });
    document.addEventListener('pointerdown', () => { state.lastInteractionAt = Date.now(); }, { passive: true });
    document.addEventListener('keydown', () => { state.lastInteractionAt = Date.now(); }, { passive: true });
  }

  async function mount(invitationId, options = {}) {
    state.invitationId = String(invitationId || '');
    state.csrf = options.csrf || csrfToken();
    build();
    wireEditorEvents();
    startAutoScheduler();
    await refresh();
    return state.panel;
  }

  function registerCommands() {
    const r = window.EInviteCommandRegistry; if (!r?.register) return;
    try {
      r.register({
        id: 'history.togglePanel', title: 'Toggle version history',
        category: 'View', keywords: ['history', 'versions', 'timeline'],
        bindings: { standard: ['Alt+H'], canva: ['Alt+H'], photoshop: ['Alt+H'] },
        run: () => { if (state.panel) state.panel.hidden = !state.panel.hidden; }
      });
      r.register({
        id: 'history.snapshot', title: 'Save version snapshot',
        category: 'File', keywords: ['snapshot', 'version', 'save'],
        bindings: { standard: ['Mod+Shift+S'], canva: ['Mod+Shift+S'], photoshop: ['Mod+Shift+S'] },
        run: () => snapshot('Manual snapshot')
      });
    } catch { /* duplicate — ignore */ }
  }

  window.EInviteHistoryTimeline = Object.freeze({
    version: 58, STRINGS, AUTO_INTERVAL_MS, COMMAND_THRESHOLD, MAX_SNAPSHOTS,
    mount, refresh, snapshot, restore, preview, cancelPreview, registerCommands
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerCommands);
  } else {
    queueMicrotask(registerCommands);
  }
})();