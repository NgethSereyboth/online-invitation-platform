#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_7_GPU_FALLBACK',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_7_GPU_FALLBACK',exc)
  try:
   page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content('<div id=stage style="position:relative;width:400px;height:300px"></div><aside class=right></aside><script>EInviteLifecycle={add(){}};const g=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,o){return t==="webgl2"?null:g.call(this,t,o)}</script>')
   for name in ['performance-observability-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js','gpu-projection-v22.js','adaptive-gpu-quality-v22.js']:page.add_script_tag(content=src(name))
   page.wait_for_function('()=>window.EInviteGraphicsDiagnostics')
   result=page.evaluate('()=>({scene:EInviteWebGLScene,projection:EInviteGPUProjection,graphics:EInviteGraphicsDiagnostics.snapshot(),panel:document.querySelector(".ei-graphics-diagnostics")?.textContent||""})')
   assert result['scene']['available'] is False and result['projection']['available'] is False,result
   assert result['graphics']['hardwareAcceleration'] is False and result['graphics']['backend']=='compatibility',result
   assert 'Compatibility' in result['panel'] and not errors,(result,errors)
  finally:browser.close()
 print('V22_1_7_GPU_FALLBACK_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
