(()=>{
'use strict';
let ready=false,promise=null;
function loadScript(src,marker){return new Promise((resolve,reject)=>{if(marker&&window[marker])return resolve(window[marker]);const existing=document.querySelector(`script[src="${src}"]`);if(existing){existing.addEventListener('load',()=>resolve(marker?window[marker]:true),{once:true});existing.addEventListener('error',()=>reject(Error(`${src} failed to load`)),{once:true});return}const s=document.createElement('script');s.src=src;s.dataset.v23ProfessionalWorkflow='1';s.onload=()=>resolve(marker?window[marker]:true);s.onerror=()=>reject(Error(`${src} failed to load`));document.head.append(s)})}
async function load(){if(window.EInviteProfessionalWorkflow&&window.EInviteNavigationHistory&&window.EInviteStyleHistory)return{workflow:window.EInviteProfessionalWorkflow,navigation:window.EInviteNavigationHistory,styleHistory:window.EInviteStyleHistory};if(promise)return promise;promise=(async()=>{await loadScript('professional-workflow-v23.js','EInviteProfessionalWorkflow');await loadScript('navigation-history-v23.js','EInviteNavigationHistory');await loadScript('style-history-v23.js','EInviteStyleHistory');return{workflow:window.EInviteProfessionalWorkflow,navigation:window.EInviteNavigationHistory,styleHistory:window.EInviteStyleHistory}})().catch(error=>{promise=null;throw error});return promise}
window.EInviteProfessionalWorkflowReady=load;
const schedule=()=>{if(ready)return;ready=true;(window.requestIdleCallback||((fn)=>setTimeout(fn,700)))(()=>load().catch(()=>0),{timeout:1600})};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
})();
