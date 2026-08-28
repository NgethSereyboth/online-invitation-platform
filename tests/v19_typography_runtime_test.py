#!/usr/bin/env python3
"""Real Chromium V19 advanced typography persistence and rendering test."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def build():
    spec=importlib.util.spec_from_file_location('inline_v19_typography',RUNTIME);assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor()

def main()->int:
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V19_TYPOGRAPHY_RUNTIME',exc)
    html=build()
    with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('V19_TYPOGRAPHY_RUNTIME',exc)
        page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(25_000);errors=[]
        page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'))
        page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
        page.set_content(html,wait_until='load',timeout=30_000);page.wait_for_timeout(1800)
        if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
        page.wait_for_function('()=>window.EInviteProfessionalEditor?.version===17&&document.querySelector("#textAutoFit")')
        page.evaluate("()=>{EInviteEditorBridge.select(['subtitle']);document.querySelector('[data-inspector-tab=\"object\"]')?.click()}");page.wait_for_timeout(180)
        long_text='សូមស្វាគមន៍មកកាន់ពិធីដ៏ពិសេសរបស់យើង។ Welcome to our joyful celebration with family and friends. សូមអរគុណចំពោះវត្តមានដ៏មានតម្លៃរបស់លោកអ្នក។'
        page.locator('#textContent').fill(long_text)
        page.select_option('#font','sans-arial')
        page.select_option('#textAlign','justify')
        page.select_option('#textWrap','pretty')
        page.select_option('#textColumns','2')
        page.locator('#textColumnGap').fill('18')
        page.select_option('#textAutoFit','fit')
        page.locator('#textMinFontSize').fill('12')
        page.wait_for_timeout(650)
        initial=page.evaluate("""()=>{const o=document.querySelector('#stage .object[data-id="subtitle"]'),c=o.querySelector('.content'),f=c.querySelector('.typography-flow'),d=state.objects.subtitle;return{fontSize:Number(c.dataset.textComputedFontSize||getComputedStyle(c).fontSize.replace('px','')),max:Number(o.dataset.textAutoFitMax),min:Number(o.dataset.textMinFontSize),fontId:d.font,font:getComputedStyle(c).fontFamily,columns:getComputedStyle(f).columnCount,gap:getComputedStyle(f).columnGap,wrap:getComputedStyle(f).textWrap,align:getComputedStyle(c).textAlign,saved:Number(d.fontSize),state:{textAutoFit:d.textAutoFit,textMinFontSize:d.textMinFontSize,textWrap:d.textWrap,textColumns:d.textColumns,textColumnGap:d.textColumnGap,textAlign:d.textAlign}}}""")
        assert initial['min']==12 and 12<=initial['fontSize']<=initial['max'],initial
        assert initial['fontId']=='sans-arial' and 'EInvite Noto Sans Khmer' in initial['font'],initial
        assert initial['columns']=='2' and initial['align']=='justify',initial
        assert initial['state']=={'textAutoFit':'fit','textMinFontSize':12,'textWrap':'pretty','textColumns':2,'textColumnGap':18,'textAlign':'justify'},initial
        page.evaluate("""()=>{EInviteEditorBridge.transact('V19 narrow text box',doc=>{doc.objects.subtitle.width='34%';doc.objects.subtitle.height='88px'});EInviteEditorBridge.select(['subtitle'])}""");page.wait_for_timeout(700)
        narrowed=page.evaluate("()=>{const c=document.querySelector('#stage .object[data-id=\"subtitle\"] .content');return{fontSize:Number(c.dataset.textComputedFontSize||parseFloat(getComputedStyle(c).fontSize)),saved:Number(state.objects.subtitle.fontSize),max:Number(state.objects.subtitle.textAutoFitMax),html:state.objects.subtitle.html}}")
        assert 12<=narrowed['fontSize']<=initial['fontSize'] and narrowed['saved']==initial['saved'] and narrowed['max']==initial['max'],narrowed
        assert 'សូមស្វាគមន៍' in narrowed['html']
        rendered=page.evaluate("()=>EInviteRenderer.renderObject(state.objects.subtitle,{id:'subtitle'})")
        for token in ('data-typography-v19="true"','text-align:justify','column-count:2','column-gap:18px','text-wrap:pretty','data-font="sans-arial"','EInvite Noto Sans Khmer'):
            assert token in rendered,(token,rendered[:500])
        page.keyboard.press('Control+z');page.wait_for_timeout(320)
        undo=page.evaluate("()=>({width:state.objects.subtitle.width,auto:state.objects.subtitle.textAutoFit,columns:state.objects.subtitle.textColumns})")
        page.keyboard.press('Control+y');page.wait_for_timeout(320)
        redo=page.evaluate("()=>({width:state.objects.subtitle.width,auto:state.objects.subtitle.textAutoFit,columns:state.objects.subtitle.textColumns})")
        assert undo['auto']=='fit' and undo['columns']==2 and redo['auto']=='fit' and redo['columns']==2,(undo,redo)
        assert undo['width']!=redo['width'],(undo,redo)
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(420)
        page.locator('#mobileQuickMode').click();page.locator('#textAutoFit').scroll_into_view_if_needed();page.wait_for_timeout(80)
        mobile=page.evaluate("""()=>{const ids=['textAutoFit','textMinFontSize','textWrap','textColumns','textColumnGap','fitTextNow'];return ids.map(id=>{const e=document.getElementById(id),r=e?.getBoundingClientRect();return{id,w:r?.width||0,h:r?.height||0,visible:!!e&&getComputedStyle(e).display!=='none'&&r.width>0&&r.height>0}})}""")
        assert all(item['visible'] for item in mobile),mobile
        assert not errors,errors[:20]
        page.close();browser.close()
    print('V19_TYPOGRAPHY_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
