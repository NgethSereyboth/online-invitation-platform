from __future__ import annotations
from dataclasses import dataclass
import os


def env(name: str, default: str = "") -> str:
    legacy=name.replace("EINVITE_","SOVAN_",1)
    return os.environ.get(name,os.environ.get(legacy,default))

def flag(name: str, default: bool=False) -> bool:
    return env(name,"1" if default else "0").lower() in {"1","true","yes","on"}

def integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:value=int(env(name,str(default)))
    except Exception:value=default
    return max(minimum,min(maximum,value))

@dataclass(frozen=True)
class PlatformConfig:
    production: bool
    feature_v29: bool
    feature_v30: bool
    feature_v31: bool
    feature_v32: bool
    object_storage_provider: str
    object_storage_bucket: str
    object_storage_endpoint: str
    object_storage_region: str
    object_storage_access_key: str
    object_storage_secret_key: str
    queue_provider: str
    collaboration_provider: str
    backup_provider: str
    public_base_url: str
    trusted_proxy_ips: tuple[str,...]
    request_limit_bytes: int
    upload_limit_bytes: int
    job_workers: int
    db_pool_min: int
    db_pool_max: int
    workspace_delete_days: int
    guest_retention_days: int
    audit_retention_days: int
    collaboration_replay_limit: int
    collaboration_update_limit: int
    raster_pixel_limit: int
    maintenance_mode: bool
    @classmethod
    def from_environment(cls) -> "PlatformConfig":
        return cls(
            production=flag("EINVITE_PRODUCTION"),feature_v29=flag("EINVITE_FEATURE_V29",True),feature_v30=flag("EINVITE_FEATURE_V30",True),feature_v31=flag("EINVITE_FEATURE_V31",True),feature_v32=flag("EINVITE_FEATURE_V32",True),
            object_storage_provider=env("EINVITE_OBJECT_STORAGE_PROVIDER","local").strip().lower() or "local",object_storage_bucket=env("EINVITE_OBJECT_STORAGE_BUCKET").strip(),object_storage_endpoint=env("EINVITE_OBJECT_STORAGE_ENDPOINT").strip(),object_storage_region=env("EINVITE_OBJECT_STORAGE_REGION","auto").strip() or "auto",object_storage_access_key=env("EINVITE_OBJECT_STORAGE_ACCESS_KEY").strip(),object_storage_secret_key=env("EINVITE_OBJECT_STORAGE_SECRET_KEY").strip(),queue_provider=env("EINVITE_QUEUE_PROVIDER","local").strip().lower() or "local",collaboration_provider=env("EINVITE_COLLABORATION_PROVIDER","local").strip().lower() or "local",backup_provider=env("EINVITE_BACKUP_PROVIDER","local").strip().lower() or "local",public_base_url=env("EINVITE_PUBLIC_BASE_URL").strip().rstrip('/'),trusted_proxy_ips=tuple(x.strip() for x in env("EINVITE_TRUSTED_PROXY_IPS").split(',') if x.strip()),request_limit_bytes=integer("EINVITE_MAX_REQUEST_BYTES",2_000_000,64_000,100_000_000),upload_limit_bytes=integer("EINVITE_MAX_UPLOAD_BYTES",50_000_000,1_000_000,5_000_000_000),job_workers=integer("EINVITE_WORKER_CONCURRENCY",2,0,32),db_pool_min=integer("EINVITE_DATABASE_POOL_MIN",1,1,50),db_pool_max=integer("EINVITE_DATABASE_POOL_MAX",10,1,100),workspace_delete_days=integer("EINVITE_WORKSPACE_TRASH_DAYS",30,1,365),guest_retention_days=integer("EINVITE_GUEST_RETENTION_DAYS",730,1,3650),audit_retention_days=integer("EINVITE_AUDIT_RETENTION_DAYS",730,30,3650),collaboration_replay_limit=integer("EINVITE_COLLABORATION_REPLAY_LIMIT",5000,100,50000),collaboration_update_limit=integer("EINVITE_COLLABORATION_UPDATE_BYTES",256000,4096,1_000_000),raster_pixel_limit=integer("EINVITE_RASTER_MAX_PIXELS",160_000_000,1_000_000,500_000_000),maintenance_mode=flag("EINVITE_MAINTENANCE_MODE"),
        )
    def validate(self) -> list[str]:
        errors=[]
        if self.production and not self.public_base_url.startswith("https://"):errors.append("Production requires an HTTPS EINVITE_PUBLIC_BASE_URL.")
        if self.production and self.object_storage_provider not in {"local","s3","r2","minio"}:errors.append("Unsupported EINVITE_OBJECT_STORAGE_PROVIDER.")
        if self.production and self.object_storage_provider!="local" and not self.object_storage_bucket:errors.append("Production object storage requires EINVITE_OBJECT_STORAGE_BUCKET.")
        if self.production and self.object_storage_provider in {"r2","minio"} and not self.object_storage_endpoint:errors.append("R2/MinIO storage requires EINVITE_OBJECT_STORAGE_ENDPOINT.")
        if self.db_pool_min>self.db_pool_max:errors.append("Database pool minimum exceeds maximum.")
        return errors
    def capabilities(self) -> dict:
        return {"professionalLayers":self.feature_v29,"rasterWorkspace":self.feature_v30,"crdtCollaboration":self.feature_v31,"productionPlatform":self.feature_v32,"objectStorageProvider":self.object_storage_provider,"queueProvider":self.queue_provider,"collaborationProvider":self.collaboration_provider,"backupProvider":self.backup_provider,"maintenanceMode":self.maintenance_mode}
