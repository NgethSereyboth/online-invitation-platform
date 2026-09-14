#!/usr/bin/env python3
"""Side-effect-free AI layout preview and responsive diagnostic coverage."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
WIDTHS=[320,360,390,430,820,1024,1180,1440]
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_AI_LAYOUT_PREVIEW',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_AI_LAYOUT_PREVIEW',exc)
  page=browser.new_page();ready(page)
  out=page.evaluate("""async widths=>{const B=EInviteEditorBridge,S=EInviteAIActionService;B.select(['title']);const c=S.captureContext(),before=S.fingerprint(B.getState()),published=JSON.stringify(B.getState().publishedSnapshot||null),long='This formal invitation wording is deliberately long enough to overflow the compact title object across responsive layouts while remaining only a proposed document mutation. '.repeat(4),preview=await S.preview([{type:'replaceText',targetIds:['title'],text:long,mode:'preserve'}],{context:c,widths}),after=S.fingerprint(B.getState()),publishedAfter=JSON.stringify(B.getState().publishedSnapshot||null);const fixed=await S.preview(S.applyRepair([{type:'replaceText',targetIds:['title'],text:long,mode:'preserve'}],'auto-fit',preview),{context:c,widths});return{before,after,published,publishedAfter,preview,fixed}}""",WIDTHS)
  assert out['before']==out['after'] and out['published']==out['publishedAfter'],out
  assert out['preview']['ok'] and set(WIDTHS).issubset({w['width'] for w in out['preview']['warnings'] if w.get('width')}),out['preview']['warnings']
  assert 'auto-fit' in out['preview']['repairOptions'] and out['fixed']['ok'],out
  browser.close()
 print('V27_3_5_AI_LAYOUT_PREVIEW_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
