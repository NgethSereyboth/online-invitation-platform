#!/usr/bin/env python3
from __future__ import annotations
import json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def free_port():
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
def call(base,path,method='GET',body=None,cookie=None,expected=200):
 data=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json'}
 if cookie:headers['Cookie']=cookie
 req=urllib.request.Request(base+path,data=data,method=method,headers=headers)
 try:
  with urllib.request.urlopen(req,timeout=15) as response:status=response.status;payload=json.loads(response.read() or b'{}');response_headers=dict(response.headers)
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
def document(message='Ready'):
 return {'schemaVersion':13,'eventType':'Wedding','fields':{'names':'Review Operations','date':'2027-03-01','venue':'Phnom Penh','message':message},'objects':{'title':{'id':'title','type':'text','left':'10%','top':'10%','width':'80%','height':'90px','html':'Review Operations','fontSize':42,'color':'#342c26','zIndex':1}},'designPages':[],'sectionOrder':['venue'],'settings':{'rsvpEnabled':False}}
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-v238-review-') as data:
  legacy=sqlite3.connect(str(Path(data)/'invites.db'))
  try:
   legacy.execute("CREATE TABLE invitation_comments(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, object_id TEXT NOT NULL DEFAULT '', body TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)")
   legacy.execute("CREATE TABLE approval_requests(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, requested_by TEXT NOT NULL, requested_from TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', note TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)")
   legacy.commit()
  finally:legacy.close()
  env={**os.environ,'EINVITE_DATA_DIR':data};env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
  proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  try:
   wait(base,proc)
   owner,owner_cookie=register(base,'v238-owner@example.com');designer,designer_cookie=register(base,'v238-designer@example.com');reviewer,reviewer_cookie=register(base,'v238-reviewer@example.com')
   created,_=call(base,'/api/invitations','POST',{'slug':'review-operations-v238','document':document()},owner_cookie,201);iid=created['id']
   call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'v238-designer@example.com','role':'designer'},owner_cookie)
   call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'v238-reviewer@example.com','role':'viewer'},owner_cookie)
   context,_=call(base,f'/api/invitations/{iid}/review-context',cookie=owner_cookie)
   assert context['role']=='owner' and context['canManage'] and context['readiness']['ready']
   assert context['readiness']['policy']=={'approvalGate':False,'unresolvedCommentsGate':False,'minApprovals':1,'updatedAt':0,'updatedBy':''}
   comment,_=call(base,f'/api/invitations/{iid}/comments','POST',{'body':'Please verify the title spacing.','objectId':'title','pageId':'hero'},reviewer_cookie,201)
   owner_context,_=call(base,f'/api/invitations/{iid}/review-context',cookie=owner_cookie)
   assert owner_context['unreadCount']>=1 and any(n['kind']=='comment.added' for n in owner_context['notifications'])
   unread=[n['id'] for n in owner_context['notifications'] if not n['read']]
   marked,_=call(base,f'/api/invitations/{iid}/review-notifications','PUT',{'ids':unread[:1]},owner_cookie);assert marked['updated']>=1
   viewer_policy,_=call(base,f'/api/invitations/{iid}/review-policy','PUT',{'approvalGate':True},reviewer_cookie,403);assert 'management' in viewer_policy['error'].lower()
   policy,_=call(base,f'/api/invitations/{iid}/review-policy','PUT',{'approvalGate':True,'unresolvedCommentsGate':True,'minApprovals':1},owner_cookie)
   assert not policy['readiness']['ready'] and len(policy['readiness']['blockers'])==2
   blocked,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':document()},owner_cookie,409)
   assert blocked['code']=='review_gate_blocked';codes={item['code'] for item in blocked['readiness']['blockers']};assert codes=={'approval_required','unresolved_comments'}
   call(base,f'/api/invitations/{iid}/comments/{comment["id"]}','PUT',{'resolved':True},designer_cookie)
   approval,_=call(base,f'/api/invitations/{iid}/approvals','POST',{'requestedFrom':'v238-reviewer@example.com','note':'Please approve this saved revision.'},designer_cookie,201)
   reviewer_context,_=call(base,f'/api/invitations/{iid}/review-context',cookie=reviewer_cookie)
   assert any(n['kind']=='approval.requested' and n['target_id']==approval['id'] for n in reviewer_context['notifications'])
   call(base,f'/api/invitations/{iid}/approvals/{approval["id"]}','PUT',{'status':'approved','note':'Approved.'},reviewer_cookie)
   ready,_=call(base,f'/api/invitations/{iid}/review-context',cookie=owner_cookie)
   assert ready['readiness']['ready'] and ready['readiness']['validApprovals']==1 and ready['readiness']['unresolvedComments']==0
   published,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':document()},owner_cookie,201);assert published['url']=='/i/review-operations-v238'
   # Saving a new revision invalidates the approval and blocks the next publish.
   time.sleep(.01);call(base,f'/api/invitations/{iid}','PUT',{'document':document('Changed after approval')},designer_cookie)
   stale,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':document('Changed after approval')},owner_cookie,409)
   assert stale['code']=='review_gate_blocked' and stale['readiness']['validApprovals']==0
   # A separate invitation remains publishable because review gates are opt-in.
   second,_=call(base,'/api/invitations','POST',{'slug':'ungated-v238','document':document('Ungated')},owner_cookie,201)
   call(base,f'/api/invitations/{second["id"]}/publish','POST',{'document':document('Ungated')},owner_cookie,201)
   db=sqlite3.connect(str(Path(data)/'invites.db'))
   try:
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};assert {'invitation_review_policies','review_notifications'}<=tables
    row=db.execute('SELECT approval_gate,unresolved_comments_gate,min_approvals FROM invitation_review_policies WHERE invitation_id=?',(iid,)).fetchone();assert row==(1,1,1)
   finally:db.close()
  finally:
   proc.terminate()
   try:proc.wait(5)
   except subprocess.TimeoutExpired:proc.kill()
   if proc.returncode not in (None,0,-15):print(proc.stdout.read() if proc.stdout else '',file=sys.stderr)
 print('V23_8_REVIEW_OPERATIONS_BACKEND_TEST_PASSED')
if __name__=='__main__':run()
