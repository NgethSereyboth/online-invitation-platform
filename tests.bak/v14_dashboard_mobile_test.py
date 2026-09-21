#!/usr/bin/env python3
"""Live-server dashboard/template and mobile Quick Edit regression for V14."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from v14_test_utils import app_server

def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V14_DASHBOARD_MOBILE',exc)
 with app_server() as (_process,base,_data):
  print('v14 dashboard/mobile server',base,flush=True)
  with sync_playwright() as pw:
   try:browser=launch_chromium(pw)
   except Exception as exc:return skipped('V14_DASHBOARD_MOBILE',exc)
   context=browser.new_context(viewport={'width':1440,'height':900});page=context.new_page();errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'favicon' not in m.text.lower() else None)
   print('dashboard load',flush=True);page.goto(base+'/dashboard.html',wait_until='domcontentloaded',timeout=30000);print('dashboard dom ready',flush=True);page.wait_for_selector('#loginView,#dashboardView',timeout=15000);print('auth surface ready',flush=True);page.locator('#authRegisterTab').click();page.locator('#email').fill('v14-layout@example.com');page.locator('#password').fill('Strong-layout-v14-123');page.locator('#registerConfirmPassword').fill('Strong-layout-v14-123');page.locator('#loginBtn').click();print('registration submitted',flush=True);page.wait_for_selector('#dashboardView:not([hidden])',timeout=15000);print('dashboard view ready',flush=True);page.wait_for_selector('.dashboard-empty',state='visible',timeout=15000);print('empty state ready',flush=True)
   assert page.locator('.dashboard-empty').count()==1
   create=page.locator('#newBtn');
   if not create.is_visible():create=page.locator('#emptyCreate')
   create.click();page.wait_for_selector('#createDialog[open]')
   assert page.locator('#templateChoices button button,#templateChoices button a,#templateChoices a button,#templateChoices [role="button"] button,#templateChoices [role="button"] a').count()==0
   assert page.locator('#templateChoices .template-choice>.template-select-action').count()>0
   page.locator('#cancelCreate').click()
   print('creating dashboard fixtures',flush=True);result=page.evaluate("""async()=>{const built={document:{schemaVersion:13,eventType:'Wedding',fields:{names:'Dashboard test',namesKm:'',date:'2027-01-01',time:'17:00',venue:'Phnom Penh',venueKm:'ភ្នំពេញ',message:'Welcome',messageKm:'សូមស្វាគមន៍'},settings:{rsvpEnabled:false,wishesEnabled:true,scheduleEnabled:true,venueEnabled:true,galleryEnabled:false,countdownEnabled:false,musicEnabled:false,openingEnabled:false,contactEnabled:false},languageMode:'both',accent:'#9d4555',palette:{background:'#fff8f2',surface:'#ffffff',text:'#342c26',heading:'#9d4555'},sectionOrder:['schedule','venue','wishes'],schedule:[],venues:[],customBlocks:[],designPages:[],objects:{title:{id:'title',type:'text',left:'10%',top:'20%',width:'80%',height:'100px',html:'Dashboard test',fontSize:40,color:'#342c26',zIndex:1}}}};const docs=[];for(let i=0;i<11;i++){const d=structuredClone(built.document);d.fields.names=i===0?'An exceptionally long English invitation title designed to test two-line dashboard clipping and overflow':i===1?'ពិធីមង្គលការខ្មែរដែលមានចំណងជើងវែងសម្រាប់សាកល្បងការបង្ហាញនៅលើផ្ទាំងគ្រប់គ្រង':'Project '+(i+1);d.fields.namesKm=i===1?d.fields.names:'';const r=await fetch('/api/invitations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:'v14-layout-'+i,document:d})});if(!r.ok)throw Error(await r.text());docs.push(await r.json())}await fetch('/api/invitations/'+docs[2].id+'/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({document:docs[2].document})});await fetch('/api/invitations/'+docs[3].id+'/archive',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({archived:true})});return docs.map(x=>x.id)}""")
   print('reloading dashboard',flush=True);page.reload(wait_until='domcontentloaded',timeout=30000);page.wait_for_selector('.invite-card',timeout=15000);page.wait_for_timeout(700)
   assert page.locator('.invite-card').count()>=11
   geometry=page.locator('.invite-card').evaluate_all("cards=>cards.map(c=>{const cover=c.querySelector('.invite-cover'),title=c.querySelector('.invite-body h2');const cr=c.getBoundingClientRect(),rr=cover.getBoundingClientRect();return {coverRatio:rr.width/cr.width,coverHeight:rr.height,titleOverflow:title.scrollWidth-title.clientWidth,cardOverflow:c.scrollWidth-c.clientWidth}})")
   assert all(x['coverRatio']>.94 and x['coverHeight']>120 and x['titleOverflow']<=2 and x['cardOverflow']<=3 for x in geometry),geometry
   assert page.get_by_text('Published',exact=True).count()>=1
   page.locator('[data-dash-filter="archived"]').click();page.wait_for_timeout(250);assert page.locator('.invite-card:not([hidden])').count()>=1
   for theme in ('light','dark'):
    page.evaluate("theme=>{localStorage.setItem('einvite-theme-mode',theme);location.reload()}",theme);page.wait_for_load_state('domcontentloaded');page.wait_for_selector('.invite-card',timeout=15000);page.wait_for_timeout(350)
    contrast=page.evaluate("()=>{const e=document.querySelector('.invite-body h2'),s=getComputedStyle(e);return {color:s.color,bg:getComputedStyle(document.body).backgroundColor,visible:e.getBoundingClientRect().height>0}}")
    assert contrast['visible'] and contrast['color']!=contrast['bg'],(theme,contrast)
   print('templates check',flush=True);page.goto(base+'/templates.html',wait_until='domcontentloaded',timeout=30000);page.wait_for_function("()=>['loaded','empty','error'].includes(document.documentElement.dataset.templatesState)",timeout=15000);assert page.evaluate('()=>document.documentElement.dataset.templatesState')=='loaded';assert page.locator('.studio-card,.template-card,[data-template-id]').count()>0;assert page.locator('button button,a button,button a').count()==0
   page.locator('#studioSearch').fill('__no_template_can_match_v18__');page.wait_for_function("()=>document.documentElement.dataset.templatesState==='empty'");assert page.locator('#studioGrid .empty').is_visible();page.locator('#studioSearch').fill('');page.wait_for_function("()=>document.documentElement.dataset.templatesState==='loaded'")
   page.route('**/api/auth/me',lambda route:route.fulfill(status=200,content_type='application/json',body='{"user":null}'));page.reload(wait_until='domcontentloaded',timeout=30000);page.wait_for_function("()=>document.documentElement.dataset.templatesState==='error'",timeout=15000);assert page.locator('#studioGrid .template-error').is_visible();page.unroute('**/api/auth/me')
   first_id=result[0]
   page.evaluate("localStorage.setItem('einvite-final-tour-seen-v1','1')")
   for width,height in ((360,800),(390,844),(430,932)):
    print('mobile viewport',width,height,flush=True)
    mobile=context.new_page();mobile.set_viewport_size({'width':width,'height':height});local=[];mobile.on('pageerror',lambda e,bag=local:bag.append(str(e)));mobile.on('console',lambda m,bag=local:bag.append(m.text) if m.type=='error' else None)
    mobile.set_default_timeout(10000);mobile.goto(base+f'/invitations/{first_id}/editor',wait_until='domcontentloaded');mobile.wait_for_function("()=>document.documentElement.dataset.editorReady==='true'",timeout=20000);mobile.wait_for_selector('#mobileEditorV14Bar')
    assert mobile.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')<=4
    assert mobile.locator('aside.left').get_attribute('aria-hidden')=='true';assert mobile.locator('aside.right').get_attribute('aria-hidden')=='true'
    mobile.locator('#mobileToolsMode').click();assert mobile.locator('aside.left').get_attribute('aria-hidden')=='false';assert mobile.locator('aside.right').get_attribute('aria-hidden')=='true'
    mobile.locator('#mobileQuickMode').click();assert mobile.locator('aside.left').get_attribute('aria-hidden')=='true';assert mobile.locator('aside.right').get_attribute('aria-hidden')=='false'
    mobile.locator('#mobileCanvasMode').click();assert mobile.locator('aside.left').get_attribute('aria-hidden')=='true';assert mobile.locator('aside.right').get_attribute('aria-hidden')=='true'
    assert not mobile.locator('#eiTimelineLaunch').is_visible();mobile.locator('#mobileAdvancedV14').click();mobile.wait_for_selector('#mobileAdvancedDialogV14[open]')
    targets=mobile.locator('#mobileEditorV14Bar button').evaluate_all("els=>els.map(e=>{const r=e.getBoundingClientRect();return [r.width,r.height]})");assert all(w>=42 and h>=42 for w,h in targets),targets
    print('mobile viewport complete',width,height,flush=True);assert not local,local;mobile.close()
   assert not errors,errors
   context.close();browser.close()
 print('V14_DASHBOARD_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
