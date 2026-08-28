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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':390,'height':844});errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(850)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  for name in ('studio-governance-v25.css','studio-operations-v26.css'):page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{localStorage.setItem('einvite-v25-studio-resources',JSON.stringify([{id:'brand-mobile',kind:'brand',name:'Mobile Brand',category:'Wedding',payload:{},governance:{},status:'approved',version:1}]));localStorage.setItem('einvite-v26-studio-releases',JSON.stringify([{id:'release-mobile',name:'Mobile Release',notes:'Mobile readiness',status:'active',manifest:[{id:'brand-mobile',kind:'brand',name:'Mobile Brand',version:1}],version:1,activatedAt:Date.now()}]));localStorage.setItem('einvite-v26-studio-release-pin',JSON.stringify({pin:{release_id:'release-mobile',release_version:1},release:{id:'release-mobile',name:'Mobile Release',status:'active',version:1}}));window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}}}""")
  page.add_script_tag(path=str(ROOT/'studio-governance-v25.js'));page.add_script_tag(path=str(ROOT/'studio-operations-v26.js'));page.wait_for_timeout(160)
  page.evaluate("()=>EInviteStudioOperations.open('releases')");page.wait_for_timeout(80)
  box=page.locator('.v26-operations-dialog').bounding_box();assert box and box['width']<=390.5 and box['x']>=-0.5,box
  overflow=page.evaluate("()=>document.documentElement.scrollWidth-document.documentElement.clientWidth");assert overflow<=1,overflow
  page.locator('.v26-operations-dialog [data-tab="deployment"]').click();page.wait_for_timeout(50)
  assert page.locator('.v26-native').is_visible() and page.locator('[data-project-backup]').is_visible()
  assert not errors,errors
  browser.close()
 print('V26_STUDIO_OPERATIONS_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
