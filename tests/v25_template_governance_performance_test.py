#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
BASE_CSS=['direct-manipulation-v24.css','content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']
BASE_JS=['direct-manipulation-v24.js','content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
CSS=BASE_CSS+['adaptive-templates-v25.css','studio-governance-v25.css','print-readiness-v25.css','template-bindings-v25.css']
JS=BASE_JS+['adaptive-templates-v25.js','studio-governance-v25.js','print-readiness-v25.js','template-bindings-v25.js']
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(850)
  for name in CSS:page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{const list=Array.from({length:80},(_,i)=>({id:'resource-'+i,kind:i%3===0?'brand':i%3===1?'template-family':'component',name:'Studio Resource '+i,category:'Performance',payload:i%3===0?{primary:'#183a64',accent:'#b18a3b',background:'#f7f8fb',surface:'#fff',text:'#18202d',headingPair:'serif-formal',bodyPair:'sans-modern'}:{},governance:{locked:i%2===0,allowedOverrides:['content','media']},status:i%4===0?'approved':'draft',version:1,createdAt:Date.now()-i,updatedAt:Date.now()-i}));localStorage.setItem('einvite-v25-studio-resources',JSON.stringify(list));window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}};try{Object.defineProperty(document.fonts,'check',{configurable:true,value:()=>true})}catch{}}""")
  for name in JS:page.add_script_tag(path=str(ROOT/name));page.wait_for_timeout(35)
  metrics=page.evaluate("""async()=>{
   const t0=performance.now();EInviteAdaptiveTemplates.apply('khmer-royal-wedding');const applyMs=performance.now()-t0;
   const d=EInviteEditorBridge.cloneState();let z=100;for(const pg of d.designPages){for(let i=0;i<45;i++){const id=`stress-${pg.id}-${i}`;pg.objects[id]={type:'text',html:`ខ្មែរ Invitation ${i}`,left:`${5+(i%10)*9}%`,top:`${8+(i%12)*7}%`,width:'18%',height:'44px',fontPairing:i%2?'khmer-ceremonial':'sans-modern',fontSize:16,zIndex:z++,visible:true,locked:false}}}EInviteEditorBridge.replaceState(d,{history:false,reason:'v25-performance-seed'});
   const b0=performance.now();let total=0;for(let i=0;i<250;i++)total+=EInviteTemplateBindings.inspect().length;const bindingMs=performance.now()-b0;
   const g0=performance.now();await EInviteStudioGovernance.load();EInviteStudioGovernance.open();await new Promise(r=>setTimeout(r,120));const governanceMs=performance.now()-g0;
   const p0=performance.now();const report=await EInvitePrintReadiness.inspect();const preflightMs=performance.now()-p0;
   return{applyMs,bindingMs,governanceMs,preflightMs,total,resources:EInviteStudioGovernance.list().length,fonts:report.fonts.length,issues:report.issues.length,conflicts:EInviteCommandRegistry.conflicts.length};
  }""")
  assert metrics['applyMs']<1000,metrics
  assert metrics['bindingMs']<1000,metrics
  assert metrics['governanceMs']<1500,metrics
  assert metrics['preflightMs']<2500,metrics
  assert metrics['resources']==80 and metrics['total']>0 and metrics['conflicts']==0,metrics
  assert page.locator('.v25-resource-card').count()<=80
  assert not errors,errors
  browser.close()
 print(f"V25_TEMPLATE_GOVERNANCE_PERFORMANCE_TEST_PASSED apply={metrics['applyMs']:.1f}ms bindings={metrics['bindingMs']:.1f}ms governance={metrics['governanceMs']:.1f}ms preflight={metrics['preflightMs']:.1f}ms")
 return 0
if __name__=='__main__':sys.exit(main())
