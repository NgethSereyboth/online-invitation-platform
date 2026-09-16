#!/usr/bin/env python3
"""Provider disclosure, bounded output, invalid response, task, auth, and rate contracts."""
from __future__ import annotations
import importlib.util,json,types,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load():
 sys.path.insert(0,str(ROOT))
 spec=importlib.util.spec_from_file_location('v27_server',ROOT/'server.py');assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def handler(mod,payload,rate=True):
 h=object.__new__(mod.Handler);out=[];h.require_user=lambda:{'id':'u1','email':'u@example.test'};h.rate_limit=lambda *a:rate;h.body=lambda limit:payload;h.json=lambda status,body:out.append((status,body));return h,out
def main()->int:
 mod=load();h=object.__new__(mod.Handler)
 arbitrary='Write a poem about an unrelated rocket';offline=h.local_ai_response('write',arbitrary,{'names':'Sophea & Dara','eventType':'wedding'})
 assert arbitrary not in offline and 'Sophea & Dara' in offline
 try:h.local_ai_response('unknown',arbitrary,{})
 except ValueError:pass
 else:raise AssertionError('Unknown local task accepted')
 old_endpoint,old_key=mod.AI_ENDPOINT,mod.AI_API_KEY
 try:
  unauth=object.__new__(mod.Handler);unauth_out=[];unauth.require_user=lambda:None;unauth.json=lambda status,body:unauth_out.append((status,body));unauth.ai_assist();assert unauth_out==[],unauth_out
  mod.AI_ENDPOINT='';mod.AI_API_KEY='';h,out=handler(mod,{'task':'write','prompt':arbitrary,'context':{'names':'Hosts'}});h.ai_assist();assert out[-1][0]==200 and out[-1][1]['provider']=='template' and out[-1][1]['providerMode']=='offline' and arbitrary not in out[-1][1]['text'],out
  h,out=handler(mod,{'task':'unknown','prompt':'x','context':{}});h.ai_assist();assert out[-1]==(400,{'error':'Unsupported assistant task'}),out
  class Resp:
   def __enter__(self):return self
   def __exit__(self,*a):return False
   def read(self,n):return json.dumps(['invalid-shape']).encode()
  mod.AI_ENDPOINT='https://provider.invalid';original=mod.urllib.request.urlopen;mod.urllib.request.urlopen=lambda *a,**k:Resp()
  h,out=handler(mod,{'task':'write','prompt':'x','context':{'names':'Hosts'}});h.ai_assist();body=out[-1][1];assert body['provider']=='template' and body['providerMode']=='fallback' and 'providerMessage' in body and 'invalid-shape' not in json.dumps(body),out
  mod.urllib.request.urlopen=original
  h,out=handler(mod,{'task':'write','prompt':'x','context':{}},rate=False);h.ai_assist();assert out==[],out
 finally:mod.AI_ENDPOINT,mod.AI_API_KEY=old_endpoint,old_key
 print('V27_3_5_AI_BACKEND_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
