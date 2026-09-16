from pathlib import Path
import subprocess, textwrap
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'scene-model-v22.js'
def run(body):
    script=textwrap.dedent(f'''global.window=global;global.structuredClone=v=>JSON.parse(JSON.stringify(v));require({str(JS)!r});{body}''')
    return subprocess.run(['node','-e',script],capture_output=True,text=True,check=True).stdout

def test_migration_idempotence_and_tree_projection():
    out=run("""const d={objects:{b:{zIndex:2,type:'text'},a:{zIndex:1,type:'image',groupId:'g'}},sceneGraph:{groups:{g:{id:'g',children:['a']}}}};const g=EInviteSceneModel.migrate(d);if(!EInviteSceneModel.validate(g).ok)throw Error('invalid');const g2=EInviteSceneModel.migrate({sceneGraph:g});if(JSON.stringify(g)!==JSON.stringify(g2))throw Error('not idempotent');console.log(g.version,g.roots.hero.length,g.nodes.g.children[0]);""")
    assert out.strip()=='2 2 a'

def test_hostile_graphs_rejected():
    out=run("""const g={version:2,roots:{hero:['a']},nodes:{a:{id:'a',parentId:'',children:['b']},b:{id:'b',parentId:'a',children:['a']}}};const r=EInviteSceneModel.validate(g);if(r.ok||!r.errors.some(x=>x.includes('cycle')||x.includes('owned')))throw Error(r.errors.join('|'));console.log('ok');""")
    assert out.strip()=='ok'

def test_reorder_and_legacy_projection():
    out=run("""const d={objects:{a:{type:'text'},b:{type:'image'}}};let g=EInviteSceneModel.migrate(d);g=EInviteSceneModel.reorder(g,'b','',0);EInviteSceneModel.syncToLegacy(d,g);if(Object.keys(d.objects)[0]!=='b')throw Error('order');console.log('ok');""")
    assert out.strip()=='ok'
