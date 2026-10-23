import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
import os
os.chdir(ROOT)

from browser_runtime import mark_editor_onboarding_seen, launch_chromium
from playwright.sync_api import sync_playwright

preset = json.loads(Path('artifacts/next-work/fb-35/seed-preset.json').read_text())
slug = preset['slug']
base = 'http://127.0.0.1:8124'
out_dir = Path('artifacts/next-work/review-r3/before')
SETTLE = 1200

SHOTS = [
    ('public-en-light-375',  'light', 'en', 375, 667),
    ('public-km-light-375',  'light', 'km', 375, 667),
    ('public-km-dark-375',   'dark',  'km', 375, 667),
    ('public-km-light-1440', 'light', 'km', 1440, 900),
]

with sync_playwright() as pw:
    browser = launch_chromium(pw)
    try:
        for name, theme, lang, w, h in SHOTS:
            ctx = browser.new_context(color_scheme=theme, reduced_motion='reduce',
                                      locale='km-KH' if lang == 'km' else 'en-US',
                                      viewport={'width': w, 'height': h})
            page = ctx.new_page()
            page.add_init_script(
                f"try{{localStorage.setItem('einvite-theme-mode','{theme}');"
                f"localStorage.setItem('einvite-lang','{lang}');}}catch(e){{}}"
                + mark_editor_onboarding_seen())
            page.goto(f'{base}/i/{slug}', wait_until='load', timeout=45000)
            try:
                page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:
                pass
            # Open the invitation (the audit's reviewed state: header + sections).
            btn = page.get_by_role('button', name='Open invitation').first
            if btn.count() == 0:
                btn = page.locator('text=Open invitation').first
            btn.click(timeout=8000)
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(SETTLE)
            crash = page.evaluate("() => { const d = document.documentElement;"
                                  "return (d.scrollWidth > window.innerWidth + 1) || window.innerWidth; }")
            out = out_dir / f'{name}.png'
            page.screenshot(path=str(out))
            print(f'OK {name} opened scrollWidthProbe={crash} -> {out}', flush=True)
            ctx.close()
    finally:
        browser.close()
print('PUBLIC_OPENED_DONE')
