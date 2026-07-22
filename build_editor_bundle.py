#!/usr/bin/env python3
"""Build the no-tooling editor enhancement bundle from maintainable source modules."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
JS=[
 'canvas-plus.js','editor-builders.js','editor-pro.js','font-browser.js','photo-editor.js',
 'ai-assistant-pro.js','collaboration.js','creative-packs.js','collaboration-live.js'
]
CSS=[
 'canvas-plus.css','editor-builders.css','editor-pro.css','font-browser.css','photo-editor.css',
 'ai-assistant-pro.css','collaboration.css','creative-packs.css','collaboration-live.css'
]
def bundle(files,out,comment):
    chunks=[comment]
    for name in files:
        chunks.append(f'\n/* ===== {name} ===== */\n')
        chunks.append((ROOT/name).read_text(encoding='utf-8'))
    (ROOT/out).write_text(''.join(chunks),encoding='utf-8')
bundle(JS,'editor-suite.js','/* Generated editor runtime bundle. Edit source modules, then run build_editor_bundle.py. */\n')
bundle(CSS,'editor-suite.css','/* Generated editor style bundle. Edit source modules, then run build_editor_bundle.py. */\n')
print('EDITOR_BUNDLE_BUILT')
