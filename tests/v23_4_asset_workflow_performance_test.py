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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000})
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  page.evaluate("""p=>{window.__assetReads=0;window.__largeAssets=Array.from({length:1500},(_,i)=>({id:`asset-${i}`,name:`Asset ${i}`,type:'image/png',serverUrl:p,folder:i%2?'Wedding':'Decor',favorite:i%17===0,width:300,height:200}));window.listAllAssets=async()=>{window.__assetReads++;return window.__largeAssets};window.usableAssetUrl=async a=>a.serverUrl}""",PNG)
  page.add_script_tag(path=str(ROOT/'asset-workflow-v23.js'));page.wait_for_timeout(220)
  result=page.evaluate("""async()=>{const a=performance.now();await EInviteAssetWorkflow.open({mode:'insert'});const b=performance.now();return{openMs:b-a,cards:document.querySelectorAll('.v23-asset-card').length,reads:window.__assetReads}}""")
  assert result['cards']==120,result
  assert result['openMs']<700,result
  page.locator('[data-load-more]').click();page.wait_for_timeout(80)
  assert page.locator('.v23-asset-card').count()==240
  page.locator('#v23AssetBrowser [data-close]').first.click();page.wait_for_timeout(70)
  page.evaluate("()=>EInviteAssetWorkflow.open({mode:'insert'})");page.wait_for_timeout(120)
  assert page.evaluate("()=>window.__assetReads")==1
  start=page.evaluate('performance.now()');page.locator('#v23AssetBrowser [data-search]').fill('Asset 1499');page.wait_for_timeout(150);elapsed=page.evaluate('(s)=>performance.now()-s',start)
  assert page.locator('.v23-asset-card').count()==1
  assert elapsed<450,elapsed
  # Pointer drag from the modal closes it and places the asset on the canvas.
  page.locator('#v23AssetBrowser [data-search]').fill('Asset 1');page.wait_for_timeout(130)
  card=page.locator('.v23-asset-card').first.bounding_box();stage=page.locator('#stage').bounding_box();before=page.locator('#stage .image-object').count()
  page.mouse.move(card['x']+20,card['y']+20);page.mouse.down();page.mouse.move(stage['x']+stage['width']*.7,stage['y']+stage['height']*.45,steps=8);page.mouse.up();page.wait_for_timeout(300)
  assert not page.locator('#v23AssetBrowser').is_visible()
  assert page.locator('#stage .image-object').count()==before+1
  browser.close()
 print('V23_4_ASSET_WORKFLOW_PERFORMANCE_TEST_PASSED',result);return 0
if __name__=='__main__':sys.exit(main())
