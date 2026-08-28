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
  page.add_script_tag(path=str(ROOT/'photo-workflow-v23.js'))
  page.add_script_tag(path=str(ROOT/'photo-style-library-v23.js'))
  page.wait_for_timeout(220)
  page.evaluate("()=>{const image=document.querySelector('#stage .image-object');clearSelection();setSelection([image])}")
  start=page.evaluate('performance.now()')
  page.evaluate("()=>EInvitePhotoStyleLibrary.open()")
  opened=page.evaluate('(s)=>performance.now()-s',start)
  assert opened<350,opened
  assert page.locator('#v23PhotoStyleLibrary [data-style-card]').count()==10
  # Populate the bounded maximum and verify rendering/search remain responsive.
  seed_start=page.evaluate('performance.now()')
  page.evaluate("""()=>{for(let i=0;i<36;i++){const o=EInviteEditorBridge.getState().objects[EInviteEditorBridge.getSelectedIds()[0]];o.imageBrightness=80+(i%40);EInvitePhotoStyleLibrary.saveSelected(`Style ${i+1}`)}}""")
  seed_ms=page.evaluate('(s)=>performance.now()-s',seed_start)
  assert page.evaluate("()=>EInvitePhotoStyleLibrary.customCount")==36
  render_start=page.evaluate('performance.now()')
  page.locator('#v23PhotoStyleLibrary [data-photo-style-search]').fill('Style 3')
  page.wait_for_timeout(30)
  search_ms=page.evaluate('(s)=>performance.now()-s',render_start)
  assert search_ms<500,search_ms
  assert page.locator('#v23PhotoStyleLibrary [data-style-card]').count()>=8
  assert page.evaluate("()=>new Blob([localStorage.getItem('einvite-photo-styles-v23')]).size<900000")
  # Repeated opens reuse one dialog and one command registration.
  page.locator('#v23PhotoStyleLibrary [data-close]').last.click();page.wait_for_timeout(50)
  for _ in range(3):
   page.evaluate("()=>EInvitePhotoStyleLibrary.open()");page.wait_for_timeout(30);page.locator('#v23PhotoStyleLibrary [data-close]').last.click();page.wait_for_timeout(30)
  assert page.locator('#v23PhotoStyleLibrary').count()==1
  assert page.evaluate("()=>EInviteCommandRegistry.list().filter(c=>c.id==='photoStyles.open').length")==1
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  assert not errors,errors
  browser.close()
 print('V23_6_PHOTO_STYLE_LIBRARY_PERFORMANCE_TEST_PASSED',{'openMs':round(opened,2),'seed36Ms':round(seed_ms,2),'searchMs':round(search_ms,2)});return 0
if __name__=='__main__':sys.exit(main())
