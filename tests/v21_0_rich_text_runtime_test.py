#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 spec=importlib.util.spec_from_file_location('inline_v21_0',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V21_0_RICH_TEXT_RUNTIME',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V21_0_RICH_TEXT_RUNTIME',exc)
  page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(45000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=60000);page.wait_for_timeout(1600)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.RichTextDocumentModel&&window.EInviteRichTextContract&&window.EInviteEditorBridge')
  starter=page.evaluate("""()=>({version:state.richTextModelVersion,title:state.objects.title.richTextModelVersion,plain:RichTextDocumentModel.exportPlainText(state.objects.title.richText),ids:state.objects.title.richText.paragraphs.flatMap(p=>[p.id,...p.runs.map(r=>r.id)])})""")
  assert starter['version']==1 and starter['title']==1 and starter['plain'] and len(starter['ids'])==len(set(starter['ids'])),starter
  migration=page.evaluate("""()=>{const legacy={type:'text',textStyleId:'body',html:'<strong>Hello</strong><br><em>សួស្តី</em><ul><li><a href="https://example.com">Guest</a></li></ul>'};const a=RichTextDocumentModel.migrateLegacy('runtime',legacy,{styleIds:new Set(Object.keys(state.typography.styles)),defaultStyleId:'body'}),b=RichTextDocumentModel.normalizeDocument(structuredClone(a),{strict:true,seed:'runtime',styleIds:new Set(Object.keys(state.typography.styles)),defaultStyleId:'body'});return{same:JSON.stringify(a)===JSON.stringify(b),plain:RichTextDocumentModel.exportPlainText(a),html:RichTextDocumentModel.exportLegacyHtml(a),locales:a.paragraphs.flatMap(p=>p.runs.map(r=>r.locale)),entities:Object.values(a.entities)}}""")
  assert migration['same'] and 'Hello' in migration['plain'] and 'សួស្តី' in migration['plain'] and '<strong>Hello</strong>' in migration['html'] and 'km' in migration['locales'] and migration['entities'][0]['url']=='https://example.com',migration
  edited=page.evaluate("""()=>{const node=document.querySelector('.object[data-id=title] .content');node.innerHTML='<strong>Changed</strong> <em>កម្ពុជា</em>';capture();const o=state.objects.title;return{plain:RichTextDocumentModel.exportPlainText(o.richText),marks:o.richText.paragraphs[0].runs.map(r=>r.marks),html:o.html,version:o.richTextModelVersion}}""")
  assert edited['plain']=='Changed កម្ពុជា' and edited['version']==1 and edited['marks'][0].get('strong') and edited['marks'][-1].get('emphasis'),edited
  hostile=page.evaluate("""()=>{const results=[];for(const value of [{version:1,paragraphs:[],entities:{},evil:1},{version:1,paragraphs:[{id:'p-ok',paragraphStyleId:'body',runs:[{id:'r-ok',text:'x',marks:{},entityId:'link-x'}]}],entities:{'link-x':{id:'link-x',type:'link',url:'javascript:alert(1)'}}}]){try{RichTextDocumentModel.normalizeDocument(value,{strict:true,styleIds:new Set(['body']),defaultStyleId:'body'});results.push(false)}catch{results.push(true)}}return results}""")
  assert hostile==[True,True],hostile
  deep=page.evaluate("""()=>{try{const n=EInviteRichTextContract.MAX_LEGACY_NESTING+1;RichTextDocumentModel.migrateLegacy('deep',{type:'text',html:'<div>'.repeat(n)+'x'+'</div>'.repeat(n)},{styleIds:new Set(['body']),defaultStyleId:'body'});return false}catch{return true}}""")
  assert deep,deep
  assert not errors,errors
  browser.close()
 print('V21_0_RICH_TEXT_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
