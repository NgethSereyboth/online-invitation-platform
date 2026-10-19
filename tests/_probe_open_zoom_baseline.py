import sys, re, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from v14_test_utils import app_server
import canvas_motion_playwright as cm

spec = importlib.util.spec_from_file_location('cmv', ROOT / 'tools/canvas-motion-visual.py')
cmv = importlib.util.module_from_spec(spec); spec.loader.exec_module(cmv)

old = cmv.baseline_sources(ROOT)
current_suite = (ROOT / 'src/js/editor-suite.js').read_text(encoding='utf-8')
old_suite = current_suite
for path in cmv.SOURCES:
    current = (ROOT / path).read_text(encoding='utf-8')
    if current in old_suite:
        old_suite = old_suite.replace(current, old[path])
replacements = [(current_suite, old_suite)]
replacements += [((ROOT / p).read_text(encoding='utf-8').rstrip(), old[p].rstrip()) for p in cmv.SOURCES]
replacements += [((ROOT / p).read_text(encoding='utf-8').rstrip(), old[p].rstrip()) for p in cmv.STYLE_SOURCES]
document_pattern = re.compile(r'.*\.(?:js|css|html)(?:\?.*)?$')

PROBE = """() => {
  const v = document.querySelector('#canvasViewport'), s = document.querySelector('#stage');
  return {
    zoom: window.EInviteCanvasViewController?.zoom,
    fitApplied: document.documentElement.dataset.workspaceFitApplied, tf: s.style.transform, rw: Math.round(s.getBoundingClientRect().width), rh: Math.round(s.getBoundingClientRect().height),
    vw: v?.clientWidth, vh: v?.clientHeight,
    sw: s?.offsetWidth, sh: s?.offsetHeight,
    objs: document.querySelectorAll('#stage .object').length, rw: Math.round(s.getBoundingClientRect().width), rh: Math.round(s.getBoundingClientRect().height), tf: s.style.transform, vr: Math.round(v.getBoundingClientRect().height)
  };
}"""

with app_server({'EINVITE_DEV_AUTH_TOKENS': '0'}) as (_, base, _):
    with sync_playwright() as rt:
        browser = launch_chromium(rt)
        for w, h in [(375, 812), (768, 1024), (1366, 900)]:
            ctx = browser.new_context(viewport={'width': w, 'height': h}, color_scheme='light')
            def baseline_response(route):
                response = route.fetch()
                body = response.text()
                for current, previous in replacements:
                    body = body.replace(current, previous)
                route.fulfill(response=response, body=body)
            ctx.route(document_pattern, baseline_response)
            page = ctx.new_page()
            cm.open_editor(page, base, identity=f'probe-base-{w}', require_motion=False)
            page.wait_for_timeout(800)
            print('BASE', w, page.evaluate(PROBE), 'motion=', page.evaluate('() => !!window.EInviteMotion'), 'ctl=', page.evaluate('() => !!window.EInviteCanvasViewController'), flush=True)
            ctx.close()
        browser.close()
