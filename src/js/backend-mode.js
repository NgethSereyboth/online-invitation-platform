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
/* Session probe — one cached `/api/auth/me` per page load. Signed out the server answers
   `200 {"user":null}` (verified with curl), so this never adds a failed request; it lets the
   studio/review/collaboration modules tell "nobody is signed in" from "server is down" and
   skip their auth-gated fetches instead of firing them into a 401 (inventory A1). */
let sessionPromise=null;
function session(){
 if(!sessionPromise){sessionPromise=ready.then(()=>{if(!isAvailable())return null;
  return fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}})
   .then(r=>r.ok?r.json():null).then(data=>(data&&data.user)||null).catch(()=>null)})}
 return sessionPromise}
function hasSession(){return session().then(Boolean)}
window.EInviteBackend={state,ready,isAvailable,staticUrl,message,disable,session,hasSession,onChange(fn){listeners.add(fn);return()=>listeners.delete(fn)}};

/* --- Signed-out request guard (inventory A1) --------------------------------
 * A signed-out load used to fire every page's session-only fetches straight at the server and get
 * 401/404 for each one: 37 failing requests across the 16 routes, one browser console error apiece
 * (docs/reviews/console-baseline.txt). Nothing about that is recoverable client-side, so the shell
 * stops sending them and answers with the same 401 JSON body the server would have sent.
 *
 * The allowlist is measured, not guessed — artifacts/probe_api_calls.mjs records every /api request
 * a signed-out load makes: the only paths that answer 200 are /api/health and /api/auth/me. The
 * guest-reachable writes (RSVP, poll vote, signup claim, public/guest APIs) are allowlisted too so a
 * guest page never loses a capability, and /api/auth/* stays open so signing in still works.
 *
 * Two deliberate properties: nothing is blocked while the backend is offline (the existing
 * "full server required" paths must keep their own messaging), and a successful sign-in or sign-out
 * invalidates the cached probe so the very next gated call re-reads the session. */
var SIGNED_OUT_ALLOWED=[
 /^\/api\/health$/,
 /^\/api\/auth\//,
 /^\/api\/public\//,
 /^\/api\/guest\//,
 /^\/api\/invitations\/[^/]+\/(rsvp[^/]*|polls\/[^/]+\/vote|signup-sheets\/[^/]+\/claim)$/
];
var SESSION_CHANGES=/^\/api\/auth\/(login|logout|logout-all|register|verify|reset|reset-confirm|password)$/;

/* Local/demo invitation ids have no server counterpart. `demo-wedding` is the app's own
 * "no invitation selected" fallback (src/js/app.js, dashboard.js, guests.js, responses.js,
 * navigation-history.js) and `local-draft` is the editor's unsaved draft. A signed-in editor
 * was still asking the server for /api/invitations/demo-wedding, /comments, /approvals,
 * /review-context, /studio-release and the four /api/studio/*?invitationId=demo-wedding routes —
 * eight 404s and eight console errors per load (the editor was already open on a real invitation,
 * 08dfadb8…/bfa1dcdd…). The shell answers them locally with the same 404 the server would send, so
 * each module takes the fallback path it already has instead of putting an error in the console. */
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


/* Pre-paint language bootstrap — the same block core/theme.js runs on the other 15 routes.
   public.html does not load theme.js, so without it the guest page could only correct
   `html.lang` after the route bundle had parsed (measured: with `einvite-lang=km` stored, the
   page rendered English while the Khmer topbar button showed as active). Idempotent: it sets the
   same value theme.js would. */
(function(){try{var el=document.documentElement,lang=localStorage.getItem('einvite-lang');
if(!lang){var nav=navigator.language||(navigator.languages&&navigator.languages[0])||'';lang=nav.toLowerCase().indexOf('km')===0?'km':'en'}
el.lang=lang}catch(e){}})();
