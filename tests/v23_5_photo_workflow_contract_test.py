#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'photo-workflow-v23.js').read_text(encoding='utf-8')
css=(ROOT/'photo-workflow-v23.css').read_text(encoding='utf-8')
loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8')
assets=(ROOT/'asset-workflow-v23.js').read_text(encoding='utf-8')
assert "const VERSION='23.5.3'" in js
for token in [
 'image.editPhoto','image.copyLook','image.pasteLook','image.resetAdjustments',
 "bridge.transact('Apply photo edits'",'{capture:false}','Hold for before',
 'data-preset-intensity','imagePositionX','imagePositionY','imageMask','imageFrame',
 'EInviteRenderer?.imageFilterStyle','EInviteRenderer?.imageTransformStyle','EInviteRenderer?.imageMaskStyle',
 'window.openEInvitePhotoEditor=open','EInviteLifecycle'
]:
 assert token in js,token
assert "window.addEventListener('keydown'" not in js
assert "document.addEventListener('keydown'" not in js
assert 'photo-workflow-v23.js' in loader
assert loader.index('asset-workflow-v23.js') < loader.index('photo-workflow-v23.js')
assert "commandButton('image.editPhoto','Edit photo',true)" in assets
for token in ['.v23-photo-workflow','.v23-photo-presets','.v23-photo-preview','.v23-photo-composition','.photo-workflow-v23']:
 assert token in css,token
assert js.count("id:'image.editPhoto'")==1
print('V23_5_PHOTO_WORKFLOW_CONTRACT_PASSED')
