#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 spec=importlib.util.spec_from_file_location('inline',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_1_SEMANTIC_BOUNDARY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_1_SEMANTIC_BOUNDARY',exc)
  page=browser.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=45000);page.wait_for_timeout(1500)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.TypographyDocumentModel&&window.EInviteEditorBridge')
  starter=page.evaluate("""()=>({title:state.objects.title&&[state.objects.title.textStyleId,state.objects.title.fontSize,state.objects.title.typographyModelVersion],subtitle:state.objects.subtitle&&[state.objects.subtitle.textStyleId,state.objects.subtitle.fontSize,state.objects.subtitle.typographyModelVersion],details:state.objects.details&&[state.objects.details.textStyleId,state.objects.details.fontSize,state.objects.details.typographyModelVersion],hero:state.objects.hero?.type})""")
  assert starter['title']==['display',64,1] and starter['subtitle']==['subheading',28,1] and starter['details']==['body',18,1] and starter['hero']=='image',starter
  boundary=page.evaluate("""()=>{const d=structuredClone(state);while(Object.keys(d.typography.styles).length<63)TypographyDocumentModel.createStyle(d,{name:'Style '+Object.keys(d.typography.styles).length});const before=JSON.stringify(d);TypographyDocumentModel.createStyle(d,{name:'Sixty four'});const at64=Object.keys(d.typography.styles).length;const snapshot=JSON.stringify(d);let rejected=false;try{TypographyDocumentModel.createStyle(d,{name:'Sixty five'})}catch(e){rejected=e instanceof RangeError}return{at64,rejected,atomic:JSON.stringify(d)===snapshot,beforeChanged:before!==snapshot,max:TypographyDocumentModel.MAX_TEXT_STYLES}}""")
  assert boundary=={'at64':64,'rejected':True,'atomic':True,'beforeChanged':True,'max':64},boundary
  read_only=page.evaluate("""()=>{const before=JSON.stringify(state),history=EInviteEditorBridge.historyLength?.()??null;document.dispatchEvent(new Event('selectionchange'));window.EInviteTypographyV20?.refresh?.();return{same:before===JSON.stringify(state),historySame:history===(EInviteEditorBridge.historyLength?.()??null)}}""")
  assert read_only['same'] and read_only['historySame'],read_only
  contrast=page.evaluate("""()=>{const n=document.createElement('div');n.style.cssText='width:120px;height:40px;background-image:linear-gradient(red,blue);color:white';n.textContent='Text';document.body.append(n);const r=TypographyLayoutService.fitAndDiagnose(n,{fontSize:18,textAutoFit:'none',textAutoFitMax:18,textMinFontSize:12,fontWeight:'400',fontStyle:'normal',lineHeight:1.3,letterSpacing:0,textAlign:'left',textVerticalAlign:'top',textWrap:'normal',textColumns:1,textColumnGap:0,textPadding:0,locale:'en'});return r.diagnostics.warnings.map(x=>x.code)}""")
  assert 'contrast-undetermined' in contrast and 'insufficient-contrast' not in contrast,contrast
  page.evaluate("()=>openGuest()");page.wait_for_selector('#modalBody .published-text[data-object-id=title]');page.wait_for_timeout(450)
  if page.locator('#modalBody #openCover').count() and page.locator('#modalBody #openCover').is_visible():page.locator('#modalBody #openCover').click()
  preview=lambda:page.evaluate("""()=>{const n=document.querySelector('#modalBody .published-text[data-object-id=title]'),f=n?.querySelector('.typography-flow'),s=n?getComputedStyle(n):null;return{root:document.querySelector('#modalBody')?.dataset.language,guest:document.querySelector('#modalBody .guest')?.lang,lang:n?.lang,font:s?.fontFamily||'',text:f?.innerText?.trim()||'',pressed:Array.from(document.querySelectorAll('#modalBody [data-guest-lang]')).filter(x=>x.getAttribute('aria-pressed')==='true').map(x=>x.dataset.guestLang)}}""")
  en=preview();assert en['root']=='en' and en['guest']=='en' and en['lang']=='en' and en['text']=='Sophea & Dara' and en['pressed']==['en'] and 'Khmer' not in en['font'].split(',')[0],en
  page.locator('#modalBody [data-guest-lang=km]').click();page.wait_for_timeout(450);km=preview();assert km['root']=='km' and km['guest']=='km' and km['lang']=='km' and 'សុភា' in km['text'] and km['pressed']==['km'] and 'EInvite Noto Serif Khmer' in km['font'],km
  page.locator('#modalBody [data-guest-lang=en]').click();page.wait_for_timeout(450);en2=preview();assert en2['lang']=='en' and en2['text']=='Sophea & Dara' and en2['pressed']==['en'] and 'Khmer' not in en2['font'].split(',')[0],en2
  assert not errors,errors
  browser.close()
 print('V20_1_SEMANTIC_BOUNDARY_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
