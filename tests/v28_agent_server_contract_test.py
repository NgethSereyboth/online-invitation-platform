#!/usr/bin/env python3
from __future__ import annotations
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 source=(ROOT/'server.py').read_text(encoding='utf-8');ast.parse(source)
 for token in ['/api/ai-agent/status','/api/ai-agent/tools','/api/ai-agent/preferences','/api/ai-agent/memories','/api/ai-agent/knowledge','/ai/messages/','/feedback','/ai/threads','/ai/plans/','/ai/jobs/']:assert token in source,token
 assert 'ensure_agent_schema(connect)' in source
 for file in ['config.py','storage.py','context.py','providers.py','tools.py','service.py']:ast.parse((ROOT/'ai_agent'/file).read_text(encoding='utf-8'))
 service=(ROOT/'ai_agent'/'service.py').read_text(encoding='utf-8')
 assert 'PERMISSION_ROLES' in service and '"manage": {"owner", "manager"}' in service
 assert 'Only a confirmed plan can report completion' in service
 info=json.loads((ROOT/'BUILD_INFO.json').read_text(encoding='utf-8'))
 assert info['version']=='0.52' and int(info.get('internalMilestone',0))>=28 and info['schemaVersion']>=14,info
 assert 'V28' in info.get('implementedMilestones',[])
 assert 'pending' in json.dumps(info.get('certification',{}),ensure_ascii=False).lower()
 print('V28_AGENT_SERVER_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
