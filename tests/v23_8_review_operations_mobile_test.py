#!/usr/bin/env python3
from pathlib import Path
import sys
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
def main():
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.add_style_tag(path=str(ROOT/'review-v23.css'))
  page.evaluate("""()=>{window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>true};window.serverInvite={id:'mobile-review-v238'};const state={policy:{approvalGate:true,unresolvedCommentsGate:true,minApprovals:2},notifications:[{id:'n1',kind:'approval.requested',message:'Approval requested',actor_email:'owner@example.com',read_at:null,created_at:Date.now()}]};window.fetch=async(input,options={})=>{const path=new URL(String(input),'http://einvite.test').pathname,method=(options.method||'GET').toUpperCase(),body=options.body?JSON.parse(options.body):{};let data=[];if(path.endsWith('/comments'))data=[];else if(path.endsWith('/approvals'))data=[];else if(path.endsWith('/review-context'))data={role:'owner',canManage:true,canEdit:true,readiness:{ready:false,policy:state.policy,validApprovals:0,pendingApprovals:1,unresolvedComments:3,blockers:[{code:'approval_required',message:'2 more current approvals required'},{code:'unresolved_comments',message:'Resolve 3 open review comments'}]},notifications:state.notifications.map(x=>({...x,read:!!x.read_at})),unreadCount:state.notifications.filter(x=>!x.read_at).length};else if(path.endsWith('/review-notifications')&&method==='PUT'){state.notifications.forEach(x=>x.read_at=Date.now());data={updated:1,readAt:Date.now()}}else if(path.endsWith('/review-policy')&&method==='PUT'){state.policy={approvalGate:!!body.approvalGate,unresolvedCommentsGate:!!body.unresolvedCommentsGate,minApprovals:Number(body.minApprovals)};data={policy:state.policy,readiness:{ready:true,policy:state.policy,validApprovals:2,pendingApprovals:0,unresolvedComments:0,blockers:[]}}}return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}})}}""")
  page.add_script_tag(path=str(ROOT/'review-v23.js'));page.wait_for_timeout(180);page.evaluate("()=>EInviteReviewWorkflow.open('approvals')");page.wait_for_timeout(300)
  drawer=page.locator('#v23ReviewDrawer');assert drawer.is_visible();box=drawer.bounding_box();assert box['x']>=-1 and box['x']+box['width']<=391 and box['y']>=0 and box['y']+box['height']<=845,box
  assert page.locator('.v23-review-tabs button').count()==3
  assert page.locator('.v23-review-readiness.is-blocked').count()==1
  assert page.locator('[data-review-policy]').count()==1
  overflow=page.evaluate("()=>({doc:document.documentElement.scrollWidth-innerWidth,drawer:document.querySelector('#v23ReviewDrawer').scrollWidth-document.querySelector('#v23ReviewDrawer').clientWidth,readiness:document.querySelector('.v23-review-readiness').scrollWidth-document.querySelector('.v23-review-readiness').clientWidth})")
  assert overflow['doc']<=1 and overflow['drawer']<=1 and overflow['readiness']<=1,overflow
  page.locator('[data-tab="activity"]').click();page.wait_for_timeout(80);assert page.locator('.v23-review-notification.is-unread').count()==1
  page.locator('[data-mark-all-read]').click();page.wait_for_timeout(70);assert page.locator('.v23-review-notification.is-unread').count()==0
  footer=page.locator('#v23ReviewDrawer footer');assert footer.is_visible();fbox=footer.bounding_box();assert fbox['y']+fbox['height']<=845
  errors=[e for e in errors if 'setPointerCapture' not in e];assert not errors,errors
  browser.close()
 print('V23_8_REVIEW_OPERATIONS_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
