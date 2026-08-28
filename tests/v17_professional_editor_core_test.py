#!/usr/bin/env python3
"""Isolated core selection and transform regression coverage for V17."""
from __future__ import annotations
from browser_runtime import launch_chromium,skipped
from v17_professional_editor_test import build,boot,box,click_center,drag_handle,reset

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V17_PROFESSIONAL_EDITOR_CORE',exc)
 html=build()
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V17_PROFESSIONAL_EDITOR_CORE',exc)
  page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(20_000);errors=[]
  page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
  boot(page,html);assert page.locator('.pe-handle').count()==8 and page.locator('.pe-rotate').count()==1
  click_center(page,'#stage .object[data-id="title"]');assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['title']
  click_center(page,'#stage .object[data-id="subtitle"]');assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['subtitle']
  page.keyboard.press('Control+z');page.wait_for_timeout(80);assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['title']
  page.keyboard.press('Control+y');page.wait_for_timeout(80);assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['subtitle']
  assert page.evaluate("()=>!('selectionIds' in (state.editorModel||{}))")
  click_center(page,'#stage .object[data-id="title"]',['Shift']);assert set(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))=={'title','subtitle'}
  click_center(page,'#stage .object[data-id="title"]',['Shift']);assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['subtitle']
  page.keyboard.press('Escape');assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==[]
  page.keyboard.press('Control+a');assert len(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))==page.locator('#stage .object:not([data-locked="true"])').count();page.keyboard.press('Escape')
  page.evaluate("()=>document.querySelector('#canvasViewport')?.scrollTo({left:0,top:0})");page.wait_for_timeout(120);s=box(page,'#stage');assert s
  marquee=page.evaluate("""()=>{const stage=document.querySelector('#stage'),r=stage.getBoundingClientRect(),v={left:Math.max(r.left+12,12),top:Math.max(r.top+12,12),right:Math.min(r.right-12,innerWidth-12),bottom:Math.min(r.bottom-12,innerHeight-12)},points=[];for(const x of [v.left,v.left+16,v.right-16,v.right])for(const y of [v.top,v.top+16,v.bottom-16,v.bottom]){const hit=document.elementFromPoint(x,y);if(hit&&stage.contains(hit)&&!hit.closest('.object,[data-pe-handle]'))points.push({x,y})}return{v,points}}""");assert marquee['points'],marquee
  for start in marquee['points'][:4]:
   page.keyboard.press('Escape');end={'x':marquee['v']['right'] if start['x']<(marquee['v']['left']+marquee['v']['right'])/2 else marquee['v']['left'],'y':marquee['v']['bottom'] if start['y']<(marquee['v']['top']+marquee['v']['bottom'])/2 else marquee['v']['top']};page.mouse.move(start['x'],start['y']);page.mouse.down();page.mouse.move(end['x'],end['y'],steps=9);page.mouse.up();page.wait_for_timeout(240)
   if len(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))>=2:break
  assert len(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))>=2,marquee
  page.evaluate("()=>{window.__v17Baseline=EInviteEditorBridge.cloneState();EInviteEditorBridge.select(['details'])}");page.wait_for_timeout(100)
  vectors={'nw':(-24,-20),'n':(0,-20),'ne':(24,-20),'e':(24,0),'se':(24,20),'s':(0,20),'sw':(-24,20),'w':(-24,0)}
  for handle,(dx,dy) in vectors.items():
   before=page.evaluate('()=>structuredClone(state.objects.details)');drag_handle(page,handle,dx,dy);after=page.evaluate('()=>structuredClone(state.objects.details)');assert after!=before,(handle,before,after);assert all(float(str(after[key]).rstrip('%px'))>=0 for key in ('left','top','width','height'));reset(page)
  original=page.evaluate("()=>{const b=document.querySelector('#peSelectionBox').getBoundingClientRect();return {cx:b.left+b.width/2,cy:b.top+b.height/2,ratio:b.width/b.height}}")
  drag_handle(page,'se',28,20,['Shift','Alt']);constrained=page.evaluate("()=>{const b=document.querySelector('#peSelectionBox').getBoundingClientRect();return {cx:b.left+b.width/2,cy:b.top+b.height/2,ratio:b.width/b.height}}")
  assert abs(constrained['cx']-original['cx'])<6 and abs(constrained['cy']-original['cy'])<6,(original,constrained);assert abs(constrained['ratio']-original['ratio'])<.08,(original,constrained);reset(page)
  before=page.evaluate("()=>({left:state.objects.details.left,top:state.objects.details.top,history:undoStack.length})");ob=box(page,'#stage .object[data-id="details"]');assert ob
  page.mouse.move(ob['x']+ob['width']/2,ob['y']+ob['height']/2);page.mouse.down();page.mouse.move(ob['x']+ob['width']/2+24,ob['y']+ob['height']/2+18,steps=5);page.mouse.up();page.wait_for_timeout(420)
  moved=page.evaluate("()=>({left:state.objects.details.left,top:state.objects.details.top,history:undoStack.length})");assert moved['history']==before['history']+1 and moved!=before
  page.keyboard.press('Control+z');page.wait_for_timeout(320);assert page.evaluate('()=>state.objects.details.left')==before['left'];page.keyboard.press('Control+y');page.wait_for_timeout(320);assert page.evaluate('()=>state.objects.details.left')==moved['left']
  page.evaluate("()=>EInviteEditorBridge.select(['details'])");page.wait_for_timeout(60);rb=box(page,'.pe-rotate');sb=box(page,'#peSelectionBox');assert rb and sb
  page.mouse.move(rb['x']+rb['width']/2,rb['y']+rb['height']/2);page.mouse.down();page.mouse.move(sb['x']+sb['width']+35,sb['y']+sb['height']/2,steps=4);page.mouse.up();page.wait_for_timeout(220)
  rotation=float(page.locator('[data-pe-transform="r"]').input_value());assert abs(rotation)>1
  bounds=page.evaluate("()=>{const a=document.querySelector('#stage .object[data-id=\"details\"]').getBoundingClientRect(),b=document.querySelector('#peSelectionBox').getBoundingClientRect();return {a:[a.left,a.top,a.width,a.height],b:[b.left,b.top,b.width,b.height]}}");assert max(abs(a-b) for a,b in zip(bounds['a'],bounds['b']))<4,bounds
  top1=page.evaluate('()=>state.objects.details.top');page.keyboard.press('ArrowUp');page.wait_for_timeout(260);top2=page.evaluate('()=>state.objects.details.top');page.keyboard.press('Shift+ArrowUp');page.wait_for_timeout(260);top3=page.evaluate('()=>state.objects.details.top');assert top1!=top2 and top2!=top3
  width=page.locator('[data-pe-transform="w"]');old=float(width.input_value());width.fill(str(max(24,old-18)));width.press('Enter');width.blur();page.wait_for_timeout(260);assert float(width.input_value())<old-10
  page.evaluate("()=>EInviteEditorBridge.replaceState(structuredClone(window.__v17Baseline),{history:true,save:false,reason:'east-multi-reset'})");page.wait_for_timeout(220);page.evaluate("()=>EInviteEditorBridge.select(['subtitle','details'])");page.wait_for_timeout(80);multi_before=page.evaluate("()=>({a:structuredClone(state.objects.subtitle),b:structuredClone(state.objects.details),h:undoStack.length})")
  east_hit=page.evaluate("()=>{const e=document.querySelector('[data-pe-handle=\"e\"]'),r=e.getBoundingClientRect(),s=document.querySelector('#stage').getBoundingClientRect(),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return{bounds:[r.left,r.top,r.width,r.height],hit:h?.dataset?.peHandle||h?.id||h?.className||h?.tagName,outwardRoom:s.right-r.right}}")
  east_dx=22 if east_hit['outwardRoom']>24 else -22
  drag_handle(page,'e',east_dx,0);multi_after=page.evaluate("()=>({a:structuredClone(state.objects.subtitle),b:structuredClone(state.objects.details),h:undoStack.length})");assert multi_after['h']==multi_before['h']+1 and multi_after['a']!=multi_before['a'] and multi_after['b']!=multi_before['b'],f'east multi-resize dx={east_dx}, history={multi_before["h"]}->{multi_after["h"]}, subtitleChanged={multi_after["a"]!=multi_before["a"]}, detailsChanged={multi_after["b"]!=multi_before["b"]}, hit={east_hit}'
  page.evaluate("()=>EInviteEditorBridge.replaceState(structuredClone(window.__v17Baseline),{history:true,save:false,reason:'south-multi-reset'})");page.wait_for_timeout(220);page.evaluate("()=>EInviteEditorBridge.select(['subtitle','details'])");page.wait_for_timeout(80)
  south_before=page.evaluate("()=>({a:structuredClone(state.objects.subtitle),b:structuredClone(state.objects.details),h:undoStack.length})");drag_handle(page,'s',0,22);south_after=page.evaluate("()=>({a:structuredClone(state.objects.subtitle),b:structuredClone(state.objects.details),h:undoStack.length})")
  assert south_after['h']==south_before['h']+1 and south_after['a']!=south_before['a'] and south_after['b']!=south_before['b'],(south_before,south_after)
  assert not errors,errors[:10];page.close();browser.close()
 print('V17_PROFESSIONAL_EDITOR_CORE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
