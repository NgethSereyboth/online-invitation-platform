"""Tests for production-oriented foundations added after the main feature suite."""
import base64
import hashlib,hmac,json,os,socket,subprocess,sys,tempfile,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def req(base,path,method='GET',body=None,token=None,cookie=None,headers=None,expected=200):
 data=None if body is None else json.dumps(body).encode();h={'Content-Type':'application/json',**(headers or {})}
 if token:h['Authorization']='Bearer '+token
 if cookie:h['Cookie']=cookie
 r=urllib.request.Request(base+path,data=data,method=method,headers=h)
 try:
  with urllib.request.urlopen(r,timeout=8) as x:return x.status,json.loads(x.read() or b'{}'),dict(x.headers)
 except urllib.error.HTTPError as e:
  payload=json.loads(e.read() or b'{}')
  if e.code!=expected:raise AssertionError((path,e.code,payload))
  return e.code,payload,dict(e.headers)
def raw_req(base,path,body,cookie,expected=201):
 h={'Content-Type':'image/png','Content-Length':str(len(body)),'X-File-Name':'cookie-session.png','Cookie':cookie}
 r=urllib.request.Request(base+path,data=body,method='POST',headers=h)
 try:
  with urllib.request.urlopen(r,timeout=8) as x:return x.status,json.loads(x.read() or b'{}'),dict(x.headers)
 except urllib.error.HTTPError as e:
  payload=json.loads(e.read() or b'{}')
  if e.code!=expected:raise AssertionError((path,e.code,payload))
  return e.code,payload,dict(e.headers)

def wait(base):
 for _ in range(100):
  try:
   if req(base,'/api/health')[0]==200:return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def cookie_from(headers):
 raw=headers.get('Set-Cookie') or headers.get('set-cookie') or ''
 assert raw and 'HttpOnly' in raw and 'SameSite=Lax' in raw,raw
 return raw.split(';',1)[0]
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-prod-foundations-') as d:
  secret='billing-secret';env={**os.environ,'EINVITE_DATA_DIR':d,'EINVITE_BILLING_WEBHOOK_SECRET':secret}
  env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
  p=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   wait(base)
   _,owner,h=req(base,'/api/auth/register','POST',{'email':'owner@example.com','password':'password123'},expected=201);owner_cookie=cookie_from(h);assert 'token' not in owner,owner
   _,me,_=req(base,'/api/auth/me',cookie=owner_cookie);assert me['user']['email']=='owner@example.com'
   # Bearer sessions are disabled by default in production mode.
   status,bearer_only,_=req(base,'/api/auth/me',token='not-a-browser-session',expected=200);assert status==200 and not bearer_only.get('user'),bearer_only
   # A stray Authorization header cannot override a valid HttpOnly cookie.
   _,me_cookie,_=req(base,'/api/auth/me',token='ignored',cookie=owner_cookie);assert me_cookie['user']['email']=='owner@example.com'
   _,collab,ch=req(base,'/api/auth/register','POST',{'email':'designer@example.com','password':'password123'},expected=201);collab_cookie=cookie_from(ch);assert 'token' not in collab,collab
   doc={'eventType':'Wedding','fields':{'names':'Foundation Test','date':'2026-12-27','venue':'Venue','message':'Join us'},'objects':{},'designPages':[],'sectionOrder':['schedule','venue','rsvp'],'settings':{'rsvpEnabled':True}}
   _,inv,_=req(base,'/api/invitations','POST',{'slug':'foundation-test','document':doc},cookie=owner_cookie,expected=201);iid=inv['id']
   _,added,_=req(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'designer@example.com','role':'designer'},cookie=owner_cookie,expected=200);assert added['role']=='designer'
   _,shared,_=req(base,'/api/invitations',cookie=collab_cookie);assert any(i['id']==iid and i['shared'] for i in shared)
   doc['fields']['message']='Edited collaboratively';req(base,f'/api/invitations/{iid}','PUT',{'document':doc},cookie=collab_cookie,expected=200)
   _,got,_=req(base,f'/api/invitations/{iid}',cookie=owner_cookie);assert got['document']['fields']['message']=='Edited collaboratively'
   # Core authenticated browser flows must work through the HttpOnly cookie alone.
   png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
   _,asset,_=raw_req(base,f'/api/invitations/{iid}/assets/raw',png,owner_cookie);assert asset['id'] and asset['url']
   _,published,_=req(base,f'/api/invitations/{iid}/publish','POST',{'document':doc},cookie=owner_cookie,expected=201);assert published['publicationId'] and published['url']=='/i/foundation-test'
   _,public_doc,_=req(base,'/api/public/foundation-test');assert public_doc['document']['fields']['message']=='Edited collaboratively'
   _,ai,_=req(base,'/api/ai/assist','POST',{'task':'romantic','prompt':'','context':{'names':'A & B','eventType':'Wedding'}},cookie=owner_cookie,expected=200);assert ai['provider']=='template' and ai['providerMode']=='offline' and ai['text']
   payload=json.dumps({'type':'subscription.updated','data':{'email':'designer@example.com','plan':'creator'}}).encode();sig=hmac.new(secret.encode(),payload,hashlib.sha256).hexdigest()
   request=urllib.request.Request(base+'/api/billing/webhook',data=payload,method='POST',headers={'Content-Type':'application/json','X-EInvite-Signature':sig})
   with urllib.request.urlopen(request,timeout=8) as x:assert x.status==200
   _,usage,_=req(base,'/api/account/usage',cookie=collab_cookie);assert usage['plan']=='creator'
   _,_,logout_headers=req(base,'/api/auth/logout','POST',{},cookie=owner_cookie);assert 'Max-Age=0' in (logout_headers.get('Set-Cookie') or logout_headers.get('set-cookie') or '')
   _,login_payload,login_headers=req(base,'/api/auth/login','POST',{'email':'owner@example.com','password':'password123'},expected=201);assert 'token' not in login_payload,login_payload
   login_cookie=cookie_from(login_headers);_,login_me,_=req(base,'/api/auth/me',cookie=login_cookie);assert login_me['user']['email']=='owner@example.com'
   print('PRODUCTION_FOUNDATIONS_TEST_PASSED')
  finally:
   p.terminate()
   try:p.wait(3)
   except: p.kill()
if __name__=='__main__':run()
