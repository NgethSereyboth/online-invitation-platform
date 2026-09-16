from pathlib import Path
import re
from collections import Counter
from route_bundle_sources import has,after

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / 'index.html').read_text(encoding='utf-8')
v7js = (ROOT / 'workflow-final-audit-v7.js').read_text(encoding='utf-8')
v7css = (ROOT / 'workflow-final-audit-v7.css').read_text(encoding='utf-8')
v6 = (ROOT / 'workflow-pro-editor-v6.js').read_text(encoding='utf-8')
continuity = (ROOT / 'workflow-continuity.js').read_text(encoding='utf-8')
legacy_flow = (ROOT / 'workflow-refine.js').read_text(encoding='utf-8')
v4 = (ROOT / 'workflow-creation-flow-v4.js').read_text(encoding='utf-8')
v3 = (ROOT / 'workflow-creation-flow-v3.js').read_text(encoding='utf-8')
v5 = (ROOT / 'workflow-ux-v5.js').read_text(encoding='utf-8')
editor_suite = (ROOT / 'editor-suite.js').read_text(encoding='utf-8')
commands = (ROOT / 'editor-command-system-v23.js').read_text(encoding='utf-8')
app = (ROOT / 'app.js').read_text(encoding='utf-8')
studio = (ROOT / 'studio-experience.js').read_text(encoding='utf-8')

# Final audit files are present and loaded after all previous workflow layers.
assert has('index.html','workflow-final-audit-v7.css')
assert has('index.html','workflow-final-audit-v7.js')
assert after('index.html','workflow-final-audit-v7.css','workflow-pro-editor-v6.css','styles')
assert after('index.html','workflow-final-audit-v7.js','workflow-pro-editor-v6.js','scripts')

# Every local script/stylesheet referenced by the editor exists.
for ref in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', index):
    if ref.startswith(('http://', 'https://', '//', 'data:')):
        continue
    assert (ROOT / ref.split('?', 1)[0]).exists(), f'missing editor dependency: {ref}'

# Static editor markup has no duplicate IDs.
ids = re.findall(r'\bid=["\']([^"\']+)', index)
assert not [item for item, count in Counter(ids).items() if count > 1]

# No workflow layer should silently refit the canvas during ordinary tool/panel/page changes.
for text in (continuity, legacy_flow, v3, v4, v5, v6, v7js):
    assert "$('#fitCanvas')?.click()" not in text
assert 'setInterval(sync,2500)' not in continuity
assert "navigate('pages',{source:'page" not in v4
assert "applyMode('pages')" not in legacy_flow

# Workflow routing remains centralized, while V23 owns the global Escape hierarchy.
assert 'function selectionFlow()' in continuity
assert 'function insertionFlow()' in continuity
assert 'function keyboardFlow(){}' in continuity
assert "window.addEventListener('keydown'" not in legacy_flow
assert "id:'ui.escape'" in commands
assert 'window.EInviteWorkflow' in continuity
assert 'e.stopImmediatePropagation()' in continuity

# Page/section flow reorder keeps page manager order synchronized with published order.
assert 'state.sectionOrder=unique' in v6
assert 'state.designPages=[' in v6 and 'pageIds.map' in v6
assert 'draggable="true"' in v6 and 'workflow-v6-grip' in v6
assert 'drag-after' in v6

# Layer reorder supports selected blocks and deterministic z-order without click storms.
assert "selectedIds=new Set(chosen().filter(o=>o.dataset.locked!=='true').map" in v6
assert 'const block=ordered.filter' in v6
assert "if(action==='front'||action==='back')" in v6
assert "$('#bringForward')?.click()" not in v6

# Multiple native image drops are batched and page drops do not automatically pollute the hero gallery.
assert 'Promise.all(files.slice(0,12)' in v6
assert "o.dataset.showInHero=onHero?'true':'false'" in v6
assert "o.dataset.showInGallery=onHero?'true':'false'" in v6
assert "const onHero = activeCanvasId === 'hero'" in app or "const onHero=activeCanvasId==='hero'" in app

# Alignment/distribution ignore locked objects instead of using them as hidden anchors.
assert "function alignSelectionV6(mode){\n  const items=chosen().filter(o=>o.dataset.locked!=='true')" in v6
assert "function distribute(axis){\n  const items=chosen().filter(o=>o.dataset.locked!=='true')" in v6

# Upload-library drag uses stable asset identity and waits for async blob insertion before positioning.
assert 'application/x-einvite-upload-asset' in studio
assert 'img.dataset.assetId' in studio
assert 'waitForInsertedObject' in studio
assert 'placeDroppedObject' in studio
assert 'canvasObjectIdsV6' in v6 and 'repositionNew(beforeIds' in v6

# Shortcut collision fix: shifted workflow shortcuts are not swallowed by the persistent tool rail.
assert "window.addEventListener('keydown',keydown,true)" in commands
for chord in ('Shift+E','Shift+T','Shift+U','Shift+F'):
    assert chord in commands
assert 'Focus canvas (Shift+F)' in v5

# V7 deterministically provides the dedicated Text workspace after the full editor shell loads.
for token in ('ensureTextWorkspace', 'workflow-v7-text-pane', 'data-v7-text-preset', 'fp-inline-font-list'):
    assert token in v7js, token

# V7 exposes flow where users need it and preserves the artboard view during chrome changes.
for token in ('workflowV7DesignFlow', 'workflowV7DockFlow', 'captureView', 'restoreView', 'workflow-v7-back-canvas'):
    assert token in v7js, token
assert 'window.EInviteProEditorV6?.renderFlow?.()' in v7js
assert 'workflow-final-audit-v7' in v7js

# Final CSS has explicit before/after insertion guides and robust scrolling.
for token in ('v6-drag-after::after', 'drag-over::before', 'scrollbar-gutter:stable', 'workflow-v7-dock-flow', ':focus-visible', 'stage-wrap>.studio-canvas-toolbar', '#canvasViewport>.ei-tool-rail', 'workflow-v5-coach{display:none', 'studio-design-mode .studio-statusbar{display:none'):
    assert token in v7css, token

print('FINAL_WORKFLOW_AUDIT_V7_TEST_PASSED')
