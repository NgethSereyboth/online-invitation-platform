#!/usr/bin/env python3
from __future__ import annotations
import base64
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def source(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_WORKER_RENDERING_BROWSER',exc)
 worker=base64.b64encode(source('scene-render-worker-v22.js').encode()).decode()
 html=f'''<!doctype html><meta charset="utf-8"><style>#stage{{position:relative;width:800px;height:600px}}.object{{position:absolute}}</style><div id="stage"></div><script>window.EInviteLifecycle={{add:()=>{{}},cleanup:()=>{{}}}};window.EInviteRenderWorkerURL=URL.createObjectURL(new Blob([atob("{worker}")],{{type:'application/javascript'}}));for(let i=0;i<120;i++){{const e=document.createElement('div');e.className='object';e.dataset.id='o'+i;e.dataset.objectType=i%4===0?'image':i%3===0?'text':'shape';e.dataset.visible='true';e.dataset.locked='false';e.dataset.opacity='1';e.style.cssText=`left:${{(i%12)*60}}px;top:${{Math.floor(i/12)*48}}px;width:50px;height:38px;z-index:${{i+1}}`;stage.append(e)}}</script><script>{source('performance-observability-v22.js')}</script><script>{source('interaction-scheduler-v22.js')}</script><script>{source('incremental-scene-renderer-v22.js')}</script><script>{source('render-worker-bridge-v22.js')}</script>'''
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_WORKER_RENDERING_BROWSER',exc)
  try:
   page=browser.new_page(viewport={'width':1000,'height':760});page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(html,wait_until='load');page.wait_for_function('()=>window.EInviteRenderWorker&&window.EInviteIncrementalRenderer&&window.EInviteInteractionScheduler&&window.EInvitePerformance')
   result=page.evaluate('''async()=>{let latest=-1,runs=0;for(let i=0;i<80;i++)EInviteInteractionScheduler.scheduleFrame('same',()=>{latest=i;runs++});await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const doc={objects:{}};for(let i=0;i<120;i++)doc.objects['o'+i]={left:`${(i%12)*60+5}px`,top:`${Math.floor(i/12)*48+3}px`,width:'50px',height:'38px',rotation:i%7,zIndex:i+1,visible:true,locked:false,opacity:1};const incremental=EInviteIncrementalRenderer.applyDocument(doc,'hero',{type:'TRANSFORM_ONLY',ids:['o0','o1','o2']});const hit=EInviteIncrementalRenderer.queryPoint(10,8);const sync=await EInviteRenderWorker.sync();document.querySelector('[data-id=\"o0\"]').style.left='205px';EInviteRenderWorker.schedulePatch(['o0']);const patch=await EInviteRenderWorker.flushPatch();const workerHit=await EInviteRenderWorker.queryPoint(210,8);const thumb=await EInviteRenderWorker.renderThumbnail({width:320,height:180});const diagnostics=await EInviteRenderWorker.diagnostics();EInvitePerformance.record('selectionLatency',4.2);EInvitePerformance.record('incrementalRender',3.1);const perf=EInvitePerformance.snapshot(),renderer=EInviteIncrementalRenderer.snapshot(),scheduler=EInviteInteractionScheduler.stats();EInviteRenderWorker.destroy();EInviteIncrementalRenderer.destroy();EInviteInteractionScheduler.destroy();EInvitePerformance.destroy();const teardown={worker:await EInviteRenderWorker.diagnostics(),renderer:EInviteIncrementalRenderer.snapshot(),scheduler:EInviteInteractionScheduler.stats(),perf:EInvitePerformance.snapshot()};return{latest,runs,incremental,hit:hit.map(x=>x.id),sync,patch,workerHit,thumb:{supported:thumb.supported,size:thumb.blob?.size||0,type:thumb.blob?.type||''},diagnostics,perf,renderer,scheduler,teardown}}''')
   assert result['latest']==79 and result['runs']==1,result
   assert result['incremental'] is True and 'o0' in result['hit'],result
   assert result['sync']['nodes']==120 and result['diagnostics']['available'] is True,result
   assert result['patch']['patched']==1 and any(item['id']=='o0' for item in result['workerHit']),result
   assert result['workerHit'] and result['thumb']['supported'] is True and result['thumb']['size']>100,result
   assert result['renderer']['index']['items']==120,result
   assert result['perf']['metrics']['incrementalRender']['count']>=1,result
   assert result['scheduler']['frameQueue']==0,result
   assert result['teardown']['worker']['available'] is False,result
   assert result['teardown']['renderer']['destroyed'] is True and result['teardown']['scheduler']['destroyed'] is True and result['teardown']['perf']['destroyed'] is True,result
   assert not errors,errors
  finally:browser.close()
 print('V22_1_WORKER_RENDERING_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
