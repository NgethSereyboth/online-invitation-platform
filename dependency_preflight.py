"""Release dependency preflight for V14 stabilization.

The release gate verifies that required packages are importable *and* that a
real Chromium process can be launched. Merely finding an executable on disk is
not enough because broken Playwright installs and locked enterprise images must
fail the release gate honestly.
"""
from __future__ import annotations
import argparse,importlib.util,os
from pathlib import Path

REQUIREMENTS={
 "Pillow":("PIL","responsive images, social cards and image processing"),
 "qrcode":("qrcode","public, personalized and authenticator QR images"),
 "argon2-cffi":("argon2","Argon2id password hashing"),
 "cryptography":("cryptography","WebAuthn/passkey verification"),
 "Playwright":("playwright","required live Chromium acceptance tests"),
 "FontTools":("fontTools","bundled WOFF2 validation"),
 "Brotli":("brotli","WOFF2 Brotli decompression"),
}

def chromium_candidates():
 values=[]
 env=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE','').strip()
 if env:values.append(Path(env))
 for fixed in ('/usr/bin/chromium','/usr/bin/chromium-browser','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'):
  values.append(Path(fixed))
 cache=Path.home()/'.cache'/'ms-playwright'
 if cache.exists():
  values.extend(cache.glob('chromium-*/chrome-linux/chrome'))
  values.extend(cache.glob('chromium-*/chrome-win/chrome.exe'))
  values.extend(cache.glob('chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium'))
 local_raw=os.environ.get('LOCALAPPDATA','').strip()
 if local_raw:
  local=Path(local_raw)/'ms-playwright'
  if local.exists():values.extend(local.glob('chromium-*/chrome-win/chrome.exe'))
 result=[];seen=set()
 for path in values:
  try:key=str(path.resolve())
  except Exception:key=str(path)
  if path.is_file() and key not in seen:seen.add(key);result.append(path)
 return result

def verify_chromium_launch(candidates):
 from playwright.sync_api import sync_playwright
 attempts=[]
 with sync_playwright() as playwright:
  options=[str(path) for path in candidates] or [None]
  for executable in options:
   try:
    kwargs={'headless':True}
    if executable:kwargs['executable_path']=executable
    browser=playwright.chromium.launch(**kwargs)
    page=browser.new_page();page.set_content('<title>V20.1 Chromium preflight</title><p>ok</p>')
    ok=page.title()=='V20.1 Chromium preflight'
    browser.close()
    if ok:return executable or 'Playwright-managed Chromium',attempts
   except Exception as exc:attempts.append(f'{executable or "Playwright-managed Chromium"}: {exc}')
 return None,attempts

def verify_woff2_decode():
 from fontTools.ttLib import TTFont
 assets=sorted((Path(__file__).parent/'assets'/'fonts').glob('*.woff2'))
 if not assets:raise RuntimeError('No bundled WOFF2 assets found')
 font=TTFont(str(assets[0]),lazy=False);font.getGlyphOrder();font.close();return assets[0].name

def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--skip-browser',action='store_true',help='development only; release_check never uses this');args=parser.parse_args(argv)
 missing=[]
 for label,(module,purpose) in REQUIREMENTS.items():
  if label=='Playwright' and args.skip_browser:continue
  ok=importlib.util.find_spec(module) is not None;print(f"[{'OK' if ok else 'MISSING'}] {label}: {purpose}")
  if not ok:missing.append(label)
 if 'FontTools' not in missing and 'Brotli' not in missing:
  try:print(f'[OK] WOFF2 decode: {verify_woff2_decode()}')
  except Exception as exc:print(f'[MISSING] WOFF2 decode: {exc}');missing.append('working WOFF2 decode')
 if not args.skip_browser and 'Playwright' not in missing:
  executable,attempts=verify_chromium_launch(chromium_candidates())
  ok=bool(executable)
  print(f"[{'OK' if ok else 'MISSING'}] Chromium launch: {executable or 'required real-browser runtime'}")
  if not ok:
   missing.append('launchable Chromium')
   for attempt in attempts:print('  '+attempt)
 elif args.skip_browser:
  print('[DEV SKIP] Browser launch check disabled by --skip-browser; this is not a release gate.')
 if missing:
  print('\nMissing: '+', '.join(missing));print('Install with: python -m pip install -r requirements-test.txt && python -m playwright install chromium')
  return 1
 print('\nV0.52 dependency preflight passed.');return 0
if __name__=='__main__':raise SystemExit(main())
