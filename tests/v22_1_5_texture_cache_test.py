#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')
def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V22_1_5_TEXTURE_CACHE',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V22_1_5_TEXTURE_CACHE',exc)
  try:
   page=browser.new_page();page.set_content('<canvas id=c width=64 height=64></canvas><canvas id=g width=64 height=64></canvas>');page.add_script_tag(content=src('tests/gpu_mock_webgl.js'));page.add_script_tag(content=src('gpu-texture-cache-v22.js'))
   result=page.evaluate('''async()=>{const gl=g.getContext('webgl2'),x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,64,64);const cache=EInviteGPUTextureCache.create(gl,{maxBytes:32768});const a=await cache.acquire('same',c),b=await cache.acquire('same',c);cache.release('same');cache.release('same');for(let i=0;i<12;i++){const q=document.createElement('canvas');q.width=q.height=512;const z=q.getContext('2d');z.fillStyle=`rgb(${i*40},20,80)`;z.fillRect(0,0,64,64);await cache.acquire('k'+i,q);cache.release('k'+i)}cache.evict();const d=cache.diagnostics();cache.destroy();return{same:a.texture===b.texture,d,after:cache.diagnostics()}}''')
   assert result['same'] is True,result
   assert result['d']['hits']>=1 and result['d']['misses']>=13,result
   assert result['d']['bytes']<=result['d']['maxBytes'] and result['d']['evictions']>=1,result
   assert result['after']['destroyed'] is True and result['after']['entries']==0,result
  finally:browser.close()
 print('V22_1_5_TEXTURE_CACHE_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
