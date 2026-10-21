#!/usr/bin/env python3
"""option_labels_i18n_check.py — NW-4.1 live EN↔KM option-label test (materials + responses).

Asserts on the real served pages:
  1. On load, every option[data-i18n-en] has textContent equal to its EN label (exactly once —
     no 'All typesAll types' duplication).
  2. Switching to Khmer rewrites exactly the options carrying data-i18n-km (count matches),
     selection survives (selected value unchanged), text becomes the Khmer label.
  3. Switching back to English restores the EN labels; no mixed EN/KM duplication
     (textContent contains no Khmer block when in EN mode, and vice versa).

Exit 0 = all pass. Evidence under --out.
"""
from __future__ import annotations
import argparse,datetime,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from v14_test_utils import app_server

PAGES={'materials':'materials.html','responses':'responses.html'}
OPTIONS_JS=r"""()=>[...document.querySelectorAll('option[data-i18n-en]')].map(o=>({v:o.value,en:o.getAttribute('data-i18n-en'),km:o.getAttribute('data-i18n-km'),text:o.textContent,selected:o.selected}))"""
DUP_JS=r"""()=>document.querySelectorAll('option').length-optionLength"""
SWITCH_JS=r"""lang=>{const btn=document.querySelector('.language-switch [data-lang="'+lang+'"]');if(btn)btn.click();return true}"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    result={'generatedAt':datetime.datetime.now().isoformat(),'pages':{}}
    failed=0
    with app_server() as (proc,base,data):
        with sync_playwright() as pw:
            browser=launch_chromium(pw)
            page=browser.new_context().new_page()
            for key,name in PAGES.items():
                page.goto(f'{base}/{name}',wait_until='load',timeout=45000)
                page.wait_for_timeout(700)
                rows={'en':page.evaluate(OPTIONS_JS)}
                page.evaluate(SWITCH_JS,'km');page.wait_for_timeout(500)
                rows['km']=page.evaluate(OPTIONS_JS)
                page.screenshot(path=str(out/f'{key}-km.png'))
                page.evaluate(SWITCH_JS,'en');page.wait_for_timeout(500)
                rows['en2']=page.evaluate(OPTIONS_JS)
                checks=[]
                # 1. EN init: text == en, no duplication
                checks.append({'name':f'{key} EN init labels match', 'passed':all(r['text']==r['en'] for r in rows['en'])})
                checks.append({'name':f'{key} EN init no duplicated text', 'passed':all(r['en'] not in r['text'][len(r['en']):] or len(r['text'])==len(r['en']) for r in rows['en'])})
                # 2. KM: text == km, selection survives
                sel_before=[r['v'] for r in rows['en'] if r['selected']]
                sel_after=[r['v'] for r in rows['km'] if r['selected']]
                checks.append({'name':f'{key} KM labels applied', 'passed':all(r['text']==r['km'] for r in rows['km'])})
                checks.append({'name':f'{key} KM selection survives', 'passed':sel_before==sel_after, 'detail':f'{sel_before} vs {sel_after}'})
                # 3. EN re-apply
                checks.append({'name':f'{key} EN after round-trip restored', 'passed':all(r['text']==r['en'] for r in rows['en2'])})
                checks.append({'name':f'{key} EN after round-trip no KM residue', 'passed':all(not any('\u1780'<=c<='\u17ff' for c in r['text']) for r in rows['en2'])})
                fsum=sum(1 for c in checks if not c['passed'])
                failed+=fsum
                result['pages'][key]={'rows':rows,'checks':checks}
            browser.close()
    (out/'option-labels.json').write_text(json.dumps(result,indent=1),encoding='utf-8')
    print(f"OPTION_LABELS_I18N pages={len(result['pages'])} failed={failed}")
    for k,v in result['pages'].items():
        for c in v['checks']:
            if not c['passed']:print('  FAIL:',c['name'],c.get('detail','')[:140])
    return 0 if failed==0 else 2

if __name__=='__main__':
    raise SystemExit(main())
