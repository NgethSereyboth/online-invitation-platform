#!/usr/bin/env python3
"""Live-server desktop/mobile editor and public layout gate for V14."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from v14_test_utils import app_server

def serious(message):
    return message.type=='error' and not any(x in message.text.lower() for x in ('favicon','youtube','soundcloud','net::err_name_not_resolved'))

def main():
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V14_LIVE_LAYOUT',exc)
    with app_server() as (_process,base,_data):
      with sync_playwright() as pw:
        try:browser=launch_chromium(pw)
        except Exception as exc:return skipped('V14_LIVE_LAYOUT',exc)
        setup=browser.new_context(viewport={'width':1280,'height':720});page=setup.new_page();page.set_default_timeout(15000)
        page.goto(base+'/dashboard.html',wait_until='networkidle');page.locator('#authRegisterTab').click();page.locator('#email').fill('v14-layout@example.com');page.locator('#password').fill('Strong-v14-layout-123');page.locator('#registerConfirmPassword').fill('Strong-v14-layout-123');page.locator('#loginBtn').click();page.wait_for_selector('#dashboardView:not([hidden])')
        result=page.evaluate("""async()=>{const d={schemaVersion:13,eventType:'Wedding',fields:{names:'V14 Layout Invitation',namesKm:'ពិធីអញ្ជើញ V14',date:'2027-01-17',time:'17:00',venue:'Phnom Penh',venueKm:'ភ្នំពេញ',message:'You are invited.',messageKm:'សូមគោរពអញ្ជើញ។'},settings:{rsvpEnabled:false,wishesEnabled:true,scheduleEnabled:true,venueEnabled:true,galleryEnabled:false,countdownEnabled:false,musicEnabled:false,openingEnabled:true,contactEnabled:false},languageMode:'both',accent:'#9d4555',palette:{background:'#fff8f2',surface:'#ffffff',text:'#342c26',heading:'#9d4555'},schedule:[],venues:[],customBlocks:[],designPages:[],objects:{title:{id:'title',type:'text',left:'10%',top:'18%',width:'80%',height:'110px',html:'V14 Layout Invitation',fontSize:42,color:'#342c26',zIndex:1}},sectionOrder:['schedule','venue','wishes']};const c=await fetch('/api/invitations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:'v14-layout-live',document:d})});if(!c.ok)throw Error(await c.text());const inv=await c.json();const p=await fetch('/api/invitations/'+inv.id+'/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({document:d})});if(!p.ok)throw Error(await p.text());return {id:inv.id,slug:inv.slug}}""")
        cookies=setup.cookies();setup.close()
        cases=[('editor',f"/invitations/{result['id']}/editor",1440,900,True),('editor',f"/invitations/{result['id']}/editor",390,844,True),('guest',f"/i/{result['slug']}",1440,900,False),('guest',f"/i/{result['slug']}",390,844,False)]
        for kind,path,width,height,auth in cases:
            context=browser.new_context(viewport={'width':width,'height':height})
            if auth:context.add_cookies(cookies)
            check=context.new_page();check.set_default_timeout(20000);errors=[];bad_responses=[]
            check.on('pageerror',lambda e,bag=errors:bag.append(str(e)))
            check.on('console',lambda m,bag=errors:bag.append(m.text) if serious(m) else None)
            check.on('response',lambda r,bag=bad_responses:bag.append((r.status,r.url)) if r.status>=400 else None)
            response=check.goto(base+path,wait_until='domcontentloaded',timeout=30000);assert response and response.status==200,(kind,width,response.status if response else None)
            if kind=='editor':
                try:check.wait_for_function("()=>document.documentElement.dataset.editorReady==='true'",timeout=30000)
                except Exception as exc:
                    diagnostic=check.evaluate("""()=>({url:location.href,page:document.body?.dataset.page,ready:document.documentElement.dataset.editorReady,backend:document.documentElement.dataset.backendMode,title:document.title,body:(document.body?.innerText||'').slice(0,500)})""")
                    raise AssertionError((kind,width,diagnostic,errors,bad_responses)) from exc
                check.wait_for_selector('#stage .object',timeout=20000)
                if check.locator('#finalTourDismiss').count() and check.locator('#finalTourDismiss').is_visible(): check.locator('#finalTourDismiss').click()
                if width==390:
                    check.wait_for_selector('#mobileEditorV14Bar',state='visible');check.locator('#mobileToolsMode').click();assert check.locator('aside.left').get_attribute('aria-hidden')=='false';assert check.locator('aside.right').get_attribute('aria-hidden')=='true';check.locator('#mobileQuickMode').click();assert check.locator('aside.left').get_attribute('aria-hidden')=='true';assert check.locator('aside.right').get_attribute('aria-hidden')=='false'
            else:
                check.wait_for_function("()=>document.querySelector('#publicRoot')?.textContent.includes('V14 Layout Invitation')",timeout=15000)
            overflow=check.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=4,(kind,width,overflow)
            assert not errors,(kind,width,errors)
            context.close()
        browser.close()
    print('V14_LIVE_LAYOUT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
