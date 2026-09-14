#!/usr/bin/env python3
"""Build deterministic V15 page bundles while retaining original source modules."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCES=ROOT/'route-bundle-sources-v15.json'
MANIFEST=ROOT/'route-bundles-v15.json'

def read(path:str)->str:
    p=ROOT/path
    if not p.is_file(): raise FileNotFoundError(f'Missing route bundle source: {path}')
    return p.read_text(encoding='utf-8')

def js_bundle(paths:list[str])->str:
    chunks=[]
    for path in paths:
        chunks.append(f';{read(path).rstrip()}')
    return ''.join(chunks)

def css_bundle(paths:list[str])->str:
    chunks=[]
    for path in paths:
        source=read(path)
        # This legacy marker is part of the authenticated-page zoom contract.
        # Preserve it while stripping non-contract comments from production CSS.
        markers=''.join(re.findall(r'/\*[^*]*compact authenticated-page zoom support[^*]*\*/',source,flags=re.I))
        chunks.append(markers+re.sub(r'/\*.*?\*/','',source,flags=re.S).rstrip())
    return ''.join(chunks)

def encoded(text:str)->bytes:
    # Generated artifacts use explicit UTF-8/LF bytes on every platform. The
    # bytes hashed below are exactly the bytes atomically written to disk.
    return text.replace('\r\n','\n').replace('\r','\n').encode('utf-8')

def digest(text:str)->str:return hashlib.sha256(encoded(text)).hexdigest()
def atomic_write(path:Path,text:str):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_bytes(encoded(text))
    temporary.replace(path)

def build(write:bool)->dict:
    spec=json.loads(SOURCES.read_text(encoding='utf-8')); result={'version':15,'pages':{}}
    for page,entry in sorted(spec['pages'].items()):
        stem=Path(page).stem; js_name=f'bundle-{stem}-v15.js'; css_name=f'bundle-{stem}-v15.css'
        js=js_bundle(entry['scripts']);css=css_bundle(entry['styles'])
        if write:
            atomic_write(ROOT/js_name,js);atomic_write(ROOT/css_name,css)
        result['pages'][page]={'javascript':js_name,'stylesheet':css_name,'sources':entry,'scriptBytes':len(encoded(js)),'styleBytes':len(encoded(css)),'scriptSha256':digest(js),'styleSha256':digest(css)}
    return result

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args(argv)
    expected=build(write=not args.check); text=json.dumps(expected,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
    if args.check:
        if not MANIFEST.is_file() or MANIFEST.read_text(encoding='utf-8')!=text:
            print('ROUTE_BUNDLE_MANIFEST_OUT_OF_DATE');return 1
        for page,item in expected['pages'].items():
            for key,hash_key in [('javascript','scriptSha256'),('stylesheet','styleSha256')]:
                p=ROOT/item[key]
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item[hash_key]:
                    print(f'ROUTE_BUNDLE_OUT_OF_DATE {page} {item[key]}');return 1
        print('ROUTE_BUNDLE_CHECK_PASSED');return 0
    atomic_write(MANIFEST,text);print(f'WROTE {len(expected["pages"])} route bundles');return 0
if __name__=='__main__':raise SystemExit(main())
