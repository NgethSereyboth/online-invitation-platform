#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_7_ADAPTIVE_GPU_QUALITY',exc)
 html='<!doctype html><style>#stage{position:relative;width:400px;height:300px}.right{width:300px}</style><div id=stage></div><aside class=right></aside><script>EInviteLifecycle={add(){}};EInviteRenderWorker={diagnostics(){return Promise.resolve({available:true})}}</script>'
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_7_ADAPTIVE_GPU_QUALITY',exc)
  try:
   page=browser.new_page();page.set_content(html);page.add_script_tag(content=src('tests/gpu_mock_webgl.js'))
   for name in ['performance-observability-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js','gpu-projection-v22.js','adaptive-gpu-quality-v22.js']:page.add_script_tag(content=src(name))
   page.wait_for_function('()=>window.EInviteGraphicsDiagnostics&&document.querySelector(".ei-graphics-diagnostics")')
   result=page.evaluate('''()=>{const d=EInviteGraphicsDiagnostics;d.setQuality('low');const low=d.snapshot();d.setQuality('off');const off=d.snapshot();d.setQuality('high');const high=d.snapshot();dispatchEvent(new CustomEvent('einvite:gpu-context-lost'));dispatchEvent(new CustomEvent('einvite:gpu-context-lost'));const lost=d.snapshot();const text=document.querySelector('.ei-graphics-diagnostics').textContent;d.destroy();EInviteGPUProjection.destroy();EInviteWebGLScene.destroy();EInvitePerformance.destroy();return{low,off,high,lost,text,panel:!!document.querySelector('.ei-graphics-diagnostics')}}''')
   assert result['low']['quality']['level']=='low' and result['low']['webgl']['qualityScale']==.6,result
   assert result['off']['enabled'] is False,result
   assert result['high']['quality']['level']=='high' and result['high']['enabled'] is True,result
   assert result['lost']['enabled'] is False and result['lost']['contextLosses']==2,result
   assert 'Graphics diagnostics' in result['text'] and result['panel'] is False,result
  finally:browser.close()
 print('V22_1_7_ADAPTIVE_GPU_QUALITY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
