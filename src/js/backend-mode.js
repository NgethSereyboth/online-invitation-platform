(()=>{'use strict';
if(window.EInviteBackend)return;
const state={status:'checking',health:null,error:null};
const listeners=new Set();
const serverMarker=!!document.querySelector('meta[name="einvite-backend"][content="full"]');
const likelyStatic=!serverMarker;
function emit(){document.documentElement.dataset.backendMode=state.status;listeners.forEach(fn=>{try{fn(state)}catch{}});document.dispatchEvent(new CustomEvent('einvite:backend-mode',{detail:{...state}}))}
async function probe(){
 if(likelyStatic){state.status='offline';emit();return state}
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),1800);
 try{const r=await fetch('/api/health',{credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{Accept:'application/json'}});if(!r.ok)throw Error(`HTTP ${r.status}`);state.health=await r.json();state.status='online'}catch(error){state.error=error;state.status='offline'}finally{clearTimeout(timer);emit()}return state
}
const ready=probe();
function isAvailable(){return state.status==='online'}
function staticUrl(id,target='editor'){
 const map={editor:'index.html',guests:'guests.html',responses:'responses.html',analytics:'analytics.html',materials:'materials.html',checkin:'checkin.html'};
 const file=map[target]||'index.html';return id?`${file}?invitation=${encodeURIComponent(id)}`:file
}
function message(target,text='This feature requires the full application server.'){
 const host=typeof target==='string'?document.querySelector(target):target;
 const box=document.createElement('section');box.className='server-required-v14';box.setAttribute('role','status');box.innerHTML='<strong>Full server required</strong><p></p>';box.querySelector('p').textContent=text;
 if(host)host.replaceChildren(box);else document.body.append(box);return box
}
function disable(root=document){root.querySelectorAll('[data-server-only],button.server-only,a.server-only').forEach(el=>{el.setAttribute('aria-disabled','true');if('disabled'in el)el.disabled=true;el.title='This feature requires the full application server.'})}
/* Session probe — one cached /api/auth/me per load (inventory A1); lets modules tell
   "nobody signed in" from "server down" without a 401 (signed-out always 200 {"user":null}). */
let sessionPromise=null;
function session(){
 if(!sessionPromise){sessionPromise=ready.then(()=>{if(!isAvailable())return null;
  return fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
   .then(r=>r.ok?r.json():null).then(data=>(data&&data.user)||null).catch(()=>null)})}
 return sessionPromise}
function hasSession(){return session().then(Boolean)}
window.EInviteBackend={state,ready,isAvailable,staticUrl,message,disable,session,hasSession,onChange(fn){listeners.add(fn);return()=>listeners.delete(fn)}};

/* Signed-out request guard (inventory A1): the allowlist is measured (artifacts/probe_api_calls.mjs) —
   only /api/health and /api/auth/me answer 200 signed out; guest-reachable writes and /api/auth/* stay
   open. Offline never blocks, and login/logout invalidates the cached probe. */
var SIGNED_OUT_ALLOWED=[
 /^\/api\/health$/,
 /^\/api\/auth\//,
 /^\/api\/public\//,
 /^\/api\/guest\//,
 /^\/api\/invitations\/[^/]+\/(rsvp[^/]*|polls\/[^/]+\/vote|signup-sheets\/[^/]+\/claim)$/
];
var SESSION_CHANGES=/^\/api\/auth\/(login|logout|logout-all|register|verify|reset|reset-confirm|password)$/;

/* demo-wedding / local-.* ids have no server counterpart (app.js, dashboard.js, guests.js,
   responses.js, navigation-history.js); the shell answers them 404 locally instead of 8 console
   errors per load. */
var LOCAL_ID=/^(demo-|local-)/;
function refsLocalId(url){
 var m=/^\/api\/invitations\/([^/]+)/.exec(url.pathname);
 if(m&&LOCAL_ID.test(decodeURIComponent(m[1])))return true;
 var q=url.searchParams.get('invitationId');
 return !!(q&&LOCAL_ID.test(q))
}
var nativeFetch=window.fetch?window.fetch.bind(window):null;
if(nativeFetch){
 window.fetch=function(input,init){
  var raw=typeof input==='string'?input:(input&&input.url)||'',url=null;
  try{url=new URL(raw,location.href)}catch(e){return nativeFetch(input,init)}
  if(url.origin!==location.origin||url.pathname.indexOf('/api/')!==0)return nativeFetch(input,init);
  var path=url.pathname;
  if(refsLocalId(url)){
   return Promise.resolve(new Response(JSON.stringify({error:'This invitation exists only in the browser (local demo data), so the server has no record of it.',code:'local-invitation-id'}),{status:404,statusText:'Not Found',headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}))
  }
  if(SIGNED_OUT_ALLOWED.some(function(p){return p.test(path)})){
   var call=nativeFetch(input,init);
   if(SESSION_CHANGES.test(path))call.then(function(){sessionPromise=null}).catch(function(){});
   return call
  }
  return session().then(function(user){
   if(user||!isAvailable())return nativeFetch(input,init);
   return new Response(JSON.stringify({error:'Authentication required',code:'unauthenticated'}),{status:401,statusText:'Unauthorized',headers:{'Content-Type':'application/json','Cache-Control':'no-store'}})
  })
 }
}
})();

/* Pre-paint language bootstrap (same block core/theme.js runs on the other routes; public.html
   does not load theme.js — measured in the km topbar-active review). Idempotent. */
(function(){try{var el=document.documentElement,lang=localStorage.getItem('einvite-lang');
if(!lang){var nav=navigator.language||(navigator.languages&&navigator.languages[0])||'';lang=nav.toLowerCase().indexOf('km')===0?'km':'en'}
el.lang=lang}catch(e){}})();
