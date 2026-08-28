#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
DOC={
 'fields':{'names':'English Title','namesKm':'ចំណងជើងខ្មែរ','message':'English subtitle','messageKm':'ចំណងជើងរងខ្មែរ','date':'2026-12-27','time':'16:00','venue':'English venue','venueKm':'ទីតាំងខ្មែរ'},
 'settings':{'rsvpEnabled':False,'scheduleEnabled':False,'venueEnabled':False,'galleryEnabled':False,'countdownEnabled':False,'openingEnabled':False,'contactEnabled':False},
 'languageMode':'both','dateFormat':'gregorian','sectionOrder':[],'palette':{'background':'#fff8f2','surface':'#fff','text':'#342c26','heading':'#9d4555'},'accent':'#9d4555',
 'objects':{
  'title':{'id':'title','type':'text','html':'English Title','left':'8%','top':'10%','width':'84%','height':'110px','textStyleId':'display','typographyModelVersion':1,'fontPairing':'serif-formal','font':'noto-serif','fontSize':64,'textAutoFit':'fit','textAutoFitMax':88,'textMinFontSize':18,'showInHero':True},
  'subtitle':{'id':'subtitle','type':'text','html':'English subtitle','left':'12%','top':'31%','width':'76%','height':'100px','textStyleId':'subheading','typographyModelVersion':1,'fontPairing':'sans-modern','font':'noto-sans','fontSize':28,'textAutoFit':'fit','textAutoFitMax':36,'textMinFontSize':14,'showInHero':True}
 },'designPages':[]}
def build(saved=''):
 html=(ROOT/'public.html').read_text(encoding='utf-8');css=(ROOT/'bundle-public-v15.css').read_text(encoding='utf-8');js=(ROOT/'bundle-public-v15.js').read_text(encoding='utf-8').replace('</script>','<\\/script>')
 payload=json.dumps({'document':DOC,'guest':None,'analyticsConsentRequired':False,'externalMediaConsentRequired':False},ensure_ascii=False)
 entries=f"[['einvite-guest-language:test','{saved}']]" if saved else '[]'
 pre=f'''<script>const __m=new Map({entries});const localStorage={{getItem:k=>__m.get(String(k))??null,setItem:(k,v)=>__m.set(String(k),String(v)),removeItem:k=>__m.delete(String(k))}};const sessionStorage={{getItem:()=>null,setItem:()=>{{}},removeItem:()=>{{}}}};window.fetch=async()=>({{ok:true,status:200,json:async()=>({payload})}});window.scrollTo=()=>{{}};if(!crypto.randomUUID)crypto.randomUUID=()=>"test-id";</script>'''
 html=re.sub(r'<script src="[^"]+"></script>','',html);html=re.sub(r'<link[^>]+>','',html)
 html=html.replace('<head>','<head><meta name="einvite-invitation-slug" content="test">',1).replace('</head>',f'<style>{css}</style>{pre}</head>').replace('</body>',f'<script>{js}</script></body>')
 return html
def snapshot(page):
 return page.evaluate("""()=>{const n=document.querySelector('[data-object-id=title]'),f=n?.querySelector('.typography-flow'),cs=n?getComputedStyle(n):null;return{root:document.querySelector('#publicRoot')?.dataset.language,lang:n?.lang,font:cs?.fontFamily||'',text:f?.textContent?.trim()||'',size:Number(n?.dataset.textComputedFontSize||0),overflow:n?Math.max(0,n.scrollWidth-n.clientWidth,n.scrollHeight-n.clientHeight):999,saved:localStorage.getItem('einvite-guest-language:test')}}""")
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_1_BILINGUAL_PUBLIC',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_1_BILINGUAL_PUBLIC',exc)
  for width in (320,360,390,430,768):
   page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   page.set_content(build(),wait_until='load',timeout=45000);page.wait_for_selector('[data-object-id=title]');page.wait_for_timeout(500)
   en=snapshot(page);assert en['root']=='en' and en['lang']=='en' and 'EInvite Noto Serif' in en['font'] and 'Khmer' not in en['font'].split(',')[0] and en['text']=='English Title' and en['overflow']<=2,(width,en)
   page.locator('[data-guest-lang=km]').click();page.wait_for_timeout(350);km=snapshot(page);assert km['root']=='km' and km['lang']=='km' and 'EInvite Noto Serif Khmer' in km['font'] and km['text']=='ចំណងជើងខ្មែរ' and km['saved']=='km' and km['overflow']<=2,(width,km)
   page.locator('[data-guest-lang=en]').click();page.wait_for_timeout(350);en2=snapshot(page);assert en2['lang']=='en' and en2['text']=='English Title' and en2['saved']=='en' and 'Khmer' not in en2['font'].split(',')[0],(width,en2)
   assert not errors,(width,errors);page.close()
  page=browser.new_page(viewport={'width':390,'height':900});page.set_content(build('km'),wait_until='load');page.wait_for_selector('[data-object-id=title]');page.wait_for_timeout(400);saved=snapshot(page);assert saved['lang']=='km' and saved['text']=='ចំណងជើងខ្មែរ' and 'EInvite Noto Serif Khmer' in saved['font'],saved;page.close();browser.close()
 print('V20_1_BILINGUAL_PUBLIC_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
