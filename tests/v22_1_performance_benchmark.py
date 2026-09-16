#!/usr/bin/env python3
from __future__ import annotations
import base64,json
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'V22_1_PERFORMANCE_RESULTS.json'
def source(name:str)->str:return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_PERFORMANCE_BENCHMARK',exc)
 worker=base64.b64encode(source('scene-render-worker-v22.js').encode()).decode()
 html=f'''<!doctype html><meta charset="utf-8"><style>html,body{{margin:0}}#stage{{position:relative;width:1600px;height:1200px;contain:layout paint style}}.object{{position:absolute;box-sizing:border-box}}</style><div id="stage"></div><script>window.EInviteLifecycle={{add:()=>{{}},cleanup:()=>{{}}}};window.EInviteRenderWorkerURL=URL.createObjectURL(new Blob([atob("{worker}")],{{type:'application/javascript'}}));</script><script>{source('performance-observability-v22.js')}</script><script>{source('interaction-scheduler-v22.js')}</script><script>{source('incremental-scene-renderer-v22.js')}</script><script>{source('render-worker-bridge-v22.js')}</script>'''
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_PERFORMANCE_BENCHMARK',exc)
  try:
   page=browser.new_page(viewport={'width':1800,'height':1400});page.set_default_timeout(60000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(html,wait_until='load');page.wait_for_function('()=>window.EInviteRenderWorker&&window.EInviteIncrementalRenderer&&window.EInvitePerformance')
   results=[]
   for count in (250,1000,3000):
    result=page.evaluate('''async count=>{const stage=document.querySelector('#stage');const t0=performance.now();stage.replaceChildren();const frag=document.createDocumentFragment();for(let i=0;i<count;i++){const el=document.createElement('div');el.className='object';el.dataset.id='b'+i;el.dataset.objectType=i%7===0?'image':i%3===0?'text':'shape';el.dataset.visible='true';el.dataset.locked='false';el.dataset.opacity='1';const x=(i%40)*38,y=Math.floor(i/40)*30;el.style.cssText=`left:${x}px;top:${y}px;width:34px;height:26px;z-index:${i+1}`;frag.append(el)}stage.append(frag);const domBuildMs=performance.now()-t0;const i0=performance.now();EInviteIncrementalRenderer.rebuildIndex();const indexBuildMs=performance.now()-i0;const doc={objects:{}};const ids=[];for(let i=0;i<Math.min(25,count);i++){ids.push('b'+i);doc.objects['b'+i]={left:`${(i%40)*38+7}px`,top:`${Math.floor(i/40)*30+5}px`,width:'34px',height:'26px',rotation:i%9,zIndex:i+1,visible:true,locked:false,opacity:1}}const p0=performance.now();const patched=EInviteIncrementalRenderer.applyDocument(doc,'hero',{type:'TRANSFORM_ONLY',ids});const incrementalPatchMs=performance.now()-p0;const q0=performance.now();let hits=0;for(let i=0;i<200;i++)hits+=EInviteIncrementalRenderer.queryPoint((i*47)%1500,(i*31)%1100).length;const query200Ms=performance.now()-q0;const w0=performance.now();const sync=await EInviteRenderWorker.sync();const workerSyncMs=performance.now()-w0;document.querySelector('[data-id="b0"]').style.left='333px';const wp0=performance.now();EInviteRenderWorker.schedulePatch(['b0']);const workerPatch=await EInviteRenderWorker.flushPatch();const workerPatchMs=performance.now()-wp0;const th0=performance.now();const thumb=await EInviteRenderWorker.renderThumbnail({width:480,height:270});const thumbnailMs=performance.now()-th0;const diagnostics=await EInviteRenderWorker.diagnostics();return{count,domBuildMs,indexBuildMs,incrementalPatchMs,query200Ms,queryAverageMs:query200Ms/200,workerSyncMs,workerPatchMs,thumbnailMs,thumbnailBytes:thumb.blob?.size||0,patched,hits,sync,workerPatch,diagnostics,memory:EInvitePerformance.snapshot().memory}}''',count)
    for key in ('domBuildMs','indexBuildMs','incrementalPatchMs','query200Ms','queryAverageMs','workerSyncMs','workerPatchMs','thumbnailMs'):
     result[key]=round(result[key],3)
    results.append(result)
   assert not errors,errors
   assert all(r['patched'] and r['sync']['nodes']==r['count'] and r['workerPatch']['patched']==1 and r['thumbnailBytes']>100 for r in results),results
   payload={'release':'V22.1.7','environment':'headless Chromium container benchmark; indicative, not native Windows certification','results':results}
   OUT.write_text(json.dumps(payload,indent=2),encoding='utf-8')
  finally:browser.close()
 print('V22_1_PERFORMANCE_BENCHMARK_PASSED');print(OUT.read_text(encoding='utf-8'));return 0
if __name__=='__main__':raise SystemExit(main())
