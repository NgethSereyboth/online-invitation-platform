"""Unit checks for the V13 scene graph migration and command-friendly schema."""
from __future__ import annotations
import json, subprocess, textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run():
    script=textwrap.dedent(r'''
      const fs=require('fs'),vm=require('vm');global.window={};global.structuredClone=global.structuredClone||((v)=>JSON.parse(JSON.stringify(v)));
      vm.runInThisContext(fs.readFileSync('editor-schema-v13.js','utf8'));
      const doc={schemaVersion:10,objects:{title:{type:'text',html:'Hero'}},designPages:[{id:'one',name:'One',objects:{title:{type:'text',html:'Page'}}}],sectionOrder:['page:one']};
      const migrated=window.EInviteEditorSchema.migrate(doc);
      if(migrated.schemaVersion!==13)throw Error('schema migration failed');
      const ids=Object.keys(migrated.sceneGraph.objects);if(ids.length!==2||new Set(ids).size!==2)throw Error('scene object collision');
      const hero=migrated.sceneGraph.pages.find(x=>x.id==='hero'),page=migrated.sceneGraph.pages.find(x=>x.id==='page:one');
      if(hero.objectIds[0]===page.objectIds[0])throw Error('canvas object IDs are not globally stable');
      migrated.sceneGraph.objects[page.objectIds[0]].html='Changed';window.EInviteEditorSchema.syncGraphToLegacy(migrated);
      if(migrated.designPages[0].objects.title.html!=='Changed')throw Error('graph to legacy mapping lost legacy object key');
      const check=window.EInviteEditorSchema.validate(migrated);if(!check.ok)throw Error(check.error);
      console.log('V13_EDITOR_MODEL_NODE_PASSED');
    ''')
    result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True,check=True)
    assert 'V13_EDITOR_MODEL_NODE_PASSED' in result.stdout
    print('V13_EDITOR_MODEL_TEST_PASSED')
if __name__=='__main__':run()
