#!/usr/bin/env python3
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000})
 page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
 for css in ['page-experience-v22.css','navigation-history-v23.css']:page.add_style_tag(path=str(ROOT/css))
 for js in ['page-experience-v22.js','navigation-history-v23.js']:page.add_script_tag(path=str(ROOT/js))
 page.wait_for_timeout(250)
 result=page.evaluate("""async()=>{
  const d=EInviteEditorBridge.getState();d.designPages=Array.from({length:120},(_,i)=>({id:`perf-${i}`,name:`Page ${i+1}`,enabled:true,objects:{[`o-${i}`]:{type:'text',text:`Page ${i+1}`,left:'10%',top:'10%',width:'30%',height:'10%',zIndex:1}}}));EInviteEditorSchema.syncLegacy(d);EInviteEditorBridge.render();EInvitePageExperience.render({force:true});await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
  const t0=performance.now();for(let i=0;i<300;i++)EInviteNavigationHistory.pages.setView(['list','thumbs','grid'][i%3]);const viewMs=performance.now()-t0;
  document.querySelector('[data-page-id="perf-0"]')?.click();const t1=performance.now();await EInviteNavigationHistory.pages.copy();await EInviteNavigationHistory.pages.paste();const transferMs=performance.now()-t1;
  const t2=performance.now();await EInviteNavigationHistory.checkpoints.create('Performance checkpoint');const checkpointMs=performance.now()-t2;
  return{viewMs,transferMs,checkpointMs,cards:document.querySelectorAll('.v22-page-card').length,pages:EInviteEditorBridge.getState().designPages.length};
 }""")
 assert result['cards']>=120 and result['pages']==121,result
 assert result['viewMs']<250,result
 assert result['transferMs']<500,result
 assert result['checkpointMs']<500,result
 print('V23_2_NAVIGATION_HISTORY_PERFORMANCE_RESULT',result)
 browser.close()
