#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
loader=(ROOT / "src" / "js" / "performance-loader.js").read_text(encoding='utf-8')
server=(ROOT/'src'/'python'/'server.py').read_text(encoding='utf-8')
assert 'adaptive-templates.js' in loader
assert 'studio-governance.js' in loader
assert 'print-readiness.js' in loader
assert 'template-bindings.js' in loader
assert loader.index('export-quality.js')<loader.index('adaptive-templates.js')<loader.index('studio-governance.js')<loader.index('print-readiness.js')<loader.index('template-bindings.js')
for name in ('adaptive-templates.js','studio-governance.js','print-readiness.js','template-bindings.js'):
 text=(ROOT/'src'/'js'/name).read_text(encoding='utf-8');assert 'addEventListener(\'keydown\'' not in text and 'addEventListener("keydown"' not in text,name
for command in ('templates.adaptive','studio.governance','print.preflight','templates.refreshBindings'):
 assert command in ''.join((ROOT/'src'/'js'/n).read_text(encoding='utf-8') for n in ('adaptive-templates.js','studio-governance.js','print-readiness.js','template-bindings.js')),command
for token in ('CREATE TABLE IF NOT EXISTS studio_resources','CREATE TABLE IF NOT EXISTS studio_governance','studio_governance_blocked','studio_print_fingerprint'):
 assert token in server,token
assert 'contentBinding' in (ROOT / "src" / "js" / "adaptive-templates.js").read_text(encoding='utf-8')
assert 'bindingDetached' in (ROOT / "src" / "js" / "template-bindings.js").read_text(encoding='utf-8')
print('V25_TEMPLATE_GOVERNANCE_CONTRACT_TEST_PASSED')
