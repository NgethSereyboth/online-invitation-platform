/* src/js/crdt-yjs-undo.js — V54.7 Phase 4b
 *
 * Per-user Y.UndoManager with trackedOrigins scoping.
 *
 * Pitfall called out in ROADMAP §7.4b:
 *   "Per-user UndoManager with trackedOrigins scoping (so one user's undo
 *    doesn't overwrite another's)."
 *
 * V31 had no undo concept — every local edit just produced a new CRDT
 * update, and the editor's native document.execCommand('undo') would
 * revert the *editor DOM*, which then diffed against lastDocument and
 * produced *another* CRDT update. With multi-user sessions this routinely
 * reverted remote edits accidentally.
 *
 * Y.js solves this natively: Y.UndoManager observes a Y type (or a list of
 * types) and tracks every operation's `origin` (which is the `Transaction`
 * origin, conventionally set to the local client ID). Setting
 * trackedOrigins = new Set([localClientId]) means undo() will ONLY revert
 * operations originated by this client.
 *
 * Public API (window.EInviteCRDTV52Undo):
 *   create(ydoc, options) -> UndoManager
 *   undo() redo() canUndo() canRedo() clear()
 *
 * options:
 *   {
 *     clientId:    number           — Y.js client ID (defaults to ydoc.clientID)
 *     captureTimeout: number(ms)    — coalesce ops within this window (default 500ms)
 *     trackedTypes: Array<Y.AbstractType>  — defaults to [ydoc.get('root')]
 *     labels: { undo, redo, nothingToUndo, nothingToRedo }  — i18n overrides
 *   }
 *
 * Bilingual EN+KH UI strings surfaced via window.EInviteI18N.
 */
(()=>{
'use strict';
if(window.EInviteCRDTV52Undo)return;

const DEFAULT_CAPTURE_TIMEOUT_MS=500;

const STRINGS={
  en:{undo:'Undo',redo:'Redo',nothingToUndo:'Nothing to undo',nothingToRedo:'Nothing to redo',stackCleared:'Undo history cleared'},
  km:{undo:'មិនធ្វើវិញ',redo:'ធ្វើវិញ',nothingToUndo:'មិនមានអ្វីដែលត្រូវមិនធ្វើវិញ',nothingToRedo:'មិនមានអ្វីដែលត្រូវធ្វើវិញ',stackCleared:'បានជម្រះប្រវត្តិមិនធ្វើវិញ'}
};

function t(key){
  const lang=window.EInviteI18N?.getLocale?.()||document.documentElement.lang||'en';
  const table=String(lang).toLowerCase().startsWith('km')?STRINGS.km:STRINGS.en;
  return table[key]||STRINGS.en[key]||key;
}

function assertYjsLoaded(){
  const Y=window.Y;
  if(!Y||typeof Y.UndoManager!=='function'){
    throw new Error('Y.js library (window.Y) is not loaded — see vendor/yjs/README.md');
  }
  return Y;
}

class UndoManager{
  /**
   * @param {Y.Doc} ydoc
   * @param {object} [options]
   */
  constructor(ydoc,options={}){
    const Y=assertYjsLoaded();
    if(!ydoc||typeof ydoc.transact!=='function')throw new Error('a Y.Doc instance is required');
    this.ydoc=ydoc;
    this.clientId=options.clientId!=null?Number(options.clientId):(ydoc.clientID||ydoc.clientid||0);
    if(!this.clientId)throw new Error('clientId could not be determined — pass options.clientId');
    this.captureTimeout=Number(options.captureTimeout||DEFAULT_CAPTURE_TIMEOUT_MS);
    const trackedTypes=Array.isArray(options.trackedTypes)&&options.trackedTypes.length
      ?options.trackedTypes
      :[ydoc.get('root')];
    // trackedOrigins is the CRITICAL field — only ops with origin === this.clientId
    // are pushed onto the undo stack. Remote-originated ops (other clients) are
    // visible to the editor but NOT undoable by this client.
    const trackedOrigins=new Set([this.clientId]);
    this._manager=new Y.UndoManager(trackedTypes,{
      trackedOrigins,
      captureTimeout:this.captureTimeout
    });
    this._labels=options.labels||{};
    this._announceListeners=new Set();
    // Y.UndoManager emits 'stack-item-added' / 'stack-item-popped' / 'stack-cleared'.
    const emit=(kind)=>()=>this._announce(kind);
    this._manager.on('stack-item-added',emit('stack-item-added'));
    this._manager.on('stack-item-popped',emit('stack-item-popped'));
    this._manager.on('stack-cleared',emit('stack-cleared'));
  }
  /**
   * Undo the most recent local-origin operation.
   * If the stack is empty, surfaces a bilingual "Nothing to undo" message
   * via the announcement channel (does NOT throw — matches editor UX).
   * @returns {boolean} true if an op was undone, false if the stack was empty
   */
  undo(){
    if(!this.canUndo()){
      this._announce('empty-undo');
      return false;
    }
    try{this._manager.undo();return true}
    catch(error){this._announce('error',{message:String(error&&error.message||error)});return false}
  }
  redo(){
    if(!this.canRedo()){
      this._announce('empty-redo');
      return false;
    }
    try{this._manager.redo();return true}
    catch(error){this._announce('error',{message:String(error&&error.message||error)});return false}
  }
  canUndo(){return Boolean(this._manager&&this._manager.undoStack&&this._manager.undoStack.length>0)}
  canRedo(){return Boolean(this._manager&&this._manager.redoStack&&this._manager.redoStack.length>0)}
  /**
   * Clear both undo and redo stacks. Useful when the user joins a fresh
   * session or explicitly resets history (e.g. after a checkpoint).
   */
  clear(){
    if(!this._manager)return;
    try{this._manager.clear()}catch{}
    this._announce('cleared');
  }
  /**
   * Wrap a mutation in a transaction tagged with this client's origin.
   * This is how the editor tells UndoManager "this whole batch is one
   * undoable unit" — e.g. a paragraph delete + cursor move is one undo.
   */
  transact(fn){
    if(typeof fn!=='function')return;
    const Y=window.Y;
    this.ydoc.transact(fn,this.clientId);
  }
  /* Internal: bilingual announcements for screen readers + the editor chip. */
  onAnnounce(fn){if(typeof fn==='function')this._announceListeners.add(fn);return()=>this._announceListeners.delete(fn)}
  _announce(kind,extra={}){
    let message;
    if(kind==='empty-undo')message=t('nothingToUndo');
    else if(kind==='empty-redo')message=t('nothingToRedo');
    else if(kind==='cleared')message=t('stackCleared');
    else message='';
    const payload={kind,message,...extra,timestamp:Date.now()};
    for(const fn of this._announceListeners){try{fn(payload)}catch{}}
    // Also surface via the platform's editor event bus if available.
    try{window.dispatchEvent(new CustomEvent('einvite:crdt-v52-undo',{detail:payload}))}catch{}
  }
}

/** Convenience factory for the common case (single Y.Doc + root map). */
function create(ydoc,options={}){
  return new UndoManager(ydoc,options);
}

window.EInviteCRDTV52Undo=Object.freeze({create,UndoManager,STRINGS,DEFAULT_CAPTURE_TIMEOUT_MS});
})();
