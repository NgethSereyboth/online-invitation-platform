#!/usr/bin/env python3
"""Browser-level smoke test for the main creation and management flows."""
import os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

ROOT=Path(__file__).resolve().parents[1]
PORT=8097
BASE=f"http://127.0.0.1:{PORT}"

def wait_server():
    for _ in range(80):
        try:
            with urllib.request.urlopen(BASE+'/api/health',timeout=.5) as r:
                if r.status==200:return
        except Exception:time.sleep(.1)
    raise RuntimeError('Server did not start')

def main():
    data=tempfile.TemporaryDirectory(prefix='einvite-ui-test-')
    env=os.environ.copy();env.update({'EINVITE_DATA_DIR':data.name,'EINVITE_ADMIN_EMAIL':'ui-test@example.com','EINVITE_DEV_AUTH_TOKENS':'1'})
    proc=subprocess.Popen([sys.executable,'-u','server.py','--port',str(PORT)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    try:
        wait_server()
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
            errors=[]
            page.on('console',lambda msg: errors.append(msg.text) if msg.type=='error' else None)
            page.on('pageerror',lambda err: errors.append(str(err)))
            try:
                page.goto(BASE+'/dashboard.html',wait_until='networkidle')
            except PlaywrightError as exc:
                if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(exc):
                    print('UI_SMOKE_SKIPPED_ENVIRONMENT_BLOCK')
                    browser.close();return
                raise
            assert page.locator('#loginView').is_visible()
            page.locator('#authRegisterTab').click()
            page.locator('#email').fill('ui-test@example.com')
            page.locator('#password').fill('strong-pass-123')
            page.locator('#registerConfirmPassword').fill('strong-pass-123')
            page.locator('#loginBtn').click()
            page.wait_for_selector('#dashboardView:not([hidden])',timeout=7000)
            page.locator('#newBtn').click();page.wait_for_selector('#createDialog[open]')
            page.locator('#newTitle').fill('Browser Review Invitation')
            page.locator('#confirmCreate').click()
            page.wait_for_url('**/index.html',timeout=9000);page.wait_for_load_state('networkidle')
            page.wait_for_selector('#stage .object',timeout=7000)
            # New professional systems are present.
            assert page.locator('.ei-tool-rail').count() or page.locator('.pro-tool-rail').count() or page.locator('[data-ei-tool]').count()
            assert page.locator('.ei-schedule-builder').count() or page.locator('[data-schedule-builder]').count()
            assert page.locator('#canvasPlusAiTools').count() or page.locator('.ei-ai-studio').count()
            # Dark mode should remain readable.
            page.evaluate("localStorage.setItem('einvite-theme-mode','dark')")
            page.reload(wait_until='networkidle');page.wait_for_selector('#stage')
            bg=page.evaluate("getComputedStyle(document.body).backgroundColor")
            assert bg
            # Text tool creates an object by canvas click.
            page.keyboard.press('t');page.locator('#stage').click(position={'x':180,'y':180})
            page.wait_for_timeout(400)
            assert page.locator('#stage .object').count()>=4
            # Alt-drag path can be exercised without crashing.
            first=page.locator('#stage .object').first
            box=first.bounding_box()
            if box:
                page.keyboard.down('Alt');page.mouse.move(box['x']+20,box['y']+20);page.mouse.down();page.mouse.move(box['x']+70,box['y']+60,steps=4);page.mouse.up();page.keyboard.up('Alt')
            # No horizontal page overflow on management pages.
            for path in ['dashboard.html','materials.html','billing.html','account.html']:
                page.goto(BASE+'/'+path,wait_until='networkidle')
                overflow=page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
                assert overflow<=4,(path,overflow)
            serious=[e for e in errors if 'favicon' not in e.lower() and 'failed to load resource' not in e.lower()]
            assert not serious, serious
            browser.close()
        print('UI_SMOKE_TEST_PASSED')
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill()
        data.cleanup()
if __name__=='__main__':main()
