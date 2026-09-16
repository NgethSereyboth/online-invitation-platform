#!/usr/bin/env python3
"""Browser regression for real public invitation markup: lunar date, optional RSVP and tap-start YouTube music."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from browser_runtime import launch_chromium,skipped,skipped
ROOT=Path(__file__).resolve().parents[1]

def build_public(payload:dict)->str:
    html=(ROOT/'public.html').read_text(encoding='utf-8')
    html=html.replace('__INVITATION_SLUG__','feature-test').replace('__INVITATION_TITLE__','Feature test').replace('__INVITATION_DESCRIPTION__','Feature test invitation')
    css=(ROOT/'styles.css').read_text(encoding='utf-8')+'\n'+(ROOT/'ux-refine.css').read_text(encoding='utf-8')
    html=re.sub(r'<link\s+[^>]*href="(?:/styles\.css|ux-refine\.css)"[^>]*>','',html,flags=re.I)
    html=html.replace('</head>',f'<style>{css}</style></head>')
    # The production route lazy-loads this library after document inspection.
    # The opaque-origin fixture cannot fetch relative scripts, so preinstall the
    # exact local library while separate contracts verify the deferred loader.
    moment=(ROOT/'vendor/momentkh.js').read_text(encoding='utf-8').replace('</script>',r'<\/script>')
    html=html.replace('</head>',f'<script>{moment}</script></head>')
    # Public executable code is external under the strict CSP. Inline every local
    # runtime module in this opaque-origin fixture so this regression continues to
    # exercise the real public renderer without requiring an HTTP server.
    html=re.sub(
        r'<script src="([^"]+)"></script>',
        lambda m:'<script>'+((ROOT/m.group(1).lstrip('/')).read_text(encoding='utf-8').replace('</script>','<\\/script>'))+'</script>',
        html,
    )
    html=html.replace('__INVITATION_SLUG__','feature-test')
    # set_content() uses an opaque origin where native sessionStorage is blocked;
    # substitute a tiny test-only store after all modules have been inlined.
    html=html.replace('sessionStorage.getItem(', 'window.__testSessionStorage.getItem(').replace('sessionStorage.setItem(', 'window.__testSessionStorage.setItem(')
    data=json.dumps(payload,ensure_ascii=False).replace('</script>','<\\/script>')
    prelude=f'''<script>
window.__publicPayload={data};window.__rsvpCalls=[];window.__testSessionStorage={{getItem:()=>null,setItem:()=>{{}}}};
window.fetch=async(url,options={{}})=>{{
 const value=String(url);
 if(value.includes('/api/public/feature-test/rsvps')){{window.__rsvpCalls.push(JSON.parse(options.body||'{{}}'));return new Response(JSON.stringify({{id:'rsvp-1',saved:true}}),{{status:201,headers:{{'Content-Type':'application/json'}}}})}}
 if(value.includes('/api/public/feature-test'))return new Response(JSON.stringify(window.__publicPayload),{{status:200,headers:{{'Content-Type':'application/json'}}}});
 return new Response(JSON.stringify({{error:'not mocked'}}),{{status:404,headers:{{'Content-Type':'application/json'}}}})
}};
</script>'''
    return html.replace('<body data-page="public">','<body data-page="public">'+prelude,1)

def payload(*,rsvp:bool)->dict:
    return {'document':{
        'eventType':'Wedding','theme':'rose','languageMode':'both','dateFormat':'both',
        'fields':{'names':'Sophea & Dara','namesKm':'សុភា និង ដារ៉ា','date':'2026-12-27','time':'16:00','venue':'Phnom Penh','venueKm':'ភ្នំពេញ','message':'Join us','messageKm':'សូមគោរពអញ្ជើញ'},
        'objects':{},'designPages':[],'sectionOrder':['rsvp'],
        'settings':{'rsvpEnabled':rsvp,'musicEnabled':True,'openingEnabled':True,'scheduleEnabled':False,'venueEnabled':False,'galleryEnabled':False,'countdownEnabled':False,'contactEnabled':False},
        'youtubeId':'dQw4w9WgXcQ','schedule':[],'venues':[],'customBlocks':[],'gallery':[]
    },'guest':{'name':'Guest'}}

def main()->int:
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('PUBLIC_GUEST_FEATURE_RUNTIME_NO_PLAYWRIGHT',exc)
    with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('PUBLIC_GUEST_FEATURE_RUNTIME_NO_CHROMIUM',exc)
        # Pure-invitation mode: no RSVP UI, Khmer lunar date rendered, music waits for the guest gesture.
        page=browser.new_page(viewport={'width':1280,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(build_public(payload(rsvp=False)),wait_until='load');page.wait_for_timeout(700)
        assert not errors,errors
        assert page.locator('#rsvp').count()==0,'RSVP must remain optional in pure invitation mode'
        lunar=page.locator('.hero-date .khmer-text').first.text_content() or ''
        assert lunar.strip() and any('\u1780'<=ch<='\u17ff' for ch in lunar),lunar
        player=page.locator('#youtubePlayer');assert player.count()==1
        assert not (player.get_attribute('src') or ''),'YouTube must not autoplay before the guest opens the invitation'
        page.locator('#openCover').click();page.wait_for_timeout(120)
        src=player.get_attribute('src') or ''
        assert 'youtube-nocookie.com/embed/dQw4w9WgXcQ' in src and 'autoplay=1' in src,src
        # Check the actual generated public document across required public widths.
        for width in (390,768,1280,1440,1920,2560):
            page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(30)
            overflow=page.evaluate("""()=>({doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,root:document.querySelector('#publicRoot').scrollWidth,client:document.querySelector('#publicRoot').clientWidth})""")
            assert overflow['doc']<=width+1 and overflow['body']<=width+1 and overflow['root']<=overflow['client']+2,(width,overflow)
        page.close()
        # RSVP-enabled mode: the public form remains functional and persists through the normal endpoint contract.
        page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(build_public(payload(rsvp=True)),wait_until='load');page.wait_for_timeout(700)
        assert not errors,errors
        form=page.locator('#rsvp');assert form.count()==1
        form.locator('input[name="name"]').fill('Browser Guest');form.locator('select[name="status"]').select_option('Yes, joyfully');form.locator('input[name="count"]').fill('2')
        form.evaluate('(form)=>form.requestSubmit()');page.wait_for_timeout(160)
        calls=page.evaluate('window.__rsvpCalls');assert len(calls)==1 and calls[0]['name']=='Browser Guest' and calls[0]['count']=='2',calls
        assert 'Thank you' in (form.text_content() or '')
        assert not errors,errors
        page.close();browser.close()
    print('PUBLIC_GUEST_FEATURE_RUNTIME_TEST_PASSED');return 0
if __name__=='__main__':sys.exit(main())
