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
 request=urllib.request.Request(base+path,data=data,method=method,headers=headers)
 try:
  with urllib.request.urlopen(request,timeout=12) as response:status=response.status;payload=json.loads(response.read() or b'{}');response_headers=dict(response.headers)
 except urllib.error.HTTPError as exc:status=exc.code;payload=json.loads(exc.read() or b'{}');response_headers=dict(exc.headers)
 assert status==expected,(path,status,payload);return payload,response_headers
def register(base,email):
 payload,headers=call(base,'/api/auth/register','POST',{'email':email,'password':'password123'},expected=201);raw=headers.get('Set-Cookie') or headers.get('set-cookie') or '';assert raw;return payload,raw.split(';',1)[0]
def wait(base,proc):
 for _ in range(220):
  if proc.poll() is not None:raise RuntimeError('server exited during startup')
  try:call(base,'/api/health');return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def document(message='Initial design'):
 return {'schemaVersion':13,'eventType':'Wedding','fields':{'names':'Review Workflow','date':'2027-02-14','venue':'Phnom Penh','message':message},'objects':{'title':{'id':'title','type':'text','left':'10%','top':'10%','width':'80%','height':'90px','html':'Review Workflow','fontSize':42,'color':'#342c26','zIndex':1},'photo':{'id':'photo','type':'image','left':'15%','top':'28%','width':'70%','height':'50%','src':'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=','zIndex':2}},'designPages':[],'sectionOrder':['venue'],'settings':{'rsvpEnabled':False}}
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-v237-review-') as data:
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
   owner,owner_cookie=register(base,'review-owner@example.com');designer,designer_cookie=register(base,'review-designer@example.com');reviewer,reviewer_cookie=register(base,'reviewer@example.com')
   created,_=call(base,'/api/invitations','POST',{'slug':'review-workflow-v237','document':document()},owner_cookie,201);iid=created['id']
   call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'review-designer@example.com','role':'designer'},owner_cookie,200)
   call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'reviewer@example.com','role':'viewer'},owner_cookie,200)
   root,_=call(base,f'/api/invitations/{iid}/comments','POST',{'body':'Move the title slightly lower.','objectId':'title','pageId':'hero','anchorX':.4,'anchorY':.2},reviewer_cookie,201)
   assert root['object_id']=='title' and root['page_id']=='hero' and root['canDelete']
   reply,_=call(base,f'/api/invitations/{iid}/comments','POST',{'body':'I will update this.','parentId':root['id'],'objectId':'ignored','pageId':'ignored','anchorX':.9,'anchorY':.9},designer_cookie,201)
   assert reply['parent_id']==root['id'] and reply['object_id']=='title' and reply['page_id']=='hero'
   point,_=call(base,f'/api/invitations/{iid}/comments','POST',{'body':'Balance this empty space.','pageId':'hero','anchorX':.812,'anchorY':.633},designer_cookie,201)
   assert abs(point['anchor_x']-.812)<.001 and abs(point['anchor_y']-.633)<.001
   listed,_=call(base,f'/api/invitations/{iid}/comments',cookie=owner_cookie)
   assert [row['id'] for row in listed[:2]]==[root['id'],reply['id']],listed
   assert all(row['canDelete'] for row in listed)
   blocked,_=call(base,f'/api/invitations/{iid}/comments/{root["id"]}','PUT',{'resolved':True},reviewer_cookie,403);assert 'permission' in blocked.get('error','').lower()
   resolved,_=call(base,f'/api/invitations/{iid}/comments/{reply["id"]}','PUT',{'resolved':True},designer_cookie,200);assert resolved=={'id':root['id'],'resolved':True}
   reopened,_=call(base,f'/api/invitations/{iid}/comments/{root["id"]}','PUT',{'resolved':False},designer_cookie,200);assert reopened['resolved'] is False
   approval,_=call(base,f'/api/invitations/{iid}/approvals','POST',{'requestedFrom':'reviewer@example.com','note':'Please approve the saved layout.'},designer_cookie,201)
   assert approval['status']=='pending' and approval['document_revision'] and approval['document_fingerprint'] and approval['summary']['objects']==2
   rows,_=call(base,f'/api/invitations/{iid}/approvals',cookie=reviewer_cookie);assert rows[0]['id']==approval['id'] and not rows[0]['stale'] and rows[0]['requested_from']=='reviewer@example.com'
   time.sleep(.01);call(base,f'/api/invitations/{iid}','PUT',{'document':document('Design changed after review request')},designer_cookie,200)
   rows,_=call(base,f'/api/invitations/{iid}/approvals',cookie=reviewer_cookie);assert rows[0]['stale'],rows[0]
   decision,_=call(base,f'/api/invitations/{iid}/approvals/{approval["id"]}','PUT',{'status':'changes-requested','note':'Please restore spacing.'},reviewer_cookie,200);assert decision['status']=='changes-requested' and decision['decided_by']==reviewer['user']['id']
   deleted,_=call(base,f'/api/invitations/{iid}/comments/{root["id"]}','DELETE',cookie=owner_cookie);assert deleted['deleted']
   remaining,_=call(base,f'/api/invitations/{iid}/comments',cookie=owner_cookie);assert root['id'] not in {x['id'] for x in remaining} and reply['id'] not in {x['id'] for x in remaining}
   call(base,f'/api/invitations/{iid}/publish','POST',{'document':document('Published design')},owner_cookie,201)
   public,_=call(base,'/api/public/review-workflow-v237');encoded=json.dumps(public).lower();assert 'invitation_comments' not in encoded and 'approval_requests' not in encoded and 'balance this empty space' not in encoded
   db=sqlite3.connect(str(Path(data)/'invites.db'))
   try:comment_cols={row[1] for row in db.execute('PRAGMA table_info(invitation_comments)')};approval_cols={row[1] for row in db.execute('PRAGMA table_info(approval_requests)')}
   finally:db.close()
   assert {'page_id','parent_id','anchor_x','anchor_y'}<=comment_cols;assert {'document_revision','document_fingerprint','summary_json','decided_by','decided_at'}<=approval_cols
  finally:
   proc.terminate()
   try:proc.wait(5)
   except subprocess.TimeoutExpired:proc.kill()
   if proc.returncode not in (None,0,-15):print(proc.stdout.read() if proc.stdout else '',file=sys.stderr)
 print('V23_7_REVIEW_BACKEND_TEST_PASSED')
if __name__=='__main__':run()
