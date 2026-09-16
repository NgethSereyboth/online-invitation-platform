#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
BASE_CSS=['direct-manipulation-v24.css','content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']
BASE_JS=['direct-manipulation-v24.js','content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
V25_CSS=['adaptive-templates-v25.css','studio-governance-v25.css','print-readiness-v25.css','template-bindings-v25.css']
V25_JS=['adaptive-templates-v25.js','studio-governance-v25.js','print-readiness-v25.js','template-bindings-v25.js']
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(1200)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  for name in BASE_CSS+V25_CSS:page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{localStorage.setItem('einvite-v25-studio-resources',JSON.stringify([{id:'studio-brand-1',kind:'brand',name:'Official Studio Brand',category:'Government',payload:{primary:'#183a64',accent:'#b18a3b',background:'#f7f8fb',surface:'#ffffff',text:'#18202d',headingPair:'serif-formal',bodyPair:'sans-modern'},governance:{locked:true,allowedOverrides:['content','media']},status:'approved',version:3,createdAt:Date.now(),updatedAt:Date.now()}]));localStorage.setItem('einvite-v25-studio-policy',JSON.stringify({approvedOnly:true,lockBrandColors:true,lockTypography:true,requireAdaptiveTemplate:true,requirePrintPreflight:true}));window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}}}""")
  for name in BASE_JS+V25_JS:page.add_script_tag(path=str(ROOT/name));page.wait_for_timeout(80)
  versions=page.evaluate("""()=>({templates:EInviteAdaptiveTemplates.version,governance:EInviteStudioGovernance.version,print:EInvitePrintReadiness.version,bindings:EInviteTemplateBindings.version,conflicts:EInviteCommandRegistry.conflicts.length})""")
  assert versions=={'templates':25,'governance':25.1,'print':25.2,'bindings':25.3,'conflicts':0},versions
  # Apply a complete adaptive family.
  page.evaluate("()=>EInviteAdaptiveTemplates.apply('government-delegation')");page.wait_for_timeout(120)
  result=page.evaluate("""()=>({pages:EInviteEditorBridge.getState().designPages.length,adaptive:EInviteEditorBridge.getState().templateFamily.adaptive,bindings:EInviteTemplateBindings.inspect().length,roles:EInviteEditorBridge.getState().designPages.every(p=>p.templateRole&&p.responsiveLayout)})""")
  assert result['pages']==5 and result['adaptive'] and result['bindings']>=8 and result['roles'],result
  # Linked content refreshes from invitation fields.
  page.evaluate("""()=>{const d=EInviteEditorBridge.cloneState();d.fields.names='Updated Delegation Name';EInviteEditorBridge.replaceState(d,{history:false,reason:'test-fields'});return EInviteTemplateBindings.refresh()}""");page.wait_for_timeout(80)
  assert page.evaluate("""()=>Object.values(EInviteEditorBridge.getState().designPages[0].objects).some(o=>o.contentBinding==='fields.names'&&o.html==='Updated Delegation Name')""")
  # Detaching protects deliberate custom content.
  binding=page.evaluate("""()=>EInviteTemplateBindings.inspect().find(x=>x.binding==='fields.names').id""")
  page.evaluate("id=>EInviteTemplateBindings.detach(id,true)",binding)
  page.evaluate("""()=>{const d=EInviteEditorBridge.cloneState();d.fields.names='Second Name';EInviteEditorBridge.replaceState(d,{history:false,reason:'test-fields-2'});EInviteTemplateBindings.refresh()}""");page.wait_for_timeout(70)
  assert page.evaluate("id=>EInviteTemplateBindings.inspect().find(x=>x.id===id).detached",binding)
  # Apply an approved governed brand from the local fallback studio library.
  page.evaluate("()=>EInviteStudioGovernance.load()");page.wait_for_timeout(80);page.evaluate("()=>EInviteStudioGovernance.apply('studio-brand-1')");page.wait_for_timeout(350)
  governed=page.evaluate("""()=>({governed:EInviteEditorBridge.getState().eventBrand.governed,version:EInviteEditorBridge.getState().studioGovernance.resourceVersion,issues:EInviteStudioGovernance.compliance().map(x=>x.code)})""")
  assert governed['governed'] and governed['version']==3 and 'adaptive-template-required' not in governed['issues'],governed
  # Prepare a clean font preflight and mark it current.
  # The inline browser fixture has no HTTP origin for bundled font assets; model a ready FontFaceSet so this workflow test isolates preflight state and governance behavior.
  page.evaluate("""()=>{try{Object.defineProperty(document.fonts,'check',{configurable:true,value:()=>true})}catch{try{document.fonts.check=()=>true}catch{}}}""")
  page.evaluate("""()=>{const d=EInviteEditorBridge.cloneState();for(const map of [d.objects,...d.designPages.map(p=>p.objects)])for(const o of Object.values(map)){if(o.type==='image'&&!o.alt)o.alt='Invitation image'}d.fields.date=d.fields.date||'2027-01-01';EInviteEditorBridge.replaceState(d,{history:false,reason:'preflight-clean'})}""")
  preflight=page.evaluate("()=>EInvitePrintReadiness.inspect()");assert preflight['status'] in ('ready','review'),preflight
  page.evaluate("()=>EInvitePrintReadiness.markCurrent()");page.wait_for_timeout(60)
  final=page.evaluate("""()=>({status:EInviteEditorBridge.getState().printReadiness.status,compliance:EInviteStudioGovernance.compliance().map(x=>x.code)})""")
  assert final['status']=='ready' and 'print-preflight-required' not in final['compliance'],final
  # Non-mutating editor commands do not invalidate a current print record.
  page.evaluate("""()=>window.dispatchEvent(new CustomEvent('einvite:editor-command',{detail:{label:'Open content browser'}}))""");page.wait_for_timeout(180)
  assert page.evaluate("()=>EInviteEditorBridge.getState().printReadiness.status")=='ready'
  # Later edits automatically stale the current preflight.
  page.evaluate("""()=>EInviteEditorBridge.transact('Change after preflight',d=>{d.fields.venue='New venue'})""");page.wait_for_timeout(350)
  assert page.evaluate("()=>EInviteEditorBridge.getState().printReadiness.status")=='stale'
  # Core dialogs remain accessible.
  page.evaluate("()=>EInviteAdaptiveTemplates.open()");assert page.locator('#v25AdaptiveTemplates').is_visible();page.locator('#v25AdaptiveTemplates [data-close]').first.click()
  page.evaluate("()=>EInviteStudioGovernance.open()");page.wait_for_timeout(60);assert page.locator('.v25-governance-dialog').is_visible();page.locator('.v25-governance-dialog [data-close]').first.click()
  page.evaluate("()=>EInvitePrintReadiness.open()");assert page.locator('.v25-print-dialog').is_visible();page.locator('.v25-print-dialog [data-close]').first.click()
  page.evaluate("()=>EInviteTemplateBindings.open()");assert page.locator('.v25-binding-dialog').is_visible()
  assert not errors,errors
  browser.close()
 print('V25_TEMPLATE_GOVERNANCE_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
