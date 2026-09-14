#!/usr/bin/env python3
"""V18 layers, groups, clipboard validation, ordering, and command-history coverage."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v18_layers',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def mouse_drag_row(page, source_id:str, target_id:str, position:str='before'):
 page.locator('#layersPanel').scroll_into_view_if_needed();page.wait_for_timeout(80)
 source=page.locator(f'.pe-layer-row[data-layer-id="{source_id}"] [data-layer-drag]');target=page.locator(f'.pe-layer-row[data-layer-id="{target_id}"]')
 sb=source.bounding_box();tb=target.bounding_box();assert sb and tb,(sb,tb)
 page.mouse.move(sb['x']+sb['width']/2,sb['y']+sb['height']/2);page.mouse.down()
 y=tb['y']+(3 if position=='before' else tb['height']-3)
 page.mouse.move(tb['x']+tb['width']/2,y,steps=8);page.wait_for_timeout(100)
 assert target.evaluate("(row,pos)=>row.classList.contains(pos==='before'?'drop-before':'drop-after')",position)
 page.mouse.up();page.wait_for_timeout(260)

def touch_drag_row(page, source_id:str, target_id:str, position:str='after'):
 page.locator('#layersPanel').scroll_into_view_if_needed();page.wait_for_timeout(80)
 source=page.locator(f'.pe-layer-row[data-layer-id="{source_id}"] [data-layer-drag]');target=page.locator(f'.pe-layer-row[data-layer-id="{target_id}"]')
 sb=source.bounding_box();tb=target.bounding_box();assert sb and tb
 payload={'sx':sb['x']+sb['width']/2,'sy':sb['y']+sb['height']/2,'tx':tb['x']+tb['width']/2,'ty':tb['y']+(3 if position=='before' else tb['height']-3)}
 page.evaluate("""p=>{const handle=document.elementFromPoint(p.sx,p.sy);if(!handle)throw Error('missing drag handle');const fire=(target,type,x,y,buttons)=>target.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,pointerId:77,pointerType:'touch',isPrimary:true,button:0,buttons,clientX:x,clientY:y}));fire(handle,'pointerdown',p.sx,p.sy,1);fire(document,'pointermove',p.tx,p.ty,1);fire(document,'pointerup',p.tx,p.ty,0)}""",payload)
 page.wait_for_timeout(300)

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V18_LAYERS_CLIPBOARD_HISTORY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V18_LAYERS_CLIPBOARD_HISTORY',exc)
  page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(20_000);errors=[]
  page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=30_000);page.wait_for_timeout(1600)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteProfessionalEditor?.version===17')

  # Layer tree reflects actual z-order. One mouse gesture creates one command and exact insertion feedback.
  page.locator('[data-inspector-tab="layers"]').click();page.wait_for_timeout(160);assert page.locator('.pe-layer-row[data-layer-id]').count()==page.locator('#stage .object').count()
  before=page.evaluate("()=>({title:state.objects.title.zIndex,details:state.objects.details.zIndex,sequence:EInviteProfessionalEditor.commandSequence})")
  mouse_drag_row(page,'details','title','before')
  after=page.evaluate("()=>({title:state.objects.title.zIndex,details:state.objects.details.zIndex,sequence:EInviteProfessionalEditor.commandSequence,label:EInviteProfessionalEditor.lastCommand?.label})")
  assert after['sequence']==before['sequence']+1 and after['label']=='Reorder layers' and after['details']>after['title'],(before,after)
  page.keyboard.press('Control+z');page.wait_for_timeout(260);undone=page.evaluate("()=>({title:state.objects.title.zIndex,details:state.objects.details.zIndex})");assert undone=={'title':before['title'],'details':before['details']},(before,undone)
  page.keyboard.press('Control+y');page.wait_for_timeout(260)

  # Touch/pointer reorder is independent of HTML5 dataTransfer.
  touch_before=page.evaluate('()=>EInviteProfessionalEditor.commandSequence');touch_drag_row(page,'details','title','after');touch_after=page.evaluate('()=>EInviteProfessionalEditor.commandSequence');assert touch_after==touch_before+1,(touch_before,touch_after)

  # Keyboard move commands announce their result and preserve row focus.
  title_row=page.locator('.pe-layer-row[data-layer-id="title"]');title_row.focus();seq=page.evaluate('()=>EInviteProfessionalEditor.commandSequence');page.keyboard.press('Alt+ArrowUp');page.wait_for_timeout(260)
  assert page.evaluate('()=>EInviteProfessionalEditor.commandSequence')==seq+1
  assert page.locator('.pe-layer-live').text_content().strip()
  assert page.evaluate("()=>document.activeElement?.dataset?.layerId")=='title'
  page.keyboard.press('Control+z');page.wait_for_timeout(220)

  # Inline rename replaces blocking prompt and remains keyboard accessible.
  page.evaluate("()=>window.prompt=()=>{throw new Error('blocking prompt must not be used')}");title_row=page.locator('.pe-layer-row[data-layer-id="title"]');title_row.focus();page.keyboard.press('F2');page.wait_for_selector('.pe-layer-row[data-layer-id="title"] .pe-layer-rename:visible')
  rename=page.locator('.pe-layer-row[data-layer-id="title"] .pe-layer-rename');rename.fill('Khmer heading layer');rename.press('Enter');page.wait_for_function("()=>state.objects.title.layerName==='Khmer heading layer'")
  assert page.evaluate("()=>document.activeElement?.dataset?.layerId")=='title'

  # Lock, hide/show, layer selection, and canvas lock enforcement.
  page.locator('.pe-layer-row[data-layer-id="title"] [data-layer-lock]').click();page.wait_for_timeout(180);assert page.evaluate('()=>state.objects.title.locked') is True
  page.keyboard.press('Escape');page.locator('#stage .object[data-id="title"]').click();assert 'title' not in page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')
  page.locator('.pe-layer-row[data-layer-id="title"] .pe-layer-main').click();assert page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==['title']
  page.locator('.pe-layer-row[data-layer-id="title"] [data-layer-visible]').click();page.wait_for_timeout(180);assert page.evaluate('()=>state.objects.title.visible') is False and page.evaluate('()=>EInviteEditorBridge.getSelectedIds()')==[]
  page.locator('.pe-layer-row[data-layer-id="title"] [data-layer-visible]').click();page.locator('.pe-layer-row[data-layer-id="title"] [data-layer-lock]').click();page.wait_for_timeout(180)

  # Clipboard operations create stable unique IDs and visible offsets.
  page.evaluate("()=>EInviteEditorBridge.select(['details'])");count=page.locator('#stage .object').count();source=page.evaluate('()=>structuredClone(state.objects.details)');page.evaluate('()=>document.body.tabIndex=-1;document.body.focus()');page.keyboard.press('Control+c');page.keyboard.press('Control+v');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count+1',arg=count,timeout=8_000)
  pasted=page.evaluate('()=>EInviteEditorBridge.getSelectedIds()');assert len(pasted)==1 and pasted[0] not in {'title','subtitle','hero','details'}
  pdata=page.evaluate('id=>structuredClone(state.objects[id])',pasted[0]);assert pdata['left']!=source['left'] or pdata['top']!=source['top']
  keys=page.evaluate('()=>Object.keys(state.objects)');scene=page.evaluate('()=>Object.keys(state.sceneGraph.objects)');assert len(keys)==len(set(keys))==len(scene)==len(set(scene))
  page.keyboard.press('Control+d');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count+2',arg=count,timeout=8_000)
  cut_count=page.locator('#stage .object').count();page.keyboard.press('Control+x');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count-1',arg=cut_count,timeout=8_000);page.keyboard.press('Control+v');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count',arg=cut_count,timeout=8_000)

  # Invalid, oversized, cyclic, old-version, cross-page, and cross-project payloads are rejected atomically.
  result=page.evaluate("""()=>{const commands=EInviteProfessionalEditor.commands,base={version:18,projectId:String(state.id||state.invitationId||''),canvasId:EInviteEditorBridge.getActiveCanvasId(),objects:[['details',structuredClone(state.objects.details)]],groups:{},copiedAt:Date.now()},before=Object.keys(state.objects).length,errors=[];document.addEventListener('einvite:clipboard-error',e=>errors.push(e.detail.message));const cases=[null,{...base,version:17},{...base,objects:'bad'},{...base,objects:[['details',{...structuredClone(state.objects.details),html:'x'.repeat(1100000)}]]},{...base,groups:{g1:{children:['g2'],parentId:'g2'},g2:{children:['g1'],parentId:'g1'}}},{...base,canvasId:'another-page'},{...base,projectId:'another-project'}];const returns=cases.map(value=>commands.pastePayload(value));return{before,after:Object.keys(state.objects).length,returns,errors}}""")
  assert result['before']==result['after'] and all(value is False for value in result['returns']) and len(result['errors'])==7,result

  # Delete/undo/redo keeps the redo stack intact after autosave.
  delete_before=page.locator('#stage .object').count();page.wait_for_function('()=>EInviteEditorBridge.getSelectedIds().length>0',timeout=8_000);page.keyboard.press('Delete');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count-1',arg=delete_before,timeout=8_000)
  page.keyboard.press('Control+z');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count',arg=delete_before,timeout=8_000);page.keyboard.press('Control+y');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count-1',arg=delete_before,timeout=8_000)

  # Nested groups remain reorderable while search is active.
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle'])");page.keyboard.press('Control+g');page.wait_for_timeout(240);first=list(page.evaluate('()=>Object.keys(state.sceneGraph.groups)'));assert first
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle','hero'])");page.keyboard.press('Control+g');page.wait_for_timeout(240);groups=page.evaluate('()=>structuredClone(state.sceneGraph.groups)');assert any(g.get('parentId') for g in groups.values()),groups
  page.locator('[data-inspector-tab="layers"]').click();page.wait_for_timeout(160)
  for button in page.locator('[data-group-expand]').all():
   if button.get_attribute('aria-label')=='Expand group':button.click();page.wait_for_timeout(100)
  search=page.locator('[data-pe-layer-search]');search.fill('Khmer heading');page.wait_for_timeout(180);assert page.locator('.pe-layer-row[data-layer-id="title"]').count()==1
  nested_seq=page.evaluate('()=>EInviteProfessionalEditor.commandSequence');page.locator('.pe-layer-row[data-layer-id="title"]').focus();page.keyboard.press('Alt+ArrowDown');page.wait_for_timeout(240);assert page.evaluate('()=>EInviteProfessionalEditor.commandSequence')==nested_seq+1
  assert page.locator('[data-pe-layer-search]').input_value()=='Khmer heading'
  search.fill('');page.wait_for_timeout(180)

  # Auto-scroll is active during pointer reorder in a constrained layer tree.
  page.evaluate("()=>EInviteEditorBridge.select(['details'])")
  for _ in range(12):page.evaluate('()=>EInviteProfessionalEditor.commands.duplicateSelection()')
  page.wait_for_timeout(300);page.locator('[data-inspector-tab="layers"]').click();page.wait_for_timeout(160)
  page.locator('#layersPanel').scroll_into_view_if_needed();page.wait_for_timeout(100);tree=page.locator('.pe-layer-tree');tree.evaluate("el=>{el.style.height='130px';el.style.maxHeight='130px';el.scrollTop=0}");source_handle=page.locator('.pe-layer-row [data-layer-drag]').first;source_handle.scroll_into_view_if_needed();tree.evaluate('el=>el.scrollTop=0');sb=source_handle.bounding_box();tb=tree.bounding_box();assert sb and tb
  page.mouse.move(sb['x']+sb['width']/2,sb['y']+sb['height']/2);page.mouse.down();page.mouse.move(tb['x']+tb['width']/2,tb['y']+tb['height']-2,steps=24);page.wait_for_timeout(220);scrolled=tree.evaluate('el=>el.scrollTop');page.mouse.up();page.wait_for_timeout(220);assert scrolled>0,scrolled

  # Orphan cleanup and schema validity remain intact.
  page.evaluate("()=>EInviteEditorBridge.select(['title','subtitle','hero'])");page.keyboard.press('Delete');page.wait_for_timeout(260)
  validity=page.evaluate("()=>({schema:EInviteEditorSchema.validate(state),orphans:Object.values(state.sceneGraph.groups||{}).filter(g=>(g.children||[]).some(id=>!state.objects[id]&&!state.sceneGraph.groups[id])).length})")
  assert validity['schema']['ok'] and validity['orphans']==0,validity
  page.keyboard.press('Control+z');page.wait_for_timeout(300)

  assert not errors,errors[:10]
  page.close();browser.close()
 print('V18_LAYERS_CLIPBOARD_HISTORY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
