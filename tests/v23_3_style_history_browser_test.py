#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  for css in ['page-experience-v22.css','professional-workflow-v23.css','navigation-history-v23.css','style-history-v23.css']:page.add_style_tag(path=str(ROOT/css))
  for js in ['page-experience-v22.js','professional-workflow-v23.js','navigation-history-v23.js','style-history-v23.js']:page.add_script_tag(path=str(ROOT/js))
  page.wait_for_timeout(450)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  assert page.evaluate("()=>EInviteStyleHistory?.version===23.3")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  # Seed one visual page with text and shape content.
  page.evaluate("""()=>{const d=EInviteEditorBridge.getState();d.palette={background:'#fff8f2',surface:'#ffffff',text:'#342c26',heading:'#9d4555'};d.accent='#9d4555';d.designPages=[{id:'style-page',name:'Style Page',enabled:true,backgroundMode:'color',background:'#fff8f2',objects:{title:{id:'title',type:'text',html:'Ceremony',left:'10%',top:'12%',width:'80%',height:'14%',fontSize:52,textStyleId:'display',zIndex:2},shape:{id:'shape',type:'shape',fill:'#cccccc',left:'20%',top:'48%',width:'60%',height:'20%',zIndex:1}}}];EInviteEditorSchema.syncLegacy(d);EInviteEditorBridge.render();EInvitePageExperience?.render?.({force:true})}""")
  page.wait_for_timeout(220)
  page.evaluate("()=>document.querySelector('[data-page-dock-thumb-id=style-page]')?.click()")
  page.wait_for_timeout(220)
  # Save the current design as a custom kit.
  kit=page.evaluate("()=>EInviteStyleHistory.kits.saveCurrent('Wedding Brand')")
  assert kit['name']=='Wedding Brand'
  assert page.evaluate("()=>EInviteStyleHistory.kits.list().some(k=>k.name==='Wedding Brand')")
  # Change the document, preview the kit, cancel, then apply to the page.
  page.evaluate("()=>EInviteEditorBridge.transact('Change palette',d=>{d.palette.background='#101820';d.accent='#ffcc00';d.designPages[0].background='#101820'},{capture:false})")
  changed=page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].background")
  page.evaluate("id=>EInviteStyleHistory.kits.preview(id,'page')",kit['id'])
  assert page.evaluate("()=>document.body.classList.contains('v23-style-previewing')")
  assert page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].background")!='#101820'
  page.evaluate("()=>EInviteStyleHistory.kits.cancel()")
  assert page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].background")==changed
  page.evaluate("id=>EInviteStyleHistory.kits.apply(id,'page')",kit['id'])
  page.wait_for_timeout(180)
  assert page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].background")=='#fff8f2'
  # Selection scope updates only selected objects.
  page.evaluate("()=>EInviteEditorBridge.setSelectionState(['shape'])")
  page.evaluate("id=>EInviteStyleHistory.kits.apply(id,'selection')",kit['id'])
  page.wait_for_timeout(120)
  assert page.evaluate("()=>EInviteEditorBridge.getState().designPages[0].objects.shape.fillColor||EInviteEditorBridge.getState().designPages[0].objects.shape.backgroundColor")=='#9d4555'
  # Create visual checkpoint, verify thumbnail and comparison data.
  page.evaluate("()=>EInviteNavigationHistory.checkpoints.create('Styled draft')")
  page.wait_for_timeout(180)
  record=page.evaluate("()=>EInviteNavigationHistory.checkpoints.list().then(x=>x[0])")
  assert record.get('thumbnail','').startswith('data:image/svg+xml')
  page.evaluate("()=>EInviteEditorBridge.transact('Add object',d=>d.designPages[0].objects.extra={id:'extra',type:'text',html:'New',left:'10%',top:'80%',width:'20%',height:'8%',zIndex:3},{capture:false})")
  diff=page.evaluate("r=>EInviteStyleHistory.history.compare(EInviteEditorBridge.getState(),r.document)",record)
  assert diff['objectDelta']==1,diff
  page.evaluate("r=>EInviteStyleHistory.history.openCompare(r)",record)
  assert page.locator('#v23HistoryCompareDialog').is_visible()
  page.locator('#v23HistoryCompareDialog [data-close]').click()
  # The style dialog and enhanced history rows are accessible and unique.
  page.evaluate("()=>EInviteStyleHistory.kits.open()")
  assert page.locator('#v23StyleKitDialog').is_visible()
  assert page.locator('.v23-style-kit-card').count()>=4
  page.locator('#v23StyleKitDialog [data-close]').click()
  page.evaluate("()=>EInviteNavigationHistory.checkpoints.open()")
  page.wait_for_timeout(650)
  assert page.locator('.v23-checkpoint-thumb').count()>=1
  assert not errors,errors
  browser.close()
 print('V23_3_STYLE_HISTORY_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
