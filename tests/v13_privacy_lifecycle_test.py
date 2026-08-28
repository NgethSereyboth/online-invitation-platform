#!/usr/bin/env python3
"""V13 privacy/account lifecycle coverage: export, archive, passkey challenge and recoverable deletion."""
from __future__ import annotations
import io,json,os,subprocess,sys,tempfile,time,urllib.error,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PORT=8127;BASE=f'http://127.0.0.1:{PORT}'

def wait():
    for _ in range(100):
        try:
            if urllib.request.urlopen(BASE+'/api/health',timeout=.5).status==200:return
        except Exception:time.sleep(.08)
    raise RuntimeError('server unavailable')

def request(path,method='GET',body=None,token=''):
    data=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json'} if data is not None else {}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=10) as r:return r.status,r.read(),dict(r.headers)
    except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)

def js(path,method='GET',body=None,token='',expected=200):
    status,raw,_=request(path,method,body,token);payload=json.loads(raw or b'{}');assert status==expected,(path,status,payload);return payload

def main():
    with tempfile.TemporaryDirectory(prefix='einvite-v13-privacy-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data,'EINVITE_DEV_AUTH_TOKENS':'1'}
        proc=subprocess.Popen([sys.executable,'-u','server.py','--port',str(PORT)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait();password='privacy-strong-password';registered=js('/api/auth/register','POST',{'email':'privacy-v13@example.com','password':password},expected=201);token=registered['token']
            invite=js('/api/invitations','POST',{'slug':'privacy-v13','document':{'fields':{'names':'Private export'},'objects':{},'designPages':[],'settings':{'rsvpEnabled':False}}},token=token,expected=201)
            exported=js('/api/account/export',token=token);assert exported['account']['email']=='privacy-v13@example.com' and any(x['id']==invite['id'] for x in exported['invitations'])
            status,raw,headers=request('/api/account/export/archive',token=token);assert status==200 and 'application/zip' in headers.get('Content-Type','');archive=zipfile.ZipFile(io.BytesIO(raw));assert 'account.json' in archive.namelist();account=json.loads(archive.read('account.json'));assert any(x['id']==invite['id'] for x in account['invitations'])
            options=js('/api/account/passkeys/register/options','POST',{},token=token);assert options['challengeId'] and options['publicKey']['challenge'] and options['publicKey']['rp']['id']
            scheduled=js('/api/account/delete/schedule','POST',{'password':password},token=token);assert scheduled['scheduled'] and scheduled['purgeAt']>int(time.time()*1000)
            cancelled=js('/api/account/delete/cancel','POST',{},token=token);assert cancelled['scheduled'] is False
            audit=js('/api/account/audit',token=token);actions={row['action'] for row in audit};assert {'account.deletion_scheduled','account.deletion_cancelled'}<=actions,actions
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()
    print('V13_PRIVACY_LIFECYCLE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
