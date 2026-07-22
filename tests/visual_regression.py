#!/usr/bin/env python3
"""Optional Playwright visual-regression runner.

Usage:
  python tests/visual_regression.py --update
  python tests/visual_regression.py

The runner seeds an authenticated account and invitation, then captures key application
screens in both light and dark modes. Some restricted sandboxes block browser loopback
navigation; that condition is reported explicitly instead of being counted as a pass.
"""
from __future__ import annotations
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
from playwright.sync_api import sync_playwright,Error as PlaywrightError
ROOT=Path(__file__).resolve().parents[1];BASELINES=ROOT/'tests'/'visual-baselines';CURRENT=ROOT/'tests'/'visual-current';PORT=8098;BASE=f'http://127.0.0.1:{PORT}'
PAGES=['dashboard.html','materials.html','billing.html','account.html','index.html']
VIEWPORTS=[('mobile',375,812),('mobile-large',430,932),('tablet',768,1024),('laptop-small',1024,768),('laptop',1366,768),('desktop',1920,1080),('desktop-large',2560,1440)]

def wait():
    for _ in range(80):
        try:
            if urllib.request.urlopen(BASE+'/api/health',timeout=.5).status==200:return
        except Exception:time.sleep(.1)
    raise RuntimeError('server unavailable')
def diff_ratio(a,b):
    ia=Image.open(a).convert('RGB');ib=Image.open(b).convert('RGB')
    if ia.size!=ib.size:return 1.0
    d=ImageChops.difference(ia,ib);stat=ImageStat.Stat(d);return sum(stat.mean)/(255*3)
def run(update=False):
    BASELINES.mkdir(parents=True,exist_ok=True);CURRENT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='einvite-visual-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data};proc=subprocess.Popen([sys.executable,'-u','server.py','--port',str(PORT)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait()
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
                context=browser.new_context(viewport={'width':1366,'height':768},device_scale_factor=1)
                page=context.new_page()
                try:
                    response=page.request.post(BASE+'/api/auth/register',data={'email':'visual@example.com','password':'password123'})
                    account=response.json();token=account.get('token','')
                    invite=page.request.post(BASE+'/api/invitations',headers={'Authorization':'Bearer '+token},data={'slug':'visual-review','document':{'eventType':'Wedding','fields':{'names':'Visual Review','date':'2026-12-27','venue':'Grand Ballroom','message':'Join us for a beautiful celebration.'},'objects':{},'designPages':[],'sectionOrder':['schedule','venue','rsvp'],'settings':{'rsvpEnabled':True}}}).json()
                    active_id=invite.get('id','')
                except Exception:
                    active_id=''
                page.add_init_script(f"localStorage.setItem('sovan-auth-token','cookie-session');const active={json.dumps(active_id)};if(active)localStorage.setItem('sovan-active-invite',active)")
                for viewport_name,width,height in VIEWPORTS:
                    page.set_viewport_size({'width':width,'height':height})
                    for mode in ['light','dark']:
                        for name in PAGES:
                            try:
                                page.goto(BASE+'/'+name,wait_until='networkidle',timeout=15000)
                            except PlaywrightError as exc:
                                if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(exc):
                                    print('VISUAL_REGRESSION_SKIPPED_ENVIRONMENT_BLOCK');context.close();browser.close();return
                                raise RuntimeError(f'Browser could not navigate to the local test server: {exc}')
                            page.evaluate("mode=>{localStorage.setItem('einvite-theme-mode',mode);document.documentElement.dataset.theme=mode;document.documentElement.dataset.themeMode=mode}",mode)
                            page.reload(wait_until='networkidle')
                            out=CURRENT/f'{Path(name).stem}-{mode}-{viewport_name}.png';page.screenshot(path=str(out),full_page=True)
                            baseline=BASELINES/out.name
                            if update:baseline.write_bytes(out.read_bytes())
                            elif baseline.exists():
                                ratio=diff_ratio(baseline,out)
                                if ratio>.035:raise AssertionError(f'{out.name} visual difference {ratio:.2%} exceeds 3.5%')
                context.close();browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill()
    print('VISUAL_REGRESSION_BASELINES_UPDATED' if update else 'VISUAL_REGRESSION_PASSED')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--update',action='store_true');run(ap.parse_args().update)
