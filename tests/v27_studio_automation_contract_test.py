#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run():
 server=(ROOT/'server.py').read_text(encoding='utf-8');js=(ROOT/'studio-automation-v27.js').read_text(encoding='utf-8');css=(ROOT/'studio-automation-v27.css').read_text(encoding='utf-8');loader=(ROOT/'performance-loader-v22.js').read_text(encoding='utf-8');schema=(ROOT/'postgres_schema.sql').read_text(encoding='utf-8')
 for token in ('studio_backup_policies','studio_bulk_jobs','bulk_pin_studio_release','studio_operations_audit','run_studio_backup_now','process_due_studio_backups'):
  assert token in server,token
 for token in ('studio.automation','studio.bulkRemediation','studio.backups','studio.auditTrail','/api/studio/backups/run','/bulk-pin'):
  assert token in js,token
 assert 'studio-automation-v27.js' in loader
 assert 'studio_backup_policies' in schema and 'studio_bulk_jobs' in schema
 assert '@media(max-width:720px)' in css
 assert "addEventListener('keydown'" not in js and 'onkeydown=' not in js
 print('V27_STUDIO_AUTOMATION_CONTRACT_TEST_PASSED')
if __name__=='__main__':run()
