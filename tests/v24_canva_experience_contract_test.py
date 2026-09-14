#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
modules={
 'direct-manipulation-v24.js':['version:24.1','text.editInline','image.cropInline','bridge.transact'],
 'content-browser-v24.js':['version:24.2','content.open','content.openElements','content.openPages','EInviteAssetWorkflow'],
 'smart-layout-v24.js':['version:24.3','layout.open','layout.stackVertical','layout.diagnostics','responsiveConstraints'],
 'brand-components-v24.js':['version:24.4','brand.open','component.saveSelection','einvite-v24-event-brand-kits','sovan-reusable-element-groups-v1'],
 'collaboration-v24.js':['version:24.5','collaboration.open','collaboration.exportSummary','einvite-v24-review-assignments'],
 'export-quality-v24.js':['version:24.6','quality.open','export.currentPng','export.projectBackup','missing-alt','review-policy'],
}
for name,tokens in modules.items():
 text=(ROOT/name).read_text(encoding='utf-8')
 for token in tokens:assert token in text,(name,token)
 assert "window.addEventListener('keydown'" not in text,name
for name in ['direct-manipulation-v24.css','content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']:
 assert (ROOT/name).stat().st_size>500,name
loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8')
order=['workspace-experience-v24.js',*modules.keys()]
for name in order:assert name in loader,name
assert [loader.index(x) for x in order]==sorted(loader.index(x) for x in order)
assert loader.count('direct-manipulation-v24.js')==1
print('V24_CANVA_EXPERIENCE_CONTRACT_TEST_PASSED')
