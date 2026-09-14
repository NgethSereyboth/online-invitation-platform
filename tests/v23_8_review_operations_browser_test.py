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
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(60)
  page.add_style_tag(path=str(ROOT/'review-v23.css'))
  page.evaluate("""()=>{
   window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>true};window.serverInvite={id:'review-operations-browser'};
   const comments=[],approvals=[];
   const notifications=[{id:'notice-1',kind:'comment.added',target_id:'comment-seed',message:'reviewer@example.com added a review comment',actor_email:'reviewer@example.com',read_at:null,created_at:Date.now()}];
   const state={policy:{approvalGate:false,unresolvedCommentsGate:false,minApprovals:1,updatedAt:0,updatedBy:''},revision:100,fingerprint:'fingerprint-100'};
   const readiness=()=>{const unresolved=comments.filter(x=>!x.parent_id&&!x.resolved).length,valid=approvals.filter(x=>x.status==='approved'&&x.document_revision===state.revision&&x.document_fingerprint===state.fingerprint).length,pending=approvals.filter(x=>x.status==='pending'&&x.document_revision===state.revision&&x.document_fingerprint===state.fingerprint).length,blockers=[];if(state.policy.approvalGate&&valid<state.policy.minApprovals)blockers.push({code:'approval_required',message:`${state.policy.minApprovals-valid} more current approval(s) required`});if(state.policy.unresolvedCommentsGate&&unresolved)blockers.push({code:'unresolved_comments',message:`Resolve ${unresolved} open review comment(s)`});return{ready:!blockers.length,policy:{...state.policy},revision:state.revision,fingerprint:state.fingerprint,validApprovals:valid,pendingApprovals:pending,unresolvedComments:unresolved,blockers}};
   window.__v238={comments,approvals,notifications,state,readiness};
   let seq=0;
   window.fetch=async(input,options={})=>{
    const path=new URL(String(input),'http://einvite.test').pathname,method=(options.method||'GET').toUpperCase(),body=options.body?JSON.parse(options.body):{};let data={},status=200;
    if(path.endsWith('/comments')&&method==='GET')data=comments;
    else if(path.endsWith('/comments')&&method==='POST'){const now=Date.now();data={id:'comment-'+(++seq),user_id:'u-reviewer',email:'reviewer@example.com',object_id:body.objectId||'',page_id:body.pageId||'hero',parent_id:body.parentId||'',anchor_x:body.anchorX??-1,anchor_y:body.anchorY??-1,body:body.body,resolved:false,created_at:now,updated_at:now,canDelete:true};comments.push(data);status=201}
    else if(path.includes('/comments/')&&method==='PUT'){const id=path.split('/').pop(),row=comments.find(x=>x.id===id);if(row)row.resolved=!!body.resolved;data={id,resolved:!!body.resolved}}
    else if(path.endsWith('/approvals')&&method==='GET')data=approvals.map(x=>({...x,stale:x.document_revision!==state.revision||x.document_fingerprint!==state.fingerprint}));
    else if(path.endsWith('/approvals')&&method==='POST'){const now=Date.now();data={id:'approval-'+(++seq),requester_email:'owner@example.com',requested_from:body.requestedFrom,status:'pending',note:body.note,document_revision:state.revision,document_fingerprint:state.fingerprint,summary:{title:'Browser',pages:1,objects:3},stale:false,created_at:now,updated_at:now};approvals.unshift(data);status=201}
    else if(path.includes('/approvals/')&&method==='PUT'){const id=path.split('/').pop(),row=approvals.find(x=>x.id===id);if(row)row.status=body.status;data={id,status:body.status,decided_by:'reviewer',decided_at:Date.now()}}
    else if(path.endsWith('/review-context')&&method==='GET')data={role:'owner',canManage:true,canEdit:true,readiness:readiness(),notifications:notifications.map(x=>({...x,read:!!x.read_at})),unreadCount:notifications.filter(x=>!x.read_at).length};
    else if(path.endsWith('/review-policy')&&method==='PUT'){state.policy={...state.policy,approvalGate:!!body.approvalGate,unresolvedCommentsGate:!!body.unresolvedCommentsGate,minApprovals:Number(body.minApprovals||1),updatedAt:Date.now(),updatedBy:'owner'};data={policy:state.policy,readiness:readiness()}}
    else if(path.endsWith('/review-notifications')&&method==='PUT'){const ids=new Set(body.ids||[]),now=Date.now();let updated=0;notifications.forEach(x=>{if(!x.read_at&&(body.all||ids.has(x.id))){x.read_at=now;updated++}});data={updated,readAt:now}}
    else{status=404;data={error:'Not found'}}
    return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}})
   }
  }""")
  page.add_script_tag(path=str(ROOT/'review-v23.js'));page.wait_for_timeout(350)
  assert page.evaluate("()=>EInviteReviewWorkflow.version==='23.8.3'")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  page.evaluate("()=>EInviteCommandRegistry.execute('review.open')");page.wait_for_timeout(120)
  assert page.locator('#v23ReviewDrawer').is_visible()
  assert page.locator('[data-tab="activity"] [data-activity-total]').inner_text()=='(1)'
  page.locator('[data-tab="activity"]').click();page.wait_for_timeout(60)
  assert page.locator('.v23-review-notification.is-unread').count()==1
  page.locator('[data-mark-all-read]').click();page.wait_for_timeout(90)
  assert page.evaluate("()=>EInviteReviewWorkflow.context.unreadCount")==0
  # Add an open comment, enable both gates, and verify readiness blockers.
  page.locator('[data-tab="comments"]').click();form=page.locator('[data-new-comment]');form.locator('textarea').fill('Resolve this before publishing.');form.locator('button[type=submit]').click();page.wait_for_timeout(100)
  page.locator('[data-tab="approvals"]').click();page.wait_for_timeout(80)
  policy=page.locator('[data-review-policy]');policy.locator('input[name=approvalGate]').check();policy.locator('input[name=unresolvedCommentsGate]').check();policy.locator('select[name=minApprovals]').select_option('1');policy.locator('button[type=submit]').click();page.wait_for_timeout(120)
  assert page.locator('.v23-review-readiness.is-blocked').count()==1
  text=page.locator('.v23-review-readiness').inner_text().lower();assert 'approval' in text and 'resolve' in text,text
  # Resolve the comment, request/approve the current revision, and become publish ready.
  page.locator('[data-tab="comments"]').click();page.locator('[data-resolve-comment]').click();page.wait_for_timeout(80)
  page.locator('[data-tab="approvals"]').click();request=page.locator('[data-request-approval]');request.locator('input[name=requestedFrom]').fill('reviewer@example.com');request.locator('textarea[name=note]').fill('Please approve.');request.locator('button[type=submit]').click();page.wait_for_timeout(100)
  page.locator('[data-decide-approval="approved"]').click();page.wait_for_timeout(80)
  page.evaluate("()=>EInviteReviewWorkflow.refresh()");page.wait_for_timeout(100)
  assert page.locator('.v23-review-readiness.is-ready').count()==1
  assert page.evaluate("()=>EInviteReviewWorkflow.context.readiness.ready")
  # A blocked publish response can route directly to the readiness surface.
  page.evaluate("()=>{__v238.state.policy={...__v238.state.policy,approvalGate:true,unresolvedCommentsGate:false,minApprovals:2};EInviteReviewWorkflow.showPublishReadiness({ready:false,policy:{approvalGate:true,unresolvedCommentsGate:false,minApprovals:2},validApprovals:1,pendingApprovals:0,unresolvedComments:0,blockers:[{code:'approval_required',message:'1 more current approval required'}]})}");page.wait_for_timeout(120)
  assert page.locator('[data-panel="approvals"]:not([hidden])').count()==1
  assert '1 more current approval' in page.locator('.v23-review-readiness').inner_text().lower()
  assert page.locator('#v23ReviewDrawer').count()==1
  assert not errors,errors
  browser.close()
 print('V23_8_REVIEW_OPERATIONS_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
