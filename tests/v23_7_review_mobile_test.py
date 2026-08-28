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
  page.evaluate("""()=>{window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>true};window.serverInvite={id:'mobile-review'};const comments=[];window.fetch=async(input,options={})=>{const path=new URL(String(input),'http://einvite.test').pathname,method=(options.method||'GET').toUpperCase(),body=options.body?JSON.parse(options.body):{};let data=[];if(path.endsWith('/comments')&&method==='POST'){data={id:'mobile-'+(comments.length+1),email:'mobile@example.com',user_id:'u',object_id:body.objectId||'',page_id:body.pageId||'hero',parent_id:'',anchor_x:body.anchorX??-1,anchor_y:body.anchorY??-1,body:body.body,resolved:false,created_at:Date.now(),updated_at:Date.now(),canDelete:true};comments.push(data);return new Response(JSON.stringify(data),{status:201})}if(path.endsWith('/comments'))data=comments;else if(path.endsWith('/approvals'))data=[];return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}})}}""")
  page.add_script_tag(path=str(ROOT/'review-v23.js'));page.wait_for_timeout(180);page.evaluate("()=>EInviteReviewWorkflow.open('comments')");page.wait_for_timeout(260)
  drawer=page.locator('#v23ReviewDrawer');assert drawer.is_visible();box=drawer.bounding_box();assert box['x']>=-1 and box['x']+box['width']<=391 and box['y']>=0 and box['y']+box['height']<=845,box
  overflow=page.evaluate("()=>({doc:document.documentElement.scrollWidth-innerWidth,drawer:document.querySelector('#v23ReviewDrawer').scrollWidth-document.querySelector('#v23ReviewDrawer').clientWidth,cols:getComputedStyle(document.querySelector('.v23-review-toolbar')).gridTemplateColumns})")
  assert overflow['doc']<=1 and overflow['drawer']<=1 and ' ' not in overflow['cols'].strip(),overflow
  page.evaluate("()=>EInviteReviewWorkflow.addComment('Mobile pin',{pageId:'hero',point:{x:.3,y:.4}})");page.wait_for_timeout(100)
  assert page.locator('#v23ReviewPins [data-comment-pin]').count()==1
  footer=page.locator('#v23ReviewDrawer footer');assert footer.is_visible();fbox=footer.bounding_box();assert fbox['y']+fbox['height']<=845
  errors=[e for e in errors if 'setPointerCapture' not in e];assert not errors,errors
  browser.close()
 print('V23_7_REVIEW_MOBILE_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
