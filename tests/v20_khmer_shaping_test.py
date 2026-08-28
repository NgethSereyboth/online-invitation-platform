#!/usr/bin/env python3
"""Real-Chromium Khmer grapheme shaping and rendered line-boundary regression."""
from __future__ import annotations
import base64
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_KHMER_SHAPING',exc)
 font=base64.b64encode((ROOT/'assets/fonts/noto-serif-khmer-400.woff2').read_bytes()).decode('ascii')
 scripts='\n'.join(f'<script>{(ROOT/name).read_text(encoding="utf-8")}</script>' for name in ('typography-contract.js','typography-layout-service.js'))
 html=f'''<!doctype html><meta charset="utf-8"><style>@font-face{{font-family:"V20 Khmer";src:url(data:font/woff2;base64,{font}) format("woff2");font-weight:400}}body{{margin:0}}.host{{position:absolute;left:20px;width:150px;height:210px;background:#fff}} </style>{scripts}<div id="host" class="host"></div>'''
 samples=[
  'កម្ពុជា សូមស្វាគមន៍មកកាន់ព្រះរាជាណាចក្រកម្ពុជា',
  'ក្រសួងមហាផ្ទៃ ក្រុមការងារ ប្រជាពលរដ្ឋ ខ្មែរ',
  'អង្គការ សន្តិសុខ ឌីជីថល សហប្រតិបត្តិការ',
 ]
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_KHMER_SHAPING',exc)
  page=browser.new_page(viewport={'width':500,'height':400});page.set_content(html,wait_until='load');page.evaluate("()=>document.fonts.ready")
  rows=[]
  for columns in (1,2):
   for align in ('left','justify'):
    for text in samples:
     result=page.evaluate("""([text,columns,align])=>{const host=document.querySelector('#host');host.replaceChildren();host.textContent=text;const model={fontStack:'"V20 Khmer", serif',fontSize:24,textAutoFit:'fit',textAutoFitMax:24,textMinFontSize:12,fontWeight:'400',fontStyle:'normal',lineHeight:1.55,letterSpacing:0,color:'#111111',textAlign:align,textVerticalAlign:'top',textWrap:'normal',textColumns:columns,textColumnGap:14,textPadding:6,locale:'km'};const fitted=TypographyLayoutService.fitAndDiagnose(host,model);const clusters=TypographyLayoutService.assertRenderedClusterIntegrity(host,'km');return{columns,align,text,clusterCount:clusters.clusters.length,violations:clusters.violations,ok:clusters.ok,lines:[...new Set(clusters.clusters.flatMap(x=>x.lines))].length,overflow:fitted.diagnostics.overflow,wordBreak:getComputedStyle(host).wordBreak,overflowWrap:getComputedStyle(host).overflowWrap,lineBreak:getComputedStyle(host).lineBreak,hyphens:getComputedStyle(host.querySelector('.typography-flow')).hyphens}}""",[text,columns,align])
     rows.append(result)
  assert all(r['ok'] and not r['violations'] and r['clusterCount']>5 and r['lines']>=2 for r in rows),rows
  assert all(r['wordBreak']=='normal' and r['overflowWrap']=='normal' and r['hyphens']=='none' for r in rows),rows
  # Explicit coeng sequence must remain one grapheme in both Intl and fallback policy.
  check=page.evaluate("""()=>{const text='ក្រ ខ្មែរ ស្ត្រី';const segments=TypographyLayoutService.segmentGraphemes(text,'km');return{segments,ok:TypographyLayoutService.preservesKhmerClusters(text,segments)}}""")
  assert check['ok'] and any('្រ' in segment or '្ត' in segment for segment in check['segments']),check
  browser.close()
 print('V20_KHMER_SHAPING_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
