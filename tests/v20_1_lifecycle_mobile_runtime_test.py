#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def build():
 spec=importlib.util.spec_from_file_location('inline',ROOT/'tests'/'inline_editor_runtime_test.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.build_inline_editor()
def main():
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_1_LIFECYCLE_MOBILE',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_1_LIFECYCLE_MOBILE',exc)
  page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=45000);page.wait_for_timeout(1500)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteEditorBridge&&window.TypographyLayoutService')
  page.evaluate("()=>EInviteEditorBridge.select(['title'])");page.wait_for_timeout(250)
  state=page.evaluate("""()=>{const bar=document.querySelector('#v20TypographyToolbar'),right=document.querySelector('.right'),closed=[...document.querySelectorAll('dialog:not([open]),[hidden]')];const focusable=closed.filter(x=>!x.inert&&[...x.querySelectorAll('button,input,select,textarea,a[href]')].some(e=>e.tabIndex>=0&&!e.disabled&&!e.closest('[inert]')));const obj=document.querySelector('[data-id=title]'),i=obj?.querySelector('i'),after=i?getComputedStyle(i,'::before'):null;return{docW:document.documentElement.scrollWidth,barVisible:bar&&!bar.hidden&&getComputedStyle(bar).display!=='none',rightVisible:right&&getComputedStyle(right).display!=='none',closedFocusable:focusable.length,handle:{w:i?getComputedStyle(i).width:'',h:i?getComputedStyle(i).height:'',afterW:after?.width||'',afterH:after?.height||''},canvas:document.querySelector('.canvas-viewport')?.getBoundingClientRect().height||0}}""")
  assert state['docW']<=391,state
  assert state['closedFocusable']==0 and not state['barVisible'],state
  assert state['handle']['w'] in ('9px','10px','12px','14px') or float(state['handle']['w'].replace('px','') or 0)<=14,state
  assert 'inset:-18px' in (ROOT/'typography-system-v20.css').read_text(),state
  assert state['canvas']>=250,state
  churn=page.evaluate("""()=>{let created=0,disconnected=0;const Old=window.ResizeObserver;window.ResizeObserver=class{constructor(){created++}observe(){}disconnect(){disconnected++}};const root=document.createElement('div');Object.assign(root.style,{width:'120px',height:'160px',position:'fixed',left:'-9999px'});document.body.append(root);const doc={typography:TypographyDocumentModel.defaultCatalog(),palette:{text:'#111',heading:'#222'},objects:{x:{type:'text',html:'Hello',textStyleId:'body',typographyModelVersion:1,fontPairing:'sans-modern',font:'noto-sans',fontSize:18,left:'0%',top:'0%',width:'100%',height:'80px'}},designPages:[]};const c1=EInviteTypographyRendererAdapters.renderThumbnail(root,doc,doc.objects,{width:390,height:844});c1.disconnect();root.replaceChildren();const c2=EInviteTypographyRendererAdapters.renderThumbnail(root,doc,doc.objects,{width:390,height:844});c2.disconnect();window.ResizeObserver=Old;root.remove();return{created,disconnected,children:root.childElementCount}}""")
  assert churn['created']==2 and churn['disconnected']==2,churn
  assert not errors,errors
  browser.close()
 print('V20_1_LIFECYCLE_MOBILE_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
