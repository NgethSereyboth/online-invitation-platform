#!/usr/bin/env python3
"""Verify self-originated revisions are identifiable and ignored by the browser sync UI."""
from __future__ import annotations
import json,os,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from browser_runtime import launch_chromium
ROOT=Path(__file__).resolve().parents[1]

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def call(base,path,method='GET',body=None,cookie=None,headers=None):
    raw=None if body is None else json.dumps(body).encode()
    h={'Content-Type':'application/json',**(headers or {})}
    if cookie:h['Cookie']=cookie
    req=urllib.request.Request(base+path,data=raw,method=method,headers=h)
    with urllib.request.urlopen(req,timeout=8) as r:
        return r.status,json.loads(r.read() or b'{}'),dict(r.headers)

def run():
    p=port();base=f'http://127.0.0.1:{p}'
    with tempfile.TemporaryDirectory(prefix='einvite-revision-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data}
        env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
        proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(p)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    if call(base,'/api/health')[0]==200:break
                except Exception:time.sleep(.1)
            _,_,h=call(base,'/api/auth/register','POST',{'email':'revision@example.com','password':'password123'})
            cookie=(h.get('Set-Cookie') or h.get('set-cookie')).split(';',1)[0]
            doc={'fields':{'names':'Revision'},'objects':{},'designPages':[],'sectionOrder':[],'settings':{}}
            _,inv,_=call(base,'/api/invitations','POST',{'slug':'revision','document':doc},cookie);iid=inv['id']
            headers={'X-EInvite-Client-Id':'client-a','X-EInvite-Mutation-Id':'mutation-a'}
            _,saved,_=call(base,f'/api/invitations/{iid}','PUT',{'document':doc},cookie,headers)
            assert saved['clientId']=='client-a' and saved['mutationId']=='mutation-a' and saved['updatedAt']>0,saved
            _,got,_=call(base,f'/api/invitations/{iid}',cookie=cookie)
            assert got['lastClientId']=='client-a' and got['lastMutationId']=='mutation-a',got
            _,published,_=call(base,f'/api/invitations/{iid}/publish','POST',{'document':doc},cookie,{'X-EInvite-Client-Id':'client-b','X-EInvite-Mutation-Id':'mutation-b'})
            assert published['clientId']=='client-b' and published['mutationId']=='mutation-b' and published['updatedAt']>0,published
        finally:
            proc.terminate()
            try:proc.wait(3)
            except:proc.kill()

    source=(ROOT/'collaboration-live.js').read_text(encoding='utf-8')
    assert 'origin===clientId' in source and 'ownMutations.has(mutation)' in source and 'einvite:local-revision' in source

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f'COLLABORATION_BROWSER_LOGIC_SKIPPED_NO_PLAYWRIGHT: {exc}')
    else:
        with sync_playwright() as pw:
            try:
                browser=launch_chromium(pw)
            except Exception as exc:
                print(f'COLLABORATION_BROWSER_LOGIC_SKIPPED_NO_CHROMIUM: {exc}')
                browser=None
            if browser:
                page=browser.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                script=source.replace('</script>','<\\/script>')
                html=f'''<!doctype html><body><div id="stage"></div><script>
                const __l=new Map([['sovan-active-invite','invite-1']]),__s=new Map();
                function store(m){{return{{getItem:k=>m.get(String(k))??null,setItem:(k,v)=>m.set(String(k),String(v)),removeItem:k=>m.delete(String(k))}}}}
                const localStorage=store(__l),sessionStorage=store(__s);
                window.serverInvite={{id:'invite-1',updatedAt:100}};
                window.uiConfirm=async()=>true;window.uiToast=()=>{{}};
                window.fetch=async()=>({{ok:true,json:async()=>({{updatedAt:100}})}});
                window.EventSource=class{{constructor(){{this.handlers={{}}}}addEventListener(n,fn){{this.handlers[n]=fn}}close(){{}}}};
                </script><script>{script}</script></body>'''
                page.set_content(html,wait_until='load');page.wait_for_timeout(80)
                result=page.evaluate("""()=>{
                    const sync=window.EInviteCollaborationSync,chip=document.querySelector('#eiRemoteChangeChip'),client=sync.clientId;
                    sync.acceptLocal({updatedAt:110,mutationId:'mine'});
                    sync.receive({updatedAt:110,clientId:'other',mutationId:'mine'});
                    const ownMutationHidden=chip.hidden;
                    sync.receive({updatedAt:120,clientId:client,mutationId:'server-copy'});
                    const ownClientHidden=chip.hidden;
                    sync.receive({updatedAt:130,clientId:'other-client',mutationId:'remote'});
                    return {ownMutationHidden,ownClientHidden,remoteVisible:!chip.hidden,known:sync.knownRevision};
                }""")
                assert not errors,errors
                assert result['ownMutationHidden'] and result['ownClientHidden'] and result['remoteVisible'] and result['known']==130,result
                browser.close()
    print('COLLABORATION_REVISION_TEST_PASSED')

if __name__=='__main__':run()
