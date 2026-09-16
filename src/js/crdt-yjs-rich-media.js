/* src/js/crdt-yjs-rich-media.js — V54.7 Phase 4b
 *
 * Custom Y.js type for rich media (images, embeds, resize handles).
 *
 * Per ROADMAP §7.4b pitfall:
 *   "Rich media sync — images, embeds, resize handles. CRDT protocols don't
 *    handle natively."
 *
 * Design rules (see docs/collab/CRDT-DESIGN.md §6):
 *   1. Asset BYTES never enter the CRDT. Only the asset REFERENCE (V32
 *      object_key string) is stored. Bytes flow through ObjectStorage
 *      (platform_v32/storage.py) via the existing V32 signed-upload flow.
 *   2. Resize handles: stored as {x, y, width, height, rotation} in a
 *      nested Y.Map. Updates are CRDT-safe (register last-write-wins per
 *      field). Local drag throttles to 60Hz render + 10Hz CRDT replication
 *      so a continuous resize doesn't flood the channel.
 *   3. The "isDragging" flag is presence-channel data, NOT Y.js data —
 *      goes through collaboration-presence-v52.js so other users see the
 *      drag-in-progress avatar immediately, without waiting for content sync.
 *
 * Public API (window.EInviteCRDTV52RichMedia):
 *   createImage(parentArray, options)   -> Y.Map
 *   createEmbed(parentArray, options)   -> Y.Map
 *   startResize(elementMap, handleId)   -> resize controller
 *   controller.update(delta)            -> void  (throttled)
 *   controller.commit()                  -> void  (final write + clears drag flag)
 *   controller.cancel()                  -> void  (reverts to pre-drag transform)
 *   transformOf(elementMap)              -> {x, y, width, height, rotation}
 *   assertNoAssetBytes(ydoc)             -> void  (CI guard — throws if base64 found)
 *   migrateV31Element(v31Element)        -> Y.Map initializer  (Phase A migration)
 *
 * Bilingual EN+KH strings surfaced via window.EInviteI18N.
 */
(()=>{
'use strict';
if(window.EInviteCRDTV52RichMedia)return;

const Y_KEY_ID='id';
const Y_KEY_KIND='kind';
const Y_KEY_ASSET_ID='assetId';
const Y_KEY_MIME='mime';
const Y_KEY_TRANSFORM='transform';
const Y_KEY_CROP='crop';
const Y_KEY_PROVIDER='provider';
const Y_KEY_VIDEO_ID='videoId';

const DEFAULT_TRANSFORM={x:0,y:0,width:320,height:240,rotation:0};
const RESIZE_RENDER_HZ=60;             // local DOM render rate
const RESIZE_REPLICATE_HZ=10;          // CRDT replication rate (network)
const MAX_TRANSFORM=100000;           // sanity ceiling — blocks overflow attempts

const STRINGS={
  en:{image:'Image',embed:'Embed',resizing:'Resizing',cancelResize:'Cancel resize'},
  km:{image:'រូបភាព',embed:'ការបញ្ចេញសំឡេង',resizing:'កំពុងប្ដូរទំហំ',cancelResize:'បោះបង់ការប្ដូរទំហំ'}
};
function t(key){
  const lang=window.EInviteI18N?.getLocale?.()||document.documentElement.lang||'en';
  return (String(lang).toLowerCase().startsWith('km')?STRINGS.km:STRINGS.en)[key]||STRINGS.en[key]||key;
}
function assertY(Y){
  if(!Y||typeof Y.Map!=='function')throw new Error('Y.js library (window.Y) is not loaded — see vendor/yjs/README.md');
}
function clampNum(n,fallback=0){const v=Number(n);return Number.isFinite(v)?Math.max(-MAX_TRANSFORM,Math.min(MAX_TRANSFORM,v)):fallback}
function isStringAssetId(value){
  // V32 object keys are strings like 'invitations/<id>/assets/<uuid>.<ext>'.
  // Refuse anything that looks like a data: URL (base64 bytes).
  if(typeof value!=='string'||!value)return false;
  if(value.startsWith('data:'))return false;
  if(value.length>1024)return false;        // V32 keys are short
  return true;
}

/**
 * Create a transform Y.Map populated with x/y/width/height/rotation.
 * All values are clamped to sane bounds to prevent CRDT poison from a
 * malicious client (NaN, Infinity, or absurd magnitudes).
 */
function createTransform(Y,transform={}){
  const map=new Y.Map();
  map.set('x',clampNum(transform.x,DEFAULT_TRANSFORM.x));
  map.set('y',clampNum(transform.y,DEFAULT_TRANSFORM.y));
  map.set('width',clampNum(transform.width,DEFAULT_TRANSFORM.width));
  map.set('height',clampNum(transform.height,DEFAULT_TRANSFORM.height));
  map.set('rotation',clampNum(transform.rotation,DEFAULT_TRANSFORM.rotation));
  return map;
}
function createCrop(Y,crop={}){
  const map=new Y.Map();
  map.set('x',clampNum(crop.x,0));
  map.set('y',clampNum(crop.y,0));
  map.set('w',clampNum(crop.w||crop.width,1));
  map.set('h',clampNum(crop.h||crop.height,1));
  return map;
}

/** Create an image element and append it to a Y.Array<Y.Map>. */
function createImage(parentArray,options={}){
  const Y=window.Y;assertY(Y);
  if(!Array.isArray(parentArray)||(typeof parentArray.push!=='function'))throw new Error('parentArray must be a Y.Array');
  if(!isStringAssetId(options.assetId))throw new Error('assetId must be a non-data: URL string');
  const element=new Y.Map();
  element.set(Y_KEY_ID,String(options.id||`img-${Date.now()}-${Math.random().toString(36).slice(2,8)}`));
  element.set(Y_KEY_KIND,'image');
  element.set(Y_KEY_ASSET_ID,options.assetId);
  element.set(Y_KEY_MIME,String(options.mime||'image/png'));
  element.set(Y_KEY_TRANSFORM,createTransform(Y,options.transform));
  if(options.crop)element.set(Y_KEY_CROP,createCrop(Y,options.crop));
  parentArray.push([element]);
  return element;
}

/** Create an embed (YouTube, SoundCloud, etc.) element. */
function createEmbed(parentArray,options={}){
  const Y=window.Y;assertY(Y);
  if(!Array.isArray(parentArray))throw new Error('parentArray must be a Y.Array');
  const provider=String(options.provider||'').toLowerCase();
  if(!['youtube','soundcloud','vimeo','spotify','custom'].includes(provider)){
    throw new Error(`Unsupported embed provider: ${provider}`);
  }
  const element=new Y.Map();
  element.set(Y_KEY_ID,String(options.id||`embed-${Date.now()}-${Math.random().toString(36).slice(2,8)}`));
  element.set(Y_KEY_KIND,'embed');
  element.set(Y_KEY_PROVIDER,provider);
  element.set(Y_KEY_VIDEO_ID,String(options.videoId||options.videoID||'').slice(0,256));
  element.set(Y_KEY_TRANSFORM,createTransform(Y,options.transform));
  parentArray.push([element]);
  return element;
}

/**
 * Read the transform back as a plain JS object (snapshot).
 * Useful for the editor's local render path which does not want to deal
 * with Y.Map observers directly.
 */
function transformOf(elementMap){
  const transform=elementMap&&elementMap.get&&elementMap.get(Y_KEY_TRANSFORM);
  if(!transform)return{...DEFAULT_TRANSFORM};
  return{
    x:clampNum(transform.get('x'),DEFAULT_TRANSFORM.x),
    y:clampNum(transform.get('y'),DEFAULT_TRANSFORM.y),
    width:clampNum(transform.get('width'),DEFAULT_TRANSFORM.width),
    height:clampNum(transform.get('height'),DEFAULT_TRANSFORM.height),
    rotation:clampNum(transform.get('rotation'),DEFAULT_TRANSFORM.rotation)
  };
}

class ResizeController{
  /**
   * @param {Y.Map} elementMap       — the image/embed Y.Map being resized
   * @param {string} handleId         — which corner/edge ('nw','ne','sw','se','n','s','e','w')
   * @param {object} [options]         — { onLocalRender: fn(transform), origin }
   */
  constructor(elementMap,handleId,options={}){
    if(!elementMap||typeof elementMap.get!=='function')throw new Error('elementMap must be a Y.Map');
    this.element=elementMap;
    this.handle=String(handleId||'se');
    this.onLocalRender=typeof options.onLocalRender==='function'?options.onLocalRender:null;
    this.origin=String(options.origin||'local');
    this.Y=window.Y;assertY(this.Y);
    this._initial=transformOf(elementMap);
    this._pending={...this._initial};
    this._replicateTimer=0;
    this._renderTimer=0;
    this._cancelled=false;
    this._committed=false;
  }
  /**
   * Apply a delta to the local transform snapshot. Renders immediately to the
   * local DOM (60Hz throttle) but defers CRDT replication to 10Hz.
   */
  update(delta){
    if(this._committed||this._cancelled)return;
    // Apply delta to the local pending transform.
    if(delta&&typeof delta==='object'){
      if(delta.width!=null)this._pending.width=clampNum(this._pending.width+Number(delta.width),this._initial.width);
      if(delta.height!=null)this._pending.height=clampNum(this._pending.height+Number(delta.height),this._initial.height);
      if(delta.x!=null)this._pending.x=clampNum(this._pending.x+Number(delta.x),this._initial.x);
      if(delta.y!=null)this._pending.y=clampNum(this._pending.y+Number(delta.y),this._initial.y);
      if(delta.rotation!=null)this._pending.rotation=clampNum(this._pending.rotation+Number(delta.rotation),this._initial.rotation);
    }
    // Local render throttle (60Hz).
    if(!this._renderTimer){
      this._renderTimer=setTimeout(()=>{
        this._renderTimer=0;
        if(this.onLocalRender)this.onLocalRender({...this._pending});
      },1000/RESIZE_RENDER_HZ);
    }
    // CRDT replication throttle (10Hz).
    if(!this._replicateTimer){
      this._replicateTimer=setTimeout(()=>this._replicate(),1000/RESIZE_REPLICATE_HZ);
    }
  }
  _replicate(){
    this._replicateTimer=0;
    if(this._committed||this._cancelled)return;
    const transform=this.element.get(Y_KEY_TRANSFORM);
    if(!transform)return;
    // Apply each field individually so concurrent drags on different fields
    // can merge (last-write-wins per field — Y.Map register semantics).
    transform.set('x',this._pending.x);
    transform.set('y',this._pending.y);
    transform.set('width',this._pending.width);
    transform.set('height',this._pending.height);
    transform.set('rotation',this._pending.rotation);
  }
  /** Final commit on pointerup. Clears the is-dragging presence flag. */
  commit(){
    if(this._cancelled)return;
    this._committed=true;
    clearTimeout(this._renderTimer);clearTimeout(this._replicateTimer);
    this._replicate();
    // Notify the presence channel that the drag ended.
    try{window.dispatchEvent(new CustomEvent('einvite:crdt-v52-resize-end',{detail:{elementId:this.element.get(Y_KEY_ID),handle:this.handle}}))}catch{}
  }
  /** Revert to the pre-drag transform. */
  cancel(){
    this._cancelled=true;
    clearTimeout(this._renderTimer);clearTimeout(this._replicateTimer);
    const transform=this.element.get(Y_KEY_TRANSFORM);
    if(transform){
      transform.set('x',this._initial.x);
      transform.set('y',this._initial.y);
      transform.set('width',this._initial.width);
      transform.set('height',this._initial.height);
      transform.set('rotation',this._initial.rotation);
    }
    if(this.onLocalRender)this.onLocalRender({...this._initial});
    try{window.dispatchEvent(new CustomEvent('einvite:crdt-v52-resize-cancel',{detail:{elementId:this.element.get(Y_KEY_ID)}}))}catch{}
  }
}

function startResize(elementMap,handleId,options={}){
  return new ResizeController(elementMap,handleId,options);
}

/**
 * CI safety guard — walks the Y.Doc and asserts that no string field
 * looks like base64 image data. Throws if any is found.
 *
 * This catches the most common implementation mistake: an engineer wires the
 * image upload handler to store base64 in the CRDT instead of going through
 * ObjectStorage. The test suite (tests/v52_crdt_offline_merge_test.py)
 * calls this after every fixture setup.
 */
function assertNoAssetBytes(ydoc){
  if(!ydoc)return;
  const visited=new WeakSet();
  const scan=(value,depth=0)=>{
    if(depth>12||value==null)return;
    if(typeof value==='string'){
      // data: URLs are the smoking gun.
      if(value.startsWith('data:'))throw new Error(`CRDT contains asset bytes (data URL, len=${value.length}) — asset bytes must NOT enter the CRDT; use the V32 ObjectStorage flow.`);
      // Heuristic: very long strings inside an image element are suspicious.
      if(depth>2&&value.length>4096&&!/^[a-z0-9._\-/:]+$/i.test(value)){
        // Allow asset IDs (alphanumeric + path chars); reject long base64-like.
        if(/^[A-Za-z0-9+/=]{4000,}$/.test(value))throw new Error(`CRDT contains a long base64-like string (len=${value.length}) — asset bytes must NOT enter the CRDT.`);
      }
      return;
    }
    if(typeof value==='object'&&!visited.has(value)){
      visited.add(value);
      if(value instanceof Map||value.constructor?.name==='Map'){
        for(const [,v] of value)scan(v,depth+1);
      }else if(typeof value.forEach==='function'){
        value.forEach(v=>scan(v,depth+1));
      }else{
        for(const k in value)scan(value[k],depth+1);
      }
    }
  };
  try{
    // Y.Doc.toJSON() returns the live state as a plain object tree.
    scan(ydoc.toJSON?ydoc.toJSON():ydoc);
  }catch(error){
    // Re-throw as the documented invariant.
    throw error;
  }
}

/**
 * Translate a V31 element (plain JS object from invitations.draft_json) to
 * the Y.Map initializer used during Phase A migration. Returns a function
 * suitable for Y.Array.push([fnMap]) or Y.Doc.transact(() => map.set(...)).
 */
function migrateV31Element(v31Element){
  if(!v31Element||typeof v31Element!=='object')return null;
  const Y=window.Y;assertY(Y);
  const element=new Y.Map();
  element.set(Y_KEY_ID,String(v31Element.id||v31Element.crdtId||`el-${Date.now()}`));
  element.set(Y_KEY_KIND,String(v31Element.kind||v31Element.type||'shape'));
  if(v31Element.assetId&&isStringAssetId(v31Element.assetId))element.set(Y_KEY_ASSET_ID,v31Element.assetId);
  if(v31Element.mime)element.set(Y_KEY_MIME,String(v31Element.mime));
  element.set(Y_KEY_TRANSFORM,createTransform(Y,v31Element.transform||v31Element.bounds||{}));
  if(v31Element.crop)element.set(Y_KEY_CROP,createCrop(Y,v31Element.crop));
  if(v31Element.children&&Array.isArray(v31Element.children)){
    const children=new Y.Array();
    for(const child of v31Element.children){const m=migrateV31Element(child);if(m)children.push([m])}
    element.set('children',children);
  }
  // Copy remaining non-reserved keys (style, lock, alt text, etc).
  const reserved=new Set([Y_KEY_ID,Y_KEY_KIND,Y_KEY_ASSET_ID,Y_KEY_MIME,Y_KEY_TRANSFORM,Y_KEY_CROP,'children','type','crdtId','bounds']);
  for(const key in v31Element){if(!reserved.has(key))element.set(key,v31Element[key])}
  return element;
}

window.EInviteCRDTV52RichMedia=Object.freeze({
  Y_KEY_ID,Y_KEY_KIND,Y_KEY_ASSET_ID,Y_KEY_MIME,Y_KEY_TRANSFORM,Y_KEY_CROP,Y_KEY_PROVIDER,Y_KEY_VIDEO_ID,
  DEFAULT_TRANSFORM,RESIZE_RENDER_HZ,RESIZE_REPLICATE_HZ,MAX_TRANSFORM,
  createImage,createEmbed,createTransform,createCrop,transformOf,
  ResizeController,startResize,assertNoAssetBytes,migrateV31Element,
  strings:STRINGS
});
})();
