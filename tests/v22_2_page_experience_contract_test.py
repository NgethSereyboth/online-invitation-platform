#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
js = (ROOT / "src" / "js" / "page-experience.js").read_text(encoding='utf-8')
css = (ROOT / "src" / "css" / "page-experience.css").read_text(encoding='utf-8')
loader = (ROOT / "src" / "js" / "performance-observability.js").read_text(encoding='utf-8')
workspace = (ROOT / "src" / "css" / "workspace.css").read_text(encoding='utf-8')
html = (ROOT / "src" / "html" / "index.html").read_text(encoding='utf-8')
combined = js + css + workspace

required = [
    "const VERSION='22.2.8'",
    'free-design',
    'event-template',
    'Add page here',
    'Reorder pages',
    'Move to first page',
    'IntersectionObserver',
    'requestIdleCallback',
    'content-visibility:auto',
    'contain:layout paint style',
    'window.renderEditorManagers=deferredManagers',
    "event.altKey||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)",
    'beginDockPointerReorder',
    "card.draggable=false",
    'v22-quick-preview',
    'renderQuickThumbnail',
    'capture:false',
    'Apply event page layout',
    'v22-page-drag-handle',
    'pendingRenderOptions',
    'activeInsertIndex()',
    '.v22-workflow-insert',
    '.v22-page-manager',
    '#workflowPageDock .workflow-v6-order-badge',
]
for term in required:
    assert term in combined, f'missing V22.2 contract term: {term}'
commands=(ROOT / "src" / "js" / "editor-command-system.js").read_text(encoding='utf-8')
assert "id:'page.addBlank'" in commands and "Mod+Enter" in commands
assert 'page-experience.js' in loader
assert 'page-experience.css' not in loader, 'CSS must not be injected by the deferred loader'
assert 'dataTransfer' not in js, 'Page reorder must not rely on browser-specific HTML5 drag/drop'
assert '72dvh' in workspace and '640px' in workspace
assert '.v22-page-dock' not in combined, 'A second competing page dock must not be introduced'
print('V22_2_PAGE_EXPERIENCE_CONTRACT_TEST_PASSED')

app=(ROOT / "src" / "js" / "app.js").read_text(encoding='utf-8')
assert 'capture: options.capture !== false' in app or 'capture:options.capture!==false' in app
assert "if (options.capture !== false) capture();" in app or 'if(options.capture!==false)capture();' in app


def test_editor_first_paint_boot_invariants():
    # P1 first-paint guard: the stylesheet and the final Pages-manager position ship in
    # the document. Injecting either after DOMContentLoaded moved the manager and the
    # page grid; measured CLS 0.5287 -> 0.4194 after these two changes.
    assert 'href="page-experience.css" data-v22-page-experience' in html
    assert 'id="designPagesManager" class="design-pages-manager" data-studio-group="pages"' in html
    assert html.index('id="designPagesManager"') < html.index('<h2>Invitation sections</h2>')
