import {createRequire} from 'node:module';
import {BASE_URL} from './lib/repo.mjs';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
const page = await browser.newPage({viewport:{width:1366,height:900}});
const account = await page.request.post(`${BASE_URL}/api/auth/register`, {data:{
  email:`snap2-${Date.now()}@example.com`, password:'Motion-test-password-123!'}});
if (!account.ok()) throw Error(`Register: ${account.status()}`);
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {
  type:i===0?'image':'shape', shapeKind:'rectangle', fillColor:'#3E7C6B',
  src:i===0?`data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="2400"><rect width="3000" height="2400" fill="#3B6FB6"/></svg>')}`:'',
  left:`${8+(i%5)*17}%`, top:`${8+Math.floor(i/5)*13}%`, width:'12%', height:'55px',
  imagePositionX:50, imagePositionY:50, imageFit:'cover', zIndex:i+1, visible:true, locked:false, showInHero:true};
const response = await page.request.post(`${BASE_URL}/api/invitations`, {data:{
  slug:`snap2-${Date.now()}`, document:{eventType:'Wedding',fields:{names:'S2'},objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}}});
if (!response.ok()) throw Error(`Invitation: ${response.status()}`);
const invite = await response.json();
await page.addInitScript(id=>localStorage.setItem('sovan-active-invite', String(id)), invite.id);
await page.goto(`${BASE_URL}/index.html?_perfdebug=1`, {waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>document.documentElement.dataset.editorReady==='true');
const dismiss=page.locator('#finalTourDismiss');
if(await dismiss.count() && await dismiss.isVisible())await dismiss.click();
await page.waitForFunction(()=>!!window.EInviteEditorCore && !!window.EInviteDirectManipulation && !!window.EInviteMotion);
await page.evaluate(async()=>{EInviteToolController.setTool('select',{announce:false});await new Promise(r=>setTimeout(r,300));EInviteCanvasViewController.fit();await new Promise(r=>setTimeout(r,450));});

const session = await page.context().newCDPSession(page);
await session.send('Profiler.enable');
await session.send('Profiler.setSamplingInterval',{interval:200});

for (let run=0; run<3; run++) {
  await page.evaluate(()=>EInviteEditorBridge.select([]));
  await new Promise(r=>setTimeout(r,300));
  const box = await page.locator('#stage .object[data-id="motion-6"]').boundingBox();
  const x = box.x+box.width/2, y = box.y+box.height/2;
  await page.evaluate(()=>{
    const m=window.__s2={frames:[],last:null,active:true,ev:[]};
    const s=t=>{if(!m.active)return;if(m.last!==null)m.frames.push([m.last,t-m.last]);m.last=t;requestAnimationFrame(s)};
    requestAnimationFrame(s);
    const log=n=>m.ev.push([n,performance.now()]);
    for (const type of ['pointerdown','pointermove','pointerup']) window.addEventListener(type,()=>log(type),{capture:true});
    new PerformanceObserver(l=>l.getEntries().forEach(e=>m.ev.push(['longtask',e.startTime,e.duration]))).observe({entryTypes:['longtask']});
  });
  await session.send('Profiler.start');
  await page.mouse.move(x,y);
  await page.mouse.down();
  for (let i=1;i<=6;i++) { await page.mouse.move(x+i*4,y+i*3); }
  await page.mouse.up();
  const {profile} = await session.send('Profiler.stop');
  const data = await page.evaluate(()=>{const m=window.__s2; m.active=false; return {frames:m.frames.filter(f=>f[1]>=30), ev:m.ev};});
  console.log(`run ${run} big frames:`, JSON.stringify(data.frames.map(f=>[+f[0].toFixed(0), +f[1].toFixed(1)])));
  console.log(`  events:`, JSON.stringify(data.ev.map(e=>e.map(v=>typeof v==='number'?+v.toFixed(1):v))));
  if (run===0) {
    const byId=new Map(profile.nodes.map(n=>[n.id,n]));
    const dt=profile.timeDeltas, counts=new Map();
    profile.samples.forEach((s,i)=>counts.set(s,(counts.get(s)||0)+(dt[i]||0)));
    const agg=new Map();
    for (const [id,us] of counts){const n=byId.get(id);const cf=n.callFrame;const k=`${cf.functionName||'(anon)'} ${cf.url.split('/').pop()}:${cf.lineNumber+1}`;agg.set(k,(agg.get(k)||0)+us)}
    [...agg].sort((a,b)=>b[1]-a[1]).slice(0,18).forEach(([k,us])=>console.log(`  ${(us/1000).toFixed(1)}ms ${k}`));
  }
  await page.evaluate(()=>{window.__s2=null});
  await page.evaluate(()=>EInviteEditorBridge.select([]));
  await new Promise(r=>setTimeout(r,300));
}
await browser.close();
