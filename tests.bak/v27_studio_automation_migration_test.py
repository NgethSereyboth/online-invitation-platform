#!/usr/bin/env python3
from __future__ import annotations
import json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def wait(base,proc):
 for _ in range(180):
  if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
  try:urllib.request.urlopen(base+'/api/health',timeout=2).read();return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def start(data):
 p=port();base=f'http://127.0.0.1:{p}';env={**os.environ,'EINVITE_DATA_DIR':data};proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(p)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);wait(base,proc);return proc
def stop(proc):
 proc.terminate()
 try:proc.wait(5)
 except subprocess.TimeoutExpired:proc.kill()
def run():
 with tempfile.TemporaryDirectory(prefix='einvite-v27-migration-') as data:
  proc=start(data);stop(proc);db_path=Path(data)/'invites.db';db=sqlite3.connect(db_path)
  try:
   db.execute('DROP TABLE studio_backup_policies');db.execute('DROP TABLE studio_bulk_jobs');db.execute('DROP TABLE backup_runs');db.execute("CREATE TABLE backup_runs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,status TEXT NOT NULL,detail_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL,completed_at INTEGER)");db.execute("INSERT INTO backup_runs VALUES('legacy','manual','completed','{}',1,2)");db.commit()
  finally:db.close()
  proc=start(data);stop(proc);db=sqlite3.connect(db_path)
  try:
   tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert {'studio_backup_policies','studio_bulk_jobs','backup_runs'}<=tables
   cols={r[1] for r in db.execute('PRAGMA table_info(backup_runs)')};assert {'owner_id','initiated_by','archive_name','size_bytes','error_text'}<=cols
   assert db.execute("SELECT status FROM backup_runs WHERE id='legacy'").fetchone()[0]=='completed'
  finally:db.close()
 print('V27_STUDIO_AUTOMATION_MIGRATION_TEST_PASSED')
if __name__=='__main__':run()
