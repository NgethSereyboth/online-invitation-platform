/* src/js/collaboration-presence-v52.js — V54.7 Phase 4b
 *
 * Dedicated ephemeral presence channel — SEPARATE from content sync.
 *
 * Per ROADMAP §7.4b pitfalls:
 *   - "Separate cursor/presence channel from content sync. Cursor sync
 *      delayed by content sync is bad. Use a dedicated ephemeral channel."
 *   - "Presence heartbeat with grace period (5–10s) to prevent flicker.
 *      Reconnection triggers 'left' events for temporary hiccups."
 *
 * V31 baseline (src/js/collaboration-studio-v31.js):
 *   - Heartbeat every 5s via POST .../presence.
 *   - 45s server-side TTL.
 *   - 800ms content-sync short-poll (presence rides the same channel).
 *   - No grace period — any interruption immediately removes the avatar.
 *
 * V52 (this module):
 *   - Heartbeat every 3s (tighter than V31).
 *   - Grace period 7s (between the 5–10s ROADMAP window).
 *   - Dedicated channel: cursor updates do NOT queue behind content updates
 *     and are NOT persisted (purely ephemeral).
 *   - WebSocket if available (window.EInviteCollabWebSocket mini-service);
 *     falls back to short-poll at POST .../collaboration/v52/presence.
 *   - Idle detection: no pointer move for 30s → mode:'idle' + avatar dims.
 *   - Remote cursor overlay rendered on #v52RemoteCursors (separate DOM
 *     from #v31RemotePresence so both V31 and V52 studios can coexist
 *     during Phase A).
 *
 * Public API (window.EInviteCollaborationPresenceV52):
 *   join(invitationId, options) -> Promise<presence>
 *   presence.update(payload)              -> void  (throttled to 60Hz locally)
 *   presence.setCursor({x, y, pageId})    -> void
 *   presence.setSelection([elementId...])  -> void
 *   presence.setMode('editing'|'viewing'|'idle') -> void
 *   presence.leave()                       -> Promise<void>
 *   presence.on('join'|'leave'|'cursor'|'selection'|'mode', fn)
 *
 * Bilingual EN+KH strings for "joined"/"left"/"editing" labels.
 */
(()=>{
'use strict';
if(window.EInviteCollaborationPresenceV52)return;

const HEARTBEAT_INTERVAL_MS=3000;
const GRACE_PERIOD_MS=7000;
const IDLE_TIMEOUT_MS=30000;
const CURSOR_THROTTLE_MS=80;
const PRESENCE_TTL_S=10;          // server-side: 10s before auto-expire
const MAX_REMOTE_CURSORS=30;

const STRINGS={
  en:{joined:'joined',left:'left',editing:'editing',viewing:'viewing',idle:'idle',you:'You',collaborator:'Collaborator'},
  km:{joined:'បានចូលរួម',left:'បានចាកចេញ',editing:'កំពុងកែសម្រួល',viewing:'កំពុងមើល',idle:'ទំនេរ',you:'អ្នក',collaborator:'សហការី'}
};
function t(key){
  const lang=window.EInviteI18N?.getLocale?.()||document.documentElement.lang||'en';
  return (String(lang).toLowerCase().startsWith('km')?STRINGS.km:STRINGS.en)[key]||STRINGS.en[key]||key;
}
function actorColor(actor){
  // Stable hue per actor (matches V31 hash pattern at collaboration-studio-v31.js:27).
  let h=0;for(const ch of String(actor||''))h=(h*31+ch.charCodeAt(0))>>>0;
  return h%360;
}
function initials(value){
  return String(value).split(/\s+|@/).filter(Boolean).slice(0,2).map(x=>x[0]).join('').toUpperCase()||'?';
}

class PresenceChannel{
  constructor(invitationId,options={}){
    this.invitationId=String(invitationId||'');
    if(!this.invitationId)throw new Error('invitationId is required');
    this.actor=options.actor||window.EInviteCRDTV31?.actorId?.()||`actor-${Math.random().toString(36).slice(2,10)}`;
    this.name=options.name||window.EInviteContext?.getUserName?.()||'';
    this.color=options.color||`hsl(${actorColor(this.actor)},65%,55%)`;
    this.avatarUrl=options.avatarUrl||'';
    this.mode=options.mode||'editing';
    this.pageId=options.pageId||window.EInviteEditorBridge?.getActiveCanvasId?.()||'hero';
    this.selection=[];
    this.cursor=null;
    this._listeners={join:new Set(),leave:new Set(),cursor:new Set(),selection:new Set(),mode:new Set(),status:new Set()};
    this._remotePresence=new Map();           // actor -> {payload, lastSeen}
    this._heartbeatTimer=0;
    this._idleTimer=0;
    this._cursorThrottle=0;
    this._lastPointerAt=Date.now();
    this._disposed=false;
    this._socket=null;
    this._pollInFlight=false;
    this._pollTimer=0;
    this._csrf=options.csrf||window.EInviteCollaborationStudioV31?.csrf?.()||null;
  }
  async join(){
    this._wireIdle();
    this._wirePointer();
    // Try WebSocket first (mini-service, optional). On failure, fall back to poll.
    if(typeof WebSocket!=='undefined'&&window.EINVITE_PRESENCE_WS_ENDPOINT){
      try{await this._connectWebSocket();this._emit('status',{transport:'websocket',connected:true})}
      catch(error){console.warn('[presence-v52] WebSocket failed, falling back to poll:',error);this._startPoll()}
    }else{
      this._startPoll();
      this._emit('status',{transport:'poll',connected:true})
    }
    this._startHeartbeat();
    await this._sendHeartbeat();
    return this;
  }
  _wireIdle(){
    const onMove=()=>{this._lastPointerAt=Date.now();if(this.mode==='idle'){this.setMode('editing')}};
    document.addEventListener('pointermove',onMove,{passive:true});
    document.addEventListener('pointerdown',onMove,{passive:true});
    document.addEventListener('keydown',onMove,{passive:true});
    this._idleTimer=setInterval(()=>{
      if(Date.now()-this._lastPointerAt>IDLE_TIMEOUT_MS&&this.mode!=='idle'){this.setMode('idle')}
    },5000);
    this._cleanup=()=>{document.removeEventListener('pointermove',onMove);document.removeEventListener('pointerdown',onMove);document.removeEventListener('keydown',onMove)};
  }
  _wirePointer(){
    const onMove=(event)=>{
      if(this._disposed)return;
      const now=Date.now();
      if(now-this._cursorThrottle<CURSOR_THROTTLE_MS)return;
      this._cursorThrottle=now;
      const stage=document.getElementById('stage');
      const rect=stage?.getBoundingClientRect();
      if(!rect)return;
      const x=(event.clientX-rect.left)/rect.width;
      const y=(event.clientY-rect.top)/rect.height;
      if(x<0||x>1||y<0||y>1)return;
      this.setCursor({x,y,pageId:this.pageId});
    };
    document.addEventListener('pointermove',onMove,{passive:true});
    const cleanup=this._cleanup||(this._cleanup=()=>{});
    this._cleanup=()=>{cleanup();document.removeEventListener('pointermove',onMove)};
  }
  _startHeartbeat(){
    clearInterval(this._heartbeatTimer);
    this._heartbeatTimer=setInterval(()=>{this._sendHeartbeat().catch(()=>{})},HEARTBEAT_INTERVAL_MS);
    // Reap stale remote presence entries after grace period.
    setInterval(()=>this._reapStale(),GRACE_PERIOD_MS);
  }
  _startPoll(){
    const poll=async()=>{
      if(this._disposed||this._pollInFlight)return;
      this._pollInFlight=true;
      try{
        const response=await fetch(`/api/invitations/${encodeURIComponent(this.invitationId)}/collaboration/v52/presence`,{
          method:'GET',credentials:'same-origin',headers:{'Accept':'application/json'}
        });
        if(response.ok){
          const payload=await response.json();
          const list=Array.isArray(payload.presence)?payload.presence:[];
          this._mergeRemote(list);
        }
      }catch{}
      finally{this._pollInFlight=false}
      this._pollTimer=setTimeout(poll,HEARTBEAT_INTERVAL_MS);
    };
    poll();
  }
  async _connectWebSocket(){
    return new Promise((resolve,reject)=>{
      const url=`${window.EINVITE_PRESENCE_WS_ENDPOINT}/ws/collaboration/v52/${encodeURIComponent(this.invitationId)}`;
      const socket=new WebSocket(url);
      this._socket=socket;
      socket.onopen=()=>{
        socket.send(JSON.stringify({type:'join',actor:this.actor,name:this.name,color:this.color,avatarUrl:this.avatarUrl,mode:this.mode,pageId:this.pageId}));
        resolve();
      };
      socket.onmessage=(event)=>{
        try{
          const message=JSON.parse(event.data);
          if(message.type==='presence'){this._mergeRemote(message.presence||[])}
          else if(message.type==='join'){this._mergeRemote([{actor:message.actor,name:message.name,color:message.color,avatarUrl:message.avatarUrl,mode:message.mode,pageId:message.pageId,updatedAt:Date.now()}])}
          else if(message.type==='leave'){this._removeRemote(message.actor)}
          else if(message.type==='cursor'){this._mergeRemote([{actor:message.actor,cursor:message.cursor,updatedAt:Date.now()}])}
        }catch{}
      };
      socket.onerror=()=>reject(new Error('WebSocket error'));
      socket.onclose=()=>{if(!this._disposed){this._startPoll()}};
    });
  }
  async _sendHeartbeat(){
    if(this._disposed)return;
    const payload={
      actor:this.actor,name:this.name,color:this.color,avatarUrl:this.avatarUrl,
      mode:this.mode,pageId:this.pageId,selection:this.selection.slice(0,100),
      cursor:this.cursor,updatedAt:Date.now()
    };
    if(this._socket&&this._socket.readyState===WebSocket.OPEN){
      this._socket.send(JSON.stringify({type:'heartbeat',...payload}));
      return;
    }
    try{
      await fetch(`/api/invitations/${encodeURIComponent(this.invitationId)}/collaboration/v52/presence`,{
        method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json',...(this._csrf?{'X-CSRF-Token':this._csrf}:{})},
        body:JSON.stringify(payload)
      });
    }catch(error){/* network error — next heartbeat will retry */}
  }
  _mergeRemote(list){
    const now=Date.now();
    for(const item of list){
      if(!item||item.actor===this.actor)continue;
      const existing=this._remotePresence.get(item.actor);
      const merged={...(existing?.payload||{}),...item};
      this._remotePresence.set(item.actor,{payload:merged,lastSeen:now});
      if(!existing)this._emit('join',merged);
      if(item.cursor&&(!existing?.payload?.cursor||JSON.stringify(existing.payload.cursor)!==JSON.stringify(item.cursor))){
        this._emit('cursor',merged);
      }
      if(item.selection&&(!existing?.payload?.selection||JSON.stringify(existing.payload.selection)!==JSON.stringify(item.selection))){
        this._emit('selection',merged);
      }
      if(existing&&existing.payload.mode!==item.mode&&item.mode){
        this._emit('mode',merged);
      }
    }
  }
  _removeRemote(actor){
    const existing=this._remotePresence.get(actor);
    if(existing){
      this._remotePresence.delete(actor);
      this._emit('leave',existing.payload);
    }
  }
  _reapStale(){
    const now=Date.now();
    for(const [actor,entry] of this._remotePresence){
      if(now-entry.lastSeen>GRACE_PERIOD_MS){
        this._remotePresence.delete(actor);
        this._emit('leave',entry.payload);
      }
    }
  }
  /* Public mutators — all fire-and-forget; throttled locally. */
  setCursor(cursor){
    if(!cursor)return;
    this.cursor=cursor;
    this._scheduleBroadcast();
  }
  setSelection(ids){
    this.selection=Array.isArray(ids)?ids.filter(Boolean).slice(0,100):[];
    this._scheduleBroadcast();
  }
  setMode(mode){
    if(this.mode===mode)return;
    this.mode=mode;
    this._scheduleBroadcast();
    this._emit('mode',{actor:this.actor,mode});
  }
  update(payload){
    if(!payload)return;
    if(payload.name!=null)this.name=payload.name;
    if(payload.color!=null)this.color=payload.color;
    if(payload.avatarUrl!=null)this.avatarUrl=payload.avatarUrl;
    if(payload.pageId!=null)this.pageId=payload.pageId;
    this._scheduleBroadcast();
  }
  _scheduleBroadcast(){
    if(this._broadcastPending)return;
    this._broadcastPending=true;
    setTimeout(()=>{
      this._broadcastPending=false;
      this._sendHeartbeat().catch(()=>{});
    },CURSOR_THROTTLE_MS);
  }
  /* Listener registration. */
  on(event,fn){
    const set=this._listeners[event]||(this._listeners[event]=new Set());
    set.add(fn);
    return ()=>set.delete(fn);
  }
  _emit(event,payload){
    const set=this._listeners[event];
    if(!set)return;
    for(const fn of set){try{fn(payload)}catch{}}
  }
  /* Snapshot of current remote presence (for the UI to render). */
  list(){
    return Array.from(this._remotePresence.values()).map(entry=>entry.payload).slice(0,MAX_REMOTE_CURSORS);
  }
  async leave(){
    if(this._disposed)return;
    this._disposed=true;
    clearInterval(this._heartbeatTimer);
    clearInterval(this._idleTimer);
    clearTimeout(this._pollTimer);
    if(this._cleanup)this._cleanup();
    if(this._socket){
      try{this._socket.send(JSON.stringify({type:'leave',actor:this.actor}));this._socket.close()}catch{}
      this._socket=null;
    }else{
      // best-effort final leave ping over HTTP
      try{
        await fetch(`/api/invitations/${encodeURIComponent(this.invitationId)}/collaboration/v52/presence`,{
          method:'POST',credentials:'same-origin',
          headers:{'Content-Type':'application/json',...(this._csrf?{'X-CSRF-Token':this._csrf}:{})},
          body:JSON.stringify({actor:this.actor,mode:'left'})
        });
      }catch{}
    }
    this._remotePresence.clear();
  }
}

/** Render remote cursors + avatar chips into the DOM. */
function renderOverlay(channel){
  const overlay=document.getElementById('v52RemoteCursors')||(()=>{
    const node=document.createElement('div');
    node.id='v52RemoteCursors';
    node.className='v52-remote-cursors';
    node.setAttribute('aria-hidden','true');
    document.getElementById('stage')?.appendChild(node)||document.body.appendChild(node);
    return node;
  })();
  overlay.replaceChildren();
  for(const item of channel.list()){
    if(!item.cursor)continue;
    const cursor=document.createElement('div');
    cursor.className='v52-remote-cursor';
    cursor.style.left=`${Math.max(0,Math.min(1,item.cursor.x))*100}%`;
    cursor.style.top=`${Math.max(0,Math.min(1,item.cursor.y))*100}%`;
    cursor.style.setProperty('--collab-color',item.color||`hsl(${actorColor(item.actor)},65%,55%)`);
    const label=document.createElement('span');
    label.className='v52-remote-cursor-label';
    label.textContent=item.name||t('collaborator');
    cursor.append(label);
    overlay.append(cursor);
  }
}

/** Convenience factory — joins the channel and wires the overlay. */
async function join(invitationId,options={}){
  const channel=new PresenceChannel(invitationId,options);
  await channel.join();
  channel.on('cursor',()=>renderOverlay(channel));
  channel.on('join',()=>renderOverlay(channel));
  channel.on('leave',()=>renderOverlay(channel));
  window.EInviteLifecycle?.add?.(()=>{channel.leave()});
  return channel;
}

window.EInviteCollaborationPresenceV52=Object.freeze({
  HEARTBEAT_INTERVAL_MS,GRACE_PERIOD_MS,IDLE_TIMEOUT_MS,CURSOR_THROTTLE_MS,PRESENCE_TTL_S,MAX_REMOTE_CURSORS,
  PresenceChannel,join,renderOverlay,strings:STRINGS
});
})();
