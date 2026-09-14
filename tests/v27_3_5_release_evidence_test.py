#!/usr/bin/env python3
"""Cumulative V27.3.5 compatibility and V0.52 release-evidence contract."""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
README_SHA='f3c158d37f1ab2367a4bd0565c230535369596431709cbbd3cb234c324633330'
MANIFEST='V0_52_RELEASE_FILE_HASHES.sha256'
DOCS={'V0_52_ARCHITECTURE.md','V0_52_CHANGELOG.md','V0_52_TEST_MATRIX.md','V0_52_KNOWN_LIMITATIONS.md','V0_52_IMPLEMENTATION_STATUS.md','V0_52_CODEX_TEST_HANDOFF.md','V0_52_CHANGED_FILES.md'}
REQUIRED_TESTS={'v53_1_operator_repair_contract_test.py','v53_1_ai_project_operator_backend_test.py','v27_3_5_ai_transaction_browser_test.py','v27_3_5_ai_rich_text_browser_test.py','v27_3_5_ai_target_revision_test.py','v27_3_5_ai_layout_preview_test.py','v27_3_5_ai_accessibility_mobile_test.py','v27_3_5_ai_backend_contract_test.py','v27_3_5_mobile_canvas_hud_test.py','v27_3_5_release_evidence_test.py','v27_3_5_typography_preview_sequence_test.py','v28_agent_server_contract_test.py','v28_agent_performance_contract_test.py','v30_raster_workspace_contract_test.py','v31_collaboration_contract_test.py','v32_platform_contract_test.py','v0_52_remaining_fixes_contract_test.py','v0_52_asset_identity_test.py','v0_52_production_deployment_hardening_test.py','v0_52_security_boundary_test.py','v0_52_upload_permission_test.py','v0_52_multi_host_deployment_test.py','v0_52_platform_dark_mode_browser_test.py','v0_52_public_lazy_loader_browser_test.py','v30_raster_worker_browser_test.py','v0_52_ai_real_server_test.py','v0_52_ai_live_browser_test.py','v0_52_dashboard_cover_navigation_test.py','v0_52_autosave_status_test.py','v0_52_publish_barrier_server_test.py','v0_52_publish_autosave_barrier_browser_test.py'}
REQUIRED_TESTS.add('v0_52_first_time_setup_contract_test.py')
REQUIRED_TESTS.add('v0_52_free_canvas_drag_test.py')
FORBIDDEN_PARTS={'__pycache__','.pytest_cache','.cache'};FORBIDDEN_NAMES={'.upload-signing-secret','.media-signing-secret','.guest-token-secret'};FORBIDDEN_SUFFIXES={'.pyc','.pyo','.pid','.log','.db','.sqlite','.sqlite3'}
def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def verify_manifest():
 path=ROOT/MANIFEST;assert path.exists(),MANIFEST;entries={};pattern=re.compile(r'^([0-9a-f]{64})  (.+)$')
 for number,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
  match=pattern.fullmatch(line);assert match,(number,line);rel=match.group(2);assert rel not in entries,rel;entries[rel]=match.group(1);p=Path(rel)
  assert not(set(p.parts)&FORBIDDEN_PARTS) and p.name not in FORBIDDEN_NAMES and p.suffix.lower() not in FORBIDDEN_SUFFIXES,rel
 expected=sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!=MANIFEST and not(set(p.relative_to(ROOT).parts)&FORBIDDEN_PARTS) and p.name not in FORBIDDEN_NAMES and p.suffix.lower() not in FORBIDDEN_SUFFIXES)
 assert sorted(entries)==expected,(len(entries),len(expected),set(expected)-set(entries),set(entries)-set(expected))
 for rel,want in entries.items():assert digest(ROOT/rel)==want,rel
def main()->int:
 info=json.loads((ROOT/'BUILD_INFO.json').read_text(encoding='utf-8'));assert info['version']=='0.52' and info['build']=='intelligent-event-ecosystem-v0.52' and info['schemaVersion']==27
 assert int(info.get('internalMilestone',0))>=52 and 'V27.3.5' in info.get('implementedMilestones',[]) and 'V52' in info.get('implementedMilestones',[])
 assert info.get('compatibilityFloor')=='V27.3.5';assert 'pending' in info['certification']['releaseCertification'].lower()
 assert set(info['requiredPendingMarkers'])=={'EINVITATION_V0_52_ALL_REQUIRED_REVIEW_CHECKS_PASSED','EINVITATION_V0_52_RELEASE_CHECK_PASSED','EINVITATION_V0_52_WINDOWS_RELEASE_CHECK_PASSED','EINVITATION_V0_52_LINUX_RELEASE_CHECK_PASSED'}
 assert not set(info['requiredPendingMarkers']).intersection(info.get('releaseMarkers',[]));assert digest(ROOT/'README.md')==README_SHA
 routes=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'));scripts=routes['pages']['index.html']['scripts'];styles=routes['pages']['index.html']['styles']
 assert 'editor-deferred-tools-bootstrap-v0_52.js' in scripts and 'ai-editor-action-service-v27.js' in scripts
 for heavy in ['ai-assistant-loader-v27.js','ai-creative-agent-v28.js','ai-agent-tool-registry-v28.js','advanced-editor-loader-v32.js','font-browser-loader-v22.js']:assert heavy not in scripts,heavy
 bootstrap=(ROOT/'editor-deferred-tools-bootstrap-v0_52.js').read_text(encoding='utf-8');assert all(x in bootstrap for x in ('ai-assistant-loader-v27.js','advanced-editor-loader-v32.js','font-browser-loader-v22.js'))
 loader=(ROOT/'ai-assistant-loader-v27.js').read_text(encoding='utf-8');assert 'ai-creative-agent-v28.js' in loader and 'ai-agent-tool-registry-v28.js' in loader and 'ai-creative-agent-v28.css' in loader
 agent=(ROOT/'ai-creative-agent-v28.js').read_text(encoding='utf-8');assert '<style' not in agent.lower() and "createElement('style')" not in agent and 'Regenerate with current selection' in agent and 'Preview against current selection' in agent
 service=(ROOT/'ai-editor-action-service-v27.js').read_text(encoding='utf-8');assert "type==='replaceText'" in service and 'bridge().transact' in service and 'STALE_REVISION' in service and 'crypto.randomUUID' in service
 server=(ROOT/'server.py').read_text(encoding='utf-8');assert 'providerMode":"connected"' in server and 'providerMode":"fallback"' in server and 'provider":"template"' in server
 size=(ROOT/'bundle-index-v15.js').stat().st_size+(ROOT/'bundle-index-v15.css').stat().st_size;assert size<=1_420_000,(size,1_420_000);assert info['certification']['editorRouteBytes']==size and info['certification']['editorRouteHeadroom']==1_420_000-size
 for name in REQUIRED_TESTS:assert (ROOT/'tests'/name).exists(),name
 for name in DOCS:assert (ROOT/name).exists(),name
 review=(ROOT/'run_review_checks.py').read_text(encoding='utf-8');release=(ROOT/'release_check.py').read_text(encoding='utf-8');assert 'EINVITATION_V0_52_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in review and '--continue-on-failure' in review;assert 'EINVITATION_V0_52_RELEASE_CHECK_PASSED' in release
 verify_manifest()
 for cmd in [['build_editor_bundle.py','--check'],['build_route_bundles.py','--check'],['build_page_manifests.py','--check']]:subprocess.run([sys.executable,str(ROOT/cmd[0]),*cmd[1:]],check=True,cwd=ROOT)
 print(f'V0_52_EDITOR_ROUTE_BYTES={size}');print('V27_3_5_RELEASE_EVIDENCE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
