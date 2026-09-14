#!/usr/bin/env python3
"""Authenticated live-server V19.1 typography persistence and publication contract."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from v14_test_utils import app_server
from v15_http_integration_test import Client
from browser_runtime import launch_chromium,skipped

def document(font='Arial,sans-serif'):
 return {'schemaVersion':13,'eventType':'Wedding','fields':{'names':'Typography V19.1','namesKm':'អក្សរខ្មែរ','date':'2027-02-14','venue':'Phnom Penh'},'objects':{'title':{'type':'text','html':'សូមស្វាគមន៍ Welcome to our celebration','font':font,'fontSize':40,'fontWeight':'700','textAutoFit':'fit','textAutoFitMax':56,'textMinFontSize':8,'textWrap':'pretty','textColumns':2,'textColumnGap':16,'textAlign':'justify','textVerticalAlign':'bottom','left':'10%','top':'10%','width':'80%','height':'140px','zIndex':2}},'designPages':[],'sectionOrder':[],'settings':{'rsvpEnabled':False}}

def main()->int:
 try:from playwright.sync_api import sync_playwright
 except Exception as exc:return skipped('V19_1_SERVER_TYPOGRAPHY_CONTRACT',exc)
 with app_server() as (_process,base,_data):
  client=Client(base);registered,_=client.request('/api/auth/register','POST',{'email':'v19-1-server@example.com','password':'strong-password-123'},201);client.token=registered['token']
  created,_=client.request('/api/invitations','POST',{'slug':'v19-1-typography','document':document()},201);iid=created['id'];slug=created['slug']
  loaded,_=client.request(f'/api/invitations/{iid}');obj=loaded['document']['objects']['title']
  assert obj['font']=='sans-arial' and obj['textAlign']=='justify' and obj['textColumns']==2,obj
  updated=document('noto-serif-khmer');updated['objects']['title'].update(textColumns=3,textColumnGap=20,textAutoFitMax=64,textMinFontSize=9)
  client.request(f'/api/invitations/{iid}','PUT',{'document':updated},200)
  reloaded,_=client.request(f'/api/invitations/{iid}');saved=reloaded['document']['objects']['title']
  assert saved['font']=='noto-serif-khmer' and saved['textAlign']=='justify' and saved['textMinFontSize']==9,saved
  client.request(f'/api/invitations/{iid}/publish','POST',{'document':reloaded['document']},201)
  public,_=client.request(f'/api/public/{slug}');published=public['document']['objects']['title']
  for key in ('font','textAlign','textWrap','textColumns','textColumnGap','textAutoFit','textAutoFitMax','textMinFontSize'):assert published[key]==saved[key],(key,published,saved)
  hostile=document('Arial;position:fixed;inset:0');hostile['objects']['title']['html']='INJECTED'
  body,_=client.request(f'/api/invitations/{iid}','PUT',{'document':hostile},400)
  assert 'font' in body.get('error','').lower(),body
  unchanged,_=client.request(f'/api/invitations/{iid}');assert unchanged['document']['objects']['title']['html']!= 'INJECTED'
  with sync_playwright() as p:
   try:browser=launch_chromium(p)
   except Exception as exc:return skipped('V19_1_SERVER_TYPOGRAPHY_CONTRACT',exc)
   page=browser.new_page(viewport={'width':390,'height':844});errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   page.goto(f'{base}/i/{slug}',wait_until='networkidle',timeout=40_000)
   page.wait_for_selector('.published-object[data-object-id="title"]')
   result=page.evaluate("""()=>{const o=document.querySelector('.published-object[data-object-id="title"]'),f=o.querySelector('.typography-flow'),s=getComputedStyle(o),fs=getComputedStyle(f);return{align:s.textAlign,font:s.fontFamily,columns:fs.columnCount,gap:fs.columnGap,computed:o.dataset.textComputedFontSize,overflowX:f.scrollWidth-Math.max(0,o.clientWidth-16),overflowY:f.scrollHeight-Math.max(0,o.clientHeight-16),html:o.outerHTML}}""")
   assert result['align']=='justify' and result['columns']=='3',result
   assert 'EInvite Noto Serif Khmer' in result['font'] and result['overflowX']<=2 and result['overflowY']<=2,result
   for bad in ('position:fixed','inset:0','url('):assert bad not in result['html']
   assert not errors,errors
   browser.close()
 print('V19_1_SERVER_TYPOGRAPHY_CONTRACT_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
