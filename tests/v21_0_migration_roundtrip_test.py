#!/usr/bin/env python3
from __future__ import annotations
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rich_text_document_model import migrate_legacy,normalize_rich_text,export_plain_text,export_legacy_html

def main():
 source='<div><b>Invitation</b> <span style="font-style:italic;text-decoration:underline">details</span></div><ol><li>First</li><li>ទីមួយ</li></ol>'
 a=migrate_legacy('details',{'type':'text','textStyleId':'body','html':source},style_ids={'body'},default_style_id='body')
 b=migrate_legacy('details',{'type':'text','textStyleId':'body','html':source},style_ids={'body'},default_style_id='body')
 assert a==b
 ids=[p['id'] for p in a['paragraphs']]+[r['id'] for p in a['paragraphs'] for r in p['runs']]
 assert len(ids)==len(set(ids)) and all(len(x)<=64 for x in ids)
 serialized=json.dumps(a,ensure_ascii=False,sort_keys=True,separators=(',',':'))
 restored=normalize_rich_text(json.loads(serialized),strict=True,seed='details',style_ids={'body'},default_style_id='body')
 assert restored==a
 assert export_plain_text(restored).splitlines()==['Invitation details','First','ទីមួយ']
 html=export_legacy_html(restored);assert '<strong>Invitation</strong>' in html and '<u><em>details</em></u>' in html and '<ol>' in html
 assert normalize_rich_text(copy.deepcopy(restored),strict=True,seed='details',style_ids={'body'},default_style_id='body')==restored
 js=(ROOT/'rich-text-document-model.js').read_text(encoding='utf-8');py=(ROOT/'rich_text_document_model.py').read_text(encoding='utf-8')
 assert 'authoritative' not in serialized.lower() and 'innerHTML' not in serialized and 'font-family' not in serialized
 assert 'exportPlainText' in js and 'exportLegacyHtml' in js and 'normalize_document_rich_text' in py
 print('V21_0_MIGRATION_ROUNDTRIP_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
