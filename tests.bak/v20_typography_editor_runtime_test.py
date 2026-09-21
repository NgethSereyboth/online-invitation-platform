#!/usr/bin/env python3
"""Real Chromium V20 semantic styles, undo/redo, accessibility and Khmer checks."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v20_typography',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_TYPOGRAPHY_EDITOR',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_TYPOGRAPHY_EDITOR',exc)
  page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(35_000);errors=[]
  page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=45_000);page.wait_for_timeout(1900)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteTypographyV20&&window.TypographyDocumentModel&&window.TypographyLayoutService&&window.EInviteCommands')
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle'])");page.wait_for_timeout(250)
  groups=page.locator('#advancedTextLayout > .v20-inspector-group > h3').all_text_contents()
  assert groups==['Text','Paragraph','Auto-fit and overflow','Columns','Advanced appearance'],groups
  for selector in ('#v20TextStyle','#font','#fontSize','#fontBold','#fontItalic','#textAlign','#color','#textAutoFit','#v20Fit','#v20ExpandBox','#v20ReduceText','#v20ResetOverride'):
   node=page.locator(selector);assert node.count()==1 and node.is_visible(),selector
  a11y=page.evaluate("""()=>[...document.querySelectorAll('#advancedTextLayout input,#advancedTextLayout select,#advancedTextLayout button')].map(e=>({id:e.id,label:e.getAttribute('aria-label')||e.closest('label')?.innerText?.trim()||e.textContent?.trim()}))""")
  assert all(x['label'] for x in a11y),a11y
  page.locator('#v20TextStyle').focus();focus=page.evaluate("""()=>{const e=document.activeElement,s=getComputedStyle(e);return{active:e.id,outline:s.outlineStyle,width:s.outlineWidth}}""");assert focus['active']=='v20TextStyle' and focus['outline']!='none' and focus['width']!='0px',focus

  before=page.evaluate("""()=>{const old=state.typography.styles.body.fontSize;EInviteCommands.execute('Create and link shared style',doc=>{const id=TypographyDocumentModel.createStyle(doc,{...doc.typography.styles.body,id:'v20-shared',name:'V20 Shared',fontSize:24,textAutoFit:'fit',textAutoFitMax:32,textMinFontSize:12});TypographyDocumentModel.linkObject(doc.objects.title,id);TypographyDocumentModel.linkObject(doc.objects.subtitle,id)});EInviteCommands.execute('Edit linked V20 style',doc=>TypographyDocumentModel.updateStyle(doc,'v20-shared',{fontSize:30,textAutoFitMax:40}));return{old,style:state.typography.styles['v20-shared'],title:state.objects.title,subtitle:state.objects.subtitle}}""")
  assert before['style']['fontSize']==30 and before['style']['textAutoFitMax']==40,before
  assert before['title']['fontSize']==30 and before['subtitle']['fontSize']==30,before
  assert before['title']['typographyOverrides']=={} and before['subtitle']['typographyOverrides']=={},before
  page.evaluate("()=>EInviteEditorBridge.undo()");page.wait_for_timeout(220)
  undo=page.evaluate("()=>({size:state.typography.styles['v20-shared'].fontSize,title:state.objects.title.fontSize,subtitle:state.objects.subtitle.fontSize})")
  assert undo=={'size':24,'title':24,'subtitle':24},undo
  page.evaluate("()=>EInviteEditorBridge.redo()");page.wait_for_timeout(220)
  redo=page.evaluate("()=>({size:state.typography.styles['v20-shared'].fontSize,title:state.objects.title.fontSize,subtitle:state.objects.subtitle.fontSize})")
  assert redo=={'size':30,'title':30,'subtitle':30},redo

  override=page.evaluate("""()=>{EInviteCommands.execute('Override one linked object',doc=>TypographyDocumentModel.setOverride(doc.objects.title,'fontSize',35));return{title:state.objects.title.fontSize,subtitle:state.objects.subtitle.fontSize,titleOverrides:state.objects.title.typographyOverrides}}""")
  assert override['title']==35 and override['subtitle']==30 and override['titleOverrides']['fontSize']==35,override
  reset=page.evaluate("""()=>{EInviteCommands.execute('Reset one override',doc=>TypographyDocumentModel.resetOverride(doc.objects.title,'fontSize'));return{title:state.objects.title.fontSize,overrides:state.objects.title.typographyOverrides}}""")
  assert reset['title']==30 and 'fontSize' not in reset['overrides'],reset

  deletion=page.evaluate("""()=>{EInviteCommands.execute('Delete style with replacement',doc=>TypographyDocumentModel.deleteStyle(doc,'v20-shared','body'));return{exists:!!state.typography.styles['v20-shared'],title:state.objects.title.textStyleId,subtitle:state.objects.subtitle.textStyleId}}""")
  assert deletion=={'exists':False,'title':'body','subtitle':'body'},deletion
  page.evaluate("()=>EInviteEditorBridge.undo()");page.wait_for_timeout(180)
  restored=page.evaluate("()=>({exists:!!state.typography.styles['v20-shared'],title:state.objects.title.textStyleId,subtitle:state.objects.subtitle.textStyleId})")
  assert restored=={'exists':True,'title':'v20-shared','subtitle':'v20-shared'},restored

  khmer=page.evaluate("""()=>{const text='កម្ពុជា សូមស្វាគមន៍ ក្រ';const segments=TypographyLayoutService.segmentGraphemes(text,'km');return{text,segments,joined:segments.join(''),preserved:TypographyLayoutService.preservesKhmerClusters(text,segments),locale:TypographyDocumentModel.detectLocale(text)}}""")
  assert khmer['joined']==khmer['text'] and khmer['preserved'] and khmer['locale']=='km',khmer

  warning=page.evaluate("""()=>{const host=document.createElement('div');Object.assign(host.style,{position:'fixed',left:'-5000px',width:'90px',height:'28px',background:'#ffffff'});host.textContent='Unreadably long Khmer text សូមស្វាគមន៍សូមស្វាគមន៍';document.body.append(host);const model={fontStack:'sans-serif',fontSize:9,textAutoFit:'none',textAutoFitMax:9,textMinFontSize:8,fontWeight:'400',fontStyle:'normal',lineHeight:1.3,letterSpacing:0,color:'#fefefe',textAlign:'left',textVerticalAlign:'top',textWrap:'normal',textColumns:3,textColumnGap:24,textPadding:2,locale:'km'};const result=TypographyLayoutService.fitAndDiagnose(host,model);return{codes:result.diagnostics.warnings.map(x=>x.code),invalid:host.getAttribute('aria-invalid')}}""")
  assert {'unreadable-size','clipped-content','excessive-columns','insufficient-contrast'}<=set(warning['codes']),warning
  assert warning['invalid']=='true',warning

  page.evaluate("""()=>{state.designPages=[{id:'v20-overflow-thumb',name:'Overflow page',enabled:true,objects:{tiny:{type:'text',html:'សូមស្វាគមន៍ '.repeat(40),font:'noto-serif-khmer',fontSize:42,textAutoFit:'none',textColumns:2,textColumnGap:24,left:'5%',top:'5%',width:'20%',height:'35px'}}}];renderPageNavigator()}""");page.wait_for_timeout(300)
  thumb=page.evaluate("""()=>{const badge=document.querySelector('.page-nav-card:not(.hero-card) .v20-overflow-badge'),text=document.querySelector('.page-nav-card:not(.hero-card) .typography-thumbnail-source .published-text');return{badge:!!badge,label:badge?.getAttribute('aria-label'),font:text?getComputedStyle(text).fontFamily:'',pipeline:!!document.querySelector('.page-nav-card:not(.hero-card) .typography-thumbnail-source')}}""")
  assert thumb['badge'] and thumb['label']=='Text overflow' and 'EInvite Noto Serif Khmer' in thumb['font'] and thumb['pipeline'],thumb

  page.locator('#v20ResponsivePreview').focus();page.locator('#v20ResponsivePreview').click();page.wait_for_timeout(220)
  widths=page.locator('.v20-preview-widths button').all_text_contents();assert widths==['320','360','390','430','768'],widths
  assert page.locator('.v20-preview-pane').count()==2
  pipelines=page.evaluate("""()=>({editor:document.querySelector('[data-preview-pipeline=editor] .object')?.dataset.previewPipeline,public:document.querySelector('[data-preview-pipeline=public] .published-object')?.dataset.previewPipeline,editorClass:!!document.querySelector('[data-preview-pipeline=editor] .object .content'),publicClass:!!document.querySelector('[data-preview-pipeline=public] .published-object .typography-flow')})""");assert pipelines=={'editor':'editor','public':'public','editorClass':True,'publicClass':True},pipelines
  page.locator('.v20-preview-dialog header button').click();page.wait_for_timeout(100);assert page.evaluate("()=>document.activeElement?.id")=='v20ResponsivePreview'
  assert not errors,errors[:20]
  browser.close()
 print('V20_TYPOGRAPHY_EDITOR_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
