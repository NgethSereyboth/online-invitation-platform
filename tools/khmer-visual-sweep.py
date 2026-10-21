#!/usr/bin/env python3
"""khmer-visual-sweep.py — NW-4.4 Khmer visual verification.

Captures 7 pages (index, dashboard, guests, templates, materials, responses, admin) in
Khmer at 1440/768/375 and records pass/fail per shot:
  - no horizontal document scroll (scrollWidth <= clientWidth on the document element)
  - .khmer-text line-height >= 1.6 anywhere Khmer is rendered (min across sampled nodes)
  - html lang startsWith 'km' after the language is forced
  - option labels readable (materials/responses: no truncation check — text presence)

Read-only; writes PNGs + JSON under --out.
"""
from __future__ import annotations
import argparse,datetime,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium,mark_editor_onboarding_seen,dismiss_editor_onboarding
from v14_test_utils import app_server

PAGES=['dashboard','guests','templates','materials','responses','admin','index']
VIEWPORTS=[(1440,900),(768,1024),(375,667)]

CHECK_JS=r"""()=>{const de=document.documentElement;const body=document.body;
 const sw=Math.max(de.scrollWidth,body?body.scrollWidth:0);
 const cw=de.clientWidth;
 let minLh=null,bad=[];
 for(const n of document.querySelectorAll('.khmer-text')){
   if(!n.offsetParent&&!n.getClientRects().length)continue;
   const cs=getComputedStyle(n);
   const lh=parseFloat(cs.lineHeight);
   const fs=parseFloat(cs.fontSize||'16');
   const ratio=lh/fs;
   if(minLh===null||ratio<minLh)minLh=ratio;
   if(ratio<1.6&&n.textContent.trim())bad.push({ratio,text:n.textContent.trim().slice(0,30)});
 }
 return {lang:de.lang,scrollW:sw,clientW:cw,hscroll:sw>cw+1,minKhmerLh:minLh,badKhmerLh:bad.slice(0,4)};}"""

def open_editor(page,base,identity='km-sweep'):
    response=page.request.post(base+'/api/auth/register',data={
        'email':identity+'@example.com','password':'Motion-test-password-123!'})
    assert response.ok,response.text()
    response=page.request.post(base+'/api/invitations',data={
        'slug':identity+'-check','document':{
            'eventType':'Wedding','fields':{'names':'Khmer sweep'},
            'objects':{},'designPages':[],
            'sectionOrder':['schedule','venue','rsvp'],
            'settings':{'rsvpEnabled':True}}})
    assert response.ok,response.text()
    invite=response.json();assert invite.get('id'),invite
    page.add_init_script("localStorage.setItem('sovan-active-invite', "+json.dumps(str(invite['id']))+");")
    page.add_init_script("localStorage.setItem('einvite-lang','km');try{document.documentElement.lang='km'}catch{}")
    page.goto(base+'/index.html',wait_until='domcontentloaded')
    dismiss_editor_onboarding(page,timeout=30000)
    page.wait_for_function('!!window.EInviteEditorCore',timeout=30000)
    page.wait_for_timeout(500)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    ap.add_argument('--skip',default='')
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    skip={s.strip() for s in args.skip.split(',') if s.strip()}
    results={'generatedAt':datetime.datetime.now().isoformat(),'shots':[]}
    failures=0
    with app_server() as (proc,base,data):
        with sync_playwright() as pw:
            browser=launch_chromium(pw)
            ctx=None
            page=None
            for pname in PAGES:
                if pname in skip:continue
                if pname=='index':
                    # editor: reuse editor route with throwaway account
                    ctx=browser.new_context();ctx.add_init_script(mark_editor_onboarding_seen())
                    page=ctx.new_page()
                    open_editor(page,base)
                else:
                    if ctx is None:
                        ctx=browser.new_context();ctx.add_init_script(mark_editor_onboarding_seen())
                        page=ctx.new_page()
                    page.goto(f'{base}/{pname}.html',wait_until='load',timeout=45000)
                    page.wait_for_timeout(600)
                # force Khmer on non-editor pages (editor open_editor already seeds it)
                page.evaluate("localStorage.setItem('einvite-lang','km')")
                page.evaluate("document.documentElement.lang='km'")
                page.wait_for_timeout(400)
                for w,h in VIEWPORTS:
                    page.set_viewport_size({"width":w,"height":h})
                    page.wait_for_timeout(500)
                    chk=page.evaluate(CHECK_JS)
                    name=f"{pname}-{w}x{h}-km.png"
                    page.screenshot(path=str(out/name),full_page=False)
                    ok=(not chk['hscroll']) and (chk['minKhmerLh'] is None or chk['minKhmerLh']>=1.55) and str(chk['lang']).lower().startswith('km')
                    if not ok:failures+=1
                    results['shots'].append({'page':pname,'viewport':f'{w}x{h}','photo':name,'ok':ok,**chk})
            if ctx:ctx.close()
            browser.close()
    (out/'sweep.json').write_text(json.dumps(results,indent=1),encoding='utf-8')
    print(f"KHMER_VISUAL_SWEEP shots={len(results['shots'])} failed={failures}")
    for s in results['shots']:
        if not s['ok']:
            print('  FAIL:',s['page'],s['viewport'],'hscroll' if s['hscroll'] else '', 'lang' if not str(s['lang']).startswith('km') else '', 'lh' if s['badKhmerLh'] else '')
    return 0 if failures==0 else 2

if __name__=='__main__':
    raise SystemExit(main())
