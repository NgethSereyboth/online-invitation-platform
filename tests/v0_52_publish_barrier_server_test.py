#!/usr/bin/env python3
from __future__ import annotations
import json,sqlite3,urllib.error,urllib.request
from contextlib import closing
from v14_test_utils import app_server

class Client:
    def __init__(self,base):self.base=base;self.token='';self.client_id='barrier-client'
    def request(self,path,method='GET',body=None,expected=200,client_id=None):
        raw=None if body is None else json.dumps(body).encode()
        headers={'Accept':'application/json'}
        if raw is not None:headers['Content-Type']='application/json'
        if self.token:headers['Authorization']=f'Bearer {self.token}'
        if method not in ('GET','HEAD','OPTIONS'):
            headers['X-EInvite-Client-Id']=client_id or self.client_id
            headers['X-EInvite-Mutation-Id']=f'{client_id or self.client_id}-{method.lower()}-{path.rsplit("/",1)[-1]}'
        req=urllib.request.Request(self.base+path,data=raw,method=method,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=20) as response:status=response.status;payload=response.read()
        except urllib.error.HTTPError as exc:status=exc.code;payload=exc.read()
        parsed=json.loads(payload or b'{}')
        assert status==expected,(method,path,status,expected,parsed)
        return parsed

def doc(venue):
    return {'schemaVersion':27,'eventType':'Wedding','fields':{'names':'Barrier Couple','namesKm':'គូស្វាមីភរិយា','date':'2027-02-03','venue':venue},'objects':{},'designPages':[],'sectionOrder':['rsvp'],'settings':{'rsvpEnabled':False,'wishesEnabled':True}}

def main()->int:
    with app_server() as (_proc,base,data):
        c=Client(base);registered=c.request('/api/auth/register','POST',{'email':'publish-barrier@example.com','password':'strong-password-123'},201);c.token=registered['token']
        created=c.request('/api/invitations','POST',{'slug':'publish-barrier','document':doc('Initial venue')},201);iid=created['id'];r0=int(created['updatedAt'])
        intended=doc('Atomic publish venue')
        published=c.request(f'/api/invitations/{iid}/publish','POST',{'document':intended,'expectedRevision':r0},201);r1=int(published['updatedAt']);assert r1>r0,published
        current=c.request(f'/api/invitations/{iid}');assert int(current['updatedAt'])==r1 and current['document']['fields']['venue']=='Atomic publish venue',current
        public=c.request('/api/public/'+current['slug']);assert public['document']['fields']['venue']=='Atomic publish venue',public
        with closing(sqlite3.connect(data/'invites.db')) as db:
            db.row_factory=sqlite3.Row
            inv=db.execute('SELECT draft_json,updated_at,document_version,last_client_id FROM invitations WHERE id=?',(iid,)).fetchone()
            pub=db.execute('SELECT document_json,document_version FROM publications WHERE invitation_id=? ORDER BY published_at DESC LIMIT 1',(iid,)).fetchone()
            pub_count=db.execute('SELECT COUNT(*) FROM publications WHERE invitation_id=?',(iid,)).fetchone()[0]
        assert json.loads(inv['draft_json'])['fields']['venue']=='Atomic publish venue';assert json.loads(pub['document_json'])['fields']['venue']=='Atomic publish venue'
        assert inv['updated_at']==r1 and inv['document_version']==1 and pub['document_version']==1,(dict(inv),dict(pub))
        remote=doc('True remote venue')
        remote_saved=c.request(f'/api/invitations/{iid}','PUT',{'document':remote,'expectedRevision':r1},200,client_id='remote-client');r2=int(remote_saved['updatedAt']);assert r2>r1
        conflict=c.request(f'/api/invitations/{iid}/publish','POST',{'document':doc('Stale local publish'),'expectedRevision':r1},409)
        assert conflict.get('code')=='revision_conflict' and int(conflict.get('updatedAt') or 0)==r2,conflict
        after=c.request(f'/api/invitations/{iid}');assert after['document']['fields']['venue']=='True remote venue' and int(after['updatedAt'])==r2,after
        with closing(sqlite3.connect(data/'invites.db')) as db:
            after_count=db.execute('SELECT COUNT(*) FROM publications WHERE invitation_id=?',(iid,)).fetchone()[0]
        assert after_count==pub_count,(pub_count,after_count)
    print('V0_52_PUBLISH_BARRIER_SERVER_TEST_PASSED');return 0
if __name__=='__main__':raise SystemExit(main())
