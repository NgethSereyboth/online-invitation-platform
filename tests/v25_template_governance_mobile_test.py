#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
BASE_CSS=['direct-manipulation-v24.css','content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']
BASE_JS=['direct-manipulation-v24.js','content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
CSS=BASE_CSS+['adaptive-templates-v25.css','studio-governance-v25.css','print-readiness-v25.css','template-bindings-v25.css']
JS=BASE_JS+['adaptive-templates-v25.js','studio-governance-v25.js','print-readiness-v25.js','template-bindings-v25.js']
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':390,'height':844});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(900)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  for name in CSS:page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{localStorage.setItem('einvite-v25-studio-resources',JSON.stringify([{id:'mobile-brand',kind:'brand',name:'Mobile Brand',category:'Government',payload:{primary:'#183a64',accent:'#b18a3b',background:'#f7f8fb',surface:'#ffffff',text:'#18202d',headingPair:'serif-formal',bodyPair:'sans-modern'},governance:{locked:false,allowedOverrides:['content']},status:'approved',version:1,createdAt:Date.now(),updatedAt:Date.now()}]));window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}}}""")
  for name in JS:page.add_script_tag(path=str(ROOT/name));page.wait_for_timeout(45)
  page.evaluate("()=>EInviteAdaptiveTemplates.apply('government-delegation')");page.wait_for_timeout(90)
  surfaces=[
   ("()=>EInviteAdaptiveTemplates.open()",'.v25-template-dialog'),
   ("()=>EInviteStudioGovernance.open()",'.v25-governance-dialog'),
   ("()=>EInvitePrintReadiness.open()",'.v25-print-dialog'),
   ("()=>EInviteTemplateBindings.open()",'.v25-binding-dialog')]
  for command,selector in surfaces:
   page.evaluate(command);page.wait_for_timeout(130)
   locator=page.locator(selector);assert locator.is_visible(),selector
   box=locator.bounding_box();assert box,selector
   assert box['x']>=-1 and box['x']+box['width']<=391,(selector,box)
   assert box['y']>=-1 and box['y']+box['height']<=845,(selector,box)
   assert page.evaluate("()=>document.documentElement.scrollWidth<=window.innerWidth+1"),selector
   locator.locator('[data-close]').first.click();page.wait_for_timeout(35)
  assert page.locator('.studio-statusbar [data-v25-governance-launch]').count()<=1
  assert page.locator('.studio-statusbar [data-v25-print-launch]').count()<=1
  assert page.locator('.studio-statusbar [data-v25-bindings-launch]').count()<=1
  assert not errors,errors
  browser.close()
 print('V25_TEMPLATE_GOVERNANCE_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
