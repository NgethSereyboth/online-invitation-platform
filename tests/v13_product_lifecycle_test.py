#!/usr/bin/env python3
"""V13 product lifecycle checks: tenant isolation, versions, operations, guest check-in and recovery."""
from __future__ import annotations
import json,os,socket,subprocess,sys,tempfile,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def req(base,path,method='GET',body=None,token=None,expected=200):
    data=None if body is None else json.dumps(body).encode('utf-8');headers={'Content-Type':'application/json'}
    if token:headers['Authorization']=f'Bearer {token}'
    request=urllib.request.Request(base+path,data=data,method=method,headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=20) as response:status=response.status;raw=response.read()
    except urllib.error.HTTPError as exc:status=exc.code;raw=exc.read()
    if status!=expected:
        try:shown=json.loads(raw or b'{}')
        except Exception:shown=raw[:200]
        raise AssertionError((method,path,status,expected,shown))
    return json.loads(raw or b'{}')

def wait(base):
    for _ in range(120):
        try:req(base,'/api/health');return
        except Exception:time.sleep(.1)
    raise RuntimeError('server did not start')

def run():
    port=free_port();base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='einvite-v13-life-') as data_dir:
        env={**os.environ,'EINVITE_DATA_DIR':data_dir,'EINVITE_DEV_AUTH_TOKENS':'1'}
        proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'server.py'),'--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            wait(base)
            owner=req(base,'/api/auth/register','POST',{'email':'life-owner@example.com','password':'strong-owner-password'},expected=201);token=owner['token']
            other=req(base,'/api/auth/register','POST',{'email':'life-other@example.com','password':'strong-other-password'},expected=201);other_token=other['token']
            doc={'schemaVersion':13,'fields':{'names':'Version One','date':'2027-01-10','time':'10:00','venue':'Hall'},'objects':{},'designPages':[],'sectionOrder':['events','guest-info'],'settings':{'rsvpEnabled':False,'openingEnabled':False},'events':[{'id':'main','name':'Ceremony','date':'2027-01-10','time':'10:00','venue':'Hall','enabled':True}]}
            invite=req(base,'/api/invitations','POST',{'slug':'v13-life','document':doc},token=token,expected=201);iid=invite['id']
            # Tenant isolation.
            req(base,f'/api/invitations/{iid}',token=other_token,expected=404)
            # Immutable publications and restore-as-draft.
            pub1=req(base,f'/api/invitations/{iid}/publish','POST',{'document':doc},token=token,expected=201)
            changed=json.loads(json.dumps(doc));changed['fields']['names']='Version Two'
            req(base,f'/api/invitations/{iid}','PUT',{'document':changed},token=token)
            pub2=req(base,f'/api/invitations/{iid}/publish','POST',{'document':changed},token=token,expected=201)
            versions=req(base,f'/api/invitations/{iid}/versions',token=token);assert len(versions)>=2
            restored=req(base,f'/api/invitations/{iid}/restore-version','POST',{'version':pub1['version']},token=token);assert restored['document']['fields']['names']=='Version One'
            old=req(base,f'/api/invitations/{iid}/versions/{pub1["version"]}',token=token);new=req(base,f'/api/invitations/{iid}/versions/{pub2["version"]}',token=token);assert old['document']['fields']['names']=='Version One' and new['document']['fields']['names']=='Version Two'
            # Custom domain and scheduled lifecycle metadata.
            future=int(time.time()*1000)+86_400_000
            ops=req(base,f'/api/invitations/{iid}/operations','PUT',{'customDomain':'invite.example.com','publishAt':future,'unpublishAt':future+86_400_000,'expiresAt':future+172_800_000},token=token)
            assert ops['customDomain']=='invite.example.com' and ops['publishAt']==future
            # Household/group/seating metadata and duplicate check-in warning.
            guest=req(base,f'/api/invitations/{iid}/guests','POST',{'name':'Guest One','email':'guest@example.com','groupName':'VIP','householdId':'family-a','tags':['family','front-row'],'tableName':'Table 1','seatLabel':'A1'},token=token,expected=201)
            first=req(base,f'/api/invitations/{iid}/guests/{guest["id"]}/check-in','PUT',{'checkedIn':True},token=token);second=req(base,f'/api/invitations/{iid}/guests/{guest["id"]}/check-in','PUT',{'checkedIn':True},token=token)
            assert first['alreadyCheckedIn'] is False and second['alreadyCheckedIn'] is True and first['checkedInAt']==second['checkedInAt']
            guests=req(base,f'/api/invitations/{iid}/guests',token=token);row=next(x for x in guests if x['id']==guest['id']);assert row['group_name']=='VIP' and row['table_name']=='Table 1' and 'family' in row['tags']
            # Scheduled campaigns preserve scheduled state when created.
            campaign=req(base,f'/api/invitations/{iid}/campaigns','POST',{'name':'VIP reminder','channel':'telegram','message':'Reminder','segment':{'group':'VIP'},'scheduledAt':future},token=token,expected=201);assert campaign['state']=='scheduled' and campaign['scheduledAt']==future
            # Trash is recoverable and removes the invitation from normal reads until restore.
            req(base,f'/api/invitations/{iid}/trash','POST',{},token=token)
            trash=req(base,'/api/trash',token=token);assert any(x['id']==iid for x in trash)
            req(base,f'/api/invitations/{iid}',token=token,expected=404)
            req(base,f'/api/invitations/{iid}/restore','POST',{},token=token)
            restored_invite=req(base,f'/api/invitations/{iid}',token=token);assert restored_invite['id']==iid
            print('V13_PRODUCT_LIFECYCLE_TEST_PASSED')
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            if proc.stderr and proc.returncode not in (0,-15):
                err=proc.stderr.read().decode('utf-8','replace')
                if err:print(err,file=sys.stderr)

if __name__=='__main__':run()
