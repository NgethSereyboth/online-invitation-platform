#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'navigation-history-v23.js').read_text(encoding='utf-8')
css=(ROOT/'navigation-history-v23.css').read_text(encoding='utf-8')
loader=(ROOT/'professional-workflow-loader-v23.js').read_text(encoding='utf-8')
required=['selection.cycleForward','selection.targetMode','page.viewList','page.copyComplete','page.pasteComplete','history.checkpoints','MAX_CHECKPOINTS=12','MAX_SNAPSHOT_BYTES','einvite-editor-v23']
missing=[x for x in required if x not in js]
assert not missing,missing
assert 'navigation-history-v23.js' in loader
assert 'data-page-view' in css and 'v23-checkpoint-dialog' in css
print('V23_2_NAVIGATION_HISTORY_CONTRACT_PASSED')
