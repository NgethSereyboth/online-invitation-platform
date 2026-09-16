#!/usr/bin/env python3
from pathlib import Path
import sys
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
def main():
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000})
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.add_style_tag(path=str(ROOT/'review-v23.css'))
  page.evaluate("""()=>{window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>true};window.serverInvite={id:'review-operations-performance'};const now=Date.now(),comments=Array.from({length:180},(_,i)=>({id:'c'+i,email:'reviewer'+(i%8)+'@example.com',user_id:'u'+(i%8),object_id:'',page_id:'hero',parent_id:i%4===3?'c'+(i-1):'',anchor_x:(i%20)/20,anchor_y:((i*7)%20)/20,body:'Review comment '+i,resolved:i%5===0,created_at:now+i,updated_at:now+i,canDelete:true})),notifications=Array.from({length:100},(_,i)=>({id:'n'+i,kind:i%2?'comment.added':'approval.requested',target_id:'t'+i,message:'Review notification '+i,actor_email:'actor'+(i%7)+'@example.com',read_at:i%3?now:null,created_at:now+i}));window.fetch=async(input)=>{const path=new URL(String(input),'http://einvite.test').pathname;let data=[];if(path.endsWith('/comments'))data=comments;else if(path.endsWith('/approvals'))data=[];else if(path.endsWith('/review-context'))data={role:'owner',canManage:true,canEdit:true,readiness:{ready:false,policy:{approvalGate:true,unresolvedCommentsGate:true,minApprovals:2},validApprovals:1,pendingApprovals:1,unresolvedComments:108,blockers:[{code:'approval_required',message:'1 more approval required'},{code:'unresolved_comments',message:'Resolve open comments'}]},notifications:notifications.map(x=>({...x,read:!!x.read_at})),unreadCount:notifications.filter(x=>!x.read_at).length};return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}})}}""")
  page.add_script_tag(path=str(ROOT/'review-v23.js'));page.wait_for_timeout(100)
  comments_ms=page.evaluate("""async()=>{const start=performance.now();EInviteReviewWorkflow.open('comments');await EInviteReviewWorkflow.refresh();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-start}""")
  activity_ms=page.evaluate("""async()=>{const start=performance.now();EInviteReviewWorkflow.open('activity');await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-start}""")
  roots=page.locator('#v23ReviewDrawer [data-thread-id]').count();notices=page.locator('#v23ReviewDrawer .v23-review-notification').count()
  assert comments_ms<1300,comments_ms;assert activity_ms<500,activity_ms;assert roots>=100,roots;assert notices==100,notices
  assert page.locator('#v23ReviewDrawer').count()==1 and page.locator('#v23ReviewPins').count()==1
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  browser.close()
 print(f'V23_8_REVIEW_OPERATIONS_PERFORMANCE_TEST_PASSED comments_ms={comments_ms:.1f} activity_ms={activity_ms:.1f} roots={roots} notifications={notices}');return 0
if __name__=='__main__':sys.exit(main())
