"""Shared process/server helpers for V14 cross-platform release tests."""
from __future__ import annotations
import contextlib,gc,os,shutil,signal,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return int(sock.getsockname()[1])

def wait_http(url,timeout=12.0):
    deadline=time.time()+timeout;last=None
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=.5) as response:
                if response.status<500:return response
        except Exception as exc:last=exc;time.sleep(.08)
    raise RuntimeError(f'Server did not become ready: {url}: {last}')

def process_options():
    if os.name=='nt':return {'creationflags':getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)}
    return {'start_new_session':True}

def stop_process(process,timeout=8):
    if process is None or process.poll() is not None:return
    try:
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=timeout)
        else:
            os.killpg(process.pid,signal.SIGTERM)
    except Exception:
        try:process.terminate()
        except Exception:pass
    try:process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            if os.name!='nt':os.killpg(process.pid,signal.SIGKILL)
            else:process.kill()
        except Exception:pass
        try:process.wait(timeout=3)
        except Exception:pass

def cleanup_path(path,retries=12):
    path=Path(path)
    for attempt in range(retries):
        try:
            if path.exists():shutil.rmtree(path)
            return
        except (PermissionError,OSError):
            gc.collect();time.sleep(min(.08*(attempt+1),.75))
    if path.exists():raise RuntimeError(f'Unable to clean temporary test directory: {path}')

@contextlib.contextmanager
def temporary_data(prefix='einvite-v14-'):
    path=Path(tempfile.mkdtemp(prefix=prefix))
    try:yield path
    finally:cleanup_path(path)

@contextlib.contextmanager
def app_server(extra_env=None):
    with temporary_data('einvite-live-v14-') as data:
        port=free_port();base=f'http://127.0.0.1:{port}'
        env={**os.environ,'EINVITE_DATA_DIR':str(data),'EINVITE_DEV_AUTH_TOKENS':'1','EINVITE_REQUIRE_EMAIL_VERIFICATION':'0'}
        env.update(extra_env or {})
        log_path=data/'server-test.log'
        log_handle=log_path.open('w',encoding='utf-8',buffering=1)
        process=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log_handle,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        failed=False
        try:
            wait_http(base+'/api/health');yield process,base,data
        except Exception:
            failed=True
            raise
        finally:
            if process.poll() is None:
                try:
                    if os.name=='nt':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)
                    else:
                        process.terminate()
                except Exception:pass
                try:process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    try:process.kill();process.wait(timeout=3)
                    except Exception:pass
            try:log_handle.close()
            except Exception:pass
            if failed:
                try:
                    tail=log_path.read_text(encoding='utf-8',errors='replace').splitlines()[-80:]
                    if tail:print('\n[V14 server log tail]\n'+'\n'.join(tail),flush=True)
                except Exception:pass
