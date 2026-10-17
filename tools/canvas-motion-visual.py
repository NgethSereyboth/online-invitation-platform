"""Compare P1 editor screenshots with pre-motion source, without restoring checkout files.

Baseline content comes from the pre-change snapshot at
artifacts/canvas-motion/baseline/before/ (captured byte-exact from the original
patch-based reconstruction before the checkpoint commit changed the git index;
kept on disk with the other verification evidence — artifacts/ is git-ignored by
repo convention; see artifacts/canvas-motion/ledger.md). Served responses are
replaced in an isolated browser context; source files stay untouched. The
replacement covers the changed JS sources AND the changed HTML/CSS documents
(mirrors included), so the comparison sees the whole delta.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from browser_runtime import launch_chromium
from canvas_motion_playwright import open_editor
from visual_regression import diff_ratio
from playwright.sync_api import sync_playwright

SOURCES = ['src/js/editor-pro.js', 'src/js/canvas-plus.js',
           'src/js/photo-editor.js', 'src/js/app.js',
           'src/js/professional-editor.js', 'src/js/direct-manipulation.js',
           'src/js/editor/editor-core.js']

# Served HTML/CSS documents changed by the same delta (source tree and python mirrors).
STYLE_SOURCES = ['src/html/index.html', 'src/css/editor-pro.css', 'src/css/editor-suite.css',
                 'src/python/index.html', 'src/python/editor-pro.css',
                 'src/python/build/editor-suite.css']


def baseline_sources(root):
    """Pre-change content for every replaced artifact.

    The baseline is the pre-change snapshot (artifacts/canvas-motion/baseline/before/),
    captured byte-exact from the original patch reconstruction and kept on disk with
    the other verification evidence. No git-index dependency remains, so the
    comparison works against any later working tree.
    """
    snapshot_root = root / 'artifacts/canvas-motion/baseline/before'
    sources = {}
    for path in SOURCES + STYLE_SOURCES:
        snapshot = snapshot_root / path
        assert snapshot.exists(), f'baseline snapshot missing: {snapshot}'
        sources[path] = snapshot.read_text(encoding='utf-8')
    return sources


def run(base, phase, out_override=None):
    out = Path(out_override) if out_override else ROOT / 'artifacts/canvas-motion' / phase
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    old = baseline_sources(ROOT)
    current_suite = (ROOT / 'src/js/editor-suite.js').read_text(encoding='utf-8')
    old_suite = current_suite
    for path in SOURCES:
        current = (ROOT / path).read_text(encoding='utf-8')
        if current in old_suite:
            old_suite = old_suite.replace(current, old[path])
    replacements = [(current_suite, old_suite)]
    replacements += [((ROOT / p).read_text(encoding='utf-8').rstrip(), old[p].rstrip()) for p in SOURCES]
    replacements += [((ROOT / p).read_text(encoding='utf-8').rstrip(), old[p].rstrip()) for p in STYLE_SOURCES]
    document_pattern = re.compile(r'.*\.(?:js|css|html)(?:\?.*)?$')
    rows = []
    with sync_playwright() as runtime:
        browser = launch_chromium(runtime)
        try:
            for width, height in [(375, 812), (768, 1024), (1366, 900)]:
                for mode in ['light', 'dark']:
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
                        open_editor(page, base,
                                    identity=f'visual-{width}-{mode}-{variant}',
                                    require_motion=variant == 'after')
                        page.evaluate("mode=>{localStorage.setItem('einvite-theme-mode',mode);document.documentElement.dataset.theme=mode;document.documentElement.dataset.themeMode=mode}", mode)
                        page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}')
                        page.evaluate("() => {EInviteToolController.setTool('select',{announce:false});EInviteEditorBridge.select([])}")
                        page.wait_for_timeout(250)
                        name = f'{variant}-{width}-{mode}.png'
                        shots[variant] = out / name
                        page.screenshot(path=str(shots[variant]))
                        context.close()
                    ratio = diff_ratio(shots['before'], shots['after'])
                    rows.append({'width': width, 'mode': mode, 'difference': ratio,
                                 'before': str(shots['before'].relative_to(ROOT)), 'after': str(shots['after'].relative_to(ROOT))})
                    print(json.dumps(rows[-1]), flush=True)
                    assert ratio <= .035, rows[-1]
        finally:
            browser.close()
    (out / 'visual-comparison.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print('CANVAS_MOTION_VISUAL_PASSED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8137')
    parser.add_argument('--phase', choices=['P1'], default='P1')
    parser.add_argument('--out', default=None,
                        help='override output directory (default artifacts/canvas-motion/<phase>)')
    args = parser.parse_args()
    run(args.base, args.phase, args.out)
