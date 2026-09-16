#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ai_agent.tools import tool_catalog,validate_tool_calls,ToolValidationError

def rejected(call):
 try:validate_tool_calls([call],10)
 except ToolValidationError:return True
 return False

def main()->int:
 tools=tool_catalog();ids=[item['id'] for item in tools]
 assert len(ids)==len(set(ids)) and len(ids)>=40
 required={'read.project_summary','rich_text.replace','photo.remove_background','publish.prepare','message.prepare_send','check.layout'}
 assert required<=set(ids)
 validated=validate_tool_calls([{'id':'rich_text.replace','arguments':{'pageId':'hero','objectIds':['title'],'text':'សូមអញ្ជើញ','mode':'preserve'},'reason':'Preserve Khmer locale and links.'}],10)
 assert validated[0]['risk']=='low' and validated[0]['reversible']
 assert rejected({'id':'unknown.tool','arguments':{}})
 for bad in [
  {'id':'object.update','arguments':{'pageId':'hero','objectIds':['title'],'patch':{'selector':'#title'}}},
  {'id':'object.update','arguments':{'pageId':'hero','objectIds':['title'],'patch':{'html':'<script>x</script>'}}},
  {'id':'object.create_text','arguments':{'pageId':'hero','text':'file:///etc/passwd'}},
  {'id':'object.create_text','arguments':{'pageId':'hero','text':'SELECT * FROM users'}},
 ]:assert rejected(bad),bad
 print('V28_AGENT_TOOL_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
