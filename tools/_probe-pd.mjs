import {createRequire} from 'node:module';
import {BASE_URL} from './lib/repo.mjs';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
const page = await browser.newPage({viewport:{width:1366,height:900}});
const account = await page.request.post(`${BASE_URL}/api/auth/register`, {data:{
  email:`pd-probe-${Date.now()}@example.com`, password:'Motion-test-password-123!'}});
if (!account.ok()) throw Error(`Register: ${account.status()}`);
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {
  type:i===0?'image':'shape', shapeKind:'rectangle', fillColor:'#3E7C6B',
  src:i===0?`data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="2400"><rect width="3000" height="2400" fill="#3B6FB6"/></svg>')}`:'',
  left:`${8+(i%5)*17}%`, top:`${8+Math.floor(i/5)*13}%`, width:'12%', height:'55px',
  imagePositionX:50, imagePositionY:50, imageFit:'cover', zIndex:i+1, visible:true, locked:false, showInHero:true};
const response = await page.request.post(`${BASE_URL}/api/invitations`, {data:{
  slug:`pd-probe-${Date.now()}`, document:{eventType:'Wedding',fields:{names:'PD'},objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}}});
if (!response.ok()) throw Error(`Invitation: ${response.status()}`);
const invite = await response.json();
await page.addInitScript(id=>localStorage.setItem('sovan-active-invite', String(id)), invite.id);
await page.goto(`${BASE_URL}/index.html?_perfdebug=1`, {waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>document.documentElement.dataset.editorReady==='true');
const dismiss=page.locator('#finalTourDismiss');
if(await dismiss.count() && await dismiss.isVisible())await dismiss.click();
await page.waitForFunction(()=>!!window.EInviteEditorCore && !!window.EInviteDirectManipulation && !!window.EInviteMotion);
await page.evaluate(async()=>{EInviteToolController.setTool('select',{announce:false});await new Promise(r=>setTimeout(r,300));EInviteCanvasViewController.fit();await new Promise(r=>setTimeout(r,450));});

const pd = (id) => page.evaluate(id=>{
  const el=document.querySelector(`#stage .object[data-id="${id}"]`);
  const r=el.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height/2;
  const t0=performance.now();
  const init={bubbles:true,cancelable:true,composed:true,clientX:x,clientY:y,button:0,buttons:1,pointerId:7,pointerType:'mouse',isPrimary:true};
  el.dispatchEvent(new PointerEvent('pointerdown',init));
  const t1=performance.now();
  window.__pdMs=t1-t0;
  return t1-t0;
},id);
const up = (id) => page.evaluate(id=>{
  const el=document.querySelector(`#stage .object[data-id="${id}"]`);
  const r=el.getBoundingClientRect();
  const t0=performance.now();
  window.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,cancelable:true,clientX:r.left,clientY:r.top,button:0,pointerId:7,pointerType:'mouse',isPrimary:true}));
  return performance.now()-t0;
},id);

const session = await page.context().newCDPSession(page);
await session.send('Profiler.enable');
await session.send('Profiler.setSamplingInterval',{interval:100});

for (const label of ['unselected-1','unselected-2']) {
  await page.evaluate(()=>EInviteEditorBridge.select([]));
  await new Promise(r=>setTimeout(r,200));
  await session.send('Profiler.start');
  const ms = await pd('motion-6');
  const {profile} = await session.send('Profiler.stop');
  await up('motion-6');
  console.log(label, 'pointerdown ms', ms.toFixed(1));
  // aggregate self time by function
  const byId=new Map(profile.nodes.map(n=>[n.id,n]));
  const dt=profile.timeDeltas, counts=new Map();
  profile.samples.forEach((s,i)=>counts.set(s,(counts.get(s)||0)+(dt[i]||0)));
  const agg=new Map();
  for (const [id,us] of counts){const n=byId.get(id);const cf=n.callFrame;const k=`${cf.functionName||'(anon)'} ${cf.url.split('/').pop()}:${cf.lineNumber+1}`;agg.set(k,(agg.get(k)||0)+us)}
  [...agg].sort((a,b)=>b[1]-a[1]).slice(0,14).forEach(([k,us])=>console.log(`  ${(us/1000).toFixed(1)}ms ${k}`));
}
await page.evaluate(()=>EInviteEditorBridge.select(['motion-6']));
await new Promise(r=>setTimeout(r,200));
const pre = await pd('motion-6');
await up('motion-6');
console.log('preselected pointerdown ms', pre.toFixed(1));
await browser.close();
