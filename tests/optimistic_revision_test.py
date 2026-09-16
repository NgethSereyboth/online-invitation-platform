#!/usr/bin/env python3
"""Verify stale collaborative autosaves cannot overwrite newer revisions."""
from __future__ import annotations
import json,os,socket,subprocess,sys,tempfile,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def call(base,path,method='GET',body=None,cookie=None,headers=None):
    raw=None if body is None else json.dumps(body).encode()
    h={'Content-Type':'application/json',**(headers or {})}
    if cookie:h['Cookie']=cookie
    req=urllib.request.Request(base+path,data=raw,method=method,headers=h)
    try:
        with urllib.request.urlopen(req,timeout=8) as r:return r.status,json.loads(r.read() or b'{}'),dict(r.headers)
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b'{}'),dict(e.headers)

def run():
    p=port();base=f'http://127.0.0.1:{p}'
    with tempfile.TemporaryDirectory(prefix='einvite-revision-lock-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data};env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
        proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(p)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    if call(base,'/api/health')[0]==200:break
                except Exception:time.sleep(.1)
            _,_,h=call(base,'/api/auth/register','POST',{'email':'lock@example.com','password':'password123'})
            cookie=(h.get('Set-Cookie') or h.get('set-cookie')).split(';',1)[0]
            doc={'fields':{'names':'Initial'},'objects':{},'designPages':[],'sectionOrder':[],'settings':{}}
            status,created,_=call(base,'/api/invitations','POST',{'slug':'lock','document':doc},cookie);assert status==201,created
            revision=created['updatedAt'];iid=created['id']
            doc_a={**doc,'fields':{'names':'Writer A'}}
            status,saved,_=call(base,f'/api/invitations/{iid}','PUT',{'document':doc_a,'expectedRevision':revision},cookie,{'X-EInvite-Client-Id':'a','X-EInvite-Mutation-Id':'a1'})
            assert status==200 and saved['updatedAt']>revision,saved
            doc_b={**doc,'fields':{'names':'Writer B'}}
            status,conflict,_=call(base,f'/api/invitations/{iid}','PUT',{'document':doc_b,'expectedRevision':revision},cookie,{'X-EInvite-Client-Id':'b','X-EInvite-Mutation-Id':'b1'})
            assert status==409 and conflict.get('code')=='revision_conflict' and conflict['updatedAt']==saved['updatedAt'],conflict
            status,latest,_=call(base,f'/api/invitations/{iid}',cookie=cookie);assert status==200
            assert latest['document']['fields']['names']=='Writer A',latest
            # Legacy clients remain supported, but current editor sends expectedRevision.
            status,legacy,_=call(base,f'/api/invitations/{iid}','PUT',{'document':doc_b},cookie);assert status==200,legacy
        finally:
            proc.terminate()
            try:proc.wait(3)
            except:proc.kill();proc.wait(timeout=5)
    app=(ROOT/'app.js').read_text(encoding='utf-8')
    assert 'expectedRevision:serverInvite.updatedAt??null' in app or 'expectedRevision: serverInvite.updatedAt ?? null' in app
    assert 'serverSaveBlockedByConflict = true' in app or 'serverSaveBlockedByConflict=true' in app
    print('OPTIMISTIC_REVISION_TEST_PASSED')

if __name__=='__main__':run()
