#!/usr/bin/env python3
"""Static-server regression: no backend routes, polling loops, or raw failures."""
from __future__ import annotations
import os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from v14_test_utils import ROOT,free_port,process_options,stop_process

def main():
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V14_STATIC_SERVER',exc)
    port=free_port();base=f'http://127.0.0.1:{port}'
    process=subprocess.Popen([sys.executable,'-u','-m','http.server',str(port),'--bind','127.0.0.1'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**process_options())
    try:
        time.sleep(.35)
        with sync_playwright() as playwright:
            try:browser=launch_chromium(playwright)
            except Exception as exc:return skipped('V14_STATIC_SERVER',exc)
            context=browser.new_context(viewport={'width':1280,'height':800})
            page=context.new_page();errors=[];api_requests=[]
            page.on('pageerror',lambda error:errors.append(f'pageerror: {error}'))
            page.on('console',lambda message:errors.append(f'console: {message.text}') if message.type=='error' and 'favicon' not in message.text.lower() else None)
            page.on('request',lambda request:api_requests.append(request.url) if '/api/' in request.url else None)
            # The Windows launcher opens "/", so the root route must retain the
            # editor's index identity instead of being restyled as a dashboard.
            page.goto(base+'/',wait_until='networkidle',timeout=30000)
            assert page.evaluate("document.body.dataset.page")=='index'
            assert page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth")
            page.goto(base+'/dashboard.html',wait_until='networkidle',timeout=30000)
            assert page.evaluate("document.documentElement.dataset.backendMode")=='offline'
            page.locator('#authRegisterTab').click();page.locator('#email').fill('static@example.com');page.locator('#password').fill('static-pass-123');page.locator('#registerConfirmPassword').fill('static-pass-123');page.locator('#loginBtn').click()
            page.wait_for_selector('#dashboardView:not([hidden])')
            assert page.get_by_text('Static preview mode',exact=True).count()==1
            create=page.locator('.dashboard-home-hero .create')
            if not create.count() or not create.is_visible():create=page.locator('#emptyCreate')
            if not create.count() or not create.is_visible():create=page.locator('.rail-create')
            create.click();page.wait_for_selector('#createDialog[open]')
            page.locator('#newTitle').fill('Static Invitation')
            page.locator('#confirmCreate').click()
            page.wait_for_url('**/index.html?invitation=*',timeout=12000);page.wait_for_load_state('domcontentloaded')
            page.wait_for_function("()=>document.documentElement.dataset.backendMode==='offline'&&!!document.querySelector('#stage')",timeout=30000)
            assert page.evaluate("document.documentElement.dataset.backendMode")=='offline'
            assert 'index.html?invitation=' in page.url
            assert page.get_by_text('Static preview mode',exact=False).count()>=1
            page.wait_for_timeout(2600)
            # No collaboration or backend polling may begin in static mode.
            assert not api_requests,api_requests
            page.goto(base+'/account.html',wait_until='networkidle')
            assert page.url.endswith('/account.html')
            assert page.get_by_text('Full server required',exact=True).count()>=1
            for filename,needle in [('materials.html','Full server required'),('checkin.html','Full server required')]:
                page.goto(base+'/'+filename,wait_until='networkidle');assert page.get_by_text(needle,exact=True).count()>=1
            page.goto(base+'/templates.html',wait_until='networkidle')
            assert page.locator('.studio-card,.template-card,[data-template-id]').count()>0
            assert page.get_by_text('No templates found',exact=True).count()==0
            # Separate interactive controls: no button nested in a button/link.
            assert page.locator('button button,a button,button a').count()==0
            page.wait_for_timeout(2200)
            assert not api_requests,api_requests
            serious=[item for item in errors if 'failed to load resource' not in item.lower()]
            assert not serious,serious
            context.close();browser.close()
        print('V14_STATIC_SERVER_TEST_PASSED');return 0
    finally:stop_process(process)

if __name__=='__main__':raise SystemExit(main())
