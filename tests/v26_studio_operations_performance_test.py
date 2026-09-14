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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000})
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(800)
  page.add_style_tag(path=str(ROOT/'studio-operations-v26.css'))
  page.evaluate("""()=>{const rs=Array.from({length:30},(_,i)=>({id:'r'+i,name:'Release '+i,notes:'Bounded release record '+i,status:i===0?'active':i<10?'draft':'retired',manifest:Array.from({length:40},(_,j)=>({id:`x${i}-${j}`,kind:j%3===0?'brand':j%3===1?'template-family':'component',name:'Resource '+j,version:1})),version:1,activatedAt:i===0?Date.now():0}));localStorage.setItem('einvite-v26-studio-releases',JSON.stringify(rs));window.EInviteFeedback={toast:()=>{}}}""")
  start=page.evaluate('performance.now()');page.add_script_tag(path=str(ROOT/'studio-operations-v26.js'));page.wait_for_timeout(80);page.evaluate("()=>EInviteStudioOperations.open('releases')");page.wait_for_timeout(70);elapsed=page.evaluate('(s)=>performance.now()-s',start)
  cards=page.locator('.v26-release-card').count();assert cards==30,cards
  assert elapsed<1500,elapsed
  assert page.evaluate('()=>EInviteCommandRegistry.conflicts.length')==0
  page.evaluate("()=>EInviteStudioOperations.open('releases')");page.wait_for_timeout(20);assert page.locator('.v26-operations-dialog').count()==1
  browser.close()
 print(f'V26_STUDIO_OPERATIONS_PERFORMANCE_TEST_PASSED {elapsed:.1f}ms');return 0
if __name__=='__main__':sys.exit(main())
