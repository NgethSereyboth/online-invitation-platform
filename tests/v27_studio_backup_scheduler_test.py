#!/usr/bin/env python3
from __future__ import annotations
import os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run():
 with tempfile.TemporaryDirectory(prefix='einvite-v27-scheduler-') as data:
  code=r'''import os,time
os.environ['EINVITE_DATA_DIR']=r"'''+data+r'''"
import server
now=int(time.time()*1000)
with server.connect() as db:
 db.execute("INSERT INTO users(id,email,password_hash,salt,password_algo,created_at,role,email_verified,plan) VALUES(?,?,?,?,?,?,?,0,?)",('owner','owner@example.com','x','x','pbkdf2-sha256-v1',now,'customer','studio'))
 db.execute("INSERT INTO studio_backup_policies(owner_id,enabled,interval_hours,retention_count,include_media,updated_by,updated_at,next_run_at) VALUES(?,1,1,2,0,?,?,?)",('owner','owner',now,now-1))
server.process_due_studio_backups(limit=1)
with server.connect() as db:
 run=db.execute("SELECT status,kind,archive_name FROM backup_runs WHERE owner_id='owner'").fetchone();policy=db.execute("SELECT last_run_at,next_run_at FROM studio_backup_policies WHERE owner_id='owner'").fetchone();audit=db.execute("SELECT action FROM audit_events WHERE user_id='owner' ORDER BY created_at DESC LIMIT 1").fetchone()
 assert run and run['status']=='completed' and run['kind']=='scheduled'
 assert policy['last_run_at'] and policy['next_run_at']>policy['last_run_at']
 assert audit and audit['action']=='studio.backup_completed'
 assert (server.BACKUPS/run['archive_name']).is_file()
print('V27_STUDIO_BACKUP_SCHEDULER_TEST_PASSED')'''
  subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True)
if __name__=='__main__':run()
