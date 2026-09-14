#!/usr/bin/env python3
"""Generate deterministic V15 page asset manifests and enforce route budgets."""
from __future__ import annotations
import argparse,json
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'page-assets-v15.json'
ROUTES={
 'dashboard':['dashboard.html'],
 'editor':['index.html'],
 'public-guest':['public.html'],
 'account-admin':['account.html','admin.html','billing.html','verify.html','reset.html','privacy.html'],
 'event-operations':['guests.html','responses.html','analytics.html','materials.html','checkin.html','templates.html','designer.html'],
}
BUDGETS={
 'dashboard':{'scripts':3,'styles':1,'bytes':460_000},
 'editor':{'scripts':3,'styles':1,'bytes':1_420_000},
 'public-guest':{'scripts':1,'styles':1,'bytes':260_000},
 'account-admin':{'scripts':3,'styles':1,'bytes':470_000},
 'event-operations':{'scripts':3,'styles':1,'bytes':530_000},
}
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.scripts=[];self.styles=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='script' and a.get('src'):self.scripts.append(a['src'])
  if tag=='link' and a.get('href') and 'stylesheet' in str(a.get('rel','')).lower():self.styles.append(a['href'])
def clean(value):return value.split('?',1)[0].split('#',1)[0].lstrip('/')
def size(value):
 p=ROOT/clean(value)
 return p.stat().st_size if p.is_file() else 0
def page_entry(name):
 p=Parser();p.feed((ROOT/name).read_text(encoding='utf-8'))
 scripts=list(dict.fromkeys(p.scripts));styles=list(dict.fromkeys(p.styles))
 return {'scripts':scripts,'styles':styles,'scriptCount':len(scripts),'styleCount':len(styles),'bytes':sum(size(x) for x in scripts+styles)}
def atomic_write(path:Path,text:str):
 temporary=path.with_name(path.name+'.tmp');temporary.write_text(text,encoding='utf-8');temporary.replace(path)
def build():
 pages={name:page_entry(name) for names in ROUTES.values() for name in names}
 routes={}
 for route,names in ROUTES.items():
  scripts=list(dict.fromkeys(x for name in names for x in pages[name]['scripts']))
  styles=list(dict.fromkeys(x for name in names for x in pages[name]['styles']))
  routes[route]={'pages':names,'scripts':scripts,'styles':styles,'budgets':BUDGETS[route]}
 return {'version':15,'pages':pages,'routes':routes}
def main(argv=None):
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args(argv)
 text=json.dumps(build(),ensure_ascii=False,indent=2,sort_keys=True)+'\n'
 if args.check:
  if not OUTPUT.is_file() or OUTPUT.read_text(encoding='utf-8')!=text:
   print('PAGE_ASSET_MANIFEST_OUT_OF_DATE');return 1
  print('PAGE_ASSET_MANIFEST_CHECK_PASSED');return 0
 atomic_write(OUTPUT,text);print(f'WROTE {OUTPUT.name}');return 0
if __name__=='__main__':raise SystemExit(main())
