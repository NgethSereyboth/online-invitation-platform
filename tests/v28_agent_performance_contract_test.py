#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 route=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))['pages']['index.html']
 startup='\n'.join(route['scripts']+route['styles'])
 for lazy in ['ai-creative-agent-v28.js','ai-agent-tool-registry-v28.js','ai-creative-agent-v28.css','advanced-editor-loader-v32.js','font-browser-loader-v22.js']:assert lazy not in startup,lazy
 assert 'editor-deferred-tools-bootstrap-v0_52.js' in route['scripts'] and 'ai-editor-action-service-v27.js' in route['scripts']
 bootstrap=(ROOT/'editor-deferred-tools-bootstrap-v0_52.js').read_text(encoding='utf-8')
 for entry in ['ai-assistant-loader-v27.js','advanced-editor-loader-v32.js','font-browser-loader-v22.js']:assert entry in bootstrap,entry
 loader=(ROOT/'ai-assistant-loader-v27.js').read_text(encoding='utf-8')
 for lazy in ['ai-creative-agent-v28.js','ai-agent-tool-registry-v28.js','ai-creative-agent-v28.css']:assert lazy in loader,lazy
 size=(ROOT/'bundle-index-v15.js').stat().st_size+(ROOT/'bundle-index-v15.css').stat().st_size;assert size<=1_420_000,size
 assert (ROOT/'editor-suite.js').read_text(encoding='utf-8').count('AI Creative Agent')==0
 print('V28_AGENT_PERFORMANCE_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
