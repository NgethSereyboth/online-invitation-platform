#!/usr/bin/env python3
from __future__ import annotations
import os,shutil,subprocess,time
from pathlib import Path
from browser_runtime import skipped
ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')
def launch(p):
 exe=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').is_file() else None)
 common=['--no-sandbox','--disable-dev-shm-usage','--ignore-gpu-blocklist','--enable-webgl','--enable-unsafe-swiftshader'] if os.name!='nt' else ['--ignore-gpu-blocklist','--enable-webgl','--enable-unsafe-swiftshader']
 kwargs={'headless':True,'args':common}
 if exe:kwargs['executable_path']=exe
 browser=p.chromium.launch(**kwargs);page=browser.new_page();available=page.evaluate('()=>!!document.createElement("canvas").getContext("webgl2")');page.close()
 if available:return browser,None
 browser.close();xvfb=None;env=os.environ.copy()
 if os.name!='nt' and shutil.which('Xvfb'):
  display=f':{90+os.getpid()%100}';xvfb=subprocess.Popen(['Xvfb',display,'-screen','0','1280x900x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.8);env['DISPLAY']=display
  args=common+['--use-gl=angle','--use-angle=swiftshader'];kwargs={'headless':False,'args':args,'env':env}
  if exe:kwargs['executable_path']=exe
  browser=p.chromium.launch(**kwargs);return browser,xvfb
 kwargs={'headless':False,'args':common}
 if exe:kwargs['executable_path']=exe
 return p.chromium.launch(**kwargs),None
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_7_REAL_WEBGL_RUNTIME',exc)
 xvfb=None
 with sync_playwright() as p:
  try:browser,xvfb=launch(p)
  except Exception as exc:return skipped('V22_1_7_REAL_WEBGL_RUNTIME',exc)
  try:
   page=browser.new_page(viewport={'width':900,'height':650});page.set_default_timeout(45000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   html='''<!doctype html><meta charset="utf-8"><style>body{margin:0}#stage{position:relative;width:520px;height:260px}.object{position:absolute}.shape-surface,img{display:block;width:100%;height:100%}</style><div id="stage"><div class="object" data-id="circle" data-object-type="shape" data-shape-kind="circle" data-fill-color="#cc3355" data-visible="true" style="left:20px;top:20px;width:100px;height:100px;z-index:1"><div class="shape-surface"></div></div><div class="object" data-id="vector" data-object-type="shape" data-shape-kind="vector" data-vector-path="M0 0 L100 0 L50 100 Z" data-vector-view-box="0 0 100 100" data-fill-color="#339966" data-visible="true" style="left:160px;top:20px;width:100px;height:100px;z-index:2"><div class="shape-surface"></div></div><div class="object" data-id="masked" data-object-type="image" data-visible="true" style="left:300px;top:20px;width:100px;height:100px;z-index:3"><img id="photo"></div></div><aside class="right"></aside><script>window.EInviteLifecycle={add(){}};const c=document.createElement('canvas');c.width=c.height=32;let q=c.getContext('2d');q.fillStyle='#3366cc';q.fillRect(0,0,32,32);photo.src=c.toDataURL();q.clearRect(0,0,32,32);q.fillStyle='white';q.fillRect(0,0,16,32);document.querySelector('[data-id=masked]').dataset.gpuMaskSrc=c.toDataURL()</script>'''
   page.set_content(html,wait_until='load')
   for name in ['performance-observability-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js','gpu-projection-v22.js','adaptive-gpu-quality-v22.js']:page.add_script_tag(content=src(name))
   page.wait_for_function('()=>window.EInviteWebGLScene')
   result=page.evaluate('''async()=>{await photo.decode();const scene=EInviteWebGLScene;if(!scene.available)return{available:false,diag:scene.diagnostics?.()};const rendered=await scene.render(null,{mode:'real-webgl'}),gl=scene.context,dpr=scene.canvas.width/stage.clientWidth,pixel=new Uint8Array(4);gl.readPixels(Math.round(70*dpr),Math.round((stage.clientHeight-70)*dpr),1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);await EInviteGPUProjection.renderPickBuffer();const r=stage.getBoundingClientRect(),center=await EInviteGPUProjection.pick(r.left+70,r.top+70),corner=await EInviteGPUProjection.pick(r.left+22,r.top+22),vector=await EInviteGPUProjection.pick(r.left+210,r.top+70),maskedLeft=await EInviteGPUProjection.pick(r.left+325,r.top+70),maskedRight=await EInviteGPUProjection.pick(r.left+380,r.top+70);return{available:true,rendered,pixel:[...pixel],center,corner,vector,maskedLeft,maskedRight,diag:scene.diagnostics(),projection:EInviteGPUProjection.diagnostics(),graphics:EInviteGraphicsDiagnostics.snapshot()}}''')
   assert result['available'] is True,result
   assert result['rendered']['drawCalls']>=3 and result['pixel'][3]>0,result
   assert result['center']=='circle' and result['corner'] is None,result
   assert result['vector']=='vector' and result['maskedLeft']=='masked',result
   assert result['maskedRight'] is None,result
   assert result['diag']['backend']=='webgl2' and result['diag']['maxTextureSize']>=4096,result
   assert result['projection']['pickObjects']==3 and result['graphics']['hardwareAcceleration'] is True,result
   assert not errors,errors
  finally:
   browser.close()
   if xvfb:
    xvfb.terminate()
    try:xvfb.wait(timeout=3)
    except Exception:xvfb.kill()
 print('V22_1_7_REAL_WEBGL_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
