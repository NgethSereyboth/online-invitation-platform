#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
CSS=[
 ('direct-manipulation-v24.css','v24Direct'),('content-browser-v24.css','v24Content'),('smart-layout-v24.css','v24Layout'),
 ('brand-components-v24.css','v24Brand'),('collaboration-v24.css','v24Collaboration'),('export-quality-v24.css','v24Quality')]
JS=['direct-manipulation-v24.js','content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(1200)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
  for name,key in CSS:
   page.add_style_tag(path=str(ROOT/name));page.evaluate("key=>{const l=document.createElement('link');l.rel='stylesheet';l.dataset[key]='1';document.head.append(l)}",key)
  page.evaluate("""()=>{
   const seedComments=[{id:'c1',parentId:'',pageId:'hero',objectId:'',body:'Review the invitation title',author:'reviewer@example.com',resolved:false,createdAt:Date.now()}];
   window.EInviteReviewWorkflow={
    comments:seedComments,approvals:[],context:{reviewers:[{email:'reviewer@example.com',role:'designer'}],readiness:{ready:true,validApprovals:1,blockers:[]},unreadCount:0},
    refresh:async()=>true,open:()=>true,jumpToComment:async()=>true,resolveComment:async(id,value)=>{const x=seedComments.find(c=>c.id===id);if(x)x.resolved=value;return x}
   };
   window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}};
  }""")
  for name in JS:page.add_script_tag(path=str(ROOT/name));page.wait_for_timeout(80)
  versions=page.evaluate("""()=>({direct:EInviteDirectManipulation.version,content:EInviteContentBrowser.version,layout:EInviteSmartLayout.version,brand:EInviteBrandComponents.version,collab:EInviteCollaborationCenter.version,quality:EInviteExportQuality.version,conflicts:EInviteCommandRegistry.conflicts.length})""")
  assert versions=={'direct':24.1,'content':24.2,'layout':24.3,'brand':24.4,'collab':24.5,'quality':24.6,'conflicts':0},versions
  # Inline editing starts from the command registry and stays local to selected text.
  text_id=page.evaluate("""()=>{const node=[...document.querySelectorAll('#stage .object')].find(n=>['text','decoration'].includes((state.objects[n.dataset.id]||{}).type));EInviteEditorBridge.select([node.dataset.id]);return node.dataset.id}""")
  assert page.evaluate("()=>EInviteCommandRegistry.execute('text.editInline')")
  assert page.locator(f'#stage .object[data-id="{text_id}"] .content[contenteditable="true"]').count()==1
  page.keyboard.press('Control+Enter');page.wait_for_timeout(50)
  # Unified content inserts a real element.
  before=page.locator('#stage .object').count();page.evaluate("()=>EInviteCommandRegistry.execute('content.openElements')");page.wait_for_timeout(80)
  assert page.locator('#v24ContentBrowser').is_visible();page.locator('[data-item="element-rectangle"]').click();page.wait_for_timeout(100)
  assert page.locator('#stage .object').count()==before+1
  # Smart layout applies one transaction to a multi-selection.
  ids=page.evaluate("()=>[...document.querySelectorAll('#stage .object')].slice(0,3).map(n=>n.dataset.id)")
  page.evaluate("ids=>EInviteEditorBridge.select(ids)",ids);assert page.evaluate("()=>EInviteCommandRegistry.execute('layout.stackVertical')")
  page.evaluate("()=>EInviteCommandRegistry.execute('layout.open')");page.wait_for_timeout(70);assert page.locator('#v24LayoutDialog').is_visible();page.locator('#v24LayoutDialog [data-close]').first.click()
  # Save a reusable component and confirm it reaches the shared component store.
  page.evaluate("ids=>EInviteEditorBridge.select(ids.slice(0,2))",ids)
  page.evaluate("()=>EInviteBrandComponents.components.saveSelection('Runtime component','Ceremony')")
  assert page.evaluate("()=>EInviteBrandComponents.components.list().some(x=>x.name==='Runtime component')")
  page.evaluate("()=>EInviteBrandComponents.open('brand')");page.wait_for_timeout(60);assert page.locator('#v24BrandDialog').is_visible();page.locator('#v24BrandDialog [data-close]').first.click()
  # Collaboration center derives assignments from private review data.
  page.evaluate("()=>EInviteCollaborationCenter.open('assignments')");page.wait_for_timeout(80);assert page.locator('#v24CollaborationDialog').is_visible()
  page.locator('[data-comment-id="c1"] [data-field="assignee"]').fill('reviewer@example.com');page.wait_for_timeout(40)
  assert page.evaluate("()=>EInviteCollaborationCenter.assignments.list().c1.assignee")=='reviewer@example.com'
  page.locator('#v24CollaborationDialog [data-close]').first.click()
  # Quality checks and backup generation are available without mutating the document.
  result=page.evaluate("()=>{const before=JSON.stringify(EInviteEditorBridge.getState());const issues=EInviteExportQuality.inspect();const payload=EInviteExportQuality.export.backup();return{same:before===JSON.stringify(EInviteEditorBridge.getState()),issues:issues.length,schema:payload.schemaVersion}}")
  assert result['same'] and result['schema']==24,result
  # Missing image descriptions can be repaired directly from the quality surface.
  image_id=page.evaluate("()=>{const entry=Object.entries(EInviteEditorBridge.getState().objects).find(([,o])=>o.type==='image'||o.src!==undefined);if(!entry)return '';delete entry[1].altText;delete entry[1].alt;EInviteEditorBridge.select([entry[0]]);return entry[0]}")
  page.evaluate("()=>EInviteExportQuality.open('quality')");page.wait_for_timeout(60);assert page.locator('#v24QualityDialog').is_visible()
  if image_id:
   page.locator('#v24QualityDialog [data-close]').first.click();page.wait_for_timeout(30)
   assert page.evaluate("()=>EInviteCommandRegistry.execute('accessibility.editAltText')")
   page.locator('#v24AltTextDialog [data-alt-value]').fill('Wedding ceremony portrait')
   page.locator('#v24AltTextDialog button[type="submit"]').click();page.wait_for_timeout(80)
   assert page.evaluate("id=>EInviteEditorBridge.getState().objects[id].alt",image_id)=='Wedding ceremony portrait'
  assert not errors,errors
  browser.close()
 print('V24_CANVA_EXPERIENCE_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
