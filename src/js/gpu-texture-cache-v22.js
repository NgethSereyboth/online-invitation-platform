(()=>{'use strict';
if(window.EInviteGPUTextureCache?.version)return;
const finite=(v,f=0)=>Number.isFinite(Number(v))?Number(v):f;
const now=()=>performance.now();
function defaultBudget(){const mobile=window.matchMedia?.('(max-width:820px)')?.matches,mem=finite(navigator.deviceMemory,8);if(mem<=2)return 32*1024*1024;if(mem<=4||mobile)return 64*1024*1024;return 128*1024*1024}
function safeKey(value){return String(value||'').slice(0,512)}
function powerOfTwo(v){return v>0&&(v&(v-1))===0}
async function bitmapFrom(source,maxSize){let bitmap=source;if(typeof source==='string'){
 const url=new URL(source,location.href);if(!['data:','blob:'].includes(url.protocol)&&url.origin!==location.origin)throw Error('Cross-origin GPU texture blocked');
 const response=await fetch(url.href,{credentials:'same-origin'});if(!response.ok)throw Error(`Texture fetch failed: ${response.status}`);bitmap=await createImageBitmap(await response.blob());
}else if(source instanceof Blob)bitmap=await createImageBitmap(source);else if(typeof ImageBitmap!=='undefined'&&source instanceof ImageBitmap)bitmap=source;else if(source instanceof HTMLImageElement){if(!source.complete)await source.decode();bitmap=await createImageBitmap(source)}else if(source instanceof HTMLCanvasElement||typeof OffscreenCanvas!=='undefined'&&source instanceof OffscreenCanvas)bitmap=await createImageBitmap(source);else throw Error('Unsupported GPU texture source');
 let width=bitmap.width||1,height=bitmap.height||1;if(width<=maxSize&&height<=maxSize)return{bitmap,width,height,owned:bitmap!==source};
 const ratio=Math.min(maxSize/width,maxSize/height),w=Math.max(1,Math.round(width*ratio)),h=Math.max(1,Math.round(height*ratio)),canvas=typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(w,h):Object.assign(document.createElement('canvas'),{width:w,height:h}),ctx=canvas.getContext('2d',{alpha:true});ctx.drawImage(bitmap,0,0,w,h);if(bitmap.close&&bitmap!==source)bitmap.close();bitmap=await createImageBitmap(canvas);return{bitmap,width:w,height:h,owned:true}
}
class TextureCache{
 constructor(gl,options={}){if(!gl)throw Error('WebGL2 context required');this.gl=gl;this.maxBytes=Math.max(8*1024*1024,finite(options.maxBytes,defaultBudget()));this.maxTextureSize=Math.min(finite(options.maxTextureSize,gl.getParameter(gl.MAX_TEXTURE_SIZE)),gl.getParameter(gl.MAX_TEXTURE_SIZE));this.entries=new Map();this.bytes=0;this.hits=0;this.misses=0;this.evictions=0;this.destroyed=false}
 async acquire(key,source,options={}){if(this.destroyed)throw Error('Texture cache destroyed');key=safeKey(key);let entry=this.entries.get(key);if(entry){entry.lastUsed=now();entry.refs++;this.hits++;return entry.promise||entry}this.misses++;entry={key,texture:null,width:0,height:0,bytes:0,lastUsed:now(),refs:1,mipmapped:false,promise:null};this.entries.set(key,entry);entry.promise=this.create(entry,source,options).catch(error=>{this.entries.delete(key);throw error});return entry.promise}
 async create(entry,source,options){const gl=this.gl,{bitmap,width,height,owned}=await bitmapFrom(source,this.maxTextureSize),texture=gl.createTexture();if(!texture)throw Error('GPU texture allocation failed');gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,bitmap);const mipmapped=options.mipmaps!==false&&powerOfTwo(width)&&powerOfTwo(height)&&Math.max(width,height)>=256;if(mipmapped){gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR)}if(owned&&bitmap.close)bitmap.close();entry.texture=texture;entry.width=width;entry.height=height;entry.mipmapped=mipmapped;entry.bytes=Math.max(4,width*height*4*(mipmapped?4/3:1));entry.promise=null;this.bytes+=entry.bytes;this.evict();return entry}
 release(key){const entry=this.entries.get(safeKey(key));if(entry)entry.refs=Math.max(0,entry.refs-1)}
 touch(key){const entry=this.entries.get(safeKey(key));if(entry)entry.lastUsed=now()}
 remove(key){const entry=this.entries.get(safeKey(key));if(!entry)return false;if(entry.texture)this.gl.deleteTexture(entry.texture);this.bytes=Math.max(0,this.bytes-entry.bytes);this.entries.delete(entry.key);return true}
 evict(){if(this.bytes<=this.maxBytes)return;const candidates=[...this.entries.values()].filter(e=>!e.refs&&!e.promise).sort((a,b)=>a.lastUsed-b.lastUsed);for(const entry of candidates){if(this.bytes<=this.maxBytes)break;if(this.remove(entry.key))this.evictions++}}
 clear(){for(const key of [...this.entries.keys()])this.remove(key)}
 setBudget(bytes){this.maxBytes=Math.max(8*1024*1024,finite(bytes,this.maxBytes));this.evict()}
 diagnostics(){return{version:'22.1.5',entries:this.entries.size,bytes:Math.round(this.bytes),maxBytes:this.maxBytes,maxTextureSize:this.maxTextureSize,hits:this.hits,misses:this.misses,evictions:this.evictions,destroyed:this.destroyed}}
 destroy(){if(this.destroyed)return;this.destroyed=true;this.clear()}
}
window.EInviteGPUTextureCache=Object.freeze({version:'22.1.5',create:(gl,options)=>new TextureCache(gl,options),defaultBudget});
})();
