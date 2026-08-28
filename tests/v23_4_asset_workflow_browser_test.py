#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
PNG='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII='
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  page.evaluate("""([a,b,c])=>{window.listAllAssets=async()=>[
   {id:'asset-a',name:'Wedding Flowers',type:'image/png',serverUrl:a,favorite:true,folder:'Wedding',tags:['floral'],width:300,height:200},
   {id:'asset-b',name:'Khmer Pattern',type:'image/png',serverUrl:b,folder:'Decor',tags:['khmer'],width:300,height:200},
   {id:'asset-c',name:'Portrait Photo',type:'image/png',serverUrl:c,folder:'People',tags:['portrait'],width:300,height:200}
  ];window.usableAssetUrl=async a=>a.serverUrl}""",[PNG,PNG,PNG])
  page.add_style_tag(path=str(ROOT/'asset-workflow-v23.css'))
  page.add_script_tag(path=str(ROOT/'asset-workflow-v23.js'))
  page.wait_for_timeout(350)
  assert page.evaluate("()=>EInviteAssetWorkflow?.version===23.4")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  assert page.locator('#v23ContextToolbar').count()==1
  # Open, search, and insert an asset.
  page.evaluate("()=>EInviteAssetWorkflow.open({title:'Image assets',mode:'insert'})")
  page.wait_for_timeout(250)
  assert page.locator('#v23AssetBrowser').is_visible()
  assert page.locator('.v23-asset-card').count()==3
  page.locator('#v23AssetBrowser [data-search]').fill('Khmer')
  page.wait_for_timeout(180)
  assert page.locator('.v23-asset-card').count()==1
  page.locator('.v23-asset-card').click()
  page.locator('#v23AssetBrowser [data-apply]').click()
  page.wait_for_timeout(250)
  ids=page.evaluate("()=>EInviteEditorBridge.getSelectedIds()")
  assert len(ids)==1
  inserted=ids[0]
  assert page.evaluate("id=>EInviteEditorBridge.getState().objects[id]?.src?.startsWith('data:image/png')",inserted)
  # Context bar is now image-specific and replacement uses the same browser.
  assert page.locator('#v23ContextToolbar').get_by_text('Replace').count()==1
  page.evaluate("()=>EInviteAssetWorkflow.open({title:'Replace selected',mode:'replace'})")
  page.wait_for_timeout(180)
  page.locator('.v23-asset-card[data-asset-id="asset-c"]').click()
  page.locator('#v23AssetBrowser [data-apply]').click()
  page.wait_for_timeout(220)
  assert page.evaluate("id=>EInviteEditorBridge.getState().objects[id].assetId==='asset-c'",inserted)
  # Existing picker compatibility remains supported.
  page.evaluate("()=>openMaterialPicker('Compatibility picker',(url,asset)=>{window.__picked={url,id:asset.id}})")
  page.wait_for_timeout(160)
  page.locator('.v23-asset-card[data-asset-id="asset-a"]').dblclick()
  page.wait_for_timeout(140)
  assert page.evaluate("()=>window.__picked.id==='asset-a'")
  # Direct file insertion works in restricted/local mode.
  page.evaluate("""()=>{const bytes=new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>');window.__dropFile=new File([bytes],'drop.svg',{type:'image/png'})}""")
  before=page.locator('#stage .image-object').count()
  page.evaluate("()=>EInviteAssetWorkflow.upload([window.__dropFile],{point:{x:500,y:500}})")
  page.wait_for_timeout(350)
  assert page.locator('#stage .image-object').count()==before+1
  assert page.locator('.v23-activity-host').count()==1
  assert not errors,errors
  browser.close()
 print('V23_4_ASSET_WORKFLOW_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
