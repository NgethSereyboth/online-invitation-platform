;(()=>{'use strict';
const DATA={"version":"20.1","modelVersion":1,"defaultFontId":"noto-serif","defaultPairingId":"serif-formal","fonts":{"noto-sans":{"label":"Noto Sans","family":"EInvite Noto Sans","stack":"'EInvite Noto Sans','EInvite Noto Sans Khmer','Noto Sans','Noto Sans Khmer','Khmer UI',Arial,sans-serif","category":"sans","scripts":["Latin","Khmer-fallback"],"weights":[400,700],"bundled":true,"license":"SIL Open Font License 1.1","copyright":"Copyright 2015 Google LLC. All Rights Reserved.","assets":{"400":"assets/fonts/noto-sans-latin-400.woff2","700":"assets/fonts/noto-sans-latin-700.woff2"},"stableId":"noto-sans","sourceType":"bundled","licenseId":"OFL-1.1","licenseFile":"licenses/fonts/Noto-OFL-1.1.txt","assetSha256":{"400":"6932db6a846e5f3eedd70862935d1e382ffa25da0851563c3e7b82129ebefe23","700":"a9885073a1b8fcde1b37ac0c4497914e598cc9057344a552217b32e4c89f0866"}},"noto-serif":{"label":"Noto Serif","family":"EInvite Noto Serif","stack":"'EInvite Noto Serif','EInvite Noto Serif Khmer','Noto Serif','Noto Serif Khmer','Khmer UI',Georgia,serif","category":"serif","scripts":["Latin","Khmer-fallback"],"weights":[400,700],"bundled":true,"license":"SIL Open Font License 1.1","copyright":"Copyright 2015 Google LLC. All Rights Reserved.","assets":{"400":"assets/fonts/noto-serif-latin-400.woff2","700":"assets/fonts/noto-serif-latin-700.woff2"},"stableId":"noto-serif","sourceType":"bundled","licenseId":"OFL-1.1","licenseFile":"licenses/fonts/Noto-OFL-1.1.txt","assetSha256":{"400":"3c94a973daf5e7fd05cb205eab2171b0af0ba42496202d54e6cdd55e45a82221","700":"d7e6e94e00d65d77273e033e0eca185d9ab37d44d4505225f364ff1453cb7039"}},"noto-sans-khmer":{"label":"Noto Sans Khmer","family":"EInvite Noto Sans Khmer","stack":"'EInvite Noto Sans Khmer','EInvite Noto Sans','Noto Sans Khmer','Noto Sans','Khmer UI',Arial,sans-serif","category":"sans","scripts":["Khmer","Latin-fallback"],"weights":[400,700],"bundled":true,"license":"SIL Open Font License 1.1","copyright":"Copyright 2016 Google Inc. All Rights Reserved.","assets":{"400":"assets/fonts/noto-sans-khmer-400.woff2","700":"assets/fonts/noto-sans-khmer-700.woff2"},"stableId":"noto-sans-khmer","sourceType":"bundled","licenseId":"OFL-1.1","licenseFile":"licenses/fonts/Noto-OFL-1.1.txt","assetSha256":{"400":"53229761be85cb21c727d19ff81e959f3a35c32925d42f02829acf53dbdbf625","700":"0eb1923fffc493ed3af0e5cb4bc467ec1c7921ce9f845888ebd3b5755b86aecd"}},"noto-serif-khmer":{"label":"Noto Serif Khmer","family":"EInvite Noto Serif Khmer","stack":"'EInvite Noto Serif Khmer','EInvite Noto Serif','Noto Serif Khmer','Noto Serif','Khmer UI',Georgia,serif","category":"serif","scripts":["Khmer","Latin-fallback"],"weights":[400,700],"bundled":true,"license":"SIL Open Font License 1.1","copyright":"Copyright 2016 Google Inc. All Rights Reserved.","assets":{"400":"assets/fonts/noto-serif-khmer-400.woff2","700":"assets/fonts/noto-serif-khmer-700.woff2"},"stableId":"noto-serif-khmer","sourceType":"bundled","licenseId":"OFL-1.1","licenseFile":"licenses/fonts/Noto-OFL-1.1.txt","assetSha256":{"400":"db80eb1479b0cb726e5fd224ba2cde7b6f92825988f4ec1e89575d851011e625","700":"fe903cee1be19a931d38a575948897f7c0d0159a8c2c028af596ec928d7976ce"}},"serif-georgia":{"label":"Classic Serif (system)","family":"Georgia","stack":"Georgia,'EInvite Noto Serif','EInvite Noto Serif Khmer','Noto Serif Khmer','Khmer UI',serif","category":"serif","scripts":["Latin","Khmer-fallback"],"weights":[400,700],"bundled":false,"legacyOnly":true,"license":"Operating-system font; bundled Noto fallbacks remain available","assets":{},"stableId":"serif-georgia","sourceType":"system-fallback"},"sans-arial":{"label":"Modern Sans (system)","family":"Arial","stack":"Arial,'EInvite Noto Sans','EInvite Noto Sans Khmer','Noto Sans Khmer','Khmer UI',sans-serif","category":"sans","scripts":["Latin","Khmer-fallback"],"weights":[400,700],"bundled":false,"legacyOnly":true,"license":"Operating-system font; bundled Noto fallbacks remain available","assets":{},"stableId":"sans-arial","sourceType":"system-fallback"},"sans-trebuchet":{"label":"Friendly (system)","family":"Trebuchet MS","stack":"'Trebuchet MS','EInvite Noto Sans','EInvite Noto Sans Khmer','Noto Sans Khmer','Khmer UI',sans-serif","category":"sans","scripts":["Latin","Khmer-fallback"],"weights":[400,700],"bundled":false,"legacyOnly":true,"license":"Operating-system font; bundled Noto fallbacks remain available","assets":{},"stableId":"sans-trebuchet","sourceType":"system-fallback"}},"pairings":{"serif-formal":{"label":"Formal Serif","en":"noto-serif","km":"noto-serif-khmer","recommended":true,"stableId":"serif-formal"},"sans-modern":{"label":"Modern Sans","en":"noto-sans","km":"noto-sans-khmer","recommended":true,"stableId":"sans-modern"},"modern-system":{"label":"Modern System Sans","en":"sans-arial","km":"noto-sans-khmer","legacyOnly":true,"stableId":"modern-system"},"ceremonial-khmer":{"label":"Khmer Ceremonial","en":"noto-serif","km":"noto-serif-khmer","recommended":true,"stableId":"ceremonial-khmer"},"classic-system":{"label":"Classic System Serif","en":"serif-georgia","km":"noto-serif-khmer","legacyOnly":true,"stableId":"classic-system"},"friendly-system":{"label":"Friendly System Sans","en":"sans-trebuchet","km":"noto-sans-khmer","legacyOnly":true,"stableId":"friendly-system"}},"colorTokens":["heading","text","accent","surface","muted","inverse"],"legacy":{"Georgia,serif":"serif-georgia","Georgia, serif":"serif-georgia","Arial,sans-serif":"sans-arial","Arial, sans-serif":"sans-arial","'Trebuchet MS',sans-serif":"sans-trebuchet","'Trebuchet MS', sans-serif":"sans-trebuchet","'Noto Serif Khmer','Khmer OS Battambang',serif":"noto-serif-khmer","'Noto Serif Khmer', 'Khmer OS Battambang', serif":"noto-serif-khmer","'Noto Sans Khmer','Khmer OS Battambang',sans-serif":"noto-sans-khmer","'Noto Sans Khmer', 'Khmer OS Battambang', sans-serif":"noto-sans-khmer","'Khmer OS Muol Light','Noto Serif Khmer',serif":"noto-serif-khmer","'Khmer OS Muol Light', 'Noto Serif Khmer', serif":"noto-serif-khmer","Noto Serif Khmer":"noto-serif-khmer","Noto Sans Khmer":"noto-sans-khmer","Georgia":"serif-georgia","Arial":"sans-arial","inherit":"noto-serif","":"noto-serif"},"maxTextStyles":64};
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const ids=Object.freeze(Object.keys(DATA.fonts)),pairingIds=Object.freeze(Object.keys(DATA.pairings)),MAX_TEXT_STYLES=DATA.maxTextStyles||64;
function finiteNumber(value,fallback,min,max){if(typeof value==='boolean'||value===null||value===''||Array.isArray(value)||(typeof value==='object'&&value!==null))return fallback;const number=typeof value==='number'?value:Number(value);return Number.isFinite(number)?Math.max(min,Math.min(max,number)):fallback}
function fontId(value,{fallback=DATA.defaultFontId,strict=false}={}){const raw=typeof value==='string'?value.trim():'';if(own(DATA.fonts,raw))return raw;if(own(DATA.legacy,raw))return DATA.legacy[raw];if(strict)throw new TypeError('Unknown font ID');return fallback}
function pairingId(value,{fallback=DATA.defaultPairingId,strict=false}={}){const raw=typeof value==='string'?value.trim():'';if(own(DATA.pairings,raw))return raw;if(strict)throw new TypeError('Unknown font pairing ID');return fallback}
function stack(value){return DATA.fonts[fontId(value)].stack}
function pairing(value){const id=pairingId(value);return Object.freeze({id,...DATA.pairings[id]})}
function pairedFont(value,locale='en'){const p=pairing(value);return fontId(String(locale).toLowerCase().startsWith('km')?p.km:p.en)}
function pairedStack(value,locale='en'){return stack(pairedFont(value,locale))}
function metadata(value){const id=fontId(value);return Object.freeze({id,...DATA.fonts[id]})}
function normalizeTypography(source={}){const o={...source},fontSize=finiteNumber(o.fontSize,32,8,200),max=finiteNumber(o.textAutoFitMax,fontSize,8,200),min=Math.min(finiteNumber(o.textMinFontSize,10,8,72),max);o.font=fontId(o.font);o.fontPairing=pairingId(o.fontPairing||o.fontPairId);o.fontSize=fontSize;o.textAutoFit=o.textAutoFit==='fit'?'fit':'none';o.textAutoFitMax=max;o.textMinFontSize=min;o.textWrap=['normal','balance','pretty'].includes(o.textWrap)?o.textWrap:'normal';o.textColumns=Math.round(finiteNumber(o.textColumns,1,1,3));o.textColumnGap=finiteNumber(o.textColumnGap,24,0,64);o.textAlign=['left','center','right','justify'].includes(o.textAlign)?o.textAlign:'center';return o}
function fitLargest({min=8,max=200,fits,steps=16}={}){min=finiteNumber(min,8,8,200);max=finiteNumber(max,200,min,200);if(typeof fits!=='function')return min;let low=min,high=max,best=min;for(let i=0;i<steps;i++){const candidate=(low+high)/2;if(fits(candidate)){best=candidate;low=candidate}else high=candidate}return Math.max(min,Math.floor((best+1e-7)*10)/10)}
async function ensureReady(idsToLoad=ids){if(!document.fonts)return;const requests=[];for(const raw of idsToLoad){const meta=DATA.fonts[fontId(raw)];if(!meta.bundled)continue;for(const weight of meta.weights||[400])requests.push(document.fonts.load(`${weight} 16px "${meta.family}"`))}await Promise.allSettled(requests)}
const registry=Object.freeze({version:DATA.version,data:DATA,MAX_TEXT_STYLES,fontIds:ids,pairingIds,fontId,pairingId,stack,pairing,pairedFont,pairedStack,metadata,ensureReady});
window.EInviteFontRegistry=registry;
window.EInviteTypography=Object.freeze({version:DATA.version,data:DATA,MAX_TEXT_STYLES,fontIds:ids,pairingIds,finiteNumber,fontId,pairingId,stack,pairing,pairedFont,pairedStack,metadata,normalizeTypography,fitLargest,ensureReady});
})();;(()=>{'use strict';
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
})();;(()=>{'use strict';
const KHMER_RE=/[\u1780-\u17ff\u19e0-\u19ff]/u;
const KHMER_MARK_RE=/[\u17b4-\u17d3\u17dd\u200c\u200d\ufe00-\ufe0f]/u;
const KHMER_COENG='\u17d2';
const finite=(value,fallback,min,max)=>globalThis.EInviteTypography?.finiteNumber?EInviteTypography.finiteNumber(value,fallback,min,max):Number.isFinite(Number(value))?Math.max(min,Math.min(max,Number(value))):fallback;
const escCss=value=>String(value??'').replace(/[;{}<>]/g,'');
function mergeKhmerSegments(segments){const merged=[];let joinNext=false;for(const segment of segments){if(!merged.length){merged.push(segment);joinNext=segment.endsWith(KHMER_COENG)||segment.endsWith('\u200d');continue}if(joinNext||KHMER_MARK_RE.test(segment[0]||'')){merged[merged.length-1]+=segment}else merged.push(segment);joinNext=merged[merged.length-1].endsWith(KHMER_COENG)||merged[merged.length-1].endsWith('\u200d')}return merged}
function segmentGraphemes(text='',locale='km'){
 const value=String(text);
 if(globalThis.Intl?.Segmenter){const segmenter=new Intl.Segmenter(locale,{granularity:'grapheme'}),segments=[...segmenter.segment(value)].map(item=>item.segment);return locale==='km'||KHMER_RE.test(value)?mergeKhmerSegments(segments):segments}
 const output=[];let joinNext=false;
 for(const char of[...value]){
  if(!output.length){output.push(char);joinNext=char===KHMER_COENG||char==='\u200d';continue}
  if(joinNext||KHMER_MARK_RE.test(char)){output[output.length-1]+=char;joinNext=char===KHMER_COENG||char==='\u200d';continue}
  output.push(char);joinNext=char===KHMER_COENG||char==='\u200d';
 }
 return output;
}
function preservesKhmerClusters(text='',segments=segmentGraphemes(text,'km')){
 const value=String(text);if(segments.join('')!==value)return false;
 return segments.every((segment,index)=>{const chars=[...segment];if(!chars.length)return false;if(index>0&&KHMER_MARK_RE.test(chars[0]))return false;if(index<segments.length-1&&(chars.at(-1)===KHMER_COENG||chars.at(-1)==='\u200d'))return false;return true});
}
function styleObject(model={}){
 const wrap=model.textWrap==='normal'?'wrap':model.textWrap;
 const vertical=model.textVerticalAlign==='top'?'flex-start':model.textVerticalAlign==='bottom'?'flex-end':'center';
 const khmer=model.locale==='km'||KHMER_RE.test(String(model.text||'')),meta=khmer&&String(model.font||'').startsWith('custom-')?globalThis.EInviteFontRegistry?.data?.fonts?.[model.font]:null,lineHeight=meta?.khmerReady?Math.max(finite(model.lineHeight,1.35,.8,3),finite(meta.recommendedLineHeight,1.42,1.15,1.8)):finite(model.lineHeight,1.35,.8,3);
 return{outer:{display:'flex',flexDirection:'column',justifyContent:vertical,alignItems:'stretch',overflow:'hidden',padding:`${finite(model.textPadding,8,0,64)}px`,fontFamily:model.fontStack||'serif',fontSize:`${model.textAutoFit==='fit'?finite(model.textAutoFitMax,model.fontSize,8,200):finite(model.fontSize,32,8,200)}px`,fontWeight:String(model.fontWeight)==='700'?'700':'400',fontStyle:model.fontStyle==='italic'?'italic':'normal',letterSpacing:`${finite(model.letterSpacing,0,-2,20)}px`,lineHeight:String(lineHeight),textAlign:['left','center','right','justify'].includes(model.textAlign)?model.textAlign:'left',color:model.color||'inherit',wordBreak:'normal',overflowWrap:khmer?'normal':'anywhere',lineBreak:khmer?'strict':'auto',textRendering:'optimizeLegibility',fontSynthesis:'none'},flow:{width:'100%',maxWidth:'100%',columnCount:String(Math.round(finite(model.textColumns,1,1,3))),columnGap:Math.round(finite(model.textColumns,1,1,3))>1?`${finite(model.textColumnGap,24,0,64)}px`:'normal',columnFill:'balance',textWrap:wrap,wordBreak:'normal',overflowWrap:khmer?'normal':'anywhere',lineBreak:khmer?'strict':'auto',hyphens:khmer?'none':'manual'}};
}
const STYLE_ORDER=Object.freeze(['display','flexDirection','justifyContent','alignItems','overflow','padding','fontFamily','fontSize','fontWeight','fontStyle','letterSpacing','lineHeight','textAlign','color','wordBreak','overflowWrap','lineBreak','textRendering','fontSynthesis','width','maxWidth','columnCount','columnGap','columnFill','textWrap','hyphens']);
const kebab=value=>value.replace(/[A-Z]/g,m=>`-${m.toLowerCase()}`);
function styleString(styles={}){return STYLE_ORDER.filter(key=>styles[key]!==undefined).map(key=>`${kebab(key)}:${escCss(styles[key])}`).join(';')+';'}
function ensureFlow(outer){if(!outer)return null;let flow=outer.querySelector?.(':scope > .typography-flow');if(!flow&&outer.ownerDocument){flow=outer.ownerDocument.createElement('div');flow.className='typography-flow';while(outer.firstChild)flow.append(outer.firstChild);outer.append(flow)}return flow||outer}
function applyStyles(node,styles){if(!node)return;for(const [key,value]of Object.entries(styles||{}))node.style[key]=value}
function applyToElement(outer,model={}){if(!outer)return null;const flow=ensureFlow(outer),styles=styleObject(model);applyStyles(outer,styles.outer);applyStyles(flow,styles.flow);outer.lang=model.locale==='km'?'km':'en';outer.dataset.typographyModelVersion='1';outer.dataset.font=model.font||'';outer.dataset.fontPairing=model.fontPairing||'';outer.dataset.fontSize=String(model.fontSize||32);outer.dataset.textAutoFit=model.textAutoFit||'none';outer.dataset.textAutoFitMax=String(model.textAutoFitMax||model.fontSize||32);outer.dataset.textMinFontSize=String(model.textMinFontSize||10);outer.dataset.textWrap=model.textWrap||'normal';outer.dataset.textColumns=String(model.textColumns||1);outer.dataset.textColumnGap=String(model.textColumnGap||24);outer.dataset.textAlign=model.textAlign||'left';outer.dataset.textStyleId=model.styleId||'';outer.__typographyModel=model;return flow}
function availableSpace(outer){const style=getComputedStyle(outer),width=Math.max(0,outer.clientWidth-(parseFloat(style.paddingLeft)||0)-(parseFloat(style.paddingRight)||0)),height=Math.max(0,outer.clientHeight-(parseFloat(style.paddingTop)||0)-(parseFloat(style.paddingBottom)||0));return{width,height}}
function measurement(outer){const flow=outer?.querySelector?.(':scope > .typography-flow')||outer;if(!outer||!flow)return{availableWidth:0,availableHeight:0,scrollWidth:0,scrollHeight:0,horizontalOverflow:0,verticalOverflow:0,overflow:false,computedSize:0};const available=availableSpace(outer),scrollWidth=Math.ceil(flow.scrollWidth),scrollHeight=Math.ceil(flow.scrollHeight),horizontalOverflow=Math.max(0,scrollWidth-Math.ceil(available.width)-1),verticalOverflow=Math.max(0,scrollHeight-Math.ceil(available.height)-1),computedSize=parseFloat(getComputedStyle(outer).fontSize)||0;return{availableWidth:available.width,availableHeight:available.height,scrollWidth,scrollHeight,horizontalOverflow,verticalOverflow,overflow:horizontalOverflow>0||verticalOverflow>0,computedSize}}
function fit(outer,model={},options={}){
 if(!outer)return null;ensureFlow(outer);applyToElement(outer,model);
 if(model.textAutoFit!=='fit'){delete outer.dataset.textComputedFontSize;return measurement(outer)}
 const available=availableSpace(outer);if(available.width<2||available.height<2)return measurement(outer);
 const min=finite(model.textMinFontSize,10,8,72),max=finite(model.textAutoFitMax,model.fontSize,Math.max(8,min),200),old=outer.style.fontSize,oldComputed=outer.dataset.textComputedFontSize;
 const fitLargest=globalThis.EInviteTypography?.fitLargest||(({min})=>min);
 const computed=fitLargest({min,max,steps:16,fits:size=>{outer.style.fontSize=`${size}px`;return!measurement(outer).overflow}});
 outer.style.fontSize=`${computed}px`;outer.dataset.textComputedFontSize=String(computed);const result={...measurement(outer),computedSize:computed,min,max};
 if(options.set===false){outer.style.fontSize=old;if(oldComputed===undefined)delete outer.dataset.textComputedFontSize;else outer.dataset.textComputedFontSize=oldComputed}
 return result;
}
function parseColor(value){const raw=String(value||'').trim();if(/^#[0-9a-f]{6}$/i.test(raw))return[parseInt(raw.slice(1,3),16),parseInt(raw.slice(3,5),16),1];const match=raw.match(/^rgba?\(\s*(\d+)[, ]+\s*(\d+)[, ]+\s*(\d+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/i);return match?[Number(match[1]),Number(match[2]),Number(match[3]),match[4]===undefined?1:Math.max(0,Math.min(1,Number(match[4])))]:null}
function luminance(rgb){const values=rgb.map(value=>{const v=value/255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return.2126*values[0]+.7152*values[1]+.0722*values[2]}
function contrastRatio(foreground,background){const fg=parseColor(foreground),bg=parseColor(background);if(!fg||!bg)return null;const a=luminance(fg),b=luminance(bg);return(Math.max(a,b)+.05)/(Math.min(a,b)+.05)}
function effectiveBackground(node){let current=node;while(current&&current!==document.documentElement){const style=getComputedStyle(current),image=style.backgroundImage||'none',opacity=Number(style.opacity||1),mix=style.mixBlendMode||'normal';if(image!=='none'||opacity<1||mix!=='normal'||current.dataset?.backgroundOverlay||current.classList?.contains('text-gradient'))return null;const value=style.backgroundColor,parsed=parseColor(value);if(parsed&&parsed[3]>=.999&&value!=='transparent')return value;current=current.parentElement}return null}
function diagnose(outer,model={}){const m=measurement(outer),warnings=[],size=m.computedSize||finite(model.fontSize,32,8,200),isLarge=size>=24||(size>=18&&String(model.fontWeight)==='700');if(size<10)warnings.push({code:'unreadable-size',severity:'error',message:`Computed text size ${size.toFixed(1)}px is unreadably small.`});else if(size<12)warnings.push({code:'small-size',severity:'warning',message:`Computed text size ${size.toFixed(1)}px may be difficult to read.`});if(m.overflow)warnings.push({code:'clipped-content',severity:'error',message:`Text is clipped by ${m.horizontalOverflow}px horizontally and ${m.verticalOverflow}px vertically.`});const columns=Math.round(finite(model.textColumns,1,1,3)),perColumn=(m.availableWidth-(columns-1)*finite(model.textColumnGap,24,0,64))/columns;if(columns>1&&perColumn<120)warnings.push({code:'excessive-columns',severity:'warning',message:`${columns} columns leave only ${Math.max(0,Math.round(perColumn))}px per column.`});if(outer){const color=getComputedStyle(outer).color,bg=effectiveBackground(outer),ratio=bg?contrastRatio(color,bg):null,minimum=isLarge?3:4.5;if(bg===null)warnings.push({code:'contrast-undetermined',severity:'info',message:'Contrast cannot be determined over images, gradients, transparency, overlays, or blend modes.'});else if(ratio!==null&&ratio<minimum)warnings.push({code:'insufficient-contrast',severity:'warning',message:`Contrast ratio ${ratio.toFixed(2)}:1 is below ${minimum}:1.`})}outer?.setAttribute?.('data-typography-overflow',m.overflow?'true':'false');outer?.setAttribute?.('aria-invalid',warnings.some(w=>w.severity==='error')?'true':'false');return{...m,warnings,ok:!warnings.some(w=>w.severity==='error')}}
function fitAndDiagnose(outer,model={},options={}){const fitResult=fit(outer,model,options),diagnostics=diagnose(outer,model);outer?.dispatchEvent?.(new CustomEvent('einvite:typography-diagnostics',{bubbles:true,detail:{model,fit:fitResult,diagnostics}}));return{fit:fitResult,diagnostics}}
function textNodes(root){if(!root?.ownerDocument)return[];const view=root.ownerDocument.defaultView||globalThis,filter=view.NodeFilter?.SHOW_TEXT||4,walker=root.ownerDocument.createTreeWalker(root,filter);const nodes=[];let node;while((node=walker.nextNode()))if(node.nodeValue)nodes.push(node);return nodes}
function renderedClusterLines(outer,locale='km'){
 const flow=outer?.querySelector?.(':scope > .typography-flow')||outer,clusters=[],violations=[];if(!flow?.ownerDocument)return{clusters,violations,ok:true};
 for(const node of textNodes(flow)){let offset=0;for(const segment of segmentGraphemes(node.nodeValue||'',locale)){const length=segment.length,range=flow.ownerDocument.createRange();range.setStart(node,offset);range.setEnd(node,offset+length);const rects=[...range.getClientRects()].filter(rect=>rect.width||rect.height),lines=[...new Set(rects.map(rect=>Math.round(rect.top*2)/2))];const entry={segment,start:offset,end:offset+length,lines,rectCount:rects.length};clusters.push(entry);if(segment.trim()&&lines.length>1)violations.push(entry);offset+=length}}
 return{clusters,violations,ok:violations.length===0&&preservesKhmerClusters(clusters.map(x=>x.segment).join(''),clusters.map(x=>x.segment))};
}
function assertRenderedClusterIntegrity(outer,locale='km'){const result=renderedClusterLines(outer,locale);outer?.setAttribute?.('data-khmer-cluster-integrity',result.ok?'true':'false');return result}
function installResponsive(root=document,options={}){
 const scope=root||document,selector=options.selector||'[data-text-auto-fit="fit"],[data-typography-model-version]',targetFor=options.targetFor||((source)=>source),modelFor=options.modelFor||((target)=>target?.__typographyModel||null),onResult=options.onResult||(()=>{}),delay=Math.max(0,Number(options.delay??48)),events=options.events||[],sources=new Set(),timers=new Map();
 const run=source=>{if(!source?.isConnected)return null;const target=targetFor(source);if(!target)return null;const model=modelFor(target,source);if(!model)return null;target.__typographyModel=model;const result=fitAndDiagnose(target,model);onResult(result,target,source,model);return result};
 const schedule=source=>{if(!source)return;clearTimeout(timers.get(source));timers.set(source,setTimeout(()=>{timers.delete(source);run(source)},delay))};
 const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(entries=>entries.forEach(entry=>schedule(entry.target))):null;
 const observe=(source,model)=>{if(!source)return source;sources.add(source);const target=targetFor(source);if(model&&target)target.__typographyModel=model;observer?.observe(source);return source};
 const discover=()=>{scope.querySelectorAll?.(selector).forEach(observe);return sources};
 discover();sources.forEach(run);
 const fontDone=()=>sources.forEach(schedule);document.fonts?.ready?.then(fontDone).catch(()=>{});document.fonts?.addEventListener?.('loadingdone',fontDone);
 const resize=()=>sources.forEach(schedule);addEventListener('resize',resize,{passive:true});
 const eventHandlers=events.map(name=>{const fn=()=>sources.forEach(schedule);addEventListener(name,fn);return[name,fn]});
 const mutation=options.observeMutations&&typeof MutationObserver!=='undefined'?new MutationObserver(()=>{discover();sources.forEach(source=>{if(!source.isConnected){observer?.unobserve(source);sources.delete(source)}})}):null;mutation?.observe(scope,{subtree:true,childList:true});
 const disconnect=()=>{observer?.disconnect();mutation?.disconnect();removeEventListener('resize',resize);document.fonts?.removeEventListener?.('loadingdone',fontDone);eventHandlers.forEach(([name,fn])=>removeEventListener(name,fn));timers.forEach(clearTimeout);timers.clear();sources.clear()};
 const refit=value=>{if(value==null){let last=null;sources.forEach(source=>{last=run(source)});return last}if(typeof value[Symbol.iterator]==='function'&&!value.nodeType){let last=null;for(const source of value){observe(source);last=run(source)}return last}observe(value);return run(value)};
 disconnect.observe=observe;disconnect.schedule=value=>{if(value==null)sources.forEach(schedule);else if(typeof value[Symbol.iterator]==='function'&&!value.nodeType)for(const source of value){observe(source);schedule(source)}else{observe(value);schedule(value)}};disconnect.refit=refit;disconnect.refresh=()=>{discover();return refit()};disconnect.disconnect=disconnect;return disconnect;
}
function renderThumbnail(root,{documentModel={},objects={},renderObject,project,width=390,height=844}={}){
 if(!root||typeof renderObject!=='function')return null;const doc=root.ownerDocument,entries=Object.entries(objects||{}).sort(([,a],[,b])=>Number(a?.zIndex||0)-Number(b?.zIndex||0)),markup=entries.map(([id,object])=>renderObject(object,{id,pageHeight:height,document:documentModel})).join('');
 const measurementHost=doc.createElement('div');measurementHost.className='typography-thumbnail-measurement';Object.assign(measurementHost.style,{position:'fixed',left:'-10000px',top:'0',width:`${width}px`,height:`${height}px`,overflow:'hidden',visibility:'hidden',pointerEvents:'none'});measurementHost.innerHTML=markup;doc.body.append(measurementHost);
 const measure=host=>entries.forEach(([id,object])=>{if(!['text','decoration'].includes(object?.type||'text'))return;const node=host.querySelector(`[data-object-id="${CSS.escape(id)}"]`);if(!node)return;const model=project?.(documentModel,object,{text:node.textContent||''})||node.__typographyModel;if(!model)return;node.__typographyModel=model;const result=fitAndDiagnose(node,model);node.querySelector(':scope > .v20-overflow-badge')?.remove();if(result.diagnostics.overflow){const badge=doc.createElement('span');badge.className='v20-overflow-badge';badge.textContent='!';badge.setAttribute('aria-label','Text overflow');node.append(badge)}});
 measure(measurementHost);const source=measurementHost.cloneNode(true);source.className='typography-thumbnail-source';Object.assign(source.style,{position:'absolute',left:'0',top:'0',width:`${width}px`,height:`${height}px`,transformOrigin:'top left',overflow:'hidden',visibility:'visible',pointerEvents:'none'});measurementHost.remove();root.append(source);
 const fitAll=()=>{const rect=root.getBoundingClientRect(),scale=rect.width>0&&rect.height>0?Math.min(rect.width/width,rect.height/height):0;source.style.transform=`scale(${scale})`;if(scale>0)measure(source)};requestAnimationFrame(fitAll);const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(fitAll):null;observer?.observe(root);document.fonts?.ready?.then(fitAll).catch(()=>{});return{source,refit:fitAll,disconnect:()=>observer?.disconnect()};
}
window.TypographyLayoutService=Object.freeze({segmentGraphemes,preservesKhmerClusters,styleObject,styleString,ensureFlow,applyToElement,availableSpace,measurement,fit,diagnose,fitAndDiagnose,contrastRatio,renderedClusterLines,assertRenderedClusterIntegrity,installResponsive,renderThumbnail});
})();;(()=>{
'use strict';
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const allowed=new Set(['BR','B','STRONG','I','EM','U','S','UL','OL','LI','SPAN','A']);
const dropWithContent=new Set(['SCRIPT','STYLE','IFRAME','OBJECT','EMBED','SVG','MATH','TEMPLATE','NOSCRIPT']);
const allowedStyles=new Set(['color','background-color','font-weight','font-style','text-decoration','text-align']);
function safeStyleValue(key,value){
  const v=String(value||'').trim();if(!v||/[\\<>]/.test(v)||/url\s*\(|expression\s*\(|javascript\s*:/i.test(v))return'';
  if(key==='color'||key==='background-color')return /^(?:#[0-9a-f]{3,8}|(?:rgb|rgba|hsl|hsla)\([0-9.,%\s+-]+\)|[a-z]{1,24})$/i.test(v)?v:'';
  if(key==='font-weight')return /^(?:normal|bold|[1-9]00)$/i.test(v)?v:'';
  if(key==='font-style')return /^(?:normal|italic|oblique)$/i.test(v)?v:'';
  if(key==='text-decoration')return /^(?:none|underline|line-through|overline)(?:\s+(?:underline|line-through|overline))*$/i.test(v)?v:'';
  if(key==='text-align')return /^(?:left|center|right|justify)$/i.test(v)?v:'';
  return'';
}
function safeHref(value){const raw=String(value||'').trim();if(!raw)return'';if(/^(?:https?:|mailto:|tel:)/i.test(raw)||raw.startsWith('/')||raw.startsWith('#'))return raw;return''}
function cleanNode(node,doc){
  if(node.nodeType===Node.TEXT_NODE)return doc.createTextNode(node.textContent||'');
  if(node.nodeType!==Node.ELEMENT_NODE)return doc.createTextNode('');
  if(dropWithContent.has(node.tagName))return doc.createTextNode('');
  if(!allowed.has(node.tagName)){const frag=doc.createDocumentFragment();[...node.childNodes].forEach(child=>frag.append(cleanNode(child,doc)));return frag}
  const el=doc.createElement(node.tagName.toLowerCase());
  if(node.tagName==='SPAN'&&node.getAttribute('style')){
    const safe=[];String(node.getAttribute('style')).split(';').forEach(pair=>{const [rawKey,...rest]=pair.split(':'),key=(rawKey||'').trim().toLowerCase(),value=safeStyleValue(key,rest.join(':'));if(allowedStyles.has(key)&&value)safe.push(`${key}:${value}`)});if(safe.length)el.setAttribute('style',safe.join(';'))
  }
  if(node.tagName==='A'){
    const href=safeHref(node.getAttribute('href'));if(href)el.setAttribute('href',href);
    const target=node.getAttribute('target');if(target==='_blank'){el.setAttribute('target','_blank');el.setAttribute('rel','noopener noreferrer')}
  }
  [...node.childNodes].forEach(child=>el.append(cleanNode(child,doc)));return el
}
function sanitizeRichText(html){
  const source=String(html??'');if(!source)return'';
  if(typeof document==='undefined')return esc(source.replace(/<(?:script|style|iframe|object|embed|svg|math|template|noscript)\b[^>]*>[\s\S]*?<\/\s*(?:script|style|iframe|object|embed|svg|math|template|noscript)\s*>/gi,'').replace(/<[^>]+>/g,''));
  const template=document.createElement('template');template.innerHTML=source;const out=document.createElement('div');[...template.content.childNodes].forEach(node=>out.append(cleanNode(node,document)));return out.innerHTML
}
function plainText(html){if(typeof document==='undefined')return String(html??'').replace(/<br\s*\/?\s*>/gi,'\n').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();const div=document.createElement('div');div.innerHTML=sanitizeRichText(html);return div.textContent||''}
function imageAdjustmentState(o={}){const state={...o};let layers=o.imageAdjustmentLayers||[];if(typeof layers==='string'){try{layers=JSON.parse(layers)}catch{layers=[]}}if(!Array.isArray(layers))layers=[];for(const layer of layers){if(!layer||layer.enabled===false)continue;const value=Number(layer.value||0);switch(layer.type){case'brightness':state.imageBrightness=Number(state.imageBrightness??100)+value;break;case'contrast':state.imageContrast=Number(state.imageContrast??100)+value;break;case'saturation':state.imageSaturation=Number(state.imageSaturation??100)+value;break;case'hue':state.imageHue=Number(state.imageHue||0)+value;break;case'blur':state.imageBlur=Number(state.imageBlur||0)+Math.max(0,value);break;case'grayscale':state.imageGrayscale=Math.max(Number(state.imageGrayscale||0),value);break;case'sepia':state.imageSepia=Math.max(Number(state.imageSepia||0),value);break;case'vibrance':state.imageVibrance=Number(state.imageVibrance||0)+value;break;case'temperature':state.imageTemperature=Number(state.imageTemperature||0)+value;break;case'gamma':state.imageGamma=Number(state.imageGamma||1)*Math.max(.25,value||1);break}}return state}
function imageFilterStyle(o={}){o=imageAdjustmentState(o);const clamp=(v,min,max,fallback)=>Math.max(min,Math.min(max,Number(v??fallback))),vibrance=clamp(o.imageVibrance,-100,100,0),temperature=clamp(o.imageTemperature,-100,100,0),saturation=clamp(o.imageSaturation,0,250,100)*(1+vibrance/250),sepia=Math.max(0,Math.min(100,clamp(o.imageSepia,0,100,0)+Math.max(0,temperature)*.18)),hue=clamp(o.imageHue,-180,180,0)+temperature*.08,levelsBlack=clamp(o.imageLevelsBlack,0,80,0),levelsWhite=clamp(o.imageLevelsWhite,20,100,100),levelRange=Math.max(20,levelsWhite-levelsBlack),gamma=clamp(o.imageGamma,.25,3,1),shadows=clamp(o.imageCurveShadows,-100,100,0),highlights=clamp(o.imageCurveHighlights,-100,100,0),gammaBrightness=100+(1-gamma)*28,curveBrightness=shadows*.10+highlights*.06,curveContrast=(highlights-shadows)*.12,contrast=clamp(o.imageContrast,20,200,100)*(100/levelRange)+curveContrast,brightness=clamp(o.imageBrightness,20,200,100)*(1-levelsBlack/220)*((gammaBrightness+curveBrightness)/100);return`brightness(${Math.max(15,Math.min(240,brightness))}%) contrast(${Math.max(15,Math.min(260,contrast))}%) saturate(${saturation}%) grayscale(${clamp(o.imageGrayscale,0,100,0)}%) sepia(${sepia}%) hue-rotate(${hue}deg) blur(${clamp(o.imageBlur,0,20,0)}px)`}
function imageTransformStyle(o={}){const px=Math.max(-60,Math.min(60,Number(o.imagePerspectiveX||0))),py=Math.max(-60,Math.min(60,Number(o.imagePerspectiveY||0))),wx=Math.max(-30,Math.min(30,Number(o.imageWarpX||0))),wy=Math.max(-30,Math.min(30,Number(o.imageWarpY||0)));return`perspective(900px) rotateY(${px}deg) rotateX(${py}deg) skew(${wx}deg,${wy}deg) scaleX(${o.imageFlipX?-1:1}) scaleY(${o.imageFlipY?-1:1})`}
function imageMaskStyle(o={}){const feather=Math.max(0,Math.min(50,Number(o.imageMaskFeather||0))),strength=Math.max(0,Math.min(100,Number(o.imageGradientMask||0)));if(!strength&&!feather)return'';const edge=Math.max(0,100-feather),alpha=Math.max(0,Math.min(1,strength/100));return`-webkit-mask-image:linear-gradient(to bottom,rgba(0,0,0,1) 0%,rgba(0,0,0,1) ${edge}%,rgba(0,0,0,${1-alpha}) 100%);mask-image:linear-gradient(to bottom,rgba(0,0,0,1) 0%,rgba(0,0,0,1) ${edge}%,rgba(0,0,0,${1-alpha}) 100%);`}
function objectDimension(value,axis='x'){if(!value)return axis==='x'?'50%':'80px';if(String(value).includes('%'))return value;const number=parseFloat(value);if(!Number.isFinite(number))return value;return`${number/(axis==='x'?390:844)*100}%`}
function animationName(value){return({'fade-up':'fadeUp','soft-zoom':'softZoom','slide-left':'slideLeft','blur-in':'blurIn','bounce-in':'bounceIn','flip-in':'flipIn','float':'floatIn','none':'none'})[value]||'fadeUp'}
function advancedObjectStyle(o={}){const blend=['normal','multiply','screen','overlay','soft-light','darken','lighten'].includes(o.blendMode)?o.blendMode:'normal';const delay=Math.max(0,Math.min(5000,Number(o.animationDelay||0)));let background='transparent';if(o.backgroundEnabled){const hex=/^#[0-9a-f]{6}$/i.test(o.backgroundColor||'')?o.backgroundColor:'#ffffff',alpha=Math.max(0,Math.min(100,Number(o.backgroundOpacity??100)))/100,h=hex.slice(1);background=`rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${alpha})`}return`mix-blend-mode:${blend};background:${background};animation-delay:${delay}ms`}
function advancedTextStyle(o={}){const transform=['none','uppercase','lowercase','capitalize'].includes(o.textTransform)?o.textTransform:'none',stroke=Math.max(0,Math.min(8,Number(o.textStrokeWidth||0))),strokeColor=/^#[0-9a-f]{6}$/i.test(o.textStrokeColor||'')?o.textStrokeColor:'#ffffff',shadowBlur=Math.max(0,Math.min(40,Number(o.textShadowBlur||0))),shadowColor=/^#[0-9a-f]{6}$/i.test(o.textShadowColor||'')?o.textShadowColor:'#000000',shadow=shadowBlur?`text-shadow:0 ${Math.max(1,Math.round(shadowBlur/4))}px ${shadowBlur}px ${shadowColor};`:'',gradient=o.textGradientEnabled?`background-image:linear-gradient(${Math.max(0,Math.min(360,Number(o.textGradientAngle||90)))}deg,${esc(o.textGradientStart||'#9d4555')},${esc(o.textGradientEnd||'#b58a3a')});background-clip:text;-webkit-background-clip:text;color:transparent;`:'';return`text-transform:${transform};-webkit-text-stroke:${stroke}px ${strokeColor};${shadow}${gradient}`}
function typographyProjection(o={},documentModel={},options={}){
 const documentData=documentModel&&typeof documentModel==='object'?documentModel:{};
 if(globalThis.TypographyDocumentModel){const catalog=TypographyDocumentModel.normalizeCatalog(documentData.typography||{}),normalized=o.typographyModelVersion?o:TypographyDocumentModel.normalizeObject(options.id||o.id||'',o,catalog);return TypographyDocumentModel.resolveObjectTypography({...documentData,typography:catalog},normalized,{text:options.text??plainText(o.html||''),locale:options.locale})}
 const t=globalThis.EInviteTypography?.normalizeTypography?globalThis.EInviteTypography.normalizeTypography(o):{...o,font:'noto-serif',fontSize:32,textAutoFit:'none',textAutoFitMax:32,textMinFontSize:10,textWrap:'normal',textColumns:1,textColumnGap:24,textAlign:'center'};
 return{...t,fontStack:globalThis.EInviteFontRegistry?.stack?EInviteFontRegistry.stack(t.font):"Georgia,serif",locale:/[\u1780-\u17ff]/u.test(String(options.text||o.html||''))?'km':'en'}
}
function typographyFontStack(font){return globalThis.EInviteFontRegistry?.stack?globalThis.EInviteFontRegistry.stack(font):'Georgia,serif'}
function typographyLayoutStyle(model={}){if(!globalThis.TypographyLayoutService)throw new Error('TypographyLayoutService must load before renderer-core.js');return TypographyLayoutService.styleString(TypographyLayoutService.styleObject(model).flow)}
function typographyOuterStyle(model={}){if(!globalThis.TypographyLayoutService)throw new Error('TypographyLayoutService must load before renderer-core.js');return TypographyLayoutService.styleString(TypographyLayoutService.styleObject(model).outer)}
function renderedElementModel(node){if(node?.__typographyModel)return node.__typographyModel;if(!node)return null;const style=getComputedStyle(node);return{styleId:node.dataset.textStyleId||'body',font:node.dataset.font||'noto-serif',fontPairing:node.dataset.fontPairing||'serif-formal',fontStack:style.fontFamily,fontSize:Number(node.dataset.fontSize||parseFloat(style.fontSize)||32),textAutoFit:node.dataset.textAutoFit==='fit'?'fit':'none',textAutoFitMax:Number(node.dataset.textAutoFitMax||node.dataset.fontSize||32),textMinFontSize:Number(node.dataset.textMinFontSize||10),fontWeight:style.fontWeight==='700'?'700':'400',fontStyle:style.fontStyle==='italic'?'italic':'normal',lineHeight:Number.parseFloat(style.lineHeight)/Math.max(1,Number.parseFloat(style.fontSize))||1.35,letterSpacing:Number.parseFloat(style.letterSpacing)||0,textAlign:node.dataset.textAlign||style.textAlign||'left',textVerticalAlign:style.justifyContent==='flex-start'?'top':style.justifyContent==='flex-end'?'bottom':'middle',textWrap:node.dataset.textWrap||'normal',textColumns:Number(node.dataset.textColumns||1),textColumnGap:Number(node.dataset.textColumnGap||24),textPadding:Number.parseFloat(style.padding)||0,locale:node.lang==='km'?'km':'en',color:style.color}}
function fitTypographyElement(outer,{set=true,model=null}={}){if(!outer)return null;const resolved=model||renderedElementModel(outer);if(!resolved)return null;const result=TypographyLayoutService.fit(outer,resolved,{set});return result?.computedSize??null}
function installResponsiveTypography(root=document){return TypographyLayoutService.installResponsive(root,{modelFor:renderedElementModel})}
const RendererAdapters=Object.freeze({
 project(documentModel,object,options={}){return typographyProjection(object,documentModel,options)},
 outerStyle(model){return typographyOuterStyle(model)},
 flowStyle(model){return typographyLayoutStyle(model)},
 attributes(model){return`data-typography-v19="true" data-typography-model-version="1" data-text-style-id="${esc(model.styleId||'body')}" data-font-pairing="${esc(model.fontPairing||'serif-formal')}" data-font="${esc(model.compatibilityFont||model.font)}" data-font-size="${model.fontSize}" data-text-auto-fit="${model.textAutoFit}" data-text-auto-fit-max="${model.textAutoFitMax}" data-text-min-font-size="${model.textMinFontSize}" data-text-wrap="${model.textWrap}" data-text-columns="${model.textColumns}" data-text-column-gap="${model.textColumnGap}" data-text-align="${model.textAlign}" lang="${model.locale==='km'?'km':'en'}"`},
 renderThumbnail(root,documentModel,objects,options={}){return TypographyLayoutService.renderThumbnail(root,{documentModel,objects,renderObject,project:RendererAdapters.project,...options})}
});
function shapeFillStyle(o={}){return o.fillMode==='gradient'?`linear-gradient(${Math.max(0,Math.min(360,Number(o.gradientAngle||135)))}deg,${esc(o.gradientStart||'#d9a6ad')},${esc(o.gradientEnd||'#9d4555')})`:esc(o.fillColor||'#d9a6ad')}
function responsiveImageAttributes(o={}){
 const src=String(o.src||''),width=Math.max(0,Number(o.intrinsicWidth||0)),height=Math.max(0,Number(o.intrinsicHeight||0));
 let attrs='';if(width&&height)attrs+=` width="${Math.round(width)}" height="${Math.round(height)}"`;
 const match=src.match(/^\/uploads\/([^?#]+)$/i),explicit=String(o.responsiveBase||'').trim();let base='';
 if(/^\/api\/(?:image|media)\/[^#]+$/i.test(explicit))base=explicit;else if(/^\/api\/media\/[^#]+$/i.test(src))base=src;else if(match&&!/\.gif$/i.test(match[1]))base=`/api/image/${encodeURIComponent(decodeURIComponent(match[1]))}`;
 if(base&&!/\.gif(?:$|[?#])/i.test(src)){const safe=esc(base),join=base.includes('?')?'&amp;':'?';attrs+=` srcset="${safe}${join}w=480&amp;format=webp 480w, ${safe}${join}w=960&amp;format=webp 960w, ${safe}${join}w=1440&amp;format=webp 1440w, ${safe}${join}w=1920&amp;format=webp 1920w" sizes="(max-width: 600px) 100vw, (max-width: 1200px) 80vw, 1200px"`}
 return attrs
}
function renderObject(o={},options={}){
 const id=options.id||'',pageHeight=Number(options.pageHeight||844),content=options.content!==undefined?options.content:(globalThis.RichTextRenderer?.renderObject(o,options.document||{},options)||sanitizeRichText(o.html||'')),heroTitle=!!options.heroTitle;
 const borderWidth=Math.max(0,Math.min(12,Number(o.borderWidth||0))),borderRadius=Math.max(0,Math.min(120,Number(o.borderRadius||0))),shadowBlur=Math.max(0,Math.min(60,Number(o.shadowBlur||0))),opacity=Math.max(.1,Math.min(1,Number(o.opacity??1))),shadow=shadowBlur?`0 ${Math.max(2,Math.round(shadowBlur/3))}px ${shadowBlur}px ${esc(o.shadowColor||'#000000')}55`:'none';
 const height=String(o.height||'80px').includes('%')?o.height:`${parseFloat(o.height||80)/pageHeight*100}%`,top=String(o.top||'0').includes('%')?o.top:`${parseFloat(o.top||0)/pageHeight*100}%`;
 const common=`left:${esc(o.left||'0')};top:${esc(top)};width:${esc(objectDimension(o.width,'x'))};height:${esc(height)};z-index:${Number(o.zIndex||1)};transform:rotate(${Number(o.rotation||0)}deg);opacity:${opacity};border:${borderWidth}px solid ${esc(o.borderColor||'#ffffff')};border-radius:${borderRadius}px;box-shadow:${shadow};animation-name:${animationName(o.animation)};animation-duration:${Math.max(300,Math.min(3000,Number(o.duration||900)))}ms;${advancedObjectStyle(o)}`;
 if(o.type==='image'&&o.src){const masks={none:'none',circle:'ellipse(50% 50% at 50% 50%)',arch:'inset(0 round 48% 48% 12% 12%)',diamond:'polygon(50% 0,100% 50%,50% 100%,0 50%)',hexagon:'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)',blob:'polygon(50% 0,78% 8%,96% 35%,91% 72%,66% 100%,31% 94%,6% 68%,0 32%,22% 7%)'},frames={none:['0','transparent'],white:['8px','#ffffff'],gold:['8px','#c79b42'],dark:['8px','#201b1b']},frame=frames[o.imageFrame||'none']||frames.none;return`<div class="published-object published-image reveal" data-object-id="${esc(id)}" style="${common};${o.dominantColor?`background:${esc(o.dominantColor)};`:''}"><img src="${esc(o.src)}"${responsiveImageAttributes(o)} alt="${esc(o.alt||'Invitation image')}" loading="lazy" decoding="async" style="object-fit:${esc(o.imageFit||'cover')};object-position:${Number(o.imagePositionX??50)}% ${Number(o.imagePositionY??50)}%;border-radius:inherit;clip-path:${masks[o.imageMask||'none']||'none'};padding:${frame[0]};background:${frame[1]};box-sizing:border-box;filter:${imageFilterStyle(o)};transform:${imageTransformStyle(o)};${imageMaskStyle(o)}"></div>`}
 if(o.type==='shape'){const kind=['rectangle','circle','line'].includes(o.shapeKind)?o.shapeKind:'rectangle',radius=kind==='circle'?'999px':'inherit';return`<div class="published-object published-shape published-shape-${kind} reveal" data-object-id="${esc(id)}" aria-hidden="true" style="${common};background:${shapeFillStyle(o)};border-radius:${radius}"></div>`}
 const t=RendererAdapters.project(options.document||{},o,{id,text:plainText(content),locale:options.locale});
 const outerStyle=RendererAdapters.outerStyle(t),flowStyle=RendererAdapters.flowStyle(t),attrs=RendererAdapters.attributes(t);
 return`<div class="published-object published-text reveal${heroTitle?' hero-object-title':''}${o.type==='decoration'?' published-decoration':''}" data-object-id="${esc(id)}" ${attrs} style="${common};${outerStyle}${advancedTextStyle(o)}"><div class="typography-flow" style="${flowStyle}">${content}</div></div>`
}
window.EInviteTypographyRendererAdapters=RendererAdapters;
window.EInviteRenderer={esc,sanitizeRichText,plainText,RendererAdapters,typographyProjection,typographyFontStack,typographyLayoutStyle,typographyOuterStyle,fitTypographyElement,installResponsiveTypography,imageFilterStyle,imageTransformStyle,imageMaskStyle,objectDimension,animationName,advancedObjectStyle,advancedTextStyle,shapeFillStyle,responsiveImageAttributes,renderObject};
})();;(()=>{
'use strict';
const ensureStack=()=>{let stack=document.querySelector('.ei-toast-stack');if(!stack){stack=document.createElement('div');stack.className='ei-toast-stack';stack.setAttribute('aria-live','polite');document.body.append(stack)}return stack};
function toast(message,options={}){
  const text=String(message??'');if(!text)return;
  const stack=ensureStack(),item=document.createElement('div');item.className=`ei-toast ${options.type||''}`.trim();
  const icon=options.icon||(options.type==='error'?'!':options.type==='success'?'✓':'✦');
  item.innerHTML=`<span class="ei-toast-icon"></span><strong></strong><button type="button" aria-label="Dismiss">×</button>`;
  item.querySelector('.ei-toast-icon').textContent=icon;item.querySelector('strong').textContent=text;
  const close=()=>{if(item.classList.contains('out'))return;item.classList.add('out');setTimeout(()=>item.remove(),190)};item.querySelector('button').onclick=close;stack.append(item);setTimeout(close,Math.max(1500,Number(options.duration||3600)));return item
}
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label>Value</label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('.ei-dialog-message').textContent=message;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input');host.hidden=false;field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';host.append(field)}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel'});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};
})();;(()=>{
 'use strict';
 const LAST_KEY='sovan-active-invite';
 const routeMatch=location.pathname.match(/\/invitations\/([^/]+)\/(editor|guests|responses|analytics|materials|checkin)\/?$/i);
 const queryId=new URLSearchParams(location.search).get('invitation');
 const routeId=routeMatch?decodeURIComponent(routeMatch[1]):'';
 const explicitId=routeId||queryId||'';
 const section=routeMatch?.[2]?.toLowerCase()||'';
 const safe=id=>String(id||'').trim();
 function getInvitationId(options={}){const direct=safe(explicitId);if(direct)return direct;if(options.allowRemembered===false)return '';return safe(localStorage.getItem(LAST_KEY))}
 function remember(id){id=safe(id);if(id)localStorage.setItem(LAST_KEY,id);return id}
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
})();;if('scrollRestoration'in history)history.scrollRestoration='manual';
const $=s=>document.querySelector(s),accountKey='sovan-account-v1',invitesKey='sovan-multi-invites-v1',localTemplatesKey='sovan-full-invitation-templates-v1';localStorage.removeItem('sovan-auth-token');
const seed=[{id:'demo-wedding',title:'Sophea & Dara',type:'Wedding',status:'Published',views:128,rsvps:34,updatedAt:new Date().toISOString()}];
let account=JSON.parse(localStorage.getItem(accountKey)||'null'),invites=JSON.parse(localStorage.getItem(invitesKey)||'null')||seed,server=false,userTemplates=[],marketTemplates=[],templateFilter='all';
const dashboardThumbnailControllers=new Map();let dashboardRichTextAssets;
function disconnectDashboardThumbnails(){for(const controller of dashboardThumbnailControllers.values())try{controller?.disconnect?.()}catch{}dashboardThumbnailControllers.clear()}
function ensureDashboardRichTextRenderer(){if(globalThis.RichTextRenderer)return Promise.resolve();if(dashboardRichTextAssets)return dashboardRichTextAssets;dashboardRichTextAssets=new Promise((resolve,reject)=>{if(!document.querySelector('link[data-rich-text-renderer]')){const link=document.createElement('link');link.rel='stylesheet';link.href='rich-text-renderer-v21.css';link.dataset.richTextRenderer='true';document.head.append(link)}const script=document.createElement('script');script.src='rich-text-renderer-v21.js';script.defer=true;script.dataset.richTextRenderer='true';script.onload=resolve;script.onerror=()=>reject(new Error('Rich-text thumbnail renderer failed to load.'));document.head.append(script)});return dashboardRichTextAssets}
async function hydrateDashboardThumbnails(){disconnectDashboardThumbnails();if(!globalThis.EInviteTypographyRendererAdapters?.renderThumbnail)return;try{await ensureDashboardRichTextRenderer()}catch(error){console.warn('Dashboard thumbnail renderer unavailable',error);document.querySelectorAll('[data-dashboard-thumbnail]').forEach(root=>root.dataset.thumbnailError='true');return}document.querySelectorAll('[data-dashboard-thumbnail]').forEach(root=>{const id=root.dataset.dashboardThumbnail,item=invites.find(x=>String(x.id)===String(id));if(!item)return;try{let doc=item.document||null;if(!doc&&!server)try{doc=JSON.parse(localStorage.getItem(`sovan-invite-draft-v3:${id}`)||'null')}catch{};if(!doc)return;const controller=EInviteTypographyRendererAdapters.renderThumbnail(root,doc,doc.objects||{}, {width:390,height:844});if(controller)dashboardThumbnailControllers.set(id,controller)}catch(error){console.warn('Dashboard thumbnail unavailable',error);root.dataset.thumbnailError='true'}})}
addEventListener('pagehide',disconnectDashboardThumbnails);addEventListener('beforeunload',disconnectDashboardThumbnails);
const clone=v=>structuredClone(v);
async function request(path,options={}){let r=await fetch(path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}});let data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data}
const templateCatalog=[
 {id:'rose',name:'Royal Rose',category:'Wedding',tone:'rose',description:'Romantic editorial arches, layered photo pages, warm rose palette.',pages:3,tags:['Romantic','Editorial']},
 {id:'gold',name:'Khmer Gold',category:'Wedding',tone:'gold',description:'Formal ceremonial structure with Khmer-inspired gold framing.',pages:3,tags:['Khmer','Ceremonial']},
 {id:'emerald',name:'Emerald Garden',category:'Wedding',tone:'emerald',description:'Botanical storytelling with airy photo features and organic cards.',pages:4,tags:['Garden','Natural']},
 {id:'midnight',name:'Midnight Luxury',category:'Wedding',tone:'midnight',description:'Cinematic dark invitation with luminous glass-like page treatments.',pages:3,tags:['Luxury','Cinematic']},
 {id:'birthday-pop',name:'Celebration Pop',category:'Birthday',tone:'rose',description:'Bright modern birthday layout with photo collage and event highlights.',pages:3,tags:['Birthday','Modern']},
 {id:'business-ivory',name:'Ivory Executive',category:'Business',tone:'ivory',description:'Clean professional invitation with agenda, speakers, and venue focus.',pages:3,tags:['Business','Formal']},
 {id:'khmer-ivory',name:'Khmer Ivory Ceremony',category:'Wedding',tone:'gold',description:'Refined ivory ceremonial invitation with Khmer-inspired typography and restrained gold detail.',pages:3,tags:['Khmer','Ivory','Ceremony']},
 {id:'modern-minimal',name:'Modern Minimal',category:'Wedding',tone:'ivory',description:'Editorial white-space layout with crisp typography and understated motion.',pages:3,tags:['Minimal','Modern']},
 {id:'botanical-blush',name:'Botanical Blush',category:'Wedding',tone:'rose',description:'Soft botanical storytelling with blush surfaces and romantic editorial pages.',pages:4,tags:['Botanical','Blush']},
 {id:'black-gold-gala',name:'Black & Gold Gala',category:'Business',tone:'midnight',description:'Premium dark event invitation for galas, launches, awards, and formal evenings.',pages:3,tags:['Gala','Luxury']},
 {id:'birthday-neon',name:'Neon Night Birthday',category:'Birthday',tone:'midnight',description:'Energetic dark birthday design with vivid accent colors and playful photo pages.',pages:3,tags:['Birthday','Neon']},
 {id:'corporate-launch',name:'Corporate Launch',category:'Business',tone:'emerald',description:'Modern launch-event layout with bold feature pages, agenda, and RSVP flow.',pages:3,tags:['Launch','Corporate']}
];
function baseDocument(title,type,theme='rose'){
 const presets={Wedding:{message:'Together with our families, we warmly invite you to celebrate our wedding.',messageKm:'ជាមួយនឹងក្រុមគ្រួសាររបស់យើង យើងខ្ញុំសូមគោរពអញ្ជើញលោកអ្នកចូលរួមអបអរសាទរពិធីមង្គលការរបស់យើង។',venue:'Your wedding venue',venueKm:'ទីតាំងពិធីមង្គលការ',schedule:[{time:'4:00 PM',title:'Guest arrival',titleKm:'ទទួលភ្ញៀវ'},{time:'5:00 PM',title:'Wedding ceremony',titleKm:'ពិធីមង្គលការ'},{time:'6:30 PM',title:'Dinner reception',titleKm:'ពិសាអាហារពេលល្ងាច'}]},Birthday:{message:'Join us for a joyful birthday celebration!',messageKm:'សូមអញ្ជើញចូលរួមអបអរសាទរពិធីខួបកំណើតដ៏រីករាយរបស់យើង!',venue:'Party venue',venueKm:'ទីតាំងពិធីខួបកំណើត',schedule:[{time:'4:00 PM',title:'Guest arrival',titleKm:'ទទួលភ្ញៀវ'},{time:'5:00 PM',title:'Cake and celebration',titleKm:'កាត់នំ និងអបអរសាទរ'}]},Business:{message:'You are warmly invited to join us for this special business event.',messageKm:'សូមគោរពអញ្ជើញលោកអ្នកចូលរួមកម្មវិធីធុរកិច្ចដ៏ពិសេសនេះ។',venue:'Event venue',venueKm:'ទីតាំងកម្មវិធី',schedule:[{time:'8:30 AM',title:'Registration',titleKm:'ចុះឈ្មោះ'},{time:'9:00 AM',title:'Opening program',titleKm:'កម្មវិធីបើក'},{time:'12:00 PM',title:'Networking lunch',titleKm:'អាហារថ្ងៃត្រង់ និងបណ្តាញទំនាក់ទំនង'}]}};
 const themes={rose:{accent:'#9d4555',opening:'soft',gallery:'grid'},gold:{accent:'#a87616',opening:'curtain',gallery:'grid'},emerald:{accent:'#1f7158',opening:'soft',gallery:'full'},midnight:{accent:'#8065c7',opening:'night',gallery:'filmstrip'}};
 const p=presets[type]||presets.Wedding,t=themes[theme]||themes.rose;
 return {eventType:type,templateId:theme,fields:{names:title,namesKm:'',date:'2026-12-27',time:'16:00',venue:p.venue,venueKm:p.venueKm,message:p.message,messageKm:p.messageKm},settings:{rsvpEnabled:true,scheduleEnabled:true,venueEnabled:true,galleryEnabled:true,countdownEnabled:true,musicEnabled:false,openingEnabled:true,contactEnabled:true},languageMode:'both',contactPhone:'',contactTelegram:'',dateFormat:'both',khmerDate:'',countdownTitle:'Counting down to our celebration',countdownTitleKm:'រាប់ថយក្រោយទៅកាន់ថ្ងៃដ៏ពិសេសរបស់យើង',theme:theme,openingStyle:t.opening,galleryStyle:t.gallery,galleryOrder:[],sectionOrder:['gallery','countdown','schedule','custom','venue','contact','rsvp'],sectionAnimations:{hero:{preset:'fade-up',duration:900},gallery:{preset:'fade-up',duration:900},countdown:{preset:'soft-zoom',duration:900},schedule:{preset:'fade-up',duration:900},custom:{preset:'fade-up',duration:900},venue:{preset:'fade-up',duration:900},contact:{preset:'fade-up',duration:900},rsvp:{preset:'fade-up',duration:900}},sectionLayouts:{countdown:'cards',schedule:'timeline',custom:'cards',venue:'cards'},sectionStyles:{},schedule:p.schedule,venues:[],customBlocks:[],designPages:[],masterPageStyle:{enabled:false,background:'#fffaf6',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0},music:null,mapUrl:'',accent:t.accent,palettePreset:'template',palette:{background:'#fff8f2',surface:'#ffffff',text:'#342c26',heading:t.accent},objects:{}}
}
function textObj(id,html,left,top,width,height,size=34,color='#342c26',font='serif-georgia'){return{id,type:'text',left,top,width,height,html,font,color,fontSize:size,textAlign:'center',fontWeight:'400',fontStyle:'normal',letterSpacing:0,lineHeight:1.35,opacity:1,borderWidth:0,borderColor:'#ffffff',borderRadius:0,shadowBlur:0,shadowColor:'#000000',animation:'fade-up',duration:'900',rotation:0,showInHero:true,showInGallery:false,zIndex:2}}
function shapeObj(id,left,top,width,height,fill,kind='rectangle',radius=0){return{id,type:'shape',left,top,width,height,fillColor:fill,shapeKind:kind,opacity:.75,borderWidth:0,borderColor:'#ffffff',borderRadius:radius,shadowBlur:0,shadowColor:'#000000',animation:'none',duration:'900',rotation:0,showInHero:true,showInGallery:false,zIndex:1}}
function page(id,name,preset,bg,objects,transition='soft'){return{id,name,preset,enabled:true,background:bg,backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0,useMasterBackground:true,animation:{preset:'fade-up',duration:900},transition:{preset:transition,duration:600},objects}}
function enrichBuiltin(doc,id){
 const style=(name,bg,text,radius=18)=>({backgroundEnabled:true,background:bg,textColorEnabled:true,textColor:text,radius,backgroundImageEnabled:false,backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0});
 if(id==='rose'){
  doc.theme='rose';doc.templateId=id;doc.palettePreset='rose';doc.palette={background:'#fff7f3',surface:'#fffdfb',text:'#412e32',heading:'#9d4555'};doc.accent='#9d4555';doc.masterPageStyle={enabled:true,background:'#fff7f3',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};
  doc.objects={title:textObj('title',doc.fields.names,'8%','9%','84%','110px',52,'#783744'),subtitle:textObj('subtitle',doc.fields.message,'14%','30%','72%','110px',22,'#5e474b'),roseArc:shapeObj('rose-arc','12%','51%','76%','270px','#d9a6ad','rectangle',130),details:textObj('details','27 December 2026<br>Your wedding venue','14%','84%','72%','90px',21,'#783744')};
  doc.designPages=[page('rose-story','Our Story','story','#fff7f3',{storyTitle:textObj('storyTitle','Our Story','12%','15%','76%','80px',44,'#9d4555'),storyBody:textObj('storyBody','A beautiful chapter begins here. Add your own story, memories, or a meaningful message.','15%','36%','70%','210px',21,'#4d3b3f')}),page('rose-photo','Photo Feature','photo','#f0d9d8',{photoTitle:textObj('photoTitle','A Moment to Remember','10%','12%','80%','75px',38,'#783744'),photoFrame:shapeObj('photoFrame','12%','30%','76%','430px','#fffaf6','rectangle',130)}),page('rose-thanks','Thank You','thankyou','#9d4555',{thanks:textObj('thanks','With love, thank you for celebrating with us.','12%','37%','76%','180px',34,'#ffffff')},'overlap')];
  doc.sectionOrder=['page:rose-story','gallery','page:rose-photo','countdown','schedule','custom','venue','contact','rsvp','page:rose-thanks'];doc.sectionStyles={gallery:style('gallery','#fffdfb','#412e32',28),countdown:style('countdown','#f6e3e1','#412e32',28),schedule:style('schedule','#fffdfb','#412e32',28),custom:style('custom','#fff7f3','#412e32',28),venue:style('venue','#fffdfb','#412e32',28),contact:style('contact','#f6e3e1','#412e32',28),rsvp:style('rsvp','#fffdfb','#412e32',28)}
 } else if(id==='gold'){
  doc.theme='gold';doc.templateId=id;doc.palettePreset='gold';doc.palette={background:'#fffaf0',surface:'#fffef9',text:'#3c2b18',heading:'#9b6b13'};doc.accent='#a87616';doc.openingStyle='curtain';doc.masterPageStyle={enabled:true,background:'#fff8e7',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};
  doc.objects={goldFrame:shapeObj('goldFrame','7%','6%','86%','880px','#fff8e7','rectangle',4),title:textObj('title',doc.fields.names,'12%','15%','76%','110px',50,'#81550b',"noto-serif-khmer"),subtitle:textObj('subtitle',doc.fields.message,'15%','39%','70%','130px',21,'#4a3821'),details:textObj('details','27 December 2026<br>Your wedding venue','14%','75%','72%','100px',23,'#81550b')};
  doc.designPages=[page('gold-ceremony','Ceremony','ceremony','#fff8e7',{head:textObj('head','Ceremony Program','12%','13%','76%','90px',42,'#9b6b13'),body:textObj('body','Traditional ceremonies, blessings, and celebration details can be presented here.','13%','34%','74%','230px',22,'#3c2b18'),diamond:shapeObj('diamond','40%','68%','20%','120px','#d9b65d','rectangle',0)}),page('gold-details','Formal Details','details','#f2dfab',{head:textObj('head','With Honour & Joy','10%','17%','80%','100px',46,'#725015'),body:textObj('body','Please join our families for this auspicious celebration.','14%','44%','72%','180px',24,'#3c2b18')}),page('gold-thanks','Blessings','thankyou','#8a641d',{thanks:textObj('thanks','Your presence and blessings are deeply appreciated.','12%','38%','76%','180px',34,'#fff9e8')},'sweep')];
  doc.sectionOrder=['page:gold-ceremony','schedule','page:gold-details','gallery','countdown','custom','venue','contact','rsvp','page:gold-thanks'];doc.sectionLayouts={countdown:'pill',schedule:'timeline',custom:'editorial',venue:'stacked'};doc.sectionStyles={gallery:style('gallery','#fffef9','#3c2b18',8),countdown:style('countdown','#f2dfab','#3c2b18',8),schedule:style('schedule','#fff8e7','#3c2b18',8),custom:style('custom','#fffef9','#3c2b18',8),venue:style('venue','#fff8e7','#3c2b18',8),contact:style('contact','#f2dfab','#3c2b18',8),rsvp:style('rsvp','#fffef9','#3c2b18',8)}
 } else if(id==='emerald'){
  doc.theme='emerald';doc.templateId=id;doc.palettePreset='emerald';doc.palette={background:'#eff8f2',surface:'#ffffff',text:'#263c34',heading:'#1f7158'};doc.accent='#1f7158';doc.masterPageStyle={enabled:true,background:'#edf7f0',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};
  doc.objects={leaf:shapeObj('leaf','4%','5%','38%','210px','#9bc9af','circle',120),title:textObj('title',doc.fields.names,'13%','18%','74%','120px',50,'#1f7158'),subtitle:textObj('subtitle',doc.fields.message,'13%','40%','74%','135px',22,'#354c43'),details:textObj('details','27 December 2026<br>Your wedding venue','15%','77%','70%','100px',22,'#1f7158')};
  doc.designPages=[page('garden-story','Our Story','story','#edf7f0',{head:textObj('head','Growing Together','12%','12%','76%','90px',42,'#1f7158'),body:textObj('body','Tell the story that brought you here and the future you are growing together.','13%','34%','74%','220px',22,'#354c43')}),page('garden-collage','Our Moments','collage','#d9eee2',{head:textObj('head','Our Favourite Moments','10%','8%','80%','85px',38,'#1f7158'),a:shapeObj('a','8%','26%','40%','300px','#ffffff','rectangle',28),b:shapeObj('b','52%','35%','40%','300px','#ffffff','rectangle',28)}),page('garden-details','Celebration','details','#edf7f0',{head:textObj('head','Celebrate With Us','10%','16%','80%','90px',42,'#1f7158'),body:textObj('body','Event schedule, dress code, and thoughtful details can live here.','12%','39%','76%','190px',22,'#354c43')}),page('garden-thanks','Thank You','thankyou','#1f7158',{thanks:textObj('thanks','Thank you for being part of our story.','12%','39%','76%','160px',36,'#ffffff')},'overlap')];
  doc.sectionOrder=['page:garden-story','page:garden-collage','gallery','countdown','schedule','page:garden-details','custom','venue','contact','rsvp','page:garden-thanks'];doc.sectionLayouts={countdown:'minimal',schedule:'cards',custom:'alternating',venue:'cards'};doc.sectionStyles={gallery:style('gallery','#ffffff','#263c34',30),countdown:style('countdown','#d9eee2','#263c34',30),schedule:style('schedule','#ffffff','#263c34',30),custom:style('custom','#edf7f0','#263c34',30),venue:style('venue','#ffffff','#263c34',30),contact:style('contact','#d9eee2','#263c34',30),rsvp:style('rsvp','#ffffff','#263c34',30)}
 } else if(id==='midnight'){
  doc.theme='midnight';doc.templateId=id;doc.palettePreset='midnight';doc.palette={background:'#0f0d16',surface:'#1d1829',text:'#f0ebf8',heading:'#bca7ff'};doc.accent='#8065c7';doc.openingStyle='night';doc.masterPageStyle={enabled:true,background:'#100e19',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};
  doc.objects={panel:shapeObj('panel','8%','9%','84%','800px','#241d35','rectangle',34),title:textObj('title',doc.fields.names,'12%','18%','76%','120px',52,'#d7cbff'),subtitle:textObj('subtitle',doc.fields.message,'15%','42%','70%','150px',21,'#e7e0f0'),details:textObj('details','27 December 2026<br>Your wedding venue','15%','76%','70%','100px',22,'#bca7ff')};
  doc.designPages=[page('night-feature','The Night Begins','split','#100e19',{head:textObj('head','An Evening to Remember','10%','13%','80%','100px',44,'#d7cbff'),body:textObj('body','A cinematic celebration under the lights.','13%','42%','74%','150px',24,'#eee8f7')}),page('night-moments','Moments','collage','#191426',{head:textObj('head','Moments in Light','10%','10%','80%','90px',40,'#bca7ff'),a:shapeObj('a','10%','30%','36%','360px','#302746','rectangle',22),b:shapeObj('b','54%','30%','36%','360px','#302746','rectangle',22)}),page('night-thanks','Finale','thankyou','#0f0d16',{thanks:textObj('thanks','See you under the lights.','12%','40%','76%','150px',40,'#d7cbff')},'sweep')];
  doc.sectionOrder=['page:night-feature','gallery','page:night-moments','countdown','schedule','custom','venue','contact','rsvp','page:night-thanks'];doc.sectionLayouts={countdown:'pill',schedule:'minimal',custom:'editorial',venue:'split'};doc.sectionStyles={gallery:style('gallery','#1d1829','#f0ebf8',28),countdown:style('countdown','#241d35','#f0ebf8',28),schedule:style('schedule','#1d1829','#f0ebf8',28),custom:style('custom','#241d35','#f0ebf8',28),venue:style('venue','#1d1829','#f0ebf8',28),contact:style('contact','#241d35','#f0ebf8',28),rsvp:style('rsvp','#1d1829','#f0ebf8',28)}
 } else if(id==='birthday-pop'){
  doc.theme='rose';doc.templateId=id;doc.palettePreset='custom';doc.palette={background:'#fff7e8',surface:'#ffffff',text:'#3d3151',heading:'#ef5b8c'};doc.accent='#ef5b8c';doc.openingStyle='soft';doc.galleryStyle='filmstrip';doc.masterPageStyle={enabled:true,background:'#fff7e8',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};
  doc.objects={bubble:shapeObj('bubble','6%','9%','88%','260px','#ffd66e','circle',150),title:textObj('title',doc.fields.names,'10%','18%','80%','120px',54,'#5c3e8f','sans-arial'),subtitle:textObj('subtitle',doc.fields.message,'13%','45%','74%','130px',23,'#3d3151','sans-arial'),details:textObj('details','27 December 2026<br>Party venue','14%','78%','72%','100px',22,'#ef5b8c','sans-arial')};
  doc.designPages=[page('birthday-collage','Photo Collage','collage','#fff0c4',{head:textObj('head','Best Moments','10%','9%','80%','80px',40,'#ef5b8c','sans-arial'),a:shapeObj('a','8%','28%','38%','320px','#ffffff','rectangle',28),b:shapeObj('b','54%','35%','38%','320px','#ffffff','rectangle',28)}),page('birthday-details','Party Details','details','#f8ddff',{head:textObj('head','Come Celebrate!','10%','15%','80%','90px',44,'#5c3e8f','sans-arial'),body:textObj('body','Food, music, cake, and a lot of fun await.','12%','40%','76%','170px',25,'#3d3151','sans-arial')}),page('birthday-thanks','See You There','thankyou','#ef5b8c',{thanks:textObj('thanks','Bring your smile — we cannot wait to celebrate together!','10%','37%','80%','190px',36,'#ffffff','sans-arial')},'overlap')];
  doc.sectionOrder=['page:birthday-collage','gallery','countdown','schedule','page:birthday-details','venue','contact','rsvp','page:birthday-thanks'];doc.sectionLayouts={countdown:'cards',schedule:'cards',custom:'cards',venue:'cards'};doc.sectionStyles={gallery:style('gallery','#ffffff','#3d3151',32),countdown:style('countdown','#fff0c4','#3d3151',32),schedule:style('schedule','#f8ddff','#3d3151',32),custom:style('custom','#ffffff','#3d3151',32),venue:style('venue','#fff0c4','#3d3151',32),contact:style('contact','#f8ddff','#3d3151',32),rsvp:style('rsvp','#ffffff','#3d3151',32)}
 } else if(id==='business-ivory'){
  doc.theme='gold';doc.templateId=id;doc.palettePreset='ivory-navy';doc.palette={background:'#f7f4ed',surface:'#ffffff',text:'#293444',heading:'#213b5a'};doc.accent='#213b5a';doc.openingStyle='minimal';doc.masterPageStyle={enabled:true,background:'#f7f4ed',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};
  doc.objects={bar:shapeObj('bar','7%','8%','2%','820px','#c8a55a','rectangle',0),title:textObj('title',doc.fields.names,'15%','16%','72%','130px',48,'#213b5a','sans-arial'),subtitle:textObj('subtitle',doc.fields.message,'15%','42%','72%','150px',21,'#4a5565','sans-arial'),details:textObj('details','27 December 2026<br>Event venue','15%','76%','72%','100px',22,'#213b5a','sans-arial')};
  doc.designPages=[page('business-agenda','Agenda','details','#ffffff',{head:textObj('head','Program Overview','10%','13%','80%','90px',40,'#213b5a','sans-arial'),body:textObj('body','Registration · Opening remarks · Main session · Networking','12%','38%','76%','220px',23,'#4a5565','sans-arial')}),page('business-feature','Event Focus','split','#eef1f4',{head:textObj('head','Connect. Learn. Collaborate.','10%','16%','80%','120px',42,'#213b5a','sans-arial'),body:textObj('body','Use this page for keynote information, speakers, or the purpose of the event.','12%','45%','76%','190px',22,'#4a5565','sans-arial')}),page('business-close','We Look Forward to Welcoming You','thankyou','#213b5a',{thanks:textObj('thanks','Thank you for joining this important occasion.','12%','40%','76%','160px',34,'#ffffff','sans-arial')},'soft')];
  doc.sectionOrder=['page:business-agenda','schedule','page:business-feature','custom','venue','contact','rsvp','page:business-close'];doc.sectionLayouts={countdown:'minimal',schedule:'minimal',custom:'editorial',venue:'split'};doc.sectionStyles={gallery:style('gallery','#ffffff','#293444',6),countdown:style('countdown','#eef1f4','#293444',6),schedule:style('schedule','#ffffff','#293444',6),custom:style('custom','#eef1f4','#293444',6),venue:style('venue','#ffffff','#293444',6),contact:style('contact','#eef1f4','#293444',6),rsvp:style('rsvp','#ffffff','#293444',6)}
 }
 return doc
}
function builtInDocument(title,type,id){
 const meta=templateCatalog.find(t=>t.id===id)||templateCatalog[0],effectiveType=meta.category==='Birthday'?'Birthday':meta.category==='Business'?'Business':type||'Wedding';
 const variantBase={'khmer-ivory':'gold','modern-minimal':'business-ivory','botanical-blush':'rose','black-gold-gala':'midnight','birthday-neon':'birthday-pop','corporate-launch':'business-ivory'};
 const baseId=variantBase[id]||id,theme=['rose','gold','emerald','midnight'].includes(baseId)?baseId:baseId==='business-ivory'?'gold':'rose';
 const doc=enrichBuiltin(baseDocument(title,effectiveType,theme),baseId);doc.templateId=id;
 if(id==='khmer-ivory'){doc.palettePreset='custom';doc.palette={background:'#fbf7ed',surface:'#fffdf7',text:'#372d20',heading:'#916b28'};doc.accent='#a7813a';doc.masterPageStyle.background='#fbf7ed';doc.openingStyle='curtain';Object.values(doc.objects||{}).forEach(o=>{if(o.type==='text')o.font=String(o.font||'').includes('khmer')?o.font:'noto-serif-khmer'})}
 if(id==='modern-minimal'){doc.eventType='Wedding';doc.theme='gold';doc.palettePreset='custom';doc.palette={background:'#f6f5f2',surface:'#ffffff',text:'#22252b',heading:'#22252b'};doc.accent='#6a6d74';doc.openingStyle='minimal';doc.sectionLayouts={countdown:'minimal',schedule:'minimal',custom:'editorial',venue:'stacked'};Object.values(doc.objects||{}).forEach(o=>{if(o.type==='text'){o.font='sans-arial';o.letterSpacing=Number(o.fontSize||20)>35?-1:0}})}
 if(id==='botanical-blush'){doc.palettePreset='custom';doc.palette={background:'#fff8f5',surface:'#fffdfb',text:'#423437',heading:'#a55d70'};doc.accent='#a55d70';doc.masterPageStyle.background='#fff8f5';doc.designPages.forEach((p,i)=>{p.background=i%2?'#f6e4df':'#fff8f5'})}
 if(id==='black-gold-gala'){doc.eventType='Business';doc.palettePreset='custom';doc.palette={background:'#0d0e12',surface:'#171820',text:'#f5f0e6',heading:'#d6b56d'};doc.accent='#d6b56d';doc.openingStyle='night';doc.masterPageStyle={enabled:true,background:'#0d0e12',backgroundImage:'',backgroundSize:'cover',backgroundOverlay:0};Object.values(doc.objects||{}).forEach(o=>{if(o.type==='text')o.color='#f5f0e6'})}
 if(id==='birthday-neon'){doc.palettePreset='custom';doc.palette={background:'#121020',surface:'#211b35',text:'#f7f2ff',heading:'#ff5fcf'};doc.accent='#7af3ff';doc.openingStyle='night';doc.masterPageStyle.background='#121020';doc.designPages.forEach((p,i)=>p.background=['#1d1631','#28173b','#6b1b68'][i%3])}
 if(id==='corporate-launch'){doc.palettePreset='custom';doc.palette={background:'#eff5f4',surface:'#ffffff',text:'#21302f',heading:'#116b63'};doc.accent='#18a999';doc.openingStyle='minimal';doc.sectionLayouts={countdown:'minimal',schedule:'cards',custom:'editorial',venue:'split'};doc.designPages.forEach((p,i)=>p.background=i%2?'#dff0ed':'#ffffff')}
 return doc
}
function instantiateCustom(template,title,type){let doc=clone(template.document||{});doc.fields={...(doc.fields||{}),names:title};doc.eventType=type||template.category||doc.eventType||'Wedding';doc.templateId=`user:${template.id}`;delete doc.id;delete doc.version;delete doc.publishedAt;return doc}
async function detect(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;server=window.EInviteBackend?window.EInviteBackend.isAvailable():false;if(server){try{let me=await request('/api/auth/me');account=me.user;if(account)await Promise.all([loadServerInvites(),loadTemplates()])}catch{account=null}}else{await loadTemplates();account=account||JSON.parse(localStorage.getItem(accountKey)||'null')}show();requestAnimationFrame(()=>scrollTo(0,0))}
async function loadServerInvites(){invites=(await request('/api/invitations')).map(i=>({...i,type:i.type||'Invitation'}))}
async function loadTemplates(){if(server){try{const [mine,market]=await Promise.all([account?request('/api/templates'):Promise.resolve([]),request('/api/template-marketplace')]);userTemplates=mine;const ownIds=new Set(mine.map(x=>x.id));marketTemplates=market.filter(x=>!ownIds.has(x.id));return}catch{}}try{userTemplates=JSON.parse(localStorage.getItem(localTemplatesKey)||'[]')}catch{userTemplates=[]}marketTemplates=[]}
function show(){let signed=!!account;$('#loginView').hidden=signed;$('#dashboardView').hidden=!signed;$('#logoutBtn').hidden=!signed;if($('#adminBtn'))$('#adminBtn').hidden=!signed||account?.role!=='admin';if($('#designerBtn'))$('#designerBtn').hidden=!signed||!['designer','admin'].includes(account?.role);$('#accountName').textContent=signed?`${account.email}${account.role?` · ${account.role}`:''}${account.plan?` · ${account.plan}`:''}${server?' · Server':' · Local demo'}`:'';if(signed)render();if(!server&&signed){let n=document.querySelector('#staticModeNotice');if(!n){n=document.createElement('div');n.id='staticModeNotice';n.className='server-required-v14';n.innerHTML='<strong>Static preview mode</strong><p>Server-backed accounts, collaboration, materials, campaigns, and check-in synchronization require the full application server.</p>';$('#dashboardView')?.prepend(n)}}}
function dashboardThumbnail(i){
 const p=i.preview||{},palette=p.palette||{},fields=p.fields||{},page=p.designPages?.[0],objects=page?.objects||p.objects||{},bg=palette.background||page?.background||'#fff8f3',text=palette.text||'#31272b';
 const hasObjects=Object.values(objects).some(o=>o&&['text','image','shape','decoration'].includes(o.type||'text'));
 return hasObjects?`<div class="dashboard-thumb-v14" style="--thumb-bg:${escapeHtml(bg)};--thumb-text:${escapeHtml(text)}"></div>`:`<div class="dashboard-thumb-v14" style="--thumb-bg:${escapeHtml(bg)};--thumb-text:${escapeHtml(text)}"><div class="thumb-fallback"><strong>${escapeHtml(fields.names||i.title||'Invitation')}</strong><small>${escapeHtml(p.eventType||i.type||'Invitation')}</small></div></div>`;
}

function render(){$('#inviteGrid').innerHTML=invites.map(i=>`<article class="invite-card" style="opacity:${i.archived?.72:1}"><button class="invite-cover" data-edit="${i.id}" data-dashboard-thumbnail="${i.id}" aria-label="Open ${escapeHtml(i.title)}" ${i.archived?'disabled':''}>${dashboardThumbnail(i)}</button><div class="invite-body"><h2 title="${escapeHtml(i.title)}">${escapeHtml(i.title)}</h2><span class="invite-status-pill">${escapeHtml(i.status)}</span><div class="stats"><span>${i.views||0} views</span>${i.rsvpEnabled===false?'<span>Invitation only</span>':`<span>${i.rsvps||0} RSVPs</span>`}</div><div class="actions"><button data-edit="${i.id}" class="primary" ${i.archived?'disabled':''}>Edit</button><button data-guests="${i.id}">Guests</button><button data-responses="${i.id}">Responses</button><button data-analytics="${i.id}">Analytics</button><button data-copy="${i.id}">Duplicate</button><button data-archive="${i.id}">${i.archived?'Restore':'Archive'}</button><button data-delete="${i.id}" class="danger">Delete</button></div></div></article>`).join('');document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>openEditor(b.dataset.edit));document.querySelectorAll('[data-guests]').forEach(b=>b.onclick=()=>window.EInviteContext?.navigate?.(b.dataset.guests,'guests'));document.querySelectorAll('[data-responses]').forEach(b=>b.onclick=()=>window.EInviteContext?.navigate?.(b.dataset.responses,'responses'));document.querySelectorAll('[data-analytics]').forEach(b=>b.onclick=()=>window.EInviteContext?.navigate?.(b.dataset.analytics,'analytics'));document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>duplicate(b.dataset.copy));document.querySelectorAll('[data-archive]').forEach(b=>b.onclick=()=>archiveInvite(b.dataset.archive));document.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>deleteInvite(b.dataset.delete));queueMicrotask(()=>{try{hydrateDashboardThumbnails()}catch(error){console.warn('Dashboard thumbnails failed',error)}})}
async function openEditor(id){localStorage.setItem('sovan-active-invite',id);sessionStorage.setItem('einvite-open-editor-tab','design');sessionStorage.removeItem('einvite-editor-session-active');if(window.EInviteContext?.navigate)return window.EInviteContext.navigate(id,'editor');location.href=`index.html?invitation=${encodeURIComponent(id)}`}function localSave(){localStorage.setItem(invitesKey,JSON.stringify(invites));render()}function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
let authMode='signin';
function setAuthMode(mode){authMode=mode;$('#authSignInTab')?.classList.toggle('active',mode==='signin');$('#authRegisterTab')?.classList.toggle('active',mode==='register');if($('#registerConfirmWrap'))$('#registerConfirmWrap').hidden=mode!=='register';if($('#authTitle'))$('#authTitle').textContent=mode==='register'?'Create your account':'Welcome back';if($('#authIntro'))$('#authIntro').textContent=mode==='register'?'Create a workspace for invitations, templates, guests, and event operations.':'Sign in to continue working on your invitations and events.';if($('#loginBtn'))$('#loginBtn').textContent=mode==='register'?'Create account':'Sign in';if($('#authStatus'))$('#authStatus').textContent=''}
$('#authSignInTab')&&( $('#authSignInTab').onclick=()=>setAuthMode('signin') );$('#authRegisterTab')&&( $('#authRegisterTab').onclick=()=>setAuthMode('register') );
$('#loginBtn').onclick=async()=>{let email=$('#email').value.trim(),password=$('#password').value,confirmPassword=$('#registerConfirmPassword')?.value||'',status=$('#authStatus'),button=$('#loginBtn');if(!/^.+@.+\..+$/.test(email)){status.textContent='Enter a valid email address.';return}if(password.length<8){status.textContent='Use a password of at least 8 characters.';return}if(authMode==='register'&&password!==confirmPassword){status.textContent='The passwords do not match.';return}button.disabled=true;status.textContent=authMode==='register'?'Creating account…':'Signing in…';try{if(server){let result=await request(authMode==='register'?'/api/auth/register':'/api/auth/login',{method:'POST',body:JSON.stringify({email,password})});if(result.mfaRequired){const code=prompt('Enter the 6-digit code from your authenticator app.');if(!code)throw Error('Two-step verification was cancelled.');result=await request('/api/auth/mfa/complete',{method:'POST',body:JSON.stringify({mfaToken:result.mfaToken,code})})}account=result.user;await Promise.all([loadServerInvites(),loadTemplates()])}else{account={id:crypto.randomUUID(),email,role:'customer',plan:'free'};localStorage.setItem(accountKey,JSON.stringify(account));await loadTemplates()}status.textContent='';show()}catch(e){status.textContent=e.message||'Authentication failed.'}finally{button.disabled=false}};
$('#logoutBtn').onclick=async()=>{if(server)try{await request('/api/auth/logout',{method:'POST'})}catch{}localStorage.removeItem('sovan-auth-token');localStorage.removeItem(accountKey);account=null;show()};
function allTemplateItems(){return[...templateCatalog.map(t=>({...t,kind:'builtin'})),...userTemplates.map(t=>({id:`user:${t.id}`,sourceId:t.id,name:t.name,category:t.category||'Wedding',tone:'custom',description:`Your reusable complete invitation · ${(t.document?.designPages||[]).length} visual pages`,pages:(t.document?.designPages||[]).length,kind:'user',document:t.document}))]}
function renderTemplateChoices(){const q=($('#templateSearch').value||'').trim().toLowerCase(),selected=$('#newTemplate').value;let items=allTemplateItems().filter(t=>(templateFilter==='all'||(templateFilter==='mine'&&t.kind==='user')||t.category===templateFilter)&&(!q||`${t.name} ${t.description} ${(t.tags||[]).join(' ')}`.toLowerCase().includes(q)));const grid=$('#templateChoices');grid.innerHTML='';if(!items.length)grid.innerHTML='<div class="template-empty">No templates match this filter.</div>';items.forEach(t=>{const button=document.createElement('article');button.className=`template-choice${selected===t.id?' active':''}`;button.dataset.templateChoice=t.id;button.dataset.tone=t.tone||'custom';button.innerHTML=`<button type="button" class="template-select-action" aria-pressed="${selected===t.id}"><div class="template-art"><em>${escapeHtml(t.category)}</em></div><div class="template-meta"><strong>${escapeHtml(t.name)}</strong><small>${escapeHtml(t.description||'Reusable invitation design')}</small></div></button>`;if(t.kind==='user'){const remove=document.createElement('button');remove.type='button';remove.className='custom-template-remove';remove.title='Delete template';remove.textContent='×';remove.onclick=async e=>{e.stopPropagation();if(!(await uiConfirm(`Delete template “${t.name}”?`,{title:'Delete template',danger:true,confirmText:'Delete'})))return;try{if(server)await request(`/api/templates/${t.sourceId}`,{method:'DELETE'});else{userTemplates=userTemplates.filter(x=>x.id!==t.sourceId);localStorage.setItem(localTemplatesKey,JSON.stringify(userTemplates))}await loadTemplates();if($('#newTemplate').value===t.id)$('#newTemplate').value='rose';renderTemplateChoices()}catch(error){alert(error.message)}};button.append(remove)}button.querySelector('.template-select-action').onclick=()=>{$('#newTemplate').value=t.id;renderTemplateChoices();updateTemplateSummary(t)};grid.append(button)});let active=items.find(t=>t.id===selected)||allTemplateItems().find(t=>t.id===selected);if(active)updateTemplateSummary(active)}
function updateTemplateSummary(t){$('#templateSummary').textContent=`${t.name} · ${t.category} · ${t.pages||0} visual page${Number(t.pages||0)===1?'':'s'} · ${t.kind==='user'?'Saved by you':'Built-in professional template'}`}
$('#templateSearch').oninput=renderTemplateChoices;document.querySelectorAll('[data-template-filter]').forEach(b=>b.onclick=()=>{templateFilter=b.dataset.templateFilter;document.querySelectorAll('[data-template-filter]').forEach(x=>x.classList.toggle('active',x===b));renderTemplateChoices()});
$('#newBtn').onclick=async()=>{$('#newTitle').value='';$('#newType').value='Wedding';$('#newTemplate').value='rose';templateFilter='all';document.querySelectorAll('[data-template-filter]').forEach((x,i)=>x.classList.toggle('active',i===0));await loadTemplates();renderTemplateChoices();$('#createDialog').showModal();$('#newTitle').focus()};$('#cancelCreate').onclick=()=>$('#createDialog').close();
$('#createForm').onsubmit=async e=>{e.preventDefault();let title=$('#newTitle').value.trim(),type=$('#newType').value,templateId=$('#newTemplate').value;if(!title)return;let custom=templateId.startsWith('user:')?userTemplates.find(t=>t.id===templateId.slice(5)):templateId.startsWith('market:')?marketTemplates.find(t=>t.id===templateId.slice(7)):null,document=custom?instantiateCustom(custom,title,type):builtInDocument(title,type,templateId),button=$('#confirmCreate');button.disabled=true;button.textContent='Creating…';try{if(server){let item=await request('/api/invitations',{method:'POST',body:JSON.stringify({slug:title,document})});await loadServerInvites();openEditor(item.id)}else{let item={id:crypto.randomUUID(),title,type:document.eventType||type,status:'Draft',views:0,rsvps:0,updatedAt:new Date().toISOString()};invites.push(item);localStorage.setItem(`sovan-invite-draft-v3:${item.id}`,JSON.stringify(document));localSave();openEditor(item.id)}}catch(error){alert(error.message)}finally{button.disabled=false;button.textContent='Create from template'}};
function copyDocument(document,title){let copy=clone(document||{});copy.fields={...(copy.fields||{}),names:title};delete copy.id;delete copy.version;delete copy.publishedAt;return copy}
async function duplicate(id){let src=invites.find(i=>i.id===id);if(!src)return;let title=src.title+' Copy';if(server){try{let source=await request('/api/invitations/'+encodeURIComponent(id)),document=copyDocument(source.document,title),item=await request('/api/invitations',{method:'POST',body:JSON.stringify({slug:title,document})});await loadServerInvites();render();return item}catch(error){return alert(`The invitation could not be duplicated: ${error.message}`)}}let sourceKey=`sovan-invite-draft-v3:${id}`,sourceDocument=JSON.parse(localStorage.getItem(sourceKey)||'null')||builtInDocument(src.title,src.type||'Wedding','rose'),item={...src,id:crypto.randomUUID(),title,status:'Draft',views:0,rsvps:0,archived:false,updatedAt:new Date().toISOString()};localStorage.setItem(`sovan-invite-draft-v3:${item.id}`,JSON.stringify(copyDocument(sourceDocument,title)));invites.push(item);localSave()}
async function archiveInvite(id){let item=invites.find(i=>i.id===id),archived=!item.archived;if(server){await request(`/api/invitations/${id}/archive`,{method:'PUT',body:JSON.stringify({archived})});await loadServerInvites();render()}else{Object.assign(item,{archived,status:archived?'Archived':'Draft'});localSave()}}
async function deleteInvite(id){let item=invites.find(i=>i.id===id);if(!(await uiConfirm(`Move “${item.title}” to Trash? You can restore it during the recovery period.`,{title:'Move invitation to Trash',danger:true,confirmText:'Move to Trash'})))return;if(server){await request(`/api/invitations/${id}/trash`,{method:'POST',body:'{}'});await loadServerInvites();render()}else{invites=invites.filter(i=>i.id!==id);localSave()}}
detect();

const v13B64ToBytes=value=>{const x=String(value||'').replace(/-/g,'+').replace(/_/g,'/'),p=x+'='.repeat((4-x.length%4)%4),raw=atob(p);return Uint8Array.from(raw,c=>c.charCodeAt(0))};
const v13BytesToB64=value=>{const raw=Array.from(new Uint8Array(value),b=>String.fromCharCode(b)).join('');return btoa(raw).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')};
const v13AssertionJSON=credential=>({id:credential.id,type:credential.type,rawId:v13BytesToB64(credential.rawId),response:{clientDataJSON:v13BytesToB64(credential.response.clientDataJSON),authenticatorData:v13BytesToB64(credential.response.authenticatorData),signature:v13BytesToB64(credential.response.signature),userHandle:credential.response.userHandle?v13BytesToB64(credential.response.userHandle):null}});
if($('#passkeyLoginBtn'))$('#passkeyLoginBtn').onclick=async()=>{const email=$('#email').value.trim(),status=$('#authStatus'),button=$('#passkeyLoginBtn');if(!/^.+@.+\..+$/.test(email)){status.textContent='Enter your email first, then choose Use a passkey.';return}if(!window.PublicKeyCredential||!navigator.credentials){status.textContent='This browser does not support passkeys.';return}button.disabled=true;status.textContent='Waiting for your passkey…';try{const data=await request('/api/auth/passkeys/login/options',{method:'POST',body:JSON.stringify({email})}),opts=data.publicKey;opts.challenge=v13B64ToBytes(opts.challenge);opts.allowCredentials=(opts.allowCredentials||[]).map(x=>({...x,id:v13B64ToBytes(x.id)}));const credential=await navigator.credentials.get({publicKey:opts});const result=await request('/api/auth/passkeys/login/complete',{method:'POST',body:JSON.stringify({challengeId:data.challengeId,credential:v13AssertionJSON(credential)})});account=result.user;await Promise.all([loadServerInvites(),loadTemplates()]);status.textContent='';show()}catch(e){status.textContent=e.message||'Passkey sign-in was cancelled.'}finally{button.disabled=false}};;const builtInFavoriteKey = 'sovan-builtin-template-favorites-v1';
let previewTemplateItem = null;

function readBuiltInFavorites(){
  try{return new Set(JSON.parse(localStorage.getItem(builtInFavoriteKey)||'[]'))}catch{return new Set()}
}
function writeBuiltInFavorites(set){localStorage.setItem(builtInFavoriteKey,JSON.stringify([...set]))}
function templateDoc(item){
  if(item.kind==='user'||item.kind==='market') return item.document||{};
  try{return builtInDocument('Your Event',item.category==='Business'?'Business':item.category||'Wedding',item.id)}catch{return {fields:{names:item.name},palette:{background:'#fff7f3',text:'#342c26',heading:'#9d4555'},designPages:[],objects:{}}}
}
function stripMarkup(value){const div=document.createElement('div');div.innerHTML=String(value||'');return div.textContent||div.innerText||''}
function templatePalette(doc,item){
  const palette=doc?.palette||{};
  const tone={rose:['#fff7f3','#412e32','#9d4555'],gold:['#fffaf0','#3c2b18','#9b6b13'],emerald:['#eff8f2','#263c34','#1f7158'],midnight:['#0f0d16','#f0ebf8','#bca7ff'],ivory:['#f7f4ed','#293444','#213b5a'],custom:['#f5f1ff','#3d3151','#6d4bc3']}[item?.tone]||['#fff7f3','#342c26','#9d4555'];
  return {background:palette.background||tone[0],text:palette.text||tone[1],heading:palette.heading||doc?.accent||tone[2],accent:doc?.accent||palette.heading||tone[2]}
}
function templateTitle(doc,item){
  const title=doc?.objects?.title?.html||doc?.fields?.names||item?.name||'Invitation';
  return stripMarkup(title).slice(0,55)
}
function liveThumbnail(item){
  const doc=templateDoc(item),p=templatePalette(doc,item),title=templateTitle(doc,item);
  const imageObject=Object.values(doc?.objects||{}).find(o=>o?.type==='image'&&o?.src);
  const bg=imageObject?.src?`background-image:linear-gradient(#fff8,#fff8),url('${escapeHtml(imageObject.src)}');background-size:cover;background-position:center;`:'';
  return `<div class="template-live-thumb" style="--thumb-bg:${p.background};--thumb-text:${p.text};--thumb-heading:${p.heading};--thumb-accent:${p.accent};${bg}"><span class="mini-dot a"></span><span class="mini-dot b"></span><span class="mini-frame"></span><strong class="mini-title">${escapeHtml(title)}</strong></div>`
}
function allTemplateItemsEnhanced(){
  const favorites=readBuiltInFavorites();
  return [
    ...templateCatalog.map(t=>({...t,kind:'builtin',favorite:favorites.has(t.id)})),
    ...userTemplates.map(t=>({
      id:`user:${t.id}`,sourceId:t.id,name:t.name,category:t.category||'Wedding',tone:'custom',
      description:t.description||`Your reusable complete invitation · ${(t.document?.designPages||[]).length} visual pages`,
      tags:t.tags||[],pages:(t.document?.designPages||[]).length,kind:'user',document:t.document,
      favorite:!!t.favorite,currentVersion:t.currentVersion||1,updatedAt:t.updatedAt
    })),
    ...marketTemplates.map(t=>({
      id:`market:${t.id}`,sourceId:t.id,name:t.name,category:t.category||'Wedding',tone:'custom',
      description:t.description||`Shared marketplace template · ${(t.document?.designPages||[]).length} visual pages`,
      tags:t.tags||[],pages:(t.document?.designPages||[]).length,kind:'market',document:t.document,
      favorite:readBuiltInFavorites().has(`market:${t.id}`),currentVersion:t.currentVersion||1,updatedAt:t.updatedAt
    }))
  ]
}
allTemplateItems = allTemplateItemsEnhanced;

async function toggleTemplateFavorite(item){
  if(item.kind==='builtin'||item.kind==='market'){
    const favorites=readBuiltInFavorites(),key=item.kind==='market'?`market:${item.sourceId}`:item.id;favorites.has(key)?favorites.delete(key):favorites.add(key);writeBuiltInFavorites(favorites)
  }else if(server){
    const updated=await request(`/api/templates/${item.sourceId}`,{method:'PUT',body:JSON.stringify({favorite:!item.favorite})});
    const index=userTemplates.findIndex(x=>x.id===item.sourceId);if(index>=0)userTemplates[index]=updated
  }else{
    const index=userTemplates.findIndex(x=>x.id===item.sourceId);if(index>=0){userTemplates[index].favorite=!item.favorite;localStorage.setItem(localTemplatesKey,JSON.stringify(userTemplates))}
  }
  renderTemplateChoices()
}

renderTemplateChoices = function(){
  const q=($('#templateSearch').value||'').trim().toLowerCase(),selected=$('#newTemplate').value;
  let items=allTemplateItems().filter(t=>{
    const filterOk=templateFilter==='all'||(templateFilter==='mine'&&t.kind==='user')||(templateFilter==='marketplace'&&t.kind==='market')||(templateFilter==='favorites'&&t.favorite)||t.category===templateFilter;
    return filterOk&&(!q||`${t.name} ${t.description} ${(t.tags||[]).join(' ')}`.toLowerCase().includes(q))
  });
  const grid=$('#templateChoices');grid.innerHTML='';if(!items.length)grid.innerHTML='<div class="template-empty">No templates match this filter.</div>';
  items.forEach(t=>{
    const card=document.createElement('article');card.className=`template-choice${selected===t.id?' active':''}`;card.dataset.templateChoice=t.id;card.dataset.tone=t.tone||'custom';
    card.innerHTML=`<button type="button" class="template-select-action" aria-pressed="${selected===t.id}">${liveThumbnail(t)}<div class="template-meta"><strong>${escapeHtml(t.name)}</strong><small>${escapeHtml(t.description||'Reusable invitation design')}</small></div></button><div class="template-choice-actions"><button type="button" class="favorite${t.favorite?' active':''}" title="${t.favorite?'Remove from favorites':'Add to favorites'}">★</button><button type="button" class="preview-card-btn">Preview</button></div>`;
    card.querySelector('.favorite').onclick=async e=>{e.stopPropagation();try{await toggleTemplateFavorite(t)}catch(error){alert(error.message)}};
    card.querySelector('.preview-card-btn').onclick=e=>{e.stopPropagation();openTemplatePreview(t)};
    if(t.kind==='user'){
      const remove=document.createElement('button');remove.type='button';remove.className='custom-template-remove';remove.title='Delete template';remove.textContent='×';
      remove.onclick=async e=>{e.stopPropagation();if(!(await uiConfirm(`Delete template “${t.name}”?`,{title:'Delete template',danger:true,confirmText:'Delete'})))return;try{if(server)await request(`/api/templates/${t.sourceId}`,{method:'DELETE'});else{userTemplates=userTemplates.filter(x=>x.id!==t.sourceId);localStorage.setItem(localTemplatesKey,JSON.stringify(userTemplates))}await loadTemplates();if($('#newTemplate').value===t.id)$('#newTemplate').value='rose';renderTemplateChoices()}catch(error){alert(error.message)}};card.append(remove)
    }
    card.querySelector('.template-select-action').onclick=()=>{$('#newTemplate').value=t.id;renderTemplateChoices();updateTemplateSummary(t)};
    grid.append(card)
  });
  const active=items.find(t=>t.id===selected)||allTemplateItems().find(t=>t.id===selected);if(active)updateTemplateSummary(active)
};

updateTemplateSummary = function(t){
  const version=t.kind==='user'?` · Version ${t.currentVersion||1}`:'';
  $('#templateSummary').textContent=`${t.name} · ${t.category} · ${t.pages||0} visual page${Number(t.pages||0)===1?'':'s'}${version} · ${t.kind==='user'?'Saved by you':t.kind==='market'?'Shared marketplace template':'Built-in professional template'}`
};

function previewObjectMarkup(obj){
  if(!obj||typeof obj!=='object')return'';
  const style=`left:${obj.left||'10%'};top:${obj.top||'10%'};width:${obj.width||'80%'};height:${obj.height||'80px'};position:absolute;transform:rotate(${Number(obj.rotation||0)}deg);opacity:${Number(obj.opacity||1)};color:${obj.color||'#342c26'};font-family:${obj.font||'serif-georgia'};font-size:${Math.max(8,Math.min(34,Number(obj.fontSize||22)))}px;text-align:${obj.textAlign||'center'};overflow:hidden;`;
  if(obj.type==='image'&&obj.src)return `<img src="${escapeHtml(obj.src)}" alt="" style="${style}object-fit:cover;border-radius:${Number(obj.borderRadius||0)}px">`;
  if(obj.type==='shape')return `<span style="${style}background:${obj.fillColor||'#d9a6ad'};border-radius:${obj.shapeKind==='circle'?'50%':Number(obj.borderRadius||0)+'px'}"></span>`;
  if(obj.type==='decoration')return `<span style="${style}display:flex;align-items:center;justify-content:center">${escapeHtml(stripMarkup(obj.html||'✦'))}</span>`;
  if(obj.type==='text'||obj.html)return `<div style="${style}">${escapeHtml(stripMarkup(obj.html||''))}</div>`;
  return''
}
function previewPageMarkup(page,master){
  const bg=page.useMasterBackground&&master?.enabled?master:page;const image=bg?.backgroundImage?`background-image:linear-gradient(rgba(0,0,0,${Number(bg.backgroundOverlay||0)/100}),rgba(0,0,0,${Number(bg.backgroundOverlay||0)/100})),url('${escapeHtml(bg.backgroundImage)}');background-size:${bg.backgroundSize||'cover'};background-position:center;`:'';
  const title=page.name||'Visual page';
  return `<div class="template-preview-page" style="--page-bg:${escapeHtml(bg?.background||'#fff')};${image}"><div><strong>${escapeHtml(title)}</strong><small style="display:block;margin-top:6px;opacity:.7">${Object.keys(page.objects||{}).length} design objects</small></div></div>`
}
function openTemplatePreview(item){
  previewTemplateItem=item;const doc=templateDoc(item),p=templatePalette(doc,item),pages=doc.designPages||[],title=templateTitle(doc,item),heroObjects=Object.values(doc.objects||{}).slice(0,24).map(previewObjectMarkup).join('');
  $('#templatePreviewBody').innerHTML=`<div class="template-preview-shell"><div class="template-preview-phone"><div class="template-preview-screen" style="--p-bg:${p.background};--p-text:${p.text};--p-heading:${p.heading}"><section class="template-preview-hero"><h2>${escapeHtml(title)}</h2>${heroObjects}</section><div class="template-preview-pages">${pages.map(page=>previewPageMarkup(page,doc.masterPageStyle)).join('')}<div class="template-preview-page"><div><strong>Event sections</strong><small style="display:block;margin-top:6px;opacity:.7">${(doc.sectionOrder||[]).filter(x=>!String(x).startsWith('page:')).join(' · ')||'Flexible sections'}</small></div></div></div></div></div><div class="template-preview-info"><p class="invite-kicker">${escapeHtml(item.category||'Invitation')} template</p><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(item.description||'Reusable invitation design')}</p><div class="template-preview-tags">${(item.tags||[]).map(tag=>`<span>${escapeHtml(tag)}</span>`).join('')}</div><div class="template-preview-features"><div class="template-preview-feature"><strong>${pages.length}</strong><br><small>Visual pages</small></div><div class="template-preview-feature"><strong>${Object.keys(doc.objects||{}).length}</strong><br><small>Hero objects</small></div><div class="template-preview-feature"><strong>${item.kind==='user'||item.kind==='market'?'Version '+(item.currentVersion||1):'Curated'}</strong><br><small>${item.kind==='user'?'Your template':item.kind==='market'?'Shared template':'Built-in design'}</small></div><div class="template-preview-feature"><strong>${doc.languageMode==='both'?'Bilingual ready':'Flexible'}</strong><br><small>Content system</small></div></div><div class="preview-page-list">${pages.map((page,i)=>`<div><span>${i+1}. ${escapeHtml(page.name||'Visual page')}</span><small>${escapeHtml(page.preset||'custom')}</small></div>`).join('')}</div></div></div>`;
  $('#templatePreviewDialog').showModal()
}

$('#closeTemplatePreview').onclick=()=>$('#templatePreviewDialog').close();
$('#usePreviewTemplate').onclick=()=>{if(!previewTemplateItem)return;$('#newTemplate').value=previewTemplateItem.id;updateTemplateSummary(previewTemplateItem);renderTemplateChoices();$('#templatePreviewDialog').close()};
$('#templateSearch').oninput=renderTemplateChoices;
document.querySelectorAll('[data-template-filter]').forEach(b=>b.onclick=()=>{templateFilter=b.dataset.templateFilter;document.querySelectorAll('[data-template-filter]').forEach(x=>x.classList.toggle('active',x===b));renderTemplateChoices()});;(() => {
  'use strict';
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => [...r.querySelectorAll(s)];
  const view = $('#dashboardView');
  if (!view) return;

  const head = $('.dash-head', view);
  const grid = $('#inviteGrid');
  if (!head || !grid) return;

  const intro = document.createElement('div');
  intro.className = 'dashboard-intro';
  intro.innerHTML = `
    <div class="dashboard-intro-copy">
      <span class="dashboard-eyebrow">Invitation workspace</span>
      <h2>Create beautiful moments, manage every guest.</h2>
      <p>Design, publish, collect RSVPs and keep your event experience in one place.</p>
      <div class="dashboard-intro-actions"><button type="button" id="dashboardCreateV14" class="primary">Create invitation</button><a class="button-link" href="templates.html">Browse templates</a><a class="button-link" href="account.html">Account</a><button type="button" id="dashboardLogoutV14">Sign out</button></div>
    </div>
    <div class="dashboard-overview-cards">
      <article><span>Invitations</span><strong id="dashMetricTotal">0</strong></article>
      <article><span>Published</span><strong id="dashMetricLive">0</strong></article>
      <article><span>Total views</span><strong id="dashMetricViews">0</strong></article>
      <article><span>RSVPs</span><strong id="dashMetricRsvp">0</strong></article>
    </div>`;
  head.after(intro);

  const toolbar = document.createElement('div');
  toolbar.className = 'dashboard-filterbar';
  toolbar.innerHTML = `
    <div class="dashboard-search"><span>⌕</span><input id="dashboardSearch" type="search" placeholder="Search invitations…"></div>
    <div class="dashboard-filter-tabs" role="group" aria-label="Invitation status">
      <button type="button" class="active" data-dash-filter="all">All</button>
      <button type="button" data-dash-filter="published">Published</button>
      <button type="button" data-dash-filter="draft">Drafts</button>
      <button type="button" data-dash-filter="archived">Archived</button>
    </div>`;
  intro.after(toolbar);

  $('#dashboardCreateV14')?.addEventListener('click',()=>$('#newBtn')?.click());
  $('#dashboardLogoutV14')?.addEventListener('click',()=>$('#logoutBtn')?.click());
  let statusFilter = 'all';
  function availableInvites(){
    try { return Array.isArray(invites) ? invites : []; } catch { return []; }
  }
  function updateMetrics(){
    const items = availableInvites();
    const total = items.filter(x=>!x.archived).length;
    const live = items.filter(x=>!x.archived && String(x.status||'').toLowerCase().includes('publish')).length;
    const views = items.reduce((s,x)=>s+Number(x.views||0),0);
    const rsvp = items.reduce((s,x)=>s+Number(x.rsvps||0),0);
    $('#dashMetricTotal').textContent = total.toLocaleString();
    $('#dashMetricLive').textContent = live.toLocaleString();
    $('#dashMetricViews').textContent = views.toLocaleString();
    $('#dashMetricRsvp').textContent = rsvp.toLocaleString();
  }
  function decorateCards(){
    $$('.invite-card', grid).forEach(card=>{
      const status = $('.invite-body>span',card);
      if(status) status.classList.add('invite-status-pill');
      const cover=$('.invite-cover',card);
      if(cover){cover.classList.add('invite-rendered-thumbnail');cover.setAttribute('type','button')}
    });
  }
  function applyFilter(){
    const q = ($('#dashboardSearch')?.value||'').trim().toLowerCase();
    $$('.invite-card',grid).forEach(card=>{
      const title=($('.invite-body h2',card)?.textContent||'').toLowerCase();
      const status=($('.invite-body>span',card)?.textContent||'').toLowerCase();
      const archived=Number.parseFloat(card.style.opacity||'1')<1;
      const statusOk=statusFilter==='all'||(statusFilter==='published'&&status.includes('publish'))||(statusFilter==='draft'&&!archived&&!status.includes('publish'))||(statusFilter==='archived'&&archived);
      card.hidden=!(statusOk&&(!q||title.includes(q)));
    });
  }
  $('#dashboardSearch').addEventListener('input',applyFilter);
  $$('[data-dash-filter]').forEach(b=>b.onclick=()=>{statusFilter=b.dataset.dashFilter;$$('[data-dash-filter]').forEach(x=>x.classList.toggle('active',x===b));applyFilter()});

  const observer=new MutationObserver(()=>{decorateCards();updateMetrics();applyFilter()});
  observer.observe(grid,{childList:true,subtree:true});
  decorateCards();updateMetrics();applyFilter();
})();;(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const html=document.documentElement, body=document.body;
body.classList.add('ui-boot');requestAnimationFrame(()=>requestAnimationFrame(()=>{body.classList.remove('ui-boot');body.classList.add('ui-ready')}));
function currentMode(){return localStorage.getItem('einvite-theme-mode')==='dark'?'dark':'light'}
function applyTheme(mode,announce=false){
  const resolved=mode==='dark'?'dark':'light';
  if(announce){html.classList.add('theme-transition');setTimeout(()=>html.classList.remove('theme-transition'),340)}
  html.dataset.theme=resolved;html.dataset.themeMode=mode;html.style.colorScheme=resolved;
  localStorage.setItem('einvite-theme-mode',mode);
  $$('.ui-theme-menu button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  const icon=$('.ui-theme-icon');if(icon)icon.textContent=resolved==='dark'?'☾':'☀';
  if(announce)toast(`${resolved[0].toUpperCase()+resolved.slice(1)} appearance`,'◐');
}
applyTheme(currentMode());
function installThemeControl(){
  const header=$('body:not(:has(.guest))>header');if(header&&$('.ui-theme',header))return;
  const wrap=document.createElement('div');wrap.className='ui-theme'+(header?'':' floating');
  wrap.innerHTML=`<button type="button" class="ui-theme-button" aria-label="Appearance" aria-haspopup="menu" aria-expanded="false" data-ui-tooltip="Appearance (Alt+T)"><span class="ui-theme-icon">◐</span></button><div class="ui-theme-menu" role="menu" hidden>
  <button type="button" data-mode="light"><span>☀</span><b>Light</b><span class="check">✓</span></button>
  <button type="button" data-mode="dark"><span>☾</span><b>Dark</b><span class="check">✓</span></button></div>`;
  if(header){const logout=$('#logoutBtn',header); if(logout)header.insertBefore(wrap,logout); else header.append(wrap)}else document.body.append(wrap);
  const trigger=$('.ui-theme-button',wrap),menu=$('.ui-theme-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  $$('[data-mode]',menu).forEach(b=>b.onclick=()=>{applyTheme(b.dataset.mode,true);menu.hidden=true;trigger.setAttribute('aria-expanded','false')});
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  applyTheme(currentMode());
}
installThemeControl();
window.EInviteThemeController=Object.freeze({currentMode,applyTheme,cycle(){const modes=['light','dark'],i=modes.indexOf(currentMode());const next=modes[(i+1)%2];applyTheme(next,true);return next}});
function installAppLauncher(){
  const header=$('body:not(:has(.guest))>header');if(!header||$('.ui-app-launcher',header))return;
  const brand=header.querySelector('strong');if(!brand)return;
  const wrap=document.createElement('div');wrap.className='ui-app-launcher';
  wrap.innerHTML=`<button type="button" class="ui-app-launcher-button" aria-label="Open workspace navigation" aria-expanded="false" data-ui-tooltip="Workspace navigation"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></button><div class="ui-app-launcher-menu" hidden><header><strong>Workspace</strong></header><div class="ui-app-grid">
  <a href="dashboard.html"><span>⌂</span><div><b>Dashboard</b><small>Your invitations</small></div></a>
  <a href="templates.html"><span>✦</span><div><b>Templates</b><small>Reusable designs</small></div></a>
  <a href="materials.html"><span>▣</span><div><b>Materials</b><small>Photos, audio & video</small></div></a>
  <a href="designer.html"><span>◇</span><div><b>Designer</b><small>Professional workspace</small></div></a>
  <a href="billing.html"><span>◎</span><div><b>Plans</b><small>Usage & limits</small></div></a>
  <a href="account.html"><span>◉</span><div><b>Account</b><small>Profile & security</small></div></a></div></div>`;
  brand.after(wrap);const trigger=$('.ui-app-launcher-button',wrap),menu=$('.ui-app-launcher-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
}
installAppLauncher();
const page=location.pathname.split('/').pop()||'dashboard.html';$$('body:not(:has(.guest))>header a').forEach(a=>{const href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];if(href===page)a.classList.add('ui-current')});
addEventListener('pointerdown',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;const r=b.getBoundingClientRect(),s=document.createElement('span');s.className='ui-ripple';const size=Math.max(r.width,r.height);s.style.width=s.style.height=size+'px';s.style.left=(e.clientX-r.left)+'px';s.style.top=(e.clientY-r.top)+'px';b.append(s);setTimeout(()=>s.remove(),560)},true);
const spotlightSelectors='.invite-card,.metric,.response-card,.wish-card,.usage-card,.plan,.studio-card,.material-card-page,.template-choice,.page-nav-card,.studio-quick-grid button,.page-builder-library button,.element-library button,.block-library button';
$$(spotlightSelectors).forEach(el=>{el.classList.add('ui-spotlight');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)})});
const stack=document.createElement('div');stack.className='ui-toast-stack';document.body.append(stack);
function toast(message,icon='✓'){const el=document.createElement('div');el.className='ui-toast';el.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),240)},2200)}
window.einviteToast=toast;
const tip=document.createElement('div');tip.className='ui-tooltip';document.body.append(tip);let tipTimer;
document.addEventListener('pointerover',e=>{const el=e.target.closest('[data-ui-tooltip],button[title]');if(!el)return;const txt=el.dataset.uiTooltip||el.getAttribute('title');if(!txt)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{const r=el.getBoundingClientRect();tip.textContent=txt;tip.style.left=Math.max(8,Math.min(innerWidth-200,r.left+r.width/2))+'px';tip.style.top=Math.max(8,r.bottom+8)+'px';tip.classList.add('show')},350)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-ui-tooltip],button[title]')){clearTimeout(tipTimer);tip.classList.remove('show')}});
if(body.classList.contains('studio-experience')){
  const main=$('body.studio-experience>main'),toolbar=$('.studio-canvas-toolbar');
  const canvasViewport=$('.canvas-viewport');
  canvasViewport?.addEventListener('pointermove',e=>{const r=canvasViewport.getBoundingClientRect();canvasViewport.style.setProperty('--canvas-pointer-x',`${e.clientX-r.left}px`);canvasViewport.style.setProperty('--canvas-pointer-y',`${e.clientY-r.top}px`)});
  let leftWidth=Math.max(300,Math.min(520,Number(localStorage.getItem('einvite-left-width'))||370)),rightWidth=Math.max(280,Math.min(460,Number(localStorage.getItem('einvite-right-width'))||330));
  function setWidths(){const available=Math.max(900,window.innerWidth||1440),stageMin=360;leftWidth=Math.max(290,Math.min(560,leftWidth,available-rightWidth-stageMin));rightWidth=Math.max(280,Math.min(520,rightWidth,available-leftWidth-stageMin));for(const target of [html,body]){target.style.setProperty('--studio-left-width',`${leftWidth}px`);target.style.setProperty('--einvite-left-width',`${leftWidth}px`);target.style.setProperty('--studio-right-width',`${rightWidth}px`);target.style.setProperty('--einvite-inspector-width',`${rightWidth}px`)}}setWidths();window.addEventListener('resize',setWidths);
  function addToggle(side,label,symbol){if(!toolbar)return;const b=document.createElement('button');b.type='button';b.className='studio-panel-toggle';b.innerHTML=symbol;b.setAttribute('aria-label',label);b.dataset.uiTooltip=label;b.onclick=()=>{const cls=`studio-${side}-collapsed`;body.classList.toggle(cls);b.setAttribute('aria-pressed',String(body.classList.contains(cls)));localStorage.setItem(`einvite-${side}-collapsed`,body.classList.contains(cls)?'1':'0')};toolbar.prepend(b);if(localStorage.getItem(`einvite-${side}-collapsed`)==='1'){body.classList.add(`studio-${side}-collapsed`);b.setAttribute('aria-pressed','true')}return b}
  addToggle('right','Toggle inspector','▥');addToggle('left','Toggle creation panel','▤');
  function resizer(side){if(!main)return;const h=document.createElement('div');h.className=`studio-panel-resizer ${side[0]}`;main.append(h);h.addEventListener('pointerdown',e=>{h.setPointerCapture(e.pointerId);h.classList.add('dragging');body.style.userSelect='none';const start=e.clientX,startL=leftWidth,startR=rightWidth;const move=ev=>{if(side==='left'){leftWidth=Math.max(290,Math.min(560,startL+(ev.clientX-start)))}else{rightWidth=Math.max(280,Math.min(520,startR-(ev.clientX-start)))}setWidths()};const up=()=>{h.classList.remove('dragging');body.style.userSelect='';localStorage.setItem('einvite-left-width',leftWidth);localStorage.setItem('einvite-right-width',rightWidth);h.removeEventListener('pointermove',move);h.removeEventListener('pointerup',up)};h.addEventListener('pointermove',move);h.addEventListener('pointerup',up)})}
  resizer('left');resizer('right');
  const context=document.createElement('div');context.className='ui-context-menu';context.hidden=true;
  context.innerHTML=`<button data-cmd="duplicate"><span>⧉</span><b>Duplicate</b><kbd>Ctrl+D</kbd></button><button data-cmd="copy"><span>□</span><b>Copy</b><kbd>Ctrl+C</kbd></button><button data-cmd="paste"><span>▣</span><b>Paste</b><kbd>Ctrl+V</kbd></button><div class="ui-context-sep"></div><button data-cmd="forward"><span>↑</span><b>Bring forward</b><kbd></kbd></button><button data-cmd="backward"><span>↓</span><b>Send backward</b><kbd></kbd></button><button data-cmd="lock"><span>◇</span><b>Lock / unlock</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="addText"><span>T</span><b>Add text</b><kbd></kbd></button><button data-cmd="fit"><span>⌗</span><b>Fit canvas</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="delete" class="danger"><span>×</span><b>Delete</b><kbd>Del</kbd></button>`;
  document.body.append(context);
  const cmdMap={duplicate:'duplicate',copy:'copyObjects',paste:'pasteObjects',forward:'bringForward',backward:'sendBackward',addText:'addText',fit:'fitCanvas',delete:'deleteBtn'};
  context.addEventListener('click',e=>{const b=e.target.closest('[data-cmd]');if(!b)return;const cmd=b.dataset.cmd;if(cmd==='lock'){const lock=$('#objectLocked');if(lock){lock.checked=!lock.checked;lock.dispatchEvent(new Event('change',{bubbles:true}))}}else document.getElementById(cmdMap[cmd])?.click();context.hidden=true});
  $('#stage')?.addEventListener('contextmenu',e=>{e.preventDefault();const obj=e.target.closest('.object');if(obj&&!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected'))obj.click();context.hidden=false;const w=220,h=390;context.style.left=Math.min(e.clientX,innerWidth-w-8)+'px';context.style.top=Math.min(e.clientY,innerHeight-h-8)+'px'});
  document.addEventListener('pointerdown',e=>{if(!context.contains(e.target))context.hidden=true});
}
addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname===location.pathname&&u.hash)return;if(a.closest('dialog'))return;e.preventDefault();body.classList.add('ui-page-leaving');setTimeout(()=>location.href=u.href,115)});
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const editor=!!$('#stage')&&!!$('.studio-left-panel');
document.documentElement.classList.add('final-ui-ready');
const progress=document.createElement('div'); progress.className='final-route-progress'; document.body.append(progress);
addEventListener('beforeunload',()=>progress.classList.add('active'));
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href]'); if(!a||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  try{const u=new URL(a.href,location.href);if(u.origin===location.origin&&u.href!==location.href)progress.classList.add('active')}catch{}
},true);
if(!document.body.classList.contains('guest')) requestAnimationFrame(()=>document.body.classList.add('final-page-entered'));
const globalObserver=new MutationObserver(()=>{
  $$('.empty:not([data-final-empty])').forEach(el=>{el.dataset.finalEmpty='1';el.classList.add('final-empty-state')});
  $$('dialog:not([data-final-dialog])').forEach(el=>{el.dataset.finalDialog='1';el.classList.add('final-dialog')});
});
globalObserver.observe(document.body,{subtree:true,childList:true});
if(!editor)return;
const stage=$('#stage');
const objectPane=$('[data-inspector-pane="object"]');
const elementsPane=$('[data-studio-pane="elements"]');
const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const applyNow=items=>{items.forEach(item=>{try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(item)}catch{}});try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};try{typeof refreshSelectionUI==='function'&&refreshSelectionUI()}catch{}};
const setData=(key,value,{apply=true}={})=>{const items=activeObjects();if(!items.length)return;items.forEach(item=>item.dataset[key]=String(value));if(apply)applyNow(items);saveNow();refreshAdvancedControls();refreshTimeline()};
const boolData=(key,value)=>setData(key,value?'true':'false');
const selectedType=()=>activeObjects()[0]?.dataset.objectType||'';
const safeText=node=>(node?.querySelector('.content')?.textContent||node?.dataset.alt||node?.dataset.objectType||'Object').trim().slice(0,38);
function toast(message,icon='✦'){
  if(typeof window.uiToast==='function')return window.uiToast(message,icon);
  let stack=$('.final-toast-stack');if(!stack){stack=document.createElement('div');stack.className='final-toast-stack';document.body.append(stack)}
  const t=document.createElement('div');t.className='final-toast';t.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(t);setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),220)},1900)
}
function selectOnly(item){try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([item])}catch{item.click()}setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0)}
function makeId(prefix='object'){return`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`}
const advanced=document.createElement('section'); advanced.className='final-advanced-inspector';
advanced.innerHTML=`
  <div class="final-panel-title"><div><small>Creative controls</small><h2>Effects & motion</h2></div><span class="final-beta">Advanced</span></div>
  <details open class="final-control-group" data-final-group="surface"><summary>Surface & blending</summary>
    <label class="final-toggle-row"><span>Object background</span><input id="finalBgEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Background<input id="finalBgColor" type="color" value="#ffffff"></label><label>Opacity <span id="finalBgOpacityValue">100%</span><input id="finalBgOpacity" type="range" min="0" max="100" value="100"></label></div>
    <label>Blend mode<select id="finalBlendMode"><option value="normal">Normal</option><option value="multiply">Multiply</option><option value="screen">Screen</option><option value="overlay">Overlay</option><option value="soft-light">Soft light</option><option value="darken">Darken</option><option value="lighten">Lighten</option></select></label>
  </details>
  <details class="final-control-group" data-final-group="shape"><summary>Gradient fill</summary>
    <label>Fill type<select id="finalFillMode"><option value="solid">Solid</option><option value="gradient">Gradient</option></select></label>
    <div class="final-two-col"><label>Start<input id="finalGradientStart" type="color" value="#d9a6ad"></label><label>End<input id="finalGradientEnd" type="color" value="#9d4555"></label></div>
    <label>Angle <span id="finalGradientAngleValue">135°</span><input id="finalGradientAngle" type="range" min="0" max="360" value="135"></label>
    <div class="final-gradient-preview" id="finalGradientPreview"></div>
  </details>
  <details class="final-control-group" data-final-group="text"><summary>Text effects</summary>
    <label>Transform<select id="finalTextTransform"><option value="none">As typed</option><option value="uppercase">UPPERCASE</option><option value="lowercase">lowercase</option><option value="capitalize">Capitalize</option></select></label>
    <label class="final-toggle-row"><span>Gradient text</span><input id="finalTextGradientEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Start<input id="finalTextGradientStart" type="color" value="#9d4555"></label><label>End<input id="finalTextGradientEnd" type="color" value="#b58a3a"></label></div>
    <label>Gradient angle <span id="finalTextGradientAngleValue">90°</span><input id="finalTextGradientAngle" type="range" min="0" max="360" value="90"></label>
    <div class="final-two-col"><label>Outline <span id="finalStrokeValue">0px</span><input id="finalStrokeWidth" type="range" min="0" max="8" step="0.5" value="0"></label><label>Outline color<input id="finalStrokeColor" type="color" value="#ffffff"></label></div>
    <div class="final-two-col"><label>Text shadow <span id="finalTextShadowValue">0px</span><input id="finalTextShadowBlur" type="range" min="0" max="40" value="0"></label><label>Shadow color<input id="finalTextShadowColor" type="color" value="#000000"></label></div>
    <div class="final-style-presets">
      <button type="button" data-final-text-style="luxury">Luxury Gold</button><button type="button" data-final-text-style="editorial">Editorial</button><button type="button" data-final-text-style="soft">Soft Glow</button><button type="button" data-final-text-style="minimal">Minimal</button>
    </div>
  </details>
  <details open class="final-control-group" data-final-group="motion"><summary>Motion timing</summary>
    <label>Animation delay <span id="finalDelayValue">0ms</span><input id="finalAnimationDelay" type="range" min="0" max="5000" step="50" value="0"></label>
    <div class="final-inline-actions"><button type="button" id="finalPreviewSelection">▶ Preview selected</button><button type="button" id="finalPreviewPage">▶ Preview page</button><button type="button" id="finalStagger">Stagger selected</button></div>
  </details>
  <details class="final-control-group" data-final-group="layout"><summary>Smart layout</summary>
    <div class="final-layout-grid"><button data-final-layout="horizontal">Horizontal stack</button><button data-final-layout="vertical">Vertical stack</button><button data-final-layout="grid">Smart grid</button><button data-final-layout="center">Center selection</button><button data-final-layout="equal-width">Equal width</button><button data-final-layout="equal-height">Equal height</button></div>
  </details>`;
if(objectPane)objectPane.append(advanced);
const controls={
 bgEnabled:$('#finalBgEnabled'),bgColor:$('#finalBgColor'),bgOpacity:$('#finalBgOpacity'),blend:$('#finalBlendMode'),fillMode:$('#finalFillMode'),gradientStart:$('#finalGradientStart'),gradientEnd:$('#finalGradientEnd'),gradientAngle:$('#finalGradientAngle'),textGradientEnabled:$('#finalTextGradientEnabled'),textGradientStart:$('#finalTextGradientStart'),textGradientEnd:$('#finalTextGradientEnd'),textGradientAngle:$('#finalTextGradientAngle'),strokeWidth:$('#finalStrokeWidth'),strokeColor:$('#finalStrokeColor'),textShadowBlur:$('#finalTextShadowBlur'),textShadowColor:$('#finalTextShadowColor'),textTransform:$('#finalTextTransform'),delay:$('#finalAnimationDelay')
};
function refreshAdvancedControls(){
  const item=activeObjects()[0],has=!!item,type=item?.dataset.objectType||'';
  advanced.classList.toggle('is-disabled',!has);
  $$('[data-final-group="shape"]',advanced).forEach(x=>x.hidden=type!=='shape');
  $$('[data-final-group="text"]',advanced).forEach(x=>x.hidden=!['text','decoration'].includes(type));
  if(!item)return;
  controls.bgEnabled.checked=item.dataset.backgroundEnabled==='true';controls.bgColor.value=item.dataset.backgroundColor||'#ffffff';controls.bgOpacity.value=item.dataset.backgroundOpacity??100;$('#finalBgOpacityValue').textContent=`${controls.bgOpacity.value}%`;controls.blend.value=item.dataset.blendMode||'normal';
  controls.fillMode.value=item.dataset.fillMode||'solid';controls.gradientStart.value=item.dataset.gradientStart||'#d9a6ad';controls.gradientEnd.value=item.dataset.gradientEnd||'#9d4555';controls.gradientAngle.value=item.dataset.gradientAngle||135;$('#finalGradientAngleValue').textContent=`${controls.gradientAngle.value}°`;$('#finalGradientPreview').style.background=`linear-gradient(${controls.gradientAngle.value}deg,${controls.gradientStart.value},${controls.gradientEnd.value})`;
  controls.textGradientEnabled.checked=item.dataset.textGradientEnabled==='true';controls.textGradientStart.value=item.dataset.textGradientStart||'#9d4555';controls.textGradientEnd.value=item.dataset.textGradientEnd||'#b58a3a';controls.textGradientAngle.value=item.dataset.textGradientAngle||90;$('#finalTextGradientAngleValue').textContent=`${controls.textGradientAngle.value}°`;controls.strokeWidth.value=item.dataset.textStrokeWidth||0;$('#finalStrokeValue').textContent=`${controls.strokeWidth.value}px`;controls.strokeColor.value=item.dataset.textStrokeColor||'#ffffff';controls.textShadowBlur.value=item.dataset.textShadowBlur||0;$('#finalTextShadowValue').textContent=`${controls.textShadowBlur.value}px`;controls.textShadowColor.value=item.dataset.textShadowColor||'#000000';controls.textTransform.value=item.dataset.textTransform||'none';controls.delay.value=item.dataset.animationDelay||0;$('#finalDelayValue').textContent=`${controls.delay.value}ms`;
}
controls.bgEnabled.onchange=e=>boolData('backgroundEnabled',e.target.checked);controls.bgColor.oninput=e=>setData('backgroundColor',e.target.value);controls.bgOpacity.oninput=e=>{$('#finalBgOpacityValue').textContent=`${e.target.value}%`;setData('backgroundOpacity',e.target.value)};controls.blend.onchange=e=>setData('blendMode',e.target.value);
controls.fillMode.onchange=e=>setData('fillMode',e.target.value);controls.gradientStart.oninput=e=>{setData('gradientStart',e.target.value);refreshAdvancedControls()};controls.gradientEnd.oninput=e=>{setData('gradientEnd',e.target.value);refreshAdvancedControls()};controls.gradientAngle.oninput=e=>{$('#finalGradientAngleValue').textContent=`${e.target.value}°`;setData('gradientAngle',e.target.value);refreshAdvancedControls()};
controls.textGradientEnabled.onchange=e=>boolData('textGradientEnabled',e.target.checked);controls.textGradientStart.oninput=e=>setData('textGradientStart',e.target.value);controls.textGradientEnd.oninput=e=>setData('textGradientEnd',e.target.value);controls.textGradientAngle.oninput=e=>{$('#finalTextGradientAngleValue').textContent=`${e.target.value}°`;setData('textGradientAngle',e.target.value)};controls.strokeWidth.oninput=e=>{$('#finalStrokeValue').textContent=`${e.target.value}px`;setData('textStrokeWidth',e.target.value)};controls.strokeColor.oninput=e=>setData('textStrokeColor',e.target.value);controls.textShadowBlur.oninput=e=>{$('#finalTextShadowValue').textContent=`${e.target.value}px`;setData('textShadowBlur',e.target.value)};controls.textShadowColor.oninput=e=>setData('textShadowColor',e.target.value);controls.textTransform.onchange=e=>setData('textTransform',e.target.value);controls.delay.oninput=e=>{$('#finalDelayValue').textContent=`${e.target.value}ms`;setData('animationDelay',e.target.value,{apply:false})};
const textStyles={
 luxury:{textGradientEnabled:'true',textGradientStart:'#7a5718',textGradientEnd:'#e9c86e',textGradientAngle:'90',textStrokeWidth:'0',textShadowBlur:'10',textShadowColor:'#5b3a0b',fontWeight:'700',letterSpacing:'1'},
 editorial:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'italic',letterSpacing:'0.5',textTransform:'none'},
 soft:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'18',textShadowColor:'#9d4555',fontWeight:'400',letterSpacing:'0'},
 minimal:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'normal',letterSpacing:'2',textTransform:'uppercase'}
};
$$('[data-final-text-style]').forEach(b=>b.onclick=()=>{const preset=textStyles[b.dataset.finalTextStyle];const items=activeObjects().filter(x=>['text','decoration'].includes(x.dataset.objectType));items.forEach(item=>Object.entries(preset).forEach(([k,v])=>item.dataset[k]=v));applyNow(items);saveNow();refreshAdvancedControls();toast(`${b.textContent.trim()} style applied`)});
function keyframesFor(name){return({
 'fade-up':[{opacity:0,transform:'translateY(24px)'},{opacity:1,transform:'translateY(0)'}],
 'soft-zoom':[{opacity:0,transform:'scale(.9)'},{opacity:1,transform:'scale(1)'}],
 'slide-left':[{opacity:0,transform:'translateX(45px)'},{opacity:1,transform:'translateX(0)'}],
 'blur-in':[{opacity:0,filter:'blur(14px)'},{opacity:1,filter:'blur(0)'}],
 'bounce-in':[{opacity:0,transform:'scale(.72)'},{opacity:1,transform:'scale(1.05)',offset:.72},{opacity:1,transform:'scale(1)'}],
 'flip-in':[{opacity:0,transform:'rotateY(80deg)'},{opacity:1,transform:'rotateY(0)'}],
 'float':[{transform:'translateY(0)'},{transform:'translateY(-12px)'},{transform:'translateY(0)'}],
 none:[{opacity:1},{opacity:1}]
})[name]||[{opacity:0},{opacity:1}]}
function previewObjects(items){items.forEach(item=>{const duration=Math.max(300,Math.min(3000,Number(item.dataset.duration||900))),delay=Math.max(0,Math.min(5000,Number(item.dataset.animationDelay||0))),rotation=`rotate(${Number(item.dataset.rotation||0)}deg)`,frames=keyframesFor(item.dataset.animation||'fade-up').map(frame=>({...frame,transform:frame.transform?`${frame.transform} ${rotation}`:rotation}));item.animate(frames,{duration,delay,easing:'cubic-bezier(.2,.8,.2,1)',fill:'none',iterations:item.dataset.animation==='float'?2:1})})}
window.EInvitePreviewObjects=items=>previewObjects(Array.isArray(items)?items:[]);
$('#finalPreviewSelection').onclick=()=>previewObjects(activeObjects());$('#finalPreviewPage').onclick=()=>previewObjects($$('.object'));$('#finalStagger').onclick=()=>{const items=activeObjects();if(items.length<2)return toast('Select two or more objects to stagger','!');items.sort((a,b)=>(parseFloat(a.style.top)||0)-(parseFloat(b.style.top)||0)||(parseFloat(a.style.left)||0)-(parseFloat(b.style.left)||0)).forEach((item,i)=>item.dataset.animationDelay=String(i*140));saveNow();refreshAdvancedControls();refreshTimeline();previewObjects(items);toast(`Staggered ${items.length} objects`)};
const timeline=document.createElement('section');timeline.className='final-timeline';timeline.innerHTML=`<div class="final-panel-title"><div><small>Sequence</small><h2>Motion timeline</h2></div><button id="finalTimelinePlay" type="button">▶ Play all</button></div><div id="finalTimelineRows"></div>`;if(objectPane)objectPane.append(timeline);
function refreshTimeline(){const host=$('#finalTimelineRows');if(!host)return;const items=$$('.object').sort((a,b)=>Number(a.style.zIndex||0)-Number(b.style.zIndex||0));host.innerHTML=items.length?'':'<p class="hint">Add objects to build a motion sequence.</p>';const maxEnd=Math.max(1000,...items.map(x=>Number(x.dataset.animationDelay||0)+Number(x.dataset.duration||900)));items.forEach(item=>{const row=document.createElement('button');row.type='button';row.className=`final-timeline-row${item.classList.contains('selected')||item.classList.contains('multi-selected')?' active':''}`;const delay=Number(item.dataset.animationDelay||0),duration=Number(item.dataset.duration||900);row.innerHTML=`<span class="final-timeline-icon">${item.dataset.objectType==='image'?'▣':item.dataset.objectType==='shape'?'□':'T'}</span><span class="final-timeline-name">${safeText(item)||'Object'}</span><span class="final-timeline-track"><i style="left:${delay/maxEnd*100}%;width:${Math.max(4,duration/maxEnd*100)}%"></i></span><small>${delay}ms</small>`;row.onclick=()=>selectOnly(item);host.append(row)})}
$('#finalTimelinePlay').onclick=()=>previewObjects($$('.object'));
function stagePercentFrame(item){return{left:parseFloat(item.style.left)||0,top:parseFloat(item.style.top)||0,width:item.getBoundingClientRect().width/stage.getBoundingClientRect().width*100,height:item.getBoundingClientRect().height/stage.getBoundingClientRect().height*100}}
function smartLayout(kind){const items=activeObjects().filter(x=>x.dataset.locked!=='true');if(!items.length)return toast('Select objects first','!');const frames=items.map(x=>({item:x,...stagePercentFrame(x)}));if(kind==='center'){const minL=Math.min(...frames.map(x=>x.left)),maxR=Math.max(...frames.map(x=>x.left+x.width)),minT=Math.min(...frames.map(x=>x.top)),maxB=Math.max(...frames.map(x=>x.top+x.height)),dx=50-(minL+maxR)/2,dy=50-(minT+maxB)/2;frames.forEach(x=>{x.item.style.left=`${x.left+dx}%`;x.item.style.top=`${x.top+dy}%`})}
 else if(kind==='horizontal'){const gap=3,total=frames.reduce((s,x)=>s+x.width,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.left-b.left).forEach(x=>{x.item.style.left=`${cur}%`;x.item.style.top='45%';cur+=x.width+gap})}
 else if(kind==='vertical'){const gap=2,total=frames.reduce((s,x)=>s+x.height,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.top-b.top).forEach(x=>{x.item.style.top=`${cur}%`;x.item.style.left=`${Math.max(4,(100-x.width)/2)}%`;cur+=x.height+gap})}
 else if(kind==='grid'){const cols=Math.ceil(Math.sqrt(frames.length)),gap=3,cell=(92-gap*(cols-1))/cols;frames.forEach((x,i)=>{const row=Math.floor(i/cols),col=i%cols;x.item.style.left=`${4+col*(cell+gap)}%`;x.item.style.top=`${8+row*22}%`;x.item.style.width=`${cell}%`})}
 else if(kind==='equal-width'){const w=Math.max(...frames.map(x=>x.width));frames.forEach(x=>x.item.style.width=`${w}%`)}
 else if(kind==='equal-height'){const h=Math.max(...frames.map(x=>x.height));frames.forEach(x=>x.item.style.height=`${h}%`)}
 try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}saveNow();toast('Layout updated')}
$$('[data-final-layout]').forEach(b=>b.onclick=()=>smartLayout(b.dataset.finalLayout));
const library=[
 {id:'flourish-1',name:'Classic flourish',cat:'Ornaments',glyph:'❦'},{id:'flourish-2',name:'Fine flourish',cat:'Ornaments',glyph:'❧'},{id:'sparkle-1',name:'Four-point sparkle',cat:'Ornaments',glyph:'✦'},{id:'sparkle-2',name:'Soft sparkle',cat:'Ornaments',glyph:'✧'},{id:'star-1',name:'Decorative star',cat:'Ornaments',glyph:'✶'},{id:'diamond-1',name:'Open diamond',cat:'Ornaments',glyph:'◇'},{id:'diamond-2',name:'Solid diamond',cat:'Ornaments',glyph:'◆'},
 {id:'heart-1',name:'Classic heart',cat:'Romance',glyph:'♥'},{id:'heart-2',name:'Outline heart',cat:'Romance',glyph:'♡'},{id:'rings',name:'Wedding rings',cat:'Romance',glyph:'◯◯'},{id:'infinity',name:'Forever mark',cat:'Romance',glyph:'∞'},{id:'love-spark',name:'Love sparkle',cat:'Romance',glyph:'♡ ✦ ♡'},
 {id:'leaf-1',name:'Botanical leaf',cat:'Botanical',glyph:'❧'},{id:'flower-1',name:'Flower mark',cat:'Botanical',glyph:'✿'},{id:'flower-2',name:'Elegant flower',cat:'Botanical',glyph:'❀'},{id:'petal',name:'Petal cluster',cat:'Botanical',glyph:'❋'},{id:'branch',name:'Leaf branch',cat:'Botanical',glyph:'☘'},
 {id:'crown',name:'Royal crown',cat:'Ceremonial',glyph:'♛'},{id:'royal',name:'Royal emblem',cat:'Ceremonial',glyph:'♔'},{id:'sun',name:'Ceremonial sun',cat:'Ceremonial',glyph:'☼'},{id:'blessing',name:'Blessing mark',cat:'Ceremonial',glyph:'✺'},{id:'lotus',name:'Lotus-inspired mark',cat:'Ceremonial',glyph:'✾'},
 {id:'quote',name:'Quote mark',cat:'Editorial',glyph:'“'},{id:'bullet',name:'Editorial bullet',cat:'Editorial',glyph:'•'},{id:'section',name:'Section divider',cat:'Editorial',glyph:'— ✦ —'},{id:'roman',name:'Roman divider',cat:'Editorial',glyph:'I · II · III'},
 {id:'rect',name:'Rectangle',cat:'Shapes',shape:'rectangle'},{id:'circle',name:'Circle',cat:'Shapes',shape:'circle'},{id:'line',name:'Line',cat:'Shapes',shape:'line'},{id:'panel',name:'Glass panel',cat:'Shapes',shape:'panel'},
 {id:'title-luxury',name:'Luxury title',cat:'Text styles',text:'YOUR CELEBRATION',preset:'luxury'},{id:'title-editorial',name:'Editorial title',cat:'Text styles',text:'A beautiful beginning',preset:'editorial'},{id:'khmer-title',name:'Khmer ceremonial title',cat:'Text styles',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',preset:'khmer'},{id:'date-badge',name:'Date badge',cat:'Text styles',text:'27 · 12 · 2026',preset:'date'},
 {id:'khmer-diamond-row',name:'Khmer diamond row',cat:'Khmer motifs',glyph:'◇ ◆ ◇ ◆ ◇'},{id:'khmer-gold-divider',name:'Ceremonial divider',cat:'Khmer motifs',glyph:'✦ ◇ ✦'},{id:'khmer-lotus-row',name:'Lotus row',cat:'Khmer motifs',glyph:'✾  ✾  ✾'},{id:'khmer-blessing-row',name:'Blessing ornament',cat:'Khmer motifs',glyph:'✺ ✦ ✺'},{id:'khmer-temple-line',name:'Temple line',cat:'Khmer motifs',glyph:'⌂ ◇ ⌂'},{id:'khmer-royal-row',name:'Royal row',cat:'Khmer motifs',glyph:'♔  ◆  ♔'},
 {id:'confetti-1',name:'Confetti sparkle',cat:'Celebration',glyph:'✦ ✧ ✶ ✦'},{id:'party-stars',name:'Party stars',cat:'Celebration',glyph:'★ ☆ ★'},{id:'balloon-pair',name:'Balloon pair',cat:'Celebration',glyph:'◯  ◯'},{id:'gift-mark',name:'Gift mark',cat:'Celebration',glyph:'▣'},{id:'cake-mark',name:'Cake mark',cat:'Celebration',glyph:'♨'},{id:'music-notes',name:'Music notes',cat:'Celebration',glyph:'♪ ♫ ♪'},
 {id:'business-arrow',name:'Forward arrow',cat:'Business',glyph:'→'},{id:'business-grid',name:'Executive grid',cat:'Business',glyph:'□ □ □'},{id:'business-dots',name:'Modern dots',cat:'Business',glyph:'• • • •'},{id:'business-plus',name:'Modern plus',cat:'Business',glyph:'+  +  +'},{id:'business-chevron',name:'Chevron line',cat:'Business',glyph:'› › ›'},{id:'business-rule',name:'Executive rule',cat:'Business',glyph:'━━━'},
 {id:'corner-top-left',name:'Corner flourish',cat:'Borders',glyph:'⌜❦'},{id:'corner-top-right',name:'Reverse corner',cat:'Borders',glyph:'❦⌝'},{id:'thin-rule',name:'Thin divider',cat:'Borders',glyph:'────────'},{id:'diamond-rule',name:'Diamond divider',cat:'Borders',glyph:'── ◇ ──'},{id:'spark-rule',name:'Spark divider',cat:'Borders',glyph:'── ✦ ──'},{id:'dot-rule',name:'Dotted divider',cat:'Borders',glyph:'· · · · · ·'},
 {id:'leaf-pair',name:'Leaf pair',cat:'Botanical',glyph:'❧  ❧'},{id:'flower-row',name:'Flower row',cat:'Botanical',glyph:'❀ ✿ ❀'},{id:'garden-spark',name:'Garden sparkle',cat:'Botanical',glyph:'❧ ✦ ❧'},{id:'clover-row',name:'Clover row',cat:'Botanical',glyph:'☘ ☘ ☘'},{id:'small-bloom',name:'Small bloom',cat:'Botanical',glyph:'✽'},{id:'floral-divider',name:'Floral divider',cat:'Botanical',glyph:'❀ ─ ❀'},
 {id:'love-divider',name:'Heart divider',cat:'Romance',glyph:'── ♡ ──'},{id:'heart-cluster',name:'Heart cluster',cat:'Romance',glyph:'♡ ♥ ♡'},{id:'promise-mark',name:'Promise mark',cat:'Romance',glyph:'∞ ♡'},{id:'ring-divider',name:'Ring divider',cat:'Romance',glyph:'─ ◯◯ ─'},{id:'love-quote',name:'Love quote',cat:'Text styles',text:'A lifetime begins here',preset:'editorial'},{id:'thank-you',name:'Thank-you title',cat:'Text styles',text:'WITH LOVE & GRATITUDE',preset:'luxury'},
 {id:'circle-outline',name:'Circle outline',cat:'Shapes',shape:'circle'},{id:'soft-panel',name:'Soft panel',cat:'Shapes',shape:'panel'},{id:'wide-line',name:'Wide line',cat:'Shapes',shape:'line'},{id:'square-card',name:'Square card',cat:'Shapes',shape:'rectangle'}
];
const librarySection=document.createElement('section');librarySection.className='final-element-library';librarySection.innerHTML=`<div class="final-panel-title"><div><small>Invitation library</small><h2>Design elements</h2></div><span class="final-library-count"></span></div><div class="final-library-search"><span>⌕</span><input type="search" placeholder="Search ornaments, flowers, text…"></div><div class="final-library-cats"></div><div class="final-library-grid"></div>`;
if(elementsPane)elementsPane.insertBefore(librarySection,elementsPane.querySelector('.studio-pane-heading')?.nextSibling||elementsPane.firstChild);
let libraryCat='All',libraryQuery='';const favKey='einvite-element-favorites-v1',recentKey='einvite-element-recent-v1';let favorites=new Set(JSON.parse(localStorage.getItem(favKey)||'[]')),recent=JSON.parse(localStorage.getItem(recentKey)||'[]');
const cats=['All','Favorites','Recent',...new Set(library.map(x=>x.cat))];
function addCustomElement(item,drop){if(item.shape){if(typeof addDesignElement==='function')addDesignElement(item.shape);return}
 const type='decoration',obj=typeof createObject==='function'?createObject(makeId('library'),type):null;if(!obj)return;const content=obj.querySelector('.content');content.textContent=item.text||item.glyph||'✦';obj.dataset.color=(window.state?.accent||$('#accent')?.value||'#9d4555');obj.dataset.fontSize=item.text?'34':'64';obj.style.width=item.text?'76%':'150px';obj.style.height=item.text?'110px':'120px';obj.style.left=drop?`${drop.x}%`:(item.text?'12%':'32%');obj.style.top=drop?`${drop.y}%`:'38%';if(item.preset==='luxury'){obj.dataset.textGradientEnabled='true';obj.dataset.textGradientStart='#7a5718';obj.dataset.textGradientEnd='#e9c86e';obj.dataset.fontWeight='700';obj.dataset.letterSpacing='2'}if(item.preset==='editorial'){obj.dataset.fontStyle='italic';obj.dataset.font='serif-georgia';obj.dataset.fontSize='38'}if(item.preset==='khmer'){obj.dataset.font="noto-serif-khmer";obj.dataset.fontSize='34';obj.dataset.color='#a87616'}if(item.preset==='date'){obj.dataset.letterSpacing='4';obj.dataset.fontSize='26';obj.dataset.backgroundEnabled='true';obj.dataset.backgroundColor='#ffffff';obj.dataset.backgroundOpacity='78';obj.dataset.borderRadius='28'}applyObjectVisualStyle(obj);stage.append(obj);clearSelection();setSelection([obj]);saveNow();
 recent=[item.id,...recent.filter(x=>x!==item.id)].slice(0,10);localStorage.setItem(recentKey,JSON.stringify(recent));renderLibrary();toast(`${item.name} added`)}
function filteredLibrary(){return library.filter(x=>{if(libraryCat==='Favorites'&&!favorites.has(x.id))return false;if(libraryCat==='Recent'&&!recent.includes(x.id))return false;if(!['All','Favorites','Recent'].includes(libraryCat)&&x.cat!==libraryCat)return false;return!libraryQuery||`${x.name} ${x.cat}`.toLowerCase().includes(libraryQuery)})}
function renderLibrary(){const catHost=$('.final-library-cats',librarySection),grid=$('.final-library-grid',librarySection);catHost.innerHTML=cats.map(c=>`<button type="button" class="${c===libraryCat?'active':''}" data-cat="${c}">${c}</button>`).join('');catHost.querySelectorAll('button').forEach(b=>b.onclick=()=>{libraryCat=b.dataset.cat;renderLibrary()});const items=filteredLibrary();$('.final-library-count',librarySection).textContent=`${items.length} items`;grid.innerHTML='';items.forEach(item=>{const card=document.createElement('article');card.className='final-element-card';card.draggable=true;card.innerHTML=`<button type="button" class="final-fav ${favorites.has(item.id)?'active':''}" aria-label="Favorite">★</button><div class="final-element-preview">${item.shape?`<i class="shape-${item.shape}"></i>`:`<span>${item.text||item.glyph}</span>`}</div><strong>${item.name}</strong><small>${item.cat}</small>`;card.onclick=e=>{if(e.target.closest('.final-fav'))return;addCustomElement(item)};card.querySelector('.final-fav').onclick=e=>{e.stopPropagation();favorites.has(item.id)?favorites.delete(item.id):favorites.add(item.id);localStorage.setItem(favKey,JSON.stringify([...favorites]));renderLibrary()};card.ondragstart=e=>{e.dataTransfer.setData('application/x-einvite-library-item',item.id);e.dataTransfer.effectAllowed='copy'};grid.append(card)})}
$('.final-library-search input',librarySection).oninput=e=>{libraryQuery=e.target.value.trim().toLowerCase();renderLibrary()};renderLibrary();
stage.addEventListener('dragover',e=>{if(Array.from(e.dataTransfer.types||[]).includes('application/x-einvite-library-item')){e.preventDefault();stage.classList.add('final-library-drop')}});stage.addEventListener('dragleave',()=>stage.classList.remove('final-library-drop'));stage.addEventListener('drop',e=>{const id=e.dataTransfer.getData('application/x-einvite-library-item');if(!id)return;e.preventDefault();stage.classList.remove('final-library-drop');const r=stage.getBoundingClientRect(),item=library.find(x=>x.id===id);if(item)addCustomElement(item,{x:Math.max(0,Math.min(85,(e.clientX-r.left)/r.width*100)),y:Math.max(0,Math.min(85,(e.clientY-r.top)/r.height*100))})});
const observer=new MutationObserver(()=>{refreshAdvancedControls();refreshTimeline()});observer.observe(stage,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-animation-delay','data-fill-mode','data-text-gradient-enabled']});
document.addEventListener('pointerup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);document.addEventListener('keyup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);
refreshAdvancedControls();refreshTimeline();
const tour=document.createElement('dialog');tour.className='final-tour';tour.innerHTML=`<form method="dialog"><button class="final-tour-close" aria-label="Close">×</button></form><div class="final-tour-art">✦</div><p class="invite-kicker">Creation Studio</p><h1>Design the invitation. Run the event.</h1><p>This workspace combines free-form visual creation with pages, animation, guest RSVP, publishing, Khmer dates and event operations.</p><div class="final-tour-grid"><article><b>1</b><strong>Create</strong><span>Drag elements, upload media and style every object.</span></article><article><b>2</b><strong>Build pages</strong><span>Mix free-form artboards with functional event sections.</span></article><article><b>3</b><strong>Animate</strong><span>Sequence motion with delay, duration and stagger controls.</span></article><article><b>4</b><strong>Publish</strong><span>Run the Design Check, publish a snapshot and manage guests.</span></article></div><div class="final-tour-actions"><button type="button" id="finalTourExplore">Explore studio</button><button type="button" id="finalTourDismiss" class="primary">Start creating</button></div>`;document.body.append(tour);
const TOUR_VERSION='studio-v27',LEGACY_TOUR_KEY='einvite-final-tour-seen-v1';let tourKey='',tourAutomatic=false,tourLauncher=null,tourSessionSeen=false,tourOpenGeneration=0;
async function resolveTourIdentity(){try{await window.EInviteBackend?.ready;if(window.EInviteBackend?.isAvailable?.()){const response=await fetch('/api/auth/me',{credentials:'same-origin'}),data=response.ok?await response.json():null,user=data?.user;if(user?.id||user?.email)return String(user.id||user.email)}}catch{}try{const user=JSON.parse(localStorage.getItem('sovan-account-v1')||'null');if(user?.id||user?.email)return String(user.id||user.email)}catch{}return'local-anonymous'}
function persistTourSeen(){tourSessionSeen=true;if(tourKey)localStorage.setItem(tourKey,'1')}
function workspaceFocus(){const target=$('#stage')||$('#canvasViewport')||$('.stage-wrap');target?.setAttribute?.('tabindex','-1');setTimeout(()=>{target?.focus?.({preventScroll:true});if(target)document.body.dataset.keyboardOwner='canvas'},0)}
function closeTour({explore=false}={}){tourOpenGeneration++;persistTourSeen();if(tour.open)tour.close();if(explore){document.querySelector('[data-studio-tab="elements"]')?.click();setTimeout(()=>$('.final-element-library')?.scrollIntoView({behavior:'smooth'}),100)}}
$('#finalTourDismiss').onclick=()=>closeTour();$('#finalTourExplore').onclick=()=>closeTour({explore:true});tour.addEventListener('cancel',event=>{event.preventDefault();closeTour()});tour.addEventListener('close',()=>{persistTourSeen();const automatic=tourAutomatic,launcher=tourLauncher;tourAutomatic=false;tourLauncher=null;if(automatic)workspaceFocus();else requestAnimationFrame(()=>launcher?.focus?.({preventScroll:true}))});
const status=$('.studio-statusbar>div:last-child');if(status){const b=document.createElement('button');b.type='button';b.className='final-tour-trigger';b.textContent='✦ Tour';b.onclick=()=>{tourAutomatic=false;tourLauncher=b;tour.showModal()};status.prepend(b)}
window.EInviteOnboardingReady=(async()=>{const generation=++tourOpenGeneration,identity=await resolveTourIdentity();tourKey=`einvite-final-tour-seen-v2:${encodeURIComponent(identity)}:${TOUR_VERSION}`;if(localStorage.getItem(LEGACY_TOUR_KEY)==='1'&&!localStorage.getItem(tourKey))localStorage.setItem(tourKey,'1');if(generation!==tourOpenGeneration||tourSessionSeen||localStorage.getItem(tourKey)==='1')return{shown:false,identity};tourAutomatic=true;tourLauncher=null;tour.showModal();await new Promise(resolve=>requestAnimationFrame(resolve));return{shown:true,identity}})();
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
if(document.body&&!document.body.dataset.page)document.body.dataset.page=page;
function dashboard(){
  const view=$('#dashboardView'),login=$('#loginView');if(!view)return;
  view.classList.add('dashboard-home');
  const rail=document.createElement('nav');rail.className='dashboard-home-rail';rail.innerHTML=`
    <button type="button" class="rail-create" title="Create invitation"><span>＋</span>Create</button>
    <a href="dashboard.html" class="active"><span>⌂</span>Home</a>
    <a href="templates.html"><span>▣</span>Templates</a>
    <a href="materials.html"><span>▧</span>Materials</a>
    <a href="billing.html"><span>◉</span>Plans</a>
    <div class="rail-spacer"></div>
    <a href="account.html"><span>◌</span>Account</a>`;
  document.body.append(rail);
  $('.rail-create',rail).onclick=()=>$('#newBtn')?.click();
  const hero=document.createElement('section');hero.className='dashboard-home-hero';hero.innerHTML=`
    <h1>What will you create today?</h1>
    <label class="dashboard-home-search"><span>⌕</span><input type="search" placeholder="Search your invitations"></label>
    <div class="dashboard-quick-create">
      <button type="button" class="create"><i>＋</i><span>Create</span></button>
      <a href="templates.html" class="template"><i>▣</i><span>Templates</span></a>
      <button type="button" class="wedding"><i>♡</i><span>Wedding</span></button>
      <button type="button" class="birthday"><i>✦</i><span>Birthday</span></button>
      <button type="button" class="business"><i>◇</i><span>Business</span></button>
      <a href="materials.html" class="upload"><i>⇧</i><span>Uploads</span></a>
    </div>`;
  view.prepend(hero);
  const createByType=(type)=>{const btn=$('#newBtn');btn?.click();setTimeout(()=>{const typeEl=$('#newType');if(typeEl){typeEl.value=type;typeEl.dispatchEvent(new Event('change',{bubbles:true}))}},40)};
  $('.create',hero).onclick=()=>$('#newBtn')?.click();$('.wedding',hero).onclick=()=>createByType('Wedding');$('.birthday',hero).onclick=()=>createByType('Birthday');$('.business',hero).onclick=()=>createByType('Business');
  const homeSearch=$('.dashboard-home-search input',hero);
  homeSearch.oninput=()=>{const old=$('#dashboardSearch');if(old){old.value=homeSearch.value;old.dispatchEvent(new Event('input',{bubbles:true}))}else{$$('.invite-card','#inviteGrid').forEach(card=>card.hidden=!card.textContent.toLowerCase().includes(homeSearch.value.toLowerCase()))}};
  const recent=document.createElement('div');recent.className='dashboard-recent-head';recent.innerHTML='<h2>Recent invitations</h2>';
  const filter=$('.dashboard-filter-tabs');if(filter)recent.append(filter);
  const grid=$('#inviteGrid');grid?.before(recent);
  grid?.addEventListener('click',e=>{const cover=e.target.closest('.invite-cover');if(!cover)return;const card=cover.closest('.invite-card');card?.querySelector('[data-edit]')?.click()});
  const header=$('body>header');
  function authState(){const signed=view.hidden===false;rail.hidden=!signed;if(header){header.querySelectorAll('a[href="materials.html"],a[href="billing.html"],a[href="account.html"]').forEach(a=>a.hidden=!signed);const logout=$('#logoutBtn');if(logout)logout.hidden=!signed}}
  new MutationObserver(authState).observe(view,{attributes:true,attributeFilter:['hidden']});authState();
}
function materials(){
  const head=$('.library-head'),upload=$('.upload-box');if(!head||!upload)return;
  const toggle=document.createElement('button');toggle.type='button';toggle.className='material-upload-toggle primary';toggle.innerHTML='<span>⇧</span> Upload files';head.append(toggle);upload.hidden=true;
  toggle.onclick=()=>{upload.hidden=!upload.hidden;toggle.innerHTML=upload.hidden?'<span>⇧</span> Upload files':'<span>×</span> Close upload';if(!upload.hidden)setTimeout(()=>$('#uploadFile')?.focus(),50)};
  const grid=$('#grid');
  const observer=new MutationObserver(()=>{
    const empty=$('.empty-library',grid);if(empty&&/Authentication required/i.test(empty.textContent)&&!empty.querySelector('.material-auth-action')){const a=document.createElement('a');a.href='dashboard.html';a.className='material-auth-action';a.innerHTML='<button type="button" class="primary">Sign in to use materials</button>';empty.append(a)}
  });observer.observe(grid,{childList:true,subtree:true});
}
function editor(){
  const main=$('body.studio-experience>main'),rail=$('.studio-tool-rail'),host=$('.studio-pane-host'),stage=$('#stage');if(!main||!rail||!host||!stage)return;
  if(!$('[data-studio-tab="text"]',rail)){
    const elementsBtn=$('[data-studio-tab="elements"]',rail);
    const b=document.createElement('button');b.type='button';b.className='studio-rail-button';b.dataset.studioTab='text';b.innerHTML='<span class="studio-nav-icon">T</span><span>Text</span>';b.title='Text, fonts and typography';rail.insertBefore(b,elementsBtn||null);
    const pane=document.createElement('section');pane.className='studio-pane studio-text-pane';pane.dataset.studioPane='text';pane.innerHTML=`
      <div class="studio-pane-heading"><div><small>Create</small><h1>Text</h1></div></div>
      <label class="refine-text-search"><span>⌕</span><input type="search" placeholder="Search fonts and combinations"></label>
      <button type="button" class="refine-add-text">T &nbsp; Add a text box</button>
      <button type="button" class="refine-magic-write">✦ Magic invitation writing</button>
      <section class="refine-text-section"><div><h3>Default text styles</h3></div><div class="refine-text-presets">
        <button class="refine-text-preset heading" data-refine-text="heading">Add a heading</button>
        <button class="refine-text-preset subheading" data-refine-text="subheading">Add a subheading</button>
        <button class="refine-text-preset body" data-refine-text="body">Add a little bit of body text</button>
        <button class="refine-text-preset khmer" data-refine-text="khmer">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section"><div><h3>Fonts</h3><small>Search · Khmer · Favorites</small></div><button type="button" class="refine-browse-fonts">Browse all fonts</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Quick invitation styles</small></div><div class="refine-font-combos">
        <button class="refine-font-combo" data-combo="gold"><span style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button class="refine-font-combo" data-combo="modern"><span style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><i>HEADING</i></span><small>Modern contrast</small></button>
        <button class="refine-font-combo" data-combo="romance"><span style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button class="refine-font-combo" data-combo="khmer"><span style="font-family:'Noto Serif Khmer','Khmer OS Muol Light',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      </div></section>`;
    host.append(pane);
    function activate(id){
      $$('[data-studio-tab]',rail).forEach(x=>x.classList.toggle('active',x.dataset.studioTab===id));
      $$('[data-studio-pane]',host).forEach(x=>x.classList.toggle('active',x.dataset.studioPane===id));
      localStorage.setItem('einvite-editor-left-tab',id);applyMode();
    }
    b.onclick=()=>activate('text');
    $('.refine-add-text',pane).onclick=()=>$('#addText')?.click();
    $$('.refine-text-preset',pane).forEach(btn=>btn.onclick=()=>{const source=$(`[data-text-preset="${btn.dataset.refineText}"]`);if(source)source.click();else $('#addText')?.click()});
    $('.refine-browse-fonts',pane).onclick=()=>$('.ei-font-launch')?.click();
    $('.refine-magic-write',pane).onclick=()=>{const ebtn=$('[data-studio-tab="event"]',rail);ebtn?.click();setTimeout(()=>$('#eiAiStudio textarea,.ei-ai-studio textarea')?.focus(),80)};
    const comboMap={gold:{font:'serif-georgia',size:48,color:'#b48a20',text:'Golden Hour'},modern:{font:'sans-arial',size:44,color:'#202127',text:'Your Celebration'},romance:{font:'serif-georgia',size:46,color:'#426b52',text:'Bride & Groom'},khmer:{font:"noto-serif-khmer",size:38,color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'}};
    $$('.refine-font-combo',pane).forEach(btn=>btn.onclick=()=>{const c=comboMap[btn.dataset.combo];$('#addText')?.click();setTimeout(()=>{const sel=$('.object.selected,.object.multi-selected');if(!sel)return;const content=sel.querySelector('.content');if(content)content.textContent=c.text;sel.dataset.font=c.font;sel.dataset.fontSize=String(c.size);sel.dataset.color=c.color;try{applyObjectVisualStyle(sel);save()}catch{}},40)});
    $('.refine-text-search input',pane).oninput=e=>{const q=e.target.value.toLowerCase();$$('.refine-text-preset,.refine-font-combo',pane).forEach(x=>x.hidden=!!q&&!x.textContent.toLowerCase().includes(q))};
  }
  function applyMode(){ /* centralized elsewhere */ }
  const openInspector=()=>{if(innerWidth<=1180&&$('.object.selected,.object.multi-selected',stage))document.body.classList.add('inspector-open')};
  stage.addEventListener('pointerup',()=>setTimeout(openInspector,0));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.body.classList.remove('inspector-open')});
  const inspector=$('.right');if(inspector&&!inspector.querySelector('.refine-inspector-close')){const c=document.createElement('button');c.type='button';c.className='refine-inspector-close';c.textContent='×';c.title='Close inspector';c.onclick=()=>document.body.classList.remove('inspector-open');inspector.prepend(c)}
}
if(page==='dashboard')dashboard();
if(page==='materials')materials();
if(page==='index')setTimeout(editor,0);
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
function dashboardFinal(){
  const grid=$('#inviteGrid'),view=$('#dashboardView'),header=$('body>header'); if(!grid||!view)return;
  const getInvites=()=>{try{return Array.isArray(invites)?invites:[]}catch{return[]}};
  const findInvite=id=>getInvites().find(x=>String(x.id)===String(id));
  const localDoc=id=>{try{return JSON.parse(localStorage.getItem(`sovan-invite-draft-v3:${id}`)||'null')}catch{return null}};
  const previewDoc=item=>item?.preview||localDoc(item?.id)||null;
  function buildPreview(item){
    const doc=previewDoc(item)||{},palette=doc.palette||{},fields=doc.fields||{},page0=(doc.designPages||[])[0]||null,objects=page0?.objects||doc.objects||{};
    const bg=page0?.background||doc.masterPageStyle?.background||palette.background||'#fff7f3',text=palette.text||'#342c26',heading=palette.heading||doc.accent||'#9d4555',accent=doc.accent||heading;
    const shell=document.createElement('div');shell.className='fp-project-preview';shell.style.setProperty('--preview-shell',`color-mix(in srgb, ${bg} 52%, var(--app-surface-2))`);
    const art=document.createElement('div');art.className='fp-project-artboard v20-faithful-thumbnail';art.style.setProperty('--preview-bg',bg);art.style.setProperty('--preview-text',text);art.style.setProperty('--preview-heading',heading);art.style.setProperty('--preview-accent',accent);art.style.background=bg;
    if(Object.keys(objects).length&&globalThis.EInviteTypographyRendererAdapters&&!art.closest('.invite-card')){TypographyDocumentModel?.normalizeDocument?.(doc,{mutate:true});art._typographyThumbnailController?.disconnect?.();art._typographyThumbnailController=EInviteTypographyRendererAdapters.renderThumbnail(art,doc,objects,{width:390,height:844})}
    else{const f=document.createElement('div');f.className='fp-thumb-fallback';f.innerHTML=`<small>${esc(doc.eventType||item.type||'Invitation')}</small><strong>${esc(fields.names||item.title||'Untitled invitation')}</strong><span>${esc(fields.date||'')} ${fields.venue?`· ${esc(fields.venue)}`:''}</span>`;art.append(f)}
    shell.append(art);return shell;
  }
  const timeAgo=value=>{const t=Number(value)||Date.parse(value)||0;if(!t)return'';const sec=Math.max(0,Math.round((Date.now()-t)/1000));if(sec<60)return'Edited just now';if(sec<3600)return`Edited ${Math.floor(sec/60)}m ago`;if(sec<86400)return`Edited ${Math.floor(sec/3600)}h ago`;if(sec<604800)return`Edited ${Math.floor(sec/86400)}d ago`;return`Edited ${new Date(t).toLocaleDateString()}`};
  function decorateCard(card){
    if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit;if(!id)return;const item=findInvite(id);if(!item)return;card.dataset.fpReady='1';card.dataset.inviteId=id;
    const cover=$('.invite-cover',card);if(cover){cover.replaceChildren(buildPreview(item));const status=document.createElement('span');status.className='fp-project-status';status.textContent=item.status||'Draft';cover.append(status);cover.onclick=()=>{if(!item.archived)card.querySelector('.actions [data-edit]')?.click()}}
    const body=$('.invite-body',card),stats=$('.stats',card),actions=$('.actions',card);if(!body||!actions)return;
    if(stats)stats.innerHTML=`<span>${esc(item.status||'Draft')}</span><span>${esc(timeAgo(item.updatedAt))}</span>`;
    const more=document.createElement('button');more.type='button';more.className='fp-project-more';more.setAttribute('aria-label','Project actions');more.setAttribute('aria-expanded','false');more.textContent='•••';
    const menu=document.createElement('div');menu.className='fp-project-menu';menu.setAttribute('role','menu');
    const map=[['Edit','[data-edit]'],['Guests','[data-guests]'],['Responses','[data-responses]'],['Analytics','[data-analytics]'],['Duplicate','[data-copy]'],[item.archived?'Restore':'Archive','[data-archive]'],['Delete','[data-delete]']];
    map.forEach(([label,selector])=>{const source=$(selector,actions);if(!source)return;const b=document.createElement('button');b.type='button';b.textContent=label;if(label==='Delete')b.className='danger';b.onclick=e=>{e.stopPropagation();menu.classList.remove('open');more.setAttribute('aria-expanded','false');source.click()};menu.append(b)});
    more.onclick=e=>{e.stopPropagation();$$('.fp-project-menu.open').filter(x=>x!==menu).forEach(x=>x.classList.remove('open'));menu.classList.toggle('open');more.setAttribute('aria-expanded',menu.classList.contains('open')?'true':'false')};
    body.append(more);card.append(menu);
  }
  const refresh=()=>$$('.invite-card',grid).forEach(decorateCard);new MutationObserver(refresh).observe(grid,{childList:true,subtree:true});refresh();
  document.addEventListener('click',()=>$$('.fp-project-menu.open').forEach(x=>x.classList.remove('open')));
  if(header&&!$('.fp-dashboard-profile',header)){
    const wrap=document.createElement('div');wrap.className='fp-dashboard-profile';wrap.innerHTML=`<button type="button" class="fp-profile-button" aria-label="Account menu">U</button><div class="fp-profile-popover"><div class="fp-profile-summary"><strong>Account</strong><small></small></div><a href="account.html">Account settings</a><a href="materials.html">Materials</a><a href="billing.html">Plans & usage</a><a href="designer.html" data-profile-designer hidden>Designer workspace</a><a href="admin.html" data-profile-admin hidden>Administration</a><button type="button" data-signout>Sign out</button></div>`;header.append(wrap);
    const button=$('.fp-profile-button',wrap),pop=$('.fp-profile-popover',wrap);button.onclick=e=>{e.stopPropagation();pop.classList.toggle('open')};pop.onclick=e=>e.stopPropagation();$('[data-signout]',wrap).onclick=()=>$('#logoutBtn')?.click();
    const update=()=>{let a=null;try{a=account}catch{}const email=a?.email||'Account';$('.fp-profile-summary strong',wrap).textContent=email;$('.fp-profile-summary small',wrap).textContent=[a?.role,a?.plan].filter(Boolean).join(' · ');button.textContent=(email[0]||'U').toUpperCase();$('[data-profile-designer]',wrap).hidden=!['designer','admin'].includes(a?.role);$('[data-profile-admin]',wrap).hidden=a?.role!=='admin';wrap.hidden=view.hidden};new MutationObserver(update).observe(view,{attributes:true,attributeFilter:['hidden']});update();document.addEventListener('click',()=>pop.classList.remove('open'));
  }
}
function materialsFinal(){
  const grid=$('#grid');if(!grid)return;
  let dialog=null;
  function itemById(id){try{return materials.find(x=>String(x.id)===String(id))}catch{return null}}
  function inviteName(id){try{return invitations.find(x=>String(x.id)===String(id))?.title||invitations.find(x=>String(x.id)===String(id))?.slug||'Invitation'}catch{return'Invitation'}}
  function ensureDialog(){if(dialog)return dialog;dialog=document.createElement('dialog');dialog.className='fp-material-preview-dialog';document.body.append(dialog);return dialog}
  function openPreview(item){if(!item)return;const kind=item.mime?.startsWith('image/')?'image':item.mime?.startsWith('video/')?'video':item.mime?.startsWith('audio/')?'audio':'file',d=ensureDialog();
    let media=kind==='image'?`<img src="${esc(item.url)}" alt="${esc(item.name)}">`:kind==='video'?`<video src="${esc(item.url)}" controls preload="metadata"></video>`:kind==='audio'?`<div><div class="fp-material-audio-art">♫</div><audio src="${esc(item.url)}" controls preload="metadata"></audio></div>`:`<div class="fp-material-audio-art">◇</div>`;
    d.innerHTML=`<div class="fp-material-preview-shell"><div class="fp-material-stage">${media}</div><aside class="fp-material-detail"><div class="fp-material-detail-head"><h2>${esc(item.name)}</h2><button type="button" class="fp-material-close">×</button></div><div class="fp-material-facts"><div><span>Type</span><strong>${esc(item.mime||'Unknown')}</strong></div><div><span>Size</span><strong>${typeof formatBytes==='function'?formatBytes(item.size):esc(item.size)}</strong></div><div><span>Invitation</span><strong>${esc(inviteName(item.invitationId))}</strong></div><div><span>Folder</span><strong>${esc(item.folder||'No folder')}</strong></div><div><span>Used</span><strong>${Number(item.usageCount||0)} reference${Number(item.usageCount||0)===1?'':'s'}</strong></div></div><div class="fp-material-preview-actions"><button type="button" class="primary" data-use>Use in design</button><div class="fp-material-secondary-actions"><button type="button" data-edit> Edit details</button><a href="${esc(item.url)}" download target="_blank" rel="noopener" class="button-link">Download</a></div><button type="button" class="fp-material-danger" data-delete>Delete material</button></div></aside></div>`;
    $('.fp-material-close',d).onclick=()=>d.close();$('[data-edit]',d).onclick=()=>{d.close();try{openEdit(item.id)}catch{grid.querySelector(`[data-edit="${CSS.escape(String(item.id))}"]`)?.click()}};$('[data-delete]',d).onclick=()=>{d.close();try{openEdit(item.id);setTimeout(()=>$('#deleteBtn')?.click(),40)}catch{}};$('[data-use]',d).onclick=()=>{localStorage.setItem('sovan-active-invite',item.invitationId);localStorage.setItem('einvite-pending-material-insert',JSON.stringify({url:item.url,name:item.name,mime:item.mime,assetId:item.id}));location.href=`/invitations/${encodeURIComponent(item.invitationId)}/editor`};d.showModal();
  }
  function decorate(){
    const empty=$('.empty-library',grid);if(empty&&/Authentication required|sign in|unauthorized/i.test(empty.textContent)){document.body.classList.add('material-auth-required');grid.innerHTML=`<div class="fp-material-auth-state"><div class="fp-material-auth-card"><div class="icon">◌</div><h2>Your session has expired</h2><p>Sign in again to access your photos, videos, audio, folders, and saved materials.</p><a href="dashboard.html" class="button-link primary">Sign in again</a></div></div>`;return}else document.body.classList.remove('material-auth-required');
    $$('.material-card-page',grid).forEach(card=>{if(card.dataset.fpReady==='1')return;const id=card.querySelector('[data-edit]')?.dataset.edit,item=itemById(id);if(!item)return;card.dataset.fpReady='1';const thumb=$('.material-thumb',card);if(thumb)thumb.onclick=()=>openPreview(item);const info=$('.material-info',card);if(info){const row=document.createElement('div');row.className='fp-material-meta-row';row.innerHTML=`<span>${item.mime?.split('/')[0]||'file'}</span>${Number(item.usageCount||0)?`<span class="fp-material-usage">Used ${Number(item.usageCount)}</span>`:''}`;info.append(row)}})
  }
  new MutationObserver(decorate).observe(grid,{childList:true,subtree:true});decorate();
}
function editorFinal(){
  const stage=$('#stage'),host=$('.studio-pane-host'),rail=$('.studio-tool-rail');if(!stage||!host||!rail)return;
  const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};const choose=o=>{try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([o])}catch{}};
  const makeId=p=>`${p}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;
  const closePaneOnMobile=()=>{if(innerWidth<=820&&document.body.classList.contains('studio-design-mode'))document.body.classList.add('mobile-pane-collapsed')};
  const openPane=()=>document.body.classList.remove('mobile-pane-collapsed');
  rail.addEventListener('click',openPane,true);
  if(!$('.fp-mobile-pane-handle')){const h=document.createElement('button');h.type='button';h.className='fp-mobile-pane-handle';h.textContent='›';h.title='Open creation panel';h.onclick=openPane;document.body.append(h)}
  $$('.studio-pane-heading',host).forEach(head=>{if(head.querySelector('.fp-mobile-pane-close'))return;const b=document.createElement('button');b.type='button';b.className='fp-mobile-pane-close';b.textContent='‹';b.title='Hide panel';b.onclick=closePaneOnMobile;head.append(b)});
  function addSvgAsset(asset){if(typeof createObject!=='function')return;const o=createObject(makeId('graphic'),'image');const data=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(asset.svg)}`;o.style.left=asset.left||'18%';o.style.top=asset.top||'24%';o.style.width=asset.width||'64%';o.style.height=asset.height||'190px';o.dataset.src=data;o.dataset.layerName=asset.name;o.dataset.showInGallery='false';o.dataset.showInHero='true';const img=o.querySelector('img');if(img){img.src=data;img.alt=asset.name}stage.append(o);choose(o);saveNow();window.uiToast?.(`${asset.name} added`,'✦');closePaneOnMobile()}
  const assets=[
    {name:'Khmer lotus corner',cat:'Khmer',width:'38%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220"><g fill="none" stroke="#b48735" stroke-width="5" stroke-linecap="round"><path d="M20 200C82 190 110 154 113 92M20 200c52-42 90-49 154-44"/><path d="M113 92c-29 21-44 51-40 84 28-10 51-31 64-61 12 29 35 49 65 58 1-34-15-63-45-83-1 31-8 57-20 77-13-20-21-45-24-75Z"/><path d="M174 156c38-12 72-9 120 21M205 148c18-18 31-40 36-68"/></g></svg>`},
    {name:'Royal gold flourish',cat:'Wedding',height:'120px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160"><g fill="none" stroke="#c5a15b" stroke-width="5"><path d="M18 82c110 0 124-58 210-58 48 0 57 38 72 58 15-20 24-58 72-58 86 0 100 58 210 58"/><path d="M22 84c110 0 126 54 218 54 32 0 49-18 60-48 11 30 28 48 60 48 92 0 108-54 218-54"/><circle cx="300" cy="82" r="12" fill="#c5a15b"/></g></svg>`},
    {name:'Botanical sprig',cat:'Botanical',width:'34%',height:'250px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 380"><g fill="none" stroke="#527760" stroke-width="5" stroke-linecap="round"><path d="M68 350C102 254 128 162 196 40"/><path d="M111 237c-58 4-84-23-91-59 44-7 76 11 98 44M137 176c-9-52 10-83 49-101 15 40 7 74-31 106M85 293c-43 4-67-15-76-47 34-8 64 2 83 31M169 116c-5-39 10-65 43-79 11 32 4 58-24 82"/></g></svg>`},
    {name:'Wedding arch',cat:'Wedding',width:'66%',height:'300px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 620"><path d="M80 600V270C80 120 145 30 250 30s170 90 170 240v330" fill="none" stroke="#b58a5a" stroke-width="10"/><g fill="#d9aeb3"><circle cx="93" cy="240" r="24"/><circle cx="112" cy="192" r="18"/><circle cx="392" cy="215" r="24"/><circle cx="370" cy="165" r="17"/></g><g fill="#6f8d72"><ellipse cx="126" cy="230" rx="12" ry="34" transform="rotate(45 126 230)"/><ellipse cx="374" cy="240" rx="12" ry="34" transform="rotate(-45 374 240)"/></g></svg>`},
    {name:'Diamond frame',cat:'Frames',width:'58%',height:'320px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500"><path d="M250 18 482 250 250 482 18 250Z" fill="none" stroke="#c6a35b" stroke-width="9"/><path d="M250 46 454 250 250 454 46 250Z" fill="none" stroke="#c6a35b" stroke-width="2" opacity=".7"/></svg>`},
    {name:'Lotus divider',cat:'Khmer',height:'110px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 150"><g fill="none" stroke="#a87616" stroke-width="4"><path d="M20 75h250M430 75h250"/><path d="M350 28c-24 18-36 40-35 66 17-6 29-18 35-36 6 18 18 30 35 36 1-26-11-48-35-66Z"/><path d="M350 44c-12 13-18 28-18 44 8-3 14-9 18-18 4 9 10 15 18 18 0-16-6-31-18-44Z"/></g></svg>`},
    {name:'Celebration confetti',cat:'Celebration',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 320"><g fill="none" stroke-linecap="round" stroke-width="10"><path d="M55 55l32 30M420 44l-28 36M118 258l35-17M380 263l-36-23" stroke="#ff5d8f"/><path d="M158 38l-8 42M328 45l18 39M58 180l44-4M410 170l34 12" stroke="#50b9d6"/><path d="M235 34l8 44M255 263l-5 38" stroke="#7d59d4"/></g><g fill="#f2b84b"><circle cx="101" cy="122" r="10"/><circle cx="395" cy="112" r="9"/><circle cx="205" cy="238" r="8"/></g></svg>`},
    {name:'Executive wave',cat:'Business',height:'150px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 180"><path d="M0 132C120 46 205 36 330 104c109 59 229 45 370-46v122H0Z" fill="#173e58"/><path d="M0 154C140 82 222 76 344 132c104 48 216 38 356-30v78H0Z" fill="#20a49b" opacity=".78"/></svg>`},
    {name:'Rose corner',cat:'Wedding',width:'36%',height:'220px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 300"><g fill="#d48d9c"><circle cx="82" cy="82" r="38"/><circle cx="120" cy="58" r="30"/><circle cx="131" cy="101" r="34"/></g><g fill="#6d8b70"><ellipse cx="186" cy="85" rx="24" ry="54" transform="rotate(48 186 85)"/><ellipse cx="98" cy="176" rx="22" ry="60" transform="rotate(12 98 176)"/></g><path d="M20 282C66 210 107 151 178 96" fill="none" stroke="#6d8b70" stroke-width="7"/></svg>`},
    {name:'Minimal line frame',cat:'Frames',width:'72%',height:'360px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700"><rect x="18" y="18" width="464" height="664" rx="18" fill="none" stroke="#65535f" stroke-width="3"/><rect x="38" y="38" width="424" height="624" rx="12" fill="none" stroke="#65535f" stroke-width="1" opacity=".55"/></svg>`},
    {name:'Star sparkle cluster',cat:'Celebration',width:'34%',height:'210px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 260"><g fill="#c69d55"><path d="m150 18 14 57 56 14-56 14-14 57-14-57-56-14 56-14Z"/><path d="m240 126 8 30 30 8-30 8-8 30-8-30-30-8 30-8Z" opacity=".72"/><circle cx="66" cy="182" r="12" opacity=".55"/></g></svg>`},
    {name:'Khmer geometric border',cat:'Khmer',height:'88px',svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 100"><defs><pattern id="p" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M40 4 76 40 40 76 4 40Z" fill="none" stroke="#a87616" stroke-width="4"/><path d="M40 19 61 40 40 61 19 40Z" fill="none" stroke="#a87616" stroke-width="2"/></pattern></defs><rect width="800" height="80" y="10" fill="url(#p)"/></svg>`}
  ];
  const pane=$('[data-studio-pane="elements"]',host);
  if(pane&&!$('.fp-visual-assets',pane)){
    const section=document.createElement('section');section.className='fp-visual-assets';section.innerHTML=`<div class="fp-visual-assets-head"><h3>Visual graphics</h3><small>Invitation-ready SVG</small></div><div class="fp-visual-asset-grid"></div>`;const grid=$('.fp-visual-asset-grid',section);
    assets.forEach(asset=>{const b=document.createElement('button');b.type='button';b.className='fp-visual-asset';b.innerHTML=`<span class="art">${asset.svg}</span><strong>${esc(asset.name)}</strong>`;b.title=`${asset.name} · ${asset.cat}`;b.onclick=()=>addSvgAsset(asset);grid.append(b)});
    const existing=$('.final-element-library',pane);pane.insertBefore(section,existing||pane.firstChild);if(existing&&!existing.closest('.fp-simple-symbols')){const details=document.createElement('details');details.className='fp-simple-symbols';details.innerHTML='<summary>Simple symbols & shapes</summary>';existing.before(details);details.append(existing)}
  }
  const textPane=$('[data-studio-pane="text"]',host);
  if(textPane&&!$('.fp-text-fonts',textPane)){
    const fonts=[
      ['Noto Sans','noto-sans','Modern'],['Modern Sans','sans-arial','Modern'],['Friendly','sans-trebuchet','Modern'],['Noto Serif','noto-serif','Serif'],['Classic Serif','serif-georgia','Serif'],['Khmer Sans','noto-sans-khmer','Khmer'],['Khmer Serif','noto-serif-khmer','Khmer']
    ].map(([name,stack,cat])=>({name,stack,cat}));
    const recent=()=>{try{return JSON.parse(localStorage.getItem('einvite-font-recent-v1')||'[]')}catch{return[]}};
    const section=document.createElement('section');section.className='refine-text-section fp-text-fonts';section.innerHTML=`<div><h3>Fonts</h3><small>Click a font to apply it or create text</small></div><div class="fp-text-category-tabs"></div><div class="fp-inline-font-list"></div>`;
    const combo=document.createElement('section');combo.className='refine-text-section';combo.innerHTML=`<div><h3>Font combinations</h3><small>Ready-made invitation typography</small></div><div class="fp-text-combo-grid">
      <button class="fp-text-combo" data-fp-combo="gold"><span class="hero" style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
      <button class="fp-text-combo" data-fp-combo="editorial"><span class="hero" style="font-family:Didot,Georgia,serif">THE<br><i>MOMENT</i></span><small>Editorial contrast</small></button>
      <button class="fp-text-combo" data-fp-combo="modern"><span class="hero" style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><small>SUBHEADING</small></span><small>Modern clean</small></button>
      <button class="fp-text-combo" data-fp-combo="romance"><span class="hero" style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
      <button class="fp-text-combo" data-fp-combo="khmer"><span class="hero" style="font-family:'Khmer OS Muol Light','Noto Serif Khmer',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      <button class="fp-text-combo" data-fp-combo="minimal"><span class="hero" style="font-family:Inter,Arial,sans-serif;letter-spacing:.12em">SAVE<br>THE DATE</span><small>Minimal spaced</small></button>
    </div>`;
    const fontPlaceholder=$('.refine-text-section',textPane)?.nextElementSibling;textPane.append(section,combo);
    let cat='All',query='';const categories=['All','Recent','Khmer','Serif','Modern'];
    const selected=()=>$('.object.selected,.object.multi-selected',stage);
    const applyFont=font=>{let o=selected();if(!o){$('#addText')?.click();o=selected()}if(!o)return;try{pushHistory(capture())}catch{}o.dataset.font=font.stack;try{applyObjectVisualStyle(o);save()}catch{}const r=[font.stack,...recent().filter(x=>x!==font.stack)].slice(0,12);localStorage.setItem('einvite-font-recent-v1',JSON.stringify(r));closePaneOnMobile()};
    function renderFonts(){const tabs=$('.fp-text-category-tabs',section),list=$('.fp-inline-font-list',section);tabs.innerHTML=categories.map(x=>`<button type="button" class="${x===cat?'active':''}" data-cat="${x}">${x}</button>`).join('');$$('[data-cat]',tabs).forEach(b=>b.onclick=()=>{cat=b.dataset.cat;renderFonts()});let data=fonts.filter(f=>{if(cat==='Recent'&&!recent().includes(f.stack))return false;if(!['All','Recent'].includes(cat)&&f.cat!==cat)return false;return!query||`${f.name} ${f.cat}`.toLowerCase().includes(query)});if(cat==='Recent')data.sort((a,b)=>recent().indexOf(a.stack)-recent().indexOf(b.stack));list.innerHTML='';data.forEach(f=>{const b=document.createElement('button');b.type='button';b.className='fp-inline-font';b.innerHTML=`<span class="sample" style="font-family:${window.EInviteTypography?.stack?.(f.stack)||'serif'}">${f.cat==='Khmer'?'សិរីមង្គល':'Beautiful moments'}</span><small>${esc(f.name)}</small>`;b.onclick=()=>applyFont(f);list.append(b)});if(!data.length)list.innerHTML='<small style="padding:12px;color:var(--app-muted)">No fonts match this view.</small>'}
    renderFonts();
    const search=$('.refine-text-search input',textPane);if(search){const prior=search.oninput;search.oninput=e=>{query=e.target.value.trim().toLowerCase();renderFonts();$$('.refine-text-preset,.fp-text-combo',textPane).forEach(x=>x.hidden=!!query&&!x.textContent.toLowerCase().includes(query));if(typeof prior==='function')prior.call(search,e)}}
    const combos={gold:{font:'serif-georgia',fontSize:'48',color:'#b48a20',text:'Golden Hour',letterSpacing:'1'},editorial:{font:'noto-serif',fontSize:'48',color:'#2c2530',text:'The Moment',fontStyle:'italic'},modern:{font:'sans-arial',fontSize:'44',color:'#202127',text:'Your Celebration',fontWeight:'700'},romance:{font:'serif-georgia',fontSize:'46',color:'#426b52',text:'Bride & Groom',fontStyle:'italic'},khmer:{font:"noto-serif-khmer",fontSize:'38',color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'},minimal:{font:'noto-sans',fontSize:'34',color:'#22242a',text:'SAVE THE DATE',letterSpacing:'5'}};
    $$('.fp-text-combo',combo).forEach(b=>b.onclick=()=>{const c=combos[b.dataset.fpCombo];$('#addText')?.click();setTimeout(()=>{const o=selected();if(!o)return;const content=o.querySelector('.content');if(content)content.textContent=c.text;Object.entries(c).forEach(([k,v])=>{if(k!=='text')o.dataset[k]=v});try{applyObjectVisualStyle(o);save()}catch{}closePaneOnMobile()},30)});
  }
  host.addEventListener('click',e=>{const insert=e.target.closest('.final-element-card,.ei-pack-card,[data-add-element],[data-text-preset],.refine-text-preset,.refine-font-combo,.fp-text-combo,.fp-visual-asset,.material-picker-card');if(insert)setTimeout(closePaneOnMobile,80)},true);
  setTimeout(()=>{let pending=null;try{pending=JSON.parse(localStorage.getItem('einvite-pending-material-insert')||'null')}catch{}if(!pending?.url||typeof createObject!=='function')return;localStorage.removeItem('einvite-pending-material-insert');const o=createObject(makeId('material'),'image');o.style.left='14%';o.style.top='18%';o.style.width='72%';o.style.height='420px';o.dataset.src=pending.url;o.dataset.layerName=pending.name||'Material';const img=o.querySelector('img');if(img){img.src=pending.url;img.alt=pending.name||'Invitation material'}stage.append(o);choose(o);saveNow();window.uiToast?.(`${pending.name||'Material'} added to the canvas`,'↑')},500);
  const context=$('.ei-context-toolbar');if(context){let scheduled=false;const decorate=()=>{scheduled=false;if(context.querySelector('.ei-context-more'))return;const secondary=['effects','animate','flipX','flipY','tidy','ungroup','page-motion','check'];const nodes=secondary.map(a=>context.querySelector(`[data-action="${a}"]`)).filter(Boolean);if(nodes.length){const more=document.createElement('button');more.type='button';more.className='ei-context-more';more.textContent='•••';more.title='More actions';const overflow=document.createElement('div');overflow.className='ei-context-overflow';nodes.forEach(n=>overflow.append(n));more.onclick=e=>{e.stopPropagation();overflow.classList.toggle('open')};context.append(more,overflow);document.addEventListener('click',()=>overflow.classList.remove('open'))}};const observer=new MutationObserver(()=>{if(context.querySelector('.ei-context-more'))return;if(scheduled)return;scheduled=true;queueMicrotask(decorate)});observer.observe(context,{childList:true,subtree:false});decorate()}
}
if(page==='dashboard')setTimeout(dashboardFinal,0);
if(page==='materials')setTimeout(materialsFinal,0);
if(page==='index')setTimeout(editorFinal,120);
})();;(()=>{'use strict';function render(){const grid=document.querySelector('#inviteGrid');if(!grid)return;const cards=grid.querySelectorAll('.invite-card,[data-invite-id],article');if(cards.length||grid.children.length)return;grid.innerHTML=`<section class="dashboard-empty"><div><small>WELCOME TO INVITATION STUDIO</small><h2>Create your first invitation</h2><p>Start with a coordinated premium template, add your event details, then preview the full guest journey before publishing.</p><div class="dashboard-empty-checklist"><span>Choose a recommended design</span><span>Add names, date and venue</span><span>Review the opening and guest flow</span><span>Publish and share your invitation</span></div><div class="dashboard-empty-templates"><button class="primary" id="emptyCreate">Create your first invitation</button><a class="button-link" href="templates.html">Recommended templates</a><a class="button-link" href="materials.html">Materials & uploads</a></div></div><div class="dashboard-empty-preview" aria-label="Example guest invitation preview"><div><span>❦</span><strong>Sophea & Dara</strong><p>Sunday · Phnom Penh</p><small>Tap to open invitation</small></div></div></section>`;document.querySelector('#emptyCreate').onclick=()=>document.querySelector('#newBtn')?.click()}
const observer=new MutationObserver(()=>{if(document.querySelector('#dashboardView:not([hidden])'))setTimeout(render,0)});document.addEventListener('DOMContentLoaded',()=>{observer.observe(document.querySelector('#inviteGrid'),{childList:true});setTimeout(render,800)});})();;(()=>{'use strict';
let lastDialogTrigger=new WeakMap();
const focusable='a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function syncPanel(panel,open,trigger){if(!panel)return;panel.hidden=!open;try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(trigger)trigger.setAttribute('aria-expanded',String(open));if(!open&&panel.contains(document.activeElement))trigger?.focus();}
function trapDialogKey(event,dialog){const nodes=[...dialog.querySelectorAll(focusable)].filter(el=>!el.hidden&&el.getClientRects().length&&!el.closest('[inert],[aria-hidden="true"]'));if(!nodes.length)return;if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}
function observeDialogs(){document.querySelectorAll('dialog').forEach(dialog=>{if(dialog.dataset.a11yBound)return;dialog.dataset.a11yBound='1';dialog.addEventListener('close',()=>{const trigger=lastDialogTrigger.get(dialog);if(trigger?.isConnected)trigger.focus()});dialog.addEventListener('cancel',event=>{event.preventDefault();dialog.close()})});}
function init(){
 document.querySelectorAll('button:not([aria-label])').forEach(b=>{if(!b.textContent.trim())b.setAttribute('aria-label',b.title||'Action')});
 document.querySelectorAll('img:not([alt])').forEach(img=>img.alt='Invitation image');
 document.querySelectorAll('a > button').forEach(button=>{const a=button.parentElement;a.classList.add(...button.classList);a.setAttribute('role','button');a.textContent=button.textContent;button.remove()});
 document.querySelectorAll('.khmer-picker select').forEach(select=>{if(!select.getAttribute('aria-label')){const label=select.closest('label')?.childNodes?.[0]?.textContent?.trim();if(label)select.setAttribute('aria-label',label)}});
 document.addEventListener('click',event=>{const trigger=event.target.closest('button,[role="button"],a');if(!trigger)return;requestAnimationFrame(()=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&!lastDialogTrigger.has(top))lastDialogTrigger.set(top,trigger);observeDialogs()})},true);
 document.addEventListener('keydown',event=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&event.key==='Tab'){trapDialogKey(event,top);return}if(event.key!=='Escape')return;if(top){top.close();event.preventDefault();event.stopPropagation();return}const openDrawer=[...document.querySelectorAll('[data-drawer-open="true"],.is-open[role="dialog"]')].filter(x=>!x.hidden).at(-1);if(openDrawer){const trigger=document.querySelector(`[aria-controls="${CSS.escape(openDrawer.id)}"]`);syncPanel(openDrawer,false,trigger);openDrawer.dataset.drawerOpen='false';event.preventDefault()}});
 document.querySelectorAll('[aria-controls]').forEach(trigger=>{if(trigger.dataset.a11yManaged==='true')return;const panel=document.getElementById(trigger.getAttribute('aria-controls'));if(!panel)return;const update=()=>{const open=trigger.getAttribute('aria-expanded')==='true'||panel.classList.contains('open')||panel.classList.contains('is-open');try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(!open&&panel.contains(document.activeElement))trigger.focus()};trigger.addEventListener('click',()=>setTimeout(update,0));update()});
 observeDialogs();new MutationObserver(observeDialogs).observe(document.body,{childList:true,subtree:true});
}
window.EInviteAccessibility={syncPanel};document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();