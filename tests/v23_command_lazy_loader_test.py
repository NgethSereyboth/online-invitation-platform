#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V23_COMMAND_LAZY_LOADER',exc)
 core=(ROOT/'editor-command-system-v23.js').read_text(encoding='utf-8')
 ui=(ROOT/'command-palette-v23.js').read_text(encoding='utf-8')
 css=(ROOT/'command-palette-v23.css').read_text(encoding='utf-8')
 requests={'js':0,'css':0}
 html=f"""<!doctype html><html><head><base href='http://einvite.test/'><meta charset='utf-8'></head><body><div id='stage'><div class='object' data-id='layer-1'></div></div><select id='zoomLevel'><option value='1'>100%</option></select><script>
 const __s=new Map();const localStorage={{getItem:k=>__s.has(String(k))?__s.get(String(k)):null,setItem:(k,v)=>__s.set(String(k),String(v)),removeItem:k=>__s.delete(String(k))}};
 window.EInviteEditorBridge={{getState:()=>({{objects:{{'layer-1':{{id:'layer-1',name:'Ceremony title',type:'text'}}}},designPages:[{{id:'page-1',name:'Ceremony page',objects:{{}}}}]}}),getSelectedIds:()=>[],getActiveCanvasId:()=> 'hero',select:ids=>window.__selection=ids}};
 window.EInviteWorkflow={{navigate:(to)=>window.__pane=to}};window.assetStore={{list:async()=>[{{id:'asset-1',name:'Lotus photograph',type:'image/png'}}]}};window.switchCanvas=id=>window.__canvas=id;
 {core}
 </script></body></html>"""
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V23_COMMAND_LAZY_LOADER',exc)
  try:
   page=browser.new_page(viewport={'width':1100,'height':760});errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   def serve_js(route):requests['js']+=1;route.fulfill(status=200,content_type='application/javascript',body=ui)
   def serve_css(route):requests['css']+=1;route.fulfill(status=200,content_type='text/css',body=css)
   page.route('http://einvite.test/command-palette-v23.js',serve_js)
   page.route('http://einvite.test/command-palette-v23.css',serve_css)
   page.set_content(html,wait_until='load')
   assert page.locator('.v23-command-surface').count()==0
   page.keyboard.press('Control+K')
   page.locator('.v23-command-surface').wait_for(state='visible')
   assert requests=={'js':1,'css':1},requests
   page.locator('.v23-command-search input').fill('Ceremony page')
   page.wait_for_function("()=>[...document.querySelectorAll('.v23-command-row small')].some(x=>x.textContent.includes('Open design page'))")
   page.locator('.v23-command-row').filter(has_text='Ceremony page').click();page.wait_for_timeout(60)
   assert page.evaluate('()=>window.__canvas')=='page:page-1'
   page.keyboard.press('Control+K');page.locator('.v23-command-surface').wait_for(state='visible')
   page.keyboard.press('Escape');page.wait_for_timeout(30)
   assert requests=={'js':1,'css':1},requests
   assert not errors,errors
  finally:browser.close()
 print('V23_COMMAND_LAZY_LOADER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
