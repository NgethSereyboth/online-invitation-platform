#!/usr/bin/env python3
"""Verify collaborators have consistent material permissions across local storage APIs."""
from __future__ import annotations
import base64,json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def call(base,path,method='GET',body=None,cookie=None,headers=None,raw=False):
    if raw:data=body
    else:data=None if body is None else json.dumps(body).encode()
    h={} if raw else {'Content-Type':'application/json'}
    h.update(headers or {})
    if cookie:h['Cookie']=cookie
    req=urllib.request.Request(base+path,data=data,method=method,headers=h)
    try:
        with urllib.request.urlopen(req,timeout=8) as r:return r.status,json.loads(r.read() or b'{}'),dict(r.headers)
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b'{}'),dict(e.headers)

def register(base,email):
    status,payload,h=call(base,'/api/auth/register','POST',{'email':email,'password':'password123'});assert status==201,payload
    return payload,(h.get('Set-Cookie') or h.get('set-cookie')).split(';',1)[0]

def run():
    p=port();base=f'http://127.0.0.1:{p}'
    with tempfile.TemporaryDirectory(prefix='einvite-collab-assets-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data,'EINVITE_ENFORCE_PLAN_LIMITS':'1'};env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
        proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(p)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    if call(base,'/api/health')[0]==200:break
                except Exception:time.sleep(.1)
            owner,owner_cookie=register(base,'owner-assets@example.com');editor,editor_cookie=register(base,'editor-assets@example.com');viewer,viewer_cookie=register(base,'viewer-assets@example.com')
            doc={'fields':{'names':'Shared assets'},'objects':{},'designPages':[],'sectionOrder':[],'settings':{}}
            status,inv,_=call(base,'/api/invitations','POST',{'slug':'shared-assets','document':doc},owner_cookie);assert status==201,inv;iid=inv['id']
            for email,role in [('editor-assets@example.com','designer'),('viewer-assets@example.com','viewer')]:
                status,payload,_=call(base,f'/api/invitations/{iid}/collaborators','POST',{'email':email,'role':role},owner_cookie);assert status==200,payload
            upload_headers={'Content-Type':'image/png','X-File-Name':urllib.parse.quote('shared.png')}
            status,asset,_=call(base,f'/api/invitations/{iid}/assets/raw','POST',PNG,editor_cookie,upload_headers,raw=True);assert status==201,asset
            aid=asset['id']
            status,items,_=call(base,f'/api/invitations/{iid}/assets',cookie=editor_cookie);assert status==200 and any(x['id']==aid for x in items),items
            status,library,_=call(base,'/api/assets',cookie=editor_cookie);assert status==200 and any(x['id']==aid and x['invitationId']==iid for x in library),library
            status,updated,_=call(base,f'/api/assets/{aid}','PUT',{'name':'renamed.png','folder':'Shared','tags':['team'],'favorite':True},editor_cookie);assert status==200 and updated['name']=='renamed.png',updated
            status,blocked,_=call(base,f'/api/invitations/{iid}/assets/raw','POST',PNG,viewer_cookie,upload_headers,raw=True);assert status in {403,404},blocked
            status,deleted,_=call(base,f'/api/invitations/{iid}/assets/{aid}','DELETE',cookie=editor_cookie);assert status==200 and deleted['deleted'],deleted

            # Project storage is charged to the invitation owner, not the collaborator who uploads.
            # Give the collaborator a Studio plan, fill the owner's Free-plan quota, then verify the
            # collaborator still cannot add more bytes to the owner's invitation.
            db=sqlite3.connect(str(Path(data)/'invites.db'))
            try:
                db.execute("UPDATE users SET plan='studio' WHERE email='editor-assets@example.com'")
                owner_id=db.execute("SELECT id FROM users WHERE email='owner-assets@example.com'").fetchone()[0]
                assert db.execute("SELECT plan FROM users WHERE id=?",(owner_id,)).fetchone()[0]=='free'
                fake_size=250_000_000-len(PNG)+1
                now=int(time.time()*1000)
                db.execute("INSERT INTO stored_objects(id,owner_id,path,storage_key,sha256,mime,size,width,height,dominant_color,processing_state,quarantine_state,scan_status,ref_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('quota-object',owner_id,'quota-fill.png','quota-fill.png','quota-sha','image/png',fake_size,1,1,'#000000','ready','released','test',1,now,now))
                db.execute("INSERT INTO assets(id,invitation_id,object_id,name,mime,path,size,created_at,folder,tags_json,favorite,sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",('quota-fill',iid,'quota-object','quota.bin','image/png','quota-fill.png',fake_size,now,'','[]',0,'quota-sha'))
                db.commit()
            finally:db.close()
            status,quota_block,_=call(base,f'/api/invitations/{iid}/assets/raw','POST',PNG,editor_cookie,upload_headers,raw=True)
            assert status==403 and quota_block.get('code')=='plan_limit_reached',quota_block
        finally:
            proc.terminate()
            try:proc.wait(3)
            except:proc.kill()
    print('COLLABORATION_ASSET_PERMISSIONS_TEST_PASSED')

if __name__=='__main__':run()
