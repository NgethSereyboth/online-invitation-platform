#!/usr/bin/env python3
from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ai_agent.config import AgentConfig
from ai_agent.providers import FakeProvider,ExternalProvider,ProviderError
from ai_agent.tools import tool_catalog,validate_tool_calls

def context(selected=True):
 return {'document':{'activePageId':'hero','selection':[{'id':'photo','type':'image'}] if selected else [],'fields':{}},'invitation':{'id':'invite-1'}}

def main()->int:
 result=FakeProvider().generate('Remove this image background, center it, and add a caption.',context(),tool_catalog(),[])
 calls=validate_tool_calls(result.tool_calls,40);ids=[c['id'] for c in calls]
 assert ids==['photo.remove_background','transform.align','object.create_text']
 result=FakeProvider().generate('Rewrite only the selected paragraph',{'document':{'activePageId':'hero','selection':[{'id':'title'}],'fields':{}},'invitation':{}},tool_catalog(),[])
 assert result.tool_calls[0]['id']=='rich_text.replace' and result.tool_calls[0]['arguments']['mode']=='preserve'
 cfg=AgentConfig('', '', '', 'external', 2, 20000, 50000, 10, 10, 1, 30, True, False, False)
 try:ExternalProvider(cfg).generate('x',context(),tool_catalog(),[])
 except ProviderError as exc:assert exc.code=='provider_unavailable'
 else:raise AssertionError('unconfigured external provider accepted')
 print('V28_AGENT_PROVIDER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
