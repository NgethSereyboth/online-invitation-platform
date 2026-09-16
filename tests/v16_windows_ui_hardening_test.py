#!/usr/bin/env python3
"""Deterministic V16 Windows portability and UI-layer checks."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    subprocess.run([sys.executable,'build_route_bundles.py'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'build_route_bundles.py','--check'],cwd=ROOT,check=True)
    manifest=json.loads((ROOT/'route-bundles-v15.json').read_text(encoding='utf-8'))
    for page,item in manifest['pages'].items():
        for file_key,hash_key in [('javascript','scriptSha256'),('stylesheet','styleSha256')]:
            payload=(ROOT/item[file_key]).read_bytes()
            assert b'\r\n' not in payload,(page,item[file_key],'CRLF generated artifact')
            assert hashlib.sha256(payload).hexdigest()==item[hash_key],(page,item[file_key])
    source=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))['pages']['index.html']
    assert source['scripts'].count('windows-ui-v16.js')==1 and source['scripts'].index('windows-ui-v16.js')<source['scripts'].index('professional-editor-v17.js')
    assert source['styles'].count('windows-ui-v16.css')==1 and source['styles'].index('windows-ui-v16.css')<source['styles'].index('professional-editor-v17.css')
    css=(ROOT/'windows-ui-v16.css').read_text(encoding='utf-8')
    js=(ROOT/'windows-ui-v16.js').read_text(encoding='utf-8')
    editor_source=(ROOT/'canvas-plus.js').read_text(encoding='utf-8')
    dashboard_enhancements=(ROOT/'dashboard-enhancements.js').read_text(encoding='utf-8')
    for token in ('transform:none!important','workflow-page-chip:not(.active)','scrollbar-width:none','v16-toolbar-more-panel','safe-area-inset-bottom','#modal.final-dialog>.close{z-index:10001'):
        assert token in css,token
    for token in ('v16ToolbarMore','keepActivePageVisible','keepActiveToolVisible','#eiTimelineLaunch','#v13OperationsBtn'):
        assert token in js,token
    assert "window.__EINVITE_PAGE||document.body?.dataset.page||" in editor_source
    assert 'class="template-select-action"' in dashboard_enhancements
    assert "card.setAttribute('role','button')" not in dashboard_enhancements
    for filename in ('tests/v12_storage_privacy_test.py','tests/v12_immediate_stabilization_test.py'):
        text=(ROOT/filename).read_text(encoding='utf-8')
        assert 'closing(sqlite3.connect' in text,filename
        assert 'with sqlite3.connect' not in text,filename
    server=(ROOT/'server.py').read_text(encoding='utf-8')
    runner=(ROOT/'run_review_checks.py').read_text(encoding='utf-8')
    release=(ROOT/'release_check.py').read_text(encoding='utf-8')
    assert 'SIGBREAK' in server
    for text in (runner,release):
        assert "PYTHONUTF8':'1'" in text and "PYTHONIOENCODING':'utf-8'" in text
        assert "reconfigure(encoding='utf-8',errors='replace')" in text
    assert ('EINVITATION_V0_52_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V27_3_5_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V27_3_4_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_6_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_5_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_4_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_3_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_2_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V23_0_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_2_7_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_1_7_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_1_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V22_0_2_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner or 'EINVITATION_V21_3_ALL_REQUIRED_REVIEW_CHECKS_PASSED' in runner)
    assert ('EINVITATION_V0_52_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V27_3_5_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V27_3_4_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_6_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_5_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_4_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_3_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_2_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V23_0_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_2_7_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_1_7_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_1_3_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V22_0_2_RELEASE_CHECK_PASSED' in release or 'EINVITATION_V21_3_RELEASE_CHECK_PASSED' in release)
    shutdown=(ROOT/'tests/v15_integration_hardening_test.py').read_text(encoding='utf-8')
    assert 'CTRL_BREAK_EVENT' in shutdown and 'request_graceful_stop' in shutdown
    print('V16_WINDOWS_UI_HARDENING_TEST_PASSED')
    return 0
if __name__=='__main__':raise SystemExit(main())
