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
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  for name in ('asset-workflow-v23.css','photo-workflow-v23.css','photo-style-library-v23.css','review-v23.css'):page.add_style_tag(path=str(ROOT/name))
  page.evaluate("""()=>{
   window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>true};window.serverInvite={id:'review-browser'};
   const comments=[],approvals=[];let seq=0,revision=100,fingerprint='fingerprint-100';
   window.__reviewMock={comments,approvals,setStale(){revision++;fingerprint='fingerprint-'+revision}};
   window.fetch=async(input,options={})=>{
    const url=new URL(String(input),'http://einvite.test'),path=url.pathname,method=(options.method||'GET').toUpperCase();
    const body=options.body?JSON.parse(options.body):{};let data={},status=200;
    if(path.endsWith('/comments')&&method==='GET')data=comments;
    else if(path.endsWith('/comments')&&method==='POST'){
     const parent=body.parentId?comments.find(x=>x.id===body.parentId):null,id='comment-'+(++seq),now=Date.now();
     data={id,invitation_id:'review-browser',user_id:'user-1',email:'reviewer@example.com',object_id:parent?.object_id||body.objectId||'',page_id:parent?.page_id||body.pageId||'hero',parent_id:parent?(parent.parent_id||parent.id):'',anchor_x:parent?.anchor_x??body.anchorX??-1,anchor_y:parent?.anchor_y??body.anchorY??-1,body:body.body,resolved:false,created_at:now,updated_at:now,canDelete:true};comments.push(data);status=201;
    }else if(path.includes('/comments/')&&method==='PUT'){
     const id=decodeURIComponent(path.split('/').pop()),row=comments.find(x=>x.id===id),root=row?.parent_id?comments.find(x=>x.id===row.parent_id):row;if(root)root.resolved=!!body.resolved;data={id:root?.id,resolved:!!body.resolved};
    }else if(path.includes('/comments/')&&method==='DELETE'){
     const id=decodeURIComponent(path.split('/').pop()),row=comments.find(x=>x.id===id),root=row?.parent_id||id;for(let i=comments.length-1;i>=0;i--)if(comments[i].id===id||(!row?.parent_id&&comments[i].parent_id===root))comments.splice(i,1);data={deleted:true};
    }else if(path.endsWith('/approvals')&&method==='GET')data=approvals.map(x=>({...x,stale:x.document_revision!==revision||x.document_fingerprint!==fingerprint}));
    else if(path.endsWith('/approvals')&&method==='POST'){
     const now=Date.now();data={id:'approval-'+(++seq),requester_email:'owner@example.com',requested_from:body.requestedFrom,status:'pending',note:body.note,document_revision:revision,document_fingerprint:fingerprint,summary:{title:'Browser Review',pages:1,objects:4},stale:false,created_at:now,updated_at:now};approvals.unshift(data);status=201;
    }else if(path.includes('/approvals/')&&method==='PUT'){
     const id=decodeURIComponent(path.split('/').pop()),row=approvals.find(x=>x.id===id);if(row){row.status=body.status;row.note=body.note||row.note;row.updated_at=Date.now();row.decided_at=Date.now()}data={id,status:body.status,decided_by:'user-1',decided_at:Date.now()};
    }else if(path.endsWith('/review-context'))data={role:'owner',canManage:true,canEdit:true,readiness:{ready:true,policy:{approvalGate:false,unresolvedCommentsGate:false,minApprovals:1},validApprovals:0,pendingApprovals:0,unresolvedComments:comments.filter(x=>!x.parent_id&&!x.resolved).length,blockers:[]},notifications:[],unreadCount:0};
    else{status=404;data={error:'Not found'}}
    return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
   };
  }""")
  for name in ('asset-workflow-v23.js','photo-workflow-v23.js','photo-style-library-v23.js','review-v23.js'):page.add_script_tag(path=str(ROOT/name))
  page.wait_for_timeout(450)
  assert page.evaluate("()=>EInviteReviewWorkflow?.version==='23.8.3'")
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  assert page.locator('.studio-statusbar [data-command-id="review.open"]').count()==1
  page.evaluate("()=>EInviteCommandRegistry.execute('review.open')");page.wait_for_timeout(120)
  assert page.locator('#v23ReviewDrawer').is_visible()
  first=page.locator('#stage .object').first;first_id=first.get_attribute('data-id');assert first_id
  page.evaluate("id=>{const node=document.querySelector(`#stage .object[data-id=\"${CSS.escape(id)}\"]`);clearSelection();setSelection([node])}",first_id)
  page.wait_for_timeout(100)
  compose=page.locator('#v23ReviewDrawer [data-new-comment]')
  compose.locator('textarea').fill('Move this object slightly lower.')
  compose.locator('button[type=submit]').click();page.wait_for_timeout(120)
  assert page.evaluate("()=>EInviteReviewWorkflow.comments.length")==1
  assert page.evaluate("()=>EInviteReviewWorkflow.comments[0].objectId")==first_id
  assert page.locator('#v23ReviewPins [data-comment-pin]').count()==1
  # Thread reply preserves the root anchor.
  page.locator('#v23ReviewDrawer [data-reply-comment]').click();reply=page.locator('#v23ReviewDrawer [data-reply-form]');reply.locator('textarea').fill('Updated in the next revision.');reply.locator('button[type=submit]').click();page.wait_for_function("()=>EInviteReviewWorkflow.comments.length===2")
  assert page.evaluate("()=>EInviteReviewWorkflow.comments.length")==2
  assert page.evaluate("()=>EInviteReviewWorkflow.comments[1].parentId===EInviteReviewWorkflow.comments[0].id")
  # Resolve and reopen the root.
  page.locator('#v23ReviewDrawer [data-resolve-comment]').click();page.wait_for_timeout(100)
  assert page.evaluate("()=>EInviteReviewWorkflow.comments[0].resolved")
  page.locator('#v23ReviewDrawer [data-review-filter]').select_option('resolved');page.wait_for_timeout(70)
  assert page.locator('#v23ReviewDrawer [data-thread-id]').count()==1
  page.locator('#v23ReviewDrawer [data-resolve-comment]').click();page.wait_for_timeout(100)
  assert not page.evaluate("()=>EInviteReviewWorkflow.comments[0].resolved")
  # Exact point placement after clearing selection.
  page.evaluate("()=>clearSelection()");page.locator('#v23ReviewDrawer [data-review-filter]').select_option('open');compose=page.locator('#v23ReviewDrawer [data-new-comment]');compose.locator('textarea').fill('Balance the whitespace here.');compose.locator('[data-place-comment]').click();page.wait_for_timeout(50)
  page.evaluate("""()=>{const stage=document.querySelector('#stage'),rect=stage.getBoundingClientRect();stage.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true,pointerId:42,clientX:rect.left+rect.width*.35,clientY:rect.top+rect.height*.62}))}""");page.wait_for_function("()=>EInviteReviewWorkflow.comments.filter(x=>!x.parentId).length===2",timeout=10000)
  assert page.evaluate("()=>EInviteReviewWorkflow.comments.filter(x=>!x.parentId).length")==2
  point=page.evaluate("()=>EInviteReviewWorkflow.comments.find(x=>x.body.includes('whitespace'))")
  assert .29<point['x']<.41 and .56<point['y']<.68,point
  assert page.locator('#v23ReviewPins [data-comment-pin]').count()==2
  # Formal revision-bound approval and stale feedback.
  page.locator('#v23ReviewDrawer [data-tab="approvals"]').click();form=page.locator('#v23ReviewDrawer [data-request-approval]');form.locator('input[name=requestedFrom]').fill('manager@example.com');form.locator('textarea[name=note]').fill('Please approve this saved design.');form.locator('button[type=submit]').click();page.wait_for_timeout(120)
  assert page.locator('#v23ReviewDrawer [data-approval-id]').count()==1
  assert 'pending' in page.locator('.studio-statusbar [data-v23-review-status]').inner_text().lower()
  page.evaluate("()=>__reviewMock.setStale()");page.evaluate("()=>EInviteReviewWorkflow.refresh()");page.wait_for_timeout(120)
  assert page.locator('#v23ReviewDrawer .v23-approval-card.is-stale').count()==1
  page.locator('#v23ReviewDrawer [data-decide-approval="approved"]').click();page.wait_for_timeout(100)
  assert page.evaluate("()=>EInviteReviewWorkflow.approvals[0].status")=="approved"
  # Repeated openings and selection changes do not duplicate UI owners.
  for _ in range(3):page.evaluate("()=>EInviteCommandRegistry.execute('review.open')")
  page.wait_for_timeout(80)
  assert page.locator('#v23ReviewDrawer').count()==1
  assert page.locator('#v23ReviewPins').count()==1
  assert page.locator('#v23ContextToolbar [data-command-id="review.addComment"]').count()==1
  errors=[error for error in errors if 'setPointerCapture' not in error]
  assert not errors,errors
  browser.close()
 print('V23_7_REVIEW_WORKFLOW_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
