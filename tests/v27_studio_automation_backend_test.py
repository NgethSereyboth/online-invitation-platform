#!/usr/bin/env python3
from __future__ import annotations
import io,json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.error,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def free_port():
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
def call(base,path,method='GET',body=None,cookie=None,expected=200):
 data=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json'}
 if cookie:headers['Cookie']=cookie
 req=urllib.request.Request(base+path,data=data,method=method,headers=headers)
 try:
  with urllib.request.urlopen(req,timeout=30) as response:status=response.status;raw=response.read();payload=json.loads(raw or b'{}');response_headers=dict(response.headers)
 except urllib.error.HTTPError as exc:status=exc.code;payload=json.loads(exc.read() or b'{}');response_headers=dict(exc.headers)
 assert status==expected,(path,status,payload);return payload,response_headers
def register(base,email):
 payload,headers=call(base,'/api/auth/register','POST',{'email':email,'password':'password123'},expected=201);return payload,(headers.get('Set-Cookie') or headers.get('set-cookie') or '').split(';',1)[0]
def wait(base,proc):
 for _ in range(240):
  if proc.poll() is not None:raise RuntimeError('server exited')
  try:call(base,'/api/health');return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def document(resource_id='',version=1):
 d={'schemaVersion':13,'fields':{'names':'V27 Operations'},'objects':{},'designPages':[],'settings':{'rsvpEnabled':False}}
 if resource_id:d.update({'studioGovernance':{'resourceId':resource_id,'resourceKind':'brand','resourceVersion':version,'brandResourceId':resource_id,'brandResourceVersion':version},'eventBrand':{'id':resource_id,'governed':True}})
 return d
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-v27-automation-') as data:
  env={**os.environ,'EINVITE_DATA_DIR':data};env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
  proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  try:
   wait(base,proc);owner,cookie=register(base,'v27-owner@example.com')
   resource,_=call(base,'/api/studio/resources','POST',{'kind':'brand','name':'V27 Brand','payload':{'primary':'#173f6d'},'status':'approved','governance':{'locked':False}},cookie,201)
   release,_=call(base,'/api/studio/releases','POST',{'name':'V27 Active','manifest':[{'id':resource['id'],'kind':'brand','name':resource['name'],'version':1}]},cookie,201)
   active,_=call(base,f'/api/studio/releases/{release["id"]}/activate','POST',{},cookie)
   invitations=[]
   for slug,doc in [('v27-compatible',document(resource['id'],1)),('v27-plain',document()),('v27-manual',document(resource['id'],2))]:
    item,_=call(base,'/api/invitations','POST',{'slug':slug,'document':doc},cookie,201);invitations.append(item)
   result,_=call(base,f'/api/studio/releases/{active["id"]}/bulk-pin','POST',{'scope':'noncurrent'},cookie)
   assert result['count']==2 and len(result['manual'])==1,result
   adoption,_=call(base,'/api/studio/adoption',cookie=cookie);assert adoption['counts']['current']==2 and adoption['counts']['unpinned']==1,adoption['counts']
   jobs,_=call(base,'/api/studio/bulk-jobs',cookie=cookie);assert jobs['jobs'] and len(jobs['jobs'][0]['result']['updated'])==2
   policy,_=call(base,'/api/studio/backup-policy','PUT',{'enabled':True,'intervalHours':6,'retentionCount':2,'includeMedia':False},cookie);assert policy['policy']['enabled'] and policy['policy']['intervalHours']==6
   run1,_=call(base,'/api/studio/backups/run','POST',{'includeMedia':False},cookie);assert run1['status']=='completed' and run1['sizeBytes']>100
   for _ in range(2):call(base,'/api/studio/backups/run','POST',{'includeMedia':False},cookie)
   listed,_=call(base,'/api/studio/backups',cookie=cookie);assert len([x for x in listed['backups'] if x['status']=='completed'])==2,listed
   backup_id=listed['backups'][0]['id'];req=urllib.request.Request(base+f'/api/studio/backups/{backup_id}/download',headers={'Cookie':cookie});raw=urllib.request.urlopen(req,timeout=30).read();z=zipfile.ZipFile(io.BytesIO(raw));payload=json.loads(z.read('account.json'));assert payload['schema']=='einvite-studio-archive-v27' and len(payload['invitations'])==3 and payload['backupPolicy']['enabled']==1
   audit,_=call(base,'/api/studio/audit?limit=300',cookie=cookie);actions={x['action'] for x in audit['events']};assert {'studio.release_bulk_pinned','studio.backup_policy_updated','studio.backup_completed'}<=actions,actions
   db=sqlite3.connect(str(Path(data)/'invites.db'))
   try:
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert {'studio_backup_policies','studio_bulk_jobs','backup_runs'}<=tables
    assert db.execute('SELECT COUNT(*) FROM backup_runs').fetchone()[0]==2
   finally:db.close()
  finally:
   proc.terminate()
   try:proc.wait(5)
   except subprocess.TimeoutExpired:proc.kill()
 print('V27_STUDIO_AUTOMATION_BACKEND_TEST_PASSED')
if __name__=='__main__':run()
