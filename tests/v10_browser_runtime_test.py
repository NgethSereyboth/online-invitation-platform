#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from inline_editor_runtime_test import build_inline_editor

def main():
    try: from playwright.sync_api import sync_playwright
    except Exception as e: return skipped('V10_BROWSER',e)
    html=build_inline_editor()
    with sync_playwright() as p:
        try:b=launch_chromium(p)
        except Exception as e:return skipped('V10_BROWSER',e)
        for width,height in [(390,844),(768,1024),(1024,768),(1280,720),(1440,900),(1920,1080)]:
            page=b.new_page(viewport={'width':width,'height':height});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='load');page.wait_for_timeout(1200)
            assert not errors,(width,errors)
            if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible(): page.locator('#finalTourDismiss').click()
            assert page.locator('.ei-experience-launch').count()==1
            if width<=600:
                page.locator('#mobileAdvancedV14').click();page.wait_for_selector('#mobileAdvancedDialogV14[open]')
                page.locator('#mobileAdvancedDialogV14 [data-launch=".ei-experience-launch"]').click()
            else:
                page.locator('#v16ToolbarMore summary').click()
                page.locator('#v16ToolbarMore .ei-experience-launch').click()
            page.wait_for_timeout(100)
            assert page.locator('#eiExperienceDialog[open]').count()==1
            assert page.locator('.ei-style-card').count()>=3
            page.locator('[data-ei-tab="opening"]').click();assert page.locator('.ei-scene-card').count()>=6
            page.locator('[data-ei-tab="storyboard"]').click();assert page.locator('.ei-story-card').count()>=2
            page.keyboard.press('Escape')
            if width<=600:
                page.locator('#mobileAdvancedV14').click();page.wait_for_selector('#mobileAdvancedDialogV14[open]')
                page.locator('#mobileAdvancedDialogV14 [data-launch="#eiFocusToggle"]').click()
            else:
                page.locator('#v16ToolbarMore summary').click()
                page.locator('#v16ToolbarMore #eiFocusToggle').click()
            assert 'ei-focus-mode' in (page.locator('body').get_attribute('class') or '')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.close()
        b.close()
    print('V10_BROWSER_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
