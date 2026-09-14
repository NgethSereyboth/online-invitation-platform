#!/usr/bin/env python3
"""Chromium geometry regression for the public invitation at phone/tablet/desktop widths."""
from __future__ import annotations
import sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped,skipped
ROOT=Path(__file__).resolve().parents[1]

def main():
    try: from playwright.sync_api import sync_playwright
    except Exception as exc:
        return skipped('PUBLIC_LAYOUT_RUNTIME_NO_PLAYWRIGHT',exc)
    css=(ROOT/'styles.css').read_text(encoding='utf-8')+'\n'+(ROOT/'ux-refine.css').read_text(encoding='utf-8')
    html=f'''<!doctype html><html><head><style>{css}</style></head><body data-page="public"><main id="publicRoot" class="guest theme-rose template-rose">
    <section class="artistic-hero-section"><div class="published-artboard" style="height:844px;max-width:390px;margin:auto"></div></section>
    <section class="guest-hero guest-summary"><p class="invite-kicker">YOU ARE INVITED</p><div class="hero-date"><h2>27 December 2026</h2><p>ថ្ងៃអាទិត្យ</p></div></section>
    <section class="schedule-section"><h2>Schedule</h2><div class="schedule-list"><article><strong>4:00 PM</strong><span>Guest arrival · ទទួលភ្ញៀវ</span></article></div></section>
    <section class="venue-section"><h2>Venue</h2><div class="venue-card"><strong>Grand Ballroom</strong><p>Phnom Penh, Cambodia</p><p><a class="button-link" href="#">Open map</a></p></div></section>
    <div class="custom-blocks"><section class="custom-info-block"><h2>Our Story</h2><p>Safe responsive content.</p></section></div>
    <form id="rsvp"><h2>RSVP</h2><label>Name<input value="Guest"></label><button>Submit</button></form>
    </main></body></html>'''
    with sync_playwright() as p:
        try: browser=launch_chromium(p)
        except Exception as exc:
            return skipped('PUBLIC_LAYOUT_RUNTIME_NO_CHROMIUM',exc)
        for width in (390,768,1280,1440,1920,2560):
            page=browser.new_page(viewport={'width':width,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='load')
            metrics=page.evaluate('''()=>{const root=document.querySelector('#publicRoot'),rr=root.getBoundingClientRect();return {doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,root:{x:rr.x,w:rr.width,right:rr.right},display:getComputedStyle(root).display,grid:getComputedStyle(root).gridTemplateColumns,children:[...root.children].map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,x:r.x,right:r.right,w:r.width,scroll:e.scrollWidth,client:e.clientWidth}})}}''')
            assert not errors,(width,errors)
            assert metrics['display']=='block',(width,metrics)
            assert metrics['doc']<=width+1 and metrics['body']<=width+1,(width,metrics)
            assert abs(metrics['root']['x'])<1 and abs(metrics['root']['w']-width)<1.5,(width,metrics)
            for child in metrics['children']:
                assert child['x']>=-1 and child['right']<=width+1,(width,child)
                assert child['scroll']<=max(child['client']+2,width+2),(width,child)
            page.close()
        browser.close()
    print('PUBLIC_LAYOUT_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
