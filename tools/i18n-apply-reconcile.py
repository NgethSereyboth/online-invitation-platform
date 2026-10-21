#!/usr/bin/env python3
"""i18n-apply-reconcile.py — archive NW-4.3 stale TRANSLATIONS.csv rows with a dated status.

Reads artifacts/next-work/nw-4-3/reconcile.json and rewrites docs/i18n/TRANSLATIONS.csv
in place (all fields quoted, CRLF preserved). Stale rows KEEP their data but their
status column becomes:

    stale-removed-2026-10-21     (removed-from-tree at HEAD)
    stale-text-changed-2026-10-21 (EN string no longer in the file; may have moved to JS)
    stale-moved-to-js-2026-10-21  (EN string verified to now live in a src/js module)

No row is deleted; no stale row remains counted as 'translated'. Fresh rows inside the
same run (not stale) keep their existing status. Idempotent: re-running skips rows
whose status already starts with 'stale-'.
"""
from __future__ import annotations
import csv,json,sys,datetime,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSV=ROOT/'docs/i18n/TRANSLATIONS.csv'
RECON=ROOT/'artifacts/next-work/nw-4-3/reconcile.json'
DATE='2026-10-21'

def main():
    recon=json.loads(RECON.read_text(encoding='utf-8'))
    stale={}
    for s in recon.get('stale',[]):
        stale[(s['file'],s['key'])]=s['state']
    rows=[]
    with CSV.open(newline='',encoding='utf-8-sig') as fh:
        rows=list(csv.reader(fh))
    header,rows=rows[0],rows[1:]
    fi=header.index('file');ki=header.index('key');si=header.index('status')
    changed=0
    moved_to_js=0
    for r in rows:
        if len(r)<7:continue
        cur=r[si].strip()
        if cur.startswith('stale-'):continue
        key_states=stale.get((r[fi],r[ki]))
        if key_states=='removed-from-tree':
            r[si]=f'stale-removed-{DATE}';changed+=1
        elif key_states=='text-changed':
            # moved-to-js check: EN string present in some src/js module (excluding bundles)
            en=r[header.index('en')]
            hit=None
            if en:
                for js in (ROOT/'src/js').rglob('*.js'):
                    if js.name.startswith('bundle-'):continue
                    try:text=js.read_text(encoding='utf-8',errors='replace')
                    except OSError:continue
                    if en in text:hit=js.relative_to(ROOT).as_posix();break
                if hit:
                    r[si]=f'stale-moved-to-js-{DATE} -> {hit}';moved_to_js+=1;changed+=1;continue
            r[si]=f'stale-text-changed-{DATE}';changed+=1
    CSV.write_text('',encoding='utf-8')
    with CSV.open('w',newline='',encoding='utf-8') as fh:
        w=csv.writer(fh,lineterminator='\r\n',quoting=csv.QUOTE_ALL)
        w.writerow(header);w.writerows(rows)
    summary={'rows':len(rows),'reclassified':changed,
             'movedToJsIdentified':moved_to_js,
             'note':f'stale rows archived with dated status on {DATE}; none deleted'}
    (RECON.parent/'apply-result.json').write_text(json.dumps(summary,indent=1),encoding='utf-8')
    print('I18N_CSV_APPLY',json.dumps(summary))
    return 0

if __name__=='__main__':
    sys.exit(main())
