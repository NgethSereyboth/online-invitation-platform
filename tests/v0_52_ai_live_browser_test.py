#!/usr/bin/env python3
from __future__ import annotations
from browser_runtime import dismiss_editor_onboarding,launch_chromium
from v14_test_utils import app_server
from playwright.sync_api import sync_playwright

def main()->int:
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION':'0','EINVITE_AI_PROVIDER':'offline','EINVITE_AI_ENDPOINT':'','EINVITE_AI_API_KEY':'','EINVITE_AI_ENABLED':'1'}) as (_proc,base,_data):
        with sync_playwright() as p:
            browser=launch_chromium(p)
            page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(18000)
            errors=[];failed=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            page.on('requestfailed',lambda r:failed.append((r.method,r.url,r.failure)))
            page.goto(base+'/dashboard.html',wait_until='networkidle')
            page.locator('#authRegisterTab').click();page.locator('#email').fill('ai-browser@example.com');page.locator('#password').fill('strong-password-123');page.locator('#registerConfirmPassword').fill('strong-password-123');page.locator('#loginBtn').click();page.wait_for_selector('#dashboardView:not([hidden])')
            page.get_by_role('button',name='Create your first invitation',exact=True).click();page.wait_for_selector('#createDialog[open]');page.locator('#newTitle').fill('AI Live Browser');page.locator('#confirmCreate').click();page.wait_for_url(lambda u:'/invitations/' in u and u.endswith('/editor'),timeout=15000)
            dismiss_editor_onboarding(page,timeout=20000)
            invite_id=page.url.split('/invitations/',1)[1].split('/',1)[0]
            source=page.evaluate("""async ({inviteId})=>{const csrf=decodeURIComponent((document.cookie.match(/(?:^|;\\s*)einvite_csrf=([^;]+)/)||[])[1]||'');const response=await fetch('/api/ai-agent/knowledge',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({title:'Ceremony guidance',content:'Use formal Khmer honorifics for the blessing ceremony and keep the RSVP optional.',scope:'invitation',invitationId:inviteId,sourceType:'policy'})});return {status:response.status,body:await response.json()}}""",{'inviteId':invite_id})
            assert source['status']==201,source
            page.locator('#eiAiTopButton').click();panel=page.locator('#eiAgentPanel');panel.wait_for(state='visible')
            page.wait_for_function("()=>document.querySelector('#eiAgentPanel [data-agent-action=send]')?.disabled===false",timeout=15000)
            assert 'offline' in panel.inner_text().lower(),panel.inner_text()
            page.locator('[data-agent-input]').fill('Please check this invitation and suggest a harmless improvement.')
            page.locator('[data-agent-action=send]').click()
            page.wait_for_function("()=>{const p=document.querySelector('#eiAgentPanel');return /Template helper|cannot generate|completed/i.test(p?.innerText||'')}",timeout=20000)
            panel.locator('[data-message-feedback="1"]').last.click()
            page.wait_for_timeout(150)
            page.locator('[data-agent-action=settings]').click()
            settings=page.locator('[data-agent-settings]')
            assert settings.is_visible()
            assert 'Ceremony guidance' in settings.inner_text(),settings.inner_text()
            assert settings.locator('[data-setting=knowledgeEnabled]').is_checked()
            assert not [x for x in failed if '/ai/' in x[1]],failed
            serious=[e for e in errors if 'favicon' not in e.lower() and 'failed to load resource' not in e.lower()]
            assert not serious,serious
            page.locator('[data-agent-action=hide-settings]').click()
            page.get_by_role('button',name='Close AI Project Operator',exact=True).click();page.wait_for_function("()=>document.querySelector('#eiAgentPanel')?.dataset.open==='false'")
            browser.close()
    print('V0_52_AI_LIVE_BROWSER_TEST_PASSED')
    return 0

if __name__=='__main__': raise SystemExit(main())
