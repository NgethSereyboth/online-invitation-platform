(()=>{
'use strict';
const CLIP='einvite-cross-project-clipboard-v13',STYLE='einvite-style-clipboard-v13';
const clone=v=>window.EInviteEditorSchema?.clone?.(v)??JSON.parse(JSON.stringify(v));
const bridge=()=>window.EInviteEditorBridge;
function canvasMap(doc,canvasId=bridge()?.getActiveCanvasId?.()||'hero'){
 if(canvasId==='hero')return doc.objects||(doc.objects={});
 const page=(doc.designPages||[]).find(p=>`page:${p.id}`===canvasId);return page?(page.objects||(page.objects={})):doc.objects;
}
function execute(label,mutator,options={}){if(!bridge())throw Error('Editor bridge is unavailable');return bridge().transact(label,mutator,options)}
function selected(){return bridge()?.getSelectedIds?.()||[]}
function getSelectedObjects(doc){const map=canvasMap(doc);return selected().map(id=>[id,map[id]]).filter(([,o])=>o)}
function copySelection(){const doc=bridge().getState(),items=getSelectedObjects(doc);if(!items.length)return false;const payload={version:1,sourceInvitation:window.EInviteContext?.getInvitationId?.()||'',items:clone(items),copiedAt:Date.now()};localStorage.setItem(CLIP,JSON.stringify(payload));return true}
function pasteSelection(){let payload;try{payload=JSON.parse(localStorage.getItem(CLIP)||'null')}catch{}if(!payload?.items?.length)return false;const newIds=[];execute('Paste objects',doc=>{const map=canvasMap(doc);const offset=3;payload.items.forEach(([oldId,o],index)=>{const id=`obj-${Date.now()}-${index}-${Math.random().toString(36).slice(2,7)}`;const next=clone(o);next.left=shift(next.left,offset+index);next.top=shift(next.top,offset+index);next.groupId='';next.parentGroupId='';map[id]=next;newIds.push(id)});});setTimeout(()=>bridge().select(newIds),0);return true}
function shift(value,delta){const n=parseFloat(value);return Number.isFinite(n)&&String(value).includes('%')?`${Math.min(95,Math.max(0,n+delta))}%`:value}
const STYLE_KEYS=['font','color','fontSize','textAlign','fontWeight','fontStyle','letterSpacing','lineHeight','fillColor','opacity','borderWidth','borderColor','borderRadius','shadowBlur','shadowColor','backgroundEnabled','backgroundColor','backgroundOpacity','blendMode','fillMode','gradientStart','gradientEnd','gradientAngle','textGradientEnabled','textGradientStart','textGradientEnd','textGradientAngle','textStrokeWidth','textStrokeColor','textShadowBlur','textShadowColor','textTransform','imageFit','imageMask','imageFrame','imageBrightness','imageContrast','imageSaturation','imageVibrance','imageTemperature','imageGamma','imageCurveShadows','imageCurveHighlights','imageGrayscale','imageSepia','imageBlur','imageSharpen','imageHue'];
function copyStyle(){const doc=bridge().getState(),first=getSelectedObjects(doc)[0]?.[1];if(!first)return false;localStorage.setItem(STYLE,JSON.stringify(Object.fromEntries(STYLE_KEYS.filter(k=>k in first).map(k=>[k,clone(first[k])]))));return true}
function pasteStyle(){let style;try{style=JSON.parse(localStorage.getItem(STYLE)||'null')}catch{}if(!style)return false;execute('Paste style',doc=>getSelectedObjects(doc).forEach(([,o])=>Object.assign(o,clone(style))));return true}
function setProperty(key,value){execute(`Set ${key}`,doc=>getSelectedObjects(doc).forEach(([,o])=>o[key]=clone(value)));}
function toggle(key,defaultValue=false){execute(`Toggle ${key}`,doc=>getSelectedObjects(doc).forEach(([,o])=>o[key]=!(o[key]??defaultValue)));}
function setConstraints(value){execute('Update responsive constraints',doc=>getSelectedObjects(doc).forEach(([,o])=>o.constraints={...(o.constraints||{}),...value}));}
function saveBreakpoint(name,patch){execute(`Set ${name} breakpoint`,doc=>getSelectedObjects(doc).forEach(([,o])=>{o.breakpoints={...(o.breakpoints||{}),[name]:{...(o.breakpoints?.[name]||{}),...patch}}}));}
function groupNested(){const ids=selected();if(ids.length<2)return null;const gid=`group-${Date.now()}-${Math.random().toString(36).slice(2,7)}`;execute('Group objects',doc=>{const map=canvasMap(doc);ids.forEach(id=>{if(map[id])map[id].groupId=gid});doc.sceneGraph=doc.sceneGraph||{};doc.sceneGraph.groups={...(doc.sceneGraph.groups||{}),[gid]:{id:gid,name:'Group',children:[...ids],parentId:'',locked:false,visible:true}}});return gid}
function tidy(axis='horizontal'){
 const ids=selected();if(ids.length<3)return false;execute('Tidy layout',doc=>{const map=canvasMap(doc);const items=ids.map(id=>[id,map[id]]).filter(([,o])=>o).sort((a,b)=>parseFloat(a[1][axis==='horizontal'?'left':'top'])-parseFloat(b[1][axis==='horizontal'?'left':'top']));const key=axis==='horizontal'?'left':'top',sizeKey=axis==='horizontal'?'width':'height';const start=parseFloat(items[0][1][key]),end=parseFloat(items.at(-1)[1][key])+parseFloat(items.at(-1)[1][sizeKey]);const total=items.reduce((n,[,o])=>n+parseFloat(o[sizeKey]||0),0),gap=Math.max(0,(end-start-total)/(items.length-1));let pos=start;items.forEach(([,o])=>{o[key]=`${pos}%`;pos+=parseFloat(o[sizeKey]||0)+gap})});return true
}
function duplicate(){const doc=bridge().getState(),items=getSelectedObjects(doc);if(!items.length)return false;const newIds=[];execute('Duplicate objects',doc2=>{const map=canvasMap(doc2);items.forEach(([oldId,o],index)=>{const id=`obj-${Date.now()}-${index}-${Math.random().toString(36).slice(2,7)}`;const next=clone(o);next.left=shift(next.left,3+index);next.top=shift(next.top,3+index);map[id]=next;newIds.push(id)})});setTimeout(()=>bridge().select(newIds),0);return true}
window.EInviteCommands={execute,selected,copySelection,pasteSelection,copyStyle,pasteStyle,setProperty,toggle,setConstraints,saveBreakpoint,groupNested,tidy,duplicate};
})();
