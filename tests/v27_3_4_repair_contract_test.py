#!/usr/bin/env python3
"""Static compatibility contract for the cumulative V27.3.4 repair inside V0.52."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def text(name:str)->str:return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 info=json.loads(text('BUILD_INFO.json'))
 assert info['version']=='0.52' and int(info.get('internalMilestone',0))>=27 and info['schemaVersion']>=14,info
 assert info.get('compatibilityFloor') in {'V27.3.4','V27.3.5'} or 'V27.3.5' in info.get('implementedMilestones',[])
 sources=json.loads(text('route-bundle-sources-v15.json'))['pages']['index.html']
 assert 'workflow-creation-flow-v4.js' in sources['scripts'] and 'workflow-creation-flow-v4.css' in sources['styles']
 assert not any('workflow-creation-flow-v3' in item for item in sources['scripts']+sources['styles'])
 assert 'graphics-runtime-v22.css' in sources['styles']
 assert sources['scripts'][-1]=='editor-responsive-contract-v27.js'
 assert sources['styles'][-1]=='editor-responsive-contract-v27.css'
 assets=json.loads(text('page-assets-v15.json'))['pages']['index.html'];assert assets['bytes']<=1_420_000,assets
 webgl=text('webgl-scene-backend-v22.js');assert 'style.remove()' not in webgl and "createElement('style')" not in webgl and 'createElement("style")' not in webgl
 assert all(event in webgl for event in ('pointercancel','lostpointercapture','visibilitychange','blur'))
 adaptive=text('adaptive-gpu-quality-v22.js');assert "createElement('style')" not in adaptive and 'createElement("style")' not in adaptive
 audit=text('workflow-final-audit-v7.js');assert "const dock=$('#workflowPageDock')" in audit and 'dock?' in audit
 review=text('review-v23.js');assert 'window.EInviteBackend?.isAvailable?.()===true' in review
 assert 'window.fetch' not in review.split('const backendOnline=',1)[1].split(';',1)[0]
 rich=text('rich-text-editing-v21.js');assert 'insertLiteralTab' in rich and "'\\t'" in rich
 final=text('final-experience.js');assert 'einvite-final-tour-seen-v2:' in final and 'einvite-final-tour-seen-v1' in final
 responsive=text('editor-responsive-contract-v27.js');assert 'const M=820,C=1180' in responsive
 for command in ([sys.executable,'build_editor_bundle.py','--check'],[sys.executable,'build_route_bundles.py','--check'],[sys.executable,'build_page_manifests.py','--check']):subprocess.run(command,cwd=ROOT,check=True)
 print('V27_3_4_REPAIR_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
