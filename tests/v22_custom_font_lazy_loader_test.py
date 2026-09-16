#!/usr/bin/env python3
from __future__ import annotations
import base64
from pathlib import Path
from browser_runtime import launch_chromium, skipped
ROOT=Path(__file__).resolve().parents[1]

def source(name:str)->str:return (ROOT/name).read_text(encoding='utf-8')
def sample_ttf()->Path:
    for p in (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('/usr/share/fonts/truetype/lato/Lato-Medium.ttf'),Path('C:/Windows/Fonts/arial.ttf')):
        if p.is_file():return p
    raise RuntimeError('No TTF test font available')

def main()->int:
    try:from playwright.sync_api import sync_playwright
    except Exception as exc:return skipped('V22_CUSTOM_FONT_LAZY_LOADER',exc)
    woff=base64.b64encode((ROOT/'assets/fonts/noto-sans-latin-400.woff2').read_bytes()).decode('ascii')
    with sync_playwright() as p:
        try:browser=launch_chromium(p)
        except Exception as exc:return skipped('V22_CUSTOM_FONT_LAZY_LOADER',exc)
        try:
            page=browser.new_page(viewport={'width':1100,'height':760});page.set_default_timeout(40_000);errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            assets={'custom-fonts-v22.js':source('custom-fonts-v22.js'),'font-browser.js':source('font-browser.js')}
            def js_handler(body):
                def handle(route):route.fulfill(status=200,content_type='application/javascript',body=body)
                return handle
            def css_handler(route):route.fulfill(status=200,content_type='text/css',body='')
            for name,body in assets.items():page.route(f'http://einvite.test/{name}',js_handler(body))
            for name in ('font-browser.css','custom-fonts-v22.css'):page.route(f'http://einvite.test/{name}',css_handler)
            html=f"""<!doctype html><meta charset='utf-8'><label>Font<select id='font'></select></label><div id='stage'></div>
<script>window.__doc={{customFonts:{{}}}};window.EInviteEditorBridge={{getState:()=>__doc,transact:(label,fn)=>fn(__doc)}};window.EInviteEditorState={{applyTextProperty:(k,v)=>window.__applied=[k,v]}};window.EInviteContext={{getInvitationId:()=>\"invite-test\"}};window.uiConfirm=async()=>true;window.__fontBytes=Uint8Array.from(atob(\"{woff}\"),c=>c.charCodeAt(0));window.__fontUrl=URL.createObjectURL(new Blob([__fontBytes],{{type:\"font/woff2\"}}));window.EInviteUpload={{uploadFont:async(id,file,options)=>{{options.onProgress?.({{phase:\"uploading\",percent:100}});return{{id:\"asset-font\",url:__fontUrl,sha256:\"abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890\",family:\"DejaVu Sans Uploaded\",weight:400,style:\"normal\",scripts:[\"Latin\"],sourceFormat:\"ttf\",originalBytes:file.size,optimizedBytes:50000,savingsPercent:65,glyphCount:1000,size:50000}}}}}};</script>
<script>{source('typography-contract.js')}</script><script>{source('custom-font-core-v22.js')}</script><script>{source('font-browser-loader-v22.js')}</script>"""
            html=html.replace("<meta charset='utf-8'>","<base href='http://einvite.test/'><meta charset='utf-8'>")
            page.set_content(html,wait_until='load')
            assert page.locator('.ei-font-launch').count()==1
            page.locator('.ei-font-launch').click(timeout=10_000)
            page.locator('dialog.ei-font-dialog[open]').wait_for(timeout=10_000)
            accept=page.locator('.ei-font-upload input').get_attribute('accept') or ''
            assert '.ttf' in accept and '.tff' in accept and '.otf' in accept and '.woff2' in accept,accept
            page.locator('.ei-font-license input').check()
            page.locator('.ei-font-upload input').set_input_files(str(sample_ttf()),timeout=10_000)
            page.wait_for_function("document.querySelector('.ei-font-upload-status')?.dataset.tone==='success'",timeout=20_000)
            result=page.evaluate("""()=>({fonts:Object.keys(__doc.customFonts||{}),status:document.querySelector('.ei-font-upload-status').textContent,applied:window.__applied,dialogs:document.querySelectorAll('dialog.ei-font-dialog').length,full:EInviteCustomFonts.version})""")
            assert len(result['fonts'])==1,result
            assert 'WOFF2' in result['status'] and 'smaller' in result['status'],result
            assert result['applied'] and result['applied'][0]=='font',result
            assert result['dialogs']==1 and result['full']=='22.0.3',result
            assert not errors,errors
        finally:browser.close()
    print('V22_CUSTOM_FONT_LAZY_LOADER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
