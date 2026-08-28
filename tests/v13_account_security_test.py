#!/usr/bin/env python3
"""V13 account-security regression checks for legacy rehash, sessions and browser CSRF."""
from __future__ import annotations
import hashlib,http.cookiejar,json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.error,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def api(base,path,method='GET',body=None,token=None,expected=200,headers=None,opener=None):
    data=None if body is None else json.dumps(body).encode('utf-8');h={'Content-Type':'application/json',**(headers or {})}
    if token:h['Authorization']=f'Bearer {token}'
    req=urllib.request.Request(base+path,data=data,method=method,headers=h)
    runner=opener.open if opener else urllib.request.urlopen
    try:
        with runner(req,timeout=20) as response:status=response.status;raw=response.read()
    except urllib.error.HTTPError as exc:status=exc.code;raw=exc.read()
    if status!=expected:
        try:shown=json.loads(raw or b'{}')
        except Exception:shown=raw[:200]
        raise AssertionError((method,path,status,expected,shown))
    return json.loads(raw or b'{}')

def wait(base):
    for _ in range(120):
        try:api(base,'/api/health');return
        except Exception:time.sleep(.1)
    raise RuntimeError('server did not start')

def run():
    port=free_port();base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='einvite-v13-sec-') as data_dir:
        env={**os.environ,'EINVITE_DATA_DIR':data_dir,'EINVITE_DEV_AUTH_TOKENS':'1'}
        proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'server.py'),'--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            wait(base)
            # Insert a genuine V12 PBKDF2-v1 account and prove successful login upgrades it.
            password='legacy-password-strong';salt=os.urandom(16).hex();digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),210_000).hex();uid=str(uuid.uuid4())
            db=sqlite3.connect(Path(data_dir)/'invites.db');db.execute("INSERT INTO users(id,email,password_hash,salt,password_algo,created_at,role,email_verified,plan) VALUES(?,?,?,?,?,?,?,0,'free')",(uid,'legacy-v13@example.com',digest,salt,'pbkdf2-sha256-v1',int(time.time()*1000),'customer'));db.commit();db.close()
            login=api(base,'/api/auth/login','POST',{'email':'legacy-v13@example.com','password':password},expected=201);token1=login['token']
            security=api(base,'/api/account/security',token=token1);assert security['passwordAlgorithm']=='argon2id-v1',security
            # A second sign-in creates another revocable device session.
            login2=api(base,'/api/auth/login','POST',{'email':'legacy-v13@example.com','password':password},expected=201);token2=login2['token']
            sessions=api(base,'/api/account/sessions',token=token1);other=next(x for x in sessions if not x['current'])
            result=api(base,f"/api/account/sessions/{other['id']}",'DELETE',token=token1);assert result['revoked'] is True
            assert api(base,'/api/auth/me',token=token2)['user'] is None
            # Browser cookie authentication requires the per-session double-submit token.
            jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            browser=api(base,'/api/auth/register','POST',{'email':'browser-csrf@example.com','password':'browser-password-strong'},expected=201,opener=opener)
            origin={'Origin':base,'Sec-Fetch-Site':'same-origin'}
            api(base,'/api/account/privacy','POST',{'analyticsConsent':True},expected=403,headers=origin,opener=opener)
            ok=api(base,'/api/account/privacy','POST',{'analyticsConsent':True,'externalMediaConsent':False,'guestDataRetentionDays':30},headers={**origin,'X-CSRF-Token':browser['csrfToken']},opener=opener)
            assert ok['privacy']['analyticsConsent'] is True and ok['privacy']['guestDataRetentionDays']==30
            # Sign out other devices keeps the current session when requested.
            keep=api(base,'/api/account/sessions/revoke-all','POST',{'keepCurrent':True},token=token1);assert keep['keptCurrent'] is True
            assert api(base,'/api/auth/me',token=token1)['user']['email']=='legacy-v13@example.com'
            print('V13_ACCOUNT_SECURITY_TEST_PASSED')
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            if proc.stderr and proc.returncode not in (0,-15):
                err=proc.stderr.read().decode('utf-8','replace')
                if err:print(err,file=sys.stderr)
if __name__=='__main__':run()
