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
  for name in ('asset-workflow-v23.css','photo-workflow-v23.css','photo-style-library-v23.css'):
   page.add_style_tag(path=str(ROOT/name))
  for name in ('asset-workflow-v23.js','photo-workflow-v23.js','photo-style-library-v23.js'):
   page.add_script_tag(path=str(ROOT/name))
  page.wait_for_timeout(450)
  assert page.evaluate("()=>EInvitePhotoStyleLibrary?.version==='23.6.3'")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  image=page.locator('#stage .image-object').first
  assert image.count()==1
  page.evaluate("()=>{const image=document.querySelector('#stage .image-object');clearSelection();setSelection([image])}")
  page.wait_for_timeout(100)
  first_id=image.get_attribute('data-id')
  assert first_id
  # Save the selected treatment as a persistent custom style.
  page.evaluate("()=>EInviteCommandRegistry.execute('photoStyles.open')")
  page.wait_for_timeout(100)
  assert page.locator('#v23PhotoStyleLibrary').is_visible()
  assert page.locator('#v23PhotoStyleLibrary [data-style-card]').count()==10
  page.locator('#v23PhotoStyleLibrary [data-save-style] input[name=name]').fill('Boss Portrait')
  page.locator('#v23PhotoStyleLibrary [data-save-style] button').click()
  page.wait_for_timeout(120)
  assert page.evaluate("()=>EInvitePhotoStyleLibrary.customCount")==1
  assert page.locator('#v23PhotoStyleLibrary [data-style-card]').count()==11
  assert page.evaluate("()=>JSON.parse(localStorage.getItem('einvite-photo-styles-v23')).length")==1
  # Add a second image and select both for batch preview/application.
  second_id=page.evaluate("""()=>{const source=document.querySelector('#stage .image-object'),id='photo-style-second';const node=createObject(id,'image');const img=node.querySelector('img');img.src=source.querySelector('img').src;node.dataset.src=img.src;node.style.left='52%';node.style.top='58%';document.querySelector('#stage').append(node);EInviteEditorBridge.save();clearSelection();setSelection([source,node]);return id}""")
  page.wait_for_timeout(140)
  assert second_id=='photo-style-second'
  before=page.evaluate("ids=>Object.fromEntries(ids.map(id=>[id,{contrast:EInviteEditorBridge.getState().objects[id].imageContrast??100,temperature:EInviteEditorBridge.getState().objects[id].imageTemperature??0}]))",[first_id,second_id])
  page.locator('#v23PhotoStyleLibrary [data-photo-style-scope]').select_option('selection')
  page.locator('#v23PhotoStyleLibrary [data-style-card="builtin-celebration"] [data-preview-style]').click()
  page.wait_for_timeout(100)
  preview=page.evaluate("ids=>Object.fromEntries(ids.map(id=>[id,{dom:Number(document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`).dataset.imageContrast||100),doc:EInviteEditorBridge.getState().objects[id].imageContrast??100}]))",[first_id,second_id])
  assert all(preview[id]['dom']>before[id]['contrast'] for id in (first_id,second_id)),preview
  assert all(preview[id]['doc']==before[id]['contrast'] for id in (first_id,second_id)),preview
  page.locator('#v23PhotoStyleLibrary [data-cancel-preview]').click();page.wait_for_timeout(100)
  restored=page.evaluate("ids=>Object.fromEntries(ids.map(id=>[id,Number(document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`).dataset.imageContrast||100)]))",[first_id,second_id])
  assert all(restored[id]==before[id]['contrast'] for id in (first_id,second_id)),restored
  # Apply to both images in one transaction, then undo once to restore both.
  page.locator('#v23PhotoStyleLibrary [data-style-card="builtin-golden-hour"] [data-apply-style]').click();page.wait_for_timeout(180)
  applied=page.evaluate("ids=>Object.fromEntries(ids.map(id=>[id,EInviteEditorBridge.getState().objects[id].imageTemperature]))",[first_id,second_id])
  assert all(applied[id]>20 for id in (first_id,second_id)),applied
  page.evaluate("()=>EInviteEditorBridge.undo()");page.wait_for_timeout(180)
  undone=page.evaluate("ids=>Object.fromEntries(ids.map(id=>[id,EInviteEditorBridge.getState().objects[id].imageTemperature??0]))",[first_id,second_id])
  assert all(undone[id]==before[id]['temperature'] for id in (first_id,second_id)),undone
  page.evaluate("()=>EInviteEditorBridge.redo()");page.wait_for_timeout(180)
  assert page.evaluate("ids=>ids.every(id=>EInviteEditorBridge.getState().objects[id].imageTemperature>20)",[first_id,second_id])
  # Current-page scope operates as one batch and records style metadata.
  page.locator('#v23PhotoStyleLibrary [data-photo-style-scope]').select_option('page')
  page.locator('#v23PhotoStyleLibrary [data-style-card="builtin-mono"] [data-apply-style]').click();page.wait_for_timeout(180)
  page_result=page.evaluate("ids=>ids.map(id=>EInviteEditorBridge.getState().objects[id].imageGrayscale)",[first_id,second_id])
  assert all(value==100 for value in page_result),page_result
  # Library management and validated import use bounded custom data.
  custom_id=page.evaluate("()=>EInvitePhotoStyleLibrary.list().find(s=>!s.builtin).id")
  duplicate_id=page.evaluate("id=>EInvitePhotoStyleLibrary.duplicate(id).id",custom_id)
  assert page.evaluate("()=>EInvitePhotoStyleLibrary.customCount")==2
  assert page.evaluate("id=>EInvitePhotoStyleLibrary.rename(id,'Boss Portrait Revised')",duplicate_id)
  assert page.evaluate("id=>EInvitePhotoStyleLibrary.remove(id)",custom_id)
  imported=page.evaluate("""async()=>{const payload={schemaVersion:1,styles:[{name:'Imported Soft',description:'Imported test',look:{imageBrightness:111,imageContrast:91,imageTemperature:9}}]};return EInvitePhotoStyleLibrary.import(new File([JSON.stringify(payload)],'styles.json',{type:'application/json'}))}""")
  assert imported==1
  assert page.evaluate("()=>EInvitePhotoStyleLibrary.customCount")==2
  assert page.locator('#v23ContextToolbar button[data-command-id="photoStyles.open"]').count()==1
  assert page.locator('.studio-statusbar [data-command-id="photoStyles.open"]').count()==1
  assert not errors,errors
  browser.close()
 print('V23_6_PHOTO_STYLE_LIBRARY_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
