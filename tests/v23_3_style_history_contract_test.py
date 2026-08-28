#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'style-history-v23.js').read_text(encoding='utf-8')
css=(ROOT/'style-history-v23.css').read_text(encoding='utf-8')
loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8')
required=['styleKits.open','styleKits.saveCurrent','history.compareCheckpoint','MAX_KITS=24','MAX_KIT_BYTES=300000','beginPreview','applyToDocument','applyToPage','applyToSelection','thumbnailSvg','compareDocuments']
missing=[x for x in required if x not in js]
assert not missing,missing
assert 'navigation-history-v23.js' in loader and 'style-history-v23.js' in loader
assert 'v23-style-kit-dialog' in css and 'v23-checkpoint-thumb' in css and 'v23-history-compare' in css
print('V23_3_STYLE_HISTORY_CONTRACT_PASSED')
