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
  page.evaluate("""()=>{window.EInviteBackend={ready:Promise.resolve(),isAvailable:()=>true};window.serverInvite={id:'review-performance'};const now=Date.now(),comments=Array.from({length:180},(_,i)=>({id:'c'+i,email:'reviewer'+(i%8)+'@example.com',user_id:'u'+(i%8),object_id:'',page_id:'hero',parent_id:i%4===3?'c'+(i-1):'',anchor_x:(i%20)/20,anchor_y:((i*7)%20)/20,body:'Review comment '+i+' about invitation spacing and typography',resolved:i%5===0,created_at:now+i,updated_at:now+i,canDelete:true}));window.fetch=async(input)=>{const path=new URL(String(input),'http://einvite.test').pathname,data=path.endsWith('/comments')?comments:[];return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}})}}""")
  page.add_script_tag(path=str(ROOT/'review-v23.js'));page.wait_for_timeout(100)
  duration=page.evaluate("""async()=>{const start=performance.now();EInviteReviewWorkflow.open('comments');await EInviteReviewWorkflow.refresh();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-start}""")
  roots=page.locator('#v23ReviewDrawer [data-thread-id]').count();pins=page.locator('#v23ReviewPins [data-comment-pin]').count()
  assert duration<1200,duration;assert roots>=100,roots;assert pins>=100,pins
  for _ in range(5):page.evaluate("()=>EInviteReviewWorkflow.open('comments')")
  assert page.locator('#v23ReviewDrawer').count()==1 and page.locator('#v23ReviewPins').count()==1
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length")==0
  browser.close()
 print(f'V23_7_REVIEW_PERFORMANCE_TEST_PASSED open_ms={duration:.1f} roots={roots} pins={pins}');return 0
if __name__=='__main__':sys.exit(main())
