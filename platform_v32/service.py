from __future__ import annotations
from pathlib import Path
import hashlib,json,time,uuid,threading,zipfile
from urllib.parse import unquote,urlparse
from .schema import ensure_platform_schema,now_ms,uid
from .config import PlatformConfig
from .storage import ObjectStorage
from .jobs import JobQueue
from .observability import Observability
from document_schema_v32 import normalize_document_v32

class PlatformServiceError(ValueError):
    def __init__(self,message,code='platform_error',status=400):super().__init__(message);self.code=code;self.status=status

ROLE_ORDER={'viewer':0,'reviewer':1,'content-editor':2,'designer':3,'manager':4,'owner':5}
ROLE_PERMISSIONS={
 'viewer':{'read'},'reviewer':{'read','comment'},'content-editor':{'read','comment','edit-content'},'designer':{'read','comment','edit-content','edit-design','assets'},'manager':{'read','comment','edit-content','edit-design','assets','publish','manage-members','backup'},'owner':{'*'}
}
SAFE_UPLOAD_MIMES={'image/jpeg','image/png','image/webp','image/gif','audio/mpeg','audio/mp4','video/mp4','video/webm'}

class PlatformService:
    def __init__(self,connect,root:Path,data:Path,signing_secret:str,audit=None,json_logs=False,config=None,upload_validator=None):
        self.connect=connect;self.root=Path(root);self.data=Path(data);self.audit=audit;self.config=config or PlatformConfig.from_environment();self.upload_validator=upload_validator;ensure_platform_schema(connect);self.observability=Observability(connect,json_logs);self.storage=ObjectStorage(self.data/'objects-v32',self.config,signing_secret);self.jobs=JobQueue(connect,self.config.job_workers,audit=audit);self.presence={};self.presence_lock=threading.Lock();self.jobs.register('workspace-backup',self._backup_job);self.jobs.register('workspace-restore',self._restore_job);self.jobs.register('raster-render',self._raster_job);self.jobs.register('media-ingest',self._media_job);self.jobs.register('bulk-personalize',self._bulk_job)
    def _row(self,row):return dict(row) if row else None
    def workspace_for_user(self,user_id):
        with self.connect() as db:
            row=db.execute("SELECT w.*,m.role membership_role FROM workspaces w JOIN workspace_memberships m ON m.workspace_id=w.id WHERE m.user_id=? AND m.status='active' AND w.deleted_at IS NULL ORDER BY CASE WHEN w.kind='personal' THEN 0 ELSE 1 END,w.created_at LIMIT 1",(user_id,)).fetchone()
        if not row:raise PlatformServiceError('Workspace membership not found.','workspace_missing',404)
        return self._row(row)
    def list_workspaces(self,user_id):
        with self.connect() as db:rows=db.execute("SELECT w.id,w.name,w.slug,w.kind,w.plan,w.settings_json,m.role,m.permissions_json,w.created_at,w.updated_at FROM workspaces w JOIN workspace_memberships m ON m.workspace_id=w.id WHERE m.user_id=? AND m.status='active' AND w.deleted_at IS NULL ORDER BY w.updated_at DESC",(user_id,)).fetchall()
        result=[]
        for row in rows:
            item=dict(row);item['settings']=self._loads(item.pop('settings_json','{}'),{});item['permissions']=self._loads(item.pop('permissions_json','{}'),{});result.append(item)
        return result
    def create_workspace(self,user_id,name,plan='free'):
        name=str(name or 'Workspace').strip()[:120] or 'Workspace';slug=self._slug(name)+'-'+uuid.uuid4().hex[:8];workspace_id=uid()
        with self.connect() as db:
            db.execute("INSERT INTO workspaces(id,name,slug,kind,owner_id,plan,settings_json,created_at,updated_at) VALUES(?,?,?,'organization',?,?, '{}',?,?)",(workspace_id,name,slug,user_id,str(plan)[:30],now_ms(),now_ms()))
            db.execute("INSERT INTO workspace_memberships(workspace_id,user_id,role,status,permissions_json,created_at,updated_at) VALUES(?,?,'owner','active','{}',?,?)",(workspace_id,user_id,now_ms(),now_ms()))
        self._audit(user_id,'workspace.created','workspace',workspace_id,{'name':name});return {'id':workspace_id,'name':name,'slug':slug,'role':'owner'}
    def membership(self,workspace_id,user_id):
        with self.connect() as db:return self._row(db.execute("SELECT w.id workspace_id,w.owner_id,w.plan,m.role,m.permissions_json FROM workspaces w JOIN workspace_memberships m ON m.workspace_id=w.id WHERE w.id=? AND m.user_id=? AND m.status='active' AND w.deleted_at IS NULL",(workspace_id,user_id)).fetchone())
    def authorize(self,workspace_id,user_id,permission='read'):
        membership=self.membership(workspace_id,user_id)
        if not membership:raise PlatformServiceError('Resource not found.','not_found',404)
        allowed=ROLE_PERMISSIONS.get(membership['role'],set());custom=self._loads(membership.get('permissions_json'),{})
        if '*' not in allowed and permission not in allowed and custom.get(permission) is not True:raise PlatformServiceError('You do not have permission for this action.','permission_denied',403)
        return membership
    def invitation_scope(self,invitation_id,user_id,permission='read'):
        with self.connect() as db:
            row=db.execute("SELECT id,owner_id,workspace_id,draft_json,updated_at,document_epoch,document_version FROM invitations WHERE id=? AND deleted_at IS NULL",(invitation_id,)).fetchone()
            collaborator=db.execute("SELECT role FROM invitation_collaborators WHERE invitation_id=? AND user_id=?",(invitation_id,user_id)).fetchone()
        if not row:raise PlatformServiceError('Invitation not found.','not_found',404)
        workspace_id=row['workspace_id'] or self.workspace_for_user(row['owner_id'])['id']
        membership=self.membership(workspace_id,user_id)
        if membership:
            membership=self.authorize(workspace_id,user_id,permission)
        else:
            role='owner' if row['owner_id']==user_id else str(collaborator['role'] if collaborator else '')
            role={'content':'content-editor','commenter':'reviewer'}.get(role,role)
            allowed=ROLE_PERMISSIONS.get(role,set())
            if not role or ('*' not in allowed and permission not in allowed):raise PlatformServiceError('Resource not found.','not_found',404)
            membership={'workspace_id':workspace_id,'role':role,'invitation_scoped':True}
        return dict(row),workspace_id,membership
    def publication_readiness(self,invitation_id,user_id,document):
        invitation,workspace_id,_=self.invitation_scope(invitation_id,user_id,'publish');blockers=[];references=[]
        public_keys={'assetId','previewAssetId','exportAssetId','resultAssetId'};reference_keys=public_keys|{'sourceAssetId'}
        def walk(value):
            if isinstance(value,dict):
                for child_key,child in list(value.items()):
                    if child and child_key in reference_keys:references.append((value,child_key,str(child),child_key in public_keys))
                    walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        walk(document)
        if references:
            candidate_ids={asset_id for _,_,asset_id,_ in references};path_hints=set()
            for container,_,_,_ in references:
                for key in ('serverId','serverAssetId','canonicalAssetId'):
                    if container.get(key):candidate_ids.add(str(container[key]))
                for key in ('url','src','serverUrl','previewUrl','exportUrl'):
                    raw=str(container.get(key) or '').strip()
                    if not raw:continue
                    try:path=Path(unquote(urlparse(raw).path)).name
                    except Exception:path=Path(raw.split('?',1)[0]).name
                    if path:path_hints.add(path)
            with self.connect() as db:
                known={};path_rows={}
                if candidate_ids:
                    marks=','.join('?' for _ in candidate_ids)
                    rows=db.execute(f"SELECT id,workspace_id,invitation_id,processing_state,path FROM assets WHERE id IN ({marks})",tuple(candidate_ids)).fetchall()
                    known={row['id']:row for row in rows}
                    versions=db.execute(f"SELECT asset_id,workspace_id,visibility FROM object_versions WHERE asset_id IN ({marks}) AND deleted_at IS NULL",tuple(candidate_ids)).fetchall();version_map={row['asset_id']:row for row in versions}
                else:version_map={}
                if path_hints:
                    marks=','.join('?' for _ in path_hints)
                    for row in db.execute(f"SELECT id,workspace_id,invitation_id,processing_state,path FROM assets WHERE path IN ({marks})",tuple(path_hints)).fetchall():path_rows.setdefault(row['path'],[]).append(row)
            resolved=[]
            def scope_issue(row):
                if row['workspace_id'] not in {None,'',workspace_id}:return 'asset_wrong_workspace'
                if row['invitation_id'] not in {None,'',invitation_id}:return 'asset_wrong_invitation'
                return ''
            for container,key,original_id,is_public in references:
                asset_id=original_id;row=known.get(asset_id);version=version_map.get(asset_id);migration_candidate=None;candidate_issue=''
                if not row and not version:
                    for candidate_id in (container.get('serverId'),container.get('serverAssetId'),container.get('canonicalAssetId')):
                        candidate=known.get(str(candidate_id or ''))
                        if not candidate:continue
                        issue=scope_issue(candidate)
                        if issue:candidate_issue=candidate_issue or issue;continue
                        migration_candidate=candidate;break
                    if not migration_candidate:
                        for url_key in ('url','src','serverUrl','previewUrl','exportUrl'):
                            raw=str(container.get(url_key) or '').strip()
                            if not raw:continue
                            try:path=Path(unquote(urlparse(raw).path)).name
                            except Exception:path=Path(raw.split('?',1)[0]).name
                            for candidate in path_rows.get(path,[]):
                                issue=scope_issue(candidate)
                                if issue:candidate_issue=candidate_issue or issue;continue
                                migration_candidate=candidate;break
                            if migration_candidate:break
                    if migration_candidate:
                        asset_id=str(migration_candidate['id']);row=migration_candidate
                        if key=='assetId' and not container.get('localAssetId'):container['localAssetId']=original_id
                        container[key]=asset_id
                        if key=='assetId':container['serverId']=asset_id
                        resolved.append({'legacyId':original_id,'assetId':asset_id,'field':key})
                if row:
                    issue=scope_issue(row)
                    if issue:blockers.append({'code':issue,'assetId':asset_id})
                    elif row['processing_state']!='ready':blockers.append({'code':'asset_not_ready','assetId':asset_id})
                elif version and version['workspace_id']!=workspace_id:blockers.append({'code':'asset_wrong_workspace','assetId':asset_id})
                elif not row and not version:blockers.append({'code':candidate_issue or 'asset_missing','assetId':asset_id})
                elif is_public and version and version['visibility']!='public':blockers.append({'code':'public_rendition_required','assetId':asset_id})
        else:resolved=[]
        return {'ready':not blockers,'blockers':blockers,'resolvedAssetIds':resolved,'workspaceId':workspace_id,'fingerprint':self._fingerprint(document),'documentEpoch':int(invitation.get('document_epoch') or 1),'documentVersion':int(invitation.get('document_version') or 0)}

    def status(self,user_id):
        workspace=self.workspace_for_user(user_id);errors=self.config.validate();return {'version':'32.0','implementationStatus':'complete-pending-independent-audit','documentSchemaVersion':27,'platformSchemaVersion':18,'productionReady':self.config.production and not errors,'configurationErrors':errors,'workspace':{'id':workspace['id'],'name':workspace['name'],'role':workspace['membership_role']},'capabilities':self.config.capabilities(),'storage':self.storage.health(),'observability':self.observability.snapshot(),'limits':{'requestBytes':self.config.request_limit_bytes,'uploadBytes':self.config.upload_limit_bytes,'collaborationUpdateBytes':self.config.collaboration_update_limit,'collaborationReplay':self.config.collaboration_replay_limit,'rasterPixels':self.config.raster_pixel_limit},'credentials':{'objectStorage':bool(self.config.object_storage_bucket) or self.config.object_storage_provider=='local','externalCollaboration':self.config.collaboration_provider=='local','queue':self.config.queue_provider=='local'}}
    def collaboration_snapshot(self,invitation_id,user_id):
        invitation,workspace_id,_=self.invitation_scope(invitation_id,user_id,'read');document=self._loads(invitation['draft_json'],{});epoch=int(invitation.get('document_epoch') or 1)
        with self.connect() as db:
            checkpoint=db.execute("SELECT id,document_json,fingerprint,state_vector_json,created_at FROM collaboration_checkpoints WHERE invitation_id=? AND document_epoch=? ORDER BY created_at DESC LIMIT 1",(invitation_id,epoch)).fetchone();rows=db.execute("SELECT id,actor_id,logical_clock,update_type,path_json,payload_json,created_at,revision FROM collaboration_updates WHERE invitation_id=? AND document_epoch=? ORDER BY revision DESC LIMIT ?",(invitation_id,epoch,self.config.collaboration_replay_limit)).fetchall()
        updates=[self._update_row(row,invitation_id,epoch) for row in reversed(rows)];return {'invitationId':invitation_id,'workspaceId':workspace_id,'epoch':epoch,'revision':max([int(row['revision']) for row in rows] or [0]),'document':document,'checkpoint':{'id':checkpoint['id'],'fingerprint':checkpoint['fingerprint'],'createdAt':checkpoint['created_at']} if checkpoint else None,'updates':updates,'presence':self._presence(invitation_id)}
    def collaboration_updates(self,invitation_id,user_id,since=0):
        invitation,workspace_id,_=self.invitation_scope(invitation_id,user_id,'read');epoch=int(invitation.get('document_epoch') or 1)
        with self.connect() as db:rows=db.execute("SELECT id,actor_id,logical_clock,update_type,path_json,payload_json,created_at,revision FROM collaboration_updates WHERE invitation_id=? AND document_epoch=? AND revision>? ORDER BY revision LIMIT ?",(invitation_id,epoch,max(0,int(since)),self.config.collaboration_replay_limit)).fetchall()
        return {'epoch':epoch,'revision':max([int(row['revision']) for row in rows] or [int(since)]),'updates':[self._update_row(row,invitation_id,epoch) for row in rows],'presence':self._presence(invitation_id),'workspaceId':workspace_id}
    def append_collaboration_updates(self,invitation_id,user_id,data):
        invitation,workspace_id,membership=self.invitation_scope(invitation_id,user_id,'edit-design' if data.get('design') else 'edit-content');epoch=int(invitation.get('document_epoch') or 1)
        if int(data.get('epoch') or epoch)!=epoch:raise PlatformServiceError('Document epoch changed.','epoch_mismatch',409)
        actor=str(data.get('actor') or '')[:160]
        if not actor:raise PlatformServiceError('Actor identity is required.','invalid_actor')
        updates=data.get('updates') or []
        if not isinstance(updates,list) or len(updates)>500:raise PlatformServiceError('A maximum of 500 updates may be submitted at once.','update_limit')
        acknowledged=[];vector={};revision=0;applied=0;document=self._loads(invitation.get('draft_json'),{})
        with self.connect() as db:
            row=db.execute("SELECT COALESCE(MAX(revision),0) max_revision FROM collaboration_updates WHERE invitation_id=? AND document_epoch=?",(invitation_id,epoch)).fetchone();revision=int(row['max_revision'] or 0)
            for raw in updates:
                update=self._validate_update(raw,invitation_id,epoch,actor);encoded=json.dumps(update['payload'],ensure_ascii=False,separators=(',',':')).encode()
                if len(encoded)>self.config.collaboration_update_limit:raise PlatformServiceError('Collaboration update exceeds the configured byte limit.','update_too_large')
                revision+=1
                try:
                    db.execute("INSERT INTO collaboration_updates(id,workspace_id,invitation_id,document_epoch,actor_id,logical_clock,update_type,path_json,payload_json,update_bytes,created_at,revision) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(update['id'],workspace_id,invitation_id,epoch,update['actor'],update['clock'],update['type'],json.dumps(update['path'],separators=(',',':')),json.dumps(update['payload'],ensure_ascii=False,separators=(',',':')),len(encoded),now_ms(),revision));acknowledged.append(update['id']);vector[actor]=max(vector.get(actor,0),update['clock']);self._apply_document_update(document,update);applied+=1
                except PlatformServiceError:raise
                except Exception:
                    existing=db.execute("SELECT id,revision FROM collaboration_updates WHERE invitation_id=? AND document_epoch=? AND actor_id=? AND logical_clock=?",(invitation_id,epoch,actor,update['clock'])).fetchone()
                    if existing:acknowledged.append(existing['id']);revision=max(revision,int(existing['revision']))
                    else:raise
            if applied:
                normalize_document_v32(document,strict=True,mutate=True);now=now_ms();db.execute("UPDATE invitations SET draft_json=?,document_version=COALESCE(document_version,0)+1,updated_at=? WHERE id=? AND document_epoch=?",(json.dumps(document,ensure_ascii=False,separators=(',',':')),now,invitation_id,epoch))
        self.observability.increment('collaboration.updates',len(acknowledged),{'role':membership['role']},workspace_id);return {'acknowledged':acknowledged,'stateVector':vector,'revision':revision,'epoch':epoch,'documentVersion':int(invitation.get('document_version') or 0)+(1 if applied else 0),'durable':True}

    def presence_update(self,invitation_id,user_id,data):
        invitation,workspace_id,membership=self.invitation_scope(invitation_id,user_id,'read');actor=str(data.get('actor') or '')[:160]
        if not actor:raise PlatformServiceError('Actor identity is required.','invalid_actor')
        item={'actor':actor,'userId':user_id,'name':str(data.get('name') or membership['role']).strip()[:100],'mode':str(data.get('mode') or 'viewing')[:40],'pageId':str(data.get('pageId') or 'hero')[:160],'selectionIds':[str(x)[:160] for x in (data.get('selectionIds') or [])[:100]],'cursor':self._cursor(data.get('cursor')),'updatedAt':now_ms()}
        with self.presence_lock:self.presence[(invitation_id,actor)]=item
        return {'ok':True,'expiresInSeconds':45,'workspaceId':workspace_id}
    def create_checkpoint(self,invitation_id,user_id,data):
        invitation,workspace_id,_=self.invitation_scope(invitation_id,user_id,'edit-design');document=self._loads(invitation['draft_json'],{});epoch=int(invitation.get('document_epoch') or 1);checkpoint_id=uid();fingerprint=str(data.get('fingerprint') or self._fingerprint(document))[:160];name=str(data.get('name') or 'Checkpoint').strip()[:120]
        with self.connect() as db:db.execute("INSERT INTO collaboration_checkpoints(id,workspace_id,invitation_id,document_epoch,name,document_json,fingerprint,state_vector_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(checkpoint_id,workspace_id,invitation_id,epoch,name,json.dumps(document,ensure_ascii=False,separators=(',',':')),fingerprint,json.dumps(data.get('stateVector') or {},separators=(',',':')),user_id,now_ms()))
        self._audit(user_id,'collaboration.checkpoint','invitation',invitation_id,{'checkpointId':checkpoint_id,'epoch':epoch});return {'id':checkpoint_id,'epoch':epoch,'fingerprint':fingerprint,'createdAt':now_ms()}
    def save_raster_document(self,invitation_id,user_id,data):
        invitation,workspace_id,_=self.invitation_scope(invitation_id,user_id,'assets');document=data.get('document') or {};encoded=json.dumps(document,ensure_ascii=False,separators=(',',':'))
        if len(encoded.encode())>2_000_000:raise PlatformServiceError('Raster edit document exceeds 2 MB.','document_too_large')
        width=int(document.get('width') or 0);height=int(document.get('height') or 0)
        if width<1 or height<1 or width*height>self.config.raster_pixel_limit:raise PlatformServiceError('Raster dimensions exceed the configured pixel limit.','raster_limit')
        edit_id=str(document.get('id') or uid())[:160];source=str(document.get('sourceAssetId') or '')[:160]
        if not source:raise PlatformServiceError('A source asset is required.','source_required')
        fingerprint=self._fingerprint(document);now=now_ms()
        with self.connect() as db:db.execute("INSERT INTO raster_edit_documents(id,workspace_id,invitation_id,owner_id,source_asset_id,source_asset_version,edit_version,document_json,status,fingerprint,preview_asset_id,result_asset_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET edit_version=raster_edit_documents.edit_version+1,document_json=excluded.document_json,status=excluded.status,fingerprint=excluded.fingerprint,preview_asset_id=excluded.preview_asset_id,result_asset_id=excluded.result_asset_id,updated_at=excluded.updated_at",(edit_id,workspace_id,invitation_id,user_id,source,max(1,int(document.get('sourceAssetVersion') or 1)),1,encoded,str(document.get('status') or 'draft')[:30],fingerprint,str(document.get('previewAssetId') or '')[:160],str(document.get('exportAssetId') or '')[:160],now,now))
        return {'id':edit_id,'fingerprint':fingerprint,'status':document.get('status') or 'draft','workspaceId':workspace_id}
    def list_raster_documents(self,invitation_id,user_id):
        _,workspace_id,_=self.invitation_scope(invitation_id,user_id,'read')
        with self.connect() as db:rows=db.execute("SELECT id,source_asset_id,source_asset_version,edit_version,status,fingerprint,preview_asset_id,result_asset_id,created_at,updated_at FROM raster_edit_documents WHERE invitation_id=? AND workspace_id=? ORDER BY updated_at DESC LIMIT 100",(invitation_id,workspace_id)).fetchall()
        return [dict(row) for row in rows]
    def submit_raster_render(self,invitation_id,user_id,edit_id,idempotency_key=''):
        _,workspace_id,_=self.invitation_scope(invitation_id,user_id,'assets')
        with self.connect() as db:row=db.execute("SELECT document_json,fingerprint,source_asset_id FROM raster_edit_documents WHERE id=? AND invitation_id=? AND workspace_id=?",(edit_id,invitation_id,workspace_id)).fetchone()
        if not row:raise PlatformServiceError('Raster edit document not found.','not_found',404)
        return self.jobs.submit(workspace_id,user_id,'raster-render',{'editId':edit_id,'fingerprint':row['fingerprint'],'sourceAssetId':row['source_asset_id'],'document':self._loads(row['document_json'],{}),'invitationId':invitation_id,'workspaceId':workspace_id,'ownerId':user_id},invitation_id,idempotency_key or f"raster:{edit_id}:{row['fingerprint']}")
    def list_jobs(self,user_id,limit=50):workspace=self.workspace_for_user(user_id);return self.jobs.list(workspace['id'],limit)
    def submit_backup(self,user_id,data):
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'backup');return self.jobs.submit(workspace['id'],user_id,'workspace-backup',{'workspaceId':workspace['id'],'kind':str(data.get('kind') or 'workspace'),'includeMedia':bool(data.get('includeMedia',True))},'',str(data.get('idempotencyKey') or ''))
    def list_backups(self,user_id):
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'backup')
        with self.connect() as db:rows=db.execute("SELECT id,kind,status,provider,object_key,checksum,size_bytes,metadata_json,recovery_epoch,created_at,completed_at FROM platform_backups WHERE workspace_id=? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 100",(workspace['id'],)).fetchall()
        return [dict(row) for row in rows]
    def backup_preview(self,user_id,backup_id):
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'backup')
        with self.connect() as db:row=db.execute("SELECT * FROM platform_backups WHERE id=? AND workspace_id=? AND deleted_at IS NULL",(backup_id,workspace['id'])).fetchone()
        if not row:raise PlatformServiceError('Backup not found.','not_found',404)
        raw=self._backup_bytes(row);digest=hashlib.sha256(raw).hexdigest()
        if row['checksum'] and digest!=row['checksum']:raise PlatformServiceError('Backup checksum validation failed.','backup_corrupt',409)
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(raw),'r') as archive:
            for info in archive.infolist():
                name=info.filename.replace('\\','/')
                if name.startswith('/') or '..' in Path(name).parts:raise PlatformServiceError('Backup contains an unsafe path.','backup_unsafe',409)
            payload=json.loads(archive.read('workspace.json'))
        return {'id':backup_id,'checksum':digest,'workspace':{'id':payload.get('workspace',{}).get('id'),'name':payload.get('workspace',{}).get('name')},'counts':{'members':len(payload.get('members') or []),'invitations':len(payload.get('invitations') or []),'assets':len(payload.get('assets') or [])},'createdAt':payload.get('createdAt'),'dryRun':True,'restoreCreatesNewEpoch':True}
    def submit_restore(self,user_id,backup_id,data,authorized=False):
        if not authorized:raise PlatformServiceError('Reauthentication is required for restore.','reauthentication_required',403)
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'backup');preview=self.backup_preview(user_id,backup_id)
        if str(data.get('confirmation') or '')!=str(workspace['slug']):raise PlatformServiceError('Type the workspace slug to confirm restore.','confirmation_required',409)
        return self.jobs.submit(workspace['id'],user_id,'workspace-restore',{'workspaceId':workspace['id'],'backupId':backup_id,'preview':preview},'',str(data.get('idempotencyKey') or f"restore:{backup_id}:{workspace['id']}"),max_retries=0)
    def storage_status(self,user_id):
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'read')
        with self.connect() as db:row=db.execute("SELECT COALESCE(SUM(size_bytes),0) total_bytes,COUNT(*) object_count FROM object_versions WHERE workspace_id=? AND deleted_at IS NULL",(workspace['id'],)).fetchone();uploads=db.execute("SELECT COUNT(*) pending FROM upload_sessions_v32 WHERE workspace_id=? AND status IN ('pending','uploading')",(workspace['id'],)).fetchone()
        return {'workspaceId':workspace['id'],'provider':self.storage.health(),'totalBytes':int(row['total_bytes'] or 0),'objectCount':int(row['object_count'] or 0),'pendingUploads':int(uploads['pending'] or 0),'privateOriginals':True,'signedDelivery':True,'multipartReady':True}
    def create_upload_session(self,user_id,data):
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'assets')
        invitation_id=str(data.get('invitationId') or '')[:160]
        if invitation_id:self.invitation_scope(invitation_id,user_id,'assets')
        name=str(data.get('name') or 'upload.bin')[:180];mime=str(data.get('mime') or 'application/octet-stream').strip().lower()[:120];size=max(1,int(data.get('size') or 0));checksum=str(data.get('checksum') or '')[:128].lower()
        if mime not in SAFE_UPLOAD_MIMES:raise PlatformServiceError('Unsupported upload type.','unsupported_upload_type',415)
        if size>self.config.upload_limit_bytes:raise PlatformServiceError('Upload exceeds the configured workspace limit.','upload_too_large',413)
        if checksum and (len(checksum)!=64 or not all(ch in '0123456789abcdef' for ch in checksum)):raise PlatformServiceError('Checksum must be a complete SHA-256 hexadecimal digest.','invalid_checksum')
        asset_id=uid();key=self.storage.safe_key(workspace['id'],asset_id,1,name);session_id=uid();expires=now_ms()+60*60*1000;multipart=bool(data.get('multipart')) and size>8_000_000
        multipart_info=self.storage.start_multipart(key,mime,{'workspace':workspace['id'],'asset':asset_id,'sha256':checksum}) if multipart else None
        upload=self.storage.signed_upload(key,mime,size,checksum,900) if not multipart else multipart_info
        with self.connect() as db:db.execute("INSERT INTO upload_sessions_v32(id,workspace_id,owner_id,invitation_id,object_key,mime,size_bytes,checksum,multipart_id,status,parts_json,expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,'pending','[]',?,?,?)",(session_id,workspace['id'],user_id,invitation_id,key,mime,size,checksum,str((multipart_info or {}).get('uploadId') or ''),expires,now_ms(),now_ms()))
        return {'id':session_id,'assetId':asset_id,'workspaceId':workspace['id'],'objectKey':key,'expiresAt':expires,'multipart':multipart,'upload':upload}
    def sign_upload_part(self,user_id,session_id,data):
        with self.connect() as db:row=db.execute("SELECT * FROM upload_sessions_v32 WHERE id=? AND owner_id=? AND status IN ('pending','uploading')",(session_id,user_id)).fetchone()
        if not row:raise PlatformServiceError('Upload session not found.','not_found',404)
        self.authorize(row['workspace_id'],user_id,'assets');part=self.storage.sign_multipart_part(row['object_key'],row['multipart_id'],int(data.get('partNumber') or 0),900)
        with self.connect() as db:db.execute("UPDATE upload_sessions_v32 SET status='uploading',updated_at=? WHERE id=?",(now_ms(),session_id))
        return part
    def complete_upload_session(self,user_id,session_id,data):
        with self.connect() as db:row=db.execute("SELECT * FROM upload_sessions_v32 WHERE id=? AND owner_id=? AND status IN ('pending','uploading')",(session_id,user_id)).fetchone()
        if not row:raise PlatformServiceError('Upload session not found.','not_found',404)
        self.authorize(row['workspace_id'],user_id,'assets')
        if row['multipart_id']:
            self.storage.complete_multipart(row['object_key'],row['multipart_id'],data.get('parts') or [])
        info=self.storage.stat(row['object_key'])
        if int(info['size'])!=int(row['size_bytes']):raise PlatformServiceError('Uploaded object size does not match the signed session.','upload_size_mismatch',409)
        if self.storage.provider!='local' and str(info.get('mime') or '').lower()!=str(row['mime']).lower():raise PlatformServiceError('Uploaded object type does not match the signed session.','upload_type_mismatch',409)
        expected=str(row['checksum'] or '');claimed=str((info.get('metadata') or {}).get('sha256') or data.get('checksum') or '').lower()
        if expected and claimed!=expected:raise PlatformServiceError('Uploaded object checksum does not match.','upload_checksum_mismatch',409)
        validation={};actual=claimed
        if self.upload_validator:
            try:
                raw=self.storage.read(row['object_key'])
                if len(raw)!=int(row['size_bytes']):raise ValueError('Uploaded object size changed during validation')
                actual=hashlib.sha256(raw).hexdigest()
                if expected and actual!=expected:raise ValueError('Uploaded object checksum does not match')
                validation=self.upload_validator(raw,str(row['mime']),str(data.get('name') or 'Uploaded asset')) or {}
            except Exception as exc:
                try:self.storage.delete(row['object_key'])
                except Exception:pass
                with self.connect() as db:db.execute("UPDATE upload_sessions_v32 SET status='failed',updated_at=? WHERE id=?",(now_ms(),session_id))
                raise PlatformServiceError('Uploaded object failed security validation.','upload_security_validation_failed',422) from exc
        parts=str(row['object_key']).split('/');asset_id=(parts[3] if len(parts)>4 and parts[0]=='workspaces' and parts[2]=='assets' else uid())[:160];version_id=uid();now=now_ms()
        with self.connect() as db:
            db.execute("INSERT INTO object_versions(id,workspace_id,asset_id,version,provider,object_key,sha256,mime,size_bytes,metadata_json,visibility,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(version_id,row['workspace_id'],asset_id,1,self.storage.provider,row['object_key'],expected or actual,row['mime'],info['size'],json.dumps({'etag':info.get('etag','')},separators=(',',':')),'private',now))
            if row['invitation_id']:
                db.execute("INSERT INTO assets(id,invitation_id,name,mime,path,size,created_at,folder,tags_json,favorite,sha256,width,height,dominant_color,object_id,processing_state,workspace_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(asset_id,row['invitation_id'],str(data.get('name') or 'Uploaded asset')[:180],row['mime'],row['object_key'],info['size'],now,'','[]',0,expected or actual,int(validation.get('width') or 0),int(validation.get('height') or 0),str(validation.get('dominantColor') or '')[:20],version_id,'ready',row['workspace_id']))
            db.execute("UPDATE upload_sessions_v32 SET status='completed',parts_json=?,updated_at=? WHERE id=?",(json.dumps(data.get('parts') or [],separators=(',',':'))[:1_000_000],now,session_id))
        self._audit(user_id,'asset.upload_completed','asset',asset_id,{'workspaceId':row['workspace_id'],'sessionId':session_id,'size':info['size']})
        return {'id':asset_id,'versionId':version_id,'workspaceId':row['workspace_id'],'status':'ready','privateOriginal':True,'size':info['size'],'mime':row['mime']}
    def sign_object_url(self,user_id,data,base_url):
        workspace=self.workspace_for_user(user_id);self.authorize(workspace['id'],user_id,'read')
        key=str(data.get('key') or '')
        if not key.startswith(f"workspaces/{workspace['id']}/"):
            raise PlatformServiceError('Resource not found.','not_found',404)
        with self.connect() as db:stored=db.execute("SELECT mime FROM object_versions WHERE workspace_id=? AND object_key=? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",(workspace['id'],key)).fetchone()
        if not stored:raise PlatformServiceError('Resource not found.','not_found',404)
        disposition=str(data.get('disposition') or 'inline').lower()
        if disposition not in {'inline','attachment'}:disposition='inline'
        if disposition=='inline' and str(stored['mime'] or '').lower() not in SAFE_UPLOAD_MIMES:disposition='attachment'
        ttl=max(60,min(3600,int(data.get('ttl') or 900)))
        return {'url':self.storage.signed_url(key,base_url,ttl,disposition),'expiresIn':ttl,'disposition':disposition}
    def submit_privacy_request(self,user_id,data):
        workspace=self.workspace_for_user(user_id);kind=str(data.get('kind') or 'export')[:40]
        if kind not in {'export','delete-user','delete-workspace','delete-invitation','retention-review'}:
            raise PlatformServiceError('Unsupported privacy request.','invalid_privacy_request')
        request_id=uid();now=now_ms();scope=data.get('scope') if isinstance(data.get('scope'),dict) else {}
        with self.connect() as db:db.execute("INSERT INTO privacy_requests(id,workspace_id,user_id,kind,status,scope_json,result_json,created_at) VALUES(?,?,?,?,?,?,'{}',?)",(request_id,workspace['id'],user_id,kind,'queued',json.dumps(scope,ensure_ascii=False,separators=(',',':')),now))
        self._audit(user_id,'privacy.requested','workspace',workspace['id'],{'requestId':request_id,'kind':kind,'scope':scope})
        return {'id':request_id,'kind':kind,'status':'queued','workspaceId':workspace['id']}
    def privacy_status(self,user_id):
        workspace=self.workspace_for_user(user_id)
        with self.connect() as db:requests=db.execute("SELECT id,kind,status,created_at,completed_at FROM privacy_requests WHERE workspace_id=? AND user_id=? ORDER BY created_at DESC LIMIT 20",(workspace['id'],user_id)).fetchall()
        return {'workspaceId':workspace['id'],'leastDataDefaults':True,'guestRetentionDays':self.config.guest_retention_days,'auditRetentionDays':self.config.audit_retention_days,'analyticsSeparatedFromAudit':True,'requests':[dict(row) for row in requests]}
    def _backup_job(self,payload,progress,cancelled):
        workspace_id=str(payload['workspaceId']);backup_id=uid();now=now_ms();path=self.data/'backups-v32'/f"workspace-{workspace_id}-{now}.zip";path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            workspace=db.execute("SELECT * FROM workspaces WHERE id=?",(workspace_id,)).fetchone();members=db.execute("SELECT workspace_id,user_id,role,status,created_at,updated_at FROM workspace_memberships WHERE workspace_id=?",(workspace_id,)).fetchall();invitations=db.execute("SELECT id,slug,draft_json,updated_at,is_published,document_epoch,document_version FROM invitations WHERE workspace_id=? AND deleted_at IS NULL",(workspace_id,)).fetchall();assets=db.execute("SELECT id,invitation_id,name,mime,size,sha256,created_at FROM assets WHERE workspace_id=?",(workspace_id,)).fetchall()
        progress(.2);payload_out={'schema':'einvite-workspace-backup-v32','workspace':dict(workspace) if workspace else {},'members':[dict(row) for row in members],'invitations':[dict(row) for row in invitations],'assets':[dict(row) for row in assets],'createdAt':now}
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as archive:archive.writestr('workspace.json',json.dumps(payload_out,ensure_ascii=False,indent=2))
        progress(.9);raw=path.read_bytes();raw_hash=hashlib.sha256(raw).hexdigest();size=len(raw);provider='local';object_key=str(path.relative_to(self.data))
        if self.config.backup_provider!='local':
            object_key=f"workspaces/{workspace_id}/backups/{path.name}";stored=self.storage.put(object_key,raw,'application/zip',{'workspace':workspace_id,'sha256':raw_hash});provider=stored['provider'];path.unlink(missing_ok=True)
        with self.connect() as db:db.execute("INSERT INTO platform_backups(id,workspace_id,owner_id,kind,status,provider,object_key,checksum,size_bytes,metadata_json,recovery_epoch,created_at,completed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(backup_id,workspace_id,str(workspace['owner_id'] if workspace else ''),str(payload.get('kind') or 'workspace'),'completed',provider,object_key,raw_hash,size,json.dumps({'includeMedia':payload.get('includeMedia',True),'encryptedByProvider':provider!='local'},separators=(',',':')),0,now,now_ms()))
        return {'backupId':backup_id,'checksum':raw_hash,'sizeBytes':size,'objectKey':object_key,'provider':provider}
    def _backup_bytes(self,row):
        key=str(row['object_key'] or '')
        if str(row['provider'] or 'local')=='local':return (self.data/key).read_bytes()
        return self.storage.read(key)
    def _restore_job(self,payload,progress,cancelled):
        workspace_id=str(payload['workspaceId']);backup_id=str(payload['backupId'])
        with self.connect() as db:backup=db.execute("SELECT * FROM platform_backups WHERE id=? AND workspace_id=? AND deleted_at IS NULL",(backup_id,workspace_id)).fetchone()
        if not backup:raise RuntimeError('Backup not found')
        raw=self._backup_bytes(backup)
        if backup['checksum'] and hashlib.sha256(raw).hexdigest()!=backup['checksum']:raise RuntimeError('Backup checksum validation failed')
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(raw),'r') as archive:
            for info in archive.infolist():
                name=info.filename.replace('\\','/')
                if name.startswith('/') or '..' in Path(name).parts:raise RuntimeError('Unsafe backup path')
            data=json.loads(archive.read('workspace.json'))
        invitations=data.get('invitations') or [];restored=0;now=now_ms()
        with self.connect() as db:
            for index,item in enumerate(invitations):
                if cancelled():raise RuntimeError('Restore cancelled')
                invitation_id=str(item.get('id') or '')
                existing=db.execute("SELECT id,draft_json,document_epoch FROM invitations WHERE id=? AND workspace_id=?",(invitation_id,workspace_id)).fetchone()
                document=self._loads(item.get('draft_json'),{}) if isinstance(item.get('draft_json'),str) else item.get('draft_json') or {};normalize_document_v32(document,strict=True,mutate=True)
                if existing:
                    checkpoint_id=uid();db.execute("INSERT INTO collaboration_checkpoints(id,workspace_id,invitation_id,document_epoch,name,document_json,fingerprint,state_vector_json,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(checkpoint_id,workspace_id,invitation_id,int(existing['document_epoch'] or 1),'Pre-restore recovery point',existing['draft_json'],self._fingerprint(self._loads(existing['draft_json'],{})),'{}',str(backup['owner_id']),now));db.execute("UPDATE invitations SET draft_json=?,document_epoch=COALESCE(document_epoch,1)+1,document_version=0,updated_at=? WHERE id=? AND workspace_id=?",(json.dumps(document,ensure_ascii=False,separators=(',',':')),now,invitation_id,workspace_id));db.execute("DELETE FROM collaboration_updates WHERE invitation_id=?",(invitation_id,));restored+=1
                progress((index+1)/max(1,len(invitations)))
            db.execute("UPDATE platform_backups SET recovery_epoch=recovery_epoch+1 WHERE id=?",(backup_id,))
        return {'backupId':backup_id,'workspaceId':workspace_id,'restoredInvitations':restored,'newRecoveryEpoch':True,'completedAt':now_ms()}
    def _raster_job(self,payload,progress,cancelled):
        try:
            from PIL import Image,ImageEnhance,ImageFilter,ImageOps
        except ImportError as exc:
            raise RuntimeError('Local raster rendering requires Pillow from requirements-production.txt') from exc
        edit=payload.get('document') or {};source_id=str(payload.get('sourceAssetId') or '')
        with self.connect() as db:asset=db.execute("SELECT id,path,mime,name,width,height FROM assets WHERE id=? AND invitation_id=?",(source_id,payload.get('invitationId'))).fetchone()
        if not asset:raise RuntimeError('Raster source asset is unavailable or unauthorized')
        path_value=str(asset['path'] or '')
        raw=self.storage.read(path_value) if path_value.startswith('workspaces/') else (self.data/'uploads'/Path(path_value).name).read_bytes()
        if cancelled():raise RuntimeError('Raster render cancelled')
        from io import BytesIO
        image=Image.open(BytesIO(raw));image.load();image=ImageOps.exif_transpose(image).convert('RGBA');progress(.15)
        if image.width*image.height>self.config.raster_pixel_limit:raise RuntimeError('Raster source exceeds the configured pixel limit')
        crop=edit.get('crop') if isinstance(edit.get('crop'),dict) else {}
        if crop and all(key in crop for key in ('x','y','width','height')):
            x=max(0,int(crop.get('x') or 0));y=max(0,int(crop.get('y') or 0));w=max(1,int(crop.get('width') or image.width));h=max(1,int(crop.get('height') or image.height));image=image.crop((x,y,min(image.width,x+w),min(image.height,y+h)))
        transform=edit.get('transform') if isinstance(edit.get('transform'),dict) else {}
        rotation=float(transform.get('rotation') or 0)
        if rotation:image=image.rotate(-rotation,expand=True,resample=Image.Resampling.BICUBIC)
        if transform.get('flipX'):image=ImageOps.mirror(image)
        if transform.get('flipY'):image=ImageOps.flip(image)
        progress(.35)
        for adjustment in (edit.get('adjustments') or [])[:256]:
            if cancelled():raise RuntimeError('Raster render cancelled')
            if not isinstance(adjustment,dict) or adjustment.get('enabled') is False:continue
            kind=str(adjustment.get('type') or adjustment.get('kind') or '');value=float(adjustment.get('value') or adjustment.get('amount') or 0)
            if kind in {'brightness','exposure'}:image=ImageEnhance.Brightness(image).enhance(max(0,min(4,1+value)))
            elif kind=='contrast':image=ImageEnhance.Contrast(image).enhance(max(0,min(4,1+value)))
            elif kind in {'saturation','vibrance'}:image=ImageEnhance.Color(image).enhance(max(0,min(4,1+value)))
            elif kind=='grayscale':image=ImageOps.grayscale(image).convert('RGBA')
            elif kind=='sepia':
                gray=ImageOps.grayscale(image);image=ImageOps.colorize(gray,'#3b2414','#f5dfb3').convert('RGBA')
            elif kind=='blur':image=image.filter(ImageFilter.GaussianBlur(max(0,min(100,value))))
            elif kind=='sharpen':image=ImageEnhance.Sharpness(image).enhance(max(0,min(8,1+value)))
        for operation in (edit.get('operations') or [])[:2000]:
            if cancelled():raise RuntimeError('Raster render cancelled')
            if not isinstance(operation,dict) or operation.get('enabled') is False:continue
            kind=str(operation.get('type') or operation.get('kind') or '')
            if kind=='resize':
                width=max(1,min(50_000,int(operation.get('width') or image.width)));height=max(1,min(50_000,int(operation.get('height') or image.height)));image=image.resize((width,height),Image.Resampling.LANCZOS)
        progress(.7)
        with self.connect() as db:row=db.execute("SELECT fingerprint,workspace_id,owner_id FROM raster_edit_documents WHERE id=?",(payload['editId'],)).fetchone()
        if not row or row['fingerprint']!=payload['fingerprint']:raise RuntimeError('Raster edit became stale before rendering completed')
        output=BytesIO();image.save(output,'WEBP',quality=92,method=6);data=output.getvalue();asset_id=uid();key=self.storage.safe_key(row['workspace_id'],asset_id,1,f"raster-{payload['editId']}.webp");stored=self.storage.put(key,data,'image/webp',{'edit':payload['editId'],'fingerprint':payload['fingerprint']});now=now_ms();version_id=uid()
        with self.connect() as db:
            db.execute("INSERT INTO object_versions(id,workspace_id,asset_id,version,provider,object_key,sha256,mime,size_bytes,metadata_json,visibility,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(version_id,row['workspace_id'],asset_id,1,stored['provider'],stored['key'],stored['sha256'],'image/webp',stored['size'],json.dumps({'width':image.width,'height':image.height,'sourceAssetId':source_id,'editId':payload['editId']},separators=(',',':')),'private',now))
            db.execute("UPDATE raster_edit_documents SET status='ready',result_asset_id=?,updated_at=? WHERE id=? AND fingerprint=?",(asset_id,now,payload['editId'],payload['fingerprint']))
        progress(1)
        return {'editId':payload['editId'],'status':'ready','assetId':asset_id,'versionId':version_id,'objectKey':key,'mime':'image/webp','width':image.width,'height':image.height,'sizeBytes':len(data),'privateOriginalPreserved':True}
    def _media_job(self,payload,progress,cancelled):progress(.5);return {'status':'provider-hook-ready','assetId':payload.get('assetId','')}
    def _bulk_job(self,payload,progress,cancelled):
        rows=payload.get('rows') or [];results=[]
        for index,row in enumerate(rows[:10000]):
            if cancelled():raise RuntimeError('Bulk generation cancelled')
            results.append({'index':index,'status':'prepared','fingerprint':self._fingerprint(row)})
            if index%50==0:progress((index+1)/max(1,len(rows)))
        return {'prepared':len(results),'items':results[:1000]}
    def _presence(self,invitation_id):
        cutoff=now_ms()-45000
        with self.presence_lock:
            for key,item in list(self.presence.items()):
                if item['updatedAt']<cutoff:self.presence.pop(key,None)
            return [dict(item) for (iid,_),item in self.presence.items() if iid==invitation_id]
    def _update_row(self,row,invitation_id,epoch):return {'version':1,'id':row['id'],'documentId':invitation_id,'epoch':epoch,'actor':row['actor_id'],'clock':int(row['logical_clock']),'type':row['update_type'],'path':self._loads(row['path_json'],[]),'payload':self._loads(row['payload_json'],{}),'timestamp':int(row['created_at']),'origin':'remote','revision':int(row['revision'])}
    def _validate_update(self,raw,invitation_id,epoch,actor):
        if not isinstance(raw,dict):raise PlatformServiceError('Invalid collaboration update.','invalid_update')
        update_type=str(raw.get('type') or '')
        if update_type not in {'set','delete','sequence-insert','sequence-move','rich-text','checkpoint'}:raise PlatformServiceError('Unknown collaboration update type.','invalid_update')
        path=raw.get('path') or []
        if not isinstance(path,list) or len(path)>20 or any(not isinstance(key,(str,int)) or len(str(key))>160 for key in path):raise PlatformServiceError('Invalid collaboration path.','invalid_update')
        if path and str(path[0]) in {'ownerId','workspaceId','permissions','published','publication','sessions','secrets'}:raise PlatformServiceError('Collaboration updates cannot change authority or publication fields.','forbidden_path',403)
        return {'id':str(raw.get('id') or uid())[:160],'actor':actor,'clock':max(1,int(raw.get('clock') or 1)),'type':update_type,'path':[str(key) for key in path],'payload':raw.get('payload') if isinstance(raw.get('payload'),dict) else {}}
    def _cursor(self,value):
        if not isinstance(value,dict):return None
        try:return {'x':max(0,min(1,float(value.get('x',0)))),'y':max(0,min(1,float(value.get('y',0))))}
        except Exception:return None
    def _audit(self,user_id,action,target_type,target_id,metadata):
        if self.audit:
            try:self.audit(user_id,action,target_type,target_id,metadata)
            except Exception:pass
    @staticmethod
    def _loads(value,fallback):
        try:return json.loads(value or '')
        except Exception:return fallback
    @staticmethod
    def _slug(value):return ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value)).strip('-')[:60] or 'workspace'
    @staticmethod
    def _fingerprint(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
