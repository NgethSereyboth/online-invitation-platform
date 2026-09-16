(()=>{
'use strict';
const VERSION=2, MAX_DEPTH=12, MAX_NODES=5000, MAX_CHILDREN=2000;
const clone=v=>typeof structuredClone==='function'?structuredClone(v):JSON.parse(JSON.stringify(v));
const safe=(v,n=80)=>String(v??'').slice(0,n);
const finite=(v,f=0,min=-1e6,max=1e6)=>{const n=Number(v);return Number.isFinite(n)?Math.max(min,Math.min(max,n)):f};
const matrix=v=>{const a=Array.isArray(v)?v:[1,0,0,1,0,0];return [finite(a[0],1),finite(a[1]),finite(a[2]),finite(a[3],1),finite(a[4]),finite(a[5])];};
function stableId(canvasId,legacyId){return canvasId==='hero'?String(legacyId):`${canvasId}::${legacyId}`}
function node(input,id,type='object'){
 const n=input&&typeof input==='object'?input:{};
 return {id:safe(n.id||id,160),type:safe(n.type||type,40),name:safe(n.name||n.layerName||(type==='group'?'Group':'Layer')),parentId:safe(n.parentId||'',160),children:Array.isArray(n.children)?[...new Set(n.children.map(x=>safe(x,160)))]:[],visible:n.visible!==false,locked:n.locked===true,collapsed:n.collapsed===true,canvasId:safe(n.canvasId||'hero',160),legacyId:safe(n.legacyId||'',160),zIndex:Math.max(0,Math.round(finite(n.zIndex,0,0,1e6))),localMatrix:matrix(n.localMatrix),pivot:{x:finite(n.pivot?.x,.5,-10,10),y:finite(n.pivot?.y,.5,-10,10)},data:n.data&&typeof n.data==='object'?clone(n.data):{}};
}
function legacyCanvases(doc){return [{id:'hero',name:'Main hero',objects:doc.objects||{}},...(doc.designPages||[]).map((p,i)=>({id:`page:${p.id}`,name:safe(p.name||`Page ${i+1}`),objects:p.objects||{}}))]}
function fromLegacy(doc){
 const nodes={},roots={},groups=doc?.sceneGraph?.groups||{};
 for(const canvas of legacyCanvases(doc||{})){
  roots[canvas.id]=[];
  const entries=Object.entries(canvas.objects).sort((a,b)=>finite(a[1]?.zIndex)-finite(b[1]?.zIndex)||a[0].localeCompare(b[0]));
  for(const [legacyId,o] of entries){const id=stableId(canvas.id,legacyId),gid=safe(o?.parentGroupId||o?.groupId||'');nodes[id]=node({...o,name:o?.layerName||o?.name,data:clone(o),id,legacyId,canvasId:canvas.id,parentId:gid||'',zIndex:o?.zIndex},id,o?.type||'object');}
 }
 for(const [gid,g] of Object.entries(groups).sort(([a],[b])=>a.localeCompare(b))){if(nodes[gid])throw Error(`Duplicate scene id: ${gid}`);nodes[gid]=node({...g,id:gid,type:'group',canvasId:g.canvasId||'hero'},gid,'group')}
 for(const n of Object.values(nodes)){if(n.parentId&&nodes[n.parentId]){const p=nodes[n.parentId];if(!p.children.includes(n.id))p.children.push(n.id)}else{n.parentId='';(roots[n.canvasId]||(roots[n.canvasId]=[])).push(n.id)}}
 for(const n of Object.values(nodes))n.children=[...new Set(n.children.filter(id=>nodes[id]))].sort((a,b)=>(nodes[a].zIndex-nodes[b].zIndex)||a.localeCompare(b));
 for(const key of Object.keys(roots))roots[key]=[...new Set(roots[key])].sort((a,b)=>(nodes[a].zIndex-nodes[b].zIndex)||a.localeCompare(b));
 const graph={version:VERSION,maxDepth:MAX_DEPTH,nodes,roots,updatedAt:0};validate(graph,{throwOnError:true});return graph;
}
function migrate(doc){const existing=doc?.sceneTree?.version===VERSION?clone(doc.sceneTree):doc?.sceneGraph?.version===VERSION?clone(doc.sceneGraph):null;if(existing){validate(existing,{throwOnError:true});return existing}return fromLegacy(doc||{})}
function validate(graph,{throwOnError=false}={}){
 const errors=[];if(!graph||graph.version!==VERSION)errors.push('Invalid scene version');
 const nodes=graph?.nodes&&typeof graph.nodes==='object'?graph.nodes:{};const ids=Object.keys(nodes);if(ids.length>MAX_NODES)errors.push(`Scene node count exceeds ${MAX_NODES}`);
 const owner=new Map();
 for(const id of ids){const n=nodes[id];if(n.id!==id)errors.push(`Node key/id mismatch: ${id}`);if(!Array.isArray(n.children))errors.push(`Invalid children: ${id}`);else if(n.children.length>MAX_CHILDREN)errors.push(`Child count exceeds ${MAX_CHILDREN}: ${id}`);for(const c of n.children||[]){if(!nodes[c])errors.push(`Missing child ${c}`);else if(owner.has(c))errors.push(`Duplicate child ownership ${c}`);else owner.set(c,id)}if(n.parentId&&!nodes[n.parentId])errors.push(`Missing parent ${n.parentId}`)}
 for(const [canvas,list] of Object.entries(graph?.roots||{})){if(!Array.isArray(list))errors.push(`Invalid root list ${canvas}`);for(const id of list||[]){if(!nodes[id])errors.push(`Missing root ${id}`);else if(owner.has(id))errors.push(`Root also owned ${id}`);else owner.set(id,'')}}
 for(const id of ids){const expected=nodes[id].parentId||'';if((owner.get(id)??'__missing__')!==expected)errors.push(`Parent/child mismatch ${id}`)}
 const visiting=new Set(),done=new Set();function walk(id,depth){if(depth>MAX_DEPTH){errors.push(`Scene depth exceeds ${MAX_DEPTH}: ${id}`);return}if(visiting.has(id)){errors.push(`Scene cycle at ${id}`);return}if(done.has(id))return;visiting.add(id);for(const c of nodes[id]?.children||[])walk(c,depth+1);visiting.delete(id);done.add(id)}for(const list of Object.values(graph?.roots||{}))for(const id of list||[])walk(id,1);for(const id of ids)if(!done.has(id))errors.push(`Orphan or cyclic node ${id}`);
 const result={ok:errors.length===0,errors};if(throwOnError&&!result.ok)throw Error(errors.join('; '));return result;
}
function syncToLegacy(doc,graph){validate(graph,{throwOnError:true});const byCanvas={};for(const [canvas,roots] of Object.entries(graph.roots)){const flat=[];const visit=id=>{const n=graph.nodes[id];if(n.type!=='group')flat.push(n);for(const c of n.children)visit(c)};roots.forEach(visit);byCanvas[canvas]=Object.fromEntries(flat.map((n,i)=>[n.legacyId||n.id,{...clone(n.data),type:n.type,name:n.name,layerName:n.name,locked:n.locked,visible:n.visible,zIndex:i+1,groupId:n.parentId,parentGroupId:n.parentId}]))}doc.objects=byCanvas.hero||{};(doc.designPages||[]).forEach(p=>p.objects=byCanvas[`page:${p.id}`]||{});doc.sceneGraph=clone(graph);return doc}
function rename(graph,id,name){const g=clone(graph);if(!g.nodes[id])throw Error(`Unknown scene node ${id}`);g.nodes[id].name=safe(name);return g}
function setState(graph,ids,patch){const g=clone(graph);for(const id of ids){if(!g.nodes[id])throw Error(`Unknown scene node ${id}`);if('visible'in patch)g.nodes[id].visible=patch.visible!==false;if('locked'in patch)g.nodes[id].locked=patch.locked===true}return g}
function reorder(graph,id,parentId,index){const g=clone(graph),n=g.nodes[id];if(!n)throw Error(`Unknown scene node ${id}`);if(parentId&&!g.nodes[parentId])throw Error(`Unknown parent ${parentId}`);const old=n.parentId?g.nodes[n.parentId].children:g.roots[n.canvasId];old.splice(old.indexOf(id),1);n.parentId=parentId||'';const list=parentId?g.nodes[parentId].children:(g.roots[n.canvasId]||(g.roots[n.canvasId]=[]));list.splice(Math.max(0,Math.min(list.length,index)),0,id);validate(g,{throwOnError:true});return g}
window.EInviteSceneModel={VERSION,MAX_DEPTH,MAX_NODES,migrate,fromLegacy,validate,syncToLegacy,rename,setState,reorder,clone,matrix};
})();
