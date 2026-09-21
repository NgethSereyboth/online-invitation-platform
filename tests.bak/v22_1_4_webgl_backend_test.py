#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_4_WEBGL_BACKEND',exc)
 html='''<!doctype html><meta charset="utf-8"><style>#stage{position:relative;width:640px;height:420px}.object{position:absolute}.shape-surface,img{width:100%;height:100%;display:block}</style><div id="stage"><div class="object selected" data-id="shape" data-object-type="shape" data-shape-kind="rectangle" data-fill-color="#b34f66" data-visible="true" style="left:30px;top:40px;width:130px;height:90px;z-index:5"><div class="shape-surface"></div><i class="resize-handle"></i></div><div class="object" data-id="image" data-object-type="image" data-visible="true" style="left:220px;top:70px;width:120px;height:100px;z-index:6"><img id="photo"></div></div><div class="right"></div><script>window.EInviteLifecycle={items:[],add(f){this.items.push(f)},cleanup(){this.items.splice(0).reverse().forEach(f=>f())}};const c=document.createElement('canvas');c.width=32;c.height=32;const x=c.getContext('2d');x.fillStyle='#2468aa';x.fillRect(0,0,32,32);photo.src=c.toDataURL()</script>'''
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_4_WEBGL_BACKEND',exc)
  try:
   page=browser.new_page(viewport={'width':900,'height':650});page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='load');page.add_script_tag(content=src('tests/gpu_mock_webgl.js'))
   for name in ['performance-observability-v22.js','interaction-scheduler-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js']:page.add_script_tag(content=src(name))
   page.wait_for_function('()=>window.EInviteWebGLScene')
   result=page.evaluate('''async()=>{await photo.decode();const scene=EInviteWebGLScene;const rendered=await scene.render(null,{mode:'test'});const gl=scene.context,pixel=new Uint8Array(4),dpr=scene.canvas.width/stage.clientWidth;gl.readPixels(Math.round(80*dpr),Math.round((stage.clientHeight-80)*dpr),1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);const started=await scene.beginPreview(document.querySelector('[data-id=shape]'),{pointerId:7,pointerType:'mouse'});await new Promise(r=>setTimeout(r,60));const during={active:scene.canvas.dataset.active,hidden:document.querySelector('[data-id=shape]').classList.contains('ei-gpu-preview-source')};scene.endPreview();const after={active:scene.canvas.dataset.active,hidden:document.querySelector('[data-id=shape]').classList.contains('ei-gpu-preview-source')};const diag=scene.diagnostics();scene.destroy();return{rendered,pixel:[...pixel],started,during,after,diag,destroyed:!document.querySelector('.ei-gpu-scene-layer')}}''')
   assert result['diag']['available'] is True,result
   assert result['diag']['backend']=='webgl2' and result['rendered']['drawCalls']>=2,result
   assert result['pixel'][3]>0,result
   assert result['started'] is True and result['during']=={'active':'true','hidden':True},result
   assert result['after']=={'active':'false','hidden':False} and result['destroyed'] is True,result
   assert not errors,errors
  finally:browser.close()
 print('V22_1_4_WEBGL_BACKEND_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
