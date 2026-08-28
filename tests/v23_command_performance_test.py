#!/usr/bin/env python3
from __future__ import annotations
import sys
from inline_editor_runtime_test import build_inline_editor
from browser_runtime import launch_chromium

def main()->int:
 try:
  from playwright.sync_api import sync_playwright
 except Exception as exc:
  print('V23_COMMAND_PERFORMANCE_SKIPPED_NO_PLAYWRIGHT',exc);return 0
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:
   print('V23_COMMAND_PERFORMANCE_SKIPPED_NO_CHROMIUM',exc);return 0
  page=browser.new_page(viewport={'width':1280,'height':900})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(build_inline_editor(),wait_until='load',timeout=30000);page.wait_for_timeout(1400)
  result=page.evaluate("""()=>{
   const bindings=EInviteShortcutManager.bindings;
   let t=performance.now();for(let i=0;i<100000;i++)bindings.get(i%2?'Mod+D':'Shift+F');const lookup=performance.now()-t;
   const batch=Array.from({length:200},(_,i)=>({id:`bench.${i}`,title:`Benchmark ${i}`,run:()=>true}));
   t=performance.now();const cleanup=EInviteCommandRegistry.registerMany(batch);const registration=performance.now()-t;
   t=performance.now();for(let i=0;i<1000;i++)window.dispatchEvent(new KeyboardEvent('keydown',{key:'F24',bubbles:true}));const ignoredEvents=performance.now()-t;
   cleanup.forEach(fn=>fn());
   return {lookup,registration,ignoredEvents,commands:EInviteCommandRegistry.list({includeHidden:true}).length,conflicts:EInviteCommandRegistry.conflicts.length};
  }""")
  assert result['lookup']<80,result
  assert result['registration']<80,result
  assert result['ignoredEvents']<150,result
  assert result['conflicts']==0,result
  assert not errors,errors[:5]
  browser.close()
 print('V23_COMMAND_PERFORMANCE_RESULT',result)
 print('V23_COMMAND_PERFORMANCE_TEST_PASSED')
 return 0
if __name__=='__main__':sys.exit(main())
