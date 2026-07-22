"""Tests for production-oriented foundations added after the main feature suite."""
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
def wait(base):
 for _ in range(100):
  try:
   if req(base,'/api/health')[0]==200:return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def run():
 port=free_port();base=f'http://127.0.0.1:{port}'
 with tempfile.TemporaryDirectory(prefix='einvite-prod-foundations-') as d:
  secret='billing-secret';env={**os.environ,'EINVITE_DATA_DIR':d,'EINVITE_BILLING_WEBHOOK_SECRET':secret}
  p=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   wait(base)
   _,owner,h=req(base,'/api/auth/register','POST',{'email':'owner@example.com','password':'password123'},expected=201);owner_token=owner['token'];cookie=h.get('Set-Cookie') or h.get('set-cookie');assert cookie and 'HttpOnly' in cookie
   # Cookie-only auth works.
   cookie_pair=cookie.split(';',1)[0];_,me,_=req(base,'/api/auth/me',cookie=cookie_pair);assert me['user']['email']=='owner@example.com'
   # A non-secret browser session marker may be sent as a legacy Bearer header; the valid HttpOnly cookie still authenticates.
   _,me_marker,_=req(base,'/api/auth/me',token='cookie-session',cookie=cookie_pair);assert me_marker['user']['email']=='owner@example.com'
   _,collab,_=req(base,'/api/auth/register','POST',{'email':'designer@example.com','password':'password123'},expected=201);collab_token=collab['token']
   doc={'eventType':'Wedding','fields':{'names':'Foundation Test','date':'2026-12-27','venue':'Venue','message':'Join us'},'objects':{},'designPages':[],'sectionOrder':['schedule','venue','rsvp'],'settings':{'rsvpEnabled':True}}
   _,inv,_=req(base,'/api/invitations','POST',{'slug':'foundation-test','document':doc},owner_token,expected=201);iid=inv['id']
   _,added,_=req(base,f'/api/invitations/{iid}/collaborators','POST',{'email':'designer@example.com','role':'designer'},owner_token,expected=200);assert added['role']=='designer'
   _,shared,_=req(base,'/api/invitations',token=collab_token);assert any(i['id']==iid and i['shared'] for i in shared)
   doc['fields']['message']='Edited collaboratively';req(base,f'/api/invitations/{iid}','PUT',{'document':doc},collab_token,expected=200)
   _,got,_=req(base,f'/api/invitations/{iid}',token=owner_token);assert got['document']['fields']['message']=='Edited collaboratively'
   # Local AI fallback is usable without credentials.
   _,ai,_=req(base,'/api/ai/assist','POST',{'task':'romantic','prompt':'','context':{'names':'A & B','eventType':'Wedding'}},owner_token,expected=200);assert ai['provider']=='local' and ai['text']
   # Billing webhook signature updates a plan.
   payload=json.dumps({'type':'subscription.updated','data':{'email':'designer@example.com','plan':'creator'}}).encode();sig=hmac.new(secret.encode(),payload,hashlib.sha256).hexdigest()
   request=urllib.request.Request(base+'/api/billing/webhook',data=payload,method='POST',headers={'Content-Type':'application/json','X-EInvite-Signature':sig})
   with urllib.request.urlopen(request,timeout=8) as x:assert x.status==200
   _,usage,_=req(base,'/api/account/usage',token=collab_token);assert usage['plan']=='creator'
   # Logout clears cookie.
   _,_,logout_headers=req(base,'/api/auth/logout','POST',{},token='cookie-session',cookie=cookie_pair);assert 'Max-Age=0' in (logout_headers.get('Set-Cookie') or logout_headers.get('set-cookie') or '')
   print('PRODUCTION_FOUNDATIONS_TEST_PASSED')
  finally:
   p.terminate()
   try:p.wait(3)
   except: p.kill()
if __name__=='__main__':run()
