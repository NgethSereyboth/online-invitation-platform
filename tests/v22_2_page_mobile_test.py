#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium, skipped
ROOT=Path(__file__).resolve().parents[1]

def build():
 spec=importlib.util.spec_from_file_location('inline_editor',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(mod);return mod.build_inline_editor()

def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_2_PAGE_MOBILE',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_2_PAGE_MOBILE',exc)
  try:
   page=browser.new_page(viewport={'width':430,'height':900});page.set_default_timeout(60000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(build(),wait_until='load');page.wait_for_timeout(1300)
   if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
   page.add_style_tag(content=(ROOT/'page-experience-v22.css').read_text(encoding='utf-8'));page.add_script_tag(content=(ROOT/'page-experience-v22.js').read_text(encoding='utf-8'));page.wait_for_function("()=>EInvitePageExperience?.version==='22.2.8'")
   page.evaluate("()=>{EInvitePageExperience.addPage({mode:'event-template',role:'title'});EInvitePageExperience.addPage({mode:'free-design'})}");page.wait_for_timeout(500)
   page.locator('#mobileToolsMode').click();page.locator('[data-studio-tab="pages"]').click();page.wait_for_timeout(350)
   layout=page.evaluate("""()=>{const pane=document.querySelector('[data-studio-pane="pages"]'),manager=document.querySelector('.v22-page-manager'),toolbar=document.querySelector('.v22-page-manager-toolbar'),filters=[...document.querySelectorAll('.v22-page-filter button')],cards=[...document.querySelectorAll('.v22-page-card')];const pr=pane.getBoundingClientRect(),mr=manager.getBoundingClientRect();return {pane:{x:pr.x,w:pr.width,sw:pane.scrollWidth,cw:pane.clientWidth},manager:{x:mr.x,w:mr.width,sw:manager.scrollWidth,cw:manager.clientWidth},toolbar:getComputedStyle(toolbar).gridTemplateColumns,filterHeights:filters.map(n=>n.getBoundingClientRect().height),cardWidths:cards.slice(0,3).map(n=>n.getBoundingClientRect().width)}}""")
   assert layout['pane']['sw']<=layout['pane']['cw']+3,layout
   assert layout['manager']['sw']<=layout['manager']['cw']+3,layout
   assert all(h>=34 for h in layout['filterHeights']),layout
   assert all(w>=90 for w in layout['cardWidths']),layout
   add=page.locator('.v22-page-manager [data-add-page]');add.scroll_into_view_if_needed();add.click();page.wait_for_timeout(100)
   menu=page.evaluate("""()=>{const m=document.querySelector('.v22-page-menu'),r=m?.getBoundingClientRect();return r?{l:r.left,r:r.right,t:r.top,b:r.bottom,w:innerWidth,h:innerHeight}:null}""")
   assert menu and menu['l']>=0 and menu['r']<=menu['w']+1 and menu['t']>=0 and menu['b']<=menu['h']+1,menu
   page.locator('.v22-page-menu [data-add-mode="free-design"]').click();page.wait_for_timeout(350)
   assert page.evaluate("()=>EInviteEditorBridge.getState().designPages.at(-1).editMode")=='free-design'
   assert not errors,errors[:20]
  finally:browser.close()
 print('V22_2_PAGE_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
