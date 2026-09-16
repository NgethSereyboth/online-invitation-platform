#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 core=(ROOT/'editor-command-system-v23.js').read_text(encoding='utf-8')
 ui=(ROOT/'command-palette-v23.js').read_text(encoding='utf-8')
 css=(ROOT/'command-palette-v23.css').read_text(encoding='utf-8')
 sources=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))
 index=sources['pages']['index.html']
 js=index['scripts'] if isinstance(index,dict) else index
 assert 'editor-command-system-v23.js' in js
 assert js.index('editor-command-system-v23.js') < js.index('app.js')
 assert 'command-palette-v23.js' not in js and 'command-palette-v23.css' not in js
 assert "version:'23.0.0'" in core and "version:'23.0.1'" in core
 assert "version:'23.0.3'" in ui
 assert 'registerMany' in core and 'validateOverride' in core and 'setProfile' in core
 assert all(name in core for name in ('standard','canva','photoshop'))
 assert 'window.EInviteCanvasPanController' in core and 'window.EInviteCanvasPanController' in (ROOT/'app.js').read_text(encoding='utf-8')
 assert 'data-capturing' in core and 'data-capturing' not in ui.replace("surface.dataset.capturing='true'",'').replace('delete surface.dataset.capturing','')
 assert '.v23-command-surface' in css and '.v23-shortcut-item' in css

 # Only the V23 command system may own a window-level editor keydown listener.
 owners=['app.js','canvas-plus.js','editor-pro.js','professional-editor-v17.js','editor-canva-v13.js','page-experience-v22.js','studio-experience.js','modern-ui.js','final-experience.js','workflow-continuity.js','workflow-creation-flow-v4.js','workflow-final-audit-v7.js','workflow-pro-editor-v6.js','workflow-ux-v5.js','ai-assistant-pro.js']
 for name in owners:
  text=(ROOT/name).read_text(encoding='utf-8')
  assert not re.search(r"window\.addEventListener\(['\"]keydown",text),name
 assert "window.addEventListener('keydown',keydown,true)" in core
 assert "window.addEventListener('keyup',keyup,true)" in core

 # Core Photoshop-style recommendations and compatibility shortcuts are registered once.
 for command_id in ('canvas.panHold','canvas.actualSize','workspace.hidePanels','arrange.backward','arrange.forward','arrange.back','arrange.front','object.toggleLock','object.toggleVisibility','ui.quickActions','ui.shortcutSettings'):
  assert f"id:'{command_id}'" in core,command_id
 for chord in ('Shift+E','Shift+T','Shift+U','Shift+F','Mod+1','Mod+[','Mod+]','Mod+Shift+[','Mod+Shift+]'):
  assert chord in core,chord
 print('V23_COMMAND_REGISTRY_TEST_PASSED')
 return 0
if __name__=='__main__':sys.exit(main())
