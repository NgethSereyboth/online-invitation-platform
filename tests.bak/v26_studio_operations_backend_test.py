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
  with urllib.request.urlopen(req,timeout=20) as response:status=response.status;payload=json.loads(response.read() or b'{}');response_headers=dict(response.headers)
 except urllib.error.HTTPError as exc:status=exc.code;payload=json.loads(exc.read() or b'{}');response_headers=dict(exc.headers)
 assert status==expected,(path,status,payload);return payload,response_headers
def register(base,email):
 payload,headers=call(base,'/api/auth/register','POST',{'email':email,'password':'password123'},expected=201);raw=headers.get('Set-Cookie') or headers.get('set-cookie') or '';return payload,raw.split(';',1)[0]
def wait(base,proc):
 for _ in range(240):
  if proc.poll() is not None:raise RuntimeError('server exited')
  try:call(base,'/api/health');return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def doc(resource_id,version=1):
 return {'schemaVersion':13,'eventType':'Government','fields':{'names':'V26 Operations','date':'2027-05-01','venue':'Phnom Penh'},'objects':{'title':{'type':'text','html':'V26 Operations','left':'10%','top':'10%','width':'80%','height':'80px','zIndex':1}},'designPages':[],'settings':{'rsvpEnabled':False},'studioGovernance':{'resourceId':resource_id,'resourceKind':'brand','resourceVersion':version,'brandResourceId':resource_id,'brandResourceVersion':version},'eventBrand':{'id':resource_id,'governed':True}}
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-v26-operations-') as data:
  env={**os.environ,'EINVITE_DATA_DIR':data};env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
  proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  try:
   wait(base,proc);owner,owner_cookie=register(base,'v26-owner@example.com');manager,manager_cookie=register(base,'v26-manager@example.com')
   created,_=call(base,'/api/invitations','POST',{'slug':'v26-operations','document':{'schemaVersion':13,'fields':{'names':'V26 Operations'},'objects':{},'designPages':[]}},owner_cookie,201);iid=created['id']
   call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'v26-manager@example.com','role':'manager'},owner_cookie)
   resource,_=call(base,'/api/studio/resources','POST',{'kind':'brand','name':'Official V26 Brand','category':'Government','payload':{'primary':'#183a64'},'status':'approved','governance':{'locked':False}},owner_cookie,201)
   release,_=call(base,'/api/studio/releases','POST',{'name':'V26 Official Release','notes':'First controlled rollout','manifest':[{'id':resource['id'],'kind':'brand','name':resource['name'],'version':resource['version']}]},owner_cookie,201)
   assert release['status']=='draft' and len(release['manifest'])==1
   listed,_=call(base,f'/api/studio/releases?invitationId={iid}',cookie=manager_cookie);assert len(listed['releases'])==1 and not listed['canManage']
   active,_=call(base,f'/api/studio/releases/{release["id"]}/activate','POST',{},owner_cookie);assert active['status']=='active'
   immutable,_=call(base,f'/api/studio/releases/{release["id"]}','PUT',{'manifest':[]},owner_cookie,409);assert immutable['code']=='activated_release_immutable'
   cloned,_=call(base,f'/api/studio/releases/{release["id"]}/clone','POST',{'name':'V26 Next Draft'},owner_cookie,201);assert cloned['status']=='draft' and cloned['manifest']==active['manifest']
   call(base,'/api/studio/governance','PUT',{'requireStudioRelease':True},owner_cookie)
   blocked,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc(resource['id'])},owner_cookie,409);assert any(x['code']=='studio_release_required' for x in blocked['readiness']['blockers'])
   pin,_=call(base,f'/api/invitations/{iid}/studio-release','PUT',{'releaseId':active['id']},manager_cookie);assert pin['pin']['release_id']==active['id']
   published,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc(resource['id'])},owner_cookie,201);assert published['publicationId']
   adoption,_=call(base,f'/api/studio/adoption?invitationId={iid}',cookie=owner_cookie);assert adoption['counts']['current']==1 and adoption['activeRelease']['id']==active['id']
   delete_block,_=call(base,f'/api/studio/resources/{resource["id"]}','DELETE',cookie=owner_cookie,expected=409);assert delete_block['code']=='studio_resource_in_active_release'
   updated,_=call(base,f'/api/studio/resources/{resource["id"]}','PUT',{'payload':{'primary':'#244a78'}},owner_cookie);assert updated['version']==2
   adoption_changed,_=call(base,f'/api/studio/adoption?invitationId={iid}',cookie=owner_cookie);assert adoption_changed['counts']['outdated']==1 and adoption_changed['releaseIssues']
   changed,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc(resource['id'])},owner_cookie,409);assert any(x['code']=='studio_release_resource_changed' for x in changed['readiness']['blockers'])
   release2,_=call(base,'/api/studio/releases','POST',{'name':'V26 Official Release 2','manifest':[{'id':resource['id'],'kind':'brand','name':resource['name'],'version':2}]},owner_cookie,201)
   active2,_=call(base,f'/api/studio/releases/{release2["id"]}/activate','POST',{},owner_cookie);assert active2['status']=='active'
   outdated,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc(resource['id'],2)},owner_cookie,409);assert any(x['code'] in {'studio_release_inactive','studio_release_pin_outdated'} for x in outdated['readiness']['blockers'])
   call(base,f'/api/invitations/{iid}/studio-release','PUT',{'releaseId':active2['id']},manager_cookie)
   published2,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc(resource['id'],2)},owner_cookie,201);assert published2['publicationId']
   export,_=call(base,'/api/account/export',cookie=owner_cookie);assert len(export['studioReleases'])==3 and len(export['studioReleasePins'])==1
   req=urllib.request.Request(base+'/api/account/export/archive',headers={'Cookie':owner_cookie});raw=urllib.request.urlopen(req,timeout=20).read();archive=zipfile.ZipFile(io.BytesIO(raw));account=json.loads(archive.read('account.json'));assert len(account['studioReleases'])==3 and len(account['studioReleasePins'])==1 and account['studioGovernance']['policy']['requireStudioRelease']
   db=sqlite3.connect(str(Path(data)/'invites.db'))
   try:
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert {'studio_releases','invitation_studio_release_pins'}<=tables
   finally:db.close()
  finally:
   proc.terminate()
   try:proc.wait(5)
   except subprocess.TimeoutExpired:proc.kill()
 print('V26_STUDIO_OPERATIONS_BACKEND_TEST_PASSED')
if __name__=='__main__':run()
