#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V28_AGENT_CONVERSATION_BROWSER',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V28_AGENT_CONVERSATION_BROWSER',exc)
  page=browser.new_page();page.set_default_timeout(12000);ready(page)
  page.evaluate("""()=>{window.EInviteContext={getInvitationId:()=> 'invite-1'};window.EInviteBackend={isAvailable:()=>false}}""")
  page.add_style_tag(content=(ROOT/'ai-creative-agent-v28.css').read_text(encoding='utf-8'))
  page.add_script_tag(content=(ROOT/'ai-agent-tool-registry-v28.js').read_text(encoding='utf-8'))
  page.add_script_tag(content=(ROOT/'ai-creative-agent-v28.js').read_text(encoding='utf-8'))
  page.evaluate("()=>EInviteAICreativeAgent.open('write',{opener:document.querySelector('#stage')})")
  panel=page.locator('#eiAgentPanel');panel.wait_for(state='visible');assert panel.get_attribute('aria-labelledby')=='eiAgentTitle'
  page.locator('[data-agent-input]').fill('Check mobile overflow');page.locator('[data-agent-action=send]').click();page.wait_for_timeout(250)
  assert 'Template helper' in panel.inner_text() or 'session-only' in panel.inner_text().lower()
  page.keyboard.press('Escape');page.wait_for_function("()=>document.querySelector('#eiAgentPanel')?.dataset.open==='false'")
  browser.close()
 print('V28_AGENT_CONVERSATION_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
