#!/usr/bin/env python3
"""Chromium coverage for the V13 studio, timeline, photo and public privacy layers."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]

STORAGE="""
const __s=()=>{const m=new Map();return{getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),clear:()=>m.clear()}};
Object.defineProperty(window,'localStorage',{value:__s()});Object.defineProperty(window,'sessionStorage',{value:__s()});
"""
DOC={
 "schemaVersion":13,
 "fields":{"names":"V13 Celebration","date":"2027-05-12","time":"10:00","venue":"Phnom Penh"},
 "objects":{},"designPages":[],"sectionOrder":["events","guest-info","wishes"],
 "settings":{"openingEnabled":False,"rsvpEnabled":False,"wishesEnabled":True,"musicEnabled":False},
 "events":[{"id":"ceremony","name":"Main Ceremony","type":"ceremony","date":"2027-05-12","time":"10:00","venue":"Royal Hall","mapUrl":"https://maps.google.com","enabled":True}],
 "guestExperience":{"dressCode":"Formal","paymentLink":"https://example.com/pay","paymentLabel":"Gift contribution"},
 "privacy":{"analyticsConsentRequired":True,"externalMediaConsentRequired":True},
 "studioBrand":{"name":"ignored"},
 "timeline":{"duration":3000,"tracks":{},"markers":[]},
}

def inline_public():
    html=(ROOT/'public.html').read_text(encoding='utf-8')
    for k,v in {
      '__INVITATION_SLUG__':'v13-browser','__INVITATION_TITLE__':'V13 Celebration','__INVITATION_DESCRIPTION__':'Invitation',
      '__INVITATION_OG_IMAGE__':'social.png','__INVITATION_OG_TYPE__':'image/png','__INVITATION_PUBLIC_URL__':'v13-browser'
    }.items(): html=html.replace(k,v)
    html=re.sub(r'<link rel="stylesheet" href="([^"]+)">',lambda m:'<style>'+(ROOT/m.group(1).lstrip('/')).read_text(encoding='utf-8')+'</style>',html)
    html=re.sub(r'<script src="([^"]+)"></script>',lambda m:'<script>'+(ROOT/m.group(1).lstrip('/')).read_text(encoding='utf-8')+'</script>',html)
    payload=json.dumps({"invitationId":"i-v13","publicationId":"p-v13","version":1,"document":DOC,"guest":None,"analyticsConsentRequired":True,"externalMediaConsentRequired":True,"studioBrand":{"name":"Khmer Studio","hidePlatformBrand":True}},ensure_ascii=False)
    fetch=STORAGE+"window.fetch=async function(url,opts){url=String(url);if(url.includes('/api/public/v13-browser/view'))return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/api/public/v13-browser'))return new Response("+json.dumps(payload)+",{status:200,headers:{'Content-Type':'application/json'}});return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}})};"
    html=html.replace('</head>','<script>'+fetch+'</script></head>')
    return html.replace('__INVITATION_SLUG__','v13-browser')

def main():
    try: from playwright.sync_api import sync_playwright
    except Exception as exc: return skipped('V13_BROWSER_RUNTIME',exc)
    with sync_playwright() as p:
        try: browser=launch_chromium(p)
        except Exception as exc: return skipped('V13_BROWSER_RUNTIME',exc)
        context=browser.new_context(viewport={'width':1440,'height':900})
        editor=context.new_page();errors=[];editor.on('pageerror',lambda e:errors.append(str(e)))
        editor.set_content(build_inline_editor(),wait_until='load');editor.wait_for_timeout(1200)
        if editor.locator('#finalTourDismiss').count() and editor.locator('#finalTourDismiss').is_visible(): editor.locator('#finalTourDismiss').click()
        assert editor.locator('#v13OperationsBtn').count()==1
        assert editor.locator('#eiTimelineLaunch').count()==1
        assert editor.locator('#eiSharedStylesV13').count()==1
        assert editor.evaluate("()=>window.EInviteEditorBridge?.getState?.().schemaVersion")>=13
        assert editor.evaluate("()=>!!window.EInviteEditorBridge?.getState?.().sceneGraph")
        assert editor.evaluate("()=>Array.isArray(window.EInviteEditorBridge?.getState?.().sharedStyles?.text)")
        editor.wait_for_function("()=>window.EInviteBackend?.state?.status==='offline'",timeout=5000)
        assert editor.locator('#v13OperationsBtn').is_disabled()
        assert 'full application server' in (editor.locator('#v13OperationsBtn').get_attribute('title') or '').lower()
        assert not editor.locator('#v13OperationsDialog').evaluate('d=>d.open')
        editor.locator('#v16ToolbarMore summary').click();editor.locator('#v16ToolbarMore #eiTimelineLaunch').click();assert editor.locator('#eiTimeline').is_visible()
        assert editor.locator('[data-tl-range-start]').count()==1 and editor.locator('[data-tl-range-end]').count()==1
        editor.locator('[data-tl-close]').click();assert editor.locator('#eiTimeline').is_hidden()
        # Theme surfaces remain readable.
        for theme in ('dark','light'):
            editor.evaluate('t=>document.documentElement.dataset.theme=t',theme)
            if not editor.locator('#v16ToolbarMore').evaluate('el=>el.open'):
                editor.locator('#v16ToolbarMore summary').click()
            colors=editor.locator('#v16ToolbarMore #v13OperationsBtn').evaluate("el=>({c:getComputedStyle(el).color,b:getComputedStyle(el).backgroundColor})")
            assert colors['c']!=colors['b'],(theme,colors)
        assert editor.evaluate('document.documentElement.scrollWidth-innerWidth')<=3
        assert not errors,errors

        mobile=context.new_page();merr=[];mobile.on('pageerror',lambda e:merr.append(str(e)));mobile.set_viewport_size({'width':390,'height':844});mobile.set_content(build_inline_editor(),wait_until='load');mobile.wait_for_timeout(1000)
        if mobile.locator('#finalTourDismiss').count() and mobile.locator('#finalTourDismiss').is_visible(): mobile.locator('#finalTourDismiss').click()
        assert mobile.evaluate('document.documentElement.scrollWidth-innerWidth')<=3
        assert mobile.locator('#v13OperationsBtn').count()==1 and mobile.locator('#eiTimelineLaunch').count()==1
        assert not merr,merr

        public=context.new_page();perr=[];public.on('pageerror',lambda e:perr.append(str(e)));public.set_viewport_size({'width':390,'height':844});public.set_content(inline_public(),wait_until='load');public.wait_for_timeout(700)
        assert public.locator('#rsvp').count()==0
        assert public.get_by_text('Main Ceremony',exact=False).count()>=1
        assert public.get_by_text('Gift contribution',exact=False).count()>=1
        assert public.locator('[data-event-calendar]').count()==1
        assert public.locator('.guest-consent-banner').count()>=1
        assert public.evaluate('document.documentElement.scrollWidth-innerWidth')<=3
        public.emulate_media(reduced_motion='reduce');public.wait_for_timeout(50)
        reduced=public.evaluate("()=>matchMedia('(prefers-reduced-motion: reduce)').matches")
        assert reduced is True
        assert not perr,perr
        public.close();mobile.close();editor.close();context.close();browser.close()
    print('V13_BROWSER_RUNTIME_TEST_PASSED');return 0

if __name__=='__main__':raise SystemExit(main())
