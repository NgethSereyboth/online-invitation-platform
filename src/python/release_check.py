#!/usr/bin/env python3
"""Build and verify the cumulative E-invitation V0.52 release."""
from __future__ import annotations
import os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PYTHON=sys.executable

def configure_utf8_console():
 for stream in (sys.stdout,sys.stderr):
  reconfigure=getattr(stream,'reconfigure',None)
  if reconfigure:
   try:reconfigure(encoding='utf-8',errors='replace')
   except (ValueError,OSError):pass

configure_utf8_console()
CHILD_ENV={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
if os.name=='nt' and CHILD_ENV.get('OPENSSL_CONF') and not Path(CHILD_ENV['OPENSSL_CONF']).is_file():
 print(f"Ignoring invalid OPENSSL_CONF for release child processes: {CHILD_ENV['OPENSSL_CONF']}",flush=True);CHILD_ENV.pop('OPENSSL_CONF',None)

def run(label,command):
 print(f"\n{'='*72}\n{label}\n{'='*72}",flush=True);subprocess.run(command,cwd=ROOT,check=True,env=CHILD_ENV)

def main():
 # A pristine extraction must pass every check-only stage before regeneration.
 run('0/16 Pristine check-only: editor bundle/source integrity',[PYTHON,'build_editor_bundle.py','--check'])
 run('1/16 Pristine check-only: route bundle/source integrity',[PYTHON,'build_route_bundles.py','--check'])
 run('2/16 Pristine check-only: page manifest and performance budgets',[PYTHON,'build_page_manifests.py','--check'])
 print('V0_52_PRISTINE_CHECK_ONLY_STAGE_PASSED',flush=True)
 run('3/16 Generate trusted typography contract',[PYTHON,'generate_typography_contract.py'])
 run('4/16 Generate structured rich-text contract',[PYTHON,'generate_rich_text_contract.py'])
 run('5/16 Regenerate deterministic editor bundle',[PYTHON,'build_editor_bundle.py'])
 run('6/16 Verify regenerated editor bundle/source integrity',[PYTHON,'build_editor_bundle.py','--check'])
 run('7/16 Regenerate deterministic route bundles',[PYTHON,'build_route_bundles.py'])
 run('8/16 Verify regenerated route bundle/source integrity',[PYTHON,'build_route_bundles.py','--check'])
 run('9/16 Regenerate route-specific page asset manifest',[PYTHON,'build_page_manifests.py'])
 run('10/16 Verify regenerated page manifest and performance budgets',[PYTHON,'build_page_manifests.py','--check'])
 print('V0_52_REGENERATE_THEN_CHECK_STAGE_PASSED',flush=True)
 run('11/16 Compile Python sources',[PYTHON,'-m','compileall','-q','server.py','security_v13.py','media_worker.py','backup_restore.py','build_editor_bundle.py','build_route_bundles.py','build_page_manifests.py','generate_typography_contract.py','generate_rich_text_contract.py','typography_contract.py','typography_document_model.py','rich_text_contract.py','rich_text_document_model.py','run_review_checks.py','release_check.py','tests'])
 node=shutil.which('node')
 if not node:raise RuntimeError('Node.js is required for JavaScript syntax checks. Run SETUP_EINVITE_COMPLETE.bat first.')
 js_files=sorted(ROOT.glob('*.js'));print(f"\n{'='*72}\n12/16 Check {len(js_files)} top-level JavaScript files\n{'='*72}",flush=True)
 for path in js_files:subprocess.run([node,'--check',str(path)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL,env=CHILD_ENV)
 print('JAVASCRIPT_SYNTAX_CHECKS_PASSED',flush=True)
 run('13/16 Verify required release dependencies and launch Chromium',[PYTHON,'dependency_preflight.py'])
 run('14/16 Run all deterministic and required live-browser checks',[PYTHON,'run_review_checks.py'])
 run('15/16 Recheck generated artifacts after the full gate',[PYTHON,'build_editor_bundle.py','--check'])
 run('16/16 Recheck route/page artifacts after the full gate',[PYTHON,'build_route_bundles.py','--check'])
 run('16/16b Recheck page manifest after the full gate',[PYTHON,'build_page_manifests.py','--check'])
 print('\nEINVITATION_V0_52_RELEASE_CHECK_PASSED',flush=True)
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except subprocess.CalledProcessError as exc:print(f'\nRELEASE_CHECK_FAILED: {exc}',file=sys.stderr);raise SystemExit(exc.returncode or 1)
 except Exception as exc:print(f'\nRELEASE_CHECK_FAILED: {exc}',file=sys.stderr);raise SystemExit(1)
