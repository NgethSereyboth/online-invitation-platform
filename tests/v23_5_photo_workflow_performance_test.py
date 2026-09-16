#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
   page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  page.add_script_tag(path=str(ROOT/'photo-workflow-v23.js'));page.wait_for_timeout(180)
  page.evaluate("""()=>{const image=document.querySelector('#stage .image-object');clearSelection();setSelection([image])}""")
  page.wait_for_timeout(80)
  image_id=page.locator('#stage .image-object.selected').get_attribute('data-id')
  before=page.evaluate("id=>JSON.stringify(EInviteEditorBridge.getState().objects[id])",image_id)
  start=page.evaluate('performance.now()')
  page.evaluate("()=>EInvitePhotoWorkflow.open()")
  opened=page.evaluate('(s)=>performance.now()-s',start)
  assert opened<350,opened
  assert page.locator('#v23PhotoWorkflow [data-photo-preset]').count()==10
  # Repeated slider previews remain DOM-only and responsive.
  preview_start=page.evaluate('performance.now()')
  page.evaluate("""()=>{const input=document.querySelector('#v23PhotoWorkflow [data-photo-key="imageBrightness"]');for(let i=0;i<120;i++){input.value=String(80+(i%60));input.dispatchEvent(new Event('input',{bubbles:true}))}}""")
  preview_ms=page.evaluate('(s)=>performance.now()-s',preview_start)
  assert preview_ms<1200,preview_ms
  current=page.evaluate("id=>JSON.stringify(EInviteEditorBridge.getState().objects[id])",image_id)
  assert current==before,'preview mutated document state'
  page.locator('#v23PhotoWorkflow [data-apply]').click();page.wait_for_timeout(150)
  assert page.locator('#v23PhotoWorkflow').count()==1
  # Repeated opens reuse one dialog and do not duplicate command registration.
  for _ in range(3):
   page.evaluate("()=>EInvitePhotoWorkflow.open()");page.wait_for_timeout(30);page.locator('#v23PhotoWorkflow [data-close]').last.click();page.wait_for_timeout(30)
  assert page.locator('#v23PhotoWorkflow').count()==1
  assert page.evaluate("()=>EInviteCommandRegistry.list().filter(c=>c.id==='image.editPhoto').length")==1
  assert not errors,errors
  browser.close()
 print('V23_5_PHOTO_WORKFLOW_PERFORMANCE_TEST_PASSED',{'openMs':round(opened,2),'preview120Ms':round(preview_ms,2)});return 0
if __name__=='__main__':sys.exit(main())
