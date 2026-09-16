from __future__ import annotations
from pathlib import Path
import hashlib,hmac,time,urllib.parse,uuid,os

class StorageError(ValueError):pass

class ObjectStorage:
    """Provider-neutral private object storage.

    Local storage is always available for development. S3-compatible providers
    use optional boto3 from requirements-production.txt and support AWS S3,
    Cloudflare R2, MinIO, and equivalent endpoints.
    """
    def __init__(self,root:Path,config,signing_secret:str):
        self.root=root.resolve();self.config=config;self.secret=signing_secret.encode();self.root.mkdir(parents=True,exist_ok=True);self._client=None
    @property
    def provider(self):return self.config.object_storage_provider
    def safe_key(self,workspace_id:str,asset_id:str,version:int,name:str='object.bin')->str:
        clean=''.join(ch for ch in Path(name).name if ch.isalnum() or ch in '._-')[:120] or 'object.bin'
        wid=''.join(ch for ch in str(workspace_id) if ch.isalnum() or ch in '-_')[:120]
        aid=''.join(ch for ch in str(asset_id) if ch.isalnum() or ch in '-_')[:120]
        if not wid or not aid:raise StorageError('Workspace and asset identifiers are required')
        return f"workspaces/{wid}/assets/{aid}/v{max(1,int(version))}/{uuid.uuid4().hex[:12]}-{clean}"
    def local_path(self,key:str)->Path:
        target=(self.root/key).resolve()
        if self.root not in target.parents:raise StorageError('Unsafe object key')
        return target
    def _s3(self):
        if self._client is not None:return self._client
        try:import boto3
        except ImportError as exc:raise StorageError('S3-compatible storage requires boto3 from requirements-production.txt') from exc
        options={'region_name':self.config.object_storage_region or 'auto'}
        if self.config.object_storage_endpoint:options['endpoint_url']=self.config.object_storage_endpoint
        if self.config.object_storage_access_key:options['aws_access_key_id']=self.config.object_storage_access_key
        if self.config.object_storage_secret_key:options['aws_secret_access_key']=self.config.object_storage_secret_key
        self._client=boto3.client('s3',**options);return self._client
    def put(self,key:str,data:bytes,mime='application/octet-stream',metadata=None)->dict:
        if self.provider=='local':return self.put_local(key,data)
        if not self.config.object_storage_bucket:raise StorageError('Object-storage bucket is not configured')
        digest=hashlib.sha256(data).hexdigest();meta={str(k)[:40]:str(v)[:200] for k,v in (metadata or {}).items()};meta['sha256']=digest
        self._s3().put_object(Bucket=self.config.object_storage_bucket,Key=key,Body=data,ContentType=mime,Metadata=meta,ServerSideEncryption='AES256')
        return {'provider':self.provider,'key':key,'size':len(data),'sha256':digest}
    def put_local(self,key:str,data:bytes)->dict:
        path=self.local_path(key);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_bytes(data);os.replace(tmp,path);return {'provider':'local','key':key,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def read(self,key:str)->bytes:
        if self.provider=='local':return self.read_local(key)
        response=self._s3().get_object(Bucket=self.config.object_storage_bucket,Key=key);return response['Body'].read()
    def read_local(self,key:str)->bytes:return self.local_path(key).read_bytes()
    def delete(self,key:str):
        if self.provider=='local':return self.delete_local(key)
        self._s3().delete_object(Bucket=self.config.object_storage_bucket,Key=key)
    def delete_local(self,key:str):self.local_path(key).unlink(missing_ok=True)
    def stat(self,key:str)->dict:
        if self.provider=='local':
            path=self.local_path(key);return {'size':path.stat().st_size,'mime':'application/octet-stream','metadata':{},'etag':''}
        response=self._s3().head_object(Bucket=self.config.object_storage_bucket,Key=key)
        return {'size':int(response.get('ContentLength') or 0),'mime':str(response.get('ContentType') or 'application/octet-stream'),'metadata':dict(response.get('Metadata') or {}),'etag':str(response.get('ETag') or '').strip('"')}
    def start_multipart(self,key:str,mime:str,metadata=None)->dict:
        if self.provider=='local':return {'provider':'local','multipart':False,'objectKey':key}
        response=self._s3().create_multipart_upload(Bucket=self.config.object_storage_bucket,Key=key,ContentType=mime,Metadata={str(k):str(v) for k,v in (metadata or {}).items()},ServerSideEncryption='AES256')
        return {'provider':self.provider,'multipart':True,'objectKey':key,'uploadId':response['UploadId']}
    def sign_multipart_part(self,key:str,upload_id:str,part_number:int,ttl:int=900)->dict:
        if self.provider=='local':raise StorageError('Local storage uses the existing resumable upload endpoint')
        part=max(1,min(10_000,int(part_number)));url=self._s3().generate_presigned_url('upload_part',Params={'Bucket':self.config.object_storage_bucket,'Key':key,'UploadId':upload_id,'PartNumber':part},ExpiresIn=max(60,min(3600,int(ttl))))
        return {'url':url,'partNumber':part,'method':'PUT'}
    def complete_multipart(self,key:str,upload_id:str,parts:list[dict])->dict:
        if self.provider=='local':raise StorageError('Local storage uses the existing resumable upload endpoint')
        normalized=[]
        for item in parts[:10_000]:
            normalized.append({'ETag':str(item.get('etag') or item.get('ETag') or '').strip('"'),'PartNumber':max(1,min(10_000,int(item.get('partNumber') or item.get('PartNumber') or 0)))})
        if not normalized or any(not item['ETag'] for item in normalized):raise StorageError('Multipart completion requires valid part ETags')
        response=self._s3().complete_multipart_upload(Bucket=self.config.object_storage_bucket,Key=key,UploadId=upload_id,MultipartUpload={'Parts':normalized})
        return {'key':key,'etag':str(response.get('ETag') or '').strip('"')}
    def signed_url(self,key:str,base_url:str,ttl:int=900,disposition:str='inline')->str:
        ttl=max(60,min(3600,int(ttl)))
        if self.provider!='local':
            return self._s3().generate_presigned_url('get_object',Params={'Bucket':self.config.object_storage_bucket,'Key':key,'ResponseContentDisposition':disposition},ExpiresIn=ttl)
        expiry=int(time.time())+ttl;message=f"{key}|{expiry}|{disposition}".encode();signature=hmac.new(self.secret,message,hashlib.sha256).hexdigest();return f"{base_url.rstrip('/')}/api/platform/v32/objects/{urllib.parse.quote(key,safe='')}?expires={expiry}&disposition={urllib.parse.quote(disposition)}&signature={signature}"
    def signed_upload(self,key:str,mime:str,size:int,checksum:str='',ttl:int=900)->dict:
        ttl=max(60,min(3600,int(ttl)))
        if self.provider=='local':return {'provider':'local','method':'POST','endpoint':'/api/uploads','objectKey':key,'expiresIn':ttl}
        conditions=[['content-length-range',1,max(1,int(size))],{'Content-Type':mime}]
        fields={'Content-Type':mime}
        if checksum:fields['x-amz-meta-sha256']=checksum;conditions.append({'x-amz-meta-sha256':checksum})
        response=self._s3().generate_presigned_post(Bucket=self.config.object_storage_bucket,Key=key,Fields=fields,Conditions=conditions,ExpiresIn=ttl)
        return {'provider':self.provider,'method':'POST','url':response['url'],'fields':response['fields'],'objectKey':key,'expiresIn':ttl}
    def verify_signature(self,key:str,expiry:int,disposition:str,signature:str)->bool:
        if self.provider!='local':return False
        if int(expiry)<int(time.time()):return False
        expected=hmac.new(self.secret,f"{key}|{int(expiry)}|{disposition}".encode(),hashlib.sha256).hexdigest();return hmac.compare_digest(expected,str(signature))
    def health(self):
        configured=self.provider=='local' or bool(self.config.object_storage_bucket)
        result={'provider':self.provider,'configured':configured,'privateOriginals':True,'signedDelivery':True,'multipartReady':self.provider!='local','localRoot':str(self.root) if self.provider=='local' else ''}
        if self.provider!='local':result.update({'bucket':self.config.object_storage_bucket,'endpointConfigured':bool(self.config.object_storage_endpoint)})
        return result
    def readiness(self):
        result=self.health()
        try:
            if self.provider=='local':
                marker=self.root/f'.ready-{uuid.uuid4().hex}'
                marker.write_bytes(b'ok');marker.unlink()
            else:
                if not self.config.object_storage_bucket:raise StorageError('Object-storage bucket is not configured')
                self._s3().head_bucket(Bucket=self.config.object_storage_bucket)
            result['ready']=True
        except Exception as exc:
            result['ready']=False;result['error']=f'{type(exc).__name__}: storage readiness probe failed'
        return result
