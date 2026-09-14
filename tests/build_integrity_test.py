#!/usr/bin/env python3
"""Verify generated editor artifacts are reproducible and loaded exactly once."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run():
    subprocess.run([sys.executable,str(ROOT/'build_editor_bundle.py'),'--check'],cwd=ROOT,check=True)
    bundle=(ROOT/'editor-suite.js').read_text(encoding='utf-8')
    styles=(ROOT/'editor-suite.css').read_text(encoding='utf-8')
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    route_sources=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))['pages']['index.html']['scripts']
    assert '/* ===== collaboration.js ===== */' not in bundle
    assert '/* ===== collaboration-live.js ===== */' not in bundle
    assert '/* ===== collaboration.css ===== */' in styles
    assert '/* ===== collaboration-live.css ===== */' in styles
    assert route_sources.count('collaboration.js')==1
    assert route_sources.count('collaboration-live.js')==1
    assert html.count('<script src="bundle-index-v15.js"></script>')==1
    commands=(ROOT/'editor-command-system-v23.js').read_text(encoding='utf-8')
    assert route_sources.count('editor-command-system-v23.js')==1
    assert route_sources.index('editor-command-system-v23.js')<route_sources.index('app.js')
    assert "window.addEventListener('keydown',keydown,true)" in commands
    assert 'EInviteRenderer?.sanitizeRichText' in bundle
    print('BUILD_INTEGRITY_TEST_PASSED')

if __name__=='__main__':run()
