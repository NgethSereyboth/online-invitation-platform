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
  for css in ['page-experience-v22.css','professional-workflow-v23.css','navigation-history-v23.css']:page.add_style_tag(path=str(ROOT/css))
  for js in ['page-experience-v22.js','professional-workflow-v23.js','navigation-history-v23.js']:page.add_script_tag(path=str(ROOT/js))
  page.wait_for_timeout(350)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  assert page.evaluate("()=>EInviteNavigationHistory?.version===23.2")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length") == 0
  # Selection mode and overlapping selection commands are centrally registered.
  original=page.evaluate("()=>EInviteNavigationHistory.selection.mode")
  page.evaluate("()=>EInviteCommandRegistry.execute('selection.targetMode')")
  assert page.evaluate("m=>EInviteNavigationHistory.selection.mode!==m",original)
  # Ensure page manager exists with three keyed views.
  page.evaluate("()=>{const d=EInviteEditorBridge.getState();d.designPages=d.designPages||[];if(!d.designPages.length)d.designPages.push({id:'v23-page-a',name:'Page A',enabled:true,objects:{a:{type:'text',text:'A',left:'10%',top:'10%',width:'30%',height:'10%',zIndex:1}}});EInviteEditorSchema.syncLegacy(d);EInviteEditorBridge.render();EInvitePageExperience?.render?.({force:true})}")
  page.wait_for_timeout(250)
  assert page.locator('.v23-page-tools').count()==1
  for mode in ['list','thumbs','grid']:
   page.evaluate("m=>EInviteNavigationHistory.pages.setView(m)",mode)
   assert page.locator('.v22-page-manager').get_attribute('data-page-view')==mode
  # Copy and paste a complete page through IndexedDB with remapped ids.
  page.evaluate("()=>document.querySelector('[data-page-id=\"v23-page-a\"]')?.click()")
  before=page.evaluate("()=>EInviteEditorBridge.getState().designPages.length")
  page.evaluate("()=>EInviteNavigationHistory.pages.copy()")
  page.wait_for_timeout(120)
  page.evaluate("()=>EInviteNavigationHistory.pages.paste()")
  page.wait_for_timeout(250)
  after=page.evaluate("()=>EInviteEditorBridge.getState().designPages.length")
  assert after==before+1,(before,after)
  assert page.evaluate("()=>{const ps=EInviteEditorBridge.getState().designPages;const a=ps.at(-1);return a&&a.id!=='v23-page-a'&&Object.keys(a.objects||{})[0]!=='a'}")
  # Checkpoint creation rejects duplicates and restores a changed draft.
  page.evaluate("()=>EInviteNavigationHistory.checkpoints.create('Before change')")
  page.wait_for_timeout(150)
  records=page.evaluate("()=>EInviteNavigationHistory.checkpoints.list()")
  assert len(records)>=1
  name_before=page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].name")
  page.evaluate("()=>EInviteEditorBridge.transact('Rename for checkpoint test',d=>d.designPages[0].name='Changed',{capture:false})")
  record=page.evaluate("()=>EInviteNavigationHistory.checkpoints.list().then(x=>x[0])")
  page.evaluate("r=>EInviteEditorBridge.replaceState(r.document,{reason:'test restore'})",record)
  assert page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].name")==name_before
  assert not errors,errors
  browser.close()
 print('V23_2_NAVIGATION_HISTORY_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
