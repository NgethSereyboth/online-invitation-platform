#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V28_AGENT_REGISTRY_BROWSER',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V28_AGENT_REGISTRY_BROWSER',exc)
  page=browser.new_page();ready(page);page.add_init_script("window.EInviteContext={getInvitationId:()=> 'invite-1'}")
  page.add_script_tag(content=(ROOT/'ai-agent-tool-registry-v28.js').read_text(encoding='utf-8'))
  page.wait_for_function('()=>window.EInviteAgentToolRegistry')
  result=page.evaluate("""async()=>{const B=EInviteEditorBridge,S=EInviteAIActionService,R=EInviteAgentToolRegistry;B.select(['title']);const before=S.fingerprint(B.getState());const plan={toolCalls:[{id:'rich_text.replace',arguments:{pageId:'hero',objectIds:['title'],text:'សូមអញ្ជើញចូលរួម',mode:'preserve'}},{id:'object.create_text',arguments:{pageId:'hero',text:'Caption',style:{textStyleId:'caption'}}}]};const prepared=await R.prepare(plan);const done=await R.execute(plan);const after=S.fingerprint(B.getState());B.undo();return{preview:prepared.preview?.ok,actions:done.actionCount,before,after,undo:S.fingerprint(B.getState()),text:B.getState().objects.title.text}}""")
  assert result['preview'] and result['actions']==2 and result['after']!=result['before'] and result['undo']==result['before'],result
  browser.close()
 print('V28_AGENT_REGISTRY_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
