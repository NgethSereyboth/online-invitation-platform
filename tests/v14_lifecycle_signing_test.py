#!/usr/bin/env python3
"""V14 stable-signing, rotation, startup, and post-commit deletion regression."""
from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(code,data,extra=None):
 env={**os.environ,'EINVITE_DATA_DIR':str(data),'EINVITE_REQUIRE_EMAIL_VERIFICATION':'0',**(extra or {})}
 return subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

def main():
 with tempfile.TemporaryDirectory(prefix='einvite-v14-signing-') as tmp:
  data=Path(tmp)
  code="import json,server;print(json.dumps({'upload':server.UPLOAD_SIGNING_SECRET,'media':server.MEDIA_SIGNING_SECRET,'guest':server.GUEST_TOKEN_SECRET}))"
  first=run(code,data);second=run(code,data);assert first.returncode==second.returncode==0,(first.stdout,second.stdout)
  assert json.loads(first.stdout.strip().splitlines()[-1])==json.loads(second.stdout.strip().splitlines()[-1])
  assert (data/'.upload-signing-secret').is_file() and (data/'.media-signing-secret').is_file()
  missing=run('import server',data,{'EINVITE_PRODUCTION':'1','EINVITE_UPLOAD_SIGNING_SECRET':'','EINVITE_MEDIA_SIGNING_SECRET':'','EINVITE_PUBLIC_BASE_URL':''})
  assert missing.returncode!=0 and 'requires stable EINVITE_UPLOAD_SIGNING_SECRET' in missing.stdout,missing.stdout
  local_url=run(
    "import server;print(server.PRODUCTION_MODE,server.REQUIRE_VERIFIED_EMAIL)",
    data,
    {
      "EINVITE_PRODUCTION":"0",
      "EINVITE_PUBLIC_BASE_URL":"http://127.0.0.1:8080",
      "EINVITE_UPLOAD_SIGNING_SECRET":"",
      "EINVITE_MEDIA_SIGNING_SECRET":"",
    },
  )
  assert local_url.returncode==0 and local_url.stdout.strip().endswith("False False"),local_url.stdout
  rotation=run(r'''
import hashlib,hmac,time,server
exp=int(time.time())+300
path='asset.png';invite='invite-1';old='old-media-secret'
payload=f'{path}|{invite}|{exp}';sig=hmac.new(old.encode(),payload.encode(),hashlib.sha256).hexdigest()
assert server.verify_media_signature(path,invite,exp,sig)
aid='asset-1';size=12;mime='image/png';upath=aid+'.png';old_u='old-upload-secret'
up=f'{invite}|{aid}|{upath}|{mime}|{size}|{exp}';usig=hmac.new(old_u.encode(),up.encode(),hashlib.sha256).hexdigest()
handler=object.__new__(server.Handler);assert handler._verify_upload_claim(invite,{'assetId':aid,'path':upath,'mime':mime,'size':size,'expires':exp,'signature':usig})[:2]==(aid,upath)
print('ROTATION_OK')
''',data,{'EINVITE_UPLOAD_SIGNING_SECRET':'new-upload-secret','EINVITE_UPLOAD_SIGNING_PREVIOUS_SECRETS':'old-upload-secret','EINVITE_MEDIA_SIGNING_SECRET':'new-media-secret','EINVITE_MEDIA_SIGNING_PREVIOUS_SECRETS':'old-media-secret'})
  assert rotation.returncode==0 and 'ROTATION_OK' in rotation.stdout,rotation.stdout
  deletion=run(r'''
import json,server
p=server.UPLOADS/'queued-delete.bin';p.write_bytes(b'delete me')
server.queue_physical_deletions([(p.name,'')]);assert p.exists()
with server.connect() as db:
 row=db.execute("SELECT state FROM background_jobs WHERE kind='storage.delete' ORDER BY created_at DESC LIMIT 1").fetchone();assert row and row['state']=='queued'
server.process_storage_delete_jobs(5);assert not p.exists()
with server.connect() as db:
 row=db.execute("SELECT state FROM background_jobs WHERE kind='storage.delete' ORDER BY created_at DESC LIMIT 1").fetchone();assert row['state']=='done'
assert server._SQLITE_SCHEMA_READY
with server.connect() as db:db.execute('SELECT 1')
assert server._SQLITE_SCHEMA_READY
print('DELETE_QUEUE_OK')
''',data,{'EINVITE_BACKGROUND_MEDIA':'1'})
  assert deletion.returncode==0 and 'DELETE_QUEUE_OK' in deletion.stdout,deletion.stdout
 print('V14_LIFECYCLE_SIGNING_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
