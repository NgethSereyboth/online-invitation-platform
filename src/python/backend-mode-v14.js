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
window.EInviteBackend={state,ready,isAvailable,staticUrl,message,disable,onChange(fn){listeners.add(fn);return()=>listeners.delete(fn)}};
})();
