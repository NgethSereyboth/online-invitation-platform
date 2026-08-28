#!/usr/bin/env python3
"""Real-HTTP persistence and immutable publication coverage for V17 commands."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v14_test_utils import app_server
from v15_http_integration_test import Client
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from document_schema_v32 import CURRENT_VERSION


def main()->int:
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION':'0'}) as (_process,base,_data):
        client=Client(base)
        registered,_=client.request('/api/auth/register','POST',{'email':'v17-persist@example.com','password':'strong-password-123'},201)
        client.token=registered['token']
        first={
            'schemaVersion':13,'eventType':'Wedding',
            'fields':{'names':'Professional Foundation','namesKm':'គ្រឹះកែសម្រួល','date':'2027-05-18','venue':'Phnom Penh'},
            'objects':{
                'title':{'type':'text','html':'Professional Foundation','left':'10%','top':'12%','width':'70%','height':'10%','rotation':0,'zIndex':1,'locked':False,'visible':True},
                'photo':{'type':'image','src':'','left':'18%','top':'30%','width':'42%','height':'28%','rotation':0,'zIndex':2,'locked':False,'visible':True},
            },
            'designPages':[],'sectionOrder':[],'settings':{'rsvpEnabled':False,'wishesEnabled':False},
            'editorModel':{'selectionIds':['title'],'professionalTransformVersion':1},
        }
        created,_=client.request('/api/invitations','POST',{'slug':'v17-professional','document':first},201)
        iid,slug,revision=created['id'],created['slug'],created['updatedAt']
        client.request(f'/api/invitations/{iid}/publish','POST',{'document':first},201)
        current,_=client.request(f'/api/invitations/{iid}');revision=current['updatedAt']
        public_first,_=client.request(f'/api/public/{slug}')
        assert public_first['document']['objects']['title']['left']=='10%'

        draft={**first,'objects':{**first['objects'],'title':{**first['objects']['title'],'left':'24%','top':'19%','width':'58%','height':'14%','rotation':17},'photo':{**first['objects']['photo'],'locked':True,'visible':False}},'sceneGraph':{'version':1,'pages':[{'id':'hero','name':'Main hero','kind':'hero','enabled':True,'objectIds':['title','photo']}],'objects':{},'groups':{'group-v17':{'id':'group-v17','name':'Couple block','children':['title','photo'],'parentId':'','locked':False,'visible':True,'collapsed':False}}}}
        saved,_=client.request(f'/api/invitations/{iid}','PUT',{'document':draft,'expectedRevision':revision},200,headers={'X-EInvite-Client-Id':'v17-test','X-EInvite-Mutation-Id':'transform-1'})
        assert saved['updatedAt']>revision
        stored,_=client.request(f'/api/invitations/{iid}')
        title=stored['document']['objects']['title']
        assert (title['left'],title['top'],title['width'],title['height'],title['rotation'])==('24%','19%','58%','14%',17)
        assert stored['document']['objects']['photo']['locked'] is True and stored['document']['objects']['photo']['visible'] is False
        assert stored['document']['schemaVersion']==CURRENT_VERSION

        public_still,_=client.request(f'/api/public/{slug}')
        assert public_still['document']['objects']['title']['left']=='10%','draft edit leaked into existing publication'
        client.request(f'/api/invitations/{iid}/publish','POST',{'document':stored['document']},201)
        public_after,_=client.request(f'/api/public/{slug}')
        assert public_after['document']['objects']['title']['left']=='24%'
        assert public_after['document']['objects']['title']['rotation']==17
        assert public_after['document']['settings']['rsvpEnabled'] is False
    print('V17_PERSISTENCE_SNAPSHOT_TEST_PASSED')
    return 0

if __name__=='__main__':raise SystemExit(main())
