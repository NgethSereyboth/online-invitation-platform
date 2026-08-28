#!/usr/bin/env python3
"""V19.1 typography inspector, thumbnail and mobile transform geometry."""
from __future__ import annotations
import importlib.util,itertools
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v19_1_geometry',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def overlap(a,b):return max(0,min(a['right'],b['right'])-max(a['left'],b['left']))*max(0,min(a['bottom'],b['bottom'])-max(a['top'],b['top']))

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V19_1_TYPOGRAPHY_VISUAL_GEOMETRY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V19_1_TYPOGRAPHY_VISUAL_GEOMETRY',exc)
  page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(30_000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=40_000);page.wait_for_timeout(1700)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.evaluate("()=>{EInviteEditorBridge.select(['subtitle']);document.querySelector('[data-inspector-tab=object]')?.click();document.querySelector('#advancedTextLayout').open=true}");page.wait_for_timeout(220)
  desktop=page.evaluate("""()=>{const a=document.querySelector('#advancedTextLayout').getBoundingClientRect(),g=document.querySelector('#typographyControls').getBoundingClientRect(),fields=[...document.querySelectorAll('#advancedTextLayout input,#advancedTextLayout select,#advancedTextLayout button')].map(e=>e.getBoundingClientRect().height);return{a:{x:a.x,w:a.width},g:{x:g.x,w:g.width},gridColumn:getComputedStyle(document.querySelector('#advancedTextLayout')).gridColumn,fields}}""")
  assert desktop['a']['w']>=desktop['g']['w']*.9 and desktop['a']['w']>180 and desktop['gridColumn'] in ('1 / -1','1 / -1'),desktop
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(350);page.locator('#mobileQuickMode').click();page.locator('#advancedTextLayout').scroll_into_view_if_needed();page.evaluate("()=>document.querySelector('#advancedTextLayout').open=true");page.wait_for_timeout(180)
  mobile=page.evaluate("""()=>{const a=document.querySelector('#advancedTextLayout').getBoundingClientRect(),sheet=document.querySelector('#mobileQuickInspector').getBoundingClientRect(),controls=document.querySelector('#typographyControls').getBoundingClientRect(),fields=[...document.querySelectorAll('#advancedTextLayout input,#advancedTextLayout select,#advancedTextLayout button')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height}).map(e=>({id:e.id,h:e.getBoundingClientRect().height}));return{a:{x:a.x,w:a.width},sheet:{x:sheet.x,w:sheet.width},controls:{x:controls.x,w:controls.width},fields}}""")
  assert mobile['a']['w']>=mobile['controls']['w']*.9 and mobile['a']['w']>260,mobile
  assert all(x['h']>=44 for x in mobile['fields']),mobile
  page.locator('#mobileQuickMode').click();page.wait_for_timeout(180)
  # Normal objects retain all nine 44px targets and 14px visual knobs.
  normal=page.evaluate("""()=>{EInviteEditorBridge.transact('Normal mobile geometry',d=>{d.objects.subtitle.width='55%';d.objects.subtitle.height='100px'});EInviteEditorBridge.select(['subtitle']);return new Promise(r=>setTimeout(()=>r([...document.querySelectorAll('#peSelectionBox [data-pe-handle]')].map(e=>{const b=e.getBoundingClientRect(),p=getComputedStyle(e,'::before');return{id:e.dataset.peHandle,w:b.width,h:b.height,vw:parseFloat(p.width),vh:parseFloat(p.height)}})),220))}""")
  assert len(normal)==9 and all(x['w']>=44 and x['h']>=44 and 10<=x['vw']<=14 and 10<=x['vh']<=14 for x in normal),normal
  tiny=page.evaluate("""()=>{EInviteEditorBridge.transact('Tiny mobile geometry',d=>{d.objects.subtitle.width='30px';d.objects.subtitle.height='30px'});EInviteEditorBridge.select(['subtitle']);return new Promise(r=>setTimeout(()=>r({tiny:document.querySelector('#peSelectionBox').classList.contains('pe-tiny-selection'),rects:[...document.querySelectorAll('#peSelectionBox [data-pe-handle]')].map(e=>{const b=e.getBoundingClientRect();return{id:e.dataset.peHandle,left:b.left,top:b.top,right:b.right,bottom:b.bottom,w:b.width,h:b.height}})}),220))}""")
  assert tiny['tiny'] and len(tiny['rects'])==9 and all(r['w']>=44 and r['h']>=44 for r in tiny['rects']),tiny
  for a,b in itertools.combinations(tiny['rects'],2):assert overlap(a,b)<=1,(a,b,overlap(a,b))
  thumb=page.evaluate("""()=>{state.designPages=[{id:'v19thumb',name:'Typography thumbnail',enabled:true,objects:{text:{type:'text',html:'សូមស្វាគមន៍ Welcome',font:'noto-serif-khmer',fontSize:80,fontWeight:'700',fontStyle:'italic',textAlign:'justify',textWrap:'pretty',textColumns:2,textColumnGap:20,letterSpacing:2,lineHeight:1.6,left:'5%',top:'5%',width:'85%',height:'180px'}}}];renderPageNavigator();return new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>{const e=document.querySelector('.page-nav-card:not(.hero-card) .typography-thumbnail-source [data-object-id=\"text\"]'),s=getComputedStyle(e),f=getComputedStyle(e.querySelector('.typography-flow'));resolve({font:s.fontFamily,size:parseFloat(s.fontSize),weight:s.fontWeight,style:s.fontStyle,align:s.textAlign,wrap:f.textWrap,columns:f.columnCount,gap:f.columnGap,letter:s.letterSpacing,line:s.lineHeight,faithful:!!e})}))) }""")
  assert 'EInvite Noto Serif Khmer' in thumb['font'] and thumb['size']>=10,thumb
  assert thumb['weight']=='700' and thumb['style']=='italic' and thumb['align']=='justify' and thumb['columns']=='2',thumb
  assert not errors,errors
  browser.close()
 print('V19_1_TYPOGRAPHY_VISUAL_GEOMETRY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
