#!/usr/bin/env python3
from __future__ import annotations
import base64
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]

def script(name):return (ROOT/name).read_text(encoding='utf-8')

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_CUSTOM_FONT_BROWSER',exc)
 encoded=base64.b64encode((ROOT/'assets/fonts/noto-sans-latin-400.woff2').read_bytes()).decode('ascii')
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_CUSTOM_FONT_BROWSER',exc)
  try:
   page=browser.new_page(viewport={'width':900,'height':650});page.set_default_timeout(25_000);errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   body=f'''<!doctype html><meta charset="utf-8"><div id="sample">Beautiful moments</div><script>window.__encoded="{encoded}";window.__bytes=Uint8Array.from(atob(__encoded),c=>c.charCodeAt(0));window.__url=URL.createObjectURL(new Blob([__bytes],{{type:'font/woff2'}}));</script><script>{script('typography-contract.js')}</script><script>{script('custom-fonts-v22.js')}</script>'''
   page.set_content(body,wait_until='load')
   result=page.evaluate("""async()=>{const id='custom-abcdef1234567890';const doc={customFonts:{[id]:{id,label:'Uploaded Runtime Font',url:__url,sha256:'abcdef1234567890abcdef1234567890',scripts:['Latin'],weight:400,style:'normal',licenseAcknowledged:true}}};EInviteCustomFonts.normalizeDocumentFonts(doc,{install:false});const entries=await EInviteCustomFonts.installDocumentFonts(doc);const meta=EInviteFontRegistry.data.fonts[id],pair='custom-pair-'+id,node=document.querySelector('#sample');node.style.fontFamily=meta.stack;await document.fonts.ready;return{id:EInviteTypography.fontId(id),pairEn:EInviteFontRegistry.pairedFont(pair,'en'),pairKm:EInviteFontRegistry.pairedFont(pair,'km'),family:getComputedStyle(node).fontFamily,entries:entries.length,loaded:document.fonts.check('16px "'+meta.family+'"')}}""")
   assert result['id']=='custom-abcdef1234567890',result
   assert result['pairEn']==result['id'] and result['pairKm']=='noto-serif-khmer',result
   assert result['entries']==1 and result['loaded'] and 'EInvite Custom' in result['family'],result
   assert not errors,errors
  finally:browser.close()
 print('V22_CUSTOM_FONT_BROWSER_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
