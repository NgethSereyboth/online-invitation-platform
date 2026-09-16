#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
CSS=['content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']
JS=['content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(900)
  for name in CSS:page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{window.EInviteReviewWorkflow={comments:Array.from({length:180},(_,i)=>({id:'c'+i,parentId:'',pageId:'hero',objectId:'',body:'Review item '+i,author:'reviewer@example.com',resolved:i%3===0,createdAt:Date.now()-i*1000})),approvals:[],context:{reviewers:[],readiness:{ready:true,blockers:[]}},refresh:async()=>true,open:()=>true};window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}}}""")
  for name in JS:page.add_script_tag(path=str(ROOT/name));page.wait_for_timeout(50)
  metrics=page.evaluate("""()=>{
   const next=EInviteEditorBridge.cloneState();next.objects={};for(let i=0;i<360;i++){const image=i%5===0;next.objects['perf-'+i]={type:image?'image':'text',src:image?"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20'%3E%3Crect width='20' height='20' fill='%23ddd'/%3E%3C/svg%3E":'',alt:image&&i%10?'Decorative invitation image':'',html:image?'':'Guest information '+i,left:(i%12*8)+'%',top:(Math.floor(i/12)%20*5)+'%',width:'7%',height:'40px',fontSize:14,zIndex:i+1,visible:true,locked:false};}EInviteEditorBridge.replaceState(next,{history:false});
   const q0=performance.now();const issues=EInviteExportQuality.inspect();const qualityMs=performance.now()-q0;
   const ids=Object.keys(next.objects).slice(0,100);EInviteEditorBridge.select(ids);const l0=performance.now();EInviteSmartLayout.stack('vertical',{gap:4,align:'center'});const layoutMs=performance.now()-l0;
   return{qualityMs,layoutMs,issues:issues.length,commands:EInviteCommandRegistry.list({includeHidden:true}).length,conflicts:EInviteCommandRegistry.conflicts.length};
  }""")
  assert metrics['qualityMs']<800,metrics
  assert metrics['layoutMs']<900,metrics
  assert metrics['issues']>0 and metrics['conflicts']==0,metrics
  page.evaluate("()=>EInviteContentBrowser.open('all')");page.wait_for_timeout(180)
  cards=page.locator('#v24ContentBrowser [data-item]').count();assert cards<=240,cards
  assert not errors,errors
  browser.close()
 print(f"V24_CANVA_EXPERIENCE_PERFORMANCE_TEST_PASSED quality={metrics['qualityMs']:.1f}ms layout={metrics['layoutMs']:.1f}ms cards={cards}");return 0
if __name__=='__main__':sys.exit(main())
