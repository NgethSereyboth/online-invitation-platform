(()=>{'use strict';if(!document.querySelector('#stage'))return;
const $=s=>document.querySelector(s);let lastSeen=Number(window.serverInvite?.updatedAt||0),notified=0,timer=null,source=null;
const token=()=>localStorage.getItem('sovan-auth-token'),id=()=>window.serverInvite?.id||localStorage.getItem('sovan-active-invite');
async function api(){const r=await fetch(`/api/invitations/${id()}`,{headers:token()?{Authorization:`Bearer ${token()}`}:{}});if(!r.ok)throw Error();return r.json()}
function ensureChip(){let chip=$('#eiRemoteChangeChip');if(!chip){chip=document.createElement('button');chip.id='eiRemoteChangeChip';chip.type='button';chip.className='ei-remote-chip';chip.hidden=true;chip.innerHTML='<span>↻</span><strong>Remote changes available</strong>';document.body.append(chip);chip.onclick=async()=>{if(!(await uiConfirm('Reload the latest server version? Unsaved local changes may be replaced.',{title:'Sync remote changes',confirmText:'Reload latest'})))return;location.reload()}}return chip}
function receive(updated){updated=Number(updated||0);if(!updated)return;if(!lastSeen){lastSeen=updated;return}if(updated>lastSeen&&updated!==notified){notified=updated;const chip=ensureChip();chip.hidden=false;window.uiToast?.('This invitation changed in another session.','↻')}lastSeen=Math.max(lastSeen,updated)}
async function poll(){if(!id()||!token()||document.hidden)return;try{const invite=await api();receive(invite.updatedAt)}catch{}}
function startPolling(){if(timer)return;poll();timer=setInterval(poll,7000)}
function startSSE(){const invitation=id();if(!invitation||!token()||!window.EventSource)return startPolling();try{source=new EventSource(`/api/invitations/${encodeURIComponent(invitation)}/events`);source.addEventListener('invitation-update',event=>{try{receive(JSON.parse(event.data).updatedAt)}catch{}});source.onerror=()=>{source?.close();source=null;startPolling()}}catch{startPolling()}}
document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll()});ensureChip();startSSE();
})();
