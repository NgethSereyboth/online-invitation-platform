#!/usr/bin/env python3
from __future__ import annotations
import copy,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from typography_document_model import normalize_document_typography
from typography_contract import MAX_TEXT_STYLES

def rejected(doc):
 try:normalize_document_typography(copy.deepcopy(doc),strict=True)
 except (ValueError,TypeError):return True
 return False

def main():
 contract=json.loads((ROOT/'typography-contract.json').read_text())
 assert contract['maxTextStyles']==MAX_TEXT_STYLES==64
 styles={f'style-{i}':{'id':f'style-{i}','name':f'Style {i}','semantic':'body'} for i in range(65)}
 assert rejected({'typography':{'styles':styles,'styleOrder':list(styles)},'objects':{},'designPages':[]})
 hostile={'typography':{'styles':{}},'objects':{'x':{'type':'text','html':'x','typographyModelVersion':1,'textStyleId':'body','fontPairing':'sans-modern','font':'Arial;position:fixed'}},'designPages':[]}
 assert rejected(hostile)
 legacy={'objects':{'x':{'type':'text','html':'x','font':'Arial, sans-serif'}},'designPages':[]}
 assert normalize_document_typography(legacy,strict=True)['objects']['x']['font']=='sans-arial'
 dashboard=(ROOT/'dashboard.js').read_text()
 assert 'function hydrateDashboardThumbnails()' in dashboard
 render=dashboard[dashboard.index('function render()'):dashboard.index('function show()',dashboard.index('function render()'))] if dashboard.find('function show()',dashboard.index('function render()'))>0 else dashboard[dashboard.index('function render()'):]
 assert render.index("document.querySelectorAll('[data-edit]')") < render.index('hydrateDashboardThumbnails()')
 assert 'dashboardThumbnailControllers' in dashboard and 'disconnectDashboardThumbnails' in dashboard
 polish=(ROOT/'final-polish.js').read_text();assert "!art.closest('.invite-card')" in polish
 app=(ROOT/'app.js').read_text()
 for token in ("textStyleId:'display'","textStyleId:'subheading'","textStyleId:'body'","id:'hero',type:'image'"):assert token in app
 editor=(ROOT/'typography-editor-v20.js').read_text();refresh=editor[editor.index('function refresh()'):]
 assert 'normalizeDocument(doc,{mutate:true})' not in refresh.split('function ',1)[0]
 assert 'data-style-limit-action' in editor and 'MAX_TEXT_STYLES' in editor
 layout=(ROOT/'typography-layout-service.js').read_text();assert "return null" in layout[layout.index('function effectiveBackground'):layout.index('function diagnose')]
 assert 'contrast-undetermined' in layout
 public=(ROOT/'public-page.js').read_text();assert 'projectTypography=async lang' in public and 'ensureReady?.([model.font])' in public and 'locale:lang' in public
 req=(ROOT/'requirements-test.txt').read_text().lower();assert 'fonttools' in req and 'brotli' in req
 pre=(ROOT/'dependency_preflight.py').read_text();assert 'verify_woff2_decode' in pre and ('V0.52 dependency preflight passed.' in pre or 'V27.3.5 dependency preflight passed' in pre or 'V27.3.4 dependency preflight passed' in pre or 'V27.3.3 dependency preflight passed' in pre or 'V26.3.3 dependency preflight passed' in pre or 'V25.3.3 dependency preflight passed' in pre or 'V24.6.3 dependency preflight passed' in pre or 'V23.8.3 dependency preflight passed' in pre or 'V23.7.3 dependency preflight passed' in pre or 'V23.6.3 dependency preflight passed' in pre or 'V23.5.3 dependency preflight passed' in pre or 'V23.4.3 dependency preflight passed' in pre or 'V23.0.3 dependency preflight passed' in pre or 'V22.2.8 dependency preflight passed' in pre or 'V22.2.7 dependency preflight passed' in pre or 'V22.1.7 dependency preflight passed' in pre or 'V22.1.3 dependency preflight passed' in pre or 'V22.0.3 dependency preflight passed' in pre or 'V22.0.2 dependency preflight passed' in pre or 'V21.3 dependency preflight passed' in pre)
 release=(ROOT/'release_check.py').read_text();runner=(ROOT/'run_review_checks.py').read_text()
 assert ('EINVITATION_V0_52_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V27_3_5_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V27_3_4_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V27_3_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V26_3_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V25_3_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V24_6_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_8_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_7_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_6_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_5_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_4_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_3_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_2_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_0_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_2_7_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_1_7_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_1_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_0_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_0_2_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V21_3_RELEASE_CHECK_PASSED' in release) and 'EINVITATION_V20_1_RELEASE_CHECK_PASSED' not in release and 'EINVITATION_V19_1_RELEASE_CHECK_PASSED' not in release
 assert ('EINVITATION_V0_52_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V27_3_5_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V27_3_4_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V27_3_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V26_3_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V25_3_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V24_6_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_8_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_7_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_6_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_5_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_4_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_3_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_2_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_0_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_2_7_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_1_7_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_1_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_0_2_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V21_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner) and 'EINVITATION_V20_1_ALL_REQUIRED_REVIEW_CHECKS_PASSED' not in runner and 'EINVITATION_V19_1_ALL_REQUIRED_REVIEW_CHECKS_PASSED' not in runner
 assert 'EINVITE_TEST_TEARDOWN_SECONDS' in runner and 'process.poll() is not None:return' not in runner
 print('V20_1_STABILIZATION_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
