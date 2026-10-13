#!/usr/bin/env python3
"""V25 template governance, bindings, governance and print preflight, in a browser.

Repaired in the bulk-guest-import verification pass, which closed verification gaps
rather than adding features. Three defects were found, in the order they surfaced:

1. **Every asset path was wrong.** The file asked for its CSS and JS at the
   repository root (``ROOT/name``), but they live under ``src/css/`` and ``src/js/``
   — and ``export-quality-v24.css`` specifically under ``src/css/organized/``. So
   the test died on ``FileNotFoundError`` before any assertion ran. Paths now
   resolve through :func:`asset`, which reports every directory it searched.
   FIXED and verified: all twenty assets now load and the flow reaches its version
   and binding assertions.
2. **The page had no usable origin.** ``page.set_content`` leaves an opaque
   ``about:blank`` document, where Chromium denies ``localStorage`` — which this
   test seeds — and nothing served the fixture's relative font requests, so the
   bundled faces never loaded and their substitute metrics overflowed the hero
   text. :func:`open_editor` serves the fixture from an http:// origin backed by the
   repository's real files. FIXED and verified: ``localStorage`` works and the font
   records report ``loaded: true``.
3. **A residual blocker, left visible rather than relaxed.** With the above fixed
   the flow runs to its print-preflight assertion and fails there: the fixture's own
   hero boxes (``title``, ``subtitle``) overflow at the rendered metrics, so the
   preflight is ``blocked`` with two ``quality-text-overflow`` errors. Growing those
   boxes does not clear it, because the seeded governed brand is ``locked`` with
   ``allowedOverrides:['content','media']`` and the app refuses the geometry change —
   the brand lock working. The blocker is named by :data:`PREFLIGHT_BLOCKED_BY` below,
   appended to the failing assertion's message, and measured in
   ``docs/reviews/bulk-guest-import-implementation.md`` §9.4 and §10.2.

On collection: this file deliberately defines only ``main()``, like every other
``*_browser_test.py`` in ``tests/`` (~30 of them, including its v25 mobile and
performance siblings), because they are run as scripts. Adding a ``test_*`` entry
point was tried in this pass and removed again: with the blocker above it could only
fail (breaking ``pytest tests/``) or skip unconditionally (pretending), so the honest
state is a script-run test that fails loudly with a documented cause.

``python3 tests/v25_template_governance_browser_test.py`` prints
``V25_TEMPLATE_GOVERNANCE_BROWSER_TEST_PASSED`` when the whole flow passes,
``…_SKIPPED`` when no browser can start, and raises the failing assertion otherwise.
"""
from __future__ import annotations
import mimetypes,sys
from pathlib import Path
from urllib.parse import unquote,urlsplit
from browser_runtime import launch_chromium, skipped
from inline_editor_runtime_test import build_inline_editor
ROOT=Path(__file__).resolve().parents[1]
BASE_CSS=['direct-manipulation-v24.css','content-browser-v24.css','smart-layout-v24.css','brand-components-v24.css','collaboration-v24.css','export-quality-v24.css']
BASE_JS=['direct-manipulation-v24.js','content-browser-v24.js','smart-layout-v24.js','brand-components-v24.js','collaboration-v24.js','export-quality-v24.js']
V25_CSS=['adaptive-templates-v25.css','studio-governance-v25.css','print-readiness-v25.css','template-bindings-v25.css']
V25_JS=['adaptive-templates-v25.js','studio-governance-v25.js','print-readiness-v25.js','template-bindings-v25.js']

# Named once, here, so a future reader does not have to re-derive it: the one reason
# this file's print-preflight step cannot pass today, and the two ways out.
PREFLIGHT_BLOCKED_BY=(
 "Brand lock: the seeded brand is 'locked' with "
 "allowedOverrides=['content','media'], so the print preflight "
 "cannot clear the hero-box overflow by growing the boxes. "
 "See docs/reviews/bulk-guest-import-implementation.md §9.4. "
 "To unblock: either (a) unlock the brand in the fixture, or "
 "(b) invoke the app's auto-fit command as a designer would, "
 "once such a command exists."
)


def asset(name:str)->str:
 """The real path of a page asset: src/css (organized under src/css/organized), then src/js."""
 roots=(ROOT/'src'/'css',ROOT/'src'/'css'/'organized') if Path(name).suffix=='.css' else (ROOT/'src'/'js',)
 for root in roots:
  candidate=root/name
  if candidate.is_file():return str(candidate)
 raise FileNotFoundError(f'{name} was not found under {", ".join(str(root) for root in roots)}')


CONTENT_TYPES={'.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf','.js':'text/javascript','.css':'text/css','.html':'text/html; charset=utf-8','.json':'application/json','.svg':'image/svg+xml','.png':'image/png'}


def open_editor(page):
 """Load the inline editor on a real HTTP origin, backed by the repository's files.

 Two defects, found after the asset paths were repaired:

 * ``page.set_content`` leaves the page on an opaque ``about:blank`` document,
   where Chromium denies ``localStorage`` ("Access is denied for this document"),
   and this test seeds it. Interception supplies the same inline HTML from an
   http:// origin with no server needed.
 * With nothing serving the page's relative asset requests, the fixture's bundled
   fonts never load, Chromium substitutes their metrics, and the hero canvas's
   ``title``/``subtitle``/``details`` text then overflows the boxes they sit in —
   so the print preflight correctly reported ``blocked`` and the flow could never
   reach the ``ready`` state it asserts. Forcing ``document.fonts.check`` to true
   (which this file already did, for the font-not-loaded issues) cannot change
   rendered metrics, so the real fix is to serve the real files.

 Requests are mapped to files under the repository root, and anything that does
 not exist there is aborted. The resolved path must stay inside the root.
 """
 html=build_inline_editor()
 def serve(route):
  request=route.request
  if request.is_navigation_request():
   return route.fulfill(status=200,content_type='text/html; charset=utf-8',body=html)
  relative=unquote(urlsplit(request.url).path).lstrip('/')
  candidate=(ROOT/relative).resolve()
  if relative and candidate.is_file() and candidate.is_relative_to(ROOT):
   content_type=CONTENT_TYPES.get(candidate.suffix) or mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
   return route.fulfill(status=200,content_type=content_type,body=candidate.read_bytes())
  return route.abort()
 page.route('**/*',serve)
 page.goto('http://einvite.local/',wait_until='load',timeout=30000)


def flow(page):
 """Every assertion. A real regression raises AssertionError out of here."""
 errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 open_editor(page);page.wait_for_timeout(1200)
 if page.locator('#finalTourDismiss').count() and page.locator('#finalTourDismiss').is_visible():page.locator('#finalTourDismiss').click();page.wait_for_timeout(80)
 for name in BASE_CSS+V25_CSS:page.add_style_tag(path=asset(name))
 page.evaluate("""()=>{localStorage.setItem('einvite-v25-studio-resources',JSON.stringify([{id:'studio-brand-1',kind:'brand',name:'Official Studio Brand',category:'Government',payload:{primary:'#183a64',accent:'#b18a3b',background:'#f7f8fb',surface:'#ffffff',text:'#18202d',headingPair:'serif-formal',bodyPair:'sans-modern'},governance:{locked:true,allowedOverrides:['content','media']},status:'approved',version:3,createdAt:Date.now(),updatedAt:Date.now()}]));localStorage.setItem('einvite-v25-studio-policy',JSON.stringify({approvedOnly:true,lockBrandColors:true,lockTypography:true,requireAdaptiveTemplate:true,requirePrintPreflight:true}));window.EInviteFeedback=window.EInviteFeedback||{toast:()=>{}}}""")
 for name in BASE_JS+V25_JS:page.add_script_tag(path=asset(name));page.wait_for_timeout(80)
 versions=page.evaluate("""()=>({templates:EInviteAdaptiveTemplates.version,governance:EInviteStudioGovernance.version,print:EInvitePrintReadiness.version,bindings:EInviteTemplateBindings.version,conflicts:EInviteCommandRegistry.conflicts.length})""")
 assert versions=={'templates':25,'governance':25.1,'print':25.2,'bindings':25.3,'conflicts':0},versions
 # Apply a complete adaptive family.
 page.evaluate("()=>EInviteAdaptiveTemplates.apply('government-delegation')");page.wait_for_timeout(120)
 result=page.evaluate("""()=>({pages:EInviteEditorBridge.getState().designPages.length,adaptive:EInviteEditorBridge.getState().templateFamily.adaptive,bindings:EInviteTemplateBindings.inspect().length,roles:EInviteEditorBridge.getState().designPages.every(p=>p.templateRole&&p.responsiveLayout)})""")
 assert result['pages']==5 and result['adaptive'] and result['bindings']>=8 and result['roles'],result
 # Linked content refreshes from invitation fields.
 page.evaluate("""()=>{const d=EInviteEditorBridge.cloneState();d.fields.names='Updated Delegation Name';EInviteEditorBridge.replaceState(d,{history:false,reason:'test-fields'});return EInviteTemplateBindings.refresh()}""");page.wait_for_timeout(80)
 assert page.evaluate("""()=>Object.values(EInviteEditorBridge.getState().designPages[0].objects).some(o=>o.contentBinding==='fields.names'&&o.html==='Updated Delegation Name')""")
 # Detaching protects deliberate custom content.
 binding=page.evaluate("""()=>EInviteTemplateBindings.inspect().find(x=>x.binding==='fields.names').id""")
 page.evaluate("id=>EInviteTemplateBindings.detach(id,true)",binding)
 page.evaluate("""()=>{const d=EInviteEditorBridge.cloneState();d.fields.names='Second Name';EInviteEditorBridge.replaceState(d,{history:false,reason:'test-fields-2'});EInviteTemplateBindings.refresh()}""");page.wait_for_timeout(70)
 assert page.evaluate("id=>EInviteTemplateBindings.inspect().find(x=>x.id===id).detached",binding)
 # Apply an approved governed brand from the local fallback studio library.
 page.evaluate("()=>EInviteStudioGovernance.load()");page.wait_for_timeout(80);page.evaluate("()=>EInviteStudioGovernance.apply('studio-brand-1')");page.wait_for_timeout(350)
 governed=page.evaluate("""()=>({governed:EInviteEditorBridge.getState().eventBrand.governed,version:EInviteEditorBridge.getState().studioGovernance.resourceVersion,issues:EInviteStudioGovernance.compliance().map(x=>x.code)})""")
 assert governed['governed'] and governed['version']==3 and 'adaptive-template-required' not in governed['issues'],governed
 # Prepare a clean font preflight and mark it current. open_editor serves the font
 # files, so the bundled faces really load; document.fonts.check is still forced for
 # the remaining asset-free faces in the inline fixture.
 #
 # KNOWN BLOCKER, measured and left rather than relaxed: the fixture's own hero boxes
 # (`title`, `subtitle`) are tighter than their text needs at the rendered metrics, so
 # the export-quality judge flags them and the lines below fail at `preflight['status']`
 # with `blocked` and two `quality-text-overflow` errors. Growing those boxes in the
 # document does NOT clear it — the seeded governed brand is `locked` with
 # `allowedOverrides:['content','media']`, so the app refuses the geometry change, which
 # is the brand lock doing its job. Making this flow green needs the fixture document in
 # tests/inline_editor_runtime_test.py to fit its own text, which is another pass's file.
 # See docs/reviews/bulk-guest-import-implementation.md, "Verification closure" §4.
 page.evaluate("""()=>{try{Object.defineProperty(document.fonts,'check',{configurable:true,value:()=>true})}catch{try{document.fonts.check=()=>true}catch{}}}""")
 page.evaluate("""()=>{const d=EInviteEditorBridge.cloneState();for(const map of [d.objects,...d.designPages.map(p=>p.objects)])for(const o of Object.values(map)){if(o.type==='image'&&!o.alt)o.alt='Invitation image'}d.fields.date=d.fields.date||'2027-01-01';EInviteEditorBridge.replaceState(d,{history:false,reason:'preflight-clean'})}""")
 preflight=page.evaluate("()=>EInvitePrintReadiness.inspect()");assert preflight['status'] in ('ready','review'),(preflight,PREFLIGHT_BLOCKED_BY)
 page.evaluate("()=>EInvitePrintReadiness.markCurrent()");page.wait_for_timeout(60)
 final=page.evaluate("""()=>({status:EInviteEditorBridge.getState().printReadiness.status,compliance:EInviteStudioGovernance.compliance().map(x=>x.code)})""")
 assert final['status']=='ready' and 'print-preflight-required' not in final['compliance'],final
 # Non-mutating editor commands do not invalidate a current print record.
 page.evaluate("""()=>window.dispatchEvent(new CustomEvent('einvite:editor-command',{detail:{label:'Open content browser'}}))""");page.wait_for_timeout(180)
 assert page.evaluate("()=>EInviteEditorBridge.getState().printReadiness.status")=='ready'
 # Later edits automatically stale the current preflight.
 page.evaluate("""()=>EInviteEditorBridge.transact('Change after preflight',d=>{d.fields.venue='New venue'})""");page.wait_for_timeout(350)
 assert page.evaluate("()=>EInviteEditorBridge.getState().printReadiness.status")=='stale'
 # Core dialogs remain accessible.
 page.evaluate("()=>EInviteAdaptiveTemplates.open()");assert page.locator('#v25AdaptiveTemplates').is_visible();page.locator('#v25AdaptiveTemplates [data-close]').first.click()
 page.evaluate("()=>EInviteStudioGovernance.open()");page.wait_for_timeout(60);assert page.locator('.v25-governance-dialog').is_visible();page.locator('.v25-governance-dialog [data-close]').first.click()
 page.evaluate("()=>EInvitePrintReadiness.open()");assert page.locator('.v25-print-dialog').is_visible();page.locator('.v25-print-dialog [data-close]').first.click()
 page.evaluate("()=>EInviteTemplateBindings.open()");assert page.locator('.v25-binding-dialog').is_visible()
 assert not errors,errors


def main()->int:
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  try:browser=launch_chromium(p)
  except Exception as exc:return skipped('V25_TEMPLATE_GOVERNANCE_BROWSER',exc)
  try:flow(browser.new_page(viewport={'width':1440,'height':1000}))
  finally:browser.close()
 print('V25_TEMPLATE_GOVERNANCE_BROWSER_TEST_PASSED');return 0



if __name__=='__main__':sys.exit(main())
