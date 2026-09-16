#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def source(name):return (ROOT/name).read_text(encoding='utf-8')
def build():
 spec=importlib.util.spec_from_file_location('inline_editor',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_7_GPU_EDITOR_INTEGRATION',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_7_GPU_EDITOR_INTEGRATION',exc)
  try:
   page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(60000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(build(),wait_until='load');page.wait_for_function('()=>window.EInviteProfessionalEditor&&window.EInviteEditorBridge');page.wait_for_timeout(900)
   if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(100)
   page.add_script_tag(content=source('tests/gpu_mock_webgl.js'))
   for name in ['performance-observability-v22.js','interaction-scheduler-v22.js','incremental-scene-renderer-v22.js','gpu-texture-cache-v22.js','webgl-scene-backend-v22.js','gpu-projection-v22.js','adaptive-gpu-quality-v22.js']:page.add_script_tag(content=source(name))
   page.wait_for_function('()=>window.EInviteWebGLScene?.available&&window.EInviteGraphicsDiagnostics')
   page.evaluate("()=>EInviteEditorBridge.select(['hero'])");page.wait_for_timeout(120)
   before=page.evaluate("()=>({seq:EInviteProfessionalEditor.commandSequence,left:EInviteEditorBridge.getState().objects.hero.left})")
   box=page.evaluate("()=>document.querySelector('#stage .object[data-id=hero]').getBoundingClientRect().toJSON()")
   x=box['x']+box['width']/2;y=box['y']+box['height']/2
   page.mouse.move(x,y);page.mouse.down();
   for step in range(1,31):page.mouse.move(x+step*2,y+step*.4)
   during=page.evaluate("()=>({active:EInviteWebGLScene.canvas.dataset.active,gpuHidden:document.querySelector('[data-id=hero]').classList.contains('ei-gpu-preview-source')})")
   page.mouse.up();page.wait_for_timeout(350)
   after=page.evaluate("()=>({seq:EInviteProfessionalEditor.commandSequence,left:EInviteEditorBridge.getState().objects.hero.left,active:EInviteWebGLScene.canvas.dataset.active,gpuHidden:document.querySelector('[data-id=hero]').classList.contains('ei-gpu-preview-source'),gpu:EInviteWebGLScene.diagnostics(),graphics:EInviteGraphicsDiagnostics.snapshot(),perf:EInvitePerformance.snapshot()})")
   assert during['active']=='true' and during['gpuHidden'] is True,(during,after)
   assert after['seq']==before['seq']+1 and after['left']!=before['left'],(before,after)
   assert after['active']=='false' and after['gpuHidden'] is False,after
   assert after['gpu']['drawCalls']>=1 and after['gpu']['textureCache']['entries']>=1,after
   assert after['graphics']['hardwareAcceleration'] is True and after['perf']['metrics']['gpuFrame']['count']>=1,after
   assert not errors,errors
  finally:browser.close()
 print('V22_1_7_GPU_EDITOR_INTEGRATION_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
