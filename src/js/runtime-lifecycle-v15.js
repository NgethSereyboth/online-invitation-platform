(()=>{'use strict';
if(window.EInviteLifecycle)return;
const cleanups=new Set();let closed=false;
function add(fn){if(typeof fn!=='function')return()=>{};if(closed){try{fn()}catch{};return()=>{}}cleanups.add(fn);return()=>cleanups.delete(fn)}
function interval(fn,ms,...args){const id=setInterval(fn,ms,...args);add(()=>clearInterval(id));return id}
function timeout(fn,ms,...args){const id=setTimeout(()=>{cleanups.delete(cancel);fn(...args)},ms);const cancel=()=>clearTimeout(id);add(cancel);return id}
function observer(instance,target,options){instance.observe(target,options);add(()=>instance.disconnect());return instance}
function controller(){const value=new AbortController();add(()=>value.abort());return value}
function cleanup(){if(closed)return;closed=true;for(const fn of [...cleanups].reverse())try{fn()}catch{}cleanups.clear()}
add(()=>document.querySelectorAll('audio,video').forEach(media=>{try{media.pause()}catch{}}));
window.addEventListener('pagehide',event=>{if(!event.persisted)cleanup()});
window.addEventListener('beforeunload',cleanup,{once:true});
window.EInviteLifecycle={add,interval,timeout,observer,controller,cleanup,get closed(){return closed}};
})();
