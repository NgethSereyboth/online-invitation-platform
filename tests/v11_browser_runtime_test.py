#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from inline_editor_runtime_test import build_inline_editor

def main():
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V11_BROWSER',exc)
    html=build_inline_editor()
    with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('V11_BROWSER',exc)
        page=browser.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='load');page.wait_for_timeout(1200)
        if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
        page.locator('#v16ToolbarMore summary').click();page.locator('#v16ToolbarMore .ei-experience-launch').click();
        # Style Kit preview is temporary and can be cancelled without persisting the preview state.
        original_kit=page.evaluate("state.styleKit?.id||''")
        page.evaluate("window.__v11OriginalSave=window.save;window.__v11SaveCalls=0;window.save=()=>window.__v11SaveCalls++");page.wait_for_timeout(500);page.evaluate("window.__v11SaveCalls=0")
        page.locator('[data-preview-kit="royal-khmer-gold"]').click();page.wait_for_timeout(100)
        assert page.evaluate("window.__v11SaveCalls")==0
        assert page.locator('#eiCancelKitPreview').count()==1 and page.evaluate("state.styleKit.id")=="royal-khmer-gold"
        page.locator('#eiCancelKitPreview').click();page.wait_for_timeout(120);assert page.evaluate("state.styleKit?.id||''")==original_kit
        page.evaluate("window.save=window.__v11OriginalSave")
        page.locator('[data-ei-tab="social"]').click();page.wait_for_timeout(300)
        assert page.locator('#eiSocialCanvas').count()==1 and page.locator('#eiDownloadPublishedSocial').count()==1 and page.locator('#eiChooseSocialPhoto').count()==1
        page.locator('#eiSocialText').select_option('light');page.locator('#eiSocialLanguage').select_option('km');page.locator('#eiRegenerateSocial').click();page.wait_for_timeout(200)
        assert page.evaluate("document.querySelector('#eiSocialCanvas').width===1200")
        # New experience controls remain readable in both application themes.
        contrast=page.evaluate("""()=>{document.documentElement.dataset.theme='dark';const el=document.querySelector('#eiExperienceDialog');const s=getComputedStyle(el);return {color:s.color,background:s.backgroundColor}}""")
        assert contrast['color']!=contrast['background'],contrast
        page.evaluate("document.documentElement.dataset.theme='light'")
        assert not errors,errors
        # Public-layout module: opening stays a direct child and the shell does not absorb it.
        result=page.evaluate('''()=>{const root=document.createElement('main');root.className='guest';root.innerHTML='<button id="openCover"></button><section id="content">Hello</section>';document.body.append(root);EInviteGuestLayouts.apply(root,{desktopGuestLayout:'ambient-frame',fields:{},socialCard:{},openingScene:{}});return {coverParent:root.querySelector('#openCover').parentElement===root,shells:root.querySelectorAll('.guest-layout-shell').length,content:root.querySelectorAll('.guest-layout-content #content').length}}''')
        assert result=={'coverParent':True,'shells':1,'content':1},result
        opening=page.evaluate('''()=>{const root=document.createElement('div');document.body.append(root);root.innerHTML=EInviteOpeningScenes.coverMarkup({fields:{names:'Test'},openingScene:{backgroundImage:'javascript:alert(1)',duration:0,enterText:'Enter'}},'en',EInviteRenderer.esc);const cover=root.querySelector('#openCover');const safe=!cover.getAttribute('style').includes('javascript:');EInviteOpeningScenes.enhance(root,{openingScene:{duration:0}});cover.click();return new Promise(resolve=>setTimeout(()=>resolve({safe,hidden:cover.hidden,aria:cover.getAttribute('aria-hidden')}),40))}''')
        assert opening=={'safe':True,'hidden':True,'aria':'true'},opening
        page.close()
        for width,height in [(390,844),(768,1024),(1024,768),(1280,720),(1440,900),(1920,1080)]:
            p2=browser.new_page(viewport={'width':width,'height':height});p2.set_content(html,wait_until='load');p2.wait_for_timeout(250)
            result=p2.evaluate("""()=>{
                document.body.innerHTML='<main class=\"guest\"><button id=\"openCover\"></button><section class=\"hero-card\"><h1>Test invitation</h1></section><section class=\"section-card\">Content</section></main>';
                const root=document.querySelector('.guest');
                EInviteGuestLayouts.apply(root,{desktopGuestLayout:'full-width',fields:{names:'Test invitation'},socialCard:{},openingScene:{}});
                return {overflow:document.documentElement.scrollWidth-innerWidth,coverDirect:root.querySelector('#openCover').parentElement===root};
            }""")
            assert result['overflow']<=2,(width,result);assert result['coverDirect'],(width,result);p2.close()
        browser.close()
    print('V11_BROWSER_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
