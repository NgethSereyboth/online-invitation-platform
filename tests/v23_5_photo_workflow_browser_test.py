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
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
   page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  page.add_style_tag(path=str(ROOT/'asset-workflow-v23.css'))
  page.add_script_tag(path=str(ROOT/'asset-workflow-v23.js'))
  page.add_style_tag(path=str(ROOT/'photo-workflow-v23.css'))
  page.add_script_tag(path=str(ROOT/'photo-workflow-v23.js'))
  page.wait_for_timeout(400)
  assert page.evaluate("()=>EInvitePhotoWorkflow?.version==='23.5.3'")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  assert page.locator('#v23ContextToolbar').count()==1
  page.evaluate("""()=>{const image=document.querySelector('#stage .image-object');clearSelection();setSelection([image])}""")
  page.wait_for_timeout(120)
  image_id=page.locator('#stage .image-object.selected,#stage .image-object.multi-selected').first.get_attribute('data-id')
  assert image_id
  original=page.evaluate("id=>({brightness:EInviteEditorBridge.getState().objects[id].imageBrightness??100,contrast:EInviteEditorBridge.getState().objects[id].imageContrast??100})",image_id)
  assert page.locator('#v23ContextToolbar').get_by_text('Edit photo',exact=True).count()==1
  page.locator('#v23ContextToolbar').get_by_text('Edit photo',exact=True).click()
  page.wait_for_timeout(120)
  assert page.locator('#v23PhotoWorkflow').is_visible()
  assert page.locator('#v23PhotoWorkflow [data-photo-preset]').count()==10
  # Preview changes only the DOM; document state remains untouched until Apply.
  page.locator('#v23PhotoWorkflow [data-photo-preset="celebration"]').click()
  page.wait_for_timeout(80)
  preview=page.evaluate("id=>({dom:Number(document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`).dataset.imageContrast),doc:EInviteEditorBridge.getState().objects[id].imageContrast??100})",image_id)
  assert preview['dom']>original['contrast'],preview
  assert preview['doc']==original['contrast'],preview
  page.locator('#v23PhotoWorkflow [data-close]').last.click()
  page.wait_for_timeout(100)
  cancelled=page.evaluate("id=>({dom:Number(document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`).dataset.imageContrast||100),doc:EInviteEditorBridge.getState().objects[id].imageContrast??100})",image_id)
  assert cancelled['dom']==original['contrast'] and cancelled['doc']==original['contrast'],cancelled
  # Apply creates one committed document action and persists adjustment/crop data.
  page.evaluate("()=>EInviteCommandRegistry.execute('image.editPhoto')")
  page.wait_for_timeout(80)
  page.locator('#v23PhotoWorkflow [data-photo-preset="golden-hour"]').click()
  page.locator('#v23PhotoWorkflow [data-photo-key="imagePositionX"]').fill('67')
  page.locator('#v23PhotoWorkflow [data-photo-key="imagePositionY"]').fill('38')
  page.locator('#v23PhotoWorkflow [data-photo-select="imageFrame"]').select_option('gold')
  page.locator('#v23PhotoWorkflow [data-photo-select="imageMask"]').select_option('arch')
  page.locator('#v23PhotoWorkflow [data-compare]').dispatch_event('pointerdown')
  assert page.locator('#v23PhotoWorkflow [data-preview-label]').inner_text()=='Before this edit'
  page.locator('#v23PhotoWorkflow [data-compare]').dispatch_event('pointerup')
  page.locator('#v23PhotoWorkflow [data-apply]').click()
  page.wait_for_timeout(180)
  applied=page.evaluate("id=>{const o=EInviteEditorBridge.getState().objects[id];return{temperature:o.imageTemperature,x:o.imagePositionX,y:o.imagePositionY,frame:o.imageFrame,mask:o.imageMask,ops:o.imageEditOperations}}",image_id)
  assert applied['temperature']>20 and applied['x']==67 and applied['y']==38,applied
  assert applied['frame']=='gold' and applied['mask']=='arch',applied
  assert isinstance(applied['ops'],list) and len(applied['ops'])>=3,applied
  # One undo returns the whole session, proving previews did not flood history.
  page.evaluate("()=>EInviteEditorBridge.undo()")
  page.wait_for_timeout(180)
  undone=page.evaluate("id=>{const o=EInviteEditorBridge.getState().objects[id];return{contrast:o.imageContrast??100,x:o.imagePositionX??50,frame:o.imageFrame??'none'}}",image_id)
  assert undone['contrast']==original['contrast'] and undone['x']==50 and undone['frame']=='none',undone
  page.evaluate("()=>EInviteEditorBridge.redo()")
  page.wait_for_timeout(180)
  assert page.evaluate("id=>EInviteEditorBridge.getState().objects[id].imageFrame==='gold'",image_id)
  # Reusable look commands are authoritative and remain conflict free.
  assert page.evaluate("()=>EInviteCommandRegistry.execute('image.copyLook')")
  assert page.evaluate("()=>EInvitePhotoWorkflow.hasCopiedLook")
  assert page.evaluate("()=>EInviteCommandRegistry.execute('image.resetAdjustments')")
  page.wait_for_timeout(120)
  assert page.evaluate("id=>(EInviteEditorBridge.getState().objects[id].imageTemperature??0)===0",image_id)
  assert page.evaluate("()=>EInviteCommandRegistry.execute('image.pasteLook')")
  page.wait_for_timeout(120)
  assert page.evaluate("id=>EInviteEditorBridge.getState().objects[id].imageTemperature>20",image_id)
  assert page.locator('#openPhotoEditor').get_attribute('data-command-id')=='image.editPhoto'
  assert not errors,errors
  browser.close()
 print('V23_5_PHOTO_WORKFLOW_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
