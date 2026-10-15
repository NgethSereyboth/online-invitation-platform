#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 route=json.loads((ROOT / "docs" / "route-bundle-sources-v15.json").read_text(encoding='utf-8'))['pages']['index.html']
 startup='\n'.join(route['scripts']+route['styles'])
 for lazy in ['ai-creative-agent-v28.js','ai-agent-tool-registry-v28.js','ai-creative-agent-v28.css','advanced-editor-loader-v32.js','font-browser-loader-v22.js']:assert lazy not in startup,lazy
 deferred='\n'.join(route.get('deferredScripts',[])+route.get('deferredStyles',[]))
 for lazy in ['ai-creative-agent-v28.js','ai-agent-tool-registry-v28.js','ai-creative-agent-v28.css','advanced-editor-loader-v32.js','font-browser-loader-v22.js']:assert lazy not in deferred,lazy
 assert 'editor-deferred-tools-bootstrap-v0_52.js' in route['scripts']
 assert 'route-deferred-loader-v15.js' in route['scripts']
 assert 'ai-editor-action-service-v27.js' in route['scripts']
 bootstrap=(ROOT / "src" / "js" / "editor-deferred-tools-bootstrap-v0_52.js").read_text(encoding='utf-8')
 for entry in ['ai-assistant-loader-v27.js','advanced-editor-loader-v32.js','font-browser-loader-v22.js']:assert entry in bootstrap,entry
 loader=(ROOT / "src" / "js" / "ai-assistant-loader-v27.js").read_text(encoding='utf-8')
 for lazy in ['ai-creative-agent-v28.js','ai-agent-tool-registry-v28.js','ai-creative-agent-v28.css']:assert lazy in loader,lazy
 # The editor-route ceiling lives in docs/perf/lighthouse-budgets.json; the
 # 1_420_000 literal was the V0.52 snapshot (see tests/route_budget_utils.py).
 sys.path.insert(0,str(ROOT / "tests"));from route_budget_utils import assert_index_route_within_budget;assert_index_route_within_budget()
 assert (ROOT / "src" / "js" / "editor-suite.js").read_text(encoding='utf-8').count('AI Creative Agent')==0
 print('V28_AGENT_PERFORMANCE_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
