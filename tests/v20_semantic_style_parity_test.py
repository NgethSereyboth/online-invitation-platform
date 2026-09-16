#!/usr/bin/env python3
"""Real-Chromium V20 linked-style parity across actual editor and public preview pipelines."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v20_parity',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_SEMANTIC_STYLE_PARITY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_SEMANTIC_STYLE_PARITY',exc)
  page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(35_000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build(),wait_until='load',timeout=45_000);page.wait_for_timeout(1800)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteTypographyV20&&window.EInviteCommands')
  page.evaluate("""()=>EInviteCommands.execute('Parity style',doc=>{const id=TypographyDocumentModel.createStyle(doc,{...doc.typography.styles.body,id:'parity-km',name:'Parity Khmer',fontPairing:'serif-formal',fontSize:34,textAutoFit:'fit',textAutoFitMax:42,textMinFontSize:12,fontWeight:'700',fontStyle:'normal',lineHeight:1.55,letterSpacing:.5,colorToken:'heading',textAlign:'justify',textVerticalAlign:'middle',textWrap:'pretty',textColumns:2,textColumnGap:18,textPadding:10});for(const key of ['title','subtitle']){const o=doc.objects[key];o.html='ក្រសួងមហាផ្ទៃ សូមស្វាគមន៍មកកាន់ព្រះរាជាណាចក្រកម្ពុជា';o.width='72%';o.height='180px';TypographyDocumentModel.linkObject(o,id)}TypographyDocumentModel.setOverride(doc.objects.subtitle,'textColumns',1)})""");page.evaluate("()=>EInviteEditorBridge.select(['title'])");page.wait_for_timeout(250);page.locator('#v20ResponsivePreview').click();page.wait_for_timeout(250)
  for width in (320,360,390,430,768):
   page.locator(f'.v20-preview-widths button[data-width="{width}"]').click();page.wait_for_timeout(180)
   result=page.evaluate("""()=>{const e=document.querySelector('[data-preview-pipeline=editor] .object[data-id=title] .content'),p=document.querySelector('[data-preview-pipeline=public] .published-object[data-object-id=title]'),ef=e?.querySelector('.typography-flow'),pf=p?.querySelector('.typography-flow'),es=getComputedStyle(e),ps=getComputedStyle(p),efs=getComputedStyle(ef),pfs=getComputedStyle(pf);return{editor:!!e,public:!!p,eSize:parseFloat(es.fontSize),pSize:parseFloat(ps.fontSize),eFont:es.fontFamily,pFont:ps.fontFamily,eWeight:es.fontWeight,pWeight:ps.fontWeight,eAlign:es.textAlign,pAlign:ps.textAlign,eColumns:efs.columnCount,pColumns:pfs.columnCount,eWrap:efs.textWrap,pWrap:pfs.textWrap,eLang:e.lang,pLang:p.lang,eOverflow:e.dataset.typographyOverflow,pOverflow:p.dataset.typographyOverflow}}""")
   assert result['editor'] and result['public'],result
   assert abs(result['eSize']-result['pSize'])<=.2,(width,result)
   for a,b in (('eFont','pFont'),('eWeight','pWeight'),('eAlign','pAlign'),('eColumns','pColumns'),('eWrap','pWrap'),('eLang','pLang'),('eOverflow','pOverflow')):assert result[a]==result[b],(width,a,b,result)
  page.keyboard.press('Escape');assert not errors,errors;browser.close()
 print('V20_SEMANTIC_STYLE_PARITY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
