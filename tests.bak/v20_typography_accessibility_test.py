#!/usr/bin/env python3
"""Real-Chromium keyboard, focus, labels, dialog and live-state coverage for V20 typography controls."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v20_a11y',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_TYPOGRAPHY_ACCESSIBILITY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_TYPOGRAPHY_ACCESSIBILITY',exc)
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(35_000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(build(),wait_until='load',timeout=45_000);page.wait_for_timeout(1800)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteTypographyV20&&document.querySelector("#v20TypographyToolbar")')
  page.evaluate("()=>EInviteEditorBridge.select(['title'])");page.wait_for_timeout(200)
  controls=page.evaluate("""()=>[...document.querySelectorAll('#v20TypographyToolbar input,#v20TypographyToolbar select,#v20TypographyToolbar button,#advancedTextLayout input,#advancedTextLayout select,#advancedTextLayout button')].map(e=>({tag:e.tagName,id:e.id,name:e.getAttribute('aria-label')||e.closest('label')?.innerText?.trim()||e.textContent?.trim(),disabled:e.disabled,hidden:!e.offsetParent}))""")
  assert controls and all(c['name'] for c in controls),controls
  assert page.locator('#v20TypographyToolbar').get_attribute('role')=='toolbar'
  assert page.locator('#v20TypographyWarnings').get_attribute('aria-live')=='polite'
  # Tab order enters the contextual toolbar and each focused control has visible focus.
  page.locator('#v20ToolbarStyle').focus();visited=[]
  for _ in range(6):
   state=page.evaluate("""()=>{const e=document.activeElement,s=getComputedStyle(e);return{id:e.id,label:e.getAttribute('aria-label')||e.closest('label')?.innerText?.trim(),outline:s.outlineStyle,width:s.outlineWidth}}""");visited.append(state);assert state['label'] and state['outline']!='none' and state['width']!='0px',state;page.keyboard.press('Tab')
  assert visited[0]['id']=='v20ToolbarStyle',visited
  # Keyboard activation updates pressed state and history.
  bold=page.locator('#v20ToolbarBold');bold.focus();page.wait_for_function("()=>document.activeElement?.id==='v20ToolbarBold'");before=bold.get_attribute('aria-pressed');page.keyboard.press('Enter');page.wait_for_timeout(150);after=bold.get_attribute('aria-pressed');assert before!=after,(before,after)
  page.keyboard.press('Control+z');page.wait_for_timeout(120);assert bold.get_attribute('aria-pressed')==before
  italic=page.locator('#v20ToolbarItalic');italic.focus();ibefore=italic.get_attribute('aria-pressed');page.keyboard.press('Space');page.wait_for_timeout(150);assert italic.get_attribute('aria-pressed')!=ibefore
  # Style dialog has an accessible name, focus enters it, Escape closes it, and focus returns.
  trigger=page.locator('#v20CreateStyle');trigger.focus();page.keyboard.press('Enter');dlg=page.locator('dialog.v20-dialog');dlg.wait_for(state='visible');labelled=dlg.get_attribute('aria-labelledby');assert labelled and page.locator('#'+labelled).count()==1
  active=page.evaluate("()=>({tag:document.activeElement.tagName,name:document.activeElement.name})");assert active['tag']=='INPUT' and active['name']=='name',active
  page.keyboard.press('Escape');page.wait_for_timeout(120);assert page.evaluate("()=>document.activeElement?.id")=='v20CreateStyle'
  # Preview activation is bound to the focused locator so unrelated delayed UI cannot steal it.
  preview=page.locator('#v20ResponsivePreview');preview.focus();page.wait_for_function("()=>document.activeElement?.id==='v20ResponsivePreview'");preview.press('Enter');pdlg=page.locator('dialog.v20-preview-dialog');pdlg.wait_for(state='visible');assert pdlg.get_attribute('aria-labelledby');assert pdlg.count()==1
  assert page.locator('[aria-label="Editor rendering"]').count()==1 and page.locator('[aria-label="Public rendering"]').count()==1
  page.keyboard.press('Escape');page.wait_for_timeout(120);assert page.evaluate("()=>document.activeElement?.id")=='v20ResponsivePreview'
  assert not errors,errors
  browser.close()
 print('V20_TYPOGRAPHY_ACCESSIBILITY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
