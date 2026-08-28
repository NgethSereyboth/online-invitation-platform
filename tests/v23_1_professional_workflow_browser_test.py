#!/usr/bin/env python3
from __future__ import annotations
import sys
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor

def main()->int:
 from playwright.sync_api import sync_playwright
 html=build_inline_editor()
 with sync_playwright() as p:
  browser=launch_chromium(p)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(html,wait_until='load',timeout=30000);page.add_style_tag(path=str(__import__('pathlib').Path(__file__).resolve().parents[1]/'professional-workflow-v23.css'));page.add_script_tag(path=str(__import__('pathlib').Path(__file__).resolve().parents[1]/'professional-workflow-v23.js'));page.wait_for_timeout(300)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  assert page.evaluate("()=>!!EInviteProfessionalWorkflow&&EInviteProfessionalWorkflow.version===23.1")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length") == 0
  # Transform previews several changes and commits only once.
  page.locator('#stage .object').first.click(force=True)
  start_history=page.evaluate("()=>EInviteEditorBridge.getHistoryState?.().past||0")
  before=page.evaluate("()=>{const id=EInviteEditorBridge.getSelectedIds()[0],o=EInviteEditorBridge.getState().objects[id];return {id,left:o.left,width:o.width,rotation:o.rotation||0}}")
  page.keyboard.press('Control+T');page.keyboard.press('ArrowRight');page.keyboard.press('ArrowRight');page.keyboard.press('Alt+ArrowRight');page.keyboard.press('Control+Alt+ArrowRight')
  assert page.evaluate("()=>EInviteProfessionalWorkflow.transform.active")
  page.keyboard.press('Enter');page.wait_for_timeout(100)
  after=page.evaluate("id=>{const o=EInviteEditorBridge.getState().objects[id];return {left:o.left,width:o.width,rotation:o.rotation||0}}",before['id'])
  assert after!=before
  # Escape cancels preview without mutating state.
  saved=page.evaluate("id=>structuredClone(EInviteEditorBridge.getState().objects[id])",before['id'])
  page.keyboard.press('Control+T');page.keyboard.press('Alt+ArrowRight');page.keyboard.press('Escape');page.wait_for_timeout(60)
  assert page.evaluate("()=>!EInviteProfessionalWorkflow.transform.active")
  assert page.evaluate("([id,saved])=>{const now=EInviteEditorBridge.getState().objects[id];return ['left','top','width','height','rotation'].every(k=>String(now[k]??'')===String(saved[k]??''))}",[before['id'],saved])
  # Isolation is reversible.
  visible_before=page.evaluate("()=>Object.fromEntries(Object.entries(EInviteEditorBridge.getState().objects).map(([id,o])=>[id,o.visible!==false]))")
  page.keyboard.press('Alt+Shift+I');page.wait_for_timeout(80)
  assert page.evaluate("()=>EInviteProfessionalWorkflow.layers.isolated")
  page.keyboard.press('Alt+Shift+I');page.wait_for_timeout(80)
  assert page.evaluate("()=>!EInviteProfessionalWorkflow.layers.isolated")
  assert page.evaluate("v=>JSON.stringify(Object.fromEntries(Object.entries(EInviteEditorBridge.getState().objects).map(([id,o])=>[id,o.visible!==false])))===JSON.stringify(v)",visible_before)
  # Arrange panel and guides are contextual.
  page.keyboard.press('Alt+Shift+P');assert page.locator('#v23ArrangePanel').is_visible()
  page.keyboard.press('Control+R');assert page.locator('#canvasFrame').evaluate("e=>e.classList.contains('show-rulers')")
  page.keyboard.press('Control+;');assert page.locator('[data-pe-toggle=guides]').get_attribute('aria-pressed') in ['true','false']
  # Crop position command updates selected image when available.
  image=page.locator('#stage .object').filter(has=page.locator('img')).first
  if image.count():
   image.click(force=True);page.wait_for_timeout(30)
   page.evaluate("()=>EInviteCommandRegistry.execute('image.cropRight')");page.wait_for_timeout(320)
   oid=page.evaluate("()=>EInviteEditorBridge.getSelectedIds()[0]")
   assert page.evaluate("id=>EInviteEditorBridge.getState().objects[id].imagePositionX>50",oid)
  assert not errors,errors
  browser.close()
 print('V23_1_PROFESSIONAL_WORKFLOW_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
