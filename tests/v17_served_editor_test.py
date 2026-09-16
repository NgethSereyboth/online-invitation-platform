#!/usr/bin/env python3
"""Real HTTP Chromium coverage for the V17 transform/layers milestone."""
from __future__ import annotations
import json,math,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_runtime import dismiss_editor_onboarding,launch_chromium,skipped
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from v14_test_utils import app_server



def server_process_diagnostic(process,data,phase,network,method,url,failure):
    try:tail=(data/'server-test.log').read_text(encoding='utf-8',errors='replace').splitlines()[-30:]
    except Exception:tail=[]
    return {'phase':phase['name'],'method':method,'url':url,'failure':str(failure),'serverAlive':process.poll() is None,'serverExitCode':process.poll(),'serverLogTail':tail,'networkTail':network[-30:]}

def goto_with_server_diagnostic(page,url,*,wait_until,timeout,process,data,phase,network):
    try:return page.goto(url,wait_until=wait_until,timeout=timeout)
    except Exception as exc:raise AssertionError(f'V17 served navigation failed: {server_process_diagnostic(process,data,phase,network,"GET",url,exc)!r}') from exc

def serious(message):
    if message.type!='error':return False
    text=message.text.lower()
    return not any(token in text for token in ('favicon','youtube','soundcloud','net::err_name_not_resolved'))


def center(page,selector):
    box=page.locator(selector).bounding_box();assert box,selector
    return box['x']+box['width']/2,box['y']+box['height']/2


def capture_nested_history_state(page):
    return page.evaluate("""()=>{const comparable=()=>{try{return typeof historyDocumentFingerprint==='function'&&typeof historySnapshot==='function'?historyDocumentFingerprint(undoStack.at(-1))===historyDocumentFingerprint(historySnapshot(state)):true}catch{return true}};return {objects:Object.fromEntries(['title','subtitle','details'].map(id=>[id,Object.fromEntries(['left','top','width','height','rotation','groupId','parentGroupId'].map(k=>[k,state.objects[id]?.[k]??null]))])),groups:structuredClone(state.sceneGraph?.groups||{}),history:{depth:undoStack.length,redoDepth:redoStack.length,cursor:undoStack.length-1,topMatchesState:comparable()},selection:[...EInviteEditorBridge.getSelectedIds()].map(String).sort(),professional:{sequence:EInviteProfessionalEditor?.commandSequence??null,last:EInviteProfessionalEditor?.lastCommand??null}}}""")


def capture_view_geometry(page,handle_selector=None,selection_selector='#peSelectionBox'):
    return page.evaluate("""({handleSelector,selectionSelector})=>{const rect=sel=>{const e=document.querySelector(sel),r=e?.getBoundingClientRect();return e&&r?{hidden:!!e.hidden,left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height,centerX:r.left+r.width/2,centerY:r.top+r.height/2}:null};const vv=window.visualViewport;const viewport=document.querySelector('#canvasViewport');return {viewport:{width:innerWidth,height:innerHeight,devicePixelRatio:devicePixelRatio||1},visualViewport:vv?{width:vv.width,height:vv.height,offsetLeft:vv.offsetLeft,offsetTop:vv.offsetTop,scale:vv.scale}:null,canvas:{zoom:window.EInviteCanvasViewController?.zoom??null,scrollLeft:viewport?.scrollLeft??null,scrollTop:viewport?.scrollTop??null,clientWidth:viewport?.clientWidth??null,clientHeight:viewport?.clientHeight??null,rect:rect('#canvasViewport')},stage:rect('#stage'),selectionBox:rect(selectionSelector),rotateHandle:rect('[data-pe-handle=\"rotate\"]'),resizeHandle:rect('[data-pe-handle=\"se\"]'),handle:handleSelector?rect(handleSelector):null}}""",{'handleSelector':handle_selector,'selectionSelector':selection_selector})


def capture_gesture_diagnostic(page,pointer=None):
    state=capture_nested_history_state(page)
    ui=page.evaluate("""()=>{const text=id=>document.querySelector(id)?.textContent?.trim()||'';return {save:text('#saveState'),server:text('#serverState'),publish:{disabled:!!document.querySelector('#publishBtn')?.disabled,busy:document.querySelector('#publishBtn')?.getAttribute('aria-busy')||'',lastError:window.__einviteLastPublishError||null,state:window.__einvitePublishState||null},serverSave:{errorCode:document.documentElement.dataset.serverSaveErrorCode||'',connected:document.documentElement.dataset.serverConnected||'',inFlight:typeof serverSaveInFlight==='undefined'?null:serverSaveInFlight,pending:typeof pendingServerDocument==='undefined'?null:!!pendingServerDocument,conflict:typeof serverSaveBlockedByConflict==='undefined'?null:serverSaveBlockedByConflict,publishBarrier:typeof publishBarrier==='undefined'?null:publishBarrier}}}""")
    return {**state,'geometry':capture_view_geometry(page),'ui':ui,'pointer':pointer}


def wait_canvas_geometry_settled(page,handle_selector,selection_selector='#peSelectionBox',timeout=8000):
    predicate="""({handleSelector,selectionSelector})=>new Promise(resolve=>{const rect=sel=>{const e=document.querySelector(sel),r=e?.getBoundingClientRect();return e&&r?[r.left,r.top,r.right,r.bottom,r.width,r.height]:null};const viewport=document.querySelector('#canvasViewport');const snap=()=>JSON.stringify({zoom:window.EInviteCanvasViewController?.zoom??null,left:viewport?.scrollLeft??null,top:viewport?.scrollTop??null,stage:rect('#stage'),selection:rect(selectionSelector),handle:rect(handleSelector)});const first=snap();requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(()=>resolve(first===snap()),0)))})"""
    page.wait_for_function(predicate,arg={'handleSelector':handle_selector,'selectionSelector':selection_selector},timeout=timeout)
    return capture_view_geometry(page,handle_selector,selection_selector)


def _rect_safe(rect,width,height,inset):
    return bool(rect and not rect.get('hidden') and rect['left']>=inset and rect['top']>=inset and rect['right']<=width-inset and rect['bottom']<=height-inset)


def _point_safe(point,width,height,inset):
    return bool(point and inset<=point['x']<=width-inset and inset<=point['y']<=height-inset)


def ensure_handle_reachable(page,handle_selector,selection_selector='#peSelectionBox',*,safe_inset=18,timeout=10000):
    deadline=time.monotonic()+timeout/1000
    attempts=[]
    while time.monotonic()<deadline:
        try:geometry=wait_canvas_geometry_settled(page,handle_selector,selection_selector,timeout=min(3000,max(500,int((deadline-time.monotonic())*1000))))
        except PlaywrightTimeoutError:geometry=capture_view_geometry(page,handle_selector,selection_selector)
        attempts.append(geometry)
        width=geometry['visualViewport']['width'] if geometry.get('visualViewport') else geometry['viewport']['width']
        height=geometry['visualViewport']['height'] if geometry.get('visualViewport') else geometry['viewport']['height']
        handle=geometry.get('handle');selection=geometry.get('selectionBox')
        center_point={'x':handle['centerX'],'y':handle['centerY']} if handle else None
        selection_safe=_rect_safe(selection,width,height,safe_inset)
        handle_safe=_point_safe(center_point,width,height,safe_inset)
        if selection_safe and handle_safe:return geometry
        selection_button=page.locator('#v24CanvasHud [data-v24-zoom="selection"]')
        fit_button=page.locator('#fitCanvas')
        if selection_button.count() and selection_button.is_visible() and selection_button.is_enabled():
            selection_button.click()
        elif fit_button.count() and fit_button.is_visible() and fit_button.is_enabled():
            fit_button.click()
        else:break
        try:wait_canvas_geometry_settled(page,handle_selector,selection_selector,timeout=min(4000,max(800,int((deadline-time.monotonic())*1000))))
        except PlaywrightTimeoutError:pass
    raise AssertionError(f'handle cannot be made safely reachable through canvas controls: handle={handle_selector!r}; attempts={attempts!r}; state={capture_gesture_diagnostic(page)!r}')


def wait_stable_nested_baseline(page,*,label,timeout=10000,quiet_ms=420):
    # App history capture may settle up to 260 ms after an ordinary save. Do not
    # trust a single short sample: require authoritative state to remain unchanged
    # continuously beyond that window while every probe itself spans two animation
    # frames plus a task turn.
    deadline=time.monotonic()+timeout/1000
    samples=[];stable_key=None;stable_since=None
    while time.monotonic()<deadline:
        probe=page.evaluate("""async()=>{const snap=()=>{const comparable=()=>{try{return typeof historyDocumentFingerprint==='function'&&typeof historySnapshot==='function'?historyDocumentFingerprint(undoStack.at(-1))===historyDocumentFingerprint(historySnapshot(state)):true}catch{return true}};return {objects:Object.fromEntries(['title','subtitle','details'].map(id=>[id,Object.fromEntries(['left','top','width','height','rotation','groupId','parentGroupId'].map(k=>[k,state.objects[id]?.[k]??null]))])),groups:structuredClone(state.sceneGraph?.groups||{}),history:{depth:undoStack.length,redoDepth:redoStack.length,cursor:undoStack.length-1,topMatchesState:comparable()},selection:[...EInviteEditorBridge.getSelectedIds()].map(String).sort(),professional:{sequence:EInviteProfessionalEditor?.commandSequence??null,last:EInviteProfessionalEditor?.lastCommand??null}}};const first=snap();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));await new Promise(r=>setTimeout(r,0));const second=snap();return {first,second,stable:JSON.stringify(first)===JSON.stringify(second)&&second.history.topMatchesState===true}}""")
        samples.append(probe);now=time.monotonic()
        if probe['stable']:
            key=json.dumps(probe['second'],sort_keys=True,separators=(',',':'))
            if key!=stable_key:stable_key=key;stable_since=now
            elif stable_since is not None and (now-stable_since)*1000>=quiet_ms:return probe['second']
        else:stable_key=None;stable_since=None
        page.wait_for_timeout(35)
    raise AssertionError(f'{label} did not reach a stable history/geometry baseline across two animation frames, a task turn, and {quiet_ms}ms quiescence: samples={samples[-6:]!r}; actual={capture_gesture_diagnostic(page)!r}')


def choose_rotate_destination(start,selection_center,width,height,inset=18):
    vx=start['x']-selection_center['x'];vy=start['y']-selection_center['y']
    for degrees in (32,-32,26,-26,20,-20,14,-14):
        angle=math.radians(degrees)
        point={'x':selection_center['x']+vx*math.cos(angle)-vy*math.sin(angle),'y':selection_center['y']+vx*math.sin(angle)+vy*math.cos(angle)}
        if _point_safe(point,width,height,inset):return point,degrees
    raise AssertionError(f'no in-viewport rotate destination is available: start={start!r}; center={selection_center!r}; viewport={(width,height)!r}')


def assert_pointer_reachable(page,pointer,*,label,inset=18):
    geometry=capture_view_geometry(page)
    width=geometry['visualViewport']['width'] if geometry.get('visualViewport') else geometry['viewport']['width']
    height=geometry['visualViewport']['height'] if geometry.get('visualViewport') else geometry['viewport']['height']
    start_ok=_point_safe(pointer.get('start'),width,height,inset);destination_ok=_point_safe(pointer.get('destination'),width,height,inset)
    pointer['inBounds']={'start':start_ok,'destination':destination_ok,'viewport':{'width':width,'height':height,'inset':inset}}
    if not(start_ok and destination_ok):raise AssertionError(f'{label} pointer is outside safe viewport bounds before mouse-down: pointer={pointer!r}; actual={capture_gesture_diagnostic(page,pointer)!r}')
    return pointer


def wait_observable_geometry_change(page,before,*,label,pointer=None,timeout=8000):
    target={'objects':before['objects']}
    predicate="""({objects})=>{const keys=['left','top','width','height','rotation'];return ['title','subtitle','details'].some(id=>keys.some(k=>String(state.objects[id]?.[k]??null)!==String(objects[id]?.[k]??null)))}"""
    try:page.wait_for_function(predicate,arg=target,timeout=timeout)
    except PlaywrightTimeoutError as exc:raise AssertionError(f'{label} produced no observable transform: before={before!r}; actual={capture_gesture_diagnostic(page,pointer)!r}') from exc
    return capture_nested_history_state(page)


def wait_single_gesture_commit(page,before,*,command_label,label,pointer=None,timeout=8000):
    target={'depth':before['history']['depth'],'sequence':before['professional']['sequence'],'label':command_label}
    predicate="""({depth,sequence,label})=>undoStack.length===depth+1&&redoStack.length===0&&EInviteProfessionalEditor?.commandSequence===sequence+1&&EInviteProfessionalEditor?.lastCommand?.label===label"""
    try:page.wait_for_function(predicate,arg=target,timeout=timeout)
    except PlaywrightTimeoutError as exc:raise AssertionError(f'{label} did not settle as one gesture/one history entry: expected={target!r}; before={before!r}; actual={capture_gesture_diagnostic(page,pointer)!r}') from exc
    return capture_nested_history_state(page)


def wait_publish_ready(page,*,label,network,timeout=20000):
    predicate="""()=>document.querySelector('#saveState')?.textContent==='Saved'&&document.querySelector('#serverState')?.textContent==='Server connected'&&!document.querySelector('#publishBtn')?.disabled&&document.querySelector('#publishBtn')?.getAttribute('aria-busy')!=='true'&&(typeof serverSaveInFlight==='undefined'||serverSaveInFlight===false)&&(typeof pendingServerDocument==='undefined'||!pendingServerDocument)&&(typeof serverSaveBlockedByConflict==='undefined'||serverSaveBlockedByConflict===false)"""
    try:page.wait_for_function(predicate,timeout=timeout)
    except PlaywrightTimeoutError as exc:raise AssertionError(f'{label} publish prerequisites timed out: state={capture_gesture_diagnostic(page)!r}; network={network[-30:]!r}') from exc


def publish_and_wait(page,*,label,network,timeout=20000):
    wait_publish_ready(page,label=label,network=network,timeout=timeout)
    try:
        with page.expect_response(lambda response:response.url.endswith('/publish') and response.request.method=='POST',timeout=timeout) as info:page.locator('#publishBtn').click()
        response=info.value
    except PlaywrightTimeoutError as exc:raise AssertionError(f'{label} publish response missing: state={capture_gesture_diagnostic(page)!r}; network={network[-40:]!r}') from exc
    if response.status!=201:raise AssertionError(f'{label} publish returned {response.status}: state={capture_gesture_diagnostic(page)!r}; network={network[-40:]!r}')
    try:page.wait_for_function("()=>!document.querySelector('#publishBtn')?.disabled&&document.querySelector('#publishBtn')?.getAttribute('aria-busy')!=='true'",timeout=timeout)
    except PlaywrightTimeoutError as exc:raise AssertionError(f'{label} publish did not finalize UI: state={capture_gesture_diagnostic(page)!r}; network={network[-40:]!r}') from exc
    return response


def wait_nested_history_state(page,expected,*,history_depth=None,redo_depth=None,label='history state',timeout=8000):
    target={'expected':expected,'historyDepth':history_depth,'redoDepth':redo_depth}
    predicate="""({expected,historyDepth,redoDepth})=>{const ids=['title','subtitle','details'],keys=['left','top','width','height','rotation','groupId','parentGroupId'];const objectsOk=ids.every(id=>keys.every(k=>String(state.objects[id]?.[k]??null)===String(expected.objects[id]?.[k]??null)));const groupsOk=JSON.stringify(state.sceneGraph?.groups||{})===JSON.stringify(expected.groups||{});const selection=[...EInviteEditorBridge.getSelectedIds()].map(String).sort(),expectedSelection=[...(expected.selection||[])].map(String).sort();const selectionOk=JSON.stringify(selection)===JSON.stringify(expectedSelection);const historyOk=(historyDepth==null||undoStack.length===historyDepth)&&(redoDepth==null||redoStack.length===redoDepth);return objectsOk&&groupsOk&&selectionOk&&historyOk;}"""
    try:
        page.wait_for_function(predicate,arg=target,timeout=timeout)
    except PlaywrightTimeoutError as exc:
        diagnostic=capture_gesture_diagnostic(page)
        raise AssertionError(f'{label} timed out: expected={target!r}; actual={diagnostic!r}') from exc
    return capture_nested_history_state(page)

def main()->int:
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V17_SERVED_EDITOR',exc)
    with app_server() as (process,base,data):
      phase={'name':'server-started'}
      with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('V17_SERVED_EDITOR',exc)
        context=browser.new_context(viewport={'width':1440,'height':900});page=context.new_page();page.set_default_timeout(12_000);errors=[];bad_responses=[];network=[]
        page.on('pageerror',lambda error:errors.append(f'PAGE:{error}'))
        page.on('console',lambda message:errors.append(f'CONSOLE:{message.text}') if serious(message) else None)
        page.on('response',lambda response:(network.append(('response',response.request.method,response.status,response.url)),bad_responses.append((response.status,response.url)) if response.status>=400 else None))
        def request_failed(request):
            failure=str(request.failure);network.append(('failed',request.method,0,request.url,failure))
            try:tail=(data/'server-test.log').read_text(encoding='utf-8',errors='replace').splitlines()[-30:]
            except Exception:tail=[]
            print('V17_REQUEST_FAILED_DIAGNOSTIC',json.dumps({'phase':phase['name'],'method':request.method,'url':request.url,'failure':failure,'serverAlive':process.poll() is None,'serverExitCode':process.poll(),'serverLogTail':tail},ensure_ascii=False),flush=True)
        page.on('requestfailed',request_failed)
        page.on('dialog',lambda dialog:dialog.accept())

        phase['name']='root-navigation';root=goto_with_server_diagnostic(page,base+'/',wait_until='domcontentloaded',timeout=30_000,process=process,data=data,phase=phase,network=network);assert root and root.status==200
        phase['name']='dashboard-navigation';dashboard=goto_with_server_diagnostic(page,base+'/dashboard.html',wait_until='networkidle',timeout=30_000,process=process,data=data,phase=phase,network=network);assert dashboard.status==200
        page.locator('#authRegisterTab').click();page.locator('#email').fill('v17-editor@example.com');page.locator('#password').fill('Strong-v17-pass-123');page.locator('#registerConfirmPassword').fill('Strong-v17-pass-123');page.locator('#loginBtn').click();page.wait_for_selector('#dashboardView:not([hidden])')
        create=page.locator('.dashboard-home-hero .create');
        if not create.is_visible():create=page.locator('#emptyCreate')
        create.click();page.wait_for_selector('#createDialog[open]');page.locator('#newTitle').fill('Professional Transform ពិធីមង្គលការ');page.evaluate("document.querySelector('#newTemplate').value='gold'");page.locator('#confirmCreate').click();page.wait_for_url('**/invitations/*/editor',timeout=20_000)
        invitation_id=page.url.split('/invitations/',1)[1].split('/',1)[0]
        page.wait_for_selector('#stage .object[data-id="title"]',timeout=20_000);page.wait_for_function("()=>document.documentElement.dataset.editorReady==='true'",timeout=20_000);page.wait_for_function("()=>window.EInviteProfessionalEditor?.version===17",timeout=20_000)
        dismiss_editor_onboarding(page,timeout=20_000)
        # The initial unauthenticated root probe may correctly reject its demo
        # invitation request. Start served-editor diagnostics after auth and
        # hydration so only errors from the workflow under test are fatal.
        errors.clear();bad_responses.clear()

        phase['name']='served-editor-core'
        # Real served selection, layers, clipboard, and undo/redo coverage.
        page.locator('#stage .object[data-id="title"]').click();page.keyboard.down('Shift');page.locator('#stage .object[data-id="subtitle"]').click();page.keyboard.up('Shift');assert set(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))=={'title','subtitle'}
        page.keyboard.press('Escape');page.keyboard.press('Control+a');assert len(page.evaluate('()=>EInviteEditorBridge.getSelectedIds()'))==page.locator('#stage .object:not([data-locked="true"])').count();page.keyboard.press('Escape')
        page.locator('[data-inspector-tab="layers"]').click();page.wait_for_timeout(120);page.locator('.pe-layer-row[data-layer-id="title"] [data-layer-lock]').click();page.wait_for_timeout(180);page.locator('#stage .object[data-id="title"]').click();assert 'title' not in page.evaluate('()=>EInviteEditorBridge.getSelectedIds()');page.locator('.pe-layer-row[data-layer-id="title"] [data-layer-lock]').click()
        page.evaluate("()=>EInviteEditorBridge.select(['details'])");before_count=page.locator('#stage .object').count();page.evaluate('()=>document.activeElement?.blur?.()');page.keyboard.press('Control+c');page.keyboard.press('Control+v');page.wait_for_function('(count)=>document.querySelectorAll(\'#stage .object\').length===count+1',arg=before_count,timeout=8_000);assert page.locator('#stage .object').count()==before_count+1;page.keyboard.press('Control+z');page.wait_for_timeout(300);assert page.locator('#stage .object').count()==before_count

        # Real pointer move and resize, committed once and persisted through reload.
        title=page.locator('#stage .object[data-id="title"]');x,y=center(page,'#stage .object[data-id="title"]');page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+28,y+22,steps=5);page.mouse.up();page.wait_for_timeout(450)
        moved=page.evaluate("()=>({left:state.objects.title.left,top:state.objects.title.top,history:undoStack.length})")
        handle=page.locator('[data-pe-handle="se"]');hb=handle.bounding_box();assert hb
        page.mouse.move(hb['x']+hb['width']/2,hb['y']+hb['height']/2);page.mouse.down();page.mouse.move(hb['x']+45,hb['y']+28,steps=4);page.mouse.up();page.wait_for_timeout(500)
        resized=page.evaluate("()=>({left:state.objects.title.left,top:state.objects.title.top,width:state.objects.title.width,height:state.objects.title.height,history:undoStack.length})")
        assert resized['history']==moved['history']+1,(moved,resized)
        expected=json.dumps({k:resized[k] for k in ('left','top','width','height')})
        page.wait_for_function("""async ({id,expected})=>{const r=await fetch('/api/invitations/'+id,{cache:'no-store'});if(!r.ok)return false;const body=await r.json(),o=body.document?.objects?.title||{};return ['left','top','width','height'].every(k=>String(o[k])===String(expected[k]))}""",arg={'id':invitation_id,'expected':json.loads(expected)},timeout=20_000)
        page.reload(wait_until='domcontentloaded',timeout=30_000);page.wait_for_function("()=>window.EInviteProfessionalEditor?.version===17&&document.documentElement.dataset.editorReady==='true'",timeout=20_000)
        reloaded=page.evaluate("()=>({left:state.objects.title.left,top:state.objects.title.top,width:state.objects.title.width,height:state.objects.title.height})");assert reloaded==json.loads(expected),(reloaded,expected)

        phase['name']='nested-transform-history'
        # Differently rotated nested groups persist through authoritative undo/redo state transitions.
        setup_depth=page.evaluate('()=>undoStack.length')
        page.evaluate("""()=>{EInviteEditorBridge.transact('V18 served rotated setup',doc=>{doc.objects.title.rotation=17;doc.objects.subtitle.rotation=-26;doc.objects.details.rotation=33});EInviteEditorBridge.select(['title','subtitle']);EInviteProfessionalEditor.commands.groupSelection();EInviteEditorBridge.select(['title','subtitle','details']);EInviteProfessionalEditor.commands.groupSelection();EInviteEditorBridge.select(['title','subtitle','details'])}""")
        page.wait_for_function('(depth)=>undoStack.length>=depth+3',arg=setup_depth,timeout=8_000)
        # Do not capture the rotate baseline while a prior setup/history task can still
        # settle. The stable sample spans two animation frames and a task turn and also
        # proves the top undo snapshot matches the current document.
        wait_stable_nested_baseline(page,label='V17 nested-group setup baseline',timeout=10_000)
        ensure_handle_reachable(page,'[data-pe-handle="rotate"]',timeout=10_000)
        rotate_before=wait_stable_nested_baseline(page,label='V17 pre-rotate baseline',timeout=10_000)
        rotate_geometry=capture_view_geometry(page,'[data-pe-handle="rotate"]');rb=rotate_geometry['handle'];gb=rotate_geometry['selectionBox'];assert rb and gb
        rotate_start={'x':rb['centerX'],'y':rb['centerY']};selection_center={'x':gb['centerX'],'y':gb['centerY']};visual=rotate_geometry.get('visualViewport') or rotate_geometry['viewport'];rotate_dest,rotate_degrees=choose_rotate_destination(rotate_start,selection_center,visual['width'],visual['height']);rotate_pointer={'start':rotate_start,'destination':rotate_dest,'degrees':rotate_degrees,'selectionBox':gb,'handle':rb,'modifiers':[]}
        assert_pointer_reachable(page,rotate_pointer,label='V17 nested-group rotate')
        page.mouse.move(rotate_start['x'],rotate_start['y']);page.mouse.down();page.mouse.move(rotate_dest['x'],rotate_dest['y'],steps=8);page.mouse.up()
        wait_observable_geometry_change(page,rotate_before,label='V17 nested-group rotate',pointer=rotate_pointer,timeout=8_000)
        rotate_committed=wait_single_gesture_commit(page,rotate_before,command_label='Rotate objects',label='V17 nested-group rotate',pointer=rotate_pointer,timeout=8_000)
        assert rotate_committed['history']['cursor']==rotate_committed['history']['depth']-1,rotate_committed

        # Rotation can expand the world-space bounds well below the 900px viewport.
        # Use the real visible Selection canvas control again before reading the resize
        # handle; then re-establish the stable document/history baseline.
        ensure_handle_reachable(page,'[data-pe-handle="se"]',timeout=10_000)
        pre_resize=wait_stable_nested_baseline(page,label='V17 pre-resize baseline',timeout=10_000)
        assert pre_resize['history']['depth']==rotate_committed['history']['depth'],(rotate_committed,pre_resize)
        assert pre_resize['professional']['sequence']==rotate_committed['professional']['sequence'],(rotate_committed,pre_resize)
        resize_geometry=capture_view_geometry(page,'[data-pe-handle="se"]');hb=resize_geometry['handle'];gb=resize_geometry['selectionBox'];assert hb and gb
        resize_start={'x':hb['centerX'],'y':hb['centerY']};selection_center={'x':gb['centerX'],'y':gb['centerY']};vx=selection_center['x']-resize_start['x'];vy=selection_center['y']-resize_start['y'];distance=max(18,min(36,min(gb['width'],gb['height'])*.12));length=max(1,math.hypot(vx,vy));resize_dest={'x':resize_start['x']+vx/length*distance,'y':resize_start['y']+vy/length*distance};resize_pointer={'start':resize_start,'destination':resize_dest,'selectionBox':gb,'handle':hb,'modifiers':['Shift','Alt']}
        assert_pointer_reachable(page,resize_pointer,label='V17 nested-group resize')
        page.keyboard.down('Shift');page.keyboard.down('Alt');page.mouse.move(resize_start['x'],resize_start['y']);page.mouse.down();page.mouse.move(resize_dest['x'],resize_dest['y'],steps=8);page.mouse.up();page.keyboard.up('Alt');page.keyboard.up('Shift')
        wait_observable_geometry_change(page,pre_resize,label='V17 nested-group resize',pointer=resize_pointer,timeout=8_000)
        group_expected=wait_single_gesture_commit(page,pre_resize,command_label='Resize objects',label='V17 nested-group resize',pointer=resize_pointer,timeout=8_000)
        assert group_expected['history']['depth']==pre_resize['history']['depth']+1,(pre_resize,group_expected)
        assert group_expected['objects']!=pre_resize['objects'],(pre_resize,group_expected)
        page.keyboard.press('Control+z')
        undone=wait_nested_history_state(page,pre_resize,history_depth=pre_resize['history']['depth'],redo_depth=1,label='V17 nested-group Undo')
        assert undone['groups']==pre_resize['groups'],(pre_resize,undone)
        page.keyboard.press('Control+y')
        redone=wait_nested_history_state(page,group_expected,history_depth=group_expected['history']['depth'],redo_depth=0,label='V17 nested-group Redo')
        assert redone['groups']==group_expected['groups'],(group_expected,redone)
        page.wait_for_function("""async ({id,expected})=>{const r=await fetch('/api/invitations/'+id,{cache:'no-store'});if(!r.ok)return false;const d=(await r.json()).document||{};return Object.entries(expected.objects).every(([oid,want])=>Object.entries(want).every(([k,v])=>String(d.objects?.[oid]?.[k]??null)===String(v??null)))&&JSON.stringify(d.sceneGraph?.groups||{})===JSON.stringify(expected.groups||{})}""",arg={'id':invitation_id,'expected':group_expected},timeout=25_000)
        page.reload(wait_until='domcontentloaded',timeout=30_000);page.wait_for_function("()=>window.EInviteProfessionalEditor?.version===17&&document.documentElement.dataset.editorReady==='true'",timeout=20_000)
        group_reloaded=capture_nested_history_state(page);assert group_reloaded['objects']==group_expected['objects'] and group_reloaded['groups']==group_expected['groups'],(group_reloaded,group_expected)

        # Khmer text editing through the real inspector remains compatible.
        page.evaluate("()=>EInviteEditorBridge.select(['subtitle'])");page.wait_for_timeout(120);page.locator('[data-inspector-tab="object"]').click();text=page.locator('#textContent');text.fill('សូមស្វាគមន៍ — Welcome');text.blur();page.wait_for_timeout(900)
        assert 'សូមស្វាគមន៍' in page.evaluate("()=>state.objects.subtitle.html")

        # Preview navigation uses the current draft and contains the Khmer text.
        page.locator('#previewBtn').click();page.wait_for_selector('#modal[open]');assert page.locator('#modalBody').get_by_text('សូមស្វាគមន៍',exact=False).count()>=1;page.locator('#modal .close').click()

        # Publish, then prove draft edits are isolated until republished.
        phase['name']='first-publish';first_publish=publish_and_wait(page,label='first',network=network,timeout=20_000)
        assert first_publish.status==201
        invitation=page.evaluate("async id=>(await (await fetch('/api/invitations/'+id,{cache:'no-store'})).json())",invitation_id);slug=invitation['slug']
        public_before=page.evaluate("async slug=>(await (await fetch('/api/public/'+encodeURIComponent(slug),{cache:'no-store'})).json()).document.objects.title",slug)
        phase['name']='post-publish-edit-autosave';page.evaluate("()=>EInviteEditorBridge.select(['title'])");page.keyboard.press('Shift+ArrowDown');page.wait_for_timeout(1100)
        draft_after=page.evaluate("()=>structuredClone(state.objects.title)");assert str(draft_after['top'])!=str(public_before['top'])
        page.wait_for_function("""async ({id,top})=>{const r=await fetch('/api/invitations/'+id,{cache:'no-store'});return r.ok&&String((await r.json()).document?.objects?.title?.top)===String(top)}""",arg={'id':invitation_id,'top':draft_after['top']},timeout=20_000)
        public_still=page.evaluate("async slug=>(await (await fetch('/api/public/'+encodeURIComponent(slug),{cache:'no-store'})).json()).document.objects.title",slug);assert str(public_still['top'])==str(public_before['top'])
        phase['name']='second-publish';second_publish=publish_and_wait(page,label='second',network=network,timeout=20_000)
        assert second_publish.status==201
        public_after=page.evaluate("async slug=>(await (await fetch('/api/public/'+encodeURIComponent(slug),{cache:'no-store'})).json()).document.objects.title",slug);assert str(public_after['top'])==str(draft_after['top'])

        phase['name']='public-render-validation';public=context.new_page();public_errors=[];public.on('pageerror',lambda error:public_errors.append(str(error)));public.on('console',lambda message:public_errors.append(message.text) if serious(message) else None)
        response=goto_with_server_diagnostic(public,base+'/i/'+slug,wait_until='networkidle',timeout=30_000,process=process,data=data,phase=phase,network=network);assert response.status==200;public.wait_for_selector('#publicRoot');assert public.get_by_text('សូមស្វាគមន៍',exact=False).count()>=1
        public.set_viewport_size({'width':390,'height':844});public.wait_for_timeout(300);assert public.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1')
        page.bring_to_front();page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(450);assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1')
        assert not errors,(errors[:20],bad_responses[:30]);assert not public_errors,public_errors[:20]
        public.close();page.close();context.close();browser.close()
    print('V17_SERVED_EDITOR_TEST_PASSED');return 0

if __name__=='__main__':raise SystemExit(main())
