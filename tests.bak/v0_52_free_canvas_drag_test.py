#!/usr/bin/env python3
"""Regression coverage for free canvas movement and drag-overlay behavior."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v17_professional_editor_test import build,boot,box


def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V0_52_FREE_CANVAS_DRAG',exc)
 with sync_playwright() as runtime:
  try:browser=launch_chromium(runtime)
  except Exception as exc:return skipped('V0_52_FREE_CANVAS_DRAG',exc)
  page=browser.new_page(viewport={'width':1100,'height':620});page.set_default_timeout(20_000);errors=[]
  page.on('pageerror',lambda error:errors.append(f'PAGE:{error}'))
  page.on('console',lambda message:errors.append(f'CONSOLE:{message.text}') if message.type=='error' else None)
  boot(page,build());page.evaluate("()=>{window.__freeCanvasBaseline=EInviteEditorBridge.cloneState();EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(160)

  # X/Y inputs accept both negative pasteboard coordinates and positions beyond
  # the artboard; width and height remain positive and bounded.
  def transform(key,value):
   page.evaluate("([key,value])=>{const control=document.querySelector(`[data-pe-transform=\"${key}\"]`);control.value=String(value);control.dispatchEvent(new Event('change',{bubbles:true}))}",[key,value]);page.wait_for_timeout(220)
  transform('x',-48);after_x=page.evaluate("()=>({model:state.objects.details.left,style:document.querySelector('#stage .object[data-id=\"details\"]').style.left,input:document.querySelector('[data-pe-transform=\"x\"]').value})");transform('y',-72)
  outside=page.evaluate("()=>Object.fromEntries(EInviteEditorBridge.getSelectedIds().map(id=>[id,{left:parseFloat(state.objects[id].left),top:parseFloat(state.objects[id].top)}]))")
  assert min(item['left'] for item in outside.values())<0 and min(item['top'] for item in outside.values())<0,(after_x,outside)
  transform('x',520)
  assert page.evaluate("()=>Math.max(...EInviteEditorBridge.getSelectedIds().map(id=>parseFloat(state.objects[id].left)))>100")

  # Restore an on-canvas position, drag at the viewport edge, and confirm that
  # the viewport follows the pointer while the stale blue overlay is hidden.
  page.evaluate("()=>{EInviteEditorBridge.replaceState(structuredClone(window.__freeCanvasBaseline),{history:true,save:false,reason:'free-canvas-drag-reset'});EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(260)
  viewport=box(page,'#canvasViewport');obj=box(page,'#stage .object[data-id="details"]');assert viewport and obj
  page.locator('#stage .object[data-id="details"]').scroll_into_view_if_needed();page.wait_for_timeout(120)
  viewport=box(page,'#canvasViewport');obj=box(page,'#stage .object[data-id="details"]');assert viewport and obj
  obj=box(page,'#stage .object[data-id="details"]');before=page.evaluate("()=>({top:state.objects.details.top,scroll:document.querySelector('#canvasViewport').scrollTop})")
  sx=obj['x']+obj['width']/2;sy=max(viewport['y']+80,min(viewport['y']+viewport['height']-90,obj['y']+obj['height']/2));edge=viewport['y']+viewport['height']-4
  page.mouse.move(sx,sy);page.mouse.down();page.mouse.move(sx,edge,steps=8);page.wait_for_timeout(80)
  during=page.evaluate("()=>({overlay:getComputedStyle(document.querySelector('#peSelectionBox')).visibility,selected:document.querySelector('#stage .object[data-id=\"details\"]').classList.contains('selected')})")
  assert during=={'overlay':'hidden','selected':True},during
  page.mouse.move(sx,edge,steps=8);page.mouse.up();page.wait_for_timeout(260)
  after=page.evaluate("()=>({top:state.objects.details.top,scroll:document.querySelector('#canvasViewport').scrollTop,overlay:getComputedStyle(document.querySelector('#peSelectionBox')).visibility})")
  assert after['scroll']>before['scroll'],(before,after)
  assert after['top']!=before['top'] and after['overlay']=='visible',(before,after)
  assert not errors,errors
  browser.close()
 print('V0_52_FREE_CANVAS_DRAG_TEST_PASSED');return 0


if __name__=='__main__':raise SystemExit(main())
