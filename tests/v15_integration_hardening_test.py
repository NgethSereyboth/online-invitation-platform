#!/usr/bin/env python3
"""Deterministic integration checks for V15 route/lifecycle hardening."""
from __future__ import annotations
import hashlib,json,os,signal,shutil,socket,subprocess,sys,tempfile,time,urllib.request
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class Assets(HTMLParser):
    def __init__(self):super().__init__();self.scripts=[];self.styles=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if tag=='script' and data.get('src'):self.scripts.append(data['src'])
        if tag=='link' and data.get('rel')=='stylesheet':self.styles.append(data.get('href'))

def free_port():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def wait_health(url,timeout=15):
    end=time.time()+timeout
    while time.time()<end:
        try:
            with urllib.request.urlopen(url,timeout=.6) as response:
                if response.status==200:return json.loads(response.read())
        except Exception:time.sleep(.1)
    raise AssertionError('V15 server did not become healthy')



def graceful_process_kwargs():
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}

def request_graceful_stop(process):
    if os.name == "nt":
        event = getattr(signal, "CTRL_BREAK_EVENT", None)
        if event is None:
            raise AssertionError("Windows graceful shutdown requires CTRL_BREAK_EVENT support")
        process.send_signal(event)
    else:
        os.killpg(process.pid, signal.SIGTERM)

def cleanup_retry(path):
    path=Path(path)
    for attempt in range(12):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except (PermissionError,OSError):
            time.sleep(min(.1*(attempt+1),.8))
    shutil.rmtree(path)

def main():
    subprocess.run([sys.executable,'build_route_bundles.py','--check'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'build_page_manifests.py','--check'],cwd=ROOT,check=True)
    source=json.loads((ROOT/'route-bundle-sources-v15.json').read_text(encoding='utf-8'))
    built=json.loads((ROOT/'route-bundles-v15.json').read_text(encoding='utf-8'))
    assert source['version']==15 and built['version']==15
    for page,entry in source['pages'].items():
        parser=Assets();parser.feed((ROOT/page).read_text(encoding='utf-8'))
        expected_script=f'bundle-{Path(page).stem}-v15.js';expected_style=f'bundle-{Path(page).stem}-v15.css'
        assert parser.styles==[expected_style],(page,parser.styles)
        if entry['scripts']:
            assert parser.scripts[-1]==expected_script,(page,parser.scripts)
        else:
            assert expected_script not in parser.scripts,(page,parser.scripts)
        assert len(parser.scripts)<=3,(page,parser.scripts)
        js_path=ROOT/expected_script;css_path=ROOT/expected_style
        js=js_path.read_text(encoding='utf-8');css=css_path.read_text(encoding='utf-8')
        # The route manifest is the authoritative source list; generated source-boundary
        # comments are intentionally omitted to keep startup routes within fixed budgets.
        built_entry=built['pages'][page]
        assert built_entry['sources']==entry,(page,built_entry['sources'],entry)
        assert hashlib.sha256(js_path.read_bytes()).hexdigest()==built_entry['scriptSha256'],page
        assert hashlib.sha256(css_path.read_bytes()).hexdigest()==built_entry['styleSha256'],page
    editor=source['pages']['index.html']['scripts']
    assert editor.count('collaboration-live.js')==1 and editor.count('app.js')==1
    assert editor[0]=='runtime-lifecycle-v15.js'
    public=source['pages']['public.html']['scripts'];assert public[0]=='runtime-lifecycle-v15.js' and public.count('public-page.js')==1

    assets=json.loads((ROOT/'page-assets-v15.json').read_text(encoding='utf-8'))
    assert assets['version']==15
    assert assets['pages']['index.html']['scriptCount']==3 and assets['pages']['index.html']['styleCount']==1
    assert assets['pages']['public.html']['bytes']>200_000  # root-relative assets are honestly counted

    sw=(ROOT/'service-worker.js').read_text(encoding='utf-8')
    assert "CACHE='einvite-checkin-v15'" in sw
    assert "if(!STATIC.has(url.pathname))return" in sw
    assert "url.pathname.startsWith('/api/')" in sw
    assert "event.respondWith(networkFirst(request,request))" in sw
    assert 'dashboard.html' not in sw and 'account.html' not in sw

    collab=(ROOT/'collaboration-live.js').read_text(encoding='utf-8')
    assert collab.count('/presence`')==1,collab.count('/presence`')
    assert 'payload.presence' in collab and 'scheduleSseRetry' in collab
    lifecycle=(ROOT/'runtime-lifecycle-v15.js').read_text(encoding='utf-8')
    assert "if(!event.persisted)cleanup()" in lifecycle and "pagehide',cleanup" not in lifecycle
    public_js=(ROOT/'public-page.js').read_text(encoding='utf-8')
    assert 'countdownTimer' in public_js and 'EInviteLifecycle' in public_js
    assert "button.disabled=false" in public_js and "data-submit-status" in public_js

    node=r'''global.window=global;global.localStorage={getItem:()=>null,setItem:()=>{},removeItem:()=>{}};delete global.indexedDB;require(process.argv[1]);(async()=>{await assetStore.put({id:'a',name:'fallback.png'});const rows=await assetStore.list();if(rows.length!==1||rows[0].name!=='fallback.png')throw Error('fallback');await assetStore.delete('a');if((await assetStore.list()).length)throw Error('delete');console.log('ok')})().catch(e=>{console.error(e);process.exit(1)})'''
    result=subprocess.run(['node','-e',node,str(ROOT/'storage.js')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stderr

    # In-process presence fallback de-duplicates and expires stale rows.
    old=os.environ.get('EINVITE_DATA_DIR');os.environ['EINVITE_DATA_DIR']=tempfile.mkdtemp(prefix='einvite-v15-presence-')
    sys.path.insert(0,str(ROOT));import server
    now=int(time.time()*1000);server.PRESENCE_STATE.clear()
    server.PRESENCE_STATE[('inv','user','client')]={'userId':'user','clientId':'client','updatedAt':now,'email':'a@example.com'}
    server.PRESENCE_STATE[('inv','old','old')]={'userId':'old','clientId':'old','updatedAt':now-120_000,'email':'old@example.com'}
    rows=server.current_presence('inv');assert len(rows)==1 and rows[0]['clientId']=='client'
    if old is None:os.environ.pop('EINVITE_DATA_DIR',None)
    else:os.environ['EINVITE_DATA_DIR']=old

    # The real server receives a platform-supported graceful signal. On Windows
    # terminate() is a forced TerminateProcess call, so CTRL_BREAK_EVENT is used
    # for real signal-handler coverage instead.
    data=tempfile.mkdtemp(prefix='einvite-v16-server-')
    port=free_port();env={**os.environ,'EINVITE_DATA_DIR':data,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
    process=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',**graceful_process_kwargs())
    try:
        health=wait_health(f'http://127.0.0.1:{port}/api/health');assert health.get('ok') is True
        started=time.monotonic();request_graceful_stop(process);process.wait(timeout=10);assert time.monotonic()-started<10
        assert process.returncode==0,process.returncode
    finally:
        if process.poll() is None:
            process.kill();process.wait(timeout=5)
    cleanup_retry(data)
    assert not Path(data).exists(),data
    print('V15_INTEGRATION_HARDENING_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
