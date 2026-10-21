#!/usr/bin/env python3
"""tools/run-gates.py — one-command gate runner for the eInvite repo (Linux portable).

Phases (default --phase all): build → bundles → smoke → pytest → lhci → canvas.
  build   `python3 build.py all`            (BUILD_OK + MIRROR_CHECK_PASSED)
  bundles `python3 build.py bundles --check` (ROUTE_BUNDLE_CHECK_PASSED)
  smoke   `tools/serve-gzip.py --port <port>` + `node tools/page-errors.mjs --all`
  pytest  `PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/ -q`  (default capture)
  lhci    `npx lhci collect` + `npx lhci assert`     (a11y must stay 1.00)
  canvas  `.venv/bin/python tests/canvas_motion_playwright.py --phase all --output <abs>`
          (visual gate: NOT RUN here — frozen baseline lives on the Windows box)

Behaviour
  - Starts/stops its own servers (gzip static server for smoke+lhci; process cleanly
    reaped in finally). The canvas phase runs the frozen harness that manages its own
    app server.
  - Serializes heavy runs with a lock file (``artifacts/next-work/gates/.run-gates.lock``);
    a second concurrent run exits 3 immediately.
  - Logs every command + exit code + key output line to
    ``artifacts/next-work/gates/<timestamp>/<phase>.log`` and prints a one-line summary
    per gate; the run stops at the first failing gate (subsequent gates report SKIPPED).
  - Pins nothing and modifies no frozen tool: the canvas gate is called as-is and the
    renderer is whatever the host provides (`launch_chromium` picks chromium/Chrome).

Exit codes: 0 all requested gates green; 1 a gate failed; 2 usage/config error;
3 another gate run holds the lock; 4 lock/python/env failure.
"""
from __future__ import annotations
import argparse,datetime,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GATES_DIR=ROOT/'artifacts'/'next-work'/'gates'
LOCK=GATES_DIR/'.run-gates.lock'
PHASES=['build','bundles','smoke','pytest','lhci','canvas']
PY=sys.executable
VENV_PY=ROOT/'.venv'/'bin'/'python'

def log_line(log,marker,text=''):
    stamp=datetime.datetime.now().strftime('%H:%M:%S')
    with log.open('a',encoding='utf-8') as fh:
        fh.write(f'[{stamp}] {marker} {text}\n')

def run(cmd:list, log:Path, *, env_extra:dict|None=None, cwd:Path|None=None, timeout:int|None=None):
    """Execute one gate command; (rc, stdout, stderr) → a caller checks rc==0."""
    log_line(log,'RUN',' '.join(cmd))
    env={**os.environ,'PYTHONIOENCODING':'utf-8'}
    if env_extra:env.update(env_extra)
    started=time.time()
    try:
        proc=subprocess.run(cmd,cwd=str(cwd or ROOT),env=env,
                            capture_output=True,text=True,timeout=timeout)
        out,code,rc=proc.stdout,proc.stderr,proc.returncode
        rc=int(rc)
    except FileNotFoundError as e:
        log_line(log,'FAIL',f'executable not found: {e}')
        return 127,'',''
    except subprocess.TimeoutExpired as e:
        log_line(log,'FAIL',f'timeout after {timeout}s')
        return 124,(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else (e.stdout or ''),''
    dur=time.time()-started
    lines=((out or '')+'\n'+(code or '')).splitlines()
    key=' | '.join([l for l in lines if any(t in l for t in ('PASSED','BUILD_OK','TOTAL pages','CANVAS_MOTION','failed','passed'))][-3:])
    log_line(log,'DONE' if rc==0 else 'FAIL',f'exit={rc} dur={dur:.1f}s key={key[:400]}')
    with log.open('a',encoding='utf-8') as fh:
        if out:fh.write(out)
        if code:fh.write('\n--- stderr ---\n'+code)
    return rc,out,code

def acquire_lock():
    GATES_DIR.mkdir(parents=True,exist_ok=True)
    try:
        if LOCK.exists():
            pid=int(LOCK.read_text().strip() or '0')
            try:
                os.kill(pid,0)
                return False,pid
            except OSError:
                LOCK.unlink()  # stale lock
        LOCK.write_text(str(os.getpid()))
        return True,0
    except OSError as e:
        return False,-1

def release_lock():
    try:
        if LOCK.exists():
            pid=int(LOCK.read_text().strip() or '0')
            if pid==os.getpid():LOCK.unlink()
    except OSError:pass

def start_static_server(port:int):
    proc=subprocess.Popen([PY,str(ROOT/'tools'/'serve-gzip.py'),'--port',str(port)],
                          cwd=str(ROOT),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                          start_new_session=True)
    import urllib.request
    for _ in range(40):
        time.sleep(0.25)
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/index.html',timeout=2).read(64)
            return proc
        except Exception:continue
    proc.terminate()
    raise RuntimeError('static server did not become ready')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase',default='all',choices=['all']+PHASES)
    ap.add_argument('--skip-heavy',action='store_true',help='skip pytest/lhci/canvas')
    ap.add_argument('--port',type=int,default=8124)
    args=ap.parse_args()
    acquired,held=acquire_lock()
    if not acquired:
        print(f'RUN_GATES_LOCKED: another run holds {LOCK} (pid {held})')
        return 3
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    run_dir=GATES_DIR/stamp
    run_dir.mkdir(parents=True,exist_ok=True)
    log=run_dir/'gates.log'
    phases=PHASES if args.phase=='all' else [args.phase]
    if args.skip_heavy:phases=[p for p in phases if p not in ('pytest','lhci','canvas')]
    server:subprocess.Popen|None=None
    results={}
    try:
        for phase in phases:
            log_line(log,'PHASE',phase)
            if phase=='build':cmd=[PY,'build.py','all']
            elif phase=='bundles':cmd=[PY,'build.py','bundles','--check']
            elif phase=='smoke':cmd=['node','tools/page-errors.mjs','--all']
            elif phase=='pytest':cmd=[str(VENV_PY) if VENV_PY.exists() else PY,'-m','pytest','tests/','-q']
            elif phase=='lhci':cmd=['npx','lhci','assert','--config','tools/lighthouserc.js']
            elif phase=='canvas':cmd=[str(VENV_PY),'tests/canvas_motion_playwright.py','--phase','all','--output',str(GATES_DIR/stamp/'canvas-acceptance')]
            if phase in ('smoke',):
                server=start_static_server(args.port) if not server else server
                env_extra={'SMOKE_BASE_URL':f'http://127.0.0.1:{args.port}'}
            elif phase=='lhci':
                server=start_static_server(args.port) if not server else server
                env_extra=None
            elif phase=='canvas':
                # frozen harness starts its own app server; needs an absolute path env-side
                env_extra=None
            else:
                env_extra=None
            rc,out,err=run(cmd,log,env_extra=env_extra)
            results[phase]=rc
            if rc!=0:
                # lhci assert needs the reports lhci collect made — if assert fails hard
                # because collect never ran in this session, run collect once and retry
                # exactly one assert (bounded, not a blind retry).
                if phase=='lhci' and 'No lighthouse reports' in (out+err):
                    c_rc,_,_=run(['npx','lhci','collect','--config','tools/lighthouserc.js'],log)
                    if c_rc==0:
                        rc,out,err=run(cmd,log)
                if rc!=0:
                    log_line(log,'STOP',f'{phase} failed — stopping chain')
                    break
        # always stop our server
        if server is not None:
            try:os.killpg(server.pid,signal.SIGTERM)
            except Exception:
                try:server.terminate()
                except Exception:pass
            server=None
            log_line(log,'SERVER','stopped static server')
    finally:
        if server is not None:
            try:os.killpg(server.pid,signal.SIGTERM)
            except Exception:
                try:server.terminate()
                except Exception:pass
        release_lock()
    # summary + skipped markers
    order=[p for p in phases]
    failed_first=next((p for p in order if results.get(p) not in (0,None)),None)
    summary={'timestamp':stamp,'results':results,'stoppedAt':failed_first}
    (run_dir/'summary.json').write_text(json.dumps(summary,indent=1),encoding='utf-8')
    for p in order:
        if p in results and results[p]==0:print(f'  PASS {p}')
        elif p in results:print(f'  FAIL {p} (exit {results[p]})')
        else:print(f'  SKIPPED {p}')
    ok=all(results.get(p)==0 for p in order) and not failed_first
    print('GATES_PASSED' if ok else 'GATES_FAILED',f'log={log}')
    return 0 if ok else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:release_lock();raise
