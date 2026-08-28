#!/usr/bin/env python3
"""Selection, transform, snapping, and layout regression coverage for V17."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v17_transform',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def box(page,selector):return page.locator(selector).bounding_box()
def click_center(page,selector,modifiers=None):
 b=box(page,selector);assert b,selector
 for key in modifiers or []:page.keyboard.down(key)
 try:page.mouse.click(b['x']+b['width']/2,b['y']+b['height']/2)
 finally:
  for key in reversed(modifiers or []):page.keyboard.up(key)

def boot(page,html):
 page.set_content(html,wait_until='load',timeout=30_000);page.wait_for_timeout(1600)
 if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
 page.wait_for_function('()=>window.EInviteProfessionalEditor?.version===17')

def reset(page):
 page.evaluate("()=>{EInviteEditorBridge.replaceState(structuredClone(window.__v17Baseline),{history:true,save:false,reason:'test-reset'});EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(220)

def nested_page(browser,html,errors):
 page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(20_000)
 page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
 boot(page,html)
 page.evaluate("""()=>{EInviteEditorBridge.transact('V18 rotated setup',doc=>{doc.objects.subtitle.rotation=24;doc.objects.details.rotation=-31});EInviteEditorBridge.select(['title','subtitle']);EInviteProfessionalEditor.commands.groupSelection();EInviteEditorBridge.select(['title','subtitle','details']);EInviteProfessionalEditor.commands.groupSelection();window.__v18NestedBaseline=EInviteEditorBridge.cloneState();EInviteEditorBridge.select(['title','subtitle','details'])}""")
 page.wait_for_timeout(320)
 return page

def drag_handle(page,name,dx,dy,modifiers=None):
 hb=box(page,f'[data-pe-handle="{name}"]');assert hb,name
 for key in modifiers or []:page.keyboard.down(key)
 try:
  page.mouse.move(hb['x']+hb['width']/2,hb['y']+hb['height']/2);page.mouse.down();page.mouse.move(hb['x']+hb['width']/2+dx,hb['y']+hb['height']/2+dy,steps=3);page.mouse.up()
 finally:
  for key in reversed(modifiers or []):page.keyboard.up(key)
 page.wait_for_timeout(160)

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V17_PROFESSIONAL_EDITOR',exc)
 html=build()
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V17_PROFESSIONAL_EDITOR',exc)
  page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(20_000);errors=[]
  page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
  boot(page,html)
  assert page.locator('.pe-handle').count()==8 and page.locator('.pe-rotate').count()==1

  # Click, Shift toggle, Escape, Ctrl+A, and marquee selection.
  click_center(page,'#stage .object[data-id="title"]');assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['title']
  click_center(page,'#stage .object[data-id="subtitle"]');assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['subtitle']
  page.keyboard.press('Control+z');page.wait_for_timeout(80);assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['title']
  page.keyboard.press('Control+y');page.wait_for_timeout(80);assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['subtitle']
  assert page.evaluate("()=>!('selectionIds' in (state.editorModel||{}))")
  click_center(page,'#stage .object[data-id="title"]',['Shift']);assert set(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))=={'title','subtitle'}
  click_center(page,'#stage .object[data-id="title"]',['Shift']);assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['subtitle']
  page.keyboard.press('Escape');assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==[]
  page.keyboard.press('Control+a');assert len(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))==page.locator('#stage .object:not([data-locked="true"])').count()
  page.keyboard.press('Escape');s=box(page,'#stage');assert s
  empty=page.evaluate("""()=>{const stage=document.querySelector('#stage'),r=stage.getBoundingClientRect();for(const x of [12,24,36,r.width-12,r.width-24])for(const y of [12,24,36,r.height-12,r.height-24]){const cx=r.left+x,cy=r.top+y,hit=document.elementFromPoint(cx,cy);if(hit&&stage.contains(hit)&&!hit.closest('.object,[data-pe-handle]'))return{x:cx,y:cy}}return{x:r.left+8,y:r.top+8}}""")
  end={'x':s['x']+s['width']-12 if empty['x']<s['x']+s['width']/2 else s['x']+12,'y':s['y']+s['height']-12 if empty['y']<s['y']+s['height']/2 else s['y']+12}
  page.mouse.move(empty['x'],empty['y']);page.mouse.down();page.mouse.move(end['x'],end['y'],steps=7);page.mouse.up();page.wait_for_timeout(160)
  assert len(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))>=2

  # Use an interior object so all eight resize directions have room.
  page.evaluate("()=>{window.__v17Baseline=EInviteEditorBridge.cloneState();EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(100)
  vectors={'nw':(-24,-20),'n':(0,-20),'ne':(24,-20),'e':(24,0),'se':(24,20),'s':(0,20),'sw':(-24,20),'w':(-24,0)}
  for handle,(dx,dy) in vectors.items():
   before=page.evaluate('()=>structuredClone(state.objects.details)');drag_handle(page,handle,dx,dy);after=page.evaluate('()=>structuredClone(state.objects.details)')
   assert after!=before,(handle,before,after)
   assert all(float(str(after[key]).rstrip('%px'))>=0 for key in ('left','top','width','height'))
   reset(page)

  # Shift aspect ratio and Alt center resize.
  original=page.evaluate("()=>{const b=document.querySelector('#peSelectionBox').getBoundingClientRect();return {cx:b.left+b.width/2,cy:b.top+b.height/2,ratio:b.width/b.height}}")
  drag_handle(page,'se',28,20,['Shift','Alt']);constrained=page.evaluate("()=>{const b=document.querySelector('#peSelectionBox').getBoundingClientRect();return {cx:b.left+b.width/2,cy:b.top+b.height/2,ratio:b.width/b.height}}")
  assert abs(constrained['cx']-original['cx'])<6 and abs(constrained['cy']-original['cy'])<6,(original,constrained)
  assert abs(constrained['ratio']-original['ratio'])<.08,(original,constrained)
  reset(page)

  # One drag gesture is one undo command; redo remains available after autosave.
  before=page.evaluate("()=>({left:state.objects.details.left,top:state.objects.details.top,history:undoStack.length})")
  ob=box(page,'#stage .object[data-id="details"]');assert ob
  page.mouse.move(ob['x']+ob['width']/2,ob['y']+ob['height']/2);page.mouse.down();page.mouse.move(ob['x']+ob['width']/2+24,ob['y']+ob['height']/2+18,steps=5);page.mouse.up();page.wait_for_timeout(420)
  moved=page.evaluate("()=>({left:state.objects.details.left,top:state.objects.details.top,history:undoStack.length})");assert moved['history']==before['history']+1 and moved!=before
  page.keyboard.press('Control+z');page.wait_for_timeout(320);assert page.evaluate('()=>state.objects.details.left')==before['left']
  page.keyboard.press('Control+y');page.wait_for_timeout(320);assert page.evaluate('()=>state.objects.details.left')==moved['left']

  # Rotation outline matches the transformed object bounds.
  page.evaluate("()=>EInviteEditorBridge.select(['details'])");page.wait_for_timeout(60);rb=box(page,'.pe-rotate');sb=box(page,'#peSelectionBox');assert rb and sb
  page.mouse.move(rb['x']+rb['width']/2,rb['y']+rb['height']/2);page.mouse.down();page.mouse.move(sb['x']+sb['width']+35,sb['y']+sb['height']/2,steps=4);page.mouse.up();page.wait_for_timeout(220)
  rotation=float(page.locator('[data-pe-transform="r"]').input_value());assert abs(rotation)>1
  bounds=page.evaluate("()=>{const a=document.querySelector('#stage .object[data-id=\"details\"]').getBoundingClientRect(),b=document.querySelector('#peSelectionBox').getBoundingClientRect();return {a:[a.left,a.top,a.width,a.height],b:[b.left,b.top,b.width,b.height]}}")
  assert max(abs(a-b) for a,b in zip(bounds['a'],bounds['b']))<4,bounds

  # Keyboard nudges and numeric controls remain synchronized.
  top1=page.evaluate('()=>state.objects.details.top');page.keyboard.press('ArrowUp');page.wait_for_timeout(260);top2=page.evaluate('()=>state.objects.details.top');page.keyboard.press('Shift+ArrowUp');page.wait_for_timeout(260);top3=page.evaluate('()=>state.objects.details.top');assert top1!=top2 and top2!=top3
  width=page.locator('[data-pe-transform="w"]');old=float(width.input_value());width.fill(str(max(24,old-18)));width.press('Enter');width.blur();page.wait_for_timeout(260);assert float(width.input_value())<old-10

  # Multi-object scaling is a single transaction.
  page.evaluate("()=>EInviteEditorBridge.select(['subtitle','details'])");page.wait_for_timeout(80);multi_before=page.evaluate("()=>({a:structuredClone(state.objects.subtitle),b:structuredClone(state.objects.details),h:undoStack.length})")
  drag_handle(page,'e',22,0);multi_after=page.evaluate("()=>({a:structuredClone(state.objects.subtitle),b:structuredClone(state.objects.details),h:undoStack.length})")
  assert multi_after['h']==multi_before['h']+1 and multi_after['a']!=multi_before['a'] and multi_after['b']!=multi_before['b']

  # Differently rotated objects and nested groups use one coherent world-space transform.
  # Start the nested-group stress phase with a fresh page so Chromium does not retain
  # pointer/paint resources from the preceding independent eight-handle matrix.
  page.close();page=nested_page(browser,html,errors);s=box(page,'#stage');assert s
  nested_baseline=page.evaluate("()=>({doc:structuredClone(state),groups:structuredClone(state.sceneGraph.groups),history:undoStack.length})");assert any(g.get('parentId') for g in nested_baseline['groups'].values()),nested_baseline['groups']
  for index,(handle,(dx,dy)) in enumerate(vectors.items()):
   if index:
    page.close();page=nested_page(browser,html,errors)
   before=page.evaluate("()=>({objects:['title','subtitle','details'].map(id=>structuredClone(state.objects[id])),history:undoStack.length})");drag_handle(page,handle,dx*.7,dy*.7);after=page.evaluate("()=>({objects:['title','subtitle','details'].map(id=>structuredClone(state.objects[id])),history:undoStack.length})")
   assert after['history']==before['history']+1 and after['objects']!=before['objects'],(handle,before,after)
   finite_values=page.evaluate("()=>['title','subtitle','details'].every(id=>['left','top','width','height','rotation'].every(k=>Number.isFinite(parseFloat(state.objects[id][k]))))");assert finite_values,handle
   page.keyboard.press('Control+z');page.wait_for_timeout(220);page.keyboard.press('Control+y');page.wait_for_timeout(220)
  page.close();page=nested_page(browser,html,errors);s=box(page,'#stage');assert s
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle','details'])");page.wait_for_timeout(100);group_before=page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))");rb=box(page,'.pe-rotate');gb=box(page,'#peSelectionBox');assert rb and gb
  page.mouse.move(rb['x']+rb['width']/2,rb['y']+rb['height']/2);page.mouse.down();page.mouse.move(gb['x']+gb['width']+32,gb['y']+gb['height']/2,steps=5);page.mouse.up();page.wait_for_timeout(220);drag_handle(page,'se',24,18,['Shift','Alt']);group_after=page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))");assert group_after!=group_before
  page.keyboard.press('Control+z');page.wait_for_timeout(220);page.keyboard.press('Control+z');page.wait_for_timeout(220);page.keyboard.press('Control+y');page.wait_for_timeout(220);page.keyboard.press('Control+y');page.wait_for_timeout(220)

  # Snapping, temporary guides, align, distribute, and user guides.
  page.evaluate("()=>EInviteEditorBridge.select(['details'])");page.wait_for_timeout(60);ob=box(page,'#stage .object[data-id="details"]');assert ob
  page.mouse.move(ob['x']+ob['width']/2,ob['y']+ob['height']/2);page.mouse.down();page.mouse.move(s['x']+s['width']/2,s['y']+s['height']*.42,steps=5);page.wait_for_timeout(40);assert page.locator('.pe-smart-guide').count()>=1;page.mouse.up();page.wait_for_timeout(180)
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle','details'])");page.evaluate("()=>EInviteProfessionalEditor.commands.alignSelection('left')");page.wait_for_timeout(220)
  lefts=page.evaluate("()=>['title','subtitle','details'].map(id=>parseFloat(state.objects[id].left))");assert max(lefts)-min(lefts)<.02,lefts
  page.evaluate("()=>EInviteProfessionalEditor.commands.distributeSelection('vertical')");page.wait_for_timeout(220)
  page.evaluate("()=>{window.prompt=()=> '42';document.querySelector('[data-pe-guide=\"x\"]').click()}");page.wait_for_timeout(160);assert page.locator('.pe-user-guide.pe-vertical').count()>=1

  # Khmer text remains editable and rendered with a valid font fallback.
  page.evaluate("()=>EInviteEditorBridge.select(['subtitle'])");page.locator('[data-inspector-tab="object"]').click();page.locator('#textContent').fill('សូមស្វាគមន៍ — Welcome');page.locator('#textContent').blur();page.wait_for_timeout(260)
  khmer=page.evaluate("()=>({html:state.objects.subtitle.html,font:getComputedStyle(document.querySelector('#stage .object[data-id=\"subtitle\"]')).fontFamily})");assert 'សូមស្វាគមន៍' in khmer['html'] and khmer['font']

  # Real mobile selection, 44x44 screen-space targets, resize, and rotate at all required viewports.
  # Mobile hit-target and transform validation uses a fresh page for deterministic
  # viewport transitions after the desktop stress phases.
  page.close();page=browser.new_page(viewport={'width':430,'height':932});page.set_default_timeout(20_000)
  page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
  boot(page,html);page.evaluate("()=>{window.__v17Baseline=EInviteEditorBridge.cloneState();EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(100)
  for width_px,height_px in ((360,800),(390,844),(430,932)):
   page.set_viewport_size({'width':width_px,'height':height_px});page.wait_for_timeout(480);reset(page);page.wait_for_timeout(220)
   click_center(page,'#stage .object[data-id="details"]');page.wait_for_timeout(180)
   mobile=page.evaluate("""()=>{const stage=document.querySelector('.stage-wrap'),right=document.querySelector('aside.right'),toolbar=document.querySelector('#peMobileContextBar');const handles=[...document.querySelectorAll('[data-pe-handle]')].map(el=>{const r=el.getBoundingClientRect();return {w:r.width,h:r.height}});const tr=toolbar?.getBoundingClientRect();return{scroll:document.documentElement.scrollWidth,w:innerWidth,mode:document.body.dataset.mobileEditorMode,inspector:document.body.classList.contains('mobile-inspector-open'),rightHidden:right?.getAttribute('aria-hidden'),stageVisible:!!stage&&getComputedStyle(stage).display!=='none'&&!stage.hidden,toolbarVisible:!!toolbar&&!toolbar.hidden&&tr.width>0&&tr.height>0,toolbarHeight:tr?.height||0,handles}}""")
   assert mobile['scroll']<=mobile['w']+1 and mobile['mode']=='canvas' and not mobile['inspector'] and mobile['rightHidden']=='true' and mobile['stageVisible'],(width_px,height_px,mobile)
   assert mobile['toolbarVisible'] and mobile['toolbarHeight']<=90,(width_px,height_px,mobile)
   assert len(mobile['handles'])==9 and all(item['w']>=43.5 and item['h']>=43.5 for item in mobile['handles']),(width_px,height_px,mobile['handles'])
   resize_before=page.evaluate('()=>({w:state.objects.details.width,h:state.objects.details.height})');drag_handle(page,'se',18,14);resize_after=page.evaluate('()=>({w:state.objects.details.width,h:state.objects.details.height})');assert resize_after!=resize_before,(width_px,height_px,resize_before,resize_after)
   reset(page);page.wait_for_timeout(180);rb=box(page,'.pe-rotate');sb=box(page,'#peSelectionBox');assert rb and sb,(width_px,height_px,rb,sb);rotation_before=float(page.locator('[data-pe-transform="r"]').input_value());page.mouse.move(rb['x']+rb['width']/2,rb['y']+rb['height']/2);page.mouse.down();page.mouse.move(sb['x']+sb['width']+20,sb['y']+sb['height']/2,steps=5);page.mouse.up();page.wait_for_timeout(220);rotation_after=float(page.locator('[data-pe-transform="r"]').input_value());assert abs(rotation_after-rotation_before)>1,(width_px,height_px,rotation_before,rotation_after)
  assert not errors,errors[:10]
  page.close();browser.close()
 print('V18_PROFESSIONAL_EDITOR_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
