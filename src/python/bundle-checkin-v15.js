;/*! core/i18n.js — EInvite global i18n resolver (FOIL-safe, synchronous)
 * v0.68.3 (ROADMAP-v0.54-to-v1.0 §4.1)
 *
 * Responsibilities:
 *   - Source of truth for UI language = <html lang>.
 *   - Persisted to localStorage key `einvite-lang` ('en'|'km').
 *   - First-visit default: navigator.language starts with `km` -> Khmer, else English.
 *   - Exposes EInviteI18n.get()/set()/t()/langText()/subscribe().
 *   - Backwards-compatible alias EInviteI18N.getLocale() (the 23 page modules already
 *     call window.EInviteI18N?.getLocale?.(); this makes them resolve through the
 *     single resolver instead of falling back to <html lang>).
 *   - Dispatches a synchronous `einvite:lang-changed` CustomEvent on <html> so any
 *     bilingual surface can re-render, and notifies subscribers.
 *   - Injects a bilingual language switch into every <header> (shared header + the
 *     editor app-bar). The switch itself is the one place both languages coexist.
 *   - Walks [data-en][data-km] form fields and sets placeholder/aria-label to the
 *     active language (text labels are handled by the .i18n-en/.i18n-km CSS hiding
 *     convention, no JS needed there).
 *
 * This file is designed to be the FIRST script in every page bundle (it is listed
 * first in earlyScripts and as the first entry of each page's `scripts`). It runs
 * synchronously in <head> (bundles are loaded blocking in <head>) so <html lang> is
 * correct before first paint -> no FOIL flash of both languages. Every public
 * method is guarded so a missing DOM / storage / navigator never throws.
 */
(function (global) {
  "use strict";
  // Guard against double-injection (earlyScripts + per-page scripts, or a future
  // head <script src>).
  if (global.EInviteI18n && global.EInviteI18N && global.EInviteI18N.version) return;
  if (global.EInviteI18n && global.EInviteI18n.version >= 1) return;

  var doc = global.document;
  var STORAGE_KEY = "einvite-lang";

  // --- Language detection ----------------------------------------------------
  function navigatorLang() {
    try {
      var nav = global.navigator && global.navigator.language;
      if (!nav) {
        var langs = global.navigator && global.navigator.languages;
        if (langs && langs.length) nav = langs[0];
      }
      if (String(nav || "").toLowerCase().indexOf("km") === 0) return "km";
    } catch (e) { /* noop */ }
    return "en";
  }
  function htmlLang() {
    try {
      var l = (doc.documentElement && doc.documentElement.lang) || "";
      return String(l).toLowerCase().indexOf("km") === 0 ? "km" : "en";
    } catch (e) { return navigatorLang(); }
  }
  function persistedLang() {
    try {
      if (!global.localStorage) return null;
      var v = global.localStorage.getItem(STORAGE_KEY);
      if (v === "km" || v === "en") return v;
    } catch (e) { /* storage disabled (private mode etc.) */ }
    return null;
  }
  function applyHtmlLang(lang) {
    try {
      if (doc.documentElement && doc.documentElement.lang !== lang) {
        doc.documentElement.lang = lang;
      }
    } catch (e) { /* noop */ }
  }
  function get() {
    // Persisted user choice wins; otherwise the live <html lang> wins (set by the
    // public page observer, the head inline, or the previous switch click); finally
    // the navigator default.
    return persistedLang() || htmlLang();
  }

  // --- Persistence + notification -------------------------------------------
  var subscribers = [];
  function persist(lang) {
    try { global.localStorage && global.localStorage.setItem(STORAGE_KEY, lang); }
    catch (e) { /* storage disabled */ }
  }
  function emit(lang) {
    applyHtmlLang(lang);
    persist(lang);
    try {
      var ev = new global.Event("einvite:lang-changed", { bubbles: true });
      ev.lang = lang;
      doc.dispatchEvent(ev);
    } catch (e) { /* older DOM; fall back to a manual property change */ }
    for (var i = 0; i < subscribers.length; i++) {
      try { subscribers[i](lang, get); } catch (e) { /* keep other subscribers alive */ }
    }
    // Re-sync every injected language switch after a real language change.
    // The `einvite:lang-changed` event re-runs boot()->injectSwitches(), but
    // injectSwitches() skips any <header> that already holds a switch, so
    // without this refresh the buttons' aria-pressed / active class stay frozen
    // at the pre-click value and read as inverted on the now-inactive button.
    // syncSwitch(null, lang) covers all switches across all <header> elements.
    syncSwitch(null, lang);
  }

  // --- Form-field helper (placeholder/aria-label for [data-en][data-km]) ----
  // Text labels (label/span/button/h2/th) are NOT touched here: the
  // `.i18n-en`/`.i18n-km` CSS convention hides the inactive span, so no JS is
  // needed for them and they re-render live on toggle via CSS.
  function applyFormFields(root) {
    var scope = root || doc;
    if (!scope.querySelectorAll) return;
    var lang = get();
    var fields = scope.querySelectorAll("[data-en][data-km]");
    for (var i = 0; i < fields.length; i++) {
      var el = fields[i];
      var tag = el.tagName;
      if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") continue;
      var en = el.getAttribute("data-en") || "";
      var km = el.getAttribute("data-km") || en;
      var val = lang === "km" ? km : en;
      if (tag === "INPUT" || tag === "TEXTAREA") el.placeholder = val;
      if (el.getAttribute("aria-label") !== null) el.setAttribute("aria-label", val);
      el.setAttribute("lang", lang === "km" ? "km" : "en");
    }
  }

  // --- Language switch injection (into every <header>) ----------------------
  function escHTML(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function makeSwitch() {
    var wrap = doc.createElement("div");
    wrap.className = "language-switch";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "Select interface language");
    var enBtn = doc.createElement("button");
    enBtn.type = "button"; enBtn.id = "lang-en"; enBtn.setAttribute("data-lang", "en");
    enBtn.setAttribute("aria-label", "Switch to English"); enBtn.textContent = "English";
    var kmBtn = doc.createElement("button");
    kmBtn.type = "button"; kmBtn.id = "lang-km"; kmBtn.setAttribute("data-lang", "km");
    kmBtn.setAttribute("aria-label", "ប្ដូះបើកភាសាខ្មែរ"); kmBtn.textContent = "ខ្មែរ";
    wrap.appendChild(enBtn); wrap.appendChild(kmBtn);
    return wrap;
  }
  function syncSwitch(wrap, lang) {
    var btns = wrap ? wrap.querySelectorAll("[data-lang]") : doc.querySelectorAll(".language-switch [data-lang]");
    for (var i = 0; i < btns.length; i++) {
      var b = btns[i];
      var on = b.getAttribute("data-lang") === lang;
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.toggle("active", on);
    }
  }
  function injectSwitches() {
    if (!doc.querySelectorAll) return;
    var headers = doc.querySelectorAll("header");
    var lang = get();
    for (var i = 0; i < headers.length; i++) {
      var h = headers[i];
      if (h.querySelector(".language-switch")) continue;
      var sw = makeSwitch();
      sw.addEventListener("click", function (e) {
        var b = e.target.closest("[data-lang]");
        if (!b) return;
        EInviteI18n.set(b.getAttribute("data-lang"));
      });
      h.appendChild(sw);
      syncSwitch(sw, lang);
    }
    applyFormFields();
  }
  function boot() {
    try { injectSwitches(); } catch (e) { /* keep going */ }
  }

  // --- Public resolver -------------------------------------------------------
  var EInviteI18n = {
    version: "1.0",
    STORAGE_KEY: STORAGE_KEY,
    get: get,
    getLocale: get, // backward-compat: EInviteI18N?.getLocale()
    set: function (lang) {
      lang = lang === "km" ? "km" : lang === "en" ? "en" : navigatorLang();
      // If the language isn't actually changing, just (re)sync the DOM attribute
      // and form fields so a forced re-render is idempotent.
      if (get() === lang) { applyHtmlLang(lang); applyFormFields(); return lang; }
      emit(lang);
      applyFormFields();
      return lang;
    },
    // t(key, STRINGS, params?) — STRINGS is a {en:{...},km:{...}} (per-locale) table.
    // Optional {token:value} params are substituted as {token} -> value.
    t: function (key, strings, params) {
      var lang = get();
      var dict = (strings && (strings[lang] || strings.en)) || {};
      var s = dict[key];
      if ((s === undefined || s === null) && strings && strings.en) s = strings.en[key];
      if (s === undefined || s === null) s = key;
      // Function-valued entries (pageLabel(n), pinLabel(n)) are invoked with the
      // caller args; their own template fills the positional values.
      if (typeof s === "function") { try { return s(params); } catch (e) { return key; } }
      s = String(s);
      if (params && typeof params === "object" && !Array.isArray(params)) {
        var keys = Object.keys(params);
        for (var i = 0; i < keys.length; i++) {
          s = s.split("{" + keys[i] + "}").join(String(params[keys[i]] == null ? "" : params[keys[i]]));
        }
      }
      return s;
    },
    // Backward-compatible langText('en','km',mode) inline shape.
    // 'en'/'km' force a language; anything else (both/guest/host/undefined)
    // renders both spans — the live <html lang> / [data-language] CSS hides the
    // inactive one, so the switch updates the page instantly without re-render.
    langText: function (en, km, mode) {
      var kmv = km != null ? km : en;
      if (mode === "en") return '<span class="i18n i18n-en">' + escHTML(en) + '</span>';
      if (mode === "km") return '<span class="i18n i18n-km khmer-text" lang="km">' + escHTML(kmv) + '</span>';
      return '<span class="i18n i18n-en">' + escHTML(en) + '</span>' +
             '<span class="i18n i18n-km khmer-text" lang="km">' + escHTML(kmv) + '</span>';
    },
    subscribe: function (fn) {
      if (typeof fn === "function" && subscribers.indexOf(fn) === -1) subscribers.push(fn);
      return function () {
        var idx = subscribers.indexOf(fn);
        if (idx > -1) subscribers.splice(idx, 1);
      };
    },
  };

  global.EInviteI18n = EInviteI18n;
  // Alias the uppercase name that 15 pre-existing modules already call via
  // `window.EInviteI18N?.getLocale?.()` so they resolve through this resolver.
  global.EInviteI18N = {
    version: "1.0",
    getLocale: get,
    set: EInviteI18n.set,
    t: EInviteI18n.t,
  };

  // Listen for external language changes (e.g. the public page's per-invitation
  // observer writing <html lang> from root[data-language]) so the switch and
  // form fields stay in sync.
  try {
    doc.addEventListener("einvite:lang-changed", boot);
  } catch (e) { /* noop */ }

  // --- Synchronous init (runs in <head> before first paint) ------------------
  var initLang = persistedLang() || navigatorLang();
  applyHtmlLang(initLang);
  applyFormFields();
  if (doc && doc.addEventListener) {
    doc.addEventListener("DOMContentLoaded", boot);
    // If the bundle is injected after parse, DOMContentLoaded may have already
    // fired; boot immediately as a safety net.
    if (doc.readyState === "interactive" || doc.readyState === "complete") {
      boot();
    }
  }
})(typeof window !== "undefined" ? window : this);;(()=>{
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
})();;(()=>{
 'use strict';
 const LAST_KEY='sovan-active-invite';
 const routeMatch=location.pathname.match(/\/invitations\/([^/]+)\/(editor|guests|responses|analytics|materials|checkin)\/?$/i);
 const queryId=new URLSearchParams(location.search).get('invitation');
 const routeId=routeMatch?decodeURIComponent(routeMatch[1]):'';
 const explicitId=routeId||queryId||'';
 const section=routeMatch?.[2]?.toLowerCase()||'';
 const safe=id=>String(id||'').trim();
 function getInvitationId(options={}){const direct=safe(explicitId);if(direct)return direct;if(options.allowRemembered===false)return '';return safe(localStorage.getItem(LAST_KEY))}
 function remember(id){id=safe(id);if(id)localStorage.setItem(LAST_KEY,id);return id}
 function route(id,target='editor'){
   id=safe(id);target=String(target||'editor').toLowerCase();
   if(!id)return target==='materials'?'materials.html':'dashboard.html';
   const allowed=new Set(['editor','guests','responses','analytics','materials','checkin']);if(!allowed.has(target))target='editor';
   if(window.EInviteBackend?.state?.status==='offline')return window.EInviteBackend.staticUrl(id,target);
   return `/invitations/${encodeURIComponent(id)}/${target}`;
 }
 async function navigate(id,target='editor'){remember(id);if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;location.href=route(id,target)}
 if(explicitId)remember(explicitId);
 async function rewriteInvitationLinks(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;const id=getInvitationId({allowRemembered:false});if(!id)return;const map={'index.html':'editor','guests.html':'guests','responses.html':'responses','analytics.html':'analytics','materials.html':'materials','checkin.html':'checkin'};document.querySelectorAll('a[href]').forEach(anchor=>{const raw=anchor.getAttribute('href')||'';const base=raw.split('?')[0].split('#')[0].replace(/^\.\//,'');const target=map[base];if(target)anchor.setAttribute('href',route(id,target))})}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',rewriteInvitationLinks,{once:true});else rewriteInvitationLinks();
 window.EInviteContext={getInvitationId,remember,route,navigate,section,explicitId,rewriteInvitationLinks};
})();;(()=>{'use strict';
const $=s=>document.querySelector(s),inviteId=window.EInviteContext?.getInvitationId({allowRemembered:false})||window.EInviteContext?.getInvitationId()||'',queueKey=`einvite-checkin-queue:${inviteId}`;let guests=[],invitation=null,stream=null,scanTimer=null;
const api=async(path,options={})=>{const r=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...(options.headers||{})}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const _isKm=()=>(window.EInviteI18n&&window.EInviteI18n.get?window.EInviteI18n.get():(document.documentElement.lang||'').toLowerCase()).startsWith('km');
const _txt=(en,km)=>_isKm()?(km!=null?km:en):en;
const _html=(en,km)=>{const isKm=_isKm();const v=isKm?(km!=null?km:en):en;return`<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km">${esc(km!=null?km:en)}</span>`};
const queue=()=>{try{return JSON.parse(localStorage.getItem(queueKey)||'[]')}catch{return[]}},saveQueue=q=>localStorage.setItem(queueKey,JSON.stringify(q));
function setNetwork(){const online=navigator.onLine;$('#networkState').textContent=online?_txt('Online','Online'):_txt('Offline','Offline');$('#networkState').classList.toggle('offline',!online);renderQueue()}
function renderQueue(){const q=queue(),el=$('#pendingQueue');el.hidden=!q.length;const en=`${q.length} ${q.length===1?'check-in change':'check-in changes'} waiting to sync when the connection returns.`;el.innerHTML=q.length?`<span class="i18n i18n-en">${en}</span><span class="i18n i18n-km khmer-text" lang="km">${en}</span>`:''}
function render(){const q=$('#guestSearch').value.trim().toLowerCase(),filtered=guests.filter(g=>`${g.name} ${g.phone||''} ${g.group_name||''} ${g.table_name||''}`.toLowerCase().includes(q)),checked=guests.filter(g=>g.checked_in).length;$('#checkinSummary').innerHTML=`${checked} of ${guests.length} <span class="i18n i18n-en">guests checked in</span><span class="i18n i18n-km khmer-text" lang="km">guests checked in</span>`;$('#checkinStats').innerHTML=`<span class="checkin-stat"><strong>${checked}</strong> <span class="i18n i18n-en">in</span><span class="i18n i18n-km khmer-text" lang="km">in</span></span><span class="checkin-stat"><strong>${guests.length-checked}</strong> <span class="i18n i18n-en">remaining</span><span class="i18n i18n-km khmer-text" lang="km">remaining</span></span>`;$('#checkinList').innerHTML=filtered.map(g=>`<article class="checkin-person ${g.checked_in?'checked':''}" data-guest-id="${esc(g.id)}"><div><strong>${esc(g.name)}</strong><small>${[g.group_name,g.table_name&&`${_txt('Table','Table')} ${g.table_name}`,g.seat_label&&`${_txt('Seat','Seat')} ${g.seat_label}`,g.phone].filter(Boolean).map(esc).join(' · ')}</small></div><button data-check-id="${esc(g.id)}" class="${g.checked_in?'':'primary'}">${g.checked_in?_txt('Undo check-in','Undo check-in'):_txt('Check in','Check in')}</button></article>`).join('')||'<p class="empty-state"><span class="i18n i18n-en">No matching guests.</span><span class="i18n i18n-km khmer-text" lang="km">No matching guests.</span></p>';document.querySelectorAll('[data-check-id]').forEach(b=>b.onclick=()=>toggle(b.dataset.checkId))}
async function load(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){window.EInviteBackend.message($('#checkinList'),'<span class="i18n i18n-en">Guest check-in synchronization requires the full application server.</span><span class="i18n i18n-km khmer-text" lang="km">Guest check-in synchronization requires the full application server.</span>');$('#scanQrBtn').disabled=true;return}try{invitation=await api(`/api/invitations/${encodeURIComponent(inviteId)}`);guests=await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);$('#eventName').innerHTML='<span class="i18n i18n-en">'+(invitation.document?.fields?.names||'Guest check-in')+'</span><span class="i18n i18n-km khmer-text" lang="km">'+(invitation.document?.fields?.names||'Guest check-in')+'</span>';$('#backToGuests').href=window.EInviteContext.route(inviteId,'guests');render();await flushQueue()}catch(e){$('#checkinList').innerHTML=`<p><span class="i18n i18n-en">Could not load this guest list: </span><span class="i18n i18n-km khmer-text" lang="km">Could not load this guest list: </span>${esc(e.message)}</p>`}}
async function toggle(id,explicit){const g=guests.find(x=>x.id===id);if(!g)return;const checked=explicit??!g.checked_in;g.checked_in=checked;g.checked_in_at=checked?Date.now():null;render();if(!navigator.onLine){const q=queue().filter(x=>x.guestId!==id);q.push({guestId:id,checkedIn:checked,createdAt:Date.now()});saveQueue(q);renderQueue();return}try{const result=await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(id)}/check-in`,{method:'PUT',body:JSON.stringify({checkedIn:checked})});if(result.alreadyCheckedIn){const notice=$('#checkinNotice');notice.textContent=`${g.name} ${_txt('was already checked in.','was already checked in.')}`;setTimeout(()=>{if(notice.textContent.includes(g.name))notice.textContent=''},3500)}}catch(e){const q=queue().filter(x=>x.guestId!==id);q.push({guestId:id,checkedIn:checked,createdAt:Date.now()});saveQueue(q);renderQueue()}}
async function flushQueue(){if(!navigator.onLine)return;let q=queue(),remaining=[];for(const item of q){try{await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(item.guestId)}/check-in`,{method:'PUT',body:JSON.stringify({checkedIn:item.checkedIn})})}catch{remaining.push(item)}}saveQueue(remaining);renderQueue();if(q.length&&!remaining.length){guests=await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);render()}}
function guestFromScanned(value){let text=String(value||'');try{const u=new URL(text,location.origin),token=u.searchParams.get('g')||u.searchParams.get('guest');if(token)return guests.find(g=>g.token===token)}catch{}return guests.find(g=>g.id===text)}
async function openScanner(){if(!('BarcodeDetector'in window)||!navigator.mediaDevices?.getUserMedia){alert(_txt('Camera QR scanning is not supported in this browser. Use guest search instead.','Camera QR scanning is not supported in this browser. Use guest search instead.'));return}try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}});$('#scannerVideo').srcObject=stream;await $('#scannerVideo').play();$('#scannerDialog').showModal();const detector=new BarcodeDetector({formats:['qr_code']});const tick=async()=>{if(!stream)return;try{const codes=await detector.detect($('#scannerVideo'));if(codes[0]){const guest=guestFromScanned(codes[0].rawValue);if(guest){await toggle(guest.id,true);closeScanner();document.querySelector(`[data-guest-id="${CSS.escape(guest.id)}"]`)?.scrollIntoView({behavior:'smooth',block:'center'});return}$('#scannerStatus').innerHTML='<span class="i18n i18n-en">This QR code does not belong to a guest in this invitation.</span><span class="i18n i18n-km khmer-text" lang="km">This QR code does not belong to a guest in this invitation.</span>'}}catch{}scanTimer=setTimeout(tick,260)};tick()}catch(e){alert(_txt('Camera could not be opened:','Camera could not be opened:')+' '+e.message)}}
function closeScanner(){clearTimeout(scanTimer);scanTimer=null;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}$('#scannerVideo').srcObject=null;$('#scannerDialog').close()}
$('#guestSearch').oninput=render;$('#scanQrBtn').onclick=openScanner;$('#closeScanner').onclick=closeScanner;$('#scannerDialog').addEventListener('close',()=>{if(stream)closeScanner()});window.addEventListener('online',()=>{setNetwork();flushQueue()});window.addEventListener('offline',setNetwork);setNetwork();load();if('serviceWorker'in navigator)navigator.serviceWorker.register('/service-worker.js').catch(()=>{});
if(window.EInviteI18n&&typeof window.EInviteI18n.subscribe==='function'){window.EInviteI18n.subscribe(function(){setNetwork();render()})}
})();;(()=>{'use strict';
let lastDialogTrigger=new WeakMap();
const focusable='a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function syncPanel(panel,open,trigger){if(!panel)return;panel.hidden=!open;try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(trigger)trigger.setAttribute('aria-expanded',String(open));if(!open&&panel.contains(document.activeElement))trigger?.focus();}
function trapDialogKey(event,dialog){const nodes=[...dialog.querySelectorAll(focusable)].filter(el=>!el.hidden&&el.getClientRects().length&&!el.closest('[inert],[aria-hidden="true"]'));if(!nodes.length)return;if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}
function observeDialogs(){document.querySelectorAll('dialog').forEach(dialog=>{if(dialog.dataset.a11yBound)return;dialog.dataset.a11yBound='1';dialog.addEventListener('close',()=>{const trigger=lastDialogTrigger.get(dialog);if(trigger?.isConnected)trigger.focus()});dialog.addEventListener('cancel',event=>{event.preventDefault();dialog.close()})});}
function init(){
 document.querySelectorAll('button:not([aria-label])').forEach(b=>{if(!b.textContent.trim())b.setAttribute('aria-label',b.title||'Action')});
 document.querySelectorAll('img:not([alt])').forEach(img=>img.alt='Invitation image');
 document.querySelectorAll('a > button').forEach(button=>{const a=button.parentElement;a.classList.add(...button.classList);a.setAttribute('role','button');a.textContent=button.textContent;button.remove()});
 document.querySelectorAll('.khmer-picker select').forEach(select=>{if(!select.getAttribute('aria-label')){const label=select.closest('label')?.childNodes?.[0]?.textContent?.trim();if(label)select.setAttribute('aria-label',label)}});
 document.addEventListener('click',event=>{const trigger=event.target.closest('button,[role="button"],a');if(!trigger)return;requestAnimationFrame(()=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&!lastDialogTrigger.has(top))lastDialogTrigger.set(top,trigger);observeDialogs()})},true);
 document.addEventListener('keydown',event=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&event.key==='Tab'){trapDialogKey(event,top);return}if(event.key!=='Escape')return;if(top){top.close();event.preventDefault();event.stopPropagation();return}const openDrawer=[...document.querySelectorAll('[data-drawer-open="true"],.is-open[role="dialog"]')].filter(x=>!x.hidden).at(-1);if(openDrawer){const trigger=document.querySelector(`[aria-controls="${CSS.escape(openDrawer.id)}"]`);syncPanel(openDrawer,false,trigger);openDrawer.dataset.drawerOpen='false';event.preventDefault()}});
 document.querySelectorAll('[aria-controls]').forEach(trigger=>{if(trigger.dataset.a11yManaged==='true')return;const panel=document.getElementById(trigger.getAttribute('aria-controls'));if(!panel)return;const update=()=>{const open=trigger.getAttribute('aria-expanded')==='true'||panel.classList.contains('open')||panel.classList.contains('is-open');try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(!open&&panel.contains(document.activeElement))trigger.focus()};trigger.addEventListener('click',()=>setTimeout(update,0));update()});
 observeDialogs();new MutationObserver(observeDialogs).observe(document.body,{childList:true,subtree:true});
}
window.EInviteAccessibility={syncPanel};document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();