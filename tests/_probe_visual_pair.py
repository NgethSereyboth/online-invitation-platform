import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import importlib.util
spec = importlib.util.spec_from_file_location('cmv', ROOT / 'tools' / 'canvas-motion-visual.py')
cmv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmv)
from browser_runtime import launch_chromium
from canvas_motion_playwright import open_editor
from visual_regression import diff_ratio
from playwright.sync_api import sync_playwright
import re
from v14_test_utils import app_server

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
out = ROOT / 'artifacts/canvas-motion/verify/pair-1366-dark'
out.mkdir(parents=True, exist_ok=True)

with app_server({'EINVITE_DEV_AUTH_TOKENS': '0'}) as (_, base, _):
    with sync_playwright() as runtime:
        browser = launch_chromium(runtime)
        width, height, mode = 1366, 900, 'dark'
        shots = {}
        for variant in ['before', 'after']:
            context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=mode)
            if variant == 'before':
                def baseline_response(route):
                    response = route.fetch()
                    body = response.text()
                    for current, previous in replacements:
                        body = body.replace(current, previous)
                    route.fulfill(response=response, body=body)
                context.route(document_pattern, baseline_response)
            page = context.new_page()
            open_editor(page, base, identity=f'probe-pair-{width}-{mode}-{variant}',
                        require_motion=variant == 'after')
            page.evaluate("mode=>{localStorage.setItem('einvite-theme-mode',mode);document.documentElement.dataset.theme=mode;document.documentElement.dataset.themeMode=mode}", mode)
            page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}')
            page.evaluate("() => {EInviteToolController.setTool('select',{announce:false});EInviteEditorBridge.select([])}")
            page.wait_for_timeout(250)
            shots[variant] = out / f'{variant}-{width}-{mode}.png'
            page.screenshot(path=str(shots[variant]))
            context.close()
        browser.close()
ratio = diff_ratio(shots['before'], shots['after'])
print('PAIR 1366 dark difference', ratio, flush=True)
assert ratio <= .035, ratio
print('PAIR_PASSED')
