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
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  for js in ['page-experience-v22.js','professional-workflow-v23.js','navigation-history-v23.js','style-history-v23.js']:page.add_script_tag(path=str(ROOT/js))
  page.wait_for_timeout(350)
  result=page.evaluate("""async()=>{const d=EInviteEditorBridge.getState();d.designPages=[];for(let p=0;p<120;p++){const objects={};for(let i=0;i<20;i++)objects[`o-${p}-${i}`]={id:`o-${p}-${i}`,type:i%3===0?'text':'shape',html:`Text ${i}`,fontSize:16+i%4*4,textStyleId:i%3===0?'body':'caption',fill:'#778899',left:`${i%10*8}%`,top:`${Math.floor(i/10)*25}%`,width:'7%',height:'12%',zIndex:i};d.designPages.push({id:`p-${p}`,name:`Page ${p+1}`,enabled:true,background:'#fff8f2',objects})}EInviteEditorSchema.syncLegacy(d);EInviteEditorBridge.render();const kit=EInviteStyleHistory.kits.extract(d,'Benchmark');let t=performance.now();const thumb=EInviteStyleHistory.history.thumbnailForDocument(d);const thumbnailMs=performance.now()-t;t=performance.now();const summary=EInviteStyleHistory.history.summary(d);const summaryMs=performance.now()-t;t=performance.now();for(let i=0;i<100;i++)EInviteStyleHistory.history.compare(d,d);const compare100Ms=performance.now()-t;return{thumbnailMs,summaryMs,compare100Ms,thumbBytes:thumb.length,summary,kitBytes:new Blob([JSON.stringify(kit)]).size}}""")
  assert result['thumbnailMs']<40,result
  assert result['summaryMs']<50,result
  assert result['compare100Ms']<250,result
  assert result['thumbBytes']<30000,result
  assert result['kitBytes']<300000,result
  assert result['summary']['pages']==120,result
  browser.close()
 print('V23_3_STYLE_HISTORY_PERFORMANCE_TEST_PASSED',result);return 0
if __name__=='__main__':sys.exit(main())
