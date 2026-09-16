#!/usr/bin/env python3
"""Deterministic V19.1 typography model, registry and renderer contract."""
from __future__ import annotations
import json,subprocess,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
 script=textwrap.dedent(r'''
  const fs=require('fs'),vm=require('vm');global.window=global;
  for(const file of ['typography-contract.js','editor-schema-v13.js','typography-layout-service.js','renderer-core.js'])vm.runInThisContext(fs.readFileSync(file,'utf8'));
  const normalized=EInviteEditorSchema.normalizeObject('khmer',{type:'text',fontSize:44,textAlign:'bad',textAutoFit:'fit',textAutoFitMax:999,textMinFontSize:-5,textWrap:'bad',textColumns:9,textColumnGap:-4},'hero');
  const legacy=EInviteEditorSchema.normalizeObject('legacy',{type:'text',font:'Arial,sans-serif',html:'Legacy'},'hero');
  const rendered=EInviteRenderer.renderObject({type:'text',html:'សូមស្វាគមន៍ <strong>Welcome</strong>',font:'sans-arial',fontSize:28,textAlign:'justify',textWrap:'pretty',textColumns:3,textColumnGap:18,textAutoFit:'fit',textAutoFitMax:46,textMinFontSize:12,left:'0%',top:'0%',width:'100%',height:'120px'},{id:'khmer'});
  const malformed=[NaN,Infinity,-Infinity,null,'',[],{},'bad'].map(v=>EInviteEditorSchema.normalizeObject('x',{type:'text',fontSize:v,textAutoFitMax:v,textMinFontSize:v,textColumnGap:v},'hero'));
  console.log(JSON.stringify({normalized,legacy,rendered,malformed,latin:EInviteRenderer.typographyFontStack('serif-georgia'),khmer:EInviteRenderer.typographyFontStack('sans-arial'),ids:EInviteTypography.fontIds}));
 ''')
 proc=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True,encoding='utf-8',check=True)
 data=json.loads(proc.stdout);n=data['normalized'];legacy=data['legacy'];rendered=data['rendered']
 assert n['font']=='noto-serif' and n['textAlign']=='center'
 assert n['textAutoFit']=='fit' and n['textAutoFitMax']==200 and n['textMinFontSize']==8
 assert n['textWrap']=='normal' and n['textColumns']==3 and n['textColumnGap']==0
 assert legacy['font']=='sans-arial' and legacy['textAutoFit']=='none'
 assert "Georgia" in data['latin'] and 'EInvite Noto Serif Khmer' in data['latin']
 assert 'EInvite Noto Sans Khmer' in data['khmer'] and 'Khmer UI' in data['khmer']
 assert {'noto-sans','noto-serif','noto-sans-khmer','noto-serif-khmer'}<=set(data['ids'])
 for item in data['malformed']:
  for key in ('fontSize','textAutoFitMax','textMinFontSize','textColumnGap'):
   assert isinstance(item[key],(int,float)) and item[key] is not None,(key,item)
 for token in ('data-typography-v19="true"','data-font="sans-arial"','text-align:justify','column-count:3','column-gap:18px','text-wrap:pretty','typography-flow','EInvite Noto Sans Khmer','សូមស្វាគមន៍','Welcome'):
  assert token in rendered,token
 for bad in ('position:fixed','url(','/*','999px'):assert bad not in rendered,bad
 print('V19_1_TYPOGRAPHY_MODEL_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
