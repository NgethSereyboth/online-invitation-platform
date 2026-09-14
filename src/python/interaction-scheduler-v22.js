(()=>{'use strict';
if(window.EInviteInteractionScheduler?.version)return;
const frameTasks=new Map(),idleTasks=new Map();let raf=0,idle=0,paused=false,destroyed=false,sequence=0;const perf=()=>window.EInvitePerformance,lifecycle=window.EInviteLifecycle;
function eventSnapshot(event){return{pointerId:event.pointerId,clientX:event.clientX,clientY:event.clientY,button:event.button,buttons:event.buttons,pressure:event.pressure,pointerType:event.pointerType,shiftKey:event.shiftKey,altKey:event.altKey,ctrlKey:event.ctrlKey,metaKey:event.metaKey,timeStamp:event.timeStamp,target:event.target,currentTarget:event.currentTarget,preventDefault:()=>{},stopImmediatePropagation:()=>{}}}
function flushFrame(time){raf=0;if(paused||destroyed)return;const tasks=[...frameTasks.values()];frameTasks.clear();for(const task of tasks){const end=perf()?.begin('scheduledTask',{key:task.key});try{task.run(time)}finally{end?.()}}if(frameTasks.size)scheduleRaf()}
function scheduleRaf(){if(!raf&&!paused&&!destroyed)raf=requestAnimationFrame(flushFrame)}
function scheduleFrame(key,run,detail){if(typeof run!=='function')return 0;const id=++sequence;frameTasks.set(String(key),{id,key:String(key),run,detail});scheduleRaf();return id}
function pointer(event,run,key=`pointer:${event.pointerId||0}`){const token=perf()?.pointerToken(event),snap=eventSnapshot(event);return scheduleFrame(key,()=>{run(snap);requestAnimationFrame(()=>perf()?.pointerPainted(token,{channel:key}))},{pointerId:snap.pointerId})}
function flushIdle(deadline){idle=0;if(paused||destroyed)return;const started=performance.now();for(const [key,task] of [...idleTasks]){if(deadline&&!deadline.didTimeout&&deadline.timeRemaining()<2)break;idleTasks.delete(key);const end=perf()?.begin('idleTask',{key});try{task.run(deadline)}finally{end?.()}if(performance.now()-started>12)break}if(idleTasks.size)scheduleIdleLoop()}
function scheduleIdleLoop(){if(idle||paused||destroyed)return;idle='requestIdleCallback'in window?requestIdleCallback(flushIdle,{timeout:800}):setTimeout(()=>flushIdle({didTimeout:true,timeRemaining:()=>0}),48)}
function scheduleIdle(key,run){if(typeof run!=='function')return 0;const id=++sequence;idleTasks.set(String(key),{id,key:String(key),run});scheduleIdleLoop();return id}
function cancel(key){frameTasks.delete(String(key));idleTasks.delete(String(key))}
function flush(){if(raf){cancelAnimationFrame(raf);raf=0}flushFrame(performance.now())}
function pause(){paused=true;if(raf)cancelAnimationFrame(raf);raf=0;if(idle){if(typeof idle==='number')('cancelIdleCallback'in window?cancelIdleCallback(idle):clearTimeout(idle));idle=0}}
function resume(){paused=false;if(frameTasks.size)scheduleRaf();if(idleTasks.size)scheduleIdleLoop()}
function stats(){return{frameQueue:frameTasks.size,idleQueue:idleTasks.size,paused,destroyed,sequence}}
function onVisibility(){document.hidden?pause():resume()}
function destroy(){if(destroyed)return;destroyed=true;pause();frameTasks.clear();idleTasks.clear();document.removeEventListener('visibilitychange',onVisibility)}
document.addEventListener('visibilitychange',onVisibility);lifecycle?.add(destroy);
window.EInviteInteractionScheduler=Object.freeze({version:'22.1.1',scheduleFrame,pointer,scheduleIdle,cancel,flush,pause,resume,stats,destroy});
})();
