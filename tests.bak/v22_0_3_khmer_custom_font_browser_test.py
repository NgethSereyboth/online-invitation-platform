#!/usr/bin/env python3
from __future__ import annotations
import base64
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def script(name):return (ROOT/name).read_text(encoding='utf-8')

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_0_3_KHMER_CUSTOM_FONT_BROWSER',exc)
 encoded=base64.b64encode((ROOT/'assets/fonts/noto-sans-khmer-400.woff2').read_bytes()).decode('ascii')
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_0_3_KHMER_CUSTOM_FONT_BROWSER',exc)
  try:
   page=browser.new_page(viewport={'width':900,'height':650});page.set_default_timeout(25_000);errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   body=f'''<!doctype html><meta charset="utf-8"><div id="sample">សិរីមង្គលអាពាហ៍ពិពាហ៍ កម្ពុជា ២០២៦</div><script>window.__encoded="{encoded}";window.__bytes=Uint8Array.from(atob(__encoded),c=>c.charCodeAt(0));window.__url=URL.createObjectURL(new Blob([__bytes],{{type:'font/woff2'}}));</script><script>{script('typography-contract.js')}</script><script>{script('custom-fonts-v22.js')}</script><script>{script('typography-layout-service.js')}</script>'''
   page.set_content(body,wait_until='load')
   result=page.evaluate("""async()=>{const id='custom-333333333333',entry={id,label:'Khmer Browser Font',url:__url,sha256:'3'.repeat(64),category:'sans',scripts:['Khmer'],weight:400,style:'normal',khmerReady:true,khmerSupport:'ready',khmerCoreCoveragePercent:100,khmerShaping:true,recommendedLineHeight:1.42,licenseAcknowledged:true},doc={customFonts:{[id]:entry}};EInviteCustomFonts.normalizeDocumentFonts(doc,{install:false});await EInviteCustomFonts.installDocumentFonts(doc);const meta=EInviteFontRegistry.data.fonts[id],pair='custom-pair-'+id,node=document.querySelector('#sample');const model={locale:'km',text:node.textContent,font:id,fontStack:meta.stack,fontSize:34,lineHeight:1.1,textPadding:0,textColumns:1,textAlign:'left',textVerticalAlign:'top',textWrap:'normal'};TypographyLayoutService.applyToElement(node,model);await document.fonts.ready;const computed=getComputedStyle(node);return{pair:EInviteFontRegistry.pairedFont(pair,'km'),loaded:document.fonts.check('34px "'+meta.family+'"','អាពាហ៍ពិពាហ៍'),family:computed.fontFamily,lineHeight:computed.lineHeight,fontSynthesis:computed.fontSynthesis,cluster:TypographyLayoutService.assertRenderedClusterIntegrity(node,'km').ok}}""")
   assert result['pair']=='custom-333333333333',result
   assert result['loaded'] and 'EInvite Custom' in result['family'],result
   assert result['fontSynthesis']=='none' and result['cluster'] is True,result
   assert not errors,errors
  finally:browser.close()
 print('V22_0_3_KHMER_CUSTOM_FONT_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
