#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor

ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 try:
  from playwright.sync_api import sync_playwright
 except Exception as exc:
  print('V23_COMMAND_BROWSER_SKIPPED_NO_PLAYWRIGHT',exc);return 0
 html=build_inline_editor()
 with sync_playwright() as p:
  try: browser=launch_chromium(p)
  except Exception as exc:
   print('V23_COMMAND_BROWSER_SKIPPED_NO_CHROMIUM',exc);return 0
  page=browser.new_page(viewport={'width':1440,'height':1000})
  errors=[]
  page.on('pageerror',lambda error:errors.append(f'PAGE: {error}'))
  page.on('console',lambda msg:errors.append(f'CONSOLE: {msg.text}') if msg.type=='error' else None)
  page.set_content(html,wait_until='load',timeout=30000)
  page.wait_for_timeout(1800)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
   page.locator('#finalTourDismiss').click();page.wait_for_timeout(100)
  assert page.evaluate("()=>!!window.EInviteCommandRegistry&&!!window.EInviteShortcutManager")
  assert page.evaluate("()=>EInviteShortcutManager.ownsGlobalKeyboard===true")
  registry_integrity=page.evaluate("""()=>{
   const dispose=EInviteCommandRegistry.register({id:'test.command',title:'Test command',run:()=>true});
   let duplicate=false;try{EInviteCommandRegistry.register({id:'test.command',title:'Duplicate',run:()=>true})}catch{duplicate=true}
   dispose();return {duplicate,removed:!EInviteCommandRegistry.get('test.command')};
  }""")
  assert registry_integrity=={'duplicate':True,'removed':True}
  assert page.evaluate("()=>EInviteCommandRegistry.conflicts.length") == 0
  assert not errors,errors[:8]

  # Existing workflow shortcuts remain compatible through the central registry.
  for chord,pane in [('Shift+E','elements'),('Shift+T','text'),('Shift+U','media')]:
   page.keyboard.press(chord);page.wait_for_timeout(60)
   assert page.locator('.studio-pane.active').get_attribute('data-studio-pane')==pane,(chord,pane)
  page.keyboard.press('Shift+F');page.wait_for_timeout(60)
  assert 'workflow-focus-canvas' in (page.locator('body').get_attribute('class') or '')
  page.keyboard.press('Shift+F');page.wait_for_timeout(60)
  assert 'workflow-focus-canvas' not in (page.locator('body').get_attribute('class') or '')

  # Layered history preserves selection undo before document undo, and scene groups survive synchronization.
  baseline=page.evaluate("()=>EInviteEditorBridge.cloneState()")
  page.locator('#stage .object[data-id="title"]').click(force=True);page.locator('#stage .object[data-id="subtitle"]').click(force=True)
  page.keyboard.press('Control+Z');page.wait_for_timeout(50)
  assert page.evaluate("()=>EInviteEditorBridge.getSelectedIds()") == ['title']
  page.keyboard.press('Control+Y');page.wait_for_timeout(50)
  assert page.evaluate("()=>EInviteEditorBridge.getSelectedIds()") == ['subtitle']
  nested=page.evaluate("""()=>{EInviteEditorBridge.select(['title','subtitle']);EInviteProfessionalEditor.commands.groupSelection();EInviteEditorBridge.select(['title','subtitle','details']);EInviteProfessionalEditor.commands.groupSelection();return structuredClone(state.sceneGraph.groups)}""")
  assert len(nested)==2 and any(group.get('parentId') for group in nested.values()),nested
  page.evaluate("doc=>EInviteEditorBridge.replaceState(doc,{history:false,save:false,reason:'v23-command-test-reset'})",baseline);page.wait_for_timeout(100)

  # Space controls the real pan state, not only cursor styling.
  page.keyboard.down('Space');page.wait_for_timeout(30)
  assert page.evaluate("()=>EInviteCanvasPanController.held&&document.body.dataset.v23SpacePan==='true'")
  page.keyboard.up('Space');page.wait_for_timeout(30)
  assert page.evaluate("()=>!EInviteCanvasPanController.held&&!document.body.dataset.v23SpacePan")
  page.locator('#panToggle').focus()
  page.keyboard.down('Space');page.wait_for_timeout(20)
  assert page.evaluate("()=>!EInviteCanvasPanController.held")
  page.keyboard.up('Space')
  if page.evaluate("()=>EInviteCanvasPanController.pinned"):
   page.locator('#panToggle').click(force=True)


  # Actual size shortcut and profile-specific duplicate/deselect behavior.
  page.select_option('#zoomLevel','1.5');page.keyboard.press('Control+1');page.wait_for_timeout(80)
  assert page.locator('#zoomLevel').input_value()=='1'
  first=page.locator('#stage .object').first
  first.click(force=True,timeout=5000);page.wait_for_timeout(50)
  before=page.locator('#stage .object').count()
  page.keyboard.press('Control+D');page.wait_for_timeout(100)
  assert page.locator('#stage .object').count()==before+1

  page.evaluate("()=>EInviteCommandRegistry.setProfile('photoshop')")
  page.locator('#stage .object').first.click(force=True,timeout=5000);page.wait_for_timeout(40)
  page.keyboard.press('Control+D');page.wait_for_timeout(60)
  assert page.locator('#stage .object.selected,#stage .object.multi-selected').count()==0
  page.locator('#stage .object').first.click(force=True,timeout=5000);page.wait_for_timeout(40)
  before=page.locator('#stage .object').count()
  page.keyboard.press('Control+J');page.wait_for_timeout(100)
  assert page.locator('#stage .object').count()==before+1

  # Toolbar buttons route through the same command exactly once.
  page.locator('#stage .object').first.click(force=True,timeout=5000);page.wait_for_timeout(40)
  before=page.locator('#stage .object').count()
  page.locator('#duplicate').click(force=True,timeout=5000);page.wait_for_timeout(100)
  assert page.locator('#stage .object').count()==before+1

  # Lazy command UI can be loaded independently and edits profiles/overrides.
  page.add_style_tag(path=str(ROOT/'command-palette-v23.css'))
  page.add_script_tag(path=str(ROOT/'command-palette-v23.js'))
  page.evaluate("()=>EInviteCommandRegistry.openUI('commands')")
  page.wait_for_timeout(100)
  assert page.locator('.v23-command-surface').is_visible()
  page.locator('.v23-command-search input').fill('zoom to 100')
  page.wait_for_timeout(60)
  assert page.locator('[data-command-id="canvas.actualSize"]').count()==1
  search=page.locator('.v23-command-search input')
  search.fill('Main hero')
  page.wait_for_function("()=>[...document.querySelectorAll('.v23-command-row small')].some(x=>x.textContent.includes('Open design page'))")
  layer_id=page.evaluate("()=>Object.keys(EInviteEditorBridge.getState().objects||{})[0]")
  search.fill(layer_id)
  page.wait_for_function("()=>[...document.querySelectorAll('.v23-command-row small')].some(x=>x.textContent.includes('Select layer'))")
  page.evaluate("()=>localStorage.setItem('sovan-reusable-page-templates-v1',JSON.stringify([{id:'qa-template',name:'Royal Ceremony Layout',category:'Wedding',page:{}}]))")
  search.fill('Royal Ceremony Layout')
  page.wait_for_function("()=>[...document.querySelectorAll('.v23-command-row small')].some(x=>x.textContent.includes('saved page template'))")
  page.evaluate("async()=>{await assetStore.put({id:'qa-asset',name:'Royal Lotus Photo',type:'image/png',tags:['lotus']});dispatchEvent(new CustomEvent('einvite:assets-changed'))}")
  search.fill('Royal Lotus Photo')
  page.wait_for_function("()=>[...document.querySelectorAll('.v23-command-row small')].some(x=>x.textContent.includes('Media workspace'))")
  page.keyboard.press('Escape');page.wait_for_timeout(40)
  assert not page.locator('.v23-command-surface').is_visible()

  # Shortcut recording stays local to the settings surface; the global manager does not steal it.
  page.evaluate("()=>EInviteCommandRegistry.openUI('shortcuts')")
  page.wait_for_timeout(80)
  row=page.locator('[data-command-id="canvas.actualSize"]')
  record=row.locator('[data-record]')
  record.scroll_into_view_if_needed();record.click();record.focus()
  page.keyboard.press('Control+3')
  page.wait_for_timeout(80)
  assert page.evaluate("()=>EInviteCommandRegistry.getShortcuts('canvas.actualSize','photoshop')[0]")=='Mod+3'
  page.keyboard.press('Escape');page.wait_for_timeout(40)
  page.evaluate("()=>EInviteCommandRegistry.resetOverrides('photoshop')")

  conflicts=page.evaluate("()=>EInviteCommandRegistry.validateOverride('photoshop','canvas.actualSize',['Mod+J'])")
  assert conflicts and any('edit.duplicate' in item['commands'] for item in conflicts)
  result=page.evaluate("()=>EInviteCommandRegistry.setOverride('canvas.actualSize',['Mod+2'],{profile:'photoshop'})")
  assert result['ok'] is True
  assert page.evaluate("()=>EInviteCommandRegistry.getShortcuts('canvas.actualSize','photoshop')[0]")=='Mod+2'
  page.evaluate("()=>EInviteCommandRegistry.resetOverrides('photoshop')")

  assert not errors,errors[:8]
  browser.close()
 print('V23_COMMAND_SYSTEM_BROWSER_TEST_PASSED')
 return 0

if __name__=='__main__':sys.exit(main())
