import {createRequire} from 'node:module';
import {BASE_URL} from './lib/repo.mjs';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
const page = await browser.newPage({viewport:{width:process.env.PD_SNAP?1366:1440,height:900}});
const account = await page.request.post(`${BASE_URL}/api/auth/register`, {data:{email:`pd-${Date.now()}@example.com`,password:'Motion-test-password-123!'}});
if(!account.ok()) throw Error('register '+account.status());
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {type:i===0?'image':'shape',shapeKind:'rectangle',fillColor:'#3E7C6B',src:'',left:`${8+(i%5)*17}%`,top:`${8+Math.floor(i/5)*13}%`,width:'12%',height:'55px',imagePositionX:50,imagePositionY:50,imageFit:'cover',zIndex:i+1,visible:true,locked:false,showInHero:true};
const response = await page.request.post(`${BASE_URL}/api/invitations`, {data:{slug:`pd-${Date.now()}`,document:{eventType:'Wedding',fields:{names:'Hitch'},objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}}});
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
const id2=process.env.PD_ID2||'motion-11';
let pt = await page.evaluate(id=>{
  const t=document.querySelector(`#stage .object[data-id="${id}"]`);const r=t.getBoundingClientRect();
  return {x:r.left+r.width/2,y:r.top+r.height/2};
},id);
const pt2 = await page.evaluate(id2=>{
  const t=document.querySelector(`#stage .object[data-id="${id2}"]`);const r=t.getBoundingClientRect();
  return {x:r.left+r.width/2,y:r.top+r.height/2};
},id2);
if(process.env.PD_CROP){
  await page.evaluate(()=>{EInviteEditorBridge.select(['motion-0']);EInviteDirectManipulation.startCrop();const tb=document.querySelector('.studio-selection-toolbar');if(tb)tb.style.pointerEvents='none'});
  if(process.env.PD_SCROLLAWAY){await page.evaluate(()=>{const v=document.querySelector('#canvasViewport');v.scrollTop+=700;v.scrollLeft+=500});await page.waitForTimeout(60)}
  await page.evaluate(()=>{const t=document.querySelector('#stage .object[data-id="motion-0"]');t?.scrollIntoView?.({block:'center',inline:'center'})});
  await page.waitForTimeout(220);
  pt = await page.evaluate(()=>{
    const t=document.querySelector('#stage .object[data-id="motion-0"]');const r=t.getBoundingClientRect();
    return {x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};
  });
}
await page.evaluate(()=>{
  window.__ev=[];
  new PerformanceObserver(l=>{for(const e of l.getEntries())window.__ev.push({name:e.name,start:Math.round(e.startTime),dur:Math.round(e.duration)})}).observe({type:'event',durationThreshold:8,buffered:false});
  window.__fr=[];let last=null;const s=t=>{if(last!==null)window.__fr.push({at:Math.round(t),dt:Math.round((t-last)*10)/10});last=t;requestAnimationFrame(s)};requestAnimationFrame(s);
  window.__lt=[];
  try{new PerformanceObserver(l=>{for(const e of l.getEntries())if(window.__lt.length<60)window.__lt.push({start:Math.round(e.startTime),dur:Math.round(e.duration)})}).observe({type:'longtask',buffered:false})}catch{}
  window.__pdInfo0=['.studio-selection-toolbar','#v54SelectionCard','.pe-selection-box'].map(sel=>{const el=document.querySelector(sel);if(!el)return[sel,'missing'];const cs=getComputedStyle(el);const r=el.getBoundingClientRect();return[sel,{hidden:el.hidden,display:cs.display,op:cs.opacity,vis:cs.visibility,wc:cs.willChange,bf:(cs.backdropFilter||'').slice(0,40),shadow:(cs.boxShadow||'').slice(0,70),rect:[Math.round(r.width),Math.round(r.height)]}]});
});
if(process.env.PD_WRITES){await page.evaluate(()=>{
  window.__writes=[];const rec=(k,v)=>{if(window.__writes.length<300)window.__writes.push(k+' :: '+String(v).slice(0,90))};
  const desc=Object.getOwnPropertyDescriptor(Element.prototype,'classList');
  Object.defineProperty(Element.prototype,'classList',{get(){window.__cl=this;return desc.get.call(this)},configurable:true});
  const who=()=>{const el=window.__cl;if(!el)return'?';return(el.id||'')+'|'+(el.tagName||'')+'|'+String(el.className||'').slice(0,36)};
  const want=()=>{const el=window.__cl;if(!el)return false;if(el===document.body)return true;if(el.closest?.('aside,header,.studio-rail,.studio-statusbar'))return true;return !!(el.children&&el.children.length>4&&el.querySelectorAll&&el.querySelectorAll('*').length>120)};
  const ca=DOMTokenList.prototype.add;DOMTokenList.prototype.add=function(...a){if(want())rec('cls.add '+who(),a.join(','));return ca.apply(this,a)};
  const cr=DOMTokenList.prototype.remove;DOMTokenList.prototype.remove=function(...a){if(want())rec('cls.rm '+who(),a.join(','));return cr.apply(this,a)};
  const ct=DOMTokenList.prototype.toggle;DOMTokenList.prototype.toggle=function(...a){if(want())rec('cls.tg '+who(),a.join(','));return ct.apply(this,a)};
  const sa=Element.prototype.setAttribute;Element.prototype.setAttribute=function(n,v){if(this===document.body)rec('body.attr',n+'='+String(v).slice(0,60));return sa.call(this,n,v)};
  const ra=Element.prototype.removeAttribute;Element.prototype.removeAttribute=function(n){if(this===document.body)rec('body.rmAttr',n);return ra.call(this,n)};
  window.__mo=[];
  new MutationObserver(rs=>{for(const r of rs){if(window.__mo.length>400)return;if(r.type==='attributes'&&(r.attributeName==='style'||r.attributeName==='class')){const t=r.target;window.__mo.push(r.attributeName+' :: '+((t.id||'')+'|'+(t.tagName||'')+'|'+String(t.className||'').slice(0,40))+' :: '+String(t.getAttribute?.(r.attributeName)||'').slice(0,80))}}}).observe(document,{subtree:true,attributes:true,attributeFilter:['style','class']});
});}
if(process.env.PD_KILL_BODYCLS){await page.evaluate(()=>{
  const ban=new Set(['v54-has-selection','ei-suppress-autofit','right-open','pe-pointer-interaction']);
  const desc=Object.getOwnPropertyDescriptor(Element.prototype,'classList');
  Object.defineProperty(Element.prototype,'classList',{get(){window.__cl=this;return desc.get.call(this)},configurable:true});
  const ca=DOMTokenList.prototype.add;DOMTokenList.prototype.add=function(...a){if(window.__cl===document.body&&a.some(t=>ban.has(t)))return;return ca.apply(this,a)};
  const cr=DOMTokenList.prototype.remove;DOMTokenList.prototype.remove=function(...a){if(window.__cl===document.body&&a.some(t=>ban.has(t)))return;return cr.apply(this,a)};
  const ct=DOMTokenList.prototype.toggle;DOMTokenList.prototype.toggle=function(...a){if(window.__cl===document.body&&ban.has(a[0]))return this.contains(a[0]);return ct.apply(this,a)};
});}
if(process.env.PD_KILL_PANECLS){await page.evaluate(()=>{
  const desc=Object.getOwnPropertyDescriptor(Element.prototype,'classList');
  Object.defineProperty(Element.prototype,'classList',{get(){window.__cl=this;return desc.get.call(this)},configurable:true});
  const isPane=()=>{const el=window.__cl;return!!el&&!!el.closest?.('.studio-inspector-tab,.studio-inspector-pane,.studio-inspector-tabs,.final-advanced-inspector')};
  const ca=DOMTokenList.prototype.add;DOMTokenList.prototype.add=function(...a){if(isPane()&&a.includes('active'))return;return ca.apply(this,a)};
  const cr=DOMTokenList.prototype.remove;DOMTokenList.prototype.remove=function(...a){if(isPane()&&a.includes('active'))return;return cr.apply(this,a)};
  const ct=DOMTokenList.prototype.toggle;DOMTokenList.prototype.toggle=function(...a){if(isPane()&&a[0]==='active')return this.contains('active');return ct.apply(this,a)};
});}
if(process.env.PD_CSS){await page.evaluate(css=>{const s=document.createElement('style');s.textContent=css;document.head.append(s)},process.env.PD_CSS);await page.waitForTimeout(250)}
if(process.env.PD_INFO){await page.evaluate(()=>{window.__pdInfoA=['.studio-selection-toolbar','#v54SelectionCard','.pe-selection-box'].map(sel=>{const el=document.querySelector(sel);if(!el)return[sel,'missing'];const cs=getComputedStyle(el);return[sel,{hidden:el.hidden,display:cs.display,op:cs.opacity,vis:cs.visibility,wc:cs.willChange,bf:(cs.backdropFilter||'').slice(0,40),rect:[Math.round(el.getBoundingClientRect().width),Math.round(el.getBoundingClientRect().height)]}]})})}
if(process.env.PD_KEEP){await page.evaluate(()=>{const s=document.createElement('style');s.textContent='@keyframes pdkeep{from{opacity:.4}to{opacity:.41}}';document.head.append(s);const d=document.createElement('div');d.style.cssText='position:fixed;left:0;top:0;width:2px;height:2px;background:#000;opacity:.4;animation:pdkeep 1s linear infinite;z-index:99999;pointer-events:none';document.body.append(d)});await page.waitForTimeout(250)}
const {x,y}=pt;
if(process.env.PD_KILL_DISPATCH){await page.evaluate(()=>{const orig=document.dispatchEvent.bind(document);document.dispatchEvent=ev=>{try{if(ev&&ev.type==='einvite:selection-changed')return true}catch(e){}return orig(ev)}})}
if(process.env.PD_WARM){await page.evaluate(async()=>{try{await window.EInviteWebGLScene?.render?.([])}catch{};await new Promise(r=>setTimeout(r,300))})}
if(process.env.PD_NOBLUR){await page.evaluate(()=>{const s=document.createElement('style');s.textContent='*{backdrop-filter:none !important;-webkit-backdrop-filter:none !important}';document.head.append(s);return new Promise(r=>setTimeout(r,300))})}
if(process.env.PD_DOUBLE){await page.mouse.click(x,y);await page.waitForTimeout(600);await page.mouse.click(Math.round(x)-260,Math.round(y)-180);await page.waitForTimeout(800)}
if(process.env.PD_NOCHROME){await page.evaluate(()=>{const s=document.createElement('style');s.textContent='.studio-selection-toolbar,#v54SelectionCard,.pe-selection-box{display:none !important}';document.head.append(s);return new Promise(r=>setTimeout(r,250))})}
if(process.env.PD_NOGL){await page.evaluate(()=>{window.EInviteWebGLScene?.setEnabled?.(false);const d=window.EInviteWebGLScene?.diagnostics?.();return new Promise(r=>setTimeout(()=>r(JSON.stringify(d)),300))})}
if(process.env.PD_KILL_SELECT){await page.mouse.click(x,y);await page.waitForTimeout(900);await page.evaluate(()=>{const b=window.EInviteEditorBridge;if(b&&b.select)b.select=()=>{}})}
if(process.env.PRESELECT){await page.mouse.click(x,y);await page.waitForTimeout(500);}
if(process.env.PD_SECOND){await page.mouse.click(x,y);await page.waitForTimeout(900)}
const mx=process.env.PD_SECOND?pt2.x:x,my=process.env.PD_SECOND?pt2.y:y;
const origin=await page.evaluate(()=>performance.timeOrigin);
const toPerf=w=>Math.round(w-origin);
if(process.env.PD_SNAP){
  let cdpT=null,traceChunks=[],traceDone=null;
  if(process.env.PD_SNAP_TRACE){
    cdpT=await page.context().newCDPSession(page);
    cdpT.on('Tracing.dataCollected',d=>{const v=d.value||[];for(let i=0;i<v.length;i++)if(traceChunks.length<500000)traceChunks.push(v[i])});
    traceDone=new Promise(r=>cdpT.on('Tracing.tracingComplete',r));
    await cdpT.send('Tracing.start',{categories:'devtools.timeline,blink.user_timing,cc,gpu,viz,disabled-by-default-devtools.timeline.invalidationTracking',transferMode:'ReportEvents'});
  }
  const vb=await page.locator('#canvasViewport').boundingBox();
  const marks={};
  const benchJs=()=>page.evaluate(()=>{const t0=performance.now();let x=0;const M=7**8;for(let i=0;i<1e7;i++)x=(x+i*3)%M;const t1=performance.now();return Math.round((t1-t0)*10)/10;});
  if(process.env.PD_SNAP_BENCHSERIES){for(let k=0;k<10;k++){const t=Math.round(await page.evaluate(()=>performance.now()));const js=await benchJs();console.log('SNAP-BENCH-T t='+t+' js='+js);await page.waitForTimeout(350)}}
  if(process.env.PD_SNAP_BENCH){console.log('SNAP-BENCH-A',await benchJs())}
  if(process.env.PD_SNAP_SAMPLE){await page.evaluate(()=>{
    window.__samples=[];window.__lt=[];
    try{new PerformanceObserver(l=>{for(const e of l.getEntries())window.__lt.push([Math.round(e.startTime),Math.round(e.duration)])}).observe({type:'longtask',buffered:false})}catch{}
    const tick=()=>{let n=document.getElementsByTagName('*').length;let rules=0;let sheets=0,errored=0,maxRules=0;for(const s of document.styleSheets){sheets++;try{const c=(s.cssRules||[]).length;rules+=c;if(c>maxRules)maxRules=c}catch{errored++}}
      window.__samples.push({t:Math.round(performance.now()),nodes:n,sheets,errored,maxRules,adopted:(document.adoptedStyleSheets||[]).length,rules,mem:performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576):-1,anims:document.getAnimations?document.getAnimations().length:-1});
      if(window.__samples.length<44)setTimeout(tick,300);};
    tick();
  });}
  if(process.env.PD_SNAP_INFO){
    const info=await page.evaluate(()=>{const st=document.querySelector('#stage'),cv=document.querySelector('#canvasViewport');const sr=st?st.getBoundingClientRect():null,cvr=cv?cv.getBoundingClientRect():null;let rules=0;for(const s of document.styleSheets){try{rules+=(s.cssRules||[]).length}catch{}}return{nodes:document.getElementsByTagName('*').length,sheets:document.styleSheets.length,rules,stage:sr?[Math.round(sr.width),Math.round(sr.height)]:null,view:[cvr?Math.round(cvr.width):0,cvr?Math.round(cvr.height):0],scroll:[cv?cv.scrollWidth:0,cv?cv.scrollHeight:0],win:[innerWidth,innerHeight],dpr:devicePixelRatio}});
    console.log('SNAP-INFO',JSON.stringify(info));
  }
  if(process.env.PD_SNAP_PREWAIT){await page.waitForTimeout(Number(process.env.PD_SNAP_PREWAIT));marks.prewaitEnd=toPerf(Date.now())}
  if(process.env.PD_SNAP_BENCH){console.log('SNAP-BENCH-B',await benchJs())}
  if(!process.env.PD_SNAP_NOPRE){
  await page.mouse.move(vb.x+vb.width/2,vb.y+vb.height/2);
  await page.keyboard.down('Control');
  for(let i=0;i<60;i++){await page.mouse.wheel(0,i<30?-1:1);await page.waitForTimeout(16)}
  await page.keyboard.up('Control');await page.waitForTimeout(160);
  marks.wheelEnd=toPerf(Date.now());
  {const x0=vb.x+vb.width/2,y0=vb.y+vb.height/2,dx=70,dy=50,dur=2000;
   await page.mouse.move(x0,y0);await page.mouse.down({button:'middle'});
   const start=Date.now();
   while(Date.now()-start<dur){const t=Math.min(1,(Date.now()-start)/dur);await page.mouse.move(x0+dx*t,y0+dy*t);await page.waitForTimeout(16)}
   await page.mouse.move(x0+dx,y0+dy);await page.mouse.up({button:'middle'});}
  marks.panEnd=toPerf(Date.now());
  }
  if(!process.env.PD_SNAP_NODESELECT){await page.evaluate(()=>EInviteEditorBridge.select([]));}
  marks.selectClear=toPerf(Date.now());
  const snapTarget=page.locator('#stage .object[data-id="motion-6"]');
  if(!process.env.PD_SNAP_NOSCROLL)await snapTarget.scrollIntoViewIfNeeded();
  marks.scrollDone=toPerf(Date.now());
  if(process.env.PD_SNAP_WAITSCROLL)await page.waitForTimeout(Number(process.env.PD_SNAP_WAITSCROLL));
  const snapBefore=await snapTarget.boundingBox();
  marks.bbox=toPerf(Date.now());
  await page.evaluate(()=>{
    try{performance.clearMarks('pdmeasure');performance.mark('pdmeasure')}catch{}
    const m=window.__motionMeasure={frames:[],at:[],commits:0,longTasks:[],latency:null,active:true,last:null,input:null};
    const sample=time=>{if(!m.active)return;if(m.last!==null){m.frames.push(time-m.last);m.at.push(time)}m.last=time;requestAnimationFrame(sample)};
    requestAnimationFrame(sample);
    m.longObserver=new PerformanceObserver(list=>m.longTasks.push(...list.getEntries().map(e=>({start:e.startTime,duration:e.duration}))));
    m.longObserver.observe({type:'longtask',buffered:false});
  });
  marks.measureStart=toPerf(Date.now());
  let grab=null;
  if(!process.env.PD_SNAP_NOGRAB){
    grab=await page.evaluate(id=>{const t=document.querySelector(`#stage .object[data-id="${id}"]`);if(!t)return null;const r=t.getBoundingClientRect();for(let fy=.85;fy>=.1;fy-=.05)for(let fx=.1;fx<=.9;fx+=.05){const x=r.left+r.width*fx,y=r.top+r.height*fy,el=document.elementFromPoint(x,y);if(el&&el.closest&&el.closest('.object')&&el.closest('.object').dataset.id===id)return{x,y}}return null},'motion-6');
  }
  marks.grabDone=toPerf(Date.now());
  if(!grab&&snapBefore)grab={x:snapBefore.x+snapBefore.width/2,y:snapBefore.y+snapBefore.height/2};
  if(!grab)throw Error('PD_SNAP: no grab point');
  const gx=grab.x,gy=grab.y,dx2=25,dy2=20;
  await page.mouse.move(gx,gy);marks.move1=toPerf(Date.now());
  await page.mouse.down();marks.down=toPerf(Date.now());
  if(!process.env.PD_SNAP_HOLDONLY){
    const start=Date.now();while(Date.now()-start<600){const t=Math.min(1,(Date.now()-start)/600);await page.mouse.move(gx+dx2*t,gy+dy2*t);await page.waitForTimeout(16)}
    await page.mouse.move(gx+dx2,gy+dy2);marks.dragEnd=toPerf(Date.now());
    if(!process.env.PD_SNAP_NOUP){await page.mouse.up();marks.up=toPerf(Date.now())}
  }
  await page.evaluate(()=>{const m=window.__motionMeasure;m.active=false;m.longObserver.disconnect()});
  marks.stop=toPerf(Date.now());
  const snap=await page.evaluate(()=>{const m=window.__motionMeasure;return {n:m.frames.length,frames:m.frames.map((f,i)=>[Math.round(m.at[i]),Math.round(f*10)/10]),longTasks:m.longTasks}});
  console.log('SNAP-MARKS',JSON.stringify(marks));
  console.log('SNAP-PREWARM',JSON.stringify(await page.evaluate(()=>({at:window.__prewarmAt||0,done:window.__prewarmDone||0,state:(window.EInviteFirstSelectionPrewarm||{}).state||'none',ok:!!(window.EInviteFirstSelectionPrewarm||{}).ok}))));
  const res=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>/deferred|bundle-index\.(js|css)|editor-suite/.test(r.name)).map(r=>({n:r.name.split('/').pop(),start:Math.round(r.startTime),end:Math.round(r.responseEnd)})));
  console.log('SNAP-RES',JSON.stringify(res));
  if(process.env.PD_SNAP_SAMPLE){
    const detail=await page.evaluate(()=>({sheets:[...document.styleSheets].map(s=>({h:(s.href||'inline').split('/').pop(),n:(()=>{try{return s.cssRules.length}catch{return -1}})()})),lt:window.__lt||[],anims:document.getAnimations?document.getAnimations().length:-1}));
    console.log('SNAP-SAMPLE-DETAIL',JSON.stringify(detail));
    console.log('SNAP-SAMPLES',JSON.stringify(await page.evaluate(()=>window.__samples)));
  }
  console.log('SNAP-FRAMES n='+snap.n+' '+snap.frames.map(([a,d],i)=>i+':@'+a+'='+d).join(' '));
  console.log('SNAP-LT',JSON.stringify(snap.longTasks));
  if(cdpT){
    await cdpT.send('Tracing.end');await traceDone;
    const mark=traceChunks.find(e=>e.name==='pdmeasure'&&(e.ph==='R'||e.ph==='I'||e.ph==='n'));
    let refUs=mark?mark.ts:Infinity;
    if(!isFinite(refUs))refUs=Math.min(...traceChunks.map(e=>e.ts||Infinity));
    const agg=new Map(),rows=[];
    for(const e of traceChunks){
      if(e.ph!=='X'||typeof e.dur!=='number'||e.dur<=0)continue;
      const t=(e.ts-refUs)/1000;
      if(t<-80||t>1500)continue;
      agg.set(e.name,(agg.get(e.name)||0)+e.dur);
      rows.push({t,name:e.name,dur:e.dur,d:e.args&&e.args.data?e.args.data:null});
    }
    console.log('SNAP-TRACE-BY-NAME\n'+[...agg.entries()].sort((a,b)=>b[1]-a[1]).slice(0,34).map(([k,v])=>`${(v/1000).toFixed(1)}\t${k}`).join('\n'));
    const watch=/^(EventDispatch|FunctionCall|UpdateLayoutTree|Layout|PrePaint|Paint|Layerize|UpdateLayerTree|InvalidateLayout|StyleRecalc|ParseHTML|RunMicrotasks|MajorGC|MinorGC|BeginMainFrame|Commit|ActivateLayerTree|DrawFrame|CompositeLayers|RasterTask|Rasterize|PriGPU|PresentFrame|SwapBuffers|Animation|HitTest|ScheduleStyle|RecalcStyle|NotifyLayout|WebGL|UpdateCompositor)/;
    const timeline=rows.filter(r=>watch.test(r.name)).sort((a,b)=>a.t-b.t);
    console.log('SNAP-TRACE-TIMELINE n='+timeline.length);
    console.log(timeline.map(r=>{
      const d=r.d||{};
      const extra=[d.type,d.functionName,d.elementCount!=null?('els='+d.elementCount):null,d.reason?String(d.reason).slice(0,50):null,d.nodeName,d.note,d.callsite].filter(x=>x!==undefined&&x!==null&&x!=='').join(' ');
      return `${r.t.toFixed(1)}\t${r.name}\t${Math.round(r.dur)}\t${(extra||'').slice(0,90)}`;
    }).join('\n'));
    const evs=rows.filter(r=>r.name==='EventDispatch');
    console.log('SNAP-TRACE-EVENTS\n'+evs.sort((a,b)=>a.t-b.t).map(r=>`${r.t.toFixed(1)}\t${(r.d&&r.d.type)||'?'}\t${Math.round(r.dur)}`).join('\n'));
    const fcs=rows.filter(r=>r.name==='FunctionCall'&&r.dur>=800);
    console.log('SNAP-TRACE-FC\n'+fcs.sort((a,b)=>b.dur-a.dur).slice(0,40).map(r=>`${Math.round(r.dur)}\t@${r.t.toFixed(1)}\t${(r.d&&r.d.functionName)||'?'}\t${(r.d&&String(r.d.callsite||'').split('/').pop())||''}`).join('\n'));
  }
  await page.evaluate(fr=>{window.__fr=fr},snap.frames.map(([a,d])=>({at:a,dt:d})));
}
const cdp=await page.context().newCDPSession(page);
const profOn=!process.env.PD_NOPROF;
if(profOn){await cdp.send('Profiler.enable');await cdp.send('Profiler.setSamplingInterval',{interval:200});await cdp.send('Profiler.start');}
if(!process.env.PD_SNAP){
if(!process.env.PD_NOMOVE)await page.mouse.move(mx,my);
if(process.env.PD_MOVEGAP)await page.waitForTimeout(Number(process.env.PD_MOVEGAP));
if(process.env.PD_NODOWN){await page.waitForTimeout(Number(process.env.PD_HOLD||80));}
else if(process.env.PD_SYNTH){await page.evaluate(([sx,sy])=>{const t=document.elementFromPoint(sx,sy)||document.querySelector('#stage');t.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true,composed:true,clientX:sx,clientY:sy,pointerId:77,pointerType:'mouse',button:0,buttons:1,isPrimary:true}));},[mx,my]);}else{await page.mouse.down();}
if(process.env.PD_DRAGMOVE){const dx=25,dy=15;const start=Date.now();while(Date.now()-start<600){const t=Math.min(1,(Date.now()-start)/600);await page.mouse.move(x+dx*t,y+dy*t);await page.waitForTimeout(16)}await page.mouse.move(x+dx,y+dy);await page.mouse.up()}
}
await page.waitForTimeout(Number(process.env.PD_HOLD||80));
const {profile}=profOn?{profile:(await cdp.send('Profiler.stop')).profile}:{profile:{nodes:[],samples:[],timeDeltas:[]}};
if(process.env.PD_METRICS){
  await cdp.send('Performance.enable');
  const snap=async()=>{const r=await cdp.send('Performance.getMetrics');const o={};for(const m of r.metrics)o[m.name]=m.value;return o};
  const diff=(a,b)=>{const o={};for(const k of Object.keys(b)){const av=a[k];const bv=b[k];if(typeof bv==='number'&&typeof av==='number'&&/Duration|Count/.test(k)&&bv!==av)o[k]=+ (bv-av).toFixed(4)}return o};
  await page.waitForTimeout(350);
  const S0=await snap();
  await cdp.send('Profiler.start');
  await page.mouse.move(mx+6,my+5);await page.mouse.down();await page.waitForTimeout(160);
  const S1=await snap();
  await page.mouse.move(mx+46,my+35,{steps:5});await page.mouse.up();await page.waitForTimeout(260);
  const S2=await snap();
  const {profile:cp}=await cdp.send('Profiler.stop');
  const byId2=new Map(cp.nodes.map(n=>[n.id,n]));
  const self2=new Map();
  cp.samples.forEach((sid,i)=>{const n=byId2.get(sid);const cf=n.callFrame;const k=`${cf.functionName||'(anon)'} ${(cf.url||'').split('/').pop()}:${cf.lineNumber}`;self2.set(k,(self2.get(k)||0)+(cp.timeDeltas[i]||0)/1000)});
  console.log('COMMIT-TOP SELF MS\n'+[...self2.entries()].sort((a,b)=>b[1]-a[1]).slice(0,26).map(([k,v])=>`${v.toFixed(1)}\t${k}`).join('\n'));
  const parent2=new Map();for(const n of cp.nodes)for(const c of (n.children||[]))parent2.set(c,n);
  const callers2=new Map();
  cp.samples.forEach((sid,i)=>{const n=byId2.get(sid);const fn=n.callFrame.functionName;if(!/^(querySelector|querySelectorAll|getBoundingClientRect|\(program\)|offsetWidth|offsetHeight|offsetLeft|offsetTop|clientWidth|clientHeight|scrollHeight|scrollTop|getComputedStyle|\(garbage collector\)|\(idle\))$/.test(fn)&&!/^get /.test(fn))return;const chain=[];let p=parent2.get(sid);for(let d=0;d<7&&p;d++){chain.push(`${p.callFrame.functionName||'(anon)'}:${p.callFrame.lineNumber}`);p=parent2.get(p.id)}const k=`${fn} <- ${chain.join(' <- ')}`;callers2.set(k,(callers2.get(k)||0)+(cp.timeDeltas[i]||0)/1000)});
  console.log('COMMIT-CALLERS\n'+[...callers2.entries()].sort((a,b)=>b[1]-a[1]).slice(0,26).map(([k,v])=>`${v.toFixed(1)}\t${k}`).join('\n'));
  await page.waitForTimeout(300);
  const S3=await snap();
  console.log('METRICS_DOWN', JSON.stringify(diff(S0,S1)));
  console.log('METRICS_COMMIT', JSON.stringify(diff(S1,S2)));
  console.log('METRICS_SETTLE', JSON.stringify(diff(S2,S3)));
}
const byId=new Map(profile.nodes.map(n=>[n.id,n]));
const self=new Map();
profile.samples.forEach((sid,i)=>{const n=byId.get(sid);const cf=n.callFrame;const k=`${cf.functionName||'(anon)'} ${(cf.url||'').split('/').pop()}:${cf.lineNumber}`;self.set(k,(self.get(k)||0)+(profile.timeDeltas[i]||0)/1000)});
const top=[...self.entries()].sort((a,b)=>b[1]-a[1]).slice(0,40);
console.log('PD-TOP SELF MS\n'+top.map(([k,v])=>`${v.toFixed(1)}\t${k}`).join('\n'));
const totals=new Map();
profile.samples.forEach((sid,i)=>{const n=byId.get(sid);const cf=n.callFrame;const k=`${cf.functionName||'(anon)'} ${(cf.url||'').split('/').pop()}:${cf.lineNumber}`;totals.set(k,(totals.get(k)||0)+(profile.timeDeltas[i]||0)/1000)});
const parent=new Map();for(const n of profile.nodes)for(const c of (n.children||[]))parent.set(c,n);
const callers=new Map();
profile.samples.forEach((sid,i)=>{const n=byId.get(sid);const fn=n.callFrame.functionName;if(!/^(querySelector|querySelectorAll|getBoundingClientRect|\(program\)|offsetWidth|offsetHeight|offsetLeft|offsetTop|clientWidth|clientHeight|scrollHeight|scrollTop|getComputedStyle|\(garbage collector\))$/.test(fn)&&!/^get /.test(fn))return;const chain=[];let p=parent.get(sid);for(let d=0;d<6&&p;d++){chain.push(`${p.callFrame.functionName||'(anon)'}:${p.callFrame.lineNumber}`);p=parent.get(p.id)}const k=`${fn} <- ${chain.join(' <- ')}`;callers.set(k,(callers.get(k)||0)+(profile.timeDeltas[i]||0)/1000)});
console.log('PD-CALLERS\n'+[...callers.entries()].sort((a,b)=>b[1]-a[1]).slice(0,30).map(([k,v])=>`${v.toFixed(1)}\t${k}`).join('\n'));
const out = await page.evaluate(()=>({
  census:{
    toolbar:document.querySelectorAll('.studio-selection-toolbar:not([hidden])').length,
    card:document.querySelectorAll('.v54-selection-card:not([hidden])').length,
    box:document.querySelectorAll('.pe-selection-box:not([hidden])').length,
    paneRight:!!document.querySelector('aside.right'),
    selected:document.querySelectorAll('#stage .object.selected').length,
    cropActive:document.querySelectorAll('#stage .object.v24-crop-active').length
  },
  events:window.__ev.filter(e=>['pointerdown','pointermove','pointerup','click'].includes(e.name)||e.dur>=30),
  bigFrames:window.__fr.filter(f=>f.dt>=25),
  longTasks:(window.__lt||[]),
  pdInfo0:(window.__pdInfo0||[]),
  pdInfoA:(window.__pdInfoA||[]),
  frames:window.__fr.length,
  writes:(window.__writes||[]).slice(0,90),
  writeCount:(window.__writes||[]).length,
  mo:(window.__mo||[]).slice(0,110),
  moCount:(window.__mo||[]).length
}));
const seen=new Set();const ev=out.events.filter(e=>{const k=e.name+e.start+e.dur;if(seen.has(k))return false;seen.add(k);return true});
console.log(ev.map(e=>`${e.name} @${e.start} dur=${e.dur}`).join('\n'));
console.log('CENSUS', JSON.stringify(out.census));
console.log('bigFrames', JSON.stringify(out.bigFrames), 'frames', out.frames);
console.log('longTasks', JSON.stringify(out.longTasks||[]));
console.log('PDINFO0', JSON.stringify(out.pdInfo0||[]));
console.log('PDINFOA', JSON.stringify(out.pdInfoA||[]));
console.log('WRITES n='+(out.writeCount||0));
console.log((out.writes||[]).join('\n'));
console.log('MO n='+(out.moCount||0));
console.log((out.mo||[]).join('\n'));
await browser.close();
