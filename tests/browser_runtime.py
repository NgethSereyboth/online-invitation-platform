"""Cross-platform Playwright Chromium launcher used by review tests."""
from __future__ import annotations
import os,re,time
from pathlib import Path

def browser_required():return os.environ.get('EINVITE_REQUIRE_BROWSER','0').lower() in {'1','true','yes'}
def skipped(label,exc):
 print(f'{label}_SKIPPED',exc)
 return 1 if browser_required() else 0

def add_style_tag_with_nonce(page, *, content=None, path=None, nonce=None):
 """Add a test stylesheet to a CSP-served page without weakening its policy.

 Playwright's `page.add_style_tag` creates a <style> element with no nonce;
 the editor pages use `style-src 'self' 'nonce-...'`, so the browser rightly
 blocks that injection. Reuse the nonce the server injected into the page's
 own <style> tags, exactly as the served styles do.
 """
 nonce=nonce or page.evaluate("()=>document.querySelector('style[nonce]')?.getAttribute('nonce')||''")
 if not nonce:
  raise AssertionError('CSP style nonce not found on the served page')
 css=content if content is not None else Path(path).read_text(encoding='utf-8')
 page.evaluate("""({css,nonce})=>{const style=document.createElement('style');style.setAttribute('nonce',nonce);style.textContent=css;document.head.append(style)}""",{'css':css,'nonce':nonce})

def mark_editor_onboarding_seen():
 """Init script that seeds the editor tour's 'seen' storage before page JS runs.

 NW-6.2 capture-determinism fix: `final-experience.js` already persists its per-identity
 seen key (`einvite-final-tour-seen-v2:{identity}:studio-v27`) and migrates the legacy
 `einvite-final-tour-seen-v1` key across versions, so seeding the legacy key makes the
 app itself decide the tour is seen — same mechanism a real second visit uses, without
 touching the first-run UX. Seeding must happen in an init script (document-scoped, before
 any page script) so `window.EInviteOnboardingReady` resolves with `shown:false` on the
 first probe instead of after a manual dismissal. Returns the script string to pass to
 `context.add_init_script`.
 """
 return "try{localStorage.setItem('einvite-final-tour-seen-v1','1')}catch{}"


def dismiss_editor_onboarding(page,*,timeout=10000):
 page.wait_for_function("()=>document.documentElement.dataset.editorReady==='true'",timeout=timeout)
 page.evaluate("async()=>{if(window.EInviteOnboardingReady)await window.EInviteOnboardingReady}")
 dismiss=page.locator('#finalTourDismiss')
 if dismiss.count() and dismiss.is_visible():
  dismiss.click()
  page.wait_for_function("()=>{const d=document.querySelector('.final-tour');return !d||!d.open||d.hidden||getComputedStyle(d).display==='none'}",timeout=timeout)


def reveal_inspector_control(page,selector,*,timeout=10000):
 """Open the inspector disclosures that contain a control.

 The 2026-10-30 reorganisation files the Edit pane into ``details.ix-group``
 sections and ``details.ix-sub`` sub-sections, and hides the legacy
 ``#typographyControls`` shell once its controls are filed. A control inside a
 closed disclosure is reachable exactly as a user reaches it: open the closed
 ancestors. This does that and then waits for Playwright's visible state; it
 does not force the control visible, click through it, or relax any wait.
 """
 control=page.locator(selector)
 control.wait_for(state='attached',timeout=timeout)
 for _ in range(6):
  opened=page.evaluate("""sel=>{const el=document.querySelector(sel);if(!el)return false;for(let n=el.parentElement;n;n=n.parentElement){if(n.tagName==='DETAILS'&&!n.open){n.open=true;return true}}return false}""",selector)
  if not opened:break
 control.wait_for(state='visible',timeout=timeout)

def open_studio_tab(page,tab,*,timeout=10000):
 """Activate one left-rail studio tab by its data attribute.

 ``studio-experience.js`` rebuilds the rail from the old static markup, so the
 visible label is presentation: `Event details` became `Event`. The
 ``data-studio-tab`` value stayed the stable contract across that rename, and
 clicking it is exactly what a user clicks, so this drives the real control
 instead of hunting a label that may move again.
 """
 button=page.locator(f'[data-studio-tab="{tab}"]:visible').first
 if not button.count():
  # Narrow layouts move the rail into the tools drawer; open it first.
  drawer=page.locator('[data-editor-drawer="left"], [data-drawer-open="left"]').first
  if drawer.count() and drawer.is_visible():drawer.click()
 button.wait_for(state='visible',timeout=timeout);button.click()
 page.locator(f'[data-studio-pane="{tab}"].active').wait_for(state='visible',timeout=timeout)

def open_event_details(page,*,timeout=10000):
 rsvp=page.get_by_role('checkbox',name='Enable RSVP attendance form',exact=True)
 venue=page.get_by_role('textbox',name='Venue — English',exact=True)
 if rsvp.count() and venue.count() and rsvp.is_visible() and venue.is_visible():return rsvp,venue
 if page.locator('[data-studio-tab="event"]:visible').count():open_studio_tab(page,'event',timeout=timeout)
 else:
  launcher=page.locator('[data-flow-open="event"]:visible').first
  launcher.wait_for(state='visible',timeout=timeout);launcher.click()
 rsvp.wait_for(state='visible',timeout=timeout);venue.wait_for(state='visible',timeout=timeout)
 return rsvp,venue

def _control_hit_diagnostic(page,selector):
 return page.evaluate("""sel=>{const e=document.querySelector(sel),r=e?.getBoundingClientRect(),cs=e?getComputedStyle(e):null,vv=window.visualViewport;const point=r?{x:Math.min(innerWidth-2,Math.max(1,r.left+r.width/2)),y:Math.min(innerHeight-2,Math.max(1,r.top+r.height/2))}:null;const stack=point?[...document.elementsFromPoint(point.x,point.y)].map((n,i)=>({i,tag:n.tagName,id:n.id||'',class:String(n.className||''),role:n.getAttribute?.('role')||'',aria:n.getAttribute?.('aria-label')||''})):[];const left=document.querySelector('aside.left'),right=document.querySelector('aside.right'),viewport=document.querySelector('#canvasViewport,.canvas-viewport');return {selector:sel,viewport:{innerWidth,innerHeight,scrollX,scrollY},visualViewport:vv?{width:vv.width,height:vv.height,offsetLeft:vv.offsetLeft,offsetTop:vv.offsetTop,scale:vv.scale}:null,body:{class:document.body.className,drawer:document.body.dataset.editorDrawer||'',layout:document.body.dataset.editorLayout||''},drawers:{left:{aria:left?.getAttribute('aria-hidden'),class:left?.className||'',scrollTop:left?.scrollTop||0},right:{aria:right?.getAttribute('aria-hidden'),class:right?.className||'',scrollTop:right?.scrollTop||0}},canvas:{scrollLeft:viewport?.scrollLeft||0,scrollTop:viewport?.scrollTop||0,rect:viewport?Object.fromEntries(['x','y','left','top','right','bottom','width','height'].map(k=>[k,viewport.getBoundingClientRect()[k]])):null},control:e&&r&&cs?{rect:Object.fromEntries(['x','y','left','top','right','bottom','width','height'].map(k=>[k,r[k]])),display:cs.display,visibility:cs.visibility,position:cs.position,zIndex:cs.zIndex,pointerEvents:cs.pointerEvents,opacity:cs.opacity}:null,point,stack};}""",selector)

def wait_for_reachable_control(page,selector,*,timeout=8000):
 control=page.locator(selector);control.wait_for(state='visible',timeout=timeout)
 deadline=time.time()+timeout/1000;last=None
 while time.time()<deadline:
  control.scroll_into_view_if_needed()
  last=page.evaluate("""async sel=>{const e=document.querySelector(sel);if(!e)return {ok:false,reason:'missing'};const frame=()=>new Promise(resolve=>requestAnimationFrame(resolve));const snap=()=>{const r=e.getBoundingClientRect();return {left:r.left,top:r.top,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};await frame();const a=snap();await frame();const b=snap();const stable=['left','top','width','height'].every(k=>Math.abs(a[k]-b[k])<=.5);const x=Math.min(innerWidth-2,Math.max(1,b.left+b.width/2)),y=Math.min(innerHeight-2,Math.max(1,b.top+b.height/2)),top=document.elementFromPoint(x,y),stack=[...document.elementsFromPoint(x,y)];const reachable=!!top&&(top===e||e.contains(top));return {ok:stable&&b.width>0&&b.height>0&&reachable,stable,reachable,rect:b,x,y,top:top?{tag:top.tagName,id:top.id||'',class:String(top.className||'')}:null,stack:stack.slice(0,8).map(n=>({tag:n.tagName,id:n.id||'',class:String(n.className||'')}))};}""",selector)
  if last.get('ok'):return last
  page.wait_for_timeout(50)
 diagnostic=_control_hit_diagnostic(page,selector)
 raise AssertionError(f'Control {selector} never became stably reachable: last={last!r}; diagnostic={diagnostic!r}')

def launch_chromium(playwright,*,headless=True):
 if os.name=='nt':
  openssl=os.environ.get('OPENSSL_CONF','').strip()
  if openssl and not Path(openssl).is_file():
   print(f'Ignoring invalid OPENSSL_CONF for Playwright child process: {openssl}')
   os.environ.pop('OPENSSL_CONF',None)
 kwargs={'headless':headless};explicit=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE','').strip();system=Path('/usr/bin/chromium')
 if explicit:kwargs['executable_path']=explicit
 elif system.is_file():kwargs['executable_path']=str(system)
 if os.name!='nt':kwargs['args']=['--no-sandbox','--disable-dev-shm-usage']
 return playwright.chromium.launch(**kwargs)
