"""Codex handoff contract for the selected V34–V52 implementation. Not executed during implementation."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
build=json.loads((ROOT/'BUILD_INFO.json').read_text(encoding='utf-8'))
assert build['version']=='0.52'
assert build['schemaVersion']==27
required=(
 'future_platform_v52/schema.py','future_platform_v52/service.py','future-studio-loader-v52.js','future-studio-v52.css','future-ui-v0_52.js','editor-deferred-tools-bootstrap-v0_52.js',
 'unified-editor-v34.js','ai-production-v35.js','template-marketplace-v36.js','enterprise-government-v42.js',
 'advanced-animation-v44.js','advanced-motion-runtime-v44.js','publishing-domains-v45.js','data-merge-v47.js',
 'plugin-platform-v48.js','plugin-runtime-v48.js','event-ecosystem-v52.js','future-public-renderer-v52.js',
)
for name in required: assert (ROOT/name).is_file(), name
server=(ROOT/'server.py').read_text(encoding='utf-8')
for token in ('/api/platform/v52/','FuturePlatformService','ensure_future_schema'): assert token in server
route=json.loads((ROOT/'route-bundles-v15.json').read_text(encoding='utf-8'))['pages']['index.html']
assert route['scriptBytes']+route['styleBytes']<=1_420_000
for lazy in ('future-studio-loader-v52.js','advanced-animation-v44.js','plugin-runtime-v48.js'):
    assert lazy not in route['sources']['scripts'], lazy
print('V0_52_SELECTED_CAPABILITIES_CONTRACT_TEST_PASSED')
