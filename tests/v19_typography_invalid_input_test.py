#!/usr/bin/env python3
"""Negative V19.1 typography validation and CSS-injection tests."""
from __future__ import annotations
import copy,importlib.util,json,math,subprocess,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load_server():
 import sys;sys.path.insert(0,str(ROOT))
 spec=importlib.util.spec_from_file_location('einvite_server_v19_1',ROOT/'server.py');assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def base(font='noto-sans'):
 return {'schemaVersion':13,'objects':{'title':{'type':'text','html':'សួស្តី Welcome','font':font,'fontSize':32,'textAutoFit':'fit','textAutoFitMax':64,'textMinFontSize':8,'textWrap':'normal','textColumns':1,'textColumnGap':0,'textAlign':'left','left':'0%','top':'0%','width':'80%','height':'100px'}},'designPages':[]}

def main()->int:
 server=load_server()
 # Every enum and numeric boundary is accepted and normalized.
 for align in ('left','center','right','justify'):
  d=base();d['objects']['title']['textAlign']=align;assert server.validate_document(d)['objects']['title']['textAlign']==align
 for wrap in ('normal','balance','pretty'):
  d=base();d['objects']['title']['textWrap']=wrap;assert server.validate_document(d)['objects']['title']['textWrap']==wrap
 for mode in ('none','fit'):
  d=base();d['objects']['title']['textAutoFit']=mode;assert server.validate_document(d)['objects']['title']['textAutoFit']==mode
 for columns in (1,2,3):
  d=base();d['objects']['title']['textColumns']=columns;assert server.validate_document(d)['objects']['title']['textColumns']==columns
 for key,values in {'fontSize':(8,200),'textAutoFitMax':(8,200),'textMinFontSize':(8,72),'textColumnGap':(0,64)}.items():
  for value in values:
   d=base();d['objects']['title'][key]=value
   if key=='textMinFontSize':d['objects']['title']['textAutoFitMax']=max(value,72)
   assert server.validate_document(d)['objects']['title'][key]==value
 # Known stacks migrate, while unknown/CSS-like values are rejected.
 migrated=server.validate_document(base('Arial,sans-serif'))['objects']['title'];assert migrated['font']=='sans-arial'
 hostile=['Arial;position:fixed;inset:0','serif/*x*/','url(https://evil.invalid/x)','bad\x00font','unknown-font','A'*20000]
 malformed=[None,'',[],{},True,False,'12','NaN','Infinity',float('nan'),float('inf')]
 cases=[]
 for value in hostile:cases.append(('font',value))
 for key in ('fontSize','textAutoFitMax','textMinFontSize','textColumns','textColumnGap'):
  for value in malformed:cases.append((key,value))
 for key,value in cases:
  d=base();d['objects']['title'][key]=value
  try:server.validate_document(d)
  except (ValueError,TypeError):pass
  else:raise AssertionError(f'accepted hostile typography {key}={value!r}')
 for key,value in [('textAutoFit','grow'),('textWrap','unsafe'),('textAlign','start'),('textColumns',1.5),('textColumns',0),('textColumns',4)]:
  d=base();d['objects']['title'][key]=value
  try:server.validate_document(d)
  except ValueError:pass
  else:raise AssertionError((key,value))
 d=base();d['objects']['title'].update(textAutoFitMax=12,textMinFontSize=13)
 try:server.validate_document(d)
 except ValueError:pass
 else:raise AssertionError('minimum larger than maximum accepted')
 d=base();d['objects']['title']['html']='X'*200_001
 try:server.validate_document(d)
 except ValueError:pass
 else:raise AssertionError('huge text accepted')
 # Browser model repairs malformed values to finite numbers and never serializes null.
 script=textwrap.dedent(r'''
 const fs=require('fs'),vm=require('vm');global.window=global;
 for(const f of ['typography-contract.js','editor-schema-v13.js','typography-layout-service.js','renderer-core.js'])vm.runInThisContext(fs.readFileSync(f,'utf8'));
 const bad=[NaN,Infinity,-Infinity,null,'',[],{},'bad'];
 const rows=bad.map(v=>EInviteEditorSchema.normalizeObject('x',{type:'text',fontSize:v,textAutoFitMax:v,textMinFontSize:v,textColumns:v,textColumnGap:v},'hero'));
 const hostile=EInviteRenderer.renderObject({type:'text',font:'does-not-exist',html:'safe',fontSize:32},{id:'x'});
 console.log(JSON.stringify({rows,hostile}));
 ''')
 out=json.loads(subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True,check=True).stdout)
 for row in out['rows']:
  encoded=json.dumps(row,allow_nan=False)
  assert 'null' not in encoded
  assert all(math.isfinite(float(row[k])) for k in ('fontSize','textAutoFitMax','textMinFontSize','textColumns','textColumnGap'))
 assert 'does-not-exist' not in out['hostile'] and 'position:fixed' not in out['hostile']
 print('V19_1_TYPOGRAPHY_INVALID_INPUT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
