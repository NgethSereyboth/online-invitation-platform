(()=>{
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
})();
