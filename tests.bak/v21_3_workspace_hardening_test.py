#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,time
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 spec=importlib.util.spec_from_file_location('inline_v213',ROOT/'tests'/'inline_editor_runtime_test.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V21_3_WORKSPACE_HARDENING',exc)
 html=build()
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V21_3_WORKSPACE_HARDENING',exc)
  page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(60000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(html,wait_until='load',timeout=60000);page.wait_for_function('()=>window.EInviteWorkspaceV21&&window.RichTextEditing&&window.EInviteEditorBridge');page.wait_for_timeout(800)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  roles=page.evaluate("""()=>({left:document.querySelector('aside.left')?.dataset.workspaceOwner,right:document.querySelector('aside.right')?.dataset.workspaceOwner,bar:(document.querySelector('#v20TypographyToolbar')||document.querySelector('.ei-context-toolbar'))?.dataset.workspaceOwner,life:EInviteWorkspaceV21.lifecycle(),zoom:EInviteWorkspaceV21.snapshot().zoom,key:EInviteWorkspaceV21.key()})""")
  assert roles['left']=='creation-library' and roles['right']=='advanced-inspector' and roles['bar']=='contextual-properties',roles
  assert roles['life']=={'observerCount':1,'active':True} and roles['key'].endswith(':desktop'),roles
  # View state is document/device scoped and restorable.
  page.select_option('#zoomLevel','1.25');page.locator('#canvasViewport').evaluate("e=>{e.scrollLeft=31;e.scrollTop=47;e.dispatchEvent(new Event('scroll'))}");page.wait_for_timeout(220);saved=page.evaluate("()=>JSON.parse(localStorage.getItem(EInviteWorkspaceV21.key()))")
  assert abs(saved['zoom']-1.25)<.01 and saved['top']>=0,saved
  page.select_option('#zoomLevel','0.5');page.evaluate("()=>{const v=document.querySelector('#canvasViewport');v.scrollLeft=0;v.scrollTop=0;EInviteWorkspaceV21.restore()}");page.wait_for_timeout(180);restored=page.evaluate("()=>EInviteWorkspaceV21.snapshot()")
  assert abs(restored['zoom']-1.25)<.01,restored
  # Realistic large structured document remains interactive under bounded latency.
  metrics=page.evaluate("""()=>{
    const start=performance.now();
    EInviteEditorBridge.transact('Create large rich-text document',doc=>{
      for(let i=0;i<180;i++){
        const id=`large-${i}`,base=structuredClone(doc.objects.details),km=i%3===0;
        const richText={version:1,entities:{},paragraphs:[{id:`p-${i}`,paragraphStyleId:'body',locale:km?'km':'en',direction:'ltr',overrides:{},list:{type:'none',level:0,start:1,marker:'disc'},tabStops:[],runs:[{id:`r-${i}`,text:km?`កម្មវិធី ${i}`:`Invitation item ${i}`,locale:km?'km':'en',marks:i%5===0?{strong:true}:{}}]}]};
        const object={...base,id,layerName:`Large item ${i}`,left:`${5+(i%10)*9}%`,top:`${5+(i%18)*5}%`,width:'18%',height:'42px',zIndex:200+i,richTextModelVersion:1,richText};
        object.html=RichTextDocumentModel.exportLegacyHtml(richText);object.text=RichTextDocumentModel.exportPlainText(richText);doc.objects[id]=object;
      }
    });
    const render=performance.now()-start,s=performance.now();EInviteEditorBridge.select(['large-179']);
    return{render,selection:performance.now()-s,count:document.querySelectorAll('#stage .object').length,heap:performance.memory?.usedJSHeapSize||0,life:EInviteWorkspaceV21.lifecycle()};
  }""")
  assert metrics['count']>=184 and metrics['render']<5000 and metrics['selection']<750,metrics
  if metrics['heap']:assert metrics['heap']<400_000_000,metrics
  assert metrics['life']['observerCount']==1,metrics
  for _ in range(8):page.evaluate("()=>EInviteWorkspaceV21.restore()")
  assert page.evaluate("()=>EInviteWorkspaceV21.lifecycle().observerCount")==1
  assert not errors,errors
  # Mobile: one compact selection bar, one drill-in panel, inert closed surfaces, small visuals/44px targets.
  mobile=browser.new_page(viewport={'width':390,'height':844});mobile.set_default_timeout(60000);mobile_errors=[]
  mobile.on('pageerror',lambda e:mobile_errors.append(str(e)));mobile.on('console',lambda m:mobile_errors.append(m.text) if m.type=='error' else None)
  mobile.set_content(html,wait_until='load',timeout=60000);mobile.wait_for_function('()=>window.EInviteWorkspaceV21&&window.EInviteEditorBridge');mobile.wait_for_timeout(900)
  if mobile.locator('#finalTourDismiss').count() and mobile.locator('#finalTourDismiss').is_visible():mobile.locator('#finalTourDismiss').click()
  mobile.evaluate("()=>EInviteEditorBridge.select(['title'])");mobile.wait_for_timeout(250)
  initial=mobile.evaluate("""()=>({left:{hidden:document.querySelector('aside.left')?.getAttribute('aria-hidden'),inert:document.querySelector('aside.left')?.inert},right:{hidden:document.querySelector('aside.right')?.getAttribute('aria-hidden'),inert:document.querySelector('aside.right')?.inert},selection:getComputedStyle(document.querySelector('#peMobileContextBar')).display,desktop:getComputedStyle(document.querySelector('#v20TypographyToolbar')).display,canvas:document.querySelector('#canvasViewport').getBoundingClientRect().height,key:EInviteWorkspaceV21.key()})""")
  assert initial['left']=={'hidden':'true','inert':True} and initial['right']=={'hidden':'true','inert':True},initial
  assert initial['selection']!='none' and initial['desktop']=='none' and initial['canvas']>300 and initial['key'].endswith(':mobile'),initial
  handles=mobile.evaluate("""()=>[...document.querySelectorAll('.pe-selection-box .pe-handle,.pe-selection-box .pe-rotate')].map(e=>{const r=e.getBoundingClientRect(),b=getComputedStyle(e,'::before');return{hitW:r.width,hitH:r.height,visualW:parseFloat(b.width)||0,visualH:parseFloat(b.height)||0}})""")
  assert handles and all(h['hitW']>=44 and h['hitH']>=44 and 0<h['visualW']<=16 and 0<h['visualH']<=16 for h in handles),handles
  mobile.locator('#mobileQuickMode').click();mobile.wait_for_timeout(120);opened=mobile.evaluate("""()=>({left:document.querySelector('aside.left').inert,right:document.querySelector('aside.right').inert,rightHidden:document.querySelector('aside.right').getAttribute('aria-hidden'),sheet:document.querySelector('aside.right').getBoundingClientRect().height})""")
  assert opened['left'] and not opened['right'] and opened['rightHidden']=='false' and opened['sheet']<700,opened
  mobile.locator('#mobileCanvasMode').click();mobile.wait_for_timeout(100);assert mobile.evaluate("()=>document.querySelector('aside.right').inert") is True
  assert not mobile_errors,mobile_errors
  page.evaluate("()=>dispatchEvent(new PageTransitionEvent('pagehide'))");page.wait_for_timeout(30);assert page.evaluate("()=>EInviteWorkspaceV21.lifecycle()")=={'observerCount':0,'active':False}
  mobile.close();page.close();browser.close()
 print('V21_3_WORKSPACE_HARDENING_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
