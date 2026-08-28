#!/usr/bin/env python3
from __future__ import annotations
import json
from browser_runtime import dismiss_editor_onboarding,launch_chromium,open_event_details
from playwright.sync_api import sync_playwright
from v14_test_utils import app_server

def main()->int:
  with app_server() as (_proc,base,_data):
    with sync_playwright() as p:
      browser=launch_chromium(p);page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(20000)
      responses=[];failed=[];page.on('dialog',lambda d:d.accept());page.on('response',lambda r:responses.append((r.request.method,r.url,r.status)) if '/api/invitations/' in r.url else None);page.on('requestfailed',lambda r:failed.append((r.method,r.url,str(r.failure))))
      page.goto(base+'/dashboard.html',wait_until='networkidle');page.locator('#authRegisterTab').click();page.locator('#email').fill('barrier-browser@example.com');page.locator('#password').fill('strong-password-123');page.locator('#registerConfirmPassword').fill('strong-password-123');page.locator('#loginBtn').click();page.wait_for_selector('#dashboardView:not([hidden])')
      page.get_by_role('button',name='Create your first invitation',exact=True).click();page.wait_for_selector('#createDialog[open]');page.locator('#newTitle').fill('Publish Barrier Browser');page.locator('#confirmCreate').click();page.wait_for_url('**/invitations/*/editor');iid=page.url.split('/invitations/',1)[1].split('/',1)[0];dismiss_editor_onboarding(page,timeout=20000)
      rsvp,venue=open_event_details(page,timeout=12000);revisions=[]
      def current():return page.evaluate("async id=>await (await fetch('/api/invitations/'+id,{cache:'no-store'})).json()",iid)
      revisions.append(int(current()['updatedAt']))
      def publish(label):
        page.wait_for_function("()=>document.querySelector('#serverState')?.textContent==='Server connected'&&!serverSaveBlockedByConflict")
        with page.expect_response(lambda r:r.url.endswith('/publish') and r.request.method=='POST') as info:page.locator('#publishBtn').click()
        response=info.value;assert response.status==201,(label,response.status,responses[-15:])
        page.wait_for_function("()=>!document.querySelector('#publishBtn')?.disabled&&document.querySelector('#publishBtn')?.getAttribute('aria-busy')!=='true'")
        body=response.json();revision=int(body['updatedAt']);assert revision>revisions[-1],(label,revisions,body);revisions.append(revision)
        inv=current();public=page.evaluate("async slug=>await (await fetch('/api/public/'+encodeURIComponent(slug),{cache:'no-store'})).json()",inv['slug'])
        assert inv['document']['fields']['venue']==public['document']['fields']['venue'],(label,inv['document']['fields']['venue'],public['document']['fields']['venue'])
        return inv
      # 1. Pending local saveTimer.
      venue.fill('Barrier saveTimer');page.wait_for_function("()=>!!saveTimer&&!serverSaveTimer&&!serverIdleSaveHandle&&!serverSaveInFlight")
      assert publish('pending saveTimer')['document']['fields']['venue']=='Barrier saveTimer'
      # 2. Pending serverSaveTimer after the local debounce has committed locally.
      rsvp,venue=open_event_details(page);venue.fill('Barrier serverSaveTimer');page.wait_for_function("()=>!!serverSaveTimer&&!serverIdleSaveHandle&&!serverSaveInFlight")
      assert publish('pending serverSaveTimer')['document']['fields']['venue']=='Barrier serverSaveTimer'
      # 3. Pending native idle callback using the application's real generation/run contract.
      rsvp,venue=open_event_details(page);venue.fill('Barrier idle callback');page.wait_for_function("()=>document.querySelector('#saveState')?.textContent==='Saved'")
      scheduled=page.evaluate("""()=>{clearTimeout(serverSaveTimer);serverSaveTimer=0;if(serverIdleSaveHandle&&'cancelIdleCallback'in window)cancelIdleCallback(serverIdleSaveHandle);const generation=saveGeneration,snapshot=structuredClone(state);serverIdleSaveHandle=requestIdleCallback(()=>{serverIdleSaveHandle=0;if(generation===saveGeneration)void saveServerDraft(snapshot)},{timeout:1800});return !!serverIdleSaveHandle}""")
      assert scheduled
      assert publish('pending idle callback')['document']['fields']['venue']=='Barrier idle callback'
      # 4. Already-running real draft PUT when publish starts.
      rsvp,venue=open_event_details(page);venue.fill('Barrier in-flight PUT');page.wait_for_function("()=>document.querySelector('#saveState')?.textContent==='Saved'")
      state=page.evaluate("""()=>{cancelScheduledServerWrites();void saveServerDraft(structuredClone(state));return {inFlight:serverSaveInFlight}}""");assert state['inFlight'],state
      assert publish('in-flight PUT')['document']['fields']['venue']=='Barrier in-flight PUT'
      # 5. Edit -> successful ordinary autosave -> second lifecycle publish.
      rsvp,venue=open_event_details(page);before_autosave=current();assert before_autosave['document']['fields']['venue']!='Barrier post-publish autosave',before_autosave['document']['fields']['venue'];before_autosave_revision=int(before_autosave['updatedAt'])
      with page.expect_response(lambda r:r.request.method=='PUT' and r.url.rstrip('/').endswith(iid)) as autosave_info:venue.fill('Barrier post-publish autosave')
      autosave_response=autosave_info.value;assert autosave_response.status==200,(autosave_response.status,responses[-20:])
      page.wait_for_function("""async id=>{if(document.querySelector('#saveState')?.textContent!=='Saved'||document.querySelector('#serverState')?.textContent!=='Server connected')return false;const r=await fetch('/api/invitations/'+id,{cache:'no-store'});return r.ok&&(await r.json()).document?.fields?.venue==='Barrier post-publish autosave'}""",arg=iid)
      autosaved=current();assert int(autosaved['updatedAt'])>before_autosave_revision,{'beforeRevision':before_autosave_revision,'autosavedRevision':autosaved.get('updatedAt'),'knownRevisions':revisions,'serverSave':page.evaluate("()=>({inFlight:serverSaveInFlight,blocked:serverSaveBlockedByConflict,pending:!!pendingServerDocument,clientRevision:serverInvite?.updatedAt??null,status:document.querySelector('#serverState')?.textContent||''})"),'responses':responses[-30:]};revisions.append(int(autosaved['updatedAt']))
      assert publish('post-publish autosave')['document']['fields']['venue']=='Barrier post-publish autosave'
      assert revisions==sorted(revisions) and len(revisions)==len(set(revisions)),revisions
      same_editor_conflicts=[x for x in responses if x[2]==409 and ('/publish' in x[1] or (x[0]=='PUT' and x[1].rstrip('/').endswith(iid)))];assert not same_editor_conflicts,same_editor_conflicts
      assert not [x for x in failed if '/api/invitations/' in x[1]],failed
      # 10. A true remote revision must still block and preserve remote data.
      local_revision=int(current()['updatedAt'])
      remote=page.evaluate("""async ({id,revision})=>{const d=structuredClone(state);d.fields.venue='True remote barrier venue';const r=await fetch('/api/invitations/'+id,{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-EInvite-Client-Id':'remote-barrier-client','X-EInvite-Mutation-Id':'remote-barrier-mutation'},body:JSON.stringify({document:d,expectedRevision:revision})});return {status:r.status,body:await r.json()}}""",{'id':iid,'revision':local_revision});assert remote['status']==200,remote
      with page.expect_response(lambda r:r.url.endswith('/publish') and r.request.method=='POST') as info:page.locator('#publishBtn').click()
      conflict=info.value;assert conflict.status==409,conflict.status;payload=conflict.json();assert payload.get('code')=='revision_conflict',payload
      page.wait_for_function("()=>serverSaveBlockedByConflict===true&&document.querySelector('#serverState')?.textContent.includes('Remote changes')")
      after=current();assert after['document']['fields']['venue']=='True remote barrier venue',after['document']['fields']['venue']
      assert page.evaluate("document.documentElement.dataset.serverSaveErrorCode")=='revision_conflict'
      browser.close()
  print('V0_52_PUBLISH_AUTOSAVE_BARRIER_BROWSER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
