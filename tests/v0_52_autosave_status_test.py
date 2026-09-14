#!/usr/bin/env python3
from __future__ import annotations
import json,sqlite3,time
from contextlib import closing
from browser_runtime import dismiss_editor_onboarding,launch_chromium,open_event_details
from v14_test_utils import app_server
from playwright.sync_api import sync_playwright

def read_doc(data,invite_id):
    with closing(sqlite3.connect(data/'invites.db')) as db:
        row=db.execute('SELECT draft_json,updated_at FROM invitations WHERE id=?',(invite_id,)).fetchone()
    assert row
    return json.loads(row[0]),int(row[1] or 0)

def main()->int:
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION':'0'}) as (_proc,base,data):
        with sync_playwright() as p:
            browser=launch_chromium(p)
            page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(18000)
            failed=[];responses=[]
            page.on('requestfailed',lambda r:failed.append((r.method,r.url,r.failure)))
            page.on('response',lambda r:responses.append((r.request.method,r.url,r.status)) if '/api/invitations/' in r.url else None)
            page.goto(base+'/dashboard.html',wait_until='networkidle')
            page.locator('#authRegisterTab').click();page.locator('#email').fill('autosave-status@example.com');page.locator('#password').fill('strong-password-123');page.locator('#registerConfirmPassword').fill('strong-password-123');page.locator('#loginBtn').click();page.wait_for_selector('#dashboardView:not([hidden])')
            page.get_by_role('button',name='Create your first invitation',exact=True).click();page.wait_for_selector('#createDialog[open]');page.locator('#newTitle').fill('Autosave Status Regression');page.locator('#confirmCreate').click();page.wait_for_url(lambda u:'/invitations/' in u and u.endswith('/editor'),timeout=15000)
            invite_id=page.url.split('/invitations/',1)[1].split('/',1)[0]
            dismiss_editor_onboarding(page,timeout=20000)
            assert page.locator('#serverState').inner_text()=='Server connected'
            initial,_=read_doc(data,invite_id);initial_rsvp=initial.get('settings',{}).get('rsvpEnabled') is not False
            new_rsvp=not initial_rsvp
            rsvp,venue=open_event_details(page,timeout=12000)
            if new_rsvp:rsvp.check()
            else:rsvp.uncheck()
            venue.fill('Autosave Verified Venue')
            # Both edits happen inside the normal debounce/idle window.
            page.wait_for_function("()=>document.querySelector('#saveState')?.textContent==='Saved'",timeout=5000)
            deadline=time.time()+12
            latest=None
            while time.time()<deadline:
                latest,_=read_doc(data,invite_id)
                if latest.get('settings',{}).get('rsvpEnabled') is new_rsvp and latest.get('fields',{}).get('venue')=='Autosave Verified Venue':break
                time.sleep(.15)
            assert latest and latest.get('settings',{}).get('rsvpEnabled') is new_rsvp,latest
            assert latest.get('fields',{}).get('venue')=='Autosave Verified Venue',latest
            page.wait_for_function("()=>document.querySelector('#serverState')?.textContent==='Server connected'",timeout=5000)
            assert page.evaluate("document.documentElement.dataset.serverSaveErrorCode||''")==''
            assert not [x for x in failed if '/api/invitations/' in x[1]],failed
            bad=[x for x in responses if x[0]=='PUT' and x[2]>=400]
            assert not bad,bad
            # The editor intentionally keeps an SSE connection open. Network-idle
            # is therefore not an authoritative reload boundary.
            page.reload(wait_until='domcontentloaded');dismiss_editor_onboarding(page,timeout=20000);page.wait_for_selector('#stage .object',state='attached',timeout=20000)
            assert page.locator('#serverState').inner_text()=='Server connected'
            rsvp,venue=open_event_details(page,timeout=12000)
            assert rsvp.is_checked() is new_rsvp
            assert venue.input_value()=='Autosave Verified Venue'
            browser.close()
    print('V0_52_AUTOSAVE_STATUS_TEST_PASSED')
    return 0

if __name__=='__main__': raise SystemExit(main())
