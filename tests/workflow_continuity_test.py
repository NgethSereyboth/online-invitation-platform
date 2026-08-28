from pathlib import Path
from route_bundle_sources import has,after

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / 'index.html').read_text(encoding='utf-8')
js = (ROOT / 'workflow-continuity.js').read_text(encoding='utf-8')
css = (ROOT / 'workflow-continuity.css').read_text(encoding='utf-8')
legacy = (ROOT / 'workflow-refine.js').read_text(encoding='utf-8')

assert has('index.html','workflow-continuity.css')
assert has('index.html','workflow-continuity.js')
assert after('index.html','workflow-continuity.css','editor-layout-stability.css','styles')
assert after('index.html','workflow-continuity.js','workflow-refine.js','scripts')
assert 'window.EInviteWorkflow' in js
assert "e.stopImmediatePropagation()" in js
assert "workflow-panel-hidden" in js and "workflow-panel-hidden" in css
assert "Recent tools" in js
assert "workflow-search-results" in js
assert "Interaction routing is intentionally centralized in workflow-continuity.js" in legacy
print('WORKFLOW_CONTINUITY_TEST_PASSED')
