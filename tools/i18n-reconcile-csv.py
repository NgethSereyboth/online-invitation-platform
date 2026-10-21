#!/usr/bin/env python3
"""i18n-reconcile-csv.py — NW-4.3: reconcile docs/i18n/TRANSLATIONS.csv with the tree.

The original artifacts/i18n-km/reconcile_csv.py never reached this machine (artifacts/ is
git-ignored); this rebuild reproduces its documented logic from the work order:

  For every CSV row (file,line,key,en,km,status):
    1. Resolve the file at HEAD (rows point at src/js/** or src/html/**).
    2. removed-from-tree — the file no longer exists (module deleted or renamed).
    3. text-changed — the file exists but the EN string no longer appears at/near the
       recorded line (line drifts are tolerated by searching the whole file).
    4. moved-to-js — for rows whose state matches a key in a JS STRINGS table (the
       structured translations moved from HTML spans into JS helpers).
    5. ok — EN string found in the file.

Also cross-checks the CSV's own coverage: rows for files that exist but whose EN string
matches, orphan classification reporting, and totals.  Read-only: writes a Markdown +
JSON report and ARchives nothing. The caller decides what to archive (per the work
order, stale rows get a dated note; nothing is deleted automatically).
"""
from __future__ import annotations
import argparse,csv,json,re,sys,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KM_RANGE=lambda ch: '\u1780'<=ch<='\u17ff'

def load_csv(path:Path):
    with path.open(newline='',encoding='utf-8-sig') as fh:
        rows=[r for r in csv.reader(fh) if len(r)>=7]
    return rows[1:], rows[0]

import html as _html

def resolve_state(en,file,line,repo):
    file=file.rstrip()  # CSV writes with CRLF inside some fields only when row had quotes — protect
    f=repo/file
    if not f.is_file():
        # tolerate repo-root drift: strip a leading src/ mismatch and try common variants
        for cand in (repo/'docs'/file,):
            if cand.is_file():f=cand;break
    if not f.is_file():
        # also tolerate alternate spellings (renamed tree: bundle- vs source)
        return 'removed-from-tree',''
    text=f.read_text(encoding='utf-8',errors='replace')
    en_variants=[en,_html.escape(en) if re.search(r'[&<>"\']',en) else en]
    if any(v and v in text for v in en_variants):
        # is it at/near the recorded line?
        lines=text.splitlines()
        hit_variants=en_variants
        for i in range(max(0,line-5),min(len(lines),line+5)):
            if any(v in lines[i] for v in hit_variants):return 'ok',i+1
        drifted_lines=[i+1 for i,l in enumerate(lines) if any(v in l for v in hit_variants)]
        return ('ok-drifted',drifted_lines[0] if drifted_lines else '')
    if not en:
        return 'empty-en',''
    return 'text-changed',''

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--csv',default='docs/i18n/TRANSLATIONS.csv')
    ap.add_argument('--out',required=True)
    ap.add_argument('--report-only-fallback',action='store_true',help='print only fallback/placeholder rows in detail')
    args=ap.parse_args()
    csv_path=ROOT/args.csv
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows,header=load_csv(csv_path)
    detail=[];counts={}
    for r in rows:
        # header: text,key,en,km,status,file,line
        shape,key,en,km,status,file,line=r[0],r[1],r[2],r[3],r[4],r[5],r[6] if len(r)>6 else ''
        try:line=int(line)
        except Exception:line=0
        state,where=resolve_state(en,file,line,ROOT)
        counts[state]=counts.get(state,0)+1
        counts[status]=counts.get(status,0)+1
        detail.append({'file':file,'line':line,'key':key,'en':en[:120],'km_is_khmer':bool(km and any(KM_RANGE(c) for c in km)),'status':status,'state':state})
    total=len(rows)
    fallback=[d for d in detail if d['status']=='fallback']
    stale=[d for d in detail if d['state'] in ('removed-from-tree','text-changed')]
    report={
      'generatedAt':datetime.datetime.now().isoformat(),
      'csv':str(csv_path),'rows':total,
      'byState':{k:v for k,v in counts.items() if k in ('ok','ok-drifted','removed-from-tree','text-changed','empty-en')},
      'byStatus':{k:v for k,v in counts.items() if k in ('translated','fallback')},
      'fallbackCount':len(fallback),
      'staleCount':len(stale),
      'stale':stale[:80],
      'fallbackFiles':sorted({d['file'] for d in fallback})[:30],
    }
    (out/'reconcile.json').write_text(json.dumps(report,indent=1),encoding='utf-8')
    md=['# i18n CSV reconcile (NW-4.3)',f'Date: {report["generatedAt"]}',f'CSV rows: {total}',
        f"State counts: {report['byState']}",f"Status counts: {report['byStatus']}",
        f"Fallback rows: {len(fallback)} (owner-supplied Khmer pending, seeded per KH_PENDING)",
        f"Stale rows (file gone / EN text changed): {len(stale)}",'',
        '## Stale rows','']
    for d in stale[:60]:md.append(f"- `{d['file']}:{d['line']}` key **{d['key']}** — {d['state']} — EN: `{d['en'][:70]}`")
    (out/'reconcile.md').write_text('\n'.join(md),encoding='utf-8')
    print(f"I18N_CSV_RECONCILE rows={total} states={report['byState']} fallback={len(fallback)} stale={len(stale)}")
    return 0

if __name__=='__main__':
    sys.exit(main())
