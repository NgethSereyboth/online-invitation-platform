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
  page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
   page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  for name in ('asset-workflow-v23.css','photo-workflow-v23.css','photo-style-library-v23.css'):
   page.add_style_tag(path=str(ROOT/name))
  for name in ('asset-workflow-v23.js','photo-workflow-v23.js','photo-style-library-v23.js'):
   page.add_script_tag(path=str(ROOT/name))
  page.wait_for_timeout(360)
  page.evaluate("()=>{const image=document.querySelector('#stage .image-object');clearSelection();setSelection([image])}")
  page.wait_for_timeout(100)
  page.evaluate("()=>EInvitePhotoStyleLibrary.open()")
  page.wait_for_timeout(120)
  metrics=page.evaluate("""()=>{const d=document.querySelector('#v23PhotoStyleLibrary'),r=d.getBoundingClientRect(),toolbar=d.querySelector('.v23-photo-style-toolbar'),list=d.querySelector('.v23-photo-style-list'),footer=d.querySelector('footer');return{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height,toolbarColumns:getComputedStyle(toolbar).gridTemplateColumns,listColumns:getComputedStyle(list).gridTemplateColumns,footerBottom:footer.getBoundingClientRect().bottom,bodyOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth}}""")
  assert metrics['left']>=-1 and metrics['right']<=391,metrics
  assert metrics['bottom']<=845 and metrics['top']>=0,metrics
  assert metrics['bodyOverflow']<=1,metrics
  assert len(metrics['toolbarColumns'].split())==1,metrics
  assert len(metrics['listColumns'].split())==1,metrics
  assert metrics['footerBottom']<=845,metrics
  assert page.locator('#v23PhotoStyleLibrary [data-style-card]').count()==10
  # The mobile photo editor exposes a visible path into the reusable style library.
  page.locator('#v23PhotoStyleLibrary [data-close]').last.click();page.wait_for_timeout(80)
  page.evaluate("()=>EInviteCommandRegistry.execute('image.editPhoto')");page.wait_for_timeout(120)
  assert page.locator('#v23PhotoWorkflow').is_visible()
  styles_button=page.locator('#v23PhotoWorkflow [data-open-photo-styles]')
  assert styles_button.count()==1 and styles_button.is_visible()
  styles_button.click();page.wait_for_timeout(120)
  assert page.locator('#v23PhotoStyleLibrary').is_visible()
  assert page.locator('#v23PhotoStyleLibrary [data-photo-style-scope]').input_value()=='selection'
  assert not errors,errors
  browser.close()
 print('V23_6_PHOTO_STYLE_LIBRARY_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
