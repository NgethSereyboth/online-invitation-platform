(()=>{
'use strict';
const VERSION=13;
const clone=v=>typeof structuredClone==='function'?structuredClone(v):JSON.parse(JSON.stringify(v));
const id=prefix=>`${prefix}-${globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(36).slice(2,9)}`}`;
const position=(value,fallback)=>{const text=String(value??fallback),n=parseFloat(text);return Number.isFinite(n)?text:String(fallback)};
const size=(value,fallback)=>{const text=String(value??fallback),n=parseFloat(text);return Number.isFinite(n)&&n>0?text:String(fallback)};
const finiteNumber=(value,fallback,min,max)=>{if(typeof value==='boolean'||value===null||value===''||Array.isArray(value)||(typeof value==='object'&&value!==null))return fallback;const number=typeof value==='number'?value:Number(value);return Number.isFinite(number)?Math.max(min,Math.min(max,number)):fallback};
const fallbackFonts={'Georgia,serif':'serif-georgia','Georgia, serif':'serif-georgia','Arial,sans-serif':'sans-arial','Arial, sans-serif':'sans-arial',"'Trebuchet MS',sans-serif":'sans-trebuchet',"'Noto Serif Khmer','Khmer OS Battambang',serif":'noto-serif-khmer',"'Noto Sans Khmer','Khmer OS Battambang',sans-serif":'noto-sans-khmer',"'Khmer OS Muol Light','Noto Serif Khmer',serif":'noto-serif-khmer','Noto Serif Khmer':'noto-serif-khmer','Noto Sans Khmer':'noto-sans-khmer'};
const fontId=value=>globalThis.EInviteTypography?.fontId?globalThis.EInviteTypography.fontId(value):fallbackFonts[String(value||'').trim()]||'noto-serif';
function normalizeObject(objectId,input={},canvasId='hero',typography=null){
 const o={...input},legacyId=String(o.legacyId||objectId||id('obj')),defaultSceneId=canvasId==='hero'?legacyId:`${canvasId}::${legacyId}`;o.legacyId=legacyId;o.id=String(o.id&&o.canvasId===canvasId?o.id:defaultSceneId);o.canvasId=String(canvasId);o.type=o.type||'text';
 o.locked=o.locked===true;o.visible=o.visible!==false;o.layerName=String(o.layerName||'').slice(0,80);o.groupId=String(o.groupId||'');o.parentGroupId=String(o.parentGroupId||o.groupId||'');
 o.left=position(o.left,'0%');o.top=position(o.top,'0%');o.width=size(o.width,'10%');o.height=size(o.height,'10%');o.rotation=finiteNumber(o.rotation,0,-360,360);o.zIndex=Math.max(1,Math.round(finiteNumber(o.zIndex,1,1,100000)));
 if(globalThis.TypographyDocumentModel){const normalized=TypographyDocumentModel.normalizeObject(legacyId,o,typography||TypographyDocumentModel.defaultCatalog());Object.assign(o,normalized)}else{o.font=fontId(o.font);o.fontSize=finiteNumber(o.fontSize,32,8,200);o.textAlign=['left','center','right','justify'].includes(o.textAlign)?o.textAlign:'center';o.textAutoFit=o.textAutoFit==='fit'?'fit':'none';o.textAutoFitMax=finiteNumber(o.textAutoFitMax,o.fontSize,8,200);o.textMinFontSize=Math.min(finiteNumber(o.textMinFontSize,10,8,72),o.textAutoFitMax);o.textWrap=['normal','balance','pretty'].includes(o.textWrap)?o.textWrap:'normal';o.textColumns=Math.round(finiteNumber(o.textColumns,1,1,3));o.textColumnGap=finiteNumber(o.textColumnGap,24,0,64)};
 o.transform={x:o.left,y:o.top,width:o.width,height:o.height,rotation:o.rotation,...(o.transform||{})};
 o.constraints={pinLeft:false,pinRight:false,pinTop:false,pinBottom:false,centerX:false,centerY:false,stretchX:false,stretchY:false,scale:true,...(o.constraints||{})};
 o.breakpoints={...(o.breakpoints||{})};return o;
}
function compatibilityGroups(doc){
 const tree=doc?.sceneTree?.version===2?doc.sceneTree:doc?.sceneGraph?.version===2?doc.sceneGraph:null;if(!tree?.nodes)return clone(doc?.sceneGraph?.groups||{});const groups={};Object.entries(tree.nodes).forEach(([gid,node])=>{if(node?.type!=='group')return;groups[gid]={id:String(node.id||gid),name:String(node.name||'Group').slice(0,80),children:(node.children||[]).map(childId=>{const child=tree.nodes[childId];return child?.type==='group'?String(childId):String(child?.legacyId||childId)}),parentId:String(node.parentId||''),locked:node.locked===true,visible:node.visible!==false,collapsed:node.collapsed===true}});return groups;
}
function buildSceneGraph(doc){
 const objects={},pages=[];
 const heroOrder=[];Object.entries(doc.objects||{}).sort((a,b)=>Number(a[1]?.zIndex||0)-Number(b[1]?.zIndex||0)).forEach(([key,value])=>{const o=normalizeObject(key,value,'hero',doc.typography);objects[o.id]=o;heroOrder.push(o.id)});
 pages.push({id:'hero',name:'Main hero',kind:'hero',enabled:true,objectIds:heroOrder});
 (doc.designPages||[]).forEach((page,index)=>{const canvasId=`page:${page.id}`;const order=[];Object.entries(page.objects||{}).sort((a,b)=>Number(a[1]?.zIndex||0)-Number(b[1]?.zIndex||0)).forEach(([key,value])=>{const o=normalizeObject(key,value,canvasId,doc.typography);objects[o.id]=o;order.push(o.id)});pages.push({id:canvasId,name:String(page.name||`Page ${index+1}`),kind:'design-page',enabled:page.enabled!==false,objectIds:order})});
 const sourceGroups=compatibilityGroups(doc),groups={};Object.entries(sourceGroups).forEach(([gid,g])=>{groups[gid]={id:String(g.id||gid),name:String(g.name||'Group').slice(0,80),children:Array.isArray(g.children)?[...new Set(g.children.map(String))]:[],parentId:String(g.parentId||''),locked:g.locked===true,visible:g.visible!==false,collapsed:g.collapsed===true}});
 return {version:1,pages,objects,groups,updatedAt:Date.now()};
}
function migrate(input){
 const d=input&&typeof input==='object'?input:{};if(globalThis.TypographyDocumentModel)TypographyDocumentModel.normalizeDocument(d,{mutate:true});if(globalThis.RichTextDocumentModel)RichTextDocumentModel.normalizeInvitation(d,{mutate:true,strict:false});d.schemaVersion=Math.max(Number(d.schemaVersion||0),VERSION);
 d.sceneTree=globalThis.EInviteSceneModel?EInviteSceneModel.migrate(d):d.sceneTree;
 if(globalThis.EInviteSceneModel&&d.sceneTree)EInviteSceneModel.syncToLegacy(d,d.sceneTree);
 d.sceneGraph=buildSceneGraph(d);
 d.editorModel={version:1,commandVersion:1,selectedBreakpoint:d.editorModel?.selectedBreakpoint||'desktop',...(d.editorModel||{})};
 d.components=Array.isArray(d.components)?d.components:[];
 d.sharedStyles={text:Array.isArray(d.sharedStyles?.text)?d.sharedStyles.text:[],color:Array.isArray(d.sharedStyles?.color)?d.sharedStyles.color:[],effect:Array.isArray(d.sharedStyles?.effect)?d.sharedStyles.effect:[]};
 d.brandKit={name:'',logos:[],colors:[],fonts:{latinHeading:'',latinBody:'',khmerHeading:'',khmerBody:''},...(d.brandKit||{})};
 d.timeline={duration:Math.max(1000,Number(d.timeline?.duration||10000)),fps:Math.max(12,Math.min(60,Number(d.timeline?.fps||30))),tracks:{...(d.timeline?.tracks||{})},markers:Array.isArray(d.timeline?.markers)?d.timeline.markers:[],playRange:{start:Math.max(0,Number(d.timeline?.playRange?.start||0)),end:Math.max(0,Number(d.timeline?.playRange?.end||d.timeline?.duration||10000))},reducedMotionFallback:d.timeline?.reducedMotionFallback||'final-state'};d.timeline.playRange.end=Math.max(d.timeline.playRange.start+100,Math.min(d.timeline.duration,d.timeline.playRange.end||d.timeline.duration));
 d.photoEdits={...(d.photoEdits||{})};d.comments=Array.isArray(d.comments)?d.comments:[];d.approval={status:'draft',requestedAt:null,approvedAt:null,approvedBy:'',note:'',...(d.approval||{})};
 d.events=Array.isArray(d.events)&&d.events.length?d.events:[{id:'primary',name:d.eventType||'Event',date:d.fields?.date||'',time:d.fields?.time||'',timezone:d.timezone||'Asia/Phnom_Penh',venue:d.fields?.venue||'',venueKm:d.fields?.venueKm||''}];
 d.timezone=String(d.timezone||d.events[0]?.timezone||'Asia/Phnom_Penh');
 d.publishSchedule={publishAt:null,unpublishAt:null,expiresAt:null,...(d.publishSchedule||{})};
 d.customDomain=String(d.customDomain||'');d.guestExperience={analyticsConsent:false,mediaConsentNotice:true,...(d.guestExperience||{})};
 return d;
}
function syncLegacy(doc){if(globalThis.TypographyDocumentModel)TypographyDocumentModel.normalizeDocument(doc,{mutate:true});if(globalThis.RichTextDocumentModel)RichTextDocumentModel.normalizeInvitation(doc,{mutate:true,strict:false});if(globalThis.EInviteSceneModel){doc.sceneTree=EInviteSceneModel.fromLegacy(doc);EInviteSceneModel.syncToLegacy(doc,doc.sceneTree)}doc.sceneGraph=buildSceneGraph(doc);return doc;}
function syncGraphToLegacy(doc){
 if(globalThis.EInviteSceneModel&&doc.sceneTree){EInviteSceneModel.syncToLegacy(doc,doc.sceneTree);doc.sceneGraph=buildSceneGraph(doc);return doc}
 const graph=doc.sceneGraph;if(!graph?.pages||!graph?.objects)return doc;
 const hero=graph.pages.find(p=>p.id==='hero');if(hero)doc.objects=Object.fromEntries((hero.objectIds||[]).filter(x=>graph.objects[x]).map(x=>[graph.objects[x].legacyId||x,stripGraphFields(graph.objects[x])]));
 (doc.designPages||[]).forEach(page=>{const p=graph.pages.find(x=>x.id===`page:${page.id}`);if(p)page.objects=Object.fromEntries((p.objectIds||[]).filter(x=>graph.objects[x]).map(x=>[graph.objects[x].legacyId||x,stripGraphFields(graph.objects[x])]))});
 return doc;
}
function stripGraphFields(o){const x=clone(o);delete x.id;delete x.canvasId;delete x.legacyId;return x;}
function validate(doc){if(globalThis.EInviteSceneModel&&doc?.sceneTree){const sceneResult=EInviteSceneModel.validate(doc.sceneTree);if(!sceneResult.ok)return {ok:false,error:sceneResult.errors.join('; ')}}const g=doc?.sceneGraph;if(!g||g.version!==1||!Array.isArray(g.pages)||!g.objects||typeof g.objects!=='object')return {ok:false,error:'Invalid scene graph'};const ids=new Set(Object.keys(g.objects));for(const p of g.pages){if(!p.id||!Array.isArray(p.objectIds))return {ok:false,error:'Invalid scene page'};for(const objectId of p.objectIds)if(!ids.has(objectId))return {ok:false,error:`Missing scene object ${objectId}`}}return {ok:true};}
window.EInviteEditorSchema={VERSION,migrate,syncLegacy,syncGraphToLegacy,buildSceneGraph,normalizeObject,validate,clone,finiteNumber};
})();
