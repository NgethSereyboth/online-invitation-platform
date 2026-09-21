#!/usr/bin/env python3
from __future__ import annotations
import io,json,os,socket,subprocess,sys,tempfile,time,urllib.error,urllib.parse,urllib.request,zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return int(sock.getsockname()[1])

def request(base,path,method='GET',body=None,token='',expected=None,headers=None,raw=False):
    if raw:
        data=body
        req_headers=dict(headers or {})
    else:
        data=None if body is None else json.dumps(body).encode('utf-8')
        req_headers={'Content-Type':'application/json',**(headers or {})}
    if token:req_headers['Authorization']=f'Bearer {token}'
    req=urllib.request.Request(base+path,data=data,method=method,headers=req_headers)
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            status=response.status; payload=response.read(); ctype=response.headers.get('Content-Type','')
    except urllib.error.HTTPError as exc:
        status=exc.code;payload=exc.read();ctype=exc.headers.get('Content-Type','')
    if 'application/x-ndjson' in ctype:
        result=[json.loads(line) for line in payload.decode('utf-8').splitlines() if line.strip()]
    else:
        try:result=json.loads(payload or b'{}')
        except Exception:result={'raw':payload.decode('utf-8','replace')}
    if expected is not None:assert status==expected,(path,status,result)
    return status,result

def register(base,email):
    status,result=request(base,'/api/auth/register','POST',{'email':email,'password':'password123'},expected=201)
    return result['user'],result['token']

def wait(base,proc):
    for _ in range(200):
        if proc.poll() is not None:raise RuntimeError('server exited early')
        try:
            if request(base,'/api/health')[0]==200:return
        except Exception:pass
        time.sleep(.1)
    raise RuntimeError('server unavailable')

def png_bytes():
    image=Image.new('RGB',(8,8),(245,230,210));buf=io.BytesIO();image.save(buf,'PNG');return buf.getvalue()

def zip_bytes(name,data=b'bad'):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:archive.writestr(name,data)
    return buf.getvalue()

def tool_ids(payload):return {item['id'] for item in payload.get('tools',[])}

def main()->int:
    port=free_port();base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='einvite-v53-backend-') as data:
        env={**os.environ,'EINVITE_DATA_DIR':data,'EINVITE_ADMIN_EMAIL':'v53-admin@example.com','EINVITE_DEV_AUTH_TOKENS':'1','EINVITE_AI_FAKE_PROVIDER':'1','EINVITE_AI_PROVIDER':'fake','EINVITE_ENFORCE_PLAN_LIMITS':'1','PYTHONDONTWRITEBYTECODE':'1'}
        proc=subprocess.Popen([sys.executable,'-u','server.py','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait(base,proc)
            admin,admin_token=register(base,'v53-admin@example.com')
            owner,owner_token=register(base,'v53-owner@example.com')
            manager,manager_token=register(base,'v53-manager@example.com')
            designer,designer_token=register(base,'v53-designer@example.com')
            viewer,viewer_token=register(base,'v53-viewer@example.com')
            document={'schemaVersion':14,'eventType':'Wedding','fields':{'names':'V53 Couple'},'objects':{'title':{'type':'text','text':'V53 Couple','left':'10%','top':'10%','width':'80%','height':'80px','zIndex':1}},'designPages':[],'settings':{'rsvpEnabled':True}}
            _,created=request(base,'/api/invitations','POST',{'slug':'v53-ai-project-operator','document':document},owner_token,201);iid=created['id']
            for email,role in [('v53-manager@example.com','manager'),('v53-designer@example.com','designer'),('v53-viewer@example.com','viewer')]:
                request(base,f'/api/invitations/{iid}/collaborators','POST',{'email':email,'role':role},owner_token,200)

            # Dynamic tool discovery is role-aware.
            _,owner_tools=request(base,f'/api/ai-agent/tools?invitationId={iid}',token=owner_token,expected=200)
            _,manager_tools=request(base,f'/api/ai-agent/tools?invitationId={iid}',token=manager_token,expected=200)
            _,designer_tools=request(base,f'/api/ai-agent/tools?invitationId={iid}',token=designer_token,expected=200)
            _,viewer_tools=request(base,f'/api/ai-agent/tools?invitationId={iid}',token=viewer_token,expected=200)
            assert 'publish.prepare' in tool_ids(owner_tools) and 'publish.prepare' in tool_ids(manager_tools)
            assert 'publish.prepare' not in tool_ids(designer_tools)
            assert 'object.update' in tool_ids(designer_tools) and 'object.update' not in tool_ids(viewer_tools)
            assert 'read.project_summary' in tool_ids(viewer_tools)

            # Upload capability disappears immediately when the account setting changes.
            request(base,f'/api/admin/users/{owner["id"]}/uploads','PUT',{'enabled':False},admin_token,200)
            _,blocked_tools=request(base,f'/api/ai-agent/tools?invitationId={iid}',token=owner_token,expected=200)
            assert {'materials.create_folder','materials.import_folder','materials.import_zip'}.isdisjoint(tool_ids(blocked_tools))
            request(base,f'/api/admin/users/{owner["id"]}/uploads','PUT',{'enabled':True},admin_token,200)

            # Recursive folder hierarchy and import job persistence.
            image=png_bytes();manifest={'rootName':'Wedding Materials','files':[{'name':'portrait.png','folder':'Wedding Materials/Bride','size':len(image),'mime':'image/png'}],'emptyDirectories':['Wedding Materials/Decorations/Frames']}
            _,job=request(base,f'/api/invitations/{iid}/materials/import-jobs','POST',manifest,owner_token,201)
            _,asset=request(base,f'/api/invitations/{iid}/assets/raw','POST',image,owner_token,201,headers={'Content-Type':'image/png','Content-Length':str(len(image)),'X-File-Name':urllib.parse.quote('portrait.png'),'X-Material-Folder':urllib.parse.quote('Wedding Materials/Bride'),'X-Material-Import-Job':job['id']},raw=True)
            _,folders=request(base,f'/api/invitations/{iid}/materials/folders',token=owner_token,expected=200)
            folder_names={row['folder'] for row in folders['folders']}
            assert {'Wedding Materials','Wedding Materials/Bride','Wedding Materials/Decorations','Wedding Materials/Decorations/Frames'} <= folder_names
            _,assets=request(base,f'/api/invitations/{iid}/assets',token=owner_token,expected=200)
            uploaded=next(row for row in assets if row['id']==asset['id']);assert uploaded['folder']=='Wedding Materials/Bride'
            _,jobs=request(base,f'/api/invitations/{iid}/materials/import-jobs',token=owner_token,expected=200)
            imported=next(row for row in jobs['jobs'] if row['id']==job['id']);assert imported['processedFiles']==1 and imported['processedBytes']==len(image)

            # Physical storage quota blocks an oversized batch before any file bytes are accepted.
            status,quota=request(base,f'/api/invitations/{iid}/materials/import-jobs','POST',{'rootName':'Too Large','files':[{'name':'huge.mp4','folder':'Too Large','size':300_000_000,'mime':'video/mp4'}]},owner_token)
            assert status==403 and quota.get('code')=='plan_limit_reached',quota

            # Checksum deduplication reuses storage while retaining separate material references.
            _,asset2=request(base,f'/api/invitations/{iid}/assets/raw','POST',image,owner_token,201,headers={'Content-Type':'image/png','Content-Length':str(len(image)),'X-File-Name':urllib.parse.quote('portrait-copy.png'),'X-Material-Folder':urllib.parse.quote('Wedding Materials/Groom')},raw=True)
            assert asset2['duplicate'] is True and asset2['id']!=asset['id']
            _,duplicates=request(base,f'/api/invitations/{iid}/materials/duplicates',token=owner_token,expected=200)
            group=next(row for row in duplicates['groups'] if {entry['id'] for entry in row['assets']}=={asset['id'],asset2['id']})
            assert group['count']==2

            # ZIP traversal is rejected before writes.
            badzip=zip_bytes('../evil.png',image)
            status,bad=request(base,f'/api/invitations/{iid}/materials/import-zip','POST',badzip,owner_token,headers={'Content-Type':'application/zip','Content-Length':str(len(badzip)),'X-File-Name':'evil.zip'},raw=True)
            assert status==400 and 'traversal' in str(bad.get('error','')).lower(),bad

            # Reference image creates a schema-validated blueprint via deterministic fake/offline path.
            _,blueprint=request(base,f'/api/invitations/{iid}/ai/design-blueprints','POST',{'assetIds':[asset['id']],'mode':'style','targetPageId':'hero'},owner_token,201)
            bp=blueprint['blueprint'];assert bp['schema']=='einvite-design-blueprint-v1' and bp['referenceAssetIds']==[asset['id']]
            assert any('watermark' in warning.lower() or 'protected' in warning.lower() for warning in bp['approximationWarnings'])

            # Create mode can preview and then create a separate invitation project from the validated blueprint.
            create_path=f'/api/invitations/{iid}/ai/design-blueprints/{blueprint["id"]}/create-invitation'
            _,bp_preview=request(base,create_path,'POST',{'previewOnly':True,'newInvitationTitle':'Blueprint Preview'},owner_token,200)
            assert bp_preview['previewOnly'] is True and bp_preview['createdInvitationId']=='' and bp_preview['document']['designPages']
            _,bp_created=request(base,create_path,'POST',{'newInvitationTitle':'Blueprint Project','slug':'blueprint-project'},owner_token,201)
            assert bp_created['createdInvitationId'] and bp_created['slug'].startswith('blueprint-project')
            _,new_invite=request(base,f'/api/invitations/{bp_created["createdInvitationId"]}',token=owner_token,expected=200)
            assert new_invite['document']['fields']['names']=='Blueprint Project' and len(new_invite['document']['designPages'][0]['objects'])>=2

            # High-risk publish plan must be explicitly confirmed.
            _,thread=request(base,f'/api/invitations/{iid}/ai/threads','POST',{'title':'Acceptance'},owner_token,201)
            status,events=request(base,f'/api/invitations/{iid}/ai/threads/{thread["id"]}/messages','POST',{'message':'Publish this invitation','context':{'pageId':'hero','objectIds':[]},'idempotencyKey':'v53-publish-plan'},owner_token,expected=200)
            plan_event=next(event for event in events if event.get('type')=='plan.proposed');plan=plan_event['plan'];assert plan['confirmationRequired'] is True
            status,denied=request(base,f'/api/invitations/{iid}/ai/plans/{plan["id"]}/confirm','POST',{'context':{'pageId':'hero','objectIds':[]}},owner_token)
            assert status==409 and denied.get('code') in {'confirmation_required','destructive_confirmation_required'}
            _,confirmed=request(base,f'/api/invitations/{iid}/ai/plans/{plan["id"]}/confirm','POST',{'context':{'pageId':'hero','objectIds':[]},'exactTargetsAccepted':True,'destructiveAccepted':True},owner_token,200)
            assert confirmed['status']=='confirmed'
            _,authorized=request(base,f'/api/invitations/{iid}/ai/plans/{plan["id"]}/authorize','POST',{'index':0,'context':{'pageId':'hero','objectIds':[]}},owner_token,200)
            assert authorized['authorized'] is True and authorized['toolId']=='publish.prepare'

            # A plan created before a draft mutation is rejected as stale.
            _,thread2=request(base,f'/api/invitations/{iid}/ai/threads','POST',{'title':'Stale'},owner_token,201)
            _,events2=request(base,f'/api/invitations/{iid}/ai/threads/{thread2["id"]}/messages','POST',{'message':'Check layout overflow','context':{'pageId':'hero','objectIds':[]},'idempotencyKey':'v53-stale-plan'},owner_token,200)
            stale_plan=next(event['plan'] for event in events2 if event.get('type')=='plan.proposed')
            _,current=request(base,f'/api/invitations/{iid}',token=owner_token,expected=200)
            changed=current['document'];changed.setdefault('fields',{})['venue']='Changed after plan'
            request(base,f'/api/invitations/{iid}','PUT',{'document':changed},owner_token,200)
            status,stale=request(base,f'/api/invitations/{iid}/ai/plans/{stale_plan["id"]}/confirm','POST',{'context':{'pageId':'hero','objectIds':[]}},owner_token)
            assert status==409 and stale.get('code')=='stale_plan',stale

            # Provider details are admin-only and never expose tokens.
            status,_=request(base,'/api/admin/ai/providers',token=owner_token);assert status==403
            _,providers=request(base,'/api/admin/ai/providers',token=admin_token,expected=200)
            serialized=json.dumps(providers).lower();assert 'api_key' not in serialized and 'authorization' not in serialized and 'token' not in serialized
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
    print('V53_1_AI_PROJECT_OPERATOR_BACKEND_TEST_PASSED');return 0

if __name__=='__main__':raise SystemExit(main())
