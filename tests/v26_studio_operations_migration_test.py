#!/usr/bin/env python3
from __future__ import annotations
import json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def call(base,path,method='GET',body=None,expected=200):
 data=None if body is None else json.dumps(body).encode();req=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=15) as r:status=r.status;payload=json.loads(r.read() or b'{}')
 except urllib.error.HTTPError as e:status=e.code;payload=json.loads(e.read() or b'{}')
 assert status==expected,(status,payload);return payload
def start(data):
 p=port();base=f'http://127.0.0.1:{p}';env={**os.environ,'EINVITE_DATA_DIR':data};proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(p)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 for _ in range(160):
  if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
  try:call(base,'/api/health');return proc,base
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def stop(proc):
 proc.terminate()
 try:proc.wait(5)
 except subprocess.TimeoutExpired:proc.kill()
def run():
 with tempfile.TemporaryDirectory(prefix='einvite-v26-migration-') as data:
  proc,base=start(data)
  try:call(base,'/api/auth/register','POST',{'email':'migration@example.com','password':'password123'},201)
  finally:stop(proc)
  db_path=Path(data)/'invites.db';db=sqlite3.connect(db_path)
  try:
   db.execute('DROP TABLE invitation_studio_release_pins');db.execute('DROP TABLE studio_releases');db.commit()
   assert db.execute("SELECT COUNT(*) FROM users WHERE email='migration@example.com'").fetchone()[0]==1
  finally:db.close()
  proc,base=start(data)
  try:
   call(base,'/api/health');db=sqlite3.connect(db_path)
   try:
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert {'studio_releases','invitation_studio_release_pins'}<=tables
    assert db.execute("SELECT COUNT(*) FROM users WHERE email='migration@example.com'").fetchone()[0]==1
   finally:db.close()
  finally:stop(proc)
 print('V26_STUDIO_OPERATIONS_MIGRATION_TEST_PASSED')
if __name__=='__main__':run()
