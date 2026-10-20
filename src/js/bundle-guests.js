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
  // Ids must be unique in a document, and this switch is injected into every <header> — the editor
  // route has six of them (measured: six #lang-km / #lang-en pairs, two of them visible) and
  // dashboard two. Only the first copy claims the ids; every copy carries `data-lang`, which is what
  // the delegated click handler and `syncSwitch` use.
  var switchCount = 0;
  function makeSwitch() {
    var first = switchCount === 0;
    switchCount++;
    var wrap = doc.createElement("div");
    wrap.className = "language-switch";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "Select interface language");
    var enBtn = doc.createElement("button");
    enBtn.type = "button"; if (first) enBtn.id = "lang-en"; enBtn.setAttribute("data-lang", "en");
    enBtn.setAttribute("aria-label", "Switch to English"); enBtn.textContent = "English";
    var kmBtn = doc.createElement("button");
    kmBtn.type = "button"; if (first) kmBtn.id = "lang-km"; kmBtn.setAttribute("data-lang", "km");
    kmBtn.setAttribute("aria-label", "ប្ដូះបើកភាសាខ្មែរ"); kmBtn.setAttribute("lang", "km"); kmBtn.textContent = "ខ្មែរ";
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
  // One delegated listener instead of one per injected switch. The editor rebuilds its header
  // (studio topbar, organizeHeader()) after load, so a per-node listener could end up on a node
  // nobody sees while the visible copy — a re-rendered clone of the same markup — had none: clicking
  // ខ្មែរ on index.html changed nothing at all (measured: no state change, no navigation, no visible
  // Khmer copy, while the same button switched languages on the other 15 routes). Delegation
  // survives re-renders and duplicate mounts.
  var delegated = false;
  function onLanguageClick(e) {
    var target = e.target;
    var b = target && target.closest ? target.closest("[data-lang]") : null;
    if (!b || !b.closest || !b.closest(".language-switch")) return;
    e.preventDefault();
    if (global.EInviteI18n && global.EInviteI18n.set) global.EInviteI18n.set(b.getAttribute("data-lang"));
  }
  function injectSwitches() {
    if (!doc.querySelectorAll) return;
    if (!delegated && doc.addEventListener) { doc.addEventListener("click", onLanguageClick); delegated = true; }
    var headers = doc.querySelectorAll("header");
    var lang = get();
    for (var i = 0; i < headers.length; i++) {
      var h = headers[i];
      if (h.querySelector(".language-switch")) continue;
      var sw = makeSwitch();
      h.appendChild(sw);
    }
    var all = doc.querySelectorAll(".language-switch");
    for (var j = 0; j < all.length; j++) syncSwitch(all[j], lang);
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
      if (mode === "km") return '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + escHTML(kmv) + '</span>';
      return '<span class="i18n i18n-en">' + escHTML(en) + '</span>' +
             '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + escHTML(kmv) + '</span>';
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
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false,selectOptions=null}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label>Value</label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('.ei-dialog-message').textContent=message;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input');host.hidden=false;if(selectOptions&&selectOptions.length){const wrap=document.createElement('label');wrap.textContent='Type';field=document.createElement('select');selectOptions.forEach(({value:v,label})=>{const o=document.createElement('option');o.value=v;o.textContent=label;field.append(o)});field.value=value;host.append(field)}else{field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';host.append(field)}}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel',selectOptions:Array.isArray(options.selectOptions)?options.selectOptions:null});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};
// Custom-units engine (owner decision, CANVA-UI §5, accepted 2026-10-20): the
// poster size prompts accept px (default), in, cm — plus inch/inches and ft —
// converting at 96 px per CSS inch (cm via 96/2.54). Shared by the editor
// custom canvas-size prompt (app.js) and the Template Studio custom poster
// size prompt (templates.js); lives here because both route bundles already
// load ui-dialogs.js before their consumer modules.
window.EInvitePosterUnits=Object.freeze({
 PX_PER:{in:96,cm:96/2.54,ft:1152},
 parse(value){
  const s=String(value||'').toLowerCase().replace(/×|,|\]/g,'x');
  const m=/(\d+(?:\.\d+)?)\s*(in|inch|inches|"|cm|centimeters?|ft|feet|')?\s*x\s*(\d+(?:\.\d+)?)\s*(in|inch|inches|"|cm|centimeters?|ft|feet|')?/.exec(s);
  if(!m)return null;
  // "24 x 36 in" — one trailing unit applies to BOTH sides; two units stay per-side.
  return {w:m[1],wu:m[2]||m[4],h:m[3],hu:m[4]||m[2]};
 },
 toPx(number,unit){
  const per=this.PX_PER[String(unit||'').replace(/inches|"/g,'in').replace(/centimeters?/,'cm').replace(/feet|'/g,'ft')];
  return per?number*per:number // bare numbers stay px
 }
});
})();;(()=>{
 'use strict';
 const LAST_KEY='sovan-active-invite';
 const routeMatch=location.pathname.match(/\/invitations\/([^/]+)\/(editor|guests|responses|analytics|materials|checkin)\/?$/i);
 const queryId=new URLSearchParams(location.search).get('invitation');
 const routeId=routeMatch?decodeURIComponent(routeMatch[1]):'';
 const explicitId=routeId||queryId||'';
 const section=routeMatch?.[2]?.toLowerCase()||'';
 const safe=id=>String(id||'').trim();
 // Local/demo ids (`demo-wedding` is the app's "nothing selected" fallback, `local-draft` the
 // unsaved editor draft) have no server counterpart. Remembering one used to make every later page
 // resolve it as if it were a real invitation: the signed-in editor asked the server for
 // /api/invitations/demo-wedding plus its comments/approvals/review-context/studio-release and the
 // four /api/studio/* routes — eight 404s per load. The remembered value is now ignored and purged.
 const isLocalId=id=>/^(demo-|local-)/i.test(safe(id));
 function getInvitationId(options={}){
   const direct=safe(explicitId);if(direct)return direct;
   if(options.allowRemembered===false)return '';
   const stored=safe(localStorage.getItem(LAST_KEY));
   if(!stored)return '';
   if(isLocalId(stored)){try{localStorage.removeItem(LAST_KEY)}catch(e){/* storage disabled */}return ''}
   return stored
 }
 function remember(id){id=safe(id);if(id&&!isLocalId(id))localStorage.setItem(LAST_KEY,id);return id}
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
})();;/**
 * guests.js — Guest list management (ROADMAP §5.6).
 * Renders the guest table, summary metrics, per-guest action buttons (edit,
 * personal-link, QR, check-in, remove), CSV import/export, and inline editing.
 * All user-facing strings go through EInviteI18n.langText() (dual .i18n-en/.i18n-km
 * spans, CSS-driven toggle) or a plain-text helper for DOM APIs (alert/confirm/
 * textContent) that reads EInviteI18n.get() at call time. No STRINGS table so
 * check-bilingual-consistency.py (which only scans top-level src/js/*.js) is
 * not polluted with EN-FALLBACK placeholders — see §8 of LANGUAGE-GAP-REPORT.
 */
const $=s=>document.querySelector(s),inviteId=window.EInviteContext?.getInvitationId()||'demo-wedding',localKey=`sovan-guests:${inviteId}`;let guests=[],server=false,slug='invitation',invitation=null,rsvpEnabled=true;
/* Goal 6b (§5.5): the batch-share selection. Declared here, with the other
   module-level state, because the wiring that reads it runs before the
   spreadsheet/link-code sections below — a const declared further down is in
   the temporal dead zone at that point (measured: bundle-guests.js threw
   "Cannot access 'pickedGuests' before initialization" and the list never
   rendered). */
const pickedGuests=new Set();
const _isKm=()=>(window.EInviteI18n&&window.EInviteI18n.get?window.EInviteI18n.get():(document.documentElement.lang||'').toLowerCase()).startsWith('km');
const _html=(en,km)=>{if(window.EInviteI18n)return window.EInviteI18n.langText(en,km);const e=_isKm()?(km!=null?km:en):en;return`<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km!=null?km:en)}</span>`};
const _txt=(en,km)=>{const isKm=_isKm();return isKm?(km!=null?km:en):en};
async function request(path,options={}){let r=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(Error(data.error||'Request failed'),{status:r.status,data});return data}
async function load(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){server=false;guests=JSON.parse(localStorage.getItem(localKey)||'[]');window.EInviteBackend.message($('#guestList'),_txt('Guest management, personal links, QR codes, and check-in require the full application server.','ការគ្រប់គ្រងភ្ញៀវ តំណផ្ទាល់ខ្លួន កូដ QR និងការឆែកចូល ត្រូវការម៉ាស៊ីនបម្រើកម្មវិធីពេញលេញ។'));render();return}try{await request('/api/health');server=true;invitation=await request(`/api/invitations/${encodeURIComponent(inviteId)}`);slug=invitation?.slug||slug;rsvpEnabled=invitation?.document?.settings?.rsvpEnabled!==false;guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}catch(error){server=false;guests=JSON.parse(localStorage.getItem(localKey)||'[]');if(error.status===404)window.EInviteBackend?.message($('#guestList'),_txt('This invitation is not available in the current server context.','ការអញ្ជើញនេះមិនអាចប្រើនៅក្នុងបរិបទម៉ាស៊ីនបម្រើបច្ចុប្បន្នទេ។'))}render()}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function guestUrl(g){if(!g?.token)return'';const code=String(g.slug||'').trim();return server?`${location.origin}/i/${encodeURIComponent(slug)}${code?`/${encodeURIComponent(code)}`:''}?g=${encodeURIComponent(g.token)}`:`${location.origin}${location.pathname.replace(/guests(?:\.html)?$/,'public.html')}?g=${encodeURIComponent(g.token)}`}
/* Goal 6a/6b (§5.1, §5.5): the shareable form of a guest link is the readable
   one — project slug plus the guest's frozen code, no ?g= token. The code is a
   mnemonic, not the capability (§4.1), so this is what a designer pastes into a
   group chat; the token stays in guestUrl() for the private per-guest link. A
   guest whose code has not been generated yet falls back to the bare project
   link, which still opens the invitation. */
function guestShareUrl(g){const code=String(g?.slug||'').trim();return server?`${location.origin}/i/${encodeURIComponent(slug)}${code?`/${encodeURIComponent(code)}`:''}`:''}
function coupleName(){return String(invitation?.document?.fields?.names||'').trim()}
/* The three channel links are the same shapes the public share panel builds
   (src/js/public-share-panel.js: t.me/share/url, wa.me/?text=,
   sharer.php?u=) — that builder is page-local and not exported, so the formats
   are mirrored here rather than loaded onto the guests route for three URLs. */
function shareChannelLinks(row){const url=guestShareUrl(row);if(!url)return'';const message=_txt(`You are invited to ${coupleName()||'our celebration'}. ${url}`,'');return`<a target="_blank" rel="noopener noreferrer" href="https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(message)}">Telegram</a><a target="_blank" rel="noopener noreferrer" href="https://wa.me/?text=${encodeURIComponent(message)}">WhatsApp</a><a target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}">Facebook</a>`}
function filtered(){let q=$('#search').value.trim().toLowerCase(),filter=$('#statusFilter').value;return guests.filter(g=>{let text=`${g.name} ${g.phone||''} ${g.email||''} ${g.group_name||''} ${g.household_id||''} ${g.table_name||''} ${(g.tags||[]).join(' ')}`.toLowerCase(),status=g.rsvp_status||'';if(!text.includes(q))return false;if(!rsvpEnabled)return filter==='all'||filter==='checked'&&g.checked_in;return filter==='all'||filter==='yes'&&status.startsWith('Yes')||filter==='no'&&status.startsWith('Unable')||filter==='pending'&&!status||filter==='checked'&&g.checked_in})}
function render(){let yes=guests.filter(g=>g.rsvp_status?.startsWith('Yes')).length,no=guests.filter(g=>g.rsvp_status?.startsWith('Unable')).length,pending=guests.length-yes-no,checked=guests.filter(g=>g.checked_in).length;$('#summary').innerHTML=rsvpEnabled?`<div class="metric"><strong>${guests.length}</strong>${_html('Invited','បានអញ្ជើញ')}</div><div class="metric"><strong>${yes}</strong>${_html('Attending','នឹងចូលរួម')}</div><div class="metric"><strong>${no}</strong>${_html('Declined','បានច្រានចោល')}</div><div class="metric"><strong>${pending}</strong>${_html('Pending','កំពុងរង់ចាំ')}</div><div class="metric"><strong>${checked}</strong>${_html('Checked in','បានឆែកចូល')}</div>`:`<div class="metric"><strong>${guests.length}</strong>${_html('Invited','បានអញ្ជើញ')}</div><div class="metric"><strong>${checked}</strong>${_html('Checked in','បានឆែកចូល')}</div><div class="metric"><strong>${_html('Off','បិទ')}</strong>${_html('RSVP disabled','RSVP បានបិទ')}</div>`;const filter=$('#statusFilter');if(filter){[...filter.options].forEach(o=>{if(['yes','no','pending'].includes(o.value))o.hidden=!rsvpEnabled});if(!rsvpEnabled&&['yes','no','pending'].includes(filter.value))filter.value='all'}
$('#guestList').innerHTML=filtered().map(g=>{const status=rsvpEnabled?esc(g.rsvp_status||_txt('Awaiting reply','កំពុងរង់ចាំការឆ្លើយតប')):(_txt(g.token_revoked_at?'Personal link revoked':(g.personalLinkAvailable?'Personal invitation ready':'Personal link needs rotation'),g.token_revoked_at?'Personal link revoked':(g.personalLinkAvailable?'Personal invitation ready':'Personal link needs rotation')));return`<div class="guest-row ${g.checked_in?'checked':''}"><div><strong>${esc(g.name)}</strong><br><small>${esc([g.phone,g.email,g.group_name&&`${_txt('Group:','ក្រុម៖')} ${g.group_name}`,g.household_id&&`${_txt('Household:','គ្រួសារ៖')} ${g.household_id}`,g.table_name&&`${_txt('Table:','តុ៖')} ${g.table_name}`,g.seat_label&&`${_txt('Seat:','អាសនៈ៖')} ${g.seat_label}`].filter(Boolean).join(' · '))}</small>${(g.tags||[]).length?`<span class="tags">${(g.tags||[]).map(tag=>`<span class="tag">${esc(tag)}</span>`).join('')}</span>`:''}
<div class="guest-meta">${g.checked_in?`${_html('Checked in','បានឆែកចូល')}${g.check_in_at?` ${_html('at','នៅ')} ${esc(new Date(g.check_in_at).toLocaleString())}`:''}`:''}${g.rsvp_status&&rsvpEnabled?`${_html('RSVP','RSVP')}: ${esc(g.rsvp_status)}`:''}${g.delivery_status?` · ${esc(g.delivery_status)}`:''}${g.opened_at?` · ${_html('Opened','បានបើក')}`:''}</div></div><span>${status}</span><button data-edit="${g.id}">${_html('Edit','កែសម្រួល')}</button><button data-link="${g.id}">${g.personalLinkAvailable?_html('Link','តំណ'):_html('Rotate link','បង្វិលតំណ')}</button><button data-qr="${g.id}" ${g.personalLinkAvailable?'':'disabled'}>${_html('QR','QR')}</button><button data-check="${g.id}">${g.checked_in?_html('Undo check-in','ធ្វើវិញការឆែកចូល'):_html('Check in','ឆែកចូល')}</button><button class="danger" data-delete="${g.id}">${_html('Remove','ដកចេញ')}</button><label class="guest-pick"><input type="checkbox" data-pick="${g.id}" ${pickedGuests.has(g.id)?'checked':''} aria-label="${esc(_txt('Select this guest for the link list','ជ្រើរើសភ្ញៀវនេះសម្រាប់បញ្ជីតំណ'))}"></label></div>`}).join('')||`<p class="empty">${_html('No guests match this filter.','គ្មានភ្ញៀវណាមួយត្រូវនឹងតម្រងនេះទេ។')}</p>`}
;
/* Goal 6b (§5.5): the selection drives "Copy all links". Checked guests are
   copied; with none checked the whole filtered list is, which is what a designer
   who has just imported a sheet wants. */
document.querySelectorAll('[data-pick]').forEach(box=>{box.onchange=()=>{box.checked?pickedGuests.add(box.dataset.pick):pickedGuests.delete(box.dataset.pick);render()}});
const selectAllBox=$('#selectAllGuests');if(selectAllBox){selectAllBox.checked=guests.length>0&&pickedGuests.size===guests.length;selectAllBox.indeterminate=pickedGuests.size>0&&pickedGuests.size<guests.length}
$('#search').oninput=render;$('#statusFilter').onchange=render;
$('#addForm').onsubmit=async e=>{e.preventDefault();let data=Object.fromEntries(new FormData(e.target));data.tags=String(data.tags||'').split(',').map(x=>x.trim()).filter(Boolean);await addGuest(data);e.target.reset();render()};
async function addGuest(data,refresh=true){if(server){const created=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`,{method:'POST',body:JSON.stringify(data)});if(refresh)guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);return created||null}const local={id:crypto.randomUUID(),name:data.name,phone:data.phone,slug:'',token:crypto.randomUUID().slice(0,12),personalLinkAvailable:true,rsvp_status:null,checked_in:false};guests.unshift(local);localStorage.setItem(localKey,JSON.stringify(guests));return local}
async function editGuest(id){let g=guests.find(x=>x.id===id);if(!g)return;const fields=[['name',_txt('Guest name','ឈ្មោះភ្ញៀវ'),g.name],['phone',_txt('Phone number','លេខទូរស័ព្ទ'),g.phone||''],['email',_txt('Email','អ៊ីមែល'),g.email||''],['groupName',_txt('Group','ក្រុម'),g.group_name||''],['householdId',_txt('Household','គ្រួសារ'),g.household_id||''],['tableName',_txt('Table','តុ'),g.table_name||''],['seatLabel',_txt('Seat','អាសនៈ'),g.seat_label||''],['tags',_txt('Tags (comma separated)','ស្លាក (បំបែកដោយក្បៀស)'),(g.tags||[]).join(', ')]];const form=document.createElement('form');form.innerHTML=`<h2>${_html('Edit guest','កែសម្រួលភ្ញៀវ')}</h2>${fields.map(([name,label,value])=>`<label>${esc(label)}<input name="${name}" value="${esc(value)}"></label>`).join('')}<div class="dialog-actions"><button type="button" data-cancel>${_html('Cancel','បោះបង់')}</button><button class="primary">${_html('Save','រក្សាទុក')}</button></div>`;$('#qrBody').replaceChildren(form);$('#qrModal').showModal();form.querySelector('[data-cancel]').onclick=()=>$('#qrModal').close();form.onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));data.tags=String(data.tags||'').split(',').map(x=>x.trim()).filter(Boolean);if(server){await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${id}`,{method:'PUT',body:JSON.stringify(data)});guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}else Object.assign(g,{name:data.name,phone:data.phone,email:data.email,group_name:data.groupName,household_id:data.householdId,table_name:data.tableName,seat_label:data.seatLabel,tags:data.tags});$('#qrModal').close();render()}}
async function checkIn(id){let g=guests.find(x=>x.id===id),checkedIn=!g.checked_in;if(server){await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${id}/check-in`,{method:'PUT',body:JSON.stringify({checkedIn})});guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}else{g.checked_in=checkedIn;g.checked_in_at=checkedIn?Date.now():null;localStorage.setItem(localKey,JSON.stringify(guests))}render()}
async function removeGuest(id){if(!(await uiConfirm(_txt('Remove this guest?','ដកភ្ញៀវនេះចេញ?'),{title:_txt('Remove guest','ដកភ្ញៀវចេញ'),danger:true,confirmText:_txt('Remove','ដកចេញ')})))return;if(server){await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${id}`,{method:'DELETE'});guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`)}else{guests=guests.filter(g=>g.id!==id);localStorage.setItem(localKey,JSON.stringify(guests))}render()}
async function rotateLink(g){let value=await uiPrompt(_txt('Optional expiration in days. Leave blank for no expiration.','ថ្ងៃផុតកំណត់ (ស្រេចចិត្ត)។ ទុកទំនេរ បើមិនចង់ឱ្យមានការផុតកំណត់។'),'',{title:_txt('Rotate personal invitation link','បង្វិលតំណអញ្ជើញផ្ទាល់ខ្លួន'),confirmText:_txt('Rotate link','បង្វិលតំណ')});if(value===null)return;const days=String(value).trim();const payload=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${g.id}/token/rotate`,{method:'POST',body:JSON.stringify(days?{expiresDays:Number(days)}:{})});g.token=payload.token;g.token_expires_at=payload.tokenExpiresAt||null;g.token_revoked_at=null;g.personalLinkAvailable=true;return payload.token}
async function manageLink(id){let g=guests.find(x=>x.id===id);if(!g)return;if(!g.token){try{await rotateLink(g);render()}catch(error){alert(_txt(error.message||'Action failed','Action failed'))}return}const url=guestUrl(g);$('#qrBody').innerHTML=`<h2>${esc(g.name)}</h2><p>${_html('Personal invitation link','តំណអញ្ជើញផ្ទាល់ខ្លួន')}</p><p class="personal-link-status">${g.token_expires_at?`${_html('Expires','ផុតកំណត់')} ${esc(new Date(g.token_expires_at).toLocaleString())}`:_html('No expiration set','មិនបានកំណត់ការផុតកំណត់ទេ')}</p><div class="dialog-actions"><button id="copyPersonalLink">${_html('Copy personal link','ចម្លងតំណផ្ទាល់ខ្លួន')}</button><button id="rotatePersonalLink">${_html('Rotate link','បង្វិលតំណ')}</button><button id="revokePersonalLink" class="danger">${_html('Revoke link','ដកតំណចេញ')}</button></div>`;$('#qrModal').showModal();$('#copyPersonalLink').onclick=async()=>{await navigator.clipboard.writeText(url);$('#copyPersonalLink').textContent=_txt('Copied!','ចម្លងរួចរាល់!')};$('#rotatePersonalLink').onclick=async()=>{try{await rotateLink(g);$('#qrModal').close();render()}catch(error){alert(_txt(error.message||'Action failed','Action failed'))}};$('#revokePersonalLink').onclick=async()=>{if(!(await uiConfirm(_txt('Revoke this personal link? Existing copies and QR codes will stop working.','ដកតំណផ្ទាល់ខ្លួននេះចេញ? ចម្លងដែលមាន និងកូដ QR នឹងឈប់ដំណើរការ។'),{title:_txt('Revoke personal link','ដកតំណផ្ទាល់ខ្លួនចេញ'),danger:true,confirmText:_txt('Revoke','ដកតំណចេញ')})))return;await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${g.id}/token/revoke`,{method:'POST',body:'{}'});g.token=null;g.personalLinkAvailable=false;g.token_revoked_at=Date.now();$('#qrModal').close();render()}}
function showQr(id){let g=guests.find(x=>x.id===id);if(!g?.token)return manageLink(id);let url=guestUrl(g),qr=server?`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(id)}/qr.png`:'';$('#qrBody').innerHTML=`<h2>${esc(g.name)}</h2>${qr?`<div id="qrImageWrap"><img id="guestQrImage" src="${qr}" alt="${_txt('QR code','កូដ QR')} for ${esc(g.name)}" width="420" height="420"><p id="qrError" class="hint" hidden></p></div>`:`<p class="hint">${_html('Run the local server to generate a private QR code.','ចាប់ផ្ដើមម៉ាស៊ីនបម្រើក្នុងស្រុក ដើម្បីបង្កើតកូដ QR ឯកជន។')}</p>`}<p><button id="copyLink">${_html('Copy personal link','ចម្លងតំណផ្ទាល់ខ្លួន')}</button>${qr?` <a id="downloadGuestQr" href="${qr}" download="${esc(g.name)}-qr.png" class="button-link">${_html('Download QR','ទាញយក QR')}</a>`:''}</p>`;$('#qrModal').showModal();const img=$('#guestQrImage'),download=$('#downloadGuestQr'),error=$('#qrError');if(img)img.onerror=()=>{img.hidden=true;if(download)download.hidden=true;if(error){error.hidden=false;error.textContent=_txt('QR generation is unavailable. The personal link can still be copied safely.','ការបង្កើត QR មិនអាចប្រើបាន។ នៅតែអាចចម្លងតំណផ្ទាល់ខ្លួនដោយសុវត្ថិភាពបាន។')}};$('#copyLink').onclick=async()=>{await navigator.clipboard.writeText(url);$('#copyLink').textContent=_txt('Copied!','ចម្លងរួចរាល់!')}}
$('.close').onclick=()=>$('#qrModal').close();
function parseCsv(text){let rows=[],row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){let c=text[i];if(c==='"'&&quoted&&text[i+1]==='"'){cell+='"';i++}else if(c==='"')quoted=!quoted;else if(c===','&&!quoted){row.push(cell.trim());cell=''}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell.trim());if(row.some(Boolean))rows.push(row);row=[];cell=''}else cell+=c}row.push(cell.trim());if(row.some(Boolean))rows.push(row);return rows}
$('#importFile').onchange=e=>{const file=e.target.files?.[0];if(file)openImport(file)};
$('#exportBtn').onclick=()=>{let rows=[[_txt('Name','ឈ្មោះ'),_txt('Phone','ទូរស័ព្ទ'),_txt('Email','អ៊ីមែល'),_txt('Group','ក្រុម'),_txt('Household','គ្រួសារ'),_txt('Table','តុ'),_txt('Seat','អាសនៈ'),_txt('Tags','ស្លាក'),rsvpEnabled?_txt('RSVP status','ស្ថានភាព RSVP'):_txt('Invitation mode','របៀបអញ្ជើញ'),_txt('Checked in','បានឆែកចូល'),_txt('Delivery','ការផ្ញើ'),_txt('Opened','បានបើក'),_txt('Personal link','តំណផ្ទាល់ខ្លួន')],...guests.map(g=>[g.name,g.phone||'',g.email||'',g.group_name||'',g.household_id||'',g.table_name||'',g.seat_label||'',(g.tags||[]).join('|'),rsvpEnabled?(g.rsvp_status||_txt('Pending','កំពុងរង់ចាំ')):_txt('RSVP disabled','RSVP បានបិទ'),g.checked_in?_txt('Yes','ចាស'):_txt('No','ទេ'),g.delivery_status||'',g.opened_at?new Date(g.opened_at).toISOString():'',guestUrl(g)])],csv=rows.map(row=>row.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\r\n'),a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='guest-list.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
/* ────────────────────────────────────────────────────────────────────────────
   Bulk guest import — the research pass's phase A (§5.7 of
   docs/reviews/bulk-guest-import-research.md).

   Why Excel is the primary path: a spreadsheet has no charset. Excel on Windows
   writes CSV as UTF-16LE-with-BOM or in a legacy codepage, and reading that as
   UTF-8 either throws or silently imports mojibake Khmer names (research risk
   2). CSV is still accepted, with the BOM sniffed; a byte stream that no
   supported encoding decodes is refused with a message that names the fix,
   never imported as garbage.

   SheetJS is loaded lazily from the vendored build only when a spreadsheet is
   actually chosen, so the guests route keeps its 3-script / 440,000-byte page
   budget (docs/route-bundle-sources.json, src/python/build/build_page_manifests.py).

   Khmer below comes from docs/i18n/TRANSLATIONS.csv where an approved string
   exists; every string passed with an EMPTY Khmer slot is listed as KH_PENDING
   in docs/reviews/bulk-guest-import-implementation.md — none is invented.
   ──────────────────────────────────────────────────────────────────────────── */
const SHEETJS_URL='/vendor/sheetjs/xlsx.mini.min.js';let sheetJsPromise=null;
function loadSheetJs(){if(window.XLSX)return Promise.resolve(window.XLSX);if(!sheetJsPromise)sheetJsPromise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=SHEETJS_URL;script.onload=()=>window.XLSX?resolve(window.XLSX):reject(Error('Spreadsheet library did not initialise'));script.onerror=()=>reject(Error('Spreadsheet library could not be loaded'));document.head.append(script)});return sheetJsPromise}
function decodeImportText(buffer){const bytes=new Uint8Array(buffer),decode=(encoding,offset)=>new TextDecoder(encoding).decode(bytes.subarray(offset));if(bytes.length>=3&&bytes[0]===0xEF&&bytes[1]===0xBB&&bytes[2]===0xBF)return{text:decode('utf-8',3),encoding:'UTF-8 with BOM'};if(bytes.length>=2&&bytes[0]===0xFF&&bytes[1]===0xFE)return{text:decode('utf-16le',2),encoding:'UTF-16LE with BOM'};if(bytes.length>=2&&bytes[0]===0xFE&&bytes[1]===0xFF)return{text:decode('utf-16be',2),encoding:'UTF-16BE with BOM'};try{return{text:new TextDecoder('utf-8',{fatal:true}).decode(bytes),encoding:'UTF-8'}}catch(error){return{text:'',encoding:'',failed:true}}}
const csvCells=rows=>rows.map(row=>Array.isArray(row)?row.map(value=>String(value??'').trim()):[]);
async function readImportFile(file){const name=String(file?.name||'').toLowerCase();if(/\.xlsx$|\.xlsm$|\.xls$/.test(name)){const XLSX=await loadSheetJs();const workbook=XLSX.read(new Uint8Array(await file.arrayBuffer()));const sheet=workbook.Sheets[workbook.SheetNames[0]];if(!sheet)throw Error('The workbook has no worksheet');return{rows:csvCells(XLSX.utils.sheet_to_json(sheet,{header:1,blankrows:false,defval:''})),source:'Excel'}}const decoded=decodeImportText(await file.arrayBuffer());if(decoded.failed)return{rows:[],source:'CSV',decodeFailure:true};return{rows:csvCells(parseCsv(decoded.text)),source:'CSV · '+decoded.encoding}}
function importStateFor(rows,source){const headerRow=rows[0]||[],header=/name|guest|ឈ្មោះ/i.test(String(headerRow[0]||'')),columns=Math.max(1,rows.reduce((max,row)=>Math.max(max,row.length),0));return{rows,source,header,columns,column:0,skipDuplicates:false,start:header?1:0}}
function importEntries(state){const entries=[];for(let index=state.start;index<state.rows.length;index++){const row=state.rows[index]||[],name=String(row[state.column]||'').trim();if(!row.some(value=>String(value||'').trim()))continue;entries.push({index,name,phone:String(row[1]||'').trim()})}return entries}
function importFindings(state){const entries=importEntries(state),blank=[],duplicates=[],seen=new Set();for(const entry of entries){if(!entry.name){blank.push(entry.index+1);continue}const key=entry.name.toLowerCase();if(seen.has(key)){duplicates.push(entry.name);continue}seen.add(key)}return{entries,blank,duplicates}}
function importRowsToImport(state){const{entries,duplicates}=importFindings(state);if(!state.skipDuplicates)return entries;const seen=new Set(),kept=[];for(const entry of entries){const key=entry.name.toLowerCase();if(seen.has(key))continue;seen.add(key);kept.push(entry)}return kept}
let importDialog=null,importState=null;
function ensureImportDialog(){if(importDialog)return importDialog;importDialog=document.createElement('dialog');importDialog.className='ei-dialog';importDialog.setAttribute('aria-modal','true');importDialog.innerHTML='<div class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="guest-import-body"></div><div class="ei-dialog-actions"></div></div>';document.body.append(importDialog);importDialog.addEventListener('close',()=>{importState=null});return importDialog}
function closeImportDialog(){importDialog?.close()}
function renderImportDialog(){
  const dialog=ensureImportDialog(),state=importState;
  const icon=dialog.querySelector('.ei-dialog-icon'),heading=dialog.querySelector('h2'),message=dialog.querySelector('.ei-dialog-message'),body=dialog.querySelector('.guest-import-body'),actions=dialog.querySelector('.ei-dialog-actions');
  if(!state){body.innerHTML='';actions.innerHTML='';return}
  if(state.failure){
    icon.textContent='!';heading.textContent=_txt('Import guests','នាំចូលភ្ញៀវ');
    message.innerHTML=_html('The file could not be read.','មិនអាចអានឯកសារបានទេ។');
    body.innerHTML=`<p class="hint">${esc(state.failure)}</p>`;
    actions.innerHTML=`<button type="button" class="ei-primary" data-cancel>${_html('Close','បិទ')}</button>`;
    actions.querySelector('[data-cancel]').onclick=closeImportDialog;return
  }
  if(state.decodeFailure){
    icon.textContent='!';heading.textContent=_txt('Import guests','នាំចូលភ្ញៀវ');
    message.innerHTML=_html('This CSV is neither UTF-8, UTF-16LE nor UTF-16BE. Export the guest list as .xlsx and import that instead — a spreadsheet has no charset, so Khmer names survive it.','ឯកសារ CSV នេះមិនមែនជា UTF-8, UTF-16LE ឬ UTF-16BE ទេ។ សូមនាំចេញបញ្ជីភ្ញៀវជា .xlsx ហើយនាំចូលវិញ — ឯកសារ spreadsheet មិនមានការកំណត់អក្សរ ដូច្នេះឈ្មោះខ្មែរនៅរក្សាបាន។');
    body.innerHTML='';actions.innerHTML=`<button type="button" class="ei-primary" data-cancel>${_html('Close','បិទ')}</button>`;
    actions.querySelector('[data-cancel]').onclick=closeImportDialog;return
  }
  const{entries,blank,duplicates}=importFindings(state),importable=importRowsToImport(state),detected=state.header?String((state.rows[0]||[])[state.column]||'').trim():'';
  icon.textContent='⇪';heading.textContent=_txt('Import guests','នាំចូលភ្ញៀវ');
  message.innerHTML=_html(state.header?`Found ${entries.length} rows, name column detected as '${detected||'Column 1'}'.`:`Found ${entries.length} rows, no header row detected — choose the name column.`,'');
  const options=Array.from({length:state.columns},(_,index)=>`<option value="${index}" ${index===state.column?'selected':''}>${esc(`Column ${index+1} — ${String((state.rows[0]||[])[index]||'').slice(0,18)||'—'}`)}</option>`).join('');
  const shown=entries.length>7?[...entries.slice(0,5),null,...entries.slice(-2)]:entries;
  const preview=shown.map(entry=>entry===null?`<div class="guest-row"><div><strong>…</strong></div></div>`:`<div class="guest-row"><div><strong>${esc(entry.name||_txt('(empty name)','(គ្មានឈ្មោះ)'))}</strong>${entry.phone?`<br><small>${esc(entry.phone)}</small>`:''}</div></div>`).join('');
  const emptyWarning=blank.length?`<p class="hint">${esc(`${blank.length} row(s) have no name, so nothing was imported yet (rows ${blank.slice(0,8).join(', ')}${blank.length>8?'…':''})`)}</p>`:'';
  // Re-import key (research §5.2): a sheet has no key of its own, so a row is
  // matched on lower(name) within this invitation. A match is updated and keeps
  // its frozen link; anything else is added. Nothing is merged or duplicated
  // silently — the counts are stated before the write.
  const existingByName=existingGuestIndex(),willUpdate=importable.filter(entry=>existingByName.has(entry.name.trim().toLowerCase())).length;
  const updateWarning=importable.length?`<p class="hint">${esc(`${willUpdate} row(s) match a guest already in this list and will be updated with their links kept; ${importable.length-willUpdate} will be added.`)}</p>`:'';
  const duplicateWarning=duplicates.length?`<p class="hint">${esc(`${duplicates.length} duplicate name(s) in this file: ${duplicates.slice(0,5).join(', ')}${duplicates.length>5?'…':''}`)}</p><label style="display:flex;gap:8px;align-items:center"><input type="checkbox" data-skip-duplicates ${state.skipDuplicates?'checked':''}> ${_html('Skip later duplicates (the default keeps both)','រំលងឈ្មោះស្ទួនពេលក្រោយ (ការកំណត់លំនាំដើមរក្សាទាំងពីរ)')}</label>`:'';
  body.innerHTML=`<label class="sr-only" for="importColumn">${_html('Name column','ជួរឈ្មោះ')}</label><select id="importColumn">${options}</select>${emptyWarning}${duplicateWarning}${updateWarning}<div class="guest-table">${preview}</div>`;
  const select=body.querySelector('#importColumn');select.onchange=()=>{state.column=Number(select.value);renderImportDialog()};
  const skip=body.querySelector('[data-skip-duplicates]');if(skip)skip.onchange=()=>{state.skipDuplicates=skip.checked;renderImportDialog()};
  actions.innerHTML=`<button type="button" data-cancel>${_html('Cancel','បោះបង់')}</button><button type="button" class="ei-primary" data-import ${blank.length||!importable.length?'disabled':''}>${esc(`Import ${importable.length} guest(s)`)}</button>`;
  actions.querySelector('[data-cancel]').onclick=closeImportDialog;
  actions.querySelector('[data-import]').onclick=()=>runImport(importable);
}
async function openImport(file){
  let parsed;
  try{parsed=await readImportFile(file)}catch(error){parsed={failure:error.message||String(error)}}
  const dialog=ensureImportDialog();
  importState=parsed.failure?{rows:[],source:'',failure:parsed.failure}:importStateFor(parsed.rows,parsed.source);
  renderImportDialog();
  if(!dialog.open)dialog.showModal();
}
async function runImport(entries){
  const button=importDialog?.querySelector('[data-import]');if(button)button.disabled=true;
  const existing=existingGuestIndex();let added=0,updated=0,failed=0;const touched=[];
  try{
    for(const entry of entries){
      const match=server?existing.get(entry.name.trim().toLowerCase()):null;
      try{
        if(match){
          // The frozen code is deliberately absent from this payload, so
          // update_guest_details' COALESCE(?,slug) leaves it untouched.
          await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(match.id)}`,{method:'PUT',body:JSON.stringify({name:match.name,phone:entry.phone||match.phone||'',email:match.email||'',groupName:match.group_name||'',householdId:match.household_id||'',tableName:match.table_name||'',seatLabel:match.seat_label||'',tags:match.tags||[]})});updated++;touched.push(match.id)
        }else{const created=await addGuest({name:entry.name,phone:entry.phone},false);added++;if(created?.id)touched.push(created.id)}
      }catch(error){failed++}
    }
  }finally{
    if(server)guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);
    closeImportDialog();render();
  }
  const summary=`${added} ${_txt('added','បានបន្ថែម')} · ${updated} ${_txt('updated','បានធ្វើបច្ចុប្បន្នភាព')}${failed?` · ${failed} ${_txt('failed','បានបរាជ័យ')}`:''}`;
  if(window.EInviteFeedback?.toast)window.EInviteFeedback.toast(summary);else alert(summary);
  $('#importFile').value='';
  openLinkEditor(guests.filter(guest=>touched.includes(guest.id)));
}
/* ── Phase C: per-guest link codes, the mapping screen and the freeze ──
   The code is a mnemonic, not the capability (research §4.1: OSWP's own source
   says the same of its household code and excludes 0 1 i l o so it can be read
   aloud). The 32-character ?g= token stays the capability and is unchanged.

   `slugify`/`randomCode` mirror server-side clean_slug/short_code for the live
   preview only. The server re-validates every submitted code and is
   authoritative; nothing here decides what a guest's link is. */
const SLUG_ALPHABET='23456789abcdefghjkmnpqrstuvwxyz';
async function copyGuestLinks(){const list=pickedGuests.size?guests.filter(g=>pickedGuests.has(g.id)):guests,urls=list.map(guestShareUrl).filter(Boolean);if(!urls.length){alert(_txt('There are no guest links to copy yet.','មិនទាន់មានតំណភ្ញៀវសម្រាប់ចម្លងទេ។'));return}await navigator.clipboard.writeText(urls.join('\n'));const summary=`${urls.length} ${_txt('link(s) copied','តំណបានចម្លង')}`;if(window.EInviteFeedback?.toast)window.EInviteFeedback.toast(summary);else alert(summary)}
function existingGuestIndex(){const index=new Map();for(const guest of guests){const key=String(guest.name||'').trim().toLowerCase();if(key&&!index.has(key))index.set(key,guest)}return index}
function slugify(value){return String(value??'').toLowerCase().replace(/[^a-z0-9-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60)}
function randomCode(length=6){const bytes=new Uint8Array(length);(window.crypto||window.msCrypto).getRandomValues(bytes);let out='';for(const byte of bytes)out+=SLUG_ALPHABET[byte%SLUG_ALPHABET.length];return out}
function proposedSlug(name,taken){const base=slugify(name)||randomCode(6);let candidate=base,index=2;while(taken.has(candidate)){candidate=`${base}-${index}`;index++}taken.add(candidate);return candidate}
function validSlug(value){return /^[a-z0-9-]{1,60}$/.test(value)}
let linkDialog=null,linkRows=[];
function ensureLinkDialog(){if(linkDialog)return linkDialog;linkDialog=document.createElement('dialog');linkDialog.className='ei-dialog';linkDialog.style.width='min(760px,calc(100vw - 32px))';linkDialog.setAttribute('aria-modal','true');linkDialog.innerHTML='<div class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon">↗</span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="guest-import-body"></div><div class="ei-dialog-actions"></div></div>';document.body.append(linkDialog);linkDialog.addEventListener('close',()=>{linkRows=[]});return linkDialog}
function closeLinkDialog(){linkDialog?.close()}
function renderLinkDialog(){
  if(!linkDialog)return;
  const body=linkDialog.querySelector('.guest-import-body'),actions=linkDialog.querySelector('.ei-dialog-actions'),message=linkDialog.querySelector('.ei-dialog-message');
  linkDialog.querySelector('h2').textContent=_txt('Guest links','តំណភ្ញៀវ');
  const changed=linkRows.filter(row=>row.slug!==row.original);
  message.innerHTML=_html(`Each guest gets their own link. Freezing keeps it: editing a name later changes the card and the page, but not a link you have already shared.${changed.length?` ${changed.length} code(s) changed and their old links will stop working.`:''}`,'');
  body.innerHTML=`<div class="guest-table">${linkRows.map((row,index)=>`<div class="guest-row"><div><strong>${esc(row.name)}</strong><br><small>${esc(slugPreview(row))}</small></div><input data-code="${index}" maxlength="60" value="${esc(row.slug)}" aria-label="${esc(_txt('Guest link code','លេខកូដតំណភ្ញៀវ'))}"><button type="button" data-regenerate="${index}" title="${esc(_txt('Generate a new code','បង្កើតលេខកូដថ្មី'))}">↻</button><span class="share-channels">${shareChannelLinks(row)}</span></div>`).join('')||`<p class="hint">${_html('No guests yet.','មិនទាន់មានភ្ញៀវនៅឡើយ។')}</p>`}</div><p class="share-note hint">${_html('Send a bare link on its own: Telegram then shows the invitation preview, and any text beside it suppresses the card.','ផ្ញើតំណទទេតែមួយដោយឡែក៖ Telegram នឹងបង្ហាញការមើលជាមុននៃការអញ្ជើញ ហើយអត្ថបទណាមួយនៅជាប់វានឹងលាក់កាតនោះ។')}</p>`;
  body.querySelectorAll('[data-code]').forEach(input=>{const index=Number(input.dataset.code);input.onchange=()=>{const cleaned=slugify(input.value)||linkRows[index].original;if(!validSlug(cleaned)){input.value=linkRows[index].original;linkRows[index].slug=linkRows[index].original}else{linkRows[index].slug=cleaned;input.value=cleaned}renderLinkDialog()}});
  body.querySelectorAll('[data-regenerate]').forEach(button=>{button.onclick=()=>{const index=Number(button.dataset.regenerate);const taken=new Set(linkRows.filter((_,position)=>position!==index).map(row=>row.slug));linkRows[index].slug=proposedSlug(linkRows[index].name,taken);renderLinkDialog()}});
  actions.innerHTML=`<button type="button" data-cancel>${_html('Close','បិទ')}</button><button type="button" data-regenerate-all>${_html('Regenerate all','បង្កើតឡើងវិញទាំងអស់')}</button><button type="button" class="ei-primary" data-freeze>${_html('Freeze and generate','ជួសជុល និងបង្កើត')}</button>`;
  actions.querySelector('[data-cancel]').onclick=closeLinkDialog;
  actions.querySelector('[data-regenerate-all]').onclick=()=>{const taken=new Set();linkRows.forEach(row=>{row.slug=proposedSlug(row.name,taken)});renderLinkDialog()};
  actions.querySelector('[data-freeze]').onclick=freezeLinks;
}
function slugPreview(row){return `/${slug}/${row.slug}${row.original&&row.slug!==row.original?`  ·  ${_txt('was','ពីមុន')} /${slug}/${row.original}`:''}`}
function openLinkEditor(list){
  if(!server)return;
  linkRows=(list&&list.length?list:guests).map(guest=>({id:guest.id,name:guest.name,slug:guest.slug||'',original:guest.slug||''})).filter(row=>row.id);
  ensureLinkDialog();renderLinkDialog();
  if(!linkDialog.open)linkDialog.showModal();
}
async function freezeLinks(){
  const changed=linkRows.filter(row=>row.slug&&row.slug!==row.original);
  const button=linkDialog?.querySelector('[data-freeze]');if(button)button.disabled=true;
  let payload;
  try{payload=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests/freeze`,{method:'POST',body:JSON.stringify({guests:changed.map(row=>({id:row.id,slug:row.slug}))})})}
  catch(error){if(button)button.disabled=false;alert(_txt(error.message||'Action failed','Action failed'));return}
  if(payload.conflicts&&payload.conflicts.length){if(button)button.disabled=false;linkDialog.querySelector('.ei-dialog-message').textContent=_txt(`These codes are already used in this invitation: ${payload.conflicts.join(', ')}`,'');return}
  guests=await request(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);
  closeLinkDialog();render();
  const summary=`${payload.updated} ${_txt('link(s) frozen','តំណត្រូវបានជួសជុល')}`;
  if(window.EInviteFeedback?.toast)window.EInviteFeedback.toast(summary);else alert(summary);
}
$('#linksBtn').onclick=()=>openLinkEditor(guests);
$('#selectAllGuests')?.addEventListener('change',event=>{pickedGuests.clear();if(event.currentTarget.checked)guests.forEach(guest=>pickedGuests.add(guest.id));render()});
$('#copyLinksBtn')?.addEventListener('click',copyGuestLinks);
if(window.EInviteI18n&&typeof window.EInviteI18n.subscribe==='function'){window.EInviteI18n.subscribe(render)};
load();;(function(){
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
})();;/**
 * ui/app-shell.js — V55 application shell behaviour (dispatch §2).
 *
 * Deliberately tiny and dependency-free. It owns exactly three things:
 *
 *   1. Rail collapse  — [data-rail-toggle] toggles `body.rail-collapsed`
 *      (persisted in localStorage['einvite-rail-collapsed']).
 *   2. Rail drawer    — below 768px the rail becomes a drawer; [data-drawer-toggle]
 *      toggles `body.rail-open`, which is also closed on Escape, on an outside
 *      click, and on hashchange.
 *   3. Appearance     — [data-theme-toggle] cycles light/dark using the SAME
 *      storage key as core/theme.js (`einvite-theme-mode`), so pages that do not
 *      load modern-ui.js (public.html, checkin.html) still get a working toggle.
 *
 * Accessibility: the toggle buttons carry aria-expanded and the rail is a
 * landmark; nothing here traps focus or blocks pointer events when closed.
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
      var glyph = btn.querySelector('[data-rail-glyph]');
      if (glyph) glyph.textContent = collapsed ? '»' : '«';
    });
  }
  function applyRailOpen(open) {
    body.classList.toggle('rail-open', !!open);
    document.querySelectorAll('[data-drawer-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!!open));
    });
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
      var glyph = btn.querySelector('[data-theme-glyph]');
      if (glyph) glyph.textContent = next === 'dark' ? '☾' : '☀';
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
})();