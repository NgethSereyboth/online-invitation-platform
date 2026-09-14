#!/usr/bin/env python3
from __future__ import annotations
import sys,zipfile
from pathlib import Path
from browser_runtime import launch_chromium
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=launch_chromium(p);page=browser.new_page(viewport={'width':1280,'height':900});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(900)
  page.add_style_tag(path=str(ROOT/'export-quality-v24.css'));page.add_script_tag(path=str(ROOT/'export-quality-v24.js'));page.wait_for_timeout(80)
  with page.expect_download(timeout=30000) as info:page.evaluate("()=>EInviteCommandRegistry.execute('export.currentSvg')")
  svg=Path(info.value.path());assert svg.read_text(errors='ignore').lstrip().startswith('<svg')
  with page.expect_download(timeout=30000) as info:page.evaluate("()=>EInviteCommandRegistry.execute('export.projectBackup')")
  backup=Path(info.value.path()).read_text();assert '"schemaVersion": 24' in backup and '"document"' in backup
  with page.expect_download(timeout=60000) as info:page.evaluate("()=>EInviteCommandRegistry.execute('export.allPng')")
  archive=Path(info.value.path());assert zipfile.is_zipfile(archive)
  with zipfile.ZipFile(archive) as z:
   names=z.namelist();assert names and all(name.endswith('.png') for name in names),names
   assert all(len(z.read(name))>100 for name in names)
  assert not errors,errors
  browser.close()
 print('V24_EXPORT_QUALITY_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
