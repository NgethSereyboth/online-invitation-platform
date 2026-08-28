#!/usr/bin/env python3
"""Mobile canvas navigation occupies reserved workspace chrome and never intersects invitation objects."""
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
SIZES=[(360,800),(390,844),(430,932)]
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_MOBILE_CANVAS_HUD',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_MOBILE_CANVAS_HUD',exc)
  page=browser.new_page();ready(page,390,844)
  page.add_style_tag(content=(Path(__file__).resolve().parents[1]/'workspace-experience-v24.css').read_text(encoding='utf-8'))
  page.add_script_tag(content=(Path(__file__).resolve().parents[1]/'workspace-experience-v24.js').read_text(encoding='utf-8'));page.wait_for_function('()=>window.EInviteWorkspaceExperience&&document.querySelector("#v24CanvasHud")')
  for width,height in SIZES:
   page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(200);page.evaluate("()=>EInviteEditorBridge.select(['details'])")
   info=page.evaluate("""()=>{const hud=document.querySelector('#v24CanvasHud'),stage=document.querySelector('#stage'),objects=[...stage.querySelectorAll('.object')],h=hud.getBoundingClientRect(),s=stage.getBoundingClientRect(),intersections=objects.map(o=>{const r=o.getBoundingClientRect(),w=Math.max(0,Math.min(h.right,r.right)-Math.max(h.left,r.left)),v=Math.max(0,Math.min(h.bottom,r.bottom)-Math.max(h.top,r.top));return{id:o.dataset.id,area:w*v}});return{hud:{top:h.top,bottom:h.bottom,left:h.left,right:h.right,position:getComputedStyle(hud).position},stage:{top:s.top,bottom:s.bottom},intersections,overflow:document.documentElement.scrollWidth-innerWidth,targets:[...hud.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>{const r=b.getBoundingClientRect();return[r.width,r.height]})}}""")
   assert info['hud']['position']=='relative' and info['hud']['top']>=info['stage']['bottom']-0.5,(width,info)
   assert max(x['area'] for x in info['intersections'])==0,(width,info)
   assert info['overflow']<=0.5 and all(w>=31 and h>=31 for w,h in info['targets']),(width,info)
  browser.close()
 print('V27_3_5_MOBILE_CANVAS_HUD_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
