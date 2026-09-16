import importlib.util
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inline',ROOT/'tests/inline_editor_runtime_test.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with sync_playwright() as p:
 b=launch_chromium(p)
 for name,vp in [('desktop',{'width':1440,'height':1000}),('mobile',{'width':430,'height':900})]:
  q=b.new_page(viewport=vp);q.set_content(m.build_inline_editor(),wait_until='load');q.wait_for_timeout(1200)
  if q.locator('#finalTourDismiss').count() and q.locator('#finalTourDismiss').is_visible():q.locator('#finalTourDismiss').click()
  q.add_style_tag(content=(ROOT/'page-experience-v22.css').read_text());q.add_script_tag(content=(ROOT/'page-experience-v22.js').read_text());q.wait_for_function("()=>EInvitePageExperience?.version==='22.2.8'")
  q.evaluate("()=>{EInvitePageExperience.addPage({mode:'event-template',role:'title'});EInvitePageExperience.addPage({mode:'free-design'});EInvitePageExperience.addPage({mode:'event-template',role:'details'})}");q.wait_for_timeout(700)
  q.locator('[data-studio-tab="pages"]').click();q.wait_for_timeout(500)
  q.screenshot(path=f'/mnt/data/v22_2_{name}.png',full_page=False)
  q.close()
 b.close()
