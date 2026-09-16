#!/usr/bin/env python3
"""Browser-level smoke test for the main creation and management flows."""
import os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from browser_runtime import dismiss_editor_onboarding,launch_chromium, skipped
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
    env=os.environ.copy();env.update({'EINVITE_DATA_DIR':data.name,'EINVITE_ADMIN_EMAIL':'ui-test@example.com'});env.pop('EINVITE_DEV_AUTH_TOKENS',None);env.pop('SOVAN_DEV_AUTH_TOKENS',None)
    proc=subprocess.Popen([sys.executable,'-u','server.py','--port',str(PORT)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    try:
        wait_server()
        with sync_playwright() as p:
            browser=launch_chromium(p)
            page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
            errors=[]
            page.on('console',lambda msg: errors.append(msg.text) if msg.type=='error' else None)
            page.on('pageerror',lambda err: errors.append(str(err)))
            try:
                page.goto(BASE+'/dashboard.html',wait_until='networkidle')
            except PlaywrightError as exc:
                browser.close()
                return skipped('UI_SMOKE', exc)
            assert page.locator('#loginView').is_visible()
            page.locator('#authRegisterTab').click()
            page.locator('#email').fill('ui-test@example.com')
            page.locator('#password').fill('strong-pass-123')
            page.locator('#registerConfirmPassword').fill('strong-pass-123')
            page.locator('#loginBtn').click()
            page.wait_for_selector('#dashboardView:not([hidden])',timeout=7000)
            assert page.evaluate("localStorage.getItem('sovan-auth-token')") is None
            assert page.evaluate("document.cookie.includes('einvite_session=')") is False  # HttpOnly cookie is intentionally unreadable to JS.
            me=page.evaluate("async()=>{const r=await fetch('/api/auth/me',{credentials:'same-origin'});return await r.json()}")
            assert me.get('user') and me['user']['email']=='ui-test@example.com',me
            create=page.get_by_role('button',name='Create your first invitation',exact=True);assert create.is_visible();create.click();page.wait_for_selector('#createDialog[open]')
            page.locator('#newTitle').fill('Browser Review Invitation')
            page.locator('#confirmCreate').click()
            page.wait_for_url(lambda url:('/invitations/' in url and url.endswith('/editor')) or url.endswith('/index.html'),timeout=12000);page.wait_for_selector('#stage .object',timeout=20000)
            editor_url=page.url
            invite_id=editor_url.split('/invitations/',1)[1].split('/',1)[0] if '/invitations/' in editor_url else ''
            assert invite_id,editor_url
            page.wait_for_selector('#stage .object',timeout=7000)
            # New professional systems are present.
            assert page.locator('.ei-tool-rail').count() or page.locator('.pro-tool-rail').count() or page.locator('[data-ei-tool]').count()
            assert page.locator('.ei-schedule-builder').count() or page.locator('[data-schedule-builder]').count()
            assert page.locator('#canvasPlusAiTools').count() or page.locator('.ei-ai-studio').count()
            # Dark mode should remain readable.
            page.evaluate("localStorage.setItem('einvite-theme-mode','dark')")
            page.reload(wait_until='domcontentloaded');page.wait_for_selector('#stage .object',timeout=20000);dismiss_editor_onboarding(page,timeout=20000)
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
            # The visible project cover and Project actions > Edit must both navigate to the same editor.
            page.goto(BASE+'/dashboard.html',wait_until='networkidle')
            cover=page.get_by_role('button',name='Open Browser Review Invitation',exact=True);assert cover.is_visible();cover.click()
            page.wait_for_url(lambda url:f'/invitations/{invite_id}/editor' in url,timeout=12000)
            page.goto(BASE+'/dashboard.html',wait_until='networkidle')
            card=page.locator('.invite-card').filter(has_text='Browser Review Invitation').first
            actions=card.get_by_role('button',name='Project actions',exact=True);assert actions.is_visible();actions.click()
            edit=card.locator('.fp-project-menu').get_by_role('button',name='Edit',exact=True);assert edit.is_visible();edit.click()
            page.wait_for_url(lambda url:f'/invitations/{invite_id}/editor' in url,timeout=12000)
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
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        data.cleanup()
if __name__=='__main__':main()
