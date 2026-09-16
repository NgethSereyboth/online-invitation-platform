#!/usr/bin/env python3
"""Bundled, delayed and offline English/Khmer font loading for V19.1."""
from __future__ import annotations
import time,urllib.request
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v14_test_utils import app_server
ROOT=Path(__file__).resolve().parents[1]
FONTS=['noto-sans-latin-400.woff2','noto-sans-latin-700.woff2','noto-serif-latin-400.woff2','noto-serif-latin-700.woff2','noto-sans-khmer-400.woff2','noto-sans-khmer-700.woff2','noto-serif-khmer-400.woff2','noto-serif-khmer-700.woff2']

def main()->int:
 for name in FONTS:
  path=ROOT/'assets'/'fonts'/name;assert path.is_file() and path.stat().st_size>1000,path
 assert (ROOT/'licenses'/'fonts'/'Noto-OFL-1.1.txt').is_file()
 css=(ROOT/'typography-fonts.css').read_text(encoding='utf-8');assert css.count('font-display:swap')==8
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V19_1_FONT_LOADING',exc)
 with app_server() as (_process,base,_data):
  for name in FONTS:
   with urllib.request.urlopen(f'{base}/assets/fonts/{name}',timeout=5) as response:
    assert response.status==200 and len(response.read())>1000
  with sync_playwright() as p:
   try:browser=launch_chromium(p)
   except Exception as exc:return skipped('V19_1_FONT_LOADING',exc)
   context=browser.new_context(viewport={'width':390,'height':844});page=context.new_page();page.set_default_timeout(35_000);font_requests=[];errors=[];bad_responses=[]
   page.on('response',lambda r:bad_responses.append((r.status,r.url)) if r.status>=400 else None)
   def delay_font(route):
    font_requests.append(route.request.url);time.sleep(.12);route.continue_()
   page.route('**/*.woff2',delay_font)
   page.goto(base+'/public.html',wait_until='domcontentloaded',timeout=40_000);page.wait_for_function('()=>window.EInviteRenderer&&window.EInviteTypography')
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   initial=page.evaluate("""()=>new Promise(resolve=>{document.body.innerHTML='<main id="fontMount" style="position:relative;width:320px;height:400px"></main>';const m=document.querySelector('#fontMount'),o={type:'text',html:'សូមស្វាគមន៍ Welcome Typography',font:'noto-serif-khmer',fontSize:52,fontWeight:'700',textAutoFit:'fit',textAutoFitMax:52,textMinFontSize:8,textWrap:'pretty',textColumns:1,textColumnGap:0,textAlign:'justify',left:'0%',top:'0%',width:'42%',height:'130px'};m.innerHTML=EInviteRenderer.renderObject(o,{id:'font'});const outer=m.firstElementChild;outer.style.position='absolute';const stop=EInviteRenderer.installResponsiveTypography(m);const before={status:document.fonts.status,computed:outer.dataset.textComputedFontSize||'',width:outer.clientWidth};document.fonts.ready.then(()=>setTimeout(()=>{const flow=outer.querySelector('.typography-flow'),cs=getComputedStyle(outer);resolve({before,after:{status:document.fonts.status,computed:outer.dataset.textComputedFontSize,font:cs.fontFamily,overflowX:flow.scrollWidth-outer.clientWidth,overflowY:flow.scrollHeight-outer.clientHeight,checks:[document.fonts.check('700 16px "EInvite Noto Serif"','Welcome'),document.fonts.check('700 16px "EInvite Noto Serif Khmer"','សូមស្វាគមន៍')]}});stop()},180))})""")
   assert initial['after']['status']=='loaded' and all(initial['after']['checks']),initial
   assert 'EInvite Noto Serif Khmer' in initial['after']['font'] and initial['after']['overflowX']<=2 and initial['after']['overflowY']<=2,initial
   assert font_requests,font_requests
   context.set_offline(True)
   offline=page.evaluate("""()=>{const m=document.querySelector('#fontMount'),outer=m.firstElementChild;outer.style.fontSize='52px';EInviteRenderer.fitTypographyElement(outer);const f=outer.querySelector('.typography-flow');return{font:getComputedStyle(outer).fontFamily,computed:outer.dataset.textComputedFontSize,overflowX:f.scrollWidth-outer.clientWidth,overflowY:f.scrollHeight-outer.clientHeight,loaded:document.fonts.check('700 16px "EInvite Noto Serif Khmer"','សូមស្វាគមន៍')}}""")
   assert offline['loaded'] and 'EInvite Noto Serif Khmer' in offline['font'] and offline['overflowX']<=2 and offline['overflowY']<=2,offline
   expected_missing=('/favicon.ico','/api/public/__INVITATION_SLUG__')
   unexpected=[item for item in bad_responses if not item[1].endswith(expected_missing)]
   if errors and bad_responses and not unexpected:errors.clear()
   assert not unexpected,(unexpected,font_requests)
   assert not errors,errors
   browser.close()
 print('V19_1_FONT_LOADING_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
