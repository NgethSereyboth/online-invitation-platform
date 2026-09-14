#!/usr/bin/env python3
"""Isolated mobile selection, hit-target, resize, and rotation coverage."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v17_professional_editor_test import build,boot,box,click_center,drag_handle

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V17_PROFESSIONAL_EDITOR_MOBILE',exc)
 html=build();errors=[]
 with sync_playwright() as p:
  for width_px,height_px in ((360,800),(390,844),(430,932)):
   try:browser=launch_chromium(p)
   except Exception as exc:return skipped('V17_PROFESSIONAL_EDITOR_MOBILE',exc)
   page=browser.new_page(viewport={'width':width_px,'height':height_px});page.set_default_timeout(20_000)
   page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None);boot(page,html)
   page.evaluate("()=>{window.__v17Baseline=EInviteEditorBridge.cloneState();EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(220);click_center(page,'#stage .object[data-id="details"]');page.wait_for_timeout(180)
   mobile=page.evaluate("""()=>{const stage=document.querySelector('.stage-wrap'),right=document.querySelector('aside.right'),toolbar=document.querySelector('#peMobileContextBar');const handles=[...document.querySelectorAll('[data-pe-handle]')].map(el=>{const r=el.getBoundingClientRect();return {w:r.width,h:r.height}});const tr=toolbar?.getBoundingClientRect();return{scroll:document.documentElement.scrollWidth,w:innerWidth,mode:document.body.dataset.mobileEditorMode,inspector:document.body.classList.contains('mobile-inspector-open'),rightHidden:right?.getAttribute('aria-hidden'),stageVisible:!!stage&&getComputedStyle(stage).display!=='none'&&!stage.hidden,toolbarVisible:!!toolbar&&!toolbar.hidden&&tr.width>0&&tr.height>0,toolbarHeight:tr?.height||0,handles}}""")
   assert mobile['scroll']<=mobile['w']+1 and mobile['mode']=='canvas' and not mobile['inspector'] and mobile['rightHidden']=='true' and mobile['stageVisible'],(width_px,height_px,mobile);assert mobile['toolbarVisible'] and mobile['toolbarHeight']<=90,(width_px,height_px,mobile);assert len(mobile['handles'])==9 and all(item['w']>=43.5 and item['h']>=43.5 for item in mobile['handles']),(width_px,height_px,mobile['handles'])
   resize_before=page.evaluate('()=>({w:state.objects.details.width,h:state.objects.details.height})');drag_handle(page,'se',18,14);resize_after=page.evaluate('()=>({w:state.objects.details.width,h:state.objects.details.height})');assert resize_after!=resize_before,(width_px,height_px,resize_before,resize_after)
   page.evaluate("()=>EInviteEditorBridge.replaceState(structuredClone(window.__v17Baseline),{history:true,save:false,reason:'mobile-rotate-reset'})");page.wait_for_timeout(220);page.evaluate("()=>EInviteEditorBridge.select(['details'])");page.wait_for_timeout(180);rb=box(page,'.pe-rotate');sb=box(page,'#peSelectionBox');assert rb and sb,(width_px,height_px,rb,sb);rotation_before=float(page.locator('[data-pe-transform="r"]').input_value());page.mouse.move(rb['x']+rb['width']/2,rb['y']+rb['height']/2);page.mouse.down();page.mouse.move(sb['x']+sb['width']+20,sb['y']+sb['height']/2,steps=5);page.mouse.up();page.wait_for_timeout(220);rotation_after=float(page.locator('[data-pe-transform="r"]').input_value());assert abs(rotation_after-rotation_before)>1,(width_px,height_px,rotation_before,rotation_after)
   page.close();browser.close()
  assert not errors,errors[:10]
 print('V17_PROFESSIONAL_EDITOR_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
