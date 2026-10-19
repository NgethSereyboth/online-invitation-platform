import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from v14_test_utils import app_server
import canvas_motion_playwright as cm

PROBE = """() => {
  const v = document.querySelector('#canvasViewport'), s = document.querySelector('#stage');
  return {
    zoom: window.EInviteCanvasViewController?.zoom,
    ls: localStorage.getItem('sovan-editor-zoom'),
    fitApplied: document.documentElement.dataset.workspaceFitApplied, tf: s.style.transform, rw: Math.round(s.getBoundingClientRect().width), rh: Math.round(s.getBoundingClientRect().height),
    vw: v?.clientWidth, vh: v?.clientHeight,
    sw: s?.offsetWidth, sh: s?.offsetHeight,
    objs: document.querySelectorAll('#stage .object').length, rw: Math.round(s.getBoundingClientRect().width), rh: Math.round(s.getBoundingClientRect().height), tf: s.style.transform, vr: Math.round(v.getBoundingClientRect().height),
    fitVal: Math.min((v.clientWidth-70)/s.offsetWidth,(v.clientHeight-70)/s.offsetHeight,1.5)
  };
}"""

with app_server({'EINVITE_DEV_AUTH_TOKENS': '0'}) as (_, base, _):
    with sync_playwright() as rt:
        browser = launch_chromium(rt)
        for w, h in [(375, 812), (768, 1024), (1366, 900)]:
            ctx = browser.new_context(viewport={'width': w, 'height': h}, color_scheme='light')
            page = ctx.new_page()
            cm.open_editor(page, base, identity=f'probe-open-{w}')
            page.wait_for_timeout(800)
            print('WIDTH', w, page.evaluate(PROBE), flush=True)
            ctx.close()
        browser.close()
