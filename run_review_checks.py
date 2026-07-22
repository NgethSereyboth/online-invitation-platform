#!/usr/bin/env python3
"""Run all deterministic review checks available without external provider credentials."""
from __future__ import annotations
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CHECKS=[
 'tests/static_integrity_test.py',
 'tests/smoke_test.py',
 'tests/plan_limit_test.py',
 'tests/final_features_test.py',
 'tests/production_foundations_test.py',
 'tests/provider_adapters_test.py',
 'tests/realtime_storage_test.py',
 'tests/signed_upload_backend_test.py',
    'tests/final_visual_polish_test.py',
]
for script in CHECKS:
    print(f'\n== {script} ==',flush=True)
    subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=True)
print('\nALL_DETERMINISTIC_REVIEW_CHECKS_PASSED')
