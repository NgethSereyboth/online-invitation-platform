#!/usr/bin/env python3
"""Rotated nested-group transforms, isolated per handle in fresh Playwright drivers."""
from __future__ import annotations
import argparse,os,subprocess,sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped
from v17_professional_editor_test import build,boot,box,drag_handle
ROOT=Path(__file__).resolve().parents[1]
VECTORS={'nw':(-24,-20),'n':(0,-20),'ne':(24,-20),'e':(24,0),'se':(24,20),'s':(0,20),'sw':(-24,20),'w':(-24,0)}

def reveal_handle(page,handle):
 page.evaluate("""async h=>{const pause=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))),v=document.querySelector('#canvasViewport');if(!v)throw new Error('Missing canvas viewport');for(let attempt=0;attempt<5;attempt++){const el=document.querySelector(`[data-pe-handle="${h}"]`);if(!el)throw new Error(`Missing ${h} handle`);const r=el.getBoundingClientRect(),vr=v.getBoundingClientRect(),margin=18;let dx=0,dy=0;if(r.left<vr.left+margin)dx=r.left-vr.left-margin;else if(r.right>vr.right-margin)dx=r.right-vr.right+margin;if(r.top<vr.top+margin)dy=r.top-vr.top-margin;else if(r.bottom>vr.bottom-margin)dy=r.bottom-vr.bottom+margin;if(!dx&&!dy)break;v.scrollBy(dx,dy);await pause()}await pause()}""",handle);page.wait_for_timeout(420)

def open_nested(p,html,errors):
 browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(20_000)
 page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None);boot(page,html)
 page.evaluate("""()=>{EInviteEditorBridge.transact('V18 rotated setup',doc=>{doc.objects.subtitle.rotation=24;doc.objects.details.rotation=-31});EInviteEditorBridge.select(['title','subtitle']);EInviteProfessionalEditor.commands.groupSelection();EInviteEditorBridge.select(['title','subtitle','details']);EInviteProfessionalEditor.commands.groupSelection();EInviteEditorBridge.select(['title','subtitle','details'])}""");page.wait_for_timeout(320)
 groups=page.evaluate("()=>structuredClone(state.sceneGraph.groups)");assert any(g.get('parentId') for g in groups.values()),groups
 return browser,page

def run_handle(handle):
 from playwright.sync_api import sync_playwright
 html=build();errors=[];dx,dy=VECTORS[handle]
 with sync_playwright() as p:
  browser,page=open_nested(p,html,errors)
  reveal_handle(page,handle)
  before=page.evaluate("()=>({objects:['title','subtitle','details'].map(id=>structuredClone(state.objects[id])),history:undoStack.length})");hit=page.evaluate("h=>{const el=document.querySelector(`[data-pe-handle=\"${h}\"]`),r=el.getBoundingClientRect(),at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2),v=document.querySelector('#canvasViewport'),vr=v.getBoundingClientRect();return{handle:[r.left,r.top,r.width,r.height],hit:at?.tagName,hitId:at?.id,hitClass:at?.className,hitHandle:at?.dataset?.peHandle,overlay:[...document.elementsFromPoint(r.left+r.width/2,r.top+r.height/2)].slice(0,6).map(x=>[x.tagName,x.id,x.className,x.dataset?.peHandle]),viewport:[vr.left,vr.top,vr.right,vr.bottom,v.scrollLeft,v.scrollTop,v.clientWidth,v.clientHeight,v.scrollWidth,v.scrollHeight],window:[innerWidth,innerHeight]}}",handle);drag_handle(page,handle,dx*.7,dy*.7);after=page.evaluate("()=>({objects:['title','subtitle','details'].map(id=>structuredClone(state.objects[id])),history:undoStack.length})")
  assert after['history']==before['history']+1 and after['objects']!=before['objects'],f'{handle}: transform did not create exactly one changed history entry ({before["history"]}->{after["history"]}, changed={after["objects"]!=before["objects"]}, hit={hit})'
  assert page.evaluate("()=>['title','subtitle','details'].every(id=>['left','top','width','height','rotation'].every(k=>Number.isFinite(parseFloat(state.objects[id][k]))))"),handle
  page.keyboard.press('Control+z');page.wait_for_timeout(220);undone=page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))");assert undone==before['objects'],f'{handle}: undo did not restore the exact pre-transform objects'
  page.keyboard.press('Control+y');page.wait_for_timeout(220);redone=page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))");assert redone==after['objects'],f'{handle}: redo did not restore the exact post-transform objects'
  assert not errors,errors[:10];page.close();browser.close()
 print(f'V18_NESTED_HANDLE_{handle.upper()}_PASSED')

def run_finish():
 from playwright.sync_api import sync_playwright
 html=build();errors=[]
 with sync_playwright() as p:
  browser,page=open_nested(p,html,errors);s=box(page,'#stage');assert s
  group_before=page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))");reveal_handle(page,'rotate');rb=box(page,'.pe-rotate');gb=box(page,'#peSelectionBox');assert rb and gb
  page.mouse.move(rb['x']+rb['width']/2,rb['y']+rb['height']/2);page.mouse.down();page.mouse.move(gb['x']+gb['width']+32,gb['y']+gb['height']/2,steps=5);page.mouse.up();page.wait_for_timeout(220);reveal_handle(page,'se');drag_handle(page,'se',24,18,['Shift','Alt']);group_after=page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))");assert group_after!=group_before
  page.keyboard.press('Control+z');page.wait_for_timeout(220);page.keyboard.press('Control+z');page.wait_for_timeout(220);assert page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))")==group_before
  page.keyboard.press('Control+y');page.wait_for_timeout(220);page.keyboard.press('Control+y');page.wait_for_timeout(220);assert page.evaluate("()=>['title','subtitle','details'].map(id=>structuredClone(state.objects[id]))")==group_after
  page.evaluate("()=>EInviteEditorBridge.select(['details'])");page.wait_for_timeout(60);ob=box(page,'#stage .object[data-id="details"]');assert ob
  page.mouse.move(ob['x']+ob['width']/2,ob['y']+ob['height']/2);page.mouse.down();page.mouse.move(s['x']+s['width']/2,s['y']+s['height']*.42,steps=5);page.wait_for_timeout(40);assert page.locator('.pe-smart-guide').count()>=1;page.mouse.up();page.wait_for_timeout(180)
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle','details'])");page.evaluate("()=>EInviteProfessionalEditor.commands.alignSelection('left')");page.wait_for_timeout(220);lefts=page.evaluate("()=>['title','subtitle','details'].map(id=>parseFloat(state.objects[id].left))");assert max(lefts)-min(lefts)<.02,lefts
  page.evaluate("()=>EInviteProfessionalEditor.commands.distributeSelection('vertical')");page.wait_for_timeout(220);page.evaluate("()=>{window.prompt=()=> '42';document.querySelector('[data-pe-guide=\"x\"]').click()}");page.wait_for_timeout(160);assert page.locator('.pe-user-guide.pe-vertical').count()>=1
  page.evaluate("()=>EInviteEditorBridge.select(['subtitle'])");page.locator('[data-inspector-tab="object"]').click();page.locator('#textContent').fill('សូមស្វាគមន៍ — Welcome');page.locator('#textContent').blur();page.wait_for_timeout(260);khmer=page.evaluate("()=>({html:state.objects.subtitle.html,font:getComputedStyle(document.querySelector('#stage .object[data-id=\"subtitle\"]')).fontFamily})");assert 'សូមស្វាគមន៍' in khmer['html'] and khmer['font']
  assert not errors,errors[:10];page.close();browser.close()
 print('V18_NESTED_FINISH_PASSED')

def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--case',choices=[*VECTORS,'finish']);args=parser.parse_args(argv)
 if args.case:
  try:
   if args.case=='finish':run_finish()
   else:run_handle(args.case)
  except ImportError as exc:return skipped('V18_NESTED_TRANSFORM_MATRIX',exc)
  return 0
 env={**os.environ,'PYTHONPATH':str(ROOT/'tests')}
 for case in [*VECTORS,'finish']:
  result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--case',case],cwd=ROOT,env=env,text=True,capture_output=True,timeout=120)
  if result.stdout:print(result.stdout.rstrip(),flush=True)
  if result.stderr:print(result.stderr.rstrip(),file=sys.stderr,flush=True)
  if result.returncode:return result.returncode
 print('V18_NESTED_TRANSFORM_MATRIX_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
