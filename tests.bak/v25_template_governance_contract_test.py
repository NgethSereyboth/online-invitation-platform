#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
loader=(ROOT / "src" / "js" / "performance-loader-v22.js").read_text()
server=(ROOT/'src'/'python'/'server.py').read_text()
assert 'adaptive-templates-v25.js' in loader
assert 'studio-governance-v25.js' in loader
assert 'print-readiness-v25.js' in loader
assert 'template-bindings-v25.js' in loader
assert loader.index('export-quality-v24.js')<loader.index('adaptive-templates-v25.js')<loader.index('studio-governance-v25.js')<loader.index('print-readiness-v25.js')<loader.index('template-bindings-v25.js')
for name in ('adaptive-templates-v25.js','studio-governance-v25.js','print-readiness-v25.js','template-bindings-v25.js'):
 text=(ROOT/'src'/'js'/name).read_text();assert 'addEventListener(\'keydown\'' not in text and 'addEventListener("keydown"' not in text,name
for command in ('templates.adaptive','studio.governance','print.preflight','templates.refreshBindings'):
 assert command in ''.join((ROOT/'src'/'js'/n).read_text() for n in ('adaptive-templates-v25.js','studio-governance-v25.js','print-readiness-v25.js','template-bindings-v25.js')),command
for token in ('CREATE TABLE IF NOT EXISTS studio_resources','CREATE TABLE IF NOT EXISTS studio_governance','studio_governance_blocked','studio_print_fingerprint'):
 assert token in server,token
assert 'contentBinding' in (ROOT / "src" / "js" / "adaptive-templates-v25.js").read_text()
assert 'bindingDetached' in (ROOT / "src" / "js" / "template-bindings-v25.js").read_text()
print('V25_TEMPLATE_GOVERNANCE_CONTRACT_TEST_PASSED')
