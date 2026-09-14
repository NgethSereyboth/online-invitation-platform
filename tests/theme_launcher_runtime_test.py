#!/usr/bin/env python3
"""Chromium regressions for theme-readable onboarding and workspace launcher dots."""
from __future__ import annotations
import importlib.util,re,sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def load_editor_builder():
    spec=importlib.util.spec_from_file_location('inline_runtime_builder',RUNTIME);assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor

def launcher_page(filename:str,mode:str)->str:
    html=(ROOT/filename).read_text(encoding='utf-8')
    # Preserve the real page shell but avoid page-specific API code; the launcher is installed by modern-ui.js.
    html=re.sub(r'<script\b[^>]*>[\s\S]*?</script>','',html,flags=re.I)
    css=[]
    for href in re.findall(r'<link\s+[^>]*href="([^"]+\.css)"[^>]*>',html,re.I):
        p=ROOT/href
        if p.exists():css.append(p.read_text(encoding='utf-8'))
    modern=(ROOT/'modern-ui.js').read_text(encoding='utf-8').replace('</script>','<\\/script>')
    prelude=f"""<script>const __m=new Map([['einvite-theme-mode','{mode}']]);const localStorage={{getItem:k=>__m.has(String(k))?__m.get(String(k)):null,setItem:(k,v)=>__m.set(String(k),String(v)),removeItem:k=>__m.delete(String(k))}};window.alert=()=>{{}};</script>"""
    html=re.sub(r'<link\s+[^>]*href="[^"]+\.css"[^>]*>','',html,flags=re.I)
    html=html.replace('</head>',f'{prelude}<style>{"".join(css)}</style></head>')
    html=html.replace('</body>',f'<script>{modern}</script></body>')
    return html

def rgb_tuple(value:str):
    nums=[float(x) for x in re.findall(r'[\d.]+',value)[:3]]
    return tuple(nums) if len(nums)==3 else (0,0,0)

def luminance(rgb):
    vals=[]
    for c in rgb:
        v=c/255
        vals.append(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)
    return .2126*vals[0]+.7152*vals[1]+.0722*vals[2]

def contrast(a,b):
    x,y=sorted((luminance(rgb_tuple(a)),luminance(rgb_tuple(b))),reverse=True)
    return (x+.05)/(y+.05)

def main()->int:
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('THEME_LAUNCHER_RUNTIME_NO_PLAYWRIGHT',exc)
    with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('THEME_LAUNCHER_RUNTIME_NO_CHROMIUM',exc)
        # Launcher is required on dashboard, editor, and a management page in both themes.
        for filename in ('dashboard.html','index.html','materials.html'):
            for mode in ('light','dark'):
                page=browser.new_page(viewport={'width':1280,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.set_content(launcher_page(filename,mode),wait_until='load');page.wait_for_timeout(120)
                dots=page.locator('.ui-app-launcher-button i')
                assert dots.count()==9,(filename,mode,dots.count(),errors)
                metrics=page.evaluate("""()=>[...document.querySelectorAll('.ui-app-launcher-button i')].map(i=>{const r=i.getBoundingClientRect(),s=getComputedStyle(i);return {w:r.width,h:r.height,display:s.display,bg:s.backgroundColor}})""")
                assert all(x['w']>=3 and x['h']>=3 and x['display']!='none' for x in metrics),(filename,mode,metrics)
                assert not errors,(filename,mode,errors)
                page.close()
        # The real editor onboarding must remain readable in light, dark, and system-resolved themes.
        editor_html=load_editor_builder()()
        for mode,resolved in (('light','light'),('dark','dark'),('system','dark')):
            page=browser.new_page(viewport={'width':1366,'height':900});page.emulate_media(reduced_motion='reduce')
            page.set_content(editor_html,wait_until='load');page.wait_for_timeout(900)
            page.evaluate("args=>{document.documentElement.dataset.theme=args.resolved;document.documentElement.dataset.themeMode=args.mode;document.documentElement.style.colorScheme=args.resolved}",{'mode':mode,'resolved':resolved});page.wait_for_timeout(420)
            if not page.locator('dialog.final-tour').is_visible():
                page.locator('.final-tour-trigger').click();page.wait_for_timeout(420)
            palette=page.evaluate("""()=>{const tour=document.querySelector('.final-tour'),card=document.querySelector('.final-tour-grid article'),title=document.querySelector('.final-tour h1'),body=document.querySelector('.final-tour>p'),strong=document.querySelector('.final-tour-grid strong'),muted=document.querySelector('.final-tour-grid span'),close=document.querySelector('.final-tour-close');return {tourBg:getComputedStyle(tour).backgroundColor,cardBg:getComputedStyle(card).backgroundColor,title:getComputedStyle(title).color,body:getComputedStyle(body).color,strong:getComputedStyle(strong).color,muted:getComputedStyle(muted).color,closeBg:getComputedStyle(close).backgroundColor,closeColor:getComputedStyle(close).color}}""")
            # Main and card text need strong contrast; muted text still needs readable UI contrast.
            assert contrast(palette['title'],palette['cardBg'])>=4.0,(mode,palette)
            assert contrast(palette['strong'],palette['cardBg'])>=4.0,(mode,palette)
            assert contrast(palette['body'],palette['cardBg'])>=3.0,(mode,palette)
            assert contrast(palette['muted'],palette['cardBg'])>=3.0,(mode,palette)
            assert contrast(palette['closeColor'],palette['closeBg'])>=3.0,(mode,palette)
            page.close()
        browser.close()
    print('THEME_LAUNCHER_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
