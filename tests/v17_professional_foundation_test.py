#!/usr/bin/env python3
"""Deterministic architecture and migration checks for the V17 editor foundation."""
from __future__ import annotations
import json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    sources=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))
    index=sources['pages']['index.html']
    js=index['scripts'];css=index['styles']
    require(js.count('professional-editor-v17.js')==1,'professional editor JS must be bundled exactly once')
    require(css.count('professional-editor-v17.css')==1,'professional editor CSS must be bundled exactly once')
    require(js[-2:]==['professional-editor-v17.js','editor-responsive-contract-v27.js'],'professional editor must own transforms before the final responsive/focus contract')
    require(css[-4:]==['professional-editor-v17.css','zoom-layout-v22.css','graphics-runtime-v22.css','editor-responsive-contract-v27.css'],'professional styles must precede the dedicated zoom, GPU, and final responsive contract layers')

    professional=(ROOT/'professional-editor-v17.js').read_text(encoding='utf-8')
    command_system=(ROOT/'editor-command-system-v23.js').read_text(encoding='utf-8')
    style=(ROOT/'professional-editor-v17.css').read_text(encoding='utf-8')
    app=(ROOT/'app.js').read_text(encoding='utf-8')
    schema=(ROOT/'editor-schema-v13.js').read_text(encoding='utf-8')
    collaboration=(ROOT/'collaboration.js').read_text(encoding='utf-8')
    collaboration_live=(ROOT/'collaboration-live.js').read_text(encoding='utf-8')
    require('version:17' in professional and 'ownsPointerInteractions:true' in professional and 'ownsKeyboardInteractions:true' in professional,'authoritative ownership flags missing')
    for handle in ('nw','n','ne','e','se','s','sw','w'):
        require(f"'{handle}'" in professional, f'missing resize handle {handle}')
    for command in ('alignSelection','distributeSelection','groupSelection','ungroupSelection','copySelection','pasteSelection','duplicateSelection','deleteSelection','reorder'):
        require(command in professional,f'missing professional command {command}')
    require('bridge().transact' in professional,'commands must use the authoritative transaction bridge')
    require("window.addEventListener('keydown',keydown,true)" in professional or ("window.addEventListener('keydown',keydown,true)" in command_system and 'EInviteShortcutManager' in command_system),'V17 shortcuts must remain available through the authoritative V23 capture-phase manager')
    require('einvite:professional-command-committed' in professional,'committed commands must expose a deterministic completion event')
    require('getInvitationId({allowRemembered:false})' in collaboration and 'getInvitationId({allowRemembered:false})' in collaboration_live,'collaboration must never poll a remembered/demo invitation outside an explicit editor route')
    require("localStorage.getItem('sovan-active-invite')" not in collaboration_live,'live collaboration must not fall back to a cross-tab remembered invitation')
    require(('save({ history: false })' in app or 'save({history:false' in app) and 'pushHistory(state)' in app,'command history must commit once and save without delayed duplicate history')
    require("window.EInviteProfessionalEditor?.ownsPointerInteractions" in app,'legacy pointer path is not gated')
    require('const VERSION=13' in schema,'schema version must remain 13')
    require('body[data-page="index"]' in style and '.pe-selection-box' in style,'professional styles must be editor-scoped')
    require('README.md' not in professional,'unexpected documentation coupling')

    node_script=r"""
const fs=require('fs'),vm=require('vm');
global.window=global;global.structuredClone=global.structuredClone||((v)=>JSON.parse(JSON.stringify(v)));
vm.runInThisContext(fs.readFileSync(process.argv[2],'utf8'),{filename:'editor-schema-v13.js'});
const source={schemaVersion:12,objects:{shared:{type:'text',left:'12%',top:'18%',width:'40%',height:'10%',rotation:'bad',zIndex:2}},designPages:[{id:'p1',name:'Page',objects:{shared:{type:'image',left:'-2%',top:'bad',width:'-5%',height:'20%',zIndex:1}}}],sceneGraph:{groups:{g1:{name:'Nested',children:['shared'],locked:true,collapsed:true}}}};
const a=EInviteEditorSchema.migrate(structuredClone(source));
if(a.schemaVersion!==13)throw Error('schema version changed incorrectly');
const ids=Object.keys(a.sceneGraph.objects);
if(ids.length!==2||new Set(ids).size!==2)throw Error('scene IDs are not unique across pages');
if(!a.sceneGraph.objects.shared||!a.sceneGraph.objects['page:p1::shared'])throw Error('stable page-aware IDs missing');
for(const o of Object.values(a.sceneGraph.objects)){
 for(const key of ['left','top'])if(!Number.isFinite(parseFloat(o[key])))throw Error('invalid position '+key);
 for(const key of ['width','height']){const n=parseFloat(o[key]);if(!Number.isFinite(n)||n<=0)throw Error('invalid size '+key)}
 if(!Number.isFinite(Number(o.rotation)))throw Error('invalid rotation');
 if(typeof o.locked!=='boolean'||typeof o.visible!=='boolean')throw Error('visibility/locking normalization missing');
}
if(!a.sceneGraph.groups.g1.locked||!a.sceneGraph.groups.g1.collapsed)throw Error('group metadata lost');
if(!EInviteEditorSchema.validate(a).ok)throw Error('migrated graph invalid');
const b=EInviteEditorSchema.migrate(structuredClone(a));
if(JSON.stringify(Object.keys(a.sceneGraph.objects).sort())!==JSON.stringify(Object.keys(b.sceneGraph.objects).sort()))throw Error('migration IDs are not stable');
console.log('NODE_V17_SCHEMA_OK');
"""
    with tempfile.TemporaryDirectory(prefix='einvite-v17-node-') as tmp:
        script=Path(tmp)/'check.js';script.write_text(node_script,encoding='utf-8',newline='\n')
        result=subprocess.run(['node',str(script),str(ROOT/'editor-schema-v13.js')],cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace')
        require(result.returncode==0,result.stdout+result.stderr)
        require('NODE_V17_SCHEMA_OK' in result.stdout,'node migration check did not complete')

    print('V17_PROFESSIONAL_FOUNDATION_TEST_PASSED')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
