#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
CSS=['direct-manipulation-v24.css','content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']
JS=['direct-manipulation-v24.js','content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':390,'height':844});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(900)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  for name in CSS:page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{window.EInviteReviewWorkflow={comments:[],approvals:[],context:{reviewers:[],readiness:{ready:true,blockers:[]}},refresh:async()=>true,open:()=>true};window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}}}""")
  for name in JS:page.add_script_tag(path=str(ROOT/name));page.wait_for_timeout(40)
  surfaces=[
   ("()=>EInviteContentBrowser.open('elements')",'#v24ContentBrowser'),
   ("()=>EInviteSmartLayout.open()",'#v24LayoutDialog'),
   ("()=>EInviteBrandComponents.open('brand')",'#v24BrandDialog'),
   ("()=>EInviteCollaborationCenter.open('summary')",'#v24CollaborationDialog'),
   ("()=>EInviteExportQuality.open('quality')",'#v24QualityDialog')]
  for command,selector in surfaces:
   page.evaluate(command);page.wait_for_timeout(120)
   box=page.locator(selector).bounding_box();assert box,selector
   assert box['x']>=-1 and box['x']+box['width']<=391,(selector,box)
   assert box['y']>=-1 and box['y']+box['height']<=845,(selector,box)
   assert page.evaluate("()=>document.documentElement.scrollWidth<=window.innerWidth+1"),selector
   page.locator(f'{selector} [data-close]').first.click();page.wait_for_timeout(30)
  # The accessibility editor is also contained on mobile.
  image_id=page.evaluate("()=>{const e=Object.entries(EInviteEditorBridge.getState().objects).find(([,o])=>o.type==='image'||o.src);EInviteEditorBridge.select(e?[e[0]]:[]);return e?.[0]||''}")
  if image_id:
   assert page.evaluate("()=>EInviteCommandRegistry.execute('accessibility.editAltText')")
   box=page.locator('#v24AltTextDialog').bounding_box();assert box and box['x']>=-1 and box['x']+box['width']<=391,box
   page.locator('#v24AltTextDialog [data-alt-cancel]').first.click()
  assert not errors,errors
  browser.close()
 print('V24_CANVA_EXPERIENCE_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
