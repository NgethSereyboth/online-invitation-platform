#!/usr/bin/env python3
"""Current AI UX compatibility contract; legacy V5 commands remain server-supported."""
from pathlib import Path
from route_bundle_sources import has
ROOT=Path(__file__).resolve().parents[1]
agent=(ROOT/'ai-creative-agent-v28.js').read_text(encoding='utf-8')
agent_css=(ROOT/'ai-creative-agent-v28.css').read_text(encoding='utf-8')
bundle=(ROOT/'editor-suite.js').read_text(encoding='utf-8')
loader=(ROOT/'ai-assistant-loader-v27.js').read_text(encoding='utf-8')
bootstrap=(ROOT/'editor-deferred-tools-bootstrap-v0_52.js').read_text(encoding='utf-8')
workflow=(ROOT/'workflow-ux-v5.js').read_text(encoding='utf-8');css=(ROOT/'workflow-ux-v5.css').read_text(encoding='utf-8');server=(ROOT/'server.py').read_text(encoding='utf-8')
assert has('index.html','workflow-ux-v5.css') and has('index.html','workflow-ux-v5.js')
for token in ['eiAgentPanel','design-review','accessibility','page-outline','translate-khmer','Regenerate with current selection','Preview against current selection']:
 assert token in agent or token in server,token
assert 'ai-creative-agent-v28.js' not in bundle and 'eiAgentPanel' not in bundle
assert 'ai-creative-agent-v28.js' in loader and 'ai-creative-agent-v28.css' in loader
assert 'ai-assistant-loader-v27.js' in bootstrap
for token in ['workflowV5ContextMenu','workflowV5Focus','workflow-v5-status','Ctrl/⌘ + .']:assert token in workflow or token in css,token
for token in ['translate-khmer','rewrite-formal','tone-friendly','page-outline','design-review','accessibility']:assert token in server,f'server missing {token}'
for token in ['role','aria-modal','inert','safe-area-inset-bottom','min-height:44px']:assert token in agent or token in agent_css,token
canvas=(ROOT/'canvas-plus.js').read_text(encoding='utf-8');assert 'aiBgThreshold' in canvas and 'aiBgFeather' in canvas and 'Removing background…' in canvas
print('UX_AI_V5_TEST_PASSED')
