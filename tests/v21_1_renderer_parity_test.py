#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 spec=importlib.util.spec_from_file_location('inline_v211',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V21_1_RENDERER_PARITY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V21_1_RENDERER_PARITY',exc)
  page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(50000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=60000);page.wait_for_timeout(1600)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.RichTextRenderer&&window.RichTextDocumentModel&&window.EInviteEditorBridge')
  page.evaluate("""()=>{const doc=state,o=doc.objects['rich-demo']={...structuredClone(doc.objects.title),layerName:'Rich text demo',left:'10%',top:'12%',zIndex:99};o.width='78%';o.height='260px';o.textAutoFit='fit';o.textAutoFitMax=38;o.textMinFontSize=12;o.richTextModelVersion=1;o.richText={version:1,entities:{'link-official':{id:'link-official',type:'link',url:'https://example.com',title:'Official invitation information'}},paragraphs:[{id:'p-heading',paragraphStyleId:'heading',locale:'en',direction:'ltr',overrides:{textAlign:'center',lineHeight:1.25,spaceAfter:10},list:{type:'none',level:0,start:1,marker:'disc'},tabStops:[],runs:[{id:'r-en',text:'Welcome ',locale:'en',marks:{strong:true,colorToken:'heading'}},{id:'r-link',text:'Guests',locale:'en',marks:{underline:true,fontPairing:'sans-modern',fontSize:30},entityId:'link-official'}]},{id:'p-km',paragraphStyleId:'body',locale:'km',direction:'ltr',overrides:{textAlign:'justify',lineHeight:1.55,indentLeft:12,firstLineIndent:16,spaceAfter:8},list:{type:'none',level:0,start:1,marker:'disc'},tabStops:[{position:72,align:'left',leader:'dots'}],runs:[{id:'r-km',text:'សូមស្វាគមន៍\tមកកាន់ព្រះរាជាណាចក្រកម្ពុជា',locale:'km',marks:{emphasis:true,fontPairing:'serif-formal'}}]},{id:'p-list1',paragraphStyleId:'body',locale:'en',direction:'ltr',overrides:{},list:{type:'bullet',level:1,start:1,marker:'square'},tabStops:[],runs:[{id:'r-list1',text:'Ceremony',locale:'en',marks:{}}]},{id:'p-list2',paragraphStyleId:'body',locale:'km',direction:'ltr',overrides:{},list:{type:'bullet',level:1,start:1,marker:'square'},tabStops:[],runs:[{id:'r-list2',text:'ពិធីមង្គលការ',locale:'km',marks:{strikethrough:true}}]}]};o.html=RichTextDocumentModel.exportLegacyHtml(o.richText);o.text=RichTextDocumentModel.exportPlainText(o.richText);apply()}""")
  page.evaluate("()=>{apply();EInviteEditorBridge.select(['rich-demo'])}");page.wait_for_timeout(400)
  editor=page.evaluate("""()=>{const c=document.querySelector('.object[data-id=rich-demo] .content'),km=c?.querySelector('[lang=km].rt-run'),en=c?.querySelector('[lang=en].rt-run');return{html:c?.innerHTML,doc:!!c?.querySelector('.rt-document'),paragraphs:c?.querySelectorAll('.rt-paragraph').length||0,links:c?.querySelectorAll('a.rt-link').length||0,lists:c?.querySelectorAll('ul.rt-list').length||0,langs:[...(c?.querySelectorAll('.rt-run')||[])].map(x=>x.lang),khFont:km?getComputedStyle(km).fontFamily:'',enFont:en?getComputedStyle(en).fontFamily:'',linkName:c?.querySelector('a.rt-link')?.getAttribute('aria-label'),unsafe:[...(c?.querySelectorAll('*')||[])].some(x=>x.hasAttribute('onclick')||x.tagName==='SCRIPT')}}""")
  assert editor['doc'] and editor['paragraphs']==4 and editor['links']==1 and editor['lists']==1 and editor['linkName']=='Official invitation information' and not editor['unsafe'],editor
  assert 'km' in editor['langs'] and 'en' in editor['langs'] and 'Khmer' in editor['khFont'] and editor['enFont']!=editor['khFont'],editor
  page.locator('#v20ResponsivePreview').click();page.wait_for_timeout(300)
  for width in (320,360,390,430,768):
   page.locator(f'.v20-preview-widths button[data-width="{width}"]').click();page.wait_for_timeout(220)
   result=page.evaluate("""()=>{const e=document.querySelector('[data-preview-pipeline=editor] .object[data-id=rich-demo] .content'),p=document.querySelector('[data-preview-pipeline=public] .published-text[data-object-id=rich-demo] .typography-flow');const E=e?.querySelector('.rt-document'),P=p?.querySelector('.rt-document');return{e:!!E,p:!!P,eh:E?.innerHTML,ph:P?.innerHTML,ep:E?.querySelectorAll('.rt-paragraph').length,pp:P?.querySelectorAll('.rt-paragraph').length,el:E?.querySelectorAll('a').length,pl:P?.querySelectorAll('a').length,eo:e?.closest('.object')?.dataset.typographyOverflow,po:p?.closest('.published-text')?.dataset.typographyOverflow,ew:e?.scrollWidth,ec:e?.clientWidth,pw:p?.scrollWidth,pc:p?.clientWidth}}""")
   assert result['e'] and result['p'] and result['ep']==result['pp']==4 and result['el']==result['pl']==1,(width,result)
   assert result['eo']==result['po'],(width,result)
  thumb=page.evaluate("""()=>{const root=document.createElement('div');root.style.cssText='width:195px;height:422px;position:fixed;left:-9999px;top:0';document.body.append(root);const ctl=EInviteTypographyRendererAdapters.renderThumbnail(root,state,state.objects,{width:390,height:844});const rt=root.querySelector('[data-object-id=rich-demo] .rt-document');const out={exists:!!rt,paragraphs:rt?.querySelectorAll('.rt-paragraph').length,links:rt?.querySelectorAll('a').length};ctl?.disconnect?.();root.remove();return out}""")
  assert thumb=={'exists':True,'paragraphs':4,'links':1},thumb
  assert not errors,errors;browser.close()
 print('V21_1_RENDERER_PARITY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
