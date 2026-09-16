#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_6_GPU_PROJECTION',exc)
 html='''<!doctype html><meta charset="utf-8"><style>body{margin:0}#stage{position:relative;width:520px;height:260px}.object{position:absolute}.shape-surface,img{display:block;width:100%;height:100%}</style><div id="stage"><div class="object" data-id="circle" data-object-type="shape" data-shape-kind="circle" data-fill-color="#cc3355" data-visible="true" style="left:20px;top:20px;width:100px;height:100px;z-index:1"><div class="shape-surface"></div></div><div class="object" data-id="vector" data-object-type="shape" data-shape-kind="vector" data-vector-path="M0 0 L100 0 L50 100 Z" data-vector-view-box="0 0 100 100" data-fill-color="#339966" data-visible="true" style="left:160px;top:20px;width:100px;height:100px;z-index:2"><div class="shape-surface"></div></div><div class="object" data-id="masked" data-object-type="image" data-visible="true" style="left:300px;top:20px;width:100px;height:100px;z-index:3"><img id="photo"></div></div><script>window.EInviteLifecycle={add(){}};const c=document.createElement('canvas');c.width=c.height=32;let q=c.getContext('2d');q.fillStyle='#3366cc';q.fillRect(0,0,32,32);photo.src=c.toDataURL();q.clearRect(0,0,32,32);q.fillStyle='white';q.fillRect(0,0,16,32);document.querySelector('[data-id=masked]').dataset.gpuMaskSrc=c.toDataURL()</script>'''
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_6_GPU_PROJECTION',exc)
  try:
   page=browser.new_page(viewport={'width':800,'height':500});page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='load');page.add_script_tag(content=src('tests/gpu_mock_webgl.js'))
   for name in ['performance-observability-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js','gpu-projection-v22.js']:page.add_script_tag(content=src(name))
   page.wait_for_function('()=>window.EInviteGPUProjection')
   result=page.evaluate('''async()=>{await photo.decode();await EInviteGPUProjection.renderPickBuffer();const r=stage.getBoundingClientRect();const center=await EInviteGPUProjection.pick(r.left+70,r.top+70),corner=await EInviteGPUProjection.pick(r.left+23,r.top+23),vector=await EInviteGPUProjection.pick(r.left+210,r.top+70),masked=await EInviteGPUProjection.pick(r.left+325,r.top+70);const draws=EInviteWebGLScene.context.draws.map(d=>({pick:d.u_pick,useTexture:d.u_useTexture,useMask:d.u_useMask,radius:d.u_radius,color:d.u_color}));const diag=EInviteGPUProjection.diagnostics();EInviteGPUProjection.destroy();EInviteWebGLScene.destroy();return{center,corner,vector,masked,draws,diag}}''')
   assert result['center']=='circle' and result['corner'] is None,result
   assert result['vector']=='vector' and result['masked']=='masked',result
   assert any(d['pick']==1 and d['useTexture']==1 for d in result['draws']),result
   assert any(d['useMask']==1 for d in result['draws']),result
   assert result['diag']['vectors'] is True and result['diag']['masks'] is True and result['diag']['pickObjects']==3,result
   assert not errors,errors
  finally:browser.close()
 print('V22_1_6_GPU_PROJECTION_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
