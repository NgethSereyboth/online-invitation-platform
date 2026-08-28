#!/usr/bin/env python3
"""Responsive, non-persistent V19.1 auto-fit at required widths and history transitions."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v19_1_responsive',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V19_1_RESPONSIVE_AUTOFIT',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V19_1_RESPONSIVE_AUTOFIT',exc)
  page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(30_000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=40_000);page.wait_for_timeout(1700)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteRenderer&&window.EInviteEditorBridge')
  text='សូមស្វាគមន៍មកកាន់ពិធីដ៏ពិសេសរបស់យើង។ Welcome to our celebration with family and friends. '*4
  widths=(320,360,390,430,768);measurements=[]
  for width in widths:
   result=page.evaluate("""([width,text])=>new Promise(resolve=>{let m=document.querySelector('#responsivePublicMount');if(!m){m=document.createElement('div');m.id='responsivePublicMount';Object.assign(m.style,{position:'fixed',left:'-6000px',top:'0',overflow:'hidden'});document.body.append(m)}m.style.width=width+'px';m.style.height=(width/390*844)+'px';const object={type:'text',html:text,font:'noto-serif-khmer',fontSize:52,textAutoFit:'fit',textAutoFitMax:52,textMinFontSize:8,textWrap:'pretty',textColumns:1,textColumnGap:0,textAlign:'justify',textVerticalAlign:'middle',left:'0%',top:'0%',width:'42%',height:'180px'};m.innerHTML=EInviteRenderer.renderObject(object,{id:'responsive'});const o=m.firstElementChild;o.style.position='absolute';const original=JSON.stringify(object);const stop=EInviteRenderer.installResponsiveTypography(m);setTimeout(()=>{const f=o.querySelector('.typography-flow');const r={width,clientWidth:o.clientWidth,scrollWidth:f.scrollWidth,clientHeight:o.clientHeight,scrollHeight:f.scrollHeight,computed:parseFloat(getComputedStyle(o).fontSize),min:Number(o.dataset.textMinFontSize),max:Number(o.dataset.textAutoFitMax),unchanged:JSON.stringify(object)===original};stop();resolve(r)},260)})""",[width,text])
   measurements.append(result)
  for r in measurements:
   assert r['clientWidth']>0 and r['min']<=r['computed']<=r['max'],r
   assert r['scrollWidth']<=r['clientWidth']+2 and r['scrollHeight']<=r['clientHeight']+2,r
   assert r['unchanged'],r
  assert 130<=measurements[0]['clientWidth']<=138,measurements[0]
  history=page.evaluate("""text=>new Promise(resolve=>{EInviteEditorBridge.transact('Auto fit baseline',doc=>{const o=doc.objects.subtitle;o.html=text;o.font='noto-serif-khmer';o.fontSize=44;o.textAutoFit='fit';o.textAutoFitMax=44;o.textMinFontSize=8;o.width='62%';o.height='120px'});EInviteEditorBridge.select(['subtitle']);setTimeout(()=>{const before=Number(document.querySelector('#stage .object[data-id="subtitle"] .content').dataset.textComputedFontSize);EInviteEditorBridge.transact('Narrow auto-fit box',doc=>{doc.objects.subtitle.width='30%'});setTimeout(()=>{const narrow=Number(document.querySelector('#stage .object[data-id="subtitle"] .content').dataset.textComputedFontSize),saved={fontSize:state.objects.subtitle.fontSize,max:state.objects.subtitle.textAutoFitMax,min:state.objects.subtitle.textMinFontSize};EInviteEditorBridge.undo();setTimeout(()=>{const undoWidth=state.objects.subtitle.width,undo=Number(document.querySelector('#stage .object[data-id="subtitle"] .content').dataset.textComputedFontSize);EInviteEditorBridge.redo();setTimeout(()=>resolve({before,narrow,undo,undoWidth,redoWidth:state.objects.subtitle.width,saved}),180)},180)},220)},220)})""",text)
  assert history['narrow']<=history['before'] and history['undoWidth']=='62%' and history['redoWidth']=='30%',history
  assert history['saved']=={'fontSize':44,'max':44,'min':8},history
  assert not errors,errors
  browser.close()
 print('V19_1_RESPONSIVE_AUTOFIT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
