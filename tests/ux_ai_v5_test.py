#!/usr/bin/env python3
"""Current AI UX compatibility contract; legacy V5 commands remain server-supported."""
from pathlib import Path
from route_bundle_sources import has
ROOT=Path(__file__).resolve().parents[1]
agent=(ROOT / "src" / "js" / "ai-creative-agent.js").read_text(encoding='utf-8')
agent_css=(ROOT / "src" / "css" / "ai-creative-agent.css").read_text(encoding='utf-8')
bundle=(ROOT / "src" / "js" / "editor-suite.js").read_text(encoding='utf-8')
loader=(ROOT / "src" / "js" / "ai-assistant-loader.js").read_text(encoding='utf-8')
bootstrap=(ROOT / "src" / "js" / "editor-deferred-tools-bootstrap.js").read_text(encoding='utf-8')
workflow=(ROOT / "src" / "js" / "workflow-ux.js").read_text(encoding='utf-8');css=(ROOT / "src" / "css" / "organized" / "workflow-ux.css").read_text(encoding='utf-8');server=(ROOT / "src" / "python" / "server.py").read_text(encoding='utf-8')
assert has('index.html','workflow-ux.css') and has('index.html','workflow-ux.js')
for token in ['eiAgentPanel','design-review','accessibility','page-outline','translate-khmer','Regenerate with current selection','Preview against current selection']:
 assert token in agent or token in server,token
assert 'ai-creative-agent.js' not in bundle and 'eiAgentPanel' not in bundle
assert 'ai-creative-agent.js' in loader and 'ai-creative-agent.css' in loader
assert 'ai-assistant-loader.js' in bootstrap
for token in ['workflowV5ContextMenu','workflowV5Focus','workflow-v5-status','Ctrl/⌘ + .']:assert token in workflow or token in css,token
for token in ['translate-khmer','rewrite-formal','tone-friendly','page-outline','design-review','accessibility']:assert token in server,f'server missing {token}'
for token in ['role','aria-modal','inert','safe-area-inset-bottom','min-height:44px']:assert token in agent or token in agent_css,token
canvas=(ROOT / "src" / "js" / "canvas-plus.js").read_text(encoding='utf-8');assert 'aiBgThreshold' in canvas and 'aiBgFeather' in canvas and 'Removing background…' in canvas
print('UX_AI_V5_TEST_PASSED')
