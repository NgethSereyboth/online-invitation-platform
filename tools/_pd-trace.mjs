import {createRequire} from 'node:module';
import {BASE_URL} from './lib/repo.mjs';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
const page = await browser.newPage({viewport:{width:1440,height:900}});
const account = await page.request.post(`${BASE_URL}/api/auth/register`, {data:{email:`tr-${Date.now()}@example.com`,password:'Motion-test-password-123!'}});
if(!account.ok()) throw Error('register '+account.status());
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {type:i===0?'image':'shape',shapeKind:'rectangle',fillColor:'#3E7C6B',src:'',left:`${8+(i%5)*17}%`,top:`${8+Math.floor(i/5)*13}%`,width:'12%',height:'55px',imagePositionX:50,imagePositionY:50,imageFit:'cover',zIndex:i+1,visible:true,locked:false,showInHero:true};
const response = await page.request.post(`${BASE_URL}/api/invitations`, {data:{slug:`tr-${Date.now()}`,document:{eventType:'Wedding',fields:{names:'Hitch'},objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}}});
if(!response.ok()) throw Error('invite '+response.status());
const invite = await response.json();
await page.addInitScript(id=>localStorage.setItem('sovan-active-invite', String(id)), invite.id);
await page.goto(`${BASE_URL}/index.html?_perfdebug=1`, {waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>document.documentElement.dataset.editorReady==='true');
await page.evaluate(async()=>{if(window.EInviteOnboardingReady)await window.EInviteOnboardingReady});
const dismiss=page.locator('#finalTourDismiss');
if(await dismiss.count() && await dismiss.isVisible())await dismiss.click();
await page.waitForFunction(()=>!!window.EInviteEditorCore && !!window.EInviteDirectManipulation && !!window.EInviteMotion);
await page.evaluate(async()=>{
  EInviteToolController.setTool('select',{announce:false});
  let prev=null;
  for(let i=0;i<20;i++){await new Promise(r=>setTimeout(r,150));const v=window.EInviteMotion.viewport.view,s=`${v.x}|${v.y}|${v.zoom}`;if(prev!==null&&s===prev)break;prev=s}
  EInviteCanvasViewController.fit();
  await new Promise(r=>setTimeout(r,450));
});
const id=process.env.PD_ID||'motion-6';
const pt = await page.evaluate(id=>{
  const t=document.querySelector(`#stage .object[data-id="${id}"]`);const r=t.getBoundingClientRect();
  return {x:r.left+r.width/2,y:r.top+r.height/2};
},id);
const {x,y}=pt;
if(process.env.PD_NO_BODY_STATE){await page.evaluate(()=>{
  const cl=document.body.classList;
  const origToggle=cl.toggle.bind(cl);
  cl.toggle=(name,force)=>{if(name==='v54-has-selection')return force??false;return origToggle(name,force)};
  const origAdd=cl.add.bind(cl),origRemove=cl.remove.bind(cl);
  cl.add=(...names)=>{if(!(names.length===1&&names[0]==='pe-pointer-interaction'))origAdd(...names)};
  cl.remove=(...names)=>{if(!(names.length===1&&names[0]==='pe-pointer-interaction'))origRemove(...names)};
})}
await page.evaluate(()=>{window.__marks=[];new PerformanceObserver(l=>{for(const e of l.getEntries())if(e.name==='pointerdown')window.__marks.push({start:e.startTime,dur:e.duration})}).observe({type:'event',durationThreshold:0,buffered:false})});
const cdp=await page.context().newCDPSession(page);
const chunks=[];
cdp.on('Tracing.dataCollected',d=>chunks.push(...(d.value||[])));
const done=new Promise(r=>cdp.on('Tracing.tracingComplete',r));
await cdp.send('Tracing.start',{categories:'devtools.timeline,blink.user_timing,cc,gpu,viz,disabled-by-default-devtools.timeline.invalidationTracking',transferMode:'ReportEvents'});
await page.mouse.move(x,y);
await page.waitForTimeout(150);
await page.mouse.down();
await page.waitForTimeout(Number(process.env.PD_HOLD||220));
await cdp.send('Tracing.end');
await done;
const marks=await page.evaluate(()=>window.__marks);
console.log('POINTERDOWN', JSON.stringify(marks));
const phases=new Map();
const detail=new Map();
for(const e of chunks){
  if(e.ph!=='X'||typeof e.dur!=='number')continue;
  phases.set(e.name,(phases.get(e.name)||0)+e.dur);
  if(e.dur>=1.5){
    const args=e.args&&e.args.data?e.args.data:{};
    const label=[e.name,args.functionName||args.type||args.name||''].filter(Boolean).join(' ');
    detail.set(label,(detail.get(label)||0)+e.dur);
  }
}
const top=[...phases.entries()].sort((a,b)=>b[1]-a[1]).slice(0,26);
console.log('TRACE PHASES (total us)');
console.log(top.map(([k,v])=>`${(v/1000).toFixed(1)}\t${k}`).join('\n'));
console.log('TRACE DETAIL >=1.5ms');
console.log([...detail.entries()].sort((a,b)=>b[1]-a[1]).slice(0,30).map(([k,v])=>`${(v/1000).toFixed(1)}\t${k}`).join('\n'));
const downEv=chunks.find(e=>e.name==='EventDispatch'&&e.args&&e.args.data&&e.args.data.type==='pointerdown');
const ref=downEv?downEv.ts/1000:marks.length?marks[0].start:0;
console.log('DOWN_EV', downEv?JSON.stringify({t:ref,dur:downEv.dur}):'none');
const inval=[],paints=[];
for(const e of chunks){
  const d=e.args&&e.args.data?e.args.data:{};
  if(e.name&&e.name.indexOf('Invalidation')>=0&&e.ph==='I')inval.push({t:(e.ts/1000-ref),reason:d.reason||'',node:d.nodeName||''});
  if(e.name==='Paint'&&e.ph==='X')paints.push({t:(e.ts/1000-ref),dur:e.dur,clip:d.clip||null});
}
const byKey=new Map();
for(const i of inval){const k=`${i.reason} [${i.node}]`;byKey.set(k,(byKey.get(k)||0)+1)}
console.log(`INVALIDATIONS n=${inval.length}`);
console.log([...byKey.entries()].sort((a,b)=>b[1]-a[1]).slice(0,24).map(([k,v])=>`${v}\t${k}`).join('\n'));
const paintTop=[...paints].sort((a,b)=>b.dur-a.dur).slice(0,16);
console.log('PAINTS top (dur us, t rel down)');
console.log(paintTop.map(p=>`${Math.round(p.dur)}\tt=${p.t.toFixed(1)}\tclip=${JSON.stringify(p.clip)}`).join('\n'));
const win=paints.filter(p=>p.t>-12&&p.t<95);
console.log(`PAINT WINDOW n=${win.length} total=${Math.round(win.reduce((a,p)=>a+p.dur,0))}`);
console.log(win.slice(0,22).map(p=>`\tt=${p.t.toFixed(1)}\tdur=${Math.round(p.dur)}\tclip=${JSON.stringify(p.clip)}`).join('\n'));
const rasters=[];
for(const e of chunks){
  if(e.name==='RasterTask'||e.name==='Rasterize'){
    const d=e.args?(e.args.tileData||e.args.data||{}):{};
    rasters.push({t:(e.ts/1000-ref),dur:e.dur,rect:d.content_rect||d.clip||null});
  }
}
console.log(`RASTERS n=${rasters.length} total_us=${Math.round(rasters.reduce((a,r)=>a+r.dur,0))}`);
const rw=rasters.filter(r=>r.t>-12&&r.t<95);
console.log(`RASTER WINDOW n=${rw.length} total=${Math.round(rw.reduce((a,r)=>a+r.dur,0))}`);
console.log(rw.slice(0,40).map(r=>`\tt=${r.t.toFixed(1)}\tdur=${Math.round(r.dur)}\trect=${JSON.stringify(r.rect)}`).join('\n'));
const invReasons=new Map();
for(const i of inval){invReasons.set(i.reason,(invReasons.get(i.reason)||0)+1)}
console.log('INV REASONS'); console.log([...invReasons.entries()].sort((a,b)=>b[1]-a[1]).slice(0,12).map(([k,v])=>`${v}\t${k}`).join('\n'));
console.log('INV SAMPLE', JSON.stringify(inval.slice(0,3).map(i=>({t:+i.t.toFixed(1),reason:i.reason,node:i.node}))));
console.log('SLICE 55-75ms (compositor)');
for(const e of chunks){
  const t=e.ts/1000-ref;
  if(t<55||t>75)continue;
  const n=e.name||'';
  if(!/Draw|Commit|Raster|Layer|Present|Begin|Activate|Swap|Damage|Pipeline|Tree|Paint/.test(n))continue;
  if(e.ph!=='X'&&e.ph!=='B'&&e.ph!=='E'&&e.ph!=='I'&&e.ph!=='b'&&e.ph!=='e')continue;
  console.log(`${t.toFixed(1)}\t${e.ph}\t${n}\t${e.dur!=null?Math.round(e.dur):''}\t${JSON.stringify(e.args||{}).slice(0,200)}`);
}
console.log('MAIN THREAD 20-58ms');
const seen2=new Set();
for(const e of chunks){
  const t=e.ts/1000-ref;
  if(t<20||t>58)continue;
  const n=e.name||'';
  if(!/^(BeginMainFrame|FireAnimationFrame|EventDispatch|RunTask|Commit|Activate|DrawFrame|PrePaint|UpdateLayoutTree|FunctionCall|ParseHTML|RunMicrotasks|MajorGC|MinorGC|UpdateLayerTree|CommitLoad|InvalidateLayout|StyleRecalc|Layout|Paint)$/.test(n))continue;
  const key=n+t.toFixed(1);
  if(seen2.has(key))continue;seen2.add(key);
  console.log(`${t.toFixed(1)}\t${n}\t${e.dur!=null?Math.round(e.dur):''}\t${JSON.stringify(e.args||{}).slice(0,110)}`);
}
await browser.close();
