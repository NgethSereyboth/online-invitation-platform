#!/usr/bin/env python3
"""Chromium geometry and editing coverage for the V16 Windows/UI release."""
from __future__ import annotations
import importlib.util,sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'tests'/'inline_editor_runtime_test.py'

def builder():
    spec=importlib.util.spec_from_file_location('inline_runtime_builder_v16',RUNTIME);assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.build_inline_editor

def dismiss(page):
    if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():
        page.locator('#finalTourDismiss').click();page.wait_for_timeout(100)

def metrics(page):
    return page.evaluate("""()=>{const box=s=>{const e=document.querySelector(s);if(!e||getComputedStyle(e).display==='none')return null;const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};const intersects=(a,b)=>!!a&&!!b&&Math.min(a.right,b.right)>Math.max(a.x,b.x)&&Math.min(a.bottom,b.bottom)>Math.max(a.y,b.y);const toolbar=document.querySelector('.stage-wrap>.studio-canvas-toolbar');const visible=[...(toolbar?.children||[])].filter(e=>getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0).map(e=>{const r=e.getBoundingClientRect();return{tag:e.tagName,id:e.id,cls:e.className,x:r.x,right:r.right,y:r.y,bottom:r.bottom}});const track=document.querySelector('.workflow-page-dock-track'),active=track?.querySelector('.workflow-page-chip.active');const tr=track?.getBoundingClientRect(),ar=active?.getBoundingClientRect();return{vw:innerWidth,docScroll:document.documentElement.scrollWidth,toolbar:box('.stage-wrap>.studio-canvas-toolbar'),toolbarScroll:toolbar?.scrollWidth||0,toolbarClient:toolbar?.clientWidth||0,toolbarChildren:visible,viewport:box('#canvasViewport'),frame:box('#canvasFrame'),dock:box('#workflowPageDock'),track:tr?{x:tr.x,right:tr.right,y:tr.y,bottom:tr.bottom}:null,active:ar?{x:ar.x,right:ar.right,y:ar.y,bottom:ar.bottom}:null,inspector:box('aside.right'),more:box('#v16ToolbarMore'),timeline:box('#eiTimelineLaunch'),focus:box('#eiFocusToggle'),style:box('.ei-experience-launch'),bottom:box('#mobileEditorV14Bar'),toolRailScrollbar:getComputedStyle(document.querySelector('.ei-tool-rail')).scrollbarWidth,overlapDockFrame:intersects(box('#workflowPageDock'),box('#canvasFrame')),overlapMoreInspector:intersects(box('#v16ToolbarMore'),box('aside.right'))}}""")

def validate(page,width,height):
    page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(350);m=metrics(page)
    assert m['docScroll']<=width+1,(width,height,m)
    assert m['dock'] and m['dock']['x']>=-1 and m['dock']['right']<=width+1,(width,height,m)
    assert m['track'] and m['active'],(width,height,m)
    assert m['active']['right']>m['track']['x'] and m['active']['x']<m['track']['right'],(width,height,m)
    # The scrollable artboard may be taller than its viewport, but the dock is
    # a reserved flex row after the viewport and cannot cover the visible area.
    assert m['dock']['y']>=m['viewport']['bottom']-1,(width,height,m)
    if width>640:
        assert m['more'] and not m['overlapMoreInspector'],(width,height,m)
        assert m['toolbarScroll']<=m['toolbarClient']+2,(width,height,m)
        for child in m['toolbarChildren']:
            assert child['x']>=m['toolbar']['x']-1 and child['right']<=m['toolbar']['right']+1,(width,height,child,m)
        assert all(item is None or item['w']==0 or item['h']==0 for item in (m['focus'],m['style'],m['timeline'])),(width,height,m)
    else:
        assert m['bottom'] and m['bottom']['x']>=-1 and m['bottom']['right']<=width+1 and m['bottom']['bottom']<=height+1,(width,height,m)
        assert m['toolRailScrollbar']=='none',(width,height,m)

def main()->int:
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V16_BROWSER_GEOMETRY_NO_PLAYWRIGHT',exc)
    html=builder()()
    with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('V16_BROWSER_GEOMETRY_NO_CHROMIUM',exc)
        page=browser.new_page(viewport={'width':1440,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(f'PAGE:{e}'))
        page.on('console',lambda m:errors.append(f'CONSOLE:{m.text}') if m.type=='error' else None)
        page.set_content(html,wait_until='load',timeout=30_000);page.wait_for_timeout(1800);dismiss(page)
        page.locator('[data-studio-tab="elements"]').click();page.wait_for_timeout(120)
        for width,height in ((1440,900),(390,844),(360,800),(430,932)):
            validate(page,width,height)
        # Dynamic resize without a reload must restore the desktop shell.
        validate(page,1440,900);validate(page,390,844);validate(page,1440,900)
        page.locator('#previewBtn').click();page.wait_for_selector('#modal[open]')
        close_hit=page.evaluate("""()=>{const e=document.querySelector('#modal[open]>.close'),r=e?.getBoundingClientRect();if(!e||!r)return false;const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return hit===e}""")
        assert close_hit,'Guest preview opening cover intercepts the close button'
        page.locator('#modal>.close').click();page.wait_for_selector('#modal:not([open])',state='attached')
        # Real English and Khmer input/edit capture remains intact after responsive transitions.
        page.locator('[data-studio-tab="event"]').click();page.wait_for_timeout(120)
        page.locator('#names').fill('V16 English Invitation')
        page.locator('#namesKm').fill('ការអញ្ជើញ វី១៦')
        page.wait_for_timeout(300)
        captured=page.evaluate("()=>({en:capture().fields.names,km:capture().fields.namesKm})")
        assert captured=={'en':'V16 English Invitation','km':'ការអញ្ជើញ វី១៦'},captured
        assert not errors,errors[:10]
        page.close();browser.close()
    print('V16_BROWSER_GEOMETRY_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
