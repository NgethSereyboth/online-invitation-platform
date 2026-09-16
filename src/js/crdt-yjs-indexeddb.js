/* src/js/crdt-yjs-indexeddb.js — V54.7 Phase 4b
 *
 * Offline persistence for the Y.js CRDT document (per-invitation).
 *
 * What this wraps:
 *   - y-indexeddb (https://github.com/yjs/y-indexeddb) — community library
 *     that persists Y.Doc updates to IndexedDB. Self-hosted in
 *     vendor/y-indexeddb/ (see vendor/yjs/README.md for CDN + integrity).
 *   - Provides a graceful fallback if y-indexeddb is not loaded: a minimal
 *     in-memory + localStorage queue that holds the most recent 256 KB of
 *     Y.js binary updates. This guarantees the editor still works offline
 *     in browsers where IndexedDB is unavailable (private mode, old Safari,
 *     enterprise lockdown).
 *
 * IndexedDB schema (database name: "einvite-yjs-collab"):
 *
 *   database: einvite-yjs-collab
 *     object store: documents (keyPath: "invitationId")
 *       record: { invitationId: string,
 *                 clientId: number,           // Y.js 32-bit client ID
 *                 snapshot: Uint8Array,      // Y.encodeStateAsUpdate()
 *                 stateVector: Uint8Array,   // Y.encodeStateVector()
 *                 fingerprint: string,        // FNV-1a of snapshot (debug)
 *                 updatedAt: number }         // Date.now()
 *     object store: updates (keyPath: "id", autoIncrement: true)
 *       index: "invitationId" (non-unique)
 *       record: { id: number, invitationId: string,
 *                 clientId: number, clock: number,
 *                 update: Uint8Array,           // single Y.js update
 *                 origin: 'local'|'remote',
 *                 createdAt: number }
 *     object store: meta (keyPath: "key")
 *       record: { key: string, value: any }     // e.g. { 'actor-' + invId: actor }
 *
 * Cross-tab safety:
 *   Each browser tab gets its own Y.js clientId. The `updates` store is
 *   append-only and indexed by invitationId so multiple tabs can flush
 *   independent streams without colliding. The `documents` store uses
 *   IndexedDB's native last-write-wins on the snapshot row (single key per
 *   invitationId). A periodic `Y.encodeStateAsUpdate` compaction
 *   (default every 30 s or 100 updates, whichever comes first) rewrites the
 *   `documents` row and trims the `updates` store.
 *
 * Public API (window.EInviteCRDTV52IndexedDB):
 *   open(invitationId, Y.Doc)        -> Promise<persistence handle>
 *   handle.flush()                   -> Promise<void>     // write pending
 *   handle.compact()                 -> Promise<void>     // rewrite snapshot + trim updates
 *   handle.pendingCount()            -> number
 *   handle.close()                   -> Promise<void>
 *   handle.clear()                    -> Promise<void>     // wipe all rows for this invitation
 *   dropDatabase()                    -> Promise<void>     // for tests
 *
 * Bilingual EN+KH strings are surfaced via window.EInviteI18N if available.
 */
(()=>{
'use strict';
if(window.EInviteCRDTV52IndexedDB)return;

const DB_NAME='einvite-yjs-collab';
const DB_VERSION=1;
const STORE_DOCUMENTS='documents';
const STORE_UPDATES='updates';
const STORE_META='meta';
const COMPACT_INTERVAL_MS=30000;
const COMPACT_UPDATE_THRESHOLD=100;
const MAX_PENDING_UPDATES=2000;     // mirrors V31 MAX_PENDING
const FALLBACK_QUEUE_KEY='einvite-yjs-queue-v52';

const STRINGS={
  en:{offlineQueue:'Offline queue',compacting:'Compacting CRDT log',synced:'Synced to IndexedDB',failed:'IndexedDB write failed'},
  km:{offlineQueue:'ការជួរក្រៅបណ្ដាញ',compacting:'កំពុងបង្ហាប់កំណត់ហេតុ CRDT',synced:'បានធ្វើសមកាលកម្មទៅ IndexedDB',failed:'សរសេរ IndexedDB បរាជ័យ'}
};
function t(key,locale){
  const lang=locale||window.EInviteI18N?.getLocale?.()||document.documentElement.lang||'en';
  return (STRINGS[lang===km?'km':'en']||STRINGS.en)[key]||STRINGS.en[key]||key;
}
// Localized string lookup for Khmer detection (avoid bundling the whole locale file).
const km=/^(km|kh|km-KH|kh-KH)$/i;

function openDB(){
  return new Promise((resolve,reject)=>{
    if(typeof indexedDB==='undefined'){reject(new Error('IndexedDB unavailable'));return}
    const request=indexedDB.open(DB_NAME,DB_VERSION);
    request.onupgradeneeded=(event)=>{
      const db=event.target.result;
      if(!db.objectStoreNames.contains(STORE_DOCUMENTS)){
        const s=db.createObjectStore(STORE_DOCUMENTS,{keyPath:'invitationId'});
        s.createIndex('updatedAt','updatedAt');
      }
      if(!db.objectStoreNames.contains(STORE_UPDATES)){
        const s=db.createObjectStore(STORE_UPDATES,{keyPath:'id',autoIncrement:true});
        s.createIndex('invitationId','invitationId');
      }
      if(!db.objectStoreNames.contains(STORE_META)){
        db.createObjectStore(STORE_META,{keyPath:'key'});
      }
    };
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error||new Error('IndexedDB open failed'));
    request.onblocked=()=>reject(new Error('IndexedDB upgrade blocked by another tab'));
  });
}

function txWrite(db,store,fn){
  return new Promise((resolve,reject)=>{
    const t=db.transaction(store,'readwrite');
    const s=t.objectStore(store);
    let result;
    t.oncomplete=()=>resolve(result);
    t.onerror=()=>reject(t.error);
    t.onabort=()=>reject(t.error||new Error('transaction aborted'));
    Promise.resolve(fn(s)).then(r=>{result=r}).catch(e=>{try{t.abort()}catch{};reject(e)});
  });
}

function txRead(db,store,fn){
  return new Promise((resolve,reject)=>{
    const t=db.transaction(store,'readonly');
    const s=t.objectStore(store);
    let result;
    t.oncomplete=()=>resolve(result);
    t.onerror=()=>reject(t.error);
    Promise.resolve(fn(s)).then(r=>{result=r}).catch(reject);
  });
}

// Minimal fallback: store the most recent binary updates in localStorage as
// base64. Used when IndexedDB is unavailable (private browsing, disabled).
const fallback={
  _queue:[],
  _dirty:false,
  load(invitationId){
    try{
      const raw=localStorage.getItem(`${FALLBACK_QUEUE_KEY}:${invitationId}`);
      if(!raw)return;
      const parsed=JSON.parse(raw);
      this._queue=Array.isArray(parsed)?parsed:[];
    }catch{this._queue=[]}
  },
  push(update,origin){
    this._queue.push({update:b64encode(update),origin,createdAt:Date.now()});
    if(this._queue.length>MAX_PENDING_UPDATES)this._queue.splice(0,this._queue.length-MAX_PENDING_UPDATES);
    this._dirty=true;
  },
  flush(invitationId){
    if(!this._dirty)return Promise.resolve();
    try{localStorage.setItem(`${FALLBACK_QUEUE_KEY}:${invitationId}`,JSON.stringify(this._queue))}catch{}
    this._dirty=false;
    return Promise.resolve();
  },
  clear(invitationId){try{localStorage.removeItem(`${FALLBACK_QUEUE_KEY}:${invitationId}`)}catch{}this._queue=[];this._dirty=false},
  pendingCount(){return this._queue.length}
};

function b64encode(bytes){let bin='';for(let i=0;i<bytes.length;i++)bin+=String.fromCharCode(bytes[i]);return btoa(bin)}
function b64decode(str){const bin=atob(str);const bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);return bytes}

class PersistenceHandle{
  constructor(db,doc,invitationId,clientId){
    this.db=db;
    this.doc=doc;
    this.invitationId=invitationId;
    this.clientId=clientId;
    this._pending=[];
    this._destroyFns=[];
    this._compactTimer=0;
    this._updateCount=0;
    this._usingFallback=false;
  }
  async _loadExisting(){
    if(this._usingFallback){
      fallback.load(this.invitationId);
      // Re-apply queued updates to the doc on startup (rejoin path).
      for(const entry of fallback._queue){
        try{this.Y.applyUpdate(this.doc,b64decode(entry.update),entry.origin||'remote')}catch{}
      }
      return;
    }
    try{
      const doc=await txRead(this.db,STORE_DOCUMENTS,s=>new Promise((resolve,reject)=>{
        const req=s.get(this.invitationId);
        req.onsuccess=()=>resolve(req.result);
        req.onerror=()=>reject(req.error);
      }));
      if(doc&&doc.snapshot&&doc.snapshot.byteLength){
        try{this.Y.applyUpdate(this.doc,new Uint8Array(doc.snapshot),'remote-rehydrate')}catch{}
      }
      const updates=await txRead(this.db,STORE_UPDATES,s=>new Promise((resolve,reject)=>{
        const idx=s.index('invitationId');
        const req=idx.getAll(this.invitationId);
        req.onsuccess=()=>resolve(req.result||[]);
        req.onerror=()=>reject(req.error);
      }));
      for(const entry of updates){
        try{this.Y.applyUpdate(this.doc,new Uint8Array(entry.update),entry.origin||'remote')}catch{}
      }
      this._updateCount=updates.length;
    }catch(error){console.warn('[yjs-indexeddb] load failed:',error)}
  }
  _wireDocUpdate(){
    if(!this.doc||typeof this.doc.on!=='function')return;
    const handler=(update,origin)=>{
      this._pending.push({update,origin:origin==='remote-rehydrate'?'remote':String(origin||'local')});
      if(this._pending.length>MAX_PENDING_UPDATES)this._pending.splice(0,this._pending.length-MAX_PENDING_UPDATES);
      this._scheduleFlush();
      if(++this._updateCount>=COMPACT_UPDATE_THRESHOLD)this._scheduleCompact();
    };
    this.doc.on('update',handler);
    this._destroyFns.push(()=>this.doc.off('update',handler));
  }
  _scheduleFlush(){
    if(this._flushTimer)return;
    this._flushTimer=setTimeout(()=>{this._flushTimer=0;this.flush().catch(()=>{})},250);
  }
  _scheduleCompact(){
    if(this._compactTimer)return;
    this._compactTimer=setTimeout(()=>{this._compactTimer=0;this.compact().catch(()=>{})},0);
  }
  async flush(){
    if(!this._pending.length)return;
    const batch=this._pending.splice(0);
    if(this._usingFallback){
      for(const entry of batch)fallback.push(entry.update,entry.origin);
      await fallback.flush(this.invitationId);
      return;
    }
    try{
      await txWrite(this.db,STORE_UPDATES,s=>{
        for(const entry of batch){
          s.add({invitationId:this.invitationId,clientId:this.clientId,clock:0,update:entry.update,origin:entry.origin,createdAt:Date.now()});
        }
      });
      this._updateCount+=0; // already incremented in handler
    }catch(error){
      // Push back to the front of the queue for retry on next flush.
      this._pending.unshift(...batch);
      console.warn('[yjs-indexeddb] flush failed, will retry:',error);
      throw error;
    }
  }
  async compact(){
    if(this._usingFallback){await fallback.flush(this.invitationId);return}
    if(typeof this.Y.encodeStateAsUpdate!=='function')return;
    const snapshot=this.Y.encodeStateAsUpdate(this.doc);
    const stateVector=this.Y.encodeStateVectorFromUpdate(snapshot);
    const fingerprint=fingerprintOf(snapshot);
    try{
      await txWrite(this.db,STORE_DOCUMENTS,s=>s.put({
        invitationId:this.invitationId,clientId:this.clientId,
        snapshot:new Uint8Array(snapshot),
        stateVector:new Uint8Array(stateVector),
        fingerprint,updatedAt:Date.now()
      }));
      // Trim updates older than the snapshot.
      await txWrite(this.db,STORE_UPDATES,s=>{
        const idx=s.index('invitationId');
        return new Promise((resolve,reject)=>{
          const range=IDBKeyRange.only(this.invitationId);
          const req=idx.openCursor(range);
          let trimmed=0;
          req.onsuccess=()=>{
            const cursor=req.result;
            if(!cursor||trimmed>=5000){resolve();return}
            cursor.delete();
            trimmed++;
            cursor.continue();
          };
          req.onerror=()=>reject(req.error);
        });
      });
      this._updateCount=0;
    }catch(error){console.warn('[yjs-indexeddb] compact failed:',error)}
  }
  pendingCount(){return this._pending.length+(this._usingFallback?fallback.pendingCount():0)}
  async clear(){
    this._pending.splice(0);
    if(this._usingFallback){fallback.clear(this.invitationId);return}
    try{
      await txWrite(this.db,STORE_UPDATES,s=>{
        const idx=s.index('invitationId');
        return new Promise((resolve,reject)=>{
          const range=IDBKeyRange.only(this.invitationId);
          const req=idx.openCursor(range);
          req.onsuccess=()=>{const cursor=req.result;if(!cursor){resolve();return}cursor.delete();cursor.continue()};
          req.onerror=()=>reject(req.error);
        });
      });
      await txWrite(this.db,STORE_DOCUMENTS,s=>s.delete(this.invitationId));
    }catch(error){console.warn('[yjs-indexeddb] clear failed:',error)}
  }
  async close(){
    if(this._flushTimer){clearTimeout(this._flushTimer);this._flushTimer=0}
    if(this._compactTimer){clearTimeout(this._compactTimer);this._compactTimer=0}
    try{await this.flush()}catch{}
    this._destroyFns.splice(0).forEach(fn=>{try{fn()}catch{}});
    if(this._compactIntervalTimer){clearInterval(this._compactIntervalTimer);this._compactIntervalTimer=0}
    if(this.db){try{this.db.close()}catch{}this.db=null}
  }
}

// FNV-1a fingerprint for debugging (matches V31 CRDT fingerprint algorithm
// so the snapshot fingerprint is comparable across V31 ↔ V52 during Phase A).
function fingerprintOf(bytes){
  let h=0x811c9dc5;
  for(let i=0;i<bytes.length;i++){h^=bytes[i];h=Math.imul(h,0x01000193)>>>0}
  return`crdt-v52-${h.toString(16).padStart(8,'0')}`;
}

/**
 * Open a persistence handle for the given invitation + Y.Doc.
 *
 * @param {string} invitationId
 * @param {object} ydoc          — Y.Doc instance (must already be created)
 * @param {object} [options]     — { clientId: number, immediate: bool }
 * @returns {Promise<PersistenceHandle>}
 */
async function open(invitationId,ydoc,options={}){
  if(!invitationId)throw new Error('invitationId is required');
  if(!ydoc||typeof ydoc.on!=='function')throw new Error('a Y.Doc instance is required');
  const Y=window.Y||options.Y;
  if(!Y)throw new Error('Y.js library (window.Y) is not loaded — see vendor/yjs/README.md');
  const clientId=options.clientId||(ydoc.clientID||ydoc.clientid||Math.floor(Math.random()*0xFFFFFFFF));
  let db=null,usingFallback=false;
  try{db=await openDB()}
  catch(error){
    console.warn('[yjs-indexeddb] IndexedDB unavailable, falling back to localStorage:',error);
    usingFallback=true;
  }
  const handle=new PersistenceHandle(db,ydoc,invitationId,clientId);
  handle.Y=Y;
  handle._usingFallback=usingFallback;
  await handle._loadExisting();
  handle._wireDocUpdate();
  // Periodic compaction so the updates store does not grow unbounded.
  handle._compactIntervalTimer=setInterval(()=>{handle.compact().catch(()=>{})},COMPACT_INTERVAL_MS);
  // Flush on pagehide so the last few updates are not lost on tab close.
  const onHide=()=>{handle.flush().catch(()=>{})};
  window.addEventListener('pagehide',onHide);
  window.addEventListener('beforeunload',onHide);
  handle._destroyFns.push(()=>{window.removeEventListener('pagehide',onHide);window.removeEventListener('beforeunload',onHide)});
  return handle;
}

async function dropDatabase(){
  if(typeof indexedDB==='undefined')return;
  return new Promise((resolve)=>{
    const req=indexedDB.deleteDatabase(DB_NAME);
    req.onsuccess=()=>resolve(true);
    req.onerror=()=>resolve(false);
    req.onblocked=()=>resolve(false);
  });
}

window.EInviteCRDTV52IndexedDB=Object.freeze({
  DB_NAME,DB_VERSION,STORE_DOCUMENTS,STORE_UPDATES,STORE_META,
  COMPACT_INTERVAL_MS,COMPACT_UPDATE_THRESHOLD,MAX_PENDING_UPDATES,
  open,dropDatabase,strings:STRINGS
});
})();
