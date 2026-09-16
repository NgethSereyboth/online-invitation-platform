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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(700)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.add_style_tag(path=str(ROOT/'studio-automation-v27.css'))
  page.evaluate("""()=>{window.__EInviteForceOnline=true;window.EInviteFeedback={toast:()=>{}};const active={id:'r',name:'Large release',status:'active',version:1,manifest:[]};const invitations=Array.from({length:500},(_,i)=>({id:'i'+i,slug:'invite-'+i,title:'Invitation '+i,published:i%2===0,updatedAt:Date.now()-i*1000,state:i%3===0?'current':i%3===1?'outdated':'unpinned'}));const events=Array.from({length:200},(_,i)=>({id:'a'+i,action:'studio.event.'+i,actorEmail:'actor@example.com',targetType:'invitation',targetId:'i'+i,metadata:{index:i},ipAddress:'127.0.0.1',createdAt:Date.now()-i*1000,hash:'h'+i,previousHash:'h'+(i+1)}));const backups=Array.from({length:50},(_,i)=>({id:'b'+i,kind:i%2?'manual':'scheduled',status:'completed',createdAt:Date.now()-i*10000,completedAt:Date.now()-i*10000+100,sizeBytes:1000+i,downloadUrl:'/download/'+i,detail:{}}));window.fetch=async path=>{path=String(path);let data=path.includes('adoption')?{activeRelease:active,counts:{current:167,outdated:167,unpinned:166},releaseIssues:[],invitations}:path.includes('/releases')?{releases:[active],canManage:true}:path.includes('backup-policy')?{policy:{enabled:true,intervalHours:24,retentionCount:7,includeMedia:true}}:path.endsWith('/backups')?{backups}:path.includes('/audit')?{events}:path.includes('bulk-jobs')?{jobs:[]}:{};return{ok:true,status:200,json:async()=>data,text:async()=>JSON.stringify(data),headers:new Headers()}}}""")
  page.add_script_tag(path=str(ROOT/'studio-automation-v27.js'));page.wait_for_timeout(100)
  elapsed=page.evaluate("""async()=>{const t=performance.now();await EInviteStudioAutomation.open('remediation');await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-t}""")
  assert elapsed<1200,elapsed;assert page.locator('.v27-table>div').count()==500
  page.locator('[data-tab="audit"]').click();page.wait_for_timeout(80);assert page.locator('.v27-audit-list article').count()==200
  page.locator('[data-tab="backups"]').click();page.wait_for_timeout(80);assert page.locator('.v27-backup-list article').count()==50
  assert page.locator('.v27-automation-dialog').count()==1
  print(f'V27_STUDIO_AUTOMATION_PERFORMANCE_TEST_PASSED {elapsed:.1f}ms');browser.close();return 0
if __name__=='__main__':sys.exit(main())
