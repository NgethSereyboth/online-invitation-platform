#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V28_AGENT_MOBILE_BROWSER',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V28_AGENT_MOBILE_BROWSER',exc)
  for width,height in [(360,800),(390,844),(430,932)]:
   page=browser.new_page(viewport={'width':width,'height':height});ready(page,width,height)
   page.evaluate("""()=>{window.EInviteContext={getInvitationId:()=> 'invite-1'};window.EInviteBackend={isAvailable:()=>false}}""")
   page.add_style_tag(content=(ROOT/'ai-creative-agent-v28.css').read_text(encoding='utf-8'))
   page.add_script_tag(content=(ROOT/'ai-agent-tool-registry-v28.js').read_text(encoding='utf-8'))
   page.add_script_tag(content=(ROOT/'ai-creative-agent-v28.js').read_text(encoding='utf-8'))
   page.evaluate("EInviteAICreativeAgent.open(document.querySelector('#stage'))");page.wait_for_timeout(100)
   result=page.evaluate("""()=>{const p=document.querySelector('#eiAgentPanel'),r=p.getBoundingClientRect(),buttons=[...p.querySelectorAll('button')].filter(b=>b.offsetParent);return{role:p.getAttribute('role'),modal:p.getAttribute('aria-modal'),left:r.left,right:r.right,width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth,minTarget:Math.min(...buttons.map(b=>Math.min(b.getBoundingClientRect().width,b.getBoundingClientRect().height))),inert:[...document.body.children].some(n=>n!==p&&n.inert)}}""")
   assert result['role']=='dialog' and result['modal']=='true' and result['left']>=-0.5 and result['right']<=width+0.5 and result['overflow']<=1 and result['minTarget']>=43.5 and result['inert'],(width,result)
   page.keyboard.press('Escape');page.close()
  browser.close()
 print('V28_AGENT_MOBILE_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
