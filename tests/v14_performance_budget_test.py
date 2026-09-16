#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build_page_manifests as manifests

def main():
 data=manifests.build()
 for page,entry in data['pages'].items():
  assert len(entry['scripts'])==len(set(entry['scripts'])),('duplicate scripts',page)
  assert len(entry['styles'])==len(set(entry['styles'])),('duplicate styles',page)
 for route,entry in data['routes'].items():
  budget=entry['budgets']
  for page in entry['pages']:
   actual=data['pages'][page]
   assert actual['scriptCount']<=budget['scripts'],(route,page,'scripts',actual['scriptCount'],budget['scripts'])
   assert actual['styleCount']<=budget['styles'],(route,page,'styles',actual['styleCount'],budget['styles'])
   assert actual['bytes']<=budget['bytes'],(route,page,'bytes',actual['bytes'],budget['bytes'])
 expected=json.loads((ROOT/'page-assets-v15.json').read_text(encoding='utf-8'))
 assert expected==data
 print('V16_PERFORMANCE_BUDGET_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
