#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.error,urllib.request
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
def base_doc():return {'schemaVersion':13,'eventType':'Government','fields':{'names':'V25 Governance','date':'2027-04-01','venue':'Phnom Penh'},'objects':{'title':{'type':'text','html':'V25 Governance','left':'10%','top':'10%','width':'80%','height':'80px','zIndex':1}},'designPages':[],'settings':{'rsvpEnabled':False},'palette':{'background':'#ffffff','surface':'#ffffff','text':'#222222','heading':'#183a64'},'accent':'#b18a3b'}
def normalized_preflight_document(doc):
 sys.path.insert(0,str(ROOT)) if str(ROOT) not in sys.path else None
 import server as server_module
 normalized=json.loads(json.dumps(doc))
 server_module.validate_document(normalized)
 normalized['printReadiness']={'status':'ready','fingerprint':server_module.studio_print_fingerprint(normalized),'checkedAt':int(time.time()*1000)}
 return normalized
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-v25-governance-') as data:
  env={**os.environ,'EINVITE_DATA_DIR':data};env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
  proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  try:
   wait(base,proc);owner,owner_cookie=register(base,'v25-owner@example.com');collab,collab_cookie=register(base,'v25-collab@example.com')
   created,_=call(base,'/api/invitations','POST',{'slug':'v25-governance','document':base_doc()},owner_cookie,201);iid=created['id']
   call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'v25-collab@example.com','role':'designer'},owner_cookie)
   resource,_=call(base,'/api/studio/resources','POST',{'kind':'brand','name':'Official V25','category':'Government','payload':{'primary':'#183a64','accent':'#b18a3b','background':'#f7f8fb','surface':'#ffffff','text':'#18202d','headingPair':'serif-formal','bodyPair':'sans-modern'},'status':'approved','governance':{'locked':True,'allowedOverrides':['content','media']}},owner_cookie,201)
   assert resource['status']=='approved' and resource['version']==1
   listed,_=call(base,f'/api/studio/resources?invitationId={iid}',cookie=collab_cookie);assert len(listed['resources'])==1 and not listed['canManage']
   call(base,f'/api/studio/resources/{resource["id"]}','PUT',{'status':'draft'},collab_cookie,404)
   updated,_=call(base,f'/api/studio/resources/{resource["id"]}','PUT',{'payload':{**resource['payload'],'primary':'#203f70'}},owner_cookie);assert updated['version']==2
   policy={'approvedOnly':True,'lockBrandColors':True,'lockTypography':True,'requireAdaptiveTemplate':True,'requirePrintPreflight':True}
   saved,_=call(base,'/api/studio/governance','PUT',policy,owner_cookie);assert saved['policy']['requirePrintPreflight']
   blocked,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':base_doc()},owner_cookie,409);assert blocked['code']=='studio_governance_blocked' and len(blocked['readiness']['blockers'])>=3
   doc=base_doc();doc['templateFamily']={'id':'government-delegation','adaptive':True};doc['palette']={'background':'#f7f8fb','surface':'#ffffff','text':'#18202d','heading':'#203f70','muted':'#18202d'};doc['accent']='#b18a3b';doc['eventBrand']={'id':resource['id'],'name':'Official V25','governed':True,'primary':'#203f70','accent':'#b18a3b','background':'#f7f8fb','surface':'#ffffff','text':'#18202d','headingPair':'serif-formal','bodyPair':'sans-modern'};doc=normalized_preflight_document(doc);[doc['typography']['styles'][key].__setitem__('fontPairing','serif-formal') for key in ('display','heading','subheading','khmer-ceremonial')];[doc['typography']['styles'][key].__setitem__('fontPairing','sans-modern') for key in ('body','caption')];doc['studioGovernance']={'resourceId':resource['id'],'resourceKind':'brand','resourceVersion':updated['version'],'status':'approved','locked':True,'brandResourceId':resource['id'],'brandResourceVersion':updated['version'],'brandStatus':'approved','brandLocked':True}
   doc=normalized_preflight_document(doc)
   fake=json.loads(json.dumps(doc));fake['studioGovernance']['resourceId']='missing-resource';fake['studioGovernance']['brandResourceId']='missing-resource';fake['eventBrand']['id']='missing-resource';fake=normalized_preflight_document(fake)
   fake_result,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':fake},owner_cookie,409);assert any(x['code']=='approved_resource_unavailable' for x in fake_result['readiness']['blockers'])
   outdated=json.loads(json.dumps(doc));outdated['studioGovernance']['resourceVersion']=1;outdated['studioGovernance']['brandResourceVersion']=1;outdated=normalized_preflight_document(outdated)
   outdated_result,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':outdated},owner_cookie,409);assert any(x['code']=='governed_resource_outdated' for x in outdated_result['readiness']['blockers'])
   wrong_color=json.loads(json.dumps(doc));wrong_color['palette']['heading']='#ff0000';wrong_color=normalized_preflight_document(wrong_color)
   color_result,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':wrong_color},owner_cookie,409);assert any(x['code']=='brand_colors_locked' for x in color_result['readiness']['blockers'])
   wrong_type=json.loads(json.dumps(doc));wrong_type['typography']['styles']['heading']['fontPairing']='sans-modern';wrong_type=normalized_preflight_document(wrong_type)
   type_result,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':wrong_type},owner_cookie,409);assert any(x['code']=='brand_typography_locked' for x in type_result['readiness']['blockers'])
   published,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc},owner_cookie,201);assert published['publicationId']
   stale=json.loads(json.dumps(doc));stale['fields']['names']='Changed after preflight'
   rejected,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':stale},owner_cookie,409);assert any(x['code']=='print_preflight_stale' for x in rejected['readiness']['blockers'])
   export,_=call(base,'/api/account/export',cookie=owner_cookie);assert export['studioResources'][0]['name']=='Official V25' and export['studioGovernance']['policy']['approvedOnly']
   call(base,f'/api/studio/resources/{resource["id"]}','DELETE',cookie=owner_cookie)
   db=sqlite3.connect(str(Path(data)/'invites.db'))
   try:
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert {'studio_resources','studio_governance'}<=tables
   finally:db.close()
  finally:
   proc.terminate()
   try:proc.wait(5)
   except subprocess.TimeoutExpired:proc.kill()
 print('V25_TEMPLATE_GOVERNANCE_BACKEND_TEST_PASSED')
if __name__=='__main__':run()
