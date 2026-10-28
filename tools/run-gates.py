#!/usr/bin/env python3
"""tools/run-gates.py — one-command gate runner for the eInvite repo (Linux portable).

Phases (default --phase all): build → bundles → smoke → layout → pytest → budgets → lhci → csp → canvas → important.
  build   `python3 build.py all`            (BUILD_OK + MIRROR_CHECK_PASSED)
  bundles `python3 build.py bundles --check` (ROUTE_BUNDLE_CHECK_PASSED)
  smoke   `tools/serve-gzip.py --port <port>` + `node tools/page-errors.mjs --all`
  layout  `tools/ui-layout-guard.py --base <app-server>` (FB-31: horizontal scroll /
          nameless controls / header overlap+height / auth-padding / editor contract,
          across 320/375/768/1024/1440 × light/dark × en/km). The runner starts its
          own fresh-data app server for this phase (dev tokens, throwaway account).
  pytest  `PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/ -q`  (default capture)
  budgets v55 route-weight budget gate (BLOCKING — FB-08). v14 is NOT a phase:
          it is known red against an aspirational stylesheet count and stays
          non-blocking per the 2026-10-22 owner answer (OD-6 / FB-11); CI's
          tests.yml runs it quarantined with continue-on-error.
  lhci    `npx --yes @lhci/cli@0.15.1 autorun --config=tools/lighthouserc.js`
          (fresh collect of all 16 routes + budgets assert; the config starts its
          own gzip server, so this phase stops the runner's server first.)
          Prints the minimum accessibility score across the 16 reports.
  csp     `tools/csp-violation-check.py` (FB-24/FB-31: creates an invitation, opens
          the editor, publishes, RSVPs; the tool starts + stops its own fresh-data
          app server unless --base is given).
  canvas  `.venv/bin/python tests/canvas_motion_playwright.py --phase all --output <abs>`
          (visual gate: NOT RUN here — frozen baseline lives on the Windows box)
  important FB-32 `!important` ratchet: `tools/css-important-inventory.py` count must
          stay ≤ IMPORTANT_PIN (ratchet lowers as cleanups land; no threshold judgement
          here, pure inventory). Cheap, so it runs in both the full and --skip-heavy set.

Behaviour
  - Starts/stops its own servers (gzip static server for smoke; process cleanly
    reaped in finally). The lhci phase runs `autorun`, whose config owns the server.
  - **Fail-closed markers (FB-23):** every phase declares the signature line(s) that
    prove it actually ran. Exit 0 without its marker is a FAIL — the unscoped
    squatted placeholder package printing a greeting and exiting 0, which made two
    "all phases green" runs false greens. The canvas phase runs the frozen harness that manages its own
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
import argparse,datetime,json,os,re,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GATES_DIR=ROOT/'artifacts'/'next-work'/'gates'
LOCK=GATES_DIR/'.run-gates.lock'
PHASES=['build','bundles','smoke','layout','pytest','budgets','lhci','csp','canvas','important']
PY=sys.executable
VENV_PY=ROOT/'.venv'/'bin'/'python'
# One pin, in one place. The unscoped `lhci` package resolves to an unrelated squatted
# prints a greeting and exits 0 — see artifacts/next-work/fb-23/NOTES.md.
LHCI_CLI=['npx','--yes','@lhci/cli@0.15.1']
LHCI_REPORTS=ROOT/'.lighthouseci'/'reports'
LHCI_PAGES=16
# FB-32 ratchet pin: inventory total must not exceed this. 3819 at FB-19 close
# (artifacts/next-work/fb-19/inventory-after2); +4 documented exceptions landed with
# evidenced fixes after that pin (FB-28 editor-styles ×2, FB-30 km display-face
# editor-suite ×1 / canvas-plus ×1) → 3823. LOWER this number as cleanups land:
# LT-6.3 pass 1 (2026-10-27) removed 7 provably-dead tokens (3816 → 3809:
# .fp-project-status 1 — LT-1.4 leftover; .flow-design-search input 6 — stale
# v15-only surface) and lowered the pin to the new count. The phase fails as
# soon as the count climbs above it.
IMPORTANT_PIN=3809
# Signature each phase must print before its exit code counts (rule R2).
MARKERS={
    'build':   ('BUILD_OK','MIRROR_CHECK_PASSED'),
    'bundles': ('ROUTE_BUNDLE_CHECK_PASSED',),
    'smoke':   ('TOTAL pages=16','consoleErrors=0','non2xx=0'),
    'layout':  ('UI_LAYOUT_GUARD_PASSED',),
    'csp':     ('CSP_CHECK_PASSED',),
    'pytest':  (' passed',),
    'budgets': ('V55_ROUTE_WEIGHT_BUDGET_TEST_PASSED',),
    'lhci':    ('Done running Lighthouse',),
    'canvas':  ('CANVAS_MOTION_VERIFY_PASSED',),
    'important': ('CSS_IMPORTANT_INVENTORY total=',),
}

def log_line(log,marker,text=''):
    stamp=datetime.datetime.now().strftime('%H:%M:%S')
    with log.open('a',encoding='utf-8') as fh:
        fh.write(f'[{stamp}] {marker} {text}\n')

def has_markers(text:str, markers):
    missing=[m for m in markers if m not in text]
    return (not missing),missing


def run(cmd:list, log:Path, *, env_extra:dict|None=None, cwd:Path|None=None, timeout:int|None=None,
        required=()):
    """Execute one gate command; (rc, stdout, stderr).

    ``required`` markers must all appear in stdout+stderr. Exit 0 without them is a
    failure, not a pass: v55-style gates print a signature only when they really ran.
    """
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
    combined=(out or '')+'\n'+(code or '')
    markers_ok,missing=has_markers(combined,required)
    if not markers_ok and rc==0:
        log_line(log,'MARKER','missing '+', '.join(repr(m) for m in missing)+' — exit 0 is not a pass')
        rc=1
    lines=combined.splitlines()
    key=' | '.join([l for l in lines if any(t in l for t in ('PASSED','BUILD_OK','TOTAL pages','CANVAS_MOTION','failed','passed'))][-3:])
    log_line(log,'DONE' if rc==0 else 'FAIL',f'exit={rc} dur={dur:.1f}s key={key[:400]}')
    with log.open('a',encoding='utf-8') as fh:
        if out:fh.write(out)
        if code:fh.write('\n--- stderr ---\n'+code)
    return rc,out,code


def stop_static_server(server, log:Path):
    """Stop the runner-owned static server; (None) so the caller's handle is cleared."""
    if server is None:
        return None
    try:os.killpg(server.pid,signal.SIGTERM)
    except Exception:
        try:server.terminate()
        except Exception:pass
    log_line(log,'SERVER','stopped static server')
    return None


def lhci_report_summary(started:float, log:Path):
    """(count, min_a11y) for LHR reports written by this phase; logs the 16 pages."""
    # `*.report.json` is one LHR object per route; the upload dir also holds other
    # JSON (lists/manifests), which carry no categories and are not reports.
    files=[p for p in LHCI_REPORTS.glob('*.report.json') if p.stat().st_mtime>=started-1]
    scores=[]
    for path in sorted(files):
        try:data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        if not isinstance(data,dict):continue
        url=str(data.get('finalUrl') or data.get('requestedUrl') or path.name)
        score=(data.get('categories') or {}).get('accessibility') or {}
        value=score.get('score')
        log_line(log,'LHR',f"{url} a11y={'n/a' if value is None else f'{value:.2f}'}")
        if isinstance(value,(int,float)):scores.append(value)
    return len(files),(min(scores) if scores else None)

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

def free_port(start:int):
    import socket
    for port in range(start,start+40):
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',port))
            except OSError:continue
            return port
    raise RuntimeError('no free port')

def start_app_server(port:int, log:Path):
    """Fresh-data app server for browser phases that need real routes (layout guard).

    Mirrors the launcher in tools/csp-violation-check.py: dev tokens, no scanner,
    own temp EINVITE_DATA_DIR, session-leader process group so stop_static_server's
    killpg reaches it.
    """
    import tempfile, urllib.request
    data_dir=tempfile.mkdtemp(prefix='einvite-gates-app-')
    env={**os.environ,'PYTHONIOENCODING':'utf-8',
         'EINVITE_DATA_DIR':data_dir,'EINVITE_DEV_AUTH_TOKENS':'1',
         'EINVITE_ALLOW_NO_SCANNER':'1',
         'PYTHONPATH':f"{ROOT/'src'/'python'}:{ROOT}"}
    py=str(VENV_PY) if VENV_PY.exists() else PY
    proc=subprocess.Popen([py,str(ROOT/'src'/'python'/'server.py'),'--port',str(port)],
                          cwd=str(ROOT),env=env,stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,start_new_session=True)
    for _ in range(120):
        time.sleep(0.25)
        if proc.poll() is not None:
            log_line(log,'FAIL',f'app server exited during startup (code {proc.returncode})')
            raise RuntimeError(f'app server exited during startup (code {proc.returncode})')
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/dashboard.html',timeout=2).read(64)
            log_line(log,'SERVER',f'app server ready on :{port} (data_dir={data_dir})')
            return proc
        except Exception:continue
    proc.terminate()
    raise RuntimeError('app server did not become ready')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase',default='all',choices=['all']+PHASES)
    ap.add_argument('--skip-heavy',action='store_true',help='skip layout/csp/pytest/budgets/lhci/canvas')
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
    layout_port=0
    if args.skip_heavy:phases=[p for p in phases if p not in ('layout','csp','pytest','budgets','lhci','canvas')]
    server:subprocess.Popen|None=None
    app_server:subprocess.Popen|None=None
    results={}
    try:
        for phase in phases:
            log_line(log,'PHASE',phase)
            if phase=='build':cmd=[PY,'build.py','all']
            elif phase=='bundles':cmd=[PY,'build.py','bundles','--check']
            elif phase=='smoke':cmd=['node','tools/page-errors.mjs','--all']
            elif phase=='pytest':cmd=[str(VENV_PY) if VENV_PY.exists() else PY,'-m','pytest','tests/','-q']
            elif phase=='budgets':cmd=[str(VENV_PY) if VENV_PY.exists() else PY,'tests/v55_route_weight_budget_test.py']
            elif phase=='lhci':cmd=[*LHCI_CLI,'autorun','--config','tools/lighthouserc.js']
            elif phase=='canvas':cmd=[str(VENV_PY),'tests/canvas_motion_playwright.py','--phase','all','--output',str(GATES_DIR/stamp/'canvas-acceptance')]
            elif phase=='layout':
                # Own fresh-data app server on a port away from the static server,
                # the lhci port and the csp tool's free-port scan start (4177).
                if app_server is None:
                    layout_port=free_port(args.port+20)
                    app_server=start_app_server(layout_port,log)
                cmd=[str(VENV_PY) if VENV_PY.exists() else PY,'tools/ui-layout-guard.py','--base',f'http://127.0.0.1:{layout_port}','--out',str(GATES_DIR/stamp/'ui-layout-guard')]
            elif phase=='csp':cmd=[str(VENV_PY) if VENV_PY.exists() else PY,'tools/csp-violation-check.py']  # own fresh-data server
            elif phase=='important':cmd=[str(VENV_PY) if VENV_PY.exists() else PY,'tools/css-important-inventory.py','--out',str(GATES_DIR/stamp/'important-inventory')]
            if phase=='smoke':
                server=start_static_server(args.port) if not server else server
                env_extra={'SMOKE_BASE_URL':f'http://127.0.0.1:{args.port}'}
            elif phase=='lhci':
                # The config's startServerCommand owns the port; two servers cannot bind it
                # and the numbers would silently measure whichever won (FB-15 hit this).
                server=stop_static_server(server,log)
                env_extra=None
            else:
                # canvas: the frozen harness starts its own app server.
                env_extra=None
            phase_started=time.time()
            rc,out,err=run(cmd,log,env_extra=env_extra,required=MARKERS.get(phase,()))
            if phase=='lhci':
                count,min_a11y=lhci_report_summary(phase_started,log)
                log_line(log,'LHR',f'reports={count}/{LHCI_PAGES} minA11y={"n/a" if min_a11y is None else f"{min_a11y:.2f}"}')
                print(f'  lhci reports={count}/{LHCI_PAGES} minA11y={"n/a" if min_a11y is None else f"{min_a11y:.2f}"}')
                if count<LHCI_PAGES:
                    log_line(log,'MARKER',f'only {count} fresh LHR reports — expected {LHCI_PAGES}')
                    rc=1
            results[phase]=rc
            if phase=='important':
                # Ratchet: the inventory tool always exits 0 (read-only recon),
                # so the count comparison happens here.
                m=re.search(r'total=(\d+)',out)
                total=int(m.group(1)) if m else -1
                if total<0:
                    log_line(log,'MARKER','no total= line in inventory output — cannot verify')
                    rc=1
                elif total>IMPORTANT_PIN:
                    log_line(log,'FAIL',f'important ratchet exceeded: {total} > pin {IMPORTANT_PIN}')
                    print(f'  !! important ratchet: {total} > pin {IMPORTANT_PIN}')
                    rc=1
                else:
                    log_line(log,'OK',f'important ratchet holds: {total} ≤ pin {IMPORTANT_PIN}')
                results[phase]=rc
            if phase=='layout':
                app_server=stop_static_server(app_server,log)
            if rc!=0:
                log_line(log,'STOP',f'{phase} failed — stopping chain')
                break
        # always stop our servers
        app_server=stop_static_server(app_server,log)
        server=stop_static_server(server,log)
    finally:
        stop_static_server(app_server,log)
        stop_static_server(server,log)
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
