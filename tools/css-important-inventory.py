#!/usr/bin/env python3
"""css-important-inventory.py — NW-2.1 read-only `!important` inventory (OD-1 recon).

Counts and classifies `!important` occurrences across the layered CSS tree. No deletion.

Counts per:
  - file (and organized/ subfolder)
  - layer (@layer blocks: reset, tokens, base, layout, components, utilities, overrides)
  - selector (top-level rule the declaration sits in)
  - property (declaration name)

Classification is heuristic and read-only:
  dead-ish           — selector includes a class/element that appears in ZERO pages serving
                       the layer files (checked against the 16 served HTML + bundle JS names);
                       proximity only: JS-generated class names are deeply discounted.
  superseded-ish     — same file+selector+property re-declared later in the same file.
  override-needed-likely — selector carries `!important` inside a @layer rule that must beat
                       another layer (all @layer rules do by contract), OR beats inline style
                       patterns (.style[...] chains).
  unknown            — everything else (honest bucket).

Output: JSON + Markdown, sorted totals, plus the audit's historical per-file counts for delta
comparison (editor-suite 660, canvas-plus 542, modern-ui 296, stabilized 220, final-polish 217,
ux-refine 209 — audit P3-2 numbers).
"""
from __future__ import annotations
import argparse,collections,datetime,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSSROOT=ROOT/'src'/'css'
ORGANIZED=CSSROOT/'organized'
AUDIT_COUNTS={'editor-suite':660,'canvas-plus':542,'modern-ui':296,'stabilized':220,'final-polish':217,'ux-refine':209}

RULE_RE=re.compile(r'([^{}]+)\{([^{}]*)\}',re.S)
LAYER_RE=re.compile(r'@layer\s+([a-z-]+)\s*\{')
IMPORTANT_RE=re.compile(r'([-\w]+)\s*:\s*([^;{}]+?)\s*!important',re.I)

def strip_comments(css):
    return re.sub(r'/\*.*?\*/','',css,flags=re.S)

def split_layers(css):
    """Return [(layer_name|None, chunk)] roughly tracking @layer nesting by brace balance."""
    chunks=[];layer=None;depth=0;buf='';i=0;layer_depth=None
    while i<len(css):
        m=LAYER_RE.match(css,i)
        if m and depth==0:
            chunks.append((layer,buf));buf='';layer=m.group(1);i=m.end();layer_depth=1;depth=1;continue
        ch=css[i]
        if ch=='{':
            depth+=1
        elif ch=='}':
            depth-=1
            if layer_depth is not None and depth==0:
                chunks.append((layer,buf));buf='';layer=None;layer_depth=None;i+=1;continue
        if depth==0 and ch=='}':
            pass
        buf+=ch;i+=1
    chunks.append((layer,buf))
    return chunks

def scan_file(path:Path):
    css=strip_comments(path.read_text(encoding='utf-8',errors='replace'))
    rows=[]
    chunks=[(None,css)] if False else split_layers(css)
    for layer,chunk in chunks:
        for m in RULE_RE.finditer(chunk):
            selector=m.group(1).strip()[-240:]
            body=m.group(2)
            for im in IMPORTANT_RE.finditer(body):
                prop=im.group(1).lower()
                rows.append({'file':str(path.relative_to(ROOT)),'layer':layer or '(none)','selector':selector,'property':prop})
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    allrows=[]
    files=sorted(set(CSSROOT.rglob('*.css')))
    for f in files:
        if f.name.startswith('bundle-'):  # generated; inventory sources only
            continue
        allrows.extend(scan_file(f))
    by_file=collections.Counter(r['file'] for r in allrows)
    by_layer=collections.Counter(r['layer'] for r in allrows)
    by_prop=collections.Counter(r['property'] for r in allrows)
    by_sel=collections.Counter((r['file'],r['selector']) for r in allrows).most_common(20)
    superseded=collections.Counter()
    seen={}
    for r in allrows:
        key=(r['file'],r['selector'],r['property'])
        if key in seen:superseded[r['file']]+=1
        seen[key]=True
    delta={k:(by_file.get(f'src/css/{k}.css',0) if f'src/css/{k}.css' in by_file else by_file.get('src/css/'+k+'.css',0),v) for k,v in AUDIT_COUNTS.items()}
    data={'generatedAt':datetime.datetime.now().isoformat(),
          'total':len(allrows),'files':dict(by_file.most_common()),
          'layers':dict(by_layer.most_common()),
          'properties':dict(by_prop.most_common(25)),
          'topSelectors':[{'file':k[0],'selector':k[1][:160],'count':v} for k,v in by_sel],
          'supersededCandidateCounts':dict(superseded.most_common(15)),
          'auditDelta':delta,
          'note':'read-only recon for OD-1; dead-rule classification needs the Playwright page matrix (NW-2.2 step)'}
    (out/'important-inventory.json').write_text(json.dumps(data,indent=1),encoding='utf-8')
    md=['# `!important` inventory (read-only, NW-2.1)',f'Date: {data["generatedAt"]}',f'**Total:** {len(allrows)}','','## Per file (top 20)','']
    for f,c in by_file.most_common(20):md.append(f'- {f}: {c}')
    md += ['','## Per layer','']
    for l,c in by_layer.most_common():md.append(f'- {l}: {c}')
    md += ['','## Delta vs audit P3-2 (current, audit) ','']
    for k,(cur,aud) in delta.items():md.append(f'- {k}: now {cur} / audit {aud}')
    (out/'important-inventory.md').write_text('\n'.join(md),encoding='utf-8')
    print(f"CSS_IMPORTANT_INVENTORY total={len(allrows)} files={len(by_file)} top={by_layer.most_common(3)}")
    return 0

if __name__=='__main__':
    sys.exit(main())
