#!/usr/bin/env node
// One-off CPU attribution probe: replicate the perf-gate snap-drag leg exactly
// (30-object page, grabPoint on motion-6, 25/20 px drag) under a CDP profiler,
// then print the top self-time functions for the drag segment.
import {chromium} from 'playwright';
import {mkdirSync} from 'fs';
import {resolve} from 'path';

const REPO_ROOT = resolve(import.meta.dirname, '..');
const BASE_URL = process.env.APP_BASE || process.env.BASE_URL || 'http://127.0.0.1:4175';
mkdirSync(resolve(REPO_ROOT, 'artifacts/canvas-motion/verify/attribution'), {recursive:true});

const browser = await chromium.launch(process.env.CHROME_PATH ? {executablePath: process.env.CHROME_PATH} : {});
const ctx = await browser.newContext({viewport:{width:1366,height:900}});
const page = await ctx.newPage();

// — replicate tools/canvas-motion-perf.mjs setup() (30-object representative page) —
await page.request.post(`${BASE_URL}/api/auth/register`, {data:{
  email:`motion-attrib-${Date.now()}@example.com`, password:'Motion-test-password-123!'
}});
const objects = {};
for (let i=0;i<30;i++) objects[`motion-${i}`] = {
  type:i===0?'image':'shape', shapeKind:'rectangle', fillColor:'#3E7C6B',
  src:i===0?`data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="2400"><rect width="3000" height="2400" fill="#3B6FB6"/></svg>')}`:'',
  left:`${8+(i%5)*17}%`, top:`${8+Math.floor(i/5)*13}%`, width:'12%', height:'55px',
  imagePositionX:50, imagePositionY:50, imageFit:'cover', zIndex:i+1,
  visible:true, locked:false, showInHero:true
};
const invite = await (await page.request.post(`${BASE_URL}/api/invitations`, {data:{
  slug:`motion-attrib-${Date.now()}`, document:{eventType:'Wedding',fields:{names:'Canvas motion'},
    objects,designPages:[],sectionOrder:['schedule','venue','rsvp'],settings:{rsvpEnabled:true}}
}})).json();
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
  for(let i=0;i<20;i++){
    await new Promise(r=>setTimeout(r,150));
    const v=window.EInviteMotion.viewport.view, s=`${v.x}|${v.y}|${v.zoom}`;
    if(prev!==null && s===prev)break;
    prev=s;
  }
  EInviteCanvasViewController.fit();
  await new Promise(r=>setTimeout(r,450));
});
// the gate selects nothing before snap-drag
await page.evaluate(()=>EInviteEditorBridge.select([]));
// Long Animation Frames observer: frames >50 ms with per-script attribution
await page.evaluate(()=>{
  const loaf=[];
  window.__loaf=loaf;
  try{
    new PerformanceObserver(list=>{
      for(const e of list.getEntries()){
        loaf.push({
          duration:e.duration,
          scripts:(e.scripts||[]).map(s=>({
            name:s.name, duration:s.duration,
            fn:s.functionName, src:s.sourceURL, line:s.sourceFunctionName || ''
          })).filter(s=>s.duration>1)
        });
      }
    }).observe({type:'long-animation-frame',buffered:false});
  }catch(error){ window.__loafUnsupported=String(error); }
});

const cdp = await ctx.newCDPSession(page);
let events=[];
cdp.on('Tracing.dataCollected', d=>events.push(...d.value));
await cdp.send('Tracing.start', {
  traceConfig: {
    includedCategories: ['devtools.timeline', 'devtools.timeline.stack', 'v8'],
    excludedCategories: ['devtools.timeline.async_soon'],
    enableSampling: true
  }
});

// replicate grabPoint for motion-6
const grab = await page.evaluate(()=>{
  const t=document.querySelector('#stage .object[data-id="motion-6"]');
  const r=t.getBoundingClientRect();
  for(let fy=.85;fy>=.1;fy-=.05)for(let fx=.1;fx<=.9;fx+=.05){
    const x=r.left+r.width*fx, y=r.top+r.height*fy, el=document.elementFromPoint(x,y);
    if(el&&el.closest&&el.closest('.object')&&el.closest('.object').dataset.id==='motion-6')return {x,y};
  }
  return null;
});

await page.mouse.move(grab.x, grab.y);
await page.mouse.down();
for(let i=1;i<=30;i++){
  const t=i/30;
  await page.mouse.move(grab.x+25*t, grab.y+20*t);
  await page.waitForTimeout(16);
}
await page.mouse.up();
await cdp.send('Tracing.end');
let traceDone=false;
cdp.on('Tracing.tracingComplete', ()=>{traceDone=true});
await new Promise(res=>{const i=setInterval(()=>{if(traceDone){clearInterval(i);res()}},50)});
console.log(`trace events total: ${events.length}`);
console.log('=== timeline events >=40ms during drag ===');
for(const e of events.filter(e=>e.ph==='X').sort((a,b)=>b.dur-a.dur).slice(0,8)){
  console.log(`top dur ${(e.dur/1000).toFixed(2)} ms  ${e.name}  @${e.cat}  ph=${e.ph}`);
}
console.log('=== timeline events >=40ms during drag ===');
for(const e of events.filter(e=>e.ph==='X'&&e.dur>=40000).sort((a,b)=>b.dur-a.dur).slice(0,20)){
  console.log(`${(e.dur/1000).toFixed(1).padStart(7)} ms  ${e.name}  @${e.cat}`);
  console.log('    args:', JSON.stringify(e.args).slice(0, 1200));
  if(e.args?.stackTrace?.length) console.log('    stack:', e.args.stackTrace.slice(0,6).map(f=>`${f.functionName||'?'} ${f.url?String(f.url).split(/[\\/]/).pop():''}>${f.lineNumber}`).join(' <- '));
  if(e.args?.sampleStackTrace?.length) console.log('    sampled:', e.args.sampleStackTrace.slice(0,6).map(f=>`${f.functionName||'?'} ${f.url?String(f.url).split(/[\\/]/).pop():''}>${f.lineNumber}`).join(' <- '));
}
await browser.close();
