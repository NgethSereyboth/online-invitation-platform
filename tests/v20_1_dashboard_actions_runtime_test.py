#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 html=(ROOT/'dashboard.html').read_text(encoding='utf-8')
 css=(ROOT/'bundle-dashboard-v15.css').read_text(encoding='utf-8')
 js=(ROOT/'bundle-dashboard-v15.js').read_text(encoding='utf-8').replace('</script>','<\\/script>')
 pre=r'''<script>const __m=new Map([['sovan-account-v1',JSON.stringify({email:'tester@example.com',role:'admin',plan:'Pro'})],['sovan-multi-invites-v1',JSON.stringify([{id:'one',title:'One',type:'Wedding',status:'Draft',views:1,rsvps:0,updatedAt:new Date().toISOString()}])],['sovan-invite-draft-v3:one',JSON.stringify({fields:{names:'One'},objects:{title:{type:'text',html:'One',textStyleId:'display',typographyModelVersion:1,fontPairing:'serif-formal',font:'noto-serif',fontSize:64}},designPages:[]})]]);const localStorage={getItem:k=>__m.get(String(k))??null,setItem:(k,v)=>__m.set(String(k),String(v)),removeItem:k=>__m.delete(String(k)),clear:()=>__m.clear()};const sessionStorage={getItem:()=>null,setItem:()=>{},removeItem:()=>{}};window.fetch=async()=>({ok:false,status:404,json:async()=>({})});window.alert=()=>{};window.confirm=()=>true;window.prompt=()=>'';window.scrollTo=()=>{};if(!crypto.randomUUID)crypto.randomUUID=()=>Math.random().toString(16).slice(2)+'-0000-4000-8000-000000000000';</script>'''
 html=re.sub(r'<script src="[^"]+"></script>','',html);html=re.sub(r'<link[^>]+>','',html)
 html=html.replace('</head>',f'<style>{css}</style>{pre}</head>').replace('</body>',f'<script>{js}</script></body>')
 return html
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_1_DASHBOARD_ACTIONS',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_1_DASHBOARD_ACTIONS',exc)
  for width in (1440,360,390,430):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   page.set_content(build(),wait_until='load',timeout=45000);page.wait_for_timeout(800)
   page.evaluate("""()=>{window.__nav=[];window.EInviteContext={navigate:(id,page)=>window.__nav.push([id,page])}}""")
   assert page.locator('#staticModeNotice').is_visible(),width
   for attr in ('edit','guests','responses','analytics','copy','archive','delete'):
    loc=page.locator(f'[data-{attr}="one"]');assert loc.count()>=1,(width,attr)
    assert page.evaluate("el=>typeof el.onclick==='function'",loc.first.element_handle()),(width,attr)
   page.evaluate("()=>{document.querySelectorAll('[data-edit=\"one\"]')[1].click();document.querySelector('[data-guests=\"one\"]').click();document.querySelector('[data-responses=\"one\"]').click();document.querySelector('[data-analytics=\"one\"]').click()}")
   nav=page.evaluate('()=>window.__nav');assert ['one','editor'] in nav and ['one','guests'] in nav and ['one','responses'] in nav and ['one','analytics'] in nav,(width,nav)
   page.evaluate("()=>document.querySelector('[data-copy=\"one\"]').click()");page.wait_for_timeout(250);assert page.evaluate("()=>JSON.parse(localStorage.getItem('sovan-multi-invites-v1')).length")>=2,width
   page.evaluate("()=>document.querySelector('[data-archive=\"one\"]').click()");page.wait_for_timeout(150);assert page.evaluate("()=>JSON.parse(localStorage.getItem('sovan-multi-invites-v1')).find(x=>x.id==='one').archived===true"),width
   assert not errors,(width,errors)
   page.close()
  browser.close()
 print('V20_1_DASHBOARD_ACTIONS_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
