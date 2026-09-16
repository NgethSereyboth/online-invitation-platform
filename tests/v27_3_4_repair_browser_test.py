#!/usr/bin/env python3
"""Focused browser acceptance for the V27.3.4 workflow/focus/offline repair."""
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]

def seeded(html:str)->str:
 marker="window.alert=()=>{};"
 return html.replace(marker,"localStorage.setItem('einvite-final-tour-seen-v1','1');"+marker,1)

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:print('V27_3_4_REPAIR_BROWSER_SKIPPED_NO_PLAYWRIGHT',exc);return 0
 html=build_inline_editor()
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:print('V27_3_4_REPAIR_BROWSER_SKIPPED_NO_CHROMIUM',exc);return 0
  # Legacy seen-state migration must suppress automatic reopening.
  print('REPAIR_BROWSER legacy',flush=True)
  legacy=browser.new_page(viewport={'width':1024,'height':800});errors=[]
  legacy.on('pageerror',lambda e:errors.append(str(e)))
  legacy.set_content(seeded(html),wait_until='load',timeout=30000)
  legacy.wait_for_timeout(1200)
  result=legacy.evaluate("()=>window.EInviteOnboardingReady")
  assert result['shown'] is False,result
  assert not legacy.locator('.final-tour').evaluate('(n)=>n.open')
  assert legacy.evaluate("()=>localStorage.getItem('einvite-final-tour-seen-v2:local-anonymous:studio-v27')")=='1'
  assert not errors,errors
  legacy.close()

  print('REPAIR_BROWSER first-run',flush=True)
  page=browser.new_page(viewport={'width':1440,'height':900});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(html,wait_until='load',timeout=30000);page.wait_for_timeout(1200)
  onboard=page.evaluate("()=>window.EInviteOnboardingReady")
  assert onboard['shown'] is True,onboard
  assert page.locator('.final-tour').evaluate('(n)=>n.open')
  page.locator('#finalTourDismiss').click();page.wait_for_timeout(180)
  focus=page.evaluate("()=>({id:document.activeElement?.id,owner:document.body.dataset.keyboardOwner,seen:localStorage.getItem('einvite-final-tour-seen-v2:local-anonymous:studio-v27')})")
  assert focus['id'] in ('stage','canvasViewport') and focus['owner']=='canvas' and focus['seen']=='1',focus
  page.wait_for_timeout(250);assert not page.locator('.final-tour').evaluate('(n)=>n.open')

  print('REPAIR_BROWSER tour-focus',flush=True)
  # Manual tour returns to its exact launcher.
  launcher=page.locator('.final-tour-trigger');launcher.click();page.wait_for_timeout(50)
  page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  assert page.evaluate("()=>document.activeElement===document.querySelector('.final-tour-trigger')")

  print('REPAIR_BROWSER dock',flush=True)
  # V4 is the single idempotent owner of the page dock.
  assert page.locator('#workflowPageDock').count()==1
  assert page.locator('#workflowPageDock .workflow-page-add').count()==1
  page.add_script_tag(path=str(ROOT/'workflow-creation-flow-v4.js'));page.wait_for_timeout(80)
  assert page.locator('#workflowPageDock').count()==1
  assert page.locator('#workflowPageDock .workflow-page-add').count()==1

  print('REPAIR_BROWSER keyboard',flush=True)
  # Pointer selection establishes canvas keyboard ownership; typing controls retain theirs.
  title=page.locator('#stage .object[data-id="title"]');title.click(force=True);page.wait_for_timeout(100)
  before=float(title.evaluate("n=>parseFloat(n.style.top||n.dataset.top||'0')"))
  page.keyboard.press('ArrowUp');page.wait_for_timeout(80)
  after=float(title.evaluate("n=>parseFloat(n.style.top||n.dataset.top||'0')"))
  assert after<before,(before,after)
  page.keyboard.down(' ');page.wait_for_timeout(30)
  assert page.evaluate("()=>window.EInviteCanvasPanController?.held===true")
  page.keyboard.up(' ');page.wait_for_timeout(30)
  assert page.evaluate("()=>window.EInviteCanvasPanController?.held===false")
  font=page.locator('#v20VisibleFont');font.focus();top_before=float(title.evaluate("n=>parseFloat(n.style.top||n.dataset.top||'0')"))
  page.keyboard.press('ArrowUp');page.wait_for_timeout(50)
  assert float(title.evaluate("n=>parseFloat(n.style.top||n.dataset.top||'0')"))==top_before

  print('REPAIR_BROWSER offline-review',flush=True)
  # Static/offline review never calls review APIs and never starts polling.
  page.evaluate("""()=>{window.__reviewFetches=0;window.__reviewIntervals=0;window.serverInvite={id:'offline-contract'};window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>false};const f=window.fetch;window.fetch=(...a)=>{window.__reviewFetches++;return f(...a)};const si=window.setInterval;window.setInterval=(...a)=>{window.__reviewIntervals++;return si(...a)}}""")
  page.add_style_tag(path=str(ROOT/'review-v23.css'));page.add_script_tag(path=str(ROOT/'review-v23.js'));page.wait_for_timeout(180)
  page.evaluate("()=>EInviteReviewWorkflow.open()");page.wait_for_timeout(120)
  page.evaluate("()=>EInviteReviewWorkflow.refresh()");page.wait_for_timeout(80)
  counters=page.evaluate("()=>({fetches:__reviewFetches,intervals:__reviewIntervals,error:EInviteReviewWorkflow.context.readiness,text:document.querySelector('#v23ReviewDrawer')?.innerText||''})")
  assert counters['fetches']==0 and counters['intervals']==0,counters
  assert 'require the application server' in counters['text'].lower() or 'requires the full application server' in counters['text'].lower(),counters
  assert not errors,errors[:10]
  browser.close()
 print('V27_3_4_REPAIR_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
