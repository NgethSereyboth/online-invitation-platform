#!/usr/bin/env python3
from __future__ import annotations
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rich_text_document_model import normalize_rich_text,migrate_legacy,export_plain_text,export_legacy_html,normalize_document_rich_text
from rich_text_contract import MAX_PARAGRAPHS,MAX_RUNS,MAX_TAB_STOPS,MAX_LIST_DEPTH,MAX_LEGACY_NESTING

def reject(fn):
 try:fn()
 except (TypeError,ValueError):return
 raise AssertionError('hostile rich-text input was accepted')

def main():
 contract=json.loads((ROOT/'rich-text-contract.json').read_text(encoding='utf-8'))
 assert contract['version']==1 and contract['maxParagraphs']==MAX_PARAGRAPHS and contract['maxRuns']==MAX_RUNS
 assert contract['maxTabStops']==MAX_TAB_STOPS and contract['maxListDepth']==MAX_LIST_DEPTH
 legacy={'type':'text','textStyleId':'body','html':'<strong>Hello</strong><br><em>សួស្តី</em><ul><li><a href="https://example.com/invite">Guest</a></li></ul>'}
 first=migrate_legacy('welcome',legacy,style_ids={'body','display'},default_style_id='body')
 second=normalize_rich_text(copy.deepcopy(first),strict=True,seed='welcome',style_ids={'body','display'},default_style_id='body')
 assert first==second
 assert len(first['paragraphs'])>=2
 assert first['paragraphs'][0]['runs'][0]['marks']=={'strong':True}
 assert any(run['locale']=='km' for p in first['paragraphs'] for run in p['runs'])
 assert any(p['list']['type']=='bullet' for p in first['paragraphs'])
 assert len(first['entities'])==1 and next(iter(first['entities'].values()))['url']=='https://example.com/invite'
 plain=export_plain_text(first);html=export_legacy_html(first)
 assert 'Hello' in plain and 'សួស្តី' in plain and '<strong>Hello</strong>' in html and '<ul>' in html and '<a href="https://example.com/invite">Guest</a>' in html
 modern={'typography':{'version':1,'defaultStyleId':'body','styles':{'body':{'id':'body'}},'styleOrder':['body']},'objects':{'welcome':{**legacy,'richTextModelVersion':1,'richText':first,'html':html}},'designPages':[],'richTextModelVersion':1}
 stable=normalize_document_rich_text(copy.deepcopy(modern),strict=True)
 assert stable==modern
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[],'entities':{},'html':'bad'},strict=True))
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':'p-good','paragraphStyleId':'body','runs':[{'id':'r-good','text':'ok','marks':{'onclick':True}}]}],'entities':{}},strict=True,style_ids={'body'}))
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':'p-good','paragraphStyleId':'body','runs':[{'id':'r-good','text':'bad\u0001','marks':{}}]}],'entities':{}},strict=True,style_ids={'body'}))
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':'p-good','paragraphStyleId':'body','runs':[{'id':'r-good','text':'x','marks':{},'entityId':'link-x'}]}],'entities':{'link-x':{'id':'link-x','type':'link','url':'javascript:alert(1)'}}},strict=True,style_ids={'body'}))
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':'p-good','paragraphStyleId':'missing','runs':[{'id':'r-good','text':'x','marks':{}}]}],'entities':{}},strict=True,style_ids={'body'}))
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':'p-good','paragraphStyleId':'body','tabStops':[{'position':i,'align':'left','leader':'none'} for i in range(MAX_TAB_STOPS+1)],'runs':[{'id':'r-good','text':'x','marks':{}}]}],'entities':{}},strict=True,style_ids={'body'}))
 reject(lambda:normalize_document_rich_text({'richTextModelVersion':1,'typography':modern['typography'],'objects':{'x':{'type':'text','html':'legacy only'}},'designPages':[]},strict=True))

 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':f'p-{i}','paragraphStyleId':'body','runs':[{'id':f'r-{i}','text':'x','marks':{}}]} for i in range(MAX_PARAGRAPHS+1)],'entities':{}},strict=True,style_ids={'body'}))
 reject(lambda:normalize_rich_text({'version':1,'paragraphs':[{'id':'p-good','paragraphStyleId':'body','list':{'type':'bullet','level':MAX_LIST_DEPTH+1,'start':1,'marker':'disc'},'runs':[{'id':'r-good','text':'x','marks':{}}]}],'entities':{}},strict=True,style_ids={'body'}))

 reject(lambda:migrate_legacy('deep',{'type':'text','html':'<div>'*(MAX_LEGACY_NESTING+1)+'x'+'</div>'*(MAX_LEGACY_NESTING+1)},style_ids={'body'},default_style_id='body'))
 reject(lambda:migrate_legacy('huge',{'type':'text','html':'x'*(contract['maxHtmlBytes']+1)},style_ids={'body'},default_style_id='body'))
 print('V21_0_RICH_TEXT_MODEL_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
