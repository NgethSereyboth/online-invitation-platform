#!/usr/bin/env python3
"""Validate bundled V20 WOFF2 metadata and load every face in real Chromium."""
from __future__ import annotations
import base64,hashlib,json
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 data=json.loads((ROOT/'typography-contract.json').read_text(encoding='utf-8'))
 css=(ROOT/'typography-fonts.css').read_text(encoding='utf-8')
 assert css.count('unicode-range:U+1780-17FF,U+19E0-19FF;')==4,css
 assert css.count('unicode-range:U+0000-024F,U+1E00-1EFF,U+2000-206F;')==4,css
 for khmer_id,latin_id in (('noto-serif-khmer','noto-serif'),('noto-sans-khmer','noto-sans')):
  stack=data['fonts'][khmer_id]['stack']
  assert stack.index(data['fonts'][latin_id]['family'])<stack.index('Khmer UI'),stack
 faces=[]
 from fontTools.ttLib import TTFont
 for font_id,meta in data['fonts'].items():
  assert meta['stableId']==font_id
  for weight,relative in meta.get('assets',{}).items():
   path=ROOT/relative;assert path.is_file() and path.stat().st_size>10_000,(font_id,weight)
   digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==meta['assetSha256'][weight]
   font=TTFont(path,lazy=True);assert 'name' in font and 'cmap' in font and 'head' in font
   mime=base64.b64encode(path.read_bytes()).decode('ascii')
   faces.append((font_id,meta['family'],str(weight),mime))
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V20_FONT_REGISTRY_LOADING',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V20_FONT_REGISTRY_LOADING',exc)
  page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  css=''.join(f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{encoded}) format('woff2');font-weight:{weight};font-style:normal;font-display:block}}" for _,family,weight,encoded in faces)
  page.set_content(f'<style>{css}</style><p id="latin">Typography system</p><p id="khmer">សូមស្វាគមន៍មកកាន់កម្ពុជា</p>',wait_until='load')
  results=page.evaluate("""async faces=>{const out=[];for(const [id,family,weight] of faces){await document.fonts.load(`${weight} 24px "${family}"`,'Typography សូមស្វាគមន៍');const loaded=document.fonts.check(`${weight} 24px "${family}"`,'Typography សូមស្វាគមន៍');const probe=document.createElement('span');probe.textContent=id.includes('khmer')?'សូមស្វាគមន៍កម្ពុជា':'Typography system';Object.assign(probe.style,{position:'fixed',left:'-9999px',fontFamily:`"${family}"`,fontWeight:weight,fontSize:'24px'});document.body.append(probe);out.push({id,weight,loaded,width:probe.getBoundingClientRect().width,status:[...document.fonts].find(x=>x.family.replaceAll('"','')===family&&String(x.weight)===String(weight))?.status||''});probe.remove()}return out}""",[(x[0],x[1],x[2]) for x in faces])
  assert len(results)==len(faces) and all(x['loaded'] and x['status']=='loaded' and x['width']>0 for x in results),results
  assert not errors,errors
  browser.close()
 print('V20_FONT_REGISTRY_LOADING_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
