#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import dismiss_editor_onboarding,launch_chromium
from v14_test_utils import app_server
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def register_and_create(page,base,title):
    page.goto(base+'/dashboard.html',wait_until='networkidle')
    page.locator('#authRegisterTab').click()
    page.locator('#email').fill('cover-nav@example.com')
    page.locator('#password').fill('strong-password-123')
    page.locator('#registerConfirmPassword').fill('strong-password-123')
    page.locator('#loginBtn').click()
    page.wait_for_selector('#dashboardView:not([hidden])',timeout=10000)
    create=page.get_by_role('button',name='Create your first invitation',exact=True)
    assert create.is_visible();create.click();page.wait_for_selector('#createDialog[open]')
    page.locator('#newTitle').fill(title);page.locator('#confirmCreate').click()
    page.wait_for_url(lambda url:'/invitations/' in url and url.endswith('/editor'),timeout=15000)
    invitation_id=page.url.split('/invitations/',1)[1].split('/',1)[0]
    dismiss_editor_onboarding(page,timeout=20000)
    return invitation_id

def main()->int:
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION':'0'}) as (_proc,base,_data):
        with sync_playwright() as p:
            browser=launch_chromium(p)
            page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(15000)
            title='Project Cover Navigation'
            invite_id=register_and_create(page,base,title)
            page.goto(base+'/dashboard.html',wait_until='networkidle')
            cover=page.get_by_role('button',name=f'Open {title}',exact=True)
            assert cover.is_visible();cover.click()
            page.wait_for_url(lambda url:f'/invitations/{invite_id}/editor' in url,timeout=15000)
            page.goto(base+'/dashboard.html',wait_until='networkidle')
            card=page.locator('.invite-card').filter(has_text=title).first
            menu_button=card.get_by_role('button',name='Project actions',exact=True)
            assert menu_button.is_visible();menu_button.click()
            edit=card.locator('.fp-project-menu').get_by_role('button',name='Edit',exact=True)
            assert edit.is_visible();edit.click()
            page.wait_for_url(lambda url:f'/invitations/{invite_id}/editor' in url,timeout=15000)
            browser.close()
    print('V0_52_DASHBOARD_COVER_NAVIGATION_TEST_PASSED')
    return 0

if __name__=='__main__': raise SystemExit(main())
