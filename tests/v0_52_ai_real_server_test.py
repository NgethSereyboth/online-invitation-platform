#!/usr/bin/env python3
from __future__ import annotations
import json, sqlite3, urllib.error, urllib.request
from pathlib import Path
from contextlib import closing
from v14_test_utils import app_server

ROOT=Path(__file__).resolve().parents[1]

class Client:
    def __init__(self,base:str):
        self.base=base; self.token=''
    def request(self,path:str,method='GET',body=None,expected=200,stream=False):
        raw=None if body is None else json.dumps(body).encode('utf-8')
        headers={'Accept':'application/x-ndjson, application/json'}
        if raw is not None: headers['Content-Type']='application/json'
        if self.token: headers['Authorization']=f'Bearer {self.token}'
        req=urllib.request.Request(self.base+path,data=raw,method=method,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=20) as response:
                status=response.status; payload=response.read(); ctype=response.headers.get('Content-Type','')
        except urllib.error.HTTPError as exc:
            status=exc.code; payload=exc.read(); ctype=exc.headers.get('Content-Type','')
        if status!=expected:
            raise AssertionError((method,path,status,expected,payload[:1000]))
        if stream:
            return payload,ctype
        return json.loads(payload or b'{}')

def document():
    return {
        'schemaVersion':27,'eventType':'Wedding',
        'fields':{'names':'AI Integration Couple','namesKm':'គូស្វាមីភរិយា','date':'2027-01-02','venue':'Phnom Penh'},
        'objects':{},'designPages':[],'sectionOrder':['rsvp'],
        'settings':{'rsvpEnabled':False,'wishesEnabled':True},
    }

def main()->int:
    with app_server({'EINVITE_AI_PROVIDER':'offline','EINVITE_AI_ENDPOINT':'','EINVITE_AI_API_KEY':'','EINVITE_AI_ENABLED':'1'}) as (_proc,base,data):
        client=Client(base)
        registered=client.request('/api/auth/register','POST',{'email':'ai-real-server@example.com','password':'strong-password-123'},201)
        client.token=registered['token']
        invite=client.request('/api/invitations','POST',{'slug':'ai-real-server','document':document()},201)
        invite_id=invite['id']
        client.request(f'/api/invitations/{invite_id}/comments','POST',{'body':'Open review note for AI context'},201)
        thread=client.request(f'/api/invitations/{invite_id}/ai/threads','POST',{'title':'Real server regression'},201)
        raw,ctype=client.request(f"/api/invitations/{invite_id}/ai/threads/{thread['id']}/messages",'POST',{
            'message':'Please check this invitation and suggest a harmless improvement.',
            'context':{'pageId':'hero','objectIds':[]},
            'idempotencyKey':'v052-real-server-regression'
        },200,stream=True)
        assert 'application/x-ndjson' in ctype,ctype
        text=raw.decode('utf-8','replace')
        lines=[line for line in text.splitlines() if line.strip()]
        assert lines,text
        events=[json.loads(line) for line in lines]
        types=[event.get('type') for event in events]
        assert types[0]=='job.started',types
        assert 'context.ready' in types,types
        assert any(t in types for t in ('assistant.completed','question','plan.proposed')),types
        assert types[-1] in ('job.completed','question','error'),types
        assert types[-1] != 'error',events[-1]
        lowered=text.lower()
        for forbidden in ('traceback','sqlite3.operationalerror','no such column','invites.db',str(data).lower()):
            assert forbidden not in lowered,(forbidden,text)
        # Confirm the real thread persisted both user and assistant output.
        stored=client.request(f"/api/invitations/{invite_id}/ai/threads/{thread['id']}")
        assert any(m.get('role')=='user' for m in stored.get('messages',[])),stored
        assert any(m.get('role')=='assistant' for m in stored.get('messages',[])),stored
        with closing(sqlite3.connect(data/'invites.db')) as db:
            job=db.execute('SELECT status,progress_json FROM ai_jobs WHERE conversation_id=? ORDER BY created_at DESC LIMIT 1',(thread['id'],)).fetchone()
            review=db.execute('SELECT COUNT(*),SUM(CASE WHEN resolved=0 THEN 1 ELSE 0 END) FROM invitation_comments WHERE invitation_id=?',(invite_id,)).fetchone()
        assert job and job[0]=='completed',job
        progress=json.loads(job[1] or '{}')
        assert progress.get('questions')==1 or progress.get('toolCalls')==0,(job,progress)
        assert review==(1,1),review
    print('V0_52_AI_REAL_SERVER_TEST_PASSED')
    return 0

if __name__=='__main__': raise SystemExit(main())
