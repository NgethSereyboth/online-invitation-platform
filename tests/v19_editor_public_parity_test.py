#!/usr/bin/env python3
"""Real Chromium editor/public typography geometry parity for V19.1."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
 spec=importlib.util.spec_from_file_location('inline_v19_1_parity',RUNTIME);assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V19_1_EDITOR_PUBLIC_PARITY',exc)
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V19_1_EDITOR_PUBLIC_PARITY',exc)
  page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(30_000);errors=[]
  page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'));page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
  page.set_content(build(),wait_until='load',timeout=40_000);page.wait_for_timeout(1800)
  if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
  page.wait_for_function('()=>window.EInviteRenderer&&window.EInviteProfessionalEditor?.version===17&&document.querySelector("#stage .object[data-id=subtitle]")')
  rows=[]
  short='សូមស្វាគមន៍ Welcome'
  long='សូមស្វាគមន៍មកកាន់ពិធីដ៏ពិសេសរបស់យើង។ Welcome to our joyful celebration with family and friends. '*5
  for columns in (1,2,3):
   for vertical in ('top','middle','bottom'):
    for kind,text in (('short',short),('overflow',long)):
     result=page.evaluate("""([columns,vertical,kind,text])=>new Promise(resolve=>{
       EInviteEditorBridge.transact('Parity typography',doc=>{const o=doc.objects.subtitle;o.html=text;o.font='noto-serif-khmer';o.fontSize=36;o.textAutoFit='fit';o.textAutoFitMax=48;o.textMinFontSize=8;o.textWrap='pretty';o.textColumns=columns;o.textColumnGap=14;o.textAlign='justify';o.textVerticalAlign=vertical;o.width='62%';o.height='150px'});EInviteEditorBridge.select(['subtitle']);
       setTimeout(()=>{const stage=document.querySelector('#stage'),editor=document.querySelector('#stage .object[data-id="subtitle"] .content'),er=editor.getBoundingClientRect();let mount=document.querySelector('#v19ParityMount');if(!mount){mount=document.createElement('div');mount.id='v19ParityMount';Object.assign(mount.style,{position:'fixed',left:'-5000px',top:'0',overflow:'hidden'});document.body.append(mount)}const sr=stage.getBoundingClientRect();Object.assign(mount.style,{width:`${sr.width}px`,height:`${sr.height}px`});mount.innerHTML=EInviteRenderer.renderObject(state.objects.subtitle,{id:'subtitle'});const pub=mount.firstElementChild;pub.style.position='absolute';EInviteRenderer.installResponsiveTypography(mount);setTimeout(()=>{const ef=editor.querySelector('.typography-flow'),pf=pub.querySelector('.typography-flow'),es=getComputedStyle(editor),ps=getComputedStyle(pub),efs=getComputedStyle(ef),pfs=getComputedStyle(pf);resolve({columns,vertical,kind,editorSize:parseFloat(es.fontSize),editorScale:sr.width/stage.offsetWidth,publicSize:parseFloat(ps.fontSize),editorColumns:efs.columnCount,publicColumns:pfs.columnCount,editorJustify:es.justifyContent,publicJustify:ps.justifyContent,editorAlign:es.textAlign,publicAlign:ps.textAlign,editorOverflowX:ef.scrollWidth-editor.clientWidth,editorOverflowY:ef.scrollHeight-editor.clientHeight,publicOverflowX:pf.scrollWidth-pub.clientWidth,publicOverflowY:pf.scrollHeight-pub.clientHeight,editorRect:[er.width,er.height],publicRect:[pub.getBoundingClientRect().width,pub.getBoundingClientRect().height]})},180)},180)
     })""",[columns,vertical,kind,text])
     rows.append(result)
  for r in rows:
   assert r['editorColumns']==str(r['columns']) and r['publicColumns']==str(r['columns']),r
   expected={'top':'flex-start','middle':'center','bottom':'flex-end'}[r['vertical']]
   assert r['editorJustify']==expected and r['publicJustify']==expected,r
   assert r['editorAlign']=='justify' and r['publicAlign']=='justify',r
   assert abs(r['editorSize']*r['editorScale']-r['publicSize'])<=1.2,r
   assert abs(r['editorRect'][0]-r['publicRect'][0])<=2 and abs(r['editorRect'][1]-r['publicRect'][1])<=2,r
   assert r['editorOverflowX']<=3 and r['editorOverflowY']<=3 and r['publicOverflowX']<=3 and r['publicOverflowY']<=3,r
  assert len(rows)==18 and not errors,errors
  browser.close()
 print('V19_1_EDITOR_PUBLIC_PARITY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
