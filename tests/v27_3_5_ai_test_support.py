from __future__ import annotations
import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inline_html()->str:
 spec=importlib.util.spec_from_file_location('v27_3_5_inline',ROOT/'tests'/'inline_editor_runtime_test.py');assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()
def ready(page,width=1280,height=900):
 page.set_viewport_size({'width':width,'height':height});page.set_default_timeout(35_000);page.set_content(inline_html(),wait_until='load',timeout=45_000);page.wait_for_timeout(1800)
 if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
 page.wait_for_function('()=>window.EInviteAIActionService&&window.EInviteEditorBridge&&document.querySelector("#stage")')
def load_full_ai(page):
 page.add_style_tag(content=(ROOT/'ai-assistant-pro.css').read_text(encoding='utf-8'))
 page.add_script_tag(content=(ROOT/'ai-assistant-pro.js').read_text(encoding='utf-8'))
 page.wait_for_function('()=>window.EInviteAI&&document.querySelector("#eiAiDrawer")')
