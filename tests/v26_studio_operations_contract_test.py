#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
loader=(ROOT/'performance-loader-v22.js').read_text()
server=(ROOT/'server.py').read_text()
client=(ROOT/'studio-operations-v26.js').read_text()
assert 'studio-operations-v26.js' in loader
assert loader.index('template-bindings-v25.js')<loader.index('studio-operations-v26.js')
assert 'addEventListener(\'keydown\'' not in client and 'addEventListener("keydown"' not in client
for command in ('studio.operations','studio.releaseCreate','studio.releasePinActive','studio.adoption','studio.deployment'):
 assert command in client,command
for token in ('CREATE TABLE IF NOT EXISTS studio_releases','CREATE TABLE IF NOT EXISTS invitation_studio_release_pins','studio_release_required','studio_release_resource_changed','/api/studio/releases','/api/studio/adoption','/clone','/studio-release'):
 assert token in server,token
assert 'requireStudioRelease' in server and 'requireStudioRelease' in (ROOT/'studio-governance-v25.js').read_text()
assert (ROOT/'studio-operations-v26.css').exists()
print('V26_STUDIO_OPERATIONS_CONTRACT_TEST_PASSED')
