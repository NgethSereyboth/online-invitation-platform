from pathlib import Path
from route_bundle_sources import has
root = Path(__file__).resolve().parents[1]
js = (root / 'workflow-pro-editor-v6.js').read_text(encoding='utf-8')
css = (root / 'workflow-pro-editor-v6.css').read_text(encoding='utf-8')
html = (root / 'index.html').read_text(encoding='utf-8')
required_js = [
    'alignToCanvas', 'workflowV6Position', 'application/x-einvite-insert-source',
    'workflowV6Flow', 'application/x-einvite-flow', 'application/x-einvite-layer',
    'window.assetStore', 'state.sectionOrder'
]
for token in required_js:
    assert token in js, token
assert has('index.html','workflow-pro-editor-v6.css')
assert has('index.html','workflow-pro-editor-v6.js')
assert '.workflow-v6-flow' in css
assert '.workflow-v6-position' in css
print('PRO_EDITOR_V6_TEST_PASSED')
