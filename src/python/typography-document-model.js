(()=>{'use strict';
const MODEL_VERSION=1,MAX_TEXT_STYLES=globalThis.EInviteTypography?.MAX_TEXT_STYLES||64;
const KHMER_RE=/[\u1780-\u17ff\u19e0-\u19ff]/u;
const STYLE_FIELDS=Object.freeze(['fontPairing','fontSize','textAutoFit','textAutoFitMax','textMinFontSize','fontWeight','fontStyle','lineHeight','letterSpacing','colorToken','color','textAlign','textVerticalAlign','textWrap','textColumns','textColumnGap','textPadding']);
const OVERRIDE_FIELDS=new Set(STYLE_FIELDS);
const clone=value=>typeof structuredClone==='function'?structuredClone(value):JSON.parse(JSON.stringify(value));
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const finite=(value,fallback,min,max)=>globalThis.EInviteTypography?.finiteNumber?EInviteTypography.finiteNumber(value,fallback,min,max):Number.isFinite(Number(value))?Math.max(min,Math.min(max,Number(value))):fallback;
const fontId=value=>globalThis.EInviteFontRegistry?.fontId?EInviteFontRegistry.fontId(value):'noto-serif';
const pairingId=value=>globalThis.EInviteFontRegistry?.pairingId?EInviteFontRegistry.pairingId(value):'serif-formal';
const pairForFont=value=>{const id=fontId(value);if(id==='noto-sans'||id==='noto-sans-khmer')return'sans-modern';if(id==='sans-arial')return'modern-system';if(id==='sans-trebuchet')return'friendly-system';if(id==='serif-georgia')return'classic-system';return'serif-formal'};
const safeId=(value,fallback='style')=>{const raw=String(value||'').trim().toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,64);return raw||fallback};
const cleanName=(value,fallback)=>String(value||fallback).trim().replace(/[\u0000-\u001f\u007f]/g,'').slice(0,80)||fallback;
const DEFAULT_STYLES=Object.freeze({
 'display':Object.freeze({id:'display',name:'Display',semantic:'display',fontPairing:'serif-formal',fontSize:64,textAutoFit:'fit',textAutoFitMax:88,textMinFontSize:18,fontWeight:'700',fontStyle:'normal',lineHeight:1.08,letterSpacing:0,colorToken:'heading',textAlign:'center',textVerticalAlign:'middle',textWrap:'balance',textColumns:1,textColumnGap:24,textPadding:8,builtin:true}),
 'heading':Object.freeze({id:'heading',name:'Heading',semantic:'heading',fontPairing:'serif-formal',fontSize:42,textAutoFit:'fit',textAutoFitMax:56,textMinFontSize:16,fontWeight:'700',fontStyle:'normal',lineHeight:1.16,letterSpacing:0,colorToken:'heading',textAlign:'center',textVerticalAlign:'middle',textWrap:'balance',textColumns:1,textColumnGap:24,textPadding:8,builtin:true}),
 'subheading':Object.freeze({id:'subheading',name:'Subheading',semantic:'subheading',fontPairing:'sans-modern',fontSize:28,textAutoFit:'fit',textAutoFitMax:36,textMinFontSize:14,fontWeight:'700',fontStyle:'normal',lineHeight:1.25,letterSpacing:0,colorToken:'heading',textAlign:'center',textVerticalAlign:'middle',textWrap:'pretty',textColumns:1,textColumnGap:24,textPadding:8,builtin:true}),
 'body':Object.freeze({id:'body',name:'Body',semantic:'body',fontPairing:'sans-modern',fontSize:18,textAutoFit:'none',textAutoFitMax:22,textMinFontSize:12,fontWeight:'400',fontStyle:'normal',lineHeight:1.5,letterSpacing:0,colorToken:'text',textAlign:'left',textVerticalAlign:'top',textWrap:'pretty',textColumns:1,textColumnGap:24,textPadding:8,builtin:true}),
 'caption':Object.freeze({id:'caption',name:'Caption',semantic:'caption',fontPairing:'sans-modern',fontSize:13,textAutoFit:'none',textAutoFitMax:16,textMinFontSize:10,fontWeight:'400',fontStyle:'normal',lineHeight:1.4,letterSpacing:.1,colorToken:'muted',textAlign:'center',textVerticalAlign:'middle',textWrap:'normal',textColumns:1,textColumnGap:16,textPadding:6,builtin:true}),
 'khmer-ceremonial':Object.freeze({id:'khmer-ceremonial',name:'Khmer Ceremonial',semantic:'khmer-ceremonial',fontPairing:'ceremonial-khmer',fontSize:48,textAutoFit:'fit',textAutoFitMax:68,textMinFontSize:18,fontWeight:'700',fontStyle:'normal',lineHeight:1.42,letterSpacing:0,colorToken:'heading',textAlign:'center',textVerticalAlign:'middle',textWrap:'balance',textColumns:1,textColumnGap:24,textPadding:10,builtin:true})
});
const DEFAULT_ORDER=Object.freeze(Object.keys(DEFAULT_STYLES));
function normalizeStyle(input={},idHint='style'){
 const id=safeId(input.id||idHint,idHint),base=DEFAULT_STYLES[input.semantic]||DEFAULT_STYLES.body;
 const fontSize=finite(input.fontSize,base.fontSize,8,200),max=finite(input.textAutoFitMax,Math.max(fontSize,base.textAutoFitMax),8,200),min=Math.min(finite(input.textMinFontSize,base.textMinFontSize,8,72),max);
 const style={id,name:cleanName(input.name,base.name),semantic:String(input.semantic||base.semantic||'custom').slice(0,40),fontPairing:pairingId(input.fontPairing||input.fontPairId||base.fontPairing),fontSize,textAutoFit:input.textAutoFit==='fit'?'fit':'none',textAutoFitMax:max,textMinFontSize:min,fontWeight:String(input.fontWeight)==='700'?'700':'400',fontStyle:input.fontStyle==='italic'?'italic':'normal',lineHeight:finite(input.lineHeight,base.lineHeight,.8,3),letterSpacing:finite(input.letterSpacing,base.letterSpacing,-2,20),colorToken:(globalThis.EInviteTypography?.data?.colorTokens||['heading','text','accent','surface','muted','inverse']).includes(input.colorToken)?input.colorToken:base.colorToken,textAlign:['left','center','right','justify'].includes(input.textAlign)?input.textAlign:base.textAlign,textVerticalAlign:['top','middle','bottom'].includes(input.textVerticalAlign)?input.textVerticalAlign:base.textVerticalAlign,textWrap:['normal','balance','pretty'].includes(input.textWrap)?input.textWrap:base.textWrap,textColumns:Math.round(finite(input.textColumns,base.textColumns,1,3)),textColumnGap:finite(input.textColumnGap,base.textColumnGap,0,64),textPadding:finite(input.textPadding,base.textPadding,0,64),builtin:input.builtin===true};
 if(/^#[0-9a-f]{6}$/i.test(String(input.color||'')))style.color=String(input.color).toLowerCase();
 return style;
}
function defaultCatalog(){return{version:MODEL_VERSION,defaultStyleId:'body',styles:Object.fromEntries(DEFAULT_ORDER.map(id=>[id,clone(DEFAULT_STYLES[id])])),styleOrder:[...DEFAULT_ORDER]}}
function inferStyleId(object={},objectId=''){
 const text=String(object.html||object.text||''),size=finite(object.fontSize,32,8,200),id=String(objectId||object.id||'').toLowerCase();
 if(KHMER_RE.test(text)&&size>=34)return'khmer-ceremonial';if(id==='title'||size>=52)return'display';if(size>=34)return'heading';if(id==='subtitle'||size>=23)return'subheading';if(size<=14)return'caption';return'body';
}
function legacyProjection(object={}){
 const fontSize=finite(object.fontSize,32,8,200),max=finite(object.textAutoFitMax,fontSize,8,200);
 const rawPair=object.fontPairing||object.fontPairId;
 const rawToken=object.colorToken;
 return{fontPairing:rawPair?pairingId(rawPair):pairForFont(object.font),fontSize,textAutoFit:object.textAutoFit==='fit'?'fit':'none',textAutoFitMax:max,textMinFontSize:Math.min(finite(object.textMinFontSize,10,8,72),max),fontWeight:String(object.fontWeight)==='700'?'700':'400',fontStyle:object.fontStyle==='italic'?'italic':'normal',lineHeight:finite(object.lineHeight,1.35,.8,3),letterSpacing:finite(object.letterSpacing,0,-2,20),colorToken:(globalThis.EInviteTypography?.data?.colorTokens||['heading','text','accent','surface','muted','inverse']).includes(rawToken)?rawToken:'text',color:/^#[0-9a-f]{6}$/i.test(String(object.color||''))?String(object.color).toLowerCase():undefined,textAlign:['left','center','right','justify'].includes(object.textAlign)?object.textAlign:'center',textVerticalAlign:['top','middle','bottom'].includes(object.textVerticalAlign)?object.textVerticalAlign:'middle',textWrap:['normal','balance','pretty'].includes(object.textWrap)?object.textWrap:'normal',textColumns:Math.round(finite(object.textColumns,1,1,3)),textColumnGap:finite(object.textColumnGap,24,0,64),textPadding:finite(object.textPadding,8,0,64)};
}
function normalizeOverrides(input={}){const out={};if(!input||typeof input!=='object'||Array.isArray(input))return out;for(const key of STYLE_FIELDS)if(own(input,key)){const probe=normalizeStyle({[key]:input[key],semantic:'body'},'probe');if(key==='color'){if(/^#[0-9a-f]{6}$/i.test(String(input[key])))out[key]=String(input[key]).toLowerCase()}else out[key]=probe[key]}return out}
function differences(source,base){const out={};for(const key of STYLE_FIELDS){const a=source[key],b=base[key];if(a!==undefined&&JSON.stringify(a)!==JSON.stringify(b))out[key]=a}return out}
function normalizeObject(objectId,input={},catalog=defaultCatalog()){
 const o={...input};if(!['text','decoration'].includes(o.type||'text'))return o;const compatibilityFont=fontId(o.font);
 let styleId=safeId(o.textStyleId||inferStyleId(o,objectId),'body');if(!catalog.styles[styleId])styleId=catalog.defaultStyleId||'body';
 const base=catalog.styles[styleId]||catalog.styles.body||normalizeStyle(DEFAULT_STYLES.body,'body');
 let overrides=normalizeOverrides(o.typographyOverrides);const legacy=legacyProjection(o);
 if(!o.typographyModelVersion){overrides={...differences(legacy,base),...overrides}}
 else if(o.typographyResolvedSnapshot&&typeof o.typographyResolvedSnapshot==='object'&&!Array.isArray(o.typographyResolvedSnapshot)){
  const snapshot=normalizeOverrides(o.typographyResolvedSnapshot);
  for(const key of STYLE_FIELDS)if(legacy[key]!==undefined&&snapshot[key]!==undefined&&JSON.stringify(legacy[key])!==JSON.stringify(snapshot[key]))overrides[key]=legacy[key];
 }
 o.typographyModelVersion=MODEL_VERSION;o.textStyleId=styleId;o.typographyDetached=o.typographyDetached===true;o.typographyOverrides=overrides;
 const resolved=resolveObjectTypography({typography:catalog,palette:{}},o,{text:o.html||'',ignoreDetached:false});
 o.font=compatibilityFont;o.fontPairing=resolved.fontPairing;o.colorToken=resolved.colorToken;
 for(const key of ['fontSize','textAutoFit','textAutoFitMax','textMinFontSize','fontWeight','fontStyle','lineHeight','letterSpacing','textAlign','textVerticalAlign','textWrap','textColumns','textColumnGap','textPadding'])o[key]=resolved[key];
 if(resolved.color)o.color=resolved.color;
 o.typographyResolvedSnapshot=Object.fromEntries(STYLE_FIELDS.filter(key=>resolved[key]!==undefined).map(key=>[key,resolved[key]]));
 return o;
}
function normalizeCatalog(input={}){
 const defaults=defaultCatalog(),rawStyles=input&&typeof input==='object'&&input.styles&&typeof input.styles==='object'&&!Array.isArray(input.styles)?input.styles:{};const styles={};
 for(const id of DEFAULT_ORDER)styles[id]=normalizeStyle({...DEFAULT_STYLES[id],...(rawStyles[id]||{}),id},id);
 for(const [id,value] of Object.entries(rawStyles).slice(0,MAX_TEXT_STYLES)){const clean=safeId(id);if(!styles[clean])styles[clean]=normalizeStyle({...value,id:clean},clean)}
 const order=[];for(const id of Array.isArray(input.styleOrder)?input.styleOrder:DEFAULT_ORDER){const clean=safeId(id);if(styles[clean]&&!order.includes(clean))order.push(clean)}for(const id of Object.keys(styles))if(!order.includes(id))order.push(id);
 const defaultStyleId=styles[safeId(input.defaultStyleId||'body')]?safeId(input.defaultStyleId||'body'):'body';return{version:MODEL_VERSION,defaultStyleId,styles,styleOrder:order.slice(0,MAX_TEXT_STYLES)};
}
function normalizeDocument(input={},options={}){
 const doc=options.mutate?input:clone(input||{});if(globalThis.EInviteCustomFonts)EInviteCustomFonts.normalizeDocumentFonts(doc);doc.typography=normalizeCatalog(doc.typography||{});
 const normalizeMap=map=>{if(!map||typeof map!=='object'||Array.isArray(map))return{};for(const [id,obj] of Object.entries(map))if(obj&&typeof obj==='object')map[id]=normalizeObject(id,obj,doc.typography);return map};
 doc.objects=normalizeMap(doc.objects||{});for(const page of Array.isArray(doc.designPages)?doc.designPages:[])page.objects=normalizeMap(page.objects||{});return doc;
}
function objectText(object={},fallback=''){return String(object.html||object.text||object.content||fallback).replace(/<[^>]+>/g,' ')}
function detectLocale(text='',explicit='auto'){if(String(explicit).toLowerCase().startsWith('km'))return'km';if(String(explicit).toLowerCase().startsWith('en'))return'en';return KHMER_RE.test(String(text))?'km':'en'}
function resolveColorToken(document={},token='text'){const palette=document.palette||{},accent=document.accent||'#9d4555',map={heading:palette.heading||accent,text:palette.text||'#342c26',accent,surface:palette.surface||'#ffffff',muted:palette.muted||'#6f6770',inverse:'#ffffff'};return map[token]||map.text}
function resolveObjectTypography(document={},object={},options={}){
 const catalog=normalizeCatalog(document.typography||{}),styleId=catalog.styles[object.textStyleId]?object.textStyleId:catalog.defaultStyleId,style=catalog.styles[styleId]||catalog.styles.body;
 const legacy=legacyProjection(object),detached=object.typographyDetached===true,overrides=normalizeOverrides(object.typographyOverrides);let result=detached?{...style,...legacy}:{...style,...overrides};
 const text=options.text??objectText(object),locale=detectLocale(text,options.locale||object.textLocale||'auto'),font=globalThis.EInviteFontRegistry?.pairedFont?EInviteFontRegistry.pairedFont(result.fontPairing,locale):fontId(object.font),fontStack=globalThis.EInviteFontRegistry?.stack?EInviteFontRegistry.stack(font):'serif';
 const max=finite(result.textAutoFitMax,result.fontSize,8,200);result={...result,id:styleId,styleId,styleName:style.name,locale,font,compatibilityFont:fontId(object.font||font),fontStack,fontSize:finite(result.fontSize,style.fontSize,8,200),textAutoFit:result.textAutoFit==='fit'?'fit':'none',textAutoFitMax:max,textMinFontSize:Math.min(finite(result.textMinFontSize,style.textMinFontSize,8,72),max),fontWeight:String(result.fontWeight)==='700'?'700':'400',fontStyle:result.fontStyle==='italic'?'italic':'normal',lineHeight:finite(result.lineHeight,style.lineHeight,.8,3),letterSpacing:finite(result.letterSpacing,style.letterSpacing,-2,20),textAlign:['left','center','right','justify'].includes(result.textAlign)?result.textAlign:style.textAlign,textVerticalAlign:['top','middle','bottom'].includes(result.textVerticalAlign)?result.textVerticalAlign:style.textVerticalAlign,textWrap:['normal','balance','pretty'].includes(result.textWrap)?result.textWrap:style.textWrap,textColumns:Math.round(finite(result.textColumns,style.textColumns,1,3)),textColumnGap:finite(result.textColumnGap,style.textColumnGap,0,64),textPadding:finite(result.textPadding,style.textPadding,0,64)};
 result.color=/^#[0-9a-f]{6}$/i.test(String(result.color||''))?result.color:resolveColorToken(document,result.colorToken);return result;
}
function walkTextObjects(document,callback){const visit=map=>Object.entries(map||{}).forEach(([id,o])=>{if(o&&['text','decoration'].includes(o.type||'text'))callback(o,id,map)});visit(document.objects);for(const page of document.designPages||[])visit(page.objects)}
function uniqueStyleId(catalog,seed='custom-style'){const base=safeId(seed,'custom-style');let id=base,n=2;while(catalog.styles[id])id=`${base}-${n++}`;return id}
function createStyle(document,input={}){document.typography=normalizeCatalog(document.typography||{});if(Object.keys(document.typography.styles).length>=MAX_TEXT_STYLES)throw new RangeError(`Text style limit (${MAX_TEXT_STYLES}) reached`);const id=uniqueStyleId(document.typography,input.id||input.name||'custom-style'),style=normalizeStyle({...input,id,builtin:false},id);document.typography.styles[id]=style;document.typography.styleOrder.push(id);return id}
function renameStyle(document,id,name){document.typography=normalizeCatalog(document.typography||{});if(!document.typography.styles[id])throw new Error('Text style not found');document.typography.styles[id].name=cleanName(name,document.typography.styles[id].name);return id}
function duplicateStyle(document,id,name){document.typography=normalizeCatalog(document.typography||{});const source=document.typography.styles[id];if(!source)throw new Error('Text style not found');return createStyle(document,{...clone(source),id:'',name:name||`${source.name} Copy`,builtin:false})}
function updateStyle(document,id,patch={}){document.typography=normalizeCatalog(document.typography||{});const source=document.typography.styles[id];if(!source)throw new Error('Text style not found');document.typography.styles[id]=normalizeStyle({...source,...patch,id,builtin:source.builtin===true},id);return document.typography.styles[id]}
function deleteStyle(document,id,replacementId='body'){document.typography=normalizeCatalog(document.typography||{});if(!document.typography.styles[id])throw new Error('Text style not found');if(id===replacementId)throw new Error('Replacement style must be different');if(!document.typography.styles[replacementId])throw new Error('Replacement style not found');walkTextObjects(document,o=>{if(o.textStyleId===id)o.textStyleId=replacementId});delete document.typography.styles[id];document.typography.styleOrder=document.typography.styleOrder.filter(x=>x!==id);if(document.typography.defaultStyleId===id)document.typography.defaultStyleId=replacementId;return replacementId}
function linkObject(object,styleId){object.textStyleId=styleId;object.typographyDetached=false;object.typographyOverrides={};object.typographyModelVersion=MODEL_VERSION;return object}
function detachObject(document,object){const resolved=resolveObjectTypography(document,object);object.typographyDetached=true;object.typographyOverrides=Object.fromEntries(STYLE_FIELDS.filter(k=>resolved[k]!==undefined).map(k=>[k,resolved[k]]));return object}
function setOverride(object,key,value){if(!OVERRIDE_FIELDS.has(key))throw new Error('Unsupported typography override');object.typographyOverrides=normalizeOverrides({...object.typographyOverrides,[key]:value});object.typographyDetached=false;return object}
function resetOverride(object,key){if(!object.typographyOverrides)return object;if(key)delete object.typographyOverrides[key];else object.typographyOverrides={};return object}
function linkedCount(document,styleId){let count=0;walkTextObjects(document,o=>{if(o.textStyleId===styleId&&!o.typographyDetached)count++});return count}
window.TypographyDocumentModel=Object.freeze({MODEL_VERSION,MAX_TEXT_STYLES,STYLE_FIELDS,DEFAULT_STYLES,defaultCatalog,normalizeStyle,normalizeCatalog,normalizeObject,normalizeDocument,resolveObjectTypography,resolveColorToken,detectLocale,walkTextObjects,createStyle,renameStyle,duplicateStyle,updateStyle,deleteStyle,linkObject,detachObject,setOverride,resetOverride,linkedCount,clone});
})();
