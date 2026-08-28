#!/usr/bin/env python3
"""Required V14 acceptance walkthrough against the real server over HTTP."""
from __future__ import annotations
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import launch_chromium,skipped
from v14_test_utils import app_server

PAGES=['dashboard.html','account.html','materials.html','templates.html']

def step(label):
    print(f'[V14 live] {label}', flush=True)

def serious_console(message):
    text=message.text
    if message.type!='error':return False
    lower=text.lower()
    return not any(x in lower for x in ('favicon','youtube','soundcloud','net::err_name_not_resolved'))

def main():
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image
    except Exception as exc:return skipped('V14_LIVE_SERVER_ACCEPTANCE',exc)
    step('starting isolated server')
    with app_server() as (_process,base,data):
        image_path=data/'acceptance.png';Image.new('RGB',(320,240),(150,74,92)).save(image_path,'PNG')
        audio_path=data/'acceptance.mp3';audio_path.write_bytes(b'ID3\x04\x00\x00\x00\x00\x00\x15TIT2\x00\x00\x00\x0b\x00\x00V14 Audio')
        step('launching Chromium')
        with sync_playwright() as playwright:
            try:browser=launch_chromium(playwright)
            except Exception as exc:return skipped('V14_LIVE_SERVER_ACCEPTANCE',exc)
            context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
            # Simulate a browser carrying a revoked/unknown localhost session.
            context.add_cookies([{'name':'einvite_session','value':'stale-v14-session','url':base,'httpOnly':True,'sameSite':'Lax'}])
            page=context.new_page();page.set_default_timeout(7000);errors=[];dialogs=[];bad_responses=[]
            page.on('pageerror',lambda error:errors.append(f'pageerror: {error}'))
            page.on('console',lambda message:errors.append(f'console: {message.text}') if serious_console(message) else None)
            page.on('dialog',lambda dialog:(dialogs.append(dialog.message),dialog.accept()))
            page.on('response',lambda response:bad_responses.append((response.status,response.url)) if response.status>=400 else None)
            step('opening dashboard with stale cookie')
            response=page.goto(base+'/dashboard.html',wait_until='networkidle',timeout=30000)
            csp=response.headers.get('content-security-policy','')
            assert "require-trusted-types-for" not in csp,csp
            assert "script-src 'self'" in csp and "script-src 'self' 'unsafe-inline'" not in csp,csp
            assert page.locator('#loginView').is_visible()
            page.locator('#authRegisterTab').click();page.locator('#email').fill('v14-browser@example.com');page.locator('#password').fill('Strong-v14-pass-123');page.locator('#registerConfirmPassword').fill('Strong-v14-pass-123');page.locator('#loginBtn').click()
            page.wait_for_selector('#dashboardView:not([hidden])',timeout=12000)
            assert page.locator('#accountName').get_by_text('v14-browser@example.com',exact=False).count()>=1
            cookies={c['name']:c['value'] for c in context.cookies()}
            assert cookies.get('einvite_session') and cookies['einvite_session']!='stale-v14-session'
            step('registered; testing logout/login')
            # Log out and log in again.
            page.locator('.fp-profile-button').click();page.locator('.fp-profile-popover [data-signout]').click();page.wait_for_selector('#loginView:not([hidden])')
            page.locator('#authSignInTab').click();page.locator('#email').fill('v14-browser@example.com');page.locator('#password').fill('Strong-v14-pass-123');page.locator('#loginBtn').click();page.wait_for_selector('#dashboardView:not([hidden])')
            step('login complete; creating invitation')
            # Create from a built-in template.
            create=page.locator('.dashboard-home-hero .create');
            if not create.is_visible():create=page.locator('#emptyCreate')
            create.click();page.wait_for_selector('#createDialog[open]')
            page.locator('#newTitle').fill('ពិធីមង្គលការ V14 — A very long invitation title for dashboard scaling')
            assert page.locator('#templateChoices .template-choice').count()>0
            page.evaluate("document.querySelector('#newTemplate').value='gold'")
            page.locator('#confirmCreate').click();page.wait_for_url('**/invitations/*/editor',timeout=15000)
            invitation_id=page.url.split('/invitations/',1)[1].split('/',1)[0]
            page.wait_for_selector('#stage .object',timeout=15000);page.wait_for_timeout(1200)
            if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click()
            try:
                page.wait_for_function("()=>document.querySelector('#serverState')?.textContent.toLowerCase().includes('connected')",timeout=15000)
            except Exception:
                diagnostic=page.evaluate("async id=>({serverState:document.querySelector('#serverState')?.textContent,backend:window.EInviteBackend?.state,status:(await fetch('/api/invitations/'+id)).status})",invitation_id)
                raise AssertionError((diagnostic,errors))
            page.wait_for_function("()=>document.documentElement.dataset.editorReady==='true'",timeout=15000)
            step('editor connected and fully hydrated; editing invitation')
            # Edit names, date/Khmer date, venue, palette and font.
            step('opening Event workflow')
            page.evaluate("window.EInviteWorkflow?.navigate?.('event',{source:'v14-acceptance'})")
            step('Event workflow navigation dispatched')
            page.wait_for_selector('#names',state='visible',timeout=8000)
            page.wait_for_function("()=>{const e=document.querySelector('#names');if(!e)return false;const r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,h=document.elementFromPoint(x,y);return !!h&&(h===e||e.contains(h)||h.contains(e))}",timeout=12000)
            step('Event fields visible and pointer-ready')
            def replace_text(selector,value):
                control=page.locator(selector);control.click();control.press('ControlOrMeta+A');page.keyboard.insert_text(value);control.press('Tab')
            replace_text('#names','Serey & Sophea');step('English name edited')
            replace_text('#namesKm','សិរី និង សុភា');step('Khmer name edited')
            page.locator('#date').fill('2027-01-17');step('date edited')
            replace_text('#venue','Royal Hall, Phnom Penh');replace_text('#venueKm','សាលមង្គល រាជធានីភ្នំពេញ');step('venues edited')
            page.locator('#dateFormat').select_option('both')
            page.wait_for_timeout(500);assert len(page.locator('#khmerDatePreview').inner_text().strip())>5
            local_event_state=page.evaluate("()=>({values:{names:document.querySelector('#names')?.value,namesKm:document.querySelector('#namesKm')?.value,date:document.querySelector('#date')?.value,venue:document.querySelector('#venue')?.value},captured:typeof capture==='function'?capture().fields:null,serverState:document.querySelector('#serverState')?.textContent})")
            step('event autosave local state '+json.dumps(local_event_state,ensure_ascii=False));assert local_event_state['captured']['names']=='Serey & Sophea',local_event_state
            page.wait_for_function("async id=>{const r=await fetch('/api/invitations/'+id,{cache:'no-store'});if(!r.ok)return false;const body=await r.json();return body.document?.fields?.names==='Serey & Sophea'&&body.document?.fields?.namesKm==='សិរី និង សុភា'}",arg=invitation_id,timeout=15000)
            step('event autosave reached server')
            page.evaluate("window.EInviteWorkflow?.navigate?.('design',{source:'v14-acceptance'})")
            page.wait_for_selector('#stage .text-object',state='visible',timeout=8000)
            text=page.locator('#stage .text-object').first;text.click();before=text.get_attribute('style');page.keyboard.press('ArrowRight');page.wait_for_timeout(150);after=text.get_attribute('style');assert before!=after
            page.locator('#v20VisibleFont').wait_for(state='visible');page.locator('#v20VisibleFont').select_option('noto-serif-khmer')
            page.locator('#accent').fill('#7b2843',force=True)
            step('text fields and movement verified')
            # Resize a text object through its visible handle.
            locator=page.locator('#stage .text-object').first
            locator.click();handle=locator.locator('i').first;box=handle.bounding_box()
            if box:
                page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.mouse.move(box['x']+28,box['y']+24,steps=4);page.mouse.up()
            step('text resize complete; starting uploads')
            # Upload real image/audio files through the editor.
            page.evaluate("window.EInviteWorkflow?.navigate?.('event',{source:'v14-acceptance-upload'})")
            page.locator('#photoUpload').set_input_files(str(image_path));page.wait_for_timeout(1800);step('image upload submitted')
            image_diag=page.evaluate("""async id=>{let api=null,local=null;try{const r=await fetch('/api/invitations/'+id+'/assets');api={status:r.status,body:await r.json()}}catch(e){api={error:String(e)}}try{local=typeof listAllAssets==='function'?await listAllAssets():'missing'}catch(e){local={error:String(e)}}const up=document.querySelector('#photoUpload');return {api,localCount:Array.isArray(local)?local.length:local,html:document.querySelector('#assets')?.innerHTML.slice(0,300),section:document.body.dataset.studioSection,upload:{files:up?.files?.length,onchange:typeof up?.onchange,disabled:up?.disabled},dialogs:[]}}""",invitation_id)
            image_diag['dialogs']=list(dialogs)
            image_diag['errors']=list(errors)
            image_diag['badResponses']=list(bad_responses[-12:])
            step('image diagnostic '+json.dumps(image_diag,ensure_ascii=False))
            page.evaluate("window.EInviteWorkflow?.navigate?.('media',{source:'v14-acceptance-material'})")
            page.wait_for_selector('#assets img',state='attached',timeout=10000);step('uploaded image appeared in materials')
            page.locator('#assets img').first.evaluate('img=>img.click()')
            page.wait_for_function("()=>document.querySelectorAll('#stage .image-object').length>0",timeout=8000)
            page.evaluate("window.EInviteWorkflow?.navigate?.('design',{source:'v14-acceptance-image'})")
            page.wait_for_selector('#stage .image-object',state='visible',timeout=8000)
            image_object=page.locator('#stage .image-object').first;image_object.click();image_handle=image_object.locator('i').first;image_box=image_handle.bounding_box()
            if image_box:
                page.mouse.move(image_box['x']+image_box['width']/2,image_box['y']+image_box['height']/2);page.mouse.down();page.mouse.move(image_box['x']+26,image_box['y']+22,steps=4);page.mouse.up()
            page.evaluate("window.EInviteWorkflow?.navigate?.('event',{source:'v14-acceptance-audio'})")
            page.locator('#musicUpload').set_input_files(str(audio_path));page.wait_for_timeout(1400);step('audio upload submitted')
            assert page.locator('#musicSource').input_value()=='uploaded'
            youtube_diag=page.evaluate("""()=>{const input=document.querySelector('#youtubeUrl');input.value='https://youtu.be/dQw4w9WgXcQ';input.dispatchEvent(new Event('input',{bubbles:true}));return {source:document.querySelector('#musicSource')?.value,enabled:document.querySelector('#musicEnabled')?.checked,id:typeof youtubeId==='function'?youtubeId(input.value):'missing'}}""")
            step('YouTube input diagnostic '+json.dumps(youtube_diag));page.wait_for_timeout(900);assert page.locator('#musicSource').input_value()=='youtube';step('YouTube source verified')
            soundcloud_diag=page.evaluate("""()=>{const input=document.querySelector('#soundcloudUrl');input.value='https://soundcloud.com/example/track';input.dispatchEvent(new Event('input',{bubbles:true}));return {source:document.querySelector('#musicSource')?.value,enabled:document.querySelector('#musicEnabled')?.checked}}""")
            step('SoundCloud input diagnostic '+json.dumps(soundcloud_diag));page.wait_for_timeout(900);assert page.locator('#musicSource').input_value()=='soundcloud';step('SoundCloud source verified')
            page.locator('#musicSource').select_option('uploaded',force=True);page.locator('#musicEnabled').check(force=True);page.wait_for_timeout(800)
            step('uploads/media configured; publishing RSVP-disabled invitation')
            # Pure invitation publish: RSVP absent publicly.
            rsvp_hit=page.evaluate("""()=>{const el=document.querySelector('#rsvpEnabled'),r=el.getBoundingClientRect(),hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {body:document.body.className,section:document.body.dataset.studioSection,rect:{x:r.x,y:r.y,w:r.width,h:r.height},hit:hit?.outerHTML?.slice(0,220),pane:el.closest('[data-studio-pane]')?.dataset.studioPane,paneClass:el.closest('[data-studio-pane]')?.className}}""")
            step('RSVP hit-test '+json.dumps(rsvp_hit))
            rsvp_toggle=page.locator('#rsvpEnabled');rsvp_toggle.evaluate("el=>{if(el.checked)el.click()}");page.wait_for_timeout(700)
            with page.expect_response(lambda response:response.url.endswith('/publish') and response.request.method=='POST',timeout=12000) as publish_info:
                page.locator('#publishBtn').click()
            publish_response=publish_info.value;publish_body=publish_response.text();step('pure publish response '+json.dumps({'status':publish_response.status,'body':publish_body},ensure_ascii=False));assert publish_response.status==201,(publish_response.status,publish_body)
            page.wait_for_timeout(800)
            invitation=page.evaluate("async id=>{const r=await fetch('/api/invitations/'+id);return r.json()}",invitation_id);slug=invitation['slug']
            public=context.new_page();public_errors=[];public.on('pageerror',lambda e:public_errors.append(str(e)));public.on('console',lambda m:public_errors.append(m.text) if serious_console(m) else None)
            pubresp=public.goto(base+'/i/'+slug,wait_until='networkidle');assert "require-trusted-types-for" not in pubresp.headers.get('content-security-policy','')
            public_diag=public.evaluate("""async()=>{const meta=document.querySelector('meta[name=\"einvite-invitation-slug\"]')?.content||'';let api={};try{const r=await fetch('/api/public/'+encodeURIComponent(meta),{cache:'no-store'});const body=await r.json();api={status:r.status,title:body.document?.fields?.names,rsvpEnabled:body.document?.settings?.rsvpEnabled}}catch(e){api={error:String(e)}}return {meta,root:document.querySelector('#publicRoot')?.textContent?.slice(0,280),api}}""")
            step('public invitation diagnostic '+json.dumps(public_diag,ensure_ascii=False))
            public.wait_for_function("()=>document.querySelector('#publicRoot')?.textContent.includes('Serey')",timeout=10000)
            if public.locator('#openCover').count():public.locator('#openCover button,#openCover').first.click();public.wait_for_timeout(400)
            assert public.locator('#guestRsvp,#rsvp').count()==0
            assert public.get_by_text('attending',exact=False).count()==0
            step('pure invitation verified; enabling RSVP')
            # Re-enable RSVP and persist one response.
            page.bring_to_front();rsvp_toggle=page.locator('#rsvpEnabled');rsvp_toggle.evaluate("el=>{if(!el.checked)el.click()}");page.wait_for_timeout(700)
            rsvp_before_publish=page.evaluate("""()=>({checked:document.querySelector('#rsvpEnabled')?.checked,captured:typeof capture==='function'?capture().settings?.rsvpEnabled:null,section:document.body.dataset.studioSection})""")
            step('RSVP before republish '+json.dumps(rsvp_before_publish))
            with page.expect_response(lambda response:response.url.endswith('/publish') and response.request.method=='POST',timeout=12000) as republish_info:
                page.locator('#publishBtn').click()
            republish_response=republish_info.value;republish_body=republish_response.text();step('RSVP publish response '+json.dumps({'status':republish_response.status,'body':republish_body},ensure_ascii=False));assert republish_response.status==201,(republish_response.status,republish_body)
            page.wait_for_timeout(800)
            published_rsvp=page.evaluate("""async slug=>{const r=await fetch('/api/public/'+slug);const p=await r.json();return {status:r.status,enabled:p.document?.settings?.rsvpEnabled,order:p.document?.sectionOrder}}""",slug)
            step('published RSVP diagnostic '+json.dumps(published_rsvp))
            public.reload(wait_until='networkidle');
            if public.locator('#openCover').count() and public.locator('#openCover').is_visible():public.locator('#openCover button,#openCover').first.click()
            public.wait_for_selector('#rsvp',timeout=10000);public.locator('#rsvp [name="name"]').fill('Browser Guest');public.locator('#rsvp [name="status"]').select_option(index=0);public.locator('#rsvp [name="count"]').fill('2')
            with public.expect_response(lambda response:'/api/public/' in response.url and response.url.endswith('/rsvps') and response.request.method=='POST',timeout=10000) as response_info:
                public.locator('#rsvp button[type="submit"],#rsvp button').last.click()
            rsvp_response=response_info.value;rsvp_body=rsvp_response.text();step('public RSVP response '+json.dumps({'status':rsvp_response.status,'body':rsvp_body},ensure_ascii=False));assert rsvp_response.status in (200,201),(rsvp_response.status,rsvp_body)
            public.wait_for_function("()=>document.querySelector('#rsvp')?.textContent.includes('Thank you')||document.querySelector('#rsvp')?.textContent.includes('សូមអរគុណ')",timeout=10000)
            page.wait_for_function("async id=>{const r=await fetch('/api/invitations/'+id+'/rsvps',{cache:'no-store'});const body=await r.json();return Array.isArray(body)&&body.length>0}",arg=invitation_id,timeout=10000)
            count=page.evaluate("async id=>{const r=await fetch('/api/invitations/'+id+'/rsvps',{cache:'no-store'});return (await r.json()).length}",invitation_id);assert count>=1
            step('RSVP persistence verified; creating personalized guest')
            # Personalized guest and real QR.
            guests=context.new_page();guests.goto(base+f'/invitations/{invitation_id}/guests',wait_until='networkidle');guests.locator('#addForm [name="name"]').fill('Personal Guest');guests.locator('#addForm button').click();guests.wait_for_timeout(800)
            with guests.expect_response(lambda response:response.url.endswith('/qr.png'),timeout=10000) as qr_response_info:
                guests.locator('[data-qr]').first.click()
            qr_response=qr_response_info.value;qr_body='' if qr_response.status==200 else qr_response.text();step('personalized QR response '+json.dumps({'status':qr_response.status,'contentType':qr_response.headers.get('content-type'),'body':qr_body},ensure_ascii=False));assert qr_response.status==200,(qr_response.status,qr_body)
            guests.wait_for_selector('#guestQrImage');guests.wait_for_function("()=>{const img=document.querySelector('#guestQrImage');return img?.complete&&img.naturalWidth>0}",timeout=10000);assert guests.locator('#guestQrImage').evaluate('img=>img.complete&&img.naturalWidth>0')
            step('personalized QR verified; testing protected media')
            # Protected media cannot be fetched directly without authorization.
            assets=page.evaluate("async id=>{const r=await fetch('/api/invitations/'+id+'/assets');return r.json()}",invitation_id);assert assets
            path=assets[0].get('path') or assets[0].get('storageKey') or ''
            page.evaluate("async id=>{if(typeof api!=='function')throw Error('Editor API bridge unavailable');await api('/api/invitations/'+id+'/access',{method:'PUT',body:JSON.stringify({mode:'password',password:'Secure-v14-passcode'})})}",invitation_id)
            anonymous=browser.new_context();probe=anonymous.new_page();direct=probe.goto(base+'/uploads/'+path,wait_until='domcontentloaded');assert direct.status in (401,403,404)
            anonymous.close()
            step('protected media verified; testing timeline')
            # Timeline keyframe and playback.
            page.bring_to_front();page.evaluate("window.EInviteWorkflow?.navigate?.('design',{source:'v14-acceptance-timeline'})");page.wait_for_selector('#stage .text-object',state='visible',timeout=10000);page.locator('#stage .text-object').first.click();page.locator('#v16ToolbarMore summary').click();page.locator('#v16ToolbarMore #eiTimelineLaunch').click();page.wait_for_selector('#eiTimeline:not([hidden])');page.locator('[data-tl-scrub]').fill('500');page.locator('[data-tl-add]').click();assert page.locator('.ei-keyframe').count()>=1;page.locator('[data-tl-play]').click();page.wait_for_timeout(250);page.locator('[data-tl-stop]').click()
            page.locator('[data-tl-close]').click()
            page.locator('#v16ToolbarMore summary').click();page.locator('#v16ToolbarMore #v13OperationsBtn').click();page.wait_for_selector('#v13OperationsDialog[open]');assert page.locator('[data-v13-tab]').count()>=7;page.locator('.v13-ops-close').click()
            step('timeline and Studio Ops verified; checking required routes')
            # Every required real-server page loads with CSP and no TrustedHTML failure.
            # Dashboard, editor, public invitation, and guests have already
            # completed full workflows above.  Exercise the remaining major
            # server-rendered pages without loading duplicate heavy editors.
            routes=[f'/invitations/{invitation_id}/materials',f'/invitations/{invitation_id}/responses',f'/invitations/{invitation_id}/analytics',f'/invitations/{invitation_id}/checkin','/account.html','/templates.html']
            for route in routes:
                check=context.new_page();local_errors=[];check.on('pageerror',lambda e,bag=local_errors:bag.append(str(e)));check.on('console',lambda m,bag=local_errors:bag.append(m.text) if serious_console(m) else None)
                r=check.goto(base+route,wait_until='domcontentloaded',timeout=30000);check.wait_for_timeout(350);assert r.status==200,(route,r.status);header=r.headers.get('content-security-policy','');assert 'require-trusted-types-for' not in header and "script-src 'self'" in header
                assert not [e for e in local_errors if 'TrustedHTML' in e or 'Trusted Types' in e],(route,local_errors)
                check.close()
            step('routes verified; live responsive layouts are covered by v14_live_layout_test.py')
            assert not [e for e in errors+public_errors if 'TrustedHTML' in e or 'Trusted Types' in e],errors+public_errors
            if errors or public_errors: step('final browser diagnostics '+json.dumps({'errors':errors,'publicErrors':public_errors,'badResponses':bad_responses},ensure_ascii=False))
            assert not errors,(errors,bad_responses)
            assert not public_errors,public_errors
            public.close();guests.close();page.close();context.close();browser.close()
            step('walkthrough complete')
    print('V14_LIVE_SERVER_ACCEPTANCE_TEST_PASSED');return 0

if __name__=='__main__':raise SystemExit(main())
