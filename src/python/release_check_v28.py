#!/usr/bin/env python3
"""Codex-facing V28 full release gate.

This script intentionally emits no success marker unless the inherited gate and
all V28 focused suites pass without skips.
"""
from __future__ import annotations
import os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON=sys.executable
ENV={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','EINVITE_REQUIRE_BROWSER':'1'}
FOCUSED=[
 'tests/v28_agent_tool_contract_test.py',
 'tests/v28_agent_storage_test.py',
 'tests/v28_agent_provider_test.py',
 'tests/v28_agent_server_contract_test.py',
 'tests/v28_agent_registry_browser_test.py',
 'tests/v28_agent_conversation_browser_test.py',
 'tests/v28_agent_mobile_browser_test.py',
 'tests/v28_agent_performance_contract_test.py',
]
def run(label,cmd):
 print(f"\n{'='*72}\n{label}\n{'='*72}",flush=True)
 subprocess.run(cmd,cwd=ROOT,check=True,env=ENV)
def main()->int:
 run('1/7 Pristine editor bundle check',[PYTHON,'build_editor_bundle.py','--check'])
 run('2/7 Pristine route bundle check',[PYTHON,'build_route_bundles.py','--check'])
 run('3/7 Pristine page manifest check',[PYTHON,'build_page_manifests.py','--check'])
 run('4/7 Inherited V27.3.5 gate',[PYTHON,'release_check.py'])
 for index,test in enumerate(FOCUSED,1):run(f'5/7 V28 focused {index}/{len(FOCUSED)}',[PYTHON,test])
 run('6/7 Regenerated artifact recheck',[PYTHON,'build_editor_bundle.py','--check'])
 run('6/7b Route/page artifact recheck',[PYTHON,'build_route_bundles.py','--check']);run('6/7c Page manifest recheck',[PYTHON,'build_page_manifests.py','--check'])
 run('7/7 Complete shipped-file manifest verification',[PYTHON,'verify_v28_manifest.py'])
 print('\nEINVITATION_V28_ALL_REQUIRED_REVIEW_CHECKS_PASSED')
 print('EINVITATION_V28_RELEASE_CHECK_PASSED')
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except subprocess.CalledProcessError as exc:print(f'\nV28_RELEASE_CHECK_FAILED: {exc}',file=sys.stderr);raise SystemExit(exc.returncode or 1)
