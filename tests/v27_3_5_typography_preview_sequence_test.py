#!/usr/bin/env python3
"""Stress the V20 preview after the preceding typography interaction sequence."""
from __future__ import annotations
import importlib.util,json
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py';ART=ROOT/'test-artifacts'/'v27_3_5_preview_sequence'
def build():
 spec=importlib.util.spec_from_file_location('inline_v27_3_5_preview',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def evidence(page,errors,console):
 ART.mkdir(parents=True,exist_ok=True)
 try:page.screenshot(path=str(ART/'failure.png'),full_page=True)
 except Exception:pass
 info=page.evaluate("""()=>({active:document.activeElement?{tag:document.activeElement.tagName,id:document.activeElement.id,cls:document.activeElement.className,aria:document.activeElement.getAttribute('aria-label')}:null,dialogs:[...document.querySelectorAll('dialog')].map(d=>({class:d.className,open:d.open,hidden:d.hidden,text:(d.textContent||'').slice(0,300)})),excerpt:document.body.innerHTML.slice(0,12000)})""")
 (ART/'failure.json').write_text(json.dumps({'runtime':info,'pageErrors':errors,'consoleErrors':console},ensure_ascii=False,indent=2),encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V27_3_5_TYPOGRAPHY_PREVIEW_SEQUENCE',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V27_3_5_TYPOGRAPHY_PREVIEW_SEQUENCE',exc)
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(35_000);errors=[];console=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
  try:
   page.set_content(build(),wait_until='load',timeout=45_000);page.wait_for_timeout(1800)
   if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
   page.wait_for_function('()=>window.EInviteTypographyV20&&document.querySelector("#v20ResponsivePreview")')
   page.evaluate("()=>EInviteEditorBridge.select(['title'])")
   for control,key in [('#v20ToolbarBold','Enter'),('#v20ToolbarItalic','Space')]:
    loc=page.locator(control);loc.focus();page.wait_for_function(f"()=>document.activeElement?.id==='{control[1:]}'");loc.press(key);page.wait_for_timeout(80)
   trigger=page.locator('#v20CreateStyle');trigger.focus();trigger.press('Enter');page.locator('dialog.v20-dialog').wait_for(state='visible');page.keyboard.press('Escape');page.wait_for_function("()=>document.activeElement?.id==='v20CreateStyle'")
   for index in range(10):
    preview=page.locator('#v20ResponsivePreview');preview.focus();page.wait_for_function("()=>document.activeElement?.id==='v20ResponsivePreview'");preview.press('Enter')
    dlg=page.locator('dialog.v20-preview-dialog');dlg.wait_for(state='visible');assert dlg.count()==1,(index,dlg.count());page.keyboard.press('Escape');dlg.wait_for(state='detached');page.wait_for_function("()=>document.activeElement?.id==='v20ResponsivePreview'")
   assert not errors,errors;assert not console,console
  except Exception:
   evidence(page,errors,console);raise
  finally:browser.close()
 print('V27_3_5_TYPOGRAPHY_PREVIEW_SEQUENCE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
