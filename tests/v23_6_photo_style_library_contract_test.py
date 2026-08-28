#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'photo-style-library-v23.js').read_text(encoding='utf-8')
css=(ROOT/'photo-style-library-v23.css').read_text(encoding='utf-8')
loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8')
photo=(ROOT/'photo-workflow-v23.js').read_text(encoding='utf-8')
assets=(ROOT/'asset-workflow-v23.js').read_text(encoding='utf-8')
assert "const VERSION='23.6.3'" in js
for token in [
 'einvite-photo-styles-v23','MAX_STYLES=36','MAX_LIBRARY_BYTES=900000',
 'photoStyles.open','photoStyles.saveSelected','photoStyles.applyPage',
 "bridge.transact(`Apply photo style: ${style.name}`",'photo.applyLookToObject',
 'photo.projectLookToNode','data-preview-style','data-apply-style',
 'data-export-styles','data-import-styles','Every image on this page',
 'EInviteLifecycle','einvite:photo-styles-changed'
]:
 assert token in js,token
assert "window.addEventListener('keydown'" not in js
assert "document.addEventListener('keydown'" not in js
assert 'photo-style-library-v23.js' in loader
assert loader.index('photo-workflow-v23.js') < loader.index('photo-style-library-v23.js')
for token in ['normalizeLook:copyLookData','applyLookToObject','projectLookToNode','get lookFields()']:
 assert token in photo,token
assert "commandButton('photoStyles.open','Photo styles')" in assets
for token in ['.v23-photo-style-dialog','.v23-photo-style-list','.v23-photo-style-card','.v23-photo-style-previewing','.v23-photo-style-toolbar']:
 assert token in css,token
assert js.count("id:'photoStyles.open'")==1
print('V23_6_PHOTO_STYLE_LIBRARY_CONTRACT_PASSED')
