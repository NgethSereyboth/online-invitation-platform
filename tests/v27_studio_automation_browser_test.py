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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(800)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.add_style_tag(path=str(ROOT/'studio-automation-v27.css'))
  page.evaluate("""()=>{
    window.__EInviteForceOnline=true;window.__bulkCount=0;
    window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}};window.uiConfirm=async()=>true;
    const active={id:'release-v27',name:'Official V27',status:'active',version:1,manifest:[]};
    window.__adoption={activeRelease:active,releaseIssues:[],counts:{current:1,outdated:1,unpinned:1},invitations:[
      {id:'i-current',slug:'current',title:'Current invitation',published:true,updatedAt:1,state:'current',releaseId:'release-v27',releaseVersion:1},
      {id:'i-old',slug:'old',title:'Outdated invitation',published:false,updatedAt:2,state:'outdated',releaseId:'old',releaseVersion:1},
      {id:'i-new',slug:'new',title:'Unpinned invitation',published:false,updatedAt:3,state:'unpinned',releaseId:null,releaseVersion:null}
    ]};
    window.__policy={enabled:false,intervalHours:24,retentionCount:7,includeMedia:true,lastRunAt:null,nextRunAt:null};window.__backups=[];
    window.fetch=async(path,options={})=>{path=String(path);let data={};const method=options.method||'GET';
      if(path.startsWith('/api/studio/adoption'))data=window.__adoption;
      else if(path.includes('/bulk-pin')&&method==='POST'){window.__bulkCount++;data={jobId:'job-1',updated:['i-old','i-new'],manual:[],skipped:[],count:2};window.__adoption.counts={current:3,outdated:0,unpinned:0};window.__adoption.invitations.forEach(x=>x.state='current')}
      else if(path.startsWith('/api/studio/releases'))data={releases:[active],canManage:true};
      else if(path==='/api/studio/backup-policy'&&method==='PUT'){window.__policy={...window.__policy,...JSON.parse(options.body||'{}'),updatedAt:10,nextRunAt:20};data={policy:window.__policy}}
      else if(path==='/api/studio/backup-policy')data={policy:window.__policy};
      else if(path==='/api/studio/backups/run'&&method==='POST'){const item={id:'backup-1',kind:'manual',status:'completed',createdAt:10,completedAt:11,sizeBytes:2048,downloadUrl:'/api/studio/backups/backup-1/download',detail:{}};window.__backups=[item];data=item}
      else if(path==='/api/studio/backups')data={backups:window.__backups};
      else if(path.startsWith('/api/studio/audit'))data={events:[{id:'a1',action:'studio.release_activated',actorEmail:'owner@example.com',targetType:'studio_release',targetId:'release-v27',metadata:{version:1},ipAddress:'127.0.0.1',createdAt:10,hash:'abc',previousHash:''}]};
      else if(path==='/api/studio/bulk-jobs')data={jobs:[]};
      return {ok:true,status:200,json:async()=>data,text:async()=>JSON.stringify(data),headers:new Headers()};
    };
  }""")
  page.add_script_tag(path=str(ROOT/'studio-automation-v27.js'));page.wait_for_timeout(200)
  info=page.evaluate("()=>({version:EInviteStudioAutomation.version,conflicts:EInviteCommandRegistry.conflicts.length})");assert info=={'version':27,'conflicts':0},info
  page.evaluate("()=>EInviteStudioAutomation.open('remediation')");page.wait_for_timeout(150);assert page.locator('.v27-automation-dialog').is_visible();assert page.locator('.v27-table>div').count()==3
  page.locator('[data-bulk-noncurrent]').click();page.wait_for_timeout(250);assert page.evaluate('()=>window.__bulkCount')==1
  page.locator('[data-tab="backups"]').click();page.wait_for_timeout(50);assert page.locator('.v27-backup-policy').is_visible();page.locator('[data-run-backup]').click();page.wait_for_timeout(250);assert page.locator('.v27-backup-list article').count()==1
  page.locator('[data-tab="audit"]').click();page.wait_for_timeout(50);assert page.locator('.v27-audit-list article').count()==1
  assert not errors,errors;browser.close()
 print('V27_STUDIO_AUTOMATION_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
