#!/usr/bin/env python3
"""Structured rich-text replacement preserves compatible marks, links, list, and Khmer locale."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v27_3_5_ai_test_support import ready
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_AI_RICH_TEXT_BROWSER',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_AI_RICH_TEXT_BROWSER',exc)
  page=browser.new_page();ready(page)
  out=page.evaluate("""()=>{const B=EInviteEditorBridge,S=EInviteAIActionService;B.transact('fixture',d=>{const o=d.objects.title;o.richText={version:1,paragraphs:[{id:'p1',paragraphStyleId:'display',locale:'km',direction:'auto',list:{type:'bullet',level:1,start:1,marker:'disc'},tabStops:[],overrides:{},runs:[{id:'r1',text:'ចំណងជើង',locale:'km',marks:{strong:true,emphasis:true},entityId:'link1'}]}],entities:{link1:{id:'link1',type:'link',url:'https://example.com'}}};o.text='ចំណងជើង';o.html='ចំណងជើង'});B.select(['title']);const context=S.captureContext();S.commit([{type:'replaceText',targetIds:['title'],text:'សូមគោរពអញ្ជើញ',mode:'preserve'}],{context});const o=B.getState().objects.title,p=o.richText.paragraphs[0],r=p.runs[0];return{text:o.text,locale:r.locale,marks:r.marks,entity:r.entityId,href:o.richText.entities[r.entityId]?.url,list:p.list,html:o.html}}""")
  assert out['text']=='សូមគោរពអញ្ជើញ' and out['locale']=='km',out
  assert out['marks']['strong'] and out['marks']['emphasis'] and out['href']=='https://example.com',out
  assert out['list']['type']=='bullet' and 'https://example.com' in out['html'] and 'javascript:' not in out['html'],out
  browser.close()
 print('V27_3_5_AI_RICH_TEXT_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
