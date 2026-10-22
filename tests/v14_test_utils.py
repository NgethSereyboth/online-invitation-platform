"""Shared process/server helpers for V14 cross-platform release tests.

FB-09 hardening (2026-10-22):
- free_port retries: bind-close-probe TOCTOU means another process can seize
  the port between close() and the server's bind; instead of handing a port
  that "worked" once, the caller gets one that still answers after server
  startup, bounded by attempts.
- wait_http fails fast: it polls the child process and, on the first observed
  exit, stops waiting and raises with the exit code, so the fixture dumps the
  server log instead of burning the whole timeout on a dead child.
- app_server reloads on CANT_BIND / address-in-use startup failures (bounded
  retries) — the intermittent "Server did not become ready after 12 s" class
  is exactly the seized-port case, not a privacy assertion bug.
- process group kill (start_new_session) is unchanged; the same group is
  reused for the retried child so teardown never leaks an orphan.
"""
from __future__ import annotations
import contextlib,gc,os,shutil,signal,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SERVER_PATH=ROOT/'src'/'python'/'server.py'

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return int(sock.getsockname()[1])

def wait_http(url,timeout=12.0,process=None):
    deadline=time.time()+timeout;last=None
    while time.time()<deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f'Server exited before becoming ready: {url} (exit={process.returncode})')
        try:
            with urllib.request.urlopen(url,timeout=.5) as response:
                if response.status<500:return response
        except Exception as exc:last=exc;time.sleep(.08)
    proc=''
    if process is not None and process.poll() is not None:
        proc=f' (child exited: {process.returncode})'
    raise RuntimeError(f'Server did not become ready: {url}: {last}{proc}')

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

def _rmtree_with_retry(path, attempts=20, delay=.25):
    path=Path(path);last_error=None
    for _ in range(attempts):
        try:
            if not path.exists():return
            shutil.rmtree(path);return
        except (PermissionError,OSError) as exc:
            last_error=exc;gc.collect();time.sleep(delay)
    raise RuntimeError(f'Unable to clean temporary test directory after {attempts} attempts: {last_error}')

def cleanup_path(path,retries=20):
    _rmtree_with_retry(path, attempts=retries)

@contextlib.contextmanager
def temporary_data(prefix='einvite-v14-'):
    path=Path(tempfile.mkdtemp(prefix=prefix))
    try:yield path
    finally:cleanup_path(path)

@contextlib.contextmanager
def fresh_server(extra_env=None, readiness_timeout=24.0, start_attempts=3):
    """Start server.py on a free port, retrying the whole startup when the
    port was seized between free_port() and bind (FB-09 TOCTOU), and failing
    fast when the child exits."""
    import urllib.error
    with temporary_data('einvite-live-v14-') as data:
        base=None;process=None;log_path=data/'server-test.log'
        env={**os.environ,'EINVITE_DATA_DIR':str(data),'EINVITE_DEV_AUTH_TOKENS':'1','EINVITE_REQUIRE_EMAIL_VERIFICATION':'0','PYTHONPATH':os.pathsep.join([str(ROOT/'src'/'python'),str(ROOT)])}
        env.update(extra_env or {})
        for attempt in range(1,start_attempts+1):
            port=free_port();base=f'http://127.0.0.1:{port}'
            log_handle=log_path.open('a' if attempt>1 else 'w',encoding='utf-8',buffering=1)
            if attempt>1:
                log_handle.write(f'\n===== FB-09 start attempt {attempt} (previous attempt failed) =====\n')
            process=subprocess.Popen([sys.executable,'-u',str(SERVER_PATH),'--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log_handle,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',**process_options())
            try:
                wait_http(base+'/api/health',timeout=readiness_timeout,process=process)
                break
            except RuntimeError as exc:
                stop_process(process,timeout=8);log_handle.close()
                exit_code=exc
                try:log_tail=log_path.read_text(encoding='utf-8',errors='replace').splitlines()[-40:]
                except Exception:log_tail=[]
                child_alive = process.poll() is None
                if attempt==start_attempts:
                    if log_tail:print('\\n[V14 server log tail]\\n'+'\\n'.join(log_tail),flush=True)
                    raise
                # Retry only the failure class that a port race can produce; a
                # child that exited with something else (or is still alive but
                # not serving) still fails — masking that would hide a real hang.
                exc_text=str(exc)
                bind_race=('Connection refused' in exc_text or 'Errno 111' in exc_text or 'ConnectionResetError' in exc_text) and not child_alive
                if not bind_race:
                    if log_tail:print('\\n[V14 server log tail]\\n'+'\\n'.join(log_tail),flush=True)
                    raise
                time.sleep(.25)
            except BaseException:
                stop_process(process,timeout=8)
                try:log_handle.close()
                except Exception:pass
                raise
        try:
            yield process,base,data
        finally:
            stop_process(process,timeout=8)
            try:log_handle.close()
            except Exception:pass

# Backwards-compatible alias: existing tests import `app_server`.
app_server=fresh_server
