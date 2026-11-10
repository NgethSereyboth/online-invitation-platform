;(() => {
  'use strict';







  if (window.EInviteDeferredRouteLoaderV15) return;


  let resolveReady;
  const ready = new Promise((res) => { resolveReady = res; });
  window.EInviteDeferredRouteLoaderV15 = { version: '15', ready };
  const current = document.currentScript;
  const src = (current && current.src) || '';


  const match = /bundle-([A-Za-z0-9_-]+?)(?:-deferred)?\.js/.exec(src);
  if (!match) { resolveReady(); return; }
  const prefix = src.slice(0, src.lastIndexOf('/') + 1);
  const stem = match[1];
  let started = false;
  function start() {
    if (started) return;
    started = true;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = `${prefix}bundle-${stem}-deferred.css`;
    document.head.appendChild(link);
    const script = document.createElement('script');
    script.src = `${prefix}bundle-${stem}-deferred.js`;
    script.addEventListener('load', () => resolveReady(), { once: true });
    script.addEventListener('error', () => resolveReady(), { once: true });
    document.head.appendChild(script);
  }
  const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 1));
  idle(start, { timeout: 2000 });
  for (const type of ['pointerdown', 'keydown', 'touchstart']) {
    window.addEventListener(type, start, { once: true, passive: true, capture: true });
  }
})();;
























(function (global) {
  "use strict";


  if (global.EInviteI18n && global.EInviteI18N && global.EInviteI18N.version) return;
  if (global.EInviteI18n && global.EInviteI18n.version >= 1) return;

  var doc = global.document;
  var STORAGE_KEY = "einvite-lang";


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



    return persistedLang() || htmlLang();
  }


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






    syncSwitch(null, lang);
  }





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


  function escHTML(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }




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



      if (h.closest("dialog, [role='dialog'], .studio-design-check, .ui-app-launcher-menu, .canvas-header-more-menu, .studio-command-dialog")) {
        var stray = h.querySelector(".language-switch");
        if (stray && stray.parentNode) stray.parentNode.removeChild(stray);
        continue;
      }
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
    applyOptions();
  }

  function applyOptions() { try { EInviteI18n.applyOptionLabels(); } catch (e) { /* keep going */ } }


  var EInviteI18n = {
    version: "1.0",
    STORAGE_KEY: STORAGE_KEY,
    get: get,
    getLocale: get, // backward-compat: EInviteI18N?.getLocale()
    set: function (lang) {
      lang = lang === "km" ? "km" : lang === "en" ? "en" : navigatorLang();


      if (get() === lang) { applyHtmlLang(lang); applyFormFields(); applyOptions(); return lang; }
      emit(lang);
      applyFormFields();
      applyOptions();
      return lang;
    },


    t: function (key, strings, params) {
      var lang = get();
      var dict = (strings && (strings[lang] || strings.en)) || {};
      var s = dict[key];
      if ((s === undefined || s === null) && strings && strings.en) s = strings.en[key];
      if (s === undefined || s === null) s = key;


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


  global.EInviteI18N = {
    version: "1.0",
    getLocale: get,
    set: EInviteI18n.set,
    t: EInviteI18n.t,
  };




  try {
    doc.addEventListener("einvite:lang-changed", boot);
  } catch (e) { /* noop */ }


  var initLang = persistedLang() || navigatorLang();
  applyHtmlLang(initLang);
  applyFormFields();
  if (doc && doc.addEventListener) {
    doc.addEventListener("DOMContentLoaded", boot);


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
  const reference=String(options.reference||'').replace(/[^A-Za-z0-9._:-]/g,'').slice(0,80);
  item.querySelector('.ei-toast-icon').textContent=icon;item.querySelector('strong').textContent=reference?`${text} · Reference: ${reference}`:text;
  const close=()=>{if(item.classList.contains('out'))return;item.classList.add('out');setTimeout(()=>item.remove(),190)};item.querySelector('button').onclick=close;stack.append(item);setTimeout(close,Math.max(1500,Number(options.duration||3600)));return item
}
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false,selectOptions=null}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label></label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');


  const shortLabel=input&&message&&message.length<=80&&/:\s*$/.test(message)?message.replace(/:\s*$/,''):input?(selectOptions&&selectOptions.length?'Choose one':''):'';
  const messageNode=dialog.querySelector('.ei-dialog-message');messageNode.textContent=shortLabel?'':message;
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input'),label=host.querySelector('label');host.hidden=false;const fieldLabel=shortLabel||(selectOptions&&selectOptions.length?'Choose one':'Value');label.textContent=fieldLabel;if(selectOptions&&selectOptions.length){field=document.createElement('select');selectOptions.forEach(({value:v,label:l})=>{const o=document.createElement('option');o.value=v;o.textContent=l;field.append(o)});field.value=value;host.append(field)}else{field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';field.setAttribute('aria-label',fieldLabel);host.append(field)}}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel',selectOptions:Array.isArray(options.selectOptions)?options.selectOptions:null});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};






window.EInvitePosterUnits=Object.freeze({
 PX_PER:{in:96,cm:96/2.54,ft:1152},
 parse(value){
  const s=String(value||'').toLowerCase().replace(/×|,|\]/g,'x');
  const m=/(\d+(?:\.\d+)?)\s*(in|inch|inches|"|cm|centimeters?|ft|feet|')?\s*x\s*(\d+(?:\.\d+)?)\s*(in|inch|inches|"|cm|centimeters?|ft|feet|')?/.exec(s);
  if(!m)return null;

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
})();;(()=>{'use strict';
const $=s=>document.querySelector(s),inviteId=window.EInviteContext?.getInvitationId({allowRemembered:false})||window.EInviteContext?.getInvitationId()||'',queueKey=`einvite-checkin-queue:${inviteId}`;let guests=[],invitation=null,stream=null,scanTimer=null;
const api=async(path,options={})=>{const r=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...(options.headers||{})}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const _isKm=()=>(window.EInviteI18n&&window.EInviteI18n.get?window.EInviteI18n.get():(document.documentElement.lang||'').toLowerCase()).startsWith('km');
const _txt=(en,km)=>_isKm()?(km!=null?km:en):en;
const _html=(en,km)=>{const isKm=_isKm();const v=isKm?(km!=null?km:en):en;return`<span class="i18n i18n-en">${esc(en)}</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km!=null?km:en)}</span>`};
const _eventName=name=>{const label=name||'Guest check-in',host=$('#eventName');if(!host)return;host.replaceChildren();const en=document.createElement('span');en.className='i18n i18n-en';en.textContent=label;const km=document.createElement('span');km.className='i18n i18n-km khmer-text';km.lang='km';km.textContent=label;host.append(en,km)};
const queue=()=>{try{return JSON.parse(localStorage.getItem(queueKey)||'[]')}catch{return[]}},saveQueue=q=>localStorage.setItem(queueKey,JSON.stringify(q));
function setNetwork(){const online=navigator.onLine;$('#networkState').textContent=online?_txt('Online','លើបណ្ដាញ'):_txt('Offline','ក្រៅបណ្ដាញ');$('#networkState').classList.toggle('offline',!online);renderQueue()}
function renderQueue(){const q=queue(),el=$('#pendingQueue');el.hidden=!q.length;const en=`${q.length} ${q.length===1?'check-in change':'check-in changes'} waiting to sync when the connection returns.`;el.innerHTML=q.length?`<span class="i18n i18n-en">${en}</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">${en}</span>`:''}
function render(){const q=$('#guestSearch').value.trim().toLowerCase(),filtered=guests.filter(g=>`${g.name} ${g.phone||''} ${g.group_name||''} ${g.table_name||''}`.toLowerCase().includes(q)),checked=guests.filter(g=>g.checked_in).length;$('#checkinSummary').innerHTML=`${checked} of ${guests.length} <span class="i18n i18n-en">guests checked in</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">guests checked in</span>`;$('#checkinStats').innerHTML=`<span class="checkin-stat"><strong>${checked}</strong> <span class="i18n i18n-en">in</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">in</span></span><span class="checkin-stat"><strong>${guests.length-checked}</strong> <span class="i18n i18n-en">remaining</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">remaining</span></span>`;$('#checkinList').innerHTML=filtered.map(g=>`<article class="checkin-person ${g.checked_in?'checked':''}" data-guest-id="${esc(g.id)}"><div><strong>${esc(g.name)}</strong><small>${[g.group_name,g.table_name&&`${_txt('Table','តុ')} ${g.table_name}`,g.seat_label&&`${_txt('Seat','អាសនៈ')} ${g.seat_label}`,g.phone].filter(Boolean).map(esc).join(' · ')}</small></div><button data-check-id="${esc(g.id)}" class="${g.checked_in?'':'primary'}">${g.checked_in?_txt('Undo check-in','ធ្វើវិញការឆែកចូល'):_txt('Check in','ឆែកចូល')}</button></article>`).join('')||'<p class="empty-state"><span class="i18n i18n-en">No matching guests.</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">No matching guests.</span></p>';document.querySelectorAll('[data-check-id]').forEach(b=>b.onclick=()=>toggle(b.dataset.checkId))}
function seedGuests(){const rows=[['Sokha Chann','012 345 678','Family','Table 1',true],['Dara Meas','098 765 432','Family','Table 1',false],['Bopha Sok','011 222 333','Friends','Table 2',false],['Vibol Pen','016 888 999','Friends','Table 2',false],['Chenda Long','070 444 555','Colleagues','Table 3',false],['Rithy Nou','081 777 111','Colleagues','Table 3',false]];return rows.map((r,i)=>({id:`demo-guest-${i+1}`,name:r[0],phone:r[1],group_name:r[2],table_name:r[3],checked_in:r[4],checked_in_at:null,token:'demo'}))}
async function load(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable()){invitation={document:{fields:{names:'Sokha & Dara — Wedding'}}};guests=seedGuests();_eventName(invitation.document.fields.names);$('#backToGuests').href=window.EInviteContext.route(inviteId,'guests');render();$('#scanQrBtn').disabled=true;return}if(!inviteId){$('#eventName').textContent='Guest check-in';$('#checkinSummary').textContent='No invitation selected';$('#checkinList').innerHTML='<p class="empty-state">Open an invitation\'s guest list to check guests in.</p>';$('#backToGuests').href='dashboard.html';$('#scanQrBtn').disabled=true;return}try{invitation=await api(`/api/invitations/${encodeURIComponent(inviteId)}`);guests=await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);_eventName(invitation.document?.fields?.names||'Guest check-in');$('#backToGuests').href=window.EInviteContext.route(inviteId,'guests');render();await flushQueue()}catch(e){$('#checkinList').innerHTML=`<p><span class="i18n i18n-en">Could not load this guest list: </span><span class="i18n i18n-km khmer-text" lang="km" lang="km">Could not load this guest list: </span>${esc(e.message)}</p>`}}
async function toggle(id,explicit){const g=guests.find(x=>x.id===id);if(!g)return;const checked=explicit??!g.checked_in;g.checked_in=checked;g.checked_in_at=checked?Date.now():null;render();if(!navigator.onLine){const q=queue().filter(x=>x.guestId!==id);q.push({guestId:id,checkedIn:checked,createdAt:Date.now()});saveQueue(q);renderQueue();return}try{const result=await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(id)}/check-in`,{method:'PUT',body:JSON.stringify({checkedIn:checked})});if(result.alreadyCheckedIn){const notice=$('#checkinNotice');notice.textContent=`${g.name} ${_txt('was already checked in.','បានឆែកចូលរួចរាល់ហើយ។')}`;setTimeout(()=>{if(notice.textContent.includes(g.name))notice.textContent=''},3500)}}catch(e){const q=queue().filter(x=>x.guestId!==id);q.push({guestId:id,checkedIn:checked,createdAt:Date.now()});saveQueue(q);renderQueue()}}
async function flushQueue(){if(!navigator.onLine)return;let q=queue(),remaining=[];for(const item of q){try{await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests/${encodeURIComponent(item.guestId)}/check-in`,{method:'PUT',body:JSON.stringify({checkedIn:item.checkedIn})})}catch{remaining.push(item)}}saveQueue(remaining);renderQueue();if(q.length&&!remaining.length){guests=await api(`/api/invitations/${encodeURIComponent(inviteId)}/guests`);render()}}
function guestFromScanned(value){let text=String(value||'');try{const u=new URL(text,location.origin),token=u.searchParams.get('g')||u.searchParams.get('guest');if(token)return guests.find(g=>g.token===token)}catch{}return guests.find(g=>g.id===text)}
async function openScanner(){if(!('BarcodeDetector'in window)||!navigator.mediaDevices?.getUserMedia){alert(_txt('Camera QR scanning is not supported in this browser. Use guest search instead.','ប៊្រោស៊ើរនេះមិនគាំទ្រការស្កេន QR តាមកាមេរ៉ាទេ។ សូមប្រើការស្វែងរកភ្ញៀវជំនួស។'));return}try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}});$('#scannerVideo').srcObject=stream;await $('#scannerVideo').play();$('#scannerDialog').showModal();const detector=new BarcodeDetector({formats:['qr_code']});const tick=async()=>{if(!stream)return;try{const codes=await detector.detect($('#scannerVideo'));if(codes[0]){const guest=guestFromScanned(codes[0].rawValue);if(guest){await toggle(guest.id,true);closeScanner();document.querySelector(`[data-guest-id="${CSS.escape(guest.id)}"]`)?.scrollIntoView({behavior:'smooth',block:'center'});return}$('#scannerStatus').innerHTML='<span class="i18n i18n-en">This QR code does not belong to a guest in this invitation.</span><span class="i18n i18n-km khmer-text" lang="km" lang="km">This QR code does not belong to a guest in this invitation.</span>'}}catch{}scanTimer=setTimeout(tick,260)};tick()}catch(e){alert(_txt('Camera could not be opened:','មិនអាចបើកកាមេរ៉ាបាន៖')+' '+e.message)}}
function closeScanner(){clearTimeout(scanTimer);scanTimer=null;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}$('#scannerVideo').srcObject=null;$('#scannerDialog').close()}
$('#guestSearch').oninput=render;$('#scanQrBtn').onclick=openScanner;$('#closeScanner').onclick=closeScanner;$('#scannerDialog').addEventListener('close',()=>{if(stream)closeScanner()});window.addEventListener('online',()=>{setNetwork();flushQueue()});window.addEventListener('offline',setNetwork);setNetwork();load();if('serviceWorker'in navigator)navigator.serviceWorker.register('/service-worker.js').catch(()=>{});
if(window.EInviteI18n&&typeof window.EInviteI18n.subscribe==='function'){window.EInviteI18n.subscribe(function(){setNetwork();render()})}
})();;







(function () {
  'use strict';
  if (window.EInviteShell && window.EInviteShell.version >= 55) return;

  var body = document.body;
  var html = document.documentElement;
  var RAIL_KEY = 'einvite-rail-collapsed';
  var THEME_KEY = 'einvite-theme-mode';

  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }


  function applyRailCollapsed(collapsed) {
    body.classList.toggle('rail-collapsed', !!collapsed);
    document.querySelectorAll('[data-rail-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!collapsed));
      var label = collapsed ? 'Expand navigation' : 'Collapse navigation';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);

      var glyph = btn.querySelector('[data-rail-glyph]');
      if (glyph && !glyph.firstElementChild) glyph.textContent = collapsed ? '»' : '«';
    });
  }



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


  function markCurrentPage() {
    var here = (location.pathname.split('/').pop() || 'dashboard.html').toLowerCase();
    document.querySelectorAll('.app-rail a[href]').forEach(function (link) {
      var target = link.getAttribute('href').split('#')[0].split('?')[0].toLowerCase();
      if (target && target === here) link.setAttribute('aria-current', 'page');
    });
  }






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


  function resolvedTheme() { return html.dataset.theme === 'dark' ? 'dark' : 'light'; }
  function applyTheme(next) {
    html.dataset.theme = next;
    html.dataset.themeMode = next;
    html.style.colorScheme = next;
    write(THEME_KEY, next);
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(next === 'dark'));
      btn.setAttribute('title', next === 'dark' ? 'Switch to light appearance' : 'Switch to dark appearance');


    });
  }


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













(() => {
  'use strict';
  if (document.body.classList.contains('guest')) return;


  const header = [...document.querySelectorAll('body > header, body > #app > header, body > .app > header')]
    .find((node) => !node.closest('dialog')) || null;
  if (!header) return;
  header.dataset.appShellWrap = '1';
  const NARROW = 600;


  const TIGHT = 400;


  const COMPACT = 360;
  const HEADER_PROPS = ['flexWrap', 'height', 'minHeight', 'overflow', 'rowGap'];
  const LEFT_PROPS = ['flex', 'maxWidth', 'maxHeight', 'minWidth', 'overflow'];
  const RIGHT_PROPS = ['order', 'flex', 'minWidth', 'height', 'maxHeight', 'alignItems', 'overflow'];
  const SWITCH_PROPS = ['flex', 'order', 'justifyContent', 'margin', 'background', 'border', 'boxShadow', 'padding', 'height', 'alignItems'];
  const clear = (node, props) => props.forEach((key) => { node.style[key] = ''; });
  function sync() {
    const narrow = window.innerWidth <= NARROW;
    const tight = window.innerWidth <= TIGHT;
    const compact = window.innerWidth <= COMPACT;
    const langSwitch = header.querySelector(':scope > .language-switch');
    const left = header.querySelector(':scope > .app-topbar-left');
    const right = header.querySelector(':scope > .app-topbar-right');
    if (!narrow) {
      clear(header, HEADER_PROPS);
      if (left) clear(left, LEFT_PROPS);
      if (right) clear(right, RIGHT_PROPS);
      if (langSwitch) clear(langSwitch, SWITCH_PROPS);
      header.style.removeProperty('--shell-topbar-pad');
      header.style.removeProperty('--shell-topbar-gap');
      return;
    }
    header.style.flexWrap = 'wrap';
    header.style.height = 'auto';
    header.style.minHeight = '56px';
    header.style.overflow = 'visible';
    header.style.rowGap = tight ? '0' : '4px';
    if (tight) {



      header.style.setProperty('--shell-topbar-pad', '0px 8px');
      header.style.setProperty('--shell-topbar-gap', '0px');



      if (left) {
        left.style.flex = compact ? '0 0 auto' : '1 1 50%';
        left.style.maxWidth = compact ? '44px' : '50%';
        left.style.maxHeight = '44px';
        left.style.minWidth = '0';
        left.style.overflow = 'hidden';
      }


      if (right && right.getBoundingClientRect().width > 0) {
        right.style.order = compact ? '0' : '20';
        right.style.flex = '0 1 auto';
        right.style.minWidth = '0';
      } else if (right) {
        clear(right, RIGHT_PROPS);
        right.style.order = '0';


        right.style.display = 'none';
      }
    } else {
      header.style.removeProperty('--shell-topbar-pad');
      header.style.removeProperty('--shell-topbar-gap');
      if (left) clear(left, LEFT_PROPS);
      if (right) { clear(right, RIGHT_PROPS); right.style.order = '0'; right.style.display = ''; }
    }
    if (langSwitch) {
      langSwitch.style.order = '20';
      langSwitch.style.justifyContent = 'flex-end';
      langSwitch.style.margin = '0';
      langSwitch.style.padding = '0';
      langSwitch.style.background = 'transparent';
      langSwitch.style.border = '0';
      langSwitch.style.boxShadow = 'none';
      langSwitch.style.flex = tight && !compact ? '0 0 auto' : '1 0 100%';
    }
  }
  sync();



  new MutationObserver(sync).observe(header, { childList: true });
  window.addEventListener('load', sync, { once: true });
  let timer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(timer);
    timer = setTimeout(sync, 120);
  });
})();