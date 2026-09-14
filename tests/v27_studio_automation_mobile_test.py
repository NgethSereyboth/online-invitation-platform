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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(700)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.add_style_tag(path=str(ROOT/'studio-automation-v27.css'))
  page.evaluate("""()=>{window.__EInviteForceOnline=true;window.EInviteFeedback={toast:()=>{}};window.uiConfirm=async()=>true;const active={id:'r',name:'Release',status:'active',version:1,manifest:[]};window.fetch=async path=>{path=String(path);let data=path.includes('adoption')?{activeRelease:active,counts:{current:1,outdated:1,unpinned:1},releaseIssues:[],invitations:[{id:'1',slug:'one',title:'One',published:true,updatedAt:1,state:'current'},{id:'2',slug:'two',title:'Two',published:false,updatedAt:1,state:'outdated'},{id:'3',slug:'three',title:'Three',published:false,updatedAt:1,state:'unpinned'}]}:path.includes('/releases')?{releases:[active],canManage:true}:path.includes('backup-policy')?{policy:{enabled:true,intervalHours:24,retentionCount:7,includeMedia:true}}:path.endsWith('/backups')?{backups:[]}:path.includes('/audit')?{events:[]}:path.includes('bulk-jobs')?{jobs:[]}:{};return{ok:true,status:200,json:async()=>data,text:async()=>JSON.stringify(data),headers:new Headers()}}}""")
  page.add_script_tag(path=str(ROOT/'studio-automation-v27.js'));page.wait_for_timeout(150);page.evaluate("()=>EInviteStudioAutomation.open('remediation')");page.wait_for_timeout(150)
  box=page.locator('.v27-automation-dialog').bounding_box();assert box and box['width']<=391 and box['height']<=845,box
  overflow=page.evaluate("()=>document.documentElement.scrollWidth>document.documentElement.clientWidth");assert not overflow
  page.locator('[data-tab="backups"]').click();page.wait_for_timeout(50);assert page.locator('.v27-form').is_visible()
  page.locator('[data-tab="audit"]').click();page.wait_for_timeout(50);assert page.locator('.v27-audit-tools').is_visible()
  assert not errors,errors;browser.close()
 print('V27_STUDIO_AUTOMATION_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
