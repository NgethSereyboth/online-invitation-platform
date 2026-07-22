(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const html=document.documentElement, body=document.body;
body.classList.add('ui-boot');requestAnimationFrame(()=>requestAnimationFrame(()=>{body.classList.remove('ui-boot');body.classList.add('ui-ready')}));

// Theme: light / system / dark
const media=window.matchMedia?.('(prefers-color-scheme: dark)');
function currentMode(){return localStorage.getItem('einvite-theme-mode')||'system'}
function applyTheme(mode,announce=false){
  const resolved=mode==='dark'||(mode==='system'&&media?.matches)?'dark':'light';
  if(announce){html.classList.add('theme-transition');setTimeout(()=>html.classList.remove('theme-transition'),340)}
  html.dataset.theme=resolved;html.dataset.themeMode=mode;html.style.colorScheme=resolved;
  localStorage.setItem('einvite-theme-mode',mode);
  $$('.ui-theme-menu button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  const icon=$('.ui-theme-icon');if(icon)icon.textContent=mode==='system'?'◐':resolved==='dark'?'☾':'☀';
  if(announce)toast(`${mode[0].toUpperCase()+mode.slice(1)} appearance`,'◐');
}
media?.addEventListener?.('change',()=>{if(currentMode()==='system')applyTheme('system')});
applyTheme(currentMode());

function installThemeControl(){
  const header=$('body:not(:has(.guest))>header');if(header&&$('.ui-theme',header))return;
  const wrap=document.createElement('div');wrap.className='ui-theme'+(header?'':' floating');
  wrap.innerHTML=`<button type="button" class="ui-theme-button" aria-label="Appearance" aria-haspopup="menu" aria-expanded="false" data-ui-tooltip="Appearance (Alt+T)"><span class="ui-theme-icon">◐</span></button><div class="ui-theme-menu" role="menu" hidden>
  <button type="button" data-mode="light"><span>☀</span><div><b>Light</b><small>Bright interface</small></div><span class="check">✓</span></button>
  <button type="button" data-mode="system"><span>◐</span><div><b>System</b><small>Follow your device</small></div><span class="check">✓</span></button>
  <button type="button" data-mode="dark"><span>☾</span><div><b>Dark</b><small>Dim creative workspace</small></div><span class="check">✓</span></button></div>`;
  if(header){const logout=$('#logoutBtn',header); if(logout)header.insertBefore(wrap,logout); else header.append(wrap)}else document.body.append(wrap);
  const trigger=$('.ui-theme-button',wrap),menu=$('.ui-theme-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  $$('[data-mode]',menu).forEach(b=>b.onclick=()=>{applyTheme(b.dataset.mode,true);menu.hidden=true;trigger.setAttribute('aria-expanded','false')});
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  applyTheme(currentMode());
}
installThemeControl();

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

// Current navigation state
const page=location.pathname.split('/').pop()||'dashboard.html';$$('body:not(:has(.guest))>header a').forEach(a=>{const href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];if(href===page)a.classList.add('ui-current')});

// Ripple feedback
addEventListener('pointerdown',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;const r=b.getBoundingClientRect(),s=document.createElement('span');s.className='ui-ripple';const size=Math.max(r.width,r.height);s.style.width=s.style.height=size+'px';s.style.left=(e.clientX-r.left)+'px';s.style.top=(e.clientY-r.top)+'px';b.append(s);setTimeout(()=>s.remove(),560)},true);

// Card spotlight tracking
const spotlightSelectors='.invite-card,.metric,.response-card,.wish-card,.usage-card,.plan,.studio-card,.material-card-page,.template-choice,.page-nav-card,.studio-quick-grid button,.page-builder-library button,.element-library button,.block-library button';
$$(spotlightSelectors).forEach(el=>{el.classList.add('ui-spotlight');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)})});

// Toast API
const stack=document.createElement('div');stack.className='ui-toast-stack';document.body.append(stack);
function toast(message,icon='✓'){const el=document.createElement('div');el.className='ui-toast';el.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),240)},2200)}
window.einviteToast=toast;

// Tooltip engine for compact controls
const tip=document.createElement('div');tip.className='ui-tooltip';document.body.append(tip);let tipTimer;
document.addEventListener('pointerover',e=>{const el=e.target.closest('[data-ui-tooltip],button[title]');if(!el)return;const txt=el.dataset.uiTooltip||el.getAttribute('title');if(!txt)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{const r=el.getBoundingClientRect();tip.textContent=txt;tip.style.left=Math.max(8,Math.min(innerWidth-200,r.left+r.width/2))+'px';tip.style.top=Math.max(8,r.bottom+8)+'px';tip.classList.add('show')},350)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-ui-tooltip],button[title]')){clearTimeout(tipTimer);tip.classList.remove('show')}});

// Editor-specific panel controls, resizers, and modern navigation convenience
if(body.classList.contains('studio-experience')){
  const main=$('body.studio-experience>main'),toolbar=$('.studio-canvas-toolbar');
  const canvasViewport=$('.canvas-viewport');
  canvasViewport?.addEventListener('pointermove',e=>{const r=canvasViewport.getBoundingClientRect();canvasViewport.style.setProperty('--canvas-pointer-x',`${e.clientX-r.left}px`);canvasViewport.style.setProperty('--canvas-pointer-y',`${e.clientY-r.top}px`)});
  let leftWidth=Number(localStorage.getItem('einvite-left-width'))||370,rightWidth=Number(localStorage.getItem('einvite-right-width'))||330;
  function setWidths(){html.style.setProperty('--studio-left-width',`${leftWidth}px`);html.style.setProperty('--studio-right-width',`${rightWidth}px`)}setWidths();
  function addToggle(side,label,symbol){if(!toolbar)return;const b=document.createElement('button');b.type='button';b.className='studio-panel-toggle';b.innerHTML=symbol;b.setAttribute('aria-label',label);b.dataset.uiTooltip=label;b.onclick=()=>{const cls=`studio-${side}-collapsed`;body.classList.toggle(cls);b.setAttribute('aria-pressed',String(body.classList.contains(cls)));localStorage.setItem(`einvite-${side}-collapsed`,body.classList.contains(cls)?'1':'0')};toolbar.prepend(b);if(localStorage.getItem(`einvite-${side}-collapsed`)==='1'){body.classList.add(`studio-${side}-collapsed`);b.setAttribute('aria-pressed','true')}return b}
  addToggle('right','Toggle inspector','▥');addToggle('left','Toggle creation panel','▤');
  function resizer(side){if(!main)return;const h=document.createElement('div');h.className=`studio-panel-resizer ${side}`;main.append(h);h.addEventListener('pointerdown',e=>{h.setPointerCapture(e.pointerId);h.classList.add('dragging');body.style.userSelect='none';const start=e.clientX,startL=leftWidth,startR=rightWidth;const move=ev=>{if(side==='left'){leftWidth=Math.max(290,Math.min(560,startL+(ev.clientX-start)))}else{rightWidth=Math.max(280,Math.min(520,startR-(ev.clientX-start)))}setWidths()};const up=()=>{h.classList.remove('dragging');body.style.userSelect='';localStorage.setItem('einvite-left-width',leftWidth);localStorage.setItem('einvite-right-width',rightWidth);h.removeEventListener('pointermove',move);h.removeEventListener('pointerup',up)};h.addEventListener('pointermove',move);h.addEventListener('pointerup',up)})}
  resizer('left');resizer('right');

  // Rich right-click context menu for the creative canvas.
  const context=document.createElement('div');context.className='ui-context-menu';context.hidden=true;
  context.innerHTML=`<button data-cmd="duplicate"><span>⧉</span><b>Duplicate</b><kbd>Ctrl+D</kbd></button><button data-cmd="copy"><span>□</span><b>Copy</b><kbd>Ctrl+C</kbd></button><button data-cmd="paste"><span>▣</span><b>Paste</b><kbd>Ctrl+V</kbd></button><div class="ui-context-sep"></div><button data-cmd="forward"><span>↑</span><b>Bring forward</b><kbd></kbd></button><button data-cmd="backward"><span>↓</span><b>Send backward</b><kbd></kbd></button><button data-cmd="lock"><span>◇</span><b>Lock / unlock</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="addText"><span>T</span><b>Add text</b><kbd></kbd></button><button data-cmd="fit"><span>⌗</span><b>Fit canvas</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="delete" class="danger"><span>×</span><b>Delete</b><kbd>Del</kbd></button>`;
  document.body.append(context);
  const cmdMap={duplicate:'duplicate',copy:'copyObjects',paste:'pasteObjects',forward:'bringForward',backward:'sendBackward',addText:'addText',fit:'fitCanvas',delete:'deleteBtn'};
  context.addEventListener('click',e=>{const b=e.target.closest('[data-cmd]');if(!b)return;const cmd=b.dataset.cmd;if(cmd==='lock'){const lock=$('#objectLocked');if(lock){lock.checked=!lock.checked;lock.dispatchEvent(new Event('change',{bubbles:true}))}}else document.getElementById(cmdMap[cmd])?.click();context.hidden=true});
  $('#stage')?.addEventListener('contextmenu',e=>{e.preventDefault();const obj=e.target.closest('.object');if(obj&&!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected'))obj.click();context.hidden=false;const w=220,h=390;context.style.left=Math.min(e.clientX,innerWidth-w-8)+'px';context.style.top=Math.min(e.clientY,innerHeight-h-8)+'px'});
  document.addEventListener('pointerdown',e=>{if(!context.contains(e.target))context.hidden=true});

  // Shortcut reference sheet.
  const sheet=document.createElement('div');sheet.className='ui-shortcuts';sheet.hidden=true;sheet.innerHTML=`<div class="ui-shortcuts-card"><header><h2>Keyboard shortcuts</h2><button type="button" data-close-shortcuts>×</button></header><div class="ui-shortcut-grid">
  <div class="ui-shortcut-row"><span>Quick actions</span><kbd>Ctrl / Cmd + K</kbd></div><div class="ui-shortcut-row"><span>Undo</span><kbd>Ctrl / Cmd + Z</kbd></div><div class="ui-shortcut-row"><span>Redo</span><kbd>Ctrl / Cmd + Shift + Z</kbd></div><div class="ui-shortcut-row"><span>Copy / Paste</span><kbd>Ctrl / Cmd + C / V</kbd></div><div class="ui-shortcut-row"><span>Duplicate</span><kbd>Ctrl / Cmd + D</kbd></div><div class="ui-shortcut-row"><span>Delete</span><kbd>Delete</kbd></div><div class="ui-shortcut-row"><span>Move selection</span><kbd>Arrow keys</kbd></div><div class="ui-shortcut-row"><span>Move faster</span><kbd>Shift + Arrows</kbd></div><div class="ui-shortcut-row"><span>Creation tabs</span><kbd>Alt + 1…5</kbd></div><div class="ui-shortcut-row"><span>Toggle inspector</span><kbd>Alt + I</kbd></div><div class="ui-shortcut-row"><span>Toggle creation panel</span><kbd>Alt + [</kbd></div><div class="ui-shortcut-row"><span>Appearance</span><kbd>Alt + T</kbd></div><div class="ui-shortcut-row"><span>Focus mode</span><kbd>F</kbd></div><div class="ui-shortcut-row"><span>Show shortcuts</span><kbd>?</kbd></div></div></div>`;document.body.append(sheet);
  sheet.onclick=e=>{if(e.target===sheet||e.target.closest('[data-close-shortcuts]'))sheet.hidden=true};
  const status=$('.studio-statusbar>div:last-child');if(status){const help=document.createElement('button');help.type='button';help.className='ui-shortcut-help';help.textContent='?';help.dataset.uiTooltip='Keyboard shortcuts';help.onclick=()=>sheet.hidden=false;status.prepend(help)}
  document.addEventListener('keydown',e=>{if(e.key==='?'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){e.preventDefault();sheet.hidden=!sheet.hidden}if(e.key==='Escape'){context.hidden=true;sheet.hidden=true}});

  // Alt+1..5 switches creation tabs, Alt+I toggles inspector, Alt+[ and Alt+] collapse panels.
  document.addEventListener('keydown',e=>{
    if(e.altKey&&/^[1-5]$/.test(e.key)){e.preventDefault();$$('[data-studio-tab]')[Number(e.key)-1]?.click()}
    if(e.altKey&&e.key.toLowerCase()==='i'){e.preventDefault();$('.studio-panel-toggle[aria-label="Toggle inspector"]')?.click()}
    if(e.altKey&&e.key==='['){e.preventDefault();$('.studio-panel-toggle[aria-label="Toggle creation panel"]')?.click()}
  });
}

// Theme shortcut
addEventListener('keydown',e=>{if(e.altKey&&e.key.toLowerCase()==='t'){e.preventDefault();const modes=['light','system','dark'],i=modes.indexOf(currentMode());applyTheme(modes[(i+1)%3],true)}});

// Workspace navigation shortcuts
addEventListener('keydown',e=>{if(!e.altKey)return;const map={h:'dashboard.html',m:'materials.html',p:'templates.html'};const target=map[e.key.toLowerCase()];if(target){e.preventDefault();location.href=target}});

// Gentle internal page transitions
addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname===location.pathname&&u.hash)return;if(a.closest('dialog'))return;e.preventDefault();body.classList.add('ui-page-leaving');setTimeout(()=>location.href=u.href,115)});
})();
