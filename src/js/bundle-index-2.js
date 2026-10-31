;/* LT-4.3: the editor's native colour inputs get a small popover with recents, an
   eyedropper where the browser has one, and a contrast hint for text colours.
   The native input stays the source of truth: every choice is written back to it
   and both `input` and `change` are dispatched, so the existing editor handlers
   keep doing the applying. No new colour logic in app.js, no HTML change. */
(() => {
  'use strict';
  const body = document.body;
  if (!body || (!document.querySelector('#stage') && !document.querySelector('#main'))) return;
  if (window.EInviteColorExtras) return;
  const RECENTS_KEY = 'einvite-color-recents-v1';
  const MAX_RECENTS = 8;
  const HEX = /^#[0-9a-f]{6}$/i;

  function recents() {
    try {
      const list = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
      return Array.isArray(list) ? list.filter((x) => HEX.test(String(x))).slice(0, MAX_RECENTS) : [];
    } catch { return []; }
  }
  function remember(hex) {
    const value = String(hex || '').toLowerCase();
    if (!HEX.test(value)) return recents();
    const next = [value, ...recents().filter((x) => x !== value)].slice(0, MAX_RECENTS);
    try { localStorage.setItem(RECENTS_KEY, JSON.stringify(next)); } catch {}
    return next;
  }

  // --- contrast -------------------------------------------------------------
  function toRgb(color) {
    const value = String(color || '').trim();
    const hex = value.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hex) {
      const raw = hex[1].length === 3 ? hex[1].replace(/(.)/g, '$1$1') : hex[1];
      const n = parseInt(raw, 16);
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    const rgb = value.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
    return rgb ? [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])] : null;
  }
  function luminance(color) {
    const rgb = toRgb(color);
    if (!rgb) return null;
    const [r, g, b] = rgb.map((channel) => {
      const c = channel / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  function contrastRatio(foreground, background) {
    const a = luminance(foreground), b = luminance(background);
    if (a === null || b === null) return null;
    const light = Math.max(a, b), dark = Math.min(a, b);
    return (light + 0.05) / (dark + 0.05);
  }
  // The page surface the text is read on: the document palette, then the stage,
  // then white. Shapes/text both sit on that surface in this editor.
  function pageBackground() {
    const palette = window.state?.palette;
    const stage = document.querySelector('#stage');
    const stageColor = stage ? getComputedStyle(stage).backgroundColor : '';
    for (const candidate of [palette?.background, stageColor, '#ffffff']) {
      if (toRgb(candidate)) return candidate;
    }
    return '#ffffff';
  }
  function contrastHint(hex) {
    const ratio = contrastRatio(hex, pageBackground());
    if (ratio === null) return '';
    const rounded = `${ratio.toFixed(1)}:1`;
    if (ratio >= 4.5) return `AA text — ${rounded}`;
    if (ratio >= 3) return `Large text only — ${rounded}`;
    return `Below AA — ${rounded}`;
  }

  // --- popover --------------------------------------------------------------
  let host = null;
  let dialog = null;
  let restoreFocus = null;

  function apply(hex) {
    if (!host || !HEX.test(hex)) return;
    const value = hex.toLowerCase();
    host.value = value;
    if (dialog) {
      dialog.querySelector('[data-cp-value]').value = value;
      dialog.querySelector('[data-cp-native]').value = value;
      renderDetails(value);
    }
    host.dispatchEvent(new Event('input', { bubbles: true }));
    host.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function renderDetails(hex) {
    if (!dialog) return;
    const hint = dialog.querySelector('[data-cp-contrast]');
    // Only text colours get a contrast verdict; a shape border on a page has no
    // readable text to judge, and a wrong hint is worse than none.
    const role = host?.dataset.ctx || host?.id || '';
    const isText = /(^|-)color$|^color$|text|accent|heading/i.test(role) && !/fill|border|shadow|background/i.test(role);
    hint.hidden = !isText;
    hint.textContent = isText ? contrastHint(hex) : '';
    hint.dataset.level = isText ? (contrastHint(hex).startsWith('AA') ? 'pass' : contrastHint(hex).startsWith('Large') ? 'large' : 'fail') : '';
    const list = dialog.querySelector('[data-cp-recents]');
    const recent = recents();
    list.replaceChildren();
    recent.forEach((value) => {
      const swatch = document.createElement('button');
      swatch.type = 'button';
      swatch.className = 'cp-recent';
      swatch.dataset.color = value;
      swatch.style.setProperty('--cp-swatch', value);
      swatch.setAttribute('aria-label', `Use recent colour ${value}`);
      swatch.addEventListener('click', () => { apply(value); remember(value); renderDetails(value); });
      list.append(swatch);
    });
    const empty = dialog.querySelector('[data-cp-empty]');
    empty.hidden = recent.length > 0;
  }

  function close({ focus = false } = {}) {
    if (!dialog) return;
    const closing = dialog;
    dialog = null;
    closing.remove();
    if (focus && restoreFocus && typeof restoreFocus.focus === 'function') restoreFocus.focus();
    restoreFocus = null;
    host = null;
  }

  // Editor JS builds no HTML strings (repo rule): the popover is nodes only.
  function el(tag, attrs = {}, text = '') {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([name, value]) => {
      if (name === 'class') node.className = value; else node.setAttribute(name, value);
    });
    if (text) node.textContent = text;
    return node;
  }

  function build() {
    const node = el('div', { class: 'cp-extras', role: 'dialog', 'aria-label': 'Colour picker extras' });
    const head = el('div', { class: 'cp-extras-head' });
    head.append(
      el('span', { class: 'cp-extras-title' }, 'Colour'),
      el('button', { type: 'button', class: 'cp-extras-close', 'data-cp-close': '', 'aria-label': 'Close colour picker' }, '×'),
    );
    const row = el('div', { class: 'cp-extras-row' });
    row.append(
      el('input', { 'data-cp-native': '', type: 'color', 'aria-label': 'Pick a colour' }),
      el('input', { 'data-cp-value': '', type: 'text', inputmode: 'text', spellcheck: 'false', maxlength: '7', 'aria-label': 'Hex colour value', placeholder: '#9d4555' }),
    );
    const actions = el('div', { class: 'cp-extras-actions' });
    actions.append(el('button', { type: 'button', class: 'cp-extras-pick', 'data-cp-eyedropper': '', hidden: '' }, 'Eyedropper'));
    node.append(
      head,
      row,
      el('p', { class: 'cp-extras-label' }, 'Recent colours'),
      el('div', { class: 'cp-extras-recents', 'data-cp-recents': '', role: 'group', 'aria-label': 'Recent colours' }),
      el('p', { class: 'cp-extras-empty', 'data-cp-empty': '', hidden: '' }, 'No recent colours yet.'),
      el('p', { class: 'cp-extras-contrast', 'data-cp-contrast': '', hidden: '' }),
      actions,
    );
    body.append(node);
    return node;
  }

  function open(input) {
    if (!input || input.type !== 'color') return false;
    if (dialog && host === input) { close({ focus: true }); return false; }
    close();
    host = input;
    restoreFocus = input;
    dialog = build();
    dialog.querySelector('[data-cp-native]').value = input.value;
    dialog.querySelector('[data-cp-value]').value = input.value;
    dialog.querySelector('[data-cp-native]').addEventListener('input', (event) => { apply(event.target.value); remember(event.target.value); });
    dialog.querySelector('[data-cp-value]').addEventListener('change', (event) => {
      const value = event.target.value.trim();
      if (!HEX.test(value)) { event.target.value = host?.value || ''; return; }
      apply(value); remember(value); renderDetails(value);
    });
    dialog.querySelector('[data-cp-close]').addEventListener('click', () => close({ focus: true }));
    const picker = dialog.querySelector('[data-cp-eyedropper]');
    if ('EyeDropper' in window) {
      picker.hidden = false;
      picker.addEventListener('click', async () => {
        try {
          const result = await new window.EyeDropper().open();
          if (result?.sRGBHex) { apply(result.sRGBHex); remember(result.sRGBHex); renderDetails(result.sRGBHex); }
        } catch { /* the user cancelled the eyedropper; nothing to apply */ }
      });
    }
    renderDetails(input.value);
    position(input);
    dialog.querySelector('[data-cp-value]').focus({ preventScroll: true });
    return true;
  }

  function position(input) {
    if (!dialog) return;
    const anchor = input.getBoundingClientRect();
    const box = dialog.getBoundingClientRect();
    const gap = 8;
    let left = Math.min(anchor.left, window.innerWidth - box.width - 12);
    left = Math.max(12, left);
    let top = anchor.bottom + gap;
    if (top + box.height > window.innerHeight - 12) top = Math.max(12, anchor.top - box.height - gap);
    dialog.style.left = `${Math.round(left)}px`;
    dialog.style.top = `${Math.round(top)}px`;
  }

  // Delegated: every colour input in the editor, including ones the panels and
  // the studio build later. `preventDefault` keeps the OS dialog closed while
  // the popover owns the interaction; the native input inside is one click away.
  document.addEventListener('click', (event) => {
    const input = event.target.closest?.('input[type="color"]');
    if (!input || !input.closest('#main, #stage, body[data-page="index"]')) return;
    if (input.closest('.cp-extras')) return;
    event.preventDefault();
    open(input);
  }, true);
  // Window capture: the editor's own Escape handlers sit on document and some stop
  // immediate propagation there, so the popover listens one level earlier.
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && dialog) { event.preventDefault(); close({ focus: true }); }
  }, true);
  document.addEventListener('pointerdown', (event) => {
    if (!dialog || event.target.closest('.cp-extras') || event.target.closest('input[type="color"]')) return;
    close();
  }, true);
  window.addEventListener('resize', () => close(), { passive: true });

  window.EInviteColorExtras = Object.freeze({
    version: 1,
    open,
    close,
    recents,
    remember,
    contrast: { ratio: contrastRatio, hint: contrastHint, background: pageBackground },
  });
})();;(function(){
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
  // The menu used to live inside the sticky header. That bar is overflow:hidden and a
  // stacking context, so the popover was clipped to a sliver at 1440 and covered by the
  // mobile language row at 390 (elementFromPoint hit the dashboard, not the buttons).
  // Anchor it to <body> with fixed coordinates so it paints above page content everywhere.
  document.body.append(menu);
  function closeThemeMenu(){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}
  function openThemeMenu(){
    menu.hidden=false;
    const r=trigger.getBoundingClientRect(),w=menu.offsetWidth||188,h=menu.offsetHeight||104;
    menu.style.position='fixed';menu.style.right='auto';menu.style.zIndex='13000';
    menu.style.left=Math.max(8,Math.min(innerWidth-w-8,r.right-w))+'px';
    menu.style.top=Math.max(8,Math.min(innerHeight-h-8,r.bottom+8))+'px';
    trigger.setAttribute('aria-expanded','true');
  }
  trigger.onclick=e=>{e.stopPropagation();if(menu.hidden)openThemeMenu();else closeThemeMenu()};
  $$('[data-mode]',menu).forEach(b=>b.onclick=()=>{applyTheme(b.dataset.mode,true);closeThemeMenu();trigger.focus()});
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)&&!menu.contains(e.target))closeThemeMenu()});
  document.addEventListener('keydown',e=>{if(e.key!=='Escape'||menu.hidden)return;closeThemeMenu();trigger.focus()});
  applyTheme(currentMode());
}
installThemeControl();
window.EInviteThemeController=Object.freeze({currentMode,applyTheme,cycle(){const modes=['light','dark'],i=modes.indexOf(currentMode());const next=modes[(i+1)%2];applyTheme(next,true);return next}});
function installAppLauncher(){
  const header=$('body:not(:has(.guest))>header');if(!header||$('.ui-app-launcher',header))return;
  const brand=header.querySelector('strong');if(!brand)return;
  const wrap=document.createElement('div');wrap.className='ui-app-launcher';
  wrap.innerHTML=`<button type="button" class="ui-app-launcher-button" aria-label="Open workspace navigation" aria-expanded="false" data-ui-tooltip="Workspace navigation"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></button><div class="ui-app-launcher-menu" hidden><div class="ui-app-menu-head"><strong>Workspace</strong></div><div class="ui-app-grid">
  <a href="dashboard.html"><span>⌂</span><div><b>Dashboard</b><small>Your invitations</small></div></a>
  <a href="templates.html"><span>✦</span><div><b>Templates</b><small>Reusable designs</small></div></a>
  <a href="materials.html"><span>▣</span><div><b>Materials</b><small>Photos, audio & video</small></div></a>
  <a href="designer.html"><span>◇</span><div><b>Designer</b><small>Professional workspace</small></div></a>
  <a href="billing.html"><span>◎</span><div><b>Plans</b><small>Usage & limits</small></div></a>
  <a href="account.html"><span>◉</span><div><b>Account</b><small>Profile & security</small></div></a></div></div>`;
  // The brand <strong> sits inside the header's dashboard link, so inserting the launcher
  // there made every click on it navigate (a full reload) before the menu could open.
  // Place it beside the anchor and cancel the default action as a belt-and-braces guard.
  const brandAnchor=brand.closest('a');
  (brandAnchor||brand).after(wrap);
  const trigger=$('.ui-app-launcher-button',wrap),menu=$('.ui-app-launcher-menu',wrap);
  trigger.onclick=e=>{e.preventDefault();e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  document.addEventListener('keydown',e=>{if(e.key!=='Escape'||menu.hidden)return;menu.hidden=true;trigger.setAttribute('aria-expanded','false');trigger.focus()});
}
installAppLauncher();
const page=location.pathname.split('/').pop()||'dashboard.html';$$('body:not(:has(.guest))>header a').forEach(a=>{const href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];if(href===page)a.classList.add('ui-current')});
addEventListener('pointerdown',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;const r=b.getBoundingClientRect(),s=document.createElement('span');s.className='ui-ripple';const size=Math.max(r.width,r.height);s.style.width=s.style.height=size+'px';s.style.left=(e.clientX-r.left)+'px';s.style.top=(e.clientY-r.top)+'px';b.append(s);setTimeout(()=>s.remove(),560)},true);
const spotlightSelectors='.invite-card,.metric,.response-card,.wish-card,.usage-card,.plan,.studio-card,.material-card-page,.template-choice,.page-nav-card,.studio-quick-grid button,.page-builder-library button,.element-library button,.block-library button';
$$(spotlightSelectors).forEach(el=>{el.classList.add('ui-spotlight');el.addEventListener('pointermove',e=>{if(window.EInviteProfessionalEditor?.activeInteraction)return;const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)})});
const stack=document.createElement('div');stack.className='ui-toast-stack';document.body.append(stack);
function toast(message,icon='✓'){const el=document.createElement('div');el.className='ui-toast';el.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),240)},2200)}
window.einviteToast=toast;
const tip=document.createElement('div');tip.className='ui-tooltip';document.body.append(tip);let tipTimer;
document.addEventListener('pointerover',e=>{const el=e.target.closest('[data-ui-tooltip],button[title]');if(!el)return;const txt=el.dataset.uiTooltip||el.getAttribute('title');if(!txt)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{const r=el.getBoundingClientRect();tip.textContent=txt;tip.style.left=Math.max(8,Math.min(innerWidth-200,r.left+r.width/2))+'px';tip.style.top=Math.max(8,r.bottom+8)+'px';tip.classList.add('show')},350)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-ui-tooltip],button[title]')){clearTimeout(tipTimer);tip.classList.remove('show')}});
if(body.classList.contains('studio-experience')){
  const main=$('body.studio-experience>main'),toolbar=$('.studio-canvas-toolbar');
  const canvasViewport=$('.canvas-viewport');
  let canvasPointerRect=null;
  canvasViewport?.addEventListener('pointermove',e=>{const r=canvasPointerRect||(canvasPointerRect=canvasViewport.getBoundingClientRect());canvasViewport.style.setProperty('--canvas-pointer-x',`${e.clientX-r.left}px`);canvasViewport.style.setProperty('--canvas-pointer-y',`${e.clientY-r.top}px`)});
  if(canvasViewport){addEventListener('scroll',()=>{canvasPointerRect=null},true);addEventListener('resize',()=>{canvasPointerRect=null},{passive:true})}
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
const markFinalSurface=el=>{if(el.matches?.('.empty:not([data-final-empty])')){el.dataset.finalEmpty='1';el.classList.add('final-empty-state')}if(el.matches?.('dialog:not([data-final-dialog])')){el.dataset.finalDialog='1';el.classList.add('final-dialog')}el.querySelectorAll?.('.empty:not([data-final-empty]),dialog:not([data-final-dialog])').forEach(markFinalSurface)};
const globalObserver=new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes)if(node.nodeType===1)markFinalSurface(node)});
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
 const type='decoration',obj=typeof createObject==='function'?createObject(makeId('library'),type):null;if(!obj)return;const content=obj.querySelector('.content');content.textContent=item.text||item.glyph||'✦';content.lang=/[\u1780-\u17FF]/.test(item.text||item.glyph||'')?'km':'en';obj.dataset.color=(window.state?.accent||$('#accent')?.value||'#9d4555');obj.dataset.fontSize=item.text?'34':'64';obj.style.width=item.text?'76%':'150px';obj.style.height=item.text?'110px':'120px';obj.style.left=drop?`${drop.x}%`:(item.text?'12%':'32%');obj.style.top=drop?`${drop.y}%`:'38%';if(item.preset==='luxury'){obj.dataset.textGradientEnabled='true';obj.dataset.textGradientStart='#7a5718';obj.dataset.textGradientEnd='#e9c86e';obj.dataset.fontWeight='700';obj.dataset.letterSpacing='2'}if(item.preset==='editorial'){obj.dataset.fontStyle='italic';obj.dataset.font='serif-georgia';obj.dataset.fontSize='38'}if(item.preset==='khmer'){obj.dataset.font="noto-serif-khmer";obj.dataset.fontSize='34';obj.dataset.color='#a87616'}if(item.preset==='date'){obj.dataset.letterSpacing='4';obj.dataset.fontSize='26';obj.dataset.backgroundEnabled='true';obj.dataset.backgroundColor='#ffffff';obj.dataset.backgroundOpacity='78';obj.dataset.borderRadius='28'}applyObjectVisualStyle(obj);stage.append(obj);clearSelection();setSelection([obj]);saveNow();
 recent=[item.id,...recent.filter(x=>x!==item.id)].slice(0,10);localStorage.setItem(recentKey,JSON.stringify(recent));renderLibrary();toast(`${item.name} added`)}
function filteredLibrary(){return library.filter(x=>{if(libraryCat==='Favorites'&&!favorites.has(x.id))return false;if(libraryCat==='Recent'&&!recent.includes(x.id))return false;if(!['All','Favorites','Recent'].includes(libraryCat)&&x.cat!==libraryCat)return false;return!libraryQuery||`${x.name} ${x.cat}`.toLowerCase().includes(libraryQuery)})}
function renderLibrary(){const catHost=$('.final-library-cats',librarySection),grid=$('.final-library-grid',librarySection);catHost.innerHTML=cats.map(c=>`<button type="button" class="${c===libraryCat?'active':''}" data-cat="${c}">${c}</button>`).join('');catHost.querySelectorAll('button').forEach(b=>b.onclick=()=>{libraryCat=b.dataset.cat;renderLibrary()});const items=filteredLibrary();$('.final-library-count',librarySection).textContent=`${items.length} items`;grid.innerHTML='';items.forEach(item=>{const card=document.createElement('article');card.className='final-element-card';card.draggable=true;card.innerHTML=`<button type="button" class="final-fav ${favorites.has(item.id)?'active':''}" aria-label="Favorite">★</button><div class="final-element-preview">${item.shape?`<i class="shape-${item.shape}"></i>`:`<span lang="${/[\u1780-\u17FF]/.test(item.text||'')?'km':'en'}">${item.text||item.glyph}</span>`}</div><strong>${item.name}</strong><small>${item.cat}</small>`;card.onclick=e=>{if(e.target.closest('.final-fav'))return;addCustomElement(item)};card.querySelector('.final-fav').onclick=e=>{e.stopPropagation();favorites.has(item.id)?favorites.delete(item.id):favorites.add(item.id);localStorage.setItem(favKey,JSON.stringify([...favorites]));renderLibrary()};card.ondragstart=e=>{e.dataTransfer.setData('application/x-einvite-library-item',item.id);e.dataTransfer.effectAllowed='copy'};grid.append(card)})}
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
})();;/* Generated editor runtime bundle. Edit source modules, then run build_editor_bundle.py. */

/* ===== canvas-plus.js ===== */
(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
// Preserve the page identity declared by the document. The development
// server serves index.html at "/", where pathname alone cannot distinguish
// the editor from the dashboard.
const page=window.__EINVITE_PAGE||document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''))||'dashboard';
document.body.dataset.page=page;

function wireAuthLayouts(){
  if(page==='dashboard'){
    const login=$('#loginView');
    if(login && !login.querySelector('.canvas-auth-panel')){
      const title=$('h1',login)?.textContent||'Welcome back';
      const intro=$('p',login)?.textContent||'Sign in to manage your invitations.';
      const email=$('#email',login), password=$('#password',login), button=$('#loginBtn',login);
      const forgot=login.querySelector('a[href="reset.html"]');
      const hint=login.querySelector('.hint');
      const panel=document.createElement('div'); panel.className='canvas-auth-panel';
      const visual=document.createElement('div'); visual.className='canvas-auth-visual';
      visual.innerHTML=`<div><span class="canvas-auth-badge">✦ Invitation Studio</span></div>
        <div><h1>Design invitations that feel premium, personal, and alive.</h1><p>A creative workspace inspired by modern design tools, specialized for invitation websites, guest management, RSVP, Khmer dates, music, galleries, and event publishing.</p></div>
        <div class="canvas-auth-bullets">
          <div><span>1</span><div><strong>Design like a studio</strong><small>Canva-like creation flow with invitation-first templates, layered editing, animations, and polished publishing.</small></div></div>
          <div><span>2</span><div><strong>Run the event</strong><small>Publish links, manage guests, collect RSVPs, generate QR codes, and review analytics in one platform.</small></div></div>
          <div><span>3</span><div><strong>Built for Cambodia</strong><small>Khmer/English content, Khmer lunar dates, YouTube music, elegant wedding styling, and mobile-friendly guest viewing.</small></div></div>
        </div>`;
      const formWrap=document.createElement('div');
      formWrap.innerHTML=`<div class="canvas-auth-tabs"><button type="button" data-mode="signin" class="active">Sign in</button><button type="button" data-mode="register">Create account</button></div>
        <div><h2>${title}</h2><p>${intro}</p></div>
        <div class="canvas-auth-form"></div>
        <div class="canvas-auth-status"></div>`;
      const formHost=$('.canvas-auth-form',formWrap), status=$('.canvas-auth-status',formWrap);
      const confirmWrap=document.createElement('label'); confirmWrap.hidden=true; confirmWrap.innerHTML='Confirm password<input id="confirmPasswordRegister" type="password" autocomplete="new-password" minlength="8">';
      const options=document.createElement('div'); options.className='canvas-auth-actions';
      options.innerHTML=`<div class="canvas-auth-links"><a href="reset.html">Forgot password?</a><span class="canvas-auth-note">The local demo still works when the development backend is offline.</span></div>`;
      [email?.closest('label'), password?.closest('label')].forEach(el=>{ if(el) formHost.append(el);});
      formHost.append(confirmWrap);
      if(button) { button.classList.add('primary'); button.textContent='Sign in'; options.prepend(button); }
      if(forgot?.parentElement) forgot.parentElement.remove();
      if(hint) hint.remove();
      panel.append(formWrap, options, status);
      login.textContent=''; login.append(visual,panel);
      let mode='signin';
      const switchMode=(next)=>{
        mode=next; $$('[data-mode]',formWrap).forEach(b=>b.classList.toggle('active',b.dataset.mode===next));
        confirmWrap.hidden=next!=='register';
        if(button) button.textContent=next==='register'?'Create account':'Sign in';
        $('h2',formWrap).textContent=next==='register'?'Create account':'Welcome back';
        $('p',formWrap).textContent=next==='register'?'Create a clean workspace for managing invitations, templates, guests, and published events.':'Sign in to continue working on invitations, templates, materials, and guest management.';
        status.textContent='';
      };
      $$('[data-mode]',formWrap).forEach(b=>b.onclick=()=>switchMode(b.dataset.mode));
      const handle=async()=>{
        const em=email?.value.trim()||'', pw=password?.value||'', cp=$('#confirmPasswordRegister')?.value||'';
        if(!/^.+@.+\..+$/.test(em)) return status.textContent='Enter a valid email address.';
        if(pw.length<8) return status.textContent='Use a password of at least 8 characters.';
        if(mode==='register' && pw!==cp) return status.textContent='The passwords do not match.';
        status.textContent=mode==='register'?'Creating account…':'Signing in…';
        button && (button.disabled=true);
        try{
          const endpoint=mode==='register'?'/api/auth/register':'/api/auth/login';
          let result=null;
          try{
            const r=await fetch(endpoint,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:em,password:pw})});
            const data=await r.json().catch(()=>({}));
            if(r.ok){ result=data; }
            else if(mode==='signin') throw new Error(data.error||'Sign in failed');
            else throw new Error(data.error||'Account creation failed');
          }catch(err){
            if(mode==='signin' && /Failed to fetch|NetworkError|fetch/i.test(String(err))){
              localStorage.setItem('sovan-account-v1',JSON.stringify({id:crypto.randomUUID(),email:em,role:'customer',plan:'Free'}));
              location.reload(); return;
            }
            if(mode==='register' && /Failed to fetch|NetworkError|fetch/i.test(String(err))){
              localStorage.setItem('sovan-account-v1',JSON.stringify({id:crypto.randomUUID(),email:em,role:'customer',plan:'Free'}));
              location.reload(); return;
            }
            throw err;
          }
          
          if(result?.user) localStorage.setItem('sovan-account-v1',JSON.stringify(result.user));
          else localStorage.setItem('sovan-account-v1',JSON.stringify({id:crypto.randomUUID(),email:em,role:'customer',plan:'Free'}));
          location.reload();
        }catch(error){
          status.textContent=error.message||'Authentication failed.';
        }finally{button && (button.disabled=false)}
      };
      button && (button.onclick=handle);
      password?.addEventListener('keydown',e=>{if(e.key==='Enter') handle()});
      $('#confirmPasswordRegister')?.addEventListener('keydown',e=>{if(e.key==='Enter') handle()});
    }
  }
  if(page==='reset'){
    const main=$('.auth-page');
    if(main && !main.querySelector('.canvas-auth-visual')){
      const visual=document.createElement('div'); visual.className='canvas-auth-visual';
      visual.innerHTML=`<div><span class="canvas-auth-badge">✦ Secure access</span></div>
        <div><h2>Recover account access cleanly and safely.</h2><p>Reset links, account verification, and password changes follow the same modern system used throughout the platform.</p></div>
        <div class="canvas-auth-bullets"><div><span>✓</span><div><strong>Simple request flow</strong><small>Request a reset link using the email tied to the account.</small></div></div><div><span>✓</span><div><strong>Clean confirmation step</strong><small>Choose a new password with a clear, minimal form.</small></div></div></div>`;
      const panel=document.createElement('div'); panel.className='canvas-auth-panel';
      const request=$('#requestView',main), confirm=$('#confirmView',main);
      panel.append(request,confirm); main.prepend(visual); main.append(panel);
    }
  }
  if(page==='verify'){
    const main=$('.verify-page');
    if(main && !main.querySelector('.canvas-auth-visual')){
      const heading=main.querySelector('h1'), status=$('#status',main), action=main.querySelector('a');
      const visual=document.createElement('div'); visual.className='canvas-auth-visual';
      visual.innerHTML=`<div><span class="canvas-auth-badge">✦ Account security</span></div>
        <div><h2>One more step to confirm your email.</h2><p>Verification keeps invitation accounts safer and improves trust for guest communications, sharing, and account recovery.</p></div>`;
      const panel=document.createElement('div'); panel.className='canvas-auth-panel';
      if(heading){heading.textContent='Email verification';panel.append(heading)}
      if(status)panel.append(status);
      if(action)panel.append(action);
      main.prepend(visual);main.append(panel);
    }
  }
}

function enhanceMaterialsPage(){
  if(page!=='materials')return;
  const box=$('.upload-box'),input=$('#uploadFile'),button=$('#uploadBtn');
  if(!box||!input||!button||box.querySelector('.canvas-upload-drop'))return;
  const drop=document.createElement('div');drop.className='canvas-upload-drop';drop.tabIndex=0;drop.innerHTML=`<div class="canvas-upload-icon">⇧</div><div><strong>Drop files here</strong><span>Upload photos, audio, or video — multiple files supported</span></div><button type="button">Browse files</button>`;
  box.insertBefore(drop,box.querySelector('.upload-row'));
  const browse=drop.querySelector('button');browse.onclick=()=>input.click();
  const setFiles=files=>{const valid=[...files].filter(file=>file&&file.size);if(!valid.length)return;const dt=new DataTransfer();valid.forEach(file=>dt.items.add(file));input.files=dt.files;drop.querySelector('strong').textContent=`${valid.length} file${valid.length===1?'':'s'} ready`;drop.querySelector('span').textContent=valid.map(file=>file.name).slice(0,3).join(' · ')+(valid.length>3?` +${valid.length-3} more`:'');};
  input.addEventListener('change',()=>setFiles(input.files));
  ['dragenter','dragover'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('drag-over')}));
  ['dragleave','drop'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('drag-over')}));
  drop.addEventListener('drop',e=>setFiles(e.dataTransfer.files));
  drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click()}});
  document.addEventListener('paste',e=>{if(['INPUT','TEXTAREA'].includes(document.activeElement?.tagName))return;const files=[...e.clipboardData.items].filter(x=>x.kind==='file').map(x=>x.getAsFile()).filter(Boolean);if(files.length){e.preventDefault();setFiles(files);window.uiToast?.(`${files.length} pasted file${files.length===1?'':'s'} ready to upload`,'⇧')}});
}

function editorEnhancements(){
  const stage=$('#stage'); if(!stage) return;
  const header=document.querySelector('body>header');
  if(header && !header.querySelector('.canvas-header-more')){
    const saveState=$('#saveState'),serverState=$('#serverState');
    if(saveState||serverState){const status=document.createElement('div');status.className='canvas-header-status';if(saveState)status.append(saveState);if(serverState)status.append(serverState);const before=$('#studioCommandBtn')||$('#previewBtn');header.insertBefore(status,before)}
    const undo=$('#undoBtn'),redo=$('#redoBtn'),preview=$('#previewBtn'),publish=$('#publishBtn'),actions=$('#studioCommandBtn'),check=$('#studioCheckBtn');
    if(undo){undo.innerHTML='↶';undo.setAttribute('aria-label','Undo');undo.title='Undo (Ctrl/Cmd+Z)';undo.classList.add('canvas-icon-button')}
    if(redo){redo.innerHTML='↷';redo.setAttribute('aria-label','Redo');redo.title='Redo (Ctrl/Cmd+Shift+Z)';redo.classList.add('canvas-icon-button')}
    if(actions)actions.textContent='Actions';if(check)check.textContent='Check';if(preview)preview.textContent='Preview';if(publish)publish.textContent='Publish';
    const more=document.createElement('div');more.className='canvas-header-more';more.innerHTML='<button type="button" class="canvas-header-more-trigger" aria-label="More editor actions" aria-expanded="false">•••</button><div class="canvas-header-more-menu" hidden><strong>Project</strong></div>';
    header.append(more);const menu=$('.canvas-header-more-menu',more),trigger=$('.canvas-header-more-trigger',more);
    [$('#backupBtn'),$('#restoreBtn')].filter(Boolean).forEach(btn=>menu.append(btn));
    trigger.onclick=()=>{menu.hidden=!menu.hidden;trigger.setAttribute('aria-expanded',String(!menu.hidden))};
    document.addEventListener('pointerdown',e=>{if(!more.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  }
  const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
  const saveNow=()=>{ try{ typeof save==='function' && save(); }catch{} };
  const applyItems=(items)=>{ items.forEach(item=>{ try{ typeof applyObjectVisualStyle==='function' && applyObjectVisualStyle(item);}catch{} }); try{ typeof updateSelectionBounds==='function'&&updateSelectionBounds(); }catch{}; try{ typeof refreshSelectionUI==='function'&&refreshSelectionUI(); }catch{}; };
  const setSelectionIfNeeded=(obj)=>{ try{ if(!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected')) typeof select==='function' && select(obj,false);}catch{} };
  const objectPane=$('[data-inspector-pane="object"]')||$('#properties')?.parentElement;
  const toast=(m,icon='✦')=>{ if(window.uiToast) window.uiToast(m,icon); else console.info(m); };
  const selectedOne=()=>activeObjects()[0]||null;
  const stagePercentFrame=(item)=>{
    if(!item)return{x:0,y:0,w:0,h:0,r:0};
    const sr=stage.getBoundingClientRect(),ir=item.getBoundingClientRect();
    return{x:(ir.left-sr.left)/sr.width*100,y:(ir.top-sr.top)/sr.height*100,w:ir.width/sr.width*100,h:ir.height/sr.height*100,r:Number(item.dataset.rotation||0)};
  };
  if(objectPane && !$('#canvasPlusTransform')){
    const block=document.createElement('section');block.className='final-advanced-inspector';block.id='canvasPlusTransform';
    block.innerHTML=`<div class="final-panel-title"><div><small>Transform</small><h2>Position & size</h2></div><span class="final-beta">Precise</span></div>
      <div class="canvas-transform-grid">
        <label>X %<input id="canvasTransformX" type="number" step="0.1"></label>
        <label>Y %<input id="canvasTransformY" type="number" step="0.1"></label>
        <label>W %<input id="canvasTransformW" type="number" step="0.1" min="1" max="100"></label>
        <label>H %<input id="canvasTransformH" type="number" step="0.1" min="1" max="100"></label>
        <label>Rotate°<input id="canvasTransformR" type="number" step="1" min="-360" max="360"></label>
        <label class="canvas-lock-ratio"><span>Keep ratio</span><input id="canvasTransformLockRatio" type="checkbox"></label>
      </div>
      <div class="canvas-transform-actions"><button type="button" data-transform-action="center">Center</button><button type="button" data-transform-action="fill-width">Fill width</button><button type="button" data-transform-action="reset-rotation">Reset rotation</button></div>`;
    objectPane.prepend(block);
    const ids={x:'canvasTransformX',y:'canvasTransformY',w:'canvasTransformW',h:'canvasTransformH',r:'canvasTransformR'};
    let ratio=1,updating=false;
    const refreshTransform=()=>{const item=selectedOne();block.classList.toggle('is-disabled',!item);if(!item)return;const f=stagePercentFrame(item);ratio=f.w/Math.max(.001,f.h);updating=true;Object.entries(ids).forEach(([key,id])=>{const map={x:f.x,y:f.y,w:f.w,h:f.h,r:f.r};$('#'+id).value=Number(map[key]).toFixed(key==='r'?0:1)});updating=false};
    const applyTransform=(key,value)=>{if(updating)return;const item=selectedOne();if(!item)return;let v=Number(value);if(!Number.isFinite(v))return;const frame=stagePercentFrame(item),lock=$('#canvasTransformLockRatio').checked;
      if(key==='x')item.style.left=`${Math.max(0,Math.min(100-frame.w,v))}%`;
      if(key==='y')item.style.top=`${Math.max(0,Math.min(100-frame.h,v))}%`;
      if(key==='w'){v=Math.max(1,Math.min(100,v));item.style.width=`${v}%`;if(lock)item.style.height=`${Math.max(1,Math.min(100,v/Math.max(.001,ratio)))}%`}
      if(key==='h'){v=Math.max(1,Math.min(100,v));item.style.height=`${v}%`;if(lock)item.style.width=`${Math.max(1,Math.min(100,v*ratio))}%`}
      if(key==='r'){item.dataset.rotation=String(v);item.style.transform=`rotate(${v}deg)`}
      applyItems([item]);saveNow();refreshTransform();
    };
    Object.entries(ids).forEach(([key,id])=>$('#'+id).addEventListener('change',e=>applyTransform(key,e.target.value)));
    block.addEventListener('click',e=>{const action=e.target.closest('[data-transform-action]')?.dataset.transformAction,item=selectedOne();if(!action||!item)return;const f=stagePercentFrame(item);if(action==='center'){item.style.left=`${(50-f.w/2).toFixed(2)}%`;item.style.top=`${(50-f.h/2).toFixed(2)}%`}if(action==='fill-width'){item.style.left='5%';item.style.width='90%'}if(action==='reset-rotation'){item.dataset.rotation='0';item.style.transform='rotate(0deg)'}applyItems([item]);saveNow();refreshTransform()});
    let pointerBusy=false,refreshQueued=false;const queueTransformRefresh=()=>{if(pointerBusy||refreshQueued)return;refreshQueued=true;requestAnimationFrame(()=>{refreshQueued=false;if(!pointerBusy)refreshTransform()})};const obs=new MutationObserver(queueTransformRefresh);obs.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','style','data-rotation']});document.addEventListener('pointerdown',()=>{pointerBusy=true},true);document.addEventListener('pointerup',()=>{pointerBusy=false;setTimeout(refreshTransform,0)},true);refreshTransform();
  }
  const eventPane=$('[data-studio-pane="event"]');
  if(eventPane && !$('#canvasSmartWriter')){
    const assistant=document.createElement('section');assistant.className='canvas-smart-assistant';assistant.id='canvasSmartWriter';
    assistant.innerHTML=`<div class="final-panel-title"><div><small>AI assistant</small><h2>Invitation writing</h2></div><span class="final-beta">Smart</span></div>
      <label>Tone<select id="canvasSmartTone"><option value="formal">Formal & elegant</option><option value="romantic">Romantic</option><option value="modern">Modern & warm</option><option value="concise">Short & clean</option><option value="business">Business formal</option></select></label>
      <div class="canvas-ai-grid"><button type="button" id="canvasGenerateCopy">Generate wording</button><button type="button" id="canvasKhmerFormal">Khmer formal wording</button><button type="button" id="canvasSuggestPalette">Suggest palette</button><button type="button" id="canvasAutoHero">Auto polish hero</button></div>
      <p class="canvas-ai-hint">These built-in smart tools work offline. A future production AI provider can replace or extend them without changing the invitation document model.</p>`;
    const heading=eventPane.querySelector('.studio-pane-heading');heading?.after(assistant);
    const value=id=>$('#'+id)?.value?.trim()||'';
    const fire=(id,v)=>{const el=$('#'+id);if(!el)return;el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))};
    const englishCopy=(tone)=>{const names=value('names')||'the hosts',date=value('date'),venue=value('venue');const datePart=date?` on ${new Date(date+'T00:00:00').toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'})}`:'';const venuePart=venue?` at ${venue}`:'';const map={
      formal:`Together with our families, ${names} request the honor of your presence as we celebrate this meaningful occasion${datePart}${venuePart}. Your presence would make the day truly memorable.`,
      romantic:`With joyful hearts and the people we love most, ${names} invite you to share in a beautiful celebration of love, laughter, and new beginnings${datePart}${venuePart}.`,
      modern:`We are celebrating, and we would love to have you there. Join ${names}${datePart}${venuePart} for good moments, great company, and a day worth remembering.`,
      concise:`Please join ${names} for a special celebration${datePart}${venuePart}. We would be honored to celebrate with you.`,
      business:`You are cordially invited to join us for a special event hosted by ${names}${datePart}${venuePart}. We look forward to welcoming you.`};return map[tone]||map.formal};
    $('#canvasGenerateCopy').onclick=()=>{fire('message',englishCopy($('#canvasSmartTone').value));toast('Invitation wording generated.','✦')};
    $('#canvasKhmerFormal').onclick=()=>{const names=value('namesKm')||value('names')||'យើងខ្ញុំ';const venue=value('venueKm')||value('venue');fire('messageKm',`យើងខ្ញុំ ${names} និងក្រុមគ្រួសារ សូមគោរពអញ្ជើញលោកអ្នក និងក្រុមគ្រួសារ ចូលរួមជាភ្ញៀវកិត្តិយសក្នុងពិធីដ៏មានអត្ថន័យរបស់យើង${venue?` ដែលប្រារព្ធនៅ ${venue}`:''}។ វត្តមានដ៏ថ្លៃថ្លារបស់លោកអ្នក គឺជាកិត្តិយស និងសេចក្តីរីករាយដ៏ធំធេងសម្រាប់យើងខ្ញុំ។`);toast('Khmer formal wording generated.','ក')};
    $('#canvasSuggestPalette').onclick=()=>{const tone=$('#canvasSmartTone').value,presets={formal:['#80512a','#fffaf2','#3a2d25','#9a6a2c'],romantic:['#a64f6a','#fff5f7','#422f36','#b7607a'],modern:['#6758c8','#f7f7ff','#26243a','#7e6ee5'],concise:['#27354a','#f8fafc','#202631','#566b88'],business:['#173a63','#f5f8fc','#172333','#315c8c']},p=presets[tone]||presets.formal;fire('accent',p[0]);fire('paletteBackground',p[1]);fire('paletteText',p[2]);fire('paletteHeading',p[3]);const preset=$('#palettePreset');if(preset){preset.value='custom';preset.dispatchEvent(new Event('change',{bubbles:true}))}toast('A matching palette was suggested.','◐')};
    $('#canvasAutoHero').onclick=()=>{const objects=$$('.object',stage);if(!objects.length)return toast('Add some hero elements first.');const texts=objects.filter(o=>o.dataset.objectType==='text'||o.dataset.objectType==='decoration'),images=objects.filter(o=>o.dataset.objectType==='image');texts.forEach((o,i)=>{const w=Math.min(84,Math.max(44,stagePercentFrame(o).w));o.style.width=`${w}%`;o.style.left=`${(50-w/2).toFixed(1)}%`;o.style.top=`${10+i*13}%`;if(i===0){o.dataset.fontSize=String(Math.max(42,Number(o.dataset.fontSize||48)));o.dataset.fontWeight='700'}});images.forEach((o,i)=>{if(i>1)return;o.style.left=i?'56%':'8%';o.style.top='48%';o.style.width='36%';o.style.height='300px';o.dataset.imageFrame=o.dataset.imageFrame||'white';o.dataset.shadowBlur='20'});applyItems(objects);saveNow();toast('Hero layout polished.','✦')};
  }
  const designPane=$('[data-inspector-pane="theme"]');
  if(designPane && !$('#canvasBackgroundStudio')){
    const section=document.createElement('section');section.className='final-advanced-inspector';section.id='canvasBackgroundStudio';
    section.innerHTML=`<div class="final-panel-title"><div><small>Canvas background</small><h2>Gradient & texture</h2></div><span class="final-beta">Design</span></div>
      <label>Background mode<select id="canvasBgMode"><option value="none">Use template / palette</option><option value="solid">Custom solid</option><option value="gradient">Gradient</option></select></label>
      <div class="final-two-col"><label>Start<input id="canvasBgStart" type="color" value="#fff8f2"></label><label>End<input id="canvasBgEnd" type="color" value="#ead8d0"></label></div>
      <label>Gradient angle <span id="canvasBgAngleValue">135°</span><input id="canvasBgAngle" type="range" min="0" max="360" value="135"></label>
      <label>Texture<select id="canvasBgTexture"><option value="none">None</option><option value="paper">Soft paper</option><option value="soft-grain">Fine grain</option><option value="dots">Dot pattern</option><option value="grid">Editorial grid</option></select></label>
      <label>Texture strength <span id="canvasBgTextureValue">18%</span><input id="canvasBgTextureOpacity" type="range" min="0" max="60" value="18"></label>
      <div class="canvas-bg-presets"><button type="button" data-bg-preset="ivory">Ivory paper</button><button type="button" data-bg-preset="rose">Rose glow</button><button type="button" data-bg-preset="midnight">Midnight</button><button type="button" data-bg-preset="emerald">Garden</button></div>`;
    const head=designPane.querySelector('.studio-inspector-heading');head?.after(section);
    const els={mode:$('#canvasBgMode'),start:$('#canvasBgStart'),end:$('#canvasBgEnd'),angle:$('#canvasBgAngle'),texture:$('#canvasBgTexture'),opacity:$('#canvasBgTextureOpacity')};
    function textureImages(texture,opacity){const a=Math.max(0,Math.min(60,Number(opacity||18)))/100,ink=`rgba(255,255,255,${(a*.45).toFixed(3)})`,shade=`rgba(0,0,0,${(a*.24).toFixed(3)})`;if(texture==='dots')return[`radial-gradient(circle at 1px 1px,${ink} 1px,transparent 1.4px)`,'18px 18px'];if(texture==='grid')return[`linear-gradient(${ink} 1px,transparent 1px),linear-gradient(90deg,${ink} 1px,transparent 1px)`,'28px 28px'];if(texture==='paper')return[`radial-gradient(circle at 20% 20%,${ink},transparent 30%),radial-gradient(circle at 78% 64%,${shade},transparent 34%),linear-gradient(115deg,transparent,${ink},transparent)`,'auto'];if(texture==='soft-grain')return[`radial-gradient(circle at 12% 18%,${ink} 0 1px,transparent 1.5px),radial-gradient(circle at 72% 68%,${shade} 0 1px,transparent 1.6px)`,'7px 7px,9px 9px'];return['','auto']}
    const render=()=>{const mode=els.mode.value,start=els.start.value,end=els.end.value,angle=Number(els.angle.value),texture=els.texture.value,opacity=Number(els.opacity.value);stage.dataset.backgroundMode=mode;stage.dataset.backgroundStart=start;stage.dataset.backgroundEnd=end;stage.dataset.backgroundAngle=String(angle);stage.dataset.backgroundTexture=texture;stage.dataset.backgroundTextureOpacity=String(opacity);$('#canvasBgAngleValue').textContent=`${angle}°`;$('#canvasBgTextureValue').textContent=`${opacity}%`;const images=[];if(mode==='gradient')images.push(`linear-gradient(${angle}deg,${start},${end})`);const [tex,size]=textureImages(texture,opacity);if(tex)images.push(tex);if(mode==='solid'){stage.style.backgroundColor=start;stage.style.backgroundImage=tex||'none';stage.style.backgroundSize=size}else if(mode==='gradient'){stage.style.backgroundColor=start;stage.style.backgroundImage=images.join(',');stage.style.backgroundSize=size}else{const preset=$('#palettePreset')?.value||'template';stage.style.backgroundColor=preset!=='template'?($('#paletteBackground')?.value||''):'';stage.style.backgroundImage=tex||'';stage.style.backgroundSize=size}saveNow()};
    const refresh=()=>{els.mode.value=stage.dataset.backgroundMode||'none';els.start.value=stage.dataset.backgroundStart||'#fff8f2';els.end.value=stage.dataset.backgroundEnd||'#ead8d0';els.angle.value=stage.dataset.backgroundAngle||'135';els.texture.value=stage.dataset.backgroundTexture||'none';els.opacity.value=stage.dataset.backgroundTextureOpacity||'18';$('#canvasBgAngleValue').textContent=`${els.angle.value}°`;$('#canvasBgTextureValue').textContent=`${els.opacity.value}%`};
    Object.values(els).forEach(el=>el.addEventListener(el.type==='range'||el.type==='color'?'input':'change',render));
    section.addEventListener('click',e=>{const preset=e.target.closest('[data-bg-preset]')?.dataset.bgPreset;if(!preset)return;const map={ivory:['solid','#f8f1e6','#f8f1e6',135,'paper',20],rose:['gradient','#fff4f4','#e9c3cd',135,'soft-grain',16],midnight:['gradient','#171321','#4c3868',145,'soft-grain',20],emerald:['gradient','#eff8f1','#b9d9c7',135,'paper',18]},v=map[preset];[els.mode.value,els.start.value,els.end.value,els.angle.value,els.texture.value,els.opacity.value]=['gradient',v[1],v[2],String(v[3]),v[4],String(v[5])];if(preset==='ivory')els.mode.value='solid';render();toast(`${e.target.textContent} background applied.`,'◐')});
    refresh();
  }

  if(objectPane && !$('#canvasPlusTextBox')){
    const textBox=document.createElement('section');textBox.className='final-advanced-inspector';textBox.id='canvasPlusTextBox';
    textBox.innerHTML=`<div class="final-panel-title"><div><small>Text box</small><h2>Flow & spacing</h2></div></div>
      <label>Vertical alignment<select id="canvasTextVertical"><option value="top">Top</option><option value="middle">Middle</option><option value="bottom">Bottom</option></select></label>
      <label>Inner padding <span id="canvasTextPaddingValue">8px</span><input id="canvasTextPadding" type="range" min="0" max="64" step="1" value="8"></label>
      <div class="canvas-pro-grid"><button type="button" data-text-fit="tight">Tight box</button><button type="button" data-text-fit="comfortable">Comfortable</button><button type="button" data-text-fit="wide">Wide title</button></div>`;
    objectPane.append(textBox);
    const textSelection=()=>activeObjects().filter(item=>['text','decoration'].includes(item.dataset.objectType));
    const syncTextBox=()=>{const item=textSelection()[0];textBox.hidden=!item;if(!item)return;$('#canvasTextVertical').value=item.dataset.textVerticalAlign||'middle';$('#canvasTextPadding').value=String(Number(item.dataset.textPadding??8));$('#canvasTextPaddingValue').textContent=`${$('#canvasTextPadding').value}px`;};
    $('#canvasTextVertical').onchange=e=>{const items=textSelection();items.forEach(item=>item.dataset.textVerticalAlign=e.target.value);applyItems(items);saveNow();};
    $('#canvasTextPadding').oninput=e=>{const items=textSelection();items.forEach(item=>item.dataset.textPadding=e.target.value);$('#canvasTextPaddingValue').textContent=`${e.target.value}px`;applyItems(items);saveNow();};
    textBox.addEventListener('click',e=>{const b=e.target.closest('[data-text-fit]');if(!b)return;const items=textSelection();if(!items.length)return;items.forEach(item=>{if(b.dataset.textFit==='tight'){item.dataset.textPadding='2';item.dataset.lineHeight='1.05'}else if(b.dataset.textFit==='comfortable'){item.dataset.textPadding='12';item.dataset.lineHeight='1.35'}else{item.dataset.textPadding='8';item.dataset.lineHeight='1.15';item.style.width='82%';item.style.left='9%'}});applyItems(items);saveNow();syncTextBox();});
    const textBoxObserver=new MutationObserver(syncTextBox);textBoxObserver.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','data-text-vertical-align','data-text-padding']});document.addEventListener('pointerup',()=>setTimeout(syncTextBox,0),true);syncTextBox();
  }

  if(objectPane && !$('#canvasPlusTextPlacement')){
    const block=document.createElement('section'); block.className='final-advanced-inspector'; block.id='canvasPlusTextPlacement';
    block.innerHTML=`<div class="final-panel-title"><div><small>Placement</small><h2>Quick position</h2></div></div>
      <div class="canvas-pro-grid">
        <button type="button" data-place="tl">Top left</button>
        <button type="button" data-place="tc">Top center</button>
        <button type="button" data-place="tr">Top right</button>
        <button type="button" data-place="cl">Center left</button>
        <button type="button" data-place="cc">Center</button>
        <button type="button" data-place="cr">Center right</button>
        <button type="button" data-place="bl">Bottom left</button>
        <button type="button" data-place="bc">Bottom center</button>
        <button type="button" data-place="br">Bottom right</button>
      </div>`;
    objectPane.append(block);
    block.addEventListener('click',e=>{
      const btn=e.target.closest('[data-place]'); if(!btn) return;
      const items=activeObjects(); if(!items.length) return;
      const srect=stage.getBoundingClientRect();
      items.forEach(item=>{
        const rect=item.getBoundingClientRect();
        const w=rect.width/srect.width*100, h=rect.height/srect.height*100;
        const [v,hz]=[btn.dataset.place[0],btn.dataset.place[1]];
        let left=2, top=2;
        if(hz==='c') left=50-w/2; else if(hz==='r') left=98-w;
        if(v==='c') top=50-h/2; else if(v==='b') top=98-h;
        item.style.left=`${Math.max(0,Math.min(100-w,left))}%`;
        item.style.top=`${Math.max(0,Math.min(100-h,top))}%`;
      });
      applyItems(items); saveNow();
    });
  }
  if(objectPane && !$('#canvasPlusAiTools')){
    const block=document.createElement('section'); block.className='final-advanced-inspector'; block.id='canvasPlusAiTools';
    block.innerHTML=`<div class="final-panel-title"><div><small>AI tools</small><h2>Photo assist</h2></div><span class="final-beta">Beta</span></div>
      <div class="canvas-ai-grid">
        <button type="button" id="aiBgCut">Auto bg cut</button>
        <button type="button" id="aiBgRestore">Restore image</button>
        <button type="button" id="aiEnhance">Magic enhance</button>
        <button type="button" id="aiSoftPortrait">Portrait soften</button>
        <button type="button" id="aiReplaceImage">Replace image</button>
        <button type="button" id="aiResetPhoto">Reset edits</button>
        <button type="button" id="aiFlipX">Flip horizontal</button>
        <button type="button" id="aiFlipY">Flip vertical</button>
      </div>
      <label class="canvas-photo-hue">Hue <span id="aiHueValue">0°</span><input id="aiHue" type="range" min="-180" max="180" step="1" value="0"></label>
      <details class="canvas-bg-cut-settings"><summary>Background removal settings</summary>
        <label>Sensitivity <span id="aiBgThresholdValue">44</span><input id="aiBgThreshold" type="range" min="20" max="90" step="1" value="44"></label>
        <label>Edge softness <span id="aiBgFeatherValue">16</span><input id="aiBgFeather" type="range" min="0" max="40" step="1" value="16"></label>
        <small>Higher sensitivity removes colors farther from the estimated background. Increase edge softness for smoother cutout edges.</small>
      </details>
      <div class="canvas-ai-hint">Local smart helpers run in the browser. Background removal estimates the background from image edges and works best when the subject is clearly separated from a simple background. The original image remains restorable.</div>`;
    objectPane.append(block);

    const toast=(m)=>{ if(window.uiToast) window.uiToast(m,'✦'); else alert(m); };
    const selectedImage=()=>activeObjects()[0]?.querySelector?.('img')||null;
    const syncSelectedImageSrc=(src)=>{ const item=activeObjects()[0]; if(!item||!src) return; const img=item.querySelector('img'); if(img) img.src=src; item.dataset.src=src; try{ if(window.state?.objects?.[item.dataset.id]) window.state.objects[item.dataset.id].src=src; }catch{} applyItems([item]); saveNow(); };
    function averageCorners(data,w,h){
      const picks=[[0,0],[w-1,0],[0,h-1],[w-1,h-1],[Math.floor(w*.5),0],[0,Math.floor(h*.5)],[w-1,Math.floor(h*.5)],[Math.floor(w*.5),h-1]];
      const acc=[0,0,0]; let count=0;
      picks.forEach(([x,y])=>{const i=(y*w+x)*4; if(data[i+3]>16){acc[0]+=data[i]; acc[1]+=data[i+1]; acc[2]+=data[i+2]; count++;}});
      return acc.map(v=>count?Math.round(v/count):255);
    }
    function dist(i,data,bg){const dr=data[i]-bg[0], dg=data[i+1]-bg[1], db=data[i+2]-bg[2]; return Math.sqrt(dr*dr+dg*dg+db*db);}
    async function cutBackground(){
      const item=activeObjects()[0]; const img=selectedImage(); if(!item||!img) return toast('Select one image first.');
      const cutButton=$('#aiBgCut'); const originalLabel=cutButton?.textContent||'Auto bg cut';
      if(cutButton){cutButton.disabled=true;cutButton.textContent='Removing background…'}
      try{
        try{ if(img.decode) await img.decode(); }catch{}
        const source=img.src; if(!item.dataset.originalSrc) item.dataset.originalSrc=source;
        const max=900; const scale=Math.min(1,max/Math.max(img.naturalWidth||img.width, img.naturalHeight||img.height));
        const w=Math.max(8,Math.round((img.naturalWidth||img.width)*scale)); const h=Math.max(8,Math.round((img.naturalHeight||img.height)*scale));
        const canvas=document.createElement('canvas'); canvas.width=w; canvas.height=h; const ctx=canvas.getContext('2d',{willReadFrequently:true});
        if(!ctx)throw Error('Canvas processing is unavailable in this browser.');
        ctx.drawImage(img,0,0,w,h); const id=ctx.getImageData(0,0,w,h), data=id.data; const bg=averageCorners(data,w,h); const visited=new Uint8Array(w*h); const stack=[];
        for(let x=0;x<w;x++){ stack.push(x,0,x,h-1); }
        for(let y=1;y<h-1;y++){ stack.push(0,y,w-1,y); }
        const threshold=Math.max(20,Math.min(90,Number($('#aiBgThreshold')?.value||44)));
        const feather=Math.max(0,Math.min(40,Number($('#aiBgFeather')?.value||16)));
        while(stack.length){
          const y=stack.pop(), x=stack.pop(); const pos=y*w+x; if(visited[pos]) continue; visited[pos]=1; const i=pos*4;
          if(data[i+3]<10 || dist(i,data,bg)<=threshold){data[i+3]=0;if(x>0)stack.push(x-1,y);if(x<w-1)stack.push(x+1,y);if(y>0)stack.push(x,y-1);if(y<h-1)stack.push(x,y+1)}
        }
        if(feather>0)for(let i=0;i<data.length;i+=4){const d=dist(i,data,bg);if(data[i+3]>0&&d<threshold+feather)data[i+3]=Math.max(0,Math.min(255,Math.round((d-threshold)/Math.max(1,feather)*255)))}
        ctx.putImageData(id,0,0);
        const localResult=canvas.toDataURL('image/png');
        const inviteId=window.EInviteContext?.getInvitationId()||localStorage.getItem('sovan-active-invite');
        if(inviteId){
          try{
            const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png',.96));
            if(blob){
              const cutFile=new File([blob],'background-cut.png',{type:'image/png',lastModified:Date.now()});
              const result=window.EInviteUpload?.upload
                ? await window.EInviteUpload.upload(inviteId,cutFile,{name:'background-cut.png'})
                : await (async()=>{const response=await fetch(`/api/invitations/${encodeURIComponent(inviteId)}/assets/raw`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'image/png','X-File-Name':'background-cut.png'},body:blob});const payload=await response.json().catch(()=>({}));if(!response.ok)throw Error(payload.error||'The cutout could not be saved to the material library');return payload})();
              if(result?.url){syncSelectedImageSrc(result.url);toast('Background removed and saved to your materials.');return}
            }
          }catch{}
        }
        syncSelectedImageSrc(localResult);toast('Background removed locally.');
      }catch(error){
        toast(error?.message||'Background removal could not be completed for this image.');
      }finally{
        if(cutButton){cutButton.disabled=false;cutButton.textContent=originalLabel}
      }
    }
    const selectedPhotoObject=()=>{const item=activeObjects()[0];return item?.dataset.objectType==='image'?item:null};
    const syncPhotoControls=()=>{const item=selectedPhotoObject();const hue=$('#aiHue');if(hue){hue.value=String(Number(item?.dataset.imageHue||0));$('#aiHueValue').textContent=`${hue.value}°`;block.classList.toggle('canvas-photo-disabled',!item)}};
    $('#aiBgCut').onclick=cutBackground;
    $('#aiBgRestore').onclick=()=>{ const item=selectedPhotoObject(); if(!item?.dataset.originalSrc) return toast('No original image is stored yet.'); syncSelectedImageSrc(item.dataset.originalSrc); toast('Original image restored.'); };
    $('#aiEnhance').onclick=()=>{ const item=selectedPhotoObject(); if(!item) return toast('Select an image first.'); item.dataset.imageBrightness='106'; item.dataset.imageContrast='114'; item.dataset.imageSaturation='114'; item.dataset.imageSepia='6'; item.dataset.imageBlur='0'; applyItems([item]); saveNow(); toast('Magic enhance applied.'); };
    $('#aiSoftPortrait').onclick=()=>{ const item=selectedPhotoObject(); if(!item) return toast('Select an image first.'); item.dataset.imageBrightness='104'; item.dataset.imageContrast='102'; item.dataset.imageSaturation='108'; item.dataset.imageBlur='0.4'; item.dataset.imageSepia='4'; applyItems([item]); saveNow(); toast('Portrait soften applied.'); };
    $('#aiFlipX').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');item.dataset.imageFlipX=item.dataset.imageFlipX==='true'?'false':'true';applyItems([item]);saveNow();toast('Horizontal flip updated.');};
    $('#aiFlipY').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');item.dataset.imageFlipY=item.dataset.imageFlipY==='true'?'false':'true';applyItems([item]);saveNow();toast('Vertical flip updated.');};
    $('#aiHue').oninput=e=>{const item=selectedPhotoObject();if(!item)return;item.dataset.imageHue=e.target.value;$('#aiHueValue').textContent=`${e.target.value}°`;applyItems([item]);saveNow();};
    $('#aiBgThreshold')?.addEventListener('input',e=>{$('#aiBgThresholdValue').textContent=e.target.value});
    $('#aiBgFeather')?.addEventListener('input',e=>{$('#aiBgFeatherValue').textContent=e.target.value});
    $('#aiResetPhoto').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');Object.assign(item.dataset,{imageBrightness:'100',imageContrast:'100',imageSaturation:'100',imageGrayscale:'0',imageSepia:'0',imageBlur:'0',imageHue:'0',imageFlipX:'false',imageFlipY:'false'});applyItems([item]);saveNow();syncPhotoControls();toast('Photo adjustments reset.');};
    $('#aiReplaceImage').onclick=()=>{const item=selectedPhotoObject();if(!item)return toast('Select an image first.');if(typeof openMaterialPicker!=='function')return toast('Material picker is unavailable.');openMaterialPicker('Replace selected image',(url,asset)=>{if(!item.dataset.originalSrc)item.dataset.originalSrc=item.querySelector('img')?.src||'';syncSelectedImageSrc(url);item.dataset.alt=asset?.name||item.dataset.alt||'Invitation image';const img=item.querySelector('img');if(img)img.alt=item.dataset.alt;saveNow();toast('Image replaced.');});};
    const photoObserver=new MutationObserver(syncPhotoControls);photoObserver.observe(stage,{subtree:true,attributes:true,attributeFilter:['class','data-image-hue']});document.addEventListener('pointerup',()=>setTimeout(syncPhotoControls,0),true);syncPhotoControls();
  }

  const elementsPane=$('[data-studio-pane="elements"]');
  if(elementsPane && !$('#canvasExtraElements')){
    const section=document.createElement('section');section.className='canvas-extra-elements';section.id='canvasExtraElements';
    const items=[['✧','Fine sparkle'],['✦','Four-point star'],['✺','Ceremonial sun'],['❦','Flourish'],['❧','Leaf flourish'],['✿','Flower'],['❀','Bloom'],['♡','Outline heart'],['♥','Heart'],['∞','Forever'],['♛','Crown'],['◇','Diamond'],['◈','Gem'],['— ✦ —','Divider'],['I · II · III','Roman divider'],['“','Quote'],['◯◯','Rings'],['☾','Moon'],['☼','Sun'],['✾','Lotus mark'],['⌁','Wave'],['×','Minimal cross'],['+','Minimal plus'],['•','Editorial dot']];
    section.innerHTML=`<div class="final-panel-title"><div><small>More assets</small><h2>Invitation symbols</h2></div><span class="final-beta">${items.length}</span></div><div class="canvas-extra-grid"></div>`;
    const grid=$('.canvas-extra-grid',section);
    const addGlyph=(glyph,name)=>{try{const id='symbol-'+Date.now()+'-'+Math.random().toString(36).slice(2,6),obj=createObject(id,'decoration'),content=obj.querySelector('.content');content.textContent=glyph;obj.dataset.fontSize=glyph.length>4?'30':'64';obj.dataset.color=$('#accent')?.value||'#9d4555';obj.style.left='34%';obj.style.top='38%';obj.style.width=glyph.length>4?'190px':'130px';obj.style.height='110px';stage.append(obj);clearSelection();setSelection([obj]);applyItems([obj]);saveNow();toast(`${name} added.`)}catch{}};
    items.forEach(([glyph,name])=>{const b=document.createElement('button');b.type='button';b.innerHTML=`<span>${glyph}</span><small>${name}</small>`;b.onclick=()=>addGlyph(glyph,name);grid.append(b)});
    elementsPane.append(section);
  }

  // Direct inline text editing: double-click a text object and type on the canvas.
  stage.addEventListener('dblclick',e=>{
    const object=e.target.closest('.text-object,.decoration-object');if(!object)return;const content=object.querySelector('.content');if(!content)return;
    e.preventDefault();e.stopPropagation();setSelectionIfNeeded(object);content.contentEditable='true';content.spellcheck=true;content.classList.add('canvas-inline-editing');content.focus();
    const range=document.createRange();range.selectNodeContents(content);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
    const finish=()=>{content.contentEditable='false';content.classList.remove('canvas-inline-editing');content.removeEventListener('blur',finish);if(window.EInviteRenderer?.sanitizeRichText)content.innerHTML=window.EInviteRenderer.sanitizeRichText(content.innerHTML);saveNow();};
    content.addEventListener('blur',finish);
    content.addEventListener('keydown',function keyHandler(ev){if(ev.key==='Escape'){ev.preventDefault();content.blur();content.removeEventListener('keydown',keyHandler)}if((ev.metaKey||ev.ctrlKey)&&ev.key==='Enter'){ev.preventDefault();content.blur();content.removeEventListener('keydown',keyHandler)}});
  },true);

  const addTextObject=()=>{
    try{
      if(typeof createObject!=="function") return;
      const id="text-"+Date.now()+"-"+Math.random().toString(36).slice(2,7);
      const obj=createObject(id,"text");
      const content=obj.querySelector(".content"); if(content) content.textContent="New text";
      obj.style.left="16%"; obj.style.top="18%"; obj.style.width="52%"; obj.style.height="110px";
      obj.dataset.fontSize="34"; obj.dataset.color=window.state?.accent||"#9d4555";
      stage.append(obj);
      try{typeof clearSelection==="function"&&clearSelection(); typeof setSelection==="function"&&setSelection([obj]);}catch{}
      applyItems([obj]); saveNow();
    }catch{}
  };

  // Keyboard commands are owned by editor-command-system.js.

  // Alt-drag duplicate
  let dragState=null;
  stage.addEventListener('pointerdown',e=>{
    if(e.button!==0 || !e.altKey) return;
    const obj=e.target.closest('.object'); if(!obj || obj.dataset.locked==='true') return;
    if(e.target.closest('.resize-handle') || e.target.closest('.rotate-handle')) return;
    setSelectionIfNeeded(obj);
    e.preventDefault(); e.stopPropagation();
    try{ typeof duplicateSelection==='function' && duplicateSelection(); }catch{}
    const items=activeObjects(); if(!items.length) return;
    const srect=stage.getBoundingClientRect();
    dragState={pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,srect,items,frames:new Map(items.map(item=>{const rect=item.getBoundingClientRect();return[item,{left:parseFloat(item.style.left)||((rect.left-srect.left)/srect.width*100),top:parseFloat(item.style.top)||((rect.top-srect.top)/srect.height*100),width:rect.width/srect.width*100,height:rect.height/srect.height*100}] }))};
    obj.setPointerCapture?.(e.pointerId);
  },true);
  const moveAltDrag=(e)=>{
    if(!dragState || dragState.pointerId!==e.pointerId) return;
    e.preventDefault();
    const dx=(e.clientX-dragState.startX)/dragState.srect.width*100, dy=(e.clientY-dragState.startY)/dragState.srect.height*100;
    dragState.items.forEach(item=>{const f=dragState.frames.get(item); item.style.left=`${Math.max(0,Math.min(100-f.width, f.left+dx))}%`; item.style.top=`${Math.max(0,Math.min(100-f.height, f.top+dy))}%`;});
    try{ typeof updateSelectionBounds==='function'&&updateSelectionBounds(); }catch{}
  };
  let altDragBatcher=null;
  stage.addEventListener('pointermove',e=>{if(!dragState||dragState.pointerId!==e.pointerId)return;e.preventDefault();altDragBatcher??=window.EInviteMotion.createFrameBatcher((a,b)=>b,moveAltDrag);altDragBatcher.accumulate(e)},true);
  const endAltDrag=(e)=>{ if(!dragState || dragState.pointerId!==e.pointerId) return; altDragBatcher?.flush();saveNow(); dragState=null; };
  stage.addEventListener('pointerup',endAltDrag,true); stage.addEventListener('pointercancel',()=>{altDragBatcher?.flush();dragState=null},true);
}

wireAuthLayouts();
enhanceMaterialsPage();
editorEnhancements();
})();

/* ===== editor-builders.js ===== */
(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!$('#stage')) return;
const dispatchInput=el=>{el.dispatchEvent(new Event('input',{bubbles:true}))};
const safe=(v='')=>String(v);
const makeButton=(text,title)=>{const b=document.createElement('button');b.type='button';b.textContent=text;b.title=title||text;return b};
const raw={section:$('#sectionOrder'),schedule:$('#scheduleText'),scheduleKm:$('#scheduleTextKm'),venues:$('#venuesText'),venuesKm:$('#venuesTextKm')};
Object.values(raw).forEach(el=>el?.closest('label')?.classList.add('ei-raw-field'));

function parseSchedule(){
  const en=(raw.schedule?.value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{const [time,...rest]=line.split('|');return{time:(time||'').trim(),title:rest.join('|').trim()}});
  const km=(raw.scheduleKm?.value||'').split(/\r?\n/).map(x=>x.trim()).map(line=>{const [time,...rest]=line.split('|');return{time:(time||'').trim(),titleKm:rest.join('|').trim()}});
  return en.map((x,i)=>({...x,titleKm:km[i]?.titleKm||''}));
}
function writeSchedule(items){
  raw.schedule.value=items.map(x=>`${safe(x.time)} | ${safe(x.title)}`).join('\n');
  raw.scheduleKm.value=items.map(x=>`${safe(x.time)} | ${safe(x.titleKm)}`).join('\n');
  dispatchInput(raw.schedule);
}
function parseVenues(){
  const en=(raw.venues?.value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{const parts=line.split('|').map(x=>x.trim());return{name:parts[0]||'',address:parts[1]||'',mapUrl:parts.slice(2).join('|').trim()}});
  const km=(raw.venuesKm?.value||'').split(/\r?\n/).map(x=>x.trim()).map(line=>{const parts=line.split('|').map(x=>x.trim());return{nameKm:parts[0]||'',addressKm:parts.slice(1).join('|').trim()}});
  return en.map((x,i)=>({...x,nameKm:km[i]?.nameKm||'',addressKm:km[i]?.addressKm||''}));
}
function writeVenues(items){
  raw.venues.value=items.map(x=>`${safe(x.name)} | ${safe(x.address)} | ${safe(x.mapUrl)}`).join('\n');
  raw.venuesKm.value=items.map(x=>`${safe(x.nameKm)} | ${safe(x.addressKm)}`).join('\n');
  dispatchInput(raw.venues);
}
function parseSections(){return(raw.section?.value||'').split(/\r?\n|,/).map(x=>x.trim()).filter(Boolean)}
function writeSections(items){raw.section.value=items.join('\n');dispatchInput(raw.section)}

function builderShell(title,description,addLabel){const host=document.createElement('section');host.className='ei-builder';host.innerHTML=`<div class="ei-builder-head"><div><h3>${title}</h3><p>${description}</p></div></div><div class="ei-builder-list"></div>`;if(addLabel){const add=makeButton(`+ ${addLabel}`);host.querySelector('.ei-builder-head').append(add);host.addButton=add}return host}

const scheduleHost=builderShell('Schedule builder','Add, edit, and reorder event timeline items visually.','Add item');scheduleHost.classList.add('ei-schedule-builder');scheduleHost.dataset.scheduleBuilder='';
raw.schedule?.closest('label')?.parentNode?.insertBefore(scheduleHost,raw.schedule.closest('label').nextSibling);
function renderSchedule(){
  let items=parseSchedule();const list=$('.ei-builder-list',scheduleHost);list.textContent='';
  if(!items.length){const empty=document.createElement('div');empty.className='ei-builder-empty';empty.textContent='No schedule items yet.';list.append(empty)}
  items.forEach((item,index)=>{
    const card=document.createElement('article');card.className='ei-builder-card';card.draggable=true;card.dataset.index=index;
    card.innerHTML=`<div class="ei-builder-row"><button type="button" class="ei-builder-handle" title="Drag to reorder">⋮⋮</button><strong>Schedule item ${index+1}</strong><div class="ei-builder-actions"></div></div><div class="ei-builder-grid"><label>Time<input data-key="time" value=""></label><label>English title<input data-key="title" value=""></label></div><div class="ei-builder-grid"><label>Khmer time<input data-key="timeKm" value=""></label><label>Khmer title<input class="khmer-input" data-key="titleKm" value=""></label></div>`;
    card.querySelector('[data-key="time"]').value=item.time||'';card.querySelector('[data-key="timeKm"]').value=item.time||'';card.querySelector('[data-key="title"]').value=item.title||'';card.querySelector('[data-key="titleKm"]').value=item.titleKm||'';
    const actions=$('.ei-builder-actions',card),up=makeButton('↑','Move earlier'),down=makeButton('↓','Move later'),del=makeButton('×','Remove');del.className='danger';actions.append(up,down,del);
    const sync=()=>{const next=parseSchedule();next[index]={time:card.querySelector('[data-key="time"]').value.trim()||card.querySelector('[data-key="timeKm"]').value.trim(),title:card.querySelector('[data-key="title"]').value,titleKm:card.querySelector('[data-key="titleKm"]').value};writeSchedule(next)};
    card.querySelectorAll('input').forEach(input=>input.addEventListener('input',()=>{if(input.dataset.key==='time')card.querySelector('[data-key="timeKm"]').value=input.value;sync()}));
    up.onclick=()=>{const next=parseSchedule();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeSchedule(next);renderSchedule()};
    down.onclick=()=>{const next=parseSchedule();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeSchedule(next);renderSchedule()};
    del.onclick=async()=>{if(!(await uiConfirm('Remove this schedule item?',{title:'Remove schedule item',danger:true,confirmText:'Remove'})))return;const next=parseSchedule();next.splice(index,1);writeSchedule(next);renderSchedule()};
    card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',String(index));e.dataTransfer.effectAllowed='move'});card.addEventListener('dragend',()=>card.classList.remove('dragging'));card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const from=Number(e.dataTransfer.getData('text/plain')),to=index;if(!Number.isInteger(from)||from===to)return;const next=parseSchedule(),[moved]=next.splice(from,1);next.splice(to,0,moved);writeSchedule(next);renderSchedule()});
    list.append(card)
  })
}
scheduleHost.addButton.onclick=()=>{const items=parseSchedule();items.push({time:'',title:'',titleKm:''});writeSchedule(items);renderSchedule();setTimeout(()=>scheduleHost.querySelector('.ei-builder-card:last-child input')?.focus(),0)};

const venueHost=builderShell('Additional venue builder','Create multiple named locations with bilingual details and map links.','Add venue');venueHost.classList.add('ei-venue-builder');venueHost.dataset.venueBuilder='';
raw.venues?.closest('label')?.parentNode?.insertBefore(venueHost,raw.venues.closest('label').nextSibling);
function renderVenues(){
  const items=parseVenues(),list=$('.ei-builder-list',venueHost);list.textContent='';
  if(!items.length){const empty=document.createElement('div');empty.className='ei-builder-empty';empty.textContent='No additional venues. The primary venue above is still used.';list.append(empty)}
  items.forEach((item,index)=>{
    const card=document.createElement('article');card.className='ei-builder-card';card.draggable=true;card.innerHTML=`<div class="ei-builder-row"><button type="button" class="ei-builder-handle" title="Drag to reorder">⋮⋮</button><strong>Venue ${index+1}</strong><div class="ei-builder-actions"></div></div><div class="ei-builder-grid"><label>English name<input data-key="name"></label><label>English address<input data-key="address"></label></div><div class="ei-builder-grid"><label>Khmer name<input class="khmer-input" data-key="nameKm"></label><label>Khmer address<input class="khmer-input" data-key="addressKm"></label></div><div class="ei-builder-grid"><label>Map URL<input data-key="mapUrl" type="url" placeholder="https://maps.google.com/..."></label><span></span></div>`;
    ['name','address','nameKm','addressKm','mapUrl'].forEach(key=>card.querySelector(`[data-key="${key}"]`).value=item[key]||'');
    const actions=$('.ei-builder-actions',card),up=makeButton('↑','Move earlier'),down=makeButton('↓','Move later'),del=makeButton('×','Remove');del.className='danger';actions.append(up,down,del);
    card.querySelectorAll('input').forEach(input=>input.addEventListener('input',()=>{const next=parseVenues();const current=next[index]||{};['name','address','nameKm','addressKm','mapUrl'].forEach(key=>current[key]=card.querySelector(`[data-key="${key}"]`).value);next[index]=current;writeVenues(next)}));
    up.onclick=()=>{const next=parseVenues();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeVenues(next);renderVenues()};down.onclick=()=>{const next=parseVenues();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeVenues(next);renderVenues()};del.onclick=async()=>{if(!(await uiConfirm('Remove this additional venue?',{title:'Remove venue',danger:true,confirmText:'Remove'})))return;const next=parseVenues();next.splice(index,1);writeVenues(next);renderVenues()};
    card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',String(index))});card.addEventListener('dragend',()=>card.classList.remove('dragging'));card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const from=Number(e.dataTransfer.getData('text/plain')),to=index;if(!Number.isInteger(from)||from===to)return;const next=parseVenues(),[moved]=next.splice(from,1);next.splice(to,0,moved);writeVenues(next);renderVenues()});list.append(card)
  })
}
venueHost.addButton.onclick=()=>{const items=parseVenues();items.push({name:'',address:'',mapUrl:'',nameKm:'',addressKm:''});writeVenues(items);renderVenues();setTimeout(()=>venueHost.querySelector('.ei-builder-card:last-child input')?.focus(),0)};

const sectionLabels={gallery:['▦','Gallery'],video:['▶','Featured video'],countdown:['◷','Countdown'],schedule:['≡','Schedule'],custom:['◇','Custom blocks'],venue:['⌖','Venue'],contact:['☎','Contact'],wishes:['♡','Guest wishes'],rsvp:['✓','RSVP']};
const sectionHost=builderShell('Guest-page structure','Drag functional sections and visual pages into the exact published order.');sectionHost.classList.add('ei-section-order-builder');sectionHost.dataset.sectionOrderBuilder='';
raw.section?.closest('label')?.parentNode?.insertBefore(sectionHost,raw.section.closest('label').nextSibling);
function labelForToken(token){if(sectionLabels[token])return{icon:sectionLabels[token][0],label:sectionLabels[token][1],detail:'Functional section'};if(token.startsWith('page:')){const id=token.slice(5),page=(window.state?.designPages||[]).find(x=>x.id===id);return{icon:'▣',label:page?.name||'Visual page',detail:'Free-form visual page'}}return{icon:'•',label:token,detail:'Section'}}
function renderSections(){const items=parseSections(),list=$('.ei-builder-list',sectionHost);list.textContent='';items.forEach((token,index)=>{const meta=labelForToken(token),card=document.createElement('article');card.className='ei-builder-card ei-builder-section-card';card.draggable=true;card.innerHTML=`<button type="button" class="ei-builder-handle" title="Drag to reorder">⋮⋮</button><div class="ei-section-token"><span class="ei-section-icon"></span><div><strong></strong><small></small></div></div><div class="ei-builder-actions"></div>`;card.querySelector('.ei-section-icon').textContent=meta.icon;card.querySelector('strong').textContent=meta.label;card.querySelector('small').textContent=meta.detail;const actions=$('.ei-builder-actions',card),up=makeButton('↑','Move earlier'),down=makeButton('↓','Move later');actions.append(up,down);up.onclick=()=>{const next=parseSections();if(index<=0)return;[next[index-1],next[index]]=[next[index],next[index-1]];writeSections(next);renderSections()};down.onclick=()=>{const next=parseSections();if(index>=next.length-1)return;[next[index+1],next[index]]=[next[index],next[index+1]];writeSections(next);renderSections()};card.addEventListener('dragstart',e=>{card.classList.add('dragging');e.dataTransfer.setData('text/plain',String(index))});card.addEventListener('dragend',()=>card.classList.remove('dragging'));card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drag-over')});card.addEventListener('dragleave',()=>card.classList.remove('drag-over'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drag-over');const from=Number(e.dataTransfer.getData('text/plain')),to=index;if(!Number.isInteger(from)||from===to)return;const next=parseSections(),[moved]=next.splice(from,1);next.splice(to,0,moved);writeSections(next);renderSections()});list.append(card)})}

function refreshAll(){renderSchedule();renderVenues();renderSections()}
window.addEventListener('einvite:state-applied',refreshAll);window.addEventListener('einvite:structure-changed',refreshAll);
let lastSnapshot='';const structureTimer=setInterval(()=>{const snapshot=[raw.section?.value,raw.schedule?.value,raw.scheduleKm?.value,raw.venues?.value,raw.venuesKm?.value].join('\u0001');if(snapshot!==lastSnapshot){lastSnapshot=snapshot;refreshAll()}},700);window.EInviteLifecycle?.add?.(()=>clearInterval(structureTimer));
refreshAll();
})();

/* ===== editor-pro.js ===== */
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
let viewRect=null,stageSize={width:390,height:844},viewportSize={width:0,height:0,left:0,top:0},tweenFrame=0,gestureCount=0,fitSettleToken=0,fitActive=false;
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
 // Any non-fit view change cancels an in-flight fit settle loop; otherwise the
 // loop keeps re-centring and swallows the user's pan/zoom (canvas P5: a middle
 // drag moved +25/+15 and the settle pulled it back to the fitted origin).
 if(source!=='fit'){fitSettleToken++;fitActive=false}
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
function fitView(){
 // Fit = scale the artboard into the viewport AND centre it. The transform layer
 // is anchored off #canvasFrame, whose box is zero-width and shifts between the
 // boot layout and the final mobile layout, so the analytic translate is only an
 // approximation: once the tween has finished, measure the rendered stage and
 // correct the residual once (rAF loop, waits out any in-flight tween/relayout).
 // The 0.35 floor left the artboard taller than a 320x568 canvas viewport (fit asked
 // for 0.258 and got 0.35, so 7 px of the stage sat outside the scroller and the
 // FB-38 artboard check failed at 320). Fit may shrink to 0.25; the user-facing zoom
 // control keeps its own clamp.
 // FB-47: phones fit inside the viewport's real content box, whose padding already
 // reserves the toolbar, the palette and the zoom HUD. Wider layouts keep the
 // pre-FB-47 70px mat so the desktop framing does not change.
 const fitFrame=()=>{
  cacheViewGeometry();
  if(!matchMedia('(max-width:700px)').matches)return{left:35,top:35,width:Math.max(0,viewport.clientWidth-70),height:Math.max(0,viewport.clientHeight-70)};
  const css=getComputedStyle(viewport),px=value=>parseFloat(value)||0;
  const padL=px(css.paddingLeft),padR=px(css.paddingRight),padT=px(css.paddingTop),padB=px(css.paddingBottom);
  return{left:padL,top:padT,width:Math.max(0,viewport.clientWidth-padL-padR),height:Math.max(0,viewport.clientHeight-padT-padB)}
 };
 const computeFit=()=>{
  const frame=fitFrame();
  const zoom=Math.max(.08,Math.min(1,frame.width/stageSize.width,frame.height/stageSize.height));
  return{zoom,x:(viewport.clientLeft||0)+frame.left+(frame.width-stageSize.width*zoom)/2+viewport.scrollLeft,y:(viewport.clientTop||0)+frame.top+(frame.height-stageSize.height*zoom)/2+viewport.scrollTop}
 };fitActive=true;const token=++fitSettleToken;const applied=setView(computeFit(),{source:'fit',animate:true});const deadline=performance.now()+3000;let stable=0,last='',rounds=0;const settle=()=>{if(token!==fitSettleToken||performance.now()>deadline)return;if(tweenFrame){stable=0;last='';requestAnimationFrame(settle);return}const sr=stage.getBoundingClientRect(),cur=`${sr.left},${sr.top},${sr.width}`;if(cur!==last){stable=0;last=cur;requestAnimationFrame(settle);return}if(++stable<3){requestAnimationFrame(settle);return}const vr=viewport.getBoundingClientRect(),frame=fitFrame(),dx=(vr.left+(viewport.clientLeft||0)+frame.left+frame.width/2)-(sr.left+sr.width/2),dy=(vr.top+(viewport.clientTop||0)+frame.top+frame.height/2)-(sr.top+sr.height/2);rounds++;if(rounds>3)return;const fit=computeFit();if(Math.abs(fit.zoom-view.zoom)>.01){stable=0;last='';setView(fit,{source:'fit'});requestAnimationFrame(settle);return}if(Math.abs(dx)>1||Math.abs(dy)>1){stable=0;last='';setView({x:view.x+dx,y:view.y+dy},{source:'fit'});requestAnimationFrame(settle)}};requestAnimationFrame(settle);return applied}
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
 const ro=new ResizeObserver(()=>{if(gestureCount)return;if(fitActive&&matchMedia('(max-width:700px)').matches)fitView();else refreshView()});ro.observe(stage);ro.observe(viewport);window.EInviteLifecycle?.add?.(()=>{ro.disconnect();stopTween();sliderBatcher.destroy()});refreshView();
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

/* ===== photo-editor.js ===== */
(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];if(!$('#stage'))return;
const selectedImage=()=>$$('.object.selected,.object.multi-selected').find(x=>x.dataset.objectType==='image')||null;const clamp=(v,a,b)=>Math.max(a,Math.min(b,Number(v)));
const dialog=document.createElement('dialog');dialog.className='ei-photo-dialog';dialog.innerHTML=`<div class="ei-photo-shell"><div class="ei-photo-stage"><span class="ei-photo-before">Edited preview</span><img alt="Photo edit preview"></div><aside class="ei-photo-panel"><div class="ei-photo-head"><h2>Edit photo</h2><button type="button" data-close aria-label="Close photo editor">×</button></div><div class="ei-photo-controls"><fieldset><legend>Quick looks</legend><div class="ei-photo-presets"><button data-preset="original">Original</button><button data-preset="portrait">Portrait</button><button data-preset="vivid">Vivid</button><button data-preset="warm">Warm</button><button data-preset="mono">B&W</button><button data-preset="soft">Soft</button></div></fieldset><fieldset><legend>Adjust</legend><div data-sliders></div></fieldset><fieldset><legend>Transform</legend><div class="ei-photo-tools"><button data-tool="rotate-left">↶ Rotate</button><button data-tool="rotate-right">↷ Rotate</button><button data-tool="flip-x">↔ Flip H</button><button data-tool="flip-y">↕ Flip V</button><button data-tool="remove-bg">✦ Remove BG</button><button data-tool="replace">▣ Replace</button></div></fieldset><fieldset><legend>Crop & frame</legend><div class="ei-photo-selects"><label>Fit<select data-select="imageFit"><option value="cover">Crop to fill</option><option value="contain">Show full image</option></select></label><label>Mask<select data-select="imageMask"><option value="none">None</option><option value="circle">Circle</option><option value="arch">Arch</option><option value="diamond">Diamond</option><option value="hexagon">Hexagon</option><option value="blob">Blob</option></select></label><label>Frame<select data-select="imageFrame"><option value="none">None</option><option value="white">White</option><option value="gold">Gold</option><option value="dark">Dark</option></select></label></div></fieldset></div><div class="ei-photo-footer"><button type="button" data-revert>Revert session</button><button type="button" data-close class="primary">Done</button></div></aside></div>`;document.body.append(dialog);
const sliderDefs=[['imageBrightness','Brightness',20,200,100,'%'],['imageContrast','Contrast',20,200,100,'%'],['imageSaturation','Saturation',0,250,100,'%'],['imageHue','Hue',-180,180,0,'°'],['imageSepia','Warmth',0,100,0,'%'],['imageGrayscale','Grayscale',0,100,0,'%'],['imageBlur','Blur',0,20,0,'px']];const sliders=$('[data-sliders]',dialog);sliderDefs.forEach(([key,label,min,max,def,suffix])=>{const row=document.createElement('div');row.className='ei-photo-slider';row.innerHTML=`<label>${label}</label><input type="range" min="${min}" max="${max}" step="${key==='imageBlur'?'.1':'1'}" data-key="${key}"><output></output>`;row.dataset.suffix=suffix;sliders.append(row)});
let item=null,snapshot=null;const preview=$('.ei-photo-stage img',dialog);
function filter(o){return`brightness(${clamp(o.imageBrightness||100,20,200)}%) contrast(${clamp(o.imageContrast||100,20,200)}%) saturate(${clamp(o.imageSaturation||100,0,250)}%) grayscale(${clamp(o.imageGrayscale||0,0,100)}%) sepia(${clamp(o.imageSepia||0,0,100)}%) hue-rotate(${clamp(o.imageHue||0,-180,180)}deg) blur(${clamp(o.imageBlur||0,0,20)}px)`}
function apply(){if(!item)return;const img=item.querySelector('img');if(img){img.style.filter=filter(item.dataset);img.style.transform=`scaleX(${item.dataset.imageFlipX==='true'?-1:1}) scaleY(${item.dataset.imageFlipY==='true'?-1:1})`}try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(item);typeof refreshSelectionUI==='function'&&refreshSelectionUI();typeof save==='function'&&save()}catch{}syncPreview()}
function syncPreview(){if(!item)return;const img=item.querySelector('img');preview.src=img?.src||'';preview.style.filter=filter(item.dataset);preview.style.transform=`rotate(${Number(item.dataset.rotation||0)}deg) scaleX(${item.dataset.imageFlipX==='true'?-1:1}) scaleY(${item.dataset.imageFlipY==='true'?-1:1})`;preview.style.objectFit=item.dataset.imageFit||'cover';sliderDefs.forEach(([key,,min,max,def])=>{const input=dialog.querySelector(`[data-key="${key}"]`);input.value=String(item.dataset[key]??def);input.closest('.ei-photo-slider').querySelector('output').textContent=`${input.value}${input.closest('.ei-photo-slider').dataset.suffix}`});$$('[data-select]',dialog).forEach(sel=>sel.value=item.dataset[sel.dataset.select]||'none')}
function open(){item=selectedImage();if(!item){window.uiToast?.('Select one image first.','!');return}snapshot={...item.dataset,src:item.querySelector('img')?.src||''};syncPreview();dialog.showModal()}
const imageControls=$('#imageControls');if(imageControls&&!$('#openPhotoEditor')){const b=document.createElement('button');b.id='openPhotoEditor';b.type='button';b.className='primary';b.textContent='Edit photo';imageControls.prepend(b);b.onclick=open}window.openEInvitePhotoEditor=open;
const sliderBatcher=window.EInviteMotion.createFrameBatcher((a,b)=>({...a,...b}),values=>{if(!item)return;Object.entries(values).forEach(([key,value])=>{item.dataset[key]=value});apply()});
sliders.addEventListener('input',e=>{const input=e.target.closest('[data-key]');if(!input||!item)return;sliderBatcher.accumulate({[input.dataset.key]:input.value})});
sliders.addEventListener('change',()=>sliderBatcher.flush());
sliders.addEventListener('pointerup',()=>sliderBatcher.flush());
dialog.addEventListener('close',()=>sliderBatcher.flush());
window.EInviteLifecycle?.add?.(()=>sliderBatcher.destroy());
$$('[data-select]',dialog).forEach(sel=>sel.onchange=()=>{if(!item)return;item.dataset[sel.dataset.select]=sel.value;apply()});
const presets={original:{imageBrightness:100,imageContrast:100,imageSaturation:100,imageHue:0,imageSepia:0,imageGrayscale:0,imageBlur:0},portrait:{imageBrightness:105,imageContrast:102,imageSaturation:107,imageHue:0,imageSepia:5,imageGrayscale:0,imageBlur:.3},vivid:{imageBrightness:104,imageContrast:118,imageSaturation:135,imageHue:0,imageSepia:0,imageGrayscale:0,imageBlur:0},warm:{imageBrightness:104,imageContrast:106,imageSaturation:112,imageHue:0,imageSepia:24,imageGrayscale:0,imageBlur:0},mono:{imageBrightness:104,imageContrast:116,imageSaturation:100,imageHue:0,imageSepia:0,imageGrayscale:100,imageBlur:0},soft:{imageBrightness:108,imageContrast:92,imageSaturation:93,imageHue:0,imageSepia:7,imageGrayscale:0,imageBlur:.6}};
dialog.addEventListener('click',e=>{const p=e.target.closest('[data-preset]');if(p&&item){Object.entries(presets[p.dataset.preset]).forEach(([k,v])=>item.dataset[k]=String(v));apply()}const tool=e.target.closest('[data-tool]');if(tool&&item){const action=tool.dataset.tool;if(action==='rotate-left'||action==='rotate-right'){item.dataset.rotation=String((Number(item.dataset.rotation||0)+(action==='rotate-left'?-90:90)+360)%360)}if(action==='flip-x')item.dataset.imageFlipX=item.dataset.imageFlipX==='true'?'false':'true';if(action==='flip-y')item.dataset.imageFlipY=item.dataset.imageFlipY==='true'?'false':'true';if(action==='remove-bg')$('#aiBgCut')?.click();if(action==='replace')$('#aiReplaceImage')?.click();apply()}});
dialog.querySelector('[data-revert]').onclick=()=>{if(!item||!snapshot)return;Object.keys(item.dataset).forEach(k=>{if(!(k in snapshot))delete item.dataset[k]});Object.entries(snapshot).forEach(([k,v])=>item.dataset[k]=v);const img=item.querySelector('img');if(img)img.src=snapshot.src;apply()};$$('[data-close]',dialog).forEach(b=>b.onclick=()=>dialog.close());
})();

/* ===== creative-packs.js ===== */
(()=>{'use strict';const $=(s,r=document)=>r.querySelector(s);if(!$('#stage'))return;const pane=document.querySelector('[data-studio-pane="elements"]');if(!pane)return;
const packs=[
 {name:'Khmer Ceremony',desc:'Gold ceremonial title, dividers and lotus marks.',preview:'✾  ◇  ✾',items:[['text','សិរីមង្គលអាពាហ៍ពិពាហ៍',{font:"noto-serif-khmer",fontSize:34,color:'#a87616',top:12,left:10,width:80}],['decoration','✾',{fontSize:58,color:'#a87616',top:35,left:15,width:18}],['decoration','◇',{fontSize:52,color:'#a87616',top:36,left:41,width:18}],['decoration','✾',{fontSize:58,color:'#a87616',top:35,left:67,width:18}]]},
 {name:'Botanical Header',desc:'Soft leaf ornaments with an editorial heading.',preview:'❧  A  ❧',items:[['decoration','❧',{fontSize:62,color:'#477a64',top:14,left:8,width:18,rotation:-16}],['text','OUR CELEBRATION',{font:'serif-georgia',fontSize:32,color:'#335a4a',top:18,left:24,width:52,letterSpacing:3}],['decoration','❧',{fontSize:62,color:'#477a64',top:14,left:74,width:18,rotation:16}]]},
 {name:'Luxury Divider',desc:'Gold divider for elegant wedding and gala pages.',preview:'— ✦ —',items:[['shape','line',{fillColor:'#c6a35b',top:48,left:16,width:25,height:1}],['decoration','✦',{fontSize:38,color:'#c6a35b',top:44,left:44,width:12}],['shape','line',{fillColor:'#c6a35b',top:48,left:59,width:25,height:1}]]},
 {name:'Photo Caption',desc:'Framed photo placeholder with a refined caption.',preview:'▣  Aa',items:[['shape','rectangle',{fillColor:'#f3eee7',top:18,left:10,width:80,height:55,borderRadius:20}],['text','A MOMENT TO REMEMBER',{font:'serif-georgia',fontSize:24,color:'#563b42',top:77,left:15,width:70,letterSpacing:2}]]},
 {name:'Birthday Spark',desc:'Colorful title and celebratory sparkle cluster.',preview:'✦ 🎉 ✦',items:[['decoration','✦',{fontSize:48,color:'#ff5e91',top:14,left:15,width:15}],['text','LET’S CELEBRATE',{font:'sans-arial',fontSize:38,color:'#6842b8',top:18,left:22,width:60,fontWeight:'700'}],['decoration','✦',{fontSize:48,color:'#33c7d8',top:14,left:72,width:15}]]},
 {name:'Executive Label',desc:'Modern business event heading with accent rule.',preview:'▌ EVENT',items:[['shape','rectangle',{fillColor:'#1d4f6e',top:20,left:10,width:2,height:15}],['text','EVENT HIGHLIGHT',{font:'sans-arial',fontSize:28,color:'#1d3446',top:20,left:16,width:68,fontWeight:'700',letterSpacing:1.5}]]}
];
const section=document.createElement('section');section.className='ei-pack-panel';section.innerHTML='<div class="final-panel-title"><div><small>Ready-made compositions</small><h2>Invitation packs</h2></div></div><div class="ei-pack-grid"></div>';pane.append(section);const grid=$('.ei-pack-grid',section);
function make(kind,content,opt,index){const id=`pack-${Date.now()}-${index}-${Math.random().toString(36).slice(2,5)}`;let type=kind;if(kind==='shape')type='shape';if(typeof createObject!=='function')return null;const obj=createObject(id,type);if(type==='text'||type==='decoration'){obj.querySelector('.content').textContent=content;obj.dataset.font=opt.font||'serif-georgia';obj.dataset.fontSize=String(opt.fontSize||32);obj.dataset.color=opt.color||'#7b4555';obj.dataset.fontWeight=opt.fontWeight||'400';obj.dataset.letterSpacing=String(opt.letterSpacing||0)}else{obj.dataset.shapeKind=content;obj.dataset.fillColor=opt.fillColor||'#d9a6ad';obj.dataset.borderRadius=String(opt.borderRadius||0)}obj.style.left=`${opt.left||10}%`;obj.style.top=`${opt.top||10}%`;obj.style.width=`${opt.width||50}%`;obj.style.height=type==='shape'?`${opt.height||12}%`:`${opt.height||12}%`;obj.dataset.rotation=String(opt.rotation||0);obj.style.zIndex=String((typeof nextZIndex==='function'?nextZIndex():10)+index);applyObjectVisualStyle(obj);return obj}
packs.forEach(pack=>{const b=document.createElement('button');b.type='button';b.className='ei-pack-card';b.innerHTML=`<div class="preview">${pack.preview}</div><strong>${pack.name}</strong><small>${pack.desc}</small>`;b.onclick=()=>{try{capture()}catch{}const created=pack.items.map((it,i)=>make(it[0],it[1],it[2],i)).filter(Boolean);created.forEach(x=>$('#stage').append(x));try{clearSelection();setSelection(created);save()}catch{}window.uiToast?.(`${pack.name} added`,'✦')};grid.append(b)});
})();;(()=>{
'use strict';
if(window.EInviteAIActionService)return;
const VERSION='27.3.5';
const bridge=()=>window.EInviteEditorBridge;
const clone=value=>{try{return structuredClone(value)}catch{return JSON.parse(JSON.stringify(value))}};
const own=(object,key)=>Object.prototype.hasOwnProperty.call(object,key);
const clean=(value,max=50000)=>String(value??'').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u202a-\u202e\u2066-\u2069\ufeff]/g,'').slice(0,max);
const bounded=(value,min,max,fallback)=>{const number=Number(value);return Number.isFinite(number)?Math.max(min,Math.min(max,number)):fallback};
const allowedTypes=new Set(['text','decoration','image','shape']);
const photoKeys=['imageBrightness','imageContrast','imageSaturation','imageVibrance','imageTemperature','imageGamma','imageCurveShadows','imageCurveHighlights','imageGrayscale','imageSepia','imageBlur','imageSharpen','imageHue','imageFlipX','imageFlipY'];
const paletteKeys=['background','heading','accent','text'];
const PHOTO_PRESETS={
 natural:{imageBrightness:100,imageContrast:100,imageSaturation:100,imageVibrance:0,imageTemperature:0,imageGamma:1,imageGrayscale:0,imageSepia:0,imageBlur:0,imageSharpen:0,imageHue:0},
 enhance:{imageBrightness:104,imageContrast:108,imageSaturation:106,imageVibrance:14,imageTemperature:2,imageGamma:1,imageGrayscale:0,imageSepia:0,imageBlur:0,imageSharpen:12,imageHue:0},
 portrait:{imageBrightness:103,imageContrast:96,imageSaturation:96,imageVibrance:8,imageTemperature:5,imageGamma:1.02,imageGrayscale:0,imageSepia:0,imageBlur:.2,imageSharpen:4,imageHue:0},
 monochrome:{imageBrightness:102,imageContrast:112,imageSaturation:0,imageVibrance:0,imageTemperature:0,imageGamma:1,imageGrayscale:100,imageSepia:0,imageBlur:0,imageSharpen:8,imageHue:0}
};
function canonical(value){
 if(Array.isArray(value))return value.map(canonical);
 if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().filter(key=>!['updatedAt','generatedAt','selectionIds'].includes(key)).map(key=>[key,canonical(value[key])]));
 return value;
}
function stableString(value){return JSON.stringify(canonical(value))}
function fingerprint(value){let hash=0x811c9dc5;for(const char of stableString(value)){hash^=char.charCodeAt(0);hash=Math.imul(hash,0x01000193)>>>0}return`fnv1a-${hash.toString(16).padStart(8,'0')}`}
function invitationId(documentState=bridge()?.getState?.()||{}){
 const direct=window.EInviteContext?.getInvitationId?.();
 if(direct)return String(direct);
 const params=new URLSearchParams(location.search),route=location.pathname.match(/\/invitations\/([^/]+)/);
 return String(params.get('id')||params.get('invitationId')||route?.[1]||documentState.id||documentState.invitationId||'local-draft');
}
function revision(documentState=bridge()?.getState?.()||{}){return Number(documentState.documentRevision??documentState.revision??documentState.serverRevision??documentState.updatedAt??0)||0}
function canvasMap(documentState,canvasId=bridge()?.getActiveCanvasId?.()||'hero',create=true){
 if(canvasId==='hero')return create?(documentState.objects||(documentState.objects={})):(documentState.objects||{});
 const pageId=String(canvasId).replace(/^page:/,''),page=(documentState.designPages||[]).find(item=>String(item.id)===pageId);
 if(!page)throw Object.assign(Error('The target page no longer exists.'),{code:'MISSING_PAGE'});
 return create?(page.objects||(page.objects={})):(page.objects||{});
}
function safeId(prefix,map={}){
 const random=crypto.randomUUID?.()||Array.from(crypto.getRandomValues(new Uint32Array(4)),number=>number.toString(36)).join('');
 let id=`${String(prefix||'object').toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,24)||'object'}-${random.toLowerCase().replace(/[^a-z0-9]/g,'').slice(0,24)}`;
 let index=2,base=id;while(own(map,id))id=`${base}-${index++}`;return id;
}
function objectType(object){return String(object?.type||object?.objectType||'text')}
function plainText(object){
 try{if(object?.richText&&window.RichTextDocumentModel)return RichTextDocumentModel.exportPlainText(object.richText)}catch{}
 return clean(object?.text??object?.html??'',50000).replace(/<br\s*\/?\s*>/gi,'\n').replace(/<[^>]*>/g,'');
}
function targetSnapshot(documentState,canvasId,targetIds){const map=canvasMap(documentState,canvasId,false);return Object.fromEntries((targetIds||[]).map(String).filter(id=>map[id]).map(id=>[id,clone(map[id])]))}
function selectionType(documentState,canvasId,targetIds){const map=canvasMap(documentState,canvasId,false),types=[...new Set((targetIds||[]).map(id=>objectType(map[id])).filter(Boolean))];return types.length===1?types[0]:types.length?'mixed':'none'}
function captureContext(options={}){
 const documentState=bridge()?.cloneState?.()||{},canvasId=String(options.canvasId||bridge()?.getActiveCanvasId?.()||'hero'),targetIds=[...new Set((options.targetIds||bridge()?.getSelectedIds?.()||[]).map(String))],snapshot=targetSnapshot(documentState,canvasId,targetIds);
 return Object.freeze({
  version:1,invitationId:invitationId(documentState),canvasId,targetObjectIds:targetIds,selectionType:selectionType(documentState,canvasId,targetIds),documentRevision:revision(documentState),documentFingerprint:fingerprint(documentState),targetFingerprint:fingerprint(snapshot),targetSnapshot:snapshot,
  relevantSnapshot:Object.fromEntries(Object.entries(snapshot).map(([id,object])=>[id,{type:objectType(object),text:plainText(object),style:{font:object.font,fontPairing:object.fontPairing,fontSize:object.fontSize,textStyleId:object.textStyleId,color:object.color,left:object.left,top:object.top,width:object.width,height:object.height}}])),
  generatedAt:Number(options.generatedAt||Date.now()),providerMode:String(options.providerMode||'unknown')
 });
}
function permissionAllowed(){
 const explicit=window.EInvitePermissions?.canEdit?.();if(explicit===false)return false;
 const role=String(document.body?.dataset?.collaborationRole||document.body?.dataset?.permission||'').toLowerCase();
 return !['viewer','reviewer','read-only','readonly'].includes(role);
}
function validateContext(context,{allowCompatibleRevision=true}={}){
 const current=bridge()?.getState?.();if(!current)return{ok:false,code:'NO_EDITOR',message:'The editor is not available.'};
 if(!permissionAllowed())return{ok:false,code:'PERMISSION',message:'You no longer have permission to edit this invitation.'};
 if(String(context?.invitationId||'')!==invitationId(current))return{ok:false,code:'INVITATION_CHANGED',message:'This result belongs to a different invitation.'};
 const canvasId=String(context?.canvasId||'hero'),map=canvasMap(current,canvasId,false),missing=(context?.targetObjectIds||[]).filter(id=>!map[id]);
 if(missing.length)return{ok:false,code:'TARGET_MISSING',message:'One or more target objects no longer exist.',missing};
 const currentTargets=targetSnapshot(current,canvasId,context?.targetObjectIds||[]),sameTargets=fingerprint(currentTargets)===String(context?.targetFingerprint||'');
 const sameDocument=fingerprint(current)===String(context?.documentFingerprint||''),currentRevision=revision(current),expectedRevision=Number(context?.documentRevision||0),revisionAvailable=currentRevision>0||expectedRevision>0,sameRevision=revisionAvailable?currentRevision===expectedRevision:sameDocument;
 if(!sameDocument&&!sameTargets)return{ok:false,code:'STALE_REVISION',message:'The target changed after this suggestion was generated.',compatibleTargets:false};
 if(!sameDocument&&revisionAvailable&&!sameRevision&&!allowCompatibleRevision)return{ok:false,code:'STALE_REVISION',message:'The invitation revision changed after this suggestion was generated.',compatibleTargets:sameTargets};
 return{ok:true,code:sameDocument?'EXACT':'COMPATIBLE',message:sameDocument?'The result matches the current document.':'The document changed elsewhere, but the original targets remain compatible.',sameTargets};
}
function richSignatures(rich){return new Set((rich?.paragraphs||[]).flatMap(paragraph=>(paragraph.runs||[]).map(run=>JSON.stringify({marks:run.marks||{},locale:run.locale||paragraph.locale||'und',entityId:run.entityId||'',list:paragraph.list||{}}))))}
function replaceRichText(documentState,id,object,text,mode='preserve'){
 const model=window.RichTextDocumentModel;if(!model)throw Object.assign(Error('The structured rich-text model is not ready.'),{code:'RICH_TEXT_UNAVAILABLE'});
 const normalized=model.normalizeObject(id,clone(object),documentState,{strict:false}),source=normalized.richText,signatures=richSignatures(source);
 if(mode==='preserve'&&signatures.size>1)throw Object.assign(Error('This selection contains multiple marks or links. Choose a replacement mode before applying.'),{code:'RICH_TEXT_MODE_REQUIRED',replacementModes:['preserve-leading-format','replace-plain']});
 const lines=clean(text,50000).replace(/\r\n?/g,'\n').split('\n'),usedParagraphs=new Set(),usedRuns=new Set();
 const paragraphs=lines.map((line,index)=>{
  const sourceParagraph=source.paragraphs[Math.min(index,source.paragraphs.length-1)]||source.paragraphs[0],sourceRun=sourceParagraph?.runs?.[0]||{marks:{},locale:'und'};
  const paragraphId=safeId('p',Object.fromEntries([...usedParagraphs].map(key=>[key,true])));usedParagraphs.add(paragraphId);
  const runId=safeId('r',Object.fromEntries([...usedRuns].map(key=>[key,true])));usedRuns.add(runId);
  const preserve=mode!=='replace-plain';
  return{id:paragraphId,paragraphStyleId:sourceParagraph?.paragraphStyleId||normalized.textStyleId||'body',overrides:clone(sourceParagraph?.overrides||{}),locale:preserve?(sourceParagraph?.locale||sourceRun.locale||model.detectLocale(line,'und')):model.detectLocale(line,'und'),direction:sourceParagraph?.direction||'auto',list:clone(sourceParagraph?.list||{type:'none',level:0,start:1,marker:'disc'}),tabStops:clone(sourceParagraph?.tabStops||[]),runs:[{id:runId,text:line,marks:preserve?clone(sourceRun.marks||{}):{},locale:preserve?(sourceRun.locale||sourceParagraph?.locale||model.detectLocale(line,'und')):model.detectLocale(line,'und'),...(preserve&&sourceRun.entityId?{entityId:sourceRun.entityId}:{})}]};
 });
 const referenced=new Set(paragraphs.flatMap(paragraph=>paragraph.runs.map(run=>run.entityId).filter(Boolean))),entities=Object.fromEntries(Object.entries(source.entities||{}).filter(([id])=>referenced.has(id)));
 const rich=model.normalizeDocument({version:model.MODEL_VERSION,paragraphs,entities},{seed:id,styleIds:Object.keys(documentState.typography?.styles||{}),defaultStyleId:documentState.typography?.defaultStyleId||'body',strict:false});
 object.richTextModelVersion=model.MODEL_VERSION;object.richText=rich;object.text=model.exportPlainText(rich);object.html=model.exportLegacyHtml(rich);
}
function parseSchedule(value){
 if(Array.isArray(value))return value.slice(0,100).map(item=>({time:clean(item?.time,80),title:clean(item?.title,240),titleKm:clean(item?.titleKm,240)})).filter(item=>item.time||item.title||item.titleKm);
 return clean(value,20000).split(/\n+/).map(line=>line.trim()).filter(Boolean).slice(0,100).map(line=>{const parts=line.split(/\s*(?:\||—|–)\s*/,3);return{time:clean(parts.shift()||'',80),title:clean(parts.join(' | ')||'',240),titleKm:''}});
}
function normalizeColor(value){const color=String(value||'').trim();if(!/^#[0-9a-f]{6}$/i.test(color))throw Object.assign(Error(`Invalid palette color: ${color||'(empty)'}`),{code:'INVALID_COLOR'});return color.toUpperCase()}
function applyAction(documentState,action,runtime){
 if(!action||typeof action!=='object'||Array.isArray(action))throw Object.assign(Error('Invalid AI editor action.'),{code:'INVALID_ACTION'});
 const type=String(action.type||''),canvasId=String(action.canvasId||runtime.canvasId||'hero'),map=canvasMap(documentState,canvasId,true),ids=[...new Set((action.targetIds||runtime.targetIds||[]).map(String))];
 const requireTargets=(minimum=1)=>{const missing=ids.filter(id=>!map[id]);if(missing.length||ids.length<minimum)throw Object.assign(Error(missing.length?'A target object no longer exists.':'This action requires a target object.'),{code:missing.length?'TARGET_MISSING':'TARGET_REQUIRED',missing});return ids.map(id=>map[id])};
 if(type==='replaceText'){const objects=requireTargets();objects.forEach((object,index)=>{if(!['text','decoration'].includes(objectType(object)))throw Object.assign(Error('Text replacement requires a text object.'),{code:'TYPE_MISMATCH'});replaceRichText(documentState,ids[index],object,action.text,action.mode||'preserve');if(action.autoFit===true){object.textAutoFit='fit';object.textAutoFitMax=bounded(object.textAutoFitMax??object.fontSize,8,200,32);object.textMinFontSize=Math.min(bounded(object.textMinFontSize,8,72,12),object.textAutoFitMax)}});return ids}
 if(type==='addText'||type==='createObject'){
  const objectTypeValue=type==='addText'?'text':String(action.objectType||'text');if(!allowedTypes.has(objectTypeValue))throw Object.assign(Error('Unsupported object type.'),{code:'UNKNOWN_OBJECT_TYPE'});
  const id=safeId(objectTypeValue,map),base=clone(action.object||{});delete base.id;delete base.legacyId;delete base.domGeometry;base.type=objectTypeValue;base.left=String(base.left??action.left??'12%');base.top=String(base.top??action.top??'24%');base.width=String(base.width??action.width??'76%');base.height=String(base.height??action.height??(objectTypeValue==='text'?'180px':'120px'));base.zIndex=Number(base.zIndex??Math.max(0,...Object.values(map).map(item=>Number(item.zIndex)||0))+1);base.visible=base.visible!==false;base.locked=base.locked===true;
  if(objectTypeValue==='text'||objectTypeValue==='decoration'){base.textStyleId=base.textStyleId||'body';base.fontSize=bounded(base.fontSize??(clean(action.text).length>180?22:28),8,200,28);replaceRichText(documentState,id,base,clean(action.text??base.text??''),action.mode||'replace-plain')}
  map[id]=base;runtime.createdIds.push(id);return[id]
 }
 if(type==='createPageWithText'){
  documentState.designPages=documentState.designPages||[];const pageIds=Object.fromEntries(documentState.designPages.map(page=>[String(page.id),true])),pageId=safeId('page',pageIds),objects={},objectId=safeId('text',objects),object=clone(action.object||{});delete object.id;delete object.legacyId;delete object.domGeometry;object.type='text';object.left=String(object.left??'10%');object.top=String(object.top??'14%');object.width=String(object.width??'80%');object.height=String(object.height??'68%');object.zIndex=Number(object.zIndex??1);object.visible=true;object.locked=false;object.textStyleId=object.textStyleId||'body';object.fontSize=bounded(object.fontSize??22,8,200,22);replaceRichText(documentState,objectId,object,clean(action.text??'',50000),action.mode||'replace-plain');objects[objectId]=object;documentState.designPages.push({id:pageId,name:clean(action.name||'AI text page',100),enabled:true,objects});runtime.createdPageIds.push(pageId);runtime.createdIds.push(objectId);return[pageId,objectId]
 }
 if(type==='updateMessage'){const field=action.locale==='km'||action.field==='messageKm'?'messageKm':'message';documentState.fields=documentState.fields||{};documentState.fields[field]=clean(action.text,50000);return[field]}
 if(type==='applySchedule'){documentState.schedule=parseSchedule(action.schedule??action.text);documentState.settings={...(documentState.settings||{}),scheduleEnabled:true};return['schedule']}
 if(type==='applyPalette'){const colors=Array.isArray(action.colors)?action.colors:clean(action.text).match(/#[0-9a-f]{6}/gi)||[];if(colors.length<2)throw Object.assign(Error('A palette needs at least two valid colors.'),{code:'INVALID_PALETTE'});const normalized=colors.slice(0,4).map(normalizeColor);documentState.palette={...(documentState.palette||{})};normalized.forEach((color,index)=>documentState.palette[paletteKeys[index]]=color);if(normalized[2])documentState.accent=normalized[2];documentState.palettePreset='custom';return['palette']}
 if(type==='duplicateObjects'){const objects=requireTargets(),newIds=[];objects.forEach((object,index)=>{const id=safeId(objectType(object),map),next=clone(object),shift=value=>{const number=parseFloat(value);return Number.isFinite(number)&&String(value).includes('%')?`${Math.min(96,Math.max(0,number+3+index))}%`:value};next.left=shift(next.left);next.top=shift(next.top);next.groupId='';next.parentGroupId='';map[id]=next;newIds.push(id);runtime.createdIds.push(id)});return newIds}
 if(type==='deleteObjects'){requireTargets();ids.forEach(id=>delete map[id]);if(documentState.sceneGraph?.groups)for(const group of Object.values(documentState.sceneGraph.groups)){group.children=(group.children||[]).filter(id=>!ids.includes(id))}return ids}
 if(type==='groupObjects'){requireTargets(2);documentState.sceneGraph=documentState.sceneGraph||{};documentState.sceneGraph.groups=documentState.sceneGraph.groups||{};const groupId=safeId('group',documentState.sceneGraph.groups);ids.forEach(id=>map[id].groupId=groupId);documentState.sceneGraph.groups[groupId]={id:groupId,name:clean(action.name||'AI group',100),children:[...ids],parentId:'',locked:false,visible:true};runtime.createdGroupIds.push(groupId);return[groupId]}
 if(type==='ungroupObjects'){requireTargets();const groups=documentState.sceneGraph?.groups||{},groupIds=new Set(ids.map(id=>map[id]?.groupId).filter(Boolean));ids.forEach(id=>{if(map[id]){map[id].groupId='';map[id].parentGroupId=''}});groupIds.forEach(id=>delete groups[id]);return[...groupIds]}
 if(type==='arrange'){requireTargets();const ordered=Object.entries(map).sort((a,b)=>Number(a[1].zIndex||0)-Number(b[1].zIndex||0)),max=Math.max(0,...ordered.map(([,object])=>Number(object.zIndex)||0)),min=Math.min(0,...ordered.map(([,object])=>Number(object.zIndex)||0));ids.forEach((id,index)=>{if(action.position==='front')map[id].zIndex=max+index+1;else if(action.position==='back')map[id].zIndex=min-ids.length+index;else if(action.position==='forward')map[id].zIndex=Number(map[id].zIndex||0)+1;else if(action.position==='backward')map[id].zIndex=Number(map[id].zIndex||0)-1;else throw Object.assign(Error('Unknown arrange position.'),{code:'INVALID_ARRANGE'})});return ids}
 if(type==='resize'){requireTargets();const patch=action.patch||{};ids.forEach(id=>{for(const key of['left','top','width','height','rotation'])if(own(patch,key)){const value=patch[key];if(key==='rotation')map[id][key]=bounded(value,-360,360,0);else if(/^\d+(?:\.\d+)?(?:%|px)$/.test(String(value)))map[id][key]=String(value);else throw Object.assign(Error(`Invalid ${key} value.`),{code:'INVALID_GEOMETRY'})}});return ids}
 if(type==='photoPreset'){const objects=requireTargets(),look=action.look&&typeof action.look==='object'?action.look:PHOTO_PRESETS[String(action.preset||'enhance')];if(!look)throw Object.assign(Error('Unknown photo preset.'),{code:'UNKNOWN_PHOTO_PRESET'});objects.forEach(object=>{if(objectType(object)!=='image')throw Object.assign(Error('Photo presets require image objects.'),{code:'TYPE_MISMATCH'});for(const key of photoKeys)if(own(look,key))object[key]=clone(look[key])});return ids}
 if(type==='updateObject'){requireTargets();const patch=action.patch&&typeof action.patch==='object'&&!Array.isArray(action.patch)?action.patch:{};const allowed=new Set(['textStyleId','fontPairing','font','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing','textAlign','textVerticalAlign','textWrap','textAutoFit','textAutoFitMax','textMinFontSize','color','backgroundEnabled','backgroundColor','opacity','visible','locked','alt','name','shape','fill','stroke','strokeWidth','borderRadius','src','assetId','crop','animation','animationDuration','animationDelay']);for(const key of Object.keys(patch)){if(!allowed.has(key))throw Object.assign(Error(`Unsupported object property: ${key}`),{code:'INVALID_OBJECT_PATCH'});if(['src'].includes(key)&&!String(patch[key]||'').startsWith('/'))throw Object.assign(Error('Asset sources must use an authorized same-origin path.'),{code:'INVALID_ASSET_SOURCE'})}ids.forEach(id=>{for(const[key,value]of Object.entries(patch)){if(key==='alt'||key==='name')map[id][key]=clean(value,key==='alt'?1000:160);else if(['fontSize','fontWeight','lineHeight','letterSpacing','textAutoFitMax','textMinFontSize','opacity','strokeWidth','borderRadius','animationDuration','animationDelay'].includes(key))map[id][key]=bounded(value,key==='opacity'?0:0,key==='opacity'?1:1000,Number(map[id][key]||0));else map[id][key]=clone(value)}});return ids}
 if(type==='updateFields'){documentState.fields=documentState.fields||{};const fields=action.fields&&typeof action.fields==='object'&&!Array.isArray(action.fields)?action.fields:{};const allowed=new Set(['names','namesKm','message','messageKm','date','dateKm','venue','venueKm','contact','contactKm','subtitle','subtitleKm','eventType','time','timezone','dressCode','dressCodeKm','transport','transportKm','accommodation','accommodationKm']);const updated=[];for(const[key,value]of Object.entries(fields)){if(!allowed.has(key))throw Object.assign(Error(`Unsupported event field: ${key}`),{code:'INVALID_EVENT_FIELD'});documentState.fields[key]=clean(value,50000);updated.push(key)}return updated}
 if(type==='createPage'){documentState.designPages=documentState.designPages||[];const pageIds=Object.fromEntries(documentState.designPages.map(page=>[String(page.id),true])),pageId=safeId('page',pageIds),page={id:pageId,name:clean(action.name||'New page',100),enabled:true,objects:{}};if(action.template&&typeof action.template==='object'){const source=clone(action.template);page.objects=source.objects&&typeof source.objects==='object'?source.objects:{};for(const[key,value]of Object.entries(source))if(!['id','name','objects','domGeometry'].includes(key))page[key]=value}documentState.designPages.push(page);runtime.createdPageIds.push(pageId);return[pageId]}
 if(type==='duplicatePage'){documentState.designPages=documentState.designPages||[];const sourceId=String(action.pageId||'').replace(/^page:/,''),source=documentState.designPages.find(page=>String(page.id)===sourceId);if(!source)throw Object.assign(Error('The page to duplicate no longer exists.'),{code:'MISSING_PAGE'});const pageIds=Object.fromEntries(documentState.designPages.map(page=>[String(page.id),true])),page=clone(source),pageId=safeId('page',pageIds);page.id=pageId;page.name=clean(action.name||`${source.name||'Page'} copy`,100);const remap={},objects={};for(const[oldId,object]of Object.entries(page.objects||{})){const newId=safeId(objectType(object),objects);remap[oldId]=newId;objects[newId]=clone(object)}for(const object of Object.values(objects)){if(object.groupId&&remap[object.groupId])object.groupId=remap[object.groupId];if(object.parentGroupId&&remap[object.parentGroupId])object.parentGroupId=remap[object.parentGroupId]}page.objects=objects;documentState.designPages.splice(documentState.designPages.indexOf(source)+1,0,page);runtime.createdPageIds.push(pageId);runtime.createdIds.push(...Object.keys(objects));return[pageId]}
 if(type==='renamePage'){documentState.designPages=documentState.designPages||[];const pageId=String(action.pageId||'').replace(/^page:/,''),page=documentState.designPages.find(item=>String(item.id)===pageId);if(!page)throw Object.assign(Error('The page to rename no longer exists.'),{code:'MISSING_PAGE'});page.name=clean(action.name||'Page',100);return[pageId]}
 if(type==='reorderPages'){documentState.designPages=documentState.designPages||[];const order=(action.pageIds||[]).map(id=>String(id).replace(/^page:/,'')),byId=new Map(documentState.designPages.map(page=>[String(page.id),page]));if(order.length!==documentState.designPages.length||order.some(id=>!byId.has(id))||new Set(order).size!==order.length)throw Object.assign(Error('The page order must contain every design page exactly once.'),{code:'INVALID_PAGE_ORDER'});documentState.designPages=order.map(id=>byId.get(id));return order}
 if(type==='alignObjects'){requireTargets(2);const objects=ids.map(id=>map[id]),numeric=(value,axis)=>{const raw=parseFloat(value);if(!Number.isFinite(raw))return 0;return String(value).includes('%')?raw:raw};const unitFor=key=>objects.every(object=>String(object[key]||'').includes('%'))?'%':'px',alignment=String(action.alignment||'center'),lefts=objects.map(object=>numeric(object.left,'x')),tops=objects.map(object=>numeric(object.top,'y')),widths=objects.map(object=>numeric(object.width,'x')),heights=objects.map(object=>numeric(object.height,'y'));let target;if(alignment==='left')target=Math.min(...lefts);else if(alignment==='right')target=Math.max(...lefts.map((v,i)=>v+widths[i]));else if(alignment==='center')target=(Math.min(...lefts)+Math.max(...lefts.map((v,i)=>v+widths[i])))/2;else if(alignment==='top')target=Math.min(...tops);else if(alignment==='bottom')target=Math.max(...tops.map((v,i)=>v+heights[i]));else if(alignment==='middle')target=(Math.min(...tops)+Math.max(...tops.map((v,i)=>v+heights[i])))/2;else throw Object.assign(Error('Unknown alignment.'),{code:'INVALID_ALIGNMENT'});ids.forEach((id,i)=>{if(['left','right','center'].includes(alignment)){const value=alignment==='left'?target:alignment==='right'?target-widths[i]:target-widths[i]/2;map[id].left=`${value}${unitFor('left')}`}else{const value=alignment==='top'?target:alignment==='bottom'?target-heights[i]:target-heights[i]/2;map[id].top=`${value}${unitFor('top')}`}});return ids}
 if(type==='distributeObjects'){requireTargets(3);const axis=String(action.axis||'horizontal'),key=axis==='vertical'?'top':'left',sizeKey=axis==='vertical'?'height':'width',unit=ids.every(id=>String(map[id][key]||'').includes('%'))?'%':'px',ordered=ids.map(id=>({id,start:parseFloat(map[id][key])||0,size:parseFloat(map[id][sizeKey])||0})).sort((a,b)=>a.start-b.start),first=ordered[0],last=ordered[ordered.length-1],span=(last.start+last.size)-first.start,total=ordered.reduce((sum,item)=>sum+item.size,0),gap=(span-total)/(ordered.length-1);let cursor=first.start;for(const item of ordered){map[item.id][key]=`${cursor}${unit}`;cursor+=item.size+gap}return ids}
 if(type==='tidyObjects'){requireTargets(2);const columns=Math.max(1,Math.min(12,Math.round(Number(action.columns)||Math.ceil(Math.sqrt(ids.length))))),gap=Math.max(0,Math.min(200,Number(action.gap)||16)),objects=ids.map(id=>map[id]),percent=objects.every(object=>['left','top','width','height'].every(key=>String(object[key]||'').includes('%'))),unit=percent?'%':'px',cellW=Math.max(...objects.map(object=>parseFloat(object.width)||20)),cellH=Math.max(...objects.map(object=>parseFloat(object.height)||20)),startX=Math.min(...objects.map(object=>parseFloat(object.left)||0)),startY=Math.min(...objects.map(object=>parseFloat(object.top)||0));ids.forEach((id,index)=>{map[id].left=`${startX+(index%columns)*(cellW+gap)}${unit}`;map[id].top=`${startY+Math.floor(index/columns)*(cellH+gap)}${unit}`});return ids}
 if(type==='applyTextStyle'){requireTargets();const styleId=clean(action.styleId,120);ids.forEach(id=>{if(!['text','decoration'].includes(objectType(map[id])))throw Object.assign(Error('Semantic text styles require text objects.'),{code:'TYPE_MISMATCH'});map[id].textStyleId=styleId;map[id].typographyDetached=false});return ids}
 if(type==='applyBrandKit'){const kit=action.kit&&typeof action.kit==='object'&&!Array.isArray(action.kit)?clone(action.kit):{};documentState.brandKitId=clean(action.brandKitId||kit.id,120);if(kit.palette&&typeof kit.palette==='object')documentState.palette={...(documentState.palette||{}),...clone(kit.palette)};if(kit.accent)documentState.accent=normalizeColor(kit.accent);if(kit.typography&&typeof kit.typography==='object')documentState.typography={...(documentState.typography||{}),...clone(kit.typography)};return['brandKitId']}
 if(type==='insertAsset'){const id=safeId('image',map),asset=action.asset&&typeof action.asset==='object'?action.asset:{};if(!String(asset.src||'').startsWith('/'))throw Object.assign(Error('Only authorized same-origin assets can be inserted.'),{code:'INVALID_ASSET_SOURCE'});map[id]={type:'image',assetId:clean(asset.id||action.assetId,120),src:String(asset.src).slice(0,2000),alt:clean(action.alt||asset.alt||asset.name||'',1000),left:String(action.left||'15%'),top:String(action.top||'15%'),width:String(action.width||'70%'),height:String(action.height||'55%'),zIndex:Math.max(0,...Object.values(map).map(item=>Number(item.zIndex)||0))+1,visible:true,locked:false};runtime.createdIds.push(id);return[id]}
 const extension=window.EInviteAIActionExtensions?.[type];if(typeof extension==='function')return extension(documentState,action,runtime);
 throw Object.assign(Error(`Unknown AI editor action: ${type||'(missing)'}`),{code:'UNKNOWN_ACTION'});
}
function normalize(documentState){window.TypographyDocumentModel?.normalizeDocument?.(documentState,{mutate:true});window.RichTextDocumentModel?.normalizeInvitation?.(documentState,{mutate:true,strict:false});window.EInviteEditorSchema?.syncLegacy?.(documentState);return documentState}
function applyActions(documentState,actions,runtime={}){runtime.createdIds=runtime.createdIds||[];runtime.createdGroupIds=runtime.createdGroupIds||[];runtime.createdPageIds=runtime.createdPageIds||[];runtime.canvasId=runtime.canvasId||bridge()?.getActiveCanvasId?.()||'hero';runtime.targetIds=runtime.targetIds||[];for(const action of actions)applyAction(documentState,action,runtime);normalize(documentState);return runtime}
function diff(before,after){
 const changes=[];function walk(a,b,path='document'){if(stableString(a)===stableString(b))return;if(a&&b&&typeof a==='object'&&typeof b==='object'&&!Array.isArray(a)&&!Array.isArray(b)){for(const key of new Set([...Object.keys(a),...Object.keys(b)]))walk(a[key],b[key],`${path}.${key}`);return}changes.push({path,before:clone(a),after:clone(b)})}walk(before,after);return changes.slice(0,500)
}
function colorLuminance(value){const hex=String(value||'').match(/^#([0-9a-f]{6})$/i)?.[1];if(!hex)return null;const parts=[0,2,4].map(index=>parseInt(hex.slice(index,index+2),16)/255).map(value=>value<=.03928?value/12.92:((value+.055)/1.055)**2.4);return .2126*parts[0]+.7152*parts[1]+.0722*parts[2]}
function contrastRatio(a,b){const first=colorLuminance(a),second=colorLuminance(b);if(first==null||second==null)return null;const high=Math.max(first,second),low=Math.min(first,second);return(high+.05)/(low+.05)}
async function waitForFonts(){try{await document.fonts?.ready}catch{};try{await window.EInviteFontRegistry?.ready?.()}catch{}}
async function renderedTypographyDiagnostics(documentState,canvasId,widths){
 const renderer=window.EInviteRenderer,layout=window.TypographyLayoutService,adapters=window.EInviteTypographyRendererAdapters;if(!renderer?.renderObject||!layout?.fitAndDiagnose||!adapters?.project)return[];
 const map=canvasMap(documentState,canvasId,false),warnings=[],host=document.createElement('div');host.dataset.aiLayoutPreview='true';Object.assign(host.style,{position:'fixed',left:'-12000px',top:'0',visibility:'hidden',pointerEvents:'none',contain:'strict',zIndex:'-1'});document.body.append(host);
 try{
  for(const viewport of widths){const pageWidth=Math.max(240,Math.min(Number(viewport)||390,1440)),pageHeight=Math.max(520,Math.round(pageWidth*844/390)),stage=document.createElement('div');Object.assign(stage.style,{position:'relative',width:`${pageWidth}px`,height:`${pageHeight}px`,overflow:'hidden',background:String(documentState.palette?.background||documentState.background||'#ffffff')});stage.innerHTML=Object.entries(map).sort(([,a],[,b])=>Number(a?.zIndex||0)-Number(b?.zIndex||0)).map(([id,object])=>renderer.renderObject(object,{id,pageHeight,document:documentState})).join('');host.replaceChildren(stage);
   for(const[id,object]of Object.entries(map)){if(!['text','decoration'].includes(objectType(object)))continue;const node=stage.querySelector(`[data-object-id="${CSS.escape(id)}"]`);if(!node)continue;const model=adapters.project(documentState,object,{text:plainText(object)}),result=layout.fitAndDiagnose(node,model,{set:false}),diagnostic=result?.diagnostics;if(diagnostic?.overflow)warnings.push({code:'TEXT_OVERFLOW',severity:'error',objectId:id,width:viewport,pipeline:'shared-renderer',message:`Text overflows at ${viewport}px by ${diagnostic.horizontalOverflow}px horizontally and ${diagnostic.verticalOverflow}px vertically.`,repairs:['auto-fit','resize-height','reflow-body-text','move-to-new-page']});for(const warning of diagnostic?.warnings||[]){if(warning.code==='clipped-content')continue;warnings.push({code:String(warning.code||'TYPOGRAPHY').toUpperCase().replace(/-/g,'_'),severity:warning.severity||'warning',objectId:id,width:viewport,pipeline:'shared-renderer',message:warning.message,repairs:[]})}
   }
  }
 }finally{host.remove()}
 return warnings;
}
async function diagnostics(documentState,canvasId,widths=[320,360,390,430,820,1024,1180,1440]){
 await waitForFonts();const map=canvasMap(documentState,canvasId,false),warnings=[];
 const schemaResult=window.EInviteEditorSchema?.validate?.(documentState);if(schemaResult&&schemaResult.ok===false)warnings.push({code:'SCHEMA',severity:'error',message:`Document schema validation failed: ${clean(schemaResult.error||'invalid document',500)}`,repairs:['cancel']});
 const background=documentState.palette?.background||documentState.background||'#ffffff';
 for(const[id,object]of Object.entries(map)){
  const type=objectType(object),left=parseFloat(object.left??0),top=parseFloat(object.top??0),width=parseFloat(object.width??0),height=parseFloat(object.height??0),percentGeometry=[object.left,object.top,object.width,object.height].every(value=>String(value??'').includes('%'));
  if(percentGeometry&&(left<0||top<0||left+width>100||top+height>100))warnings.push({code:'BOUNDS',severity:'error',objectId:id,message:'Object extends outside the page bounds.',repairs:['move-inside-bounds','resize']});
  if(type==='image'&&!clean(object.alt,1000).trim())warnings.push({code:'MISSING_ALT',severity:'warning',objectId:id,message:'Image is missing alternative text.',repairs:['add-alt-text']});
  if(['text','decoration'].includes(type)){const ratio=contrastRatio(object.color||documentState.palette?.text||'#222222',object.backgroundEnabled?object.backgroundColor:background);if(ratio!=null&&ratio<4.5)warnings.push({code:'CONTRAST',severity:'warning',objectId:id,message:`Text contrast is ${ratio.toFixed(2)}:1.`,repairs:['change-text-color','change-background']})}
 }
 const rendered=await renderedTypographyDiagnostics(documentState,canvasId,widths),seen=new Set();return[...warnings,...rendered].filter(item=>{const key=[item.code,item.objectId,item.width||0,item.message].join('|');if(seen.has(key))return false;seen.add(key);return true});
}
async function preview(actions,{context=captureContext(),widths}={}){
 const validation=validateContext(context);if(!validation.ok)return{ok:false,stale:true,validation,context};
 const before=bridge().cloneState(),after=clone(before),runtime={canvasId:context.canvasId,targetIds:[...(context.targetObjectIds||[])],createdIds:[],createdGroupIds:[],createdPageIds:[]};
 try{applyActions(after,actions,runtime)}catch(error){return{ok:false,error:{code:error.code||'ACTION_FAILED',message:error.message,replacementModes:error.replacementModes||[]},context}}
 const warnings=await diagnostics(after,context.canvasId,widths),changes=diff(before,after);return{ok:true,context,validation,beforeFingerprint:fingerprint(before),afterFingerprint:fingerprint(after),changes,warnings,affectedObjectIds:[...new Set([...context.targetObjectIds,...runtime.createdIds])],affectedPages:[...new Set([context.canvasId,...runtime.createdPageIds.map(id=>`page:${id}`)])],createdIds:runtime.createdIds,createdPageIds:runtime.createdPageIds,repairOptions:[...new Set(warnings.flatMap(item=>item.repairs||[]))]};
}
function commit(actions,{context=captureContext(),label='AI edit',selectionAfter=null}={}){
 const validation=validateContext(context);if(!validation.ok)throw Object.assign(Error(validation.message),{code:validation.code,validation});
 const before=bridge().cloneState(),runtime={canvasId:context.canvasId,targetIds:[...(context.targetObjectIds||[])],createdIds:[],createdGroupIds:[],createdPageIds:[]};
 let result;try{result=bridge().transact(label,documentState=>{applyActions(documentState,actions,runtime);return clone(runtime)},{capture:false})}catch(error){if(fingerprint(bridge().getState())!==fingerprint(before))bridge().replaceState(before,{history:false,save:false,reason:'AI batch rollback'});throw error}
 const selected=selectionAfter||(runtime.createdIds.length?runtime.createdIds:(context.targetObjectIds||[]));requestAnimationFrame(()=>bridge()?.select?.(selected));window.dispatchEvent(new CustomEvent('einvite:ai-job-committed',{detail:{label,actions:actions.map(action=>action.type),context,createdIds:[...runtime.createdIds],createdPageIds:[...runtime.createdPageIds]}}));return{ok:true,result,createdIds:[...runtime.createdIds],createdPageIds:[...runtime.createdPageIds],validation};
}
function applyRepair(actions,repair,previewResult){
 const targetIds=previewResult?.affectedObjectIds||[];if(repair==='auto-fit')return actions.map(action=>action.type==='replaceText'?{...clone(action),autoFit:true}:clone(action));
 if(repair==='resize-height'){const amended=actions.map(action=>clone(action));amended.push(...targetIds.map(id=>({type:'resize',targetIds:[id],patch:{height:'260px'}})));return amended}
 if(repair==='reflow-body-text')return actions.map(action=>action.type==='replaceText'?{type:'addText',canvasId:action.canvasId,text:action.text,mode:'replace-plain',object:{textStyleId:'body',fontSize:20,left:'10%',top:'20%',width:'80%',height:'60%',textAutoFit:'fit',textAutoFitMax:20,textMinFontSize:12}}:clone(action));
 if(repair==='move-to-new-page')return actions.map(action=>action.type==='replaceText'?{type:'createPageWithText',text:action.text,mode:'replace-plain',name:'AI overflow text',object:{textStyleId:'body',fontSize:22,left:'10%',top:'12%',width:'80%',height:'72%',textAutoFit:'fit',textAutoFitMax:22,textMinFontSize:12}}:clone(action));
 return actions;
}
window.EInviteAIActionService=Object.freeze({version:VERSION,captureContext,validateContext,preview,commit,applyRepair,fingerprint,diff,diagnostics,applyActions,plainText,safeId,canvasMap,PHOTO_PRESETS});
})();;(()=>{'use strict';if(window.EInviteDeferredToolsV052)return;const tasks=new Map(),load=src=>tasks.get(src)||(tasks.set(src,new Promise((ok,no)=>{const s=document.createElement('script');s.src=src;s.onload=ok;s.onerror=()=>no(Error(`Could not load ${src}`));document.head.append(s)}).catch(e=>{tasks.delete(src);throw e})),tasks.get(src));function button(id,text,data,parent){if(document.getElementById(id))return;const b=document.createElement('button');b.id=id;b.type='button';b.className='ei-advanced-launcher';b.textContent=text;Object.assign(b.dataset,data);parent?.append(b)}function init(){const top=document.querySelector('.studio-topbar');button('eiAiTopButton','✦ Agent',{deferredTool:'ai',openAi:'write'},top);button('eiAdvancedStudio','Studio Pro',{deferredTool:'advanced',einviteAdvancedOpen:'v29',einviteAdvancedView:'layers'},top);button('eiFuturePlatform','Platform',{deferredTool:'advanced',einviteAdvancedOpen:'v52',einviteAdvancedView:'editor'},top);const label=document.querySelector('#font')?.closest('label');button('eiFontBootstrap','Browse fonts',{deferredTool:'font'},label);document.addEventListener('click',click);document.addEventListener('keydown',key);window.EInviteDeferredToolsV052=Object.freeze({version:'0.52',load})}async function click(e){const t=e.target.closest?.('[data-deferred-tool]');if(!t)return;e.preventDefault();try{if(t.dataset.deferredTool==='ai'){await load('ai-assistant-loader.js');return window.EInviteAILoader?.open?.(t.dataset.openAi||'write',t)}if(t.dataset.deferredTool==='advanced'){await load('advanced-editor-loader.js');return window.EInviteAdvancedLoader?.open?.(t.dataset.einviteAdvancedOpen||'v29',t.dataset.einviteAdvancedView||'layers',t)}if(t.dataset.deferredTool==='font'){t.remove();await load('font-browser-loader.js');return document.querySelector('.ei-font-launch')?.click()}}catch(error){window.uiAlert?.(error.message,{title:'Editor tools'})}}function key(e){if((e.ctrlKey||e.metaKey)&&e.key==='.'&&!e.altKey){e.preventDefault();const t=document.getElementById('eiAiTopButton');t?.click()}}function destroy(){document.removeEventListener('click',click);document.removeEventListener('keydown',key);delete window.EInviteDeferredToolsV052}window.EInviteLifecycle?.add?.(destroy);document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init,{once:true}):init()})();;(()=>{'use strict';
if(window.__EInviteCollaborationPanelInit)return;window.__EInviteCollaborationPanelInit=true;
const $=(s,r=document)=>r.querySelector(s); if(!$('#stage'))return;
localStorage.removeItem('sovan-auth-token');
const inviteId=()=>window.serverInvite?.id||window.EInviteContext?.getInvitationId({allowRemembered:false})||'';
async function api(path,options={}){const r=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',}});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'Request failed');return d}
const sharePane=document.querySelector('[data-inspector-pane="publish"]')||document.querySelector('aside.right');if(!sharePane)return;
const section=document.createElement('section');section.className='ei-collab-card';section.innerHTML=`<div><small>Collaboration</small><h2>Invite collaborators</h2><p class="hint">Share editing access with another registered account. Owners and managers can manage collaborators.</p></div><div class="ei-collab-form"><input id="eiCollabEmail" type="email" placeholder="name@example.com"><select id="eiCollabRole"><option value="viewer">Can view</option><option value="content">Edit content</option><option value="designer">Edit design</option><option value="manager">Manage project</option></select><button id="eiCollabAdd" type="button">Invite</button></div><div id="eiCollabState" class="hint"></div><div id="eiCollabList" class="ei-collab-list"></div>`;sharePane.append(section);
async function load(){const id=inviteId();if(!id){section.hidden=true;return}section.hidden=false;const state=$('#eiCollabState');try{const rows=await api(`/api/invitations/${id}/collaborators`);state.textContent=rows.length?`${rows.length} collaborator${rows.length===1?'':'s'}`:'No collaborators yet.';const list=$('#eiCollabList');list.innerHTML='';rows.forEach(row=>{const el=document.createElement('div');el.className='ei-collab-row';el.innerHTML=`<div><strong></strong><small></small></div><span></span><button type="button" class="danger">Remove</button>`;el.querySelector('strong').textContent=row.email;el.querySelector('small').textContent='Registered collaborator';el.querySelector('span').textContent=row.role;el.querySelector('button').onclick=async()=>{if(!(await uiConfirm(`Remove ${row.email} from this invitation?`,{title:'Remove collaborator',danger:true,confirmText:'Remove'})))return;try{await api(`/api/invitations/${id}/collaborators/${row.userId}`,{method:'DELETE'});uiToast('Collaborator removed','✓');load()}catch(e){uiAlert(e.message)}};list.append(el)})}catch(e){state.textContent=e.message;$('#eiCollabList').innerHTML=''}}
$('#eiCollabAdd').onclick=async()=>{const email=$('#eiCollabEmail').value.trim(),role=$('#eiCollabRole').value;if(!email)return;try{await api(`/api/invitations/${inviteId()}/collaborators`,{method:'POST',body:JSON.stringify({email,role})});$('#eiCollabEmail').value='';uiToast('Collaborator added','✓');load()}catch(e){uiAlert(e.message)}};
(async()=>{if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){section.hidden=true;return}setTimeout(load,250);document.addEventListener('einvite:server-connected',load,{once:true})})();
})();;(()=>{'use strict';
if(window.__EInviteCollaborationLiveInit)return;
window.__EInviteCollaborationLiveInit=true;
if(!document.querySelector('#stage'))return;
const $=selector=>document.querySelector(selector),life=window.EInviteLifecycle;
const clientId=sessionStorage.getItem('einvite-editor-client-id')||(crypto.randomUUID?.()||`client-${Date.now()}-${Math.random().toString(36).slice(2)}`);
sessionStorage.setItem('einvite-editor-client-id',clientId);
let knownRevision=Number(window.serverInvite?.updatedAt||0),notifiedRevision=0,pollTimer=0,presenceTimer=0,retryTimer=0,source=null,stopped=false;
const ownMutations=new Set();
const id=()=>window.serverInvite?.id||window.EInviteContext?.getInvitationId({allowRemembered:false})||'';
async function api(signal){const invitation=id();if(!invitation)throw Error('Invitation unavailable');const r=await fetch(`/api/invitations/${encodeURIComponent(invitation)}`,{credentials:'same-origin',cache:'no-store',signal});if(!r.ok)throw Error();return r.json()}
function ensureChip(){let chip=$('#eiRemoteChangeChip');if(!chip){chip=document.createElement('button');chip.id='eiRemoteChangeChip';chip.type='button';chip.className='ei-remote-chip';chip.hidden=true;chip.innerHTML='<span>↻</span><strong>Remote changes available</strong>';document.body.append(chip);chip.onclick=async()=>{if(!(await uiConfirm('Reload the latest server version? Unsaved local changes may be replaced.',{title:'Sync remote changes',confirmText:'Reload latest'})))return;location.reload()}}return chip}
function receive(change){const updated=Number(change?.updatedAt??change??0),origin=String(change?.clientId||''),mutation=String(change?.mutationId||'');if(!updated)return;if(!knownRevision){knownRevision=updated;return}if(origin===clientId||ownMutations.has(mutation)||updated<=knownRevision){knownRevision=Math.max(knownRevision,updated);return}if(updated!==notifiedRevision){notifiedRevision=updated;const chip=ensureChip();chip.hidden=false;window.uiToast?.('This invitation changed in another session.','↻')}knownRevision=Math.max(knownRevision,updated)}
function acceptLocal(detail={}){const updated=Number(detail.updatedAt||0),mutation=String(detail.mutationId||'');if(mutation)ownMutations.add(mutation);if(ownMutations.size>100)ownMutations.delete(ownMutations.values().next().value);if(updated)knownRevision=Math.max(knownRevision,updated);const chip=ensureChip();chip.hidden=true;notifiedRevision=0}
document.addEventListener('einvite:local-revision',event=>acceptLocal(event.detail||{}));
async function poll(){if(stopped||!id()||document.hidden)return;const controller=new AbortController();try{const invite=await api(controller.signal);receive({updatedAt:invite.updatedAt})}catch{}finally{controller.abort()}}
function startPolling(){if(stopped||pollTimer)return;poll();pollTimer=(life?.interval||setInterval)(poll,7000)}
function stopPolling(){if(pollTimer){clearInterval(pollTimer);pollTimer=0}}
function scheduleSseRetry(){if(stopped||retryTimer)return;retryTimer=(life?.timeout||setTimeout)(()=>{retryTimer=0;if(!document.hidden)startSSE()},60000)}
function startSSE(){if(stopped)return;const invitation=id();if(!invitation||!window.EventSource){startPolling();return}try{source?.close();source=new EventSource(`/api/invitations/${encodeURIComponent(invitation)}/events`);source.addEventListener('open',stopPolling);source.addEventListener('invitation-update',event=>{try{receive(JSON.parse(event.data))}catch{}});source.onerror=()=>{source?.close();source=null;startPolling();scheduleSseRetry()}}catch{startPolling();scheduleSseRetry()}}
function ensurePresence(){let root=$('#eiPresenceStack');if(root)return root;root=document.createElement('div');root.id='eiPresenceStack';root.className='ei-presence-stack';root.hidden=true;root.setAttribute('aria-label','People currently viewing this invitation');document.body.append(root);return root}
function renderPresence(rows=[]){const others=rows.filter(x=>x.clientId!==clientId),root=ensurePresence();root.hidden=!others.length;root.replaceChildren(...others.slice(0,4).map(x=>{const span=document.createElement('span');span.className='ei-presence-avatar';span.title=String(x.email||'Collaborator');span.textContent=String(x.email||'?').trim().slice(0,1).toUpperCase();return span}));if(others.length){const label=document.createElement('span');label.className='ei-presence-label';label.textContent=`${others.length} collaborator${others.length===1?'':'s'} here`;root.append(label)}}
async function heartbeatPresence(){const invitation=id();if(stopped||!invitation||document.hidden)return;const controller=new AbortController();try{const selected=window.EInviteEditorBridge?.getSelectedIds?.()[0]||'',response=await fetch(`/api/invitations/${encodeURIComponent(invitation)}/presence`,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({clientId,mode:document.body.dataset.focusMode==='true'?'focus':'editing',selectedObjectId:selected}),signal:controller.signal});if(!response.ok)return;const payload=await response.json();renderPresence(Array.isArray(payload)?payload:(payload.presence||[]))}catch{}finally{controller.abort()}}
function stop(){if(stopped)return;stopped=true;stopPolling();if(presenceTimer){clearInterval(presenceTimer);presenceTimer=0}if(retryTimer){clearTimeout(retryTimer);retryTimer=0}source?.close();source=null}
const onVisibility=()=>{if(document.hidden)return;if(window.EInviteBackend?.isAvailable()){poll();heartbeatPresence();if(!source)startSSE()}};
document.addEventListener('visibilitychange',onVisibility);life?.add?.(()=>document.removeEventListener('visibilitychange',onVisibility));life?.add?.(stop);window.addEventListener('pagehide',stop,{once:true});
(async()=>{if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){stop();return}ensureChip();startSSE();heartbeatPresence();presenceTimer=(life?.interval||setInterval)(heartbeatPresence,15000)})();
window.EInviteCollaborationSync={clientId,get knownRevision(){return knownRevision},receive,acceptLocal};
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
if(document.body&&!document.body.dataset.page)document.body.dataset.page=page;
/* V55 (dispatch Group 2): the previous dashboard-home layer is retired. It injected a
   fixed 76px rail, a marketing hero ("What will you create today?"), a second search
   field and an English-only quick-create row, and it hid the real .dash-head. The shell
   now owns the welcome row, the filter row and the card grid; dashboard-polish.js owns
   the loading / empty / error states. See docs/reviews/redesign-report.md. */
function dashboard(){ /* retired in v55 */ }
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
        <button class="refine-text-preset khmer" data-refine-text="khmer" lang="km">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section"><div><h3>Fonts</h3><small>Search · Khmer · Favorites</small></div><button type="button" class="refine-browse-fonts">Browse all fonts</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Quick invitation styles</small></div><div class="refine-font-combos">
        <button class="refine-font-combo" data-combo="gold"><span style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button class="refine-font-combo" data-combo="modern"><span style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><i>HEADING</i></span><small>Modern contrast</small></button>
        <button class="refine-font-combo" data-combo="romance"><span style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button class="refine-font-combo" data-combo="khmer"><span lang="km" style="font-family:'Noto Serif Khmer','Khmer OS Muol Light',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
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
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const calendarLabel=value=>{const dt=new Date(`${value||''}T00:00:00`);if(!value||Number.isNaN(dt.getTime()))return value||'';const wanted=document.documentElement.lang==='km'?'km-KH':'en-US',locale=Intl.DateTimeFormat.supportedLocalesOf([wanted]).length?wanted:'en-US';return new Intl.DateTimeFormat(locale,{dateStyle:'long'}).format(dt)};
const staleDate=/^\d{4} M\d{2} \d{1,2}/;
function dashboardFinal(){
  const grid=$('#inviteGrid'),view=$('#dashboardView'),header=$('body>header'); if(!grid||!view)return;
  const getInvites=()=>{try{return Array.isArray(invites)?invites:[]}catch{return[]}};
  const findInvite=id=>getInvites().find(x=>String(x.id)===String(id));
  const localDoc=id=>{try{return JSON.parse(localStorage.getItem(`sovan-invite-draft-v3:${id}`)||'null')}catch{return null}};
  const previewDoc=item=>item?.preview||localDoc(item?.id)||null;
  function buildPreview(item){
    const doc=previewDoc(item)||{},palette=doc.palette||{},fields=doc.fields||{},page0=(doc.designPages||[])[0]||null,objects=page0?.objects||doc.objects||{};
    const detail=objects.details;if(detail&&staleDate.test(String(detail.html||'')))detail.html=String(detail.html).replace(staleDate,calendarLabel(fields.date));
    const bg=page0?.background||doc.masterPageStyle?.background||palette.background||'#fff7f3',text=palette.text||'#342c26',heading=palette.heading||doc.accent||'#9d4555',accent=doc.accent||heading;
    const shell=document.createElement('div');shell.className='fp-project-preview';shell.style.setProperty('--preview-shell',`color-mix(in srgb, ${bg} 52%, var(--app-surface-2))`);
    const art=document.createElement('div');art.className='fp-project-artboard v20-faithful-thumbnail';art.style.setProperty('--preview-bg',bg);art.style.setProperty('--preview-text',text);art.style.setProperty('--preview-heading',heading);art.style.setProperty('--preview-accent',accent);art.style.background=bg;
    if(Object.keys(objects).length&&globalThis.EInviteTypographyRendererAdapters&&!art.closest('.invite-card')){TypographyDocumentModel?.normalizeDocument?.(doc,{mutate:true});art._typographyThumbnailController?.disconnect?.();art._typographyThumbnailController=EInviteTypographyRendererAdapters.renderThumbnail(art,doc,objects,{width:390,height:844})}
    else{const f=document.createElement('div');f.className='fp-thumb-fallback';f.innerHTML=`<small>${esc(doc.eventType||item.type||'Invitation')}</small><strong>${esc(fields.names||item.title||'Untitled invitation')}</strong><span>${esc(fields.date||'')} ${fields.venue?`· ${esc(fields.venue)}`:''}</span>`;art.append(f)}
    shell.append(art);return shell;
  }
  const timeAgo=value=>{const t=Number(value)||Date.parse(value)||0;if(!t)return'';const sec=Math.max(0,Math.round((Date.now()-t)/1000));if(sec<60)return'Edited just now';if(sec<3600)return`Edited ${Math.floor(sec/60)}m ago`;if(sec<86400)return`Edited ${Math.floor(sec/3600)}h ago`;if(sec<604800)return`Edited ${Math.floor(sec/86400)}d ago`;return`Edited ${new Date(t).toLocaleDateString()}`};
  function decorateCard(card){
    if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit;if(!id)return;const item=findInvite(id);if(!item)return;card.dataset.fpReady='1';card.dataset.inviteId=id;
    const cover=$('.invite-cover',card);if(cover){cover.replaceChildren(buildPreview(item));cover.onclick=()=>{if(!item.archived)card.querySelector('.actions [data-edit]')?.click()}}
    const body=$('.invite-body',card),stats=$('.stats',card),actions=$('.actions',card);if(!body||!actions)return;
    if(stats)stats.innerHTML=`<span>${esc(item.status||'Draft')}</span><span>${esc(timeAgo(item.updatedAt))}</span>`;
    const more=document.createElement('button');more.type='button';more.className='fp-project-more';more.setAttribute('aria-label','Project actions');more.setAttribute('aria-expanded','false');more.textContent='•••';
    const menu=document.createElement('div');menu.className='fp-project-menu';menu.setAttribute('role','menu');
    const map=[['Edit','[data-edit]'],['Guests','[data-guests]'],['Responses','[data-responses]'],['Analytics','[data-analytics]'],['Duplicate','[data-copy]'],[item.archived?'Restore':'Archive','[data-archive]'],['Delete','[data-delete]']];
    map.forEach(([label,selector])=>{const source=$(selector,actions);if(!source)return;const b=document.createElement('button');b.type='button';b.textContent=label;if(label==='Delete')b.className='danger';b.onclick=e=>{e.stopPropagation();menu.classList.remove('open');more.setAttribute('aria-expanded','false');source.click()};menu.append(b)});
    more.onclick=e=>{e.stopPropagation();$$('.fp-project-menu.open').filter(x=>x!==menu).forEach(x=>x.classList.remove('open'));menu.classList.toggle('open');more.setAttribute('aria-expanded',menu.classList.contains('open')?'true':'false')};
    body.append(more);card.append(menu);
  }
  const refresh=()=>$$('.invite-card',grid).forEach(decorateCard);new MutationObserver(refresh).observe(grid,{childList:true,subtree:true});refresh();
  document.addEventListener('click',()=>$$('.fp-project-menu.open').forEach(x=>x.classList.remove('open')));
  if(header&&!$('.fp-dashboard-profile',header)){
    const wrap=document.createElement('div');wrap.className='fp-dashboard-profile';wrap.innerHTML=`<button type="button" class="fp-profile-button" aria-label="Account menu">U</button><div class="fp-profile-popover"><div class="fp-profile-summary"><strong>Account</strong><small></small></div><a href="account.html">Account settings</a><a href="materials.html">Materials</a><a href="billing.html">Plans & usage</a><a href="designer.html" data-profile-designer hidden>Designer workspace</a><a href="admin.html" data-profile-admin hidden>Administration</a><button type="button" data-signout>Sign out</button></div>`;header.append(wrap);
    const button=$('.fp-profile-button',wrap),pop=$('.fp-profile-popover',wrap);button.onclick=e=>{e.stopPropagation();pop.classList.toggle('open')};pop.onclick=e=>e.stopPropagation();$('[data-signout]',wrap).onclick=()=>$('#logoutBtn')?.click();
    const update=()=>{let a=null;try{a=account}catch{}const email=a?.email||'Account';$('.fp-profile-summary strong',wrap).textContent=email;$('.fp-profile-summary small',wrap).textContent=[a?.role,a?.plan].filter(Boolean).join(' · ');button.textContent=(email[0]||'U').toUpperCase();$('[data-profile-designer]',wrap).hidden=!['designer','admin'].includes(a?.role);$('[data-profile-admin]',wrap).hidden=a?.role!=='admin';wrap.hidden=view.hidden};new MutationObserver(update).observe(view,{attributes:true,attributeFilter:['hidden']});update();document.addEventListener('click',()=>pop.classList.remove('open'));
  }
}
function materialsFinal(){
  const grid=$('#grid');if(!grid)return;
  let dialog=null;
  function itemById(id){try{return materials.find(x=>String(x.id)===String(id))}catch{return null}}
  function inviteName(id){try{return invitations.find(x=>String(x.id)===String(id))?.title||invitations.find(x=>String(x.id)===String(id))?.slug||'Invitation'}catch{return'Invitation'}}
  function ensureDialog(){if(dialog)return dialog;dialog=document.createElement('dialog');dialog.className='fp-material-preview-dialog';document.body.append(dialog);return dialog}
  function openPreview(item){if(!item)return;const kind=item.mime?.startsWith('image/')?'image':item.mime?.startsWith('video/')?'video':item.mime?.startsWith('audio/')?'audio':'file',d=ensureDialog();
    let media=kind==='image'?`<img src="${esc(item.url)}" alt="${esc(item.name)}">`:kind==='video'?`<video src="${esc(item.url)}" controls preload="metadata"></video>`:kind==='audio'?`<div><div class="fp-material-audio-art">♫</div><audio src="${esc(item.url)}" controls preload="metadata"></audio></div>`:`<div class="fp-material-audio-art">◇</div>`;
    d.innerHTML=`<div class="fp-material-preview-shell"><div class="fp-material-stage">${media}</div><aside class="fp-material-detail"><div class="fp-material-detail-head"><h2>${esc(item.name)}</h2><button type="button" class="fp-material-close">×</button></div><div class="fp-material-facts"><div><span>Type</span><strong>${esc(item.mime||'Unknown')}</strong></div><div><span>Size</span><strong>${typeof formatBytes==='function'?formatBytes(item.size):esc(item.size)}</strong></div><div><span>Invitation</span><strong>${esc(inviteName(item.invitationId))}</strong></div><div><span>Folder</span><strong>${esc(item.folder||'No folder')}</strong></div><div><span>Used</span><strong>${Number(item.usageCount||0)} reference${Number(item.usageCount||0)===1?'':'s'}</strong></div></div><div class="fp-material-preview-actions"><button type="button" class="primary" data-use>Use in design</button><div class="fp-material-secondary-actions"><button type="button" data-edit> Edit details</button><a href="${esc(item.url)}" download target="_blank" rel="noopener" class="button-link">Download</a></div><button type="button" class="fp-material-danger" data-delete>Delete material</button></div></aside></div>`;
    $('.fp-material-close',d).onclick=()=>d.close();$('[data-edit]',d).onclick=()=>{d.close();try{openEdit(item.id)}catch{grid.querySelector(`[data-edit="${CSS.escape(String(item.id))}"]`)?.click()}};$('[data-delete]',d).onclick=()=>{d.close();try{openEdit(item.id);setTimeout(()=>$('#deleteBtn')?.click(),40)}catch{}};$('[data-use]',d).onclick=()=>{localStorage.setItem('sovan-active-invite',item.invitationId);localStorage.setItem('einvite-pending-material-insert',JSON.stringify({url:item.url,name:item.name,mime:item.mime,assetId:item.id}));location.href=`/invitations/${encodeURIComponent(item.invitationId)}/editor`};d.showModal();
  }
  function decorate(){
    const empty=$('.empty-library',grid);if(empty&&/Authentication required|sign in|unauthorized/i.test(empty.textContent)){document.body.classList.add('material-auth-required');grid.innerHTML=`<div class="fp-material-auth-state"><div class="fp-material-auth-card"><div class="icon">◌</div><h2>Your session has expired</h2><p>Sign in again to access your photos, videos, audio, folders, and saved materials.</p><a href="dashboard.html" class="button-link primary">Sign in again</a></div></div>`;return}else document.body.classList.remove('material-auth-required');
    $$('.material-card-page',grid).forEach(card=>{if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit,item=itemById(id);if(!item)return;card.dataset.fpReady='1';const thumb=$('.material-thumb',card);if(thumb)thumb.onclick=()=>openPreview(item);const info=$('.material-info',card);if(info){const row=document.createElement('div');row.className='fp-material-meta-row';row.innerHTML=`<span>${item.mime?.split('/')[0]||'file'}</span>${Number(item.usageCount||0)?`<span class="fp-material-usage">Used ${Number(item.usageCount)}</span>`:''}`;info.append(row)}})
  }
  new MutationObserver(decorate).observe(grid,{childList:true,subtree:true});decorate();
}
function editorFinal(){
  const stage=$('#stage'),host=$('.studio-pane-host'),rail=$('.studio-tool-rail');if(!stage||!host||!rail)return;
  const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};const choose=o=>{try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([o])}catch{}};
  const makeId=p=>`${p}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
  // The creation drawer is owned by editor-responsive-contract-v27 (EInviteResponsiveLayout): it
  // derives `mobile-pane-collapsed` from body[data-editor-drawer] on every sync, so toggling the
  // class by hand is reverted in the same tick and the handle looked dead. Delegate to the owner
  // when it is present, and keep the class toggle only as the fallback for hosts without it.
  const owner=()=>window.EInviteResponsiveLayout;
  const closePaneOnMobile=()=>{if(owner()?.closeCreation){owner().closeCreation();return}if(innerWidth<=820&&document.body.classList.contains('studio-design-mode'))document.body.classList.add('mobile-pane-collapsed')};
  const openPane=()=>{if(owner()?.openCreation){owner().openCreation();return}document.body.classList.remove('mobile-pane-collapsed')};
  rail.addEventListener('click',openPane,true);
  if(!$('.fp-mobile-pane-handle')){const h=document.createElement('button');h.type='button';h.className='fp-mobile-pane-handle';h.textContent='›';h.title='Open creation panel';h.onclick=openPane;document.body.append(h)}
  $$('.studio-pane-heading',host).forEach(head=>{if(head.querySelector('.fp-mobile-pane-close'))return;const b=document.createElement('button');b.type='button';b.className='fp-mobile-pane-close';b.textContent='‹';b.title='Hide panel';b.onclick=closePaneOnMobile;head.append(b)});
  function addSvgAsset(asset){if(typeof createObject!=='function')return;const o=createObject(makeId('graphic'),'image');const data=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(asset.svg)}`;o.style.left=asset.left||'18%';o.style.top=asset.top||'24%';o.style.width=asset.width||'64%';o.style.height=asset.height||'190px';o.dataset.src=data;o.dataset.layerName=asset.name;o.dataset.showInGallery='false';o.dataset.showInHero='true';const img=o.querySelector('img');if(img){img.src=data;img.alt=asset.name}stage.append(o);choose(o);saveNow();window.uiToast?.(`${asset.name} added`,'✦');closePaneOnMobile()}
  const assets=[
    {name:'Khmer lotus corner',cat:'Khmer',width:'38%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220"><g fill="none" stroke="#b48735" stroke-width="5" stroke-linecap="round"><path d="M20 200C82 190 110 154 113 92M20 200c52-42 90-49 154-44"/><path d="M113 92c-29 21-44 51-40 84 28-10 51-31 64-61 12 29 35 49 65 58 1-34-15-63-45-83-1 31-8 57-20 77-13-20-21-45-24-75Z"/><path d="M174 156c38-12 72-9 120 21M205 148c18-18 31-40 36-68"/></g></svg>`},
    {name:'Royal gold flourish',cat:'Wedding',height:'120px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160"><g fill="none" stroke="#c5a15b" stroke-width="5"><path d="M18 82c110 0 124-58 210-58 48 0 57 38 72 58 15-20 24-58 72-58 86 0 100 58 210 58"/><path d="M22 84c110 0 126 54 218 54 32 0 49-18 60-48 11 30 28 48 60 48 92 0 108-54 218-54"/><circle cx="300" cy="82" r="12" fill="#c5a15b"/></g></svg>`},
    {name:'Botanical sprig',cat:'Botanical',width:'34%',height:'250px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 380"><g fill="none" stroke="#527760" stroke-width="5" stroke-linecap="round"><path d="M68 350C102 254 128 162 196 40"/><path d="M111 237c-58 4-84-23-91-59 44-7 76 11 98 44M137 176c-9-52 10-83 49-101 15 40 7 74-31 106M85 293c-43 4-67-15-76-47 34-8 64 2 83 31M169 116c-5-39 10-65 43-79 11 32 4 58-24 82"/></g></svg>`},
    {name:'Wedding arch',cat:'Wedding',width:'66%',height:'300px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 620"><path d="M80 600V270C80 120 145 30 250 30s170 90 170 240v330" fill="none" stroke="#b58a5a" stroke-width="10"/><g fill="#d9aeb3"><circle cx="93" cy="240" r="24"/><circle cx="112" cy="192" r="18"/><circle cx="392" cy="215" r="24"/><circle cx="370" cy="165" r="17"/></g><g fill="#6f8d72"><ellipse cx="126" cy="230" rx="12" ry="34" transform="rotate(45 126 230)"/><ellipse cx="374" cy="240" rx="12" ry="34" transform="rotate(-45 374 240)"/></g></svg>`},
    {name:'Diamond frame',cat:'Frames',width:'58%',height:'320px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500"><path d="M250 18 482 250 250 482 18 250Z" fill="none" stroke="#c6a35b" stroke-width="9"/><path d="M250 46 454 250 250 454 46 250Z" fill="none" stroke="#c6a35b" stroke-width="2" opacity=".7"/></svg>`},
    {name:'Lotus divider',cat:'Khmer',height:'110px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 150"><g fill="none" stroke="#a87616" stroke-width="4"><path d="M20 75h250M430 75h250"/><path d="M350 28c-24 18-36 40-35 66 17-6 29-18 35-36 6 18 18 30 35 36 1-26-11-48-35-66Z"/><path d="M350 44c-12 13-18 28-18 44 8-3 14-9 18-18 4 9 10 15 18 18 0-16-6-31-18-44Z"/></g></svg>`},
    {name:'Celebration confetti',cat:'Celebration',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 320"><g fill="none" stroke-linecap="round" stroke-width="10"><path d="M55 55l32 30M420 44l-28 36M118 258l35-17M380 263l-36-23" stroke="#ff5d8f"/><path d="M158 38l-8 42M328 45l18 39M58 180l44-4M410 170l34 12" stroke="#50b9d6"/><path d="M235 34l8 44M255 263l-5 38" stroke="#7d59d4"/></g><g fill="#f2b84b"><circle cx="101" cy="122" r="10"/><circle cx="395" cy="112" r="9"/><circle cx="205" cy="238" r="8"/></g></svg>`},
    {name:'Executive wave',cat:'Business',height:'150px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 180"><path d="M0 132C120 46 205 36 330 104c109 59 229 45 370-46v122H0Z" fill="#173e58"/><path d="M0 154C140 82 222 76 344 132c104 48 216 38 356-30v78H0Z" fill="#20a49b" opacity=".78"/></svg>`},
    {name:'Rose corner',cat:'Wedding',width:'36%',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 300"><g fill="#d48d9c"><circle cx="82" cy="82" r="38"/><circle cx="120" cy="58" r="30"/><circle cx="131" cy="101" r="34"/></g><g fill="#6d8b70"><ellipse cx="186" cy="85" rx="24" ry="54" transform="rotate(48 186 85)"/><ellipse cx="98" cy="176" rx="22" ry="60" transform="rotate(12 98 176)"/></g><path d="M20 282C66 210 107 151 178 96" fill="none" stroke="#6d8b70" stroke-width="7"/></svg>`},
    {name:'Minimal line frame',cat:'Frames',width:'72%',height:'360px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700"><rect x="18" y="18" width="464" height="664" rx="18" fill="none" stroke="#65535f" stroke-width="3"/><rect x="38" y="38" width="424" height="624" rx="12" fill="none" stroke="#65535f" stroke-width="1" opacity=".55"/></svg>`},
    {name:'Star sparkle cluster',cat:'Celebration',width:'34%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 260"><g fill="#c69d55"><path d="m150 18 14 57 56 14-56 14-14 57-14-57-56-14 56-14Z"/><path d="m240 126 8 30 30 8-30 8-8 30-8-30-30-8 30-8Z" opacity=".72"/><circle cx="66" cy="182" r="12" opacity=".55"/></g></svg>`},
    {name:'Khmer geometric border',cat:'Khmer',height:'88px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 100"><defs><pattern id="p" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M40 4 76 40 40 76 4 40Z" fill="none" stroke="#a87616" stroke-width="4"/><path d="M40 19 61 40 40 61 19 40Z" fill="none" stroke="#a87616" stroke-width="2"/></pattern></defs><rect width="800" height="80" y="10" fill="url(#p)"/></svg>`}
  ];
  const pane=$('[data-studio-pane="elements"]',host);
  if(pane&&!$('.fp-visual-assets',pane)){
    const section=document.createElement('section');section.className='fp-visual-assets';section.innerHTML=`<div class="fp-visual-assets-head"><h3>Visual graphics</h3><small>Invitation-ready SVG</small></div><div class="fp-visual-asset-grid"></div>`;const grid=$('.fp-visual-asset-grid',section);
    assets.forEach(asset=>{const b=document.createElement('button');b.type='button';b.className='fp-visual-asset';b.innerHTML=`<span class="art">${asset.svg}</span><strong>${esc(asset.name)}</strong>`;b.title=`${asset.name} · ${asset.cat}`;b.onclick=()=>addSvgAsset(asset);grid.append(b)});
    const existing=$('.final-element-library',pane);pane.insertBefore(section,existing||pane.firstChild);if(existing&&!existing.closest('.fp-simple-symbols')){const details=document.createElement('details');details.className='fp-simple-symbols';details.innerHTML='<summary>Simple symbols & shapes</summary>';existing.before(details);details.append(existing)}
  }
  const textPane=$('[data-studio-pane="text"]',host);
  if(textPane&&!$('.fp-text-fonts',textPane)){
    const fonts=[
      ['Noto Sans','noto-sans','Modern'],['Modern Sans','sans-arial','Modern'],['Friendly','sans-trebuchet','Modern'],['Noto Serif','noto-serif','Serif'],['Classic Serif','serif-georgia','Serif'],['Khmer Sans','noto-sans-khmer','Khmer'],['Khmer Serif','noto-serif-khmer','Khmer']
    ].map(([name,stack,cat])=>({name,stack,cat}));
    const recent=()=>{try{return JSON.parse(localStorage.getItem('einvite-font-recent-v1')||'[]')}catch{return[]}};
    const section=document.createElement('section');section.className='refine-text-section fp-text-fonts';section.innerHTML=`<div><h3>Fonts</h3><small>Click a font to apply it or create text</small></div><div class="fp-text-category-tabs"></div><div class="fp-inline-font-list"></div>`;
    const combo=document.createElement('section');combo.className='refine-text-section';combo.innerHTML=`<div><h3>Font combinations</h3><small>Ready-made invitation typography</small></div><div class="fp-text-combo-grid">
      <button class="fp-text-combo" data-fp-combo="gold"><span class="hero" style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
      <button class="fp-text-combo" data-fp-combo="editorial"><span class="hero" style="font-family:Didot,Georgia,serif">THE<br><i>MOMENT</i></span><small>Editorial contrast</small></button>
      <button class="fp-text-combo" data-fp-combo="modern"><span class="hero" style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><small>SUBHEADING</small></span><small>Modern clean</small></button>
      <button class="fp-text-combo" data-fp-combo="romance"><span class="hero" style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
      <button class="fp-text-combo" data-fp-combo="khmer"><span class="hero" lang="km" style="font-family:'Khmer OS Muol Light','Noto Serif Khmer',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      <button class="fp-text-combo" data-fp-combo="minimal"><span class="hero" style="font-family:Inter,Arial,sans-serif;letter-spacing:.12em">SAVE<br>THE DATE</span><small>Minimal spaced</small></button>
    </div>`;
    const fontPlaceholder=$('.refine-text-section',textPane)?.nextElementSibling;textPane.append(section,combo);
    let cat='All',query='';const categories=['All','Recent','Khmer','Serif','Modern'];
    const selected=()=>$('.object.selected,.object.multi-selected',stage);
    const applyFont=font=>{let o=selected();if(!o){$('#addText')?.click();o=selected()}if(!o)return;try{pushHistory(capture())}catch{}o.dataset.font=font.stack;try{applyObjectVisualStyle(o);save()}catch{}const r=[font.stack,...recent().filter(x=>x!==font.stack)].slice(0,12);localStorage.setItem('einvite-font-recent-v1',JSON.stringify(r));closePaneOnMobile()};
    function renderFonts(){const tabs=$('.fp-text-category-tabs',section),list=$('.fp-inline-font-list',section);tabs.innerHTML=categories.map(x=>`<button type="button" class="${x===cat?'active':''}" data-cat="${x}">${x}</button>`).join('');$$('[data-cat]',tabs).forEach(b=>b.onclick=()=>{cat=b.dataset.cat;renderFonts()});let data=fonts.filter(f=>{if(cat==='Recent'&&!recent().includes(f.stack))return false;if(!['All','Recent'].includes(cat)&&f.cat!==cat)return false;return!query||`${f.name} ${f.cat}`.toLowerCase().includes(query)});if(cat==='Recent')data.sort((a,b)=>recent().indexOf(a.stack)-recent().indexOf(b.stack));list.innerHTML='';data.forEach(f=>{const b=document.createElement('button');b.type='button';b.className='fp-inline-font';b.innerHTML=`<span class="sample" lang="${f.cat==='Khmer'?'km':'en'}" style="font-family:${window.EInviteTypography?.stack?.(f.stack)||'serif'}">${f.cat==='Khmer'?'សិរីមង្គល':'Beautiful moments'}</span><small>${esc(f.name)}</small>`;b.onclick=()=>applyFont(f);list.append(b)});if(!data.length)list.innerHTML='<small style="padding:12px;color:var(--app-muted)">No fonts match this view.</small>'}
    renderFonts();
    const search=$('.refine-text-search input',textPane);if(search){const prior=search.oninput;search.oninput=e=>{query=e.target.value.trim().toLowerCase();renderFonts();$$('.refine-text-preset,.fp-text-combo',textPane).forEach(x=>x.hidden=!!query&&!x.textContent.toLowerCase().includes(query));if(typeof prior==='function')prior.call(search,e)}}
    const combos={gold:{font:'serif-georgia',fontSize:'48',color:'#b48a20',text:'Golden Hour',letterSpacing:'1'},editorial:{font:'noto-serif',fontSize:'48',color:'#2c2530',text:'The Moment',fontStyle:'italic'},modern:{font:'sans-arial',fontSize:'44',color:'#202127',text:'Your Celebration',fontWeight:'700'},romance:{font:'serif-georgia',fontSize:'46',color:'#426b52',text:'Bride & Groom',fontStyle:'italic'},khmer:{font:"noto-serif-khmer",fontSize:'38',color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'},minimal:{font:'noto-sans',fontSize:'34',color:'#22242a',text:'SAVE THE DATE',letterSpacing:'5'}};
    $$('.fp-text-combo',combo).forEach(b=>b.onclick=()=>{const c=combos[b.dataset.fpCombo];$('#addText')?.click();setTimeout(()=>{const o=selected();if(!o)return;const content=o.querySelector('.content');if(content)content.textContent=c.text;Object.entries(c).forEach(([k,v])=>{if(k!=='text')o.dataset[k]=v});try{applyObjectVisualStyle(o);save()}catch{}closePaneOnMobile()},30)});
  }
  host.addEventListener('click',e=>{const insert=e.target.closest('.final-element-card,.ei-pack-card,[data-add-element],[data-text-preset],.refine-text-preset,.refine-font-combo,.fp-text-combo,.fp-visual-asset,.material-picker-card');if(insert)setTimeout(closePaneOnMobile,80)},true);
  setTimeout(()=>{let pending=null;try{pending=JSON.parse(localStorage.getItem('einvite-pending-material-insert')||'null')}catch{}if(!pending?.url||typeof createObject!=='function')return;localStorage.removeItem('einvite-pending-material-insert');const o=createObject(makeId('material'),'image');o.style.left='14%';o.style.top='18%';o.style.width='72%';o.style.height='420px';o.dataset.src=pending.url;o.dataset.layerName=pending.name||'Material';const img=o.querySelector('img');if(img){img.src=pending.url;img.alt=pending.name||'Invitation material'}stage.append(o);choose(o);saveNow();window.uiToast?.(`${pending.name||'Material'} added to the canvas`,'↑')},500);
  const context=$('.ei-context-toolbar');if(context){let scheduled=false;const decorate=()=>{scheduled=false;if(context.querySelector('.ei-context-more'))return;const secondary=['effects','animate','flipX','flipY','tidy','ungroup','page-motion','check'];const nodes=secondary.map(a=>context.querySelector(`[data-action="${a}"]`)).filter(Boolean);if(nodes.length){const more=document.createElement('button');more.type='button';more.className='ei-context-more';more.textContent='•••';more.title='More actions';const overflow=document.createElement('div');overflow.className='ei-context-overflow';nodes.forEach(n=>overflow.append(n));more.onclick=e=>{e.stopPropagation();overflow.classList.toggle('open')};context.append(more,overflow);document.addEventListener('click',()=>overflow.classList.remove('open'))}};const observer=new MutationObserver(()=>{if(context.querySelector('.ei-context-more'))return;if(scheduled)return;scheduled=true;queueMicrotask(decorate)});observer.observe(context,{childList:true,subtree:false});decorate()}
}
if(page==='dashboard')setTimeout(dashboardFinal,0);
if(page==='materials')setTimeout(materialsFinal,0);
if(page==='index')setTimeout(editorFinal,120);
})();;(()=>{
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
  // FB-43: the pane host is built with its first tab (Event) active, and the
  // workflow then activates the real start tab (Design on a fresh session).
  // Entering content mode in between made <main> switch to position:fixed at
  // y=126 and back, i.e. the editor's only 'poor' CLS. Until the workflow owns
  // the section (it publishes EInviteWorkflow), boot in the neutral layout.
  const content=(section==='event'||section==='blocks')&&!!window.EInviteWorkflow;
  body.classList.toggle('studio-content-mode',content);
  body.classList.toggle('studio-design-mode',!content);
  body.dataset.studioSection=section;
  if(main){main.style.removeProperty('display');main.style.removeProperty('grid-template-columns')}
  if(stageWrap)stageWrap.hidden=content;
  if(inspector)inspector.hidden=content;
  if(selection)selection.hidden=content;
  if(status)status.hidden=content||innerWidth<=1180;
  $$('.studio-panel-resizer',main).forEach(x=>x.hidden=content||innerWidth<=1180);
  // P2 fix (DESIGN-FIX-TASK 2026-10-19): never hide the canvas because an
  // Event/Blocks/content panel is active. The canvas is the product here —
  // users were losing their poster the moment they opened Event or Blocks.
  // Content mode now only collapses the inspector; the stage stays visible
  // at every viewport width (mobile included, where the drawers overlay it).
  if(stageWrap)stageWrap.hidden=false;
  if(inspector)inspector.hidden=false;
  if(selection)selection.hidden=content;
  if(status)status.hidden=innerWidth<=1180;
  $$('.studio-panel-resizer',main).forEach(x=>x.hidden=innerWidth<=1180);
  if(content){
    body.classList.remove('mobile-pane-collapsed');
  }else{
    requestAnimationFrame(()=>{
      try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{}
      window.dispatchEvent(new Event('einvite:layout-stable'));
    });
  }
}
clampPanelWidths();
applyLayout();
  // Owner decision (CANVA-UI §5, accepted 2026-10-20): poster documents have
  // no event data — hide the Event/Blocks rail buttons, the RSVP + countdown
  // left-panel groups ([data-poster-hide] wrappers in index.html) and the
  // Design-home Event/Blocks cards (workflow-refine flow); auto-open the
  // Elements pane once; the canvas itself now always stays visible.
  function posterPanelTreatments(){
    $$('.studio-tool-rail [data-studio-tab="event"],.studio-tool-rail [data-studio-tab="blocks"]').forEach(b=>{b.hidden=true});
    $$('[data-poster-hide]').forEach(node=>{node.hidden=true});
    $$('[data-flow-open="event"],[data-flow-open="blocks"]').forEach(el=>{
      if(el.closest('[data-studio-pane="design"]'))el.hidden=true; // flow cards
    });
    if(['event','blocks'].includes(activeSection())){ // never leave a hidden pane active
      document.querySelector('.studio-tool-rail [data-studio-tab="elements"]')?.click();
    }
  }
  // workflow-refine (Design home) rebuilds/reorders the rail after this script
  // runs; re-apply the treatments whenever those surfaces change.
  const posterTreatWatcher=new MutationObserver(()=>{
    if(body.dataset.posterPaneApplied)posterPanelTreatments();
  });
  for(const target of [rail,host]){
    if(target)posterTreatWatcher.observe(target,{childList:true,subtree:target!==rail});
  }
  // Public hook: app.js (connectServer) re-migrates `state` from the fetched
  // server document and calls this; it re-drives posterAutoPane without assuming
  // load order beyond app.js loading later in the bundle.
  window.EInvitePosterTreat=()=>{try{window.__posterPaneWaitDone=false;applyLayout();posterAutoPane()}catch{}};
  function posterAutoPane(){
  const st=window.EInviteEditorBridge?.getState?.();
  if(!st||st.eventType!=='Poster'||body.dataset.posterPaneApplied)return;
  body.dataset.posterPaneApplied='1';
  posterPanelTreatments();
  if(activeSection()==='event'){
    // Route the switch through the public tab button (click) — direct class
    // toggles get re-applied back by the pane watchers.
    document.querySelector('.studio-tool-rail [data-studio-tab="elements"]')?.click();
  }
}
posterAutoPane();
for(const n of ['einvite:editor-ready','einvite:editor-state-replaced'])document.addEventListener(n,posterAutoPane);
(function posterPanePoll(attempt){ // panes are built later by studio-experience; poll briefly
  if(body.dataset.posterPaneApplied||attempt>600){const st=window.EInviteEditorBridge?.getState?.();if(st&&st.eventType==='Poster'&&attempt<=600&&!window.__posterPaneWaitDone){window.__posterPaneWaitDone=true;setTimeout(()=>posterAutoPane(),100);return}return}
  window.__posterPaneWaitDone=false;requestAnimationFrame(()=>posterPanePoll(attempt+1));
})(0);
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
})();;(()=>{
'use strict';
const existing=window.EInviteWorkflowV4;if(existing?.refresh){existing.refresh();return}
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
if(!document.body?.classList.contains('studio-experience')||!$('#stage')||!window.EInviteWorkflow)return;
const body=document.body, stage=$('#stage'), viewport=$('#canvasViewport'), stageWrap=$('.stage-wrap'), host=$('.studio-pane-host'), toolbar=$('.studio-canvas-toolbar,.toolbar');
const compact=()=>innerWidth<=1180;
let lastSelection='';
function selected(){return $$('.object.selected,.object.multi-selected',stage)}
function selectedOne(){const s=selected();return s.length===1?s[0]:null}
function sig(){return selected().map(x=>x.dataset.id||'').sort().join('|')}
function typeOf(o){return o?.dataset.objectType||o?.dataset.type||(o?.classList.contains('image-object')?'image':o?.classList.contains('shape-object')?'shape':'text')}
function toast(message,icon='✓'){window.uiToast?.(message,icon)}
function fitSoon(){clearTimeout(fitSoon.t);fitSoon.t=setTimeout(()=>{try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{};try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};dispatchEvent(new CustomEvent('einvite:workspace-resized'))},120)}
function activateTool(name){
  const b=$(`[data-ei-tool="${name}"]`);
  if(b&&!b.classList.contains('active'))b.click();
}
function ensurePageDock(){
  let dock=$('#workflowPageDock');
  if(dock)return dock;
  dock=document.createElement('nav');dock.id='workflowPageDock';dock.className='workflow-page-dock';dock.setAttribute('aria-label','Invitation pages');
  dock.innerHTML='<div class="workflow-page-dock-track"></div><button type="button" class="workflow-page-add" title="Add a page">＋</button>';
  $('.stage-wrap')?.append(dock);
  const add=$('.workflow-page-add',dock);if(add&&!add.dataset.workflowBaseWired){add.dataset.workflowBaseWired='1';add.onclick=()=>{window.EInviteWorkflow.navigate('pages');if(compact())window.EInviteWorkflow.collapsePanel(false)}};
  return dock;
}
function renderPageDock(){
  const source=$('#pageNavigator');if(!source)return;
  const dock=ensurePageDock(),track=$('.workflow-page-dock-track',dock);track.innerHTML='';
  const cards=$$('.page-nav-card',source);
  cards.forEach((card,index)=>{
    const button=document.createElement('button');button.type='button';button.className=`workflow-page-chip${card.classList.contains('active')?' active':''}`;
    const thumb=card.querySelector('.page-thumb')?.cloneNode(true);if(thumb){thumb.removeAttribute('id');thumb.querySelectorAll('[id]').forEach(x=>x.removeAttribute('id'));}
    const label=card.querySelector('strong')?.textContent?.trim()||`Page ${index+1}`;
    button.innerHTML=`<span class="workflow-page-number">${index+1}</span><span class="workflow-page-mini"></span><strong></strong>`;
    $('.workflow-page-mini',button).append(thumb||document.createElement('span'));$('strong',button).textContent=label;
    button.dataset.pageId=card.dataset.pageId||'';
    button.dataset.canvasId=card.dataset.pageId?(typeof designPageToken==='function'?designPageToken(card.dataset.pageId):`page:${card.dataset.pageId}`):'hero';
    button.onclick=()=>{try{typeof switchCanvas==='function'&&switchCanvas(button.dataset.canvasId)}catch{};setTimeout(()=>{renderPageDock()},60)};
    track.append(button);
  });
  const active=$('.workflow-page-chip.active',track);active?.scrollIntoView?.({block:'nearest',inline:'center'});
}
const ownedPageDock=ensurePageDock();
const pageSource=$('#pageNavigator');if(pageSource){new MutationObserver(()=>requestAnimationFrame(renderPageDock)).observe(pageSource,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});renderPageDock()}
function beginInlineText(o){
  if(!o||!['text','decoration'].includes(typeOf(o)))return;
  const content=o.querySelector('.content');if(!content)return;
  setTimeout(()=>{
    content.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true}));
    content.focus?.({preventScroll:true});
    try{const range=document.createRange(),sel=getSelection();range.selectNodeContents(content);sel.removeAllRanges();sel.addRange(range)}catch{}
    toast('Text added — start typing','T');
  },90);
}
function centerNewObject(o){
  if(!o||o.dataset.workflowPositioned==='1')return;
  const left=parseFloat(o.style.left),top=parseFloat(o.style.top);
  if(Number.isNaN(left)||Number.isNaN(top))return;
  if(left>=28&&left<=42&&top>=30&&top<=48){o.style.left='50%';o.style.top='50%';o.style.transform=`translate(-50%,-50%) rotate(${Number(o.dataset.rotation||0)}deg)`;o.dataset.workflowPositioned='1'}
}
function afterInsertion(source,before){
  setTimeout(()=>{
    const now=sig(),o=selectedOne();
    if(!now||now===before||!o)return;
    centerNewObject(o);
    const type=typeOf(o);
    body.dataset.workflowObjectType=type;
    if(type==='text'&&(source.matches('[data-text-preset],.refine-add-text,.refine-text-preset,.fp-text-combo')||source.closest('[data-studio-pane="text"]'))){beginInlineText(o)}
    else if(type==='image')toast('Photo added — use Edit photo for adjustments','▣');
    else toast('Element added to the canvas','✦');
    activateTool('select');
    if(compact())window.EInviteWorkflow.collapsePanel(true);
  },170);
}
const insertionSelector='[data-add-element],[data-text-preset],.refine-add-text,.refine-text-preset,.refine-font-combo,.fp-text-combo,.ei-pack-card,.final-element-card,.fp-visual-asset,.material-picker-card';
document.addEventListener('pointerdown',e=>{const source=e.target.closest(insertionSelector);if(source)source.dataset.workflowBefore=sig()},true);
document.addEventListener('click',e=>{const source=e.target.closest(insertionSelector);if(!source)return;afterInsertion(source,source.dataset.workflowBefore||'')},true);
function ensureCanvasWelcome(){
  let empty=$('#workflowCanvasWelcome');if(empty)return empty;
  empty=document.createElement('div');empty.id='workflowCanvasWelcome';empty.className='workflow-canvas-welcome';empty.hidden=true;
  empty.innerHTML='<strong>Start designing</strong><span>Add text, photos, elements, or pages from the left panel.</span><div><button data-open="elements">Add elements</button><button data-open="text">Add text</button><button data-open="media">Upload photo</button></div>';
  viewport?.append(empty);
  empty.addEventListener('click',e=>{const b=e.target.closest('[data-open]');if(b)window.EInviteWorkflow.navigate(b.dataset.open)});
  return empty;
}
function updateCanvasWelcome(){const w=ensureCanvasWelcome();const count=$$('.object',stage).length;w.hidden=count>0||body.classList.contains('studio-content-mode')}
new MutationObserver(updateCanvasWelcome).observe(stage,{childList:true,subtree:false});updateCanvasWelcome();
window.addEventListener('einvite:workflow-navigation',e=>{
  const to=e.detail?.to;
  if(to==='pages')setTimeout(renderPageDock,80);
  if(['elements','text','media'].includes(to)&&compact())body.classList.remove('inspector-open');
});
window.addEventListener('einvite:state-applied',()=>setTimeout(()=>{renderPageDock();updateCanvasWelcome()},120));
function clickFirst(...selectors){for(const selector of selectors){const el=$(selector);if(el){el.click();return true}}return false}
function closeTransientMenus(except){$$('.workflow-v4-popover.open').forEach(menu=>{if(menu!==except)menu.classList.remove('open')})}
function placePopover(menu,anchor,{align='start',placement='above',gap=10}={}){
  menu.classList.add('open');menu.style.visibility='hidden';menu.style.left='12px';menu.style.top='12px';
  const anchorRect=anchor.getBoundingClientRect(),menuRect=menu.getBoundingClientRect(),margin=12;
  const preferredLeft=align==='end'?anchorRect.right-menuRect.width:anchorRect.left;
  const left=Math.max(margin,Math.min(innerWidth-menuRect.width-margin,preferredLeft));
  const above=anchorRect.top-menuRect.height-gap,below=anchorRect.bottom+gap;
  const preferredTop=placement==='below'?below:above;
  const fallbackTop=placement==='below'?above:below;
  const fitsPreferred=preferredTop>=margin&&preferredTop+menuRect.height<=innerHeight-margin;
  const top=Math.max(margin,Math.min(innerHeight-menuRect.height-margin,fitsPreferred?preferredTop:fallbackTop));
  menu.style.left=`${left}px`;menu.style.top=`${top}px`;menu.style.visibility='';
}
document.addEventListener('pointerdown',e=>{if(!e.target.closest('.workflow-v4-popover,.workflow-v4-trigger,.workflow-page-chip'))closeTransientMenus()},true);
function pageLabelFromId(id){
  if(!id)return'Main hero';
  try{return state?.designPages?.find(p=>p.id===id)?.name||'Visual page'}catch{return'Visual page'}
}
function ensurePageMenu(){
  let menu=$('#workflowV4PageMenu');if(menu)return menu;
  menu=document.createElement('div');menu.id='workflowV4PageMenu';menu.className='workflow-v4-popover workflow-v4-page-menu';menu.innerHTML=`
    <button type="button" data-page-action="rename">Rename page</button>
    <button type="button" data-page-action="duplicate">Duplicate page</button>
    <button type="button" data-page-action="template">Save as template</button>
    <hr>
    <button type="button" class="danger" data-page-action="delete">Delete page</button>`;
  document.body.append(menu);
  menu.addEventListener('click',async e=>{
    const b=e.target.closest('[data-page-action]');if(!b)return;
    const id=menu.dataset.pageId;if(!id)return;
    menu.classList.remove('open');
    const action=b.dataset.pageAction;
    if(action==='rename'){
      const page=state?.designPages?.find(p=>p.id===id);if(!page)return;
      const value=await window.uiPrompt?.('Choose a page name:',page.name||'Visual Page',{title:'Rename page',confirmText:'Rename'});
      if(value==null||!value.trim())return;
      page.name=value.trim().slice(0,80);save?.();renderPageNavigator?.();renderDesignPagesManager?.();toast('Page renamed');
    }
    if(action==='duplicate'){duplicateDesignPage?.(id);toast('Page duplicated')}
    if(action==='template'){savePageTemplate?.(id)}
    if(action==='delete'){removeDesignPage?.(id)}
  });
  return menu;
}
function openPageMenu(button){
  const id=button.dataset.pageId;if(!id)return;
  const menu=ensurePageMenu();closeTransientMenus(menu);menu.dataset.pageId=id;
  placePopover(menu,button,{placement:'above'});
}
function enhancePageDock(){
  const dock=$('#workflowPageDock');if(!dock)return;
  $$('.workflow-page-chip',dock).forEach(button=>{
    if(button.dataset.v4Wired==='1')return;button.dataset.v4Wired='1';
    const id=button.dataset.pageId;
    if(id){
      button.draggable=true;
      button.addEventListener('dragstart',e=>{e.dataTransfer.setData('application/x-einvite-page',id);e.dataTransfer.effectAllowed='move';button.classList.add('dragging')});
      button.addEventListener('dragend',()=>button.classList.remove('dragging'));
      button.addEventListener('dragover',e=>{if(e.dataTransfer.types.includes('application/x-einvite-page')){e.preventDefault();button.classList.add('drag-over')}});
      button.addEventListener('dragleave',()=>button.classList.remove('drag-over'));
      button.addEventListener('drop',e=>{const moving=e.dataTransfer.getData('application/x-einvite-page');button.classList.remove('drag-over');if(moving&&moving!==id){e.preventDefault();reorderVisualPages?.(moving,id);toast('Pages reordered','↕')}});
      const more=document.createElement('span');more.className='workflow-page-more';more.textContent='•••';more.title='Page actions';more.onclick=e=>{e.preventDefault();e.stopPropagation();openPageMenu(button)};button.append(more);
      button.addEventListener('contextmenu',e=>{e.preventDefault();openPageMenu(button)});
    }
  });
  const add=$('.workflow-page-add',dock);if(add&&!add.dataset.v4Wired){add.dataset.v4Wired='1';add.onclick=e=>{e.preventDefault();e.stopPropagation();openPageAddMenu(add)}}
}
const dock=$('#workflowPageDock');
if(dock)new MutationObserver(()=>requestAnimationFrame(enhancePageDock)).observe(dock,{childList:true,subtree:true});
setTimeout(enhancePageDock,100);
function ensurePageAddMenu(){
  let menu=$('#workflowV4PageAdd');if(menu)return menu;
  menu=document.createElement('div');menu.id='workflowV4PageAdd';menu.className='workflow-v4-popover workflow-v4-page-add';
  document.body.append(menu);return menu;
}
function renderPageAddMenu(){
  const menu=ensurePageAddMenu();menu.innerHTML='<header><strong>Add a page</strong><button type="button" data-close>×</button></header><div class="workflow-v4-page-grid"></div>';
  const grid=$('.workflow-v4-page-grid',menu),seen=new Set();
  $$('[data-add-page]').forEach(source=>{
    const type=source.dataset.addPage;if(!type||seen.has(type))return;seen.add(type);
    const button=document.createElement('button');button.type='button';button.dataset.addPageType=type;
    button.innerHTML=`<span>${source.querySelector('span')?.textContent||'▣'}</span><strong>${source.querySelector('strong')?.textContent||type}</strong>`;
    button.onclick=()=>{menu.classList.remove('open');source.click();setTimeout(()=>{toast('Page added — continue designing','＋')},100)};grid.append(button);
  });
  $('[data-close]',menu).onclick=()=>menu.classList.remove('open');
  return menu;
}
function openPageAddMenu(anchor){
  const menu=renderPageAddMenu();closeTransientMenus(menu);placePopover(menu,anchor,{align:'end',placement:'above'});
}
function ensureQuickAdd(){
  if($('#workflowV4QuickAdd'))return;
  const trigger=document.createElement('button');trigger.id='workflowV4QuickAdd';trigger.type='button';trigger.className='workflow-v4-trigger workflow-v4-quick-add-trigger';trigger.innerHTML='<span>＋</span><b>Add</b>';trigger.title='Quick add';
  const menu=document.createElement('div');menu.id='workflowV4QuickAddMenu';menu.className='workflow-v4-popover workflow-v4-quick-add';menu.innerHTML=`
    <header><strong>Add to your invitation</strong><small>Quick insert</small></header>
    <div class="workflow-v4-add-grid">
      <button data-quick-add="heading"><span>T</span><b>Heading</b><small>Large title text</small></button>
      <button data-quick-add="text"><span>t</span><b>Text box</b><small>Start typing</small></button>
      <button data-quick-add="elements"><span>✦</span><b>Elements</b><small>Graphics & ornaments</small></button>
      <button data-quick-add="uploads"><span>⇧</span><b>Uploads</b><small>Photos, video & audio</small></button>
      <button data-quick-add="page"><span>▣</span><b>Page</b><small>Add another page</small></button>
      <button data-quick-add="blocks"><span>▦</span><b>Content block</b><small>Story, note & details</small></button>
    </div>`;
  stageWrap?.append(trigger);document.body.append(menu);
  trigger.onclick=e=>{e.stopPropagation();const open=!menu.classList.contains('open');closeTransientMenus(menu);if(!open)return;placePopover(menu,trigger,{placement:'above'})};
  menu.addEventListener('click',e=>{const b=e.target.closest('[data-quick-add]');if(!b)return;menu.classList.remove('open');const action=b.dataset.quickAdd;
    if(action==='heading'){if(!clickFirst('[data-text-preset="heading"]','.refine-text-preset.heading')){window.EInviteWorkflow.navigate('text')}}
    if(action==='text'){if(!clickFirst('.refine-add-text','#addText'))window.EInviteWorkflow.navigate('text')}
    if(action==='elements')window.EInviteWorkflow.navigate('elements',{source:'quick-add'});
    if(action==='uploads')window.EInviteWorkflow.navigate('media',{source:'quick-add'});
    if(action==='blocks')window.EInviteWorkflow.navigate('blocks',{source:'quick-add'});
    if(action==='page')openPageAddMenu(trigger);
  });
}
ensureQuickAdd();
let lastCanvas='';
function currentCanvas(){
  const active=$('.workflow-page-chip.active');return active?.dataset.canvasId||'';
}
function watchCanvas(){
  const next=currentCanvas();if(!next||next===lastCanvas)return;lastCanvas=next;
  setTimeout(()=>{try{typeof updateCanvasView==='function'&&updateCanvasView()}catch{};try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}},60);
}
const pageDock=$('#workflowPageDock');if(pageDock)new MutationObserver(watchCanvas).observe(pageDock,{subtree:true,attributes:true,attributeFilter:['class']});
watchCanvas();
function refreshWorkflowV4(){
  ensurePageDock();renderPageDock();enhancePageDock();ensureQuickAdd();updateCanvasWelcome();watchCanvas();
}
body.classList.remove('workflow-creation-flow-v3');
body.classList.add('workflow-creation-flow-v4');
window.EInviteWorkflowV4={version:4,stage,refresh:refreshWorkflowV4,openQuickAdd:()=>$('#workflowV4QuickAdd')?.click(),openPageMenu,openPageAddMenu};
refreshWorkflowV4();
})();;(()=>{'use strict';
const MAX_DURATION=5000;
function safeColor(value,fallback='#fff8f2'){const v=String(value||'').trim();return /^#[0-9a-f]{3,8}$/i.test(v)?v:fallback;}
function safeImage(value){const v=String(value||'').trim();if(!v)return'';if(/^https?:\/\//i.test(v)||/^\/uploads\//.test(v)||/^\/api\/image\//.test(v)||/^data:image\/(?:png|jpe?g|webp|avif|gif);base64,/i.test(v))return v;return'';}
function duration(value){const n=Number(value);return Number.isFinite(n)?Math.max(0,Math.min(MAX_DURATION,n)):1100;}
function cssUrl(value){return String(value).replace(/["'()\\\n\r]/g,c=>`\\${c}`);}
function coverMarkup(d,mode,esc){const o=d.openingScene||{},namesEn=d.fields?.names||'Open invitation',namesKm=d.fields?.namesKm||namesEn,subtitleEn=o.subtitle||'You are warmly invited',subtitleKm=o.subtitleKm||subtitleEn,enterEn=o.enterText||'Open invitation',enterKm=o.enterTextKm||'សូមបើកការអញ្ជើញ',names=mode==='km'?namesKm:namesEn,subtitle=mode==='km'?subtitleKm:subtitleEn,enter=mode==='km'?enterKm:enterEn,color=safeColor(o.backgroundColor),image=safeImage(o.backgroundImage),shade=o.textVariant==='light'?'#0005':'#fff3',bg=image?`background-image:linear-gradient(${shade},${shade}),url(&quot;${esc(cssUrl(image))}&quot;);background-color:${color}`:`background-color:${color}`;return `<button id="openCover" type="button" class="open-cover opening-scene-${esc(o.id||'soft-monogram')}" data-monogram="${esc(o.monogram||'')}" style="${bg};--opening-duration:${duration(o.duration)}ms"><span data-cover-en="${esc(subtitleEn)}" data-cover-km="${esc(subtitleKm)}">${esc(subtitle)}</span>${o.monogram?`<b class="opening-monogram">${esc(o.monogram)}</b>`:''}<strong data-cover-en="${esc(namesEn)}" data-cover-km="${esc(namesKm)}">${esc(names||'Invitation')}</strong><em data-cover-en="${esc(enterEn)}" data-cover-km="${esc(enterKm)}">${esc(enter)}</em></button>`;}
function enhance(root,d){const cover=root.querySelector('#openCover');if(!cover)return;const ms=duration(d.openingScene?.duration);cover.style.transitionDuration=`${ms}ms`;const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;if(reduced){cover.dataset.reducedMotion='true';cover.style.transition='none';}cover.addEventListener('keydown',e=>{if(e.key==='Escape'&&d.openingScene?.skipAllowed!==false){e.preventDefault();cover.click();}});cover.addEventListener('click',()=>{const hide=()=>{cover.setAttribute('aria-hidden','true');cover.hidden=true;};if(reduced||ms===0)setTimeout(hide,0);else setTimeout(hide,Math.min(ms+120,MAX_DURATION+120));},{once:true});}
window.EInviteOpeningScenes={coverMarkup,enhance,safeImage,safeColor};
})();;(()=>{'use strict';
function kitStyle(d){const k=window.EInviteExperience?.kits?.[d.styleKit?.id];if(!k)return'';const o=d.styleKit?.overrides||{},radius={minimal:'6px',soft:'14px',rounded:'24px'}[k.radius]||'14px',shadow={ceremonial:'0 18px 55px #5b3a1820',editorial:'0 16px 44px #17171718',soft:'0 18px 48px #754c5718'}[k.shadow]||'0 16px 42px #00000014',gap={compact:'20px',balanced:'32px',generous:'46px'}[k.spacing]||'32px';return `--kit-background:${o.background||k.background};--kit-surface:${o.surface||k.surface};--kit-text:${o.text||k.text};--kit-accent:${o.accent||k.accent};--kit-muted:${o.muted||k.muted};--kit-heading-font:${JSON.stringify(k.headingFont)};--kit-body-font:${JSON.stringify(k.bodyFont)};--kit-khmer-heading:${JSON.stringify(k.khmerHeadingFont)};--kit-khmer-body:${JSON.stringify(k.khmerBodyFont)};--kit-radius:${radius};--kit-shadow:${shadow};--kit-section-gap:${gap}`;}
function safeAmbientPhoto(d){const value=String(d.socialCard?.photo||d.openingScene?.backgroundImage||'').trim();return /^(?:https?:\/\/|\/uploads\/)/i.test(value)?value.replace(/["'()\\\n\r]/g,''):''}
function apply(root,d){
  if(root.dataset.guestLayoutApplied==='true')return;root.dataset.guestLayoutApplied='true';
  const layout=['ambient-frame','editorial-split','full-width'].includes(d.desktopGuestLayout)?d.desktopGuestLayout:'ambient-frame',kit=window.EInviteExperience?.kits?.[d.styleKit?.id];root.style.cssText += ';'+kitStyle(d);root.classList.add('style-kit-'+(d.styleKit?.id||'custom'));if(kit){root.dataset.kitButton=kit.buttonStyle||'';root.dataset.kitPhotoFrame=kit.photoFrame||'';root.dataset.kitOrnament=kit.ornament||'';root.dataset.kitDivider=kit.divider||'';root.dataset.kitMotion=kit.motion||'';}const ambient=safeAmbientPhoto(d);if(ambient)root.style.setProperty('--guest-ambient-image',`url("${ambient}")`);
  const cover=root.querySelector(':scope > #openCover');if(cover)cover.remove();const content=document.createElement('div');content.className='guest-layout-content';while(root.firstChild)content.append(root.firstChild);const shell=document.createElement('div');shell.className=`guest-layout-shell guest-layout-${layout}`;
  if(layout==='editorial-split'){const f=d.fields||{},mode=d.languageMode||'both',summary=document.createElement('aside'),names=mode==='km'?(f.namesKm||f.names):(f.names||'Invitation'),venue=mode==='km'?(f.venueKm||f.venue):(f.venue||'');summary.className='guest-layout-summary';summary.innerHTML=`<small>${mode==='km'?'សូមគោរពអញ្ជើញ':'YOU ARE INVITED'}</small><h1>${window.EInviteRenderer?.esc(names||'Invitation')}</h1><p>${window.EInviteRenderer?.esc(f.date||'')}</p><p>${window.EInviteRenderer?.esc(venue||'')}</p>`;shell.append(summary)}
  shell.append(content);root.append(shell);if(cover)root.append(cover);root.dataset.desktopLayout=layout;
  root.querySelectorAll('img').forEach((img,i)=>{if(!img.loading)img.loading=i<2?'eager':'lazy';img.decoding='async';if(!img.getAttribute('alt')){img.alt='';img.setAttribute('aria-hidden','true');}});root.querySelectorAll('section').forEach(s=>s.classList.add('guest-lazy-section'));
}
window.EInviteGuestLayouts={apply,kitStyle,safeAmbientPhoto};
})();;(()=>{
'use strict';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const SIZES={og:[1200,630],square:[1080,1080],story:[1080,1920]};
function cleanUrl(url=location.href){const u=new URL(url,location.href);['g','guest','guestToken','access','access_token','token'].forEach(k=>u.searchParams.delete(k));return u.href;}
function fitImage(ctx,img,w,h){const scale=Math.max(w/img.naturalWidth,h/img.naturalHeight),sw=w/scale,sh=h/scale,sx=Math.max(0,(img.naturalWidth-sw)/2),sy=Math.max(0,(img.naturalHeight-sh)/2);ctx.drawImage(img,sx,sy,sw,sh,0,0,w,h)}
function loadImage(url){return new Promise(resolve=>{if(!url)return resolve(null);const img=new Image();try{if(new URL(url,location.href).origin!==location.origin)img.crossOrigin='anonymous'}catch{}img.onload=()=>resolve(img);img.onerror=()=>resolve(null);img.src=url})}
function wrap(ctx,text,x,y,max,line,limit=4){const value=String(text||'').trim();if(!value)return y;const units=/\s/.test(value)?value.split(/\s+/):Array.from(value),joiner=/\s/.test(value)?' ':'';let row='',yy=y,count=0;for(const unit of units){const next=row?row+joiner+unit:unit;if(ctx.measureText(next).width>max&&row){ctx.fillText(row,x,yy);yy+=line;row=unit;if(++count>=limit-1)break}else row=next}if(row&&count<limit)ctx.fillText(row,x,yy);return yy+line}
function cardText(d){const s=d.socialCard||{},f=d.fields||{},language=s.language||d.languageMode||'both',en=f.names||'Invitation',km=f.namesKm||'';let names=[en],venue=f.venue||'';if(language==='km'){names=[km||en];venue=f.venueKm||venue}else if(language==='both'&&km&&km!==en){names=[en,km];venue=[f.venue,f.venueKm].filter(Boolean).join(' · ')}return{language,names,date:f.date||'',venue}}
async function draw(canvas,d,format='og'){
  const [w,h]=SIZES[format]||SIZES.og;canvas.width=w;canvas.height=h;
  const ctx=canvas.getContext('2d'),kit=window.EInviteExperience?.kits?.[d.styleKit?.id]||{},s=d.socialCard||{},t=cardText(d),background=kit.background||d.palette?.background||'#fff8f2',accent=kit.accent||d.accent||'#9d4555',text=s.textVariant==='light'?'#fff':kit.text||d.palette?.text||'#342c26';
  ctx.fillStyle=background;ctx.fillRect(0,0,w,h);
  const photo=await loadImage(s.photo);
  if(photo){fitImage(ctx,photo,w,h);ctx.fillStyle=s.textVariant==='light'?'rgba(0,0,0,.46)':'rgba(255,248,242,.68)';ctx.fillRect(0,0,w,h)}else{if(s.textVariant==='light'){ctx.fillStyle=accent;ctx.fillRect(0,0,w,h)}const grd=ctx.createLinearGradient(0,0,w,h);grd.addColorStop(0,accent+'33');grd.addColorStop(1,'#ffffff00');ctx.fillStyle=grd;ctx.fillRect(0,0,w,h)}
  ctx.strokeStyle=accent;ctx.lineWidth=Math.max(3,w/300);ctx.strokeRect(w*.045,h*.07,w*.91,h*.86);
  const align=['left','center','right'].includes(s.alignment)?s.alignment:'center';ctx.textAlign=align;ctx.textBaseline='alphabetic';const x=align==='left'?w*.1:align==='right'?w*.9:w*.5;
  ctx.fillStyle=accent;ctx.font=`700 ${Math.round(w*.025)}px Inter, Arial, sans-serif`;ctx.fillText(t.language==='km'?'សូមគោរពអញ្ជើញ':'YOU ARE INVITED',x,h*.19);
  if(s.monogram){ctx.globalAlpha=.11;ctx.fillStyle=accent;ctx.font=`700 ${Math.round(w*.28)}px ${kit.headingFont||'Georgia'}, serif`;ctx.textAlign='center';ctx.fillText(s.monogram,w*.5,h*.58);ctx.globalAlpha=1;ctx.textAlign=align}
  ctx.fillStyle=text;let y=h*(t.names.length>1?.34:.39);for(const name of t.names){const khmer=/[\u1780-\u17FF]/.test(name),font=khmer?(kit.khmerHeadingFont||'Noto Sans Khmer'):(kit.headingFont||'Georgia');ctx.font=`700 ${Math.round(w*(t.names.length>1?.048:.064))}px "${font}", serif`;y=wrap(ctx,name,x,y,w*.76,Math.round(w*.07),2)+Math.round(w*.012)}
  ctx.font=`500 ${Math.round(w*.027)}px Inter, Arial, sans-serif`;if(t.date){ctx.fillText(t.date,x,Math.max(y,h*.67));y=Math.max(y,h*.67)+Math.round(w*.047)}
  if(t.venue){const khmer=/[\u1780-\u17FF]/.test(t.venue),font=khmer?(kit.khmerBodyFont||'Noto Sans Khmer'):(kit.bodyFont||'Arial');ctx.font=`400 ${Math.round(w*.024)}px "${font}", sans-serif`;wrap(ctx,t.venue,x,y,w*.72,Math.round(w*.034),3)}
  return canvas;
}
function download(canvas,name){try{const a=document.createElement('a');a.download=name;a.href=canvas.toDataURL('image/png',.92);a.click()}catch{window.uiToast?.('This photo source cannot be exported from the browser. Use the published-card download instead.','!')}}
async function downloadUrl(url,name,button){try{if(button)button.disabled=true;const r=await fetch(url,{credentials:'same-origin'});if(!r.ok){const data=await r.json().catch(()=>({}));throw Error(data.error||`Download failed (${r.status})`)}const blob=await r.blob(),a=document.createElement('a');a.download=name;a.href=URL.createObjectURL(blob);a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500);return true}catch(err){window.uiToast?.(err?.message||'This download is not available yet.','!');if(button&&/QR generation is unavailable/i.test(err?.message||'')){button.hidden=true;button.setAttribute('aria-hidden','true')}return false}finally{if(button&&!button.hidden)button.disabled=false}}
function render(host){
  const d=state.socialCard||{};
  host.innerHTML=`<div class="ei-field-grid"><label>Social cover photo URL<div class="ei-inline-field"><input id="eiSocialPhoto" value="${esc(d.photo||'')}" placeholder="Choose an uploaded photo"><button type="button" id="eiChooseSocialPhoto">Choose material</button></div></label><label>Text alignment<select id="eiSocialAlign"><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label><label>Text color<select id="eiSocialText"><option value="dark">Dark</option><option value="light">Light</option></select></label><label>Language<select id="eiSocialLanguage"><option value="en">English</option><option value="km">Khmer</option><option value="both">Bilingual</option></select></label><label>Monogram<input id="eiSocialMonogram" maxlength="8" value="${esc(d.monogram||'')}"></label><label>Format<select id="eiSocialFormat"><option value="og">Open Graph · 1200×630</option><option value="square">Square · 1080×1080</option><option value="story">Story · 1080×1920</option></select></label></div><div class="ei-social-preview"><canvas id="eiSocialCanvas" aria-label="Social invitation card preview"></canvas></div><div class="ei-share-actions" style="margin-top:14px"><button id="eiCopyLink">Copy public link</button><button id="eiCopyMessage">Copy invitation message</button><a id="eiTelegram" target="_blank" rel="noopener noreferrer">Telegram</a><a id="eiWhatsapp" target="_blank" rel="noopener noreferrer">WhatsApp</a><a id="eiFacebook" target="_blank" rel="noopener noreferrer">Facebook</a><button id="eiRegenerateSocial">Regenerate preview</button><button id="eiDownloadSocial">Download preview</button><button id="eiDownloadPublishedSocial">Download published card</button><button id="eiDownloadQr">Download branded QR</button><button id="eiSaveSocial" class="primary">Save settings</button></div>`;
  const canvas=host.querySelector('#eiSocialCanvas'),format=host.querySelector('#eiSocialFormat');host.querySelector('#eiSocialAlign').value=d.alignment||'center';host.querySelector('#eiSocialText').value=d.textVariant||'dark';host.querySelector('#eiSocialLanguage').value=d.language||state.languageMode||'both';let refreshToken=0;
  const refresh=async()=>{state.socialCard={...(state.socialCard||{}),photo:host.querySelector('#eiSocialPhoto').value.trim(),alignment:host.querySelector('#eiSocialAlign').value,textVariant:host.querySelector('#eiSocialText').value,language:host.querySelector('#eiSocialLanguage').value,monogram:host.querySelector('#eiSocialMonogram').value.trim()};const token=++refreshToken;await draw(canvas,state,format.value);if(token!==refreshToken)return};
  host.querySelectorAll('input,select').forEach(x=>x.addEventListener('input',refresh));refresh();
  host.querySelector('#eiChooseSocialPhoto').onclick=()=>typeof openMaterialPicker==='function'?openMaterialPicker('Choose social cover',(url)=>{host.querySelector('#eiSocialPhoto').value=url;refresh()}):window.uiToast?.('Open Materials and copy an uploaded image URL.','!');
  const url=cleanUrl(serverInvite?.slug?`${location.origin}/i/${serverInvite.slug}`:location.href),msg=`You are invited to ${state.fields?.names||'our event'}${state.fields?.date?` — ${state.fields.date}`:''}. ${url}`;host.querySelector('#eiTelegram').href=`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(msg)}`;host.querySelector('#eiWhatsapp').href=`https://wa.me/?text=${encodeURIComponent(msg)}`;host.querySelector('#eiFacebook').href=`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
  host.querySelector('#eiCopyLink').onclick=()=>navigator.clipboard.writeText(url);host.querySelector('#eiCopyMessage').onclick=()=>navigator.clipboard.writeText(msg);host.querySelector('#eiRegenerateSocial').onclick=refresh;host.querySelector('#eiDownloadSocial').onclick=()=>download(canvas,`invitation-${format.value}.png`);
  host.querySelector('#eiDownloadPublishedSocial').onclick=e=>serverInvite?.slug?downloadUrl(`/api/public/${encodeURIComponent(serverInvite.slug)}/social-card.png?format=${encodeURIComponent(format.value)}`,`invitation-${format.value}.png`,e.currentTarget):window.uiToast?.('Publish the invitation first.','!');
  host.querySelector('#eiDownloadQr').onclick=e=>serverInvite?.slug?downloadUrl(`/api/public/${encodeURIComponent(serverInvite.slug)}/qr-card.png`,'invitation-qr.png',e.currentTarget):window.uiToast?.('Publish the invitation first.','!');
  host.querySelector('#eiSaveSocial').onclick=()=>{refresh();save();window.uiToast?.('Social card settings saved. Republish to update public metadata.','✓')};
}
window.EInviteSocialCard={draw,render,cleanUrl,cardText};
})();;(()=>{'use strict';
const labels={opening:['Opening','✦'],hero:['Main hero','♥'],gallery:['Gallery','▦'],video:['Video','▶'],countdown:['Countdown','◷'],schedule:['Schedule','☷'],custom:['Content blocks','¶'],venue:['Venue','⌖'],contact:['Contact','☎'],wishes:['Guest wishes','♡'],rsvp:['RSVP','✓'],closing:['Closing','◇']};
function enabled(d,key){if(key==='opening')return d.settings?.openingEnabled!==false;if(key==='hero')return true;if(key==='rsvp')return d.settings?.rsvpEnabled!==false;if(key==='wishes')return d.settings?.wishesEnabled===true;if(key==='gallery')return d.settings?.galleryEnabled!==false;if(key==='video')return d.settings?.videoEnabled===true;if(key==='countdown')return d.settings?.countdownEnabled!==false;if(key==='schedule')return d.settings?.scheduleEnabled!==false;if(key==='venue')return d.settings?.venueEnabled!==false;if(key==='contact')return d.settings?.contactEnabled!==false;return true}
function warning(d,key){if(!enabled(d,key))return key==='rsvp'?'Optional RSVP is disabled.':'';if(key==='gallery'&&!Object.values(d.objects||{}).some(o=>o.type==='image'&&o.showInGallery!==false))return'No gallery photos selected.';if(key==='video'&&!d.video?.url)return'Video section is enabled but no video is selected.';if(key==='schedule'&&!(d.schedule||[]).length)return'No schedule items.';if(key==='venue'&&!d.fields?.venue&&!(d.venues||[]).length)return'No venue entered.';if(key==='custom'&&!(d.customBlocks||[]).length)return'No content blocks yet.';return''}
function flow(d){const base=[{key:'opening',token:null},{key:'hero',token:null}],order=Array.isArray(d.sectionOrder)?d.sectionOrder:[];order.filter(token=>!['opening','hero'].includes(String(token))).forEach(token=>base.push(String(token).startsWith('page:')?{key:'page',token}:{key:token,token}));return base}
function render(host){host.innerHTML=`<div class="ei-storyboard-toolbar"><button data-device="mobile" class="primary">Mobile</button><button data-device="tablet">Tablet</button><button data-device="desktop">Desktop</button><button id="eiPlayInvitation">Play invitation</button><span class="hint">Drag items to reorder the existing invitation flow.</span></div><div class="ei-storyboard-list" id="eiStoryList"></div>`;const list=host.querySelector('#eiStoryList');flow(state).forEach((item,index)=>{const page=item.key==='page'?(state.designPages||[]).find(p=>`page:${p.id}`===item.token):null,key=item.key,name=page?.name||labels[key]?.[0]||key,icon=page?'▤':labels[key]?.[1]||'•',on=page?page.enabled!==false:enabled(state,key),warn=page&&!Object.keys(page.objects||{}).length?'Page has no objects.':warning(state,key),card=document.createElement('article');card.className='ei-story-card';card.draggable=!!item.token;card.dataset.token=item.token||'';card.setAttribute('aria-disabled',String(!on));card.innerHTML=`<div class="ei-story-thumb">${icon}</div><div class="ei-story-copy"><strong>${name}</strong><small>${item.token||'Fixed journey stage'}</small>${warn?`<div class="ei-story-warning">${warn}</div>`:''}</div><div class="ei-story-actions">${item.token?'<button data-edit>Edit</button><button data-up aria-label="Move earlier">↑</button><button data-down aria-label="Move later">↓</button>':''}</div>`;if(item.token){card.querySelector('[data-edit]').onclick=()=>{if(key==='page'){activeCanvasId=item.token;apply();document.querySelector('#eiExperienceDialog')?.close()}else document.querySelector('#'+({gallery:'galleryStyle',video:'videoEnabled',countdown:'countdownTitle',schedule:'scheduleText',custom:'customBlocksManager',venue:'venue',contact:'contactPhone',wishes:'wishesEnabled',rsvp:'rsvpEnabled'}[key]||'sectionOrder'))?.focus()};card.querySelector('[data-up]').onclick=()=>move(item.token,-1);card.querySelector('[data-down]').onclick=()=>move(item.token,1);card.ondragstart=e=>e.dataTransfer.setData('text/plain',item.token);card.ondragover=e=>e.preventDefault();card.ondrop=e=>{e.preventDefault();reorder(e.dataTransfer.getData('text/plain'),item.token)}}list.append(card)});host.querySelectorAll('[data-device]').forEach(b=>b.onclick=()=>{host.querySelectorAll('[data-device]').forEach(x=>x.classList.toggle('primary',x===b));previewDevice=b.dataset.device});host.querySelector('#eiPlayInvitation').onclick=()=>play(host)}
function move(token,delta){const a=[...(state.sectionOrder||[])],i=a.indexOf(token),j=i+delta;if(i<0||j<0||j>=a.length)return;[a[i],a[j]]=[a[j],a[i]];state.sectionOrder=a;const field=document.querySelector('#sectionOrder');if(field)field.value=a.join('\n');save();render(document.querySelector('#eiExperienceBody'))}
function reorder(from,to){const a=[...(state.sectionOrder||[])],i=a.indexOf(from),j=a.indexOf(to);if(i<0||j<0||i===j)return;a.splice(j,0,a.splice(i,1)[0]);state.sectionOrder=a;const field=document.querySelector('#sectionOrder');if(field)field.value=a.join('\n');save();render(document.querySelector('#eiExperienceBody'))}
let previewDevice='mobile';function play(host){const url=serverInvite?.slug?`${location.origin}/i/${serverInvite.slug}`:null;if(!url){window.uiToast?.('Publish once to play the full guest journey.','!');return}host.innerHTML=`<div class="ei-storyboard-toolbar"><button id="eiBackStory">← Storyboard</button><strong>${previewDevice[0].toUpperCase()+previewDevice.slice(1)} preview</strong></div><div class="ei-story-preview" data-device="${previewDevice}"><iframe title="Full invitation preview" src="${url}"></iframe></div>`;host.querySelector('#eiBackStory').onclick=()=>render(host)}
function renderChecks(host){const images=Object.values(state.objects||{}).filter(o=>o.type==='image'),animations=Object.values(state.sectionAnimations||{}).filter(a=>a.preset&&a.preset!=='none').length+Object.values(state.objects||{}).filter(o=>o.animation&&o.animation!=='none').length,large=images.filter(o=>Number(o.sizeBytes||0)>2_000_000),missing=images.filter(o=>!Number(o.intrinsicWidth||0)||!Number(o.intrinsicHeight||0)),gallery=images.filter(o=>o.showInGallery!==false),videoSize=Number(state.video?.sizeBytes||0),musicSize=Number(state.music?.sizeBytes||0),checks=[['Oversized images',large.length?`${large.length} image(s) exceed 2 MB.`:'No oversized image metadata found.',!large.length],['Animation density',animations>18?`${animations} animations may feel busy.`:`${animations} active animations.`,animations<=18],['Image dimensions',missing.length?`${missing.length} image(s) lack saved dimensions.`:'Image dimensions look complete.',!missing.length],['Media size',videoSize>25_000_000||musicSize>12_000_000?'Large music/video may load slowly.':'Music and video metadata are within guidance.',!(videoSize>25_000_000||musicSize>12_000_000)],['Gallery weight',gallery.length>18?`${gallery.length} gallery images may be heavy.`:`${gallery.length} gallery images.`,gallery.length<=18]];host.innerHTML=`<h3>Invitation performance check</h3><p>These checks are guidance and do not remove content.</p><div class="ei-performance-list">${checks.map(([n,m,ok])=>`<article class="card ${ok?'ei-check-ok':'ei-check-warn'}"><strong>${ok?'✓':'⚠'} ${n}</strong><p>${m}</p></article>`).join('')}</div>`}
window.EInviteStoryboard={render,renderChecks,flow,enabled,warning};
})();;(()=>{'use strict';
const E=()=>window.EInviteExperience,esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
let previewBase=null,previewKitId='';
function applyAndSave(next,message){previewBase=null;previewKitId='';state=E().migrate(next);apply();save();window.uiToast?.(message,'✦');renderExperience();}
function previewKit(id){if(!previewBase)previewBase=E().copy(state);previewKitId=id;state=E().migrate(E().applyKit(E().copy(previewBase),id));apply();window.uiToast?.('Style preview is temporary until you apply it.','◌');renderExperience('styles');}
function keepPreview(message='Style kit applied'){if(!previewBase)return;previewBase=null;previewKitId='';save();window.uiToast?.(message,'✦');renderExperience('styles');}
function cancelPreview(message='Style preview cancelled'){if(!previewBase)return;state=E().migrate(previewBase);previewBase=null;previewKitId='';apply();if(message)window.uiToast?.(message,'↶');renderExperience('styles');}
function sceneOptions(){return[
 ['soft-monogram','Soft Monogram','#fff7f4','#e8cfd1','#6f3c4a'],['royal-khmer-gate','Royal Khmer Gate','#2f1b10','#8a5b16','#f4d98f'],['silk-curtain','Silk Curtain','#4a111d','#a43d4f','#fff1d5'],['floral-reveal','Floral Reveal','#fffaf8','#e7c5ca','#754c57'],['cinematic-photo','Cinematic Photo','#121212','#555','#fff'],['minimal-editorial','Minimal Editorial','#f4efe7','#ddd2c2','#171717']];}
function stylePanel(){const preview=previewBase?`<div class="ei-kit-preview-banner" role="status"><div><strong>Previewing ${esc(E().kits[previewKitId]?.name||'style kit')}</strong><small>This preview has not been saved.</small></div><button id="eiCancelKitPreview">Cancel</button><button id="eiKeepKitPreview" class="primary">Apply preview</button></div>`:'';return `${preview}<div class="ei-style-grid">${Object.values(E().kits).map(k=>`<article class="ei-style-card ${state.styleKit?.id===k.id?'is-active':''}"><div class="ei-style-preview" style="background:linear-gradient(145deg,${k.preview[2]},${k.preview[1]});color:${k.preview[0]}"><span>${esc(k.name)}</span></div><div class="ei-style-copy"><small>${esc(k.category)}</small><h3>${esc(k.name)}</h3><p>${esc(k.description)}</p><div class="ei-style-actions"><button data-preview-kit="${k.id}">Preview</button><button class="primary" data-apply-kit="${k.id}">Apply</button></div></div></article>`).join('')}</div><div class="ei-exp-footer"><label>Desktop layout <select id="eiDesktopLayout"><option value="ambient-frame">Ambient Frame</option><option value="editorial-split">Editorial Split</option><option value="full-width">Full Width</option></select></label><button id="eiRestoreDefaults">Restore template defaults</button></div>`;}
function openingPanel(){const o=state.openingScene||E().openingDefaults;return `<div class="ei-scene-grid">${sceneOptions().map(([id,name,a,b,t])=>`<button class="ei-scene-card ${o.id===id?'is-active':''}" data-scene="${id}" style="--scene-a:${a};--scene-b:${b};--scene-text:${t}"><span>✦</span><strong>${name}</strong></button>`).join('')}</div><div class="ei-field-grid" style="margin-top:18px"><label>Optional monogram<input id="eiMonogram" maxlength="8" value="${esc(o.monogram||'')}"></label><label>Subtitle<input id="eiOpeningSubtitle" maxlength="120" value="${esc(o.subtitle||'')}"></label><label>Enter button — English<input id="eiEnterText" maxlength="40" value="${esc(o.enterText||'Open invitation')}"></label><label>Enter button — Khmer<input id="eiEnterTextKm" class="khmer-text" lang="km" maxlength="60" value="${esc(o.enterTextKm||'បើកការអញ្ជើញ')}"></label><label>Background color<input id="eiOpeningColor" type="color" value="${/^#[0-9a-f]{6}$/i.test(o.backgroundColor||'')?o.backgroundColor:'#fff8f2'}"></label><label>Background image<div class="ei-inline-field"><input id="eiOpeningImage" value="${esc(o.backgroundImage||'')}" placeholder="Choose an uploaded image"><button type="button" id="eiChooseOpeningImage">Choose material</button></div></label><label>Text variant<select id="eiOpeningText"><option value="dark">Dark text</option><option value="light">Light text</option></select></label><label>Scene duration<input id="eiOpeningDuration" type="range" min="400" max="2500" step="100" value="${Math.max(400,Math.min(2500,Number(o.duration||1100)))}"></label></div><label><input id="eiOpeningDecor" type="checkbox" ${o.decorative!==false?'checked':''}> Decorative elements</label><label><input id="eiOpeningSkip" type="checkbox" ${o.skipAllowed!==false?'checked':''}> Allow skip / enter immediately</label><div class="ei-exp-footer"><button id="eiSaveOpening" class="primary">Save opening scene</button></div>`;}
function renderExperience(tab='styles'){const body=document.querySelector('#eiExperienceBody');if(!body)return;document.querySelectorAll('[data-ei-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.eiTab===tab)));if(tab==='styles')body.innerHTML=stylePanel();else if(tab==='opening')body.innerHTML=openingPanel();else return;bind(body,tab);}
function bind(body,tab){
 if(tab==='styles'){
  body.querySelector('#eiKeepKitPreview')?.addEventListener('click',()=>keepPreview());body.querySelector('#eiCancelKitPreview')?.addEventListener('click',()=>cancelPreview());
  const dl=body.querySelector('#eiDesktopLayout');dl.value=state.desktopGuestLayout||'ambient-frame';dl.onchange=()=>{if(previewBase)cancelPreview('');state.desktopGuestLayout=dl.value;state.styleKit={...(state.styleKit||{}),overrides:{...(state.styleKit?.overrides||{}),desktopLayout:dl.value}};save()};
  body.querySelectorAll('[data-apply-kit]').forEach(b=>b.onclick=()=>{const base=previewBase||state;applyAndSave(E().applyKit(E().copy(base),b.dataset.applyKit),'Style kit applied')});
  body.querySelectorAll('[data-preview-kit]').forEach(b=>b.onclick=()=>previewKit(b.dataset.previewKit));
  body.querySelector('#eiRestoreDefaults').onclick=()=>applyAndSave(E().restoreDefaults(previewBase||state),'Template defaults restored');
 }
 if(tab==='opening'){
  body.querySelectorAll('[data-scene]').forEach(b=>b.onclick=()=>{state.openingScene={...(state.openingScene||E().openingDefaults),id:b.dataset.scene};renderExperience('opening')});
  body.querySelector('#eiOpeningText').value=state.openingScene?.textVariant||'dark';
  body.querySelector('#eiChooseOpeningImage')?.addEventListener('click',()=>typeof openMaterialPicker==='function'?openMaterialPicker('Choose opening background',(url)=>{body.querySelector('#eiOpeningImage').value=url}):window.uiToast?.('Open Materials and copy an uploaded image URL.','!'));
  body.querySelector('#eiSaveOpening').onclick=()=>{state.openingScene={...(state.openingScene||E().openingDefaults),monogram:body.querySelector('#eiMonogram').value.trim(),subtitle:body.querySelector('#eiOpeningSubtitle').value.trim(),enterText:body.querySelector('#eiEnterText').value.trim()||'Open invitation',enterTextKm:body.querySelector('#eiEnterTextKm').value.trim()||'បើកការអញ្ជើញ',backgroundColor:body.querySelector('#eiOpeningColor').value,backgroundImage:body.querySelector('#eiOpeningImage').value.trim(),textVariant:body.querySelector('#eiOpeningText').value,duration:Number(body.querySelector('#eiOpeningDuration').value),decorative:body.querySelector('#eiOpeningDecor').checked,skipAllowed:body.querySelector('#eiOpeningSkip').checked};state.openingStyle=state.openingScene.id;const legacy=document.querySelector('#openingStyle');if(legacy)legacy.value=state.openingStyle;save();window.uiToast?.('Opening scene saved','✦')};
 }
}
function init(){
 if(!document.body.matches('[data-page="editor"],[data-page="index"]'))return;state=E().migrate(state);
 const focus=document.createElement('button');focus.id='eiFocusToggle';focus.className='ei-focus-toggle';focus.textContent='Focus';focus.setAttribute('aria-pressed',localStorage.getItem('einvite-focus-mode')==='true'?'true':'false');focus.onclick=()=>{const on=focus.getAttribute('aria-pressed')!=='true';focus.setAttribute('aria-pressed',String(on));document.body.classList.toggle('ei-focus-mode',on);localStorage.setItem('einvite-focus-mode',String(on))};if(focus.getAttribute('aria-pressed')==='true')document.body.classList.add('ei-focus-mode');
 const launch=document.createElement('button');launch.className='primary ei-experience-launch';launch.textContent='Style & Experience';launch.setAttribute('aria-haspopup','dialog');document.body.append(focus,launch);
 const dialog=document.createElement('dialog');dialog.id='eiExperienceDialog';dialog.className='ei-experience-dialog';dialog.innerHTML=`<div class="ei-exp-head"><div><small>Visual experience</small><h2>Invitation Style & Flow</h2></div><div class="ei-exp-tabs" role="tablist"><button data-ei-tab="styles" aria-selected="true">Style Kits</button><button data-ei-tab="opening">Opening</button><button data-ei-tab="storyboard">Storyboard</button><button data-ei-tab="social">Share Card</button><button data-ei-tab="checks">Design Check</button></div><button id="eiExperienceClose" aria-label="Close experience studio">×</button></div><div class="ei-exp-body" id="eiExperienceBody"></div>`;document.body.append(dialog);
 launch.onclick=()=>{renderExperience('styles');dialog.showModal()};dialog.querySelector('#eiExperienceClose').onclick=()=>dialog.close();dialog.querySelectorAll('[data-ei-tab]').forEach(b=>b.onclick=()=>{const tab=b.dataset.eiTab;if(previewBase&&tab!=='styles')cancelPreview('');if(tab==='storyboard')window.EInviteStoryboard?.render(dialog.querySelector('#eiExperienceBody'));else if(tab==='social')window.EInviteSocialCard?.render(dialog.querySelector('#eiExperienceBody'));else if(tab==='checks')window.EInviteStoryboard?.renderChecks(dialog.querySelector('#eiExperienceBody'));else renderExperience(tab);document.querySelectorAll('[data-ei-tab]').forEach(x=>x.setAttribute('aria-selected',String(x===b)))});dialog.addEventListener('close',()=>{if(previewBase)cancelPreview('');launch.focus()});
 const quick=document.createElement('div');quick.className='ei-quick-toolbar';quick.hidden=true;quick.innerHTML='<button data-q="duplicate" title="Duplicate" aria-label="Duplicate selected object">⧉</button><button data-q="front" title="Bring forward" aria-label="Bring selected object forward">↑</button><button data-q="back" title="Send backward" aria-label="Send selected object backward">↓</button><button data-q="delete" title="Delete" aria-label="Delete selected object">⌫</button><button data-q="advanced" title="Advanced inspector" aria-label="Open advanced inspector">•••</button>';document.body.append(quick);
 document.addEventListener('click',()=>setTimeout(()=>quick.hidden=!document.querySelector('.selected,[data-selected="true"]'),0),true);quick.querySelector('[data-q="delete"]').onclick=()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true}));quick.querySelector('[data-q="duplicate"]').onclick=()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'d',ctrlKey:true,bubbles:true}));quick.querySelector('[data-q="front"]').onclick=()=>document.querySelector('[data-arrange="forward"]')?.click();quick.querySelector('[data-q="back"]').onclick=()=>document.querySelector('[data-arrange="backward"]')?.click();quick.querySelector('[data-q="advanced"]').onclick=()=>document.querySelector('.right')?.scrollIntoView({behavior:'smooth'});
}
window.renderExperience=renderExperience;window.EInviteStyleKitUI={previewKit,keepPreview,cancelPreview};document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();;(()=>{'use strict';
let lastDialogTrigger=new WeakMap();
const focusable='a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function syncPanel(panel,open,trigger){if(!panel)return;panel.hidden=!open;try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(trigger)trigger.setAttribute('aria-expanded',String(open));if(!open&&panel.contains(document.activeElement))trigger?.focus();}
function trapDialogKey(event,dialog){const nodes=[...dialog.querySelectorAll(focusable)].filter(el=>!el.hidden&&el.getClientRects().length&&!el.closest('[inert],[aria-hidden="true"]'));if(!nodes.length)return;if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}
function observeDialogs(root){const dialogs=root?(root.nodeType===1&&root.matches?.('dialog')?[root]:[...(root.querySelectorAll?.('dialog')||[])]):[...document.querySelectorAll('dialog')];dialogs.forEach(dialog=>{if(dialog.dataset.a11yBound)return;dialog.dataset.a11yBound='1';dialog.addEventListener('close',()=>{const trigger=lastDialogTrigger.get(dialog);if(trigger?.isConnected)trigger.focus()});dialog.addEventListener('cancel',event=>{event.preventDefault();dialog.close()})});}
function init(){
 document.querySelectorAll('button:not([aria-label])').forEach(b=>{if(!b.textContent.trim())b.setAttribute('aria-label',b.title||'Action')});
 document.querySelectorAll('img:not([alt])').forEach(img=>img.alt='Invitation image');
 document.querySelectorAll('a > button').forEach(button=>{const a=button.parentElement;a.classList.add(...button.classList);a.setAttribute('role','button');a.textContent=button.textContent;button.remove()});
 document.querySelectorAll('.khmer-picker select').forEach(select=>{if(!select.getAttribute('aria-label')){const label=select.closest('label')?.childNodes?.[0]?.textContent?.trim();if(label)select.setAttribute('aria-label',label)}});
 document.addEventListener('click',event=>{const trigger=event.target.closest('button,[role="button"],a');if(!trigger)return;requestAnimationFrame(()=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&!lastDialogTrigger.has(top))lastDialogTrigger.set(top,trigger);observeDialogs()})},true);
 document.addEventListener('keydown',event=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&event.key==='Tab'){trapDialogKey(event,top);return}if(event.key!=='Escape')return;if(top){top.close();event.preventDefault();event.stopPropagation();return}const openDrawer=[...document.querySelectorAll('[data-drawer-open="true"],.is-open[role="dialog"]')].filter(x=>!x.hidden).at(-1);if(openDrawer){const trigger=document.querySelector(`[aria-controls="${CSS.escape(openDrawer.id)}"]`);syncPanel(openDrawer,false,trigger);openDrawer.dataset.drawerOpen='false';event.preventDefault()}});
 document.querySelectorAll('[aria-controls]').forEach(trigger=>{if(trigger.dataset.a11yManaged==='true')return;const panel=document.getElementById(trigger.getAttribute('aria-controls'));if(!panel)return;const update=()=>{const open=trigger.getAttribute('aria-expanded')==='true'||panel.classList.contains('open')||panel.classList.contains('is-open');try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(!open&&panel.contains(document.activeElement))trigger.focus()};trigger.addEventListener('click',()=>setTimeout(update,0));update()});
 observeDialogs();new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes){if(node.nodeType!==1)continue;if(node.matches?.('dialog')||node.querySelector?.('dialog'))observeDialogs(node)}}).observe(document.body,{childList:true,subtree:true});
}
window.EInviteAccessibility={syncPanel};document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();;(()=>{
'use strict';
const CLIP='einvite-cross-project-clipboard-v13',STYLE='einvite-style-clipboard-v13';
const clone=v=>window.EInviteEditorSchema?.clone?.(v)??JSON.parse(JSON.stringify(v));
const bridge=()=>window.EInviteEditorBridge;
function canvasMap(doc,canvasId=bridge()?.getActiveCanvasId?.()||'hero'){
 if(canvasId==='hero')return doc.objects||(doc.objects={});
 const page=(doc.designPages||[]).find(p=>`page:${p.id}`===canvasId);return page?(page.objects||(page.objects={})):doc.objects;
}
function execute(label,mutator,options={}){if(!bridge())throw Error('Editor bridge is unavailable');return bridge().transact(label,mutator,options)}
function selected(){return bridge()?.getSelectedIds?.()||[]}
function getSelectedObjects(doc){const map=canvasMap(doc);return selected().map(id=>[id,map[id]]).filter(([,o])=>o)}
function copySelection(){const doc=bridge().getState(),items=getSelectedObjects(doc);if(!items.length)return false;const payload={version:1,sourceInvitation:window.EInviteContext?.getInvitationId?.()||'',items:clone(items),copiedAt:Date.now()};localStorage.setItem(CLIP,JSON.stringify(payload));return true}
function pasteSelection(){let payload;try{payload=JSON.parse(localStorage.getItem(CLIP)||'null')}catch{}if(!payload?.items?.length)return false;const newIds=[];execute('Paste objects',doc=>{const map=canvasMap(doc);const offset=3;payload.items.forEach(([oldId,o],index)=>{const id=`obj-${Date.now()}-${index}-${Math.random().toString(36).slice(2,7)}`;const next=clone(o);next.left=shift(next.left,offset+index);next.top=shift(next.top,offset+index);next.groupId='';next.parentGroupId='';map[id]=next;newIds.push(id)});});setTimeout(()=>bridge().select(newIds),0);return true}
function shift(value,delta){const n=parseFloat(value);return Number.isFinite(n)&&String(value).includes('%')?`${Math.min(95,Math.max(0,n+delta))}%`:value}
const STYLE_KEYS=['font','color','fontSize','textAlign','fontWeight','fontStyle','letterSpacing','lineHeight','fillColor','opacity','borderWidth','borderColor','borderRadius','shadowBlur','shadowColor','backgroundEnabled','backgroundColor','backgroundOpacity','blendMode','fillMode','gradientStart','gradientEnd','gradientAngle','textGradientEnabled','textGradientStart','textGradientEnd','textGradientAngle','textStrokeWidth','textStrokeColor','textShadowBlur','textShadowColor','textTransform','imageFit','imageMask','imageFrame','imageBrightness','imageContrast','imageSaturation','imageVibrance','imageTemperature','imageGamma','imageCurveShadows','imageCurveHighlights','imageGrayscale','imageSepia','imageBlur','imageSharpen','imageHue'];
function copyStyle(){const doc=bridge().getState(),first=getSelectedObjects(doc)[0]?.[1];if(!first)return false;localStorage.setItem(STYLE,JSON.stringify(Object.fromEntries(STYLE_KEYS.filter(k=>k in first).map(k=>[k,clone(first[k])]))));return true}
function pasteStyle(){let style;try{style=JSON.parse(localStorage.getItem(STYLE)||'null')}catch{}if(!style)return false;execute('Paste style',doc=>getSelectedObjects(doc).forEach(([,o])=>Object.assign(o,clone(style))));return true}
function setProperty(key,value){execute(`Set ${key}`,doc=>getSelectedObjects(doc).forEach(([,o])=>o[key]=clone(value)));}
function toggle(key,defaultValue=false){execute(`Toggle ${key}`,doc=>getSelectedObjects(doc).forEach(([,o])=>o[key]=!(o[key]??defaultValue)));}
function setConstraints(value){execute('Update responsive constraints',doc=>getSelectedObjects(doc).forEach(([,o])=>o.constraints={...(o.constraints||{}),...value}));}
function saveBreakpoint(name,patch){execute(`Set ${name} breakpoint`,doc=>getSelectedObjects(doc).forEach(([,o])=>{o.breakpoints={...(o.breakpoints||{}),[name]:{...(o.breakpoints?.[name]||{}),...patch}}}));}
function groupNested(){const ids=selected();if(ids.length<2)return null;const gid=`group-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;execute('Group objects',doc=>{const map=canvasMap(doc);ids.forEach(id=>{if(map[id])map[id].groupId=gid});doc.sceneGraph=doc.sceneGraph||{};doc.sceneGraph.groups={...(doc.sceneGraph.groups||{}),[gid]:{id:gid,name:'Group',children:[...ids],parentId:'',locked:false,visible:true}}});return gid}
function tidy(axis='horizontal'){
 const ids=selected();if(ids.length<3)return false;execute('Tidy layout',doc=>{const map=canvasMap(doc);const items=ids.map(id=>[id,map[id]]).filter(([,o])=>o).sort((a,b)=>parseFloat(a[1][axis==='horizontal'?'left':'top'])-parseFloat(b[1][axis==='horizontal'?'left':'top']));const key=axis==='horizontal'?'left':'top',sizeKey=axis==='horizontal'?'width':'height';const start=parseFloat(items[0][1][key]),end=parseFloat(items.at(-1)[1][key])+parseFloat(items.at(-1)[1][sizeKey]);const total=items.reduce((n,[,o])=>n+parseFloat(o[sizeKey]||0),0),gap=Math.max(0,(end-start-total)/(items.length-1));let pos=start;items.forEach(([,o])=>{o[key]=`${pos}%`;pos+=parseFloat(o[sizeKey]||0)+gap})});return true
}
function duplicate(){const doc=bridge().getState(),items=getSelectedObjects(doc);if(!items.length)return false;const newIds=[];execute('Duplicate objects',doc2=>{const map=canvasMap(doc2);items.forEach(([oldId,o],index)=>{const id=`obj-${Date.now()}-${index}-${Math.random().toString(36).slice(2,7)}`;const next=clone(o);next.left=shift(next.left,3+index);next.top=shift(next.top,3+index);map[id]=next;newIds.push(id)})});setTimeout(()=>bridge().select(newIds),0);return true}
window.EInviteCommands={execute,selected,copySelection,pasteSelection,copyStyle,pasteStyle,setProperty,toggle,setConstraints,saveBreakpoint,groupNested,tidy,duplicate};
})();;(()=>{'use strict';
const MODEL=()=>window.TypographyDocumentModel,LAYOUT=()=>window.TypographyLayoutService,bridge=()=>window.EInviteEditorBridge;
const $=s=>document.querySelector(s);let lastTextSelectionSignature='';const el=(tag,attrs={},text='')=>{const node=document.createElement(tag);for(const[k,v]of Object.entries(attrs)){if(k==='class')node.className=v;else if(k==='dataset')Object.assign(node.dataset,v);else if(k==='html')node.innerHTML=v;else if(k.startsWith('aria-'))node.setAttribute(k,v);else if(k in node)node[k]=v;else node.setAttribute(k,v)}if(text)node.textContent=text;return node};
function canvasMap(doc){const canvas=bridge()?.getActiveCanvasId?.()||'hero';if(canvas==='hero')return doc.objects||(doc.objects={});const page=(doc.designPages||[]).find(p=>`page:${p.id}`===canvas);return page?(page.objects||(page.objects={})):doc.objects}
function selectedEntries(doc=bridge()?.getState?.()){const map=canvasMap(doc||{});return(bridge()?.getSelectedIds?.()||[]).map(id=>[id,map[id]]).filter(([,o])=>o&&['text','decoration'].includes(o.type||'text'))}
function firstSelected(doc=bridge()?.getState?.()){return selectedEntries(doc)[0]?.[1]||null}
function preserveViewport(run){const viewport=$('#canvasViewport'),snapshot=viewport?{left:viewport.scrollLeft,top:viewport.scrollTop}:null,result=run();requestAnimationFrame(()=>{if(viewport&&snapshot){viewport.scrollLeft=snapshot.left;viewport.scrollTop=snapshot.top}});return result}
function command(label,mutator){const ids=bridge()?.getSelectedIds?.()||[];return preserveViewport(()=>{const result=window.EInviteCommands.execute(label,doc=>{mutator(doc,selectedEntries(doc));MODEL()?.normalizeDocument(doc,{mutate:true})},{capture:false});requestAnimationFrame(()=>bridge()?.select?.(ids));return result})}
function applyLayout(patch,label='Update typography layout'){const clean=patch&&typeof patch==='object'?patch:{};return command(label,(doc,entries)=>entries.forEach(([,object])=>{if(Object.prototype.hasOwnProperty.call(clean,'width'))object.width=String(clean.width);for(const key of ['textAutoFit','textAutoFitMax','textMinFontSize','textColumns','textColumnGap','textWrap','overflowState'])if(Object.prototype.hasOwnProperty.call(clean,key))MODEL().setOverride(object,key,clean[key]);if(Object.prototype.hasOwnProperty.call(clean,'responsiveOverrides'))object.responsiveOverrides=structuredClone(clean.responsiveOverrides||{})}))}
function labeled(text,control){const label=el('label',{class:'v20-field'});label.append(el('span',{},text),control);return label}
function button(text,id,handler,attrs={}){const b=el('button',{type:'button',id,...attrs},text);b.addEventListener('click',handler);b.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&!event.repeat){event.preventDefault();event.stopPropagation();b.click()}});return b}
function currentStyleId(){return firstSelected()?.textStyleId||'body'}
function styleOptions(select){const doc=bridge()?.getState?.(),catalog=doc?.typography||MODEL()?.defaultCatalog();const sig=catalog.styleOrder.map(id=>id+':'+(catalog.styles[id]?.name||id)).join('|')+'|'+currentStyleId()+'|'+catalog.defaultStyleId;if(select._v20StyleSig===sig)return;select._v20StyleSig=sig;select.replaceChildren(...catalog.styleOrder.map(id=>el('option',{value:id},catalog.styles[id]?.name||id)));select.value=catalog.styles[currentStyleId()]?currentStyleId():catalog.defaultStyleId}
function setStyle(styleId){command('Link text style',(doc,entries)=>entries.forEach(([,o])=>MODEL().linkObject(o,styleId)));refresh()}
function setOverride(key,value,label=`Set ${key}`){command(label,(doc,entries)=>entries.forEach(([,o])=>MODEL().setOverride(o,key,value)));refresh()}
function openForm({title,fields,submitText='Save',onSubmit}){const returnFocus=document.activeElement,titleId=`v20-dialog-title-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,dlg=el('dialog',{class:'v20-dialog','aria-labelledby':titleId}),form=el('form',{method:'dialog',class:'v20-dialog-card'});form.append(el('h2',{id:titleId},title));const controls={};for(const field of fields){let c;if(field.type==='select'){c=el('select',{name:field.name,required:field.required!==false});for(const option of field.options)c.append(el('option',{value:option.value,selected:option.value===field.value},option.label))}else c=el('input',{name:field.name,type:field.type||'text',value:field.value??'',min:field.min,max:field.max,step:field.step,required:field.required!==false});controls[field.name]=c;form.append(labeled(field.label,c))}const status=el('p',{class:'v20-dialog-status',role:'alert'}),actions=el('div',{class:'v20-dialog-actions'}),cancel=button('Cancel','',()=>dlg.close()),submit=el('button',{type:'submit',class:'primary'},submitText);actions.append(cancel,submit);form.append(status,actions);form.addEventListener('submit',event=>{event.preventDefault();try{const values=Object.fromEntries(new FormData(form));onSubmit(values);dlg.close()}catch(error){status.textContent=error.message||String(error)}});dlg.addEventListener('close',()=>{dlg.remove();setTimeout(()=>returnFocus?.focus?.(),0)});dlg.append(form);document.body.append(dlg);dlg.showModal();requestAnimationFrame(()=>Object.values(controls)[0]?.focus());return dlg}
function createStyle(){const doc=bridge().getState();if(Object.keys(doc.typography?.styles||{}).length>=MODEL().MAX_TEXT_STYLES){if(liveRegion)liveRegion.textContent=`Text style limit of ${MODEL().MAX_TEXT_STYLES} reached.`;return}const source=doc.typography.styles[currentStyleId()]||doc.typography.styles.body;openForm({title:'Create text style',fields:[{name:'name',label:'Style name',value:`${source.name} Copy`}],submitText:'Create',onSubmit:({name})=>command('Create text style',d=>{const id=MODEL().createStyle(d,{...source,id:'',name,builtin:false});selectedEntries(d).forEach(([,o])=>MODEL().linkObject(o,id))})})}
function renameStyle(){const doc=bridge().getState(),id=currentStyleId(),style=doc.typography.styles[id];openForm({title:'Rename text style',fields:[{name:'name',label:'Style name',value:style.name}],submitText:'Rename',onSubmit:({name})=>command('Rename text style',d=>MODEL().renameStyle(d,id,name))})}
function duplicateStyle(){const doc=bridge().getState();if(Object.keys(doc.typography?.styles||{}).length>=MODEL().MAX_TEXT_STYLES){if(liveRegion)liveRegion.textContent=`Text style limit of ${MODEL().MAX_TEXT_STYLES} reached.`;return}const id=currentStyleId(),style=doc.typography.styles[id];openForm({title:'Duplicate text style',fields:[{name:'name',label:'New style name',value:`${style.name} Copy`}],submitText:'Duplicate',onSubmit:({name})=>command('Duplicate text style',d=>{const created=MODEL().duplicateStyle(d,id,name);selectedEntries(d).forEach(([,o])=>MODEL().linkObject(o,created))})})}
function deleteStyle(){const doc=bridge().getState(),id=currentStyleId(),style=doc.typography.styles[id],options=doc.typography.styleOrder.filter(x=>x!==id).map(x=>({value:x,label:doc.typography.styles[x].name}));if(style?.builtin&&['body','display','heading','subheading','caption','khmer-ceremonial'].includes(id)){announce('Built-in semantic styles cannot be deleted. Duplicate one to customize it.');return}openForm({title:`Delete “${style.name}”`,fields:[{name:'replacement',label:'Replace linked objects with',type:'select',value:'body',options}],submitText:'Delete and replace',onSubmit:({replacement})=>command('Delete text style',d=>MODEL().deleteStyle(d,id,replacement))})}
function editStyle(){const doc=bridge().getState(),id=currentStyleId(),style=doc.typography.styles[id],pairs=Object.entries(window.EInviteFontRegistry.data.pairings).map(([value,x])=>({value,label:x.label})),choice=items=>items.map(value=>({value,label:String(value).replace(/(^|-)([a-z])/g,(_,a,b)=>`${a?' ':''}${b.toUpperCase()}`)}));openForm({title:`Edit ${style.name}`,fields:[{name:'fontPairing',label:'English / Khmer pairing',type:'select',value:style.fontPairing,options:pairs},{name:'fontSize',label:'Configured size',type:'number',value:style.fontSize,min:8,max:200,step:1},{name:'textAutoFit',label:'Auto-fit',type:'select',value:style.textAutoFit,options:[{value:'none',label:'Off'},{value:'fit',label:'Fit inside box'}]},{name:'textAutoFitMax',label:'Maximum size',type:'number',value:style.textAutoFitMax,min:8,max:200,step:1},{name:'textMinFontSize',label:'Minimum size',type:'number',value:style.textMinFontSize,min:8,max:72,step:1},{name:'fontWeight',label:'Weight',type:'select',value:style.fontWeight,options:[{value:'400',label:'Regular'},{value:'700',label:'Bold'}]},{name:'fontStyle',label:'Style',type:'select',value:style.fontStyle,options:[{value:'normal',label:'Normal'},{value:'italic',label:'Italic'}]},{name:'lineHeight',label:'Line height',type:'number',value:style.lineHeight,min:.8,max:3,step:.05},{name:'letterSpacing',label:'Letter spacing',type:'number',value:style.letterSpacing,min:-2,max:20,step:.5},{name:'colorToken',label:'Color token',type:'select',value:style.colorToken,options:choice(['heading','text','accent','surface','muted','inverse'])},{name:'textAlign',label:'Alignment',type:'select',value:style.textAlign,options:choice(['left','center','right','justify'])},{name:'textVerticalAlign',label:'Vertical alignment',type:'select',value:style.textVerticalAlign,options:choice(['top','middle','bottom'])},{name:'textWrap',label:'Wrapping',type:'select',value:style.textWrap,options:choice(['normal','balance','pretty'])},{name:'textColumns',label:'Columns',type:'number',value:style.textColumns,min:1,max:3,step:1},{name:'textColumnGap',label:'Column gap',type:'number',value:style.textColumnGap,min:0,max:64,step:1},{name:'textPadding',label:'Box padding',type:'number',value:style.textPadding,min:0,max:64,step:1}],onSubmit:v=>command(`Edit ${style.name} style`,d=>MODEL().updateStyle(d,id,{...v,fontSize:Number(v.fontSize),textAutoFitMax:Number(v.textAutoFitMax),textMinFontSize:Number(v.textMinFontSize),lineHeight:Number(v.lineHeight),letterSpacing:Number(v.letterSpacing),textColumns:Number(v.textColumns),textColumnGap:Number(v.textColumnGap),textPadding:Number(v.textPadding)}))})}
function detach(){command('Detach text style',(doc,entries)=>entries.forEach(([,o])=>MODEL().detachObject(doc,o)));refresh()}
function resetOverrides(){command('Reset typography overrides',(doc,entries)=>entries.forEach(([,o])=>MODEL().resetOverride(o)));refresh()}
function reduceText(){command('Reduce text',(doc,entries)=>entries.forEach(([,o])=>{const model=MODEL().resolveObjectTypography(doc,o),key=model.textAutoFit==='fit'?'textAutoFitMax':'fontSize';MODEL().setOverride(o,key,Math.max(model.textMinFontSize||8,(model[key]||model.fontSize)-2))}));refresh()}
function expandBox(){const selected=bridge().getSelectedIds?.()||[],heights={};for(const id of selected){const node=document.querySelector(`.object[data-id="${CSS.escape(id)}"]`),content=node?.querySelector('.content');if(node&&content){const delta=Math.max(0,content.scrollHeight-content.clientHeight)+12;heights[id]=String(node.style.height||'80px').includes('%')?`${Math.min(100,parseFloat(node.style.height)+Math.max(2,delta/844*100))}%`:`${Math.max(parseFloat(node.style.height)||80,(parseFloat(node.style.height)||80)+delta)}px`}}command('Expand text box',(doc,entries)=>entries.forEach(([id,o])=>{if(heights[id])o.height=heights[id]}));refresh()}
function fitNow(){document.querySelectorAll('.object.selected,.object[data-selected="true"]').forEach(node=>window.TypographyLayoutService&&window.EInviteEditorState&&window.dispatchEvent(new CustomEvent('einvite:request-typography-fit',{detail:{node}})));$('#fitTextNow')?.click();announce('Text fitted to the current box without changing the configured document size.')}
let liveRegion;
function announce(message){if(liveRegion)liveRegion.textContent=message}
function inspectorGroup(title,controls){const section=el('section',{class:'v20-inspector-group'});section.append(el('h3',{},title));for(const c of controls)if(c)section.append(c);return section}
function takeControl(id){const control=$('#'+id);return control?.closest('label,.typography-toggle-row,.typography-fit-status,p')||control}
function buildInspector(){const root=$('#typographyControls');if(!root)return;const styleSelect=el('select',{id:'v20TextStyle','aria-label':'Semantic text style'});styleSelect.addEventListener('change',()=>setStyle(styleSelect.value));const styleActions=el('div',{class:'v20-style-actions'});styleActions.append(button('Edit','v20EditStyle',editStyle,{'aria-label':'Edit linked text style'}),button('Create','v20CreateStyle',createStyle,{'data-style-limit-action':'create'}),button('Rename','v20RenameStyle',renameStyle),button('Duplicate','v20DuplicateStyle',duplicateStyle,{'data-style-limit-action':'duplicate'}),button('Delete','v20DeleteStyle',deleteStyle));const linkActions=el('div',{class:'v20-one-click-actions'});linkActions.append(button('Detach','v20DetachStyle',detach),button('Reset override','v20ResetOverride',resetOverrides));const status=el('div',{id:'v20TypographyStatus',class:'v20-status-grid','aria-live':'polite'});status.innerHTML='<span>Maximum <strong data-v20-max>—</strong></span><span>Live <strong data-v20-live>—</strong></span><span>Minimum <strong data-v20-min>—</strong></span><span>Overflow <strong data-v20-overflow>—</strong></span>';const warnings=el('div',{id:'v20TypographyWarnings',class:'v20-warning-list',role:'status','aria-live':'polite'});const oneClick=el('div',{class:'v20-one-click-actions'});oneClick.append(button('Fit','v20Fit',fitNow),button('Expand box','v20ExpandBox',expandBox),button('Reduce text','v20ReduceText',reduceText),button('Reset override','v20ResetOverride2',resetOverrides));const advanced=$('#advancedTextLayout');const vertical=el('select',{id:'v20VerticalAlign','aria-label':'Vertical text alignment'});for(const value of['top','middle','bottom'])vertical.append(el('option',{value},value[0].toUpperCase()+value.slice(1)));vertical.addEventListener('change',()=>setOverride('textVerticalAlign',vertical.value,'Set vertical alignment'));const padding=el('input',{id:'v20TextPadding',type:'range',min:0,max:64,step:1,value:8,'aria-label':'Text box padding'});padding.addEventListener('input',()=>setOverride('textPadding',Number(padding.value),'Set text padding')); const runFont=el('select',{id:'v20RunFont','aria-label':'Font pairing for selected text'});
 for(const[value,entry]of Object.entries(window.EInviteFontRegistry?.data?.pairings||{}))runFont.append(el('option',{value},entry.label||value));
 const runSize=el('select',{id:'v20RunSize','aria-label':'Size for selected text'});
 for(const value of[10,12,14,16,18,20,24,28,32,36,42,48,56,64,72,80])runSize.append(el('option',{value:String(value)},`${value}px`));
 const runStatus=el('p',{id:'v20RunStatus',class:'v20-ok',role:'status','aria-live':'polite'},'Select text inside the object to format one run.');
 const runApply=button('Apply to selected text','v20RunApply',()=>{window.RichTextEditing?.applyRunMark?.({fontPairing:runFont.value,fontSize:Number(runSize.value)});refresh()},{'aria-describedby':'v20RunStatus'});
 runApply.disabled=true;runApply.setAttribute('aria-disabled','true');
 const runActions=el('div',{class:'v20-one-click-actions'});runActions.append(runApply);
 const runGroup=inspectorGroup('Selected text (run)',[labeled('Font pairing',runFont),labeled('Size',runSize),runActions,runStatus]);
 const toggleRow=takeControl('fontBold');const digitCommand=$('#convertDigits'),digitActions=digitCommand?el('div',{class:'v20-one-click-actions'}):null;if(digitActions)digitActions.append(digitCommand);const groups=[inspectorGroup('Text',[labeled('Semantic style',styleSelect),styleActions,linkActions,takeControl('font'),takeControl('color'),takeControl('fontSize'),toggleRow,...(digitActions?[digitActions]:[])]),inspectorGroup('Paragraph',[takeControl('textAlign'),takeControl('letterSpacing'),takeControl('lineHeight'),takeControl('textWrap')]),inspectorGroup('Auto-fit and overflow',[takeControl('textAutoFit'),takeControl('textMinFontSize'),takeControl('fitTextNow'),status,oneClick,warnings,takeControl('typographyV19State')]),inspectorGroup('Columns',[takeControl('textColumns'),takeControl('textColumnGap')]),inspectorGroup('Advanced appearance',[labeled('Vertical alignment',vertical),labeled('Text box padding',padding)]),runGroup];const shell=el('details',{id:'advancedTextLayout',class:'typography-v19-controls v20-typography-shell',open:true});shell.append(el('summary',{class:'v20-shell-summary'},'Typography controls'),...groups);root.replaceChildren(shell);root._v20Advanced={vertical,padding};liveRegion=el('div',{class:'sr-only',role:'status','aria-live':'polite'});shell.append(liveRegion)}
function proxySelect(sourceId,label,handler){const source=$('#'+sourceId),control=source?.cloneNode(true);if(!control)return null;control.removeAttribute('id');control.dataset.v20Proxy=sourceId;control.setAttribute('aria-label',label);control.addEventListener('change',()=>{if(control.value!=='__mixed__')handler(control.value,source)});return control}
function iconButton(icon,label,handler,attrs={}){
 const b=el('button',{type:'button',class:'v20-ico',title:label,'aria-label':label,...attrs},icon);
 b.addEventListener('click',handler);return b
}
function buildToolbar(){
 const host=$('.stage-wrap > .toolbar');if(!host)return;
 const bar=el('div',{id:'v20TypographyToolbar',class:'v20-context-toolbar',role:'toolbar','aria-label':'Text formatting',hidden:true});
 const style=el('select',{id:'v20ToolbarStyle','aria-label':'Text style',title:'Text style'});style.addEventListener('change',()=>setStyle(style.value));
 const font=proxySelect('font','Font for selected text',value=>window.EInviteEditorState?.applyTextProperty?.('font',value));if(font){font.id='v20VisibleFont';font.title='Font';font.prepend(el('option',{value:'__mixed__',disabled:true,hidden:true},'Mixed fonts'))}
 const size=el('input',{id:'v20ToolbarSize',type:'number',min:8,max:200,step:1,inputmode:'numeric','aria-label':'Font size',title:'Font size (px)',class:'v20-size-input'});
 const applySize=value=>{const n=Math.round(Number(value));if(!Number.isFinite(n))return;const clamp=Math.max(8,Math.min(200,n)),object=firstSelected();if(!object)return;size.value=String(clamp);setOverride(object.textAutoFit==='fit'?'textAutoFitMax':'fontSize',clamp,'Set text size')};
 let sizeTimer=0;
 size.addEventListener('input',()=>{clearTimeout(sizeTimer);sizeTimer=setTimeout(()=>applySize(size.value),240)});
 size.addEventListener('change',()=>{clearTimeout(sizeTimer);applySize(size.value)});
 size.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();clearTimeout(sizeTimer);applySize(size.value);size.blur()}});
 const smaller=iconButton('−','Decrease font size',()=>applySize(Number(size.value)-1)),larger=iconButton('+','Increase font size',()=>applySize(Number(size.value)+1));
 const bold=iconButton('B','Bold',()=>{const doc=bridge().getState(),object=firstSelected(doc),model=object&&MODEL().resolveObjectTypography(doc,object);if(model)setOverride('fontWeight',model.fontWeight==='700'?'400':'700','Toggle bold')},{'aria-pressed':'false'}),italic=iconButton('I','Italic',()=>{const doc=bridge().getState(),object=firstSelected(doc),model=object&&MODEL().resolveObjectTypography(doc,object);if(model)setOverride('fontStyle',model.fontStyle==='italic'?'normal':'italic','Toggle italic')},{'aria-pressed':'false'});
 bold.id='v20ToolbarBold';bold.classList.add('v20-ico-letter');italic.id='v20ToolbarItalic';italic.classList.add('v20-ico-letter');italic.querySelector('i')?.remove();italic.innerHTML='<em>I</em>';
 const alignGroup=el('span',{class:'v20-align-group',role:'group','aria-label':'Text alignment'});const alignButtons={};
 for(const[dir,icon,label]of[['left','⇤','Align left'],['center','↔','Align centre'],['right','⇥','Align right'],['justify','≡','Justify']]){
  // data-align is reserved by professional-editor.js for object alignment;
  // using it here made every text-align click align the whole object instead
  // and then stop propagation before this button's handler ran.
  const b=iconButton(icon,label,()=>setOverride('textAlign',dir,'Set text alignment'),{'aria-pressed':'false','data-text-align':dir});alignButtons[dir]=b;alignGroup.append(b)
 }
 const color=el('input',{id:'v20ToolbarColor',type:'color','aria-label':'Text colour',title:'Text colour'});color.addEventListener('input',()=>setOverride('color',color.value,'Set text color'));
 const colorWrap=el('label',{class:'v20-color-wrap',title:'Text colour'});colorWrap.append(el('span',{class:'v20-color-icon','aria-hidden':'true'},'◐'),color);
 const fit=el('span',{class:'v20-fit-pill','aria-live':'polite',title:'Auto-fit state'},'Auto-fit —');
 const toggle=iconButton('⌃','Hide text controls',()=>setCollapsed(!bar.classList.contains('collapsed')),{'aria-expanded':'false','aria-controls':'v20TypographyToolbar'});toggle.id='v20ToolbarToggle';toggle.classList.add('v20-toolbar-toggle');
 const setCollapsed=collapsed=>{bar.classList.toggle('collapsed',collapsed);toggle.setAttribute('aria-expanded',String(!collapsed));toggle.title=collapsed?'Show text controls':'Hide text controls';toggle.textContent=collapsed?'Aa':'⌃';localStorage.setItem('einvite-typography-toolbar-collapsed',collapsed?'1':'0')};
 const divider=()=>el('span',{class:'v20-rule','aria-hidden':'true'});
 const styleWrap=el('label',{class:'v20-compact-select',title:'Text style'});styleWrap.append(el('span',{class:'v20-select-icon','aria-hidden':'true'},'Aa'),style);
 const fontWrap=el('label',{class:'v20-compact-select',title:'Font'});fontWrap.append(el('span',{class:'v20-select-icon','aria-hidden':'true'},'Ag'),font);
 const sizeWrap=el('span',{class:'v20-size-group'});sizeWrap.append(smaller,size,larger);
 bar.append(styleWrap,fontWrap,sizeWrap,divider(),bold,italic,alignGroup,colorWrap,fit,toggle);
 setCollapsed(localStorage.getItem('einvite-typography-toolbar-collapsed')==='1');host.insertAdjacentElement('afterend',bar);bar._refs={style,font,size,bold,italic,align:alignButtons,color,fit,toggle};
}
function buildPreview(){const toolbar=$('#v20TypographyToolbar');if(!toolbar)return;const trigger=button('Responsive preview','v20ResponsivePreview',openPreview,{'aria-haspopup':'dialog','aria-label':'Open responsive typography preview'});trigger.className='v20-responsive-preview-trigger';toolbar.append(trigger)}
function preparePreviewObject(node,doc,object,id,width,mode){
 node.dataset.previewPipeline=mode;node.dataset.objectId=id;node.style.position='absolute';node.style.left=object.left||'0%';node.style.top=String(object.top||'0').includes('%')?object.top:`${parseFloat(object.top||0)/844*100}%`;node.style.width=object.width||'40%';node.style.height=String(object.height||'80px').includes('%')?object.height:`${parseFloat(object.height||80)/844*100}%`;node.style.zIndex=String(object.zIndex||1);const target=mode==='editor'?node.querySelector('.content'):node;if(!target)return;const model=EInviteRenderer.RendererAdapters.project(doc,object,{text:EInviteRenderer.plainText(object.html||'')});target.__typographyModel=model;const result=LAYOUT().fitAndDiagnose(target,model);if(result.diagnostics.overflow)target.classList.add('v20-preview-overflow')}
function renderEditorPreview(container,doc,width){container.replaceChildren();const frame=el('div',{class:'v20-preview-frame v20-preview-editor',dataset:{previewPipeline:'editor'}});frame.style.width=`${width}px`;const live=$('#stage'),stage=live?.cloneNode(true)||el('div',{class:'stage'});stage.removeAttribute('id');stage.classList.add('v20-preview-artboard','v20-editor-preview-artboard');stage.style.width=`${width}px`;stage.style.height=`${Math.round(width*844/390)}px`;stage.querySelectorAll('.selected,[data-selected="true"]').forEach(node=>{node.classList.remove('selected');delete node.dataset.selected});stage.querySelectorAll('.resize-handle,.rotate-handle,.selection-box,.group-bounds').forEach(node=>node.remove());const map=canvasMap(doc);stage.querySelectorAll('.object').forEach(node=>{const id=node.dataset.id,object=map[id];if(!object){node.remove();return}preparePreviewObject(node,doc,object,id,width,'editor')});frame.append(stage);container.append(frame)}
function renderPublicPreview(container,doc,width){container.replaceChildren();const frame=el('div',{class:'v20-preview-frame v20-preview-public',dataset:{previewPipeline:'public'}});frame.style.width=`${width}px`;const stage=el('div',{class:'published-artboard v20-preview-artboard'});stage.style.width=`${width}px`;stage.style.height=`${Math.round(width*844/390)}px`;const map=canvasMap(doc);for(const[id,object]of Object.entries(map).sort((a,b)=>Number(a[1].zIndex||0)-Number(b[1].zIndex||0))){const temp=el('template');temp.innerHTML=EInviteRenderer.renderObject(object,{id,pageHeight:844,document:doc});const node=temp.content.firstElementChild;if(node){stage.append(node);preparePreviewObject(node,doc,object,id,width,'public')}}frame.append(stage);container.append(frame)}
function openPreview(event){
 const trigger=event?.currentTarget?.closest?.('#v20ResponsivePreview')||$('#v20ResponsivePreview'),existing=$('dialog.v20-preview-dialog');
 if(existing){if(!existing.open)existing.showModal();existing.querySelector('button')?.focus();return existing}
 const returnFocus=trigger&&trigger.isConnected?trigger:document.activeElement,doc=MODEL().normalizeDocument(bridge().cloneState(),{mutate:true}),titleId=`v20-preview-title-${crypto.randomUUID?.()||Date.now()}`,dlg=el('dialog',{class:'v20-preview-dialog','aria-labelledby':titleId}),card=el('div',{class:'v20-preview-card'}),head=el('header'),title=el('h2',{id:titleId},'Editor / public responsive typography preview'),close=button('Close','',()=>dlg.close()),widths=el('div',{class:'v20-preview-widths',role:'group','aria-label':'Preview width'}),panes=el('div',{class:'v20-preview-panes'}),editorPane=el('section',{class:'v20-preview-pane','aria-label':'Editor rendering'}),publicPane=el('section',{class:'v20-preview-pane','aria-label':'Public rendering'});
 editorPane.append(el('h3',{},'Actual editor DOM'));publicPane.append(el('h3',{},'Actual public renderer'));
 const editorHost=el('div',{class:'v20-preview-scroll'}),publicHost=el('div',{class:'v20-preview-scroll'});editorPane.append(editorHost);publicPane.append(publicHost);panes.append(editorPane,publicPane);
 const show=width=>{widths.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.width)===width)));renderEditorPreview(editorHost,doc,width);renderPublicPreview(publicHost,doc,width)};
 for(const width of[320,360,390,430,768]){const b=button(String(width),'',()=>show(width),{'aria-pressed':width===390?'true':'false','aria-label':`Preview at ${width} pixels`});b.dataset.width=String(width);widths.append(b)}
 head.append(title,close);card.append(head,widths,panes);dlg.append(card);
 let restored=false;const restore=()=>{if(restored)return;restored=true;dlg.remove();requestAnimationFrame(()=>{const target=returnFocus?.isConnected?returnFocus:$('#stage');target?.focus?.({preventScroll:true});if(target===$('#stage'))window.EInviteEditorBridge?.claimCanvasKeyboard?.()})};
 dlg.addEventListener('close',restore,{once:true});dlg.addEventListener('cancel',event=>{event.preventDefault();dlg.close()});document.body.append(dlg);dlg.showModal();show(390);close.focus();return dlg
}
function buildMobileSummary(){const properties=$('#properties');if(!properties)return;const summary=el('div',{id:'v20MobileSelectionSummary',class:'v20-mobile-selection-summary','aria-live':'polite'});properties.prepend(summary)}
function syncInactiveSurfaces(){document.querySelectorAll('dialog').forEach(node=>{if(node.open){if(node.dataset.v20AutoInert){node.inert=false;node.removeAttribute('inert');delete node.dataset.v20AutoInert}}else if(!node.inert){node.inert=true;node.dataset.v20AutoInert='true'}});document.querySelectorAll('[hidden]').forEach(node=>{if(!node.inert){node.inert=true;node.dataset.v20AutoInert='true'}});document.querySelectorAll('[data-v20-auto-inert]:not([hidden])').forEach(node=>{if(node.tagName!=='DIALOG'||node.open){node.inert=false;node.removeAttribute('inert');delete node.dataset.v20AutoInert}})}
let v20InertTimer=0;function scheduleInactiveSync(){if(v20InertTimer)return;v20InertTimer=setTimeout(()=>{v20InertTimer=0;if(window.EInviteProfessionalEditor?.activeInteraction)return;syncInactiveSurfaces()},220)}
let v20LimitControlCache=null;const v20LimitControls=()=>{if(v20LimitControlCache&&v20LimitControlCache.length&&v20LimitControlCache[0].isConnected)return v20LimitControlCache;v20LimitControlCache=[...document.querySelectorAll('[data-style-limit-action]')];return v20LimitControlCache};
function diagnosticsForSelected(){const node=document.querySelector('.object.selected .content')||document.querySelector('.object .content'),objectNode=node?.closest('.object'),doc=bridge()?.getState?.(),object=firstSelected(doc);if(!node||!object||!doc)return null;const model=MODEL().resolveObjectTypography(doc,object,{text:EInviteRenderer?.plainText?.(object.html||'')||''});node.__typographyModel=model;return{model,result:LAYOUT()?.fitAndDiagnose(node,model),objectNode}}
function refresh(){const doc=bridge()?.getState?.();if(!doc||!MODEL())return;const entries=selectedEntries(doc),selected=entries[0]?.[1]||null,textSelected=!!selected,selectionSignature=entries.map(([id])=>id).sort().join('|');const atStyleLimit=Object.keys(doc.typography?.styles||{}).length>=MODEL().MAX_TEXT_STYLES;v20LimitControls().forEach(control=>{control.disabled=atStyleLimit;control.setAttribute('aria-disabled',String(atStyleLimit));control.title=atStyleLimit?`Maximum ${MODEL().MAX_TEXT_STYLES} text styles reached`:''});const inspector=$('#v20TextStyle'),toolbar=$('#v20TypographyToolbar');if(inspector){styleOptions(inspector);inspector.disabled=!textSelected;const adv=$('#typographyControls')?._v20Advanced;if(adv&&textSelected){const m=MODEL().resolveObjectTypography(doc,selected);adv.vertical.value=m.textVerticalAlign;adv.padding.value=String(m.textPadding)}}if(toolbar){toolbar.hidden=!textSelected;toolbar.setAttribute('aria-hidden',String(!textSelected));if(textSelected){const r=toolbar._refs,models=entries.map(([,object])=>MODEL().resolveObjectTypography(doc,object,{text:EInviteRenderer?.plainText?.(object.html||'')||''})),model=models[0],fonts=[...new Set(models.map(m=>m.font))];styleOptions(r.style);const mixed=fonts.length>1,mixedOption=r.font?.querySelector('option[value="__mixed__"]');if(mixedOption){mixedOption.hidden=!mixed;mixedOption.disabled=!mixed}if(r.font){r.font.value=mixed?'__mixed__':model.font;r.font.dataset.mixed=String(mixed);r.font.setAttribute('aria-label',mixed?'Font for selected text, mixed values':'Font for selected text')}if(document.activeElement!==r.size)r.size.value=model.textAutoFit==='fit'?model.textAutoFitMax:model.fontSize;r.bold.setAttribute('aria-pressed',String(model.fontWeight==='700'));r.italic.setAttribute('aria-pressed',String(model.fontStyle==='italic'));for(const[dir,button]of Object.entries(r.align||{}))button.setAttribute('aria-pressed',String(model.textAlign===dir));r.color.value=/^#[0-9a-f]{6}$/i.test(model.color)?model.color:'#000000';r.fit.textContent=model.textAutoFit==='fit'?`${model.textMinFontSize}–${model.textAutoFitMax}px`:'Auto';r.fit.title=model.textAutoFit==='fit'?`Auto-fit ${model.textMinFontSize}–${model.textAutoFitMax}px`:'Auto-fit off';if(selectionSignature&&selectionSignature!==lastTextSelectionSignature){const activeInspector=document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab||'';const preserveLayerWorkflow=activeInspector==='layers'&&document.body.dataset.keyboardOwner!=='canvas';if(!preserveLayerWorkflow){const responsive=window.EInviteResponsiveLayout,layout=responsive?.mode?.()||'desktop',tab=document.querySelector('[data-inspector-tab="object"]');if(layout==='desktop')tab?.click();else{document.querySelectorAll('[data-inspector-tab]').forEach(node=>node.classList.toggle('active',node===tab));document.querySelectorAll('[data-inspector-pane]').forEach(node=>node.classList.toggle('active',node.dataset.inspectorPane==='object'));localStorage.setItem('einvite-editor-right-tab','object')}}}}}lastTextSelectionSignature=selectionSignature;const d=textSelected?diagnosticsForSelected():null,model=d?.model,diag=d?.result?.diagnostics;const set=(selector,value)=>{const n=$(selector);if(n&&n.textContent!==value)n.textContent=value};set('[data-v20-max]',model?`${model.textAutoFitMax}px`:'—');set('[data-v20-live]',diag?`${diag.computedSize.toFixed(1)}px`:'—');set('[data-v20-min]',model?`${model.textMinFontSize}px`:'—');set('[data-v20-overflow]',diag?(diag.overflow?'Clipped':'Clear'):'—');const warnings=$('#v20TypographyWarnings');const wSig=diag?(diag.overflow?'1':'0')+'|'+(diag.warnings||[]).map(w=>w.severity+':'+w.message).join('|'):'';if(warnings&&warnings.dataset.v20WarnSig!==wSig){warnings.dataset.v20WarnSig=wSig;warnings.replaceChildren(...(diag?.warnings||[]).map(w=>el('p',{class:`v20-warning v20-${w.severity}`},w.message)));if(!diag?.warnings?.length)warnings.append(el('p',{class:'v20-ok'},'No typography accessibility warnings.'))}const run=window.RichTextEditing?.runSelection?.(),runFont=$('#v20RunFont'),runSize=$('#v20RunSize'),runApply=$('#v20RunApply'),runStatus=$('#v20RunStatus');if(runApply){runApply.disabled=!run;runApply.setAttribute('aria-disabled',String(!run))}if(run&&runFont&&run.marks?.fontPairing)runFont.value=run.marks.fontPairing;if(run&&runSize&&run.marks?.fontSize)runSize.value=String(run.marks.fontSize);if(runStatus)runStatus.textContent=run?`${run.locale==='km'?'Khmer':'Latin'} run: ${run.text.slice(0,40)}`:'Select text inside the object to format one run.';
const mobile=$('#v20MobileSelectionSummary');if(mobile)mobile.textContent=textSelected?`${selected.textStyleId||'Body'} · ${model?.fontSize||'—'}px · ${model?.locale==='km'?'Khmer':'English'} · ${diag?.overflow?'Overflow':'Fits'}`:'No text object selected'}
function install(){if(!MODEL()||!LAYOUT()||!bridge())return;buildInspector();buildToolbar();buildPreview();buildMobileSummary();syncInactiveSurfaces();refresh();document.addEventListener('selectionchange',()=>requestAnimationFrame(refresh));window.addEventListener('einvite:editor-command',()=>requestAnimationFrame(refresh));window.addEventListener('einvite:state-applied',()=>requestAnimationFrame(refresh));document.addEventListener('einvite:typography-selection-diagnostics',()=>requestAnimationFrame(refresh));document.addEventListener('einvite:request-typography-fit',event=>{const object=event.detail?.node,content=object?.querySelector('.content'),doc=bridge().getState(),map=canvasMap(doc),data=map[object?.dataset?.id];if(content&&data){const model=MODEL().resolveObjectTypography(doc,data,{text:content.textContent||''});LAYOUT().fitAndDiagnose(content,model)}});let v20RefreshQueued=false;new MutationObserver(()=>{if(v20RefreshQueued)return;v20RefreshQueued=true;requestAnimationFrame(()=>{v20RefreshQueued=false;refresh()})}).observe($('#stage'),{subtree:true,attributes:true,attributeFilter:['class']});new MutationObserver(()=>scheduleInactiveSync()).observe(document.body,{subtree:true,attributes:true,attributeFilter:['hidden','open']});window.EInviteTypographyV20={refresh,openPreview,command,applyLayout,setStyle,setOverride,resetOverrides}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(install,0),{once:true});else setTimeout(install,0);
})();;(()=>{
'use strict';
const q=(s,r=document)=>r.querySelector(s),clone=v=>typeof structuredClone==='function'?structuredClone(v):JSON.parse(JSON.stringify(v));
const STYLE_KEYS={
 text:['font','color','fontSize','textAlign','textVerticalAlign','textPadding','fontWeight','fontStyle','letterSpacing','lineHeight','textAutoFit','textAutoFitMax','textMinFontSize','textWrap','textColumns','textColumnGap','textGradientEnabled','textGradientStart','textGradientEnd','textGradientAngle','textStrokeWidth','textStrokeColor','textShadowBlur','textShadowColor','textTransform'],
 color:['color','fillColor','backgroundEnabled','backgroundColor','backgroundOpacity','borderColor','fillMode','gradientStart','gradientEnd','gradientAngle','textGradientEnabled','textGradientStart','textGradientEnd','textGradientAngle'],
 effect:['opacity','borderWidth','borderRadius','shadowBlur','shadowColor','blendMode','imageFrame','imageMask','imageBrightness','imageContrast','imageSaturation','imageVibrance','imageTemperature','imageGamma','imageGrayscale','imageSepia','imageBlur','imageHue','imageSharpen','imageAdjustmentLayers']
};
function bridge(){return window.EInviteEditorBridge}
function selected(){return window.EInviteCommands?.selected?.()||bridge()?.getSelectedIds?.()||[]}
function canvasMap(doc){const canvas=bridge()?.getActiveCanvasId?.()||'hero';if(canvas==='hero')return doc.objects||(doc.objects={});const page=(doc.designPages||[]).find(p=>`page:${p.id}`===canvas);return page?(page.objects||(page.objects={})):doc.objects||(doc.objects={})}
function ensureStore(doc){doc.sharedStyles=doc.sharedStyles&&typeof doc.sharedStyles==='object'?doc.sharedStyles:{};for(const type of Object.keys(STYLE_KEYS))if(!Array.isArray(doc.sharedStyles[type]))doc.sharedStyles[type]=[];return doc.sharedStyles}
function firstObject(doc){const map=canvasMap(doc),id=selected()[0];return id?map[id]:null}
function status(message){const out=q('#eiSharedStyleStatus');if(!out)return;out.textContent=message;clearTimeout(status.timer);status.timer=setTimeout(()=>out.textContent='',1800)}
function render(){const root=q('#eiSharedStylesV13');if(!root||!bridge())return;const type=q('#eiSharedStyleType').value,doc=bridge().getState(),styles=ensureStore(doc)[type];const select=q('#eiSharedStyleSelect');const previous=select.value;select.innerHTML='<option value="">Select a saved style…</option>'+styles.map(item=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('');if(styles.some(x=>x.id===previous))select.value=previous;q('#eiApplySharedStyle').disabled=!select.value;q('#eiDeleteSharedStyle').disabled=!select.value}
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function capture(type,obj){return Object.fromEntries(STYLE_KEYS[type].filter(key=>obj&&Object.prototype.hasOwnProperty.call(obj,key)).map(key=>[key,clone(obj[key])]))}
function save(){const type=q('#eiSharedStyleType').value,doc=bridge().getState(),obj=firstObject(doc);if(!obj)return alert('Select an object first.');const proposed=type==='text'?'Heading style':type==='color'?'Brand color style':'Effect style',name=prompt('Name this reusable style:',proposed)?.trim();if(!name)return;const values=capture(type,obj);if(!Object.keys(values).length)return alert(`The selected object does not have ${type} styling to save.`);window.EInviteCommands.execute('Save shared style',next=>{const store=ensureStore(next),id=`style-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;store[type].push({id,name:name.slice(0,80),type,values,createdAt:Date.now(),updatedAt:Date.now()})});render();status('Style saved')}
function apply(){const type=q('#eiSharedStyleType').value,id=q('#eiSharedStyleSelect').value;if(!id)return;window.EInviteCommands.execute('Apply shared style',doc=>{const style=ensureStore(doc)[type].find(x=>x.id===id),map=canvasMap(doc);if(!style)return;for(const objectId of selected())if(map[objectId])Object.assign(map[objectId],clone(style.values))});status('Style applied')}
function remove(){const type=q('#eiSharedStyleType').value,id=q('#eiSharedStyleSelect').value;if(!id)return;const current=ensureStore(bridge().getState())[type].find(x=>x.id===id);if(!confirm(`Delete shared style “${current?.name||'this style'}”?`))return;window.EInviteCommands.execute('Delete shared style',doc=>{const store=ensureStore(doc);store[type]=store[type].filter(x=>x.id!==id)});render();status('Style deleted')}
function install(){if(q('#eiSharedStylesV13')||!bridge())return true;const props=q('#properties');if(!props)return false;const section=document.createElement('section');section.id='eiSharedStylesV13';section.className='ei-shared-styles-v13';section.innerHTML=`<h2>Shared styles <span>V13</span></h2><p>Reuse coordinated text, color, and effect styling across pages without flattening individual controls.</p><div class="ei-shared-style-grid"><label>Style type<select id="eiSharedStyleType"><option value="text">Text style</option><option value="color">Color style</option><option value="effect">Effect style</option></select></label><label>Saved style<select id="eiSharedStyleSelect"><option value="">Select a saved style…</option></select></label></div><div class="ei-shared-style-actions"><button type="button" id="eiSaveSharedStyle">Save from selection</button><button type="button" id="eiApplySharedStyle">Apply</button><button type="button" id="eiDeleteSharedStyle" class="danger">Delete</button></div><p id="eiSharedStyleStatus" class="ei-shared-style-status" role="status" aria-live="polite"></p>`;props.append(section);q('#eiSharedStyleType').addEventListener('change',render);q('#eiSharedStyleSelect').addEventListener('change',render);q('#eiSaveSharedStyle').onclick=save;q('#eiApplySharedStyle').onclick=apply;q('#eiDeleteSharedStyle').onclick=remove;window.addEventListener('einvite:editor-command',render);document.addEventListener('selectionchange',()=>setTimeout(render,0));render();return true}
function boot(){if(install())return;const observer=new MutationObserver(()=>{if(install())observer.disconnect()});observer.observe(document.documentElement,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();;(() => {
  'use strict';
  if (window.__einviteMobileEditorV14) return;
  window.__einviteMobileEditorV14 = true;
  const body = document.body;
  const stage = document.getElementById('stage');
  const left = document.querySelector('aside.left');
  const right = document.querySelector('aside.right');
  if (!body || !stage || !left || !right) return;
  // Only add mobile-editor-v14 class at ≤600px where the legacy mobile layout applies
  const mq = matchMedia('(max-width: 600px)');
  function applyMobileClass() {
    if (mq.matches) body.classList.add('mobile-editor-v14');
    else body.classList.remove('mobile-editor-v14');
  }
  applyMobileClass();
  mq.addEventListener('change', applyMobileClass);
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  let returnFocus = null;
  let fitTimer = 0;
  function fitMobileCanvas(delay = 80) {
    if (!mq.matches) return;
    clearTimeout(fitTimer);
    fitTimer = setTimeout(() => {
      const fit = document.getElementById('fitCanvas');
      if (fit && body.dataset.mobileEditorMode === 'canvas') fit.click();
    }, delay);
  }
  function setHiddenState(panel, hidden) {
    if (!panel) return;
    panel.setAttribute('aria-hidden', String(hidden));
    if ('inert' in panel) panel.inert = hidden;
  }
  function currentMode() {
    if (body.classList.contains('mobile-creation-open')) return 'tools';
    if (body.classList.contains('mobile-inspector-open')) return 'quick';
    return 'canvas';
  }
  function sync() {
    const mobile = mq.matches;
    const mode = mobile ? currentMode() : 'desktop';
    body.dataset.mobileEditorMode = mode;
    if (!mobile) {
      body.classList.remove('mobile-creation-open', 'mobile-inspector-open', 'mobile-advanced-open');
      setHiddenState(left, false); setHiddenState(right, false);
    } else {
      setHiddenState(left, mode !== 'tools');
      setHiddenState(right, mode !== 'quick');
    }
    $$('#mobileEditorV14Bar [data-mobile-mode]').forEach(button => {
      const active = button.dataset.mobileMode === mode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
      button.setAttribute('aria-expanded', String(active && mode !== 'canvas'));
    });
  }
  function openMode(mode, trigger) {
    if (!mq.matches) return;
    returnFocus = trigger || document.activeElement;
    body.classList.toggle('mobile-creation-open', mode === 'tools');
    body.classList.toggle('mobile-inspector-open', mode === 'quick');
    body.classList.remove('mobile-advanced-open');
    sync();
    if (mode === 'tools') $('.studio-pane.active input, .studio-pane.active button, .studio-pane.active select, .studio-pane.active textarea, .studio-rail-button')?.focus({preventScroll:true});
    if (mode === 'quick') $('.studio-inspector-pane.active input, .studio-inspector-pane.active button, .studio-inspector-tab')?.focus({preventScroll:true});
    if (mode === 'canvas') {
      stage.focus?.({preventScroll:true});
      fitMobileCanvas();
      if (returnFocus instanceof HTMLElement && returnFocus.id !== 'mobileCanvasMode') returnFocus = null;
    }
  }
  const bar = document.createElement('nav');
  bar.id = 'mobileEditorV14Bar';
  bar.className = 'mobile-editor-v14-bar';
  bar.setAttribute('aria-label', 'Mobile editor controls');
  bar.innerHTML = `
    <button type="button" id="mobileCanvasMode" data-mobile-mode="canvas" aria-pressed="true"><span aria-hidden="true">▣</span><small>Canvas</small></button>
    <button type="button" id="mobileToolsMode" data-a11y-managed="true" data-mobile-mode="tools" aria-controls="mobileCreationPanel" aria-expanded="false"><span aria-hidden="true">＋</span><small>Tools</small></button>
    <button type="button" id="mobileQuickMode" data-a11y-managed="true" data-mobile-mode="quick" aria-controls="mobileQuickInspector" aria-expanded="false"><span aria-hidden="true">✎</span><small>Quick Edit</small></button>
    <button type="button" id="mobilePreviewV14"><span aria-hidden="true">◉</span><small>Preview</small></button>
    <button type="button" id="mobilePublishV14"><span aria-hidden="true">↗</span><small>Publish</small></button>
    <button type="button" id="mobileAdvancedV14" aria-haspopup="dialog"><span aria-hidden="true">•••</span><small>Advanced</small></button>`;
  document.body.append(bar);
  left.id ||= 'mobileCreationPanel';
  right.id ||= 'mobileQuickInspector';
  bar.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.mobileMode) return openMode(button.dataset.mobileMode, button);
    if (button.id === 'mobilePreviewV14') return document.getElementById('previewBtn')?.click();
    if (button.id === 'mobilePublishV14') return document.getElementById('publishBtn')?.click();
    if (button.id === 'mobileAdvancedV14') openAdvanced(button);
  });
  const advanced = document.createElement('dialog');
  advanced.id = 'mobileAdvancedDialogV14';
  advanced.className = 'mobile-advanced-v14';
  advanced.setAttribute('aria-labelledby', 'mobileAdvancedTitleV14');
  advanced.innerHTML = `<div class="mobile-advanced-head"><div><small>Advanced tools</small><h2 id="mobileAdvancedTitleV14">More editor capabilities</h2></div><button type="button" data-close aria-label="Close advanced tools">×</button></div>
    <p>Advanced photo, animation and studio operations stay out of the mobile canvas until you need them.</p>
    <div class="mobile-advanced-grid">
      <button type="button" data-launch=".ei-experience-launch">Style &amp; experience</button>
      <button type="button" data-launch="#eiFocusToggle">Focus mode</button>
      <button type="button" data-launch="#eiTimelineLaunch">Animation timeline</button>
      <button type="button" data-launch="#v13OperationsBtn">Studio operations</button>
      <button type="button" data-launch="#photoEditorLaunch,#openPhotoEditor,[data-photo-editor-open]">Photo editor</button>
      <button type="button" data-launch="#canvasPlusAiTools,.ai-fab,[data-ai-open]">AI tools</button>
      <button type="button" data-inspector="layers">Layers</button>
      <button type="button" data-inspector="sections">Sections & order</button>
    </div>`;
  document.body.append(advanced);
  function openAdvanced(trigger) {
    returnFocus = trigger;
    body.classList.add('mobile-advanced-open');
    advanced.showModal();
    advanced.querySelector('[data-close]')?.focus();
  }
  function closeAdvanced() {
    if (advanced.open) advanced.close();
    body.classList.remove('mobile-advanced-open');
    returnFocus?.focus?.({preventScroll:true});
  }
  advanced.addEventListener('click', event => {
    if (event.target === advanced || event.target.closest('[data-close]')) return closeAdvanced();
    const launch = event.target.closest('[data-launch]');
    if (launch) {
      const target = launch.dataset.launch.split(',').map(x => $(x.trim())).find(Boolean);
      closeAdvanced();
      target?.click();
      return;
    }
    const inspector = event.target.closest('[data-inspector]');
    if (inspector) {
      closeAdvanced();
      openMode('quick', document.getElementById('mobileQuickMode'));
      right.querySelector(`[data-inspector-tab="${CSS.escape(inspector.dataset.inspector)}"]`)?.click();
    }
  });
  advanced.addEventListener('cancel', event => { event.preventDefault(); closeAdvanced(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mq.matches && !advanced.open && currentMode() !== 'canvas') {
      event.preventDefault(); openMode('canvas', document.getElementById('mobileCanvasMode'));
    }
  }, true);
  stage.addEventListener('pointerdown', () => {
    if (mq.matches && currentMode() !== 'canvas') openMode('canvas', document.getElementById('mobileCanvasMode'));
  }, true);
  document.addEventListener('click', event => {
    if (!mq.matches) return;
    if (event.target.closest('[data-studio-tab]')) {
      body.classList.add('mobile-creation-open'); body.classList.remove('mobile-inspector-open'); sync();
    }
    if (event.target.closest('[data-inspector-tab]')) {
      body.classList.add('mobile-inspector-open'); body.classList.remove('mobile-creation-open'); sync();
    }
  }, true);
  mq.addEventListener?.('change', event => { sync(); if (event.matches) fitMobileCanvas(120); });
  addEventListener('resize', () => { sync(); if (mq.matches) fitMobileCanvas(140); }, {passive:true});
  document.addEventListener('einvite:server-connected', () => fitMobileCanvas(160));
  document.addEventListener('einvite:editor-ready', () => fitMobileCanvas(120));
  requestAnimationFrame(() => { if (mq.matches) openMode('canvas', document.getElementById('mobileCanvasMode')); else sync(); });
})();;(() => {
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
let overlaySyncFrame=0,overlaySyncFull=false,overlaySyncLifecycle=null,overlayResizeObserver=null,overlayObservedSizes=new WeakMap(),lastRevealAdjustAt=0;
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
function pxOr(value,total,compute){
const text=String(value??'').trim(); const n=parseFloat(text);
if(!Number.isFinite(n)) return compute();
return text.endsWith('%') ? n/100*total : n;
}
function pct(value,total,bounded=true){ const n=value/Math.max(1,total)*100,resolved=bounded?clamp(n,0,100):finite(n);return `${resolved.toFixed(4).replace(/0+$/,'').replace(/\.$/,'')}%`; }
let worldRectCache=null;
function worldRect(){if(worldRectCache)return worldRectCache;const r=stage.getBoundingClientRect(),zoom=window.EInviteMotion?.viewport?.view.zoom||1;worldRectCache={left:r.left,top:r.top,width:stage.offsetWidth||r.width/zoom,height:stage.offsetHeight||r.height/zoom,zoom};queueMicrotask(()=>{worldRectCache=null});return worldRectCache}
function frameOf(el,sr=worldRect()){
if(!sr.zoom)sr=worldRect();
const style=el.style;
// Read the bounding rect (a forced layout after style writes) only when offsets are unusable.
const w=clamp(pxOr(style.width,sr.width,()=>el.offsetWidth||el.getBoundingClientRect().width),MIN_SIZE,sr.width);
const h=clamp(pxOr(style.height,sr.height,()=>el.offsetHeight||el.getBoundingClientRect().height),MIN_SIZE,sr.height);
return {
id:el.dataset.id,
x:finite(pxOr(style.left,sr.width,()=>el.offsetLeft)),
y:finite(pxOr(style.top,sr.height,()=>el.offsetTop)),
w,h,r:finite(el.dataset.rotation,0)
};
}
function frameOfStyle(el,sr){
    const style=el.style;
    const w=clamp(px(style.width,sr.width,MIN_SIZE),MIN_SIZE,sr.width);
    const h=clamp(px(style.height,sr.height,MIN_SIZE),MIN_SIZE,sr.height);
    return {
    id:el.dataset.id,
    x:finite(px(style.left,sr.width,0)),
    y:finite(px(style.top,sr.height,0)),
    w,h,r:finite(el.dataset.rotation,0)
    };
}
function visibleRect(el,sr=worldRect()){
if(!sr.zoom)sr=worldRect();const r=el.getBoundingClientRect(),z=sr.zoom;
return {x:(r.left-sr.left)/z,y:(r.top-sr.top)/z,w:r.width/z,h:r.height/z,right:(r.right-sr.left)/z,bottom:(r.bottom-sr.top)/z};
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
if(mode==='compositor'&&base){el.dataset.peTransformPreview='true';el.style.transform=`translate3d(${f.x-base.x}px,${f.y-base.y}px,0) rotate(${f.r}deg)`}
else{el.style.left=pct(f.x,sr.width,false);el.style.top=pct(f.y,sr.height,false);el.style.width=pct(f.w,sr.width);el.style.height=pct(f.h,sr.height);el.style.transform=`rotate(${f.r}deg)`}
el.dataset.rotation=String(Math.round(f.r*100)/100);
});
if(interaction){const box=ensureOverlay();box.hidden=true}else{syncOverlay();syncTransformInputs()}
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
},{...(renderOptions.incremental===true?{incremental:true,patch:{type:renderOptions.patchType||'TRANSFORM_ONLY',ids:[...ids]}}:{}),...(renderOptions.coalesceKey?{coalesceKey:renderOptions.coalesceKey,coalesceDelay:500}: {})});
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
function commitFrames(label,frames,nextSelection=frames.map(f=>f.id),options={}){
const sr=worldRect(), safe=frames.map(f=>safeFrame(f,sr));
commit(label,map=>safe.forEach(f=>{const o=map[f.id];if(!o)return;o.left=pct(f.x,sr.width,false);o.top=pct(f.y,sr.height,false);o.width=pct(f.w,sr.width);o.height=pct(f.h,sr.height);o.rotation=Math.round(f.r*100)/100;}),nextSelection,{incremental:true,patchType:'TRANSFORM_ONLY',...options});
}
function revealSelection(){
const v=$('#canvasViewport'),b=overlay;if(!v||!b||b.hidden)return;
const adjust=()=>{if(interaction||b.hidden)return;const now=Date.now();if(now-lastRevealAdjustAt<200)return;const r=v.getBoundingClientRect(),q=b.getBoundingClientRect(),m=48,w=window.visualViewport,l=Math.max(r.left,w?.offsetLeft||0),t=Math.max(r.top,w?.offsetTop||0),rr=Math.min(r.right,(w?.offsetLeft||0)+(w?.width||innerWidth)),bb=Math.min(r.bottom,(w?.offsetTop||0)+(w?.height||innerHeight));let x=0,y=0;if(q.left<l+m)x=q.left-l-m;else if(q.right>rr-m)x=q.right-rr+m;if(q.top<t+m)y=q.top-t-m;else if(q.bottom>bb-m)y=q.bottom-bb+m;if(x||y){lastRevealAdjustAt=now;v.scrollBy(x,y);scheduleOverlaySync()}};
setTimeout(adjust,120);requestAnimationFrame(()=>requestAnimationFrame(adjust));
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
const overlayStyles=(el,next)=>{const st=el.style;for(const k in next){const v=String(next[k]);if(st[k]!==v)st[k]=v}};
function syncOverlay(){
const box=ensureOverlay(),items=selectedElements(); if(!items.length){if(!box.hidden)box.hidden=true;delete box.dataset.peSelectionIds;return}
box.dataset.peSelectionIds=JSON.stringify(items.map(item=>item.dataset.id));
const sr=worldRect(),live=interaction?.type==='move'&&interaction.previewFrames?.length?interaction.previewFrames:null;if(box.hidden)box.hidden=false;
if(live&&interaction.overlayStart){const first=interaction.frames[0],current=live.find(frame=>frame.id===first?.id),scaleX=sr.zoom,scaleY=sr.zoom,dx=(current&&first?current.x-first.x:0)*scaleX+(sr.left-interaction.sr.left),dy=(current&&first?current.y-first.y:0)*scaleY+(sr.top-interaction.sr.top),start=interaction.overlayStart;overlayStyles(box,{left:`${start.left+dx}px`,top:`${start.top+dy}px`,width:`${start.width}px`,height:`${start.height}px`,transform:start.transform});box.classList.toggle('pe-tiny-selection',start.width<56||start.height<56);}
else if(items.length===1){const f=frameOf(items[0],sr);overlayStyles(box,{left:`${sr.left+f.x*sr.zoom}px`,top:`${sr.top+f.y*sr.zoom}px`,width:`${f.w*sr.zoom}px`,height:`${f.h*sr.zoom}px`,transform:`rotate(${f.r}deg)`});box.classList.toggle('pe-tiny-selection',f.w<56||f.h<56);}
else {const b=visibleBBox(items,sr);overlayStyles(box,{left:`${sr.left+b.x*sr.zoom}px`,top:`${sr.top+b.y*sr.zoom}px`,width:`${b.w*sr.zoom}px`,height:`${b.h*sr.zoom}px`,transform:'none'});box.classList.toggle('pe-tiny-selection',b.w<56||b.h<56);}
const lbl=$('.pe-selection-label',box),lblText=items.length>1?`${items.length} objects`:items[0].dataset.layerName||items[0].dataset.objectType||'Object';if(lbl&&lbl.textContent!==lblText)lbl.textContent=lblText;
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
const sr=worldRect();let f;if(items.length===1)f=frameOf(items[0],sr);else{const b=visibleBBox(items,sr);f={...b,r:0}};
for(const key of ['x','y','w','h','r']){const input=$(`[data-pe-transform="${key}"]`,panel);if(input&&document.activeElement!==input)input.value=String(Math.round(f[key]*10)/10)}
}
function applyNumericTransform(key,value){
const items=selectedElements().filter(el=>el.dataset.locked!=='true');if(!items.length)return;
const sr=worldRect(),frames=items.map(el=>frameOf(el,sr)),old=bbox(frames);let next={...old};
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
const toggle=event.target.closest('[data-pe-toggle]');if(toggle){settings[toggle.dataset.peToggle]=!settings[toggle.dataset.peToggle];if(toggle.dataset.peToggle==='guides')bridge().transact('Show guides / បង្ហាញបន្ទាត់ណែនាំ',doc=>{doc.editorModel={...(doc.editorModel||{}),guidesVisible:settings.guides}},{render:false,capture:false});saveSettings();return}
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
if(window.EInviteMotion?.measurements){if(axis==='clear')window.EInviteMotion.measurements.clearGuides();else{const size=window.EInviteMotion.viewport.size;window.EInviteMotion.measurements.addGuide(axis,(axis==='x'?size.width:size.height)/2)}return}
const doc=bridge().getState();doc.editorModel=doc.editorModel||{};const current=clone(doc.editorModel.guides||{x:[],y:[]});
if(axis==='clear'){current.x=[];current.y=[]}
else {const raw=prompt(`Guide position in percent (0–100):`,'50');if(raw===null)return;const n=clamp(parseFloat(raw),0,100);current[axis]=[...new Set([...(current[axis]||[]),n])].sort((a,b)=>a-b)}
commit('Update guides',(map,nextDoc)=>{nextDoc.editorModel={...(nextDoc.editorModel||{}),guides:current}},selectedIds());
}
function renderUserGuides(){
if(window.EInviteMotion?.measurements){window.EInviteMotion.measurements.render();return}
$$('.pe-user-guide',stage).forEach(el=>el.remove());if(!settings.guides)return;
const guideData=bridge().getState().editorModel?.guides||{x:[],y:[]};
(guideData.x||[]).forEach(v=>{const el=document.createElement('div');el.className='pe-user-guide pe-vertical';el.style.left=`${v}%`;stage.append(el)});
(guideData.y||[]).forEach(v=>{const el=document.createElement('div');el.className='pe-user-guide pe-horizontal';el.style.top=`${v}%`;stage.append(el)});
}
function clearSmartGuides(){window.EInviteMotion?.measurements?.clear();$$('.pe-smart-guide,.pe-measurement',stage).forEach(el=>el.remove());}
function smartGuide(axis,position,label=''){
const el=document.createElement('div');el.className=`pe-smart-guide pe-${axis}`;if(axis==='vertical')el.style.left=`${position}px`;else el.style.top=`${position}px`;stage.append(el);
if(label){const tag=document.createElement('span');tag.className='pe-measurement';tag.textContent=label;if(axis==='vertical')tag.style.left=`${position+4}px`;else tag.style.top=`${position+4}px`;stage.append(tag)}
}
function snapDelta(selectionBox,others,dx,dy,sr){
if(window.EInviteMotion?.snap){if(!settings.snap){window.EInviteMotion.measurements.clear();return{dx,dy}}const result=window.EInviteMotion.snap.resolve({box:selectionBox,others,dx,dy,page:sr,zoom:sr.zoom||1,guides:bridge().getState().editorModel?.guides,grid:settings.grid?settings.gridSize:0,previous:interaction?.snapHits||{}});if(interaction)interaction.snapHits=result.hits;window.EInviteMotion.measurements.show(result);return result}
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
const sr=worldRect(),frames=items.map(el=>frameOf(el,sr)),selection=items.length>1?visibleBBox(items,sr):bbox(frames),scrollLeft=viewport?.scrollLeft||0,scrollTop=viewport?.scrollTop||0;
const overlayBox=ensureOverlay(),overlayLeft=parseFloat(overlayBox.style.left),overlayTop=parseFloat(overlayBox.style.top),overlayWidth=parseFloat(overlayBox.style.width),overlayHeight=parseFloat(overlayBox.style.height),overlayRect=Number.isFinite(overlayLeft)&&Number.isFinite(overlayTop)&&Number.isFinite(overlayWidth)&&Number.isFinite(overlayHeight)?null:overlayBox.getBoundingClientRect(),overlayStart={left:finite(overlayLeft,overlayRect?overlayRect.left:0),top:finite(overlayTop,overlayRect?overlayRect.top:0),width:finite(overlayWidth,overlayRect?overlayRect.width:0),height:finite(overlayHeight,overlayRect?overlayRect.height:0),transform:overlayBox.style.transform||'none'};
const captureOwner=event.target.closest?.('[data-pe-handle]')?overlayBox:stage;
const ids=Object.freeze(items.map(el=>el.dataset.id));
interaction={type,handle,pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,sr,frames,selection,ids,moved:false,captureOwner,overlayStart,others:null,scrollLeft,scrollTop};
if(!sameIdSet(selectedIds(),ids))bridge().select([...ids]);
if(type==='rotate'){interaction.center={x:selection.x+selection.w/2,y:selection.y+selection.h/2};interaction.startAngle=Math.atan2(event.clientY-(sr.top+interaction.center.y*sr.zoom),event.clientX-(sr.left+interaction.center.x*sr.zoom));}
clearSmartGuides();event.stopImmediatePropagation();
}
function edgePan(event){
if(!viewport||interaction?.type!=='move')return;const r=viewport.getBoundingClientRect(),e=56,s=24;viewport.scrollBy(event.clientX<r.left+e?-s:event.clientX>r.right-e?s:0,event.clientY<r.top+e?-s:event.clientY>r.bottom-e?s:0);
}
function moveInteraction(event){
if(!interaction||event.pointerId!==interaction.pointerId)return;event.preventDefault();event.stopImmediatePropagation();interaction.moved=true;
const i=interaction;holdInteractionSelection(i);const dx=(event.clientX-i.startX+(viewport?.scrollLeft||0)-i.scrollLeft)/i.sr.zoom,dy=(event.clientY-i.startY+(viewport?.scrollTop||0)-i.scrollTop)/i.sr.zoom;
if(i.type==='move'){
const snapped=event.altKey?{dx,dy}:snapDelta(i.selection,i.others??(i.others=(settings.snap?activeObjects().filter(el=>!i.ids.includes(el.dataset.id)).slice(0,100).map(el=>frameOfStyle(el,i.sr)):[])),dx,dy,i.sr);
previewFrames(i.frames.map(f=>({...f,x:f.x+snapped.dx,y:f.y+snapped.dy})),i.sr,'compositor');return;
}
if(i.type==='rotate'){
let delta=(Math.atan2(event.clientY-(i.sr.top+i.center.y*i.sr.zoom),event.clientX-(i.sr.left+i.center.x*i.sr.zoom))-i.startAngle)*180/Math.PI;if(event.shiftKey)delta=Math.round(delta/15)*15;const rad=delta*Math.PI/180;
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
if(i.captureOwner?.hasPointerCapture?.(i.pointerId))i.captureOwner.releasePointerCapture(i.pointerId);
if(i.moved)window.EInviteMotion.viewport?.endGesture();
if(cancelled){i.transaction?.cancel();syncAll();window.EInvitePerformance?.record?.('gestureCancelled',1,{type:i.type});return}
if(window.__DEBUG_RESIZE)console.log('END_DEBUG',JSON.stringify({type:i.type,moved:i.moved,ids:i.ids,frames,selection:i.selection,previewFramesLen:i.previewFrames?.length}));if(i.moved){try{commitFrames(i.type==='move'?'Move objects':i.type==='rotate'?'Rotate objects':'Resize objects',frames,i.ids);i.transaction?.commit()}catch(error){i.transaction?.cancel();throw error}}else syncAll();
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
if(event.button!==0||window.EInviteCanvasPanController?.held||$('#panToggle')?.getAttribute('aria-pressed')==='true'||event.target.closest?.('[contenteditable=true]'))return;
if(interaction){event.preventDefault();event.stopImmediatePropagation();return}
const handle=event.target.closest('[data-pe-handle]');if(handle){event.preventDefault();event.stopImmediatePropagation();startInteraction(handle.dataset.peHandle==='rotate'?'rotate':'resize',event,handle.dataset.peHandle,overlaySelectionIds());return}
if(event.target.closest?.('.object.v24-crop-active'))return;
const object=event.target.closest('.object');
if(object&&stage.contains(object)){
if(object.dataset.locked==='true'){
const prior=document.querySelector('[data-inspector-tab].active')?.dataset.inspectorTab||'';
setTimeout(()=>{if(prior)document.querySelector(`[data-inspector-tab="${CSS.escape(prior)}"]`)?.click()},20);
event.preventDefault();event.stopImmediatePropagation();return
}
if(event.shiftKey||event.ctrlKey||event.metaKey){toggleSelection([object.dataset.id]);event.preventDefault();event.stopImmediatePropagation();return}
if(!selectedIds().includes(object.dataset.id))setSelection([object.dataset.id]);
event.preventDefault();startInteraction('move',event);return;
}
if(event.target.closest('button,input,select,textarea,[contenteditable=true]'))return;
startMarquee(event);
}
const pointerBatcher=window.EInviteMotion.createFrameBatcher((a,b)=>b,value=>{if(interaction?.type==='marquee')moveMarquee(value);else moveInteraction(value)});
window.EInviteLifecycle?.add?.(()=>pointerBatcher.destroy());
function pointerMove(event){
const i=interaction;if(!i||event.pointerId!==i.pointerId)return;
if(i.type!=='marquee'&&!i.moved){if(Math.abs(event.clientX-i.startX)<3&&Math.abs(event.clientY-i.startY)<3)return;i.moved=true;i.transaction=bridge().beginUndoTransaction?.('Transform objects / បម្លែងវត្ថុ');document.body.classList.add('pe-pointer-interaction');document.body.dataset.pePointerInteraction=i.type;window.EInviteMotion.viewport?.beginGesture();if(event.pointerType!=='touch')i.captureOwner.setPointerCapture?.(event.pointerId)}
event.preventDefault();event.stopImmediatePropagation();pointerBatcher.accumulate(event);
}
function pointerUp(event){pointerBatcher.flush();if(interaction?.type==='marquee')endMarquee(event);else endInteraction(event,event.type==='pointercancel')}
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
const priorTree=panel.querySelector('.pe-layer-tree'),active=document.activeElement,activeRow=active?.closest?.('.pe-layer-row'),activeIdentity=layerFocusIdentity||layerIdentity(activeRow),searchFocused=active?.matches?.('[data-pe-layer-search]'),searchSelection=searchFocused?[active.selectionStart,active.selectionEnd]:null;
const doc=bridge().getState(),map=activeMap(doc),gs=groups(doc),selection=new Set(selectedIds()),query=panel.querySelector('[data-pe-layer-search]')?.value||'';
const structure=JSON.stringify([Object.entries(map).map(([id,o])=>[id,o.zIndex,o.visible,o.locked,o.type,o.layerName,o.html]),Object.entries(gs).map(([id,g])=>[id,g.name,g.parentId,g.children]),[...expandedGroups].sort(),query,layerAnnouncement]),selectionKey=[...selection].sort().join('|');
if(panel._peLayerStructure===structure&&panel.querySelector('.pe-layer-tree')){
// Structure unchanged: a selection-only change just moves the active highlight, so skip the full tree rebuild.
if(panel._peLayerSelection!==selectionKey){panel.querySelectorAll('.pe-layer-row').forEach(row=>{const ids=String(row.dataset.layerIds||'').split(',').filter(Boolean);row.classList.toggle('active',ids.some(id=>selection.has(id)))});panel._peLayerSelection=selectionKey}
return;
}
const priorScroll=priorTree?.scrollTop||0;panel.innerHTML=`<div class="pe-layer-toolbar"><input data-pe-layer-search type="search" placeholder="Search layers" value=""><button data-pe-arrange="front" title="Bring to front">Front</button><button data-pe-arrange="forward" title="Bring forward">↑</button><button data-pe-arrange="backward" title="Send backward">↓</button><button data-pe-arrange="back" title="Send to back">Back</button></div><div class="pe-layer-tree" role="tree" aria-label="Layers"></div><div class="pe-layer-live" aria-live="polite" aria-atomic="true"></div>`;
const search=$('[data-pe-layer-search]',panel);search.value=query;search.addEventListener('focus',clearRememberedLayerFocus);const tree=$('.pe-layer-tree',panel);tree.scrollTop=priorScroll;
const objectOrder=Object.keys(map).sort((a,b)=>finite(map[b].zIndex)-finite(map[a].zIndex));const objectInGroup=new Set(Object.values(gs).flatMap(g=>g.children||[]).filter(id=>map[id]));const topGroups=Object.keys(gs).filter(id=>!gs[id].parentId);
const layerRank=id=>map[id]?finite(map[id].zIndex):Math.max(0,...descendantIds(id,gs).map(child=>finite(map[child]?.zIndex)));
function matches(id,isGroup){const label=(isGroup?gs[id]?.name:layerTitle(id,map[id]))||'';return !query||String(label).toLowerCase().includes(query.toLowerCase())}
function objectRow(id,depth){const o=map[id];if(!o||!matches(id,false))return null;const row=document.createElement('div');row.className=`pe-layer-row${selection.has(id)?' active':''}`;row.dataset.layerId=id;row.dataset.layerIds=id;row.style.setProperty('--depth',depth);row.setAttribute('role','treeitem');row.setAttribute('aria-keyshortcuts','F2 Alt+ArrowUp Alt+ArrowDown Alt+Home Alt+End');row.innerHTML=`<span class="pe-layer-indent"></span><button data-layer-visible aria-label="${o.visible===false?'Show':'Hide'} layer">${o.visible===false?'○':'◉'}</button><button class="pe-layer-main"><span>${o.type==='image'?'▧':o.type==='shape'?'□':'T'}</span><strong></strong></button><button data-layer-lock aria-label="${o.locked?'Unlock':'Lock'} layer">${o.locked?'🔒':'◇'}</button><button data-layer-more aria-label="Layer actions">⋯</button><button data-layer-drag aria-label="Reorder layer" title="Drag to reorder">↕</button>`;row.querySelector('strong').textContent=layerTitle(id,o);wireLayerRow(row,id,false);return row}
function groupRow(id,depth){const g=gs[id];if(!g)return null;const ids=descendantsForLayer(id),match=matches(id,true)||ids.some(child=>matches(child,false));if(!match)return null;const wrap=document.createElement('div');wrap.className='pe-layer-group';const row=document.createElement('div');row.className=`pe-layer-row pe-group-row${ids.some(x=>selection.has(x))?' active':''}`;row.dataset.groupId=id;row.dataset.layerIds=ids.join(',');row.style.setProperty('--depth',depth);row.setAttribute('role','treeitem');row.setAttribute('aria-keyshortcuts','F2 Alt+ArrowUp Alt+ArrowDown Alt+Home Alt+End');const open=expandedGroups.has(id);row.innerHTML=`<span class="pe-layer-indent"></span><button data-group-expand aria-label="${open?'Collapse':'Expand'} group">${open?'▾':'▸'}</button><button data-layer-visible aria-label="${ids.every(x=>map[x]?.visible===false)?'Show':'Hide'} group">${ids.every(x=>map[x]?.visible===false)?'○':'◉'}</button><button class="pe-layer-main"><span>◫</span><strong></strong></button><button data-layer-lock aria-label="Toggle group lock">${ids.every(x=>map[x]?.locked)?'🔒':'◇'}</button><button data-layer-more aria-label="Group actions">⋯</button><button data-layer-drag aria-label="Reorder group" title="Drag to reorder">↕</button>`;row.querySelector('strong').textContent=g.name||'Group';wireLayerRow(row,id,true);wrap.append(row);if(open){const childBox=document.createElement('div');childBox.className='pe-layer-children';(g.children||[]).slice().sort((a,b)=>layerRank(b)-layerRank(a)).forEach(child=>{const node=gs[child]?groupRow(child,depth+1):objectRow(child,depth+1);if(node)childBox.append(node)});wrap.append(childBox)}return wrap}
const topEntries=[...topGroups.map(id=>({id,group:true,rank:layerRank(id)})),...objectOrder.filter(id=>!objectInGroup.has(id)).map(id=>({id,group:false,rank:layerRank(id)}))].sort((a,b)=>b.rank-a.rank);topEntries.forEach(entry=>{const node=entry.group?groupRow(entry.id,0):objectRow(entry.id,0);if(node)tree.append(node)});
search.addEventListener('input',()=>renderLayers(panel));panel.querySelectorAll('[data-pe-arrange]').forEach(b=>b.onclick=()=>{rememberLayerFocus(layerIdentity(document.activeElement?.closest?.('.pe-layer-row')));reorder(selectedIds(),b.dataset.peArrange);announceLayer(`Selected layers moved ${b.title.toLowerCase()}.`)});$('.pe-layer-live',panel).textContent=layerAnnouncement;
tree.scrollTop=priorScroll;if(searchFocused){search.focus();if(searchSelection)search.setSelectionRange(...searchSelection)}else if(activeIdentity)restoreLayerFocus(panel,activeIdentity);
panel._peLayerStructure=structure;panel._peLayerSelection=selectionKey;
} finally {layersRendering=false}
}
function plainText(html){const el=document.createElement('div');el.innerHTML=html||'';return(el.textContent||'').trim().slice(0,36)}
function layerTitle(id,o){
  // Legacy imports stored the placeholder word "Layer" as a real name; treat
  // generic type words as empty so the live content can supply a useful label.
  if(o?.layerName&&!/^(layer|object|text|image|shape)$/i.test(String(o.layerName).trim()))return o.layerName
  // Rich-text objects often store html as a rendered structure; the live
  // canvas node is the reliable source for a human layer label.
  const node=document.querySelector(`#stage .object[data-id="${window.CSS?.escape?CSS.escape(id):String(id)}"] .content`)
  const live=(node?.innerText||'').replace(/\s+/g,' ').trim()
  if(live)return live.slice(0,36)
  if(o?.type==='image')return 'Image'
  if(o?.type==='shape')return 'Shape'
  return plainText(o?.html)||id||'Layer'
}
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
function nudge(dx,dy){const items=selectedElements().filter(el=>el.dataset.locked!=='true');if(!items.length)return;const sr=worldRect(),frames=items.map(el=>{const f=frameOf(el,sr);return{...f,x:f.x+dx,y:f.y+dy}});commitFrames('Nudge objects / ផ្លាស់ទីវត្ថុ',frames,frames.map(f=>f.id),{coalesceKey:`motion-nudge:${selectedIds().join(',')}`})}
function cancelInteraction(){if(!interaction)return false;pointerBatcher.flush();const event={pointerId:interaction.pointerId,preventDefault(){},stopImmediatePropagation(){}};if(interaction.type==='marquee'){marquee?.remove();marquee=null;interaction=null}else endInteraction(event,true);return true}
function interceptLegacyButtons(event){
const button=event.target.closest('button');if(!button)return;let handled=true;
if(button.id==='groupObjects')groupSelection();else if(button.id==='ungroupObjects')ungroupSelection();else if(button.id==='duplicate')duplicateSelection();else if(button.id==='deleteBtn')deleteSelection();else if(button.id==='bringForward')reorder(selectedIds(),'forward');else if(button.id==='sendBackward')reorder(selectedIds(),'backward');else if(button.dataset.align)alignSelection(button.dataset.align);else if(button.dataset.distribute)distributeSelection(button.dataset.distribute);else handled=false;
if(handled){event.preventDefault();event.stopImmediatePropagation()}
}
let heavySyncFrame=0;
function syncAll(){ensureTransformPanel();ensureAssistancePanel();ensureMobileContextBar();syncTransformInputs();syncOverlay();syncMobileContextBar();if(heavySyncFrame)return;heavySyncFrame=requestAnimationFrame(()=>{heavySyncFrame=0;renderUserGuides();renderLayers()})}
function scheduleOverlaySync(full=false){
if(full===true)overlaySyncFull=true;
if(overlaySyncFrame)return;
overlaySyncFrame=setTimeout(()=>{overlaySyncFrame=0;const runFull=overlaySyncFull;overlaySyncFull=false;if(runFull)syncAll();else{syncOverlay();syncTransformInputs()}},0);
}
function teardownOverlaySync(){
if(overlaySyncFrame)clearTimeout(overlaySyncFrame);overlaySyncFrame=0;overlaySyncFull=false;
overlayResizeObserver?.disconnect();overlayResizeObserver=null;overlayObservedSizes=new WeakMap();
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
if('ResizeObserver'in window){
// Change detection on the observed boxes. The observer watches #stage and
// #viewport, and the sync it schedules re-renders the layers panel and the
// overlay — which resizes the stage. Without this guard the observer re-arms
// itself on its own output, so the synchronous work runs at frame rate instead of
// when the canvas actually changes size. Measured: this loop accounts for the
// 1,359 ms / 13 calls the previous pass attributed to the syncAll rAF, and this is
// the same self-triggering shape as the mutation-observer defect fixed in
// src/js/editor/ui-components.js, which went 3,429 ms -> 689 ms by the same means.
// A genuine resize still notifies: the box key is compared per observed element.
overlayResizeObserver=new ResizeObserver(entries=>{let boxChanged=false;for(const entry of entries){const box=entry.borderBoxSize&&entry.borderBoxSize[0];const key=box?`${Math.round(box.inlineSize)}x${Math.round(box.blockSize)}`:`${Math.round(entry.contentRect.width)}x${Math.round(entry.contentRect.height)}`;if(overlayObservedSizes.get(entry.target)!==key){overlayObservedSizes.set(entry.target,key);boxChanged=true}}if(boxChanged)scheduleOverlaySync()});overlayResizeObserver.observe(stage);if(viewport)overlayResizeObserver.observe(viewport)}
}
function boot(){
window.EInviteProfessionalEditor={version:17,ownsPointerInteractions:true,ownsKeyboardInteractions:true,renderLayers,sync:syncAll,get commandSequence(){return commandSequence},get lastCommand(){return lastCommand?clone(lastCommand):null},get activeInteraction(){return interaction?{type:interaction.type,handle:interaction.handle,pointerId:interaction.pointerId,ids:interaction.ids?[...interaction.ids]:[]}:null},commands:{cancelInteraction,alignSelection,distributeSelection,groupSelection,ungroupSelection,copySelection,cutSelection,pasteSelection,pastePayload,validateClipboardPayload,duplicateSelection,deleteSelection,reorder,reorderRelative,nudge,clearSelection,setSelection,setObjectFlag,undoSelection,redoSelection}};
document.body.classList.add('professional-editor-v17');stage.style.overflow='visible';ensureOverlay();ensureTransformPanel();ensureAssistancePanel();ensureMobileContextBar();applyAssistanceState();installOverlaySync();
stage.addEventListener('pointerdown',pointerDown,true);window.addEventListener('pointermove',event=>{if(interaction)pointerMove(event)},true);window.addEventListener('pointerup',event=>{if(interaction)pointerUp(event)},true);window.addEventListener('pointercancel',event=>{if(interaction)pointerUp(event)},true);
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
})();;/**
 * editor-core.js — Canvas core for the EInvite studio editor (v54 refactor).
 *
 * This module consolidates the former `workspace-experience-v24.js` into a
 * readable, fully-documented module. It is responsible for the canvas-level
 * interaction surface that surrounds the design document:
 *
 *   • Canvas zoom HUD (bottom-right cluster) + zoom preset popover.
 *   • A floating "selection card" that reports the active selection's size
 *     and rotation without stealing pointer focus.
 *   • Alt-drag duplication of objects (with live preview ghosts).
 *   • Middle-mouse / middle-pointer canvas panning.
 *   • A hover label that names the object under the pointer.
 *   • The "Essentials / All controls" inspector mode toggle, persisted to
 *     localStorage, so advanced chrome can be progressively disclosed.
 *   • Registration of canvas keyboard shortcuts into the command registry.
 *
 * BUG FIXES introduced here (vs. the old v24 module):
 *
 *   1. No auto-font-scaling on resize — while the user is dragging a resize or
 *      rotate handle the TypographyLayoutService auto-fit pass is suppressed
 *      so the configured font size is preserved (see `AutoFitGuard`).
 *   2. No auto-resize on click/selection — selecting an object no longer
 *      triggers a one-shot refit; auto-fit only runs on explicit user intent
 *      (the "Fit" button / a text change), never on a bare selection event.
 *
 * The module is designed to be loaded once, after the editor bridge, command
 * registry, and canvas view controller are available. It is idempotent: a
 * second load is a no-op (guarded by `window.EInviteEditorCore?.version`).
 */
(() => {
  'use strict';

  // Idempotency guard — prevents double-initialisation if the bundle loads
  // this module more than once.
  if (window.EInviteEditorCore?.version >= 54) return;

  /** Editor-core API namespace exposed on `window`. */
  const api = { version: 54, destroy: null };

  // --- External dependencies -------------------------------------------------
  // These globals are provided by earlier bundle modules. We capture them once
  // so the rest of the module reads cleanly.
  const registry = window.EInviteCommandRegistry;
  const bridge = window.EInviteEditorBridge;
  const controller = window.EInviteCanvasViewController;
  const viewport = document.querySelector('#canvasViewport');
  const stage = document.querySelector('#stage');
  const wrap = document.querySelector('.stage-wrap');

  // Bail out silently when the editor chrome is not present on the page (e.g.
  // the module is bundled into a non-editor route). This keeps the bundle safe
  // to include globally.
  if (!registry || !bridge || !controller || !viewport || !stage || !wrap) return;

  // --- Tiny DOM helpers ------------------------------------------------------
  /**
   * Query a single element, scoped to `root` (document by default).
   * @param {string} selector CSS selector.
   * @param {ParentNode} [root=document] Search root.
   * @returns {Element|null}
   */
  const $ = (selector, root = document) => root.querySelector(selector);
  /**
   * Query all matching elements as an array, scoped to `root`.
   * @param {string} selector CSS selector.
   * @param {ParentNode} [root=document] Search root.
   * @returns {Element[]}
   */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  /** Listener cleanup stack — every `on()` registration pushes a remover. */
  const cleanup = [];
  /**
   * Attach an event listener and remember how to remove it.
   * @param {EventTarget|null} target Target (null-safe).
   * @param {string} type Event name.
   * @param {EventListenerOrEventListenerObject} fn Handler.
   * @param {AddEventListenerOptions|boolean} [options] Listener options.
   */
  function on(target, type, fn, options) {
    target?.addEventListener?.(type, fn, options);
    cleanup.push(() => target?.removeEventListener?.(type, fn, options));
  }

  /** Module-level mutable state. Kept at the top so the lifecycle is obvious. */
  let hud = null;
  let popover = null;
  let selectionCard = null;
  let cardGeometryTracked = false;
  let hoverBox = null;
  let inspectorToggle = null;
  let inspectorEmpty = null;
  let footerTools = null;
  let contextObserver = null;
  let selectionObserver = null;
  let headerObserver = null;
  let footerObserver = null;
  let resizeObserver = null;
  let raf = 0;
  let destroyed = false;

  /** Remembers the original DOM position of header buttons so they can be
   *  restored when the viewport grows wide enough to show them inline. */
  const headerHomes = new Map();

  // --- Small utilities -------------------------------------------------------
  /** Clamp `v` into `[min,max]`; non-finite values fall back to `min`. */
  const clamp = (v, min, max) => Math.min(max, Math.max(min, Number(v) || 0));

  /**
   * Escape a value for safe insertion into HTML text/attribute contexts.
   * @param {unknown} value
   * @returns {string}
   */
  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  /** Deep-clone via the editor schema (falls back to JSON round-trip). */
  const clone = value => window.EInviteEditorSchema?.clone?.(value) ?? JSON.parse(JSON.stringify(value));

  /**
   * Generate a unique identifier with a readable prefix.
   * @param {string} prefix
   * @returns {string}
   */
  function uid(prefix) {
    return `${prefix}-${crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
  }

  /**
   * Resolve the object map for the currently active canvas.
   *
   * The editor supports a "hero" canvas plus numbered design pages. This
   * helper returns the correct `{id: object}` dictionary for whichever
   * canvas is active so command handlers operate on the right scope.
   *
   * @param {object} doc The editor document state.
   * @returns {Record<string, object>}
   */
  function activeMap(doc) {
    const canvas = bridge.getActiveCanvasId?.() || 'hero';
    if (canvas === 'hero') return doc.objects || (doc.objects = {});
    const pageId = String(canvas).replace(/^page:/, '');
    const page = (doc.designPages || []).find(item => String(item.id) === pageId);
    return page ? (page.objects || (page.objects = {})) : (doc.objects || (doc.objects = {}));
  }

  /**
   * Return the DOM elements currently marked as selected on the stage.
   * @returns {Element[]}
   */
  function selectedElements() {
    const ids = new Set(bridge.getSelectedIds?.() || []);
    return $$('.object', stage).filter(el => ids.has(el.dataset.id));
  }

  /**
   * Produce a human-readable type label for an object element, derived from
   * its `layerName` / `objectType` / `type` dataset attributes.
   * @param {Element} el
   * @returns {string}
   */
  function readableType(el) {
    const raw = el?.dataset.layerName || el?.dataset.objectType || el?.dataset.type || 'Object';
    return String(raw).replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  /**
   * Compute the current stage scale (CSS pixels per layout pixel).
   * Used to convert screen-space selection rects back into canvas units.
   * @returns {number}
   */
  function stageScale() {
    // The motion viewport already knows the zoom the stage is drawn at. Reading it
    // avoids a layout flush on every selection update, which the drag path triggers
    // right after writing the overlay styles.
    const zoom = window.EInviteMotion?.viewport?.view?.zoom;
    if (Number.isFinite(zoom) && zoom > 0) return zoom;
    const rect = stage.getBoundingClientRect();
    return rect.width / Math.max(1, stage.offsetWidth);
  }

  /**
   * Measure the bounding box of the current selection in canvas units,
   * together with a short label and (for single selections) rotation.
   * @returns {{items:Element[],left:number,top:number,right:number,bottom:number,width:number,height:number,label:string,rotation:number}|null}
   */
  function selectionMetrics() {
    const items = selectedElements();
    if (!items.length) return null;
    const scale = Math.max(0.001, stageScale());
    const rects = items.map(el => el.getBoundingClientRect());
    const left = Math.min(...rects.map(r => r.left));
    const top = Math.min(...rects.map(r => r.top));
    const right = Math.max(...rects.map(r => r.right));
    const bottom = Math.max(...rects.map(r => r.bottom));
    return {
      items,
      left, top, right, bottom,
      width: (right - left) / scale,
      height: (bottom - top) / scale,
      label: items.length > 1 ? `${items.length} objects` : readableType(items[0]),
      rotation: items.length === 1 ? Number(items[0].dataset.rotation || 0) : 0
    };
  }

  // =========================================================================
  // AutoFitGuard — fixes "no auto-font-shrink on resize" & "no auto-resize on
  // click". The TypographyLayoutService refits text whenever it observes a
  // geometry change or a selection change. During an active resize drag and
  // for a single tick after a selection event we suppress that refit so the
  // user's configured font size is honoured.
  // =========================================================================
  const AutoFitGuard = (() => {
    /** When true, the patched scheduler must skip refit work. */
    let suppressed = false;
    /** Pending release timer (we keep suppression briefly after a drag ends
     *  so the final commit does not immediately re-trigger a refit). */
    let releaseTimer = 0;
    /** Original schedule/refit references, captured when we patch the service. */
    let originalSchedule = null;
    let originalRefit = null;
    let patched = false;

    /**
     * Toggle suppression and reflect it on the body so CSS can react.
     * @param {boolean} value
     * @param {string} [reason] Debug label.
     */
    function set(value, reason) {
      suppressed = !!value;
      document.body.classList.toggle('ei-suppress-autofit', suppressed);
      // Always sync --ei-font-size from each element's data-font-size attribute
      // (runs whether or not AutoFitGuard is suppressing): the CSS rule that
      // reads --ei-font-size is gated on body.ei-suppress-autofit, so setting the
      // var unconditionally is a no-op when not suppressing and guarantees the
      // var(--ei-font-size, inherit) backstop never falls through to the parent size.
      document.querySelectorAll('[data-font-size]').forEach(function(el) {
        el.style.setProperty('--ei-font-size', el.getAttribute('data-font-size') + 'px');
      });
      if (reason && window.__EINVITE_DEBUG_AUTOFIT) {
        // eslint-disable-next-line no-console
        console.debug('[AutoFitGuard]', reason, suppressed ? 'suppressed' : 'released');
      }
    }

    /**
     * Suppress for `ms` milliseconds, then auto-release.
     * @param {number} ms
     */
    function suppressFor(ms) {
      clearTimeout(releaseTimer);
      set(true);
      releaseTimer = setTimeout(() => set(false), ms);
    }

    /**
     * Patch the global TypographyLayoutService AND the responsive controller
     * so their `schedule` and `refit` methods become no-ops while suppression
     * is active. Safe to call before they exist (retries on later events).
     *
     * Note: the service object (window.TypographyLayoutService) exposes
     * `installResponsive` but NOT `schedule`/`refit` directly — those live on
     * the controller returned by `installResponsive`, which app.js exposes on
     * `window.typographyLayoutController`. We patch both shapes defensively.
     *
     * This is retryable: if the controller appears later (app.js creates it
     * after editor-core installs), a subsequent patch() call will patch it.
     * The `patched` flag only guards the service-level fit patch.
     */
    function patch() {
      const svc = window.TypographyLayoutService;
      if (!svc) return;
      // Always attempt to patch the controller — it may appear after install.
      patchController(window.typographyLayoutController);
      // Patch the service-level fit methods once.
      if (patched) return;
      patched = true;
      if (typeof svc.fit === 'function' && !svc.__v54FitPatched) {
        const originalFit = svc.fit.bind(svc);
        try {
          svc.fit = function fit(...rest) {
            if (suppressed) return null;
            return originalFit(...rest);
          };
          svc.__v54FitPatched = true;
        } catch (e) { /* fit is read-only — skip patching */ }
      }
      if (typeof svc.fitAndDiagnose === 'function' && !svc.__v54FitDiagnosePatched) {
        const originalFitDiag = svc.fitAndDiagnose.bind(svc);
        try {
          svc.fitAndDiagnose = function fitAndDiagnose(...rest) {
            if (suppressed) return null;
            return originalFitDiag(...rest);
          };
          svc.__v54FitDiagnosePatched = true;
        } catch (e) { /* read-only — skip patching */ }
      }
    }

    /**
     * Patch a responsive controller's `schedule` and `refit` methods.
     * Idempotent per controller (guarded by `__v54Patched`).
     * @param {object|null} ctrl
     */
    function patchController(ctrl) {
      if (!ctrl) return;
      if (typeof ctrl.schedule === 'function' && !ctrl.__v54Patched) {
        const original = ctrl.schedule.bind(ctrl);
        ctrl.schedule = function scheduled(items, ...rest) {
          if (suppressed) return; // honour the user's font size during resize/click
          return original(items, ...rest);
        };
        ctrl.__v54Patched = true;
      }
      if (typeof ctrl.refit === 'function' && !ctrl.__v54RefitPatched) {
        const original = ctrl.refit.bind(ctrl);
        ctrl.refit = function refit(node, ...rest) {
          if (suppressed) return null;
          return original(node, ...rest);
        };
        ctrl.__v54RefitPatched = true;
      }
      if (typeof ctrl.refresh === 'function' && !ctrl.__v54RefreshPatched) {
        const original = ctrl.refresh.bind(ctrl);
        ctrl.refresh = function refresh(...rest) {
          if (suppressed) return null;
          return original(...rest);
        };
        ctrl.__v54RefreshPatched = true;
      }
    }

    return {
      /** Begin suppressing auto-fit (called on resize-handle pointerdown). */
      begin() { clearTimeout(releaseTimer); set(true, 'resize-begin'); },
      /** End suppression, holding it briefly so the commit settles first. */
      end(ms = 320) { suppressFor(ms); },
      /** Suppress for a single tick (called on selection-changed). */
      pulse(ms = 220) { suppressFor(ms); },
      /** Is suppression currently active? */
      get active() { return suppressed; },
      /** Try to patch the global service (idempotent). */
      patch
    };
  })();

  // =========================================================================
  // Canvas HUD (zoom cluster)
  // =========================================================================
  /**
   * Lazily build the bottom-right zoom HUD and wire its buttons.
   * @returns {HTMLDivElement}
   */
  function ensureHud() {
    if (hud) return hud;
    hud = document.createElement('div');
    hud.id = 'v54CanvasHud';
    hud.className = 'v54-canvas-hud';
    hud.setAttribute('aria-label', 'Canvas navigation');
    hud.innerHTML = (
      '<button type="button" data-v54-zoom="out" aria-label="Zoom out">−</button>' +
      '<button type="button" class="v54-zoom-value" data-v54-zoom="menu" aria-haspopup="menu">100%</button>' +
      '<button type="button" data-v54-zoom="in" aria-label="Zoom in">+</button>' +
      '<span></span>' +
      '<button type="button" data-v54-zoom="fit">Fit</button>' +
      '<button type="button" data-v54-zoom="selection">Selection</button>' +
      '<button type="button" data-command-id="workspace.hidePanels" title="Hide or show panels">Focus</button>'
    );
    wrap.append(hud);
    hud.addEventListener('click', event => {
      const action = event.target.closest('[data-v54-zoom]')?.dataset.v54Zoom;
      if (!action) return;
      if (action === 'out') controller.setZoom(controller.zoom - 0.1, { source: 'hud' });
      if (action === 'in') controller.setZoom(controller.zoom + 0.1, { source: 'hud' });
      if (action === 'fit') controller.fit();
      if (action === 'selection') controller.zoomToSelection();
      if (action === 'menu') toggleZoomMenu(event.target);
    });
    return hud;
  }

  /**
   * Lazily build the zoom-preset popover.
   * @returns {HTMLDivElement}
   */
  function ensureZoomMenu() {
    if (popover) return popover;
    popover = document.createElement('div');
    popover.id = 'v54ZoomMenu';
    popover.className = 'v54-zoom-menu';
    popover.hidden = true;
    popover.setAttribute('role', 'menu');
    popover.innerHTML = (
      [.5, .75, 1, 1.25, 1.5, 2]
        .map(value => `<button type="button" role="menuitem" data-v54-preset="${value}">${Math.round(value * 100)}%</button>`)
        .join('') +
      '<hr><button type="button" role="menuitem" data-v54-fit>Fit canvas</button>' +
      '<button type="button" role="menuitem" data-v54-selection>Zoom to selection</button>' +
      '<small>Ctrl/Cmd + wheel to zoom at pointer</small>'
    );
    document.body.append(popover);
    popover.addEventListener('click', event => {
      const preset = event.target.closest('[data-v54-preset]')?.dataset.v54Preset;
      if (preset) controller.setZoom(Number(preset), { source: 'menu' });
      else if (event.target.closest('[data-v54-fit]')) controller.fit();
      else if (event.target.closest('[data-v54-selection]')) controller.zoomToSelection();
      else return;
      closeZoomMenu();
    });
    return popover;
  }

  /**
   * Toggle the zoom popover open/closed, anchored to a button.
   * @param {Element} anchor
   */
  function toggleZoomMenu(anchor) {
    const menu = ensureZoomMenu();
    if (!menu.hidden) return closeZoomMenu();
    const rect = anchor.getBoundingClientRect();
    menu.hidden = false;
    menu.style.left = `${Math.min(innerWidth - menu.offsetWidth - 12, Math.max(12, rect.left - menu.offsetWidth / 2 + rect.width / 2))}px`;
    menu.style.top = `${Math.max(12, rect.top - menu.offsetHeight - 8)}px`;
    menu.querySelector('button')?.focus();
  }

  /** Hide the zoom popover. */
  function closeZoomMenu() { if (popover) popover.hidden = true; }

  // =========================================================================
  // Selection card (floating size/rotation read-out)
  // =========================================================================
  /**
   * Lazily build the selection card and prepend it to the viewport.
   * @returns {HTMLDivElement}
   */
  function ensureSelectionCard() {
    if (selectionCard) return selectionCard;
    selectionCard = document.createElement('div');
    selectionCard.id = 'v54SelectionCard';
    selectionCard.className = 'v54-selection-card';
    selectionCard.hidden = true;
    // Canva-style context card: a compact action row above a size read-out.
    selectionCard.innerHTML = '<div class="v54-selection-actions" role="toolbar" aria-label="Selection actions">' +
      '<button type="button" data-v54-action="text" title="Edit text" aria-label="Edit text"><span aria-hidden="true">T</span></button>' +
      '<button type="button" data-v54-action="crop" title="Crop" aria-label="Crop"><span aria-hidden="true">\u25A3</span></button>' +
      // Duplicate/Delete stay in the canvas action bar; repeating them in this
      // card made three copies of the same destructive command on one screen.
      '<button type="button" data-v54-action="more" title="More actions" aria-label="More actions"><span aria-hidden="true">\u22EF</span></button>' +
      '</div>' +
      '<div class="v54-selection-readout"><small data-v54-page></small><strong data-v54-label></strong><span data-v54-metrics></span></div>';
    selectionCard.addEventListener('click', onSelectionCardAction);
    viewport.prepend(selectionCard);
    trackSelectionCardGeometry();
    return selectionCard;
  }

  /**
   * Handle the floating selection card's action row.
   *
   * Every action resolves to an existing editor capability — no new state is
   * invented here: text/crop move focus into the inspector control that owns
   * the edit, while duplicate/delete run the registered editor commands.
   * @param {MouseEvent} event
   */
  function onSelectionCardAction(event) {
    const button = event.target.closest?.('[data-v54-action]');
    if (!button || button.disabled) return;
    event.preventDefault();
    event.stopPropagation();
    const action = button.dataset.v54Action;
    if (action === 'text') {
      const field = $('#textContent');
      if (field) { field.focus({ preventScroll: true }); field.select?.(); }
      document.querySelector('[data-studio-tab="design"]')?.click();
      return;
    }
    if (action === 'crop') {
      document.querySelector('[data-studio-tab="media"]')?.click();
      const fit = $('#imageFit');
      if (fit) fit.focus({ preventScroll: true });
      return;
    }
    if (action === 'duplicate') { registry.execute?.('edit.duplicate'); return; }
    if (action === 'delete') { registry.execute?.('edit.delete'); return; }
    if (action === 'more') { registry.openUI?.(); return; }
  }

  /** Required vertical gap between the selected object's box and the card. */
  const SELECTION_CARD_GAP = 8;

  /**
   * Anchor the selection card to the primary selected element's bounding box:
   * 8px above it, flipped below when that would clip the viewport (dispatch §3-G4).
   *
   * Positioning is done by measuring the card where it actually is and moving it
   * by the delta to where it must be — never by offsetTop/offsetLeft arithmetic.
   * Those are resolved against the containing block's *padding* box, so any
   * border on the offset parent is silently added to every measurement:
   * `#canvasViewport` carries clientTop 1 / clientLeft 11, which turned the
   * required 8px gap into 5px and pushed the horizontal centre 11px off. A
   * getBoundingClientRect() delta reports real viewport geometry, so it stays
   * exact whatever the offset parent's border, padding, scroll or a transformed
   * ancestor does (G4/G7).
   * @param {HTMLElement} card
   * @param {boolean} hasSelection
   */
  function positionSelectionCard(card, hasSelection) {
    if (!hasSelection) { if (card.style.transform) card.style.transform = ''; return; }
    const ids = bridge.getSelectedIds?.() || [];
    const target = ids.length ? stage.querySelector(`.object[data-id="${typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(ids[0]) : ids[0]}"]`) : null;
    if (!target) return;
    const box = target.getBoundingClientRect();
    if (!box.width && !box.height) return;
    // Measure the card untransformed, then translate it by the exact delta.
    if (card.style.transform !== 'none') card.style.transform = 'none';
    const cardRect = card.getBoundingClientRect();
    if (!cardRect.width && !cardRect.height) return;
    const desiredLeft = box.left + box.width / 2 - cardRect.width / 2;
    const above = box.top - SELECTION_CARD_GAP - cardRect.height;
    const flip = above < SELECTION_CARD_GAP;
    const desiredTop = flip ? box.bottom + SELECTION_CARD_GAP : above;
    const nextTransform = `translate(${Math.round(desiredLeft - cardRect.left)}px, ${Math.round(desiredTop - cardRect.top)}px)`;
    if (card.style.transform !== nextTransform) card.style.transform = nextTransform;
    card.classList.toggle('is-below', flip);
  }

  /**
   * On narrow viewports the right inspector is a drawer; selecting an object
   * opens it so the tap has a visible result (dispatch §3-G6).
   * @param {boolean} hasSelection
   */
  function syncInspectorDrawer(hasSelection) {
    if (typeof innerWidth === 'number' && innerWidth > 768) {
      document.body.classList.remove('right-open');
      return;
    }
    const layout = window.EInviteResponsiveLayout;
    const narrow = !layout || typeof layout.mode !== 'function' || layout.mode() !== 'desktop';
    // `editor-responsive-contract.js` owns the narrow-viewport drawer and
    // reveals the pane from its own transform rules. Its API takes a boolean
    // (`openInspector: o => set('inspector', o)`) — calling it with no argument
    // is a no-op that leaves the panel translated off-screen (G6), so pass it.
    if (!hasSelection) {
      document.body.classList.remove('right-open');
      if (narrow) { try { layout?.closeInspector?.(true); } catch { /* ignore */ } }
      return;
    }
    document.body.classList.add('right-open');
    if (narrow) { try { layout?.openInspector?.(true); } catch { /* ignore */ } }
  }

  /**
   * Refresh the selection card contents from the current selection. Hidden
   * when nothing is selected.
   */
  function updateSelectionCard() {
    if (destroyed) return;
    const card = ensureSelectionCard();
    const metrics = selectionMetrics();
    const shouldHideCard = !metrics;
    if (card.hidden !== shouldHideCard) card.hidden = shouldHideCard;
    syncInspectorDrawer(!!metrics);
    if (!metrics) { positionSelectionCard(card, false); return; }
    const setCardText = (sel, value) => { const node = $(sel, card); if (node && node.textContent !== value) node.textContent = value; };
    const canvasLabel = $('#activeCanvasLabel')?.textContent?.trim() || 'Canvas';
    setCardText('[data-v54-page]', canvasLabel);
    setCardText('[data-v54-label]', metrics.label);
    const rotation = Math.abs(metrics.rotation) > 0.05 ? ` · ${Math.round(metrics.rotation * 10) / 10}°` : '';
    setCardText('[data-v54-metrics]', `${Math.round(metrics.width)} × ${Math.round(metrics.height)}${rotation}`);
    card.classList.toggle('is-multi', metrics.items.length > 1);
    // Crop only applies to image objects; a disabled control always says why.
    const crop = $('[data-v54-action="crop"]', card);
    if (crop) {
      const first = metrics.items?.[0] || null;
      const isImage = !!first && (first.dataset.type === 'image' || !!first.querySelector('img'));
      crop.disabled = !isImage;
      crop.title = isImage ? 'Crop' : 'Crop applies to image objects only';
    }
    // Re-measure on the next frame. Selecting an object settles its box (and the
    // narrow-viewport inspector drawer) in the same tick, so a card placed against
    // the pre-layout rect sits a few pixels into the selection instead of 8px above
    // it. The guard keeps this a no-op once the card is hidden again.
    requestAnimationFrame(() => { if (!destroyed && !card.hidden) positionSelectionCard(card, true); });
  }

  /**
   * Re-position the card whenever anything that can move the selected object
   * moves.
   *
   * Selecting an object settles its layout over more than one frame: the
   * inspector's controls appear (which re-centres the stage) and `.canvas-frame`
   * runs a 0.3s `transform` transition whose hover state is `translateY(-2px)`.
   * Both land *after* the card has been placed, which left the gap at 6px
   * instead of the required 8px (G4/G7). Mirroring every event that can move the
   * canvas keeps the card glued to the object, instead of widening the nominal
   * gap to hide the error.
   */
  function trackSelectionCardGeometry() {
    if (cardGeometryTracked) return;
    cardGeometryTracked = true;
    const reposition = () => {
      if (destroyed || !selectionCard || selectionCard.hidden) return;
      positionSelectionCard(selectionCard, true);
    };
    viewport.addEventListener('scroll', reposition, { passive: true });
    // `transitionend` bubbles, so a capture listener sees `.canvas-frame`'s
    // transform transition — and any other transition inside the canvas.
    viewport.addEventListener('transitionend', reposition, true);
    window.addEventListener('resize', reposition, { passive: true });
    document.addEventListener('einvite:workspace-resized', reposition);
    document.addEventListener('einvite:layout-stable', reposition);
  }

  /**
   * Toggle body classes that drive inspector empty-state visibility and
   * update the empty-state copy.
   */
  function updateSelectionState() {
    const selected = selectedElements();
    const hasSelection = selected.length > 0;
    document.body.classList.toggle('v54-has-selection', hasSelection);
    if (inspectorEmpty) {
      inspectorEmpty.hidden = hasSelection;
      const label = inspectorEmpty.querySelector('[data-v54-empty-label]');
      if (label) label.textContent = hasSelection ? 'Selection ready' : 'Select an object to edit its position, style, image, text, and animation.';
    }
  }

  /**
   * renderContextPanel (B2/B4) — "click first, edit second".
   *
   * Dispatches on the selected element's type and shows only the relevant
   * property controls in the right context panel.  When nothing is selected,
   * the empty-state placeholder is shown and all type-specific sections are
   * hidden.
   *
   * Type dispatch:
   *   text-object     → text content + typography controls + animation
   *   image-object    → image controls + appearance
   *   rectangle|circle|line → shape controls + appearance
   *   (unknown)       → appearance only
   *
   * @param {{elements: Element[], type: string|null}} selection
   */
  function renderContextPanel(selection) {
    const pane = document.querySelector('[data-inspector-pane="object"]');
    if (!pane) return;

    const properties = $('#properties');
    if (!properties) return;

    const selected = selection.elements || [];
    const hasSelection = selected.length > 0;

    // Show/hide the "no selection" placeholder.
    const placeholder = pane.querySelector('.v54-inspector-placeholder');
    const placeholderDisplay = hasSelection ? 'none' : 'grid';
    if (placeholder && placeholder.style.display !== placeholderDisplay) placeholder.style.display = placeholderDisplay;

    if (!hasSelection) {
      // Hide all type-specific control groups.  No !important: none of these
      // sections carry a competing !important display rule in the CSS, so a
      // plain inline style reliably beats the author declaration.
      ['#typographyControls', '#shapeControls', '#imageControls',
       '#alignment-grid', '#textContentLabel'].forEach(sel => {
        const el = pane.querySelector(sel);
        if (el) el.style.display = 'none';
      });
      // Hide Appearance / Fine position sub-headings.
      pane.querySelectorAll('h2').forEach(h => {
        const txt = (h.textContent || '').toLowerCase();
        if ((txt.includes('appearance') || txt.includes('fine position')) && h.style.display !== 'none') h.style.display = 'none';
      });
      return;
    }

    // Determine the primary type from the first selected element.
    const first = selected[0];
    const type = first?.dataset?.objectType || first?.className || '';

    // Helper: show a section, hide another.  No !important is needed: the
    // `#typographyControls` rule in ux-refine.css no longer carries !important,
    // so a plain inline `display:none` (reinforced by el.hidden + the UA
    // `[hidden]` rule) reliably overrides the author `display:grid`.
    const show = (sel) => { const el = pane.querySelector(sel); if (el && (el.hidden || el.style.display)) { el.hidden = false; el.style.removeProperty('display'); } };
    const hide = (sel) => { const el = pane.querySelector(sel); if (el && (!el.hidden || el.style.display !== 'none')) { el.hidden = true; el.style.display = 'none'; } };

    // Selection summary is always visible when something is selected.
    const summary = pane.querySelector('.selection-summary');
    if (summary && (summary.hidden || summary.style.display)) { summary.hidden = false; summary.style.removeProperty('display'); }

    // Dispatch by type.
    let isText = false, isImage = false, isShape = false;

    if (type.includes('text')) {
      isText = true;
    } else if (type.includes('image')) {
      isImage = true;
    } else if (type.includes('rectangle') || type.includes('circle') || type.includes('line') || type.includes('shape')) {
      isShape = true;
    } else {
      // Unknown — show appearance only.
      isText = isImage = isShape = false;
    }

    if (isText) {
      show('#textContentLabel');
      show('#typographyControls');
      show('#animationControls');
      hide('#shapeControls');
      hide('#imageControls');
    } else if (isImage) {
      show('#imageControls');
      show('#textContentLabel');  // images can have alt-text
      hide('#typographyControls');
      hide('#shapeControls');
    } else if (isShape) {
      show('#shapeControls');
      show('#textContentLabel');  // shapes can have labels
      hide('#typographyControls');
      hide('#imageControls');
    } else {
      // Generic — show appearance controls only.
      hide('#textContentLabel');
      hide('#typographyControls');
      hide('#shapeControls');
      hide('#imageControls');
    }

    // Alignment grid always available for movable objects.
    if (type.includes('text') || type.includes('image') || type.includes('rectangle') || type.includes('circle') || type.includes('line')) {
      show('#alignment-grid');
      show('h2[align-group="position"]');  // alignment is always shown
    }

    // Appearance / Fine position sections are shown for all selectable objects.
    pane.querySelectorAll('h2').forEach(h => {
      const txt = (h.textContent || '').toLowerCase();
      if ((txt.includes('appearance') || txt.includes('fine position')) && h.style.display) h.style.removeProperty('display');
    });

    // Dispatch event so other modules can react.
    const evt = new window.CustomEvent('einvite:context-panel-rendered', {
      detail: { type, elementCount: selected.length },
      bubbles: true,
    });
    if (evt) pane.dispatchEvent(evt);
  }

  /**
   * Build the current selection descriptor and delegate to renderContextPanel.
   */
  function refreshContextPanel() {
    const selected = selectedElements();
    renderContextPanel({
      elements: selected,
      type: selected.length === 1 ? (selected[0].dataset?.objectType || null) : (selected.length > 1 ? 'multi' : null),
    });
  }


  /**
   * Coalesce update work into a single macrotask so rapid selection/mutation
   * bursts do not thrash layout.
   */
  function scheduleUpdate() {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      updateSelectionCard();
      updateSelectionState();
      refreshContextPanel();
      updateZoomLabel();
      // NOTE: layoutContextToolbar / header / footer organisation deliberately
      // NOT called here — running them on every selection change is what made
      // the toolbar "jump". They run on install + resize only (see ui-layout).
    });
  }

  /** Sync the zoom HUD's numeric label + selection button disabled state. */
  function updateZoomLabel() {
    const value = $('.v54-zoom-value', ensureHud());
    if (value) value.textContent = `${Math.round(controller.zoom * 100)}%`;
    ensureHud().querySelector('[data-v54-zoom="selection"]').disabled = !(bridge.getSelectedIds?.() || []).length;
  }

  /**
   * Ctrl/Cmd + wheel zooms the canvas at the pointer location.
   * @param {WheelEvent} event
   */
  const motion = window.EInviteMotion;
  const wheelBatcher = motion.createFrameBatcher(
    (a, b) => ({ delta: a.delta + b.delta, clientX: b.clientX, clientY: b.clientY }),
    value => {
      // Preserve the old per-event wheel response in P1; P5 adopts the new clamp.
      controller.setZoom(controller.zoom * Math.exp(-value.delta * 0.0024), {
        clientX: value.clientX, clientY: value.clientY, source: 'wheel'
      });
      scheduleUpdate();
    }
  );
  const settleWheel = motion.debounce(() => wheelBatcher.flush(), motion.MOTION.WHEEL_SETTLE_MS);
  cleanup.push(() => { settleWheel.cancel(); wheelBatcher.destroy(); });
  function wheelZoom(event) {
    if (window.EInviteMotion?.input) { window.EInviteMotion.input.wheel(event); return; }
    if (!(event.ctrlKey || event.metaKey)) return;
    event.preventDefault();
    event.stopPropagation();
    wheelBatcher.accumulate({delta: clamp(event.deltaY, -120, 120), clientX: event.clientX, clientY: event.clientY});
    settleWheel();
  }

  // =========================================================================
  // Alt-drag duplication (with live preview ghosts)
  // =========================================================================
  let duplicateDrag = null;
  let middlePan = null;

  /**
   * Begin an alt-drag duplication gesture. Only the primary button while Alt
   * is held (and no other modifiers) qualifies. Clicking on resize/rotate
   * handles, editable text, or form controls is ignored.
   * @param {PointerEvent} event
   */
  function beginDuplicateDrag(event) {
    if (event.button !== 0 || !event.altKey || event.shiftKey || event.ctrlKey || event.metaKey || duplicateDrag || middlePan) return;
    if (event.target.closest?.('[data-pe-handle],.pe-handle,.pe-rotate,.resize-handle,.rotate-handle,[contenteditable=true],button,input,select,textarea')) return;
    const object = event.target.closest?.('#stage .object');
    if (!object || object.dataset.locked === 'true') return;

    let ids = bridge.getSelectedIds?.() || [];
    if (!ids.includes(object.dataset.id)) { ids = [object.dataset.id]; bridge.select?.(ids); }

    const elements = $$('.object', stage).filter(el => ids.includes(el.dataset.id) && el.dataset.locked !== 'true');
    if (!elements.length) return;

    const sr = stage.getBoundingClientRect();
    const scale = Math.max(0.001, stageScale());
    // Capture each element's starting frame in canvas units once.
    const frames = elements.map(el => {
      const rect = el.getBoundingClientRect();
      return { id: el.dataset.id, x: (rect.left - sr.left) / scale, y: (rect.top - sr.top) / scale, w: rect.width / scale, h: rect.height / scale };
    });
    // Clone each element as a translucent preview ghost.
    const previews = elements.map((el, index) => {
      const preview = el.cloneNode(true);
      preview.dataset.v54DuplicatePreview = '1';
      preview.dataset.id = `preview-${index}`;
      preview.classList.remove('selected', 'multi-selected', 'marquee-hit');
      preview.setAttribute('aria-hidden', 'true');
      preview.querySelectorAll('[id]').forEach(node => node.removeAttribute('id'));
      stage.append(preview);
      return preview;
    });

    duplicateDrag = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, ids, frames, previews, scale, active: false, dx: 0, dy: 0, target: event.target };
    event.target.setPointerCapture?.(event.pointerId);
    document.body.classList.add('v54-alt-duplicating');
    hideHover();
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  /**
   * Move the duplicate-drag preview ghosts. A small dead-zone avoids
   * accidentally duplicating on a plain click.
   * @param {PointerEvent} event
   */
  const duplicateBatcher = motion.createFrameBatcher((a, b) => b, applyDuplicateDrag);
  cleanup.push(() => duplicateBatcher.destroy());
  function moveDuplicateDrag(event) {
    if (!duplicateDrag || event.pointerId !== duplicateDrag.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    duplicateBatcher.accumulate(event);
  }
  function applyDuplicateDrag(event) {
    const drag = duplicateDrag;
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const screenDx = event.clientX - drag.startX;
    const screenDy = event.clientY - drag.startY;
    if (!drag.active && Math.abs(screenDx) < 3 && Math.abs(screenDy) < 3) return;
    drag.active = true;
    drag.dx = screenDx / drag.scale;
    drag.dy = screenDy / drag.scale;
    drag.previews.forEach(preview => { preview.style.translate = `${drag.dx}px ${drag.dy}px`; });
  }

  /**
   * Walk the group ancestry of each duplicated object so nested groups are
   * cloned alongside their members.
   * @param {object} doc Editor document.
   * @param {string[]} ids Object ids being duplicated.
   * @returns {{all:object,wanted:Set<string>}}
   */
  function sourceGroups(doc, ids) {
    const all = doc.sceneGraph?.groups || {};
    const wanted = new Set();
    ids.forEach(id => {
      let groupId = activeMap(doc)[id]?.groupId || '';
      let guard = 0;
      while (groupId && all[groupId] && guard++ < 50) {
        wanted.add(groupId);
        groupId = all[groupId].parentId || '';
      }
    });
    return { all, wanted };
  }

  /**
   * Commit the duplicate-drag gesture as a single transaction, re-clamping
   * positions to the stage and remapping group ids.
   * @param {object} drag The active duplicate-drag state.
   * @returns {string[]} The new object ids.
   */
  function commitDuplicateDrag(drag) {
    const newIds = [];
    const stageWidth = Math.max(1, stage.offsetWidth);
    const stageHeight = Math.max(1, stage.offsetHeight);
    const idMap = new Map(drag.ids.map(id => [id, uid('obj')]));
    idMap.forEach(id => newIds.push(id));

    bridge.transact?.('Alt-drag duplicate', doc => {
      const map = activeMap(doc);
      const { all, wanted } = sourceGroups(doc, drag.ids);
      const groupMap = new Map([...wanted].map(id => [id, uid('group')]));
      const maxZ = Math.max(0, ...Object.values(map).map(value => Number(value.zIndex) || 0));

      drag.ids.forEach((oldId, index) => {
        const source = map[oldId];
        if (!source) return;
        const next = clone(source);
        const frame = drag.frames[index];
        const newId = idMap.get(oldId);
        const x = clamp(frame.x + drag.dx, 0, Math.max(0, stageWidth - frame.w));
        const y = clamp(frame.y + drag.dy, 0, Math.max(0, stageHeight - frame.h));
        next.left = `${x / stageWidth * 100}%`;
        next.top = `${y / stageHeight * 100}%`;
        next.zIndex = maxZ + index + 1;
        next.legacyId = newId;
        next.groupId = groupMap.get(next.groupId) || '';
        next.parentGroupId = groupMap.get(next.parentGroupId) || '';
        delete next.id;
        map[newId] = next;
      });

      if (wanted.size) {
        doc.sceneGraph = doc.sceneGraph || {};
        doc.sceneGraph.groups = doc.sceneGraph.groups || {};
        [...wanted].forEach(oldId => {
          const group = all[oldId];
          const newId = groupMap.get(oldId);
          doc.sceneGraph.groups[newId] = {
            ...clone(group),
            id: newId,
            parentId: groupMap.get(group.parentId) || '',
            children: (group.children || []).map(child => groupMap.get(child) || idMap.get(child)).filter(Boolean)
          };
        });
      }
    });

    bridge.select?.(newIds);
    window.EInviteFeedback?.toast?.('Duplicated and moved');
    return newIds;
  }

  /**
   * End the duplicate-drag gesture, committing unless `cancel` is set.
   * @param {PointerEvent} event
   * @param {boolean} [cancel=false]
   */
  function endDuplicateDrag(event, cancel = false) {
    duplicateBatcher.flush();
    const drag = duplicateDrag;
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    duplicateDrag = null;
    drag.previews.forEach(preview => preview.remove());
    document.body.classList.remove('v54-alt-duplicating');
    if (drag.active && !cancel) commitDuplicateDrag(drag);
    scheduleUpdate();
  }

  // =========================================================================
  // Middle-button panning
  // =========================================================================
  /**
   * Begin a middle-button canvas pan gesture.
   * @param {PointerEvent} event
   */
  function startMiddlePan(event) {
    if (window.EInviteMotion?.input) return;
    if (event.button !== 1) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    middlePan = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, left: viewport.scrollLeft, top: viewport.scrollTop };
    viewport.classList.add('v54-middle-panning');
    viewport.setPointerCapture?.(event.pointerId);
  }

  /** Move the canvas viewport according to the active middle-pan gesture. */
  const middlePanBatcher = motion.createFrameBatcher((a, b) => b, event => {
    if (!middlePan || event.pointerId !== middlePan.pointerId) return;
    viewport.scrollLeft = middlePan.left - (event.clientX - middlePan.x);
    viewport.scrollTop = middlePan.top - (event.clientY - middlePan.y);
  });
  cleanup.push(() => middlePanBatcher.destroy());
  function moveMiddlePan(event) {
    if (!middlePan || event.pointerId !== middlePan.pointerId) return;
    event.preventDefault();
    middlePanBatcher.accumulate(event);
  }

  /** Release the middle-pan gesture. */
  function endMiddlePan(event) {
    if (!middlePan || event.pointerId !== middlePan.pointerId) return;
    middlePanBatcher.flush();
    middlePan = null;
    viewport.classList.remove('v54-middle-panning');
  }

  // =========================================================================
  // Hover label
  // =========================================================================
  /**
   * Lazily build the hover label element.
   * @returns {HTMLDivElement}
   */
  function ensureHoverBox() {
    if (hoverBox) return hoverBox;
    hoverBox = document.createElement('div');
    hoverBox.className = 'v54-hover-box';
    hoverBox.hidden = true;
    hoverBox.innerHTML = '<span></span>';
    document.body.append(hoverBox);
    return hoverBox;
  }

  /**
   * Track the object under the pointer and show its type label. Skipped for
   * touch pointers, active pans, transforms, and already-selected/locked
   * objects.
   * @param {PointerEvent} event
   */
  function hoverMove(event) {
    if (event.pointerType === 'touch' || middlePan || document.body.classList.contains('v23-transform-active')) return hideHover();
    const object = event.target.closest?.('#stage .object');
    if (!object || object.classList.contains('selected') || object.classList.contains('multi-selected') || object.dataset.locked === 'true') return hideHover();
    const rect = object.getBoundingClientRect();
    const box = ensureHoverBox();
    box.hidden = false;
    const hoverStyle = { left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, height: `${rect.height}px`, transform: 'none' };
    for (const hoverKey in hoverStyle) { if (box.style[hoverKey] !== hoverStyle[hoverKey]) box.style[hoverKey] = hoverStyle[hoverKey]; }
    const hoverText = readableType(object);
    const hoverSpan = box.querySelector('span');
    if (hoverSpan && hoverSpan.textContent !== hoverText) hoverSpan.textContent = hoverText;
  }

  /** Hide the hover label. */
  function hideHover() { if (hoverBox) hoverBox.hidden = true; }

  // =========================================================================
  // Inspector mode (Essentials / All controls)
  // =========================================================================
  /**
   * Build the inspector-mode toggle and tag advanced controls so they can be
   * hidden in "Essentials" mode. The choice is persisted to localStorage.
   */
  function ensureInspectorMode() {
    const right = $('.right');
    if (!right || inspectorToggle) return;

    // OD-23: the bar ships in index.html so the inspector column is its final
    // height at first paint; reuse it instead of inserting a new one.
    inspectorToggle = $(':scope > .v54-inspector-mode', right) || document.createElement('div');
    if (!inspectorToggle.parentElement) {
      inspectorToggle.className = 'v54-inspector-mode';
      inspectorToggle.innerHTML = '<span>Inspector</span><button type="button" data-v54-inspector-toggle></button>';
      right.insertBefore(inspectorToggle, right.children[1] || null);
    }

    // Selectors for controls considered "advanced" — hidden in Essentials.
    const advanced = [
      '#advancedTextLayout', '#peLayoutAssistance', '#borderWidth', '#borderColor', '#borderRadius',
      '#shadowBlur', '#shadowColor', '#imagePositionX', '#imagePositionY', '#showInGallery', '#showInHero',
      '#objectLocked', '.alignment-grid'
    ];
    advanced.forEach(selector => $$(selector).forEach(node => (node.closest('label,details,section,div') || node).classList.add('v54-advanced-control')));

    const objectPane = $('[data-inspector-pane="object"]', right);
    if (objectPane) {
      $$('.final-timeline,#canvasPlusAiTools', objectPane).forEach(node => node.classList.add('v54-advanced-control'));
      $$('.final-advanced-inspector', objectPane).forEach(node => {
        if (!['canvasPlusTransform', 'canvasPlusTextBox', 'canvasPlusTextPlacement'].includes(node.id)) node.classList.add('v54-advanced-control');
      });
      // Empty state shown when nothing is selected — offers quick-add actions.
      inspectorEmpty = document.createElement('section');
      inspectorEmpty.className = 'v54-inspector-empty';
      inspectorEmpty.innerHTML = '<span aria-hidden="true">↖</span><strong>Choose something to edit</strong><p data-v54-empty-label>Select an object to edit its position, style, image, text, and animation.</p><div><button type="button" data-v54-open="text">Add text</button><button type="button" data-v54-open="elements">Browse elements</button><button type="button" data-v54-open="media">Add media</button></div>';
      const heading = $('.studio-inspector-heading', objectPane);
      if (heading && objectPane.firstElementChild !== heading) objectPane.prepend(heading);
      heading?.after(inspectorEmpty);
      inspectorEmpty.addEventListener('click', event => {
        const id = event.target.closest('[data-v54-open]')?.dataset.v54Open;
        if (!id) return;
        document.querySelector(`[data-studio-tab="${id}"]`)?.click();
      });
    }

    // Restore the user's last choice (default: essentials for a calmer UI).
    const saved = localStorage.getItem('einvite-v54-inspector-mode') || 'essential';
    setInspectorMode(saved === 'all' ? 'all' : 'essential');
    inspectorToggle.querySelector('button').onclick = () => setInspectorMode(document.body.classList.contains('v54-inspector-essential') ? 'all' : 'essential');
  }

  /**
   * Switch between "essential" (advanced controls hidden) and "all" modes.
   * @param {'essential'|'all'} mode
   */
  function setInspectorMode(mode) {
    const essential = mode !== 'all';
    document.body.classList.toggle('v54-inspector-essential', essential);
    try { localStorage.setItem('einvite-v54-inspector-mode', essential ? 'essential' : 'all'); } catch { /* ignore quota errors */ }
    if (inspectorToggle) {
      const button = inspectorToggle.querySelector('button');
      button.textContent = essential ? 'Essentials' : 'All controls';
      button.setAttribute('aria-pressed', String(!essential));
      button.title = essential ? 'Show all advanced controls' : 'Show essential controls only';
    }
  }

  // =========================================================================
  // Header & footer progressive disclosure (run on install + resize only)
  // =========================================================================
  /**
   * Remember the original DOM location of a header node via a comment marker
   * so it can be restored when the viewport is wide enough.
   * @param {Element} node
   */
  function rememberHeaderHome(node) {
    if (!node?.id || headerHomes.has(node.id)) return;
    const marker = document.createComment(`v54-home-${node.id}`);
    node.before(marker);
    headerHomes.set(node.id, marker);
  }

  /**
   * Move a header node back to its remembered home, if any.
   * @param {Element} node
   */
  function restoreHeaderNode(node) {
    const marker = headerHomes.get(node?.id);
    if (marker?.parentNode && marker.nextSibling !== node) marker.after(node);
  }

  /**
   * Reorganise the studio top bar into a compact "more" menu on narrow
   * viewports. Runs on install + resize only (NOT on every selection) so the
   * toolbar stays stable.
   */
  function organizeHeader() {
    const header = $('.studio-topbar');
    const more = $('.canvas-header-more');
    const menu = $('.canvas-header-more-menu', more);
    if (!header || !more || !menu) return;

    const ids = ['studioCommandBtn', 'studioCheckBtn', 'previewBtn', 'eiAiTopButton', 'eiAdvancedStudio', 'eiFuturePlatform'];
    ids.map(id => document.getElementById(id)).filter(Boolean).forEach(rememberHeaderHome);

    let project = $('.v54-header-menu-project', menu);
    let actions = $('.v54-header-menu-actions', menu);
    let advanced = $('.v54-header-menu-advanced', menu);
    if (!project) {
      project = document.createElement('div');
      project.className = 'v54-header-menu-section v54-header-menu-project';
      project.innerHTML = '<strong>Project</strong>';
      [$('#backupBtn'), $('#restoreBtn')].filter(Boolean).forEach(node => project.append(node));
      menu.replaceChildren(project);
    }
    if (!actions) {
      actions = document.createElement('div');
      actions.className = 'v54-header-menu-section v54-header-menu-actions';
      actions.innerHTML = '<strong>Editor</strong>';
      menu.append(actions);
    }
    if (!advanced) {
      advanced = document.createElement('div');
      advanced.className = 'v54-header-menu-section v54-header-menu-advanced';
      advanced.innerHTML = '<strong>Advanced tools</strong>';
      menu.append(advanced);
    }

    const compact = innerWidth <= 1180;
    const narrow = innerWidth <= 760;
    ['eiAdvancedStudio', 'eiFuturePlatform'].forEach(id => {
      const node = document.getElementById(id);
      if (node && node.parentElement !== advanced) advanced.append(node);
    });
    ['studioCommandBtn', 'studioCheckBtn', 'eiAiTopButton'].forEach(id => {
      const node = document.getElementById(id);
      if (!node) return;
      if (compact) { if (node.parentElement !== actions) actions.append(node); }
      else restoreHeaderNode(node);
    });
    const preview = $('#previewBtn');
    if (preview) {
      if (narrow) { if (preview.parentElement !== actions) actions.append(preview); }
      else restoreHeaderNode(preview);
    }
    menu.classList.toggle('v54-has-actions', actions.querySelector('button') != null);
    actions.hidden = !actions.querySelector('button');

    // A menu is closed until the user opens it. The mobile canvas header mounts
    // this popup absolutely over the artboard, so leaving it open hides the
    // selection (and blocks the tap that is supposed to open the inspector
    // drawer). Close it here; the trigger and click-outside still drive it.
    menu.hidden = true;
    const moreTrigger = $('.canvas-header-more-trigger', more);
    moreTrigger?.setAttribute('aria-expanded', 'false');
    // Wire the trigger exactly once: organizeHeader re-runs on every resize, and
    // a fresh listener per run would stack up on document. Escape is handled by the
    // command system's `ui.escape` (window capture, `ownsGlobalKeyboard`), which closes
    // this menu through closeTopLayer(); the document listener below is the fallback for
    // any route that loads the studio without command-system-v23.
    if (moreTrigger && !more.dataset.moreTriggerWired) {
      more.dataset.moreTriggerWired = '1';
      moreTrigger.onclick = () => {
        menu.hidden = !menu.hidden;
        moreTrigger.setAttribute('aria-expanded', String(!menu.hidden));
      };
      // Capture phase, deliberately. `#stage` owns a capture-phase `pointerdown` handler that ends in
      // `stopImmediatePropagation()` when the pointer lands on an object (professional-editor.js,
      // the object-drag start), so a bubble-phase listener here never sees a click on the canvas.
      // Measured at 1280: a click on a canvas object at (640, 648) left the menu open
      // (`hidden:false`, `aria-expanded="true"`) while a click on empty chrome closed it.
      // Focus is deliberately not moved on a pointer dismissal — the user just clicked elsewhere, and
      // the canvas owns selection rather than focus. The keyboard path below returns focus.
      document.addEventListener('pointerdown', event => {
        if (!more.contains(event.target)) {
          menu.hidden = true;
          moreTrigger.setAttribute('aria-expanded', 'false');
        }
      }, true);
      document.addEventListener('keydown', event => {
        if (event.key !== 'Escape' || menu.hidden) return;
        menu.hidden = true;
        moreTrigger.setAttribute('aria-expanded', 'false');
        moreTrigger.focus();
      });
    }

  }

  /**
   * Build the footer "Tools" overflow trigger + menu.
   * @returns {HTMLDivElement|null}
   */
  function ensureFooterTools() {
    const footer = $('.studio-statusbar');
    const host = footer?.lastElementChild;
    if (!footer || !host) return null;
    if (footerTools?.isConnected) return footerTools;
    // OD-23: the trigger ships in index.html; only its menu contents and wiring
    // are built here, so the status bar is already 44 px tall at first paint.
    footerTools = $('.v54-footer-tools', host) || document.createElement('div');
    if (!footerTools.parentElement) {
      footerTools.className = 'v54-footer-tools';
      footerTools.innerHTML = '<button type="button" class="v54-footer-tools-trigger" aria-expanded="false">Tools <span>⌃</span></button><div class="v54-footer-tools-menu" hidden><strong>Workspace tools</strong><div></div></div>';
      host.append(footerTools);
    }
    const trigger = $('.v54-footer-tools-trigger', footerTools);
    const menu = $('.v54-footer-tools-menu', footerTools);
    trigger.onclick = event => {
      event.stopPropagation();
      menu.hidden = !menu.hidden;
      trigger.setAttribute('aria-expanded', String(!menu.hidden));
      if (!menu.hidden) menu.querySelector('button')?.focus();
    };
    menu.addEventListener('click', event => {
      if (event.target.closest('button')) {
        menu.hidden = true;
        trigger.setAttribute('aria-expanded', 'false');
      }
    });
    return footerTools;
  }

  /**
   * Move stray footer buttons into the footer Tools menu. Runs on install +
   * resize only.
   */
  function organizeFooter() {
    const tools = ensureFooterTools();
    const footer = $('.studio-statusbar');
    const host = footer?.lastElementChild;
    const menu = $('.v54-footer-tools-menu>div', tools);
    if (!tools || !host || !menu) return;
    [...host.children]
      .filter(node => node.tagName === 'BUTTON' && !node.classList.contains('v54-footer-tools-trigger'))
      .forEach(button => menu.append(button));
    tools.hidden = !menu.querySelector('button');
    watchFooter(host);
  }

  /**
   * Launchers are added by later modules (templates, brand, quality, team,
   * history, photo styles...). They prepend straight into the status bar's last
   * cell, after `organizeFooter()` has already run, so they sprawl past the
   * viewport until the next resize. Re-organise whenever that cell changes.
   */
  let footerObserverHost = null;
  function watchFooter(host) {
    if (footerObserverHost === host) return;
    footerObserverHost = host;
    let queued = false;
    new MutationObserver(() => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => { queued = false; organizeFooter(); });
    }).observe(host, { childList: true });
  }

  // =========================================================================
  // Command registration
  // =========================================================================
  /**
   * Register canvas-related keyboard shortcuts into the command registry.
   */
  function registerCommands() {
    registry.registerMany?.([
      {
        id: 'canvas.zoomSelection', title: 'Zoom to selection', category: 'Canvas',
        keywords: ['focus', 'selected object', 'fit'],
        bindings: { standard: ['Mod+2'], canva: ['Mod+2'], photoshop: ['Mod+2'] },
        enabled: () => !!(bridge.getSelectedIds?.() || []).length,
        run: () => controller.zoomToSelection()
      },
      {
        id: 'canvas.zoomPointerHelp', title: 'Show canvas navigation controls', category: 'Canvas',
        keywords: ['trackpad', 'wheel', 'pan', 'zoom'],
        bindings: { standard: [], canva: [], photoshop: [] },
        run: () => {
          ensureHud().animate?.(
            [{ transform: 'translateY(6px)', opacity: 0.6 }, { transform: 'translateY(0)', opacity: 1 }],
            { duration: 220 }
          );
          return true;
        }
      }
    ]);
  }

  // =========================================================================
  // Auto-fit suppression wiring (bugs #1 & #2)
  // =========================================================================
  /**
   * Detect the start of a resize/rotate drag via pointerdown on a handle and
   * engage AutoFitGuard so font size is locked for the duration of the drag.
   * @param {PointerEvent} event
   */
  function onHandlePointerDown(event) {
    const handle = event.target.closest?.(
      '.resize-handle,.rotate-handle,.pe-handle,.pe-rotate,[data-pe-handle],.object .handle'
    );
    if (!handle) return;
    AutoFitGuard.begin();
  }

  /** Release AutoFitGuard shortly after the drag ends. */
  function onHandlePointerUp() {
    if (AutoFitGuard.active) AutoFitGuard.end();
  }

  /**
   * Pulse AutoFitGuard for a single tick after a selection change so that
   * selecting an object does NOT trigger an automatic box refit (bug #2).
   */
  function onSelectionChanged() {
    AutoFitGuard.patch();   // re-attempt controller patch (may appear after install)
    AutoFitGuard.pulse();
    syncInspectorDrawer((bridge.getSelectedIds?.() || []).length > 0);
    scheduleUpdate();
  }

  /**
   * Wire the mobile inspector drawer toggle (topbar button in index.html).
   * Toggling is idempotent and safe on desktop, where the drawer CSS is inert.
   */
  function wireInspectorDrawer() {
    const toggle = $('#v54InspectorDrawer');
    if (!toggle) return;
    const sync = () => toggle.setAttribute('aria-expanded', String(document.body.classList.contains('right-open')));
    toggle.addEventListener('click', () => {
      const open = document.body.classList.toggle('right-open');
      const layout = window.EInviteResponsiveLayout;
      if (layout && typeof layout.mode === 'function' && layout.mode() !== 'desktop') {
        if (open) layout.openInspector?.(); else layout.closeInspector?.();
      }
      sync();
    });
    document.addEventListener('einvite:workspace-resized', sync);
    sync();
  }

  // =========================================================================
  // Install / destroy
  // =========================================================================
  /**
   * Install the module: build chrome, wire events, register commands, and
   * observe the DOM. Called once on DOMContentLoaded (or immediately if the
   * DOM is already ready).
   */
  function install() {
    document.body.classList.add('workspace-experience-v54');
    ensureHud();
    ensureSelectionCard();
    ensureHoverBox();
    ensureInspectorMode();
    wireInspectorDrawer();
    organizeHeader();
    organizeFooter();
    registerCommands();
    updateZoomLabel();
    scheduleUpdate();

    // Fit the canvas on first paint for small screens (better first impression).
    if (matchMedia('(max-width:600px)').matches) {
      requestAnimationFrame(() => requestAnimationFrame(() => controller.fit()));
    }

    // Canvas input handlers.
    on(viewport, 'wheel', wheelZoom, { capture: true, passive: false });
    on(document, 'pointerdown', beginDuplicateDrag, true);
    on(window, 'pointermove', moveDuplicateDrag, true);
    on(window, 'pointerup', event => endDuplicateDrag(event, false), true);
    on(window, 'pointercancel', event => endDuplicateDrag(event, true), true);
    on(viewport, 'pointerdown', startMiddlePan, true);
    on(viewport, 'pointermove', moveMiddlePan, true);
    on(viewport, 'pointerup', endMiddlePan, true);
    on(viewport, 'pointercancel', endMiddlePan, true);
    on(stage, 'pointermove', hoverMove, { passive: true });
    on(stage, 'pointerleave', hideHover);

    // Auto-fit guard wiring — fixes "font shrinks on resize" & "box resizes on click".
    on(stage, 'pointerdown', onHandlePointerDown, true);
    on(window, 'pointerup', onHandlePointerUp, true);
    on(document, 'einvite:selection-changed', onSelectionChanged);
    // Also try to patch the typography service once it's available.
    on(window, 'einvite:editor-ready', () => { AutoFitGuard.patch(); organizeHeader(); organizeFooter(); });

    // Keyboard parity for the same popovers: a role="menu" must close on Escape,
    // and focus has to land back on the control that opened it.
    on(document, 'keydown', event => {
      if (event.key !== 'Escape') return;
      if (popover && !popover.hidden) { closeZoomMenu(); $('.v54-zoom-value')?.focus(); }
      const tools = $('.v54-footer-tools-menu');
      if (tools && !tools.hidden) {
        tools.hidden = true;
        $('.v54-footer-tools-trigger')?.setAttribute('aria-expanded', 'false');
        $('.v54-footer-tools-trigger')?.focus();
      }
    });

    // Close popovers on outside interaction.
    on(document, 'pointerdown', event => {
      if (!event.target.closest?.('#v54ZoomMenu,.v54-zoom-value')) closeZoomMenu();
      if (!event.target.closest?.('.v54-footer-tools')) {
        const menu = $('.v54-footer-tools-menu');
        if (menu) {
          menu.hidden = true;
          $('.v54-footer-tools-trigger')?.setAttribute('aria-expanded', 'false');
        }
      }
    }, true);

    on(window, 'einvite:zoom-changed', scheduleUpdate);
    on(window, 'einvite:state-applied', () => { AutoFitGuard.patch(); scheduleUpdate(); });
    on(window, 'einvite:editor-state-replaced', scheduleUpdate);
    on(window, 'resize', () => { AutoFitGuard.patch(); organizeHeader(); organizeFooter(); scheduleUpdate(); });

    // Observe DOM mutations so the selection card / empty state stay in sync.
    // NOTE: we deliberately do NOT re-run organiseHeader/Footer here — doing
    // so on every mutation is what previously caused the toolbar to "jump".
    contextObserver = new MutationObserver(records => {
      if (records.some(record => {
        const target = record.target;
        if (target?.closest?.('.v54-context-menu')) return false;
        return target?.id === 'v23ContextToolbar' || target?.parentElement?.id === 'v23ContextToolbar' ||
          [...record.addedNodes].some(node => node.nodeType === 1 && (node.id === 'v23ContextToolbar' || node.querySelector?.('#v23ContextToolbar')));
      })) scheduleUpdate();
    });
    contextObserver.observe(document.body, { childList: true, subtree: true });

    selectionObserver = new MutationObserver(scheduleUpdate);
    selectionObserver.observe(stage, { subtree: true, attributes: true, attributeFilter: ['class'], childList: true });

    resizeObserver = new ResizeObserver(() => { organizeHeader(); organizeFooter(); scheduleUpdate(); });
    resizeObserver.observe(wrap);
    resizeObserver.observe(viewport);

    // Expose the public API under BOTH the new (EInviteEditorCore) and the
    // legacy (EInviteWorkspaceExperience) namespaces. Claiming the legacy
    // namespace means any late-loading copy of the old
    // `workspace-experience-v24.js` (which guards on
    // `window.EInviteWorkspaceExperience?.version >= 24`) will detect v>=24
    // and no-op, preventing duplicate canvas chrome. This lets us supersede
    // the old module safely even if a deferred loader still references it.
    window.EInviteWorkspaceExperience = Object.freeze({
      version: 24,
      refresh: scheduleUpdate,
      zoomToSelection: () => controller.zoomToSelection(),
      get hud() { return hud; }
    });
    window.EInviteEditorCore = Object.freeze({
      ...api,
      refresh: scheduleUpdate,
      renderContextPanel,
      refreshContextPanel,
      zoomToSelection: () => controller.zoomToSelection(),
      AutoFitGuard,
      get hud() { return hud; }
    });
  }

  /**
   * Tear down everything: remove listeners, observers, and DOM. Used by the
   * editor lifecycle so the module can be safely re-initialised.
   */
  function destroy() {
    destroyed = true;
    if (raf) cancelAnimationFrame(raf);
    if (duplicateDrag) {
      duplicateDrag.previews.forEach(preview => preview.remove());
      duplicateDrag = null;
    }
    cleanup.splice(0).forEach(fn => { try { fn(); } catch { /* ignore */ } });
    contextObserver?.disconnect();
    selectionObserver?.disconnect();
    resizeObserver?.disconnect();
    hud?.remove();
    popover?.remove();
    selectionCard?.remove();
    hoverBox?.remove();
    inspectorToggle?.remove();
    inspectorEmpty?.remove();
    footerTools?.remove();
    headerHomes.forEach(marker => marker.remove());
    headerHomes.clear();
    document.body.classList.remove('workspace-experience-v54', 'v54-inspector-essential', 'v54-has-selection', 'ei-suppress-autofit');
    delete window.EInviteEditorCore;
  }
  api.destroy = destroy;

  // Register teardown with the editor lifecycle if present.
  window.EInviteLifecycle?.add?.(destroy);

  // Boot.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();;/**
 * ui-layout.js — Editor layout chrome (v54 refactor).
 *
 * Consolidates the former `windows-ui-v16.js` into a documented, stable
 * module responsible for the studio editor's surrounding layout:
 *
 *   • Stage column ordering (toolbar → context row → viewport → page dock).
 *   • The toolbar "More" overflow menu (secondary canvas/studio controls).
 *   • Keeping the active page chip and active tool visible (scroll-into-view).
 *
 * BUG FIXES vs. the old v16 module:
 *
 *   3. Stable toolbar — the old module ran `moveSecondaryControls()` and
 *      `layoutContextToolbar()` on EVERY DOM mutation (via a MutationObserver
 *      on `childList` + `class` + `aria-pressed`), which physically moved
 *      toolbar buttons into/out of the "More" panel and toggled the context
 *      row between `display:block` and `display:none`. That is what made the
 *      shortcut-bar icons "jump". This module instead:
 *        - Populates the "More" panel ONCE on install, then only re-checks on
 *          viewport resize (debounced). Buttons keep their DOM position.
 *        - Gives the context row a stable, reserved height so showing/hiding
 *          it never shifts surrounding chrome.
 *   4. Full sidebar labels — adds a "collapse to icons" toggle so long
 *      category titles (Elements, Uploads, …) can be shown in full, with an
 *      icon-only mode available when space is tight.
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';

  // Idempotency guard.
  if (window.EInviteUiLayout?.version >= 54) return;
  window.EInviteUiLayout = { version: 54 };

  // Claim the legacy v16 namespace too, so any stray late-loading copy of the
  // old `windows-ui-v16.js` (guarded by `window.__einviteWindowsUiV16`) will
  // no-op rather than double-process the toolbar chrome.
  window.__einviteWindowsUiV16 = true;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);
  /** @type {(selector:string, root?:ParentNode)=>Element[]} */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const body = document.body;
  // Bail when the editor stage is not present (non-editor routes).
  if (!body || !$('#stage')) return;

  body.classList.add('windows-ui-v54');

  // --- Module state ----------------------------------------------------------
  /** The lazily-built "More" details element + its panel. */
  let toolbarMore = null;
  let morePanel = null;
  /** Set of controls already moved into the More panel (avoids double-move). */
  const moved = new Set();
  /** Debounce handle for resize-driven re-checks. */
  let resizeRaf = 0;

  /**
   * Selectors for secondary controls that belong in the toolbar "More" menu.
   * These are the long-tail of canvas/studio toggles that would otherwise
   * crowd the primary toolbar.
   */
  const secondarySelectors = [
    '#gridToggle', '#rulersToggle', '#safeMarginToggle', '#copyObjects', '#pasteObjects',
    '#workflowV5Focus', '#workflowV6FlowBtn', '#eiFocusToggle', '.ei-experience-launch', '#eiTimelineLaunch', '#v13OperationsBtn'
  ];

  /**
   * Resolve the primary canvas toolbar element.
   * @returns {Element|null}
   */
  function toolbar() {
    return $('.stage-wrap > .studio-canvas-toolbar, .stage-wrap > .toolbar');
  }

  /**
   * Lazily build the "More" details menu inside the toolbar and wire its
   * outside-click / Escape dismissal. The menu is appended near the active
   * canvas label so it sits at the end of the primary toolbar group.
   * @returns {HTMLDetailsElement|null}
   */
  function ensureToolbarMore() {
    const bar = toolbar();
    if (!bar) return null;
    if (!toolbarMore) {
      toolbarMore = document.createElement('details');
      toolbarMore.id = 'v54ToolbarMore';
      toolbarMore.className = 'v54-toolbar-more';
      toolbarMore.innerHTML =
        '<summary aria-label="More canvas and studio tools">More <span aria-hidden="true">⌄</span></summary>' +
        '<div class="v54-toolbar-more-panel" role="group" aria-label="More canvas and studio tools"></div>';
      morePanel = $('.v54-toolbar-more-panel', toolbarMore);
      const label = $('#activeCanvasLabel', bar);
      if (label) bar.insertBefore(toolbarMore, label);
      else bar.append(toolbarMore);

      // Reflect open state onto aria-expanded for assistive tech.
      toolbarMore.addEventListener('toggle', () => {
        toolbarMore.querySelector('summary')?.setAttribute('aria-expanded', String(toolbarMore.open));
      });
      // Close on outside pointerdown.
      document.addEventListener('pointerdown', event => {
        if (toolbarMore?.open && !event.target.closest('#v54ToolbarMore')) toolbarMore.open = false;
      }, true);
      // Close on Escape and return focus to the summary.
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && toolbarMore?.open) {
          event.preventDefault();
          toolbarMore.open = false;
          toolbarMore.querySelector('summary')?.focus({ preventScroll: true });
        }
      }, true);
    }
    return toolbarMore;
  }

  /**
   * Move each secondary control into the "More" panel. Runs ONCE on install
   * (and again only if new controls appear after a resize), so the toolbar
   * layout is stable and icons do not jump on every selection/mutation.
   */
  function populateToolbarMore() {
    ensureToolbarMore();
    if (!morePanel) return;
    secondarySelectors.forEach(selector => {
      const element = $(selector);
      if (!element || moved.has(element) || element.closest('#v54ToolbarMore')) return;
      moved.add(element);
      element.classList.add('v54-toolbar-secondary');
      // Clear any inline positioning that the old module left behind so the
      // control lays out naturally inside the panel.
      ['left', 'right', 'top', 'bottom', 'transform'].forEach(prop => element.style.removeProperty(prop));
      morePanel.append(element);
    });
  }

  /**
   * Close the "More" menu after a panel button is activated.
   * @param {Event} event
   */
  function closeMoreAfterAction(event) {
    if (!toolbarMore?.open || !event.target.closest('.v54-toolbar-more-panel button')) return;
    requestAnimationFrame(() => { if (toolbarMore) toolbarMore.open = false; });
  }

  /**
   * Scroll the active page chip into view within the page dock track. Called
   * after navigation clicks and on resize.
   */
  function keepActivePageVisible() {
    const track = $('.workflow-page-dock-track');
    const active = $('.workflow-page-chip.active', track || document);
    if (!track || !active) return;
    const target = Math.max(0, active.offsetLeft - (track.clientWidth - active.offsetWidth) / 2);
    if (Math.abs(track.scrollLeft - target) > 1) track.scrollTo({ left: target, behavior: 'auto' });
  }

  /**
   * Scroll the active tool button into view within its tool rail.
   * @param {ParentNode} [root=document]
   */
  function keepActiveToolVisible(root = document) {
    $$('.ei-tool-rail', root).forEach(rail => {
      const active = $('.active,[aria-pressed="true"]', rail);
      if (!active) return;
      const left = active.offsetLeft;
      const right = left + active.offsetWidth;
      const visibleLeft = rail.scrollLeft;
      const visibleRight = visibleLeft + rail.clientWidth;
      if (left < visibleLeft) rail.scrollTo({ left: Math.max(0, left - 8), behavior: 'auto' });
      else if (right > visibleRight) rail.scrollTo({ left: Math.max(0, right - rail.clientWidth + 8), behavior: 'auto' });
    });
  }

  /**
   * Promote the context toolbar to a stable, reserved row above the viewport.
   *
   * Unlike the old module, this NEVER toggles `display:none` (which caused
   * layout shift). Instead it reserves a stable min-height row and only
   * flips a `visible` class so the surrounding chrome never moves.
   */
  function ensureContextRow() {
    const wrap = $('.stage-wrap');
    const context = $('.ei-context-toolbar');
    if (!wrap || !context) return;

    if (!context.classList.contains('v54-context-row')) {
      context.classList.add('v54-context-row');
      const viewportEl = $('#canvasViewport', wrap);
      if (viewportEl) wrap.insertBefore(context, viewportEl);
      else wrap.append(context);
    }

    // Decide whether the context row has content worth showing. We check
    // children length and an explicit hide flag, but we never set
    // display:none — the reserved row keeps surrounding layout stable.
    const hasContent = context.children.length > 0 && context.style.display !== 'none';
    context.classList.toggle('visible', hasContent);
  }

  /**
   * Mark the page dock row as reserved so it keeps its slot in the column.
   */
  function ensureDockOrder() {
    const wrap = $('.stage-wrap');
    const dock = $('#workflowPageDock');
    if (wrap && dock && dock.parentElement === wrap) {
      dock.dataset.v54ReservedRow = 'true';
      requestAnimationFrame(keepActivePageVisible);
    }
  }

  /**
   * Debounced resize re-check: re-populate the More panel (in case new
   * controls appeared) and re-run the stability passes. Toolbar buttons keep
   * their positions; only overflow discovery runs.
   */
  function onResize() {
    if (resizeRaf) return;
    resizeRaf = requestAnimationFrame(() => {
      resizeRaf = 0;
      populateToolbarMore();
      ensureContextRow();
      ensureDockOrder();
      keepActivePageVisible();
      keepActiveToolVisible();
    });
  }

  // =========================================================================
  // Sidebar labels — full text + collapse-to-icons toggle (bug #4)
  // =========================================================================
  /** localStorage key for the sidebar collapse preference. */
  const SIDEBAR_KEY = 'einvite-v54-sidebar-collapsed';

  /**
   * Read the persisted sidebar collapse preference.
   * @returns {boolean}
   */
  function sidebarCollapsed() {
    try { return localStorage.getItem(SIDEBAR_KEY) === '1'; } catch { return false; }
  }

  /**
   * Apply (or clear) the sidebar collapsed state. Collapsed shows icons only;
   * expanded shows full category labels so "Elements"/"Uploads" are readable.
   * @param {boolean} collapsed
   */
  function setSidebarCollapsed(collapsed) {
    body.classList.toggle('sidebar-collapsed', collapsed);
    try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0'); } catch { /* ignore */ }
    const toggle = $('#v54SidebarCollapse');
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(collapsed));
      toggle.title = collapsed ? 'Show labels' : 'Show icons only';
      const label = toggle.querySelector('.v54-collapse-label');
      if (label) label.textContent = collapsed ? '›' : '‹';
    }
  }

  /**
   * Inject a collapse toggle button into the tool rail header so the user can
   * switch between "full labels" and "icon-only" modes. Idempotent.
   * If the button already exists in the HTML (pre-rendered for first paint),
   * just wire up its click handler and sync its state.
   */
  /**
   * What the sidebar toggle means at the current width.
   *
   * Above 820px it switches the rail between full labels and icon-only. At or below 820px the rail
   * column is translated off-canvas on purpose, so that toggle has no visible effect — but the
   * compact layout still owns a real "sidebar": the creation drawer in
   * editor-responsive-contract-v27. Drive that instead of doing nothing.
   */
  function toggleSidebar() {
    const owner = window.EInviteResponsiveLayout;
    if (innerWidth <= 820 && owner && typeof owner.openCreation === 'function' && owner.mode && owner.mode() !== 'desktop') {
      if (body.classList.contains('mobile-pane-collapsed')) owner.openCreation();
      else owner.closeCreation();
      return;
    }
    setSidebarCollapsed(!body.classList.contains('sidebar-collapsed'));
  }

  function ensureSidebarCollapseButton() {
    const existing = $('#v54SidebarCollapse');
    if (existing) {
      // Wire up the click handler on the pre-rendered button.
      existing.onclick = toggleSidebar;
      setSidebarCollapsed(sidebarCollapsed());  // sync aria/title
      return;
    }
    const rail = $('.studio-tool-rail');
    if (!rail) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'v54SidebarCollapse';
    button.className = 'v54-sidebar-collapse';
    button.setAttribute('aria-pressed', String(sidebarCollapsed()));
    button.title = sidebarCollapsed() ? 'Show labels' : 'Show icons only';
    button.innerHTML = '<span class="v54-collapse-label" aria-hidden="true">‹</span><span class="sr-only">Toggle sidebar labels</span>';
    button.addEventListener('click', toggleSidebar);
    // Place at the top of the rail so it is always reachable.
    rail.prepend(button);
  }

  // =========================================================================
  // Wiring
  // =========================================================================
  /**
   * One-shot install: build chrome once, then attach only lightweight
   * scroll-into-view listeners. Crucially, we do NOT observe every DOM
   * mutation — that was the source of the "jumping" toolbar.
   */
  function install() {
    populateToolbarMore();
    ensureContextRow();
    ensureDockOrder();
    ensureSidebarCollapseButton();
    setSidebarCollapsed(sidebarCollapsed());
    keepActivePageVisible();
    keepActiveToolVisible();

    document.addEventListener('click', closeMoreAfterAction, true);
    // Keep the active page/tool scrolled into view after navigation clicks —
    // this is cheap and does not move toolbar chrome.
    document.addEventListener('click', event => {
      if (event.target.closest('.workflow-page-chip,.workflow-page-add,#workflowV7DockFlow')) requestAnimationFrame(keepActivePageVisible);
      // The callback is wrapped: requestAnimationFrame invokes it with a DOMHighResTimeStamp,
      // which used to land in keepActiveToolVisible's `root` parameter and throw
      // "root.querySelectorAll is not a function" on every tool click.
      if (event.target.closest('.ei-tool-rail button')) requestAnimationFrame(() => keepActiveToolVisible());
    }, true);

    // Re-check overflow only on resize, not on every state change.
    window.addEventListener('resize', onResize, { passive: true });

    // Re-run the stability passes once the editor is ready / state applied —
    // but throttled and NOT on every selection (which would re-introduce
    // jumping). The context-row class is cheap to re-assert.
    window.addEventListener('einvite:state-applied', () => setTimeout(() => { ensureContextRow(); keepActivePageVisible(); }, 80));
    document.addEventListener('einvite:editor-ready', () => setTimeout(() => { ensureContextRow(); ensureDockOrder(); }, 80));

    // Expose API for other modules / debugging.
    window.EInviteUiLayout = Object.freeze({
      version: 54,
      refresh: () => { populateToolbarMore(); ensureContextRow(); ensureDockOrder(); keepActivePageVisible(); keepActiveToolVisible(); },
      setSidebarCollapsed,
      sidebarCollapsed
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();;/**
 * ui-components.js — Editor workspace components (v54 refactor).
 *
 * A small, focused module that fixes text-overflow defects in the workspace
 * navigation chrome (bug #5: "Navigation Overflow — workspace navigation
 * cards/bubbles must expand or wrap text to fully contain long words").
 *
 * The root cause: many navigation surfaces use `white-space:nowrap` or omit an
 * `overflow-wrap` rule, so a single long word (a long invitation title, a
 * guest name, a venue, a template name) spills outside its card and overlaps
 * neighbours. CSS alone can fix the wrapping; this module additionally:
 *
 *   • Classifies workspace navigation surfaces so the CSS in
 *     `editor-styles.css` has stable hooks to target.
 *   • Provides a tiny progressive-enhancement that measures whether a card's
 *     text still overflows after wrapping and, if so, expands the card's
 *     min-height so the text is never clipped.
 *   • Adds a "long-word" guard to user-generated bubbles (page chips,
 *     layer rows, invite/material cards) so the layout stays predictable.
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';
  if (window.EInviteUiComponents?.version >= 54) return;

  /** @type {(selector:string, root?:ParentNode)=>Element[]} */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  /**
   * CSS selectors for the workspace navigation surfaces whose text must never
   * spill. Shared between the tagging pass and the overflow-measurement pass.
   */
  const NAV_SURFACE_SELECTORS = [
    // Studio rail + pane cards
    '.studio-rail-button',
    '.studio-quick-grid button',
    '.studio-tip-card',
    '.page-nav-card',
    // Workflow chips/bubbles
    '.workflow-page-chip',
    '.workflow-page-chip strong',
    '.workflow-recent-grid button',
    '.workflow-search-results button',
    // Library / material / invite cards
    '.invite-card .invite-body h2',
    '.invite-card .actions button',
    '.material-card-page',
    '.studio-card',
    '.template-choice',
    '.template-live-thumb',
    // Layer rows + command palette rows
    '.layer-row',
    '.v23-command-row',
    // Dashboard overview + filter tabs
    '.dashboard-overview-cards article',
    '.dashboard-filter-tabs button',
    // Inspector headings / labels
    '.studio-inspector-heading strong',
    '.studio-pane-heading h1'
  ];
  const NAV_SURFACE_QUERY = NAV_SURFACE_SELECTORS.join(',');

  /**
   * Tag every matching surface with a stable hook class so the CSS rules in
   * `editor-styles.css` can apply wrapping without fragile selector chains.
   * Idempotent (the class is only added once).
   */
  function tagNavSurfaces(root = document) {
    // Scan the given root for the whole selector list in one pass. Callers
    // reacting to specific inserted subtrees pass that subtree, so a burst of
    // unrelated DOM churn does not re-scan the whole document.
    const nodes = [...(root.matches?.(NAV_SURFACE_QUERY) ? [root] : []), ...$$(NAV_SURFACE_QUERY, root)];
    nodes.forEach(node => {
      if (!node.classList.contains('v54-nav-text')) node.classList.add('v54-nav-text');
    });
  }

  /**
   * Progressive enhancement: after the browser applies the CSS wrapping
   * rules, some cards may still be too short for their (now-wrapped) text and
   * would clip it. Measure scrollHeight vs. clientHeight and expand the
   * min-height so the full text is visible.
   *
   * This runs on a ResizeObserver of the stage + on editor events, throttled.
   */
  let expandRaf = 0;
  /**
   * Expand any nav card whose wrapped text is taller than its box.
   */
  function expandOverflowingCards() {
    if (expandRaf) return;
    expandRaf = requestAnimationFrame(() => {
      expandRaf = 0;
      const nodes = $$('.v54-nav-text');
      // Read every box FIRST, write every box SECOND.
      //
      // The previous version read and wrote inside one loop. Writing
      // `style.minHeight` dirties style, so each following `node.scrollHeight`
      // read forced a fresh document style recalculation + layout — up to one
      // full recalculation per matched node, on every mutation, on every resize,
      // and on every font load. Measured on index.html before this change:
      // 3,429 ms of Recalculate Style across 24 invocations (max 358 ms,
      // 143 ms per invocation for 30 nodes). Reading first costs one forced
      // recalculation for the whole batch instead.
      const overflowed = [];
      for (const node of nodes) {
        // Only measure leaf text containers (skip wrappers without their own
        // text height).
        const height = node.scrollHeight;
        if (height - node.clientHeight > 2) overflowed.push([node, `${Math.ceil(height)}px`]);
      }
      for (const [node, next] of overflowed) {
        // Assigning the value it already has still invalidates style, so skip it.
        if (node.style.minHeight !== next) node.style.minHeight = next;
      }
    });
  }

  /**
   * Observe the stage + panes for content changes that may introduce new nav
   * surfaces (e.g. switching tabs renders a new list of cards), then re-tag
   * and re-measure. Throttled via rAF so bursts are cheap.
   */
  function observeSurfaces() {
    const target = document.querySelector('#stage, .studio-pane-host, .studio-inspector-host');
    if (typeof MutationObserver === 'undefined') return;
    const observer = new MutationObserver(mutations => {
      // Only element insertions can introduce a nav surface. Attribute-only and
      // character-data batches cannot, and skipping them keeps a re-render that
      // only toggles classes from scheduling a measurement pass.
      const added = [];
      for (const m of mutations) for (const node of m.addedNodes || []) if (node.nodeType === 1) added.push(node);
      if (!added.length) return;
      // Tag only the inserted subtrees; a batch that cannot contain a nav
      // surface (the common case during canvas gestures) skips the pass whole.
      let relevant = false;
      for (const node of added) {
        if (node.matches(NAV_SURFACE_QUERY) || node.querySelector(NAV_SURFACE_QUERY)) { relevant = true; break; }
      }
      if (!relevant) return;
      for (const node of added) tagNavSurfaces(node);
      expandOverflowingCards();
    });
    // `target` is kept as the deliberate observation root: it is where the
    // surfaces this module tags are rendered. document.body is the fallback when
    // the editor shell is not on the page at all (module is loaded site-wide).
    observer.observe(target || document.body, { childList: true, subtree: true });
    // Re-measure on resize as font metrics / widths change.
    window.addEventListener('resize', () => { tagNavSurfaces(); expandOverflowingCards(); }, { passive: true });
  }

  /**
   * Install the module.
   */
  function install() {
    tagNavSurfaces();
    expandOverflowingCards();
    observeSurfaces();
    // Defer a second pass so fonts have loaded and metrics are final.
    if (document.fonts?.ready?.then) {
      document.fonts.ready.then(() => { tagNavSurfaces(); expandOverflowingCards(); });
    }
    window.EInviteUiComponents = Object.freeze({
      version: 54,
      refresh: () => { tagNavSurfaces(); expandOverflowingCards(); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();;/*
 * Inspector reorganisation (2026-10-30).
 *
 * The Edit pane had grown into ~5,600 px of stacked panels: a transform card,
 * six typography cards, duplicate alignment grids, motion tools, V13 panels,
 * and the orphaned Design pane. This module keeps the existing DOM nodes (and
 * therefore every id, listener and save path) but files them into a short
 * icon-led toolbar plus one accordion group per job:
 *
 *   Position · Text · Style · Arrange · Motion · Page · More
 *
 * Position opens by default so size/position stay immediate. Text, Style and
 * Arrange hold the essentials the owner asked to keep in the pane; the rest is
 * one click away. The old Design tab is retired here: its palette, template and
 * background controls move into the always-available Page group.
 */
(() => {
  'use strict';

  const pane = () => document.querySelector('[data-inspector-pane="object"]');
  const props = () => pane()?.querySelector('#properties');
  const tools = [
    ['position', 'Position & size', 'M12 3v18M3 12h18M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3'],
    ['text', 'Text', 'M5 6h14M12 6v13M8 19h8'],
    ['style', 'Appearance', 'M12 3a9 9 0 1 0 0 18zM12 3v18'],
    ['arrange', 'Arrange', 'M4 7h16M4 12h16M4 17h16'],
    ['motion', 'Motion', 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM10 9l6 3-6 3z'],
    ['page', 'Page & palette', 'M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5'],
    ['more', 'More tools', 'M6 12h.01M12 12h.01M18 12h.01']
  ];
  const meta = {
    position: ['⊹', 'Position', 'X, Y, size and rotation'],
    text: ['T', 'Text', 'Content, type and fit'],
    style: ['◐', 'Style', 'Fill, border, shadow and photo'],
    arrange: ['⇅', 'Arrange', 'Align, order, lock and delete'],
    motion: ['✦', 'Motion', 'Animation, effects and timing'],
    page: ['▤', 'Page', 'Palette, background and template'],
    more: ['⋯', 'More', 'Advanced and responsive tools']
  };
  const icon = (path) => `<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg>`;
  let built = false;
  let busy = false;
  let queued = 0;

  const hasSelection = () => document.body.classList.contains('v54-has-selection')
    || Boolean(document.querySelector('.object.selected, .object.multi-selected'));

  const make = (tag, cls, html) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
  };

  function group(name) {
    const [iconText, label, hint] = meta[name];
    const details = make('details', 'ix-group');
    details.dataset.ixGroup = name;
    details.innerHTML = `<summary><span class="ix-group-icon" aria-hidden="true">${iconText}</span><span class="ix-group-name">${label}</span><small class="ix-group-hint">${hint}</small><span class="ix-chevron" aria-hidden="true">⌄</span></summary><div class="ix-body"></div>`;
    details.addEventListener('toggle', () => {
      if (details.open && !busy) closeOthers(details);
      syncTools();
    });
    return details;
  }

  function closeOthers(current) {
    const host = current.parentElement;
    if (!host) return;
    host.querySelectorAll(':scope > details.ix-group[open]').forEach((other) => {
      if (other !== current) other.open = false;
    });
  }

  function openGroup(name, scroll = true) {
    const target = pane()?.querySelector(`.ix-group[data-ix-group="${CSS.escape(name)}"]`);
    if (!target || target.hidden) return;
    target.open = true;
    closeOthers(target);
    if (scroll) target.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    syncTools();
  }

  function build() {
    const hostPane = pane();
    const hostProps = props();
    if (!hostPane || !hostProps || hostPane.querySelector('.ix-toolbox')) return false;

    // Keep the shell that app.js hides/shows, but move its contents into the
    // groups. The summary stays at the top of the pane for quick selection info.
    const summary = hostProps.querySelector('.selection-summary');
    const toolbox = make('div', 'ix-toolbox');
    toolbox.setAttribute('role', 'toolbar');
    toolbox.setAttribute('aria-label', 'Edit tools');
    tools.forEach(([name, label, path]) => {
      const button = make('button', 'ix-tool');
      button.type = 'button';
      button.dataset.ixTool = name;
      button.setAttribute('aria-label', label);
      button.title = label;
      button.innerHTML = `${icon(path)}<em class="ix-tool-tip">${label}</em>`;
      toolbox.append(button);
    });

    const groups = make('div', 'ix-groups');
    Object.keys(meta).forEach((name) => groups.append(group(name)));

    hostPane.insertBefore(toolbox, hostPane.querySelector('#noSelection'));
    hostPane.append(groups);
    toolbox.addEventListener('click', (event) => {
      const button = event.target.closest('[data-ix-tool]');
      if (!button || button.disabled) return;
      const name = button.dataset.ixTool;
      const target = groups.querySelector(`[data-ix-group="${CSS.escape(name)}"]`);
      if (!target) return;
      if (target.open) target.open = false;
      else openGroup(name);
      syncTools();
    });
    return true;
  }

  function slot(name) {
    return pane()?.querySelector(`.ix-group[data-ix-group="${CSS.escape(name)}"] .ix-body`);
  }

  function move(node, name) {
    const target = slot(name);
    if (!node || !target || target.contains(node)) return false;
    target.append(node);
    return true;
  }

  function hide(node) {
    if (node) node.hidden = true;
  }

  function compactTypography() {
    const root = pane()?.querySelector('#typographyControls');
    if (!root) return;
    root.hidden = true;
    const textSlot = slot('text');
    if (!textSlot) return;
    root.querySelectorAll(':scope > .v20-typography-shell > .v20-inspector-group, :scope > .v20-inspector-group').forEach((section) => {
      if (section.closest('.ix-sub')) return;
      const title = (section.querySelector('h3')?.textContent || 'Text').trim();
      // The parent tool is already called Text; a child sub-panel with the
      // same label read as a second, redundant section.
      const label = /^text$/i.test(title) ? 'Style & type' : title;
      const sub = make('details', 'ix-sub');
      sub.dataset.title = title;
      sub.innerHTML = `<summary><span>${label}</span><span class="ix-chevron" aria-hidden="true">⌄</span></summary>`;
      const body = make('div', 'ix-sub-body');
      section.classList.add('ix-flat');
      body.append(section);
      sub.append(body);
      textSlot.append(sub);
    });
  }

  // Page and More collect several unrelated cards. Fold each card into a
  // compact sub-accordion so opening the tool never drops a 1,300–1,800px wall
  // of controls into the pane.
  function foldSections(name) {
    const body = slot(name);
    if (!body) return;
    // Only fold direct children that are still loose. Late modules (responsive
    // constraints, shared styles) append cards after the first pass, so an
    // all-or-nothing guard left them as an unfolded wall at the bottom.
    const children = [...body.children].filter((node) => !node.classList.contains('ix-sub-fold'));
    const headingOf = (node) => {
      if (node.matches('h2, h3')) return (node.textContent || '').trim();
      return (node.querySelector(':scope > h2, :scope > .final-panel-title h2, :scope > header h2')?.textContent || '').trim();
    };
    const units = [];
    let current = null;
    children.forEach((node) => {
      const heading = headingOf(node);
      if (node.matches('h2, h3') || (heading && !node.matches('label'))) {
        current = { title: heading || 'Section', nodes: [] };
        units.push(current);
      }
      if (current) current.nodes.push(node);
    });
    if (!units.length) return;
    units.forEach((unit) => {
      const sub = make('details', 'ix-sub ix-sub-fold');
      const summary = make('summary');
      const label = make('span');
      // More holds an advanced transform card whose heading matched the
      // Position tool exactly. Rename the duplicate so the two read as
      // different jobs.
      label.textContent = name === 'more' && /^position\s*&\s*size$/i.test(unit.title) ? 'Advanced transform' : unit.title;
      const chevron = make('span', 'ix-chevron', '⌄');
      chevron.setAttribute('aria-hidden', 'true');
      summary.append(label, chevron);
      const inner = make('div', 'ix-sub-body');
      unit.nodes.forEach((node) => {
        if (node.matches('h2, h3')) node.hidden = true;
        else node.querySelectorAll(':scope > h2, :scope > .final-panel-title h2').forEach((heading) => { heading.hidden = true; });
        inner.append(node);
      });
      sub.append(summary, inner);
      body.append(sub);
    });
  }

  function moveLabel(selector, name) {
    const node = pane()?.querySelector(selector);
    if (!node || node.closest('.ix-groups')) return;
    move(node.closest('label,.toggle-row'), name);
  }

  function moveSection(selector, name) {
    const node = pane()?.querySelector(selector);
    if (!node || node.closest('.ix-groups')) return;
    move(node, name);
  }

  function classify() {
    const hostPane = pane();
    const hostProps = props();
    if (!hostPane || !hostProps || busy) return;
    busy = true;
    try {
      if (!built) built = build();
      if (!hostPane.querySelector('.ix-groups')) return;

      // Selection summary lives above the toolbar and is hidden with #properties.
      const summary = hostProps.querySelector('.selection-summary');
      if (summary) summary.hidden = false;

      // Position — keep the precise transform card open at rest.
      const position = hostPane.querySelector('#peTransformPanel');
      if (position && !position.closest('.ix-groups')) move(position, 'position');

      // Text — the text field plus the six typography cards, each collapsible.
      const textArea = hostProps.querySelector('#textContentLabel');
      if (textArea && !textArea.closest('.ix-groups')) move(textArea, 'text');
      compactTypography();
      const textBox = hostPane.querySelector('#canvasPlusTextBox');
      if (textBox && !textBox.closest('.ix-groups') && slot('text')) {
        // Vertical alignment / box padding are a second block inside Text.
        // Fold them so opening Text shows the content field and a short list of
        // headings, not a fully expanded form below it.
        const sub = make('details', 'ix-sub');
        sub.dataset.title = 'Text box';
        sub.innerHTML = `<summary><span>Text box</span><span class="ix-chevron" aria-hidden="true">⌄</span></summary>`;
        const body = make('div', 'ix-sub-body');
        body.append(textBox);
        sub.append(body);
        slot('text').append(sub);
      }

      // Style — object appearance and the photo tools. The typography V19 style
      // recipes stay nearby because they restyle the selected object.
      const style = slot('style');
      if (style) {
        hostPane.querySelectorAll('h2').forEach((heading) => {
          if (/^appearance$/i.test(heading.textContent.trim()) && !heading.closest('.ix-groups')) move(heading, 'style');
        });
        ['objectOpacity', 'borderWidth', 'borderColor', 'borderRadius', 'shadowBlur', 'shadowColor'].forEach((id) => moveLabel(`#${id}`, 'style'));
        const recipes = hostPane.querySelector('.studio-style-recipes, #studio-style-recipes');
        if (recipes && !recipes.closest('.ix-groups')) move(recipes, 'style');
        const image = hostPane.querySelector('#imageControls');
        if (image && !image.closest('.ix-groups')) move(image, 'style');
        const photo = hostPane.querySelector('#canvasPlusAiTools');
        if (photo && !photo.closest('.ix-groups')) move(photo, 'style');
      }

      // Arrange — one alignment grid only, order, grouping, lock and delete.
      const arrange = slot('arrange');
      if (arrange) {
        const headings = [...hostPane.querySelectorAll('h2')].filter((h) => !h.closest('.ix-groups'));
        // Both headings said the same thing above one grid. Keep the grid and
        // let the Arrange group summary provide the label.
        headings.filter((h) => /^(alignment|align selected)$/i.test(h.textContent.trim())).forEach(hide);
        const mainGrid = hostPane.querySelector('#alignment-grid');
        if (mainGrid && !mainGrid.closest('.ix-groups')) move(mainGrid, 'arrange');
        const grids = [...hostPane.querySelectorAll('.alignment-grid')].filter((g) => !g.closest('.ix-groups'));
        grids.forEach((grid, index) => {
          if (index === 0) move(grid, 'arrange');
          else hide(grid);
        });
        move(hostPane.querySelector('#bringForward')?.closest('div.actions'), 'arrange');
        move(hostPane.querySelector('#groupObjects')?.closest('div.actions'), 'arrange');
        moveLabel('#showInHero', 'arrange');
        moveLabel('#objectLocked', 'arrange');
        // Duplicate and Delete are in the always-visible canvas action bar;
        // repeating them at the bottom of this group made the same command
        // appear three times on one screen. Keep the legacy buttons in the DOM
        // (toolbar handlers still click them) but out of the visible stack.
        hide(hostPane.querySelector('#duplicate'));
        hide(hostPane.querySelector('#deleteBtn'));
      }

      // Motion — animation picker, effects card, precision tools and timeline.
      const motion = slot('motion');
      if (motion) {
        move(hostPane.querySelector('#animationControls'), 'motion');
        move(hostPane.querySelector('.motion-measurement-settings'), 'motion');
        hostPane.querySelectorAll('.final-advanced-inspector').forEach((section) => {
          if (section.closest('.ix-groups') || section.id) return;
          const text = (section.querySelector('h2')?.textContent || '').trim();
          if (/effect|motion/i.test(text)) move(section, 'motion');
        });
        hostPane.querySelectorAll('.final-timeline').forEach((node) => move(node, 'motion'));
      }

      // Page — the retired Design tab, now always reachable.
      const pagePane = document.querySelector('[data-inspector-pane="theme"]');
      if (pagePane) {
        if (pagePane.classList.contains('active')) document.querySelector('[data-inspector-tab="object"]')?.click();
        const page = slot('page');
        if (page) {
          [...pagePane.children].forEach((node) => {
            if (node.classList.contains('studio-inspector-heading')) return;
            if (!page.contains(node)) page.append(node);
          });
        }
        document.querySelector('[data-inspector-tab="theme"]')?.remove();
        pagePane.remove();
      }
      foldSections('page');

      // More — advanced duplicates, responsive constraints and fine nudging.
      const more = slot('more');
      if (more) {
        move(hostPane.querySelector('#canvasPlusTransform'), 'more');
        move(hostPane.querySelector('#canvasPlusTextPlacement'), 'more');
        move(hostPane.querySelector('#eiSharedStylesV13'), 'more');
        move(hostPane.querySelector('#eiConstraintPanel'), 'more');
        move(hostPane.querySelector('#shapeControls'), 'more');
        const fine = [...hostPane.querySelectorAll('h2')].find((h) => /^fine position$/i.test(h.textContent.trim()));
        if (fine && !fine.closest('.ix-groups')) move(fine, 'more');
        hostPane.querySelectorAll('.actions').forEach((actions) => {
          if (actions.closest('.ix-groups')) return;
          if (actions.querySelector('[data-nudge], [data-size]')) move(actions, 'more');
        });
      }

      // Any late standalone card that belongs to none of the above is safer in
      // More than left as a 5,000 px wall below the groups.
      hostPane.querySelectorAll(':scope > .final-advanced-inspector, :scope > section[id]').forEach((section) => {
        if (section.closest('.ix-groups') || !section.id) return;
        if (['canvasPlusTransform', 'canvasPlusTextBox', 'canvasPlusTextPlacement', 'canvasPlusAiTools'].includes(section.id)) return;
        move(section, 'more');
      });
      foldSections('more');

      hide(hostProps.querySelector(':scope > .final-timeline'));
      const legacyHeading = hostPane.querySelector(':scope > h2.studio-inspector-heading');
      if (legacyHeading) hide(legacyHeading);
      syncSelection();
      syncTools();
    } finally {
      busy = false;
    }
  }

  function syncSelection() {
    const hostPane = pane();
    const hostProps = props();
    if (!hostPane || !hostProps) return;
    const selected = hasSelection();
    hostPane.classList.toggle('ix-has-selection', selected);
    hostPane.classList.toggle('ix-no-selection', !selected);
    // PW-2: the Transform panel is dimmed + hinted until something is selected.
    // canvas-plus owns the same class on its own refresh; keep both in step here
    // so a single click clears it and clearing the selection restores it.
    const transformPanel = hostPane.querySelector('#canvasPlusTransform') || document.querySelector('#canvasPlusTransform');
    if (transformPanel) transformPanel.classList.toggle('is-disabled', !selected);
    hostPane.querySelectorAll('.ix-tool').forEach((button) => {
      const objectTool = button.dataset.ixTool !== 'page';
      button.disabled = objectTool && !selected;
      button.setAttribute('aria-disabled', String(button.disabled));
      button.title = button.disabled ? 'Select an object on the canvas to use this tool' : button.getAttribute('aria-label');
    });
    hostPane.querySelectorAll('.ix-group').forEach((groupNode) => {
      const page = groupNode.dataset.ixGroup === 'page';
      groupNode.hidden = !page && !selected;
    });
    if (!selected) {
      const pageGroup = hostPane.querySelector('.ix-group[data-ix-group="page"]');
      if (pageGroup && !pageGroup.open) {
        busy = true;
        pageGroup.open = true;
        busy = false;
      }
    }
  }

  function syncTools() {
    const hostPane = pane();
    if (!hostPane) return;
    hostPane.querySelectorAll('.ix-tool').forEach((button) => {
      const target = hostPane.querySelector(`.ix-group[data-ix-group="${CSS.escape(button.dataset.ixTool)}"]`);
      const open = Boolean(target?.open);
      button.classList.toggle('active', open);
      button.setAttribute('aria-expanded', String(open));
    });
  }

  function installShare() {
    const publish = document.querySelector('[data-inspector-pane="publish"]');
    if (!publish || publish.dataset.shareModern === 'true') return;
    const slug = publish.querySelector('#publicSlug')?.closest('label');
    const access = publish.querySelector('#accessMode')?.closest('label');
    const password = publish.querySelector('#accessPassword')?.closest('label');
    const save = publish.querySelector('#savePublishingSettings');
    const state = publish.querySelector('#publishingSettingsState');
    const info = publish.querySelector('#publishInfo');
    const history = publish.querySelector('#historyBtn');
    const unpublish = publish.querySelector('#unpublishBtn');
    const rsvp = publish.querySelector('#rsvpBtn');
    const wishes = publish.querySelector('#wishesBtn');
    if (!info || !history) return;
    publish.dataset.shareModern = 'true';
    const shell = make('div', 'share-shell');
    shell.innerHTML = `
      <div class="share-hero">
        <div class="share-state"><span class="share-state-dot" aria-hidden="true"></span><div><strong data-share-state>Draft</strong><small data-share-hint>Publish to create a shareable link.</small></div></div>
        <div class="share-link"><input data-share-url type="text" readonly value="" aria-label="Public invitation link"><button type="button" data-share-copy>Copy</button></div>
        <div class="share-main-actions"><button type="button" class="primary" data-share-publish>Publish</button><button type="button" data-share-preview>Preview</button></div>
      </div>
      <details class="share-section" open>
        <summary><span>Link &amp; access</span><small>Set the public address and who can open it.</small></summary>
        <div class="share-section-body"></div>
      </details>
      <details class="share-section">
        <summary><span>Manage</span><small>Versions, responses and guest wishes.</small></summary>
        <div class="share-section-body share-manage"></div>
      </details>`;
    const accessBody = shell.querySelector('.share-section-body');
    [slug, access, password, save, state].filter(Boolean).forEach((node) => accessBody.append(node));
    const manage = shell.querySelector('.share-manage');
    [history, unpublish, rsvp, wishes].filter(Boolean).forEach((node) => manage.append(node));
    // The hero already states draft/published; the legacy #publishInfo line is
    // kept in the DOM (app.js still updates it) but not shown, so it cannot
    // contradict the state with a stale local-snapshot message.
    // Collaboration and other modules append their own cards to this pane.
    // Keep them instead of discarding their DOM (and their event bindings).
    const moved = new Set([slug, access, password, save, state, info, history, unpublish, rsvp, wishes].filter(Boolean));
    const extras = [...publish.children].filter((node) => !moved.has(node)
      && node.id !== 'publishingSettings'
      && !node.classList.contains('studio-inspector-heading')
      && !(node.tagName === 'H2' && /^publishing$/i.test(node.textContent.trim())));
    extras.forEach((node) => shell.append(node));
    // app.js still writes #publishInfo on every publish/refresh. It must stay in
    // the document (hidden) or refreshPublish() throws inside apply() and every
    // subsequent edit — font size included — is rolled back.
    if (info) {
      info.hidden = true;
      shell.append(info);
    }
    publish.replaceChildren(shell);
    const url = shell.querySelector('[data-share-url]');
    const copy = shell.querySelector('[data-share-copy]');
    const copyText = async () => {
      if (!url.value) return;
      try {
        await navigator.clipboard.writeText(url.value);
      } catch {
        url.select();
        document.execCommand?.('copy');
      }
      copy.textContent = 'Copied';
      setTimeout(() => { copy.textContent = 'Copy'; }, 1400);
    };
    copy.addEventListener('click', copyText);
    shell.querySelector('[data-share-publish]').addEventListener('click', () => document.querySelector('#publishBtn')?.click());
    shell.querySelector('[data-share-preview]').addEventListener('click', () => document.querySelector('#previewBtn')?.click());
    const sync = () => {
      const text = (info.textContent || '').replace(/\s+/g, ' ').trim();
      let serverPublished = null;
      try {
        const inviteId = window.EInviteContext?.getInvitationId?.({ allowRemembered: false });
        const cached = inviteId ? window.inviteStore?.read(`sovan-server-invite:${inviteId}`) : null;
        if (cached && typeof cached.published === 'boolean') serverPublished = cached.published;
      } catch { serverPublished = null; }
      const published = serverPublished ?? !/not published|no snapshot|draft|unpublished|offline/i.test(text);
      const slugValue = (publish.querySelector('#publicSlug')?.value || '').trim();
      let link = '';
      if (info.dataset.publicUrl) {
        try { link = new URL(info.dataset.publicUrl, location.origin).href; } catch { link = ''; }
      }
      if (!link && slugValue) link = `${location.origin}/i/${encodeURIComponent(slugValue)}`;
      if (url.value !== link) url.value = link;
      copy.disabled = !link;
      copy.setAttribute('aria-disabled', String(!link));
      shell.dataset.published = String(published);
      shell.querySelector('[data-share-state]').textContent = published ? 'Published' : 'Draft';
      shell.querySelector('[data-share-hint]').textContent = published ? 'Anyone with the link can open the invitation.' : 'Publish to create a shareable link.';
      shell.querySelector('[data-share-publish]').textContent = published ? 'Update snapshot' : 'Publish';
    };
    sync();
    new MutationObserver(sync).observe(info, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['data-public-url'] });
    publish.addEventListener('input', sync);
    publish.addEventListener('change', sync);
  }

  function schedule() {
    if (queued) return;
    queued = requestAnimationFrame(() => {
      queued = 0;
      classify();
      syncSelection();
      installShare();
    });
  }

  function install() {
    if (!pane()) return;
    classify();
    installShare();
    const observer = new MutationObserver((records) => {
      if (busy) return;
      if (records.every((record) => record.target.closest?.('.ix-groups') && record.type === 'attributes')) return;
      schedule();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    const hostProps = props();
    if (hostProps) {
      new MutationObserver(syncSelection).observe(hostProps, { attributes: true, attributeFilter: ['hidden'] });
    }
    document.addEventListener('einvite:selection-changed', () => {
      requestAnimationFrame(() => {
        syncSelection();
        if (!hasSelection()) openGroup('page', false);
        else {
          const active = pane()?.querySelector('.ix-group[open]');
          if (!active || active.dataset.ixGroup === 'page') {
            const textObject = document.querySelector('#textContentLabel:not([hidden])');
            openGroup(textObject ? 'text' : 'position', false);
          }
        }
      });
    });
    const selectedText = document.querySelector('#textContentLabel:not([hidden])');
    if (hasSelection()) openGroup(selectedText ? 'text' : 'position', false);
    else openGroup('page', false);
    syncSelection();
    syncTools();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(install, 90), { once: true });
  else setTimeout(install, 90);
})();;/**
 * ui/app-shell.js — V55 shell: rail collapse, rail drawer, appearance.
 *
 * Collapse persists in localStorage['einvite-rail-collapsed']; the drawer
 * (≤768px) closes on Escape, outside click and hashchange; the theme toggle
 * uses core/theme.js's `einvite-theme-mode`, so pages without modern-ui.js
 * still work. Toggles expose aria-expanded; nothing traps focus.
 */
(function () {
  'use strict';
  if (window.EInviteShell && window.EInviteShell.version >= 55) return;

  var body = document.body;
  var html = document.documentElement;
  var RAIL_KEY = 'einvite-rail-collapsed';
  var THEME_KEY = 'einvite-theme-mode';

  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }

  /* --- 1. Rail collapse -------------------------------------------------- */
  function applyRailCollapsed(collapsed) {
    body.classList.toggle('rail-collapsed', !!collapsed);
    document.querySelectorAll('[data-rail-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!collapsed));
      var label = collapsed ? 'Expand navigation' : 'Collapse navigation';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      /* Converted pages rotate an SVG; the editor still uses the text glyph. */
      var glyph = btn.querySelector('[data-rail-glyph]');
      if (glyph && !glyph.firstElementChild) glyph.textContent = collapsed ? '»' : '«';
    });
  }
  /* QA 2026-10-30 (UI-4): the drawer had no scrim and its off-screen links
     stayed focusable. Add a scrim, mark the closed rail inert on mobile, and
     return focus to the toggle when the drawer closes under the keyboard. */
  function ensureScrim() {
    var scrim = document.querySelector('.app-drawer-scrim');
    if (!scrim) {
      scrim = document.createElement('div');
      scrim.className = 'app-drawer-scrim';
      scrim.setAttribute('aria-hidden', 'true');
      document.body.append(scrim);
    }
    return scrim;
  }
  function applyRailOpen(open) {
    var wasOpen = body.classList.contains('rail-open');
    var rail = document.querySelector('.app-rail');
    body.classList.toggle('rail-open', !!open);
    ensureScrim();
    if (rail) rail.inert = window.matchMedia('(max-width: 768px)').matches && !open;
    document.querySelectorAll('[data-drawer-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!!open));
    });
    if (!open && wasOpen && rail && rail.contains(document.activeElement)) {
      var toggle = document.querySelector('[data-drawer-toggle]');
      if (toggle) toggle.focus();
    }
  }

  /* --- 2. Current page --------------------------------------------------- */
  function markCurrentPage() {
    var here = (location.pathname.split('/').pop() || 'dashboard.html').toLowerCase();
    document.querySelectorAll('.app-rail a[href]').forEach(function (link) {
      var target = link.getAttribute('href').split('#')[0].split('?')[0].toLowerCase();
      if (target && target === here) link.setAttribute('aria-current', 'page');
    });
  }

  /*
   * Pages that show a signed-out flow (dashboard) hide their rail until the
   * signed-in view is revealed, so the login card gets the full canvas. The
   * same flag flips the topbar down to Skeleton B (brand + language + theme).
   */
  function syncAutoRail() {
    var autoRail = document.querySelector('.app-rail[data-rail-auto]');
    var signedIn = document.getElementById('dashboardView');
    var signedInVisible = !signedIn || !signedIn.hidden;
    if (autoRail) autoRail.hidden = !signedInVisible;
    if (signedIn) body.classList.toggle('auth-mode', !signedInVisible);
  }

  function watchAutoRail() {
    var signedIn = document.getElementById('dashboardView');
    if (!signedIn || typeof MutationObserver !== 'function') return;
    new MutationObserver(syncAutoRail).observe(signedIn, { attributes: true, attributeFilter: ['hidden'] });
  }

  /* --- 3. Appearance ----------------------------------------------------- */
  function resolvedTheme() { return html.dataset.theme === 'dark' ? 'dark' : 'light'; }
  function applyTheme(next) {
    html.dataset.theme = next;
    html.dataset.themeMode = next;
    html.style.colorScheme = next;
    write(THEME_KEY, next);
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(next === 'dark'));
      btn.setAttribute('title', next === 'dark' ? 'Switch to light appearance' : 'Switch to dark appearance');
      /* Both symbols live in the button; the theme attribute on <html> shows the
         right one, so nothing is assigned here. */
    });
  }

  /* --- Wiring ------------------------------------------------------------ */
  document.addEventListener('click', function (event) {
    var railToggle = event.target.closest('[data-rail-toggle]');
    if (railToggle) {
      var collapsed = !body.classList.contains('rail-collapsed');
      applyRailCollapsed(collapsed);
      write(RAIL_KEY, collapsed ? '1' : '0');
      return;
    }
    var drawerToggle = event.target.closest('[data-drawer-toggle]');
    if (drawerToggle) { applyRailOpen(!body.classList.contains('rail-open')); return; }
    var themeToggle = event.target.closest('[data-theme-toggle]');
    if (themeToggle) { applyTheme(resolvedTheme() === 'dark' ? 'light' : 'dark'); return; }
    /* Outside click closes the mobile drawer but never the desktop rail. */
    if (body.classList.contains('rail-open') && !event.target.closest('.app-rail')) applyRailOpen(false);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && body.classList.contains('rail-open')) applyRailOpen(false);
  });
  window.addEventListener('hashchange', function () { applyRailOpen(false); });
  window.addEventListener('resize', function () { if (innerWidth > 768) applyRailOpen(false); });

  function init() {
    markCurrentPage();
    applyRailCollapsed(read(RAIL_KEY) === '1');
    applyRailOpen(false);
    syncAutoRail();
    watchAutoRail();
    applyTheme(read(THEME_KEY) === 'dark' ? 'dark' : 'light');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();

  window.EInviteShell = Object.freeze({
    version: 55,
    collapseRail: applyRailCollapsed,
    openRail: applyRailOpen,
    syncAutoRail: syncAutoRail,
    setTheme: applyTheme
  });
})();;(()=>{'use strict';if(window.EInviteResponsiveLayout?.version>=27)return;const M=820,C=1180,q=(s,r=document)=>r.querySelector(s),b=document.body,m=q('body.studio-experience>main'),l=q('aside.left'),r=q('aside.right'),h=q('.studio-pane-host',l),a=q('.studio-tool-rail',l),s=q('.stage-wrap'),w=q('#stage');if(!b?.classList.contains('studio-experience')||!m||!l||!r||!h||!a||!s)return;w?.setAttribute('tabindex','-1');let y=0,i=0,p=0;const mode=()=>innerWidth<=M?'mobile':innerWidth<=C?'compact':'desktop',state=(n,o)=>{n?.setAttribute('aria-hidden',`${!o}`);if(n&&'inert'in n)n.inert=!o;n?.classList.toggle('einvite-drawer-closed',!o)},focus=()=>{w?.focus({preventScroll:true});b.dataset.keyboardOwner='canvas'};function sync(){if(y)return;y=1;const x=mode(),d=b.dataset.editorDrawer;b.classList.toggle('einvite-layout-mobile',x==='mobile');b.classList.toggle('einvite-layout-compact',x==='compact');b.classList.toggle('einvite-layout-desktop',x==='desktop');b.dataset.editorLayout=x;if(x==='desktop'){b.dataset.editorDrawer='desktop';b.classList.remove('mobile-creation-open','mobile-inspector-open','inspector-open','mobile-pane-collapsed');state(l,1);state(h,1);state(r,1);a.inert=false;a.removeAttribute('aria-hidden')}else{if(!i||!['canvas','creation','inspector'].includes(d))b.dataset.editorDrawer='canvas';const v=b.dataset.editorDrawer,c=v==='creation',n=v==='inspector';b.classList.toggle('mobile-creation-open',c);b.classList.toggle('mobile-inspector-open',n);b.classList.toggle('inspector-open',n);b.classList.toggle('mobile-pane-collapsed',!c);if(x==='mobile'){state(l,c);a.inert=!c}else{state(l,1);a.inert=false}a.removeAttribute('aria-hidden');state(h,c);state(r,n)}i=1;requestAnimationFrame(()=>dispatchEvent(new CustomEvent('einvite:workspace-resized',{detail:{layout:mode(),drawer:b.dataset.editorDrawer}})));y=0}function set(d,o={}){b.dataset.editorDrawer=d||'canvas';sync();if(o.focus){const z=d==='creation'?h.querySelector('.studio-pane.active input,.studio-pane.active button,.studio-pane.active select,.studio-pane.active textarea'):d==='inspector'?r.querySelector('.studio-inspector-pane.active input,.studio-inspector-pane.active button,.studio-inspector-tab'):w;z?.focus({preventScroll:true})}}const api={version:27,MOBILE_MAX:M,COMPACT_MAX:C,mode,sync,setDrawer:set,openCreation:o=>set('creation',o),closeCreation:o=>set('canvas',o),openInspector:o=>set('inspector',o),closeInspector:o=>set('canvas',o),focusCanvas(){set('canvas');focus()}};document.addEventListener('click',e=>{if(mode()==='desktop')return;if(e.target.closest('.studio-tool-rail [data-studio-tab]'))b.dataset.editorDrawer='creation';else if(e.target.closest('[data-inspector-tab]'))b.dataset.editorDrawer='inspector';else{const z=e.target.closest('[data-mobile-mode]');if(!z)return;b.dataset.editorDrawer=z.dataset.mobileMode==='tools'?'creation':z.dataset.mobileMode==='quick'?'inspector':'canvas'}queueMicrotask(sync)},true);new MutationObserver(()=>{if(!y&&mode()!=='desktop'){if(b.classList.contains('mobile-inspector-open')||b.classList.contains('inspector-open'))b.dataset.editorDrawer='inspector';else if(b.classList.contains('mobile-creation-open')&&!b.classList.contains('mobile-pane-collapsed'))b.dataset.editorDrawer='creation';sync()}}).observe(b,{attributes:true,attributeFilter:['class']});const typing=n=>!!n&&(n.matches?.('input,textarea,select,[contenteditable="true"]')||n.isContentEditable),control=n=>typing(n)||!!n?.matches?.('button,a[href],[role="button"],[role="menuitem"],[role="tab"]');document.addEventListener('pointerdown',e=>{if(!e.target.closest?.('#stage .object,#stage,#canvasViewport,.stage-wrap')||control(e.target)||e.target.closest?.('.content[contenteditable="true"],.studio-canvas-toolbar,#v20TypographyToolbar')){p=0;return}p=1;b.dataset.keyboardOwner='canvas';queueMicrotask(focus)},true);document.addEventListener('pointerup',()=>{if(p){p=0;b.dataset.keyboardOwner='canvas';focus()}},true);document.addEventListener('pointercancel',()=>p=0,true);for(const n of['einvite:marquee-complete','einvite:resize-complete','einvite:rotation-complete','einvite:drag-complete','einvite:professional-command-committed'])document.addEventListener(n,e=>{if(e.detail?.source!=='keyboard'){b.dataset.keyboardOwner='canvas';focus()}});document.addEventListener('focusin',e=>{const t=e.target;b.dataset.keyboardOwner=t===w||t?.id==='canvasViewport'?'canvas':control(t)||t?.closest?.('aside.left,aside.right,.studio-topbar,.mobile-editor-v14-bar,.studio-canvas-toolbar,#v20TypographyToolbar')?'control':t?.closest?.('#stage,#canvasViewport,.stage-wrap')?'canvas':b.dataset.keyboardOwner},true);const back=new WeakMap,show=HTMLDialogElement.prototype.showModal;HTMLDialogElement.prototype.showModal=function(...x){const a=document.activeElement;back.set(this,{a,c:b.dataset.keyboardOwner==='canvas'&&(a===w||a?.id==='canvasViewport')});return show.apply(this,x)};document.addEventListener('close',e=>{if(!(e.target instanceof HTMLDialogElement))return;const x=back.get(e.target);back.delete(e.target);requestAnimationFrame(()=>requestAnimationFrame(()=>x?.c?(focus(),b.dataset.keyboardOwner='canvas'):x?.a?.isConnected&&x.a.focus?.({preventScroll:true})))},true);addEventListener('resize',sync,{passive:true});document.addEventListener('einvite:editor-ready',sync);requestAnimationFrame(sync);window.EInviteResponsiveLayout=Object.freeze(api)})();;// first-selection-prewarm — pays the one-time cost of the first selection-chrome
// paint at boot, where nothing is being measured, instead of on the user's first
// selection gesture.
//
// Why: on a fresh browser profile, the first selection in the editor shows three
// composited chrome elements (selection card / toolbar / box) for the first time.
// That first present pays GPU pipeline + lazy-compile costs that can stall a
// single frame by ~100 ms on a cold browser (measured: canvas-motion perf gate
// snap gesture, run 1 of 3 only). Warming the same path at editor-ready moves
// the cost off the first interaction; subsequent selections are unchanged.
//
// Safety:
// - Runs once per page load, only after the editor reports ready and the stage
//   has a laid-out object.
// - Skipped entirely if the user interacts first (their selection pays it).
// - Selection is cleared afterwards; no document/undo state is touched.
// - LT-1.9: the typography strip is hidden during the warm hold. It is in
//   normal flow above the canvas, so letting it paint for 140ms pushed the
//   toolbar and canvas down twice (CLS 0.38). The selection card and bounds
//   still warm; only the strip's first layout is left to the first real
//   selection. Inline display (not a class) because typography-system.css is
//   unlayered and outranks every layered rule.
(function () {
  'use strict';
  if (window.EInviteFirstSelectionPrewarm) return;

  var api = { version: '1', state: 'idle', at: 0, done: 0, ok: false };
  window.EInviteFirstSelectionPrewarm = api;

  var attempts = 0;
  var userInteracted = false;
  var HOLD_MS = 140;
  var POLL_MS = 80;
  var MAX_ATTEMPTS = 240;

  document.addEventListener('pointerdown', function () {
    userInteracted = true;
    restoreStrip();
  }, true);
  document.addEventListener('keydown', function () {
    if (api.state === 'done') restoreStrip();
  }, true);

  function candidate() {
    var el = document.querySelector('#stage .object[data-id]');
    if (!el || !el.getBoundingClientRect) return null;
    var r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return null;
    var bridge = window.EInviteEditorBridge;
    if (!bridge || typeof bridge.select !== 'function') return null;
    return { id: el.dataset.id, bridge: bridge };
  }

  var strip = null;

  function hideStrip() {
    strip = document.getElementById('v20TypographyToolbar');
    if (strip) strip.style.display = 'none';
  }

  function restoreStrip() {
    if (strip && strip.style) strip.style.removeProperty('display');
    strip = null;
  }

  function finish(ok) {
    // Typography queues one more refresh from the synthetic selection after
    // the bridge has cleared it; restoring now let that stale pass paint the
    // strip for ~40ms with nothing selected (and shift the canvas). Give the
    // queue time to drain while the strip is still display:none, then hand it
    // back. A real pointer/key selection restores it immediately below.
    if (ok) setTimeout(restoreStrip, 700); else restoreStrip();
    api.state = 'done';
    api.ok = !!ok;
    api.done = Math.round(performance.now());
    window.__prewarmAt = api.at;
    window.__prewarmDone = api.done;
  }

  function warm() {
    if (api.state !== 'idle') return;
    if (userInteracted || document.hidden) return finish(false);
    if (++attempts > MAX_ATTEMPTS) return finish(false);
    var c = null;
    try { c = candidate(); } catch (e) { c = null; }
    if (!c) return void setTimeout(warm, POLL_MS);
    api.state = 'active';
    api.at = Math.round(performance.now());
    hideStrip();
    try { c.bridge.select([c.id]); } catch (e) { return finish(false); }
    setTimeout(function () {
      try { c.bridge.select([]); } catch (e) {}
      finish(true);
    }, HOLD_MS);
  }

  function start() {
    if (document.documentElement.dataset.editorReady === 'true') {
      setTimeout(warm, 120);
      return;
    }
    var iv = setInterval(function () {
      if (document.documentElement.dataset.editorReady === 'true') {
        clearInterval(iv);
        setTimeout(warm, 120);
      }
    }, 60);
    setTimeout(function () { clearInterval(iv); }, 20000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();