#!/usr/bin/env python3
from __future__ import annotations
import copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server import validate_document
from document_schema_v32 import CURRENT_VERSION

def reject(doc):
 try:validate_document(copy.deepcopy(doc))
 except (TypeError,ValueError):return
 raise AssertionError('server accepted invalid rich-text document')

def base(html='<strong>Hello</strong><br>សួស្តី'):
 return {'schemaVersion':13,'objects':{'title':{'type':'text','html':html,'font':'noto-serif','fontSize':52,'left':'10%','top':'10%','width':'80%','height':'120px'}},'designPages':[]}

def main():
 migrated=validate_document(base())
 assert migrated['schemaVersion']==CURRENT_VERSION and migrated['richTextModelVersion']==1
 obj=migrated['objects']['title'];assert obj['richTextModelVersion']==1 and obj['richText']['version']==1
 assert obj['html'].startswith('<strong>Hello</strong><br>')
 assert any(run['locale']=='km' for p in obj['richText']['paragraphs'] for run in p['runs'])
 assert validate_document(copy.deepcopy(migrated))==migrated
 tampered=copy.deepcopy(migrated);tampered['objects']['title']['html']='Changed outside model';reject(tampered)
 mixed=copy.deepcopy(migrated);del mixed['objects']['title']['richText'];reject(mixed)
 unsafe=base('<a href="javascript:alert(1)">bad</a>');valid=validate_document(unsafe);assert 'javascript:' not in valid['objects']['title']['html']
 modern=copy.deepcopy(migrated);entity={'id':'link-good','type':'link','url':'javascript:alert(1)'};modern['objects']['title']['richText']['entities']={'link-good':entity};modern['objects']['title']['richText']['paragraphs'][0]['runs'][0]['entityId']='link-good';modern['objects']['title']['html']='';reject(modern)
 unknown=copy.deepcopy(migrated);unknown['objects']['title']['richText']['paragraphs'][0]['evil']=1;reject(unknown)

 half=copy.deepcopy(migrated);del half['objects']['title']['richTextModelVersion'];reject(half)
 wrong=copy.deepcopy(migrated);wrong['objects']['title']['richTextModelVersion']=99;reject(wrong)
 print('V21_0_RICH_TEXT_SERVER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
