#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'asset-workflow-v23.js').read_text(encoding='utf-8')
css=(ROOT/'asset-workflow-v23.css').read_text(encoding='utf-8')
loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8')
assert "version:23.4" in js
for token in ['assets.open','assets.replaceSelected','assets.insertImage','openMaterialPicker','IntersectionObserver','pointerdown','einvite:asset-library-changed','EInviteFeedback','v23ContextToolbar']:
 assert token in js,token
assert 'asset-workflow-v23.js' in loader
for token in ['.v23-asset-browser','.v23-context-toolbar','.v23-activity-host','.v23-asset-drop-target']:
 assert token in css,token
print('V23_4_ASSET_WORKFLOW_CONTRACT_PASSED')
