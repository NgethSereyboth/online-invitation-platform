#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 spec=importlib.util.spec_from_file_location('inline_editor',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def source(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_EDITOR_INTERACTION_PERFORMANCE',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_EDITOR_INTERACTION_PERFORMANCE',exc)
  try:
   page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(60000);errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(build(),wait_until='load',timeout=60000);page.wait_for_function('()=>window.EInviteProfessionalEditor&&window.EInviteEditorBridge');page.wait_for_timeout(1600)
   if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(120)
   for name in ['performance-observability-v22.js','interaction-scheduler-v22.js','incremental-scene-renderer-v22.js']:
    page.add_script_tag(content=source(name))
   page.wait_for_function('()=>window.EInvitePerformance&&window.EInviteInteractionScheduler&&window.EInviteIncrementalRenderer')
   page.evaluate("()=>{window.__inc=0;addEventListener('einvite:incremental-render',()=>__inc++);EInviteEditorBridge.select(['title'])}");page.wait_for_timeout(150)
   before=page.evaluate("()=>({seq:EInviteProfessionalEditor.commandSequence,left:document.querySelector('#stage .object[data-id=title]').style.left})")
   box=page.evaluate("()=>document.querySelector('#stage .object[data-id=title]').getBoundingClientRect().toJSON()")
   x=box['x']+min(30,box['width']/4);y=box['y']+min(30,box['height']/4)
   page.mouse.move(x,y);page.mouse.down()
   for step in range(1,61):page.mouse.move(x+step*1.7,y+step*.35)
   page.mouse.up();page.wait_for_timeout(450)
   after=page.evaluate("""()=>({seq:EInviteProfessionalEditor.commandSequence,left:document.querySelector('#stage .object[data-id=title]').style.left,stateLeft:EInviteEditorBridge.getState().objects.title.left,stateTop:EInviteEditorBridge.getState().objects.title.top,last:EInviteProfessionalEditor.lastCommand,inc:__inc,perf:EInvitePerformance.snapshot(),scheduler:EInviteInteractionScheduler.stats(),renderer:EInviteIncrementalRenderer.snapshot(),preview:document.querySelector('[data-id=title]').dataset.peTransformPreview||'',will:document.querySelector('[data-id=title]').style.willChange})""")
   assert after['seq']==before['seq']+1,(before,after)
   assert after['left']!=before['left'] and after['inc']>=1,(before,after)
   assert after['scheduler']['frameQueue']==0 and after['preview']=='' and after['will'] in ('auto',''),after
   assert after['perf']['metrics']['pointerLatency']['count']>=1,after
   assert after['renderer']['index']['items']>=4,after
   assert not errors,errors
  finally:browser.close()
 print('V22_1_EDITOR_INTERACTION_PERFORMANCE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
