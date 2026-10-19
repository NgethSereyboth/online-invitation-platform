import {createRequire} from 'node:module';
import {BASE_URL} from './lib/repo.mjs';
const require = createRequire(new URL('./playwright-check/package.json', import.meta.url));
const {chromium} = require('playwright');
const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {});
const page = await browser.newPage({viewport:{width:1440,height:900}});
const account = await page.request.post(`${BASE_URL}/api/auth/register`, {data:{email:`hitch-${Date.now()}@example.com`,password:'Motion-test-password-123!'}});
if(!account.ok()) throw Error('register '+account.status());
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {type:i===0?'image':'shape',shapeKind:'rectangle',fillColor:'#3E7C6B',src:'',left:`${8+(i%5)*17}%`,top:`${8+Math.floor(i/5)*13}%`,width:'12%',height:'55px',imagePositionX:50,imagePositionY:50,imageFit:'cover',zIndex:i+1,visible:true,locked:false,showInHero:true};
const response = await page.request.post(`${BASE_URL}/api/invitations`, {data:{slug:`hitch-${Date.now()}`,document:{eventType:'Wedding',fields:{names:'Hitch'},objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}}});
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
const id='motion-6';
const pt = await page.evaluate(id=>{
  const t=document.querySelector(`#stage .object[data-id="${id}"]`);const r=t.getBoundingClientRect();
  return {x:r.left+r.width/2,y:r.top+r.height/2};
},id);
await page.evaluate(()=>{
  window.__ev=[];
  new PerformanceObserver(l=>{for(const e of l.getEntries())window.__ev.push({name:e.name,start:Math.round(e.startTime),dur:Math.round(e.duration)})}).observe({type:'event',durationThreshold:8,buffered:false});
  window.__fr=[];let last=null;const s=t=>{if(last!==null)window.__fr.push({at:Math.round(t),dt:Math.round((t-last)*10)/10});last=t;requestAnimationFrame(s)};requestAnimationFrame(s);
  window.__t0=performance.now();
});
const {x,y}=pt;
if(process.env.PRESELECT){await page.mouse.click(x,y);await page.waitForTimeout(500);}
const cdp=await page.context().newCDPSession(page);
await cdp.send('Profiler.enable');await cdp.send('Profiler.setSamplingInterval',{interval:200});
await cdp.send('Profiler.start');
await page.mouse.move(x,y);await page.mouse.down();
const start=Date.now();
while(Date.now()-start<600){const t=Math.min(1,(Date.now()-start)/600);await page.mouse.move(x+25*t,y+20*t);await page.waitForTimeout(16)}
await page.mouse.move(x+25,y+20);await page.mouse.up();
await page.waitForTimeout(400);
const {profile}=await cdp.send('Profiler.stop');
const byId=new Map(profile.nodes.map(n=>[n.id,n]));
const self=new Map();
profile.samples.forEach((sid,i)=>{const n=byId.get(sid);const cf=n.callFrame;const k=`${cf.functionName||'(anon)'} ${(cf.url||'').split('/').pop()}:${cf.lineNumber}`;self.set(k,(self.get(k)||0)+(profile.timeDeltas[i]||0)/1000)});
const top=[...self.entries()].sort((a,b)=>b[1]-a[1]).slice(0,30);
console.log('TOP SELF MS\n'+top.map(([k,v])=>`${v.toFixed(1)}\t${k}`).join('\n'));
const parent=new Map();for(const n of profile.nodes)for(const c of (n.children||[]))parent.set(c,n);
const callers=new Map();
profile.samples.forEach((sid,i)=>{const n=byId.get(sid);const fn=n.callFrame.functionName;if(!/^(querySelector|querySelectorAll|getBoundingClientRect|\(program\)|offsetWidth|clientWidth|scrollHeight)$/.test(fn)&&!/^get /.test(fn))return;const chain=[];let p=parent.get(sid);for(let d=0;d<4&&p;d++){chain.push(`${p.callFrame.functionName||'(anon)'}:${p.callFrame.lineNumber}`);p=parent.get(p.id)}const k=`${fn} <- ${chain.join(' <- ')}`;callers.set(k,(callers.get(k)||0)+(profile.timeDeltas[i]||0)/1000)});
console.log('CALLERS\n'+[...callers.entries()].sort((a,b)=>b[1]-a[1]).slice(0,25).map(([k,v])=>`${v.toFixed(1)}\t${k}`).join('\n'));
const out = await page.evaluate(()=>({
  events:window.__ev.filter(e=>['pointerdown','pointermove','pointerup','click'].includes(e.name)||e.dur>=30),
  bigFrames:window.__fr.filter(f=>f.dt>=40),
  frames:window.__fr.length
}));
const seen=new Set();const ev=out.events.filter(e=>{const k=e.name+e.start+e.dur;if(seen.has(k))return false;seen.add(k);return true});
console.log(ev.map(e=>`${e.name} @${e.start} dur=${e.dur}`).join('\n'));
console.log('bigFrames', JSON.stringify(out.bigFrames), 'frames', out.frames);
await browser.close();
